"""Add inventory.count_sessions and inventory.count_items for physical stock counts.

Revision ID: 0004_inventory_counts
Revises: 0003_suppliers
Create Date: 2026-05-14 10:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_inventory_counts"
down_revision: Union[str, None] = "0003_suppliers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── count_sessions ──────────────────────────────────────────────
    op.create_table(
        "count_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(200), nullable=False),
        # draft → in_progress → applied | cancelled
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'draft'")
        ),
        sa.Column("notes", sa.Text, nullable=True),
        # Snapshot metrics (populated on apply)
        sa.Column("total_products_counted", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("total_with_difference", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("total_positive_delta", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("total_negative_delta", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column(
            "total_value_impact",
            sa.Numeric(16, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_by", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", sa.String(200), nullable=True),
        schema="inventory",
    )
    op.create_index(
        "ix_count_sessions_status",
        "count_sessions",
        ["status"],
        schema="inventory",
    )
    op.create_index(
        "ix_count_sessions_created_at",
        "count_sessions",
        ["created_at"],
        schema="inventory",
    )

    # ─── count_items ─────────────────────────────────────────────────
    op.create_table(
        "count_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inventory.count_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog.products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Snapshot at count time
        sa.Column("sku", sa.String(80), nullable=False),
        sa.Column("product_name", sa.String(300), nullable=False),
        sa.Column("category_name", sa.String(120), nullable=True),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        # Stock in system when count was created
        sa.Column("system_qty", sa.Integer, nullable=False, server_default=sa.text("0")),
        # Physically counted quantity (null = not counted yet)
        sa.Column("counted_qty", sa.Integer, nullable=True),
        # delta = counted_qty - system_qty (null until counted)
        sa.Column("delta", sa.Integer, nullable=True),
        # value_impact = delta * unit_cost
        sa.Column(
            "value_impact", sa.Numeric(16, 2), nullable=True
        ),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("session_id", "product_id", name="uq_count_items_session_product"),
        schema="inventory",
    )
    op.create_index(
        "ix_count_items_session_id",
        "count_items",
        ["session_id"],
        schema="inventory",
    )
    op.create_index(
        "ix_count_items_product_id",
        "count_items",
        ["product_id"],
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_table("count_items", schema="inventory")
    op.drop_table("count_sessions", schema="inventory")
