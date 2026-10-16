"""Guías de envío nacional desde el admin (16-oct-2026).

Diego: *"aprobamos la venta y le damos aprobada y así se genera la guía que le
llega al cliente, la guía al proveedor para la recogida o nosotros llevamos el
paquete al punto donde nos digan en Pereira y Dosquebradas"*.

Lo que hace cada pieza:

- **Generar guía**: se dispara sola al FACTURAR un pedido nacional pagado (es el
  momento en que la venta existe y el stock ya se descontó), y también a mano con
  un botón, por si falló o si hubo que cancelarla y volverla a sacar. Descuenta
  saldo de la cuenta de Envia.
- **Etiqueta**: el PDF que va pegado al paquete. Envia lo deja en una URL pública.
- **Rastreo**: pregunta a Envia por dónde va y guarda el estado.
- **Recogida**: pide que la transportadora pase por el local, con fecha y franja.
- **Puntos de entrega**: las oficinas de la transportadora en Dosquebradas y
  Pereira donde se puede dejar el paquete si no se quiere esperar la recogida.
- **Cancelar**: solo antes de que la transportadora la escanee. Envia devuelve el
  saldo y aquí queda registrado cuánto.

NINGÚN FALLO DE ENVIA TUMBA UN CAMBIO DE ESTADO. Si al facturar la guía no sale,
el pedido queda facturado igual, con una nota interna que dice por qué, y el botón
de generar queda a la vista. Perder la factura por un error de la transportadora
sería peor que quedarse sin guía un rato.
"""

from __future__ import annotations

import csv
import io
import logging
import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.deps import DBSession, require_permission
from app.models.crm import Customer
from app.models.portal import PortalOrder, Shipment
from app.services import envia
from app.services.portal_order_actions import queue_customer_notification

log = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/portal/orders", tags=["admin-envios"])


def _guia_dict(g: Shipment | None) -> dict | None:
    if g is None:
        return None
    return {
        "id": str(g.id),
        "carrier": g.carrier,
        "carrier_nombre": envia.NOMBRES.get(g.carrier, g.carrier),
        "service": g.service,
        "service_name": g.service_name,
        "label_cost": float(g.label_cost) if g.label_cost is not None else None,
        "currency": g.currency,
        "envia_shipment_id": g.envia_shipment_id,
        "tracking_number": g.tracking_number,
        "track_url": g.track_url,
        "label_url": g.label_url,
        "status": g.status,
        "status_at": g.status_at.isoformat() if g.status_at else None,
        "events": g.events or [],
        "pickup_number": g.pickup_number,
        "pickup_date": g.pickup_date.isoformat() if g.pickup_date else None,
        "pickup_window": g.pickup_window,
        "cancelled_at": g.cancelled_at.isoformat() if g.cancelled_at else None,
        "refunded_amount": float(g.refunded_amount) if g.refunded_amount is not None else None,
        "packages": g.packages or [],
        "created_at": g.created_at.isoformat() if g.created_at else None,
        "created_by": g.created_by,
    }


async def guia_activa(db: DBSession, order_id: uuid.UUID) -> Shipment | None:
    """La guía vigente del pedido: la última que no se canceló."""
    return (
        await db.execute(
            select(Shipment)
            .where(Shipment.portal_order_id == order_id, Shipment.cancelled_at.is_(None))
            .order_by(Shipment.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _pedido(db: DBSession, order_id: uuid.UUID) -> PortalOrder:
    order = (await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")
    if order.shipping_mode != "national" or not order.shipping_destination or not order.shipping_quote:
        raise HTTPException(400, "Este pedido no es un envío nacional por transportadora.")
    return order


def _paquetes_de(order: PortalOrder, items: list) -> list[dict]:
    return envia.empacar(
        [{"nombre": i.name or "", "cantidad": i.quantity} for i in items],
        int(float(order.unit_price or 0)),
    )


async def generar_para_pedido(
    db: DBSession, order: PortalOrder, actor: str = "admin", aunque_no_pagado: bool = False
) -> Shipment:
    """Genera la guía ante Envia y la guarda. Idempotente: si ya hay una activa, la
    devuelve sin crear otra (cada guía cuesta saldo)."""
    from app.models.portal import PortalOrderItem

    existente = await guia_activa(db, order.id)
    if existente:
        return existente
    if order.payment_status != "paid" and not aunque_no_pagado:
        raise HTTPException(409, "El pedido no está pagado. Un envío nacional sale solo con el pago confirmado.")
    if (order.workflow_status or "") == "cancelled":
        raise HTTPException(409, "El pedido está cancelado.")

    items = (
        await db.execute(
            select(PortalOrderItem).where(
                PortalOrderItem.portal_order_id == order.id, PortalOrderItem.is_removed.is_(False)
            )
        )
    ).scalars().all()
    paquetes = _paquetes_de(order, items)
    q = order.shipping_quote or {}
    referencia = order.order_reference or str(order.id)[:8].upper()
    try:
        r = await envia.generar_guia(
            envia.destino_a_envia(order.shipping_destination or {}),
            paquetes, q["carrier"], q["service"], referencia,
            comentarios=f"Pedido {referencia} · Bigotes y Paticas · {order.product_name}"[:200],
        )
    except envia.EnviaError as exc:
        raise HTTPException(502, f"Envia no generó la guía: {exc}") from exc

    guia = Shipment(
        portal_order_id=order.id,
        carrier=q["carrier"],
        service=q["service"],
        service_name=q.get("service_nombre"),
        label_cost=r.get("totalPrice"),
        currency=r.get("currency") or "COP",
        envia_shipment_id=r.get("shipmentId"),
        tracking_number=r.get("trackingNumber"),
        track_url=r.get("trackUrl"),
        label_url=r.get("label"),
        status="Created",
        status_at=datetime.now(UTC),
        packages=paquetes,
        raw_generate={k: v for k, v in r.items() if k != "packages"},
        created_by=actor,
    )
    db.add(guia)
    await db.flush()
    log.info("ENVIA · guía %s (%s) para pedido %s · saldo Envia %s",
             guia.tracking_number, guia.carrier, referencia, r.get("currentBalance"))
    # El correo con la guía sale aquí mismo, en segundo plano. El WhatsApp lo manda
    # el admin desde el modal que se abre al generar.
    try:
        from app.services import correos_envio

        await correos_envio.guia_lista(order, guia)
    except Exception:
        log.exception("ENVIA · guía creada pero falló el correo de %s", referencia)
    return guia


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("/{order_id}/envio")
async def ver_envio(order_id: uuid.UUID, db: DBSession) -> dict:
    order = await _pedido(db, order_id)
    guias = (
        await db.execute(
            select(Shipment).where(Shipment.portal_order_id == order_id).order_by(Shipment.created_at.desc())
        )
    ).scalars().all()
    activa = next((g for g in guias if g.cancelled_at is None), None)
    return {
        "modo": order.shipping_mode,
        "destino": order.shipping_destination,
        "cotizacion": order.shipping_quote,
        "pagado": order.payment_status == "paid",
        "guia": _guia_dict(activa),
        "historial": [_guia_dict(g) for g in guias],
        "envia_env": envia.ENV,
    }


class GenerarIn(BaseModel):
    aunque_no_pagado: bool = False


@router.post("/{order_id}/envio/generar", dependencies=[Depends(require_permission("crm:write"))])
async def generar(order_id: uuid.UUID, payload: GenerarIn, db: DBSession) -> dict:
    order = await _pedido(db, order_id)
    guia = await generar_para_pedido(db, order, aunque_no_pagado=payload.aunque_no_pagado)
    notif = await queue_customer_notification(order, "shipment_created", db)
    await db.commit()
    out = {"ok": True, "guia": _guia_dict(guia)}
    if notif:
        out["pending_notification"] = notif
    return out


@router.post("/{order_id}/envio/rastrear")
async def rastrear(order_id: uuid.UUID, db: DBSession) -> dict:
    await _pedido(db, order_id)
    guia = await guia_activa(db, order_id)
    if not guia or not guia.tracking_number:
        raise HTTPException(404, "Este pedido no tiene guía.")
    try:
        datos = await envia.rastrear([guia.tracking_number])
    except envia.EnviaError as exc:
        raise HTTPException(502, str(exc)) from exc
    if datos:
        d = datos[0]
        guia.status = (d.get("status") or guia.status or "")[:60]
        guia.status_at = datetime.now(UTC)
        eventos = d.get("eventHistory") or []
        guia.events = [
            {"fecha": e.get("date") or e.get("createdAt") or e.get("timestamp"),
             "estado": e.get("status") or e.get("description"),
             "lugar": e.get("location") or e.get("city")}
            for e in eventos
        ][:50]
        await db.commit()
    return {"ok": True, "guia": _guia_dict(guia)}


@router.post("/{order_id}/envio/cancelar", dependencies=[Depends(require_permission("crm:write"))])
async def cancelar(order_id: uuid.UUID, db: DBSession) -> dict:
    await _pedido(db, order_id)
    guia = await guia_activa(db, order_id)
    if not guia or not guia.tracking_number:
        raise HTTPException(404, "Este pedido no tiene guía activa.")
    try:
        r = await envia.cancelar_guia(guia.carrier, guia.tracking_number)
    except envia.EnviaError as exc:
        raise HTTPException(502, f"Envia no pudo cancelar la guía: {exc}") from exc
    guia.cancelled_at = datetime.now(UTC)
    guia.refunded_amount = r.get("refundedAmount")
    guia.status = "Canceled"
    await db.commit()
    return {"ok": True, "guia": _guia_dict(guia)}


class RecogidaIn(BaseModel):
    fecha: date
    desde: int = Field(ge=6, le=20)
    hasta: int = Field(ge=7, le=21)
    instrucciones: str | None = Field(default=None, max_length=200)


@router.post("/{order_id}/envio/recogida", dependencies=[Depends(require_permission("crm:write"))])
async def recogida(order_id: uuid.UUID, payload: RecogidaIn, db: DBSession) -> dict:
    await _pedido(db, order_id)
    guia = await guia_activa(db, order_id)
    if not guia or not guia.tracking_number:
        raise HTTPException(404, "Primero genera la guía.")
    if payload.hasta <= payload.desde:
        raise HTTPException(422, "La franja horaria no tiene sentido.")
    if payload.fecha < date.today():
        raise HTTPException(422, "La fecha de recogida ya pasó.")
    peso = sum(float(p.get("weight") or 0) for p in (guia.packages or [])) or 1.0
    try:
        r = await envia.programar_recogida(
            guia.carrier, payload.fecha.isoformat(), payload.desde, payload.hasta,
            [guia.tracking_number], len(guia.packages or []) or 1, peso,
            payload.instrucciones or "",
        )
    except envia.EnviaError as exc:
        raise HTTPException(502, f"La transportadora no aceptó la recogida: {exc}") from exc
    guia.pickup_number = str(r.get("pickupNumber") or r.get("confirmation") or "")[:80] or None
    guia.pickup_date = payload.fecha
    guia.pickup_window = f"{payload.desde:02d}:00-{payload.hasta:02d}:00"
    await db.commit()
    return {"ok": True, "guia": _guia_dict(guia), "respuesta": r}


@router.get("/{order_id}/envio/puntos")
async def puntos(order_id: uuid.UUID, db: DBSession) -> dict:
    """Oficinas de la transportadora en Dosquebradas y Pereira para dejar el paquete."""
    order = await _pedido(db, order_id)
    carrier = (order.shipping_quote or {}).get("carrier", "")
    salida = []
    for ciudad, postal in (("Dosquebradas", "661001"), ("Pereira", "660001")):
        for b in await envia.sucursales(carrier, ciudad, postal, limite=6):
            a = b.get("address") or {}
            salida.append({
                "nombre": b.get("reference") or "",
                "direccion": a.get("street") or "",
                "ciudad": (a.get("city") or ciudad).strip().title(),
                "lat": a.get("latitude"),
                "lng": a.get("longitude"),
                "distancia_km": b.get("distance"),
                "recibe": bool(a.get("admission", True)),
            })
    vistos: set[str] = set()
    unicos = []
    for p in salida:
        k = f"{p['direccion']}|{p['ciudad']}"
        if k not in vistos:
            vistos.add(k)
            unicos.append(p)
    return {"carrier": carrier, "carrier_nombre": envia.NOMBRES.get(carrier, carrier), "puntos": unicos}


# ══════════════════════════════════════════════════════════════════════════════
# REGISTRO DE ENVÍOS (Diego, 16-oct-2026)
#
# *"Eso lo llevamos no a ventas sino a un registro de envíos para ver cuánto va
# costando esos envíos y cruzarlos con Bold"*. Una fila por pedido nacional: lo
# que el cliente pagó por el envío, lo que cobró Envia por la guía, la diferencia,
# la referencia y el total de Bold, la factura y el estado de la guía.
# ══════════════════════════════════════════════════════════════════════════════

router_registro = APIRouter(prefix="/admin/envios", tags=["admin-envios"])


async def _filas_registro(db: DBSession, desde: date | None, hasta: date | None) -> list[dict]:
    q = (
        select(PortalOrder, Customer.full_name)
        .join(Customer, PortalOrder.customer_id == Customer.id, isouter=True)
        .where(PortalOrder.shipping_mode == "national")
        .where(PortalOrder.payment_status.isnot(None), PortalOrder.payment_status != "pending")
        .order_by(PortalOrder.created_at.desc())
    )
    if desde:
        q = q.where(PortalOrder.created_at >= datetime.combine(desde, datetime.min.time(), tzinfo=UTC))
    if hasta:
        q = q.where(PortalOrder.created_at < datetime.combine(hasta, datetime.max.time(), tzinfo=UTC))
    filas = (await db.execute(q)).all()
    ids = [o.id for o, _ in filas]
    guias: dict = {}
    if ids:
        for g in (
            await db.execute(
                select(Shipment).where(Shipment.portal_order_id.in_(ids)).order_by(Shipment.created_at.asc())
            )
        ).scalars().all():
            # La vigente manda; si todas se cancelaron, queda la última cancelada.
            actual = guias.get(g.portal_order_id)
            if actual is None or actual.cancelled_at is not None:
                guias[g.portal_order_id] = g
    salida = []
    for o, nombre in filas:
        qo = o.shipping_quote or {}
        d = o.shipping_destination or {}
        g = guias.get(o.id)
        cobrado = float(qo.get("precio") or 0)
        costo = float(g.label_cost) if (g and g.label_cost is not None and g.cancelled_at is None) else None
        total_bold = float(o.bold_amount or o.total_amount or 0)
        salida.append({
            "order_id": str(o.id),
            "fecha": (o.paid_at or o.created_at).isoformat(),
            "order_reference": o.order_reference,
            "cliente": nombre,
            "ciudad": d.get("ciudad"),
            "departamento": d.get("departamento_nombre"),
            "carrier": qo.get("carrier_nombre"),
            "servicio": qo.get("service_nombre"),
            "dias": qo.get("dias"),
            "payment_status": o.payment_status,
            "workflow_status": o.workflow_status,
            "total_bold": total_bold,
            "productos": max(0.0, total_bold - cobrado) if total_bold else 0.0,
            "envio_cobrado": cobrado,
            "envio_costo": costo,
            "diferencia": (cobrado - costo) if costo is not None else None,
            "invoice_number": o.invoice_number,
            "guia": g.tracking_number if g else None,
            "guia_estado": g.status if g else None,
            "guia_cancelada": bool(g and g.cancelled_at),
            "refund": float(g.refunded_amount) if (g and g.refunded_amount is not None) else None,
            "track_url": g.track_url if g else None,
        })
    return salida


@router_registro.get("/registro")
async def registro_envios(
    db: DBSession,
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    csv_: bool = Query(default=False, alias="csv"),
):
    filas = await _filas_registro(db, desde, hasta)
    if csv_:
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(["fecha", "referencia_bold", "cliente", "ciudad", "departamento", "transportadora", "servicio",
                    "estado_pago", "estado_pedido", "total_bold", "productos", "envio_cobrado_cliente",
                    "costo_guia_envia", "diferencia", "factura", "guia", "estado_guia", "guia_cancelada", "devuelto"])
        for f in filas:
            w.writerow([f["fecha"][:16].replace("T", " "), f["order_reference"], f["cliente"], f["ciudad"],
                        f["departamento"], f["carrier"], f["servicio"], f["payment_status"], f["workflow_status"],
                        int(f["total_bold"]), int(f["productos"]), int(f["envio_cobrado"]),
                        "" if f["envio_costo"] is None else int(f["envio_costo"]),
                        "" if f["diferencia"] is None else int(f["diferencia"]),
                        f["invoice_number"] or "", f["guia"] or "", f["guia_estado"] or "",
                        "sí" if f["guia_cancelada"] else "no", "" if f["refund"] is None else int(f["refund"])])
        return StreamingResponse(
            iter(["\ufeff" + buf.getvalue()]), media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=registro_envios.csv"},
        )
    pagadas = [f for f in filas if f["payment_status"] == "paid"]
    con_costo = [f for f in pagadas if f["envio_costo"] is not None]
    return {
        "filas": filas,
        "totales": {
            "pedidos_pagados": len(pagadas),
            "envio_cobrado": sum(f["envio_cobrado"] for f in pagadas),
            "envio_costo": sum(f["envio_costo"] for f in con_costo),
            "diferencia": sum(f["diferencia"] for f in con_costo),
            "guias_generadas": len(con_costo),
            "total_bold": sum(f["total_bold"] for f in pagadas),
            "productos": sum(f["productos"] for f in pagadas),
        },
    }
