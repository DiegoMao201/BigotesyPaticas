"""Admin Portal — endpoints de gestión de pedidos y citas del portal."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy import update as sa_update

from app.api.v1.portal_notifications import notify_customer
from app.deps import DBSession, require_permission
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
from app.services.ga4 import enviar_purchase, enviar_purchase_cita
from app.services.portal_order_actions import (
    InsufficientStockError,
    bridge_to_sales,
    credit_loyalty_points,
    process_referral_reward,
    queue_customer_notification,
)

router = APIRouter(
    prefix="/admin/portal",
    tags=["admin-portal"],
    dependencies=[Depends(require_permission("crm:read"))],
)


# ── schemas ───────────────────────────────────────────────────────────────────


class OrderStatusUpdate(BaseModel):
    status: str
    notes: str | None = None
    cancel_reason: str | None = None


class ApptStatusUpdate(BaseModel):
    status: str
    cancel_reason: str | None = None
    # Al confirmar, el admin dice cuánto se demora el servicio (1-4 h): esas horas quedan
    # bloqueadas en la web y el portal (29-sep-2026).
    duration_min: int | None = Field(default=None, ge=30, le=480)


# ── helpers ───────────────────────────────────────────────────────────────────


def _pet_name_subquery(db_session):
    """Subquery no es necesaria — usamos join directo en las consultas."""
    pass


async def _stock_availability(db: DBSession, product_ids: set[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Suma inventory.Stock.quantity por producto (todas las ubicaciones).

    Una sola query agrupada — evita N+1 al revisar disponibilidad de varios pedidos.
    """
    if not product_ids:
        return {}
    from app.models.inventory import Stock

    rows = (
        await db.execute(
            select(Stock.product_id, func.sum(Stock.quantity))
            .where(Stock.product_id.in_(product_ids))
            .group_by(Stock.product_id)
        )
    ).all()
    return {pid: int(total or 0) for pid, total in rows}


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


@router.get("/customers/recent-logins")
async def recent_logins(db: DBSession) -> list[dict]:
    """Clientes que iniciaron sesión en el portal en las últimas 24h y todavía
    no tienen ningún pedido -- candidatos para el mensaje de bienvenida +
    incentivo de doble puntos en su primer pedido (promo permanente, ver
    credit_loyalty_points()). El envío sigue siendo manual: se arma el link
    de wa.me listo, el admin da clic para enviarlo."""
    now = datetime.now(UTC)

    sessions = (
        await db.execute(
            select(
                PortalSession.customer_id, func.max(PortalSession.created_at).label("last_login")
            )
            .where(
                PortalSession.expires_at > now,
                PortalSession.created_at >= now - timedelta(hours=24),
            )
            .group_by(PortalSession.customer_id)
        )
    ).all()
    if not sessions:
        return []

    customer_ids = [s.customer_id for s in sessions]

    order_counts = dict(
        (
            await db.execute(
                select(PortalOrder.customer_id, func.count())
                .where(PortalOrder.customer_id.in_(customer_ids))
                .group_by(PortalOrder.customer_id)
            )
        ).all()
    )

    contacted_ids = {
        row[0]
        for row in (
            await db.execute(
                select(ActivityLog.entity_id).where(
                    ActivityLog.entity_type == "customer",
                    ActivityLog.action == "login_incentive_sent",
                    ActivityLog.entity_id.in_(customer_ids),
                    ActivityLog.created_at >= now - timedelta(days=30),
                )
            )
        ).all()
    }

    customers = {
        c.id: c
        for c in (await db.execute(select(Customer).where(Customer.id.in_(customer_ids))))
        .scalars()
        .all()
    }

    result = []
    for s in sessions:
        cust = customers.get(s.customer_id)
        if not cust or order_counts.get(s.customer_id, 0) > 0:
            continue  # ya tiene pedidos, no aplica el incentivo de "primer pedido"

        first_name = (cust.full_name or "").split(" ")[0] or ""
        saludo = f"¡Hola {first_name}!" if first_name else "¡Hola!"
        msg = (
            f"{saludo} 🐾 Vimos que entraste a tu portal de Bigotes y Paticas, ¡gracias por "
            f"registrarte! Si haces tu primer pedido, te llevas el DOBLE de puntos de fidelidad 🎉. "
            f"Entra aquí: https://mi.bigotesypaticas.com"
        )
        phone_digits = "".join(ch for ch in (cust.phone or "") if ch.isdigit())
        wa_phone = (
            (phone_digits if phone_digits.startswith("57") else f"57{phone_digits}")
            if phone_digits
            else ""
        )
        wa_link = (
            f"https://wa.me/{wa_phone}?text={quote(msg)}"
            if wa_phone
            else f"https://wa.me/?text={quote(msg)}"
        )

        result.append(
            {
                "customer_id": str(s.customer_id),
                "customer_name": cust.full_name,
                "phone": cust.phone,
                "last_login": s.last_login.isoformat(),
                "message": msg,
                "whatsapp_link": wa_link,
                "already_contacted": s.customer_id in contacted_ids,
            }
        )

    result.sort(key=lambda r: r["last_login"], reverse=True)
    return result


@router.post("/customers/{customer_id}/mark-login-contacted")
async def mark_login_contacted(customer_id: uuid.UUID, db: DBSession) -> dict:
    """Registra que ya se envió el mensaje de bienvenida/incentivo a este
    cliente, para no volver a mostrarlo en la lista los próximos 30 días."""
    db.add(
        ActivityLog(
            entity_type="customer",
            entity_id=customer_id,
            action="login_incentive_sent",
            actor_type="admin",
            notes="Mensaje de bienvenida + doble puntos primer pedido, enviado por WhatsApp",
            visible_to_customer=False,
        )
    )
    await db.commit()
    return {"ok": True}


# ── SOS: moderación de animales encontrados/rescatados ──────────────────
# Los reporta el cliente desde el portal (ver app/api/v1/rescues.py); acá el
# admin solo modera: ve todos los reportes, cierra el evento cuando ya pasó
# tiempo prudente, marca un animal como reunido con su familia, o quita una
# foto inapropiada/duplicada.


def _rescue_admin_out(
    event, reporter_name: str | None, reporter_phone: str | None, animals: list
) -> dict:
    return {
        "id": str(event.id),
        "title": event.title,
        "description": event.description,
        "address": event.address,
        "lat": float(event.lat),
        "lng": float(event.lng),
        "found_at": event.found_at.isoformat(),
        "contact_phone": event.contact_phone,
        "status": event.status,
        "outcome": event.outcome,
        "resolution_note": event.resolution_note,
        "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
        "public_until": event.public_until.isoformat() if event.public_until else None,
        "created_at": event.created_at.isoformat(),
        "reporter_name": reporter_name,
        "reporter_phone": reporter_phone,
        "animal_count": len(animals),
        "unclaimed_count": sum(1 for a in animals if a.status == "unclaimed"),
        "animals": [
            {
                "id": str(a.id),
                "photo_url": a.photo_url,
                "thumb_url": a.thumb_url,
                "species": a.species,
                "description": a.description,
                "status": a.status,
            }
            for a in animals
        ],
    }


@router.get("/rescues")
async def list_rescue_events_admin(
    db: DBSession, status_filter: str = Query(default="all", alias="status")
) -> list[dict]:
    from app.models.community import RescueAnimal, RescueEvent

    q = select(RescueEvent, Customer.full_name, Customer.phone).join(
        Customer, Customer.id == RescueEvent.reporter_customer_id, isouter=True
    )
    if status_filter != "all":
        q = q.where(RescueEvent.status == status_filter)
    rows = (await db.execute(q.order_by(RescueEvent.found_at.desc()))).all()

    event_ids = [r[0].id for r in rows]
    animals_by_event: dict[uuid.UUID, list] = {}
    if event_ids:
        animal_rows = (
            (
                await db.execute(
                    select(RescueAnimal)
                    .where(RescueAnimal.rescue_event_id.in_(event_ids))
                    .order_by(RescueAnimal.sort_order, RescueAnimal.created_at)
                )
            )
            .scalars()
            .all()
        )
        for a in animal_rows:
            animals_by_event.setdefault(a.rescue_event_id, []).append(a)

    return [
        _rescue_admin_out(event, reporter_name, reporter_phone, animals_by_event.get(event.id, []))
        for event, reporter_name, reporter_phone in rows
    ]


@router.get("/rescues/{event_id}")
async def get_rescue_event_admin(event_id: uuid.UUID, db: DBSession) -> dict:
    from app.models.community import RescueAnimal, RescueEvent

    row = (
        await db.execute(
            select(RescueEvent, Customer.full_name, Customer.phone)
            .join(Customer, Customer.id == RescueEvent.reporter_customer_id, isouter=True)
            .where(RescueEvent.id == event_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Evento de rescate no encontrado")
    event, reporter_name, reporter_phone = row

    animals = (
        (
            await db.execute(
                select(RescueAnimal)
                .where(RescueAnimal.rescue_event_id == event_id)
                .order_by(RescueAnimal.sort_order, RescueAnimal.created_at)
            )
        )
        .scalars()
        .all()
    )
    return _rescue_admin_out(event, reporter_name, reporter_phone, animals)


class RescueEventStatusUpdate(BaseModel):
    status: str


@router.patch("/rescues/{event_id}", dependencies=[Depends(require_permission("crm:write"))])
async def update_rescue_event_admin(
    event_id: uuid.UUID, payload: RescueEventStatusUpdate, db: DBSession
) -> dict:
    from app.models.community import RescueEvent

    if payload.status not in {"open", "closed"}:
        raise HTTPException(status_code=422, detail="status debe ser 'open' o 'closed'")
    event = (
        await db.execute(select(RescueEvent).where(RescueEvent.id == event_id))
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Evento de rescate no encontrado")
    event.status = payload.status
    await db.commit()
    return {"ok": True, "status": event.status}


class RescueAnimalStatusUpdate(BaseModel):
    status: str


@router.patch(
    "/rescues/{event_id}/animals/{animal_id}",
    dependencies=[Depends(require_permission("crm:write"))],
)
async def update_rescue_animal_admin(
    event_id: uuid.UUID, animal_id: uuid.UUID, payload: RescueAnimalStatusUpdate, db: DBSession
) -> dict:
    from app.models.community import RescueAnimal

    if payload.status not in {"unclaimed", "reunited"}:
        raise HTTPException(status_code=422, detail="status debe ser 'unclaimed' o 'reunited'")
    animal = (
        await db.execute(
            select(RescueAnimal).where(
                RescueAnimal.id == animal_id, RescueAnimal.rescue_event_id == event_id
            )
        )
    ).scalar_one_or_none()
    if not animal:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    animal.status = payload.status
    await db.commit()
    return {"ok": True, "status": animal.status}


@router.delete(
    "/rescues/{event_id}/animals/{animal_id}",
    dependencies=[Depends(require_permission("crm:write"))],
)
async def delete_rescue_animal_admin(
    event_id: uuid.UUID, animal_id: uuid.UUID, db: DBSession
) -> dict:
    from app.models.community import RescueAnimal

    animal = (
        await db.execute(
            select(RescueAnimal).where(
                RescueAnimal.id == animal_id, RescueAnimal.rescue_event_id == event_id
            )
        )
    ).scalar_one_or_none()
    if not animal:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    await db.delete(animal)
    await db.commit()
    return {"ok": True}


# ── Foro de adopción: moderación ─────────────────────────────────────────
# Igual que rescues: lo publica el cliente desde el portal (adoption.py);
# acá el admin solo modera.


def _adoption_admin_out(listing, customer_name: str | None, customer_phone: str | None) -> dict:
    # Publicado desde el portal (tiene cuenta) -> nombre/tel de crm.customers.
    # Publicado desde el foro rápido del store (sin cuenta) -> listing.reporter_name
    # + listing.contact_phone (lo que la persona escribió directamente).
    is_quick_post = listing.reporter_customer_id is None
    return {
        "id": str(listing.id),
        "post_type": listing.post_type,
        "title": listing.title,
        "description": listing.description,
        "species": listing.species,
        "breed": listing.breed,
        "address": listing.address,
        "lat": float(listing.lat) if listing.lat is not None else None,
        "lng": float(listing.lng) if listing.lng is not None else None,
        "delivery_notes": listing.delivery_notes,
        "contact_phone": listing.contact_phone,
        "photos": listing.photos or [],
        "status": listing.status,
        "outcome": listing.outcome,
        "outcome_note": listing.outcome_note,
        "outcome_at": listing.outcome_at.isoformat() if listing.outcome_at else None,
        "public_until": listing.public_until.isoformat() if listing.public_until else None,
        "created_at": listing.created_at.isoformat(),
        "reporter_name": customer_name or listing.reporter_name,
        "reporter_phone": customer_phone or (listing.contact_phone if is_quick_post else None),
        "is_quick_post": is_quick_post,
    }


@router.get("/adoption-listings")
async def list_adoption_listings_admin(
    db: DBSession,
    status_filter: str = Query(default="all", alias="status"),
    q_search: str | None = Query(default=None, alias="q"),
) -> list[dict]:
    """`q` busca por nombre o teléfono (del que reportó) -- para ubicar
    rápido la publicación cuando alguien escribe agradeciendo por WhatsApp."""
    from app.models.community import AdoptionListing

    q = select(AdoptionListing, Customer.full_name, Customer.phone).join(
        Customer, Customer.id == AdoptionListing.reporter_customer_id, isouter=True
    )
    if status_filter != "all":
        q = q.where(AdoptionListing.status == status_filter)
    if q_search:
        term = f"%{q_search.strip()}%"
        q = q.where(
            (AdoptionListing.reporter_name.ilike(term))
            | (AdoptionListing.contact_phone.ilike(term))
            | (Customer.full_name.ilike(term))
            | (Customer.phone.ilike(term))
        )
    rows = (await db.execute(q.order_by(AdoptionListing.created_at.desc()))).all()
    return [_adoption_admin_out(listing, name, phone) for listing, name, phone in rows]


class AdoptionListingStatusUpdate(BaseModel):
    status: str


@router.patch(
    "/adoption-listings/{listing_id}", dependencies=[Depends(require_permission("crm:write"))]
)
async def update_adoption_listing_admin(
    listing_id: uuid.UUID, payload: AdoptionListingStatusUpdate, db: DBSession
) -> dict:
    from app.models.community import AdoptionListing

    if payload.status not in {"open", "closed"}:
        raise HTTPException(status_code=422, detail="status debe ser 'open' o 'closed'")
    listing = (
        await db.execute(select(AdoptionListing).where(AdoptionListing.id == listing_id))
    ).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    listing.status = payload.status
    await db.commit()
    return {"ok": True, "status": listing.status}


class AdoptionOutcomeUpdate(BaseModel):
    outcome: str
    outcome_note: str | None = None


@router.patch(
    "/adoption-listings/{listing_id}/outcome",
    dependencies=[Depends(require_permission("crm:write"))],
)
async def update_adoption_outcome_admin(
    listing_id: uuid.UUID, payload: AdoptionOutcomeUpdate, db: DBSession
) -> dict:
    """Marca la publicación como 'matched' (encontró hogar/adoptante) -- se
    exhibe como historia de éxito en el store antes de cerrarse."""
    from app.models.community import AdoptionListing

    if payload.outcome not in {"pending", "matched"}:
        raise HTTPException(status_code=422, detail="outcome debe ser 'pending' o 'matched'")
    listing = (
        await db.execute(select(AdoptionListing).where(AdoptionListing.id == listing_id))
    ).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    from app.services import community_lifecycle as lc

    listing.outcome = payload.outcome
    listing.outcome_note = (payload.outcome_note or "").strip() or None
    if payload.outcome == "matched":
        listing.outcome_at, listing.public_until = lc.public_window()
    else:
        listing.outcome_at = None
        listing.public_until = None
    await db.commit()
    _ping_indexnow(lc.resolved_urls("adoption", listing.id))
    return {"ok": True, "outcome": listing.outcome, "public_until": listing.public_until}


@router.delete(
    "/adoption-listings/{listing_id}", dependencies=[Depends(require_permission("crm:write"))]
)
async def delete_adoption_listing_admin(listing_id: uuid.UUID, db: DBSession) -> dict:
    from app.models.community import AdoptionListing

    listing = (
        await db.execute(select(AdoptionListing).where(AdoptionListing.id == listing_id))
    ).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    await db.delete(listing)
    await db.commit()
    return {"ok": True}


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
    orders = [order for order, _, _ in rows]

    # Ítems por pedido (tabla nueva) — para pedidos legado sin filas ahí, se usa
    # el producto/cantidad guardados directo en PortalOrder como fallback, igual
    # que en _order_render_data() / bridge_to_sales().
    order_ids = [o.id for o in orders]
    items_by_order: dict[uuid.UUID, list[PortalOrderItem]] = {}
    if order_ids:
        item_rows = (
            (
                await db.execute(
                    select(PortalOrderItem).where(
                        PortalOrderItem.portal_order_id.in_(order_ids),
                        PortalOrderItem.is_removed.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        for it in item_rows:
            items_by_order.setdefault(it.portal_order_id, []).append(it)

    all_product_ids: set[uuid.UUID] = set()
    for o in orders:
        items = items_by_order.get(o.id)
        if items:
            all_product_ids.update(i.product_id for i in items if i.product_id)
        elif o.product_id:
            all_product_ids.add(o.product_id)
    stock_by_product = await _stock_availability(db, all_product_ids)

    def _has_stock_issues(order: PortalOrder) -> bool:
        items = items_by_order.get(order.id)
        if items:
            checks = [(i.product_id, i.quantity) for i in items]
        elif order.product_id:
            checks = [(order.product_id, order.quantity)]
        else:
            return False
        for pid, qty in checks:
            available = stock_by_product.get(pid)
            if available is not None and available < qty:
                return True
        return False

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
                "workflow_status": order.workflow_status,
                "invoice_number": order.invoice_number,
                "sales_order_id": str(order.sales_order_id) if order.sales_order_id else None,
                "notes": order.notes,
                "created_at": order.created_at.isoformat(),
                "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
                "points_awarded": order.points_awarded,
                "has_stock_issues": _has_stock_issues(order),
                # 'web' = entró por el checkout de la tienda (sin cuenta); None = portal
                "origen": order.origen,
                # Pago en línea (5-oct-2026). Sin esto, en la lista un pedido YA
                # COBRADO se ve igual que uno que todavía puede no pagarse nunca, y
                # son dos cosas muy distintas: uno hay que alistarlo ya, el otro no.
                "payment_status": order.payment_status,
                "payment_method": order.payment_method,
                "order_reference": order.order_reference,
                "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            }
        )
    return result


# Estados de workflow_status que aún requieren gestión del admin (todo lo que no es terminal)
PENDING_WORKFLOW_STATUSES = [
    "received",
    "under_review",
    "awaiting_customer",
    "ready_to_invoice",
    "invoiced",
    "in_preparation",
    "ready_for_delivery",
    "in_transit",
]


@router.get("/orders/pending-summary")
async def pending_orders_summary(db: DBSession) -> dict:
    """Resumen liviano para el aviso global de pedidos del portal sin gestionar."""
    rows = (
        await db.execute(
            select(PortalOrder.id, PortalOrder.created_at)
            .where(PortalOrder.workflow_status.in_(PENDING_WORKFLOW_STATUSES))
            .order_by(PortalOrder.created_at.desc())
        )
    ).all()
    return {
        "count": len(rows),
        "newest_created_at": rows[0].created_at.isoformat() if rows else None,
    }


@router.patch("/orders/{order_id}", dependencies=[Depends(require_permission("crm:write"))])
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
        try:
            await bridge_to_sales(order, db)
        except InsufficientStockError as e:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "No se puede facturar: falta stock en uno o más productos.",
                    "shortages": e.shortages,
                },
            ) from e
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
        # Aquí —y solo aquí— la venta es real: se le cuenta a Google como `purchase`.
        # Vale para los pedidos de la tienda web y para los del portal: son la misma
        # tabla y el mismo botón. Los de la web traen el client_id de la cookie _ga, así
        # que además quedan atribuidos a la búsqueda o al anuncio que trajo al cliente.
        # Nunca tumba la entrega: enviar_purchase() no lanza excepciones.
        await enviar_purchase(db, order)
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


# ── Agenda del admin (29-sep-2026) ───────────────────────────────────────────
# Diego: "el admin no tiene generador de citas… estamos desconectados de la gente que
# entra por la app y las que agendan en tienda o llaman". Una sola agenda: lo que agenda
# o acepta el admin bloquea esas horas en la web y el portal (misma regla: conflictos()).


def _ya_empezo(appt: Appointment, accion: str) -> None:
    """29-sep-2026: una cita reagendada para mañana quedó 'completada' por error (el botón
    Completar salía junto a Confirmar) y desapareció de la agenda. Completar o marcar
    'no asistió' solo tiene sentido cuando la hora de la cita ya llegó."""
    if appt.scheduled_at > datetime.now(UTC):
        from app.api.v1.portal_appointments import _TZ_CO

        cuando = appt.scheduled_at.astimezone(_TZ_CO).strftime("%d/%m a las %H:%M")
        raise HTTPException(
            409,
            f"No se puede {accion} todavía: la cita es el {cuando}. "
            "Completar es para cuando el servicio ya se hizo.",
        )


def _origen_cita(notes: str | None) -> str:
    n = notes or ""
    if "Reservó en la web" in n:
        return "web"
    if "Agendada por el admin" in n:
        return "admin"
    return "portal"


@router.get("/appointments/agenda")
async def agenda_del_dia(db: DBSession, date: str = Query(...)) -> dict:
    """Citas pendientes y confirmadas de un día, con su bloque de horas."""
    from datetime import date as _date

    from app.api.v1.portal_appointments import _CLOSE_H, _OPEN_H, _TZ_CO, bloqueos_entre
    from app.models.portal import Pet

    try:
        d = _date.fromisoformat(date)
    except ValueError as exc:
        raise HTTPException(422, "Fecha inválida") from exc
    ini = datetime(d.year, d.month, d.day, tzinfo=_TZ_CO)
    rows = (
        await db.execute(
            select(Appointment, Customer.full_name, Customer.phone, Pet.name, Pet.species)
            .join(Customer, Appointment.customer_id == Customer.id, isouter=True)
            .join(Pet, Appointment.pet_id == Pet.id, isouter=True)
            .where(
                Appointment.scheduled_at >= ini - timedelta(hours=8),
                Appointment.scheduled_at < ini + timedelta(days=1),
                Appointment.status.in_(["pending", "confirmed", "completed"]),
            )
            .order_by(Appointment.scheduled_at)
        )
    ).all()
    bloqueos = await bloqueos_entre(db, ini, ini + timedelta(days=1))
    citas = []
    for a, nombre, tel, mascota, especie in rows:
        local = a.scheduled_at.astimezone(_TZ_CO)
        fin = local + timedelta(minutes=a.duration_min or 60)
        if fin <= ini:
            continue
        en_bloqueo = a.status != "completed" and any(b.inicio < fin and b.fin > local for b in bloqueos)
        citas.append({
            "id": str(a.id),
            "inicio": local.strftime("%H:%M"),
            "fin": fin.strftime("%H:%M"),
            "duration_min": a.duration_min,
            "status": a.status,
            "customer_name": nombre,
            "customer_phone": tel,
            "pet_name": mascota,
            "species": especie,
            "origen": _origen_cita(a.notes),
            "notes": a.notes,
            "en_bloqueo": en_bloqueo,
        })
    fin_dia = ini + timedelta(days=1)
    return {"date": date, "abre": f"{_OPEN_H:02d}:00", "cierra": f"{_CLOSE_H:02d}:00",
            "cerrado": d.weekday() == 6, "citas": citas,
            "bloqueos": [_bloqueo_out(b, ini, fin_dia) for b in bloqueos]}


# ── Bloqueos de agenda (29-sep-2026) ─────────────────────────────────────────
# "bloquear días… el groomer no está, se va de vacaciones, se enfermó… así el portal y la
# web no tendrán disponibles esos días o esas horas… y no que por estar bloqueado no me
# deje moverme en la agenda". La web y el portal los respetan; el admin puede agendar
# encima. Al bloquear se devuelven las citas afectadas para reagendarlas y avisar.


def _bloqueo_out(b, dia_ini: datetime | None = None, dia_fin: datetime | None = None) -> dict:
    from app.api.v1.portal_appointments import _TZ_CO

    ini = b.inicio.astimezone(_TZ_CO)
    fin = b.fin.astimezone(_TZ_CO)
    out = {
        "id": str(b.id),
        "inicio": ini.isoformat(),
        "fin": fin.isoformat(),
        "motivo": b.motivo,
        "dia_completo": ini.hour == 0 and ini.minute == 0 and fin.hour == 0 and fin.minute == 0,
    }
    if dia_ini is not None and dia_fin is not None:  # recortado al día que se mira
        out["desde_hora"] = max(ini, dia_ini.astimezone(_TZ_CO)).strftime("%H:%M") if ini > dia_ini else "00:00"
        out["hasta_hora"] = fin.strftime("%H:%M") if fin < dia_fin else "24:00"
    return out


class BloqueoIn(BaseModel):
    fecha_desde: str
    fecha_hasta: str | None = None      # días completos: hasta este día inclusive
    hora_desde: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")  # solo horas de un día
    hora_hasta: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    motivo: str | None = Field(default=None, max_length=200)


async def _citas_afectadas(db, inicio: datetime, fin: datetime) -> list[dict]:
    from app.api.v1.portal_appointments import _TZ_CO
    from app.models.portal import Pet

    rows = (
        await db.execute(
            select(Appointment, Customer.full_name, Customer.phone, Pet.name)
            .join(Customer, Appointment.customer_id == Customer.id, isouter=True)
            .join(Pet, Appointment.pet_id == Pet.id, isouter=True)
            .where(
                Appointment.scheduled_at < fin,
                Appointment.scheduled_at >= inicio - timedelta(hours=8),
                Appointment.status.in_(["pending", "confirmed"]),
            )
            .order_by(Appointment.scheduled_at)
        )
    ).all()
    out = []
    for a, nombre, tel, mascota in rows:
        if a.scheduled_at + timedelta(minutes=a.duration_min or 60) <= inicio:
            continue
        local = a.scheduled_at.astimezone(_TZ_CO)
        out.append({"id": str(a.id), "cuando": local.isoformat(), "status": a.status,
                    "customer_name": nombre, "customer_phone": tel, "pet_name": mascota})
    return out


@router.get("/appointments/bloqueos")
async def listar_bloqueos(db: DBSession) -> list[dict]:
    """Bloqueos vigentes y futuros."""
    from app.models.portal import AgendaBloqueo

    rows = (
        await db.execute(
            select(AgendaBloqueo).where(AgendaBloqueo.fin > datetime.now(UTC)).order_by(AgendaBloqueo.inicio)
        )
    ).scalars().all()
    out = []
    for b in rows:
        d = _bloqueo_out(b)
        d["afectadas"] = await _citas_afectadas(db, b.inicio, b.fin)
        out.append(d)
    return out


@router.post("/appointments/bloqueos", status_code=201, dependencies=[Depends(require_permission("crm:write"))])
async def crear_bloqueo(payload: BloqueoIn, db: DBSession) -> dict:
    from datetime import date as _date

    from app.api.v1.portal_appointments import _TZ_CO
    from app.models.portal import AgendaBloqueo

    try:
        d1 = _date.fromisoformat(payload.fecha_desde)
        d2 = _date.fromisoformat(payload.fecha_hasta) if payload.fecha_hasta else d1
    except ValueError as exc:
        raise HTTPException(422, "Fecha inválida") from exc
    if payload.hora_desde and payload.hora_hasta:
        h1 = [int(x) for x in payload.hora_desde.split(":")]
        h2 = [int(x) for x in payload.hora_hasta.split(":")]
        inicio = datetime(d1.year, d1.month, d1.day, h1[0], h1[1], tzinfo=_TZ_CO)
        fin = datetime(d1.year, d1.month, d1.day, h2[0], h2[1], tzinfo=_TZ_CO)
        if fin <= inicio:
            raise HTTPException(422, "La hora final debe ser después de la inicial")
    else:
        if d2 < d1:
            raise HTTPException(422, "La fecha final debe ser igual o posterior a la inicial")
        if (d2 - d1).days > 120:
            raise HTTPException(422, "Bloquea máximo 4 meses de una vez")
        inicio = datetime(d1.year, d1.month, d1.day, tzinfo=_TZ_CO)
        fin = datetime(d2.year, d2.month, d2.day, tzinfo=_TZ_CO) + timedelta(days=1)
    b = AgendaBloqueo(inicio=inicio, fin=fin, motivo=(payload.motivo or "").strip() or None)
    db.add(b)
    await db.flush()
    afectadas = await _citas_afectadas(db, inicio, fin)
    await db.commit()
    out = _bloqueo_out(b)
    out["afectadas"] = afectadas
    return out


@router.delete("/appointments/bloqueos/{bloqueo_id}", dependencies=[Depends(require_permission("crm:write"))])
async def quitar_bloqueo(bloqueo_id: uuid.UUID, db: DBSession) -> dict:
    from app.models.portal import AgendaBloqueo

    b = (await db.execute(select(AgendaBloqueo).where(AgendaBloqueo.id == bloqueo_id))).scalar_one_or_none()
    if not b:
        raise HTTPException(404, "Bloqueo no encontrado")
    await db.delete(b)
    await db.commit()
    return {"ok": True}


@router.get("/appointments/free-starts")
async def horas_libres(
    db: DBSession,
    date: str = Query(...),
    duration: int = Query(120, ge=30, le=480),
    excluir: uuid.UUID | None = Query(None),  # al reagendar, la cita misma no cuenta
) -> dict:
    from datetime import date as _date

    from app.api.v1.portal_appointments import horas_libres_admin

    try:
        d = _date.fromisoformat(date)
    except ValueError as exc:
        raise HTTPException(422, "Fecha inválida") from exc
    libres, bloqueadas = await horas_libres_admin(db, d, duration, excluir)
    return {"date": date, "duration": duration, "starts": libres, "bloqueadas": bloqueadas}


class AdminApptCreate(BaseModel):
    date: str
    time: str = Field(pattern=r"^\d{2}:\d{2}$")
    duration_min: int = Field(ge=30, le=480)
    owner_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=20)
    pet_name: str = Field(min_length=1, max_length=60)
    species: str = Field(default="perro", pattern="^(perro|gato)$")
    origen: str = Field(default="tienda", pattern="^(tienda|llamada|whatsapp)$")
    notes: str | None = Field(default=None, max_length=500)


@router.post("/appointments", status_code=201, dependencies=[Depends(require_permission("crm:write"))])
async def crear_cita_admin(payload: AdminApptCreate, db: DBSession) -> dict:
    """El admin agenda (en tienda, por llamada o WhatsApp): queda CONFIRMADA y bloquea
    esas horas para la web y el portal."""
    from datetime import date as _date

    from app.api.v1.portal_appointments import _TZ_CO, conflictos, describir_cruce
    from app.services.citas import cliente_por_telefono, digitos_telefono, limpiar, mascota_de

    try:
        d = _date.fromisoformat(payload.date)
        hh, mm = (int(x) for x in payload.time.split(":"))
        inicio = datetime(d.year, d.month, d.day, hh, mm, tzinfo=_TZ_CO)
    except ValueError as exc:
        raise HTTPException(422, "Fecha u hora inválida") from exc
    if inicio < datetime.now(_TZ_CO) - timedelta(minutes=30):
        raise HTTPException(422, "Esa hora ya pasó")
    tel = digitos_telefono(payload.phone)
    if not tel:
        raise HTTPException(422, "Escribe un celular válido (10 dígitos, p. ej. 311 660 2399)")
    cruces = await conflictos(db, inicio, payload.duration_min)
    if cruces:
        raise HTTPException(409, f"{describir_cruce(cruces)}. Elige otra hora o una duración menor.")

    ahora = datetime.now(_TZ_CO)
    nombre = limpiar(payload.owner_name)
    mascota = limpiar(payload.pet_name)
    cliente = await cliente_por_telefono(db, nombre, tel, f"agenda_admin_{payload.origen}", ahora, consentimiento=False)
    pet = await mascota_de(db, cliente, mascota, payload.species, "Registrada al agendar en el admin")
    etiqueta = {"tienda": "en la tienda", "llamada": "por llamada", "whatsapp": "por WhatsApp"}[payload.origen]
    notas = [f"Agendada por el admin ({etiqueta})", f"Tel: {tel}",
             f"{'Perro' if payload.species == 'perro' else 'Gato'}: {mascota}"]
    if payload.notes and payload.notes.strip():
        notas.append(payload.notes.strip())
    appt = Appointment(
        pet_id=pet.id,
        customer_id=cliente.id,
        service_type="grooming",
        scheduled_at=inicio,
        duration_min=payload.duration_min,
        status="confirmed",
        confirmed_at=datetime.now(UTC),
        notes=" · ".join(notas),
    )
    db.add(appt)
    await db.commit()
    return {"ok": True, "id": str(appt.id), "customer_name": cliente.full_name}


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


@router.patch("/appointments/{appt_id}", dependencies=[Depends(require_permission("crm:write"))])
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
    if new_status == "completed":
        _ya_empezo(appt, "completar")

    if new_status in ("confirmed", "pending") and (payload.duration_min or new_status == "confirmed"):
        from app.api.v1.portal_appointments import conflictos, describir_cruce

        dur = payload.duration_min or appt.duration_min
        cruces = await conflictos(db, appt.scheduled_at, dur, excluir=appt.id)
        if cruces:
            raise HTTPException(
                status_code=409,
                detail=f"{describir_cruce(cruces)}. Cambia la duración o reacomoda el horario.",
            )
        appt.duration_min = dur

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
    new_quantity: int = Field(ge=1, le=999)
    reason: str | None = None


class EditPricePayload(BaseModel):
    new_unit_price: float = Field(ge=0)
    reason: str


class SubstitutePayload(BaseModel):
    new_product_id: uuid.UUID
    new_quantity: int | None = Field(default=None, ge=1, le=999)
    reason: str


class AddItemPayload(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, le=999)
    notes: str | None = None
    reason: str | None = None


class RemoveItemPayload(BaseModel):
    reason: str


class DiscountPayload(BaseModel):
    discount_amount: float = Field(ge=0)
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

# Pedido editable (items, precio, descuento) solo ANTES de facturar: después ya
# existe la venta en sales.orders y el inventario se descontó; editar el pedido
# del portal dejaría la factura y el pedido diciendo cosas distintas.
NON_EDITABLE_STATUSES = {
    "invoiced", "in_preparation", "ready_for_delivery", "in_transit",
    "delivered", "cancelled", "returned",
}

# Acciones que cambian lo que el cliente pidió: si no se le han avisado, el admin
# ve "N cambios que el cliente no conoce" y decide si pedir aprobación o no.
CHANGE_ACTIONS = (
    "item_quantity_changed", "item_substituted", "item_added", "item_removed",
    "item_price_changed", "discount_applied", "address_changed",
)


def _is_editable(order: PortalOrder) -> bool:
    return not order.sales_order_id and (order.workflow_status or "received") not in NON_EDITABLE_STATUSES


def _ensure_editable(order: PortalOrder) -> None:
    if not _is_editable(order):
        raise HTTPException(
            409,
            "El pedido ya está facturado o cerrado: no se puede cambiar. "
            "Si hay que corregirlo, cancélalo (devuelve el inventario) y créalo de nuevo.",
        )


async def _load_order(db: DBSession, order_id: uuid.UUID) -> PortalOrder:
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")
    return order


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

    stock_by_product = await _stock_availability(db, {i.product_id for i in items if i.product_id})

    items_data = []
    has_stock_issues = False
    for i in items:
        available = stock_by_product.get(i.product_id) if i.product_id else None
        stock_ok = available is None or available >= i.quantity
        if not stock_ok:
            has_stock_issues = True
        items_data.append(
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
                "available_stock": available,
                "stock_ok": stock_ok,
            }
        )

    subtotal = sum(float(i.subtotal or 0) for i in items)
    discount = float(order.discount_amount or 0)
    shipping = 0.0  # portal: domicilio gratis en TODO pedido (Diego 27-sep-2026, para incentivar el portal)
    total = subtotal - discount + shipping

    customer = (
        (
            await db.execute(select(Customer).where(Customer.id == order.customer_id))
        ).scalar_one_or_none()
        if order.customer_id
        else None
    )

    # Cambios hechos por el admin que el cliente todavía no conoce
    unsent_q = select(ActivityLog).where(
        ActivityLog.entity_type == "order",
        ActivityLog.entity_id == order_id,
        ActivityLog.visible_to_customer.is_(True),
        ActivityLog.notification_sent_at.is_(None),
        ActivityLog.action.in_(CHANGE_ACTIONS),
    )
    if order.customer_confirmed_changes_at:
        unsent_q = unsent_q.where(ActivityLog.created_at > order.customer_confirmed_changes_at)
    unsent = (await db.execute(unsent_q.order_by(ActivityLog.created_at))).scalars().all()

    return {
        "id": str(order.id),
        "is_editable": _is_editable(order),
        "sales_order_id": str(order.sales_order_id) if order.sales_order_id else None,
        "unsent_changes": [
            {"action": lg.action, "changes": lg.changes, "notes": lg.notes,
             "created_at": lg.created_at.isoformat()}
            for lg in unsent
        ],
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
        "has_stock_issues": has_stock_issues,
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
    "received": ["under_review", "awaiting_customer", "ready_to_invoice", "cancelled"],
    "under_review": ["awaiting_customer", "ready_to_invoice", "cancelled"],
    "awaiting_customer": ["ready_to_invoice", "under_review", "cancelled"],
    # si se edita después de aprobado, se puede volver a pedir aprobación o revisar
    "ready_to_invoice": ["invoiced", "awaiting_customer", "under_review", "cancelled"],
    "invoiced": ["in_preparation", "cancelled"],
    "in_preparation": ["ready_for_delivery"],
    "ready_for_delivery": ["in_transit"],
    "in_transit": ["delivered"],
    "delivered": [],
    "cancelled": [],
    "returned": [],
}


@router.patch(
    "/orders/{order_id}/workflow", dependencies=[Depends(require_permission("crm:write"))]
)
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

    if new == "cancelled":
        await _reverse_invoice(order, payload.internal_notes or "cancelado desde el flujo", db)
        order.status = "cancelled"

    # ── Portar lógica del endpoint viejo ──────────────────────────────────────
    if new == "invoiced":
        try:
            await bridge_to_sales(order, db)
        except InsufficientStockError as e:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "No se puede facturar: falta stock en uno o más productos.",
                    "shortages": e.shortages,
                },
            ) from e

    if new == "delivered":
        await credit_loyalty_points(order, db)
        await process_referral_reward(order, db)
        # Este es el botón "Marcar entregado" del admin, y este es el único momento en
        # que la venta es real. Aquí se le cuenta a Google como `purchase`: sirve igual
        # para los pedidos de la tienda web (que traen el client_id de la cookie _ga y
        # quedan atribuidos a la búsqueda o al anuncio) y para los del portal. Si Google
        # está caído esto devuelve False y no estorba: entregar nunca puede fallar.
        await enviar_purchase(db, order)

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


@router.patch(
    "/orders/{order_id}/items/{item_id}/quantity",
    dependencies=[Depends(require_permission("crm:write"))],
)
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
    _ensure_editable(await _load_order(db, order_id))

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
    # Ya NO pasa sola a "esperando cliente" (Diego 28-sep-2026: "no puedo modificar el
    # pedido sin darle un aprobado"). El cambio queda como "sin avisar" y el admin
    # decide: pedir aprobación, solo avisar, o seguir si ya lo acordó con el cliente.
    await db.commit()
    return await _get_order_with_items(db, order_id)


# ── PATCH item unit price ─────────────────────────────────────────────────────


@router.patch(
    "/orders/{order_id}/items/{item_id}/price",
    dependencies=[Depends(require_permission("crm:write"))],
)
async def edit_item_price(
    order_id: uuid.UUID, item_id: uuid.UUID, payload: EditPricePayload, db: DBSession
) -> dict:
    item = (
        await db.execute(
            select(PortalOrderItem).where(
                PortalOrderItem.id == item_id,
                PortalOrderItem.portal_order_id == order_id,
                PortalOrderItem.is_removed.is_(False),
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item no encontrado")
    _ensure_editable(await _load_order(db, order_id))

    old_price = float(item.unit_price or 0)
    item.unit_price = Decimal(str(payload.new_unit_price))
    item.subtotal = item.unit_price * item.quantity
    await _recalculate_total(db, order_id)
    await _log(
        db,
        order_id,
        "item_price_changed",
        changes={
            "item": item.name,
            "unit_price": {"before": old_price, "after": payload.new_unit_price},
            "reason": payload.reason,
        },
        notes=payload.reason,
        visible=True,
    )
    await db.commit()
    return await _get_order_with_items(db, order_id)


# ── POST substitute item ──────────────────────────────────────────────────────


@router.post(
    "/orders/{order_id}/items/{item_id}/substitute",
    dependencies=[Depends(require_permission("crm:write"))],
)
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
    _ensure_editable(await _load_order(db, order_id))

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
    await db.commit()
    return await _get_order_with_items(db, order_id)


# ── POST add item ─────────────────────────────────────────────────────────────


@router.post("/orders/{order_id}/items", dependencies=[Depends(require_permission("crm:write"))])
async def add_item_to_order(order_id: uuid.UUID, payload: AddItemPayload, db: DBSession) -> dict:
    from app.models.catalog import Product

    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")
    _ensure_editable(order)

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
    await db.commit()
    return await _get_order_with_items(db, order_id)


# ── DELETE remove item ────────────────────────────────────────────────────────


@router.delete(
    "/orders/{order_id}/items/{item_id}", dependencies=[Depends(require_permission("crm:write"))]
)
async def remove_item_from_order(
    order_id: uuid.UUID, item_id: uuid.UUID, payload: RemoveItemPayload, db: DBSession
) -> dict:
    _ensure_editable(await _load_order(db, order_id))
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
    await db.commit()
    return await _get_order_with_items(db, order_id)


# ── POST apply discount ───────────────────────────────────────────────────────


@router.post("/orders/{order_id}/discount", dependencies=[Depends(require_permission("crm:write"))])
async def apply_discount(order_id: uuid.UUID, payload: DiscountPayload, db: DBSession) -> dict:
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")
    _ensure_editable(order)
    subtotal = await _recalculate_total(db, order_id)
    if payload.discount_amount > subtotal:
        raise HTTPException(400, f"El descuento no puede ser mayor que el subtotal (${int(subtotal):,})".replace(",", "."))
    order.discount_amount = Decimal(str(payload.discount_amount))
    order.discount_reason = payload.reason
    await _log(
        db,
        order_id,
        "discount_applied",
        changes={"discount_amount": payload.discount_amount, "reason": payload.reason},
        visible=True,
    )
    await db.commit()
    return await _get_order_with_items(db, order_id)


# ── PATCH shipping address ────────────────────────────────────────────────────


@router.patch(
    "/orders/{order_id}/shipping-address", dependencies=[Depends(require_permission("crm:write"))]
)
async def change_shipping_address(
    order_id: uuid.UUID, payload: AddressPayload, db: DBSession
) -> dict:
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")
    if (order.workflow_status or "received") in ("delivered", "cancelled", "returned"):
        raise HTTPException(409, "El pedido ya está cerrado: no se puede cambiar la dirección")
    if not payload.shipping_address.strip():
        raise HTTPException(400, "La dirección no puede quedar vacía")
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


@router.patch("/orders/{order_id}/notes", dependencies=[Depends(require_permission("crm:write"))])
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


@router.post(
    "/orders/{order_id}/confirm-customer-approval",
    dependencies=[Depends(require_permission("crm:write"))],
)
async def confirm_customer_approval(
    order_id: uuid.UUID, payload: ConfirmApprovalPayload, db: DBSession
) -> dict:
    order = (
        await db.execute(select(PortalOrder).where(PortalOrder.id == order_id))
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")
    now = datetime.now(UTC)
    # Los cambios quedan "avisados": el cliente los aprobó por este canal
    await db.execute(
        sa_update(ActivityLog)
        .where(
            ActivityLog.entity_id == order_id,
            ActivityLog.entity_type == "order",
            ActivityLog.visible_to_customer.is_(True),
            ActivityLog.notification_sent_at.is_(None),
        )
        .values(notification_sent_at=now, notification_channel=payload.channel)
    )
    order.customer_confirmed_changes_at = now
    order.customer_confirmation_channel = payload.channel
    # Aprobar sirve desde cualquier punto antes de facturar (ya se habló con el cliente)
    if (order.workflow_status or "received") in ("received", "under_review", "awaiting_customer"):
        order.workflow_status = "ready_to_invoice"
        order.last_status_change_at = now
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


@router.post(
    "/orders/{order_id}/notifications/mark-sent",
    dependencies=[Depends(require_permission("crm:write"))],
)
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


async def _reverse_invoice(order: PortalOrder, reason: str, db: DBSession) -> None:
    """Si el pedido ya se facturó, anula la venta y devuelve el inventario.
    Mismo patrón que la cancelación del POS (sales.py cancel_order). Idempotente."""
    if not order.sales_order_id:
        return
    from app.models.inventory import Stock, StockLocation, StockMovement
    from app.models.sales import Order as SalesOrder

    so = (
        await db.execute(select(SalesOrder).where(SalesOrder.id == order.sales_order_id))
    ).scalar_one_or_none()
    if not so or so.status in ("cancelled", "refunded"):
        return
    loc = (
        await db.execute(select(StockLocation).where(StockLocation.is_default == 1).limit(1))
    ).scalar_one_or_none() or (
        await db.execute(select(StockLocation).order_by(StockLocation.created_at).limit(1))
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    # Se devuelve exactamente lo que salió al facturar (sus movimientos SALE)
    sold = (
        await db.execute(
            select(StockMovement).where(
                StockMovement.reference_type == "PORTAL_ORDER",
                StockMovement.reference_id == order.id,
                StockMovement.movement_type == "SALE",
            )
        )
    ).scalars().all()
    for mv in sold:
        qty = -int(mv.quantity_delta)
        if qty <= 0:
            continue
        stock = (
            await db.execute(
                select(Stock)
                .where(Stock.product_id == mv.product_id, Stock.location_id == mv.location_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if stock:
            stock.quantity += qty
        db.add(
            StockMovement(
                product_id=mv.product_id,
                location_id=mv.location_id or (loc.id if loc else None),
                movement_type="RETURN",
                quantity_delta=qty,
                quantity_after=stock.quantity if stock else qty,
                reference_type="PORTAL_ORDER",
                reference_id=order.id,
                occurred_at=now,
                created_by="admin_portal",
                notes=f"Cancelación pedido portal #{str(order.id)[:8]} — {reason}",
            )
        )
    so.status = "cancelled"
    so.metadata_ = {
        **(so.metadata_ or {}),
        "cancelled_at": now.isoformat(),
        "cancel_reason": f"Pedido portal cancelado: {reason}",
    }


@router.post("/orders/{order_id}/cancel", dependencies=[Depends(require_permission("crm:write"))])
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
    await _reverse_invoice(order, payload.reason, db)
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
        "cancel_reason": getattr(appt, "cancel_reason", None),
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


@router.patch(
    "/appointments/{appt_id}/reschedule", dependencies=[Depends(require_permission("crm:write"))]
)
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


@router.patch(
    "/appointments/{appt_id}/confirm-choice",
    dependencies=[Depends(require_permission("crm:write"))],
)
async def confirm_appt_customer_choice(
    appt_id: uuid.UUID, payload: ConfirmApptChoicePayload, db: DBSession
) -> dict:
    appt = (
        await db.execute(select(Appointment).where(Appointment.id == appt_id))
    ).scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Cita no encontrada")
    new_dt = datetime.fromisoformat(payload.chosen_datetime)
    from app.api.v1.portal_appointments import conflictos, describir_cruce

    cruces = await conflictos(db, new_dt, appt.duration_min, excluir=appt.id)
    if cruces:
        raise HTTPException(409, f"{describir_cruce(cruces)}. Elige otra hora.")
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


class ApptCompletePayload(BaseModel):
    """Cuánto se cobró por la cita. Opcional para no romper el admin viejo ni quitarle
    libertad a Diego: la cita se completa con o sin precio."""

    price: float | None = Field(default=None, ge=0, le=100_000_000)


@router.patch(
    "/appointments/{appt_id}/complete", dependencies=[Depends(require_permission("crm:write"))]
)
async def complete_appointment(
    appt_id: uuid.UUID,
    db: DBSession,
    payload: ApptCompletePayload | None = None,
) -> dict:
    appt = (
        await db.execute(select(Appointment).where(Appointment.id == appt_id))
    ).scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Cita no encontrada")
    _ya_empezo(appt, "completar")
    appt.status = "completed"
    appt.completed_at = datetime.now(UTC)
    if hasattr(appt, "workflow_status"):
        appt.workflow_status = "completed"

    # Cuánto se cobró. Es opcional: si el admin no lo escribe, la cita se completa igual
    # (así funcionaba antes y no se le quita libertad), pero entonces Google no se entera
    # de la venta — ver enviar_purchase_cita, que a propósito no inventa un valor.
    if payload is not None and payload.price is not None:
        appt.price = Decimal(str(payload.price))

    # Este es el momento en que la peluquería es plata de verdad. Si Google está caído
    # esto devuelve False y no estorba: completar una cita nunca puede fallar.
    await enviar_purchase_cita(db, appt)

    await db.commit()
    return {"ok": True, "price": float(appt.price) if appt.price else None}


@router.patch(
    "/appointments/{appt_id}/no-show", dependencies=[Depends(require_permission("crm:write"))]
)
async def no_show_appointment(appt_id: uuid.UUID, db: DBSession) -> dict:
    appt = (
        await db.execute(select(Appointment).where(Appointment.id == appt_id))
    ).scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Cita no encontrada")
    _ya_empezo(appt, "marcar que no asistió")
    appt.status = "cancelled"
    if hasattr(appt, "workflow_status"):
        appt.workflow_status = "no_show"
    await db.commit()
    return {"ok": True}


class ApptNotesPayload(BaseModel):
    notes: str


@router.patch(
    "/appointments/{appt_id}/notes", dependencies=[Depends(require_permission("crm:write"))]
)
async def update_appointment_notes(
    appt_id: uuid.UUID, payload: ApptNotesPayload, db: DBSession
) -> dict:
    appt = (
        await db.execute(select(Appointment).where(Appointment.id == appt_id))
    ).scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Cita no encontrada")
    appt.notes = payload.notes
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
    # Solo mensajes de pedidos ABIERTOS: los de pedidos ya entregados o cancelados
    # inflaban el contador del menú sin que hubiera nada que hacer (Diego 28-sep-2026).
    q = (
        select(PendingNotification)
        .join(PortalOrder, PortalOrder.id == PendingNotification.portal_order_id)
        .where(
            PendingNotification.status == "pending",
            func.coalesce(PortalOrder.workflow_status, PortalOrder.status).notin_(
                ["delivered", "cancelled", "returned"]
            ),
        )
    )
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


@router.post(
    "/notifications/{notif_id}/mark-sent", dependencies=[Depends(require_permission("crm:write"))]
)
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


@router.post(
    "/notifications/{notif_id}/skip", dependencies=[Depends(require_permission("crm:write"))]
)
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


# ── Mascotas perdidas (SOS): moderación + "ya está en casa" ──────────────
# El dueño puede cerrar su caso desde el portal (sos.py); aquí el admin
# puede hacerlo por él (la mayoría avisa por WhatsApp y no vuelve al portal)
# y dejar la historia de éxito visible 30 días en el store.

_bg_tasks: set = set()


def _ping_indexnow(urls: list[str]) -> None:
    import asyncio

    from app.services.seo_notifications import notify_indexnow

    task = asyncio.create_task(notify_indexnow(urls))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


def _lost_admin_out(event, reporter_name: str | None, reporter_phone: str | None) -> dict:
    return {
        "id": str(event.id),
        "pet_name": event.pet_name,
        "species": event.species,
        "breed": event.breed,
        "color": event.color,
        "photos": event.photos or [],
        "last_seen_lat": float(event.last_seen_lat),
        "last_seen_lng": float(event.last_seen_lng),
        "last_seen_at": event.last_seen_at.isoformat(),
        "contact_phone": event.contact_phone,
        "reward": float(event.reward) if event.reward is not None else None,
        "status": event.status,
        "found_at": event.found_at.isoformat() if event.found_at else None,
        "resolution_note": event.resolution_note,
        "public_until": event.public_until.isoformat() if event.public_until else None,
        "notified_count": event.notified_count,
        "created_at": event.created_at.isoformat(),
        "reporter_name": reporter_name,
        "reporter_phone": reporter_phone or event.contact_phone,
    }


@router.get("/lost")
async def list_lost_admin(
    db: DBSession,
    status_filter: str = Query(default="all", alias="status"),
    q_search: str | None = Query(default=None, alias="q"),
) -> list[dict]:
    from app.models.community import SOSEvent

    q = select(SOSEvent, Customer.full_name, Customer.phone).join(
        Customer, Customer.id == SOSEvent.reporter_customer_id, isouter=True
    )
    if status_filter != "all":
        q = q.where(SOSEvent.status == status_filter)
    if q_search:
        term = f"%{q_search.strip()}%"
        q = q.where(
            (SOSEvent.pet_name.ilike(term))
            | (SOSEvent.contact_phone.ilike(term))
            | (Customer.full_name.ilike(term))
            | (Customer.phone.ilike(term))
        )
    rows = (await db.execute(q.order_by(SOSEvent.created_at.desc()))).all()
    return [_lost_admin_out(e, name, phone) for e, name, phone in rows]


class LostStatusUpdate(BaseModel):
    status: str  # 'active' | 'closed'


@router.patch("/lost/{event_id}", dependencies=[Depends(require_permission("crm:write"))])
async def update_lost_status_admin(
    event_id: uuid.UUID, payload: LostStatusUpdate, db: DBSession
) -> dict:
    """Cerrar (ocultar sin final feliz) o reabrir un reporte."""
    from app.models.community import SOSEvent

    if payload.status not in {"active", "closed"}:
        raise HTTPException(status_code=422, detail="status debe ser 'active' o 'closed'")
    event = (await db.execute(select(SOSEvent).where(SOSEvent.id == event_id))).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    event.status = payload.status
    if payload.status == "active":
        event.found_at = None
        event.public_until = None
    await db.commit()
    return {"ok": True, "status": event.status}


class LostOutcomeUpdate(BaseModel):
    outcome: str  # 'found' | 'active'
    resolution_note: str | None = None


@router.patch("/lost/{event_id}/outcome", dependencies=[Depends(require_permission("crm:write"))])
async def update_lost_outcome_admin(
    event_id: uuid.UUID, payload: LostOutcomeUpdate, db: DBSession
) -> dict:
    """'found': ¡ya está en casa! -- se exhibe 30 días como historia de éxito,
    se avisa a los vecinos que estaban pendientes y se marca la mascota del
    portal como no perdida. 'active': deshacer (vuelve a estar perdida)."""
    from app.api.v1.sos import _notify_nearby_customers
    from app.models.community import SOSEvent
    from app.services import community_lifecycle as lc

    if payload.outcome not in {"found", "active"}:
        raise HTTPException(status_code=422, detail="outcome debe ser 'found' o 'active'")
    event = (await db.execute(select(SOSEvent).where(SOSEvent.id == event_id))).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    if payload.outcome == "found":
        first_time = event.status != "found"
        event.status = "found"
        event.resolution_note = (payload.resolution_note or "").strip() or None
        if first_time or not event.found_at:
            event.found_at, event.public_until = lc.public_window()
        if event.pet_id:
            from app.models.portal import Pet

            pet = (await db.execute(select(Pet).where(Pet.id == event.pet_id))).scalar_one_or_none()
            if pet:
                pet.is_lost = False
        if first_time:
            await _notify_nearby_customers(
                db,
                event,
                notif_type="sos_found",
                title=f"🎉 {event.pet_name} fue encontrado(a)",
                body=f"Buenas noticias: {event.pet_name} ya apareció. ¡Gracias por estar pendiente!",
            )
    else:
        event.status = "active"
        event.found_at = None
        event.public_until = None
        event.resolution_note = None
        if event.pet_id:
            from app.models.portal import Pet

            pet = (await db.execute(select(Pet).where(Pet.id == event.pet_id))).scalar_one_or_none()
            if pet:
                pet.is_lost = True

    await db.commit()
    _ping_indexnow(lc.resolved_urls("lost", event.id))
    return {
        "ok": True,
        "status": event.status,
        "public_until": event.public_until.isoformat() if event.public_until else None,
    }


@router.delete("/lost/{event_id}", dependencies=[Depends(require_permission("crm:write"))])
async def delete_lost_admin(event_id: uuid.UUID, db: DBSession) -> dict:
    from app.models.community import SOSEvent

    event = (await db.execute(select(SOSEvent).where(SOSEvent.id == event_id))).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    await db.delete(event)
    await db.commit()
    return {"ok": True}


# ── Rescates: final feliz a nivel evento ────────────────────────────────


class RescueOutcomeUpdate(BaseModel):
    outcome: str  # 'reunited' | 'pending'
    resolution_note: str | None = None


@router.patch(
    "/rescues/{event_id}/outcome", dependencies=[Depends(require_permission("crm:write"))]
)
async def update_rescue_outcome_admin(
    event_id: uuid.UUID, payload: RescueOutcomeUpdate, db: DBSession
) -> dict:
    """'reunited': todos los animalitos del evento volvieron con su familia --
    se exhibe 30 días como historia de éxito (y marca cada ficha como
    reunida). 'pending': deshacer."""
    from app.models.community import RescueAnimal, RescueEvent
    from app.services import community_lifecycle as lc

    if payload.outcome not in {"reunited", "pending"}:
        raise HTTPException(status_code=422, detail="outcome debe ser 'reunited' o 'pending'")
    event = (
        await db.execute(select(RescueEvent).where(RescueEvent.id == event_id))
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Evento de rescate no encontrado")

    event.outcome = payload.outcome
    if payload.outcome == "reunited":
        event.resolution_note = (payload.resolution_note or "").strip() or None
        event.resolved_at, event.public_until = lc.public_window()
        await db.execute(
            sa_update(RescueAnimal)
            .where(RescueAnimal.rescue_event_id == event_id)
            .values(status="reunited")
        )
    else:
        event.resolution_note = None
        event.resolved_at = None
        event.public_until = None
    await db.commit()
    _ping_indexnow(lc.resolved_urls("found", event.id))
    return {
        "ok": True,
        "outcome": event.outcome,
        "public_until": event.public_until.isoformat() if event.public_until else None,
    }


# ── Comentarios públicos: moderación ────────────────────────────────────


@router.get("/comments")
async def list_comments_admin(
    db: DBSession,
    status_filter: str = Query(default="all", alias="status"),
    limit: int = Query(default=100, le=500),
) -> list[dict]:
    """Últimos comentarios de la comunidad con el título de la publicación
    a la que pertenecen, para moderar rápido."""
    from app.models.community import AdoptionListing, CommunityComment, RescueEvent, SOSEvent

    q = select(CommunityComment)
    if status_filter != "all":
        q = q.where(CommunityComment.status == status_filter)
    rows = (
        (await db.execute(q.order_by(CommunityComment.created_at.desc()).limit(limit)))
        .scalars()
        .all()
    )

    ids_by_type: dict[str, set] = {"adoption": set(), "lost": set(), "found": set()}
    for c in rows:
        ids_by_type.setdefault(c.entity_type, set()).add(c.entity_id)
    titles: dict[tuple[str, uuid.UUID], str] = {}
    if ids_by_type["adoption"]:
        for r in (
            await db.execute(
                select(AdoptionListing.id, AdoptionListing.title).where(
                    AdoptionListing.id.in_(ids_by_type["adoption"])
                )
            )
        ).all():
            titles[("adoption", r.id)] = r.title
    if ids_by_type["lost"]:
        for r in (
            await db.execute(
                select(SOSEvent.id, SOSEvent.pet_name).where(SOSEvent.id.in_(ids_by_type["lost"]))
            )
        ).all():
            titles[("lost", r.id)] = r.pet_name
    if ids_by_type["found"]:
        for r in (
            await db.execute(
                select(RescueEvent.id, RescueEvent.title).where(
                    RescueEvent.id.in_(ids_by_type["found"])
                )
            )
        ).all():
            titles[("found", r.id)] = r.title

    paths = {
        "adoption": "/adopcion",
        "lost": "/mascotas-perdidas",
        "found": "/mascotas-encontradas",
    }
    return [
        {
            "id": str(c.id),
            "entity_type": c.entity_type,
            "entity_id": str(c.entity_id),
            "entity_title": titles.get((c.entity_type, c.entity_id)),
            "entity_url": f"https://bigotesypaticas.com{paths[c.entity_type]}/{c.entity_id}",
            "author_name": c.author_name,
            "body": c.body,
            "status": c.status,
            "created_at": c.created_at.isoformat(),
        }
        for c in rows
    ]


class CommentStatusUpdate(BaseModel):
    status: str  # 'visible' | 'hidden'


@router.patch("/comments/{comment_id}", dependencies=[Depends(require_permission("crm:write"))])
async def update_comment_admin(
    comment_id: uuid.UUID, payload: CommentStatusUpdate, db: DBSession
) -> dict:
    from app.models.community import CommunityComment

    if payload.status not in {"visible", "hidden"}:
        raise HTTPException(status_code=422, detail="status debe ser 'visible' o 'hidden'")
    c = (
        await db.execute(select(CommunityComment).where(CommunityComment.id == comment_id))
    ).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")
    c.status = payload.status
    await db.commit()
    return {"ok": True, "status": c.status}


@router.delete("/comments/{comment_id}", dependencies=[Depends(require_permission("crm:write"))])
async def delete_comment_admin(comment_id: uuid.UUID, db: DBSession) -> dict:
    from app.models.community import CommunityComment

    c = (
        await db.execute(select(CommunityComment).where(CommunityComment.id == comment_id))
    ).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")
    await db.delete(c)
    await db.commit()
    return {"ok": True}
