"""Portal Appointments — citas de grooming, baño, consulta, etc."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, select

from app.api.v1.portal_auth import PortalUser
from app.api.v1.portal_loyalty import POINTS_APPOINTMENT, award_points
from app.deps import DBSession
from app.models.crm import Customer
from app.models.portal import Appointment

router = APIRouter(prefix="/portal/appointments", tags=["portal"])


# ── schemas ───────────────────────────────────────────────────────────

class AppointmentIn(BaseModel):
    pet_id: str
    service_type: str
    scheduled_at: str   # ISO-8601 con TZ (e.g. "2026-07-01T10:00:00-05:00")
    duration_min: int = 60
    notes: str | None = None


class AppointmentOut(BaseModel):
    id: str
    pet_id: str
    service_type: str
    scheduled_at: str
    duration_min: int
    status: str
    price: float | None
    notes: str | None
    created_at: str
    points_earned: int | None = None


def _appt_out(a: Appointment, points: int | None = None) -> AppointmentOut:
    return AppointmentOut(
        id=str(a.id),
        pet_id=str(a.pet_id),
        service_type=a.service_type,
        scheduled_at=a.scheduled_at.isoformat(),
        duration_min=a.duration_min,
        status=a.status,
        price=float(a.price) if a.price else None,
        notes=a.notes,
        created_at=a.created_at.isoformat(),
        points_earned=points,
    )


# ── endpoints ─────────────────────────────────────────────────────────

@router.get("", response_model=list[AppointmentOut])
async def list_appointments(
    db: DBSession,
    customer: Customer = PortalUser,
    upcoming_only: bool = Query(False, description="Solo citas futuras"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> list[AppointmentOut]:
    q = select(Appointment).where(Appointment.customer_id == customer.id)
    if upcoming_only:
        q = q.where(Appointment.scheduled_at >= datetime.now(UTC))
    q = q.order_by(Appointment.scheduled_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return [_appt_out(a) for a in rows]


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    payload: AppointmentIn,
    db: DBSession,
    customer: Customer = PortalUser,
) -> AppointmentOut:
    scheduled = datetime.fromisoformat(payload.scheduled_at)
    if scheduled <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="La cita debe ser en el futuro")

    appt = Appointment(
        pet_id=uuid.UUID(payload.pet_id),
        customer_id=customer.id,
        service_type=payload.service_type,
        scheduled_at=scheduled,
        duration_min=payload.duration_min,
        status="pending",
        notes=payload.notes,
    )
    db.add(appt)
    await db.commit()
    await db.refresh(appt)
    return _appt_out(appt)


@router.get("/{appt_id}", response_model=AppointmentOut)
async def get_appointment(
    appt_id: uuid.UUID,
    db: DBSession,
    customer: Customer = PortalUser,
) -> AppointmentOut:
    appt = (
        await db.execute(
            select(Appointment).where(
                and_(Appointment.id == appt_id, Appointment.customer_id == customer.id)
            )
        )
    ).scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return _appt_out(appt)


@router.patch("/{appt_id}/cancel", response_model=AppointmentOut)
async def cancel_appointment(
    appt_id: uuid.UUID,
    db: DBSession,
    customer: Customer = PortalUser,
) -> AppointmentOut:
    appt = (
        await db.execute(
            select(Appointment).where(
                and_(Appointment.id == appt_id, Appointment.customer_id == customer.id)
            )
        )
    ).scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    if appt.status in ("completed", "cancelled"):
        raise HTTPException(status_code=409, detail=f"Cita ya está {appt.status}")
    appt.status = "cancelled"
    await db.commit()
    await db.refresh(appt)
    return _appt_out(appt)


# ── endpoint interno: admin marca como completada y otorga puntos ─────

@router.patch("/{appt_id}/complete", response_model=AppointmentOut)
async def complete_appointment(
    appt_id: uuid.UUID,
    price: float | None = None,
    db: DBSession = None,
    customer: Customer = PortalUser,
) -> AppointmentOut:
    """Admin-facing: marcar cita como completada y otorgar 50 pts."""
    appt = (
        await db.execute(
            select(Appointment).where(Appointment.id == appt_id)
        )
    ).scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    if appt.status == "completed":
        raise HTTPException(status_code=409, detail="Cita ya completada")

    appt.status = "completed"
    if price is not None:
        appt.price = price
    await db.commit()

    await award_points(
        customer_id=appt.customer_id,
        points=POINTS_APPOINTMENT,
        reason="appointment",
        reference_type="appointment",
        reference_id=appt.id,
        description=f"Cita completada: {appt.service_type}",
        db=db,
    )

    await db.refresh(appt)
    return _appt_out(appt, points=POINTS_APPOINTMENT)
