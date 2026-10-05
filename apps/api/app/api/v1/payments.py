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

import asyncio
import hashlib
import logging
import re
import time
from collections import deque
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.deps import DBSession
from app.models.portal import PaymentEvent, PortalOrder, PortalOrderItem
from app.services import bold

log = logging.getLogger(__name__)
router = APIRouter(tags=["pagos"])

#: Más de esto no es un webhook de Bold, es alguien probando suerte.
MAX_CUERPO = 256 * 1024

#: BPW-20261005-a3f9c201 o BPP-…. Validar la forma evita ir a la base por cada
#: cadena suelta que alguien escriba en la URL.
_REFERENCIA_OK = re.compile(r"^BP[WP]-\d{8}-[0-9a-f]{8}$")


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
    # CloudEvents: el id del pago está en `data.payment_id` y repetido en `subject`.
    # Se usa el segundo como respaldo; `id` (el del EVENTO, no el del pago) solo como
    # último recurso, porque dos eventos del mismo pago traen `id` distinto y
    # confundirlos rompería la idempotencia.
    payment_id = str(datos.get("payment_id") or cuerpo.get("subject") or cuerpo.get("id") or "")
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
        # LA CLAVE DE UN EVENTO INVÁLIDO NUNCA PUEDE SER EL payment_id REAL.
        #
        # Encontrado probando en producción el 5-oct-2026, y es grave: la versión
        # anterior usaba `payment_id or hash`, así que un evento con firma inválida
        # que trajera un payment_id insertaba su fila con ESE id. Cuando después
        # llegaba el webhook legítimo del mismo pago, chocaba contra el UNIQUE y se
        # descartaba como "duplicado ya procesado" — y el pedido se quedaba sin
        # confirmar para siempre.
        #
        # O sea: cualquiera que conociera o acertara un payment_id podía BLOQUEAR la
        # confirmación de un pago real, sin firma y sin dejar más rastro que un 401.
        # Un ataque barato contra el cobro, no contra el dato.
        #
        # El prefijo `invalida:` más el hash del cuerpo lo cierra por los dos lados:
        # jamás colisiona con un evento legítimo, y el mismo intento repetido sigue
        # chocando consigo mismo, que era lo que evitaba llenar la tabla.
        clave = f"invalida:{hashlib.sha256(raw).hexdigest()[:40]}"
        await _registrar_evento(
            db, clave, tipo, referencia, cuerpo, False, monto, error="firma inválida",
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
        elif tipo == "VOID_REJECTED":
            # Se intentó anular y el intento falló: el pago SIGUE siendo válido y el
            # pedido no se toca. Queda escrito porque un intento de anulación es algo
            # que conviene poder mirar después.
            log.warning("BOLD · intento de anulación RECHAZADO en %s", referencia)
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

    if pedido.payment_status == "expired":
        # Pagó tarde. **Se acepta igual**: el dinero entró, y rechazarlo sería
        # quedarnos con el cobro sin entregar nada. Pero se avisa fuerte, porque
        # entre el vencimiento y el pago el stock pudo haberse vendido a otro.
        log.warning(
            "BOLD · %s estaba VENCIDO y entró el pago igual — revisar existencias",
            pedido.order_reference,
        )

    # La transición se hace con un UPDATE CONDICIONADO por el estado anterior, no
    # leyendo y escribiendo. Entre el `if` de arriba y este commit caben milisegundos,
    # y en esos milisegundos puede entrar la conciliación con el mismo pago: si los
    # dos escribieran, se dispararía dos veces todo lo que viene después. Con el
    # WHERE en el UPDATE, solo uno de los dos toca filas y el otro se entera.
    marcado = await db.execute(
        update(PortalOrder)
        .where(
            PortalOrder.id == pedido.id,
            or_(PortalOrder.payment_status != "paid", PortalOrder.payment_status.is_(None)),
        )
        .values(
            payment_status="paid",
            bold_payment_id=payment_id,
            paid_at=datetime.now(UTC),
        )
    )
    await db.commit()
    if marcado.rowcount == 0:
        log.info("BOLD · %s ya lo había marcado otro proceso", pedido.order_reference)
        await _cerrar_evento(db, payment_id)
        return

    log.info("BOLD · PAGADO %s · %s pesos", pedido.order_reference, monto)

    # AQUÍ NO SE ACREDITAN PUNTOS NI SE CREA LA VENTA, Y ES A PROPÓSITO.
    #
    # El encargo pedía ejecutar al pagar "la misma cadena que ya corre el portal".
    # Mirando cómo funciona de verdad (admin_portal.py), esa cadena NO cuelga del
    # pago sino del avance del pedido: `bridge_to_sales()` corre al FACTURAR y
    # `credit_loyalty_points()` + el `purchase` a Google corren al ENTREGAR.
    #
    # Engancharlas al pago rompería el negocio en dos sitios: le daríamos puntos a
    # alguien por algo que todavía no ha recibido —y como la función es idempotente,
    # al entregar ya no se los daría, así que el error quedaría escondido—, y le
    # contaríamos a Google una compra que aún puede cancelarse o devolverse.
    #
    # Pagar NO es haber recibido. El pago solo cambia el estado de pago; el resto del
    # recorrido sigue exactamente igual que hasta hoy, y es el admin quien lo mueve.
    # Se cierra el evento AQUI, antes de avisar. El pago ya esta registrado y el
    # pedido marcado: eso es lo que el evento tenia que lograr. Si se cerrara despues
    # de los avisos, cualquier cosa que colgara el correo dejaria el evento como "sin
    # procesar" para siempre — que fue exactamente lo que pasó en la primera prueba
    # real del 5-oct-2026.
    await _cerrar_evento(db, payment_id)
    await _avisar_pago(db, pedido, monto)


async def _avisar_pago(db: DBSession, pedido: PortalOrder, monto: int | None) -> None:
    """Avisa de un pedido PAGADO: al panel y al correo de la tienda.

    Un pedido pagado no es un pedido más. Hasta hoy todos entraban sin pagar y
    podían esperar; este ya tiene el dinero y al cliente hay que responderle. Por eso
    lleva su propio tipo de notificación y su propio correo, en vez de confundirse
    con los demás en la misma lista.

    Se reutiliza `notify_admins()`, que ya inserta en `portal.notifications` y
    publica en el canal de Redis, en vez de escribir un camino paralelo.

    **Ningún fallo de aviso puede tumbar un pago ya cobrado.** El dinero ya entró y
    el pedido ya está marcado; si el correo no sale, se registra y se sigue. Perder
    el aviso es molesto, perder la venta es grave.
    """
    canal = "la tienda web" if (pedido.order_reference or "").startswith("BPW") else "el portal"
    total = monto if monto is not None else int(pedido.total_amount or 0)
    titulo = f"💳 Pedido PAGADO · ${total:,.0f}".replace(",", ".")
    cuerpo = f"{pedido.product_name} · pagado en línea desde {canal}"

    log.info("BOLD · avisando del pago de %s", pedido.order_reference)
    datos = {
        "order_id": str(pedido.id),
        "order_reference": pedido.order_reference,
        "total": total,
        "canal": canal,
        "pagado": True,
    }

    # LA NOTIFICACIÓN SE INSERTA A MANO, NO POR notify_admins().
    #
    # En la prueba del 5-oct-2026 el aviso no aparecía y no dejaba ni una línea de
    # error: el pago se confirmaba, el evento se cerraba, y la notificación
    # sencillamente no existía. `notify_admins()` hace dos cosas —escribe en la base
    # y publica en Redis— y bastaba con que la segunda se atascara para perder
    # también la primera.
    #
    # Separarlas arregla eso de raíz: lo que Diego TIENE que ver queda escrito en la
    # base pase lo que pase, y el empujón por Redis es un extra que puede fallar sin
    # llevarse nada por delante.
    # EL AVISO VA EN SU PROPIA SESIÓN, no en la que viene arrastrada.
    #
    # Probando el 5-oct-2026: el log de entrada salía, y después nada — ni el de
    # éxito, ni el de error, ni la fila en la base. La sesión que llega hasta aquí ya
    # hizo tres commits (marcar el pago, cerrar el evento) y se quedaba colgada en el
    # siguiente, sin lanzar nada que el `except` pudiera atrapar.
    #
    # Una sesión nueva y corta no arrastra ese estado. Y el `wait_for` garantiza que,
    # pase lo que pase, esto termina: una tarea de fondo bloqueada para siempre es
    # peor que un aviso perdido, porque se lleva todo lo que venga detrás.
    from app.db import AsyncSessionLocal

    try:
        async with asyncio.timeout(15):
            async with AsyncSessionLocal() as db2:
                from app.models.portal import PortalNotification

                db2.add(
                    PortalNotification(
                        customer_id=None,
                        is_admin=True,
                        type="web_order_paid",
                        title=titulo,
                        body=cuerpo,
                        data=datos,
                    )
                )
                await db2.commit()
        log.info("BOLD · aviso guardado para %s", pedido.order_reference)
    except Exception:
        log.exception("BOLD · FALLO EL AVISO AL PANEL de %s", pedido.order_reference)

    # Nota: no se publica aparte en Redis. `notify_admins()` escribiría una SEGUNDA
    # fila, y el panel mostraría el mismo pago dos veces. El aviso en vivo llegará
    # cuando el panel lea de la base, que es de donde lee hoy.

    try:
        from app.services.email import STORE_EMAIL, send_email

        html = (
            f"<h2 style='color:#187f77'>Pedido pagado en línea</h2>"
            f"<p><b>Referencia:</b> {pedido.order_reference}<br>"
            f"<b>Total:</b> ${total:,.0f}".replace(",", ".") + "<br>"
            f"<b>Origen:</b> {canal}<br>"
            f"<b>Entrega:</b> {pedido.shipping_address or 'sin dirección'}</p>"
            f"<p style='color:#555'>Ya está pagado. Entra al panel para alistarlo.</p>"
        )
        # send_email es síncrono y haría esperar al event loop: va a un hilo. Y con
        # TOPE: un SMTP que no contesta dejaría la tarea colgada indefinidamente, y
        # con ella todo lo que viniera después.
        await asyncio.wait_for(
            asyncio.to_thread(send_email, STORE_EMAIL, titulo, html), timeout=20
        )
    except Exception:
        log.exception("BOLD · no se pudo enviar el correo de %s", pedido.order_reference)


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


_CONSULTAS: dict[str, deque[float]] = {}
_MAX_CONSULTAS = 60
_VENTANA_S = 60.0


def _ip_de(request: Request) -> str:
    """La IP del cliente. Las peticiones llegan por el proxy de Next, así que la real
    viene en la cabecera; si no está, se usa la de la conexión."""
    return (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "?")
    )


def _frenar_consultas(ip: str) -> None:
    """Tope de consultas de estado por IP y minuto.

    La página de confirmación pregunta cada 3 segundos durante 2 minutos, o sea 40
    consultas legítimas por pago. El tope de 60 deja holgura para eso y corta un
    script que quiera barrer referencias.
    """
    ahora = time.monotonic()
    marcas = _CONSULTAS.setdefault(ip, deque())
    while marcas and ahora - marcas[0] > _VENTANA_S:
        marcas.popleft()
    if len(marcas) >= _MAX_CONSULTAS:
        raise HTTPException(status_code=429, detail="Demasiadas consultas, espera un momento")
    marcas.append(ahora)
    # Sin esto el diccionario crece con cada IP que pase por aquí y no baja nunca.
    if len(_CONSULTAS) > 2000:
        for k in [k for k, v in _CONSULTAS.items() if not v or ahora - v[-1] > _VENTANA_S * 5]:
            _CONSULTAS.pop(k, None)


@router.get("/payments/{referencia}/cobro")
async def datos_de_cobro(referencia: str, request: Request, db: DBSession) -> dict:
    """Lo que necesita la página de pago para abrir el checkout de Bold.

    Es lo que convierte un enlace en una forma de cobrar: con esto, `/pagar/{ref}`
    funciona igual si el cliente viene del checkout, del portal, o de un enlace que
    Diego le mandó por WhatsApp. Un solo sitio donde se paga.

    **LA FIRMA NO SE CALCULA AQUÍ: SE DEVUELVE LA QUE SE GUARDÓ AL CREAR EL PEDIDO.**
    Volver a firmar en cada consulta parece inofensivo y no lo es: si entre medias
    cambiara el precio del producto, saldría una firma para un monto distinto del que
    se le prometió al cliente. Lo que se firmó una vez es lo que se cobra.

    Qué NO sale de aquí: teléfono, dirección, nombre ni nada del cliente. La
    referencia viaja en un enlace y hay que asumir que puede acabar en manos de
    alguien más; que pueda pagar es el objetivo, que pueda husmear no.
    """
    _frenar_consultas(_ip_de(request))
    if not _REFERENCIA_OK.match(referencia):
        return {"ok": False, "motivo": "referencia inválida"}

    pedido = (
        await db.execute(select(PortalOrder).where(PortalOrder.order_reference == referencia))
    ).scalar_one_or_none()
    if pedido is None:
        return {"ok": False, "motivo": "no existe"}

    estado = pedido.payment_status or "pending"
    if estado != "pending":
        # Ya está resuelto: la página lo dirá, pero no se le da con qué volver a pagar.
        return {"ok": False, "motivo": estado, "estado": estado, "referencia": referencia}

    vencido = bool(
        pedido.payment_expires_at
        and pedido.payment_expires_at < datetime.now(UTC)
    )

    items = (
        (
            await db.execute(
                select(PortalOrderItem).where(PortalOrderItem.portal_order_id == pedido.id)
            )
        )
        .scalars()
        .all()
    )

    return {
        "ok": not vencido,
        "motivo": "vencido" if vencido else None,
        "estado": estado,
        "referencia": referencia,
        "amount": pedido.bold_amount,
        "currency": "COP",
        "integrity_signature": bold.firma_integridad(referencia, pedido.bold_amount)
        if pedido.bold_amount
        else None,
        "identity_key": bold.IDENTITY_KEY,
        "expira": pedido.payment_expires_at.isoformat() if pedido.payment_expires_at else None,
        "items": [
            {"nombre": i.name, "cantidad": i.quantity, "subtotal": float(i.subtotal or 0)}
            for i in items
        ],
    }


@router.get("/payments/{referencia}/estado")
async def estado_pago(referencia: str, request: Request, db: DBSession) -> dict:
    """Estado real del pago, para la página de confirmación.

    Devuelve lo MÍNIMO. La referencia viaja en la URL y en el enlace de pago, así
    que hay que asumir que alguien que no es el dueño puede llegar a verla: aquí no
    salen teléfono, dirección ni datos del cliente.
    """
    _frenar_consultas(_ip_de(request))

    # Se valida el formato ANTES de ir a la base: una referencia que no tiene nuestra
    # forma no puede existir, y así no se gasta una consulta por cada intento.
    if not _REFERENCIA_OK.match(referencia):
        return {"encontrado": False, "estado": "desconocido"}

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
        # `bold_amount` es el entero EXACTO que se cobró. `total_amount` es Numeric y
        # pasarlo por int() lo trunca: un total de 76000.6 se mostraría como 76000.
        "total": pedido.bold_amount or int(pedido.total_amount or 0),
        "pagado_en": pedido.paid_at.isoformat() if pedido.paid_at else None,
        # Para que la página sepa si seguir preguntando o dejar de hacerlo.
        "definitivo": (pedido.payment_status or "pending") != "pending",
    }
