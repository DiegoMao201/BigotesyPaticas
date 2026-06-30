"""Add purchasing.purchases and purchasing.purchase_items tables.

Revision ID: 0002_purchases
Revises: 0001_init
Create Date: 2026-05-11 12:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_purchases"
down_revision: str | None = "0001_init"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # purchasing.purchases
    op.create_table(
        "purchases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("folio", sa.String(80), nullable=True, index=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supplier_name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="received"),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("payment_method", sa.String(40), nullable=False, server_default="efectivo"),
        sa.Column("payment_reference", sa.String(120), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        schema="purchasing",
    )
    op.create_index("ix_purchasing_purchases_status", "purchases", ["status"], schema="purchasing")
    op.create_index(
        "ix_purchasing_purchases_purchased_at", "purchases", ["purchased_at"], schema="purchasing"
    )

    # purchasing.purchase_items
    op.create_table(
        "purchase_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "purchase_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("purchasing.purchases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog.products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sku_proveedor", sa.String(80), nullable=True),
        sa.Column("sku_interno", sa.String(80), nullable=True),
        sa.Column("product_name", sa.String(300), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("factor_pack", sa.Integer, nullable=False, server_default="1"),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("tax_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema="purchasing",
    )
    op.create_index(
        "ix_purchasing_purchase_items_purchase_id",
        "purchase_items",
        ["purchase_id"],
        schema="purchasing",
    )
    op.create_index(
        "ix_purchasing_purchase_items_product_id",
        "purchase_items",
        ["product_id"],
        schema="purchasing",
    )


def downgrade() -> None:
    op.drop_table("purchase_items", schema="purchasing")
    op.drop_table("purchases", schema="purchasing")
