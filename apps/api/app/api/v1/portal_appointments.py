"""Portal Appointments — citas de grooming, baño, consulta, etc. + disponibilidad."""
from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, select

from app.api.v1.portal_auth import PortalUser
from app.api.v1.portal_loyalty import POINTS_APPOINTMENT, award_points
from app.deps import DBSession
from app.models.crm import Customer
from app.models.portal import Appointment

router = APIRouter(prefix="/portal/appointments", tags=["portal"])

# Horario configurable por ENV
_AM_START = int(os.getenv("PORTAL_BUSINESS_HOURS_AM", "9-12").split("-")[0])
_AM_END   = int(os.getenv("PORTAL_BUSINESS_HOURS_AM", "9-12").split("-")[1])
_PM_START = int(os.getenv("PORTAL_BUSINESS_HOURS_PM", "14-17").split("-")[0])
_PM_END   = int(os.getenv("PORTAL_BUSINESS_HOURS_PM", "14-17").split("-")[1])
_SLOT_CAP = int(os.getenv("PORTAL_SLOT_CAPACITY", "1"))


# ── schemas ───────────────────────────────────────────────────────────

class SlotOut(BaseModel):
    time: str          # "09:00"
    available: bool
    reason: str | None = None


class AvailabilityOut(BaseModel):
    date: str
    service: str
    slots: list[SlotOut]


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


def _build_slots(hours: range) -> list[str]:
    return [f"{h:02d}:00" for h in hours]


# ── endpoints ─────────────────────────────────────────────────────────

@router.get("/availability", response_model=AvailabilityOut)
async def get_availability(
    db: DBSession,
    customer: Customer = PortalUser,
    date_str: str = Query(..., alias="date", description="YYYY-MM-DD"),
    service: str = Query("baño"),
) -> AvailabilityOut:
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=422, detail="Fecha inválida, usa YYYY-MM-DD")

    if target_date < date.today():
        raise HTTPException(status_code=422, detail="No puedes agendar en días pasados")

    # Generar todos los slots del día
    am_slots = _build_slots(range(_AM_START, _AM_END))
    pm_slots = _build_slots(range(_PM_START, _PM_END + 1))
    all_slots = am_slots + pm_slots

    # Contar citas existentes por slot (pending o confirmed)
    day_start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)

    existing = (
        await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.scheduled_at >= day_start,
                    Appointment.scheduled_at < day_end,
                    Appointment.status.in_(["pending", "confirmed"]),
                )
            )
        )
    ).scalars().all()

    booked: dict[str, int] = {}
    for a in existing:
        slot = a.scheduled_at.strftime("%H:00")
        booked[slot] = booked.get(slot, 0) + 1

    slots = [
        SlotOut(
            time=slot,
            available=booked.get(slot, 0) < _SLOT_CAP,
            reason="ocupado" if booked.get(slot, 0) >= _SLOT_CAP else None,
        )
        for slot in all_slots
    ]

    return AvailabilityOut(date=date_str, service=service, slots=slots)


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
    await db.flush()

    # Notificaciones bidireccionales
    try:
        from app.api.v1.portal_notifications import notify_admins, notify_customer
        service_label = payload.service_type.capitalize()
        fecha_str = scheduled.strftime("%d/%m/%Y a las %H:%M")
        await notify_customer(
            db,
            customer.id,
            notif_type="appointment",
            title="✅ Cita solicitada",
            body=f"{service_label} el {fecha_str}. Te avisaremos cuando la aprueben.",
            data={"appointment_id": str(appt.id)},
        )
        await notify_admins(
            db,
            notif_type="new_appointment",
            title=f"Nueva cita: {service_label}",
            body=f"{customer.full_name or 'Cliente'} solicitó {service_label} el {fecha_str}",
            data={"appointment_id": str(appt.id), "customer_id": str(customer.id)},
        )
    except Exception:
        pass

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


# ── acciones admin (approve / reschedule) ────────────────────────────────────

class ApprovePayload(BaseModel):
    new_scheduled_at: str | None = None  # si se reprograma al mismo tiempo


@router.patch("/{appt_id}/approve", response_model=AppointmentOut)
async def admin_approve(
    appt_id: uuid.UUID,
    payload: ApprovePayload | None = None,
    db: DBSession = None,
) -> AppointmentOut:
    """Admin: aprobar cita (requiere auth de admin — la UI lo llama con credenciales admin)."""
    appt = (await db.execute(select(Appointment).where(Appointment.id == appt_id))).scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    if payload and payload.new_scheduled_at:
        appt.scheduled_at = datetime.fromisoformat(payload.new_scheduled_at)
    appt.status = "confirmed"
    await db.flush()
    try:
        from app.api.v1.portal_notifications import notify_customer
        fecha_str = appt.scheduled_at.strftime("%d/%m/%Y a las %H:%M")
        await notify_customer(
            db,
            appt.customer_id,
            notif_type="appt_confirmed",
            title="✅ Cita confirmada",
            body=f"Tu {appt.service_type} del {fecha_str} está confirmada.",
            data={"appointment_id": str(appt.id)},
        )
    except Exception:
        pass
    await db.commit()
    await db.refresh(appt)
    return _appt_out(appt)


@router.patch("/{appt_id}/complete", response_model=AppointmentOut)
async def complete_appointment(
    appt_id: uuid.UUID,
    price: float | None = None,
    db: DBSession = None,
    customer: Customer = PortalUser,
) -> AppointmentOut:
    appt = (await db.execute(select(Appointment).where(Appointment.id == appt_id))).scalar_one_or_none()
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
