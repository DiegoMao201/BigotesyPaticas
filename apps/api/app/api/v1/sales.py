"""Endpoints de ventas: crear órdenes (atómico), consultar, cancelar, factura PDF."""
from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, select

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
async def list_orders(
    db: DBSession,
    limit: int = Query(50, ge=1, le=500),
    status_filter: str | None = Query(None, alias="status"),
    channel: str | None = None,
):
    stmt = select(Order).order_by(desc(Order.occurred_at)).limit(limit)
    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
    if channel:
        stmt = stmt.where(Order.channel == channel)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


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
    default_loc = (await db.execute(
        select(StockLocation).where(StockLocation.is_default == True).limit(1)
    )).scalar_one_or_none()
    location_id = default_loc.id if default_loc else None

    for item in o.items:
        stock = (await db.execute(
            select(Stock).where(
                Stock.product_id == item.product_id,
                Stock.location_id == location_id,
            )
        )).scalar_one_or_none()
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
    o.metadata_ = {**(o.metadata_ or {}), "cancelled_at": datetime.now(UTC).isoformat(), "cancelled_by": user.email, "cancel_reason": reason or ""}
    await db.commit()
    return {"ok": True, "order_number": o.order_number}


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
        c = (await db.execute(
            select(CRMCustomer).where(CRMCustomer.id == o.customer_id)
        )).scalar_one_or_none()
        if c:
            cust_name = c.full_name or "Consumidor Final"
            cust_doc = c.document_id or ""

    items_rows = ""
    for item in o.items:
        total_line = float(item.unit_price) * item.quantity - float(item.discount)
        disc_str = f"-${float(item.discount):,.0f}" if float(item.discount) > 0 else ""
        items_rows += f"""
        <tr>
          <td>{item.name_snapshot}</td>
          <td class="center">{item.sku_snapshot}</td>
          <td class="right">{item.quantity}</td>
          <td class="right">${float(item.unit_price):,.0f}</td>
          <td class="right red">{disc_str}</td>
          <td class="right bold">${total_line:,.0f}</td>
        </tr>"""

    payments_rows = ""
    for pay in o.payments:
        payments_rows += f"<tr><td>{pay.method}</td><td class='right bold'>${float(pay.amount):,.0f}</td></tr>"

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Factura {o.order_number}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 12px; color: #1a1a1a; padding: 32px; background: white; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 28px; border-bottom: 3px solid #FF6B35; padding-bottom: 18px; }}
  .logo {{ font-size: 22px; font-weight: 800; color: #FF6B35; }}
  .logo span {{ color: #1a1a1a; }}
  .invoice-info {{ text-align: right; }}
  .invoice-number {{ font-size: 18px; font-weight: 700; color: #FF6B35; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 100px; font-size: 10px; font-weight: 700; text-transform: uppercase; background: #d1fae5; color: #065f46; }}
  .badge.cancelled {{ background: #fee2e2; color: #991b1b; }}
  .section {{ margin-bottom: 18px; }}
  .section h3 {{ font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: #6b7280; margin-bottom: 6px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #fff7ed; color: #92400e; font-size: 10px; text-transform: uppercase; padding: 8px 10px; text-align: left; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #f3f4f6; }}
  .right {{ text-align: right; }}
  .center {{ text-align: center; }}
  .bold {{ font-weight: 700; }}
  .red {{ color: #ef4444; }}
  .totals {{ margin-top: 10px; float: right; width: 240px; }}
  .totals td {{ border: none; padding: 4px 10px; }}
  .totals .grand {{ font-size: 15px; font-weight: 800; color: #FF6B35; border-top: 2px solid #FF6B35; padding-top: 8px; }}
  .footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #e5e7eb; color: #9ca3af; font-size: 10px; text-align: center; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="logo">🐾 Bigotes<span> y Paticas</span></div>
    <div style="color:#6b7280; font-size:11px; margin-top:4px;">Tienda de mascotas · Dosquebradas, Colombia</div>
    <div style="color:#6b7280; font-size:11px;">bigotesypaticasdosquebradas@gmail.com</div>
  </div>
  <div class="invoice-info">
    <div class="invoice-number">{o.order_number}</div>
    <div style="color:#6b7280; font-size:11px; margin-top:4px;">{o.occurred_at.strftime("%d/%m/%Y %H:%M")}</div>
    <div style="margin-top:6px;"><span class="badge {'cancelled' if o.status=='cancelled' else ''}">{o.status.upper()}</span></div>
  </div>
</div>

<div class="two-col">
  <div class="section">
    <h3>Cliente</h3>
    <div class="bold">{cust_name}</div>
    <div style="color:#6b7280">{cust_doc}</div>
  </div>
  <div class="section">
    <h3>Canal · Pago</h3>
    <div>{o.channel}</div>
    <div class="bold">{o.payment_status}</div>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th>Producto</th><th class="center">SKU</th><th class="right">Cant.</th>
      <th class="right">Precio</th><th class="right">Descuento</th><th class="right">Total</th>
    </tr>
  </thead>
  <tbody>{items_rows}</tbody>
</table>

<div style="overflow:hidden; margin-top:16px;">
  <table class="totals">
    <tr><td>Subtotal</td><td class="right">${float(o.subtotal):,.0f}</td></tr>
    {f'<tr><td style="color:#ef4444">Descuentos</td><td class="right" style="color:#ef4444">-${float(o.discount_total):,.0f}</td></tr>' if float(o.discount_total) > 0 else ''}
    <tr class="grand"><td>TOTAL</td><td class="right">${float(o.grand_total):,.0f}</td></tr>
  </table>
</div>

<div style="clear:both; margin-top:20px;">
  <div class="section">
    <h3>Pagos recibidos</h3>
    <table style="max-width:280px">
      <tbody>{payments_rows}</tbody>
    </table>
    {f'<div style="color:#059669; font-weight:700; margin-top:6px; font-size:13px;">Cambio: ${float(o.paid_amount - o.grand_total):,.0f}</div>' if float(o.paid_amount) > float(o.grand_total) else ''}
  </div>
</div>

{f'<div class="section"><h3>Notas</h3><div>{o.notes}</div></div>' if o.notes else ''}

<div class="footer">
  Gracias por tu compra 🐾 · Este documento es un comprobante de venta · Bigotes y Paticas
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
