"""Modelos del schema `portal` — App de Fidelización de Clientes."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import Base, TimestampMixin, UUIDPKMixin


class Pet(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "pets"
    __table_args__ = (
        CheckConstraint(
            "color_theme IN ('teal','coral','amber','purple','pink','green')",
            name="ck_pets_color_theme",
        ),
        {"schema": "portal"},
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    breed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    birth_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    food_brand: Mapped[str | None] = mapped_column(String(200), nullable=True)
    food_freq_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color_theme: Mapped[str] = mapped_column(String(20), nullable=False, default="teal")
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, index=True
    )

    health_records: Mapped[list["HealthRecord"]] = relationship(
        "HealthRecord", back_populates="pet", cascade="all, delete-orphan", lazy="selectin"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="pet", cascade="all, delete-orphan"
    )


class HealthRecord(UUIDPKMixin, Base):
    __tablename__ = "health_records"
    __table_args__ = ({"schema": "portal"},)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    pet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portal.pets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    record_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(Date, nullable=False)
    next_due_at: Mapped[datetime | None] = mapped_column(Date, nullable=True, index=True)
    vet_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    pet: Mapped["Pet"] = relationship("Pet", back_populates="health_records")


class Appointment(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','confirmed','completed','cancelled')",
            name="ck_appt_status",
        ),
        {"schema": "portal"},
    )

    pet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portal.pets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_type: Mapped[str] = mapped_column(String(100), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    pet: Mapped["Pet"] = relationship("Pet", back_populates="appointments")


class PortalOrder(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "portal_orders"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_portal_orders_qty"),
        CheckConstraint(
            "status IN ('received','processing','ready','delivered','cancelled')",
            name="ck_portal_orders_status",
        ),
        {"schema": "portal"},
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portal.pets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.products.id", ondelete="SET NULL"),
        nullable=True,
    )
    product_name: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="received", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PortalSession(UUIDPKMixin, Base):
    __tablename__ = "portal_sessions"
    __table_args__ = ({"schema": "portal"},)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class LoyaltyPoint(UUIDPKMixin, Base):
    __tablename__ = "loyalty_points"
    __table_args__ = (
        CheckConstraint("points <> 0", name="ck_loyalty_points_positive"),
        CheckConstraint(
            "reason IN ('purchase','portal_order','appointment','referral','manual')",
            name="ck_loyalty_reason",
        ),
        {"schema": "portal"},
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PortalNotification(UUIDPKMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "type IN ('health_reminder','order_update','loyalty','appointment','birthday','general')",
            name="ck_notif_type",
        ),
        {"schema": "portal"},
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
