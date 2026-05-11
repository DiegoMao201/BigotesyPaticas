"""Modelos del bounded context `purchasing` (Compras a proveedores)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Integer, Numeric,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import (
    AuditMixin,
    Base,
    TimestampMixin,
    UUIDPKMixin,
)


class Purchase(UUIDPKMixin, TimestampMixin, AuditMixin, Base):
    """Orden / factura de compra a proveedor."""
    __tablename__ = "purchases"
    __table_args__ = ({"schema": "purchasing"},)

    # Número de referencia / folio (ej: número de factura DIAN)
    folio: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)

    # Proveedor (snapshot + FK opcional a tabla suppliers)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    supplier_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Estado: draft, confirmed, received, cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="received", index=True)

    # Totales
    subtotal: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    # Pago
    payment_method: Mapped[str] = mapped_column(String(40), nullable=False, default="efectivo")
    payment_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Notas / observaciones
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Fecha de la factura / compra
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Relación con ítems
    items: Mapped[list["PurchaseItem"]] = relationship(
        "PurchaseItem",
        back_populates="purchase",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PurchaseItem(UUIDPKMixin, TimestampMixin, Base):
    """Línea de producto dentro de una compra."""
    __tablename__ = "purchase_items"
    __table_args__ = ({"schema": "purchasing"},)

    purchase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchasing.purchases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # FK a catálogo (nullable: podría ser un producto no catalogado)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Snapshots en el momento de la compra
    sku_proveedor: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sku_interno: Mapped[str | None] = mapped_column(String(80), nullable=True)
    product_name: Mapped[str] = mapped_column(String(300), nullable=False)

    # Cantidades y costos
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    factor_pack: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_cost: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    tax_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    total_cost: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    # Relación inversa
    purchase: Mapped["Purchase"] = relationship("Purchase", back_populates="items")
