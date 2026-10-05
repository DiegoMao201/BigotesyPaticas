"""Webhook de Bold y consulta de estado del pago. Sirve a la tienda y al portal.

Diego (4-oct-2026): *"hablamos el mismo idioma en web y en el portal"*. Por eso no
hay dos webhooks ni dos consultas de estado: hay uno de cada cosa, y el canal se
distingue por el prefijo de la referencia (`BPW-` tienda, `BPP-` portal).

LA REGLA QUE SOSTIENE TODO ESTO
-------------------------------
Un pedido pasa a pagado **solo** desde este webhook con firma válida, o desde la
conciliación servidor contra servidor. Nunca desde un parámetro de la URL a la que
Bold devuelve al cliente: eso es texto que cualquiera escribe a mano en la barra de
direcciones. La página de confirmación usa ese parámetro únicamente para saber QUÉ
pedido preguntar, y la respuesta la da `GET /payments/{referencia}/estado`, que lee
la base.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Request, Response, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.deps import DBSession
from app.models.portal import PaymentEvent, PortalOrder
from app.services import bold

log = logging.getLogger(__name__)
router = APIRouter(tags=["pagos"])

#: Más de esto no es un webhook de Bold, es alguien probando suerte.
MAX_CUERPO = 256 * 1024


@router.post("/webhooks/bold", status_code=status.HTTP_200_OK)
async def webhook_bold(request: Request, db: DBSession, tareas: BackgroundTasks) -> Response:
    """Recibe los avisos de pago de Bold.

    Es público porque tiene que serlo —Bold no puede traer una sesión nuestra— y se
    autentica con la firma. Cuatro cosas lo hacen seguro, y las cuatro importan:

    **1. El cuerpo se lee CRUDO, en bytes, antes de tocar el JSON.** Si se dejara
    que FastAPI lo deserializara y luego se volviera a serializar, cambiarían los
    espacios y el orden de las llaves, y la firma no coincidiría jamás. Es el fallo
    clásico de esta validación y el motivo de que aquí no haya un modelo Pydantic
    en la firma de la función.

    **2. Idempotencia en la base, no en el código.** Bold reintenta hasta cinco
    veces (15 min, 1 h, 4 h, 8 h, 24 h) y eso es funcionamiento normal. El
    `INSERT ... ON CONFLICT DO NOTHING` sobre `payment_events.bold_payment_id`
    decide: si no insertó, ese pago ya se procesó y salimos. Un `SELECT` previo no
    serviría, porque dos reintentos simultáneos pasarían los dos.

    **3. Se responde 200 enseguida y el trabajo va a segundo plano.** Bold da menos
    de dos segundos; si tardamos más lo cuenta como fallo y reintenta, y acabamos
    procesando en paralelo lo mismo.

    **4. Una firma inválida se GUARDA y se responde 401**, sin tocar el pedido. Sin
    ese registro, depurar una firma que no cuadra obligaría a reproducir el pago.
    """
    raw = await request.body()
    if len(raw) > MAX_CUERPO:
        log.warning("BOLD · webhook descartado por tamaño: %s bytes", len(raw))
        return Response(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    firma = request.headers.get("x-bold-signature", "")
    valido, con_llave = bold.verificar_webhook(raw, firma)

    try:
        cuerpo = await request.json()
    except Exception:
        cuerpo = {}
    if not isinstance(cuerpo, dict):
        cuerpo = {}

    datos = cuerpo.get("data") or {}
    tipo = str(cuerpo.get("type") or "DESCONOCIDO")
    payment_id = str(datos.get("payment_id") or cuerpo.get("id") or "")
    referencia = str((datos.get("metadata") or {}).get("reference") or "")
    monto = (datos.get("amount") or {}).get("total")
    monto = int(monto) if isinstance(monto, (int, float)) and monto > 0 else None

    if not valido:
        # Se registra el intento aunque no haya payment_id: sin una marca, un
        # atacante probando firmas no deja rastro.
        log.warning(
            "BOLD · firma INVÁLIDA · tipo=%s ref=%s firma=%s",
            tipo, referencia, bold.enmascarar(firma),
        )
        await _registrar_evento(
            db, payment_id or f"invalida-{datetime.now(UTC).timestamp()}",
            tipo, referencia, cuerpo, False, monto, error="firma inválida",
        )
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    if not payment_id:
        log.error("BOLD · webhook válido pero sin payment_id · tipo=%s", tipo)
        return Response(status_code=status.HTTP_200_OK)

    nuevo = await _registrar_evento(db, payment_id, tipo, referencia, cuerpo, True, monto)
    if not nuevo:
        # Reintento de algo ya procesado. No es un error: es Bold haciendo su
        # trabajo. 200 para que deje de reintentar.
        log.info("BOLD · reintento de %s ya procesado (%s)", payment_id, tipo)
        return Response(status_code=status.HTTP_200_OK)

    log.info("BOLD · evento %s · ref=%s · firma válida con '%s'", tipo, referencia, con_llave)
    tareas.add_task(_procesar, payment_id, tipo, referencia, monto)
    return Response(status_code=status.HTTP_200_OK)


async def _registrar_evento(
    db: DBSession,
    payment_id: str,
    tipo: str,
    referencia: str,
    cuerpo: dict,
    firma_valida: bool,
    monto: int | None,
    error: str | None = None,
) -> bool:
    """Deja el evento en la bitácora. Devuelve True si es la PRIMERA vez.

    El `ON CONFLICT DO NOTHING` sobre el índice único es el candado de idempotencia
    de toda la integración: es la base de datos la que arbitra, así que resiste dos
    reintentos simultáneos, que es donde falla cualquier comprobación previa.
    """
    sent = (
        pg_insert(PaymentEvent.__table__)
        .values(
            bold_payment_id=payment_id,
            event_type=tipo,
            order_reference=referencia or None,
            raw_payload=cuerpo,
            signature_valid=firma_valida,
            amount=monto,
            error=error,
            received_at=datetime.now(UTC),
        )
        .on_conflict_do_nothing(index_elements=["bold_payment_id"])
        .returning(PaymentEvent.__table__.c.id)
    )
    fila = (await db.execute(sent)).first()
    await db.commit()
    return fila is not None


async def _procesar(payment_id: str, tipo: str, referencia: str, monto: int | None) -> None:
    """Aplica el evento al pedido. Corre en segundo plano, con su propia sesión.

    Va aparte y no dentro del endpoint porque la sesión de la petición ya se cerró
    cuando esto corre: una tarea de fondo que reutilice la sesión del request falla
    de forma intermitente, que es la peor manera de fallar.
    """
    from app.db import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        pedido = (
            await db.execute(
                select(PortalOrder).where(PortalOrder.order_reference == referencia)
            )
        ).scalar_one_or_none()

        if pedido is None:
            log.error("BOLD · %s: no existe pedido con referencia %s", tipo, referencia)
            await _cerrar_evento(db, payment_id, error="pedido inexistente")
            return

        if tipo == "SALE_APPROVED":
            await _aprobar(db, pedido, payment_id, monto)
        elif tipo == "SALE_REJECTED":
            await _marcar(db, pedido, "failed", payment_id)
            log.info("BOLD · pago rechazado · %s", referencia)
            await _cerrar_evento(db, payment_id)
        elif tipo == "VOID_APPROVED":
            await _marcar(db, pedido, "voided", payment_id)
            # Puede ser un pedido YA DESPACHADO: esto no es una notificación más.
            log.warning("BOLD · ANULACIÓN de %s — revisar si ya se entregó", referencia)
            await _cerrar_evento(db, payment_id)
        else:
            log.info("BOLD · evento %s sin acción definida (%s)", tipo, referencia)
            await _cerrar_evento(db, payment_id)


async def _aprobar(db: DBSession, pedido: PortalOrder, payment_id: str, monto: int | None) -> None:
    """Confirma el pago. **El monto manda.**

    Si lo que cobró Bold no es exactamente lo que firmamos, NO se confirma. Puede ser
    un intento de manipulación o un error nuestro de cálculo, y en los dos casos lo
    correcto es parar y que lo mire una persona: confirmar un pedido cobrando de
    menos es perder dinero en silencio.
    """
    if monto is not None and pedido.bold_amount is not None and monto != pedido.bold_amount:
        log.error(
            "BOLD · DISCREPANCIA en %s · cobrado=%s esperado=%s · NO se confirma",
            pedido.order_reference, monto, pedido.bold_amount,
        )
        await _cerrar_evento(
            db, payment_id,
            error=f"monto no coincide: cobrado={monto} esperado={pedido.bold_amount}",
        )
        return

    if pedido.payment_status == "paid":
        # Ya estaba pagado: la conciliación se nos adelantó. Nada que hacer.
        await _cerrar_evento(db, payment_id)
        return

    pedido.payment_status = "paid"
    pedido.bold_payment_id = payment_id
    pedido.paid_at = datetime.now(UTC)
    await db.commit()
    log.info("BOLD · PAGADO %s · %s pesos", pedido.order_reference, monto)

    # La cadena de siempre: puente a sales, puntos, referidos y avisos. Se reutiliza
    # tal cual la del portal, que ya es idempotente, en vez de escribir una paralela.
    from app.services.portal_order_actions import credit_loyalty_points

    try:
        await credit_loyalty_points(pedido, db)
        await db.commit()
    except Exception:
        # Un fallo acreditando puntos NO puede desandar un pago cobrado. Se registra
        # y se sigue: el pedido está pagado y eso es lo que no se puede perder.
        log.exception("BOLD · pago OK pero fallaron los puntos de %s", pedido.order_reference)

    await _cerrar_evento(db, payment_id)


async def _marcar(db: DBSession, pedido: PortalOrder, estado: str, payment_id: str) -> None:
    """Estados que no son 'pagado'. Nunca pisa un pago ya confirmado.

    La guarda es la máquina de estados en su forma mínima: un pedido pagado no
    vuelve atrás porque llegue un evento desordenado, y los eventos llegan
    desordenados — los reintentos de Bold pueden tardar hasta 24 horas.
    """
    if pedido.payment_status == "paid":
        log.warning(
            "BOLD · se ignora '%s' sobre %s, que ya está pagado",
            estado, pedido.order_reference,
        )
        return
    pedido.payment_status = estado
    pedido.bold_payment_id = pedido.bold_payment_id or payment_id
    await db.commit()


async def _cerrar_evento(db: DBSession, payment_id: str, error: str | None = None) -> None:
    """Marca el evento como procesado. Lo que quede sin `processed_at` es lo que
    se quedó a medias, y es justo lo que hay que poder listar después."""
    evento = (
        await db.execute(
            select(PaymentEvent).where(PaymentEvent.bold_payment_id == payment_id)
        )
    ).scalar_one_or_none()
    if evento is not None:
        evento.processed_at = datetime.now(UTC)
        if error:
            evento.error = error
        await db.commit()


@router.get("/payments/{referencia}/estado")
async def estado_pago(referencia: str, db: DBSession) -> dict:
    """Estado real del pago, para la página de confirmación.

    Devuelve lo MÍNIMO. La referencia viaja en la URL y en el enlace de pago, así
    que hay que asumir que alguien que no es el dueño puede llegar a verla: aquí no
    salen teléfono, dirección ni datos del cliente.
    """
    pedido = (
        await db.execute(select(PortalOrder).where(PortalOrder.order_reference == referencia))
    ).scalar_one_or_none()

    if pedido is None:
        return {"encontrado": False, "estado": "desconocido"}

    return {
        "encontrado": True,
        "referencia": pedido.order_reference,
        "estado": pedido.payment_status or "pending",
        "metodo": pedido.payment_method,
        "total": int(pedido.total_amount or 0),
        "pagado_en": pedido.paid_at.isoformat() if pedido.paid_at else None,
        # Para que la página sepa si seguir preguntando o dejar de hacerlo.
        "definitivo": (pedido.payment_status or "pending") != "pending",
    }
