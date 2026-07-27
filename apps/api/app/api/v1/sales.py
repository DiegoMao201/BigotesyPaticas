"""Endpoints de ventas: crear órdenes (atómico), consultar, cancelar, factura PDF."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc, func, select

from app.deps import CurrentUser, DBSession, require_permission
from app.models.catalog import Product
from app.models.inventory import Stock, StockLocation, StockMovement
from app.models.sales import Order, OrderItem, Payment
from app.schemas.sales import OrderCreate, OrderOut

router = APIRouter(prefix="/sales", tags=["sales"])


class MarkPaidPayload(BaseModel):
    method: str = "Efectivo"
    reference: str | None = None
    notes: str | None = None


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

    # Resolver location default (fallback: primera disponible si ninguna tiene is_default=1)
    loc = (
        await db.execute(select(StockLocation).where(StockLocation.is_default == 1).limit(1))
    ).scalar_one_or_none()
    if loc is None:
        loc = (
            await db.execute(select(StockLocation).order_by(StockLocation.created_at).limit(1))
        ).scalar_one_or_none()
    if loc is None:
        raise HTTPException(status_code=500, detail="No hay location default")

    # Lock pesimista sobre los productos involucrados (ordenado por id para evitar deadlocks)
    product_ids = sorted({i.product_id for i in payload.items}, key=str)

    products: dict[uuid.UUID, Product] = {}
    for pid in product_ids:
        p = (
            await db.execute(select(Product).where(Product.id == pid).with_for_update(of=Product))
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
    # Colecto movimientos ANTES del flush para poder asignar order.id después
    pending_movements: list[StockMovement] = []

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

        pending_movements.append(
            StockMovement(
                product_id=prod.id,
                location_id=loc.id,
                movement_type="SALE",
                quantity_delta=-item_in.quantity,
                quantity_after=stock.quantity,
                unit_cost=unit_cost,
                reference_type="ORDER",
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

    # Ahora que tenemos order.id, añadimos los movimientos con reference_id correcto
    for mv in pending_movements:
        mv.reference_id = order.id
        db.add(mv)

    await db.commit()
    await db.refresh(order)
    return order


@router.get(
    "/orders/{order_id}",
    response_model=OrderOut,
    dependencies=[Depends(require_permission("sales:read"))],
)
async def get_order(order_id: uuid.UUID, db: DBSession) -> OrderOut:
    o = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if o is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return o


def _product_match_condition(q: str):
    """Coincide si algún ítem de la orden (nombre/SKU) matchea, o —para ventas legadas sin
    order_items normalizados— si la lista de productos en notas lo menciona."""
    from sqlalchemy import String, cast, exists, or_

    pattern = f"%{q}%"
    item_match = exists().where(
        OrderItem.order_id == Order.id,
        or_(
            OrderItem.name_snapshot.ilike(pattern),
            OrderItem.sku_snapshot.ilike(pattern),
        ),
    )
    return or_(item_match, cast(Order.notes, String).ilike(pattern))


def _customer_match_condition(q: str):
    """Coincide por nombre, teléfono o documento del cliente asociado a la orden."""
    from sqlalchemy import exists, or_

    from app.models.crm import Customer as CRMCustomer

    pattern = f"%{q}%"
    return exists().where(
        CRMCustomer.id == Order.customer_id,
        or_(
            CRMCustomer.full_name.ilike(pattern),
            CRMCustomer.phone.ilike(pattern),
            CRMCustomer.document_id.ilike(pattern),
        ),
    )


def _orders_search_condition(q: str):
    """Búsqueda general (OR): # orden, notas, producto o cliente — para el buscador rápido."""
    from sqlalchemy import String, cast, or_

    pattern = f"%{q}%"
    return or_(
        Order.order_number.ilike(pattern),
        cast(Order.notes, String).ilike(pattern),
        _product_match_condition(q),
        _customer_match_condition(q),
    )


@router.get("/orders", dependencies=[Depends(require_permission("sales:read"))])
async def list_orders(
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    q: str | None = None,
    product_q: str | None = None,
    customer_q: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    channel: str | None = None,
    payment_status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """Lista órdenes con búsqueda por número, producto o cliente, filtros y paginación.

    `q` es un buscador rápido de texto libre (OR entre orden/producto/cliente/notas).
    `product_q` y `customer_q` son filtros dedicados que se combinan con AND entre sí
    y con `q`, para acotar p.ej. "facturas de este cliente que incluyan este producto".
    """
    from datetime import date as dt_date

    stmt = select(Order).order_by(desc(Order.occurred_at))
    count_stmt = select(func.count()).select_from(Order)

    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
        count_stmt = count_stmt.where(Order.status == status_filter)
    if channel:
        stmt = stmt.where(Order.channel == channel)
        count_stmt = count_stmt.where(Order.channel == channel)
    if payment_status:
        stmt = stmt.where(Order.payment_status == payment_status)
        count_stmt = count_stmt.where(Order.payment_status == payment_status)
    if q:
        cond = _orders_search_condition(q)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if product_q:
        cond = _product_match_condition(product_q)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if customer_q:
        cond = _customer_match_condition(customer_q)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if date_from:
        try:
            d = dt_date.fromisoformat(date_from)
            stmt = stmt.where(Order.occurred_at >= d)
            count_stmt = count_stmt.where(Order.occurred_at >= d)
        except ValueError:
            pass
    if date_to:
        try:
            d = dt_date.fromisoformat(date_to)
            from datetime import timedelta

            d_end = d + timedelta(days=1)
            stmt = stmt.where(Order.occurred_at < d_end)
            count_stmt = count_stmt.where(Order.occurred_at < d_end)
        except ValueError:
            pass

    total = (await db.execute(count_stmt)).scalar_one()

    # Revenue aggregate (same filters, excludes cancelled)
    rev_stmt = (
        select(
            func.coalesce(func.sum(Order.grand_total), 0).label("revenue"),
            func.count().label("cnt"),
        )
        .select_from(Order)
        .where(Order.status != "cancelled")
    )
    if status_filter and status_filter != "cancelled":
        rev_stmt = rev_stmt.where(Order.status == status_filter)
    if channel:
        rev_stmt = rev_stmt.where(Order.channel == channel)
    if payment_status:
        rev_stmt = rev_stmt.where(Order.payment_status == payment_status)
    if q:
        rev_stmt = rev_stmt.where(_orders_search_condition(q))
    if product_q:
        rev_stmt = rev_stmt.where(_product_match_condition(product_q))
    if customer_q:
        rev_stmt = rev_stmt.where(_customer_match_condition(customer_q))
    if date_from:
        try:
            d = dt_date.fromisoformat(date_from)
            rev_stmt = rev_stmt.where(Order.occurred_at >= d)
        except ValueError:
            pass
    if date_to:
        try:
            d = dt_date.fromisoformat(date_to)
            from datetime import timedelta

            d_end = d + timedelta(days=1)
            rev_stmt = rev_stmt.where(Order.occurred_at < d_end)
        except ValueError:
            pass
    rev_row = (await db.execute(rev_stmt)).one()
    total_revenue = float(rev_row.revenue)
    active_count = int(rev_row.cnt)
    avg_ticket = total_revenue / active_count if active_count > 0 else 0.0

    offset = (page - 1) * page_size
    rows = (await db.execute(stmt.offset(offset).limit(page_size))).scalars().all()

    # Batch-load nombres de clientes para evitar N+1 queries
    from app.models.crm import Customer as CRMCustomer
    from app.schemas.sales import OrderOut

    customer_ids = [o.customer_id for o in rows if o.customer_id]
    customers_map: dict = {}
    if customer_ids:
        cust_rows = (
            await db.execute(
                select(CRMCustomer.id, CRMCustomer.full_name, CRMCustomer.phone).where(
                    CRMCustomer.id.in_(customer_ids)
                )
            )
        ).all()
        customers_map = {c.id: c for c in cust_rows}

    items = []
    for o in rows:
        out = OrderOut.model_validate(o)
        if o.customer_id and o.customer_id in customers_map:
            cust = customers_map[o.customer_id]
            out.customer_name = cust.full_name
            out.customer_phone = cust.phone
        items.append(out)

    return {
        "items": items,
        "total": total,
        "total_revenue": total_revenue,
        "avg_ticket": avg_ticket,
        "active_count": active_count,
        "page": page,
        "page_size": page_size,
    }


@router.post(
    "/orders/{order_id}/cancel",
    dependencies=[Depends(require_permission("sales:write"))],
)
async def cancel_order(
    order_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
    reason: str | None = None,
):
    """Cancela una orden y revierte los movimientos de stock."""
    o = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if o is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if o.status == "cancelled":
        raise HTTPException(status_code=409, detail="Ya cancelada")
    if o.status == "refunded":
        raise HTTPException(status_code=409, detail="Ya reembolsada")

    # Revertir stock para cada item
    default_loc = (
        await db.execute(select(StockLocation).where(StockLocation.is_default == 1).limit(1))
    ).scalar_one_or_none()
    if default_loc is None:
        default_loc = (
            await db.execute(select(StockLocation).order_by(StockLocation.created_at).limit(1))
        ).scalar_one_or_none()
    location_id = default_loc.id if default_loc else None

    for item in o.items:
        stock = (
            await db.execute(
                select(Stock).where(
                    Stock.product_id == item.product_id,
                    Stock.location_id == location_id,
                )
            )
        ).scalar_one_or_none()
        if stock:
            stock.quantity += item.quantity
        mv = StockMovement(
            product_id=item.product_id,
            location_id=location_id,
            movement_type="RETURN",
            quantity_delta=item.quantity,
            quantity_after=(stock.quantity if stock else item.quantity),
            notes=f"Cancelación orden {o.order_number}" + (f" — {reason}" if reason else ""),
            occurred_at=datetime.now(UTC),
            reference_type="order",
            reference_id=o.id,
            created_by=user.email,
        )
        db.add(mv)

    o.status = "cancelled"
    o.metadata_ = {
        **(o.metadata_ or {}),
        "cancelled_at": datetime.now(UTC).isoformat(),
        "cancelled_by": user.email,
        "cancel_reason": reason or "",
    }
    await db.commit()
    return {"ok": True, "order_number": o.order_number}


@router.post(
    "/orders/{order_id}/mark-paid",
    dependencies=[Depends(require_permission("sales:write"))],
)
async def mark_order_paid(
    order_id: uuid.UUID,
    payload: MarkPaidPayload,
    db: DBSession,
    user: CurrentUser,
):
    """Marca una orden como pagada registrando el saldo pendiente como pago."""
    o = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if o is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if o.status == "cancelled":
        raise HTTPException(status_code=409, detail="No se puede pagar una orden anulada")
    if o.status == "refunded":
        raise HTTPException(status_code=409, detail="No se puede pagar una orden reembolsada")

    pending = Decimal(str(o.balance_due or 0))
    if pending <= 0:
        if o.payment_status != "Pagado":
            o.payment_status = "Pagado"
            o.balance_due = Decimal("0")
            o.updated_by = user.email
            await db.commit()
        return {
            "ok": True,
            "order_number": o.order_number,
            "amount_applied": 0.0,
            "payment_status": "Pagado",
        }

    pay = Payment(
        order_id=o.id,
        method=payload.method,
        amount=pending,
        received_at=datetime.now(UTC),
        reference=payload.reference,
        notes=payload.notes,
        created_by=user.email,
    )
    db.add(pay)

    o.paid_amount = Decimal(str(o.paid_amount or 0)) + pending
    o.balance_due = Decimal("0")
    o.payment_status = "Pagado"
    o.payment_method = payload.method
    o.metadata_ = {
        **(o.metadata_ or {}),
        "marked_paid_at": datetime.now(UTC).isoformat(),
        "marked_paid_by": user.email,
    }
    o.updated_by = user.email

    await db.commit()
    return {
        "ok": True,
        "order_number": o.order_number,
        "amount_applied": float(pending),
        "payment_status": o.payment_status,
    }


@router.get("/orders/{order_id}/invoice")
async def get_invoice_pdf(
    order_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
):
    """Genera el comprobante de venta en PDF real (WeasyPrint) con diseño de marca."""
    from app.services.invoice_pdf import generate_invoice_pdf, render_invoice_html

    o = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if o is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    cust_name = "Consumidor Final"
    cust_doc = ""
    if o.customer_id:
        from app.models.crm import Customer as CRMCustomer

        c = (
            await db.execute(select(CRMCustomer).where(CRMCustomer.id == o.customer_id))
        ).scalar_one_or_none()
        if c:
            cust_name = c.full_name or "Consumidor Final"
            cust_doc = c.document_id or ""

    html = render_invoice_html(order=o, customer_name=cust_name, customer_doc=cust_doc)
    pdf_bytes = generate_invoice_pdf(html)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="factura-{o.order_number}.pdf"',
        },
    )
