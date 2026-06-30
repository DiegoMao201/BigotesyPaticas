"""portal v4 schema — orders/appointments/notifications/referrals.

Revision ID: 0010_portal_v4_schema
Revises: 0009_customer_terms_notifications
Create Date: 2026-06-26
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "0010_portal_v4_schema"
down_revision = "0009_customer_terms_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── portal.portal_orders — nuevas columnas ────────────────────────────────
    op.execute(
        text(
            "ALTER TABLE portal.portal_orders ADD COLUMN IF NOT EXISTS invoice_number VARCHAR(50) NULL"
        )
    )
    op.execute(
        text(
            "ALTER TABLE portal.portal_orders ADD COLUMN IF NOT EXISTS invoiced_at TIMESTAMPTZ NULL"
        )
    )
    op.execute(
        text("ALTER TABLE portal.portal_orders ADD COLUMN IF NOT EXISTS invoice_pdf_url TEXT NULL")
    )
    op.execute(
        text(
            "ALTER TABLE portal.portal_orders ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ NULL"
        )
    )
    op.execute(
        text(
            "ALTER TABLE portal.portal_orders ADD COLUMN IF NOT EXISTS points_awarded INTEGER NOT NULL DEFAULT 0"
        )
    )
    op.execute(
        text(
            "ALTER TABLE portal.portal_orders ADD COLUMN IF NOT EXISTS under_minimum BOOLEAN NOT NULL DEFAULT false"
        )
    )
    op.execute(
        text("ALTER TABLE portal.portal_orders ADD COLUMN IF NOT EXISTS sales_order_id UUID NULL")
    )

    # Expand portal_orders status CHECK (drop old, add new with 'invoiced')
    op.execute(
        text("ALTER TABLE portal.portal_orders DROP CONSTRAINT IF EXISTS ck_portal_orders_status")
    )
    op.execute(
        text(
            "ALTER TABLE portal.portal_orders ADD CONSTRAINT ck_portal_order_status CHECK (status IN ("
            "  'received','processing','invoiced','ready','delivered','cancelled'"
            "))"
        )
    )

    # ── portal.portal_orders — columna adicional ──────────────────────────────
    op.execute(
        text(
            "ALTER TABLE portal.portal_orders ADD COLUMN IF NOT EXISTS processed_by VARCHAR(100) NULL"
        )
    )

    # ── portal.appointments — nuevas columnas ─────────────────────────────────
    op.execute(
        text(
            "ALTER TABLE portal.appointments ADD COLUMN IF NOT EXISTS confirmed_by VARCHAR(100) NULL"
        )
    )
    op.execute(
        text(
            "ALTER TABLE portal.appointments ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ NULL"
        )
    )
    op.execute(
        text(
            "ALTER TABLE portal.appointments ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ NULL"
        )
    )
    op.execute(
        text(
            "ALTER TABLE portal.appointments ADD COLUMN IF NOT EXISTS reminder_sent BOOLEAN NOT NULL DEFAULT false"
        )
    )
    op.execute(
        text("ALTER TABLE portal.appointments ADD COLUMN IF NOT EXISTS cancel_reason TEXT NULL")
    )

    # ── portal.pets — thumbnail ───────────────────────────────────────────────
    op.execute(text("ALTER TABLE portal.pets ADD COLUMN IF NOT EXISTS thumb_url TEXT NULL"))

    # ── portal.notifications — nueva columna ──────────────────────────────────
    op.execute(
        text("ALTER TABLE portal.notifications ADD COLUMN IF NOT EXISTS action_url TEXT NULL")
    )

    # Expand notifications type CHECK
    op.execute(text("ALTER TABLE portal.notifications DROP CONSTRAINT IF EXISTS ck_notif_type"))
    op.execute(
        text(
            "ALTER TABLE portal.notifications ADD CONSTRAINT ck_notif_type CHECK (type IN ("
            "  'health_reminder','order_update','loyalty','appointment','birthday','general',"
            "  'new_order','new_appointment','new_customer',"
            "  'order_confirmed','order_ready','order_delivered','appt_confirmed',"
            "  'appt_rescheduled','appt_cancelled','referral_signup','referral_reward',"
            "  'welcome_bonus','order_invoiced'"
            "))"
        )
    )

    # ── crm.customers — columnas de referidos ─────────────────────────────────
    op.execute(
        text("ALTER TABLE crm.customers ADD COLUMN IF NOT EXISTS referral_code VARCHAR(20) NULL")
    )
    op.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_referral_code "
            "ON crm.customers(referral_code) WHERE referral_code IS NOT NULL"
        )
    )
    op.execute(
        text("ALTER TABLE crm.customers ADD COLUMN IF NOT EXISTS referred_by_code VARCHAR(20) NULL")
    )
    op.execute(
        text("ALTER TABLE crm.customers ADD COLUMN IF NOT EXISTS referred_by_customer_id UUID NULL")
    )

    # ── portal.referrals — nueva tabla ───────────────────────────────────────
    op.execute(
        text("""
        CREATE TABLE IF NOT EXISTS portal.referrals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            referrer_customer_id UUID NOT NULL REFERENCES crm.customers(id) ON DELETE CASCADE,
            referred_customer_id UUID NOT NULL REFERENCES crm.customers(id) ON DELETE CASCADE,
            referral_code VARCHAR(20) NOT NULL,
            signed_up_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            first_purchase_at TIMESTAMPTZ,
            reward_paid_at TIMESTAMPTZ,
            UNIQUE (referred_customer_id)
        )
    """)
    )
    op.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_referrals_referrer "
            "ON portal.referrals(referrer_customer_id)"
        )
    )
    op.execute(
        text("CREATE INDEX IF NOT EXISTS idx_referrals_code " "ON portal.referrals(referral_code)")
    )


def downgrade() -> None:
    # referrals table
    op.execute(text("DROP TABLE IF EXISTS portal.referrals"))

    # crm.customers referral columns
    op.execute(text("ALTER TABLE crm.customers DROP COLUMN IF EXISTS referred_by_customer_id"))
    op.execute(text("ALTER TABLE crm.customers DROP COLUMN IF EXISTS referred_by_code"))
    op.execute(text("DROP INDEX IF EXISTS crm.uq_customers_referral_code"))
    op.execute(text("ALTER TABLE crm.customers DROP COLUMN IF EXISTS referral_code"))

    # notifications action_url + revert CHECK
    op.execute(text("ALTER TABLE portal.notifications DROP CONSTRAINT IF EXISTS ck_notif_type"))
    op.execute(
        text(
            "ALTER TABLE portal.notifications ADD CONSTRAINT ck_notif_type CHECK (type IN ("
            "  'health_reminder','order_update','loyalty','appointment','birthday','general',"
            "  'new_order','new_appointment','new_customer','order_confirmed','order_ready',"
            "  'order_delivered','appt_confirmed','appt_rescheduled','appt_cancelled'"
            "))"
        )
    )
    op.execute(text("ALTER TABLE portal.notifications DROP COLUMN IF EXISTS action_url"))

    # appointments columns
    op.execute(text("ALTER TABLE portal.appointments DROP COLUMN IF EXISTS cancel_reason"))
    op.execute(text("ALTER TABLE portal.appointments DROP COLUMN IF EXISTS completed_at"))
    op.execute(text("ALTER TABLE portal.appointments DROP COLUMN IF EXISTS confirmed_at"))

    # portal_orders — revert status CHECK + columns
    op.execute(
        text("ALTER TABLE portal.portal_orders DROP CONSTRAINT IF EXISTS ck_portal_order_status")
    )
    op.execute(
        text(
            "ALTER TABLE portal.portal_orders ADD CONSTRAINT ck_portal_orders_status CHECK (status IN ("
            "  'received','processing','ready','delivered','cancelled'"
            "))"
        )
    )
    op.execute(text("ALTER TABLE portal.portal_orders DROP COLUMN IF EXISTS sales_order_id"))
    op.execute(text("ALTER TABLE portal.portal_orders DROP COLUMN IF EXISTS under_minimum"))
    op.execute(text("ALTER TABLE portal.portal_orders DROP COLUMN IF EXISTS points_awarded"))
    op.execute(text("ALTER TABLE portal.portal_orders DROP COLUMN IF EXISTS delivered_at"))
    op.execute(text("ALTER TABLE portal.portal_orders DROP COLUMN IF EXISTS invoice_pdf_url"))
    op.execute(text("ALTER TABLE portal.portal_orders DROP COLUMN IF EXISTS invoiced_at"))
    op.execute(text("ALTER TABLE portal.portal_orders DROP COLUMN IF EXISTS invoice_number"))
