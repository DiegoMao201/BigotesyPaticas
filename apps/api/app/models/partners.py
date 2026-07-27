"""Modelos del schema `partners` — directorio de aliados (Fase 3 del plan comunidad)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common import Base, SoftDeleteMixin, TimestampMixin, UUIDPKMixin


class Partner(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Aliado del directorio: veterinaria, paseador, refugio o peluquería."""

    __tablename__ = "partners"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_partners_slug"),
        CheckConstraint(
            "partner_type IN ('vet','walker','shelter','groomer')", name="ck_partners_type"
        ),
        {"schema": "partners"},
    )

    slug: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    partner_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    business_name: Mapped[str] = mapped_column(String(160), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(160), nullable=False)
    document_id: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(40), nullable=True)
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating_avg: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False, default=0)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    commission_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    extra: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class Service(UUIDPKMixin, TimestampMixin, Base):
    """Servicio ofrecido por un aliado (sin disponibilidad/agendamiento todavía)."""

    __tablename__ = "services"
    __table_args__ = (
        UniqueConstraint("partner_id", "slug", name="uq_services_partner_slug"),
        CheckConstraint("price_type IN ('fixed','from','quote')", name="ck_services_price_type"),
        {"schema": "partners"},
    )

    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_type: Mapped[str] = mapped_column(String(10), nullable=False, default="fixed")
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    requires_pet: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
