"""Fase 1 comunidad: schema community.* para SOS de mascotas perdidas.

Añade sos_events + sos_sightings, y columnas de geolocalización/preferencias
en crm.customers + is_lost en portal.pets. Todo aditivo, reversible.

Revision ID: 0023_sos_mascotas_perdidas
Revises: 0022
Create Date: 2026-07-26
"""

from __future__ import annotations

from alembic import op

revision = "0023_sos_mascotas_perdidas"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE SCHEMA IF NOT EXISTS community;

        CREATE TABLE IF NOT EXISTS community.sos_events (
            id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pet_id                UUID REFERENCES portal.pets(id) ON DELETE SET NULL,
            reporter_customer_id  UUID NOT NULL REFERENCES crm.customers(id) ON DELETE CASCADE,
            pet_name              VARCHAR(150) NOT NULL,
            species               VARCHAR(30)  NOT NULL,
            breed                 VARCHAR(100),
            color                 VARCHAR(100) NOT NULL,
            photos                JSONB        NOT NULL DEFAULT '[]',
            last_seen_lat         NUMERIC(9,6) NOT NULL,
            last_seen_lng         NUMERIC(9,6) NOT NULL,
            last_seen_at          TIMESTAMPTZ  NOT NULL,
            contact_phone         VARCHAR(40)  NOT NULL,
            reward                NUMERIC(12,2),
            status                VARCHAR(20)  NOT NULL DEFAULT 'active'
                                   CHECK (status IN ('active', 'found', 'closed', 'expired')),
            radius_km             INTEGER      NOT NULL DEFAULT 5,
            notified_count        INTEGER      NOT NULL DEFAULT 0,
            found_at              TIMESTAMPTZ,
            created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_sos_events_status_created
            ON community.sos_events(status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_sos_events_reporter
            ON community.sos_events(reporter_customer_id);

        CREATE TABLE IF NOT EXISTS community.sos_sightings (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            sos_event_id         UUID NOT NULL REFERENCES community.sos_events(id) ON DELETE CASCADE,
            spotter_customer_id  UUID NOT NULL REFERENCES crm.customers(id) ON DELETE CASCADE,
            lat                  NUMERIC(9,6) NOT NULL,
            lng                  NUMERIC(9,6) NOT NULL,
            photo_url            TEXT,
            note                 TEXT,
            seen_at              TIMESTAMPTZ  NOT NULL,
            created_at           TIMESTAMPTZ  NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_sos_sightings_event
            ON community.sos_sightings(sos_event_id);

        ALTER TABLE crm.customers
            ADD COLUMN IF NOT EXISTS last_lat NUMERIC(9,6),
            ADD COLUMN IF NOT EXISTS last_lng NUMERIC(9,6),
            ADD COLUMN IF NOT EXISTS last_location_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS sos_radius_km INTEGER NOT NULL DEFAULT 5,
            ADD COLUMN IF NOT EXISTS notification_prefs JSONB NOT NULL
                DEFAULT '{"sos": true, "promos": true, "appointments": true}';

        ALTER TABLE portal.pets
            ADD COLUMN IF NOT EXISTS is_lost BOOLEAN NOT NULL DEFAULT false;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE portal.pets DROP COLUMN IF EXISTS is_lost;

        ALTER TABLE crm.customers
            DROP COLUMN IF EXISTS last_lat,
            DROP COLUMN IF EXISTS last_lng,
            DROP COLUMN IF EXISTS last_location_at,
            DROP COLUMN IF EXISTS sos_radius_km,
            DROP COLUMN IF EXISTS notification_prefs;

        DROP TABLE IF EXISTS community.sos_sightings;
        DROP TABLE IF EXISTS community.sos_events;
        DROP SCHEMA IF EXISTS community;
    """)
