"""Foro rápido de adopción: publicar sin cuenta, solo nombre + teléfono.

Añade reporter_name (texto libre) a community.adoption_listings para las
publicaciones anónimas del foro público (sin PortalUser) -- las publicadas
desde el portal siguen usando reporter_customer_id como hasta ahora.

Revision ID: 0030_adoption_reporter_name
Revises: 0029_adoption_listings
Create Date: 2026-08-28
"""

from __future__ import annotations

from alembic import op

revision = "0030_adoption_reporter_name"
down_revision = "0029_adoption_listings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE community.adoption_listings
            ADD COLUMN IF NOT EXISTS reporter_name VARCHAR(150);
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE community.adoption_listings DROP COLUMN IF EXISTS reporter_name;
    """)
