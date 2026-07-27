"""Directorio público de aliados/servicios (Fase 3 del plan móvil/comunidad).

Solo lectura, sin autenticación — es un directorio público. Agendamiento,
disponibilidad y dashboard de aliados quedan para la siguiente iteración.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.deps import DBSession
from app.models.partners import Partner, Service

router = APIRouter(prefix="/partners", tags=["partners"])

PARTNER_TYPES = {"vet", "walker", "shelter", "groomer"}


def _partner_out(p: Partner) -> dict:
    return {
        "id": str(p.id),
        "slug": p.slug,
        "partner_type": p.partner_type,
        "business_name": p.business_name,
        "city": p.city,
        "address": p.address,
        "lat": float(p.lat) if p.lat is not None else None,
        "lng": float(p.lng) if p.lng is not None else None,
        "logo_url": p.logo_url,
        "cover_url": p.cover_url,
        "bio": p.bio,
        "phone": p.phone,
        "whatsapp": p.whatsapp,
        "rating_avg": float(p.rating_avg),
        "rating_count": p.rating_count,
        "verified": p.verified_at is not None,
    }


def _service_out(s: Service) -> dict:
    return {
        "id": str(s.id),
        "slug": s.slug,
        "name": s.name,
        "description": s.description,
        "duration_min": s.duration_min,
        "price": float(s.price) if s.price is not None else None,
        "price_type": s.price_type,
        "category": s.category,
        "requires_pet": s.requires_pet,
    }


async def _get_published_partner(slug: str, db: DBSession) -> Partner:
    partner = (
        await db.execute(select(Partner).where(Partner.slug == slug, Partner.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if partner is None or partner.published_at is None:
        raise HTTPException(status_code=404, detail="Aliado no encontrado")
    return partner


@router.get("")
async def list_partners(
    db: DBSession,
    type: str | None = Query(default=None),
    city: str | None = None,
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    km: int = Query(default=20, ge=1, le=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    if type is not None and type not in PARTNER_TYPES:
        raise HTTPException(422, f"type debe ser uno de: {', '.join(sorted(PARTNER_TYPES))}")

    stmt = select(Partner).where(Partner.published_at.is_not(None), Partner.deleted_at.is_(None))
    if type:
        stmt = stmt.where(Partner.partner_type == type)
    if city:
        stmt = stmt.where(func.lower(Partner.city) == city.lower())

    if lat is not None and lng is not None:
        distance_expr = 6371 * func.acos(
            func.least(
                1.0,
                func.greatest(
                    -1.0,
                    func.cos(func.radians(lat))
                    * func.cos(func.radians(Partner.lat))
                    * func.cos(func.radians(Partner.lng) - func.radians(lng))
                    + func.sin(func.radians(lat)) * func.sin(func.radians(Partner.lat)),
                ),
            )
        )
        stmt = stmt.where(Partner.lat.is_not(None), Partner.lng.is_not(None), distance_expr <= km)
        stmt = stmt.order_by(distance_expr.asc())
    else:
        stmt = stmt.order_by(Partner.rating_avg.desc(), Partner.business_name.asc())

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    return {
        "items": [_partner_out(p) for p in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{slug}")
async def get_partner(slug: str, db: DBSession) -> dict:
    partner = await _get_published_partner(slug, db)
    return _partner_out(partner)


@router.get("/{slug}/services")
async def list_partner_services(slug: str, db: DBSession) -> list[dict]:
    partner = await _get_published_partner(slug, db)
    services = (
        (
            await db.execute(
                select(Service)
                .where(Service.partner_id == partner.id, Service.is_active.is_(True))
                .order_by(Service.category, Service.name)
            )
        )
        .scalars()
        .all()
    )
    return [_service_out(s) for s in services]
