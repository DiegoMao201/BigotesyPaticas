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


# ----------------------------- Products -------------------------------------
@router.get("", response_model=ProductListResponse)
async def list_products(
    db: DBSession,
    q: str | None = Query(None, description="Búsqueda por nombre/sku"),
    brand_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
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
    if is_published is not None:
        stmt = stmt.where(Product.is_published == is_published)
        count_stmt = count_stmt.where(Product.is_published == is_published)
    if is_featured is not None:
        stmt = stmt.where(Product.is_featured == is_featured)
        count_stmt = count_stmt.where(Product.is_featured == is_featured)

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

    items = []
    for r in rows:
        p_out = ProductOut.model_validate(r)
        p_out.stock_qty = stock_map.get(r.id, 0)
        p_out.in_stock = p_out.stock_qty > 0
        items.append(p_out)

    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, math.ceil(total / per_page)),
    )


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


@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("catalog:write"))],
)
async def create_product(payload: ProductCreate, db: DBSession):
    slug = slugify(payload.name)
    p = Product(slug=slug, **payload.model_dump())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@router.patch(
    "/{product_id}",
    response_model=ProductOut,
    dependencies=[Depends(require_permission("catalog:write"))],
)
async def update_product(product_id: uuid.UUID, payload: ProductUpdate, db: DBSession):
    p = (await db.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    await db.commit()
    await db.refresh(p)
    return p


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
