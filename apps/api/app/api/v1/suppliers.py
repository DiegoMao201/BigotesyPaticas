"""Endpoints CRUD reales de proveedores (purchasing.suppliers)."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.deps import CurrentUser, DBSession, require_permission
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
        (await db.execute(
            select(SupplierSkuMap.supplier_id, func.count())
            .where(SupplierSkuMap.supplier_id.in_([r.id for r in rows] or [uuid.uuid4()]))
            .group_by(SupplierSkuMap.supplier_id)
        )).all()
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
    cnt = (await db.execute(
        select(func.count()).select_from(SupplierSkuMap).where(SupplierSkuMap.supplier_id == supplier_id)
    )).scalar_one()
    out = SupplierOut.model_validate(s)
    out.sku_count = cnt
    return out


@router.post("", response_model=SupplierOut, dependencies=[Depends(require_permission("purchasing:write"))])
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


@router.patch("/{supplier_id}", response_model=SupplierOut, dependencies=[Depends(require_permission("purchasing:write"))])
async def update_supplier(supplier_id: uuid.UUID, payload: SupplierUpdate, db: DBSession, user: CurrentUser) -> SupplierOut:
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
    cnt = (await db.execute(
        select(func.count()).select_from(SupplierSkuMap).where(SupplierSkuMap.supplier_id == supplier_id)
    )).scalar_one()
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
async def list_supplier_skus(supplier_id: uuid.UUID, db: DBSession, user: CurrentUser):
    rows = (await db.execute(
        select(SupplierSkuMap).where(SupplierSkuMap.supplier_id == supplier_id)
    )).scalars().all()
    return [
        {
            "id": str(r.id),
            "sku_proveedor": r.sku_proveedor,
            "product_id": str(r.product_id),
            "factor_pack": r.factor_pack,
            "last_unit_cost": float(r.last_unit_cost) if r.last_unit_cost is not None else None,
            "last_tax_pct": float(r.last_tax_pct) if r.last_tax_pct is not None else None,
            "last_seen_at": r.last_seen_at.isoformat() if r.last_seen_at else None,
        } for r in rows
    ]
