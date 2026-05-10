"""Endpoints de inventario: stock por SKU/producto, ajustes."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

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
