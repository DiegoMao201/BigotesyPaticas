"""Modelos del bounded context `catalog` — productos, categorías, marcas, variantes."""
from __future__ import annotations

import datetime
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Index
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

    brand: Mapped[Brand | None] = relationship(Brand, lazy="joined")
    category: Mapped[Category | None] = relationship(Category, lazy="joined")
