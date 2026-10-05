"""Modelos del schema `finance`."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import ClassVar

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common import AuditMixin, Base, TimestampMixin, UUIDPKMixin


class CashClosing(UUIDPKMixin, TimestampMixin, AuditMixin, Base):
    """Cierre de caja diario — registra la conciliación de cada jornada."""

    __tablename__ = "cash_closings"
    __table_args__ = (
        UniqueConstraint("fecha", name="uq_cash_closings_fecha"),
        CheckConstraint("status IN ('open','closed','sin_conteo')", name="ck_cash_closings_status"),
        {"schema": "finance"},
    )

    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)

    # Carry-over: efectivo en caja al inicio del día
    saldo_inicial: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    # Gastos en efectivo ingresados manualmente
    gastos_efectivo: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    # Excedente de efectivo consignado al banco al cerrar
    consignaciones: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    # Fondo fijo que aplicaba ESE día (columna por cierre, no constante global —
    # si la base cambia en el futuro, el histórico conserva la que aplicó ese día)
    base_caja: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=300000)

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
    # Snapshot de compras a proveedor pagadas en efectivo ese día — ese
    # dinero sale físicamente de caja y se resta del saldo esperado.
    snap_compras_efectivo: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0
    )

    # Valores al cierre
    saldo_final_efectivo: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    saldo_contado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    diferencia: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Expense(UUIDPKMixin, Base):
    """Un gasto del negocio. Tabla propia desde el 5-oct-2026.

    Antes vivían en `ops.legacy_id_map` dentro de un JSON: el monto era texto, la
    fecha también, no había índices, y cada informe era una consulta frágil escrita
    a mano que leía las 478 filas enteras para filtrarlas en Python.

    DOS CAMPOS QUE DECIDEN SI EL ANÁLISIS SIRVE O NO:

    - **`tipo`**: 'Operativo' (sostener la tienda abierta) o 'Mercancía' (lo que se
      revende). La mercancía YA está descontada en el margen bruto; meterla en los
      gastos fijos contaría el mismo peso dos veces e inflaría el punto de
      equilibrio hasta volverlo inalcanzable.
    - **`es_fijo`**: si se repite todos los meses. Es lo que separa el costo de
      tener la tienda abierta de un imprevisto, y sin esa distinción el punto de
      equilibrio mezcla peras con manzanas.
    """

    __tablename__ = "expenses"
    __table_args__: ClassVar = {"schema": "finance"}

    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    categoria: Mapped[str] = mapped_column(String(60), nullable=False, default="Sin categoría")
    tipo: Mapped[str] = mapped_column(String(30), nullable=False, default="Operativo")
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    metodo_pago: Mapped[str | None] = mapped_column(String(40), nullable=True)
    banco_origen: Mapped[str | None] = mapped_column(String(60), nullable=True)
    es_fijo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    #: De dónde salió la fila al migrar desde el JSON. Permite rastrear el origen.
    legacy_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
