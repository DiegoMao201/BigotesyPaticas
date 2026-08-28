"""SOS: animales encontrados/rescatados, agrupados por evento de rescate.

Añade community.rescue_events (un lugar/fecha donde se encontraron uno o más
animales) y community.rescue_animals (una foto + descripción por animal,
N por evento). Todo aditivo, reversible.

Revision ID: 0027_rescue_events
Revises: 0026_aliados_agenda_bookings
Create Date: 2026-08-16
"""

from __future__ import annotations

from alembic import op

revision = "0027_rescue_events"
down_revision = "0026_aliados_agenda_bookings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS community.rescue_events (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title             VARCHAR(200) NOT NULL,
            description       TEXT,
            address           VARCHAR(300),
            lat               NUMERIC(9,6) NOT NULL,
            lng               NUMERIC(9,6) NOT NULL,
            found_at          TIMESTAMPTZ  NOT NULL,
            contact_phone     VARCHAR(40),
            status            VARCHAR(20)  NOT NULL DEFAULT 'open'
                               CHECK (status IN ('open', 'closed')),
            created_by_admin  VARCHAR(200),
            created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_rescue_events_status_found
            ON community.rescue_events(status, found_at DESC);

        CREATE TABLE IF NOT EXISTS community.rescue_animals (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rescue_event_id   UUID NOT NULL REFERENCES community.rescue_events(id) ON DELETE CASCADE,
            photo_url         TEXT NOT NULL,
            thumb_url         TEXT,
            species           VARCHAR(30),
            description       TEXT,
            status            VARCHAR(20)  NOT NULL DEFAULT 'unclaimed'
                               CHECK (status IN ('unclaimed', 'reunited')),
            sort_order        INTEGER      NOT NULL DEFAULT 0,
            created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_rescue_animals_event
            ON community.rescue_animals(rescue_event_id);
        CREATE INDEX IF NOT EXISTS idx_rescue_animals_status
            ON community.rescue_animals(status);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS community.rescue_animals;
        DROP TABLE IF EXISTS community.rescue_events;
    """)
