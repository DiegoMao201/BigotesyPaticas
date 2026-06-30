"""seo_landings table

Revision ID: 0012_seo_landings
Revises: 0011_blog_posts
Create Date: 2026-06-27
"""

from alembic import op

revision = "0012_seo_landings"
down_revision = "0011_blog_posts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS content")

    op.execute("""
        CREATE TABLE IF NOT EXISTS content.seo_landings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug VARCHAR(200) UNIQUE NOT NULL,
            target_keyword VARCHAR(200) NOT NULL,
            title VARCHAR(200) NOT NULL,
            h1 VARCHAR(200) NOT NULL,
            meta_description VARCHAR(320),
            intro_content TEXT,
            category_slug VARCHAR(100),
            geographic_focus VARCHAR(100),
            cta_text VARCHAR(120),
            is_active BOOLEAN NOT NULL DEFAULT true,
            enriched_by_ai BOOLEAN NOT NULL DEFAULT false,
            ai_model VARCHAR(100),
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_seo_landings_slug
        ON content.seo_landings(slug)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_seo_landings_active
        ON content.seo_landings(is_active)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS content.seo_landings")
