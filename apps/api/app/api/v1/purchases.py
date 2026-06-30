"""Endpoints de compras a proveedores (Módulo Compras)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.deps import CurrentUser, DBSession, require_permission
from app.models.catalog import Product
from app.models.inventory import Stock, StockLocation, StockMovement
from app.models.purchasing import Purchase, PurchaseItem, SupplierSkuMap

router = APIRouter(prefix="/purchases", tags=["purchases"])


# ─── Schemas ──────────────────────────────────────────────────────


class PurchaseItemIn(BaseModel):
    product_id: uuid.UUID | None = None
    sku_proveedor: str | None = None
    sku_interno: str | None = None
    product_name: str
    quantity: int = Field(ge=1)
    factor_pack: int = Field(default=1, ge=1)
    unit_cost: float = Field(ge=0)
    tax_pct: float = Field(default=0, ge=0, le=100)


class PurchaseItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID | None
    sku_proveedor: str | None
    sku_interno: str | None
    product_name: str
    quantity: int
    factor_pack: int
    unit_cost: float
    tax_pct: float
    total_cost: float

    class Config:
        from_attributes = True


class PurchaseCreate(BaseModel):
    folio: str | None = None
    supplier_name: str
    supplier_id: uuid.UUID | None = None
    payment_method: str = "efectivo"
    payment_reference: str | None = None
    notes: str | None = None
    purchased_at: datetime | None = None
    items: list[PurchaseItemIn] = Field(min_length=1)
    # Si True, aplica los movimientos de stock y actualiza costos inmediatamente
    receive_now: bool = True


class PurchaseUpdate(BaseModel):
    folio: str | None = None
    supplier_name: str | None = None
    payment_method: str | None = None
    payment_reference: str | None = None
    notes: str | None = None
    purchased_at: datetime | None = None
    status: Literal["draft", "confirmed", "received", "cancelled"] | None = None


class PurchaseOut(BaseModel):
    id: uuid.UUID
    folio: str | None
    supplier_name: str
    supplier_id: uuid.UUID | None
    status: str
    subtotal: float
    tax_amount: float
    total: float
    payment_method: str
    payment_reference: str | None
    notes: str | None
    purchased_at: datetime
    created_at: datetime
    items: list[PurchaseItemOut]

    class Config:
        from_attributes = True


class PurchaseSummary(BaseModel):
    id: uuid.UUID
    folio: str | None
    supplier_name: str
    status: str
    total: float
    items_count: int
    payment_method: str
    purchased_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class PurchaseListResponse(BaseModel):
    items: list[PurchaseSummary]
    total: int
    page: int
    page_size: int
    total_spend: float


# ─── Helpers ──────────────────────────────────────────────────────


def _calc_item_total(item: PurchaseItemIn) -> float:
    return round(item.unit_cost * item.quantity * (1 + item.tax_pct / 100), 2)


async def _apply_stock_and_cost(
    db,
    purchase: Purchase,
    items: list[PurchaseItem],
    user_email: str,
) -> None:
    """Crea movimientos de stock tipo PURCHASE y actualiza costo del producto."""
    # Resolver location default
    loc = (
        await db.execute(select(StockLocation).where(StockLocation.is_default == 1).limit(1))
    ).scalar_one_or_none()
    if loc is None:
        # Crear location default si no existe
        loc = StockLocation(code="PRINCIPAL", name="Bodega Principal", is_default=1)
        db.add(loc)
        await db.flush()

    for item in items:
        if item.product_id is None:
            continue  # No mapear productos sin ID

        # Actualizar costo del producto si el nuevo costo es > 0
        if item.unit_cost > 0:
            product = (
                await db.execute(select(Product).where(Product.id == item.product_id))
            ).scalar_one_or_none()
            if product:
                product.cost = Decimal(str(item.unit_cost))

        # Unidades reales = quantity x factor_pack
        units = item.quantity * item.factor_pack

        stock = (
            await db.execute(
                select(Stock)
                .where(Stock.product_id == item.product_id)
                .where(Stock.location_id == loc.id)
                .with_for_update()
            )
        ).scalar_one_or_none()

        if stock is None:
            stock = Stock(
                product_id=item.product_id,
                location_id=loc.id,
                quantity=0,
                reserved=0,
            )
            db.add(stock)
            await db.flush()

        new_qty = stock.quantity + units
        stock.quantity = new_qty

        movement = StockMovement(
            product_id=item.product_id,
            location_id=loc.id,
            movement_type="PURCHASE",
            quantity_delta=units,
            quantity_after=new_qty,
            unit_cost=item.unit_cost,
            reference_type="purchase",
            reference_id=purchase.id,
            notes=f"Compra #{purchase.folio or str(purchase.id)[:8]} — {item.product_name}",
            occurred_at=purchase.purchased_at,
            created_by=user_email,
        )
        db.add(movement)


async def _upsert_supplier_sku_map(
    db,
    purchase: Purchase,
    items: list[PurchaseItem],
) -> None:
    """Actualiza memoria SKU proveedor -> producto interno para auto-match futuro."""
    if purchase.supplier_id is None:
        return

    for item in items:
        sku_prov = (item.sku_proveedor or "").strip()
        if not sku_prov or item.product_id is None:
            continue

        existing = (
            await db.execute(
                select(SupplierSkuMap).where(
                    SupplierSkuMap.supplier_id == purchase.supplier_id,
                    SupplierSkuMap.sku_proveedor == sku_prov,
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            db.add(
                SupplierSkuMap(
                    supplier_id=purchase.supplier_id,
                    sku_proveedor=sku_prov,
                    product_id=item.product_id,
                    factor_pack=max(1, int(item.factor_pack or 1)),
                    last_unit_cost=float(item.unit_cost),
                    last_tax_pct=float(item.tax_pct),
                    last_seen_at=purchase.purchased_at,
                )
            )
        else:
            existing.product_id = item.product_id
            existing.factor_pack = max(1, int(item.factor_pack or 1))
            existing.last_unit_cost = float(item.unit_cost)
            existing.last_tax_pct = float(item.tax_pct)
            existing.last_seen_at = purchase.purchased_at


# ─── Endpoints ────────────────────────────────────────────────────


@router.get(
    "",
    response_model=PurchaseListResponse,
    dependencies=[Depends(require_permission("purchasing:read"))],
)
async def list_purchases(
    db: DBSession,
    q: str | None = Query(None, description="Buscar por folio o proveedor"),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    stmt = select(Purchase)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Purchase.folio.ilike(like),
                Purchase.supplier_name.ilike(like),
            )
        )
    if status:
        stmt = stmt.where(Purchase.status == status)

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(total_stmt)).scalar_one()

    total_spend_stmt = select(func.coalesce(func.sum(Purchase.total), 0)).select_from(
        stmt.subquery()
    )
    total_spend = float((await db.execute(total_spend_stmt)).scalar_one())

    stmt = stmt.order_by(Purchase.purchased_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    summaries = [
        PurchaseSummary(
            id=r.id,
            folio=r.folio,
            supplier_name=r.supplier_name,
            status=r.status,
            total=float(r.total),
            items_count=len(r.items),
            payment_method=r.payment_method,
            purchased_at=r.purchased_at,
            created_at=r.created_at,
        )
        for r in rows
    ]

    return PurchaseListResponse(
        items=summaries,
        total=total,
        page=page,
        page_size=page_size,
        total_spend=total_spend,
    )


@router.get(
    "/{purchase_id}",
    response_model=PurchaseOut,
    dependencies=[Depends(require_permission("purchasing:read"))],
)
async def get_purchase(purchase_id: uuid.UUID, db: DBSession):
    purchase = (
        await db.execute(select(Purchase).where(Purchase.id == purchase_id))
    ).scalar_one_or_none()
    if purchase is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return PurchaseOut(
        id=purchase.id,
        folio=purchase.folio,
        supplier_name=purchase.supplier_name,
        supplier_id=purchase.supplier_id,
        status=purchase.status,
        subtotal=float(purchase.subtotal),
        tax_amount=float(purchase.tax_amount),
        total=float(purchase.total),
        payment_method=purchase.payment_method,
        payment_reference=purchase.payment_reference,
        notes=purchase.notes,
        purchased_at=purchase.purchased_at,
        created_at=purchase.created_at,
        items=[
            PurchaseItemOut(
                id=it.id,
                product_id=it.product_id,
                sku_proveedor=it.sku_proveedor,
                sku_interno=it.sku_interno,
                product_name=it.product_name,
                quantity=it.quantity,
                factor_pack=it.factor_pack,
                unit_cost=float(it.unit_cost),
                tax_pct=float(it.tax_pct),
                total_cost=float(it.total_cost),
            )
            for it in purchase.items
        ],
    )


@router.post(
    "",
    response_model=PurchaseOut,
    status_code=201,
    dependencies=[Depends(require_permission("purchasing:write"))],
)
async def create_purchase(
    payload: PurchaseCreate,
    db: DBSession,
    user: CurrentUser,
):
    """Crea una compra y opcionalmente aplica los movimientos de stock (receive_now=True)."""
    now = datetime.now(UTC)
    purchased_at = payload.purchased_at or now

    # Calcular totales
    subtotal = 0.0
    tax_amount = 0.0
    items_db = []

    for item_in in payload.items:
        item_total = _calc_item_total(item_in)
        item_subtotal = round(item_in.unit_cost * item_in.quantity, 2)
        item_tax = round(item_total - item_subtotal, 2)
        subtotal += item_subtotal
        tax_amount += item_tax
        items_db.append(
            PurchaseItem(
                product_id=item_in.product_id,
                sku_proveedor=item_in.sku_proveedor,
                sku_interno=item_in.sku_interno,
                product_name=item_in.product_name,
                quantity=item_in.quantity,
                factor_pack=item_in.factor_pack,
                unit_cost=Decimal(str(item_in.unit_cost)),
                tax_pct=Decimal(str(item_in.tax_pct)),
                total_cost=Decimal(str(item_total)),
            )
        )

    total = round(subtotal + tax_amount, 2)
    status = "received" if payload.receive_now else "confirmed"

    purchase = Purchase(
        folio=payload.folio,
        supplier_name=payload.supplier_name,
        supplier_id=payload.supplier_id,
        status=status,
        subtotal=Decimal(str(subtotal)),
        tax_amount=Decimal(str(tax_amount)),
        total=Decimal(str(total)),
        payment_method=payload.payment_method,
        payment_reference=payload.payment_reference,
        notes=payload.notes,
        purchased_at=purchased_at,
        created_by=user.email,
        items=items_db,
    )
    db.add(purchase)
    await db.flush()  # get purchase.id

    if payload.receive_now:
        await _apply_stock_and_cost(db, purchase, items_db, user.email)

    await _upsert_supplier_sku_map(db, purchase, items_db)

    await db.commit()
    await db.refresh(purchase)

    return await get_purchase(purchase.id, db)


@router.patch(
    "/{purchase_id}",
    response_model=PurchaseOut,
    dependencies=[Depends(require_permission("purchasing:write"))],
)
async def update_purchase(
    purchase_id: uuid.UUID,
    payload: PurchaseUpdate,
    db: DBSession,
    user: CurrentUser,
):
    purchase = (
        await db.execute(select(Purchase).where(Purchase.id == purchase_id))
    ).scalar_one_or_none()
    if purchase is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")

    if payload.folio is not None:
        purchase.folio = payload.folio
    if payload.supplier_name is not None:
        purchase.supplier_name = payload.supplier_name
    if payload.payment_method is not None:
        purchase.payment_method = payload.payment_method
    if payload.payment_reference is not None:
        purchase.payment_reference = payload.payment_reference
    if payload.notes is not None:
        purchase.notes = payload.notes
    if payload.purchased_at is not None:
        purchase.purchased_at = payload.purchased_at
    if payload.status is not None:
        purchase.status = payload.status

    purchase.updated_by = user.email
    await db.commit()
    return await get_purchase(purchase_id, db)


@router.delete(
    "/{purchase_id}",
    status_code=204,
    dependencies=[Depends(require_permission("purchasing:write"))],
)
async def delete_purchase(purchase_id: uuid.UUID, db: DBSession):
    purchase = (
        await db.execute(select(Purchase).where(Purchase.id == purchase_id))
    ).scalar_one_or_none()
    if purchase is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    if purchase.status == "received":
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar una compra ya recibida en stock. Cancélala primero.",
        )
    await db.delete(purchase)
    await db.commit()


@router.post(
    "/{purchase_id}/receive",
    response_model=PurchaseOut,
    dependencies=[Depends(require_permission("purchasing:write"))],
)
async def receive_purchase(
    purchase_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
):
    """Marca la compra como recibida y aplica los movimientos de stock."""
    purchase = (
        await db.execute(select(Purchase).where(Purchase.id == purchase_id))
    ).scalar_one_or_none()
    if purchase is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    if purchase.status == "received":
        raise HTTPException(status_code=409, detail="Esta compra ya fue recibida")
    if purchase.status == "cancelled":
        raise HTTPException(status_code=409, detail="No se puede recibir una compra cancelada")

    purchase.status = "received"
    purchase.updated_by = user.email
    await _apply_stock_and_cost(db, purchase, list(purchase.items), user.email)
    await db.commit()
    return await get_purchase(purchase_id, db)


@router.get(
    "/stats/summary",
    dependencies=[Depends(require_permission("purchasing:read"))],
)
async def purchases_stats(db: DBSession):
    """Resumen estadístico de compras."""
    from datetime import timedelta

    now = datetime.now(UTC)
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_30 = now - timedelta(days=30)

    total_spend_month = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(Purchase.total), 0))
                .where(Purchase.purchased_at >= start_month)
                .where(Purchase.status != "cancelled")
            )
        ).scalar_one()
    )
    total_count_month = int(
        (
            await db.execute(
                select(func.count(Purchase.id))
                .where(Purchase.purchased_at >= start_month)
                .where(Purchase.status != "cancelled")
            )
        ).scalar_one()
    )
    # Top suppliers this month
    top_suppliers = (
        await db.execute(
            select(
                Purchase.supplier_name,
                func.sum(Purchase.total).label("total"),
                func.count(Purchase.id).label("count"),
            )
            .where(Purchase.purchased_at >= start_30)
            .where(Purchase.status != "cancelled")
            .group_by(Purchase.supplier_name)
            .order_by(func.sum(Purchase.total).desc())
            .limit(5)
        )
    ).all()

    return {
        "total_spend_month": total_spend_month,
        "total_count_month": total_count_month,
        "top_suppliers": [
            {"supplier_name": r.supplier_name, "total": float(r.total), "count": int(r.count)}
            for r in top_suppliers
        ],
    }
