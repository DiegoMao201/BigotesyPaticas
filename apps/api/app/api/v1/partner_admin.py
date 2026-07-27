"""Panel del aliado autenticado: perfil, servicios, disponibilidad y reservas."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from slugify import slugify
from sqlalchemy import func, select

from app.api.v1.partner_auth import CurrentPartnerUser
from app.deps import DBSession
from app.models.partners import Booking, Partner, PartnerReview, Service, ServiceSlot

router = APIRouter(prefix="/partner", tags=["partner"])

BOOKING_STATUSES = {"pending", "confirmed", "completed", "cancelled", "no_show"}
PRICE_TYPES = {"fixed", "from", "quote"}


# ── schemas ───────────────────────────────────────────────────────────


class ProfileIn(BaseModel):
    business_name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = None
    whatsapp: str | None = None
    address: str | None = None
    city: str | None = Field(default=None, min_length=2, max_length=80)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    bio: str | None = None
    logo_url: str | None = None
    cover_url: str | None = None


class ServiceIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    duration_min: int | None = Field(default=None, ge=5, le=480)
    price: float | None = Field(default=None, ge=0)
    price_type: str = "fixed"
    category: str = Field(min_length=2, max_length=40)
    requires_pet: bool = True


class SlotIn(BaseModel):
    service_id: str | None = None
    day_of_week: int = Field(ge=0, le=6)
    start_time: str  # "09:00"
    end_time: str  # "17:00"
    slot_minutes: int = Field(default=30, ge=5, le=240)
    max_bookings: int = Field(default=1, ge=1, le=50)


class BookingActionIn(BaseModel):
    notes_partner: str | None = None
    reason: str | None = None


def _partner_full_out(p: Partner) -> dict:
    return {
        "id": str(p.id),
        "slug": p.slug,
        "partner_type": p.partner_type,
        "business_name": p.business_name,
        "legal_name": p.legal_name,
        "document_id": p.document_id,
        "email": p.email,
        "phone": p.phone,
        "whatsapp": p.whatsapp,
        "address": p.address,
        "city": p.city,
        "lat": float(p.lat) if p.lat is not None else None,
        "lng": float(p.lng) if p.lng is not None else None,
        "logo_url": p.logo_url,
        "cover_url": p.cover_url,
        "bio": p.bio,
        "rating_avg": float(p.rating_avg),
        "rating_count": p.rating_count,
        "is_published": p.published_at is not None,
        "is_verified": p.verified_at is not None,
    }


def _service_out(s: Service) -> dict:
    return {
        "id": str(s.id),
        "slug": s.slug,
        "name": s.name,
        "description": s.description,
        "duration_min": s.duration_min,
        "price": float(s.price) if s.price is not None else None,
        "price_type": s.price_type,
        "category": s.category,
        "requires_pet": s.requires_pet,
        "is_active": s.is_active,
    }


def _slot_out(s: ServiceSlot) -> dict:
    return {
        "id": str(s.id),
        "service_id": str(s.service_id) if s.service_id else None,
        "day_of_week": s.day_of_week,
        "start_time": s.start_time.strftime("%H:%M"),
        "end_time": s.end_time.strftime("%H:%M"),
        "slot_minutes": s.slot_minutes,
        "max_bookings": s.max_bookings,
        "is_active": s.is_active,
    }


def _booking_out(b: Booking) -> dict:
    return {
        "id": str(b.id),
        "customer_id": str(b.customer_id),
        "service_id": str(b.service_id) if b.service_id else None,
        "pet_id": str(b.pet_id) if b.pet_id else None,
        "scheduled_at": b.scheduled_at.isoformat(),
        "duration_min": b.duration_min,
        "status": b.status,
        "price_snapshot": float(b.price_snapshot) if b.price_snapshot is not None else None,
        "notes_customer": b.notes_customer,
        "notes_partner": b.notes_partner,
        "cancelled_reason": b.cancelled_reason,
        "created_at": b.created_at.isoformat(),
    }


async def _get_own_partner(partner_user: CurrentPartnerUser, db: DBSession) -> Partner:
    partner = (
        await db.execute(select(Partner).where(Partner.id == partner_user.partner_id))
    ).scalar_one_or_none()
    if partner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aliado no encontrado")
    return partner


async def _get_own_service(service_id: uuid.UUID, partner_id: uuid.UUID, db: DBSession) -> Service:
    svc = (
        await db.execute(
            select(Service).where(Service.id == service_id, Service.partner_id == partner_id)
        )
    ).scalar_one_or_none()
    if svc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Servicio no encontrado")
    return svc


# ── dashboard / perfil ───────────────────────────────────────────────


@router.get("/dashboard")
async def dashboard(partner_user: CurrentPartnerUser, db: DBSession) -> dict:
    partner = await _get_own_partner(partner_user, db)
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)

    pending_count = (
        await db.execute(
            select(func.count())
            .select_from(Booking)
            .where(Booking.partner_id == partner.id, Booking.status == "pending")
        )
    ).scalar_one()
    today_count = (
        await db.execute(
            select(func.count())
            .select_from(Booking)
            .where(
                Booking.partner_id == partner.id,
                Booking.status.in_(["confirmed", "completed"]),
                Booking.scheduled_at >= today_start,
                Booking.scheduled_at <= today_end,
            )
        )
    ).scalar_one()

    return {
        "partner": _partner_full_out(partner),
        "pending_bookings": pending_count,
        "today_bookings": today_count,
    }


@router.get("/profile")
async def get_profile(partner_user: CurrentPartnerUser, db: DBSession) -> dict:
    partner = await _get_own_partner(partner_user, db)
    return _partner_full_out(partner)


@router.put("/profile")
async def update_profile(
    payload: ProfileIn, partner_user: CurrentPartnerUser, db: DBSession
) -> dict:
    partner = await _get_own_partner(partner_user, db)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(partner, field, value)
    await db.commit()
    await db.refresh(partner)
    return _partner_full_out(partner)


# ── servicios ─────────────────────────────────────────────────────────


@router.get("/services")
async def list_services(partner_user: CurrentPartnerUser, db: DBSession) -> list[dict]:
    rows = (
        (
            await db.execute(
                select(Service)
                .where(Service.partner_id == partner_user.partner_id)
                .order_by(Service.name)
            )
        )
        .scalars()
        .all()
    )
    return [_service_out(s) for s in rows]


@router.post("/services", status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: ServiceIn, partner_user: CurrentPartnerUser, db: DBSession
) -> dict:
    if payload.price_type not in PRICE_TYPES:
        raise HTTPException(422, f"price_type debe ser uno de: {', '.join(sorted(PRICE_TYPES))}")
    base_slug = slugify(payload.name)
    slug = base_slug
    suffix = 2
    while (
        await db.execute(
            select(Service.id).where(
                Service.partner_id == partner_user.partner_id, Service.slug == slug
            )
        )
    ).scalar_one_or_none():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    svc = Service(
        partner_id=partner_user.partner_id,
        slug=slug,
        name=payload.name,
        description=payload.description,
        duration_min=payload.duration_min,
        price=payload.price,
        price_type=payload.price_type,
        category=payload.category,
        requires_pet=payload.requires_pet,
        is_active=True,
    )
    db.add(svc)
    await db.commit()
    await db.refresh(svc)
    return _service_out(svc)


@router.put("/services/{service_id}")
async def update_service(
    service_id: uuid.UUID, payload: ServiceIn, partner_user: CurrentPartnerUser, db: DBSession
) -> dict:
    if payload.price_type not in PRICE_TYPES:
        raise HTTPException(422, f"price_type debe ser uno de: {', '.join(sorted(PRICE_TYPES))}")
    svc = await _get_own_service(service_id, partner_user.partner_id, db)
    svc.name = payload.name
    svc.description = payload.description
    svc.duration_min = payload.duration_min
    svc.price = payload.price
    svc.price_type = payload.price_type
    svc.category = payload.category
    svc.requires_pet = payload.requires_pet
    await db.commit()
    await db.refresh(svc)
    return _service_out(svc)


@router.delete("/services/{service_id}")
async def deactivate_service(
    service_id: uuid.UUID, partner_user: CurrentPartnerUser, db: DBSession
) -> dict:
    svc = await _get_own_service(service_id, partner_user.partner_id, db)
    svc.is_active = False
    await db.commit()
    return {"ok": True}


# ── disponibilidad ────────────────────────────────────────────────────


@router.get("/slots")
async def list_slots(partner_user: CurrentPartnerUser, db: DBSession) -> list[dict]:
    rows = (
        (
            await db.execute(
                select(ServiceSlot)
                .where(ServiceSlot.partner_id == partner_user.partner_id)
                .order_by(ServiceSlot.day_of_week, ServiceSlot.start_time)
            )
        )
        .scalars()
        .all()
    )
    return [_slot_out(s) for s in rows]


@router.post("/slots", status_code=status.HTTP_201_CREATED)
async def create_slot(payload: SlotIn, partner_user: CurrentPartnerUser, db: DBSession) -> dict:
    try:
        start = datetime.strptime(payload.start_time, "%H:%M").time()
        end = datetime.strptime(payload.end_time, "%H:%M").time()
    except ValueError as exc:
        raise HTTPException(422, "Hora inválida, usa HH:MM") from exc
    if end <= start:
        raise HTTPException(422, "La hora de fin debe ser después de la de inicio")

    service_uuid = uuid.UUID(payload.service_id) if payload.service_id else None
    if service_uuid is not None:
        await _get_own_service(service_uuid, partner_user.partner_id, db)

    slot = ServiceSlot(
        partner_id=partner_user.partner_id,
        service_id=service_uuid,
        day_of_week=payload.day_of_week,
        start_time=start,
        end_time=end,
        slot_minutes=payload.slot_minutes,
        max_bookings=payload.max_bookings,
        is_active=True,
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return _slot_out(slot)


@router.delete("/slots/{slot_id}")
async def delete_slot(slot_id: uuid.UUID, partner_user: CurrentPartnerUser, db: DBSession) -> dict:
    slot = (
        await db.execute(
            select(ServiceSlot).where(
                ServiceSlot.id == slot_id, ServiceSlot.partner_id == partner_user.partner_id
            )
        )
    ).scalar_one_or_none()
    if slot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Franja no encontrada")
    await db.delete(slot)
    await db.commit()
    return {"ok": True}


# ── reservas ──────────────────────────────────────────────────────────


@router.get("/bookings")
async def list_bookings(
    partner_user: CurrentPartnerUser,
    db: DBSession,
    booking_status: str | None = Query(default=None, alias="status"),
) -> list[dict]:
    if booking_status is not None and booking_status not in BOOKING_STATUSES:
        raise HTTPException(422, f"status debe ser uno de: {', '.join(sorted(BOOKING_STATUSES))}")

    stmt = select(Booking).where(Booking.partner_id == partner_user.partner_id)
    if booking_status:
        stmt = stmt.where(Booking.status == booking_status)
    stmt = stmt.order_by(Booking.scheduled_at.desc()).limit(200)
    rows = (await db.execute(stmt)).scalars().all()
    return [_booking_out(b) for b in rows]


async def _get_own_booking(booking_id: uuid.UUID, partner_id: uuid.UUID, db: DBSession) -> Booking:
    booking = (
        await db.execute(
            select(Booking).where(Booking.id == booking_id, Booking.partner_id == partner_id)
        )
    ).scalar_one_or_none()
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reserva no encontrada")
    return booking


@router.patch("/bookings/{booking_id}/confirm")
async def confirm_booking(
    booking_id: uuid.UUID, payload: BookingActionIn, partner_user: CurrentPartnerUser, db: DBSession
) -> dict:
    booking = await _get_own_booking(booking_id, partner_user.partner_id, db)
    if booking.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"La reserva está {booking.status}")
    booking.status = "confirmed"
    if payload.notes_partner:
        booking.notes_partner = payload.notes_partner
    await db.commit()
    await db.refresh(booking)
    return _booking_out(booking)


@router.patch("/bookings/{booking_id}/complete")
async def complete_booking(
    booking_id: uuid.UUID, payload: BookingActionIn, partner_user: CurrentPartnerUser, db: DBSession
) -> dict:
    booking = await _get_own_booking(booking_id, partner_user.partner_id, db)
    if booking.status not in ("confirmed", "pending"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"La reserva está {booking.status}")
    booking.status = "completed"
    if payload.notes_partner:
        booking.notes_partner = payload.notes_partner
    await db.commit()
    await db.refresh(booking)
    return _booking_out(booking)


@router.patch("/bookings/{booking_id}/no-show")
async def no_show_booking(
    booking_id: uuid.UUID, partner_user: CurrentPartnerUser, db: DBSession
) -> dict:
    booking = await _get_own_booking(booking_id, partner_user.partner_id, db)
    if booking.status not in ("confirmed", "pending"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"La reserva está {booking.status}")
    booking.status = "no_show"
    await db.commit()
    await db.refresh(booking)
    return _booking_out(booking)


@router.patch("/bookings/{booking_id}/cancel")
async def cancel_booking(
    booking_id: uuid.UUID, payload: BookingActionIn, partner_user: CurrentPartnerUser, db: DBSession
) -> dict:
    booking = await _get_own_booking(booking_id, partner_user.partner_id, db)
    if booking.status in ("completed", "cancelled"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"La reserva está {booking.status}")
    booking.status = "cancelled"
    booking.cancelled_reason = payload.reason
    await db.commit()
    await db.refresh(booking)
    return _booking_out(booking)


@router.get("/reviews")
async def list_reviews(partner_user: CurrentPartnerUser, db: DBSession) -> list[dict]:
    rows = (
        (
            await db.execute(
                select(PartnerReview)
                .where(PartnerReview.partner_id == partner_user.partner_id)
                .order_by(PartnerReview.created_at.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": str(r.id),
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
