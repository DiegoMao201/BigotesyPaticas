"""Funciones compartidas de acciones sobre pedidos del portal.

Usadas por AMBOS endpoints de cambio de status:
  - PATCH /admin/portal/orders/{id}          (endpoint viejo)
  - PATCH /admin/portal/orders/{id}/workflow  (endpoint nuevo, Pet Monitor)

Todas las funciones son idempotentes.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from sqlalchemy import select

from app.deps import DBSession
from app.models.portal import (
    LoyaltyPoint,
    PendingNotification,
    PortalOrder,
    PortalOrderItem,
    PortalReferral,
)

# ── Mapeo de workflow_status a template de notificación ───────────────────────

NOTIFICATION_TEMPLATES: dict[str, str] = {
    "received": "order_received",
    "awaiting_customer": "changes_to_confirm",
    "invoiced": "order_invoiced",
    "in_transit": "ready_for_delivery",
    "delivered": "delivered_with_review_cta",
}


# ── Helper: datos mínimos para renderizar mensajes ────────────────────────────


async def _order_render_data(order: PortalOrder, db: DBSession) -> dict:
    from app.models.crm import Customer

    customer = (
        await db.execute(select(Customer).where(Customer.id == order.customer_id))
    ).scalar_one_or_none()

    items = (
        (
            await db.execute(
                select(PortalOrderItem).where(
                    PortalOrderItem.portal_order_id == order.id,
                    PortalOrderItem.is_removed == False,  # noqa: E712
                )
            )
        )
        .scalars()
        .all()
    )

    subtotal = sum(float(i.subtotal or 0) for i in items)
    if not subtotal and order.unit_price:
        subtotal = float(order.unit_price) * (order.quantity or 1)
    discount = float(order.discount_amount or 0)
    shipping = 0.0 if subtotal >= 30_000 else 8_000.0
    total = subtotal - discount + shipping

    return {
        "id": str(order.id),
        "customer_name": customer.full_name if customer else "",
        "customer_phone": customer.phone if customer else None,
        "payment_method": order.payment_method,
        "shipping_address": order.shipping_address,
        "customer_facing_notes": order.customer_facing_notes,
        "items": [
            {
                "name": i.name or "",
                "quantity": i.quantity,
                "subtotal": float(i.subtotal or 0),
                "is_substituted": i.is_substituted,
                "substituted_from_name": i.substituted_from_name,
            }
            for i in items
        ],
        "subtotal": subtotal,
        "discount_amount": discount,
        "shipping": shipping,
        "total": total,
    }


# ── Helper: renderizar plantilla WhatsApp ─────────────────────────────────────


def _render_template(template_code: str, data: dict) -> str:
    name = data.get("customer_name", "")
    first = name.split(" ")[0] if name else "cliente"
    items = data.get("items", [])

    def fmt_cop(v: float) -> str:
        return f"${int(v):,}".replace(",", ".")

    items_text = "\n".join(
        f"• {i['name']} x{i['quantity']} — {fmt_cop(i['subtotal'])}" for i in items
    )

    totals_parts = []
    if data.get("discount_amount", 0) > 0:
        totals_parts.append(f"Descuento: -{fmt_cop(data['discount_amount'])}")
    shipping = data.get("shipping", 0)
    totals_parts.append("Envío: Gratis 🎉" if shipping == 0 else f"Envío: {fmt_cop(shipping)}")
    totals_parts.append(f"*TOTAL: {fmt_cop(data['total'])}*")
    totals = "\n".join(totals_parts)

    order_id = data.get("id", "")

    if template_code == "order_received":
        return (
            f"Hola {first}! 🐾 Recibimos tu pedido en Bigotes y Paticas.\n\n"
            f"{items_text}\n\n{totals}\n\n"
            f"Estamos revisando disponibilidad. Te avisamos pronto!"
        )

    if template_code == "changes_to_confirm":
        note = (
            f"\n\n📌 {data['customer_facing_notes']}" if data.get("customer_facing_notes") else ""
        )
        return (
            f"Hola {first}! Revisamos tu pedido y hay cambios 🐾\n\n"
            f"{items_text}\n\n{totals}{note}\n\n"
            f"Por favor responde *SÍ* para confirmar o dinos si tienes alguna duda."
        )

    if template_code == "order_invoiced":
        pm = data.get("payment_method") or "pendiente"
        return (
            f"Hola {first}! Tu pedido fue facturado ✅ y está siendo preparado con todo el amor 🐾\n\n"
            f"Pago: {pm}\n\n"
            f"Te avisamos cuando salga a domicilio!"
        )

    if template_code == "ready_for_delivery":
        addr = data.get("shipping_address") or "pendiente"
        return (
            f"Hola {first}! Tu pedido ya está en camino 🚚🐾\n\n"
            f"Dirección: {addr}\n\n"
            f"Estaremos pronto por allá!"
        )

    if template_code == "delivered_with_review_cta":
        short_id = order_id[-8:].upper()
        return (
            f"Hola {first}! Tu pedido #{short_id} fue entregado con éxito ✅🐾\n\n"
            f"Esperamos que tu mascota disfrute cada producto. ¿Nos regalas 2 minutos para calificar tu compra?\n\n"
            f"👇 Entra al portal y gana *20 Puntos Bigotes* por cada reseña (30 si subes foto):\n"
            f"https://portal.bigotesypaticas.com/orders/{order_id}/calificar\n\n"
            f"¡Tu opinión ayuda a otras familias con mascotas! 🐶🐱\n\n"
            f"Bigotes y Paticas 🏠🐾"
        )

    return ""


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PÚBLICAS COMPARTIDAS
# ══════════════════════════════════════════════════════════════════════════════


async def bridge_to_sales(order: PortalOrder, db: DBSession) -> str:
    """Crea sales.order desde portal_order al facturar. Idempotente.

    Returns invoice_number (existente o nuevo).
    """
    if order.sales_order_id:
        return order.invoice_number or ""

    from app.api.v1.sales import _next_order_number
    from app.models.sales import Order as SalesOrder
    from app.models.sales import OrderItem as SalesOrderItem

    items = (
        (
            await db.execute(
                select(PortalOrderItem).where(
                    PortalOrderItem.portal_order_id == order.id,
                    PortalOrderItem.is_removed == False,  # noqa: E712
                )
            )
        )
        .scalars()
        .all()
    )

    total = sum(float(i.subtotal or 0) for i in items)
    if not total and order.unit_price:
        total = float(order.unit_price) * (order.quantity or 1)

    invoice_num = await _next_order_number(db)
    now = datetime.now(UTC)

    sales_order = SalesOrder(
        order_number=invoice_num,
        channel="PORTAL",
        customer_id=order.customer_id,
        grand_total=total,
        subtotal=total,
        tax_total=0,
        discount_total=0,
        shipping_total=0,
        payment_status="Pendiente",
        status="confirmed",
        occurred_at=now,
        notes=f"Pedido portal #{str(order.id)[:8]}",
        metadata_={"portal_order_id": str(order.id)},
    )
    db.add(sales_order)
    await db.flush()

    if items:
        for i in items:
            db.add(
                SalesOrderItem(
                    order_id=sales_order.id,
                    product_id=i.product_id,
                    sku_snapshot=i.sku or "",
                    name_snapshot=i.name or order.product_name,
                    quantity=i.quantity,
                    unit_price=float(i.unit_price or 0),
                    unit_cost=0,
                    discount=0,
                    line_total=float(i.subtotal or 0),
                )
            )
    else:
        db.add(
            SalesOrderItem(
                order_id=sales_order.id,
                product_id=order.product_id,
                sku_snapshot="",
                name_snapshot=order.product_name,
                quantity=order.quantity,
                unit_price=float(order.unit_price or 0),
                unit_cost=0,
                discount=0,
                line_total=total,
            )
        )

    order.invoice_number = invoice_num
    order.invoiced_at = now
    order.sales_order_id = sales_order.id
    return invoice_num


async def credit_loyalty_points(order: PortalOrder, db: DBSession) -> int:
    """Acredita puntos de lealtad por entrega. Idempotente.

    Returns puntos acreditados (0 si ya estaban acreditados).
    """
    if order.points_awarded and order.points_awarded > 0:
        return 0

    items = (
        (
            await db.execute(
                select(PortalOrderItem).where(
                    PortalOrderItem.portal_order_id == order.id,
                    PortalOrderItem.is_removed == False,  # noqa: E712
                )
            )
        )
        .scalars()
        .all()
    )

    total = sum(float(i.subtotal or 0) for i in items)
    if not total and order.unit_price:
        total = float(order.unit_price) * (order.quantity or 1)

    points = math.floor(total / 1000)
    order.points_awarded = points

    if points > 0:
        now = datetime.now(UTC)
        db.add(
            LoyaltyPoint(
                customer_id=order.customer_id,
                points=points,
                reason="portal_order",
                reference_type="portal_order",
                reference_id=order.id,
                description=f"Entrega de pedido: {order.product_name}",
                expires_at=now + timedelta(days=365),
            )
        )

    return points


async def process_referral_reward(order: PortalOrder, db: DBSession) -> bool:
    """Otorga 100 pts al referidor si esta es la primera compra. Idempotente.

    Returns True si se procesó recompensa, False si ya estaba pagada o no hay referral.
    """
    referral = (
        await db.execute(
            select(PortalReferral).where(
                PortalReferral.referred_customer_id == order.customer_id,
                PortalReferral.reward_paid_at == None,  # noqa: E711
            )
        )
    ).scalar_one_or_none()

    if not referral:
        return False

    now = datetime.now(UTC)
    if referral.first_purchase_at is None:
        referral.first_purchase_at = now

    referral.reward_paid_at = now
    db.add(
        LoyaltyPoint(
            customer_id=referral.referrer_customer_id,
            points=100,
            reason="referral",
            reference_type="referral",
            reference_id=referral.id,
            description="Recompensa por referir a un nuevo cliente",
            expires_at=now + timedelta(days=365),
        )
    )

    # Notificar al referidor en portal (no requiere WhatsApp manual)
    from app.api.v1.portal_notifications import notify_customer

    await notify_customer(
        db,
        referral.referrer_customer_id,
        notif_type="referral_reward",
        title="¡Ganaste puntos por referir!",
        body="Tu amigo hizo su primera compra. ¡Recibiste 100 puntos de fidelidad! 🎉",
        data={"referral_id": str(referral.id), "points": 100},
    )
    return True


async def queue_customer_notification(
    order: PortalOrder,
    new_status: str,
    db: DBSession,
) -> dict | None:
    """Crea registro en portal.pending_notifications para modal WhatsApp admin.

    NO envía nada por WhatsApp — solo persiste el mensaje pre-armado
    para que el admin lo envíe manualmente desde el modal.

    Returns dict serializable con la notificación creada, o None si el status
    no requiere notificación.
    """
    template_code = NOTIFICATION_TEMPLATES.get(new_status)
    if not template_code:
        return None

    render_data = await _order_render_data(order, db)
    rendered_message = _render_template(template_code, render_data)
    if not rendered_message:
        return None

    wa_link = f"https://wa.me/?text={quote(rendered_message)}"

    notif = PendingNotification(
        portal_order_id=order.id,
        template_code=template_code,
        rendered_message=rendered_message,
        whatsapp_link=wa_link,
        status="pending",
    )
    db.add(notif)
    await db.flush()

    return {
        "id": str(notif.id),
        "portal_order_id": str(notif.portal_order_id),
        "template_code": notif.template_code,
        "rendered_message": notif.rendered_message,
        "whatsapp_link": notif.whatsapp_link,
        "status": notif.status,
        "customer_name": render_data.get("customer_name", ""),
        "customer_phone": render_data.get("customer_phone"),
        "created_at": notif.created_at.isoformat() if notif.created_at else None,
    }
