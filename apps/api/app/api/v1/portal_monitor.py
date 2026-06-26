"""Admin endpoint — /v1/admin/pet-monitor: KPIs + feeds del portal (polling 30s)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import and_, func, select

from app.deps import CurrentUser, DBSession
from app.models.portal import Appointment, LoyaltyPoint, PortalNotification, PortalOrder, PortalSession

router = APIRouter(prefix="/admin/pet-monitor", tags=["admin"])


# ── schemas ───────────────────────────────────────────────────────────

class MonitorKPIs(BaseModel):
    active_sessions_24h: int
    orders_pending: int
    appointments_today: int
    loyalty_points_issued_30d: int


class PendingOrder(BaseModel):
    id: str
    customer_name: str | None
    product_name: str
    quantity: int
    status: str
    created_at: str


class UpcomingAppointment(BaseModel):
    id: str
    customer_name: str | None
    pet_name: str | None
    service_type: str
    scheduled_at: str
    status: str


class MonitorResponse(BaseModel):
    kpis: MonitorKPIs
    pending_orders: list[PendingOrder]
    upcoming_appointments: list[UpcomingAppointment]
    as_of: str


# ── endpoint ──────────────────────────────────────────────────────────

@router.get("", response_model=MonitorResponse)
async def pet_monitor(
    db: DBSession,
    _user: CurrentUser,
) -> MonitorResponse:
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # ── KPIs ──────────────────────────────────────────────────────────

    # Sesiones activas últimas 24h
    active_sessions = (
        await db.execute(
            select(func.count(PortalSession.id)).where(
                and_(
                    PortalSession.expires_at > now,
                    PortalSession.created_at >= now - timedelta(hours=24),
                )
            )
        )
    ).scalar_one()

    # Pedidos pendientes (received + processing)
    orders_pending = (
        await db.execute(
            select(func.count(PortalOrder.id)).where(
                PortalOrder.status.in_(["received", "processing"])
            )
        )
    ).scalar_one()

    # Citas de hoy
    appts_today = (
        await db.execute(
            select(func.count(Appointment.id)).where(
                and_(
                    Appointment.scheduled_at >= today_start,
                    Appointment.scheduled_at < today_end,
                    Appointment.status.in_(["pending", "confirmed"]),
                )
            )
        )
    ).scalar_one()

    # Puntos otorgados en 30 días
    points_30d = (
        await db.execute(
            select(func.coalesce(func.sum(LoyaltyPoint.points), 0)).where(
                and_(
                    LoyaltyPoint.points > 0,
                    LoyaltyPoint.created_at >= now - timedelta(days=30),
                )
            )
        )
    ).scalar_one()

    # ── Pending orders (con nombre de cliente via join) ─────────────

    from app.models.crm import Customer

    pending_orders_rows = (
        await db.execute(
            select(PortalOrder, Customer.full_name)
            .join(Customer, Customer.id == PortalOrder.customer_id, isouter=True)
            .where(PortalOrder.status.in_(["received", "processing"]))
            .order_by(PortalOrder.created_at.desc())
            .limit(30)
        )
    ).all()

    # ── Upcoming appointments ─────────────────────────────────────────

    from app.models.portal import Pet

    appt_rows = (
        await db.execute(
            select(Appointment, Customer.full_name, Pet.name.label("pet_name"))
            .join(Customer, Customer.id == Appointment.customer_id, isouter=True)
            .join(Pet, Pet.id == Appointment.pet_id, isouter=True)
            .where(
                and_(
                    Appointment.scheduled_at >= now,
                    Appointment.scheduled_at <= now + timedelta(days=7),
                    Appointment.status.in_(["pending", "confirmed"]),
                )
            )
            .order_by(Appointment.scheduled_at)
            .limit(20)
        )
    ).all()

    return MonitorResponse(
        kpis=MonitorKPIs(
            active_sessions_24h=int(active_sessions),
            orders_pending=int(orders_pending),
            appointments_today=int(appts_today),
            loyalty_points_issued_30d=int(points_30d),
        ),
        pending_orders=[
            PendingOrder(
                id=str(row.PortalOrder.id),
                customer_name=row.full_name,
                product_name=row.PortalOrder.product_name,
                quantity=row.PortalOrder.quantity,
                status=row.PortalOrder.status,
                created_at=row.PortalOrder.created_at.isoformat(),
            )
            for row in pending_orders_rows
        ],
        upcoming_appointments=[
            UpcomingAppointment(
                id=str(row.Appointment.id),
                customer_name=row.full_name,
                pet_name=row.pet_name,
                service_type=row.Appointment.service_type,
                scheduled_at=row.Appointment.scheduled_at.isoformat(),
                status=row.Appointment.status,
            )
            for row in appt_rows
        ],
        as_of=now.isoformat(),
    )
