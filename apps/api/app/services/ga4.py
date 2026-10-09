"""Le cuenta a Google que la tienda web vendió — Measurement Protocol de GA4.

POR QUÉ ESTO EXISTE. El checkout de la tienda solo abría WhatsApp. El pedido llegaba
completo al teléfono de Diego y Google no se enteraba de nada: GA4 reportaba 0 compras
y 0 checkouts con 10 carritos y 42 fichas vistas en una semana. Google Ads estaba
recibiendo clics sin saber cuáles vendían, o sea pagando a ciegas.

CUÁNDO SE MANDA. Cuando el admin marca el pedido como ENTREGADO, no cuando el cliente
pulsa el botón. Ese es el único momento en que la venta es de verdad: antes de eso es
intención, y una intención contada como compra infla los números del propio tablero de
Diego. El purchase se manda UNA vez por pedido (candado purchase_sent_at).

EL client_id ES LO QUE HACE QUE SIRVA. GA4 no atribuye por dirección IP ni por teléfono:
atribuye por el id de la cookie _ga del navegador que hizo la visita. La tienda lo captura
en el checkout y lo guarda con el pedido; acá se devuelve. Sin él, la compra entra como
"(direct)" y Google no le da el crédito a la búsqueda ni al anuncio que trajo al cliente
— se mediría la plata sin saber de dónde salió, que es la mitad de lo que hace falta.
Cuando el cliente trae las cookies bloqueadas se manda igual con un id derivado del
pedido: la venta se cuenta (que es lo que Diego pidió) aunque no se pueda atribuir.

NUNCA REVIENTA UN PEDIDO. Si Google responde mal, si falta el secreto o si no hay red,
esto registra el problema en el log y devuelve False. Marcar un pedido como entregado no
puede fallar porque Google esté caído.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy import select

from app.config import get_settings
from app.models.portal import PortalOrder, PortalOrderItem

log = logging.getLogger(__name__)

URL = "https://www.google-analytics.com/mp/collect"
URL_DEBUG = "https://www.google-analytics.com/debug/mp/collect"
MONEDA = "COP"


def _client_id_de_respaldo(order_id) -> str:
    """Un client_id estable para el pedido, cuando no se pudo leer la cookie _ga.

    Formato de GA4: dos números separados por punto. Derivarlo del id del pedido lo
    hace estable: si algún día hay que reenviar el evento, no se duplica el usuario.
    """
    h = hashlib.sha256(str(order_id).encode()).hexdigest()
    return f"{int(h[:8], 16)}.{int(h[8:16], 16)}"


async def _items_del_pedido(db, order: PortalOrder) -> list[dict]:
    filas = (
        (
            await db.execute(
                select(PortalOrderItem)
                .where(PortalOrderItem.portal_order_id == order.id)
                .order_by(PortalOrderItem.created_at)
            )
        )
        .scalars()
        .all()
    )
    items = []
    for f in filas:
        if getattr(f, "is_removed", False):
            continue
        items.append(
            {
                "item_id": f.sku or (str(f.product_id) if f.product_id else "sin-sku"),
                "item_name": (f.name or "Producto")[:100],
                "quantity": int(f.quantity or 1),
                "price": float(f.unit_price or 0),
            }
        )
    if items:
        return items
    # Pedido de un solo renglón (sin filas en portal_order_items)
    return [
        {
            "item_id": str(order.product_id) if order.product_id else "sin-sku",
            "item_name": (order.product_name or "Pedido")[:100],
            "quantity": int(order.quantity or 1),
            "price": float(order.unit_price or 0),
        }
    ]


def _valor(order: PortalOrder) -> float:
    """Lo que realmente se vendió, con el descuento ya aplicado si lo hubo."""
    if order.total_amount is not None:
        return float(order.total_amount)
    bruto = float(order.unit_price or 0)
    return max(bruto - float(order.discount_amount or 0), 0.0)


async def enviar_purchase(db, order: PortalOrder, *, debug: bool = False) -> bool:
    """Manda el purchase de este pedido a GA4. Idempotente. No lanza excepciones."""
    s = get_settings()
    if not s.ga4_measurement_id or not s.ga4_api_secret:
        log.warning(
            "ga4: pedido %s entregado pero falta GA4_MEASUREMENT_ID o GA4_API_SECRET; "
            "la compra NO se le contó a Google",
            order.id,
        )
        return False
    if order.purchase_sent_at is not None and not debug:
        log.info("ga4: pedido %s ya tenía purchase enviado (%s)", order.id, order.purchase_sent_at)
        return False

    valor = _valor(order)
    if valor <= 0:
        log.warning("ga4: pedido %s sin valor (%s); no se manda purchase", order.id, valor)
        return False

    params: dict = {
        "transaction_id": str(order.id),
        "value": round(valor, 2),
        "currency": MONEDA,
        "items": await _items_del_pedido(db, order),
    }
    if order.invoice_number:
        params["affiliation"] = order.invoice_number
    if order.ga_session_id:
        # Pega el evento a la sesión exacta de la visita, no solo al usuario.
        params["session_id"] = order.ga_session_id
    # engagement_time_msec es obligatorio para que GA4 no descarte el evento.
    params["engagement_time_msec"] = 1

    cuerpo = {
        "client_id": order.ga_client_id or _client_id_de_respaldo(order.id),
        "non_personalized_ads": False,
        "events": [{"name": "purchase", "params": params}],
    }

    if not await _mandar(cuerpo, f"pedido {order.id}", debug=debug):
        return False

    order.purchase_sent_at = datetime.now(UTC)
    log.info(
        "ga4: purchase enviado · pedido %s · %s %s · client_id %s",
        order.id,
        valor,
        MONEDA,
        "de la cookie" if order.ga_client_id else "de respaldo (sin cookie _ga)",
    )
    return True


async def enviar_purchase_cita(db, appt, *, debug: bool = False) -> bool:
    """Le cuenta a Google la peluquería cobrada. Idempotente. No lanza excepciones.

    La reserva en la web ya se reporta como `generate_lead` desde el navegador; esto es
    la plata. Se manda cuando el admin completa la cita y escribe cuánto cobró, porque
    hasta ahí no hay venta: una cita reservada que no llegó no es ingreso.

    Sin precio no se manda nada. Es a propósito: un valor inventado le enseñaría a Google
    Ads a pujar por un número que no existe, y eso es peor que no medir.
    """
    s = get_settings()
    if not s.ga4_measurement_id or not s.ga4_api_secret:
        log.warning(
            "ga4: cita %s completada pero falta GA4_MEASUREMENT_ID o GA4_API_SECRET; "
            "la venta NO se le contó a Google",
            appt.id,
        )
        return False
    if getattr(appt, "purchase_sent_at", None) is not None and not debug:
        log.info("ga4: cita %s ya tenía purchase enviado", appt.id)
        return False

    valor = float(appt.price or 0)
    if valor <= 0:
        log.info(
            "ga4: cita %s completada sin precio; no se manda purchase (así es a propósito)",
            appt.id,
        )
        return False

    servicio = (appt.service_type or "Peluquería")[:100]
    params: dict = {
        "transaction_id": f"cita-{appt.id}",
        "value": round(valor, 2),
        "currency": MONEDA,
        "items": [
            {
                "item_id": "servicio-peluqueria",
                "item_name": servicio,
                "item_category": "Peluquería",
                "quantity": 1,
                "price": round(valor, 2),
            }
        ],
        "engagement_time_msec": 1,
    }
    if getattr(appt, "ga_session_id", None):
        params["session_id"] = appt.ga_session_id

    cuerpo = {
        "client_id": getattr(appt, "ga_client_id", None) or _client_id_de_respaldo(appt.id),
        "non_personalized_ads": False,
        "events": [{"name": "purchase", "params": params}],
    }

    if not await _mandar(cuerpo, f"cita {appt.id}", debug=debug):
        return False

    appt.purchase_sent_at = datetime.now(UTC)
    log.info(
        "ga4: purchase enviado · cita %s · %s %s · client_id %s",
        appt.id,
        valor,
        MONEDA,
        "de la cookie" if getattr(appt, "ga_client_id", None) else "de respaldo (sin cookie _ga)",
    )
    return True


async def _mandar(cuerpo: dict, etiqueta: str, *, debug: bool = False) -> bool:
    """Hace el POST a Measurement Protocol. Devuelve si Google aceptó el evento."""
    s = get_settings()
    url = URL_DEBUG if debug else URL
    try:
        async with httpx.AsyncClient(timeout=10) as cli:
            r = await cli.post(
                url,
                params={
                    "measurement_id": s.ga4_measurement_id,
                    "api_secret": s.ga4_api_secret,
                },
                json=cuerpo,
            )
    except Exception as e:  # red caída, DNS, timeout
        log.error("ga4: no se pudo mandar el purchase de %s: %s", etiqueta, e)
        return False

    if debug:
        log.info("ga4 debug %s (%s): %s", r.status_code, etiqueta, r.text[:800])
        return r.status_code == 200

    # Measurement Protocol responde 204 sin cuerpo cuando acepta el evento.
    if r.status_code not in (200, 204):
        log.error(
            "ga4: Google respondió %s al purchase de %s: %s",
            r.status_code,
            etiqueta,
            r.text[:300],
        )
        return False
    return True


async def enviar_purchase_de_venta(
    db, venta, pago: PortalOrder, *, aplicacion=None, debug: bool = False
) -> bool:
    """Le cuenta a Google una venta YA FACTURADA que se cobró con un enlace de pago.

    Diego (9-oct-2026): *"es un pago sin pedido porque ya está facturado… asociarlo a
    la venta que ya se realizó y enviarlo a Google como venta"*.

    **LOS PRODUCTOS SALEN DE LA VENTA, NO DEL PAGO.** Un pago libre no tiene ítems
    —no es un pedido, es plata— así que mandar lo que trae el pago le enseñaría a
    Google que vendemos un artículo llamado "Pago / abono". Lo que se vendió está en
    `sales.order_items`, y es lo que se manda: nombre real, cantidad y precio.

    **El `transaction_id` es el número de la VENTA** (`BP-2026…`), no el id del pago.
    Así, si algún día la misma venta se reportara por otro camino, Google la reconoce
    como la misma y no la cuenta dos veces. Un identificador de negocio es más seguro
    que uno técnico justo para esto.

    **La marca de "ya enviado" va en la APLICACIÓN, no en el pago.** Un pago puede
    cubrir tres facturas, y para Google eso son tres transacciones distintas; si la
    marca viviera en el pago, aplicar dos facturas hoy y la tercera mañana dejaría a
    la tercera sin contar. Con la marca por aplicación, cada venta se cuenta una vez
    y solo una.

    Sin excepciones hacia afuera: contarle mal a Google nunca puede estorbar un cobro
    que ya está hecho.
    """
    from app.models.sales import OrderItem as VentaItem

    s = get_settings()
    if not s.ga4_measurement_id or not s.ga4_api_secret:
        log.warning("ga4: falta GA4_MEASUREMENT_ID o GA4_API_SECRET; la venta %s NO se "
                    "le contó a Google", getattr(venta, "order_number", "?"))
        return False
    marca = aplicacion if aplicacion is not None else pago
    if marca.purchase_sent_at is not None and not debug:
        log.info("ga4: la venta %s ya se le había contado a Google", venta.order_number)
        return False

    valor = float(venta.grand_total or 0)
    if valor <= 0:
        log.warning("ga4: venta %s sin valor; no se manda purchase", venta.order_number)
        return False

    filas = (await db.execute(
        select(VentaItem).where(VentaItem.order_id == venta.id)
    )).scalars().all()
    items = []
    for f in filas:
        nombre = None
        try:
            from app.models.catalog import Product

            nombre = (await db.execute(
                select(Product.name).where(Product.id == f.product_id)
            )).scalar_one_or_none()
        except Exception:
            pass
        items.append({
            "item_id": str(f.product_id),
            "item_name": (nombre or "Producto")[:100],
            "price": round(float(f.unit_price or 0), 2),
            "quantity": int(f.quantity or 1),
        })

    params: dict = {
        "transaction_id": str(venta.order_number),
        "value": round(valor, 2),
        "currency": MONEDA,
        "items": items,
        "affiliation": "Cobro con enlace de pago",
        "engagement_time_msec": 1,
    }
    if pago.ga_session_id:
        params["session_id"] = pago.ga_session_id

    cuerpo = {
        # Si el cliente pagó desde un enlace que le mandamos por WhatsApp no hay
        # cookie _ga, y Google lo verá como tráfico directo. Es lo honesto: no vino
        # de un anuncio y atribuírselo a uno sería enseñarle a pujar por una mentira.
        "client_id": pago.ga_client_id or _client_id_de_respaldo(venta.id),
        "non_personalized_ads": False,
        "events": [{"name": "purchase", "params": params}],
    }

    if not await _mandar(cuerpo, f"venta {venta.order_number}", debug=debug):
        return False

    marca.purchase_sent_at = datetime.now(UTC)
    log.info("ga4: purchase enviado · venta %s · %s %s · %s ítems",
             venta.order_number, valor, MONEDA, len(items))
    return True
