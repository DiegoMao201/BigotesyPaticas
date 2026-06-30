"""Endpoints CRUD reales de proveedores (purchasing.suppliers)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.deps import CurrentUser, DBSession, require_permission
from app.models.catalog import Product
from app.models.inventory import Stock, StockMovement
from app.models.purchasing import Supplier, SupplierSkuMap

# Router montado en /v1/suppliers (reemplaza el legacy de finance.py).
# Para conservar el legacy: se monta finance.suppliers_router en /v1/suppliers-legacy.
router = APIRouter(prefix="/suppliers", tags=["suppliers"])


# ─── Schemas ────────────────────────────────────────────────────────


class SupplierIn(BaseModel):
    nit: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    contact_name: str | None = None
    payment_terms_days: int = 0
    notes: str | None = None
    is_active: bool = True


class SupplierUpdate(BaseModel):
    nit: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    contact_name: str | None = None
    payment_terms_days: int | None = None
    notes: str | None = None
    is_active: bool | None = None


class SupplierOut(BaseModel):
    id: uuid.UUID
    nit: str
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    contact_name: str | None = None
    payment_terms_days: int
    notes: str | None = None
    is_active: bool
    created_at: datetime
    sku_count: int = 0

    class Config:
        from_attributes = True


# ─── Endpoints ──────────────────────────────────────────────────────


@router.get("")
async def list_suppliers(
    db: DBSession,
    user: CurrentUser,
    q: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    stmt = select(Supplier).order_by(Supplier.name)
    cstmt = select(func.count()).select_from(Supplier)

    if q:
        pat = f"%{q}%"
        cond = or_(Supplier.name.ilike(pat), Supplier.nit.ilike(pat), Supplier.email.ilike(pat))
        stmt = stmt.where(cond)
        cstmt = cstmt.where(cond)
    if is_active is not None:
        stmt = stmt.where(Supplier.is_active == is_active)
        cstmt = cstmt.where(Supplier.is_active == is_active)

    total = (await db.execute(cstmt)).scalar_one()
    offset = (page - 1) * page_size
    rows = (await db.execute(stmt.offset(offset).limit(page_size))).scalars().all()

    # Conteo de SKUs por supplier
    sku_counts = dict(
        (
            await db.execute(
                select(SupplierSkuMap.supplier_id, func.count())
                .where(SupplierSkuMap.supplier_id.in_([r.id for r in rows] or [uuid.uuid4()]))
                .group_by(SupplierSkuMap.supplier_id)
            )
        ).all()
    )

    items = []
    for r in rows:
        d = SupplierOut.model_validate(r).model_dump()
        d["sku_count"] = sku_counts.get(r.id, 0)
        d["id"] = str(r.id)
        items.append(d)

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{supplier_id}", response_model=SupplierOut)
async def get_supplier(supplier_id: uuid.UUID, db: DBSession, user: CurrentUser) -> SupplierOut:
    s = (await db.execute(select(Supplier).where(Supplier.id == supplier_id))).scalar_one_or_none()
    if s is None:
        raise HTTPException(404, "Proveedor no encontrado")
    cnt = (
        await db.execute(
            select(func.count())
            .select_from(SupplierSkuMap)
            .where(SupplierSkuMap.supplier_id == supplier_id)
        )
    ).scalar_one()
    out = SupplierOut.model_validate(s)
    out.sku_count = cnt
    return out


@router.post(
    "", response_model=SupplierOut, dependencies=[Depends(require_permission("purchasing:write"))]
)
async def create_supplier(payload: SupplierIn, db: DBSession, user: CurrentUser) -> SupplierOut:
    # Validación NIT único (case-insensitive trim)
    nit = payload.nit.strip()
    existing = (await db.execute(select(Supplier).where(Supplier.nit == nit))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(409, f"Ya existe un proveedor con NIT {nit}: {existing.name}")
    s = Supplier(
        nit=nit,
        name=payload.name.strip(),
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        contact_name=payload.contact_name,
        payment_terms_days=payload.payment_terms_days,
        notes=payload.notes,
        is_active=payload.is_active,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    out = SupplierOut.model_validate(s)
    out.sku_count = 0
    return out


@router.patch(
    "/{supplier_id}",
    response_model=SupplierOut,
    dependencies=[Depends(require_permission("purchasing:write"))],
)
async def update_supplier(
    supplier_id: uuid.UUID, payload: SupplierUpdate, db: DBSession, user: CurrentUser
) -> SupplierOut:
    s = (await db.execute(select(Supplier).where(Supplier.id == supplier_id))).scalar_one_or_none()
    if s is None:
        raise HTTPException(404, "Proveedor no encontrado")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(s, k, v)
    s.updated_by = user.id
    await db.commit()
    await db.refresh(s)
    out = SupplierOut.model_validate(s)
    cnt = (
        await db.execute(
            select(func.count())
            .select_from(SupplierSkuMap)
            .where(SupplierSkuMap.supplier_id == supplier_id)
        )
    ).scalar_one()
    out.sku_count = cnt
    return out


@router.delete("/{supplier_id}", dependencies=[Depends(require_permission("purchasing:write"))])
async def delete_supplier(supplier_id: uuid.UUID, db: DBSession, user: CurrentUser):
    s = (await db.execute(select(Supplier).where(Supplier.id == supplier_id))).scalar_one_or_none()
    if s is None:
        raise HTTPException(404, "Proveedor no encontrado")
    # Soft delete via is_active (preserva integridad de compras)
    s.is_active = False
    s.updated_by = user.id
    await db.commit()
    return {"ok": True, "soft_deleted": True}


# ─── SKU map (memoria proveedor → producto interno) ─────────────────


class SkuMapOut(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    sku_proveedor: str
    product_id: uuid.UUID
    factor_pack: int
    last_unit_cost: float | None = None
    last_tax_pct: float | None = None
    last_seen_at: datetime | None = None

    class Config:
        from_attributes = True


@router.get("/{supplier_id}/skus")
async def list_supplier_skus(
    supplier_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
    velocity_days: int = Query(30, ge=7, le=120),
):
    rows = (
        await db.execute(
            select(SupplierSkuMap, Product)
            .join(Product, Product.id == SupplierSkuMap.product_id)
            .where(SupplierSkuMap.supplier_id == supplier_id)
            .order_by(Product.name)
        )
    ).all()

    if not rows:
        return {
            "items": [],
            "summary": {
                "associated_products": 0,
                "urgent_8d": 0,
                "to_replenish_15d": 0,
                "monitor_20d": 0,
                "recommended_units_8d": 0,
                "recommended_units_15d": 0,
                "recommended_units_20d": 0,
            },
        }

    product_ids = [prod.id for _, prod in rows]

    stock_rows = (
        await db.execute(
            select(
                Stock.product_id,
                func.coalesce(func.sum(Stock.quantity - Stock.reserved), 0),
            )
            .where(Stock.product_id.in_(product_ids))
            .group_by(Stock.product_id)
        )
    ).all()
    stock_by_product = {pid: int(qty or 0) for pid, qty in stock_rows}

    cutoff = datetime.now(UTC) - timedelta(days=velocity_days)
    sales_rows = (
        await db.execute(
            select(
                StockMovement.product_id,
                func.coalesce(func.sum(func.abs(StockMovement.quantity_delta)), 0),
            )
            .where(
                StockMovement.product_id.in_(product_ids),
                StockMovement.movement_type == "SALE",
                StockMovement.occurred_at >= cutoff,
            )
            .group_by(StockMovement.product_id)
        )
    ).all()
    sold_by_product = {pid: float(units or 0) for pid, units in sales_rows}

    items: list[dict] = []
    summary = {
        "associated_products": len(rows),
        "urgent_8d": 0,
        "to_replenish_15d": 0,
        "monitor_20d": 0,
        "recommended_units_8d": 0,
        "recommended_units_15d": 0,
        "recommended_units_20d": 0,
    }

    for sku_map, product in rows:
        available = stock_by_product.get(product.id, 0)
        sold_units = sold_by_product.get(product.id, 0.0)
        avg_daily = sold_units / float(velocity_days)
        days_cover = (available / avg_daily) if avg_daily > 0 else None

        reorder_8d = max(0, ceil(avg_daily * 8 - available))
        reorder_15d = max(0, ceil(avg_daily * 15 - available))
        reorder_20d = max(0, ceil(avg_daily * 20 - available))

        if available <= 0:
            urgency = "AGOTADO"
        elif reorder_8d > 0:
            urgency = "URGENTE_8D"
        elif reorder_15d > 0:
            urgency = "REPOSICION_15D"
        elif reorder_20d > 0:
            urgency = "MONITOREAR_20D"
        else:
            urgency = "OK"

        if urgency in ("AGOTADO", "URGENTE_8D"):
            summary["urgent_8d"] += 1
        elif urgency == "REPOSICION_15D":
            summary["to_replenish_15d"] += 1
        elif urgency == "MONITOREAR_20D":
            summary["monitor_20d"] += 1

        summary["recommended_units_8d"] += reorder_8d
        summary["recommended_units_15d"] += reorder_15d
        summary["recommended_units_20d"] += reorder_20d

        items.append(
            {
                "id": str(sku_map.id),
                "sku_proveedor": sku_map.sku_proveedor,
                "product_id": str(product.id),
                "product_sku": product.sku,
                "product_name": product.name,
                "factor_pack": sku_map.factor_pack,
                "last_unit_cost": float(sku_map.last_unit_cost)
                if sku_map.last_unit_cost is not None
                else None,
                "last_tax_pct": float(sku_map.last_tax_pct)
                if sku_map.last_tax_pct is not None
                else None,
                "last_seen_at": sku_map.last_seen_at.isoformat() if sku_map.last_seen_at else None,
                "stock_available": available,
                "avg_daily_sales": round(avg_daily, 3),
                "days_cover": round(days_cover, 1) if days_cover is not None else None,
                "reorder_qty_8d": reorder_8d,
                "reorder_qty_15d": reorder_15d,
                "reorder_qty_20d": reorder_20d,
                "urgency": urgency,
            }
        )

    return {"items": items, "summary": summary}
