"""Portal Location — captura la última ubicación del cliente (para SOS y directorio de aliados)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.v1.portal_auth import PortalUser
from app.deps import DBSession
from app.models.crm import Customer

router = APIRouter(prefix="/portal/location", tags=["portal"])


class LocationIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class NotificationPrefsIn(BaseModel):
    sos: bool | None = None
    promos: bool | None = None
    appointments: bool | None = None
    sos_radius_km: int | None = Field(default=None, ge=1, le=50)


@router.post("")
async def update_location(
    payload: LocationIn, db: DBSession, customer: Customer = PortalUser
) -> dict:
    """Actualiza la última ubicación conocida del cliente (throttled en el cliente, no aquí)."""
    customer.last_lat = payload.lat
    customer.last_lng = payload.lng
    customer.last_location_at = datetime.now(UTC)
    await db.commit()
    return {"ok": True}


@router.put("/preferences")
async def update_notification_prefs(
    payload: NotificationPrefsIn, db: DBSession, customer: Customer = PortalUser
) -> dict:
    """Actualiza preferencias de notificación (SOS/promos/citas) y radio de alertas SOS."""
    prefs = dict(customer.notification_prefs or {})
    if payload.sos is not None:
        prefs["sos"] = payload.sos
    if payload.promos is not None:
        prefs["promos"] = payload.promos
    if payload.appointments is not None:
        prefs["appointments"] = payload.appointments
    customer.notification_prefs = prefs
    if payload.sos_radius_km is not None:
        customer.sos_radius_km = payload.sos_radius_km
    await db.commit()
    return {"ok": True, "notification_prefs": prefs, "sos_radius_km": customer.sos_radius_km}
