"""Portal Orders — pedidos desde el portal de clientes (sin mostrar stock)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select

from app.api.v1.portal_auth import PortalUser
from app.api.v1.portal_loyalty import award_points
from app.deps import DBSession
from app.models.catalog import Product
from app.models.crm import Customer
from app.models.portal import PortalOrder

router = APIRouter(prefix="/portal/orders", tags=["portal"])


# ── schemas ───────────────────────────────────────────────────────────

class OrderIn(BaseModel):
    product_id: str
    pet_id: str | None = None
    quantity: int = 1
    notes: str | None = None


class OrderOut(BaseModel):
    id: str
    product_id: str | None
    product_name: str
    pet_id: str | None
    quantity: int
    unit_price: float | None
    status: str
    notes: str | None
    created_at: str
    points_earned: int | None = None


def _order_out(o: PortalOrder, points: int | None = None) -> OrderOut:
    return OrderOut(
        id=str(o.id),
        product_id=str(o.product_id) if o.product_id else None,
        product_name=o.product_name,
        pet_id=str(o.pet_id) if o.pet_id else None,
        quantity=o.quantity,
        unit_price=float(o.unit_price) if o.unit_price else None,
        status=o.status,
        notes=o.notes,
        created_at=o.created_at.isoformat(),
        points_earned=points,
    )


# ── endpoints ─────────────────────────────────────────────────────────

@router.get("", response_model=list[OrderOut])
async def list_orders(
    db: DBSession,
    customer: Customer = PortalUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> list[OrderOut]:
    rows = (
        await db.execute(
            select(PortalOrder)
            .where(PortalOrder.customer_id == customer.id)
            .order_by(PortalOrder.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return [_order_out(o) for o in rows]


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderIn,
    db: DBSession,
    customer: Customer = PortalUser,
) -> OrderOut:
    # Buscar producto — SOLO para capturar nombre y precio snapshot.
    # NUNCA validar stock; siempre se acepta el pedido.
    product = (
        await db.execute(
            select(Product).where(
                and_(
                    Product.id == uuid.UUID(payload.product_id),
                    Product.deleted_at == None,  # noqa: E711
                )
            )
        )
    ).scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    order = PortalOrder(
        customer_id=customer.id,
        pet_id=uuid.UUID(payload.pet_id) if payload.pet_id else None,
        product_id=product.id,
        product_name=product.name,
        quantity=max(1, payload.quantity),
        unit_price=float(product.price) if product.price else None,
        status="received",
        notes=payload.notes,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    # Puntos de fidelidad: 1 punto por cada $1.000
    points_earned = 0
    if order.unit_price:
        total = order.unit_price * order.quantity
        points_earned = int(total / 1_000)
        if points_earned > 0:
            await award_points(
                customer_id=customer.id,
                points=points_earned,
                reason="portal_order",
                reference_type="portal_order",
                reference_id=order.id,
                description=f"Pedido portal: {product.name} ×{order.quantity}",
                db=db,
            )

    return _order_out(order, points=points_earned if points_earned else None)


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: uuid.UUID,
    db: DBSession,
    customer: Customer = PortalUser,
) -> OrderOut:
    order = (
        await db.execute(
            select(PortalOrder).where(
                and_(
                    PortalOrder.id == order_id,
                    PortalOrder.customer_id == customer.id,
                )
            )
        )
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return _order_out(order)


# ── top products ────────────────────────────────────────────────────────

@router.get("/me/top-products")
async def top_products(
    db: DBSession,
    customer: Customer = PortalUser,
    limit: int = Query(5, ge=1, le=20),
) -> list[dict]:
    """Top productos del cliente (por frecuencia en pedidos portal).
    Fallback a los más pedidos en general si el cliente es nuevo."""

    # Productos más pedidos por este cliente en el portal
    personal = (
        await db.execute(
            select(
                PortalOrder.product_id,
                func.count().label("freq"),
            )
            .where(
                PortalOrder.customer_id == customer.id,
                PortalOrder.product_id.is_not(None),
            )
            .group_by(PortalOrder.product_id)
            .order_by(func.count().desc())
            .limit(limit)
        )
    ).all()

    product_ids = [r.product_id for r in personal]

    if len(product_ids) < limit:
        # Fallback: productos más pedidos en general (excluyendo los ya encontrados)
        popular = (
            await db.execute(
                select(
                    PortalOrder.product_id,
                    func.count().label("freq"),
                )
                .where(
                    PortalOrder.product_id.is_not(None),
                    PortalOrder.product_id.not_in(product_ids) if product_ids else True,
                )
                .group_by(PortalOrder.product_id)
                .order_by(func.count().desc())
                .limit(limit - len(product_ids))
            )
        ).all()
        product_ids += [r.product_id for r in popular]

    if not product_ids:
        return []

    products_rows = (
        await db.execute(
            select(Product).where(
                Product.id.in_(product_ids),
                Product.deleted_at.is_(None),
            )
        )
    ).scalars().all()

    prod_map = {p.id: p for p in products_rows}
    result = []
    for pid in product_ids:
        p = prod_map.get(pid)
        if p:
            result.append({
                "id": str(p.id),
                "name": p.name,
                "price": float(p.price) if p.price else 0,
                "image_url": p.image_url,
                "sku": p.sku,
            })
    return result
