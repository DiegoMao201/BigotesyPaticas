"""Red de seguridad: busca pagos que Bold cobró y de los que nunca nos enteramos.

**Esta es la diferencia entre perder una venta pagada y no perderla.** Los webhooks
se pierden: por un despliegue justo en ese segundo, por una caída de red, por un
proxy que corta. Sin esto, un cliente que pagó se queda esperando un pedido que
nadie vio, y el dinero ya está cobrado.

Cada ciclo pregunta a Bold, servidor contra servidor, por los pedidos que llevan
rato esperando. Y lo hace **con la misma función de confirmación que usa el
webhook**, no con una copia: si fueran dos caminos distintos, tarde o temprano uno
de los dos tendría un arreglo que al otro le falta.

Es idempotente de punta a punta. Si el webhook llega más tarde encuentra el pago ya
registrado en `payment_events`, no inserta y se va.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select

from app.models.portal import PortalOrder
from app.services import bold

log = logging.getLogger(__name__)

#: Cada cuánto se revisa. Diez minutos: suficiente para que un cliente no se
#: desespere y poco para no castigar la API de Bold con preguntas inútiles.
INTERVALO_S = 600

#: No se pregunta por un pedido recién creado. Antes de este margen el cliente
#: todavía está escribiendo la tarjeta y Bold aún no tiene nada que contar.
EDAD_MINIMA_MIN = 5

#: Pasado esto sin pago, el pedido se da por vencido.
VENCIMIENTO_MIN = 30

#: Tope por ciclo. Si un día hay cientos de pendientes, es mejor repartirlos en
#: varias vueltas que disparar cientos de peticiones de golpe.
MAX_POR_CICLO = 40


async def conciliar_una_vez() -> dict:
    """Una pasada. Devuelve el recuento, para poder dispararla a mano y ver qué hizo."""
    from app.api.v1.payments import _aprobar, _registrar_evento
    from app.db import AsyncSessionLocal

    if not bold.esta_configurado():
        return {"revisados": 0, "nota": "Bold sin configurar"}

    ahora = datetime.now(UTC)
    limite = ahora - timedelta(minutes=EDAD_MINIMA_MIN)
    resumen = {"revisados": 0, "aprobados": 0, "vencidos": 0, "rechazados": 0, "errores": 0}

    async with AsyncSessionLocal() as db:
        pendientes = (
            (
                await db.execute(
                    select(PortalOrder)
                    .where(
                        PortalOrder.payment_status == "pending",
                        PortalOrder.payment_method == "bold",
                        PortalOrder.order_reference.is_not(None),
                        PortalOrder.created_at < limite,
                    )
                    .order_by(PortalOrder.created_at)
                    .limit(MAX_POR_CICLO)
                )
            )
            .scalars()
            .all()
        )

        for pedido in pendientes:
            resumen["revisados"] += 1
            try:
                voucher = await bold.consultar_voucher(pedido.order_reference or "")
            except Exception:
                # Que Bold no conteste no puede tumbar el ciclo: el pedido sigue
                # pendiente y se vuelve a intentar en diez minutos.
                log.exception("BOLD · conciliación falló al consultar %s", pedido.order_reference)
                resumen["errores"] += 1
                continue

            estado = str(voucher.get("estado", "")).upper()

            if estado == "APPROVED":
                payment_id = str(voucher.get("payment_id") or f"conciliado:{pedido.order_reference}")
                monto = voucher.get("monto")
                monto = int(monto) if isinstance(monto, (int, float)) and monto > 0 else None

                # Se deja constancia ANTES de confirmar, igual que hace el webhook.
                # Si no insertó, es que el webhook ya lo trajo: no se toca nada.
                nuevo = await _registrar_evento(
                    db, payment_id, "SALE_APPROVED_CONCILIADO",
                    pedido.order_reference or "", voucher.get("crudo") or {}, True, monto,
                )
                if not nuevo:
                    continue

                log.warning(
                    "BOLD · CONCILIACIÓN rescató %s: estaba pagado y el webhook nunca llegó",
                    pedido.order_reference,
                )
                await _aprobar(db, pedido, payment_id, monto)
                resumen["aprobados"] += 1

            elif estado in {"REJECTED", "FAILED"}:
                pedido.payment_status = "failed"
                await db.commit()
                resumen["rechazados"] += 1

            elif estado in {"NO_TRANSACTION_FOUND", "ERROR"}:
                # Nunca hubo intento de pago. Solo se vence por tiempo; mientras
                # tanto el cliente todavía puede volver y pagar el mismo enlace.
                creado = pedido.created_at
                if creado and creado.tzinfo is None:
                    creado = creado.replace(tzinfo=UTC)
                if creado and (ahora - creado) > timedelta(minutes=VENCIMIENTO_MIN):
                    pedido.payment_status = "expired"
                    await db.commit()
                    resumen["vencidos"] += 1

            # PROCESSING y PENDING (PSE) se dejan como están: siguen en curso.

    if resumen["aprobados"] or resumen["vencidos"] or resumen["rechazados"]:
        log.info("BOLD · conciliación: %s", resumen)
    return resumen


async def bucle_conciliacion() -> None:
    """Corre para siempre. Se lanza al arrancar la API.

    Nunca se deja morir: cualquier excepción se registra y el bucle sigue. Una tarea
    de fondo que muere en silencio es peor que no tenerla, porque todo el mundo cree
    que está puesta la red de seguridad.
    """
    log.info("BOLD · conciliación activa, cada %s s", INTERVALO_S)
    # Un respiro al arrancar: durante el despliegue la base y la red aún se asientan.
    await asyncio.sleep(60)
    while True:
        try:
            await conciliar_una_vez()
        except asyncio.CancelledError:
            log.info("BOLD · conciliación detenida")
            raise
        except Exception:
            log.exception("BOLD · la conciliación falló; se reintenta en el próximo ciclo")
        await asyncio.sleep(INTERVALO_S)
