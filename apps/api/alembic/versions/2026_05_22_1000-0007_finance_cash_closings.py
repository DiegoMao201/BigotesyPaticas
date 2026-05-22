"""Add finance.cash_closings table for daily cash reconciliation.

Revision ID: 0007_finance_cash_closings
Revises: 0006_seed_default_location
Create Date: 2026-05-22 10:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_finance_cash_closings"
down_revision = "0006_seed_default_location"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE finance.cash_closings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by VARCHAR(100),
            updated_by VARCHAR(100),

            fecha DATE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'open'
                CONSTRAINT ck_cash_closings_status CHECK (status IN ('open','closed')),

            saldo_inicial NUMERIC(14,2) NOT NULL DEFAULT 0,
            gastos_efectivo NUMERIC(14,2) NOT NULL DEFAULT 0,

            snap_ventas_por_metodo JSONB NOT NULL DEFAULT '{}',
            snap_creditos_por_metodo JSONB NOT NULL DEFAULT '{}',
            snap_total_ventas NUMERIC(14,2) NOT NULL DEFAULT 0,

            saldo_final_efectivo NUMERIC(14,2),
            saldo_contado NUMERIC(14,2),
            diferencia NUMERIC(14,2),

            notas TEXT,
            closed_at TIMESTAMPTZ,
            closed_by VARCHAR(100),

            CONSTRAINT uq_cash_closings_fecha UNIQUE (fecha)
        )
    """)
    op.create_index(
        "ix_finance_cash_closings_fecha", "cash_closings", ["fecha"], schema="finance"
    )
    op.create_index(
        "ix_finance_cash_closings_status", "cash_closings", ["status"], schema="finance"
    )


def downgrade() -> None:
    op.drop_index("ix_finance_cash_closings_status", table_name="cash_closings", schema="finance")
    op.drop_index("ix_finance_cash_closings_fecha", table_name="cash_closings", schema="finance")
    op.drop_table("cash_closings", schema="finance")
