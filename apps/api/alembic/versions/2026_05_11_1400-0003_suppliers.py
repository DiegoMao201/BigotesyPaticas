"""Add purchasing.suppliers and purchasing.supplier_sku_map.

Revision ID: 0003_suppliers
Revises: 0002_purchases
Create Date: 2026-05-11 14:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_suppliers"
down_revision: str | None = "0002_purchases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("nit", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("contact_name", sa.String(200), nullable=True),
        sa.Column("payment_terms_days", sa.Integer, nullable=False, server_default="0"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint("nit", name="uq_suppliers_nit"),
        schema="purchasing",
    )
    op.create_index("ix_suppliers_name", "suppliers", ["name"], schema="purchasing")
    op.create_index("ix_suppliers_nit", "suppliers", ["nit"], schema="purchasing")

    op.create_table(
        "supplier_sku_map",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("purchasing.suppliers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sku_proveedor", sa.String(80), nullable=False),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog.products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("factor_pack", sa.Integer, nullable=False, server_default="1"),
        sa.Column("last_unit_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("last_tax_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("supplier_id", "sku_proveedor", name="uq_supplier_sku"),
        schema="purchasing",
    )
    op.create_index(
        "ix_supplier_sku_map_sku", "supplier_sku_map", ["sku_proveedor"], schema="purchasing"
    )


def downgrade() -> None:
    op.drop_index("ix_supplier_sku_map_sku", table_name="supplier_sku_map", schema="purchasing")
    op.drop_table("supplier_sku_map", schema="purchasing")
    op.drop_index("ix_suppliers_nit", table_name="suppliers", schema="purchasing")
    op.drop_index("ix_suppliers_name", table_name="suppliers", schema="purchasing")
    op.drop_table("suppliers", schema="purchasing")
