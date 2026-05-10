"""Modelos del bounded context `inventory`."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common import (
    AuditMixin,
    Base,
    TimestampMixin,
    UUIDPKMixin,
)


class StockLocation(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "stock_locations"
    __table_args__ = (UniqueConstraint("code", name="uq_stock_locations_code"), {"schema": "inventory"})

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
    # Tipos: SALE, PURCHASE, ADJUSTMENT, RETURN, TRANSFER_IN, TRANSFER_OUT
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)  # +/-
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
