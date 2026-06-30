"""Add missing updated_at column to inventory.count_items.

The original migration 0004 created count_items without updated_at,
but the CountItem model uses TimestampMixin which requires it.

Revision ID: 0005_fix_count_items_updated_at
Revises: 0004_inventory_counts
Create Date: 2026-05-14 11:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_fix_count_items_updated_at"
down_revision: str | None = "0004_inventory_counts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "count_items",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_column("count_items", "updated_at", schema="inventory")
