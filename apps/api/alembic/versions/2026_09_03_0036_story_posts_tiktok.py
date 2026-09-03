"""TikTok como destino manual de las stories (mientras no haya video.publish).

content.story_posts gana tres columnas: tiktok_publish_id (id que devuelve
TikTok al subir el video a la bandeja de la app), tiktok_status (último
estado consultado: SEND_TO_USER_INBOX, PUBLISH_COMPLETE, FAILED...) y
tiktok_sent_at. Mismo patrón que instagram_reel_id/facebook_feed_id.

Revision ID: 0036_story_posts_tiktok
Revises: 0035_tiktok_auth
Create Date: 2026-09-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0036_story_posts_tiktok"
down_revision = "0035_tiktok_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "story_posts",
        sa.Column("tiktok_publish_id", sa.String(128), nullable=True),
        schema="content",
    )
    op.add_column(
        "story_posts",
        sa.Column("tiktok_status", sa.String(40), nullable=True),
        schema="content",
    )
    op.add_column(
        "story_posts",
        sa.Column("tiktok_sent_at", sa.DateTime(timezone=True), nullable=True),
        schema="content",
    )


def downgrade() -> None:
    op.drop_column("story_posts", "tiktok_sent_at", schema="content")
    op.drop_column("story_posts", "tiktok_status", schema="content")
    op.drop_column("story_posts", "tiktok_publish_id", schema="content")
