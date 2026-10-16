"""Cotización de envío nacional para el checkout (sin cuenta). 16-oct-2026.

El cliente escribe a qué ciudad va el pedido y aquí se le dice cuánto cuesta y
cuánto tarda con cada transportadora, ANTES de pagar. Es el paso que faltaba para
vender fuera de Pereira y Dosquebradas: hasta hoy el checkout mandaba a "coordinar
por WhatsApp".

Lo que decide este endpoint no es definitivo: al crear el pedido, el servidor vuelve
a pedirle la tarifa a la transportadora y cobra ESA. Aquí solo se muestra.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.deps import DBSession
from app.models.catalog import Product
from app.services import envia

log = logging.getLogger(__name__)
router = APIRouter(prefix="/public/shipping", tags=["public"])

#: Municipios con domicilio propio. Si el cliente pide cotización a uno de estos, no
#: se le cobra transportadora: se le dice que use el domicilio local.
DANE_LOCALES = {"66001000": "Pereira", "66170000": "Dosquebradas"}

MAX_COTIZACIONES_IP_HORA = 40
_por_ip: dict[str, deque] = {}


def _ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")


def _frenar(ip: str) -> None:
    ahora = time.monotonic()
    q = _por_ip.setdefault(ip, deque())
    while q and ahora - q[0] > 3600:
        q.popleft()
    if len(q) >= MAX_COTIZACIONES_IP_HORA:
        raise HTTPException(429, "Demasiadas cotizaciones seguidas. Escríbenos por WhatsApp, por favor.")
    q.append(ahora)
    if len(_por_ip) > 5000:
        for k in list(_por_ip)[:1000]:
            _por_ip.pop(k, None)


class ItemIn(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, le=99)


class DestinoIn(BaseModel):
    """Lo que el cliente escribe. Ciudad y departamento son lo mínimo para cotizar;
    la calle hace falta para la guía, no para el precio."""

    departamento: str = Field(min_length=2, max_length=3)
    ciudad: str = Field(min_length=2, max_length=80)
    calle: str | None = Field(default=None, max_length=160)
    barrio: str | None = Field(default=None, max_length=80)
    referencia: str | None = Field(default=None, max_length=160)
    postal: str | None = Field(default=None, max_length=10)
    cedula: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=120)
    lat: float | None = None
    lng: float | None = None


class CotizacionIn(BaseModel):
    items: list[ItemIn] = Field(min_length=1, max_length=40)
    destino: DestinoIn


@router.get("/departamentos")
async def departamentos() -> list[dict]:
    return [{"codigo": c, "nombre": n} for c, n in envia.DEPARTAMENTOS]


async def resolver_destino(d: DestinoIn, nombre: str = "", telefono: str = "") -> dict:
    """Destino validado contra Envia: con código DANE y postal. Lanza 422 si la
    ciudad no existe en ese departamento."""
    if d.departamento.upper() not in envia.DEPARTAMENTO_NOMBRE:
        raise HTTPException(422, "Elige un departamento de la lista.")
    loc = await envia.localizar(d.ciudad, d.departamento)
    if not loc:
        raise HTTPException(
            422,
            f"No encontramos «{d.ciudad.strip()}» en {envia.DEPARTAMENTO_NOMBRE[d.departamento.upper()]}. "
            "Revisa el nombre del municipio.",
        )
    postal = (d.postal or "").strip()
    if not postal.isdigit() or len(postal) != 6:
        postal = await envia.codigo_postal(loc["nombre"], loc["dane"], loc["state"]) or ""
    return {
        "nombre": nombre,
        "telefono": telefono,
        "email": (d.email or "").strip() or None,
        "cedula": (d.cedula or "").strip() or None,
        "calle": (d.calle or "").strip(),
        "barrio": (d.barrio or "").strip(),
        "referencia": (d.referencia or "").strip(),
        "ciudad": loc["nombre"],
        "dane": loc["dane"],
        "departamento": loc["state"],
        "departamento_nombre": envia.DEPARTAMENTO_NOMBRE.get(loc["state"], loc["state"]),
        "postal": postal,
        "lat": d.lat,
        "lng": d.lng,
    }


async def paquetes_de(db: DBSession, items: list[ItemIn]) -> tuple[list[dict], Decimal, dict]:
    """Los paquetes de Envia y el subtotal, a partir de los productos de la base."""
    try:
        ids = [uuid.UUID(i.product_id) for i in items]
    except ValueError as exc:
        raise HTTPException(422, "Producto inválido en el carrito") from exc
    productos = {
        p.id: p
        for p in (
            await db.execute(select(Product).where(Product.id.in_(ids), Product.deleted_at.is_(None)))
        ).scalars().all()
    }
    if any(i not in productos for i in ids):
        raise HTTPException(404, "Un producto del carrito ya no está disponible. Actualiza la página, por favor.")
    subtotal = Decimal("0")
    lista = []
    for it in items:
        p = productos[uuid.UUID(it.product_id)]
        subtotal += Decimal(str(p.price or 0)) * it.quantity
        lista.append({"nombre": p.name or "", "cantidad": it.quantity, "atributos": p.attributes or {}})
    return envia.empacar(lista, int(subtotal)), subtotal, productos


@router.post("/quote")
async def cotizar(payload: CotizacionIn, request: Request, db: DBSession) -> dict:
    _frenar(_ip(request))
    if not envia.esta_configurado():
        raise HTTPException(503, "Los envíos por transportadora no están disponibles en este momento.")

    destino = await resolver_destino(payload.destino)
    if destino["dane"] in DANE_LOCALES:
        # Es nuestra propia zona: no hay transportadora que cobrar.
        return {
            "ok": True,
            "local": True,
            "destino": destino,
            "tarifas": [],
            "mensaje": f"{DANE_LOCALES[destino['dane']]} es nuestra zona de domicilio propio: "
                       "elige «Pereira o Dosquebradas» y te lo llevamos nosotros.",
        }

    paquetes, subtotal, _ = await paquetes_de(db, payload.items)
    tarifas = await envia.cotizar(envia.destino_a_envia(destino), paquetes)
    peso = round(sum(float(p["weight"]) for p in paquetes), 2)
    log.info("ENVIA · cotización a %s (%s): %d tarifas, %.1f kg",
             destino["ciudad"], destino["departamento"], len(tarifas), peso)
    return {
        "ok": True,
        "local": False,
        "destino": destino,
        "subtotal": float(subtotal),
        "peso_kg": peso,
        "paquetes": len(paquetes),
        "tarifas": [t.dict() for t in tarifas],
        "mensaje": None if tarifas else (
            "Ninguna transportadora nos dio tarifa para esa ciudad. Escríbenos por WhatsApp y lo revisamos."
        ),
    }
