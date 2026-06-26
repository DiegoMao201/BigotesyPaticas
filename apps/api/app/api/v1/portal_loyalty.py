"""Portal Loyalty — puntos de fidelización.

Reglas:
  purchase / portal_order : 1 punto por $1.000 COP
  appointment (completed) : 50 puntos
  referral                : 200 puntos
  Vigencia                : 12 meses desde la creación
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import and_, func, select

from app.api.v1.portal_auth import PortalUser
from app.deps import DBSession
from app.models.crm import Customer
from app.models.portal import LoyaltyPoint

router = APIRouter(prefix="/portal/loyalty", tags=["portal"])

POINTS_PER_THOUSAND = 1
POINTS_APPOINTMENT = 50
POINTS_REFERRAL = 200


# ── helper usado por otros routers ────────────────────────────────────

async def award_points(
    *,
    customer_id: uuid.UUID,
    points: int,
    reason: str,
    reference_type: str | None,
    reference_id: uuid.UUID | None,
    description: str | None,
    db: DBSession,
) -> LoyaltyPoint:
    lp = LoyaltyPoint(
        customer_id=customer_id,
        points=points,
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        expires_at=datetime.now(UTC) + timedelta(days=365),
    )
    db.add(lp)
    await db.commit()
    await db.refresh(lp)
    return lp


# ── schemas ───────────────────────────────────────────────────────────

class LoyaltyOut(BaseModel):
    id: str
    points: int
    reason: str
    description: str | None
    expires_at: str
    created_at: str


class BalanceOut(BaseModel):
    total_active: int
    total_earned_lifetime: int
    history: list[LoyaltyOut]


# ── endpoints ─────────────────────────────────────────────────────────

@router.get("/balance", response_model=BalanceOut)
async def get_balance(db: DBSession, customer: Customer = PortalUser) -> BalanceOut:
    now = datetime.now(UTC)

    active_q = select(func.coalesce(func.sum(LoyaltyPoint.points), 0)).where(
        and_(
            LoyaltyPoint.customer_id == customer.id,
            LoyaltyPoint.expires_at > now,
            LoyaltyPoint.redeemed_at == None,  # noqa: E711
            LoyaltyPoint.points > 0,
        )
    )
    total_active = (await db.execute(active_q)).scalar_one()

    lifetime_q = select(func.coalesce(func.sum(LoyaltyPoint.points), 0)).where(
        and_(
            LoyaltyPoint.customer_id == customer.id,
            LoyaltyPoint.points > 0,
        )
    )
    total_lifetime = (await db.execute(lifetime_q)).scalar_one()

    history = (
        await db.execute(
            select(LoyaltyPoint)
            .where(LoyaltyPoint.customer_id == customer.id)
            .order_by(LoyaltyPoint.created_at.desc())
            .limit(50)
        )
    ).scalars().all()

    return BalanceOut(
        total_active=int(total_active),
        total_earned_lifetime=int(total_lifetime),
        history=[
            LoyaltyOut(
                id=str(lp.id),
                points=lp.points,
                reason=lp.reason,
                description=lp.description,
                expires_at=lp.expires_at.isoformat(),
                created_at=lp.created_at.isoformat(),
            )
            for lp in history
        ],
    )
