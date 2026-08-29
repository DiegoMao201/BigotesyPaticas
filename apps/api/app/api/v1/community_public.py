"""Lectura pública (sin auth) de la comunidad -- para que el store (sitio
público indexado por Google) muestre mascotas perdidas, animales encontrados
y el foro de adopción. Publicar sigue siendo siempre del portal (sos.py,
rescues.py, adoption.py, todos detrás de PortalUser) -- este router es
100% de solo lectura, pensado para SSR/generateMetadata/sitemap.

No se expone el nombre de quien reportó (privacidad en una página pública
indexada); el teléfono de contacto sí, porque quien publicó lo hizo
explícitamente para que la comunidad lo contacte.
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.deps import DBSession
from app.models.community import AdoptionListing, RescueAnimal, RescueEvent, SOSEvent
from app.services.seo_notifications import notify_indexnow

router = APIRouter(prefix="/public/community", tags=["community-public"])

MAX_QUICK_POSTS_PER_PHONE_PER_DAY = 5

_background_tasks: set[asyncio.Task] = set()


def _ping_indexnow(urls: list[str]) -> None:
    task = asyncio.create_task(notify_indexnow(urls))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def _lost_out(row: SOSEvent) -> dict:
    return {
        "id": str(row.id),
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
        "created_at": row.created_at.isoformat(),
    }


def _animal_out(a: RescueAnimal) -> dict:
    return {
        "id": str(a.id),
        "photo_url": a.photo_url,
        "thumb_url": a.thumb_url,
        "species": a.species,
        "description": a.description,
        "status": a.status,
    }


def _found_out(row: RescueEvent, animals: list[RescueAnimal]) -> dict:
    return {
        "id": str(row.id),
        "title": row.title,
        "description": row.description,
        "address": row.address,
        "lat": float(row.lat),
        "lng": float(row.lng),
        "found_at": row.found_at.isoformat(),
        "contact_phone": row.contact_phone,
        "status": row.status,
        "created_at": row.created_at.isoformat(),
        "animal_count": len(animals),
        "cover_thumb_url": (animals[0].thumb_url or animals[0].photo_url) if animals else None,
        "animals": [_animal_out(a) for a in animals],
    }


def _adoption_out(row: AdoptionListing) -> dict:
    return {
        "id": str(row.id),
        "post_type": row.post_type,
        "reporter_name": row.reporter_name,
        "title": row.title,
        "description": row.description,
        "species": row.species,
        "breed": row.breed,
        "address": row.address,
        "lat": float(row.lat) if row.lat is not None else None,
        "lng": float(row.lng) if row.lng is not None else None,
        "delivery_notes": row.delivery_notes,
        "contact_phone": row.contact_phone,
        "photos": row.photos or [],
        "status": row.status,
        "outcome": row.outcome,
        "outcome_note": row.outcome_note,
        "outcome_at": row.outcome_at.isoformat() if row.outcome_at else None,
        "created_at": row.created_at.isoformat(),
    }


class QuickAdoptionPostIn(BaseModel):
    post_type: str
    reporter_name: str = Field(min_length=2, max_length=150)
    contact_phone: str = Field(min_length=7, max_length=40)
    message: str = Field(min_length=5, max_length=1000)
    accepted_privacy: bool


# ── mascotas perdidas ─────────────────────────────────────────────────


@router.get("/lost")
async def public_list_lost(db: DBSession, limit: int = Query(default=100, le=300)) -> list[dict]:
    rows = (
        (
            await db.execute(
                select(SOSEvent)
                .where(SOSEvent.status == "active")
                .order_by(SOSEvent.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [_lost_out(r) for r in rows]


@router.get("/lost/{event_id}")
async def public_get_lost(event_id: uuid.UUID, db: DBSession) -> dict:
    row = (await db.execute(select(SOSEvent).where(SOSEvent.id == event_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return _lost_out(row)


# ── animales encontrados/rescatados ──────────────────────────────────


@router.get("/found")
async def public_list_found(db: DBSession, limit: int = Query(default=100, le=300)) -> list[dict]:
    rows = (
        (
            await db.execute(
                select(RescueEvent)
                .where(RescueEvent.status == "open")
                .order_by(RescueEvent.found_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    event_ids = [r.id for r in rows]
    animals_by_event: dict[uuid.UUID, list[RescueAnimal]] = {}
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
    return [_found_out(r, animals_by_event.get(r.id, [])) for r in rows]


@router.get("/found/{event_id}")
async def public_get_found(event_id: uuid.UUID, db: DBSession) -> dict:
    row = (
        await db.execute(select(RescueEvent).where(RescueEvent.id == event_id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Evento de rescate no encontrado")
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
    return _found_out(row, animals)


# ── foro de adopción ──────────────────────────────────────────────────


@router.get("/adoption")
async def public_list_adoption(
    db: DBSession,
    post_type: str | None = Query(default=None),
    outcome: str | None = Query(default=None),
    limit: int = Query(default=100, le=300),
) -> list[dict]:
    q = select(AdoptionListing).where(AdoptionListing.status == "open")
    if post_type:
        q = q.where(AdoptionListing.post_type == post_type)
    if outcome:
        q = q.where(AdoptionListing.outcome == outcome)
    order_col = AdoptionListing.outcome_at if outcome == "matched" else AdoptionListing.created_at
    rows = (await db.execute(q.order_by(order_col.desc()).limit(limit))).scalars().all()
    return [_adoption_out(r) for r in rows]


@router.get("/adoption/{listing_id}")
async def public_get_adoption(listing_id: uuid.UUID, db: DBSession) -> dict:
    row = (
        await db.execute(select(AdoptionListing).where(AdoptionListing.id == listing_id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    return _adoption_out(row)


@router.post("/adoption/quick-post", status_code=status.HTTP_201_CREATED)
async def public_quick_adoption_post(payload: QuickAdoptionPostIn, db: DBSession) -> dict:
    """Foro rápido del store: cualquiera publica con solo nombre + teléfono,
    sin necesidad de cuenta en el portal. Se muestra de inmediato (sin
    revisión previa) -- el admin puede borrarla después si hace falta."""
    if payload.post_type not in {"offer", "want"}:
        raise HTTPException(status_code=422, detail="post_type debe ser 'offer' o 'want'")
    if not payload.accepted_privacy:
        raise HTTPException(
            status_code=422,
            detail="Debes aceptar que tu nombre y teléfono sean visibles para publicar",
        )

    phone = payload.contact_phone.strip()
    from datetime import UTC, datetime, timedelta

    recent_count = (
        await db.execute(
            select(AdoptionListing).where(
                AdoptionListing.contact_phone == phone,
                AdoptionListing.created_at >= datetime.now(UTC) - timedelta(hours=24),
            )
        )
    ).all()
    if len(recent_count) >= MAX_QUICK_POSTS_PER_PHONE_PER_DAY:
        raise HTTPException(
            status_code=429, detail="Ya publicaste varias veces hoy, intenta más tarde"
        )

    message = payload.message.strip()
    listing = AdoptionListing(
        reporter_customer_id=None,
        reporter_name=payload.reporter_name.strip(),
        post_type=payload.post_type,
        title=message[:80],
        description=message,
        contact_phone=phone,
        photos=[],
        status="open",
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)

    _ping_indexnow(
        [
            "https://bigotesypaticas.com/adopcion",
            f"https://bigotesypaticas.com/adopcion/{listing.id}",
            "https://bigotesypaticas.com/sitemap.xml",
        ]
    )
    return _adoption_out(listing)
