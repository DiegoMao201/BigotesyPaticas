"""Antifraude: liberar un pedido marcado y llevar el registro de contracargos.

Diego (8-oct-2026): *"necesito protegerme de todas las maneras contra posibles
fraudes… pero tampoco quiero frenar la página para que no venda"*.

Las dos cosas caben porque el semáforo NO toca la venta. El pago se confirma siempre
y el cliente no ve nada distinto; lo único que cambia es que un puñado de pedidos
—el 0,1 % medido contra 2.730 ventas reales— llegan con una etiqueta que dice
"llama antes de entregar". Aquí está el botón para quitarla cuando esa llamada ya se
hizo, y la libreta donde se anotan los contracargos que lleguen.

POR QUÉ LOS CONTRACARGOS SE ANOTAN A MANO
Porque Bold no los manda. Su webhook tiene cuatro eventos —`SALE_APPROVED`,
`SALE_REJECTED`, `VOID_APPROVED`, `VOID_REJECTED`— y ninguno es de disputa: el aviso
llega por correo. Un contracargo que nadie anota no existe para el sistema, y hay
dos relojes corriendo: **2 días hábiles** para mandar soportes y débito automático
**dentro de los 3 días hábiles** siguientes al aviso.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.deps import CurrentUser, DBSession, require_permission
from app.models.portal import Chargeback, PortalOrder

log = logging.getLogger(__name__)
# LA PROTECCIÓN VA EN EL ROUTER, NO ENDPOINT POR ENDPOINT.
#
# Se desplegó una vez sin esto y los dos GET quedaron PÚBLICOS: cualquiera podía leer
# las referencias de los pedidos marcados, sus montos y las tarjetas enmascaradas.
# `admin_portal` lo hace así —`dependencies` en el APIRouter— y copiar solo el prefijo
# sin copiar el candado fue el error.
#
# Puesto aquí, un endpoint nuevo nace protegido aunque a quien lo escriba se le
# olvide; puesto uno por uno, el que se olvide queda abierto y nadie lo nota.
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_permission("crm:read"))],
)

#: El techo que Bold tolera antes de poder retener saldos. No es un número nuestro:
#: está en su manual de ventas no presenciales.
INDICE_FRAUDE_MAXIMO = 2.5


def _dias_habiles(desde: datetime, dias: int) -> datetime:
    """Suma días hábiles, saltando sábados y domingos.

    Importa que sean hábiles y no corridos: el plazo de Bold para mandar soportes es
    de 2 días **hábiles**, y contar corrido haría que un aviso de viernes pareciera
    vencido el domingo, cuando en realidad vence el martes.
    """
    fecha = desde
    while dias > 0:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5:
            dias -= 1
    return fecha


# ─────────────────────────────────────────────────────────────────────────────
# Liberar un pedido que el semáforo marcó
# ─────────────────────────────────────────────────────────────────────────────

class LiberarPayload(BaseModel):
    #: Qué se hizo para verificar. Obligatorio: si no queda escrito que se llamó, en
    #: una disputa no hay forma de demostrar que se verificó.
    nota: str = Field(min_length=3, max_length=500)


@router.patch(
    "/portal/orders/{order_id}/riesgo",
    dependencies=[Depends(require_permission("crm:write"))],
)
async def liberar_riesgo(
    order_id: uuid.UUID, payload: LiberarPayload, db: DBSession, user: CurrentUser
) -> dict:
    """Marca que un pedido de riesgo ya se verificó y puede despacharse.

    No borra el nivel de riesgo ni las señales: las deja intactas y encima escribe
    quién verificó, cuándo y qué hizo. Borrarlo sería perder justo el dato que
    después permite demostrar diligencia, y también el que permite medir si el
    semáforo acierta o grita de más.
    """
    pedido = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")
    if not pedido.risk_level or pedido.risk_level == "bajo":
        raise HTTPException(400, "Este pedido no está marcado como riesgoso.")

    pedido.risk_cleared_at = datetime.now(UTC)
    pedido.risk_cleared_by = user.full_name or user.email
    pedido.risk_cleared_note = payload.nota.strip()
    await db.commit()

    log.info("ANTIFRAUDE · %s liberado por %s", pedido.order_reference, pedido.risk_cleared_by)
    return {
        "ok": True,
        "risk_level": pedido.risk_level,
        "risk_cleared_at": pedido.risk_cleared_at.isoformat(),
        "risk_cleared_by": pedido.risk_cleared_by,
    }


@router.get("/portal/orders/riesgo/pendientes")
async def pedidos_en_riesgo(db: DBSession) -> list[dict]:
    """Los pedidos marcados que todavía nadie ha verificado.

    Es la lista contra la que se trabaja: si está vacía, no hay nada que decidir.
    """
    filas = (
        await db.execute(
            select(PortalOrder)
            .where(
                PortalOrder.risk_level.in_(("alto", "medio")),
                PortalOrder.risk_cleared_at.is_(None),
                PortalOrder.workflow_status.notin_(("delivered", "cancelled")),
            )
            .order_by(PortalOrder.risk_score.desc(), PortalOrder.created_at.desc())
            .limit(100)
        )
    ).scalars().all()

    return [
        {
            "id": str(o.id),
            "order_reference": o.order_reference,
            "product_name": o.product_name,
            "total": float(o.total_amount or 0),
            "risk_level": o.risk_level,
            "risk_score": o.risk_score,
            "risk_flags": o.risk_flags or [],
            "bold_card_brand": o.bold_card_brand,
            "bold_masked_pan": o.bold_masked_pan,
            "workflow_status": o.workflow_status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in filas
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Contracargos
# ─────────────────────────────────────────────────────────────────────────────

class ContracargoIn(BaseModel):
    order_reference: str | None = Field(default=None, max_length=60)
    bold_payment_id: str | None = None
    amount: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=1000)
    #: Cuándo avisó Bold. Se pide porque el correo puede verse un día después, y el
    #: reloj de los 2 días hábiles corre desde el aviso, no desde que se anotó.
    notified_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)


@router.post("/chargebacks", dependencies=[Depends(require_permission("crm:write"))])
async def registrar_contracargo(payload: ContracargoIn, db: DBSession) -> dict:
    """Anota un contracargo apenas llega el correo de Bold.

    Calcula solo la fecha límite para mandar soportes (2 días hábiles), que es el
    dato que de verdad importa: pasada, ya no hay disputa que pelear.
    """
    aviso = payload.notified_at or datetime.now(UTC)
    cb = Chargeback(
        order_reference=(payload.order_reference or "").strip() or None,
        bold_payment_id=payload.bold_payment_id,
        amount=int(payload.amount),
        reason=payload.reason,
        notified_at=aviso,
        evidence_due_at=_dias_habiles(aviso, 2),
        notes=payload.notes,
    )
    db.add(cb)
    await db.commit()

    # Si el contracargo apunta a un pedido nuestro, se deja ver desde el pedido: es
    # donde alguien lo va a buscar cuando pregunte "¿y este qué pasó?".
    pedido = None
    if cb.order_reference:
        pedido = (
            await db.execute(
                select(PortalOrder).where(PortalOrder.order_reference == cb.order_reference)
            )
        ).scalar_one_or_none()

    log.warning("ANTIFRAUDE · CONTRACARGO de $%s sobre %s", cb.amount, cb.order_reference)
    return {
        "ok": True,
        "id": str(cb.id),
        "evidence_due_at": cb.evidence_due_at.isoformat(),
        # Lo que hay en el expediente HOY. Si viene vacío, la disputa está perdida y
        # es mejor saberlo ahora que dos días después.
        "evidencia_disponible": {
            "entregado_a": pedido.delivered_to_name if pedido else None,
            "documento": pedido.delivered_to_doc if pedido else None,
            "foto": pedido.delivery_evidence_url if pedido else None,
            "entregado_el": pedido.delivered_at.isoformat()
            if pedido and pedido.delivered_at else None,
            "verificado_por": pedido.risk_cleared_by if pedido else None,
        } if pedido else None,
    }


class ContracargoUpdate(BaseModel):
    outcome: str | None = Field(default=None, pattern="^(pendiente|ganado|perdido)$")
    evidence_sent_at: datetime | None = None
    evidence_summary: str | None = Field(default=None, max_length=4000)
    notes: str | None = Field(default=None, max_length=2000)


@router.patch("/chargebacks/{cb_id}", dependencies=[Depends(require_permission("crm:write"))])
async def actualizar_contracargo(
    cb_id: uuid.UUID, payload: ContracargoUpdate, db: DBSession
) -> dict:
    cb = (await db.execute(select(Chargeback).where(Chargeback.id == cb_id))).scalar_one_or_none()
    if not cb:
        raise HTTPException(404, "Contracargo no encontrado")

    if payload.outcome:
        cb.outcome = payload.outcome
        if payload.outcome != "pendiente":
            cb.resolved_at = datetime.now(UTC)
    for campo in ("evidence_sent_at", "evidence_summary", "notes"):
        if (valor := getattr(payload, campo)) is not None:
            setattr(cb, campo, valor)
    await db.commit()
    return {"ok": True, "outcome": cb.outcome}


@router.get("/chargebacks")
async def listar_contracargos(db: DBSession, dias: int = Query(default=180, ge=1, le=1095)) -> dict:
    """Los contracargos y el índice de fraude contra el techo de Bold.

    El índice es lo que decide si Bold puede empezar a retener saldos: su manual fija
    el máximo en 2,5 %. Sin medirlo no hay forma de saber si vamos bien, y cuando se
    pasa ya es tarde.
    """
    desde = datetime.now(UTC) - timedelta(days=dias)
    filas = (
        await db.execute(
            select(Chargeback).where(Chargeback.notified_at >= desde)
            .order_by(Chargeback.notified_at.desc())
        )
    ).scalars().all()

    # El denominador son los pagos en línea del mismo periodo: el índice de fraude se
    # mide sobre lo que se cobró por ese canal, no sobre toda la tienda.
    pagados = int(
        (await db.execute(
            select(func.count()).select_from(PortalOrder).where(
                PortalOrder.payment_status == "paid",
                PortalOrder.paid_at >= desde,
            )
        )).scalar() or 0
    )
    perdidos = [c for c in filas if c.outcome == "perdido"]
    indice = round(100.0 * len(filas) / pagados, 2) if pagados else 0.0

    return {
        "dias": dias,
        "pagos_en_linea": pagados,
        "contracargos": len(filas),
        "perdidos": len(perdidos),
        "monto_perdido": sum(c.amount for c in perdidos),
        "indice_fraude": indice,
        "indice_maximo_bold": INDICE_FRAUDE_MAXIMO,
        "por_encima_del_limite": indice > INDICE_FRAUDE_MAXIMO,
        "items": [
            {
                "id": str(c.id),
                "order_reference": c.order_reference,
                "amount": c.amount,
                "reason": c.reason,
                "outcome": c.outcome,
                "notified_at": c.notified_at.isoformat(),
                "evidence_due_at": c.evidence_due_at.isoformat() if c.evidence_due_at else None,
                "evidence_sent_at": c.evidence_sent_at.isoformat() if c.evidence_sent_at else None,
                "vencido": bool(
                    c.evidence_due_at
                    and not c.evidence_sent_at
                    and c.evidence_due_at < datetime.now(UTC)
                    and c.outcome == "pendiente"
                ),
            }
            for c in filas
        ],
    }
