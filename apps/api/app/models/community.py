"""Modelos del schema `community` — comunidad de dueños de mascotas (SOS, etc.)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common import Base, TimestampMixin, UUIDPKMixin


class SOSEvent(UUIDPKMixin, TimestampMixin, Base):
    """Reporte de mascota perdida."""

    __tablename__ = "sos_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','found','closed','expired')", name="ck_sos_events_status"
        ),
        {"schema": "community"},
    )

    pet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portal.pets.id", ondelete="SET NULL"), nullable=True
    )
    reporter_customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pet_name: Mapped[str] = mapped_column(String(150), nullable=False)
    species: Mapped[str] = mapped_column(String(30), nullable=False)
    breed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str] = mapped_column(String(100), nullable=False)
    photos: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    last_seen_lat: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    last_seen_lng: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(40), nullable=False)
    reward: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    radius_km: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    notified_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    found_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RescueEvent(UUIDPKMixin, TimestampMixin, Base):
    """Grupo de animales encontrados/rescatados juntos en un mismo lugar."""

    __tablename__ = "rescue_events"
    __table_args__ = (
        CheckConstraint("status IN ('open','closed')", name="ck_rescue_events_status"),
        {"schema": "community"},
    )

    reporter_customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crm.customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    lat: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    lng: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    found_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    created_by_admin: Mapped[str | None] = mapped_column(String(200), nullable=True)


class RescueAnimal(UUIDPKMixin, TimestampMixin, Base):
    """Una foto/ficha individual dentro de un RescueEvent."""

    __tablename__ = "rescue_animals"
    __table_args__ = (
        CheckConstraint("status IN ('unclaimed','reunited')", name="ck_rescue_animals_status"),
        {"schema": "community"},
    )

    rescue_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community.rescue_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    photo_url: Mapped[str] = mapped_column(Text, nullable=False)
    thumb_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    species: Mapped[str | None] = mapped_column(String(30), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unclaimed", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AdoptionListing(UUIDPKMixin, TimestampMixin, Base):
    """Foro de adopción: 'offer' (doy un animal en adopción) o 'want' (busco adoptar)."""

    __tablename__ = "adoption_listings"
    __table_args__ = (
        CheckConstraint("post_type IN ('offer','want')", name="ck_adoption_listings_post_type"),
        CheckConstraint("status IN ('open','closed')", name="ck_adoption_listings_status"),
        {"schema": "community"},
    )

    reporter_customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crm.customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Publicaciones del "foro rápido" (sin cuenta, público) guardan aquí el
    # nombre que la persona escribió -- reporter_customer_id queda NULL.
    reporter_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    post_type: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    species: Mapped[str | None] = mapped_column(String(30), nullable=True)
    breed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    delivery_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_phone: Mapped[str] = mapped_column(String(40), nullable=False)
    photos: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)


class SOSSighting(UUIDPKMixin, Base):
    """Avistamiento reportado por alguien de la comunidad."""

    __tablename__ = "sos_sightings"
    __table_args__ = ({"schema": "community"},)

    sos_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community.sos_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    spotter_customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crm.customers.id", ondelete="CASCADE"), nullable=False
    )
    lat: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    lng: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
