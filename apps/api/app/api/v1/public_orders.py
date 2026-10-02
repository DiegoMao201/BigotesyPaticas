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

import re
import time
import uuid
from collections import deque
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.v1.portal_appointments import _TZ_CO
from app.deps import DBSession
from app.models.catalog import Product
from app.models.portal import PortalOrder, PortalOrderItem
from app.services.citas import cliente_por_telefono, limpiar

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
MAX_POR_IP_HORA = 20

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


class ItemIn(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, le=99)


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
    ga_client_id: str | None = Field(default=None, max_length=64)
    ga_session_id: str | None = Field(default=None, max_length=32)
    gclid: str | None = Field(default=None, max_length=500)
    website: str | None = None  # trampa para bots: una persona nunca lo llena


@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_pedido_web(payload: PedidoIn, request: Request, db: DBSession) -> dict:
    if payload.website:  # bot: respondemos "ok" sin guardar nada
        return {"ok": True}
    _frenar_abuso(_ip(request))

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

    try:
        from app.api.v1.portal_notifications import notify_admins

        await notify_admins(
            db,
            notif_type="new_order",
            title="Nuevo pedido desde la tienda web",
            body=f"{nombre} ({tel}) pidió {n} producto(s) por ${int(total):,}".replace(",", ".")
            + " 🛒",
            data={"order_id": str(order.id), "customer_id": str(cliente.id), "origen": "web"},
        )
    except Exception:
        pass

    await db.commit()
    return {
        "ok": True,
        "order_id": str(order.id),
        "subtotal": float(subtotal),
        "envio": float(envio),
        "total": float(total),
    }
