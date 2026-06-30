"""Portal Orders — pedidos desde el portal de clientes (sin mostrar stock)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select

from app.api.v1.portal_auth import PortalUser
from app.api.v1.portal_loyalty import award_points
from app.deps import DBSession
from app.models.catalog import Product
from app.models.crm import Customer
from app.models.portal import ActivityLog, PortalOrder, PortalOrderItem
from app.models.sales import Order as SalesOrder
from app.models.sales import OrderItem as SalesOrderItem
from app.services import meta_conversion_api as capi

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
        (
            await db.execute(
                select(PortalOrder)
                .where(PortalOrder.customer_id == customer.id)
                .order_by(PortalOrder.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
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
                description=f"Pedido portal: {product.name} x{order.quantity}",
                db=db,
            )

    # Meta Conversion API — Purchase event
    if order.unit_price:
        total_value = order.unit_price * order.quantity
        capi.send_event(
            "Purchase",
            user_data={
                "email": customer.email,
                "phone": customer.phone,
                "external_id": str(customer.id),
                "first_name": customer.full_name.split()[0] if customer.full_name else "",
            },
            custom_data={
                "value": round(total_value, 2),
                "currency": "COP",
                "content_ids": [product.sku or str(product.id)],
                "content_type": "product",
                "content_name": product.name,
                "num_items": order.quantity,
            },
            event_id=f"portal_order_{order.id}",
            event_source_url="https://mi.bigotesypaticas.com",
        )

    return _order_out(order, points=points_earned if points_earned else None)


# ── multi-product order ────────────────────────────────────────────────


class MultiOrderItemIn(BaseModel):
    product_id: str
    quantity: int = 1
    notes: str | None = None


class MultiOrderIn(BaseModel):
    items: list[MultiOrderItemIn]
    shipping_address: str
    payment_method: str
    general_notes: str | None = None


@router.post("/multi", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_multi_order(
    payload: MultiOrderIn,
    db: DBSession,
    customer: Customer = PortalUser,
) -> OrderOut:
    """Pedido con múltiples productos. NUNCA valida stock."""
    if not payload.items:
        raise HTTPException(status_code=400, detail="El carrito está vacío")

    product_ids = [uuid.UUID(i.product_id) for i in payload.items]
    products_rows = (
        (
            await db.execute(
                select(Product).where(
                    Product.id.in_(product_ids),
                    Product.deleted_at == None,  # noqa: E711
                )
            )
        )
        .scalars()
        .all()
    )
    products_map = {p.id: p for p in products_rows}

    for item in payload.items:
        pid = uuid.UUID(item.product_id)
        if pid not in products_map:
            raise HTTPException(status_code=404, detail=f"Producto {item.product_id} no encontrado")
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail="Cantidad debe ser mayor a 0")

    subtotal = sum(
        float(products_map[uuid.UUID(i.product_id)].price or 0) * i.quantity for i in payload.items
    )
    shipping = 0 if subtotal >= 30000 else 8000
    _total = subtotal + shipping
    points_to_earn = int(subtotal / 1000)

    # Use first product as primary (backward compat with portal_orders columns)
    first_prod = products_map[uuid.UUID(payload.items[0].product_id)]

    order = PortalOrder(
        customer_id=customer.id,
        product_id=first_prod.id,
        product_name=f"Pedido multi-producto ({len(payload.items)} items)",
        quantity=sum(i.quantity for i in payload.items),
        unit_price=subtotal,
        notes=payload.general_notes,
        payment_method=payload.payment_method,
        shipping_address=payload.shipping_address,
        status="received",
    )
    db.add(order)
    await db.flush()

    for item in payload.items:
        pid = uuid.UUID(item.product_id)
        prod = products_map[pid]
        unit = float(prod.price or 0)
        db.add(
            PortalOrderItem(
                portal_order_id=order.id,
                product_id=prod.id,
                sku=prod.sku,
                name=prod.name,
                image_url=prod.primary_image_url,
                quantity=item.quantity,
                unit_price=unit,
                subtotal=unit * item.quantity,
                notes=item.notes,
            )
        )

    await db.commit()
    await db.refresh(order)

    import contextlib

    points_earned = 0
    with contextlib.suppress(Exception):
        points_earned = await award_points(db, customer.id, order.id, points_to_earn)

    return _order_out(order, points=points_earned or None)


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
    """Top productos del cliente leyendo TODO el historial de sales.orders.
    Fallback a más populares globalmente si el cliente tiene poca historia."""

    # Historial completo del cliente en sales.orders
    personal = (
        await db.execute(
            select(
                SalesOrderItem.product_id,
                func.count().label("freq"),
                func.max(SalesOrder.occurred_at).label("last_at"),
            )
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrder.customer_id == customer.id,
                SalesOrderItem.product_id.is_not(None),
            )
            .group_by(SalesOrderItem.product_id)
            .order_by(func.count().desc(), func.max(SalesOrder.occurred_at).desc())
            .limit(limit)
        )
    ).all()

    product_ids = [r.product_id for r in personal]

    if len(product_ids) < limit:
        # Fallback: más pedidos globalmente (excluye los ya encontrados)
        popular_q = (
            select(SalesOrderItem.product_id, func.count().label("freq"))
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .join(Product, SalesOrderItem.product_id == Product.id)
            .where(
                SalesOrderItem.product_id.is_not(None),
                Product.deleted_at.is_(None),
                Product.is_published == True,  # noqa: E712
            )
            .group_by(SalesOrderItem.product_id)
            .order_by(func.count().desc())
            .limit(limit - len(product_ids))
        )
        if product_ids:
            popular_q = popular_q.where(SalesOrderItem.product_id.not_in(product_ids))
        popular = (await db.execute(popular_q)).all()
        product_ids += [r.product_id for r in popular]

    if not product_ids:
        return []

    products_rows = (
        (
            await db.execute(
                select(Product).where(
                    Product.id.in_(product_ids),
                    Product.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )

    prod_map = {p.id: p for p in products_rows}
    result = []
    for pid in product_ids:
        p = prod_map.get(pid)
        if p:
            result.append(
                {
                    "id": str(p.id),
                    "name": p.name,
                    "price": float(p.price) if p.price else 0,
                    "image_url": p.primary_image_url,
                    "sku": p.sku,
                }
            )
    return result


# ── timeline del pedido (cliente) ──────────────────────────────────────

ACTION_LABELS: dict[str, str] = {
    "created": "Pedido recibido 📬",
    "status_changed": "Estado actualizado",
    "item_quantity_changed": "Cantidad ajustada",
    "item_substituted": "Producto sustituido",
    "item_added": "Producto agregado",
    "item_removed": "Producto removido",
    "discount_applied": "Descuento aplicado 🎉",
    "address_changed": "Dirección actualizada",
    "notes_updated": "Nota del equipo",
    "cancelled": "Pedido cancelado",
}


@router.get("/{order_id}/timeline")
async def order_timeline(
    order_id: uuid.UUID,
    db: DBSession,
    customer: Customer = PortalUser,
) -> dict:
    """Timeline informativo del pedido visible al cliente."""
    order = (
        await db.execute(
            select(PortalOrder).where(
                PortalOrder.id == order_id,
                PortalOrder.customer_id == customer.id,
            )
        )
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    items = (
        (
            await db.execute(
                select(PortalOrderItem)
                .where(
                    PortalOrderItem.portal_order_id == order_id,
                    PortalOrderItem.is_removed == False,  # noqa: E712
                )
                .order_by(PortalOrderItem.created_at)
            )
        )
        .scalars()
        .all()
    )

    # Activity log visible al cliente
    try:
        logs = (
            (
                await db.execute(
                    select(ActivityLog)
                    .where(
                        ActivityLog.entity_type == "order",
                        ActivityLog.entity_id == order_id,
                        ActivityLog.visible_to_customer == True,  # noqa: E712
                    )
                    .order_by(ActivityLog.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        timeline = [
            {
                "action": lg.action,
                "label": ACTION_LABELS.get(lg.action, lg.action.replace("_", " ").title()),
                "notes": lg.notes,
                "created_at": lg.created_at.isoformat(),
            }
            for lg in logs
        ]
    except Exception:
        # activity_log table may not exist yet in dev
        timeline = []

    subtotal = sum(float(i.subtotal or 0) for i in items)
    discount = float(order.discount_amount or 0) if hasattr(order, "discount_amount") else 0.0
    shipping = 0.0 if subtotal >= 30000 else 8000.0
    total = subtotal - discount + shipping

    ws = getattr(order, "workflow_status", order.status)

    return {
        "id": str(order.id),
        "status": order.status,
        "workflow_status": ws,
        "customer_facing_notes": getattr(order, "customer_facing_notes", None),
        "payment_method": order.payment_method,
        "shipping_address": order.shipping_address,
        "discount_amount": discount,
        "subtotal": subtotal,
        "shipping": shipping,
        "total": total,
        "invoice_number": order.invoice_number,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "created_at": order.created_at.isoformat(),
        "items": [
            {
                "id": str(i.id),
                "product_id": str(i.product_id) if i.product_id else None,
                "name": i.name,
                "image_url": i.image_url,
                "quantity": i.quantity,
                "unit_price": float(i.unit_price or 0),
                "subtotal": float(i.subtotal or 0),
                "is_substituted": i.is_substituted,
                "substituted_from_name": i.substituted_from_name,
                "notes": i.notes,
            }
            for i in items
        ],
        "timeline": timeline,
    }
