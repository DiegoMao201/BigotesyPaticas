"""Fase 3 comunidad: schema partners.* — directorio de aliados y servicios.

Añade partners.partners + partners.services (directorio público de
veterinarias, paseadores, refugios y peluquerías). Sin agendamiento todavía
(PartnerUser/ServiceSlot/Booking quedan para la siguiente iteración). Todo
aditivo, reversible.

Revision ID: 0025_aliados_servicios_partners
Revises: 0024_sos_notification_types
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op

revision = "0025_aliados_servicios_partners"
down_revision = "0024_sos_notification_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE SCHEMA IF NOT EXISTS partners;

        CREATE TABLE IF NOT EXISTS partners.partners (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug             VARCHAR(160) NOT NULL UNIQUE,
            partner_type     VARCHAR(20)  NOT NULL
                             CHECK (partner_type IN ('vet','walker','shelter','groomer')),
            business_name    VARCHAR(160) NOT NULL,
            legal_name       VARCHAR(160) NOT NULL,
            document_id      VARCHAR(30)  NOT NULL,
            email            VARCHAR(160),
            phone            VARCHAR(40),
            whatsapp         VARCHAR(40),
            address          VARCHAR(200),
            city             VARCHAR(80)  NOT NULL,
            lat              NUMERIC(9,6),
            lng              NUMERIC(9,6),
            logo_url         TEXT,
            cover_url        TEXT,
            bio              TEXT,
            rating_avg       NUMERIC(3,2) NOT NULL DEFAULT 0,
            rating_count     INTEGER      NOT NULL DEFAULT 0,
            verified_at      TIMESTAMPTZ,
            published_at     TIMESTAMPTZ,
            commission_pct   NUMERIC(5,2) NOT NULL DEFAULT 0,
            extra            JSONB        NOT NULL DEFAULT '{}',
            deleted_at       TIMESTAMPTZ,
            created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_partners_type ON partners.partners(partner_type);
        CREATE INDEX IF NOT EXISTS idx_partners_city ON partners.partners(city);
        CREATE INDEX IF NOT EXISTS idx_partners_published ON partners.partners(published_at);

        CREATE TABLE IF NOT EXISTS partners.services (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            partner_id     UUID NOT NULL REFERENCES partners.partners(id) ON DELETE CASCADE,
            slug           VARCHAR(160) NOT NULL,
            name           VARCHAR(160) NOT NULL,
            description    TEXT,
            duration_min   INTEGER,
            price          NUMERIC(12,2),
            price_type     VARCHAR(10)  NOT NULL DEFAULT 'fixed'
                           CHECK (price_type IN ('fixed','from','quote')),
            category       VARCHAR(40)  NOT NULL,
            requires_pet   BOOLEAN      NOT NULL DEFAULT true,
            is_active      BOOLEAN      NOT NULL DEFAULT true,
            created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
            UNIQUE (partner_id, slug)
        );

        CREATE INDEX IF NOT EXISTS idx_services_partner ON partners.services(partner_id);
        CREATE INDEX IF NOT EXISTS idx_services_category ON partners.services(category);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS partners.services;
        DROP TABLE IF EXISTS partners.partners;
        DROP SCHEMA IF EXISTS partners;
    """)
