"""Portal Appointments — citas de grooming, baño, consulta, etc. + disponibilidad."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, select

from app.api.v1.portal_auth import PortalUser
from app.api.v1.portal_loyalty import POINTS_APPOINTMENT, award_points
from app.deps import DBSession
from app.models.crm import Customer
from app.models.portal import Appointment

_TZ_CO = ZoneInfo("America/Bogota")

router = APIRouter(prefix="/portal/appointments", tags=["portal"])

# Horario de la peluquería. 28-sep-2026: antes era 9-12 y 14-17 por defecto (ninguna
# variable puesta en producción) → ofrecía 9 a. m. con la tienda cerrada, nada después de
# las 5, domingos, y no contaba que un baño dura 2 h. El horario real es el de la ficha de
# Google y la web: lunes a sábado de 10 a. m. a 7 p. m. (business-info.ts).
_OPEN_H = int(os.getenv("PORTAL_OPEN_HOURS", "10-19").split("-")[0])
_CLOSE_H = int(os.getenv("PORTAL_OPEN_HOURS", "10-19").split("-")[1])
_CLOSED_WEEKDAYS = {6}  # domingo (date.weekday(): lunes=0)
_SLOT_CAP = int(os.getenv("PORTAL_SLOT_CAPACITY", "1"))
_DEFAULT_DURATION = 120  # baño y peluquería
_MIN_LEAD = timedelta(hours=1)  # hoy: no ofrecer una hora que empieza en menos de 1 h


# ── schemas ───────────────────────────────────────────────────────────


class SlotOut(BaseModel):
    time: str  # "09:00"
    available: bool
    reason: str | None = None


class AvailabilityOut(BaseModel):
    date: str
    service: str
    slots: list[SlotOut]


class AppointmentIn(BaseModel):
    pet_id: str
    service_type: str
    scheduled_at: str  # ISO-8601 con TZ (e.g. "2026-07-01T10:00:00-05:00")
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


async def compute_slots(db, target_date: date, duration_min: int = _DEFAULT_DURATION) -> list[SlotOut]:
    """Horas de inicio para una cita de `duration_min` ese día. Una hora está ocupada si
    alguna cita pendiente o confirmada se cruza con [inicio, inicio + duración). La usan el
    portal y la reserva pública de la web, para que las dos vean lo mismo."""
    if target_date.weekday() in _CLOSED_WEEKDAYS:
        return []
    dur = timedelta(minutes=max(30, min(duration_min, 240)))
    day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=_TZ_CO)
    existing = (
        await db.execute(
            select(Appointment.scheduled_at, Appointment.duration_min).where(
                and_(
                    Appointment.scheduled_at >= day_start - timedelta(hours=6),
                    Appointment.scheduled_at < day_start + timedelta(days=1),
                    Appointment.status.in_(["pending", "confirmed"]),
                )
            )
        )
    ).all()
    now = datetime.now(_TZ_CO)
    slots: list[SlotOut] = []
    h = _OPEN_H
    while day_start + timedelta(hours=h) + dur <= day_start + timedelta(hours=_CLOSE_H):
        ini = day_start + timedelta(hours=h)
        fin = ini + dur
        cruces = sum(
            1 for s_at, s_dur in existing
            if s_at < fin and s_at + timedelta(minutes=s_dur or 60) > ini
        )
        if ini < now + _MIN_LEAD:
            slots.append(SlotOut(time=f"{h:02d}:00", available=False, reason="ya pasó"))
        else:
            ok = cruces < _SLOT_CAP
            slots.append(SlotOut(time=f"{h:02d}:00", available=ok, reason=None if ok else "ocupado"))
        h += 1
    return slots


async def ensure_slot_free(db, scheduled: datetime, duration_min: int) -> None:
    """409 si esa hora ya no está libre (otra persona la tomó mientras elegía) o está
    fuera del horario. Misma regla que ve el calendario."""
    local = scheduled.astimezone(_TZ_CO)
    hora = local.strftime("%H:00")
    slots = await compute_slots(db, local.date(), duration_min)
    slot = next((x for x in slots if x.time == hora), None)
    if slot is None or local.minute != 0:
        raise HTTPException(status_code=422, detail="Esa hora está fuera del horario de la peluquería")
    if not slot.available:
        msg = ("Esa hora ya pasó. Elige otra, por favor." if slot.reason == "ya pasó"
               else "Esa hora se acaba de ocupar. Elige otra, por favor.")
        raise HTTPException(status_code=409, detail=msg)


async def conflictos(db, inicio: datetime, duration_min: int, excluir: uuid.UUID | None = None) -> list[Appointment]:
    """Citas pendientes o confirmadas que se cruzan con [inicio, inicio + duración).
    Es la regla ÚNICA de la agenda (29-sep-2026): la usan la web, el portal y el admin,
    así lo que agenda o acepta el admin bloquea esas horas para todos."""
    fin = inicio + timedelta(minutes=duration_min)
    rows = (
        await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.scheduled_at < fin,
                    Appointment.scheduled_at >= inicio - timedelta(hours=8),
                    Appointment.status.in_(["pending", "confirmed"]),
                )
            )
        )
    ).scalars().all()
    return [
        a for a in rows
        if a.id != excluir and a.scheduled_at + timedelta(minutes=a.duration_min or 60) > inicio
    ]


async def horas_libres_admin(db, target_date: date, duration_min: int) -> list[str]:
    """Para el admin: inicios cada 30 min dentro del horario donde cabe una cita de esa
    duración sin cruzarse con nada. Hoy, desde la media hora en curso."""
    day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=_TZ_CO)
    dur = timedelta(minutes=duration_min)
    ahora = datetime.now(_TZ_CO) - timedelta(minutes=29)
    out: list[str] = []
    t = day_start + timedelta(hours=_OPEN_H)
    while t + dur <= day_start + timedelta(hours=_CLOSE_H):
        if t >= ahora and len(await conflictos(db, t, duration_min)) < _SLOT_CAP:
            out.append(t.strftime("%H:%M"))
        t += timedelta(minutes=30)
    return out


def describir_cruce(citas: list[Appointment]) -> str:
    a = citas[0]
    ini = a.scheduled_at.astimezone(_TZ_CO)
    fin = ini + timedelta(minutes=a.duration_min or 60)
    return f"Se cruza con otra cita de {ini.strftime('%H:%M')} a {fin.strftime('%H:%M')}"


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
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Fecha inválida, usa YYYY-MM-DD") from exc

    if target_date < datetime.now(_TZ_CO).date():
        raise HTTPException(status_code=422, detail="No puedes agendar en días pasados")

    slots = await compute_slots(db, target_date)

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
    if scheduled.tzinfo is None:
        # El portal manda "YYYY-MM-DDTHH:MM:SS" sin offset -- es hora Colombia.
        scheduled = scheduled.replace(tzinfo=_TZ_CO)
    if scheduled <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="La cita debe ser en el futuro")
    await ensure_slot_free(db, scheduled, payload.duration_min)

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
    appt = (
        await db.execute(select(Appointment).where(Appointment.id == appt_id))
    ).scalar_one_or_none()
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
    appt = (
        await db.execute(select(Appointment).where(Appointment.id == appt_id))
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
