"""meta pixel analytics — tabla de eventos Conversion API.

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-28
"""

from alembic import op

revision = "0020"
down_revision = "0019_image_ab_test"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    op.execute("""
        CREATE TABLE IF NOT EXISTS analytics.meta_conversion_events (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_name      VARCHAR(50)  NOT NULL,
            event_time      TIMESTAMP    NOT NULL DEFAULT NOW(),
            event_id        VARCHAR(100) UNIQUE,
            user_email      VARCHAR(255),
            user_phone      VARCHAR(50),
            user_external_id VARCHAR(100),
            event_data      JSONB,
            custom_data     JSONB,
            status          VARCHAR(20)  NOT NULL DEFAULT 'pending',
            sent_at         TIMESTAMP,
            error_message   TEXT,
            created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_meta_events_status_time
        ON analytics.meta_conversion_events(status, event_time)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS analytics.meta_conversion_events")
