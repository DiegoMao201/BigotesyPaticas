"""Modelos del schema `finance`."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common import AuditMixin, Base, TimestampMixin, UUIDPKMixin


class CashClosing(UUIDPKMixin, TimestampMixin, AuditMixin, Base):
    """Cierre de caja diario — registra la conciliación de cada jornada."""

    __tablename__ = "cash_closings"
    __table_args__ = (
        UniqueConstraint("fecha", name="uq_cash_closings_fecha"),
        CheckConstraint("status IN ('open','closed')", name="ck_cash_closings_status"),
        {"schema": "finance"},
    )

    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)

    # Carry-over: efectivo en caja al inicio del día
    saldo_inicial: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    # Gastos en efectivo ingresados manualmente
    gastos_efectivo: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    # Snapshot de ventas por método (guardado al cerrar — mientras open se computa live)
    snap_ventas_por_metodo: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    # Snapshot de créditos/devoluciones por método
    snap_creditos_por_metodo: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    # Total ventas snapshot
    snap_total_ventas: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    # Valores al cierre
    saldo_final_efectivo: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    saldo_contado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    diferencia: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
