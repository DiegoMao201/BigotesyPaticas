"""Portal de Fidelización — schema portal con 7 tablas.

pets, health_records, appointments, portal_orders, portal_sessions,
loyalty_points, notifications.

Revision ID: 0008_portal_schema
Revises: 0007_finance_cash_closings
Create Date: 2026-06-25 10:00:00.000000
"""
from __future__ import annotations

from alembic import op

revision = "0008_portal_schema"
down_revision = "0007_finance_cash_closings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS portal")

    # ── pets ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE portal.pets (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id     UUID NOT NULL
                                REFERENCES crm.customers(id) ON DELETE CASCADE,
            name            VARCHAR(100) NOT NULL,
            species         VARCHAR(50)  NOT NULL,
            breed           VARCHAR(100),
            birth_date      DATE,
            weight_kg       DECIMAL(5,2),
            food_brand      VARCHAR(200),
            food_freq_days  INTEGER,
            color_theme     VARCHAR(20)  NOT NULL DEFAULT 'teal'
                                CONSTRAINT ck_pets_color_theme
                                CHECK (color_theme IN
                                    ('teal','coral','amber','purple','pink','green')),
            photo_url       TEXT,
            notes           TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ
        )
    """)
    op.create_index("ix_portal_pets_customer_id",  "pets", ["customer_id"],  schema="portal")
    op.create_index("ix_portal_pets_deleted_at",   "pets", ["deleted_at"],   schema="portal")
    op.create_index("ix_portal_pets_species",      "pets", ["species"],      schema="portal")

    # ── health_records ───────────────────────────────────────────────
    op.execute("""
        CREATE TABLE portal.health_records (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pet_id       UUID NOT NULL
                             REFERENCES portal.pets(id) ON DELETE CASCADE,
            record_type  VARCHAR(100) NOT NULL,
            name         VARCHAR(200) NOT NULL,
            applied_at   DATE NOT NULL,
            next_due_at  DATE,
            vet_name     VARCHAR(200),
            notes        TEXT,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.create_index("ix_portal_hr_pet_id",    "health_records", ["pet_id"],       schema="portal")
    op.create_index("ix_portal_hr_next_due",  "health_records", ["next_due_at"],  schema="portal")
    op.create_index("ix_portal_hr_type",      "health_records", ["record_type"],  schema="portal")

    # ── appointments ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE portal.appointments (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pet_id        UUID NOT NULL
                              REFERENCES portal.pets(id) ON DELETE CASCADE,
            customer_id   UUID NOT NULL
                              REFERENCES crm.customers(id) ON DELETE CASCADE,
            service_type  VARCHAR(100) NOT NULL,
            scheduled_at  TIMESTAMPTZ NOT NULL,
            duration_min  INTEGER NOT NULL DEFAULT 60,
            status        VARCHAR(50) NOT NULL DEFAULT 'pending'
                              CONSTRAINT ck_appt_status
                              CHECK (status IN
                                  ('pending','confirmed','completed','cancelled')),
            price         DECIMAL(10,2),
            notes         TEXT,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.create_index("ix_portal_appt_pet_id",      "appointments", ["pet_id"],       schema="portal")
    op.create_index("ix_portal_appt_customer_id", "appointments", ["customer_id"],  schema="portal")
    op.create_index("ix_portal_appt_scheduled",   "appointments", ["scheduled_at"], schema="portal")
    op.create_index("ix_portal_appt_status",      "appointments", ["status"],       schema="portal")

    # ── portal_orders ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE portal.portal_orders (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id   UUID NOT NULL
                              REFERENCES crm.customers(id) ON DELETE CASCADE,
            pet_id        UUID
                              REFERENCES portal.pets(id) ON DELETE SET NULL,
            product_id    UUID
                              REFERENCES catalog.products(id) ON DELETE SET NULL,
            product_name  VARCHAR(300) NOT NULL,
            quantity      INTEGER NOT NULL DEFAULT 1
                              CONSTRAINT ck_portal_orders_qty CHECK (quantity > 0),
            unit_price    DECIMAL(10,2),
            status        VARCHAR(50) NOT NULL DEFAULT 'received'
                              CONSTRAINT ck_portal_orders_status
                              CHECK (status IN
                                  ('received','processing','ready','delivered','cancelled')),
            notes         TEXT,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.create_index("ix_portal_orders_customer",  "portal_orders", ["customer_id"], schema="portal")
    op.create_index("ix_portal_orders_pet_id",    "portal_orders", ["pet_id"],      schema="portal")
    op.create_index("ix_portal_orders_status",    "portal_orders", ["status"],      schema="portal")
    op.create_index("ix_portal_orders_created",   "portal_orders", ["created_at"],  schema="portal")

    # ── portal_sessions ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE portal.portal_sessions (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id UUID NOT NULL
                            REFERENCES crm.customers(id) ON DELETE CASCADE,
            token       VARCHAR(255) UNIQUE NOT NULL,
            expires_at  TIMESTAMPTZ NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.create_index("ix_portal_sessions_token",    "portal_sessions", ["token"],       schema="portal")
    op.create_index("ix_portal_sessions_customer", "portal_sessions", ["customer_id"], schema="portal")
    op.create_index("ix_portal_sessions_expires",  "portal_sessions", ["expires_at"],  schema="portal")

    # ── loyalty_points ───────────────────────────────────────────────
    op.execute("""
        CREATE TABLE portal.loyalty_points (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id    UUID NOT NULL
                               REFERENCES crm.customers(id) ON DELETE CASCADE,
            points         INTEGER NOT NULL
                               CONSTRAINT ck_loyalty_points_positive CHECK (points <> 0),
            reason         VARCHAR(100) NOT NULL
                               CONSTRAINT ck_loyalty_reason
                               CHECK (reason IN
                                   ('purchase','portal_order','appointment','referral','manual')),
            reference_type VARCHAR(50),
            reference_id   UUID,
            description    TEXT,
            expires_at     TIMESTAMPTZ NOT NULL
                               DEFAULT (now() + INTERVAL '12 months'),
            redeemed_at    TIMESTAMPTZ,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.create_index("ix_portal_lp_customer",  "loyalty_points", ["customer_id"], schema="portal")
    op.create_index("ix_portal_lp_expires",   "loyalty_points", ["expires_at"],  schema="portal")
    op.create_index("ix_portal_lp_reason",    "loyalty_points", ["reason"],      schema="portal")

    # ── notifications ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE portal.notifications (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id  UUID NOT NULL
                             REFERENCES crm.customers(id) ON DELETE CASCADE,
            title        VARCHAR(200) NOT NULL,
            body         TEXT NOT NULL,
            type         VARCHAR(50) NOT NULL
                             CONSTRAINT ck_notif_type
                             CHECK (type IN (
                                 'health_reminder','order_update','loyalty',
                                 'appointment','birthday','general'
                             )),
            read_at      TIMESTAMPTZ,
            data         JSONB NOT NULL DEFAULT '{}',
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.create_index("ix_portal_notif_customer", "notifications", ["customer_id"], schema="portal")
    op.create_index("ix_portal_notif_read_at",  "notifications", ["read_at"],     schema="portal")
    op.create_index("ix_portal_notif_type",     "notifications", ["type"],        schema="portal")
    op.create_index("ix_portal_notif_created",  "notifications", ["created_at"],  schema="portal")


def downgrade() -> None:
    for tbl in [
        "notifications", "loyalty_points", "portal_sessions",
        "portal_orders", "appointments", "health_records", "pets",
    ]:
        op.drop_table(tbl, schema="portal")
    op.execute("DROP SCHEMA IF EXISTS portal")
