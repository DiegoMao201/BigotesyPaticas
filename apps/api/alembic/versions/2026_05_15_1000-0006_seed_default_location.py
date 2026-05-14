"""Seed default stock location.

If a location already exists, mark the first one as is_default=1.
If none exists, create 'Bodega Principal' with is_default=1.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-15 10:00:00.000000
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0006_seed_default_location"
down_revision = "0005_fix_count_items_updated_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Check if any location exists
    result = conn.execute(
        sa.text("SELECT id FROM inventory.stock_locations ORDER BY created_at LIMIT 1")
    ).fetchone()

    if result is not None:
        # Mark the first existing location as default
        conn.execute(
            sa.text(
                "UPDATE inventory.stock_locations SET is_default = 1, updated_at = now() "
                "WHERE id = :loc_id"
            ),
            {"loc_id": result[0]},
        )
    else:
        # No locations at all — create the main one
        new_id = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO inventory.stock_locations (id, code, name, is_default, created_at, updated_at) "
                "VALUES (:id, 'MAIN', 'Bodega Principal', 1, now(), now())"
            ),
            {"id": new_id},
        )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE inventory.stock_locations SET is_default = 0 WHERE is_default = 1")
    )
