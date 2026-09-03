"""Conexión OAuth de TikTok (Content Posting API) + estado de solicitudes.

content.tiktok_auth: guarda el access_token/refresh_token de la cuenta de
TikTok conectada (una sola cuenta real, pero se deja open_id como llave
única por si algún día se reconecta con otra). Los tokens NUNCA se
exponen por API -- solo se leen server-side para publicar.

content.tiktok_oauth_state: state de un solo uso para el paso de
autorización (anti-CSRF del flujo OAuth), con expiración corta -- se
borra o vence a los 10 minutos, antes de eso se debe completar el
callback.

Revision ID: 0035_tiktok_auth
Revises: 0034_story_posts_reels_feed
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "0035_tiktok_auth"
down_revision = "0034_story_posts_reels_feed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS content.tiktok_auth (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            open_id VARCHAR(100) NOT NULL,
            username VARCHAR(150),
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            scope TEXT,
            expires_at TIMESTAMPTZ NOT NULL,
            refresh_expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_tiktok_auth_open_id
            ON content.tiktok_auth (open_id);

        CREATE TABLE IF NOT EXISTS content.tiktok_oauth_state (
            state VARCHAR(100) PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS content.tiktok_oauth_state;
        DROP TABLE IF EXISTS content.tiktok_auth;
    """)
