"""Pedido de la tienda web (bigotesypaticas.com/checkout), SIN cuenta.

Diego (2-oct-2026): "esos pedidos llegan al admin y yo les hago el proceso como a un
pedido del portal y cuando le doy completado le decimos a google fue una compra real…
necesitamos informarle a google que mi pagina si esta vendiendo".

Antes de esto el checkout solo armaba el enlace de WhatsApp: el pedido llegaba completo
al teléfono y no quedaba en ninguna tabla. Ahora entra al MISMO flujo que los del portal
(portal.portal_orders en 'received' → el admin lo factura, lo alista y lo entrega), con
dos diferencias que importan:

  origen='web'    para que Diego sepa de un vistazo cuál entró por la tienda.
  ga_client_id    el id de la cookie _ga de esa visita, que es lo que le permite a GA4
                  pegar la compra con la búsqueda o el anuncio que trajo al cliente.

El mensaje de WhatsApp NO cambia: la tienda guarda el pedido y después abre WhatsApp
igual que siempre. Si esto falla, el front abre WhatsApp de todas formas — perder una
venta por un error de registro sería mucho peor que no registrarla.

Mismo patrón que /v1/public/grooming: cliente por teléfono (lo encuentra o lo crea),
trampa para bots, freno por IP. NUNCA valida stock, igual que el portal: el admin decide.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections import deque
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from app.api.v1.portal_appointments import _TZ_CO
from app.deps import DBSession
from app.models.catalog import Product
from app.models.portal import PortalOrder, PortalOrderItem
from app.services import bold
from app.services.citas import cliente_por_telefono, limpiar

log = logging.getLogger(__name__)
router = APIRouter(prefix="/public/orders", tags=["public"])

# Regla de domicilio de la tienda web (27-sep-2026). Está duplicada a propósito:
# el front la muestra (apps/store/src/lib/delivery.ts) y el servidor la DECIDE, porque
# el total no puede depender de lo que diga el navegador. Si una cambia, cambian las dos.
GRATIS_DESDE = Decimal("30000")
RADIO_CERCA_KM = 5.0
TARIFA_CERCA = Decimal("3000")
TARIFA_LEJOS = Decimal("5000")
RADIO_MAX_KM = 15.0

MAX_ITEMS = 40
# El freno es contra bots, no contra clientes. Las peticiones de la tienda pasan por el
# proxy de Next (apps/store/next.config.mjs reescribe /api/v1/* hacia la API), así que
# hasta comprobarlo en producción no se sabe si llega la IP real del cliente o la del
# contenedor. Si llegara la del contenedor, un número bajo le cerraría la puerta a toda
# la tienda; por eso el tope es alto y la IP detectada se registra en el log.
MAX_POR_IP_HORA = 60

_por_ip: dict[str, deque] = {}


def _ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


def _frenar_abuso(ip: str) -> None:
    ahora = time.monotonic()
    q = _por_ip.setdefault(ip, deque())
    while q and ahora - q[0] > 3600:
        q.popleft()
    if len(q) >= MAX_POR_IP_HORA:
        raise HTTPException(
            status_code=429,
            detail="Demasiados pedidos seguidos. Escríbenos por WhatsApp, por favor.",
        )
    q.append(ahora)
    if len(_por_ip) > 5000:
        for k in list(_por_ip)[:1000]:
            _por_ip.pop(k, None)


def _celular(raw: str) -> str:
    """Celular colombiano de 10 dígitos (3xx…). Acepta +57, espacios y guiones."""
    d = re.sub(r"\D", "", raw or "")
    if len(d) == 12 and d.startswith("57"):
        d = d[2:]
    if not re.fullmatch(r"3\d{9}", d):
        raise HTTPException(
            status_code=422,
            detail="Escribe un celular de 10 dígitos, por ejemplo 320 687 6633.",
        )
    return d


def _domicilio(subtotal: Decimal, km: float | None) -> tuple[Decimal, str]:
    """Valor del domicilio y el texto que queda escrito en el pedido."""
    if subtotal >= GRATIS_DESDE:
        return Decimal("0"), "Domicilio gratis (pedido desde $30.000)"
    if km is None:
        return Decimal("0"), "Domicilio por confirmar (sin ubicación)"
    if km > RADIO_MAX_KM:
        return Decimal("0"), f"Domicilio por confirmar (a {km:.1f} km, fuera de zona)"
    valor = TARIFA_CERCA if km <= RADIO_CERCA_KM else TARIFA_LEJOS
    return valor, f"Domicilio ${int(valor):,}".replace(",", ".") + f" (a {km:.1f} km)"


def _puede_pagar_en_linea(km: float | None) -> tuple[bool, str]:
    """¿Se le puede cobrar por adelantado? Devuelve (sí/no, motivo).

    COBRAR SIN PODER ENTREGAR ES EL PEOR FALLO POSIBLE de esta integración. Peor que
    no vender: el cliente paga, espera, y hay que devolverle el dinero y explicarle
    por qué. La confianza no se recupera con un reembolso.

    Dos casos la bloquean:

    - **Sin ubicación.** No se sabe si se puede llegar. Antes esto daba domicilio
      $0 y dejaba pagar: se cobraba a ciegas.
    - **Fuera del radio de reparto.** Más allá de 15 km ya no es la zona urbana de
      Pereira y Dosquebradas. Hay que coordinar el envío, acordar el costo y a veces
      decir que no — y nada de eso se puede hacer con el dinero ya cobrado.

    El pedido NO se rechaza: entra igual y se cierra por WhatsApp, que es como se ha
    hecho siempre. Lo único que se niega es el cobro anticipado.
    """
    if km is None:
        return False, (
            "Necesitamos tu ubicación para poder cobrarte el domicilio correcto. "
            "Escríbenos por WhatsApp y lo coordinamos."
        )
    if km > RADIO_MAX_KM:
        return False, (
            f"Tu dirección está a {km:.1f} km del local, fuera de nuestra zona de "
            "reparto en Pereira y Dosquebradas. Escríbenos por WhatsApp: coordinamos "
            "el envío contigo y te decimos el costo antes de cobrarte."
        )
    return True, ""


class ItemIn(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, le=99)


def _recortar(valor: object, tope: int) -> str | None:
    """Recorta un dato de analítica al tamaño de SU columna. Nunca lanza.

    El tope no es decorativo: tiene que ser el de la columna real
    (`ga_client_id` varchar(64), `ga_session_id` varchar(32)). Recortar a un
    número mayor cambiaría el 422 de Pydantic por un error de base al insertar,
    que es el mismo pedido perdido con peor mensaje.
    """
    if valor is None:
        return None
    texto = str(valor).strip()[:tope]
    return texto or None


class PedidoIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=20)
    items: list[ItemIn] = Field(min_length=1, max_length=MAX_ITEMS)
    direccion: str | None = Field(default=None, max_length=300)
    lat: float | None = None
    lng: float | None = None
    km: float | None = None
    notes: str | None = Field(default=None, max_length=500)
    # La huella de Google de ESTA visita. Sin esto la compra entra como "(direct)".
    #
    # ⚠️ ESTOS TRES CAMPOS NO PUEDEN RECHAZAR UN PEDIDO. NUNCA.
    #
    # Tenían `max_length` y el 5-oct-2026 se descubrió lo que costaba: Google cambió
    # el formato de su cookie de sesión (GS1 → GS2) y el valor que extraemos pasó de
    # ser un número corto a `s1759600000$o5$g1$t1759600123$j60$l0$h0`, de 39
    # caracteres. Pydantic devolvía 422 y el pedido ENTERO se perdía.
    #
    # Llevaba así desde el 2 de octubre y nadie lo vio, porque el checkout guardaba
    # con `.catch(() => {})`: cada pedido de la tienda se caía en silencio. En la base
    # no hay un solo registro con origen='web'.
    #
    # Son datos de MEDICIÓN. Perder la atribución de una venta es molesto; perder la
    # venta es grave. Por eso ahora se recortan en vez de rechazar: entre medir mal y
    # no vender, se mide mal.
    ga_client_id: str | None = None
    ga_session_id: str | None = None
    gclid: str | None = None

    @field_validator("ga_client_id", mode="before")
    @classmethod
    def _recortar_client_id(cls, v: object) -> str | None:
        return _recortar(v, 64)

    @field_validator("ga_session_id", mode="before")
    @classmethod
    def _recortar_session_id(cls, v: object) -> str | None:
        return _recortar(v, 32)

    @field_validator("gclid", mode="before")
    @classmethod
    def _recortar_gclid(cls, v: object) -> str | None:
        return _recortar(v, 500)
    # Como quiere pagar. 'bold' = en linea con tarjeta/PSE/Nequi; 'cash' =
    # contraentrega, el flujo de siempre. Es lo UNICO que el navegador decide sobre
    # el pago: el monto se calcula abajo, contra la base, y se firma en el servidor.
    payment_method: Literal["bold", "cash"] = "cash"
    website: str | None = None  # trampa para bots: una persona nunca lo llena


@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_pedido_web(payload: PedidoIn, request: Request, db: DBSession) -> dict:
    if payload.website:  # bot: respondemos "ok" sin guardar nada
        return {"ok": True}
    ip = _ip(request)
    log.info("pedido web entrando · ip detectada: %s", ip)
    _frenar_abuso(ip)

    tel = _celular(payload.phone)
    nombre = limpiar(payload.full_name)

    try:
        ids = [uuid.UUID(i.product_id) for i in payload.items]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Producto inválido en el carrito") from exc

    productos = {
        p.id: p
        for p in (
            await db.execute(
                select(Product).where(
                    Product.id.in_(ids),
                    Product.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    }
    faltantes = [str(i) for i in ids if i not in productos]
    if faltantes:
        raise HTTPException(
            status_code=404,
            detail="Un producto del carrito ya no está disponible. Actualiza la página, por favor.",
        )

    # Los precios SIEMPRE salen de la base, nunca del navegador.
    subtotal = Decimal("0")
    for it in payload.items:
        p = productos[uuid.UUID(it.product_id)]
        subtotal += Decimal(str(p.price or 0)) * it.quantity

    envio, envio_texto = _domicilio(subtotal, payload.km)
    total = subtotal + envio

    ahora = datetime.now(_TZ_CO)
    cliente = await cliente_por_telefono(
        db, nombre, tel, "pedido_web_tienda", ahora, consentimiento=True
    )

    direccion = []
    if payload.direccion:
        direccion.append(payload.direccion.strip())
    if payload.lat is not None and payload.lng is not None:
        direccion.append(f"https://www.google.com/maps?q={payload.lat:.6f},{payload.lng:.6f}")
    if payload.km is not None:
        direccion.append(f"a {payload.km:.1f} km del local")

    notas = [f"Pedido desde la tienda web · Tel: {tel}", envio_texto]
    if payload.notes and payload.notes.strip():
        notas.append(payload.notes.strip())

    primero = productos[uuid.UUID(payload.items[0].product_id)]
    n = len(payload.items)

    # ── PAGO EN LINEA ────────────────────────────────────────────────────────
    # El monto que se firma es el que acaba de calcular ESTE servidor a partir de
    # los precios de la base. El navegador solo dijo que productos y cuantos.
    #
    # `int(total)` sin decimales es obligatorio: Bold exige 76000, nunca 76.000 ni
    # 76000.00, y un error aqui no da mensaje — rechaza el cobro en silencio.
    # El cobro anticipado solo se permite dentro de la zona de reparto. Si no, el
    # pedido entra igual pero como contraentrega/WhatsApp, y la respuesta dice POR QUE
    # —el front necesita el motivo para explicárselo al cliente en sus palabras.
    en_zona, motivo_sin_pago = _puede_pagar_en_linea(payload.km)
    paga_en_linea = (
        payload.payment_method == "bold" and bold.esta_configurado() and en_zona
    )
    referencia = bold.nueva_referencia("web", ahora) if paga_en_linea else None
    monto_bold = int(total) if paga_en_linea else None
    firma = bold.firma_integridad(referencia, monto_bold) if paga_en_linea else None
    order = PortalOrder(
        customer_id=cliente.id,
        product_id=primero.id,
        product_name=(
            f"Pedido web ({n} items)" if n > 1 else (primero.name or "Pedido web")[:300]
        ),
        quantity=sum(i.quantity for i in payload.items),
        unit_price=subtotal,
        total_amount=total,
        notes=" · ".join(notas),
        shipping_address=" · ".join(direccion) or None,
        status="received",
        workflow_status="received",
        origen="web",
        payment_method="bold" if paga_en_linea else "cash",
        order_reference=referencia,
        payment_status="pending" if paga_en_linea else None,
        bold_amount=monto_bold,
        payment_expires_at=(
            ahora + timedelta(minutes=bold.MINUTOS_PARA_PAGAR) if paga_en_linea else None
        ),
        ga_client_id=payload.ga_client_id or None,
        ga_session_id=payload.ga_session_id or None,
        gclid=payload.gclid or None,
    )
    db.add(order)
    await db.flush()

    for it in payload.items:
        p = productos[uuid.UUID(it.product_id)]
        unit = Decimal(str(p.price or 0))
        db.add(
            PortalOrderItem(
                portal_order_id=order.id,
                product_id=p.id,
                sku=p.sku,
                name=p.name,
                image_url=p.primary_image_url,
                quantity=it.quantity,
                unit_price=unit,
                subtotal=unit * it.quantity,
            )
        )

    # AL ADMIN SOLO LE LLEGA LA COMPRA, NUNCA LA INTENCIÓN.
    #
    # Diego (5-oct-2026): "al admin no puede llegar la intención de compra, solo
    # llega el pedido pagado... o por el contrario llega el pedido contraentrega que
    # no usa Bold".
    #
    # Si va a pagar en línea, aquí todavía no hay nada que avisar: abrió el checkout
    # y puede no volver nunca. El aviso sale cuando el pago se confirma, desde el
    # webhook, y entonces dice "💳 Pedido PAGADO". Un panel que suena cada vez que
    # alguien MIRA el checkout deja de servir para avisar.
    #
    # El de contraentrega sí avisa aquí: ahí no hay nada que esperar.
    if not paga_en_linea:
        try:
            from app.api.v1.portal_notifications import notify_admins

            await notify_admins(
                db,
                notif_type="new_order",
                title="Nuevo pedido desde la tienda web",
                body=f"{nombre} ({tel}) pidió {n} producto(s) por ${int(total):,}".replace(
                    ",", "."
                )
                + " 🛒",
                data={
                    "order_id": str(order.id),
                    "customer_id": str(cliente.id),
                    "origen": "web",
                },
            )
        except Exception:
            # Un fallo de aviso no puede tumbar un pedido ya guardado.
            log.exception("no se pudo avisar del pedido web %s", order.id)

    await db.commit()
    respuesta = {
        "ok": True,
        "order_id": str(order.id),
        "subtotal": float(subtotal),
        "envio": float(envio),
        "total": float(total),
        "payment_method": "bold" if paga_en_linea else "cash",
        # Si pidió pagar en línea y no se pudo, aquí va el motivo en palabras del
        # cliente. Sin esto el front solo sabría que "no se pudo", que es justo la
        # clase de silencio que genera desconfianza.
        "pago_en_linea_bloqueado": (
            motivo_sin_pago if (payload.payment_method == "bold" and not paga_en_linea) else None
        ),
        "fuera_de_zona": payload.km is not None and payload.km > RADIO_MAX_KM,
        # Desglose, para que el cliente vea de dónde sale cada peso.
        "envio_texto": envio_texto,
    }
    if paga_en_linea:
        respuesta["bold"] = {
            "order_reference": referencia,
            # Entero, sin decimales: es lo que se firmo y lo que Bold debe cobrar.
            "amount": monto_bold,
            "currency": "COP",
            "integrity_signature": firma,
            # Publica por diseno: va en el boton. La secreta NUNCA sale del servidor.
            "identity_key": bold.IDENTITY_KEY,
        }
    return respuesta
