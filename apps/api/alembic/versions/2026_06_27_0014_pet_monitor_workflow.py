"""pet monitor workflow: workflow_status, activity_log, appointments reschedule

Revision ID: 0014_pet_monitor_workflow
Revises: 0013_portal_order_items
Create Date: 2026-06-27
"""
from __future__ import annotations
from alembic import op

revision = "0014_pet_monitor_workflow"
down_revision = "0013_portal_order_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── portal_orders: campos de workflow ─────────────────────────────────
    op.execute("""
        ALTER TABLE portal.portal_orders
            ADD COLUMN IF NOT EXISTS workflow_status VARCHAR(40) DEFAULT 'received',
            ADD COLUMN IF NOT EXISTS internal_notes TEXT,
            ADD COLUMN IF NOT EXISTS customer_facing_notes TEXT,
            ADD COLUMN IF NOT EXISTS last_status_change_at TIMESTAMPTZ DEFAULT now(),
            ADD COLUMN IF NOT EXISTS last_status_changed_by UUID,
            ADD COLUMN IF NOT EXISTS customer_confirmed_changes_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS customer_confirmation_channel VARCHAR(40),
            ADD COLUMN IF NOT EXISTS discount_amount DECIMAL(10,2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS discount_reason TEXT,
            ADD COLUMN IF NOT EXISTS total_amount DECIMAL(10,2);
    """)

    # Backfill workflow_status desde status
    op.execute("""
        UPDATE portal.portal_orders
        SET workflow_status = CASE
            WHEN status = 'pending'   THEN 'received'
            WHEN status = 'invoiced'  THEN 'invoiced'
            WHEN status = 'delivered' THEN 'delivered'
            WHEN status = 'cancelled' THEN 'cancelled'
            ELSE 'received'
        END
        WHERE workflow_status IS NULL OR workflow_status = 'received';
    """)

    # Backfill total_amount desde unit_price * quantity de items (o del campo legacy)
    op.execute("""
        UPDATE portal.portal_orders po
        SET total_amount = COALESCE(
            (SELECT SUM(poi.unit_price * poi.quantity)
             FROM portal.portal_order_items poi
             WHERE poi.portal_order_id = po.id),
            COALESCE(po.unit_price, 0) * po.quantity
        )
        WHERE po.total_amount IS NULL;
    """)

    # Constraint workflow_status
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'workflow_status_check'
                  AND conrelid = 'portal.portal_orders'::regclass
            ) THEN
                ALTER TABLE portal.portal_orders
                    ADD CONSTRAINT workflow_status_check CHECK (workflow_status IN (
                        'received', 'under_review', 'awaiting_customer',
                        'ready_to_invoice', 'invoiced', 'in_preparation',
                        'ready_for_delivery', 'in_transit', 'delivered',
                        'cancelled', 'returned'
                    ));
            END IF;
        END$$;
    """)

    # ── activity_log ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS portal.activity_log (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type      VARCHAR(50) NOT NULL,
            entity_id        UUID NOT NULL,
            action           VARCHAR(80) NOT NULL,
            actor_type       VARCHAR(20),
            actor_id         UUID,
            actor_name       VARCHAR(200),
            changes          JSONB,
            notes            TEXT,
            visible_to_customer BOOLEAN DEFAULT false,
            notification_sent_at TIMESTAMPTZ,
            notification_channel VARCHAR(40),
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_activity_log_entity
            ON portal.activity_log(entity_type, entity_id, created_at DESC);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_activity_log_unsent
            ON portal.activity_log(entity_id, notification_sent_at)
            WHERE visible_to_customer = true AND notification_sent_at IS NULL;
    """)

    # ── función log_activity ──────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION portal.log_activity(
            p_entity_type VARCHAR,
            p_entity_id   UUID,
            p_action      VARCHAR,
            p_actor_type  VARCHAR   DEFAULT 'system',
            p_actor_id    UUID      DEFAULT NULL,
            p_actor_name  VARCHAR   DEFAULT NULL,
            p_changes     JSONB     DEFAULT NULL,
            p_notes       TEXT      DEFAULT NULL,
            p_visible     BOOLEAN   DEFAULT false
        ) RETURNS UUID AS $$
        DECLARE log_id UUID;
        BEGIN
            INSERT INTO portal.activity_log (
                entity_type, entity_id, action, actor_type, actor_id,
                actor_name, changes, notes, visible_to_customer
            ) VALUES (
                p_entity_type, p_entity_id, p_action, p_actor_type, p_actor_id,
                p_actor_name, p_changes, p_notes, p_visible
            ) RETURNING id INTO log_id;
            RETURN log_id;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Seed activity_log con pedidos existentes (created event)
    op.execute("""
        INSERT INTO portal.activity_log (entity_type, entity_id, action, actor_type, visible_to_customer, created_at)
        SELECT 'order', id, 'created', 'system', true, created_at
        FROM portal.portal_orders
        WHERE NOT EXISTS (
            SELECT 1 FROM portal.activity_log al
            WHERE al.entity_id = portal_orders.id AND al.action = 'created'
        );
    """)

    # ── portal_order_items: agregar is_substituted / substituted_from_name ─
    op.execute("""
        ALTER TABLE portal.portal_order_items
            ADD COLUMN IF NOT EXISTS is_substituted BOOLEAN DEFAULT false,
            ADD COLUMN IF NOT EXISTS substituted_from_name VARCHAR(500),
            ADD COLUMN IF NOT EXISTS is_removed BOOLEAN DEFAULT false;
    """)

    # ── appointments: workflow_status ─────────────────────────────────────
    op.execute("""
        ALTER TABLE portal.appointments
            ADD COLUMN IF NOT EXISTS workflow_status VARCHAR(40) DEFAULT 'requested',
            ADD COLUMN IF NOT EXISTS rescheduled_from_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS reschedule_reason TEXT,
            ADD COLUMN IF NOT EXISTS reschedule_reason_category VARCHAR(80),
            ADD COLUMN IF NOT EXISTS compensation_points INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS proposed_options JSONB;
    """)

    op.execute("""
        UPDATE portal.appointments
        SET workflow_status = CASE
            WHEN status = 'pending'   THEN 'requested'
            WHEN status = 'confirmed' THEN 'confirmed'
            WHEN status = 'completed' THEN 'completed'
            WHEN status = 'cancelled' THEN 'cancelled'
            ELSE 'requested'
        END
        WHERE workflow_status IS NULL OR workflow_status = 'requested';
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'appt_workflow_check'
            ) THEN
                ALTER TABLE portal.appointments
                    ADD CONSTRAINT appt_workflow_check CHECK (workflow_status IN (
                        'requested', 'confirmed', 'awaiting_customer_reschedule',
                        'rescheduled', 'in_progress', 'completed', 'no_show', 'cancelled'
                    ));
            END IF;
        END$$;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS portal.log_activity CASCADE;")
    op.execute("DROP INDEX IF EXISTS portal.idx_activity_log_unsent;")
    op.execute("DROP INDEX IF EXISTS portal.idx_activity_log_entity;")
    op.execute("DROP TABLE IF EXISTS portal.activity_log;")
    op.execute("""
        ALTER TABLE portal.portal_orders
            DROP COLUMN IF EXISTS workflow_status,
            DROP COLUMN IF EXISTS internal_notes,
            DROP COLUMN IF EXISTS customer_facing_notes,
            DROP COLUMN IF EXISTS last_status_change_at,
            DROP COLUMN IF EXISTS last_status_changed_by,
            DROP COLUMN IF EXISTS customer_confirmed_changes_at,
            DROP COLUMN IF EXISTS customer_confirmation_channel,
            DROP COLUMN IF EXISTS discount_amount,
            DROP COLUMN IF EXISTS discount_reason,
            DROP COLUMN IF EXISTS total_amount;
    """)
    op.execute("""
        ALTER TABLE portal.appointments
            DROP COLUMN IF EXISTS workflow_status,
            DROP COLUMN IF EXISTS rescheduled_from_at,
            DROP COLUMN IF EXISTS reschedule_reason,
            DROP COLUMN IF EXISTS reschedule_reason_category,
            DROP COLUMN IF EXISTS compensation_points,
            DROP COLUMN IF EXISTS proposed_options;
    """)
