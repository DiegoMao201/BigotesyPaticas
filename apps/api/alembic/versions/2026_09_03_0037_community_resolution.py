"""Cierre con final feliz unificado para la comunidad + comentarios públicos.

Los cuatro casos (dar en adopción, buscar adoptar, mascota perdida, animal
encontrado) pasan a tener el mismo trío: resultado + nota + fecha, y una
ventana de visibilidad pública (`public_until` = resolución + 30 días).
Pasada esa fecha la historia de éxito se oculta sola (filtro por fecha en
las consultas públicas: no hace falta cron).

- sos_events: ya tenía status='found' + found_at; se agrega la nota y la
  ventana pública.
- rescue_events: gana outcome ('pending'|'reunited') a nivel evento (antes
  solo existía por animal, sin fecha ni nota).
- adoption_listings: ya tenía outcome/outcome_note/outcome_at; se agrega la
  ventana pública.
- community.comments: comentarios públicos (nombre + texto) sobre cualquiera
  de las tres entidades, con moderación (visible/hidden) desde el admin.

Revision ID: 0037_community_resolution
Revises: 0036_story_posts_tiktok
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "0037_community_resolution"
down_revision = "0036_story_posts_tiktok"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE community.sos_events
            ADD COLUMN IF NOT EXISTS resolution_note TEXT,
            ADD COLUMN IF NOT EXISTS public_until TIMESTAMPTZ;

        UPDATE community.sos_events
           SET public_until = found_at + interval '30 days'
         WHERE status = 'found' AND found_at IS NOT NULL AND public_until IS NULL;

        ALTER TABLE community.rescue_events
            ADD COLUMN IF NOT EXISTS outcome VARCHAR(20) NOT NULL DEFAULT 'pending'
                CHECK (outcome IN ('pending', 'reunited')),
            ADD COLUMN IF NOT EXISTS resolution_note TEXT,
            ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS public_until TIMESTAMPTZ;

        ALTER TABLE community.adoption_listings
            ADD COLUMN IF NOT EXISTS public_until TIMESTAMPTZ;

        UPDATE community.adoption_listings
           SET public_until = outcome_at + interval '30 days'
         WHERE outcome = 'matched' AND outcome_at IS NOT NULL AND public_until IS NULL;

        CREATE INDEX IF NOT EXISTS idx_sos_events_public_until
            ON community.sos_events(status, public_until);
        CREATE INDEX IF NOT EXISTS idx_rescue_events_outcome
            ON community.rescue_events(outcome, public_until);
        CREATE INDEX IF NOT EXISTS idx_adoption_listings_public_until
            ON community.adoption_listings(outcome, public_until);

        CREATE TABLE IF NOT EXISTS community.comments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type VARCHAR(20) NOT NULL
                CHECK (entity_type IN ('adoption', 'lost', 'found')),
            entity_id UUID NOT NULL,
            author_name VARCHAR(80) NOT NULL,
            body TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'visible'
                CHECK (status IN ('visible', 'hidden')),
            ip_hash VARCHAR(64),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_community_comments_entity
            ON community.comments(entity_type, entity_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_community_comments_created
            ON community.comments(created_at DESC);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS community.comments;
        ALTER TABLE community.adoption_listings DROP COLUMN IF EXISTS public_until;
        ALTER TABLE community.rescue_events
            DROP COLUMN IF EXISTS outcome,
            DROP COLUMN IF EXISTS resolution_note,
            DROP COLUMN IF EXISTS resolved_at,
            DROP COLUMN IF EXISTS public_until;
        ALTER TABLE community.sos_events
            DROP COLUMN IF EXISTS resolution_note,
            DROP COLUMN IF EXISTS public_until;
    """)
