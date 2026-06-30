"""sprint5.2: tabla portal.pending_notifications para modal WhatsApp admin

Revision ID: 0018_pending_notifications
Revises: 0017_content_engine
Create Date: 2026-06-28
"""

from __future__ import annotations

from alembic import op

revision = "0018_pending_notifications"
down_revision = "0017_content_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS portal.pending_notifications (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            portal_order_id UUID NOT NULL REFERENCES portal.portal_orders(id) ON DELETE CASCADE,
            template_code   VARCHAR(80)  NOT NULL,
            rendered_message TEXT        NOT NULL,
            whatsapp_link   TEXT         NOT NULL,
            status          VARCHAR(20)  NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'sent_by_admin', 'skipped')),
            created_at      TIMESTAMP    NOT NULL DEFAULT now(),
            sent_at         TIMESTAMP,
            sent_by         UUID
        );

        CREATE INDEX IF NOT EXISTS idx_pending_notif_portal_order
            ON portal.pending_notifications(portal_order_id, status);

        CREATE INDEX IF NOT EXISTS idx_pending_notif_status_created
            ON portal.pending_notifications(status, created_at);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS portal.pending_notifications;")
