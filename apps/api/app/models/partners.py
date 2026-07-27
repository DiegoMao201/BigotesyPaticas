"""Modelos del schema `partners` — directorio de aliados (Fase 3 del plan comunidad)."""

from __future__ import annotations

import uuid
from datetime import datetime, time
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
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
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


class PartnerUser(UUIDPKMixin, TimestampMixin, Base):
    """Cuenta de acceso al panel del aliado (login propio, separado de admin/portal)."""

    __tablename__ = "partner_users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_partner_users_email"),
        CheckConstraint("role IN ('owner','staff')", name="ck_partner_users_role"),
        {"schema": "partners"},
    )

    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="owner")
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ServiceSlot(UUIDPKMixin, TimestampMixin, Base):
    """Disponibilidad recurrente semanal configurada por el aliado."""

    __tablename__ = "service_slots"
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_service_slots_dow"),
        {"schema": "partners"},
    )

    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.services.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    max_bookings: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Booking(UUIDPKMixin, TimestampMixin, Base):
    """Reserva de un cliente con un aliado para un servicio en una franja horaria."""

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','confirmed','completed','cancelled','no_show')",
            name="ck_bookings_status",
        ),
        {"schema": "partners"},
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.services.id", ondelete="SET NULL"), nullable=True
    )
    pet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portal.pets.id", ondelete="SET NULL"), nullable=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    price_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    notes_customer: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_partner: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)


class PartnerReview(UUIDPKMixin, TimestampMixin, Base):
    """Calificación del cliente tras una reserva completada."""

    __tablename__ = "partner_reviews"
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_partner_reviews_booking"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_partner_reviews_rating"),
        {"schema": "partners"},
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.bookings.id", ondelete="CASCADE"), nullable=False
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crm.customers.id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
