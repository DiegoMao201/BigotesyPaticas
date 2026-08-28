"""Foro de adopción: quien da un animal en adopción y quien busca adoptar.

community.adoption_listings -- una publicación por caso ('offer' o 'want'),
modelada sobre sos_events (una foto[] por publicación, no un grupo de
animales distintos como rescue_events).

Revision ID: 0029_adoption_listings
Revises: 0028_rescue_events_reporter
Create Date: 2026-08-28
"""

from __future__ import annotations

from alembic import op

revision = "0029_adoption_listings"
down_revision = "0028_rescue_events_reporter"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS community.adoption_listings (
            id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            reporter_customer_id   UUID REFERENCES crm.customers(id) ON DELETE SET NULL,
            post_type              VARCHAR(10)  NOT NULL
                                    CHECK (post_type IN ('offer', 'want')),
            title                  VARCHAR(200) NOT NULL,
            description            TEXT,
            species                VARCHAR(30),
            breed                  VARCHAR(100),
            address                VARCHAR(300),
            lat                    NUMERIC(9,6),
            lng                    NUMERIC(9,6),
            delivery_notes         TEXT,
            contact_phone          VARCHAR(40)  NOT NULL,
            photos                 JSONB        NOT NULL DEFAULT '[]',
            status                 VARCHAR(20)  NOT NULL DEFAULT 'open'
                                    CHECK (status IN ('open', 'closed')),
            created_at             TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at             TIMESTAMPTZ  NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_adoption_listings_status_type
            ON community.adoption_listings(status, post_type, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_adoption_listings_reporter
            ON community.adoption_listings(reporter_customer_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS community.adoption_listings;")
