"""Aplicar un pago sin pedido a las ventas YA facturadas que le corresponden.

Diego (9-oct-2026): *"me llegó al admin como pedido, pero es un pago sin pedido
porque ya está facturado"* → *"no tiene productos, es un pago, no un pedido"* →
*"puede ser una o dos ventas o muchas ventas un solo pago; yo pueda asignarle las
ventas ya registradas correspondientes"*.

EL CASO REAL QUE LO MOTIVÓ
Mabel compra en la tienda, se le factura (`BP-20261008-0006`, $252.500, dos bultos)
y se va. Esa noche paga por el enlace. El sistema crea un `portal_orders` con el
cobro… **sin un solo ítem**, porque no es un pedido: es plata.

DE DÓNDE SALE CADA COSA
El pago aporta **el dinero y la trazabilidad** (referencia de Bold, tarjeta, hora).
Las ventas aportan **qué se vendió**. Por eso el `purchase` de Google viaja con los
ítems de `sales.order_items` y con el **número de cada venta** como `transaction_id`:
mandar lo que trae el pago le enseñaría a Google que vendemos un artículo llamado
*"Pago / abono"*.

UN PAGO, VARIAS VENTAS
El monto se reparte entre las ventas elegidas, cada una hasta su saldo, en el orden
en que vienen. Lo que sobre queda **sin aplicar** y se dice: inventarle un destino a
la plata sobrante es peor que dejarla a la vista.

LO QUE ESTO EVITA
El cobro quedaba en `ready_to_invoice`. Un clic en *Facturar* habría llamado a
`bridge_to_sales()` creando **una segunda venta** y descontando otra vez el
inventario. Al aplicarlo se cierra, y además el camino de facturar queda bloqueado
para estos registros.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.api.v1.sales import _normalizar_estado_pago
from app.deps import CurrentUser, DBSession, require_permission
from app.models.catalog import Product
from app.models.crm import Customer
from app.models.portal import PaymentApplication, PortalOrder
from app.models.sales import Order as Venta
from app.models.sales import OrderItem as VentaItem
from app.models.sales import Payment as PagoVenta
from app.services.ga4 import enviar_purchase_de_venta

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/portal",
    tags=["admin-portal"],
    # El candado va en el router. Se aprendió el 8-oct dejando dos endpoints abiertos.
    dependencies=[Depends(require_permission("crm:read"))],
)

#: Cobros que NO son pedidos: nacen del enlace de cobro o del pago libre de la web.
#: Son los únicos que pueden aplicarse a ventas, y los únicos que jamás deben
#: facturarse —facturarlos crearía una venta duplicada.
ORIGENES_DE_COBRO = ("libre", "link")

#: Cuánto hacia atrás se buscan ventas. Mes y medio cubre al que paga la misma noche
#: y al que salda sus facturas viejas de una vez.
DIAS_ATRAS = 45


async def _ya_aplicado(db, pago_id: uuid.UUID) -> list[PaymentApplication]:
    return list((await db.execute(
        select(PaymentApplication).where(PaymentApplication.portal_order_id == pago_id)
    )).scalars().all())


async def _items_de(db, venta_id: uuid.UUID) -> list[dict]:
    filas = (await db.execute(
        select(Product.name, VentaItem.quantity, VentaItem.unit_price)
        .join(VentaItem, VentaItem.product_id == Product.id)
        .where(VentaItem.order_id == venta_id)
    )).all()
    return [{"nombre": n, "cantidad": c, "precio": float(p or 0)} for n, c, p in filas]


@router.get("/orders/{order_id}/ventas-candidatas")
async def ventas_candidatas(order_id: uuid.UUID, db: DBSession) -> dict:
    """Las ventas a las que este cobro podría corresponder, la mejor primero.

    Buscar a mano entre cientos de facturas es justo donde esto se vuelve "complicado
    para el admin". Lo que identifica de verdad es **cliente + monto + cercanía en el
    tiempo**: una venta del mismo cliente por el mismo valor es casi con seguridad la
    correcta, así que esa va arriba.
    """
    pago = (await db.execute(
        select(PortalOrder).where(PortalOrder.id == order_id)
    )).scalar_one_or_none()
    if not pago:
        raise HTTPException(404, "Cobro no encontrado")

    monto = Decimal(str(pago.bold_amount or pago.total_amount or 0))
    aplicadas = await _ya_aplicado(db, pago.id)
    usado = sum(Decimal(str(a.amount)) for a in aplicadas)
    ids_aplicados = {a.sales_order_id for a in aplicadas}

    condiciones = []
    if pago.customer_id:
        condiciones.append(Venta.customer_id == pago.customer_id)
        telefono = (await db.execute(
            select(Customer.phone).where(Customer.id == pago.customer_id)
        )).scalar_one_or_none()
        if telefono:
            # También por teléfono: el mismo humano puede estar dos veces en
            # `customers` —una por la web y otra del mostrador— y ahí el id no casa.
            ids = (await db.execute(
                select(Customer.id).where(Customer.phone == telefono)
            )).scalars().all()
            if ids:
                condiciones.append(Venta.customer_id.in_(ids))

    candidatas = []
    if condiciones:
        desde = datetime.now(UTC) - timedelta(days=DIAS_ATRAS)
        ventas = (await db.execute(
            select(Venta).where(or_(*condiciones), Venta.created_at >= desde)
            .order_by(Venta.created_at.desc()).limit(40)
        )).scalars().all()
        for v in ventas:
            total = Decimal(str(v.grand_total or 0))
            pagado = Decimal(str(v.paid_amount or 0))
            candidatas.append({
                "id": str(v.id),
                "order_number": v.order_number,
                "grand_total": float(total),
                "paid_amount": float(pagado),
                "falta": float(max(Decimal("0"), total - pagado)),
                "status": v.status,
                "payment_status": v.payment_status,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "coincide_el_monto": total == monto,
                "ya_aplicada": v.id in ids_aplicados,
                "items": await _items_de(db, v.id),
            })
        # Monto exacto primero; luego las más recientes. Las ya aplicadas, al final.
        candidatas.sort(key=lambda x: (x["ya_aplicada"], not x["coincide_el_monto"],
                                       x["created_at"] or ""), reverse=False)
        candidatas.sort(key=lambda x: (x["ya_aplicada"], not x["coincide_el_monto"]))

    return {
        "monto_del_cobro": float(monto),
        "ya_aplicado": float(usado),
        "disponible": float(max(Decimal("0"), monto - usado)),
        "es_cobro_sin_pedido": (pago.origen or "") in ORIGENES_DE_COBRO,
        "ventas_aplicadas": [
            {"sales_order_id": str(a.sales_order_id), "amount": a.amount,
             "enviado_a_google": a.purchase_sent_at is not None}
            for a in aplicadas
        ],
        "candidatas": candidatas,
    }


class VentaAAplicar(BaseModel):
    sales_order_id: uuid.UUID
    #: Cuánto abonarle. Si no viene, se le abona lo que le falte (hasta donde alcance
    #: el pago). Se deja explicitable porque hay repartos que solo sabe el humano.
    monto: int | None = Field(default=None, ge=0)


class AplicarPayload(BaseModel):
    ventas: list[VentaAAplicar] = Field(min_length=1, max_length=25)
    #: Contarle las ventas a Google. Por defecto sí: es la razón por la que Diego pidió
    #: esto. Apagable porque una venta de mostrador cobrada por enlace le llega a
    #: Google como tráfico directo, y hay casos en que no se quiere mezclar.
    enviar_a_google: bool = True
    nota: str | None = Field(default=None, max_length=500)


@router.post(
    "/orders/{order_id}/aplicar-a-ventas",
    dependencies=[Depends(require_permission("crm:write"))],
)
async def aplicar_a_ventas(
    order_id: uuid.UUID, payload: AplicarPayload, db: DBSession, user: CurrentUser
) -> dict:
    """Cierra un cobro contra una o varias ventas ya facturadas. Un botón, todo el trámite.

    Por cada venta elegida:

    1. **Le abona solo lo que le falta.** Si ya estaba cobrada —el caso de Mabel,
       donde el pago se registró como "Tarjeta" al facturar— **no se agrega ningún
       pago**: duplicarlo dejaría la venta cobrada dos veces y descuadraría la caja.
       En su lugar se le escribe la referencia de Bold al pago que ya existe, que es
       lo que permite rastrear un contracargo hasta su venta.
    2. **Se lo cuenta a Google** con los productos de ESA venta y su número de factura
       como `transaction_id`.

    Se puede aplicar en varias tandas: lo ya aplicado no se repite y lo que sobre
    queda disponible para otra venta.
    """
    pago = (await db.execute(
        select(PortalOrder).where(PortalOrder.id == order_id)
    )).scalar_one_or_none()
    if not pago:
        raise HTTPException(404, "Cobro no encontrado")
    if pago.payment_status != "paid":
        raise HTTPException(400, "Este cobro todavía no está pagado.")

    monto_total = Decimal(str(pago.bold_amount or pago.total_amount or 0))
    previas = await _ya_aplicado(db, pago.id)
    disponible = max(Decimal("0"), monto_total - sum(Decimal(str(a.amount)) for a in previas))
    ya_estan = {a.sales_order_id for a in previas}
    ahora = datetime.now(UTC)
    referencia = pago.order_reference or str(pago.id)

    resultados = []
    # Lo que ya estaba cobrado en las ventas elegidas. Se lleva aparte porque NO es
    # sobrante: decir "sobran $252.500" cuando el dinero ya estaba contabilizado en la
    # venta haría pensar que hay plata suelta, y la hay cero.
    cubierto_antes = Decimal("0")
    for elegida in payload.ventas:
        if elegida.sales_order_id in ya_estan:
            resultados.append({"sales_order_id": str(elegida.sales_order_id),
                               "error": "Ya estaba aplicada a este pago"})
            continue

        venta = (await db.execute(
            select(Venta).where(Venta.id == elegida.sales_order_id)
        )).scalar_one_or_none()
        if not venta:
            resultados.append({"sales_order_id": str(elegida.sales_order_id),
                               "error": "Venta no encontrada"})
            continue

        total = Decimal(str(venta.grand_total or 0))
        pagado = Decimal(str(venta.paid_amount or 0))
        falta = max(Decimal("0"), total - pagado)
        # Lo que se le abona: lo pedido, o lo que le falte; nunca más de lo disponible.
        pedido_ = Decimal(str(elegida.monto)) if elegida.monto is not None else falta
        abono = min(pedido_, falta, disponible)

        pago_venta_id = None
        if abono > 0:
            fila = PagoVenta(
                order_id=venta.id, method="Bold", amount=abono,
                received_at=pago.paid_at or ahora, reference=referencia,
                notes=f"Pago en línea con Bold · {referencia}", created_by=user.email,
            )
            db.add(fila)
            await db.flush()
            pago_venta_id = fila.id
            venta.paid_amount = pagado + abono
            venta.balance_due = max(Decimal("0"), total - venta.paid_amount)
            venta.payment_status = _normalizar_estado_pago(venta.balance_due, total)
            disponible -= abono
        else:
            # Ya estaba cobrada: no se toca la plata, solo se deja el rastro — y solo
            # si hay UN pago sin referencia del mismo valor. Escribir sobre uno ambiguo
            # sería inventar una trazabilidad que no tenemos.
            sin_ref = (await db.execute(
                select(PagoVenta).where(
                    PagoVenta.order_id == venta.id,
                    PagoVenta.reference.is_(None),
                    PagoVenta.amount == monto_total,
                )
            )).scalars().all()
            if len(sin_ref) == 1:
                sin_ref[0].reference = referencia
                sin_ref[0].notes = ((sin_ref[0].notes or "")
                                    + f" · cobrado en línea con Bold ({referencia})").strip()
                pago_venta_id = sin_ref[0].id
                cubierto_antes += Decimal(str(sin_ref[0].amount))

        aplicacion = PaymentApplication(
            portal_order_id=pago.id, sales_order_id=venta.id,
            amount=int(abono), sales_payment_id=pago_venta_id,
            created_by=user.email, note=(payload.nota or "").strip() or None,
        )
        db.add(aplicacion)
        try:
            await db.flush()
        except IntegrityError:
            # El UNIQUE hizo su trabajo: alguien aplicó lo mismo en paralelo.
            await db.rollback()
            raise HTTPException(409, f"La venta {venta.order_number} ya tenía este pago aplicado.")

        enviado = False
        if payload.enviar_a_google:
            try:
                enviado = await enviar_purchase_de_venta(db, venta, pago, aplicacion=aplicacion)
            except Exception:
                # Que Google no se entere jamás puede estorbar un cobro ya conciliado.
                log.exception("No se pudo contarle a Google la venta %s", venta.order_number)

        resultados.append({
            "sales_order_id": str(venta.id),
            "order_number": venta.order_number,
            "abonado_ahora": float(abono),
            "ya_estaba_cobrada": falta == 0,
            "saldo": float(venta.balance_due or 0),
            "estado_de_pago": venta.payment_status,
            "enviado_a_google": enviado,
        })
        ya_estan.add(venta.id)

    # El cobro se cierra en cuanto queda atado a alguna venta: fuera de la bandeja de
    # pendientes y fuera del camino de facturación.
    if any("error" not in r for r in resultados):
        aplicadas_ok = [r for r in resultados if "error" not in r]
        pago.sales_order_id = uuid.UUID(aplicadas_ok[0]["sales_order_id"])
        pago.workflow_status = "delivered"
        pago.status = "delivered"
        pago.delivered_at = pago.delivered_at or ahora
        numeros = ", ".join(r["order_number"] for r in aplicadas_ok)
        detalle = (f"[{ahora.strftime('%d/%m %H:%M')}] Aplicado a {numeros} por "
                   f"{user.full_name or user.email}"
                   + (f" · {payload.nota.strip()}" if payload.nota else ""))
        pago.internal_notes = f"{(pago.internal_notes or '').strip()}\n{detalle}".strip()

    await db.commit()
    log.info("COBRO · %s aplicado a %s venta(s); queda disponible %s",
             referencia, len(resultados), disponible)

    sobrante = max(Decimal("0"), disponible - cubierto_antes)
    return {
        "ok": True,
        "monto_del_cobro": float(monto_total),
        # Dinero que ya estaba registrado en las ventas (se pagó al facturar) y que
        # este cobro solo viene a identificar. No es plata suelta.
        "ya_estaba_registrado": float(cubierto_antes),
        # Plata del cobro que todavía no tiene venta a la que ir. Si queda algo, se
        # dice y punto: inventarle destino es peor que dejarlo a la vista.
        "sobrante_sin_aplicar": float(sobrante),
        "ventas": resultados,
    }
