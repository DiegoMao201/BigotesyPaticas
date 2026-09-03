"""Publicar también como Reel (IG+FB) y post de Feed (FB), no solo Story.

Instagram: un Reel con share_to_feed=true queda en la pestaña Reels Y en el
feed principal con una sola llamada a la API -- no hace falta nada aparte.
Facebook NO tiene ese combo: un Reel de Facebook (/video_reels) no garantiza
aparecer en el feed de la página, así que para feed en Facebook se hace una
publicación de video normal aparte (/{page-id}/videos).

Se agregan 3 columnas de resultado (mismo patrón que instagram_story_id /
facebook_story_id ya existentes) para poder ver en el admin qué destinos
publicaron bien y cuáles fallaron, sin bloquear los demás.

Revision ID: 0034_story_posts_reels_feed
Revises: 0033_purchases_credito_cartera
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op

revision = "0034_story_posts_reels_feed"
down_revision = "0033_purchases_credito_cartera"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE content.story_posts
            ADD COLUMN IF NOT EXISTS instagram_reel_id VARCHAR(100),
            ADD COLUMN IF NOT EXISTS facebook_reel_id VARCHAR(100),
            ADD COLUMN IF NOT EXISTS facebook_feed_id VARCHAR(100);
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE content.story_posts
            DROP COLUMN IF EXISTS instagram_reel_id,
            DROP COLUMN IF EXISTS facebook_reel_id,
            DROP COLUMN IF EXISTS facebook_feed_id;
    """)
