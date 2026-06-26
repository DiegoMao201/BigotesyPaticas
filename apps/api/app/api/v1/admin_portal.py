"""Admin Portal — endpoints de gestión de pedidos y citas del portal."""
from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text

from app.api.v1.portal_notifications import notify_admins, notify_customer
from app.deps import DBSession
from app.models.crm import Customer
from app.models.portal import (
    Appointment,
    LoyaltyPoint,
    PortalNotification,
    PortalOrder,
    PortalReferral,
    PortalSession,
)
from app.models.sales import Order as SalesOrder, OrderItem as SalesOrderItem

router = APIRouter(prefix="/admin/portal", tags=["admin-portal"])


# ── schemas ───────────────────────────────────────────────────────────────────

class OrderStatusUpdate(BaseModel):
    status: str
    notes: str | None = None
    cancel_reason: str | None = None


class ApptStatusUpdate(BaseModel):
    status: str
    cancel_reason: str | None = None


# ── helpers ───────────────────────────────────────────────────────────────────

def _pet_name_subquery(db_session):
    """Subquery no es necesaria — usamos join directo en las consultas."""
    pass


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("/overview")
async def portal_overview(db: DBSession) -> dict:
    """KPIs del portal: sesiones activas, pedidos pendientes, citas hoy, puntos 30d."""
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    thirty_ago = now - timedelta(days=30)

    # Sesiones activas en las últimas 24h
    active_sessions = (await db.execute(
        select(func.count()).select_from(PortalSession).where(
            PortalSession.expires_at > now,
            PortalSession.created_at >= now - timedelta(hours=24),
        )
    )).scalar_one()

    # Pedidos pendientes (received + processing)
    pending_orders = (await db.execute(
        select(func.count()).select_from(PortalOrder).where(
            PortalOrder.status.in_(["received", "processing"])
        )
    )).scalar_one()

    # Citas hoy
    appts_today = (await db.execute(
        select(func.count()).select_from(Appointment).where(
            Appointment.scheduled_at >= today_start,
            Appointment.scheduled_at < today_end,
            Appointment.status.notin_(["cancelled"]),
        )
    )).scalar_one()

    # Puntos otorgados en los últimos 30 días
    points_30d = (await db.execute(
        select(func.coalesce(func.sum(LoyaltyPoint.points), 0)).where(
            LoyaltyPoint.created_at >= thirty_ago,
            LoyaltyPoint.points > 0,
        )
    )).scalar_one()

    return {
        "active_sessions_24h": active_sessions,
        "pending_orders": pending_orders,
        "appointments_today": appts_today,
        "loyalty_points_30d": int(points_30d),
        "as_of": now.isoformat(),
    }


@router.get("/orders")
async def list_portal_orders(
    db: DBSession,
    status: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
) -> list[dict]:
    """Lista pedidos del portal con datos de cliente y mascota."""
    from app.models.portal import Pet

    q = (
        select(
            PortalOrder,
            Customer.full_name.label("customer_name"),
            Pet.name.label("pet_name"),
        )
        .join(Customer, PortalOrder.customer_id == Customer.id, isouter=True)
        .join(Pet, PortalOrder.pet_id == Pet.id, isouter=True)
        .order_by(PortalOrder.created_at.desc())
        .limit(limit)
    )
    if status:
        q = q.where(PortalOrder.status == status)

    rows = (await db.execute(q)).all()
    result = []
    for order, customer_name, pet_name in rows:
        result.append({
            "id": str(order.id),
            "customer_name": customer_name,
            "pet_name": pet_name,
            "product_name": order.product_name,
            "quantity": order.quantity,
            "unit_price": float(order.unit_price) if order.unit_price else None,
            "status": order.status,
            "invoice_number": order.invoice_number,
            "sales_order_id": str(order.sales_order_id) if order.sales_order_id else None,
            "notes": order.notes,
            "created_at": order.created_at.isoformat(),
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
            "points_awarded": order.points_awarded,
        })
    return result


@router.patch("/orders/{order_id}")
async def update_portal_order(
    order_id: uuid.UUID,
    payload: OrderStatusUpdate,
    db: DBSession,
) -> dict:
    """Actualiza el estado de un pedido del portal y notifica al cliente."""
    order = (await db.execute(
        select(PortalOrder).where(PortalOrder.id == order_id)
    )).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    old_status = order.status
    new_status = payload.status

    valid_transitions = {
        "received": ["processing", "cancelled"],
        "processing": ["invoiced", "ready", "cancelled"],
        "invoiced": ["ready", "cancelled"],
        "ready": ["delivered", "cancelled"],
        "delivered": [],
        "cancelled": [],
    }
    if new_status not in valid_transitions.get(old_status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Transición inválida: {old_status} → {new_status}",
        )

    order.status = new_status
    if payload.notes is not None:
        order.notes = payload.notes

    now = datetime.now(UTC)

    if old_status == "received" and new_status == "processing":
        await notify_customer(
            db,
            order.customer_id,
            notif_type="order_confirmed",
            title="Pedido en preparación",
            body="Tu pedido está en preparación 🐾",
            data={"order_id": str(order.id)},
        )

    elif new_status == "invoiced":
        from app.api.v1.sales import _next_order_number
        invoice_num = await _next_order_number(db)
        total = float(order.unit_price or 0) * order.quantity

        # Crear venta REAL en sales.orders con channel='PORTAL'
        sales_order = SalesOrder(
            order_number=invoice_num,
            channel="PORTAL",
            customer_id=order.customer_id,
            grand_total=total,
            subtotal=total,
            tax_total=0,
            discount_total=0,
            shipping_total=0,
            payment_status="Pendiente",
            status="confirmed",
            occurred_at=now,
            notes=f"Pedido portal #{str(order.id)[:8]}",
            metadata={"portal_order_id": str(order.id)},
        )
        db.add(sales_order)
        await db.flush()

        # Crear ítem de la venta
        item = SalesOrderItem(
            order_id=sales_order.id,
            product_id=order.product_id,
            sku_snapshot="",
            name_snapshot=order.product_name,
            quantity=order.quantity,
            unit_price=order.unit_price or 0,
            unit_cost=0,
            discount=0,
            line_total=total,
        )
        db.add(item)

        order.invoice_number = invoice_num
        order.invoiced_at = now
        order.sales_order_id = sales_order.id
        if payload.notes:
            order.processed_by = payload.notes
        await notify_customer(
            db,
            order.customer_id,
            notif_type="order_invoiced",
            title="Pedido facturado",
            body=f"Tu pedido fue facturado — {invoice_num} 🧾",
            data={"order_id": str(order.id), "invoice_number": invoice_num},
        )

    elif new_status == "ready":
        await notify_customer(
            db,
            order.customer_id,
            notif_type="order_ready",
            title="Pedido listo para entrega",
            body="Tu pedido está listo para entrega 🎉",
            data={"order_id": str(order.id)},
        )

    elif new_status == "delivered":
        order.delivered_at = now

        # Calcular puntos: 1 punto por cada $1.000 COP
        price = float(order.unit_price or 0)
        points = math.floor(price * order.quantity / 1000)
        order.points_awarded = points

        if points > 0:
            lp = LoyaltyPoint(
                customer_id=order.customer_id,
                points=points,
                reason="portal_order",
                reference_type="portal_order",
                reference_id=order.id,
                description=f"Entrega de pedido: {order.product_name}",
                expires_at=now + timedelta(days=365),
            )
            db.add(lp)

        await notify_customer(
            db,
            order.customer_id,
            notif_type="order_delivered",
            title="Pedido entregado",
            body=f"Tu pedido fue entregado. Ganaste {points} puntos de fidelidad 🐾" if points > 0
                 else "Tu pedido fue entregado con éxito 🐾",
            data={"order_id": str(order.id), "points_awarded": points},
        )

        # Verificar referido: si es primera entrega y referrer no ha recibido recompensa
        referral = (await db.execute(
            select(PortalReferral).where(
                PortalReferral.referred_customer_id == order.customer_id,
                PortalReferral.reward_paid_at == None,  # noqa: E711
            )
        )).scalar_one_or_none()

        if referral:
            # Marcar primera compra si no estaba marcada
            if referral.first_purchase_at is None:
                referral.first_purchase_at = now

            # Otorgar 100 puntos al referidor
            referral.reward_paid_at = now
            referrer_lp = LoyaltyPoint(
                customer_id=referral.referrer_customer_id,
                points=100,
                reason="referral",
                reference_type="referral",
                reference_id=referral.id,
                description="Recompensa por referir a un nuevo cliente",
                expires_at=now + timedelta(days=365),
            )
            db.add(referrer_lp)

            await notify_customer(
                db,
                referral.referrer_customer_id,
                notif_type="referral_reward",
                title="¡Ganaste puntos por referir!",
                body="Tu amigo hizo su primera compra. ¡Recibiste 100 puntos de fidelidad! 🎉",
                data={"referral_id": str(referral.id), "points": 100},
            )

    elif new_status == "cancelled":
        reason_text = payload.cancel_reason or ""
        await notify_customer(
            db,
            order.customer_id,
            notif_type="general",
            title="Pedido cancelado",
            body=f"Tu pedido fue cancelado. {reason_text}".strip(),
            data={"order_id": str(order.id)},
        )

    await db.commit()
    await db.refresh(order)
    return {"ok": True, "id": str(order.id), "status": order.status}


@router.get("/appointments")
async def list_portal_appointments(
    db: DBSession,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
) -> list[dict]:
    """Lista citas del portal con datos de cliente y mascota."""
    from app.models.portal import Pet

    q = (
        select(
            Appointment,
            Customer.full_name.label("customer_name"),
            Pet.name.label("pet_name"),
        )
        .join(Customer, Appointment.customer_id == Customer.id, isouter=True)
        .join(Pet, Appointment.pet_id == Pet.id, isouter=True)
        .order_by(Appointment.scheduled_at.desc())
        .limit(limit)
    )
    if status:
        q = q.where(Appointment.status == status)
    if date_from:
        q = q.where(Appointment.scheduled_at >= datetime.fromisoformat(date_from))
    if date_to:
        q = q.where(Appointment.scheduled_at <= datetime.fromisoformat(date_to))

    rows = (await db.execute(q)).all()
    result = []
    for appt, customer_name, pet_name in rows:
        result.append({
            "id": str(appt.id),
            "customer_name": customer_name,
            "pet_name": pet_name,
            "service_type": appt.service_type,
            "scheduled_at": appt.scheduled_at.isoformat(),
            "duration_min": appt.duration_min,
            "status": appt.status,
            "price": float(appt.price) if appt.price else None,
            "notes": appt.notes,
            "confirmed_at": appt.confirmed_at.isoformat() if appt.confirmed_at else None,
            "completed_at": appt.completed_at.isoformat() if appt.completed_at else None,
            "cancel_reason": appt.cancel_reason,
            "created_at": appt.created_at.isoformat(),
        })
    return result


@router.patch("/appointments/{appt_id}")
async def update_portal_appointment(
    appt_id: uuid.UUID,
    payload: ApptStatusUpdate,
    db: DBSession,
) -> dict:
    """Actualiza el estado de una cita del portal y notifica al cliente."""
    appt = (await db.execute(
        select(Appointment).where(Appointment.id == appt_id)
    )).scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    old_status = appt.status
    new_status = payload.status
    now = datetime.now(UTC)

    appt.status = new_status

    if new_status == "confirmed":
        appt.confirmed_at = now
        # Format date for notification
        scheduled_str = appt.scheduled_at.strftime("%d/%m/%Y a las %H:%M")
        await notify_customer(
            db,
            appt.customer_id,
            notif_type="appt_confirmed",
            title="Cita confirmada",
            body=f"Tu cita fue confirmada para el {scheduled_str} 🐾",
            data={"appointment_id": str(appt.id), "scheduled_at": appt.scheduled_at.isoformat()},
        )

    elif new_status == "completed":
        appt.completed_at = now

    elif new_status == "cancelled":
        if payload.cancel_reason:
            appt.cancel_reason = payload.cancel_reason
        reason_text = payload.cancel_reason or ""
        await notify_customer(
            db,
            appt.customer_id,
            notif_type="appt_cancelled",
            title="Cita cancelada",
            body=f"Tu cita fue cancelada. {reason_text}".strip(),
            data={"appointment_id": str(appt.id)},
        )

    await db.commit()
    await db.refresh(appt)
    return {"ok": True, "id": str(appt.id), "status": appt.status}


@router.get("/feed")
async def admin_feed(db: DBSession) -> list[dict]:
    """Últimas 20 notificaciones (admin + cliente) ordenadas por fecha."""
    rows = (await db.execute(
        select(PortalNotification)
        .order_by(PortalNotification.created_at.desc())
        .limit(20)
    )).scalars().all()

    return [
        {
            "id": str(n.id),
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "is_admin": n.is_admin,
            "customer_id": str(n.customer_id) if n.customer_id else None,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "created_at": n.created_at.isoformat(),
            "data": n.data or {},
        }
        for n in rows
    ]
