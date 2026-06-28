"""Modelos del bounded context `catalog` — productos, categorías, marcas, variantes."""
from __future__ import annotations

import datetime
import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Index, ARRAY
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import (
    AuditMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPKMixin,
)


class Brand(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "brands"
    __table_args__ = (UniqueConstraint("slug", name="uq_brands_slug"), {"schema": "catalog"})

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False, index=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Category(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("slug", name="uq_categories_slug"), {"schema": "catalog"})

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    children: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent", remote_side="Category.parent_id"
    )
    parent: Mapped["Category | None"] = relationship("Category", back_populates="children", remote_side="Category.id")


class Product(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_products_sku"),
        UniqueConstraint("slug", name="uq_products_slug"),
        Index("ix_products_name_trgm", "name", postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),
        {"schema": "catalog"},
    )

    sku: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(280), nullable=False, index=True)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.brands.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Precios (en COP, sin decimales en práctica, pero soportamos)
    cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    compare_at_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    margin_pct: Mapped[float] = mapped_column(Numeric(5, 4), default=0.20, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Multimedia y SEO
    primary_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    images: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    seo_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seo_description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Atributos extensibles (peso, tamaño, especie, etc.)
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    # Enriquecimiento IA (columnas añadidas via ALTER TABLE IF NOT EXISTS)
    enriched_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    enriched_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True, default=None)
    enriched_model: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)

    # Filtros avanzados de catálogo (sprint-3, migración 0015)
    life_stage: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    size_range: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    health_concerns: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True, default=None)
    pet_type: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)
    brand_normalized: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)

    # Rating agregado (recalculado por trigger trg_recalc_product_rating)
    rating_avg: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True, default=None)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating_distribution: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)

    brand: Mapped[Brand | None] = relationship(Brand, lazy="joined")
    category: Mapped[Category | None] = relationship(Category, lazy="joined")


class ProductReview(UUIDPKMixin, Base):
    """Reseñas verificadas de productos por clientes con pedido entregado."""
    __tablename__ = "product_reviews"
    __table_args__ = (
        UniqueConstraint("customer_id", "product_id", name="uq_review_customer_product"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_review_rating"),
        CheckConstraint(
            "status IN ('pending','approved','rejected','auto_published')",
            name="ck_review_status",
        ),
        Index("idx_product_reviews_product", "product_id", "status", "created_at"),
        {"schema": "catalog"},
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalog.products.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crm.customers.id", ondelete="CASCADE"), nullable=False
    )
    sales_order_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_urls: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    pet_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pet_breed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    moderation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    moderated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    moderated_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
    admin_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_reply_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
    is_verified_purchase: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    helpful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(nullable=False, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(nullable=False, default=datetime.datetime.utcnow)

    product: Mapped[Product] = relationship(Product, backref="reviews", lazy="select")


class GBPReviewCache(UUIDPKMixin, Base):
    """Cache local de reseñas de Google Business Profile."""
    __tablename__ = "gbp_reviews_cache"
    __table_args__ = (
        Index("idx_gbp_reviews_matched", "matched_customer_id"),
        Index("idx_gbp_reviews_created", "review_created_at"),
        {"schema": "catalog"},
    )

    google_review_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    reviewer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reviewer_photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    relative_time: Mapped[str | None] = mapped_column(String(100), nullable=True)
    review_created_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
    business_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_reply_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime.datetime] = mapped_column(nullable=False, default=datetime.datetime.utcnow)
    matched_customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crm.customers.id"), nullable=True
    )
    points_credited: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    points_credited_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
