"""Fase 3 comunidad (completa): login de aliados, disponibilidad, reservas y reseñas.

Añade partners.partner_users, partners.service_slots, partners.bookings y
partners.partner_reviews. Habilita el registro público de aliados, la agenda
real por disponibilidad configurable, el agendamiento del cliente y la
calificación de servicios. Todo aditivo, reversible.

Revision ID: 0026_aliados_agenda_bookings
Revises: 0025_aliados_servicios_partners
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op

revision = "0026_aliados_agenda_bookings"
down_revision = "0025_aliados_servicios_partners"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS partners.partner_users (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            partner_id     UUID NOT NULL REFERENCES partners.partners(id) ON DELETE CASCADE,
            email          CITEXT NOT NULL UNIQUE,
            password_hash  VARCHAR(255) NOT NULL,
            role           VARCHAR(20)  NOT NULL DEFAULT 'owner'
                           CHECK (role IN ('owner','staff')),
            full_name      VARCHAR(150) NOT NULL,
            is_active      BOOLEAN      NOT NULL DEFAULT true,
            created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_partner_users_partner ON partners.partner_users(partner_id);

        CREATE TABLE IF NOT EXISTS partners.service_slots (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            partner_id     UUID NOT NULL REFERENCES partners.partners(id) ON DELETE CASCADE,
            service_id     UUID REFERENCES partners.services(id) ON DELETE CASCADE,
            day_of_week    INTEGER      NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
            start_time     TIME         NOT NULL,
            end_time       TIME         NOT NULL,
            slot_minutes   INTEGER      NOT NULL DEFAULT 30,
            max_bookings   INTEGER      NOT NULL DEFAULT 1,
            is_active      BOOLEAN      NOT NULL DEFAULT true,
            created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_service_slots_partner ON partners.service_slots(partner_id);
        CREATE INDEX IF NOT EXISTS idx_service_slots_service ON partners.service_slots(service_id);

        CREATE TABLE IF NOT EXISTS partners.bookings (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id      UUID NOT NULL REFERENCES crm.customers(id) ON DELETE CASCADE,
            partner_id       UUID NOT NULL REFERENCES partners.partners(id) ON DELETE CASCADE,
            service_id       UUID REFERENCES partners.services(id) ON DELETE SET NULL,
            pet_id           UUID REFERENCES portal.pets(id) ON DELETE SET NULL,
            scheduled_at     TIMESTAMPTZ  NOT NULL,
            duration_min     INTEGER      NOT NULL DEFAULT 30,
            status           VARCHAR(20)  NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending','confirmed','completed','cancelled','no_show')),
            price_snapshot   NUMERIC(12,2),
            notes_customer   TEXT,
            notes_partner    TEXT,
            cancelled_reason VARCHAR(255),
            created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_bookings_customer ON partners.bookings(customer_id);
        CREATE INDEX IF NOT EXISTS idx_bookings_partner ON partners.bookings(partner_id);
        CREATE INDEX IF NOT EXISTS idx_bookings_status ON partners.bookings(status);
        CREATE INDEX IF NOT EXISTS idx_bookings_scheduled_at ON partners.bookings(scheduled_at);

        CREATE TABLE IF NOT EXISTS partners.partner_reviews (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            booking_id   UUID NOT NULL UNIQUE REFERENCES partners.bookings(id) ON DELETE CASCADE,
            partner_id   UUID NOT NULL REFERENCES partners.partners(id) ON DELETE CASCADE,
            customer_id  UUID NOT NULL REFERENCES crm.customers(id) ON DELETE CASCADE,
            rating       INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            comment      TEXT,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_partner_reviews_partner ON partners.partner_reviews(partner_id);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS partners.partner_reviews;
        DROP TABLE IF EXISTS partners.bookings;
        DROP TABLE IF EXISTS partners.service_slots;
        DROP TABLE IF EXISTS partners.partner_users;
    """)
