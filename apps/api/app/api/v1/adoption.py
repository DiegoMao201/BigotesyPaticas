"""Foro de adopción: quien da un animal en adopción y quien busca adoptar.

Publicar (crear + subir fotos) es siempre del cliente logueado en el portal
(PortalUser), igual que sos.py/rescues.py. La lectura pública para el store
vive en community_public.py (sin auth).
"""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.v1.portal_auth import PortalUser
from app.deps import DBSession
from app.models.community import AdoptionListing
from app.models.crm import Customer
from app.services.media_upload import ALLOWED_CONTENT_TYPES, MAX_UPLOAD_BYTES, upload_image_webp

router = APIRouter(prefix="/adoption", tags=["adoption"])

MAX_PHOTOS_PER_UPLOAD = 15


class AdoptionListingIn(BaseModel):
    post_type: str
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    species: str | None = None
    breed: str | None = None
    address: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    delivery_notes: str | None = None
    contact_phone: str = Field(min_length=7, max_length=40)


def _listing_out(row: AdoptionListing) -> dict:
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
        "created_at": row.created_at.isoformat(),
    }


@router.post("/listings", status_code=status.HTTP_201_CREATED)
async def create_adoption_listing(
    payload: AdoptionListingIn, db: DBSession, customer: Customer = PortalUser
) -> dict:
    if payload.post_type not in {"offer", "want"}:
        raise HTTPException(status_code=422, detail="post_type debe ser 'offer' o 'want'")
    if payload.post_type == "offer" and (payload.lat is None or payload.lng is None):
        raise HTTPException(status_code=422, detail="Para dar un animal en adopción necesitamos la ubicación")

    listing = AdoptionListing(
        reporter_customer_id=customer.id,
        post_type=payload.post_type,
        title=payload.title,
        description=payload.description,
        species=payload.species,
        breed=payload.breed,
        address=payload.address,
        lat=Decimal(str(payload.lat)) if payload.lat is not None else None,
        lng=Decimal(str(payload.lng)) if payload.lng is not None else None,
        delivery_notes=payload.delivery_notes,
        contact_phone=payload.contact_phone,
        photos=[],
        status="open",
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return _listing_out(listing)


@router.get("/listings")
async def list_my_and_public_listings(
    db: DBSession, _customer: Customer = PortalUser, post_type: str | None = None
) -> list[dict]:
    q = select(AdoptionListing).where(AdoptionListing.status == "open")
    if post_type:
        q = q.where(AdoptionListing.post_type == post_type)
    rows = (await db.execute(q.order_by(AdoptionListing.created_at.desc()))).scalars().all()
    return [_listing_out(r) for r in rows]


@router.get("/listings/{listing_id}")
async def get_adoption_listing(listing_id: uuid.UUID, db: DBSession, _customer: Customer = PortalUser) -> dict:
    row = (
        await db.execute(select(AdoptionListing).where(AdoptionListing.id == listing_id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    return _listing_out(row)


@router.post("/listings/{listing_id}/photos", status_code=status.HTTP_201_CREATED)
async def upload_adoption_photos(
    listing_id: uuid.UUID,
    db: DBSession,
    customer: Customer = PortalUser,
    files: list[UploadFile] = File(...),
) -> dict:
    listing = (
        await db.execute(select(AdoptionListing).where(AdoptionListing.id == listing_id))
    ).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    if listing.reporter_customer_id != customer.id:
        raise HTTPException(status_code=403, detail="Solo quien publicó puede agregar fotos")
    if len(files) > MAX_PHOTOS_PER_UPLOAD:
        raise HTTPException(status_code=422, detail=f"Máximo {MAX_PHOTOS_PER_UPLOAD} fotos por solicitud")

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
            asyncio.to_thread(upload_image_webp, contents, key_prefix=f"bigotesypaticas/adoption/{listing_id}")
            for contents in contents_list
        ]
    )
    listing.photos = [*(listing.photos or []), *[u["url"] for u in uploaded]]
    await db.commit()
    return {"ok": True, "photos": listing.photos}
