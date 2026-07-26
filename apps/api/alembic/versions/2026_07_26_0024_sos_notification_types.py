"""Fase 1 comunidad: agrega tipos sos_nearby/sos_sighting/sos_found al CHECK de portal.notifications.

Revision ID: 0024_sos_notification_types
Revises: 0023_sos_mascotas_perdidas
Create Date: 2026-07-26
"""

from __future__ import annotations

from alembic import op

revision = "0024_sos_notification_types"
down_revision = "0023_sos_mascotas_perdidas"
branch_labels = None
depends_on = None

_OLD_TYPES = (
    "'health_reminder', 'order_update', 'loyalty', 'appointment', 'birthday', 'general', "
    "'new_order', 'new_appointment', 'new_customer', 'order_confirmed', 'order_ready', "
    "'order_delivered', 'appt_confirmed', 'appt_rescheduled', 'appt_cancelled', "
    "'referral_signup', 'referral_reward', 'welcome_bonus', 'order_invoiced'"
)
_NEW_TYPES = _OLD_TYPES + ", 'sos_nearby', 'sos_sighting', 'sos_found'"


def upgrade() -> None:
    op.execute(f"""
        ALTER TABLE portal.notifications DROP CONSTRAINT IF EXISTS ck_notif_type;
        ALTER TABLE portal.notifications
            ADD CONSTRAINT ck_notif_type CHECK (type::text = ANY (ARRAY[{_NEW_TYPES}]::text[]));
    """)


def downgrade() -> None:
    op.execute(f"""
        ALTER TABLE portal.notifications DROP CONSTRAINT IF EXISTS ck_notif_type;
        ALTER TABLE portal.notifications
            ADD CONSTRAINT ck_notif_type CHECK (type::text = ANY (ARRAY[{_OLD_TYPES}]::text[]));
    """)
