"""Backfill reference_id NULL en stock_movements de tipo SALE.

El bug: db.new está vacío tras db.flush(), así que reference_id nunca se seteó.
Este migration lo repara usando product_id + occurred_at para mapear orden.

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-04
"""

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE inventory.stock_movements sm
        SET reference_id = o.id
        FROM sales.orders o
        JOIN sales.order_items oi ON oi.order_id = o.id
        WHERE sm.reference_type = 'ORDER'
          AND sm.reference_id IS NULL
          AND sm.movement_type = 'SALE'
          AND sm.product_id = oi.product_id
          AND sm.occurred_at = o.occurred_at
    """)


def downgrade() -> None:
    pass
