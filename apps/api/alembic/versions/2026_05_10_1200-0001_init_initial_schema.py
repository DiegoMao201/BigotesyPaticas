"""Initial schema — auth + catalog + inventory + sales + crm + ops.

Revision ID: 0001_init
Revises:
Create Date: 2026-05-10 12:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SCHEMAS = [
    "catalog",
    "inventory",
    "sales",
    "purchasing",
    "crm",
    "finance",
    "auth",
    "ops",
    "analytics",
]


def upgrade() -> None:
    # Extensiones (idempotentes)
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")

    for schema in SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    # ---- auth.roles
    op.create_table(
        "roles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column(
            "permissions", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False
        ),
        sa.UniqueConstraint("name", name="uq_roles_name"),
        schema="auth",
    )

    # ---- auth.users
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_superadmin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
        schema="auth",
    )
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"], schema="auth")
    op.create_index("ix_users_email", "users", ["email"], schema="auth")

    # ---- auth.user_roles
    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        schema="auth",
    )

    # ---- catalog.brands
    op.create_table(
        "brands",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(140), nullable=False),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.UniqueConstraint("slug", name="uq_brands_slug"),
        schema="catalog",
    )
    op.create_index("ix_brands_slug", "brands", ["slug"], schema="catalog")

    # ---- catalog.categories
    op.create_table(
        "categories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog.categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
        schema="catalog",
    )
    op.create_index("ix_categories_slug", "categories", ["slug"], schema="catalog")
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"], schema="catalog")

    # ---- catalog.products
    op.create_table(
        "products",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(280), nullable=False),
        sa.Column("short_description", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "brand_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog.brands.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog.categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("cost", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("price", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("compare_at_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("margin_pct", sa.Numeric(5, 4), server_default="0.20", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("primary_image_url", sa.String(500), nullable=True),
        sa.Column("images", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("seo_title", sa.String(255), nullable=True),
        sa.Column("seo_description", sa.String(500), nullable=True),
        sa.Column("attributes", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("tags", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.UniqueConstraint("sku", name="uq_products_sku"),
        sa.UniqueConstraint("slug", name="uq_products_slug"),
        schema="catalog",
    )
    op.create_index("ix_products_sku", "products", ["sku"], schema="catalog")
    op.create_index("ix_products_slug", "products", ["slug"], schema="catalog")
    op.create_index("ix_products_brand_id", "products", ["brand_id"], schema="catalog")
    op.create_index("ix_products_category_id", "products", ["category_id"], schema="catalog")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_name_trgm ON catalog.products USING gin (name gin_trgm_ops)"
    )

    # ---- inventory.stock_locations
    op.create_table(
        "stock_locations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("is_default", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("code", name="uq_stock_locations_code"),
        schema="inventory",
    )

    # ---- inventory.stock
    op.create_table(
        "stock",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog.products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inventory.stock_locations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reserved", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reorder_point", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("product_id", "location_id", name="uq_stock_product_location"),
        sa.CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        sa.CheckConstraint("reserved >= 0", name="reserved_non_negative"),
        schema="inventory",
    )
    op.create_index("ix_stock_product_id", "stock", ["product_id"], schema="inventory")
    op.create_index("ix_stock_location_id", "stock", ["location_id"], schema="inventory")

    # ---- inventory.stock_movements
    op.create_table(
        "stock_movements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog.products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inventory.stock_locations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("movement_type", sa.String(20), nullable=False),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("quantity_after", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("reference_type", sa.String(40), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        schema="inventory",
    )
    op.create_index("ix_sm_product_id", "stock_movements", ["product_id"], schema="inventory")
    op.create_index("ix_sm_location_id", "stock_movements", ["location_id"], schema="inventory")
    op.create_index("ix_sm_movement_type", "stock_movements", ["movement_type"], schema="inventory")
    op.create_index(
        "ix_sm_reference", "stock_movements", ["reference_type", "reference_id"], schema="inventory"
    )
    op.create_index("ix_sm_occurred_at", "stock_movements", ["occurred_at"], schema="inventory")

    # ---- crm.customers
    op.create_table(
        "customers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("document_id", sa.String(40), nullable=True),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("rfm_segment", sa.String(20), nullable=True),
        sa.Column("rfm_recency_days", sa.Integer(), nullable=True),
        sa.Column("rfm_frequency", sa.Integer(), nullable=True),
        sa.Column("rfm_monetary", sa.Numeric(14, 2), nullable=True),
        sa.Column("last_purchase_at", sa.Date(), nullable=True),
        sa.Column("extra", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.UniqueConstraint("document_id", name="uq_customers_document_id"),
        schema="crm",
    )
    op.create_index("ix_customers_full_name", "customers", ["full_name"], schema="crm")
    op.create_index("ix_customers_email", "customers", ["email"], schema="crm")
    op.create_index("ix_customers_phone", "customers", ["phone"], schema="crm")

    # ---- sales.orders
    op.create_table(
        "orders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column("order_number", sa.String(40), nullable=False),
        sa.Column("channel", sa.String(30), server_default="POS_NEW", nullable=False),
        sa.Column("status", sa.String(30), server_default="confirmed", nullable=False),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crm.customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("subtotal", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("discount_total", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("tax_total", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("shipping_total", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("grand_total", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("paid_amount", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("balance_due", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("payment_status", sa.String(20), server_default="Pendiente", nullable=False),
        sa.Column("payment_method", sa.String(40), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.UniqueConstraint("order_number", name="uq_orders_order_number"),
        schema="sales",
    )
    op.create_index("ix_orders_order_number", "orders", ["order_number"], schema="sales")
    op.create_index("ix_orders_channel", "orders", ["channel"], schema="sales")
    op.create_index("ix_orders_status", "orders", ["status"], schema="sales")
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"], schema="sales")
    op.create_index("ix_orders_payment_status", "orders", ["payment_status"], schema="sales")
    op.create_index("ix_orders_occurred_at", "orders", ["occurred_at"], schema="sales")

    # ---- sales.order_items
    op.create_table(
        "order_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sales.orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("catalog.products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sku_snapshot", sa.String(64), nullable=False),
        sa.Column("name_snapshot", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("discount", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="quantity_positive"),
        schema="sales",
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"], schema="sales")
    op.create_index("ix_order_items_product_id", "order_items", ["product_id"], schema="sales")

    # ---- sales.payments
    op.create_table(
        "payments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sales.orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("method", sa.String(40), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference", sa.String(120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        schema="sales",
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"], schema="sales")
    op.create_index("ix_payments_received_at", "payments", ["received_at"], schema="sales")

    # ---- ops.legacy_id_map
    op.create_table(
        "legacy_id_map",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("entity", sa.String(40), nullable=False),
        sa.Column("legacy_id", sa.String(120), nullable=False),
        sa.Column("new_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extra", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.UniqueConstraint("entity", "legacy_id", name="uq_legacy_id_map_entity_legacy_id"),
        schema="ops",
    )
    op.create_index("ix_legacy_entity", "legacy_id_map", ["entity"], schema="ops")
    op.create_index("ix_legacy_legacy_id", "legacy_id_map", ["legacy_id"], schema="ops")
    op.create_index("ix_legacy_new_id", "legacy_id_map", ["new_id"], schema="ops")

    # ---- ops.audit_log
    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity", sa.String(60), nullable=False),
        sa.Column("entity_id", sa.String(120), nullable=True),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        schema="ops",
    )
    op.create_index("ix_audit_occurred_at", "audit_log", ["occurred_at"], schema="ops")
    op.create_index("ix_audit_actor", "audit_log", ["actor"], schema="ops")
    op.create_index("ix_audit_action", "audit_log", ["action"], schema="ops")
    op.create_index("ix_audit_entity", "audit_log", ["entity"], schema="ops")


def downgrade() -> None:
    op.drop_table("audit_log", schema="ops")
    op.drop_table("legacy_id_map", schema="ops")
    op.drop_table("payments", schema="sales")
    op.drop_table("order_items", schema="sales")
    op.drop_table("orders", schema="sales")
    op.drop_table("customers", schema="crm")
    op.drop_table("stock_movements", schema="inventory")
    op.drop_table("stock", schema="inventory")
    op.drop_table("stock_locations", schema="inventory")
    op.drop_table("products", schema="catalog")
    op.drop_table("categories", schema="catalog")
    op.drop_table("brands", schema="catalog")
    op.drop_table("user_roles", schema="auth")
    op.drop_table("users", schema="auth")
    op.drop_table("roles", schema="auth")
