"""SOS: animales encontrados/rescatados, agrupados por evento de rescate.

Complementa sos.py (mascotas PERDIDAS, reportadas por el dueño) con el caso
inverso: alguien (hoy, el admin) encontró/rescató uno o más animales en un
mismo lugar y sube sus fotos para que la gente que busca su mascota pueda
reconocerla. Un RescueEvent agrupa N RescueAnimal (una foto + descripción
opcional cada uno).
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.v1.portal_auth import PortalUser
from app.deps import DBSession, require_permission
from app.models.community import RescueAnimal, RescueEvent
from app.models.crm import Customer
from app.services.media_upload import ALLOWED_CONTENT_TYPES, MAX_UPLOAD_BYTES, upload_image_webp

router = APIRouter(prefix="/sos/rescues", tags=["sos"])

MAX_PHOTOS_PER_UPLOAD = 30


# ── schemas ───────────────────────────────────────────────────────────


class RescueEventIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    address: str | None = None
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    found_at: datetime | None = None
    contact_phone: str | None = None


class RescueEventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    address: str | None = None
    contact_phone: str | None = None
    status: str | None = None


class RescueAnimalUpdate(BaseModel):
    description: str | None = None
    species: str | None = None
    status: str | None = None


def _animal_out(a: RescueAnimal) -> dict:
    return {
        "id": str(a.id),
        "photo_url": a.photo_url,
        "thumb_url": a.thumb_url,
        "species": a.species,
        "description": a.description,
        "status": a.status,
        "sort_order": a.sort_order,
    }


def _event_out(row: RescueEvent, animals: list[RescueAnimal] | None = None, distance_km: float | None = None) -> dict:
    animals = animals or []
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
        "unclaimed_count": sum(1 for a in animals if a.status == "unclaimed"),
        "cover_thumb_url": animals[0].thumb_url or animals[0].photo_url if animals else None,
        "animals": [_animal_out(a) for a in animals],
        "distance_km": round(distance_km, 2) if distance_km is not None else None,
    }


async def _get_animals(db: DBSession, event_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[RescueAnimal]]:
    if not event_ids:
        return {}
    rows = (
        await db.execute(
            select(RescueAnimal)
            .where(RescueAnimal.rescue_event_id.in_(event_ids))
            .order_by(RescueAnimal.sort_order, RescueAnimal.created_at)
        )
    ).scalars().all()
    by_event: dict[uuid.UUID, list[RescueAnimal]] = {}
    for a in rows:
        by_event.setdefault(a.rescue_event_id, []).append(a)
    return by_event


# ── endpoints públicos (portal) ──────────────────────────────────────────


@router.get("")
async def list_rescue_events(
    db: DBSession,
    _customer: Customer = PortalUser,
    status_filter: str = Query(default="open", alias="status"),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
) -> list[dict]:
    q = select(RescueEvent).where(RescueEvent.status == status_filter)
    rows = (await db.execute(q)).scalars().all()

    animals_by_event = await _get_animals(db, [r.id for r in rows])

    result = []
    for row in rows:
        distance_km = None
        if lat is not None and lng is not None:
            import math

            dlat, dlng = math.radians(float(row.lat) - lat), math.radians(float(row.lng) - lng)
            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(math.radians(lat)) * math.cos(math.radians(float(row.lat))) * math.sin(dlng / 2) ** 2
            )
            distance_km = 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        result.append(_event_out(row, animals_by_event.get(row.id), distance_km))

    result.sort(key=lambda r: r["found_at"], reverse=True)
    return result


@router.get("/{event_id}")
async def get_rescue_event(event_id: uuid.UUID, db: DBSession, _customer: Customer = PortalUser) -> dict:
    row = (await db.execute(select(RescueEvent).where(RescueEvent.id == event_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Evento de rescate no encontrado")
    animals_by_event = await _get_animals(db, [event_id])
    return _event_out(row, animals_by_event.get(event_id))


# ── endpoints de administración ──────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_rescue_event(
    payload: RescueEventIn,
    db: DBSession,
    admin=Depends(require_permission("crm:write")),
) -> dict:
    event = RescueEvent(
        title=payload.title,
        description=payload.description,
        address=payload.address,
        lat=Decimal(str(payload.lat)),
        lng=Decimal(str(payload.lng)),
        found_at=payload.found_at or datetime.now(UTC),
        contact_phone=payload.contact_phone,
        status="open",
        created_by_admin=admin.full_name if hasattr(admin, "full_name") else None,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return _event_out(event)


@router.patch("/{event_id}")
async def update_rescue_event(
    event_id: uuid.UUID,
    payload: RescueEventUpdate,
    db: DBSession,
    _admin=Depends(require_permission("crm:write")),
) -> dict:
    event = (await db.execute(select(RescueEvent).where(RescueEvent.id == event_id))).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Evento de rescate no encontrado")
    if payload.status is not None and payload.status not in {"open", "closed"}:
        raise HTTPException(status_code=422, detail="status debe ser 'open' o 'closed'")

    for field in ("title", "description", "address", "contact_phone", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(event, field, value)

    await db.commit()
    animals_by_event = await _get_animals(db, [event_id])
    return _event_out(event, animals_by_event.get(event_id))


@router.post("/{event_id}/animals", status_code=status.HTTP_201_CREATED)
async def upload_rescue_animals(
    event_id: uuid.UUID,
    db: DBSession,
    files: list[UploadFile] = File(...),
    descriptions: str | None = Form(default=None),
    _admin=Depends(require_permission("crm:write")),
) -> dict:
    """Sube 1..N fotos de una vez, cada una crea su propia ficha RescueAnimal.

    `descriptions`, si viene, es un JSON array de strings en el mismo orden
    que `files` (índices sin descripción pueden ir como "" o faltar)."""
    event = (await db.execute(select(RescueEvent).where(RescueEvent.id == event_id))).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Evento de rescate no encontrado")
    if len(files) > MAX_PHOTOS_PER_UPLOAD:
        raise HTTPException(status_code=422, detail=f"Máximo {MAX_PHOTOS_PER_UPLOAD} fotos por solicitud")

    desc_list: list[str] = []
    if descriptions:
        try:
            desc_list = json.loads(descriptions)
        except json.JSONDecodeError:
            raise HTTPException(status_code=422, detail="descriptions debe ser un JSON array de strings")

    contents_list: list[bytes] = []
    for f in files:
        if f.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=422, detail=f"{f.filename}: solo se aceptan JPEG, PNG o WebP")
        contents = await f.read()
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"{f.filename}: la imagen no debe superar 5 MB")
        contents_list.append(contents)

    uploaded = await asyncio.gather(
        *[
            asyncio.to_thread(upload_image_webp, contents, key_prefix=f"bigotesypaticas/rescues/{event_id}")
            for contents in contents_list
        ]
    )

    max_order = (
        await db.execute(select(func.coalesce(func.max(RescueAnimal.sort_order), -1)).where(RescueAnimal.rescue_event_id == event_id))
    ).scalar_one()

    new_animals = []
    for i, urls in enumerate(uploaded):
        animal = RescueAnimal(
            rescue_event_id=event_id,
            photo_url=urls["url"],
            thumb_url=urls["thumb_url"],
            description=(desc_list[i] or None) if i < len(desc_list) and desc_list[i] else None,
            status="unclaimed",
            sort_order=max_order + 1 + i,
        )
        db.add(animal)
        new_animals.append(animal)

    await db.commit()
    for a in new_animals:
        await db.refresh(a)
    return {"ok": True, "animals": [_animal_out(a) for a in new_animals]}


@router.patch("/{event_id}/animals/{animal_id}")
async def update_rescue_animal(
    event_id: uuid.UUID,
    animal_id: uuid.UUID,
    payload: RescueAnimalUpdate,
    db: DBSession,
    _admin=Depends(require_permission("crm:write")),
) -> dict:
    animal = (
        await db.execute(
            select(RescueAnimal).where(RescueAnimal.id == animal_id, RescueAnimal.rescue_event_id == event_id)
        )
    ).scalar_one_or_none()
    if not animal:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    if payload.status is not None and payload.status not in {"unclaimed", "reunited"}:
        raise HTTPException(status_code=422, detail="status debe ser 'unclaimed' o 'reunited'")

    for field in ("description", "species", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(animal, field, value)

    await db.commit()
    return _animal_out(animal)


@router.delete("/{event_id}/animals/{animal_id}")
async def delete_rescue_animal(
    event_id: uuid.UUID,
    animal_id: uuid.UUID,
    db: DBSession,
    _admin=Depends(require_permission("crm:write")),
) -> dict:
    animal = (
        await db.execute(
            select(RescueAnimal).where(RescueAnimal.id == animal_id, RescueAnimal.rescue_event_id == event_id)
        )
    ).scalar_one_or_none()
    if not animal:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    await db.delete(animal)
    await db.commit()
    return {"ok": True}
