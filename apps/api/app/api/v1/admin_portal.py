"""Admin Portal — endpoints de gestión de pedidos y citas del portal."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy import update as sa_update

from app.api.v1.portal_notifications import notify_customer
from app.deps import DBSession
from app.models.crm import Customer
from app.models.portal import (
    ActivityLog,
    Appointment,
    LoyaltyPoint,
    PendingNotification,
    PortalNotification,
    PortalOrder,
    PortalOrderItem,
    PortalSession,
)
from app.services.portal_order_actions import (
    bridge_to_sales,
    credit_loyalty_points,
    process_referral_reward,
    queue_customer_notification,
)

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
    active_sessions = (
        await db.execute(
            select(func.count())
            .select_from(PortalSession)
            .where(
                PortalSession.expires_at > now,
                PortalSession.created_at >= now - timedelta(hours=24),
            )
        )
    ).scalar_one()

    # Pedidos pendientes (received + processing)
    pending_orders = (
        await db.execute(
            select(func.count())
            .select_from(PortalOrder)
            .where(PortalOrder.status.in_(["received", "processing"]))
        )
    ).scalar_one()

    # Citas hoy
    appts_today = (
        await db.execute(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.scheduled_at >= today_start,
                Appointment.scheduled_at < today_end,
                Appointment.status.notin_(["cancelled"]),
            )
        )
    ).scalar_one()

    # Puntos otorgados en los últimos 30 días
    points_30d = (
        await db.execute(
            select(func.coalesce(func.sum(LoyaltyPoint.points), 0)).where(
                LoyaltyPoint.created_at >= thirty_ago,
                LoyaltyPoint.points > 0,
            )
        )
    ).scalar_one()

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
        result.append(
            {
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
            }
        )
    return result


@router.patch("/orders/{order_id}")
async def update_portal_order(
    order_id: uuid.UUID,
    payload: OrderStatusUpdate,
    db: DBSession,
) -> dict:
    """Actualiza el estado de un pedido del portal y notifica al cliente."""
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
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

    if new_status == "processing":
        await notify_customer(
            db,
            order.customer_id,
            notif_type="order_confirmed",
            title="Pedido en preparación",
            body="Tu pedido está en preparación 🐾",
            data={"order_id": str(order.id)},
        )

    elif new_status == "invoiced":
        # Usar función compartida (idempotente)
        await bridge_to_sales(order, db)
        await notify_customer(
            db,
            order.customer_id,
            notif_type="order_invoiced",
            title="Pedido facturado",
            body=f"Tu pedido fue facturado — {order.invoice_number} 🧾",
            data={"order_id": str(order.id), "invoice_number": order.invoice_number},
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
        # Usar funciones compartidas (idempotentes)
        points = await credit_loyalty_points(order, db)
        await process_referral_reward(order, db)
        await notify_customer(
            db,
            order.customer_id,
            notif_type="order_delivered",
            title="Pedido entregado",
            body=f"Tu pedido fue entregado. Ganaste {points} puntos de fidelidad 🐾"
            if points > 0
            else "Tu pedido fue entregado con éxito 🐾",
            data={"order_id": str(order.id), "points_awarded": points},
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
        result.append(
            {
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
            }
        )
    return result


@router.patch("/appointments/{appt_id}")
async def update_portal_appointment(
    appt_id: uuid.UUID,
    payload: ApptStatusUpdate,
    db: DBSession,
) -> dict:
    """Actualiza el estado de una cita del portal y notifica al cliente."""
    appt = (
        await db.execute(select(Appointment).where(Appointment.id == appt_id))
    ).scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

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
    rows = (
        (
            await db.execute(
                select(PortalNotification).order_by(PortalNotification.created_at.desc()).limit(20)
            )
        )
        .scalars()
        .all()
    )

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


# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 2 — Pet Monitor Fase 1: gestión completa de pedidos
# ══════════════════════════════════════════════════════════════════════════════

# ── Schemas ───────────────────────────────────────────────────────────────────


class ChangeWorkflowPayload(BaseModel):
    new_status: str
    internal_notes: str | None = None


class EditQuantityPayload(BaseModel):
    new_quantity: int
    reason: str | None = None


class SubstitutePayload(BaseModel):
    new_product_id: uuid.UUID
    new_quantity: int | None = None
    reason: str


class AddItemPayload(BaseModel):
    product_id: uuid.UUID
    quantity: int = 1
    notes: str | None = None
    reason: str | None = None


class RemoveItemPayload(BaseModel):
    reason: str


class DiscountPayload(BaseModel):
    discount_amount: float
    reason: str


class AddressPayload(BaseModel):
    shipping_address: str


class NotesPayload(BaseModel):
    internal_notes: str | None = None
    customer_facing_notes: str | None = None


class ConfirmApprovalPayload(BaseModel):
    channel: str  # 'whatsapp_replied'|'phone_call'|'in_store'
    notes: str | None = None


class MarkSentPayload(BaseModel):
    channel: str = "whatsapp"


class CancelOrderPayload(BaseModel):
    reason: str
    refund_points: bool = False


class RescheduleApptPayload(BaseModel):
    proposed_options: list[str]  # ISO datetime strings
    reason_category: str
    reason_notes: str | None = None
    compensation_points: int = 50


class ConfirmApptChoicePayload(BaseModel):
    chosen_datetime: str
    customer_confirmed_via: str = "whatsapp"


# ── Helper ────────────────────────────────────────────────────────────────────


async def _get_order_with_items(db: DBSession, order_id: uuid.UUID) -> dict:
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")

    items = (
        (
            await db.execute(
                select(PortalOrderItem)
                .where(
                    PortalOrderItem.portal_order_id == order_id,
                    PortalOrderItem.is_removed.is_(False),
                )
                .order_by(PortalOrderItem.created_at)
            )
        )
        .scalars()
        .all()
    )

    items_data = [
        {
            "id": str(i.id),
            "product_id": str(i.product_id) if i.product_id else None,
            "sku": i.sku,
            "name": i.name,
            "image_url": i.image_url,
            "quantity": i.quantity,
            "unit_price": float(i.unit_price) if i.unit_price else 0,
            "subtotal": float(i.subtotal) if i.subtotal else 0,
            "notes": i.notes,
            "is_substituted": i.is_substituted,
            "substituted_from_name": i.substituted_from_name,
        }
        for i in items
    ]

    subtotal = sum(float(i.subtotal or 0) for i in items)
    discount = float(order.discount_amount or 0)
    shipping = 0.0 if subtotal >= 30000 else 8000.0
    total = subtotal - discount + shipping

    customer = (
        (
            await db.execute(select(Customer).where(Customer.id == order.customer_id))
        ).scalar_one_or_none()
        if order.customer_id
        else None
    )

    return {
        "id": str(order.id),
        "customer_id": str(order.customer_id) if order.customer_id else None,
        "customer_name": customer.full_name if customer else None,
        "customer_phone": customer.phone if customer else None,
        "customer_email": customer.email if customer else None,
        "status": order.status,
        "workflow_status": order.workflow_status,
        "payment_method": order.payment_method,
        "shipping_address": order.shipping_address,
        "internal_notes": order.internal_notes,
        "customer_facing_notes": order.customer_facing_notes,
        "discount_amount": float(order.discount_amount or 0),
        "discount_reason": order.discount_reason,
        "subtotal": subtotal,
        "shipping": shipping,
        "total": total,
        "points_awarded": order.points_awarded,
        "invoice_number": order.invoice_number,
        "last_status_change_at": order.last_status_change_at.isoformat()
        if order.last_status_change_at
        else None,
        "customer_confirmed_changes_at": order.customer_confirmed_changes_at.isoformat()
        if order.customer_confirmed_changes_at
        else None,
        "customer_confirmation_channel": order.customer_confirmation_channel,
        "created_at": order.created_at.isoformat(),
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "items": items_data,
    }


async def _log(
    db: DBSession,
    entity_id: uuid.UUID,
    action: str,
    actor_name: str = "Admin",
    changes: dict | None = None,
    notes: str | None = None,
    visible: bool = True,
) -> None:
    entry = ActivityLog(
        entity_type="order",
        entity_id=entity_id,
        action=action,
        actor_type="admin",
        actor_name=actor_name,
        changes=changes,
        notes=notes,
        visible_to_customer=visible,
    )
    db.add(entry)


async def _recalculate_total(db: DBSession, order_id: uuid.UUID) -> float:
    items = (
        (
            await db.execute(
                select(PortalOrderItem).where(
                    PortalOrderItem.portal_order_id == order_id,
                    PortalOrderItem.is_removed.is_(False),
                )
            )
        )
        .scalars()
        .all()
    )
    total = sum(float(i.subtotal or (i.unit_price or 0) * i.quantity) for i in items)
    await db.execute(
        sa_update(PortalOrder)
        .where(PortalOrder.id == order_id)
        .values(total_amount=Decimal(str(total)))
    )
    return total


# ── GET order detail ──────────────────────────────────────────────────────────


@router.get("/orders/{order_id}/detail")
async def get_order_detail(order_id: uuid.UUID, db: DBSession) -> dict:
    return await _get_order_with_items(db, order_id)


# ── GET activity log ──────────────────────────────────────────────────────────


@router.get("/orders/{order_id}/activity")
async def get_order_activity(order_id: uuid.UUID, db: DBSession) -> list[dict]:
    logs = (
        (
            await db.execute(
                select(ActivityLog)
                .where(ActivityLog.entity_type == "order", ActivityLog.entity_id == order_id)
                .order_by(ActivityLog.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": str(lg.id),
            "action": lg.action,
            "actor_type": lg.actor_type,
            "actor_name": lg.actor_name,
            "changes": lg.changes,
            "notes": lg.notes,
            "visible_to_customer": lg.visible_to_customer,
            "notification_sent_at": lg.notification_sent_at.isoformat()
            if lg.notification_sent_at
            else None,
            "created_at": lg.created_at.isoformat(),
        }
        for lg in logs
    ]


# ── PATCH workflow status ──────────────────────────────────────────────────────

WORKFLOW_TRANSITIONS: dict[str, list[str]] = {
    "received": ["under_review", "awaiting_customer", "cancelled"],
    "under_review": ["awaiting_customer", "ready_to_invoice", "cancelled"],
    "awaiting_customer": ["ready_to_invoice", "cancelled"],
    "ready_to_invoice": ["invoiced", "cancelled"],
    "invoiced": ["in_preparation", "cancelled"],
    "in_preparation": ["ready_for_delivery"],
    "ready_for_delivery": ["in_transit"],
    "in_transit": ["delivered"],
    "delivered": [],
    "cancelled": [],
    "returned": [],
}


@router.patch("/orders/{order_id}/workflow")
async def change_workflow_status(
    order_id: uuid.UUID, payload: ChangeWorkflowPayload, db: DBSession
) -> dict:
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")

    old = order.workflow_status or "received"
    new = payload.new_status
    allowed = WORKFLOW_TRANSITIONS.get(old, [])
    if new not in allowed:
        raise HTTPException(400, f"Transición no permitida: {old} → {new}")

    order.workflow_status = new
    order.last_status_change_at = datetime.now(UTC)
    if payload.internal_notes:
        existing = order.internal_notes or ""
        order.internal_notes = f"{existing}\n[{datetime.now(UTC).strftime('%d/%m %H:%M')}] {payload.internal_notes}".strip()

    if new == "delivered":
        order.delivered_at = datetime.now(UTC)
        order.status = "delivered"

    # ── Portar lógica del endpoint viejo ──────────────────────────────────────
    if new == "invoiced":
        await bridge_to_sales(order, db)

    if new == "delivered":
        await credit_loyalty_points(order, db)
        await process_referral_reward(order, db)

    # Encolar notificación WhatsApp para modal admin (no envía nada automático)
    pending_notif = await queue_customer_notification(order, new, db)

    await _log(
        db, order_id, "status_changed", changes={"workflow_status": {"before": old, "after": new}}
    )
    await db.commit()

    result: dict = {"ok": True, "workflow_status": new}
    if pending_notif:
        result["pending_notification"] = pending_notif
    return result


# ── PATCH item quantity ────────────────────────────────────────────────────────


@router.patch("/orders/{order_id}/items/{item_id}/quantity")
async def edit_item_quantity(
    order_id: uuid.UUID, item_id: uuid.UUID, payload: EditQuantityPayload, db: DBSession
) -> dict:
    item = (
        await db.execute(
            select(PortalOrderItem).where(
                PortalOrderItem.id == item_id,
                PortalOrderItem.portal_order_id == order_id,
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item no encontrado")

    old_qty = item.quantity
    item.quantity = payload.new_quantity
    item.subtotal = (item.unit_price or Decimal("0")) * payload.new_quantity

    await _recalculate_total(db, order_id)
    await _log(
        db,
        order_id,
        "item_quantity_changed",
        changes={
            "item": item.name,
            "quantity": {"before": old_qty, "after": payload.new_quantity},
            "reason": payload.reason,
        },
        notes=payload.reason,
        visible=True,
    )
    # Mark as awaiting_customer if currently under_review
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if order and order.workflow_status in ("received", "under_review"):
        order.workflow_status = "awaiting_customer"
    await db.commit()
    return await _get_order_with_items(db, order_id)


# ── POST substitute item ──────────────────────────────────────────────────────


@router.post("/orders/{order_id}/items/{item_id}/substitute")
async def substitute_item(
    order_id: uuid.UUID, item_id: uuid.UUID, payload: SubstitutePayload, db: DBSession
) -> dict:
    from app.models.catalog import Product

    item = (
        await db.execute(
            select(PortalOrderItem).where(
                PortalOrderItem.id == item_id, PortalOrderItem.portal_order_id == order_id
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item no encontrado")

    new_prod = (
        await db.execute(select(Product).where(Product.id == payload.new_product_id))
    ).scalar_one_or_none()
    if not new_prod:
        raise HTTPException(404, "Producto de sustitución no encontrado")

    old_name = item.name
    old_data = {"name": old_name, "sku": item.sku, "unit_price": float(item.unit_price or 0)}

    item.substituted_from_name = old_name
    item.is_substituted = True
    item.product_id = new_prod.id
    item.sku = new_prod.sku
    item.name = new_prod.name
    item.image_url = new_prod.primary_image_url
    item.unit_price = new_prod.price
    item.quantity = payload.new_quantity or item.quantity
    item.subtotal = new_prod.price * item.quantity
    item.notes = f"Sustituido. Motivo: {payload.reason}"

    await _recalculate_total(db, order_id)
    await _log(
        db,
        order_id,
        "item_substituted",
        changes={
            "before": old_data,
            "after": {"name": new_prod.name, "sku": new_prod.sku},
            "reason": payload.reason,
        },
        notes=payload.reason,
        visible=True,
    )
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if order and order.workflow_status in ("received", "under_review"):
        order.workflow_status = "awaiting_customer"
    await db.commit()
    return await _get_order_with_items(db, order_id)


# ── POST add item ─────────────────────────────────────────────────────────────


@router.post("/orders/{order_id}/items")
async def add_item_to_order(order_id: uuid.UUID, payload: AddItemPayload, db: DBSession) -> dict:
    from app.models.catalog import Product

    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")

    prod = (
        await db.execute(select(Product).where(Product.id == payload.product_id))
    ).scalar_one_or_none()
    if not prod:
        raise HTTPException(404, "Producto no encontrado")

    new_item = PortalOrderItem(
        portal_order_id=order_id,
        product_id=prod.id,
        sku=prod.sku,
        name=prod.name,
        image_url=prod.primary_image_url,
        quantity=payload.quantity,
        unit_price=prod.price,
        subtotal=prod.price * payload.quantity,
        notes=payload.notes,
    )
    db.add(new_item)
    await _recalculate_total(db, order_id)
    await _log(
        db,
        order_id,
        "item_added",
        changes={"name": prod.name, "quantity": payload.quantity, "unit_price": float(prod.price)},
        notes=payload.reason,
        visible=True,
    )
    if order.workflow_status in ("received", "under_review"):
        order.workflow_status = "awaiting_customer"
    await db.commit()
    return await _get_order_with_items(db, order_id)


# ── DELETE remove item ────────────────────────────────────────────────────────


@router.delete("/orders/{order_id}/items/{item_id}")
async def remove_item_from_order(
    order_id: uuid.UUID, item_id: uuid.UUID, payload: RemoveItemPayload, db: DBSession
) -> dict:
    items_count = (
        await db.execute(
            select(func.count())
            .select_from(PortalOrderItem)
            .where(
                PortalOrderItem.portal_order_id == order_id,
                PortalOrderItem.is_removed == False,  # noqa: E712
            )
        )
    ).scalar() or 0
    if items_count <= 1:
        raise HTTPException(400, "No se puede quitar el único item. Cancela el pedido.")

    item = (
        await db.execute(
            select(PortalOrderItem).where(
                PortalOrderItem.id == item_id, PortalOrderItem.portal_order_id == order_id
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item no encontrado")

    item.is_removed = True
    item.subtotal = Decimal("0")
    await _recalculate_total(db, order_id)
    await _log(
        db,
        order_id,
        "item_removed",
        changes={"name": item.name, "reason": payload.reason},
        notes=payload.reason,
        visible=True,
    )
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if order and order.workflow_status in ("received", "under_review"):
        order.workflow_status = "awaiting_customer"
    await db.commit()
    return await _get_order_with_items(db, order_id)


# ── POST apply discount ───────────────────────────────────────────────────────


@router.post("/orders/{order_id}/discount")
async def apply_discount(order_id: uuid.UUID, payload: DiscountPayload, db: DBSession) -> dict:
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")
    order.discount_amount = Decimal(str(payload.discount_amount))
    order.discount_reason = payload.reason
    await _log(
        db,
        order_id,
        "discount_applied",
        changes={"discount_amount": payload.discount_amount, "reason": payload.reason},
        visible=True,
    )
    if order.workflow_status in ("received", "under_review"):
        order.workflow_status = "awaiting_customer"
    await db.commit()
    return await _get_order_with_items(db, order_id)


# ── PATCH shipping address ────────────────────────────────────────────────────


@router.patch("/orders/{order_id}/shipping-address")
async def change_shipping_address(
    order_id: uuid.UUID, payload: AddressPayload, db: DBSession
) -> dict:
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")
    old_addr = order.shipping_address
    order.shipping_address = payload.shipping_address
    await _log(
        db,
        order_id,
        "address_changed",
        changes={"before": old_addr, "after": payload.shipping_address},
        visible=True,
    )
    await db.commit()
    return {"ok": True}


# ── PATCH notes ───────────────────────────────────────────────────────────────


@router.patch("/orders/{order_id}/notes")
async def update_order_notes(order_id: uuid.UUID, payload: NotesPayload, db: DBSession) -> dict:
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")
    if payload.internal_notes is not None:
        ts = datetime.now(UTC).strftime("%d/%m %H:%M")
        order.internal_notes = (
            (order.internal_notes or "") + f"\n[{ts}] {payload.internal_notes}"
        ).strip()
    if payload.customer_facing_notes is not None:
        order.customer_facing_notes = payload.customer_facing_notes
        await _log(
            db,
            order_id,
            "notes_updated",
            changes={"customer_facing_notes": payload.customer_facing_notes},
            visible=True,
        )
    await db.commit()
    return {"ok": True}


# ── POST confirm customer approval ────────────────────────────────────────────


@router.post("/orders/{order_id}/confirm-customer-approval")
async def confirm_customer_approval(
    order_id: uuid.UUID, payload: ConfirmApprovalPayload, db: DBSession
) -> dict:
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")
    order.customer_confirmed_changes_at = datetime.now(UTC)
    order.customer_confirmation_channel = payload.channel
    if order.workflow_status == "awaiting_customer":
        order.workflow_status = "ready_to_invoice"
    await _log(
        db,
        order_id,
        f"customer_confirmed_via_{payload.channel}",
        notes=payload.notes,
        visible=False,
    )
    await db.commit()
    return {"ok": True, "workflow_status": order.workflow_status}


# ── POST mark notifications sent ──────────────────────────────────────────────


@router.post("/orders/{order_id}/notifications/mark-sent")
async def mark_notifications_sent(
    order_id: uuid.UUID, payload: MarkSentPayload, db: DBSession
) -> dict:
    now = datetime.now(UTC)
    await db.execute(
        sa_update(ActivityLog)
        .where(
            ActivityLog.entity_id == order_id,
            ActivityLog.entity_type == "order",
            ActivityLog.visible_to_customer == True,  # noqa: E712
            ActivityLog.notification_sent_at == None,  # noqa: E711
        )
        .values(notification_sent_at=now, notification_channel=payload.channel)
    )
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if order and order.workflow_status == "under_review":
        order.workflow_status = "awaiting_customer"
    await db.commit()
    return {"ok": True, "marked_at": now.isoformat()}


# ── POST cancel order ─────────────────────────────────────────────────────────


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: uuid.UUID, payload: CancelOrderPayload, db: DBSession) -> dict:
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")
    if order.workflow_status in ("delivered", "cancelled"):
        raise HTTPException(
            400, f"No se puede cancelar un pedido en estado {order.workflow_status}"
        )
    order.workflow_status = "cancelled"
    order.status = "cancelled"
    order.last_status_change_at = datetime.now(UTC)
    await _log(
        db,
        order_id,
        "cancelled",
        changes={"reason": payload.reason},
        notes=payload.reason,
        visible=True,
    )
    await db.commit()
    return {"ok": True}


# ── Appointment endpoints (sprint-2) ──────────────────────────────────────────


@router.get("/appointments/{appt_id}/detail")
async def get_appointment_detail(appt_id: uuid.UUID, db: DBSession) -> dict:
    from app.models.portal import Pet

    row = (
        await db.execute(
            select(
                Appointment,
                Customer.full_name.label("customer_name"),
                Customer.phone.label("customer_phone"),
                Pet.name.label("pet_name"),
            )
            .join(Customer, Appointment.customer_id == Customer.id, isouter=True)
            .join(Pet, Appointment.pet_id == Pet.id, isouter=True)
            .where(Appointment.id == appt_id)
        )
    ).first()
    if not row:
        raise HTTPException(404, "Cita no encontrada")
    appt, customer_name, customer_phone, pet_name = row
    logs = (
        (
            await db.execute(
                select(ActivityLog)
                .where(ActivityLog.entity_type == "appointment", ActivityLog.entity_id == appt_id)
                .order_by(ActivityLog.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "id": str(appt.id),
        "customer_id": str(appt.customer_id) if appt.customer_id else None,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "pet_name": pet_name,
        "service_type": appt.service_type,
        "scheduled_at": appt.scheduled_at.isoformat(),
        "duration_min": appt.duration_min,
        "status": appt.status,
        "workflow_status": getattr(appt, "workflow_status", appt.status),
        "price": float(appt.price) if appt.price else None,
        "notes": appt.notes,
        "reschedule_reason": getattr(appt, "reschedule_reason", None),
        "reschedule_reason_category": getattr(appt, "reschedule_reason_category", None),
        "proposed_options": getattr(appt, "proposed_options", None),
        "compensation_points": getattr(appt, "compensation_points", 0),
        "created_at": appt.created_at.isoformat(),
        "activity": [
            {
                "action": lg.action,
                "actor_name": lg.actor_name,
                "changes": lg.changes,
                "visible_to_customer": lg.visible_to_customer,
                "created_at": lg.created_at.isoformat(),
            }
            for lg in logs
        ],
    }


@router.patch("/appointments/{appt_id}/reschedule")
async def reschedule_appointment(
    appt_id: uuid.UUID, payload: RescheduleApptPayload, db: DBSession
) -> dict:
    appt = (
        await db.execute(select(Appointment).where(Appointment.id == appt_id))
    ).scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Cita no encontrada")

    old_dt = appt.scheduled_at.isoformat()
    appt.status = "pending"
    if hasattr(appt, "workflow_status"):
        appt.workflow_status = "awaiting_customer_reschedule"
    if hasattr(appt, "rescheduled_from_at"):
        appt.rescheduled_from_at = appt.scheduled_at
    if hasattr(appt, "reschedule_reason_category"):
        appt.reschedule_reason_category = payload.reason_category
    if hasattr(appt, "reschedule_reason"):
        appt.reschedule_reason = payload.reason_notes
    if hasattr(appt, "proposed_options"):
        appt.proposed_options = payload.proposed_options
    if hasattr(appt, "compensation_points"):
        appt.compensation_points = payload.compensation_points

    entry = ActivityLog(
        entity_type="appointment",
        entity_id=appt_id,
        action="rescheduled",
        actor_type="admin",
        changes={
            "original_datetime": old_dt,
            "proposed_options": payload.proposed_options,
            "reason_category": payload.reason_category,
            "compensation_points": payload.compensation_points,
        },
        visible_to_customer=True,
    )
    db.add(entry)
    await db.commit()
    return {
        "ok": True,
        "workflow_status": getattr(appt, "workflow_status", "awaiting_customer_reschedule"),
    }


@router.patch("/appointments/{appt_id}/confirm-choice")
async def confirm_appt_customer_choice(
    appt_id: uuid.UUID, payload: ConfirmApptChoicePayload, db: DBSession
) -> dict:
    appt = (
        await db.execute(select(Appointment).where(Appointment.id == appt_id))
    ).scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Cita no encontrada")
    new_dt = datetime.fromisoformat(payload.chosen_datetime)
    appt.scheduled_at = new_dt
    appt.status = "confirmed"
    appt.confirmed_at = datetime.now(UTC)
    if hasattr(appt, "workflow_status"):
        appt.workflow_status = "confirmed"
    entry = ActivityLog(
        entity_type="appointment",
        entity_id=appt_id,
        action="reschedule_confirmed",
        actor_type="admin",
        changes={"new_datetime": new_dt.isoformat(), "via": payload.customer_confirmed_via},
        visible_to_customer=True,
    )
    db.add(entry)
    await db.commit()
    return {"ok": True}


@router.patch("/appointments/{appt_id}/complete")
async def complete_appointment(appt_id: uuid.UUID, db: DBSession) -> dict:
    appt = (
        await db.execute(select(Appointment).where(Appointment.id == appt_id))
    ).scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Cita no encontrada")
    appt.status = "completed"
    appt.completed_at = datetime.now(UTC)
    if hasattr(appt, "workflow_status"):
        appt.workflow_status = "completed"
    await db.commit()
    return {"ok": True}


@router.patch("/appointments/{appt_id}/no-show")
async def no_show_appointment(appt_id: uuid.UUID, db: DBSession) -> dict:
    appt = (
        await db.execute(select(Appointment).where(Appointment.id == appt_id))
    ).scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Cita no encontrada")
    appt.status = "cancelled"
    if hasattr(appt, "workflow_status"):
        appt.workflow_status = "no_show"
    await db.commit()
    return {"ok": True}


# ── Portal customer: order timeline ──────────────────────────────────────────


@router.get("/orders/{order_id}/timeline-preview")
async def order_timeline_preview(order_id: uuid.UUID, db: DBSession) -> list[dict]:
    """Admin preview del timeline que verá el cliente."""
    logs = (
        (
            await db.execute(
                select(ActivityLog)
                .where(
                    ActivityLog.entity_type == "order",
                    ActivityLog.entity_id == order_id,
                    ActivityLog.visible_to_customer.is_(True),
                )
                .order_by(ActivityLog.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "action": lg.action,
            "changes": lg.changes,
            "notification_sent_at": lg.notification_sent_at.isoformat()
            if lg.notification_sent_at
            else None,
            "created_at": lg.created_at.isoformat(),
        }
        for lg in logs
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# SPRINT 5.2 — Endpoints de notificaciones pendientes (modal WhatsApp admin)
# ═══════════════════════════════════════════════════════════════════════════════


def _notif_dict(n: PendingNotification) -> dict:
    return {
        "id": str(n.id),
        "portal_order_id": str(n.portal_order_id),
        "template_code": n.template_code,
        "rendered_message": n.rendered_message,
        "whatsapp_link": n.whatsapp_link,
        "status": n.status,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "sent_at": n.sent_at.isoformat() if n.sent_at else None,
    }


@router.get("/notifications/pending")
async def list_pending_notifications(
    db: DBSession,
    min_age_minutes: int = Query(default=0, ge=0),
) -> list[dict]:
    """Lista notificaciones WhatsApp pendientes de envío por el admin."""
    q = select(PendingNotification).where(PendingNotification.status == "pending")
    if min_age_minutes > 0:
        cutoff = datetime.now(UTC) - timedelta(minutes=min_age_minutes)
        q = q.where(PendingNotification.created_at <= cutoff)
    q = q.order_by(PendingNotification.created_at.desc())
    rows = (await db.execute(q)).scalars().all()

    result = []
    for n in rows:
        order = (
            await db.execute(select(PortalOrder).where(PortalOrder.id == n.portal_order_id))
        ).scalar_one_or_none()
        customer = None
        if order:
            customer = (
                await db.execute(select(Customer).where(Customer.id == order.customer_id))
            ).scalar_one_or_none()

        d = _notif_dict(n)
        d["customer_name"] = customer.full_name if customer else ""
        d["customer_phone"] = customer.phone if customer else None
        d["invoice_number"] = order.invoice_number if order else None
        result.append(d)

    return result


class MarkNotifPayload(BaseModel):
    channel: str = "whatsapp"


@router.post("/notifications/{notif_id}/mark-sent")
async def mark_notification_sent(
    notif_id: uuid.UUID,
    payload: MarkNotifPayload,
    db: DBSession,
) -> dict:
    """Marca una notificación como enviada manualmente por el admin."""
    notif = (
        await db.execute(select(PendingNotification).where(PendingNotification.id == notif_id))
    ).scalar_one_or_none()
    if not notif:
        raise HTTPException(404, "Notificación no encontrada")

    notif.status = "sent_by_admin"
    notif.sent_at = datetime.now(UTC)

    # Registrar en activity_log del pedido
    await _log(
        db,
        notif.portal_order_id,
        "whatsapp_template_sent",
        changes={"template_code": notif.template_code, "channel": payload.channel},
        visible=False,
    )
    await db.commit()
    return {"ok": True, "status": "sent_by_admin", "sent_at": notif.sent_at.isoformat()}


@router.post("/notifications/{notif_id}/skip")
async def skip_notification(notif_id: uuid.UUID, db: DBSession) -> dict:
    """Omite una notificación pendiente (Diego decidió no enviar este mensaje)."""
    notif = (
        await db.execute(select(PendingNotification).where(PendingNotification.id == notif_id))
    ).scalar_one_or_none()
    if not notif:
        raise HTTPException(404, "Notificación no encontrada")

    notif.status = "skipped"
    await db.commit()
    return {"ok": True, "status": "skipped"}
