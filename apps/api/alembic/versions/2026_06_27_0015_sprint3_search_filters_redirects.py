"""sprint3: pg_trgm + slug_redirects + product filter columns + product_waitlist

Revision ID: 0015_sprint3_search_filters_redirects
Revises: 0014_pet_monitor_workflow
Create Date: 2026-06-27
"""

from __future__ import annotations

from alembic import op

revision = "0015_sprint3_search_filters_redirects"
down_revision = "0014_pet_monitor_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. pg_trgm extension ──────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # ── 2. Trigram indexes for fuzzy search ───────────────────────────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_name_trgm
        ON catalog.products USING GIN (name gin_trgm_ops);
    """)
    # ── 3. slug_redirects table ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS catalog.slug_redirects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            old_slug VARCHAR(500) UNIQUE NOT NULL,
            new_slug VARCHAR(500) NOT NULL,
            product_id UUID REFERENCES catalog.products(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT now(),
            redirect_count INTEGER DEFAULT 0,
            last_redirect_at TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_slug_redirects_old
        ON catalog.slug_redirects(old_slug);
    """)

    # ── 4. Product filter columns for advanced catalog ────────────────────
    op.execute("""
        ALTER TABLE catalog.products
            ADD COLUMN IF NOT EXISTS life_stage VARCHAR(50),
            ADD COLUMN IF NOT EXISTS size_range VARCHAR(50),
            ADD COLUMN IF NOT EXISTS health_concerns TEXT[],
            ADD COLUMN IF NOT EXISTS pet_type VARCHAR(20),
            ADD COLUMN IF NOT EXISTS brand_normalized VARCHAR(100);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_life_stage
        ON catalog.products(life_stage);
        CREATE INDEX IF NOT EXISTS idx_products_size_range
        ON catalog.products(size_range);
        CREATE INDEX IF NOT EXISTS idx_products_brand_norm
        ON catalog.products(brand_normalized);
        CREATE INDEX IF NOT EXISTS idx_products_brand_trgm
        ON catalog.products USING GIN (COALESCE(brand_normalized, '') gin_trgm_ops);
        CREATE INDEX IF NOT EXISTS idx_products_health
        ON catalog.products USING GIN(health_concerns);
        CREATE INDEX IF NOT EXISTS idx_products_pet_type
        ON catalog.products(pet_type);
    """)

    # ── 5. product_waitlist table ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS catalog.product_waitlist (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id UUID REFERENCES catalog.products(id) ON DELETE CASCADE,
            email VARCHAR(255) NOT NULL,
            phone VARCHAR(50),
            name VARCHAR(200),
            notified_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT now(),
            UNIQUE(product_id, email)
        );
        CREATE INDEX IF NOT EXISTS idx_product_waitlist_product
        ON catalog.product_waitlist(product_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS catalog.product_waitlist;")
    op.execute("DROP TABLE IF EXISTS catalog.slug_redirects;")
    op.execute("""
        ALTER TABLE catalog.products
            DROP COLUMN IF EXISTS life_stage,
            DROP COLUMN IF EXISTS size_range,
            DROP COLUMN IF EXISTS health_concerns,
            DROP COLUMN IF EXISTS pet_type,
            DROP COLUMN IF EXISTS brand_normalized;
    """)
    op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
