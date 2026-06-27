"""Endpoints de catálogo: productos, marcas, categorías."""
from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from slugify import slugify
from sqlalchemy import func, or_, select

from app.deps import DBSession, require_permission
from app.models.catalog import Brand, Category, Product
from app.models.inventory import Stock
from app.models.purchasing import Supplier, SupplierSkuMap
from app.schemas.catalog import (
    BrandOut,
    CategoryOut,
    ProductCreate,
    ProductListResponse,
    ProductOut,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["catalog"])
brands_router = APIRouter(prefix="/brands", tags=["catalog"])
categories_router = APIRouter(prefix="/categories", tags=["catalog"])


async def _supplier_map(db: DBSession, product_ids: list) -> dict:
    """Devuelve {product_id: (supplier_id_str, supplier_name)} usando el ultimo
    proveedor asociado en purchasing.supplier_sku_map (por last_seen_at)."""
    if not product_ids:
        return {}
    rows = (
        await db.execute(
            select(
                SupplierSkuMap.product_id,
                SupplierSkuMap.supplier_id,
                Supplier.name,
                SupplierSkuMap.last_seen_at,
                SupplierSkuMap.created_at,
            )
            .join(Supplier, Supplier.id == SupplierSkuMap.supplier_id)
            .where(SupplierSkuMap.product_id.in_(product_ids))
            .where(Supplier.is_active == True)  # noqa: E712
        )
    ).all()
    from datetime import datetime, timezone

    _MIN = datetime.min.replace(tzinfo=timezone.utc)

    def _norm(dt):
        if dt is None:
            return _MIN
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

    best: dict = {}
    for pid, sid, sname, last_seen, created in rows:
        key = _norm(last_seen or created)
        cur = best.get(pid)
        if cur is None or key >= cur[0]:
            best[pid] = (key, sid, sname)
    return {pid: (str(v[1]), v[2]) for pid, v in best.items()}


async def _upsert_product_supplier(db: DBSession, product: Product, supplier_id) -> None:
    """Asocia (o reasocia) un producto a un proveedor manualmente.

    Crea/actualiza una fila en supplier_sku_map usando el SKU interno como
    sku_proveedor por defecto, para que la derivacion de proveedor lo detecte.
    """
    from datetime import UTC, datetime

    if supplier_id is None:
        return
    sup = (await db.execute(select(Supplier).where(Supplier.id == supplier_id))).scalar_one_or_none()
    if sup is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    existing = (
        await db.execute(
            select(SupplierSkuMap)
            .where(SupplierSkuMap.supplier_id == supplier_id)
            .where(SupplierSkuMap.product_id == product.id)
        )
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if existing is not None:
        existing.last_seen_at = now
    else:
        db.add(
            SupplierSkuMap(
                supplier_id=supplier_id,
                sku_proveedor=product.sku,
                product_id=product.id,
                factor_pack=1,
                last_unit_cost=product.cost,
                last_seen_at=now,
            )
        )


# ----------------------------- Products -------------------------------------
@router.get("", response_model=ProductListResponse)
async def list_products(
    db: DBSession,
    q: str | None = Query(None, description="Búsqueda por nombre/sku"),
    brand_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    category_slug: str | None = Query(None, description="Filtrar por slug de categoría (resuelve UUID internamente)"),
    species: str | None = Query(None, description="Filtrar por especie: perro, gato (incluye mixto automáticamente)"),
    supplier_id: uuid.UUID | None = Query(None, description="Filtrar por proveedor asociado"),
    without_supplier: bool = Query(False, description="Solo productos sin proveedor"),
    is_published: bool | None = None,
    is_featured: bool | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
):
    stmt = select(Product).where(Product.deleted_at.is_(None))
    count_stmt = select(func.count(Product.id)).where(Product.deleted_at.is_(None))

    if q:
        # Multi-token AND: each word must appear in name or sku (order-independent)
        from sqlalchemy import and_
        tokens = q.split()
        for token in tokens:
            like = f"%{token}%"
            cond = or_(Product.name.ilike(like), Product.sku.ilike(like))
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
    if brand_id:
        stmt = stmt.where(Product.brand_id == brand_id)
        count_stmt = count_stmt.where(Product.brand_id == brand_id)
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
        count_stmt = count_stmt.where(Product.category_id == category_id)
    if category_slug:
        cat = (await db.execute(
            select(Category)
            .where(func.lower(Category.slug) == category_slug.lower())
            .where(Category.deleted_at.is_(None))
        )).scalar_one_or_none()
        if cat:
            stmt = stmt.where(Product.category_id == cat.id)
            count_stmt = count_stmt.where(Product.category_id == cat.id)
    if species:
        species_cond = or_(
            Product.attributes["species"].astext == species,
            Product.attributes["species"].astext == "mixto",
        )
        stmt = stmt.where(species_cond)
        count_stmt = count_stmt.where(species_cond)
    if is_published is not None:
        stmt = stmt.where(Product.is_published == is_published)
        count_stmt = count_stmt.where(Product.is_published == is_published)
    if is_featured is not None:
        stmt = stmt.where(Product.is_featured == is_featured)
        count_stmt = count_stmt.where(Product.is_featured == is_featured)

    # Filtros por proveedor (vía supplier_sku_map)
    if supplier_id is not None:
        sub = select(SupplierSkuMap.product_id).where(SupplierSkuMap.supplier_id == supplier_id)
        stmt = stmt.where(Product.id.in_(sub))
        count_stmt = count_stmt.where(Product.id.in_(sub))
    if without_supplier:
        sub_all = select(SupplierSkuMap.product_id).distinct()
        stmt = stmt.where(Product.id.notin_(sub_all))
        count_stmt = count_stmt.where(Product.id.notin_(sub_all))

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(Product.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(stmt)).scalars().all()

    # Fetch stock totals for all products in one query
    product_ids = [r.id for r in rows]
    stock_map: dict = {}
    if product_ids:
        stock_rows = (await db.execute(
            select(Stock.product_id, func.sum(Stock.quantity).label("qty"))
            .where(Stock.product_id.in_(product_ids))
            .group_by(Stock.product_id)
        )).all()
        stock_map = {r.product_id: int(r.qty or 0) for r in stock_rows}

    supplier_map = await _supplier_map(db, product_ids)

    items = []
    for r in rows:
        p_out = ProductOut.model_validate(r)
        p_out.stock_qty = stock_map.get(r.id, 0)
        p_out.in_stock = p_out.stock_qty > 0
        sup = supplier_map.get(r.id)
        if sup:
            p_out.supplier_id = sup[0]
            p_out.supplier_name = sup[1]
        items.append(p_out)

    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, math.ceil(total / per_page)),
    )


# ----------------------------- Advanced catalog with facets -----------------
@router.get("/catalog")
async def catalog_products(
    db: DBSession,
    category_slug: str | None = None,
    life_stage: str | None = None,
    size_range: str | None = None,
    health_concerns: str | None = None,
    brand: str | None = None,
    pet_type: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    in_stock: bool | None = None,
    sort: str = Query("relevance", pattern="^(relevance|price_asc|price_desc|name|newest)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(40, ge=1, le=100),
):
    """Advanced catalog endpoint with facet filtering and counts."""
    from sqlalchemy import cast, String, text as sql_text

    stmt = select(Product).where(
        Product.is_published == True,  # noqa: E712
        Product.deleted_at.is_(None),
    )

    if category_slug:
        cat = (await db.execute(
            select(Category).where(func.lower(Category.slug) == category_slug.lower())
        )).scalar_one_or_none()
        if cat:
            stmt = stmt.where(Product.category_id == cat.id)

    if life_stage:
        stages = [s.strip() for s in life_stage.split(",")]
        stmt = stmt.where(or_(
            Product.life_stage.in_(stages),
            Product.life_stage == "all",
        ))

    if size_range:
        sizes = [s.strip() for s in size_range.split(",")]
        stmt = stmt.where(or_(
            Product.size_range.in_(sizes),
            Product.size_range == "all",
        ))

    if brand:
        brands_list = [b.strip() for b in brand.split(",")]
        stmt = stmt.where(Product.brand_normalized.in_(brands_list))

    if pet_type:
        stmt = stmt.where(or_(
            Product.pet_type == pet_type,
            Product.pet_type == "both",
        ))

    if price_min is not None:
        stmt = stmt.where(Product.price >= price_min)
    if price_max is not None:
        stmt = stmt.where(Product.price <= price_max)

    if health_concerns:
        concerns = [c.strip() for c in health_concerns.split(",")]
        stmt = stmt.where(
            sql_text("health_concerns && ARRAY[:concerns]::text[]").bindparams(
                concerns=concerns
            )
        )

    if sort == "price_asc":
        stmt = stmt.order_by(Product.price.asc())
    elif sort == "price_desc":
        stmt = stmt.order_by(Product.price.desc())
    elif sort == "name":
        stmt = stmt.order_by(Product.name.asc())
    else:
        stmt = stmt.order_by(Product.created_at.desc())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    product_ids = [r.id for r in rows]
    stock_map: dict = {}
    if product_ids:
        stock_rows = (await db.execute(
            select(Stock.product_id, func.sum(Stock.quantity).label("qty"))
            .where(Stock.product_id.in_(product_ids))
            .group_by(Stock.product_id)
        )).all()
        stock_map = {r.product_id: int(r.qty or 0) for r in stock_rows}

    items = []
    for r in rows:
        stock_qty = stock_map.get(r.id, 0)
        if in_stock and stock_qty == 0:
            continue
        p_out = ProductOut.model_validate(r)
        p_out.stock_qty = stock_qty
        p_out.in_stock = stock_qty > 0
        items.append(p_out)

    facets: dict = {}
    try:
        facet_stmt = select(Product).where(
            Product.is_published == True,  # noqa: E712
            Product.deleted_at.is_(None),
        )
        facet_rows = (await db.execute(facet_stmt)).scalars().all()

        life_stages: dict = {}
        size_ranges: dict = {}
        brands_count: dict = {}
        pet_types: dict = {}

        for p in facet_rows:
            if p.life_stage and p.life_stage != "all":
                life_stages[p.life_stage] = life_stages.get(p.life_stage, 0) + 1
            if p.size_range and p.size_range != "all":
                size_ranges[p.size_range] = size_ranges.get(p.size_range, 0) + 1
            if p.brand_normalized:
                brands_count[p.brand_normalized] = brands_count.get(p.brand_normalized, 0) + 1
            if p.pet_type and p.pet_type != "both":
                pet_types[p.pet_type] = pet_types.get(p.pet_type, 0) + 1

        facets = {
            "life_stages": life_stages,
            "size_ranges": size_ranges,
            "brands": dict(sorted(brands_count.items(), key=lambda x: -x[1])[:20]),
            "pet_types": pet_types,
        }
    except Exception:
        facets = {}

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "facets": facets,
    }


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: uuid.UUID, db: DBSession):
    p = (await db.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
    if p is None or p.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    p_out = ProductOut.model_validate(p)
    stock_rows = (await db.execute(
        select(func.sum(Stock.quantity)).where(Stock.product_id == p.id)
    )).scalar_one()
    p_out.stock_qty = int(stock_rows or 0)
    p_out.in_stock = p_out.stock_qty > 0
    supplier_map = await _supplier_map(db, [p.id])
    sup = supplier_map.get(p.id)
    if sup:
        p_out.supplier_id = sup[0]
        p_out.supplier_name = sup[1]
    return p_out


@router.get("/by-slug/{slug}", response_model=ProductOut)
async def get_product_by_slug(slug: str, db: DBSession):
    p = (
        await db.execute(select(Product).where(Product.slug == slug))
    ).scalar_one_or_none()
    if p is None or p.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    p_out = ProductOut.model_validate(p)
    stock_total = (await db.execute(
        select(func.sum(Stock.quantity)).where(Stock.product_id == p.id)
    )).scalar_one()
    p_out.stock_qty = int(stock_total or 0)
    p_out.in_stock = p_out.stock_qty > 0
    return p_out


@router.get("/{product_id}/related", response_model=list[ProductOut])
async def related_products(
    product_id: uuid.UUID,
    db: DBSession,
    limit: int = Query(4, ge=1, le=12),
):
    """Productos relacionados (misma categoría, sin el propio producto)."""
    product = (await db.execute(
        select(Product).where(Product.id == product_id).where(Product.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    stmt = (
        select(Product)
        .where(Product.deleted_at.is_(None))
        .where(Product.is_published == True)  # noqa: E712
        .where(Product.id != product_id)
    )
    if product.category_id:
        stmt = stmt.where(Product.category_id == product.category_id)
    stmt = stmt.order_by(Product.is_featured.desc(), Product.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    product_ids = [r.id for r in rows]
    stock_map: dict = {}
    if product_ids:
        stock_rows = (await db.execute(
            select(Stock.product_id, func.sum(Stock.quantity).label("qty"))
            .where(Stock.product_id.in_(product_ids))
            .group_by(Stock.product_id)
        )).all()
        stock_map = {r.product_id: int(r.qty or 0) for r in stock_rows}

    items = []
    for r in rows:
        p_out = ProductOut.model_validate(r)
        p_out.stock_qty = stock_map.get(r.id, 0)
        p_out.in_stock = p_out.stock_qty > 0
        items.append(p_out)
    return items


@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("catalog:write"))],
)
async def create_product(payload: ProductCreate, db: DBSession):
    data = payload.model_dump()
    supplier_id = data.pop("supplier_id", None)
    slug = slugify(payload.name)
    p = Product(slug=slug, **data)
    db.add(p)
    await db.flush()
    if supplier_id is not None:
        await _upsert_product_supplier(db, p, supplier_id)
    await db.commit()
    await db.refresh(p)
    out = ProductOut.model_validate(p)
    if supplier_id is not None:
        sup = (await _supplier_map(db, [p.id])).get(p.id)
        if sup:
            out.supplier_id = sup[0]
            out.supplier_name = sup[1]
    return out


@router.patch(
    "/{product_id}",
    response_model=ProductOut,
    dependencies=[Depends(require_permission("catalog:write"))],
)
async def update_product(product_id: uuid.UUID, payload: ProductUpdate, db: DBSession):
    p = (await db.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    data = payload.model_dump(exclude_unset=True)
    supplier_id = data.pop("supplier_id", None)
    for k, v in data.items():
        setattr(p, k, v)
    if supplier_id is not None:
        await _upsert_product_supplier(db, p, supplier_id)
    await db.commit()
    await db.refresh(p)
    out = ProductOut.model_validate(p)
    sup = (await _supplier_map(db, [p.id])).get(p.id)
    if sup:
        out.supplier_id = sup[0]
        out.supplier_name = sup[1]
    return out


# ----------------------------- Brands ---------------------------------------
@brands_router.get("", response_model=list[BrandOut])
async def list_brands(db: DBSession):
    rows = (
        await db.execute(select(Brand).where(Brand.deleted_at.is_(None)).order_by(Brand.name))
    ).scalars().all()
    return rows


# ----------------------------- Categories -----------------------------------
@categories_router.get("", response_model=list[CategoryOut])
async def list_categories(db: DBSession):
    rows = (
        await db.execute(
            select(Category)
            .where(Category.deleted_at.is_(None))
            .order_by(Category.sort_order, Category.name)
        )
    ).scalars().all()
    return rows
