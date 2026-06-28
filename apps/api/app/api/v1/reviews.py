"""Reseñas de productos — clientes verificados + moderación admin + GBP cache."""
from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select, and_, desc, text

from app.api.v1.portal_auth import PortalUser
from app.api.v1.portal_loyalty import award_points
from app.deps import DBSession, require_permission
from app.models.catalog import GBPReviewCache, Product, ProductReview
from app.models.crm import Customer
from app.models.portal import PortalOrder, PortalOrderItem

# ── Schemas ───────────────────────────────────────────────────────────────────

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: str | None = Field(None, max_length=200)
    comment: str | None = Field(None, max_length=2000)
    photo_urls: list[str] = Field(default_factory=list, max_length=2)
    pet_name: str | None = Field(None, max_length=100)

    @field_validator("photo_urls")
    @classmethod
    def max_two_photos(cls, v: list[str]) -> list[str]:
        if len(v) > 2:
            raise ValueError("Máximo 2 fotos por reseña")
        return v


class ReviewOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    rating: int
    title: str | None
    comment: str | None
    photo_urls: list[str]
    pet_name: str | None
    status: str
    is_verified_purchase: bool
    helpful_count: int
    admin_reply: str | None
    admin_reply_at: datetime | None
    created_at: datetime
    customer_first_name: str | None = None
    points_awarded: int

    model_config = {"from_attributes": True}


class ModerationAction(BaseModel):
    action: Literal["approve", "reject"]
    notes: str | None = None


class AdminReply(BaseModel):
    reply: str = Field(..., min_length=1, max_length=2000)


class GBPMatchRequest(BaseModel):
    customer_id: uuid.UUID


# ── Helpers ───────────────────────────────────────────────────────────────────

POINTS_REVIEW_BASE = 20
POINTS_REVIEW_WITH_PHOTO = 30

async def _has_verified_purchase(db: DBSession, customer_id: uuid.UUID, product_id: uuid.UUID) -> bool:
    """Retorna True si el cliente tiene al menos un pedido entregado con ese producto."""
    q = (
        select(func.count())
        .select_from(PortalOrderItem)
        .join(PortalOrder, PortalOrder.id == PortalOrderItem.portal_order_id)
        .where(
            PortalOrderItem.product_id == product_id,
            PortalOrder.customer_id == customer_id,
            PortalOrder.status == "delivered",
        )
    )
    count = (await db.execute(q)).scalar_one()
    return count > 0


# ── Routers ───────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/v1", tags=["reviews"])
admin_router = APIRouter(prefix="/v1/admin", tags=["admin-reviews"])
public_router = APIRouter(prefix="/v1/public", tags=["public"])


# ── Endpoints públicos de reseñas por producto ────────────────────────────────

@router.get("/products/{product_id}/reviews")
async def list_product_reviews(
    product_id: uuid.UUID,
    page: int = 1,
    page_size: int = 10,
    sort: Literal["recent", "helpful", "rating_high", "rating_low"] = "recent",
    db: DBSession = ...,
):
    page_size = min(page_size, 50)
    base = select(ProductReview).where(
        ProductReview.product_id == product_id,
        ProductReview.status.in_(["approved", "auto_published"]),
    )

    order_col = {
        "recent": desc(ProductReview.created_at),
        "helpful": desc(ProductReview.helpful_count),
        "rating_high": desc(ProductReview.rating),
        "rating_low": ProductReview.rating,
    }[sort]

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        await db.execute(base.order_by(order_col).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()

    # Enriquecer con nombre del cliente
    result = []
    for rev in rows:
        customer = (await db.execute(select(Customer).where(Customer.id == rev.customer_id))).scalar_one_or_none()
        d = ReviewOut.model_validate(rev)
        d.customer_first_name = customer.first_name if customer else "Cliente"
        result.append(d)

    # Aggregate
    product = (await db.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
    aggregate = {
        "avg": float(product.rating_avg) if product and product.rating_avg else 0.0,
        "count": product.rating_count if product else 0,
        "distribution": product.rating_distribution or {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
    }

    return {"reviews": result, "total": total, "aggregate": aggregate, "page": page}


@router.post("/products/{product_id}/reviews/{review_id}/helpful", status_code=200)
async def mark_helpful(
    product_id: uuid.UUID,
    review_id: uuid.UUID,
    request: Request,
    db: DBSession = ...,
):
    """Incrementa helpful_count +1 (rate-limit básico por IP en header)."""
    rev = (
        await db.execute(
            select(ProductReview).where(
                ProductReview.id == review_id,
                ProductReview.product_id == product_id,
                ProductReview.status.in_(["approved", "auto_published"]),
            )
        )
    ).scalar_one_or_none()
    if not rev:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")
    rev.helpful_count += 1
    await db.commit()
    return {"helpful_count": rev.helpful_count}


# ── Endpoints portal cliente ───────────────────────────────────────────────────

@router.post("/portal/products/{product_id}/reviews", status_code=201)
async def create_review(
    product_id: uuid.UUID,
    payload: ReviewCreate,
    customer: Customer = PortalUser,
    db: DBSession = ...,
):
    # Verificar compra
    is_verified = await _has_verified_purchase(db, customer.id, product_id)
    if not is_verified:
        raise HTTPException(
            status_code=403,
            detail="Solo puedes reseñar productos que hayas comprado y recibido.",
        )

    # Verificar que el producto existe y está publicado
    product = (
        await db.execute(select(Product).where(Product.id == product_id, Product.is_published == True))
    ).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Verificar que no haya reseñado antes
    existing = (
        await db.execute(
            select(ProductReview).where(
                ProductReview.customer_id == customer.id,
                ProductReview.product_id == product_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Ya reseñaste este producto")

    # Determinar status y puntos
    has_photo = len(payload.photo_urls) > 0
    pts = POINTS_REVIEW_WITH_PHOTO if has_photo else POINTS_REVIEW_BASE
    auto = payload.rating == 5

    rev = ProductReview(
        product_id=product_id,
        customer_id=customer.id,
        rating=payload.rating,
        title=payload.title,
        comment=payload.comment,
        photo_urls=payload.photo_urls,
        pet_name=payload.pet_name,
        status="auto_published" if auto else "pending",
        is_verified_purchase=True,
        points_awarded=pts if auto else 0,
    )
    db.add(rev)
    await db.flush()  # obtener ID antes del commit

    # Acreditar puntos inmediatamente si es 5 estrellas
    if auto:
        await award_points(
            customer_id=customer.id,
            points=pts,
            reason="review",
            reference_type="product_review",
            reference_id=rev.id,
            description=f"Reseña {'con foto ' if has_photo else ''}de {product.name[:60]}",
            db=db,
        )

    await db.commit()
    await db.refresh(rev)
    return ReviewOut.model_validate(rev)


@router.get("/portal/products/{product_id}/reviews/mine")
async def my_review(
    product_id: uuid.UUID,
    customer: Customer = PortalUser,
    db: DBSession = ...,
):
    rev = (
        await db.execute(
            select(ProductReview).where(
                ProductReview.customer_id == customer.id,
                ProductReview.product_id == product_id,
            )
        )
    ).scalar_one_or_none()
    if not rev:
        return {"review": None}
    return {"review": ReviewOut.model_validate(rev)}


# ── Endpoints admin moderación ─────────────────────────────────────────────────

@admin_router.get("/reviews")
async def admin_list_reviews(
    status_filter: str = "pending",
    page: int = 1,
    page_size: int = 20,
    _=require_permission("admin"),
    db: DBSession = ...,
):
    page_size = min(page_size, 100)
    base = select(ProductReview)
    if status_filter != "all":
        base = base.where(ProductReview.status == status_filter)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        await db.execute(
            base.order_by(desc(ProductReview.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    result = []
    for rev in rows:
        customer = (await db.execute(select(Customer).where(Customer.id == rev.customer_id))).scalar_one_or_none()
        product = (await db.execute(select(Product).where(Product.id == rev.product_id))).scalar_one_or_none()
        d = ReviewOut.model_validate(rev)
        d.customer_first_name = customer.first_name if customer else "Cliente"
        result.append({
            **d.model_dump(),
            "customer_name": f"{customer.first_name or ''} {customer.last_name or ''}".strip() if customer else "Desconocido",
            "customer_phone": customer.phone if customer else None,
            "product_name": product.name if product else "Producto eliminado",
            "product_sku": product.sku if product else None,
            "product_image": product.primary_image_url if product else None,
        })

    return {"reviews": result, "total": total, "page": page}


@admin_router.patch("/reviews/{review_id}")
async def moderate_review(
    review_id: uuid.UUID,
    payload: ModerationAction,
    _=require_permission("admin"),
    db: DBSession = ...,
):
    rev = (await db.execute(select(ProductReview).where(ProductReview.id == review_id))).scalar_one_or_none()
    if not rev:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")

    now = datetime.now(UTC)
    if payload.action == "approve":
        rev.status = "approved"
        rev.moderated_at = now
        rev.moderation_notes = payload.notes

        # Acreditar puntos si no se acreditaron aún
        if rev.points_awarded == 0:
            has_photo = len(rev.photo_urls) > 0
            pts = POINTS_REVIEW_WITH_PHOTO if has_photo else POINTS_REVIEW_BASE
            rev.points_awarded = pts
            product = (await db.execute(select(Product).where(Product.id == rev.product_id))).scalar_one_or_none()
            await award_points(
                customer_id=rev.customer_id,
                points=pts,
                reason="review",
                reference_type="product_review",
                reference_id=rev.id,
                description=f"Reseña aprobada de {product.name[:60] if product else 'producto'}",
                db=db,
            )
    else:
        rev.status = "rejected"
        rev.moderated_at = now
        rev.moderation_notes = payload.notes

    await db.commit()
    await db.refresh(rev)
    return ReviewOut.model_validate(rev)


@admin_router.post("/reviews/{review_id}/reply")
async def reply_review(
    review_id: uuid.UUID,
    payload: AdminReply,
    _=require_permission("admin"),
    db: DBSession = ...,
):
    rev = (await db.execute(select(ProductReview).where(ProductReview.id == review_id))).scalar_one_or_none()
    if not rev:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")
    rev.admin_reply = payload.reply
    rev.admin_reply_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(rev)
    return {"ok": True, "admin_reply": rev.admin_reply}


# ── Endpoint público GBP reviews ──────────────────────────────────────────────

@public_router.get("/gbp-reviews")
async def public_gbp_reviews(limit: int = 6, db: DBSession = ...):
    limit = min(limit, 20)
    rows = (
        await db.execute(
            select(GBPReviewCache)
            .where(GBPReviewCache.rating >= 4)
            .order_by(desc(GBPReviewCache.review_created_at))
            .limit(limit)
        )
    ).scalars().all()

    avg_q = await db.execute(select(func.avg(GBPReviewCache.rating), func.count()).select_from(GBPReviewCache))
    avg_row = avg_q.one()
    avg = round(float(avg_row[0] or 5.0), 1)
    count = avg_row[1] or 0

    reviews = [
        {
            "reviewer_name": r.reviewer_name,
            "reviewer_photo": r.reviewer_photo_url,
            "rating": r.rating,
            "comment": r.comment or "",
            "created_at": r.review_created_at.isoformat() if r.review_created_at else None,
        }
        for r in rows
    ]
    return {"reviews": reviews, "aggregate": {"avg": avg, "count": count}}


# ── Admin GBP ─────────────────────────────────────────────────────────────────

@admin_router.get("/gbp-reviews/unmatched")
async def gbp_unmatched(
    _=require_permission("admin"),
    db: DBSession = ...,
):
    rows = (
        await db.execute(
            select(GBPReviewCache)
            .where(GBPReviewCache.matched_customer_id == None)
            .order_by(desc(GBPReviewCache.review_created_at))
        )
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "reviewer_name": r.reviewer_name,
            "rating": r.rating,
            "comment": r.comment,
            "review_created_at": r.review_created_at.isoformat() if r.review_created_at else None,
            "points_credited": r.points_credited,
        }
        for r in rows
    ]


@admin_router.post("/gbp-reviews/{gbp_id}/match")
async def gbp_match_customer(
    gbp_id: uuid.UUID,
    payload: GBPMatchRequest,
    _=require_permission("admin"),
    db: DBSession = ...,
):
    row = (await db.execute(select(GBPReviewCache).where(GBPReviewCache.id == gbp_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Reseña GBP no encontrada")
    row.matched_customer_id = payload.customer_id
    if row.points_credited == 0:
        row.points_credited = 50
        row.points_credited_at = datetime.now(UTC)
        await award_points(
            customer_id=payload.customer_id,
            points=50,
            reason="gbp_review",
            reference_type="gbp_review",
            reference_id=gbp_id,
            description=f"Reseña en Google: {row.reviewer_name}",
            db=db,
        )
    await db.commit()
    return {"ok": True}
