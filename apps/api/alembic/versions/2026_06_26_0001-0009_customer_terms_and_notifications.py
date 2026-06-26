"""Términos de uso en customers + is_admin en notifications.

Revision ID: 0009_customer_terms_notifications
Revises: 0008_portal_schema
Create Date: 2026-06-26 00:01:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_customer_terms_notifications"
down_revision = "0008_portal_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── crm.customers — consentimiento legal ─────────────────────────────
    op.add_column(
        "customers",
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
        schema="crm",
    )
    op.add_column(
        "customers",
        sa.Column("data_consent_at", sa.DateTime(timezone=True), nullable=True),
        schema="crm",
    )
    op.add_column(
        "customers",
        sa.Column("consent_version", sa.String(10), nullable=True),
        schema="crm",
    )

    # ── portal.notifications — notificaciones admin + customer_id nullable ──
    op.add_column(
        "notifications",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        schema="portal",
    )
    # Hacer customer_id nullable para notificaciones de admin
    op.alter_column(
        "notifications",
        "customer_id",
        nullable=True,
        schema="portal",
    )
    # Ampliar el check de tipos para admitir todos los tipos nuevos
    op.execute(
        "ALTER TABLE portal.notifications DROP CONSTRAINT IF EXISTS ck_notif_type"
    )
    op.execute(
        "ALTER TABLE portal.notifications ADD CONSTRAINT ck_notif_type "
        "CHECK (type IN ('health_reminder','order_update','loyalty','appointment',"
        "'birthday','general','new_order','new_appointment','new_customer',"
        "'order_confirmed','order_ready','order_delivered','appt_confirmed',"
        "'appt_rescheduled','appt_cancelled'))"
    )


def downgrade() -> None:
    op.drop_column("customers", "terms_accepted_at", schema="crm")
    op.drop_column("customers", "data_consent_at", schema="crm")
    op.drop_column("customers", "consent_version", schema="crm")
    op.drop_column("notifications", "is_admin", schema="portal")
    op.alter_column(
        "notifications",
        "customer_id",
        nullable=False,
        schema="portal",
    )
