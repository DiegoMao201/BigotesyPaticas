"""Modelos del bounded context `inventory`."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import (
    AuditMixin,
    Base,
    TimestampMixin,
    UUIDPKMixin,
)


class StockLocation(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "stock_locations"
    __table_args__ = (
        UniqueConstraint("code", name="uq_stock_locations_code"),
        {"schema": "inventory"},
    )

    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_default: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)


class Stock(UUIDPKMixin, TimestampMixin, Base):
    """Cantidad disponible por (producto, location)."""

    __tablename__ = "stock"
    __table_args__ = (
        UniqueConstraint("product_id", "location_id", name="uq_stock_product_location"),
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        CheckConstraint("reserved >= 0", name="reserved_non_negative"),
        {"schema": "inventory"},
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.stock_locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class StockMovement(UUIDPKMixin, TimestampMixin, AuditMixin, Base):
    """Cada cambio en stock genera un row inmutable. Append-only."""

    __tablename__ = "stock_movements"
    __table_args__ = ({"schema": "inventory"},)

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.stock_locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Tipos: SALE, PURCHASE, ADJUSTMENT, RETURN, TRANSFER_IN, TRANSFER_OUT, COUNT_ADJUST
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)  # +/-
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


# ─── Physical Inventory Count ───────────────────────────────────────────


class CountSession(UUIDPKMixin, TimestampMixin, Base):
    """Sesión de conteo físico de inventario."""

    __tablename__ = "count_sessions"
    __table_args__ = ({"schema": "inventory"},)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metrics snapshot (populated on apply)
    total_products_counted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_with_difference: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_positive_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_negative_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_value_impact: Mapped[Decimal] = mapped_column(
        Numeric(16, 2), nullable=False, default=Decimal("0")
    )

    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(200), nullable=True)

    items: Mapped[list[CountItem]] = relationship(
        "CountItem",
        back_populates="session",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CountItem(UUIDPKMixin, TimestampMixin, Base):
    """Ítem individual de una sesión de conteo."""

    __tablename__ = "count_items"
    __table_args__ = (
        UniqueConstraint("session_id", "product_id", name="uq_count_items_session_product"),
        {"schema": "inventory"},
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.count_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    product_name: Mapped[str] = mapped_column(String(300), nullable=False)
    category_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    system_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    counted_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_impact: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[CountSession] = relationship("CountSession", back_populates="items")
