"""Enlaces de cobro que crea Diego a mano, para ventas que no nacen en la web.

Diego (5-oct-2026): *"la página de pagos o link de pago para cualquier otro tipo de
pagos que no son de la web, ¿qué URL o cómo lo comparto?"*.

El caso es el de todos los días: alguien escribe por WhatsApp, Diego le arma el
pedido, y hasta hoy el cobro se cerraba contra entrega o por transferencia. Con esto
le manda un enlace y cobra al momento.

POR QUÉ NO SE USAN LOS "LINKS DE PAGO" DEL PANEL DE BOLD
Bold los ofrece y funcionan, pero el dinero entraría por fuera: no crean pedido, no
avisan al admin, no quedan en `portal_orders` y no aparecen en los reportes. Una
venta que el sistema no ve es una venta que después hay que cuadrar a mano. Creando
el cobro aquí, entra por el MISMO camino que todo lo demás —webhook, verificación de
monto, aviso, correo, pedido pagado— y se usa LA MISMA página de pago.

SOBRE EL MONTO
En la tienda el monto lo calcula el servidor y jamás se acepta del navegador: ahí el
que pide es un desconocido. Aquí lo fija un **admin autenticado con permiso de
escritura**, que es la autoridad sobre los precios de su propio negocio. No es la
misma situación y no merece la misma regla.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.v1.portal_appointments import _TZ_CO
from app.deps import DBSession, require_permission
from app.models.portal import PortalOrder
from app.services import bold
from app.services.citas import cliente_por_telefono, limpiar

log = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/payment-links", tags=["admin"])

TIENDA = "https://bigotesypaticas.com"

#: Tope de seguridad. No es desconfianza: es que un cero de más en un cobro que se
#: manda por WhatsApp se descubre cuando el cliente ya lo vio.
MAX_COBRO = 20_000_000


class CobroIn(BaseModel):
    concepto: str = Field(min_length=3, max_length=200)
    monto: int = Field(gt=0, le=MAX_COBRO)
    cliente_nombre: str = Field(min_length=2, max_length=120)
    cliente_telefono: str = Field(min_length=7, max_length=20)
    notas: str | None = Field(default=None, max_length=500)
    #: Minutos de validez. Por defecto un día: un enlace que se manda por WhatsApp
    #: no se paga en 30 minutos como el checkout; la gente lo lee cuando puede.
    minutos_validez: int = Field(default=1440, ge=30, le=10_080)


@router.post("", dependencies=[Depends(require_permission("crm:write"))])
async def crear_enlace_de_cobro(payload: CobroIn, db: DBSession) -> dict:
    """Crea un cobro y devuelve el enlace para mandárselo al cliente.

    El pedido queda en `portal_orders` con `origen='link'`, así que se distingue de
    los de la tienda y del portal, pero recorre exactamente el mismo camino: cuando
    el cliente paga, el webhook lo confirma, suena el aviso, sale el correo y el
    pedido aparece en el panel como **PAGADO**.

    Mientras no se pague NO aparece en el panel, igual que los de la tienda: un
    enlace enviado todavía no es una venta.
    """
    if not bold.esta_configurado():
        raise HTTPException(
            status_code=503,
            detail="Bold no está configurado: no se pueden crear enlaces de cobro.",
        )

    telefono = limpiar(payload.cliente_telefono)
    nombre = limpiar(payload.cliente_nombre)
    ahora = datetime.now(_TZ_CO)

    # Se busca o se crea el cliente por su celular, igual que en todo el resto del
    # sistema: así el cobro queda colgado de SU ficha y suma a su historial, en vez
    # de ser un registro suelto.
    cliente = await cliente_por_telefono(
        db, nombre, telefono, "link_de_cobro", ahora, consentimiento=False
    )

    referencia = bold.nueva_referencia("portal", ahora).replace("BPP-", "BPL-", 1)
    monto = int(payload.monto)

    order = PortalOrder(
        customer_id=cliente.id,
        product_name=payload.concepto[:300],
        quantity=1,
        unit_price=Decimal(monto),
        total_amount=Decimal(monto),
        notes=" · ".join(
            x for x in [f"Enlace de cobro · Tel: {telefono}", payload.notas] if x
        ),
        status="received",
        workflow_status="received",
        origen="link",
        payment_method="bold",
        payment_status="pending",
        order_reference=referencia,
        bold_amount=monto,
        payment_expires_at=ahora + timedelta(minutes=payload.minutos_validez),
    )
    db.add(order)
    await db.commit()

    enlace = f"{TIENDA}/pagar/{referencia}"
    log.info("COBRO · enlace creado %s por $%s (%s)", referencia, monto, nombre)

    # El mensaje llega listo para enviar. Escribirlo a mano cada vez es donde se
    # cuelan los errores de monto y donde se pierde el tono.
    texto = (
        f"Hola {nombre.split()[0]}! 🐾 Aquí está tu enlace para pagar "
        f"{payload.concepto}: ${monto:,.0f}".replace(",", ".")
        + f"\n\n{enlace}\n\nEs un pago seguro procesado por Bold. "
        "Cualquier duda, escríbenos por aquí mismo."
    )

    return {
        "ok": True,
        "order_id": str(order.id),
        "referencia": referencia,
        "monto": monto,
        "enlace": enlace,
        "expira": order.payment_expires_at.isoformat(),
        "whatsapp": f"https://wa.me/57{telefono}?text={quote(texto)}",
        "mensaje": texto,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PAGO LIBRE: el cliente pone el monto, sin pedido de por medio
# ─────────────────────────────────────────────────────────────────────────────

publico = APIRouter(prefix="/public/pago-libre", tags=["public"])

#: Freno por IP. No hay nada que robar aquí, pero sí se puede llenar la base.
_libre_por_ip: dict[str, list[float]] = {}
MAX_LIBRES_HORA = 10


class PagoLibreIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    telefono: str = Field(min_length=7, max_length=20)
    monto: int = Field(ge=1000, le=MAX_COBRO)
    concepto: str | None = Field(default=None, max_length=200)
    website: str | None = None  # trampa para bots


@publico.post("")
async def crear_pago_libre(payload: PagoLibreIn, request: Request, db: DBSession) -> dict:
    """Un cobro que el propio cliente arma, sin pedido detrás.

    Sirve para abonos, saldos pendientes y cobros sueltos: "le quedé debiendo
    $30.000 de la peluquería", "quiero abonar a la cuenta". Hasta hoy eso se cerraba
    en efectivo o por transferencia y había que anotarlo a mano.

    **AQUÍ EL MONTO SÍ LO PONE EL CLIENTE, Y NO ES UNA CONTRADICCIÓN.** La regla de
    que el servidor calcula el monto existe para impedir que alguien compre un bulto
    de concentrado por mil pesos: protege un PRECIO que nosotros fijamos. En un pago
    libre no hay producto ni precio que proteger — el cliente declara cuánto quiere
    pagar y paga exactamente eso. Nadie sale perdiendo si pone una cifra baja:
    simplemente abonó menos.

    Lo que sí hace falta es que quede registrado y que Diego se entere, porque un
    abono que nadie ve es un abono que después hay que reconstruir de memoria.
    """
    if payload.website:  # bot
        return {"ok": True}

    if not bold.esta_configurado():
        raise HTTPException(status_code=503, detail="Los pagos en línea no están disponibles.")

    ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "?")
    )
    ahora_s = time.monotonic()
    marcas = [t for t in _libre_por_ip.get(ip, []) if ahora_s - t < 3600]
    if len(marcas) >= MAX_LIBRES_HORA:
        raise HTTPException(status_code=429, detail="Demasiados intentos. Escríbenos por WhatsApp.")
    marcas.append(ahora_s)
    _libre_por_ip[ip] = marcas

    telefono = limpiar(payload.telefono)
    nombre = limpiar(payload.nombre)
    ahora = datetime.now(_TZ_CO)
    cliente = await cliente_por_telefono(
        db, nombre, telefono, "pago_libre", ahora, consentimiento=False
    )

    referencia = bold.nueva_referencia("portal", ahora).replace("BPP-", "BPX-", 1)
    monto = int(payload.monto)
    concepto = (payload.concepto or "Pago / abono").strip()[:200]

    order = PortalOrder(
        customer_id=cliente.id,
        product_name=concepto[:300],
        quantity=1,
        unit_price=Decimal(monto),
        total_amount=Decimal(monto),
        notes=f"Pago libre desde la web · Tel: {telefono}",
        status="received",
        workflow_status="received",
        origen="libre",
        payment_method="bold",
        payment_status="pending",
        order_reference=referencia,
        bold_amount=monto,
        payment_expires_at=ahora + timedelta(minutes=bold.MINUTOS_PARA_PAGAR),
    )
    db.add(order)
    await db.commit()

    log.info("PAGO LIBRE · %s por $%s (%s)", referencia, monto, nombre)
    return {
        "ok": True,
        "referencia": referencia,
        "monto": monto,
        "pagar_en": f"{TIENDA}/pagar/{referencia}",
    }
