"""sprint5: product_reviews + gbp_reviews_cache + rating columns + trigger

Revision ID: 0016_sprint5_reviews_gbp
Revises: 0015_sprint3_search_filters_redirects
Create Date: 2026-06-27
"""
from __future__ import annotations
from alembic import op

revision = "0016_sprint5_reviews_gbp"
down_revision = "0015_sprint3_search_filters_redirects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        -- ── Rating columns en catalog.products ──────────────────────────────────
        ALTER TABLE catalog.products
            ADD COLUMN IF NOT EXISTS rating_avg     DECIMAL(3,2),
            ADD COLUMN IF NOT EXISTS rating_count   INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS rating_distribution JSONB;

        -- ── Tabla product_reviews ────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS catalog.product_reviews (
            id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id            UUID NOT NULL REFERENCES catalog.products(id) ON DELETE CASCADE,
            customer_id           UUID NOT NULL REFERENCES portal.customers(id) ON DELETE CASCADE,
            sales_order_item_id   UUID,
            rating                INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            title                 VARCHAR(200),
            comment               TEXT CHECK (char_length(comment) <= 2000),
            photo_urls            TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            pet_name              VARCHAR(100),
            pet_breed             VARCHAR(100),
            status                VARCHAR(20) NOT NULL DEFAULT 'pending'
                                  CHECK (status IN ('pending','approved','rejected','auto_published')),
            moderation_notes      TEXT,
            moderated_by          UUID,
            moderated_at          TIMESTAMPTZ,
            admin_reply           TEXT,
            admin_reply_at        TIMESTAMPTZ,
            is_verified_purchase  BOOLEAN NOT NULL DEFAULT true,
            points_awarded        INTEGER NOT NULL DEFAULT 0,
            helpful_count         INTEGER NOT NULL DEFAULT 0,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (customer_id, product_id)
        );

        CREATE INDEX IF NOT EXISTS idx_product_reviews_product
            ON catalog.product_reviews (product_id, status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_product_reviews_customer
            ON catalog.product_reviews (customer_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_product_reviews_status
            ON catalog.product_reviews (status, created_at DESC);

        -- ── Tabla gbp_reviews_cache ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS catalog.gbp_reviews_cache (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            google_review_id     VARCHAR(255) NOT NULL UNIQUE,
            reviewer_name        VARCHAR(200) NOT NULL,
            reviewer_photo_url   TEXT,
            rating               INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            comment              TEXT,
            relative_time        VARCHAR(100),
            review_created_at    TIMESTAMPTZ,
            business_reply       TEXT,
            business_reply_at    TIMESTAMPTZ,
            fetched_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            matched_customer_id  UUID REFERENCES portal.customers(id),
            points_credited      INTEGER NOT NULL DEFAULT 0,
            points_credited_at   TIMESTAMPTZ
        );

        CREATE INDEX IF NOT EXISTS idx_gbp_reviews_matched
            ON catalog.gbp_reviews_cache (matched_customer_id);
        CREATE INDEX IF NOT EXISTS idx_gbp_reviews_created
            ON catalog.gbp_reviews_cache (review_created_at DESC);

        -- ── Actualizar constraint de loyalty_points.reason ────────────────────────
        ALTER TABLE portal.loyalty_points
            DROP CONSTRAINT IF EXISTS ck_loyalty_reason;
        ALTER TABLE portal.loyalty_points
            ADD CONSTRAINT ck_loyalty_reason CHECK (
                reason IN (
                    'purchase','portal_order','appointment','referral','manual',
                    'review','gbp_review','review_gbp'
                )
            );

        -- ── Trigger: recalcular rating_avg/count cuando cambia una reseña ────────
        CREATE OR REPLACE FUNCTION catalog.recalc_product_rating()
        RETURNS TRIGGER AS $$
        DECLARE
            v_product_id UUID;
        BEGIN
            v_product_id := COALESCE(NEW.product_id, OLD.product_id);
            UPDATE catalog.products SET
                rating_avg = (
                    SELECT ROUND(AVG(rating)::numeric, 2)
                    FROM catalog.product_reviews
                    WHERE product_id = v_product_id
                      AND status IN ('approved', 'auto_published')
                ),
                rating_count = (
                    SELECT COUNT(*)
                    FROM catalog.product_reviews
                    WHERE product_id = v_product_id
                      AND status IN ('approved', 'auto_published')
                ),
                rating_distribution = (
                    SELECT jsonb_object_agg(rating::text, cnt)
                    FROM (
                        SELECT rating, COUNT(*) AS cnt
                        FROM catalog.product_reviews
                        WHERE product_id = v_product_id
                          AND status IN ('approved', 'auto_published')
                        GROUP BY rating
                    ) sub
                ),
                updated_at = now()
            WHERE id = v_product_id;
            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_recalc_product_rating ON catalog.product_reviews;
        CREATE TRIGGER trg_recalc_product_rating
        AFTER INSERT OR UPDATE OR DELETE ON catalog.product_reviews
        FOR EACH ROW EXECUTE FUNCTION catalog.recalc_product_rating();
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS trg_recalc_product_rating ON catalog.product_reviews;
        DROP FUNCTION IF EXISTS catalog.recalc_product_rating();
        DROP TABLE IF EXISTS catalog.gbp_reviews_cache;
        DROP TABLE IF EXISTS catalog.product_reviews;
        ALTER TABLE catalog.products
            DROP COLUMN IF EXISTS rating_avg,
            DROP COLUMN IF EXISTS rating_count,
            DROP COLUMN IF EXISTS rating_distribution;
        ALTER TABLE portal.loyalty_points
            DROP CONSTRAINT IF EXISTS ck_loyalty_reason;
        ALTER TABLE portal.loyalty_points
            ADD CONSTRAINT ck_loyalty_reason CHECK (
                reason IN ('purchase','portal_order','appointment','referral','manual')
            );
    """)
