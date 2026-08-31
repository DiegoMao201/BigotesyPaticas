"""Compras: método de pago con crédito 15/30 días + cartera con proveedores.

Hoy `purchasing.purchases.payment_method` es texto libre sin usarse en
ningún cálculo ni UI (siempre queda en el default "efectivo"). Esta
migración le da uso real:

- `due_date`: fecha de vencimiento para compras a crédito (purchased_at +
  15 o 30 días, calculado en el backend al crear/editar la compra).
- `payment_status`: 'pagada' (efectivo/transferencia, pago inmediato) o
  'pendiente' (crédito, hasta que se marque pagada) / 'pagada' tras marcarla.
- `paid_at`: cuándo se marcó pagada una compra a crédito.

También se agrega `finance.cash_closings.snap_compras_efectivo`: snapshot
de las compras en efectivo del día (mismo patrón que snap_ventas_por_metodo)
para que el cierre reste ese efectivo que salió de caja para pagar
proveedores, y para poder detectar alteración si una compra se edita
después de cerrado el día (igual que ya se hace con ventas/créditos).

Revision ID: 0033_purchases_credito_cartera
Revises: 0032_cash_closing_fondo_fijo
Create Date: 2026-08-31
"""

from __future__ import annotations

from alembic import op

revision = "0033_purchases_credito_cartera"
down_revision = "0032_cash_closing_fondo_fijo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE purchasing.purchases
            ADD COLUMN IF NOT EXISTS due_date DATE,
            ADD COLUMN IF NOT EXISTS payment_status VARCHAR(20) NOT NULL DEFAULT 'pagada',
            ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;

        ALTER TABLE purchasing.purchases
            DROP CONSTRAINT IF EXISTS ck_purchases_payment_status;

        ALTER TABLE purchasing.purchases
            ADD CONSTRAINT ck_purchases_payment_status
                CHECK (payment_status IN ('pagada', 'pendiente'));

        CREATE INDEX IF NOT EXISTS ix_purchases_payment_status_due_date
            ON purchasing.purchases (payment_status, due_date);

        ALTER TABLE finance.cash_closings
            ADD COLUMN IF NOT EXISTS snap_compras_efectivo NUMERIC(14,2) NOT NULL DEFAULT 0;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE finance.cash_closings
            DROP COLUMN IF EXISTS snap_compras_efectivo;

        DROP INDEX IF EXISTS purchasing.ix_purchases_payment_status_due_date;

        ALTER TABLE purchasing.purchases
            DROP CONSTRAINT IF EXISTS ck_purchases_payment_status;

        ALTER TABLE purchasing.purchases
            DROP COLUMN IF EXISTS due_date,
            DROP COLUMN IF EXISTS payment_status,
            DROP COLUMN IF EXISTS paid_at;
    """)
