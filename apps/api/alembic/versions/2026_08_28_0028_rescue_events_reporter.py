"""Rescate: los reporta el cliente desde el portal, no el admin.

Añade reporter_customer_id a community.rescue_events -- quién de la
comunidad encontró/rescató a los animales. El admin pasa a ser solo
moderador (cerrar evento, marcar animal como reunido, quitar fotos).

Revision ID: 0028_rescue_events_reporter
Revises: 0027_rescue_events
Create Date: 2026-08-28
"""

from __future__ import annotations

from alembic import op

revision = "0028_rescue_events_reporter"
down_revision = "0027_rescue_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE community.rescue_events
            ADD COLUMN IF NOT EXISTS reporter_customer_id UUID
                REFERENCES crm.customers(id) ON DELETE SET NULL;

        CREATE INDEX IF NOT EXISTS idx_rescue_events_reporter
            ON community.rescue_events(reporter_customer_id);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS community.idx_rescue_events_reporter;
        ALTER TABLE community.rescue_events DROP COLUMN IF EXISTS reporter_customer_id;
    """)
