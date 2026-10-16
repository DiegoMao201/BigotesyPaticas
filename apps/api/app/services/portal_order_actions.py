"""Funciones compartidas de acciones sobre pedidos del portal.

Usadas por AMBOS endpoints de cambio de status:
  - PATCH /admin/portal/orders/{id}          (endpoint viejo)
  - PATCH /admin/portal/orders/{id}/workflow  (endpoint nuevo, Pet Monitor)

Todas las funciones son idempotentes.
"""

from __future__ import annotations

import math
import uuid
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


class InsufficientStockError(Exception):
    """Se lanza cuando bridge_to_sales() detecta que uno o más ítems del pedido
    no tienen stock suficiente para facturar. `shortages` es una lista de
    dicts {sku, name, requested, available} para mostrarle al admin."""

    def __init__(self, shortages: list[dict]):
        self.shortages = shortages
        super().__init__(
            "Stock insuficiente: "
            + ", ".join(
                f"{s['name']} (pedido {s['requested']}, disponible {s['available']})"
                for s in shortages
            )
        )


NOTIFICATION_TEMPLATES: dict[str, str] = {
    "received": "order_received",
    "awaiting_customer": "changes_to_confirm",
    "invoiced": "order_invoiced",
    "in_transit": "ready_for_delivery",
    "delivered": "delivered_with_review_cta",
    # Envío nacional: se avisa en cuanto existe la guía (16-oct-2026).
    "shipment_created": "shipment_created",
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
    shipping = 0.0  # portal: domicilio gratis en TODO pedido (Diego 27-sep-2026, para incentivar el portal)
    nacional = order.shipping_mode == "national"
    if nacional:
        # Envío por transportadora: lo que el cliente pagó por el envío es lo que
        # cotizó y se congeló en el pedido.
        shipping = float((order.shipping_quote or {}).get("precio") or 0)
    total = subtotal - discount + shipping

    guia = None
    if nacional:
        from app.models.portal import Shipment

        guia = (
            await db.execute(
                select(Shipment)
                .where(Shipment.portal_order_id == order.id, Shipment.cancelled_at.is_(None))
                .order_by(Shipment.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    return {
        "id": str(order.id),
        "customer_name": customer.full_name if customer else "",
        "customer_phone": customer.phone if customer else None,
        "payment_method": order.payment_method,
        "shipping_address": order.shipping_address,
        "shipping_mode": order.shipping_mode or "local",
        "carrier_nombre": (order.shipping_quote or {}).get("carrier_nombre"),
        "dias_envio": (order.shipping_quote or {}).get("dias"),
        "tracking_number": guia.tracking_number if guia else None,
        "track_url": guia.track_url if guia else None,
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


def _wa_digits(phone: str | None) -> str:
    """Dígitos para wa.me: respeta el código de país si viene con '+', y a los
    celulares colombianos de 10 dígitos les antepone 57 (mismo criterio que
    apps/admin/src/lib/phone.ts)."""
    raw = (phone or "").strip()
    digits = "".join(c for c in raw if c.isdigit())
    if not digits or raw.startswith("+"):
        return digits
    return f"57{digits}" if len(digits) == 10 else digits


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
            f"¡Hola {first}! 🐾 Recibimos tu pedido en *Bigotes y Paticas*.\n\n"
            f"{items_text}\n\n{totals}\n\n"
            f"Revisamos disponibilidad y te confirmamos muy pronto.\n\n"
            f"📱 Sigue tu pedido en el portal: https://mi.bigotesypaticas.com\n"
            f"📸 Instagram: @bigotesypaticas"
        )

    if template_code == "changes_to_confirm":
        note = (
            f"\n\n📌 {data['customer_facing_notes']}" if data.get("customer_facing_notes") else ""
        )
        return (
            f"¡Hola {first}! Revisamos tu pedido y tenemos unos cambios 🐾\n\n"
            f"{items_text}\n\n{totals}{note}\n\n"
            f"Responde *SÍ* para confirmarlo, o apruébalo en tu portal. Si tienes alguna duda, escríbenos. ¡Estamos aquí para ayudarte!\n\n"
            f"📱 Tu portal de clientes: https://mi.bigotesypaticas.com"
        )

    if template_code == "order_invoiced":
        pm = data.get("payment_method") or "pendiente"
        return (
            f"¡Hola {first}! Tu pedido fue facturado ✅ y está siendo preparado con todo el cariño 🐾\n\n"
            f"Pago: {pm}\n\n"
            f"Te avisamos cuando salga a domicilio.\n\n"
            f"📱 Sigue el estado en tu portal: https://mi.bigotesypaticas.com\n"
            f"🛒 Catálogo completo: https://bigotesypaticas.com"
        )

    nacional = data.get("shipping_mode") == "national"
    guia_txt = ""
    if data.get("tracking_number"):
        guia_txt = f"📦 Guía {data.get('carrier_nombre') or ''}: *{data['tracking_number']}*"
        if data.get("track_url"):
            guia_txt += f"\n🔎 Rastréalo aquí: {data['track_url']}"

    carrier = data.get('carrier_nombre') or 'la transportadora'
    # Quién responde por qué, en el mismo mensaje de la guía (Diego, 16-oct-2026):
    # la compra es con la tienda; desde que la transportadora recibe el paquete,
    # el transporte y la entrega son responsabilidad de ella.
    responsabilidad = (
        f"📌 Tu compra es con Bigotes y Paticas. Desde que {carrier} recibe el paquete, "
        f"el transporte y la entrega son responsabilidad de {carrier}; cualquier novedad "
        f"nos la escribes por aquí y nosotros gestionamos la reclamación contigo."
    )

    if template_code == "shipment_created":
        return (
            f"¡Hola {first}! Tu pedido ya tiene guía de envío ✅🐾\n\n"
            f"{guia_txt}\n\n"
            f"Sale con {carrier} y el tiempo estimado es "
            f"{data.get('dias_envio') or 'de pocos días'} desde que lo recoge. "
            f"Ya está pagado: no pagas nada al recibir.\n\n"
            f"{responsabilidad}\n\n"
            f"🛒 bigotesypaticas.com · 📸 @bigotesypaticas"
        )

    if template_code == "ready_for_delivery" and nacional:
        addr = data.get("shipping_address") or "pendiente"
        return (
            f"¡Hola {first}! Tu pedido ya está en manos de {data.get('carrier_nombre') or 'la transportadora'} 🚚🐾\n\n"
            f"📍 Va para: {addr}\n"
            f"{guia_txt}\n\n"
            f"Tiempo estimado: {data.get('dias_envio') or 'pocos días'}. Tu pedido ya está pagado: "
            f"no tienes que pagar nada al recibirlo.\n\n"
            f"{responsabilidad}\n\n"
            f"📸 @bigotesypaticas · 🛒 bigotesypaticas.com"
        )

    if template_code == "ready_for_delivery":
        addr = data.get("shipping_address") or "pendiente"
        return (
            f"¡Hola {first}! Tu pedido ya va en camino 🚚🐾\n\n"
            f"📍 Dirección: {addr}\n\n"
            f"¡Estaremos pronto por allá! Pago contra entrega.\n\n"
            f"📱 Tu portal: https://mi.bigotesypaticas.com\n"
            f"📸 @bigotesypaticas · 🛒 bigotesypaticas.com"
        )

    if template_code == "delivered_with_review_cta":
        short_id = order_id[-8:].upper()
        return (
            f"¡Hola {first}! Tu pedido #{short_id} fue entregado con éxito ✅🐾\n\n"
            f"¿Tu mascota ya lo aprobó? 🐶🐱 Esperamos que lo disfrute muchísimo.\n\n"
            f"⭐ *Califica tu compra y gana 20 Puntos Bigotes* (30 si subes foto):\n"
            f"👉 https://mi.bigotesypaticas.com\n\n"
            f"¿Aún no tienes cuenta en el portal? Regístrate gratis en 30 segundos:\n"
            f"👉 https://mi.bigotesypaticas.com/registro\n\n"
            f"En el portal puedes:\n"
            f"✓ Acumular Puntos Bigotes con cada compra\n"
            f"✓ Llevar el carnet de salud de tu mascota\n"
            f"✓ Pedir domicilio sin llamar\n\n"
            f"📸 Síguenos en Instagram: @bigotesypaticas\n"
            f"🛒 Tienda: https://bigotesypaticas.com\n"
            f"📍 Samara Plaza Mall, Local 2 · 320 687 6633\n\n"
            f"¡Gracias por confiar en Bigotes y Paticas! 🏠🐾"
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
    # El descuento que el admin dio en el pedido tiene que llegar a la factura
    discount = min(float(order.discount_amount or 0), total)
    envio_nacional = (
        float((order.shipping_quote or {}).get("precio") or 0)
        if order.shipping_mode == "national" else 0.0
    )

    # ── Validar + descontar inventario real ANTES de crear la factura ────────
    # Mismo patrón que el POS (app/api/v1/sales.py): lock de fila + StockMovement.
    # Si falta stock, se lanza InsufficientStockError y NO se crea nada (rollback
    # automático de get_db() al propagar la excepción).
    from app.models.catalog import Product
    from app.models.inventory import Stock, StockLocation, StockMovement

    if items:
        stock_lines = [(i.product_id, i.quantity, i.name or "") for i in items if i.product_id]
    elif order.product_id:
        stock_lines = [(order.product_id, order.quantity or 1, order.product_name)]
    else:
        stock_lines = []

    if stock_lines:
        loc = (
            await db.execute(select(StockLocation).where(StockLocation.is_default == 1).limit(1))
        ).scalar_one_or_none()
        if not loc:
            loc = (
                await db.execute(select(StockLocation).order_by(StockLocation.created_at).limit(1))
            ).scalar_one_or_none()

        shortages: list[dict] = []
        locked_stocks: dict[uuid.UUID, Stock] = {}
        if loc:
            for product_id, qty, name in stock_lines:
                stock = (
                    await db.execute(
                        select(Stock)
                        .where(Stock.product_id == product_id)
                        .where(Stock.location_id == loc.id)
                        .with_for_update()
                    )
                ).scalar_one_or_none()
                available = stock.quantity if stock else 0
                if available < qty:
                    prod = (
                        await db.execute(select(Product.sku).where(Product.id == product_id))
                    ).scalar_one_or_none()
                    shortages.append(
                        {"sku": prod or "", "name": name, "requested": qty, "available": available}
                    )
                else:
                    locked_stocks[product_id] = stock

            if shortages:
                raise InsufficientStockError(shortages)

            occurred_at = datetime.now(UTC)
            for product_id, qty, _name in stock_lines:
                stock = locked_stocks[product_id]
                stock.quantity -= qty
                db.add(
                    StockMovement(
                        product_id=product_id,
                        location_id=loc.id,
                        movement_type="SALE",
                        quantity_delta=-qty,
                        quantity_after=stock.quantity,
                        reference_type="PORTAL_ORDER",
                        reference_id=order.id,
                        occurred_at=occurred_at,
                        created_by="admin_portal",
                        notes=f"Facturación pedido portal #{str(order.id)[:8]}",
                    )
                )

    invoice_num = await _next_order_number(db)
    now = datetime.now(UTC)

    # EL ENVÍO NO ES VENTA (Diego, 16-oct-2026): *"al facturar solo facturo el
    # producto, pero necesito ver en la venta y en la factura el pago del envío
    # discriminado [...] eso lo llevamos no a ventas sino a un registro de envíos
    # para cruzarlo con Bold"*. Por eso `grand_total` lleva SOLO los productos;
    # el envío queda en `shipping_total` y en `metadata` para verlo en la factura
    # y en el registro de envíos, sin sumar a los ingresos.
    metadata = {"portal_order_id": str(order.id)}
    if envio_nacional:
        q = order.shipping_quote or {}
        metadata["envio"] = {
            "modo": "national", "carrier": q.get("carrier"), "carrier_nombre": q.get("carrier_nombre"),
            "cobrado_al_cliente": envio_nacional, "order_reference": order.order_reference,
            "bold_amount": order.bold_amount,
        }
    sales_order = SalesOrder(
        order_number=invoice_num,
        channel="PORTAL",
        customer_id=order.customer_id,
        grand_total=total - discount,
        subtotal=total,
        tax_total=0,
        discount_total=discount,
        shipping_total=envio_nacional,
        payment_status="Pendiente",
        status="confirmed",
        occurred_at=now,
        notes=f"Pedido portal #{str(order.id)[:8]}",
        metadata_=metadata,
    )
    db.add(sales_order)
    await db.flush()

    # Un pedido nacional YA PAGADO con Bold entra a la venta como pagado, por el
    # valor de los productos: el resto del cobro de Bold es el envío y vive en el
    # registro de envíos. Así la factura sale con el sello PAGADO y la caja no
    # muestra un saldo pendiente que el cliente ya cubrió.
    if envio_nacional and order.payment_status == "paid" and order.payment_method == "bold":
        from app.models.sales import Payment

        productos = total - discount
        db.add(
            Payment(
                order_id=sales_order.id,
                method="bold",
                amount=productos,
                received_at=order.paid_at or now,
                reference=order.order_reference,
                notes=(f"Pago en línea Bold de ${int(order.bold_amount or 0):,}: productos "
                       f"${int(productos):,} + envío ${int(envio_nacional):,} (registro de envíos)").replace(",", "."),
                created_by="bold",
            )
        )
        sales_order.paid_amount = productos
        sales_order.balance_due = 0
        sales_order.payment_status = "Pagado"
        sales_order.payment_method = "bold"

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

    # Promo permanente: doble puntos en el primer pedido entregado del cliente.
    is_first_order = False
    if points > 0:
        prior = (
            await db.execute(
                select(LoyaltyPoint.id)
                .where(
                    LoyaltyPoint.customer_id == order.customer_id,
                    LoyaltyPoint.reason == "portal_order",
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        is_first_order = prior is None
        if is_first_order:
            points *= 2

    order.points_awarded = points

    if points > 0:
        now = datetime.now(UTC)
        description = f"Entrega de pedido: {order.product_name}"
        if is_first_order:
            description += " (¡doble puntos por tu primer pedido!)"
        db.add(
            LoyaltyPoint(
                customer_id=order.customer_id,
                points=points,
                reason="portal_order",
                reference_type="portal_order",
                reference_id=order.id,
                description=description,
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

    # Con el número del cliente: antes iba sin teléfono y WhatsApp pedía elegir el
    # contacto a mano en cada mensaje (Diego 28-sep-2026).
    digits = _wa_digits(render_data.get("customer_phone"))
    wa_link = f"https://wa.me/{digits}?text={quote(rendered_message)}"

    # El mensaje anterior de este pedido que nunca se envió ya no aplica: queda
    # "saltado" para que no se acumulen avisos viejos en el contador del admin.
    from sqlalchemy import update as sa_update

    await db.execute(
        sa_update(PendingNotification)
        .where(
            PendingNotification.portal_order_id == order.id,
            PendingNotification.status == "pending",
        )
        .values(status="skipped")
    )

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
