"""SOS Mascotas Perdidas — comunidad de dueños de mascotas (Fase 1 del plan móvil/comunidad)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text

from app.api.v1.portal_auth import PortalUser
from app.api.v1.portal_notifications import notify_customer
from app.deps import DBSession
from app.models.community import SOSEvent, SOSSighting
from app.models.crm import Customer
from app.services.media_upload import ALLOWED_CONTENT_TYPES, MAX_UPLOAD_BYTES, upload_image_webp
from app.services.seo_notifications import notify_indexnow

router = APIRouter(prefix="/sos", tags=["sos"])

_background_tasks: set[asyncio.Task] = set()


def _ping_indexnow(urls: list[str]) -> None:
    task = asyncio.create_task(notify_indexnow(urls))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


SPECIES = {"perro", "gato", "otro"}


# ── schemas ───────────────────────────────────────────────────────────


class SOSReportIn(BaseModel):
    pet_id: uuid.UUID | None = None
    pet_name: str = Field(min_length=1, max_length=150)
    species: str
    breed: str | None = None
    color: str = Field(min_length=1, max_length=100)
    last_seen_lat: float = Field(ge=-90, le=90)
    last_seen_lng: float = Field(ge=-180, le=180)
    last_seen_at: datetime | None = None
    contact_phone: str = Field(min_length=7, max_length=40)
    reward: Decimal | None = None
    radius_km: int = Field(default=5, ge=1, le=50)


class SightingIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    photo_url: str | None = None
    note: str | None = None
    seen_at: datetime | None = None


def _sos_out(
    row: SOSEvent, reporter_name: str | None = None, distance_km: float | None = None
) -> dict:
    return {
        "id": str(row.id),
        "pet_id": str(row.pet_id) if row.pet_id else None,
        "reporter_customer_id": str(row.reporter_customer_id),
        "reporter_name": reporter_name,
        "pet_name": row.pet_name,
        "species": row.species,
        "breed": row.breed,
        "color": row.color,
        "photos": row.photos or [],
        "last_seen_lat": float(row.last_seen_lat),
        "last_seen_lng": float(row.last_seen_lng),
        "last_seen_at": row.last_seen_at.isoformat(),
        "contact_phone": row.contact_phone,
        "reward": float(row.reward) if row.reward is not None else None,
        "status": row.status,
        "radius_km": row.radius_km,
        "notified_count": row.notified_count,
        "found_at": row.found_at.isoformat() if row.found_at else None,
        "created_at": row.created_at.isoformat(),
        "distance_km": round(distance_km, 2) if distance_km is not None else None,
    }


async def _notify_nearby_customers(
    db: DBSession, event: SOSEvent, *, notif_type: str, title: str, body: str
) -> int:
    """Notificación in-app (no push nativo todavía) a clientes con ubicación dentro del radio."""
    rows = (
        await db.execute(
            text("""
                SELECT id, sos_radius_km,
                    6371 * acos(least(1.0, greatest(-1.0,
                        cos(radians(:lat)) * cos(radians(last_lat)) * cos(radians(last_lng) - radians(:lng))
                        + sin(radians(:lat)) * sin(radians(last_lat))
                    ))) AS distance_km
                FROM crm.customers
                WHERE deleted_at IS NULL
                  AND id != :reporter_id
                  AND last_lat IS NOT NULL
                  AND last_lng IS NOT NULL
                  AND coalesce((notification_prefs->>'sos')::boolean, true) = true
            """),
            {
                "lat": event.last_seen_lat,
                "lng": event.last_seen_lng,
                "reporter_id": event.reporter_customer_id,
            },
        )
    ).all()

    notified = 0
    for r in rows:
        radius = min(event.radius_km, r.sos_radius_km) if r.sos_radius_km else event.radius_km
        if r.distance_km <= radius:
            await notify_customer(
                db,
                r.id,
                notif_type=notif_type,
                title=title,
                body=body,
                data={"sos_event_id": str(event.id), "distance_km": round(r.distance_km, 2)},
            )
            notified += 1
    return notified


# ── endpoints ─────────────────────────────────────────────────────────


@router.post("/report", status_code=status.HTTP_201_CREATED)
async def report_lost_pet(
    payload: SOSReportIn, db: DBSession, customer: Customer = PortalUser
) -> dict:
    if payload.species not in SPECIES:
        raise HTTPException(
            status_code=422, detail=f"species debe ser uno de: {', '.join(SPECIES)}"
        )

    event = SOSEvent(
        pet_id=payload.pet_id,
        reporter_customer_id=customer.id,
        pet_name=payload.pet_name,
        species=payload.species,
        breed=payload.breed,
        color=payload.color,
        photos=[],
        last_seen_lat=payload.last_seen_lat,
        last_seen_lng=payload.last_seen_lng,
        last_seen_at=payload.last_seen_at or datetime.now(UTC),
        contact_phone=payload.contact_phone,
        reward=payload.reward,
        status="active",
        radius_km=payload.radius_km,
    )
    db.add(event)
    await db.flush()

    if payload.pet_id:
        from app.models.portal import Pet

        pet = (await db.execute(select(Pet).where(Pet.id == payload.pet_id))).scalar_one_or_none()
        if pet and pet.customer_id == customer.id:
            pet.is_lost = True

    notified = await _notify_nearby_customers(
        db,
        event,
        notif_type="sos_nearby",
        title=f"🐾 {event.pet_name} se perdió cerca de ti",
        body=f"{customer.full_name} reportó a {event.pet_name} ({event.species}) perdido(a). Toca para ver el reporte.",
    )
    event.notified_count = notified

    await db.commit()
    await db.refresh(event)

    _ping_indexnow(
        [
            "https://bigotesypaticas.com/mascotas-perdidas",
            f"https://bigotesypaticas.com/mascotas-perdidas/{event.id}",
            "https://bigotesypaticas.com/sitemap.xml",
        ]
    )
    return _sos_out(event)


@router.get("/nearby")
async def list_nearby(
    db: DBSession,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    km: int = Query(default=15, ge=1, le=100),
    status_filter: str = Query(default="active", alias="status"),
    _customer: Customer = PortalUser,
) -> list[dict]:
    distance_expr = (
        6371
        * func.acos(
            func.least(
                1.0,
                func.greatest(
                    -1.0,
                    func.cos(func.radians(lat))
                    * func.cos(func.radians(SOSEvent.last_seen_lat))
                    * func.cos(func.radians(SOSEvent.last_seen_lng) - func.radians(lng))
                    + func.sin(func.radians(lat)) * func.sin(func.radians(SOSEvent.last_seen_lat)),
                ),
            )
        )
    ).label("distance_km")

    subq = (
        select(SOSEvent, Customer.full_name.label("reporter_name"), distance_expr)
        .join(Customer, Customer.id == SOSEvent.reporter_customer_id)
        .where(SOSEvent.status == status_filter)
        .subquery()
    )
    rows = (
        await db.execute(
            select(subq).where(subq.c.distance_km <= km).order_by(subq.c.created_at.desc())
        )
    ).all()

    result = []
    for r in rows:
        event = SOSEvent(
            id=r.id,
            pet_id=r.pet_id,
            reporter_customer_id=r.reporter_customer_id,
            pet_name=r.pet_name,
            species=r.species,
            breed=r.breed,
            color=r.color,
            photos=r.photos,
            last_seen_lat=r.last_seen_lat,
            last_seen_lng=r.last_seen_lng,
            last_seen_at=r.last_seen_at,
            contact_phone=r.contact_phone,
            reward=r.reward,
            status=r.status,
            radius_km=r.radius_km,
            notified_count=r.notified_count,
            found_at=r.found_at,
            created_at=r.created_at,
        )
        result.append(_sos_out(event, reporter_name=r.reporter_name, distance_km=r.distance_km))
    return result


@router.get("/{sos_id}")
async def get_sos_detail(
    sos_id: uuid.UUID, db: DBSession, _customer: Customer = PortalUser
) -> dict:
    row = (
        await db.execute(
            select(SOSEvent, Customer.full_name)
            .join(Customer, Customer.id == SOSEvent.reporter_customer_id)
            .where(SOSEvent.id == sos_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    event, reporter_name = row

    sightings = (
        await db.execute(
            select(SOSSighting, Customer.full_name)
            .join(Customer, Customer.id == SOSSighting.spotter_customer_id)
            .where(SOSSighting.sos_event_id == sos_id)
            .order_by(SOSSighting.seen_at.desc())
        )
    ).all()

    out = _sos_out(event, reporter_name=reporter_name)
    out["sightings"] = [
        {
            "id": str(s.id),
            "spotter_name": name,
            "lat": float(s.lat),
            "lng": float(s.lng),
            "photo_url": s.photo_url,
            "note": s.note,
            "seen_at": s.seen_at.isoformat(),
        }
        for s, name in sightings
    ]
    return out


@router.post("/{sos_id}/sighting", status_code=status.HTTP_201_CREATED)
async def report_sighting(
    sos_id: uuid.UUID, payload: SightingIn, db: DBSession, customer: Customer = PortalUser
) -> dict:
    event = (await db.execute(select(SOSEvent).where(SOSEvent.id == sos_id))).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    if event.status != "active":
        raise HTTPException(status_code=409, detail="Este reporte ya no está activo")

    sighting = SOSSighting(
        sos_event_id=sos_id,
        spotter_customer_id=customer.id,
        lat=payload.lat,
        lng=payload.lng,
        photo_url=payload.photo_url,
        note=payload.note,
        seen_at=payload.seen_at or datetime.now(UTC),
    )
    db.add(sighting)

    await notify_customer(
        db,
        event.reporter_customer_id,
        notif_type="sos_sighting",
        title=f"👀 Alguien vio a {event.pet_name}",
        body=f"{customer.full_name} reportó un avistamiento de {event.pet_name}. Toca para ver los detalles.",
        data={"sos_event_id": str(sos_id)},
    )

    await db.commit()
    return {"ok": True}


@router.post("/{sos_id}/found")
async def mark_found(sos_id: uuid.UUID, db: DBSession, customer: Customer = PortalUser) -> dict:
    event = (await db.execute(select(SOSEvent).where(SOSEvent.id == sos_id))).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    if event.reporter_customer_id != customer.id:
        raise HTTPException(status_code=403, detail="Solo quien reportó puede cerrar este caso")

    from app.services import community_lifecycle as lc

    event.status = "found"
    event.found_at, event.public_until = lc.public_window()

    if event.pet_id:
        from app.models.portal import Pet

        pet = (await db.execute(select(Pet).where(Pet.id == event.pet_id))).scalar_one_or_none()
        if pet:
            pet.is_lost = False

    await _notify_nearby_customers(
        db,
        event,
        notif_type="sos_found",
        title=f"🎉 {event.pet_name} fue encontrado(a)",
        body=f"Buenas noticias: {event.pet_name} ya apareció. ¡Gracias por estar pendiente!",
    )

    await db.commit()
    _ping_indexnow(lc.resolved_urls("lost", event.id))
    return {"ok": True, "status": "found"}


@router.post("/{sos_id}/photos")
async def upload_sos_photo(
    sos_id: uuid.UUID, db: DBSession, customer: Customer = PortalUser, file: UploadFile = File(...)
) -> dict:
    event = (await db.execute(select(SOSEvent).where(SOSEvent.id == sos_id))).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    if event.reporter_customer_id != customer.id:
        raise HTTPException(status_code=403, detail="Solo quien reportó puede agregar fotos")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="Solo se aceptan imágenes JPEG, PNG o WebP")
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="La imagen no debe superar 5 MB")

    urls = upload_image_webp(contents, key_prefix=f"bigotesypaticas/sos/{sos_id}")
    event.photos = [*(event.photos or []), urls["url"]]

    await db.commit()
    return {"ok": True, "url": urls["url"], "thumb_url": urls["thumb_url"], "photos": event.photos}
