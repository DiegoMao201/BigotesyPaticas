"""Foro de adopción: marcar como "encontró hogar" (historia de éxito).

Separado de status (open/closed): outcome permite mostrar la publicación
como historia de éxito ANTES de cerrarla, para que el sitio muestre
evidencia real de que el foro funciona.

Revision ID: 0031_adoption_outcome
Revises: 0030_adoption_reporter_name
Create Date: 2026-08-29
"""

from __future__ import annotations

from alembic import op

revision = "0031_adoption_outcome"
down_revision = "0030_adoption_reporter_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE community.adoption_listings
            ADD COLUMN IF NOT EXISTS outcome VARCHAR(20) NOT NULL DEFAULT 'pending'
                CHECK (outcome IN ('pending', 'matched')),
            ADD COLUMN IF NOT EXISTS outcome_note TEXT,
            ADD COLUMN IF NOT EXISTS outcome_at TIMESTAMPTZ;

        CREATE INDEX IF NOT EXISTS idx_adoption_listings_outcome
            ON community.adoption_listings(outcome, outcome_at DESC);
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE community.adoption_listings
            DROP COLUMN IF EXISTS outcome,
            DROP COLUMN IF EXISTS outcome_note,
            DROP COLUMN IF EXISTS outcome_at;
    """)
