"""Cierre de caja: fondo fijo, consignaciones, y status 'sin_conteo'.

La caja opera con FONDO FIJO de $300.000: cada día abre con esa base y el
excedente de efectivo se consigna al banco. Se agregan las columnas
necesarias para registrar la consignación y la base que aplicaba ese día
(no una constante global — si la base cambia en el futuro, el histórico
conserva la que aplicó ese día). El status 'sin_conteo' es para el backfill
de días históricos donde nadie contó el efectivo (saldo_contado/diferencia
deben quedar NULL, nunca 0 — un cuadre de 0 en esos días sería inventado).

Revision ID: 0032_cash_closing_fondo_fijo
Revises: 0031_adoption_outcome
Create Date: 2026-08-30
"""

from __future__ import annotations

from alembic import op

revision = "0032_cash_closing_fondo_fijo"
down_revision = "0031_adoption_outcome"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE finance.cash_closings
            ADD COLUMN IF NOT EXISTS consignaciones NUMERIC(14,2) NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS base_caja NUMERIC(14,2) NOT NULL DEFAULT 300000;

        ALTER TABLE finance.cash_closings
            DROP CONSTRAINT IF EXISTS ck_cash_closings_status;

        ALTER TABLE finance.cash_closings
            ADD CONSTRAINT ck_cash_closings_status
                CHECK (status IN ('open', 'closed', 'sin_conteo'));
    """)


def downgrade() -> None:
    # Nota: si existen filas con status='sin_conteo' (del backfill histórico),
    # este downgrade fallará al recrear el CHECK más estricto — es esperado,
    # no se reescriben datos históricos automáticamente en un downgrade.
    op.execute("""
        ALTER TABLE finance.cash_closings
            DROP CONSTRAINT IF EXISTS ck_cash_closings_status;

        ALTER TABLE finance.cash_closings
            ADD CONSTRAINT ck_cash_closings_status
                CHECK (status IN ('open', 'closed'));

        ALTER TABLE finance.cash_closings
            DROP COLUMN IF EXISTS consignaciones,
            DROP COLUMN IF EXISTS base_caja;
    """)
