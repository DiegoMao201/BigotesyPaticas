"""Modelos del bounded context `sales`."""

from __future__ import annotations

import uuid
from datetime import datetime

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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import (
    AuditMixin,
    Base,
    TimestampMixin,
    UUIDPKMixin,
)


class Order(UUIDPKMixin, TimestampMixin, AuditMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("order_number", name="uq_orders_order_number"),
        {"schema": "sales"},
    )

    order_number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    # Origen: POS_STREAMLIT, POS_NEW, STORE_WEB, ADMIN_MANUAL
    channel: Mapped[str] = mapped_column(String(30), nullable=False, default="POS_NEW", index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="confirmed", index=True)

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Totales (denormalizados, fuente de verdad financiera)
    subtotal: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    discount_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    tax_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    shipping_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    grand_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    # Pagos
    paid_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    balance_due: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    payment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Pendiente", index=True
    )
    payment_method: Mapped[str | None] = mapped_column(String(40), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    items: Mapped[list[OrderItem]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )
    payments: Mapped[list[Payment]] = relationship(
        "Payment", back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderItem(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        {"schema": "sales"},
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sku_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    discount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    line_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    order: Mapped[Order] = relationship(Order, back_populates="items")


class Payment(UUIDPKMixin, TimestampMixin, AuditMixin, Base):
    __tablename__ = "payments"
    __table_args__ = ({"schema": "sales"},)

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    method: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped[Order] = relationship(Order, back_populates="payments")
