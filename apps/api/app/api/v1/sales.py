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

        pending_movements.append(StockMovement(
            product_id=prod.id,
            location_id=loc.id,
            movement_type="SALE",
            quantity_delta=-item_in.quantity,
            quantity_after=stock.quantity,
            unit_cost=unit_cost,
            reference_type="ORDER",
            occurred_at=occurred_at,
            created_by=user.email,
        ))

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


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(order_id: uuid.UUID, db: DBSession) -> OrderOut:
    o = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if o is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return o


@router.get("/orders")
async def list_orders(
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    q: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    channel: str | None = None,
    payment_status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """Lista órdenes con búsqueda por número o cliente, filtros y paginación."""
    from datetime import date as dt_date

    from sqlalchemy import String, cast, or_

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
        pattern = f"%{q}%"
        cond = or_(
            Order.order_number.ilike(pattern),
            cast(Order.notes, String).ilike(pattern),
        )
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
        pattern = f"%{q}%"
        cond = or_(
            Order.order_number.ilike(pattern),
            cast(Order.notes, String).ilike(pattern),
        )
        rev_stmt = rev_stmt.where(cond)
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

    return {
        "items": rows,
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
    """Genera factura/comprobante en PDF usando HTML puro (sin WeasyPrint)."""
    o = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if o is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # Customer name
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

    def compact_ref(sku: str) -> str:
        raw = (sku or "").strip()
        if not raw:
            return "-"
        if len(raw) <= 16:
            return raw
        safe = "".join(ch for ch in raw if ch.isalnum())
        return f"REF-{(safe or raw)[-6:].upper()}"

    items_rows = ""
    for item in o.items:
        total_line = float(item.unit_price) * item.quantity - float(item.discount)
        disc_str = f"-${float(item.discount):,.0f}" if float(item.discount) > 0 else "-"
        items_rows += f"""
        <tr>
          <td class="product-cell">
            <div class="product-name">{item.name_snapshot}</div>
          </td>
          <td class="center"><span class="ref-chip">{compact_ref(item.sku_snapshot or "")}</span></td>
          <td class="right">{item.quantity}</td>
          <td class="right">${float(item.unit_price):,.0f}</td>
          <td class="right discount">{disc_str}</td>
          <td class="right bold">${total_line:,.0f}</td>
        </tr>"""

    payments_rows = ""
    for pay in o.payments:
        method = (pay.method or "").replace("_", " ").title()
        payments_rows += (
            f"<tr><td>{method}</td><td class='right bold'>${float(pay.amount):,.0f}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Factura {o.order_number}</title>
<style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        font-family: 'Avenir Next', 'Segoe UI', Tahoma, Geneva, sans-serif;
        font-size: 12px;
        color: #1f2937;
        padding: 28px;
        background: #f6fbfb;
    }}
    .sheet {{
        background: #ffffff;
        border: 1px solid #dbe7e6;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 20px 50px rgba(13, 74, 69, 0.08);
    }}
    .brand-strip {{
        height: 10px;
        background: linear-gradient(90deg, #0d4a45 0%, #187f77 50%, #f5a641 100%);
    }}
    .content {{ padding: 22px 24px 20px; }}
    .header {{ display: flex; justify-content: space-between; gap: 16px; margin-bottom: 18px; }}
    .brand {{ font-size: 24px; font-weight: 800; letter-spacing: -0.02em; color: #0d4a45; }}
    .brand small {{ display: block; font-size: 11px; font-weight: 500; color: #4b5563; margin-top: 4px; }}
    .invoice-card {{
        min-width: 220px;
        border-radius: 12px;
        background: #edfaf9;
        border: 1px solid #cbe9e6;
        padding: 10px 12px;
        text-align: right;
    }}
    .invoice-no {{ font-size: 19px; font-weight: 800; color: #0d4a45; }}
    .muted {{ color: #6b7280; font-size: 11px; }}
    .badge {{
        display: inline-block;
        margin-top: 6px;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        background: #d1fae5;
        color: #065f46;
    }}
    .badge.cancelled {{ background: #fee2e2; color: #991b1b; }}
    .meta {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin: 6px 0 18px;
    }}
    .meta-card {{
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 10px 12px;
    }}
    .meta-title {{ font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6b7280; margin-bottom: 5px; }}
    .meta-value {{ font-size: 13px; font-weight: 600; color: #111827; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{
        background: #fef3e0;
        color: #7c3d0a;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 8px 10px;
        text-align: left;
    }}
    td {{ padding: 8px 10px; border-bottom: 1px solid #edf2f7; }}
    tbody tr:nth-child(odd) {{ background: #fcfdfd; }}
    .right {{ text-align: right; }}
    .center {{ text-align: center; }}
    .bold {{ font-weight: 700; }}
    .discount {{ color: #dc2626; }}
    .product-cell {{ min-width: 220px; }}
    .product-name {{ font-weight: 600; color: #0f172a; }}
    .ref-chip {{
        display: inline-block;
        font-family: 'JetBrains Mono', 'Consolas', monospace;
        font-size: 11px;
        font-weight: 700;
        color: #0d4a45;
        background: #d4f5f3;
        border: 1px solid #a3eeea;
        border-radius: 999px;
        padding: 2px 8px;
    }}
    .summary {{
        margin-top: 14px;
        display: grid;
        grid-template-columns: 1fr 250px;
        gap: 16px;
        align-items: start;
    }}
    .payments-card {{
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 10px 12px;
        background: #ffffff;
    }}
    .payments-title {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: #6b7280; margin-bottom: 6px; font-weight: 700; }}
    .totals {{
        border: 1px solid #dbe7e6;
        border-radius: 12px;
        background: #f9fcfc;
        padding: 8px;
    }}
    .totals td {{ border: none; padding: 4px 8px; }}
    .totals .grand {{
        font-size: 15px;
        font-weight: 800;
        color: #0d4a45;
        border-top: 2px solid #187f77;
        padding-top: 8px;
    }}
    .notes {{
        margin-top: 14px;
        border: 1px dashed #cbd5e1;
        border-radius: 10px;
        padding: 10px 12px;
        color: #334155;
        background: #f8fafc;
    }}
    .footer {{
        margin-top: 18px;
        padding-top: 12px;
        border-top: 1px solid #e5e7eb;
        color: #6b7280;
        font-size: 10px;
        text-align: center;
    }}
</style>
</head>
<body>
<div class="sheet">
    <div class="brand-strip"></div>
    <div class="content">
        <div class="header">
            <div>
                <div class="brand">Bigotes y Paticas<small>Tienda de mascotas · Dosquebradas, Colombia · bigotesypaticasdosquebradas@gmail.com</small></div>
            </div>
            <div class="invoice-card">
                <div class="invoice-no">{o.order_number}</div>
                <div class="muted">{o.occurred_at.strftime("%d/%m/%Y %H:%M")}</div>
                <span class="badge {'cancelled' if o.status == 'cancelled' else ''}">{o.status.upper()}</span>
            </div>
        </div>

        <div class="meta">
            <div class="meta-card">
                <div class="meta-title">Cliente</div>
                <div class="meta-value">{cust_name}</div>
                <div class="muted">{cust_doc or 'Sin documento'}</div>
            </div>
            <div class="meta-card">
                <div class="meta-title">Canal y estado de pago</div>
                <div class="meta-value">{o.channel}</div>
                <div class="muted">{o.payment_status}</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Producto</th>
                    <th class="center">Referencia</th>
                    <th class="right">Cant.</th>
                    <th class="right">Precio</th>
                    <th class="right">Descuento</th>
                    <th class="right">Total</th>
                </tr>
            </thead>
            <tbody>{items_rows}</tbody>
        </table>

        <div class="summary">
            <div class="payments-card">
                <div class="payments-title">Pagos recibidos</div>
                <table>
                    <tbody>{payments_rows}</tbody>
                </table>
                {f'<div style="color:#059669; font-weight:700; margin-top:6px; font-size:12px;">Cambio entregado: ${float(o.paid_amount - o.grand_total):,.0f}</div>' if float(o.paid_amount) > float(o.grand_total) else ''}
            </div>
            <table class="totals">
                <tr><td>Subtotal</td><td class="right">${float(o.subtotal):,.0f}</td></tr>
                {f'<tr><td style="color:#dc2626">Descuentos</td><td class="right" style="color:#dc2626">-${float(o.discount_total):,.0f}</td></tr>' if float(o.discount_total) > 0 else ''}
                <tr class="grand"><td>TOTAL</td><td class="right">${float(o.grand_total):,.0f}</td></tr>
            </table>
        </div>

        {f'<div class="notes"><strong>Notas:</strong> {o.notes}</div>' if o.notes else ''}

        <div class="footer">
            Gracias por tu compra. Este documento es un comprobante de venta oficial de Bigotes y Paticas.
        </div>
    </div>
</div>
</body>
</html>"""

    return StreamingResponse(
        io.BytesIO(html.encode("utf-8")),
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="factura-{o.order_number}.html"',
        },
    )
