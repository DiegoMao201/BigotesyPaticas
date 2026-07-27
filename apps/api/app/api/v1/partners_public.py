"""Directorio público de aliados/servicios (Fase 3 del plan móvil/comunidad).

Lectura pública sin autenticación (directorio + disponibilidad). Agendar sí
requiere sesión de cliente del portal (PortalUser), igual que reportar un SOS.
"""

from __future__ import annotations

import uuid
from datetime import date as date_
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select

from app.api.v1.portal_auth import PortalUser
from app.deps import DBSession
from app.models.crm import Customer
from app.models.partners import Booking, Partner, Service, ServiceSlot

router = APIRouter(prefix="/partners", tags=["partners"])

PARTNER_TYPES = {"vet", "walker", "shelter", "groomer"}
_TZ_CO = ZoneInfo("America/Bogota")


def _partner_out(p: Partner) -> dict:
    return {
        "id": str(p.id),
        "slug": p.slug,
        "partner_type": p.partner_type,
        "business_name": p.business_name,
        "city": p.city,
        "address": p.address,
        "lat": float(p.lat) if p.lat is not None else None,
        "lng": float(p.lng) if p.lng is not None else None,
        "logo_url": p.logo_url,
        "cover_url": p.cover_url,
        "bio": p.bio,
        "phone": p.phone,
        "whatsapp": p.whatsapp,
        "rating_avg": float(p.rating_avg),
        "rating_count": p.rating_count,
        "verified": p.verified_at is not None,
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
    }


async def _get_published_partner(slug: str, db: DBSession) -> Partner:
    partner = (
        await db.execute(select(Partner).where(Partner.slug == slug, Partner.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if partner is None or partner.published_at is None:
        raise HTTPException(status_code=404, detail="Aliado no encontrado")
    return partner


@router.get("")
async def list_partners(
    db: DBSession,
    type: str | None = Query(default=None),
    city: str | None = None,
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    km: int = Query(default=20, ge=1, le=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    if type is not None and type not in PARTNER_TYPES:
        raise HTTPException(422, f"type debe ser uno de: {', '.join(sorted(PARTNER_TYPES))}")

    stmt = select(Partner).where(Partner.published_at.is_not(None), Partner.deleted_at.is_(None))
    if type:
        stmt = stmt.where(Partner.partner_type == type)
    if city:
        stmt = stmt.where(func.lower(Partner.city) == city.lower())

    if lat is not None and lng is not None:
        distance_expr = 6371 * func.acos(
            func.least(
                1.0,
                func.greatest(
                    -1.0,
                    func.cos(func.radians(lat))
                    * func.cos(func.radians(Partner.lat))
                    * func.cos(func.radians(Partner.lng) - func.radians(lng))
                    + func.sin(func.radians(lat)) * func.sin(func.radians(Partner.lat)),
                ),
            )
        )
        stmt = stmt.where(Partner.lat.is_not(None), Partner.lng.is_not(None), distance_expr <= km)
        stmt = stmt.order_by(distance_expr.asc())
    else:
        stmt = stmt.order_by(Partner.rating_avg.desc(), Partner.business_name.asc())

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    return {
        "items": [_partner_out(p) for p in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{slug}")
async def get_partner(slug: str, db: DBSession) -> dict:
    partner = await _get_published_partner(slug, db)
    return _partner_out(partner)


@router.get("/{slug}/services")
async def list_partner_services(slug: str, db: DBSession) -> list[dict]:
    partner = await _get_published_partner(slug, db)
    services = (
        (
            await db.execute(
                select(Service)
                .where(Service.partner_id == partner.id, Service.is_active.is_(True))
                .order_by(Service.category, Service.name)
            )
        )
        .scalars()
        .all()
    )
    return [_service_out(s) for s in services]


# ── disponibilidad + agendamiento ───────────────────────────────────────


@router.get("/{slug}/availability")
async def get_availability(
    slug: str,
    db: DBSession,
    service_id: uuid.UUID,
    date: str = Query(..., description="YYYY-MM-DD"),
) -> dict:
    partner = await _get_published_partner(slug, db)
    service = (
        await db.execute(
            select(Service).where(
                Service.id == service_id,
                Service.partner_id == partner.id,
                Service.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if service is None:
        raise HTTPException(404, "Servicio no encontrado")

    try:
        target_date = date_.fromisoformat(date)
    except ValueError as exc:
        raise HTTPException(422, "Fecha inválida, usa YYYY-MM-DD") from exc
    if target_date < datetime.now(_TZ_CO).date():
        raise HTTPException(422, "No puedes agendar en días pasados")

    day_of_week = target_date.weekday()  # 0=lunes .. 6=domingo, igual que el modelo
    rules = (
        (
            await db.execute(
                select(ServiceSlot).where(
                    ServiceSlot.partner_id == partner.id,
                    ServiceSlot.day_of_week == day_of_week,
                    ServiceSlot.is_active.is_(True),
                    (ServiceSlot.service_id.is_(None)) | (ServiceSlot.service_id == service_id),
                )
            )
        )
        .scalars()
        .all()
    )

    # Generar franjas discretas a partir de las reglas de disponibilidad del día
    raw_slots: dict[str, int] = {}  # "HH:MM" -> max_bookings
    for rule in rules:
        cursor = datetime.combine(target_date, rule.start_time, tzinfo=_TZ_CO)
        end = datetime.combine(target_date, rule.end_time, tzinfo=_TZ_CO)
        step = timedelta(minutes=rule.slot_minutes)
        while cursor + step <= end:
            key = cursor.strftime("%H:%M")
            raw_slots[key] = max(raw_slots.get(key, 0), rule.max_bookings)
            cursor += step

    if not raw_slots:
        return {"date": date, "service_id": str(service_id), "slots": []}

    day_start = datetime.combine(target_date, datetime.min.time(), tzinfo=_TZ_CO)
    day_end = day_start + timedelta(days=1)
    existing = (
        (
            await db.execute(
                select(Booking).where(
                    and_(
                        Booking.partner_id == partner.id,
                        Booking.scheduled_at >= day_start,
                        Booking.scheduled_at < day_end,
                        Booking.status.in_(["pending", "confirmed"]),
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    booked: dict[str, int] = {}
    for b in existing:
        key = b.scheduled_at.astimezone(_TZ_CO).strftime("%H:%M")
        booked[key] = booked.get(key, 0) + 1

    now_co = datetime.now(_TZ_CO)
    slots = []
    for time_str in sorted(raw_slots):
        slot_dt = datetime.combine(
            target_date, datetime.strptime(time_str, "%H:%M").time(), tzinfo=_TZ_CO
        )
        capacity = raw_slots[time_str]
        available = booked.get(time_str, 0) < capacity and slot_dt > now_co
        slots.append({"time": time_str, "available": available})

    return {"date": date, "service_id": str(service_id), "slots": slots}


class BookingIn(BaseModel):
    service_id: uuid.UUID
    scheduled_at: str  # ISO-8601 con TZ
    pet_id: uuid.UUID | None = None
    notes_customer: str | None = Field(default=None, max_length=500)


@router.post("/{slug}/bookings", status_code=201)
async def create_booking(
    slug: str,
    payload: BookingIn,
    db: DBSession,
    customer: Customer = PortalUser,
) -> dict:
    partner = await _get_published_partner(slug, db)
    service = (
        await db.execute(
            select(Service).where(
                Service.id == payload.service_id,
                Service.partner_id == partner.id,
                Service.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if service is None:
        raise HTTPException(404, "Servicio no encontrado")

    try:
        scheduled = datetime.fromisoformat(payload.scheduled_at)
    except ValueError as exc:
        raise HTTPException(422, "Fecha/hora inválida") from exc
    if scheduled.tzinfo is None:
        # El frontend manda la hora local de Bogotá tal cual la mostró /availability, sin offset.
        scheduled = scheduled.replace(tzinfo=_TZ_CO)
    if scheduled <= datetime.now(_TZ_CO):
        raise HTTPException(422, "La reserva debe ser en el futuro")

    day_of_week = scheduled.astimezone(_TZ_CO).weekday()
    time_of_day = scheduled.astimezone(_TZ_CO).time()
    rule = (
        (
            await db.execute(
                select(ServiceSlot).where(
                    ServiceSlot.partner_id == partner.id,
                    ServiceSlot.day_of_week == day_of_week,
                    ServiceSlot.is_active.is_(True),
                    ServiceSlot.start_time <= time_of_day,
                    ServiceSlot.end_time > time_of_day,
                    (ServiceSlot.service_id.is_(None)) | (ServiceSlot.service_id == service.id),
                )
            )
        )
        .scalars()
        .first()
    )
    if rule is None:
        raise HTTPException(422, "Ese horario ya no está disponible")

    existing_count = (
        await db.execute(
            select(func.count())
            .select_from(Booking)
            .where(
                Booking.partner_id == partner.id,
                Booking.scheduled_at == scheduled,
                Booking.status.in_(["pending", "confirmed"]),
            )
        )
    ).scalar_one()
    if existing_count >= rule.max_bookings:
        raise HTTPException(409, "Ese horario se acaba de ocupar, elige otro")

    booking = Booking(
        customer_id=customer.id,
        partner_id=partner.id,
        service_id=service.id,
        pet_id=payload.pet_id,
        scheduled_at=scheduled,
        duration_min=service.duration_min or rule.slot_minutes,
        status="pending",
        price_snapshot=service.price,
        notes_customer=payload.notes_customer,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return {
        "id": str(booking.id),
        "partner_id": str(partner.id),
        "service_id": str(service.id),
        "scheduled_at": booking.scheduled_at.isoformat(),
        "status": booking.status,
    }
