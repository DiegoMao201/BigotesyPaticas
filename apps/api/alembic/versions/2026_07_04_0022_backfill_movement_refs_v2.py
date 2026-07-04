"""Backfill v2: reference_id en stock_movements con ventana de ±5 s.

La migración 0021 usó igualdad exacta de timestamps; si había diferencia
de microsegundos o el POS viejo generó la orden con un timestamp distinto,
no se actualizó. Esta versión usa DISTINCT ON + ventana de 5 segundos.

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-04
"""

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE inventory.stock_movements sm
        SET reference_id = subq.order_id
        FROM (
            SELECT DISTINCT ON (sm2.id)
                sm2.id   AS movement_id,
                o.id     AS order_id
            FROM inventory.stock_movements sm2
            JOIN sales.order_items oi ON oi.product_id = sm2.product_id
            JOIN sales.orders o       ON o.id = oi.order_id
            WHERE sm2.reference_type = 'ORDER'
              AND sm2.reference_id IS NULL
              AND sm2.movement_type = 'SALE'
              AND ABS(EXTRACT(EPOCH FROM (sm2.occurred_at - o.occurred_at))) < 5
            ORDER BY sm2.id, ABS(EXTRACT(EPOCH FROM (sm2.occurred_at - o.occurred_at)))
        ) subq
        WHERE sm.id = subq.movement_id
    """)


def downgrade() -> None:
    pass
