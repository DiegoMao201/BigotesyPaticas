"""content schema + blog_posts table para SEO.

Revision ID: 0011_blog_posts
Revises: 0010_portal_v4_schema
Create Date: 2026-06-27
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "0011_blog_posts"
down_revision = "0010_portal_v4_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(text("CREATE SCHEMA IF NOT EXISTS content;"))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS content.blog_posts (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            slug            VARCHAR(200) UNIQUE NOT NULL,
            title           VARCHAR(300) NOT NULL,
            excerpt         TEXT,
            content         TEXT        NOT NULL DEFAULT '',
            cover_image_url TEXT,
            category        VARCHAR(80),
            keywords        TEXT[]      DEFAULT '{}',
            meta_title      VARCHAR(200),
            meta_description VARCHAR(300),
            author          VARCHAR(120) NOT NULL DEFAULT 'Equipo Bigotes y Paticas',
            published_at    TIMESTAMPTZ,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            view_count      INTEGER     NOT NULL DEFAULT 0,
            enriched_by_ai  BOOLEAN     NOT NULL DEFAULT TRUE,
            ai_model        VARCHAR(100)
        );
    """))

    op.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_blog_published
            ON content.blog_posts (published_at DESC NULLS LAST);
    """))
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_blog_category
            ON content.blog_posts (category);
    """))
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_blog_slug
            ON content.blog_posts (slug);
    """))


def downgrade() -> None:
    op.execute(text("DROP TABLE IF EXISTS content.blog_posts;"))
