"""portal order items + payment_method + shipping_address

Revision ID: 0013_portal_order_items
Revises: 0012_seo_landings
Create Date: 2026-06-27

"""
from __future__ import annotations

from alembic import op

revision = "0013_portal_order_items"
down_revision = "0012_seo_landings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add payment_method and shipping_address to portal_orders
    op.execute("""
        ALTER TABLE portal.portal_orders
            ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50),
            ADD COLUMN IF NOT EXISTS shipping_address TEXT;
    """)

    # Create portal_order_items table
    op.execute("""
        CREATE TABLE IF NOT EXISTS portal.portal_order_items (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            portal_order_id  UUID NOT NULL
                                 REFERENCES portal.portal_orders(id) ON DELETE CASCADE,
            product_id       UUID
                                 REFERENCES catalog.products(id) ON DELETE SET NULL,
            sku              VARCHAR(120),
            name             VARCHAR(500),
            image_url        TEXT,
            quantity         INTEGER NOT NULL DEFAULT 1
                                 CONSTRAINT ck_portal_order_items_qty CHECK (quantity > 0),
            unit_price       DECIMAL(10,2),
            subtotal         DECIMAL(10,2),
            notes            TEXT,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_portal_order_items_order
            ON portal.portal_order_items(portal_order_id);
    """)

    # Backfill existing single-product orders into portal_order_items
    op.execute("""
        INSERT INTO portal.portal_order_items
            (portal_order_id, product_id, sku, name, image_url,
             quantity, unit_price, subtotal, created_at)
        SELECT
            po.id,
            po.product_id,
            p.sku,
            po.product_name,
            p.primary_image_url,
            po.quantity,
            po.unit_price,
            COALESCE(po.unit_price, 0) * po.quantity,
            po.created_at
        FROM portal.portal_orders po
        LEFT JOIN catalog.products p ON p.id = po.product_id
        WHERE NOT EXISTS (
            SELECT 1 FROM portal.portal_order_items poi
            WHERE poi.portal_order_id = po.id
        )
        AND po.product_id IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS portal.idx_portal_order_items_order;")
    op.execute("DROP TABLE IF EXISTS portal.portal_order_items;")
    op.execute("""
        ALTER TABLE portal.portal_orders
            DROP COLUMN IF EXISTS shipping_address,
            DROP COLUMN IF EXISTS payment_method;
    """)
