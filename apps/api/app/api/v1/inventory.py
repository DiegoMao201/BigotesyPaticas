"""Endpoints de inventario: stock por SKU/producto, ajustes."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.deps import CurrentUser, DBSession, require_permission
from app.models.catalog import Product
from app.models.inventory import Stock, StockLocation, StockMovement

router = APIRouter(prefix="/inventory", tags=["inventory"])


class StockOut(BaseModel):
    product_id: uuid.UUID
    location_id: uuid.UUID
    quantity: int
    reserved: int
    available: int


class AdjustmentIn(BaseModel):
    product_id: uuid.UUID
    location_id: uuid.UUID | None = None
    quantity_delta: int = Field(description="Positivo o negativo")
    notes: str | None = None


@router.get("/stock/{product_id}", response_model=list[StockOut])
async def get_stock(product_id: uuid.UUID, db: DBSession):
    rows = (
        await db.execute(select(Stock).where(Stock.product_id == product_id))
    ).scalars().all()
    return [
        StockOut(
            product_id=s.product_id,
            location_id=s.location_id,
            quantity=s.quantity,
            reserved=s.reserved,
            available=max(0, s.quantity - s.reserved),
        )
        for s in rows
    ]


@router.post(
    "/adjust",
    response_model=StockOut,
    dependencies=[Depends(require_permission("inventory:adjust"))],
)
async def adjust_stock(payload: AdjustmentIn, db: DBSession, user: CurrentUser):
    # Resolver location default si no se da
    location_id = payload.location_id
    if location_id is None:
        loc = (
            await db.execute(
                select(StockLocation).where(StockLocation.is_default == 1).limit(1)
            )
        ).scalar_one_or_none()
        if loc is None:
            raise HTTPException(
                status_code=400, detail="No hay location default configurada"
            )
        location_id = loc.id

    # Lock pesimista sobre la fila de stock
    stock = (
        await db.execute(
            select(Stock)
            .where(Stock.product_id == payload.product_id)
            .where(Stock.location_id == location_id)
            .with_for_update()
        )
    ).scalar_one_or_none()

    if stock is None:
        if payload.quantity_delta < 0:
            raise HTTPException(status_code=400, detail="Sin stock para descontar")
        stock = Stock(
            product_id=payload.product_id,
            location_id=location_id,
            quantity=0,
        )
        db.add(stock)

    new_qty = stock.quantity + payload.quantity_delta
    if new_qty < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stock insuficiente: actual={stock.quantity}, delta={payload.quantity_delta}",
        )
    stock.quantity = new_qty

    movement = StockMovement(
        product_id=payload.product_id,
        location_id=location_id,
        movement_type="ADJUSTMENT",
        quantity_delta=payload.quantity_delta,
        quantity_after=new_qty,
        notes=payload.notes,
        occurred_at=datetime.now(UTC),
        created_by=user.email,
    )
    db.add(movement)
    await db.commit()
    await db.refresh(stock)

    return StockOut(
        product_id=stock.product_id,
        location_id=stock.location_id,
        quantity=stock.quantity,
        reserved=stock.reserved,
        available=max(0, stock.quantity - stock.reserved),
    )


# ─────────────── List all stock with product info (for inventory page) ────────────

class StockRowOut(BaseModel):
    product_id: uuid.UUID
    sku: str
    name: str
    category_name: str | None = None
    quantity: int
    reserved: int
    available: int
    cost: float
    price: float
    margin_pct: float
    stock_value_cost: float
    stock_value_price: float


class StockListResponse(BaseModel):
    items: list[StockRowOut]
    total: int
    page: int
    page_size: int
    total_value_cost: float
    total_value_price: float
    out_of_stock: int
    low_stock: int


@router.get("/stock", response_model=StockListResponse)
async def list_stock(
    db: DBSession,
    user: CurrentUser,
    q: str | None = Query(None),
    only_in_stock: bool = False,
    only_low_stock: bool = False,
    sort_by: str = Query("quantity", pattern="^(quantity|cost|price|stock_value_cost|stock_value_price|margin_pct|name|sku)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    # Sum stock per product
    stock_sub = (
        select(
            Stock.product_id.label("product_id"),
            func.coalesce(func.sum(Stock.quantity), 0).label("qty"),
            func.coalesce(func.sum(Stock.reserved), 0).label("reserved"),
        )
        .group_by(Stock.product_id)
        .subquery()
    )

    stmt = (
        select(Product, stock_sub.c.qty, stock_sub.c.reserved)
        .outerjoin(stock_sub, stock_sub.c.product_id == Product.id)
        .where(Product.deleted_at.is_(None))
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))

    rows = (await db.execute(stmt)).all()
    items = []
    total_value_cost = 0.0
    total_value_price = 0.0
    out_of_stock = 0
    low_stock = 0
    for p, qty, reserved in rows:
        q_int = int(qty or 0)
        r_int = int(reserved or 0)
        avail = max(0, q_int - r_int)
        cost = float(p.cost or 0)
        price = float(p.price or 0)
        if only_in_stock and q_int <= 0:
            continue
        if only_low_stock and q_int > 5:
            continue
        if q_int <= 0:
            out_of_stock += 1
        elif q_int < 5:
            low_stock += 1
        sv_cost = q_int * cost
        sv_price = q_int * price
        margin = round((price - cost) / price * 100, 1) if price > 0 else 0.0
        total_value_cost += sv_cost
        total_value_price += sv_price
        items.append(StockRowOut(
            product_id=p.id,
            sku=p.sku,
            name=p.name,
            category_name=None,
            quantity=q_int,
            reserved=r_int,
            available=avail,
            cost=cost,
            price=price,
            margin_pct=margin,
            stock_value_cost=sv_cost,
            stock_value_price=sv_price,
        ))

    # Sort
    reverse = (sort_dir == "desc")
    sort_key_map = {
        "quantity": lambda x: x.quantity,
        "cost": lambda x: x.cost,
        "price": lambda x: x.price,
        "stock_value_cost": lambda x: x.stock_value_cost,
        "stock_value_price": lambda x: x.stock_value_price,
        "margin_pct": lambda x: x.margin_pct,
        "name": lambda x: x.name.lower(),
        "sku": lambda x: x.sku.lower(),
    }
    items.sort(key=sort_key_map.get(sort_by, lambda x: -x.quantity), reverse=reverse)
    total = len(items)
    start_idx = (page - 1) * page_size
    return StockListResponse(
        items=items[start_idx:start_idx + page_size],
        total=total,
        page=page,
        page_size=page_size,
        total_value_cost=total_value_cost,
        total_value_price=total_value_price,
        out_of_stock=out_of_stock,
        low_stock=low_stock,
    )


# ─────────────── List stock movements ────────────────────

class MovementOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str | None = None
    product_sku: str | None = None
    movement_type: str
    quantity_delta: int
    quantity_after: int
    unit_cost: float | None = None
    reference_type: str | None = None
    reference_id: str | None = None
    notes: str | None = None
    occurred_at: datetime
    created_by: str | None = None


@router.get("/movements", response_model=dict)
async def list_movements(
    db: DBSession,
    user: CurrentUser,
    product_id: uuid.UUID | None = None,
    movement_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    stmt = select(StockMovement, Product.name, Product.sku).join(
        Product, Product.id == StockMovement.product_id
    )
    if product_id:
        stmt = stmt.where(StockMovement.product_id == product_id)
    if movement_type:
        stmt = stmt.where(StockMovement.movement_type == movement_type)
    stmt = stmt.order_by(StockMovement.occurred_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).all()
    items = [
        MovementOut(
            id=m.id,
            product_id=m.product_id,
            product_name=name,
            product_sku=sku,
            movement_type=m.movement_type,
            quantity_delta=m.quantity_delta,
            quantity_after=m.quantity_after,
            unit_cost=float(m.unit_cost) if m.unit_cost is not None else None,
            reference_type=m.reference_type,
            reference_id=str(m.reference_id) if m.reference_id else None,
            notes=m.notes,
            occurred_at=m.occurred_at,
            created_by=m.created_by,
        )
        for m, name, sku in rows
    ]
    return {"items": items, "total": len(items)}


# ─────────────── Update product pricing (cost + price) ────────────

class PricingUpdateIn(BaseModel):
    cost: float | None = Field(None, ge=0, description="Costo unitario (precio de compra)")
    price: float | None = Field(None, ge=0, description="Precio de venta público")


class PricingUpdateOut(BaseModel):
    product_id: uuid.UUID
    sku: str
    name: str
    cost: float
    price: float
    margin_pct: float


@router.patch(
    "/stock/{product_id}/pricing",
    response_model=PricingUpdateOut,
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def update_product_pricing(
    product_id: uuid.UUID,
    payload: PricingUpdateIn,
    db: DBSession,
    user: CurrentUser,
):
    """Actualiza costo y/o precio de venta de un producto."""
    product = (
        await db.execute(
            select(Product).where(Product.id == product_id).where(Product.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if payload.cost is not None:
        from decimal import Decimal
        product.cost = Decimal(str(payload.cost))
    if payload.price is not None:
        from decimal import Decimal
        product.price = Decimal(str(payload.price))

    await db.commit()
    await db.refresh(product)

    cost = float(product.cost or 0)
    price = float(product.price or 0)
    margin = round((price - cost) / price * 100, 1) if price > 0 else 0.0

    return PricingUpdateOut(
        product_id=product.id,
        sku=product.sku,
        name=product.name,
        cost=cost,
        price=price,
        margin_pct=margin,
    )
