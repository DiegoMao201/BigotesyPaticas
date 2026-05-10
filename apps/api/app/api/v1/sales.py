"""Endpoints de ventas: crear órdenes (atómico), consultar."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select

from app.deps import CurrentUser, DBSession, require_permission
from app.models.catalog import Product
from app.models.inventory import Stock, StockLocation, StockMovement
from app.models.sales import Order, OrderItem, Payment
from app.schemas.sales import OrderCreate, OrderOut

router = APIRouter(prefix="/sales", tags=["sales"])


def _normalizar_estado_pago(saldo: Decimal, total: Decimal) -> str:
    """Bit-exact con bp_common.payments — sin etiquetas."""
    if total <= 0:
        return "Pagado"
    if saldo <= 0:
        return "Pagado"
    if saldo >= total:
        return "Pendiente"
    return "Abono parcial"


async def _next_order_number(db) -> str:
    """Formato BP-YYYYMMDD-XXXX."""
    today = datetime.now(UTC).strftime("%Y%m%d")
    last = (
        await db.execute(
            select(Order.order_number)
            .where(Order.order_number.like(f"BP-{today}-%"))
            .order_by(desc(Order.order_number))
            .limit(1)
        )
    ).scalar_one_or_none()
    seq = 1
    if last:
        try:
            seq = int(last.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    return f"BP-{today}-{seq:04d}"


@router.post(
    "/orders",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("sales:write"))],
)
async def create_order(payload: OrderCreate, db: DBSession, user: CurrentUser) -> OrderOut:
    """Crea una orden de manera ATÓMICA: descuenta stock + registra movimientos + payments."""
    if not payload.items:
        raise HTTPException(status_code=400, detail="La orden requiere al menos un ítem")

    # Resolver location default
    loc = (
        await db.execute(
            select(StockLocation).where(StockLocation.is_default == 1).limit(1)
        )
    ).scalar_one_or_none()
    if loc is None:
        raise HTTPException(status_code=500, detail="No hay location default")

    # Lock pesimista sobre los productos involucrados (ordenado por id para evitar deadlocks)
    product_ids = sorted({i.product_id for i in payload.items}, key=str)

    products: dict[uuid.UUID, Product] = {}
    for pid in product_ids:
        p = (
            await db.execute(select(Product).where(Product.id == pid).with_for_update())
        ).scalar_one_or_none()
        if p is None or p.deleted_at is not None or not p.is_active:
            raise HTTPException(status_code=400, detail=f"Producto inválido: {pid}")
        products[pid] = p

    # Construir items y validar stock
    occurred_at = payload.occurred_at or datetime.now(UTC)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)

    order = Order(
        order_number=await _next_order_number(db),
        channel=payload.channel,
        status="confirmed",
        customer_id=payload.customer_id,
        occurred_at=occurred_at,
        notes=payload.notes,
        shipping_total=Decimal(payload.shipping_total),
        created_by=user.email,
    )

    subtotal = Decimal("0")
    discount_total = Decimal("0")

    for item_in in payload.items:
        prod = products[item_in.product_id]
        unit_price = item_in.unit_price if item_in.unit_price is not None else Decimal(prod.price)
        unit_cost = Decimal(prod.cost)
        line_total = (unit_price * item_in.quantity) - Decimal(item_in.discount)
        if line_total < 0:
            raise HTTPException(status_code=400, detail="Descuento mayor al subtotal de línea")

        subtotal += unit_price * item_in.quantity
        discount_total += Decimal(item_in.discount)

        order.items.append(
            OrderItem(
                product_id=prod.id,
                sku_snapshot=prod.sku,
                name_snapshot=prod.name,
                quantity=item_in.quantity,
                unit_price=unit_price,
                unit_cost=unit_cost,
                discount=Decimal(item_in.discount),
                line_total=line_total,
            )
        )

        # Lock + descuento de stock
        stock = (
            await db.execute(
                select(Stock)
                .where(Stock.product_id == prod.id)
                .where(Stock.location_id == loc.id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if stock is None or stock.quantity < item_in.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stock insuficiente para {prod.sku}",
            )
        stock.quantity -= item_in.quantity

        db.add(
            StockMovement(
                product_id=prod.id,
                location_id=loc.id,
                movement_type="SALE",
                quantity_delta=-item_in.quantity,
                quantity_after=stock.quantity,
                unit_cost=unit_cost,
                reference_type="ORDER",
                reference_id=None,  # se setea tras flush
                occurred_at=occurred_at,
                created_by=user.email,
            )
        )

    order.subtotal = subtotal
    order.discount_total = discount_total
    order.grand_total = subtotal - discount_total + Decimal(payload.shipping_total)

    # Payments
    paid = Decimal("0")
    for pay in payload.payments:
        order.payments.append(
            Payment(
                method=pay.method,
                amount=Decimal(pay.amount),
                received_at=occurred_at,
                reference=pay.reference,
                notes=pay.notes,
                created_by=user.email,
            )
        )
        paid += Decimal(pay.amount)

    order.paid_amount = paid
    order.balance_due = max(Decimal("0"), order.grand_total - paid)
    order.payment_status = _normalizar_estado_pago(order.balance_due, order.grand_total)
    if payload.payments:
        order.payment_method = payload.payments[0].method

    db.add(order)
    await db.flush()  # obtiene order.id

    # Asociar movimientos al order_id (parche en lote)
    for item in order.items:
        # buscar el movimiento que insertamos arriba para este producto
        for mv in [
            obj for obj in db.new if isinstance(obj, StockMovement) and obj.product_id == item.product_id and obj.reference_id is None
        ]:
            mv.reference_id = order.id

    await db.commit()
    await db.refresh(order)
    return order


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(order_id: uuid.UUID, db: DBSession) -> OrderOut:
    o = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if o is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return o


@router.get("/orders", response_model=list[OrderOut])
async def list_orders(db: DBSession, limit: int = 50):
    rows = (
        await db.execute(select(Order).order_by(desc(Order.occurred_at)).limit(limit))
    ).scalars().all()
    return rows
