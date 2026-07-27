"""Mis reservas — vista del cliente sobre sus bookings con aliados (Fase 3)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.v1.portal_auth import PortalUser
from app.deps import DBSession
from app.models.crm import Customer
from app.models.partners import Booking, Partner, PartnerReview, Service

router = APIRouter(prefix="/portal/bookings", tags=["portal"])


def _booking_out(b: Booking, partner: Partner, service: Service | None, reviewed: bool) -> dict:
    return {
        "id": str(b.id),
        "partner_id": str(partner.id),
        "partner_slug": partner.slug,
        "partner_name": partner.business_name,
        "partner_type": partner.partner_type,
        "partner_phone": partner.phone,
        "service_name": service.name if service else None,
        "scheduled_at": b.scheduled_at.isoformat(),
        "duration_min": b.duration_min,
        "status": b.status,
        "price_snapshot": float(b.price_snapshot) if b.price_snapshot is not None else None,
        "notes_customer": b.notes_customer,
        "cancelled_reason": b.cancelled_reason,
        "created_at": b.created_at.isoformat(),
        "reviewed": reviewed,
    }


@router.get("")
async def list_my_bookings(
    db: DBSession,
    customer: Customer = PortalUser,
    upcoming_only: bool = Query(False),
) -> list[dict]:
    stmt = select(Booking).where(Booking.customer_id == customer.id)
    if upcoming_only:
        stmt = stmt.where(Booking.status.in_(["pending", "confirmed"]))
    stmt = stmt.order_by(Booking.scheduled_at.desc()).limit(100)
    rows = (await db.execute(stmt)).scalars().all()
    if not rows:
        return []

    partner_ids = {b.partner_id for b in rows}
    service_ids = {b.service_id for b in rows if b.service_id}
    booking_ids = {b.id for b in rows}

    partners = (
        (await db.execute(select(Partner).where(Partner.id.in_(partner_ids)))).scalars().all()
    )
    partner_map = {p.id: p for p in partners}

    services = (
        (await db.execute(select(Service).where(Service.id.in_(service_ids)))).scalars().all()
        if service_ids
        else []
    )
    service_map = {s.id: s for s in services}

    reviewed_ids = set(
        (
            await db.execute(
                select(PartnerReview.booking_id).where(PartnerReview.booking_id.in_(booking_ids))
            )
        )
        .scalars()
        .all()
    )

    return [
        _booking_out(
            b, partner_map[b.partner_id], service_map.get(b.service_id), b.id in reviewed_ids
        )
        for b in rows
        if b.partner_id in partner_map
    ]


@router.patch("/{booking_id}/cancel")
async def cancel_my_booking(
    booking_id: uuid.UUID,
    db: DBSession,
    customer: Customer = PortalUser,
) -> dict:
    booking = (
        await db.execute(
            select(Booking).where(Booking.id == booking_id, Booking.customer_id == customer.id)
        )
    ).scalar_one_or_none()
    if booking is None:
        raise HTTPException(404, "Reserva no encontrada")
    if booking.status in ("completed", "cancelled"):
        raise HTTPException(409, f"La reserva ya está {booking.status}")
    booking.status = "cancelled"
    booking.cancelled_reason = "Cancelada por el cliente"
    await db.commit()
    return {"ok": True}


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)


@router.post("/{booking_id}/review")
async def review_booking(
    booking_id: uuid.UUID,
    payload: ReviewIn,
    db: DBSession,
    customer: Customer = PortalUser,
) -> dict:
    booking = (
        await db.execute(
            select(Booking).where(Booking.id == booking_id, Booking.customer_id == customer.id)
        )
    ).scalar_one_or_none()
    if booking is None:
        raise HTTPException(404, "Reserva no encontrada")
    if booking.status != "completed":
        raise HTTPException(409, "Solo puedes calificar reservas completadas")

    existing = (
        await db.execute(select(PartnerReview).where(PartnerReview.booking_id == booking_id))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(409, "Ya calificaste esta reserva")

    review = PartnerReview(
        booking_id=booking.id,
        partner_id=booking.partner_id,
        customer_id=customer.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    await db.flush()

    partner = (
        await db.execute(select(Partner).where(Partner.id == booking.partner_id))
    ).scalar_one()
    new_count = partner.rating_count + 1
    new_avg = ((float(partner.rating_avg) * partner.rating_count) + payload.rating) / new_count
    partner.rating_count = new_count
    partner.rating_avg = round(new_avg, 2)

    await db.commit()
    return {"ok": True}
