"""Aprobación de aliados — panel admin de BP (registro público, revisión staff)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.deps import DBSession, require_permission
from app.models.partners import Partner

router = APIRouter(
    prefix="/admin/partners",
    tags=["admin"],
    dependencies=[Depends(require_permission("partners:read"))],
)


def _partner_out(p: Partner) -> dict:
    return {
        "id": str(p.id),
        "slug": p.slug,
        "partner_type": p.partner_type,
        "business_name": p.business_name,
        "legal_name": p.legal_name,
        "document_id": p.document_id,
        "email": p.email,
        "phone": p.phone,
        "whatsapp": p.whatsapp,
        "address": p.address,
        "city": p.city,
        "bio": p.bio,
        "rating_avg": float(p.rating_avg),
        "rating_count": p.rating_count,
        "is_published": p.published_at is not None,
        "is_verified": p.verified_at is not None,
        "created_at": p.created_at.isoformat(),
    }


@router.get("")
async def list_partners(
    db: DBSession,
    status_filter: str = Query(default="pending", alias="status"),
) -> list[dict]:
    stmt = select(Partner).where(Partner.deleted_at.is_(None))
    if status_filter == "pending":
        stmt = stmt.where(Partner.published_at.is_(None))
    elif status_filter == "published":
        stmt = stmt.where(Partner.published_at.is_not(None))
    elif status_filter != "all":
        raise HTTPException(422, "status debe ser: pending | published | all")
    stmt = stmt.order_by(Partner.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [_partner_out(p) for p in rows]


async def _get_partner(partner_id: uuid.UUID, db: DBSession) -> Partner:
    partner = (
        await db.execute(select(Partner).where(Partner.id == partner_id))
    ).scalar_one_or_none()
    if partner is None:
        raise HTTPException(404, "Aliado no encontrado")
    return partner


@router.patch("/{partner_id}/approve", dependencies=[Depends(require_permission("partners:write"))])
async def approve_partner(partner_id: uuid.UUID, db: DBSession) -> dict:
    partner = await _get_partner(partner_id, db)
    partner.published_at = datetime.now(UTC)
    await db.commit()
    return {"ok": True, "published": True}


@router.patch("/{partner_id}/reject", dependencies=[Depends(require_permission("partners:write"))])
async def reject_partner(partner_id: uuid.UUID, db: DBSession) -> dict:
    partner = await _get_partner(partner_id, db)
    partner.published_at = None
    partner.deleted_at = datetime.now(UTC)
    await db.commit()
    return {"ok": True}


@router.patch("/{partner_id}/verify", dependencies=[Depends(require_permission("partners:write"))])
async def toggle_verified(partner_id: uuid.UUID, db: DBSession) -> dict:
    partner = await _get_partner(partner_id, db)
    partner.verified_at = None if partner.verified_at is not None else datetime.now(UTC)
    await db.commit()
    return {"ok": True, "verified": partner.verified_at is not None}
