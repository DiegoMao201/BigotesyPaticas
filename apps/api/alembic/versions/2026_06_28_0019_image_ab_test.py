"""0019 — A/B test imagen: columnas Flux Pro + config default_image_model

Revision ID: 0019_image_ab_test
Revises: 0018_pending_notifications
Create Date: 2026-06-28
"""

from alembic import op

revision = "0019_image_ab_test"
down_revision = "0018_pending_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE content.scheduled_posts
            ADD COLUMN IF NOT EXISTS image_url_alternative TEXT,
            ADD COLUMN IF NOT EXISTS image_model VARCHAR(50) DEFAULT 'gpt-image-1',
            ADD COLUMN IF NOT EXISTS alternative_image_model VARCHAR(50),
            ADD COLUMN IF NOT EXISTS image_cost_usd DECIMAL(6,4) DEFAULT 0.50,
            ADD COLUMN IF NOT EXISTS alternative_cost_usd DECIMAL(6,4);

        INSERT INTO content.engine_config (key, value, description)
        VALUES
            ('default_image_model', 'gpt-image-1',
             'Modelo IA para imágenes: gpt-image-1 | flux-1.1-pro')
        ON CONFLICT (key) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE content.scheduled_posts
            DROP COLUMN IF EXISTS image_url_alternative,
            DROP COLUMN IF EXISTS image_model,
            DROP COLUMN IF EXISTS alternative_image_model,
            DROP COLUMN IF EXISTS image_cost_usd,
            DROP COLUMN IF EXISTS alternative_cost_usd;

        DELETE FROM content.engine_config WHERE key = 'default_image_model';
    """)
