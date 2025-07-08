"""Unified migration - Complete multi-tenant marketplace schema

Revision ID: 001_unified_migration
Revises:
Create Date: 2025-07-01 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_unified_migration"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for the multi-tenant marketplace."""
    import uuid

    # Drop all existing tables first (handles both fresh installs and migrations from old schema)
    # This ensures a clean slate for both development and production deployments
    connection = op.get_bind()

    # Drop tables if they exist (in reverse dependency order)
    tables_to_drop = [
        "second_hand_product_images",
        "cart_items",
        "second_hand_products",
        "carts",
        "products",
        "discounts",
        "users",
        "tenants",
    ]

    for table in tables_to_drop:
        try:
            connection.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        except Exception:
            pass  # Ignore errors if table doesn't exist

    # Drop enum types if they exist
    try:
        connection.execute(sa.text("DROP TYPE IF EXISTS cartstatus CASCADE"))
    except Exception:
        pass

    # Create tenants table first (required for foreign keys)
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("subdomain", sa.String(length=50), nullable=False),
        sa.Column("domain", sa.String(length=100), nullable=True),
        sa.Column("shopify_app_url", sa.String(length=200), nullable=True),
        sa.Column("shopify_api_key", sa.String(length=100), nullable=True),
        sa.Column("shopify_api_secret", sa.String(length=100), nullable=True),
        sa.Column("shopify_access_token", sa.String(length=200), nullable=True),
        sa.Column("shopify_webhook_secret", sa.String(length=100), nullable=True),
        sa.Column("shopify_scopes", sa.String(length=500), nullable=True),
        sa.Column("shopify_api_version", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("settings", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenants_id"), "tenants", ["id"], unique=True)
    op.create_index(op.f("ix_tenants_subdomain"), "tenants", ["subdomain"], unique=True)
    op.create_index(op.f("ix_tenants_domain"), "tenants", ["domain"], unique=False)

    # Create users table with UUID id and role support
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=200), nullable=False),
        sa.Column(
            "role", sa.String(length=20), nullable=False, server_default="client"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=True)
    op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"], unique=False)
    # Note: Username and email are unique per tenant, not globally

    # Create discounts table
    op.create_table(
        "discounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("discount_type", sa.String(length=20), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("min_purchase", sa.Float(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_discounts_id"), "discounts", ["id"], unique=False)
    op.create_index(
        op.f("ix_discounts_tenant_id"), "discounts", ["tenant_id"], unique=False
    )

    # Create products table
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_id"), "products", ["id"], unique=False)
    op.create_index(
        op.f("ix_products_tenant_id"), "products", ["tenant_id"], unique=False
    )

    # Create carts table
    op.create_table(
        "carts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "completed", "abandoned", name="cartstatus"),
            nullable=False,
        ),
        sa.Column("discount_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["discount_id"], ["discounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_carts_id"), "carts", ["id"], unique=False)
    op.create_index(op.f("ix_carts_tenant_id"), "carts", ["tenant_id"], unique=False)

    # Create cart_items table
    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cart_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cart_items_id"), "cart_items", ["id"], unique=False)

    # Create second_hand_products table
    op.create_table(
        "second_hand_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("condition", sa.String(length=20), nullable=False),
        sa.Column("original_sku", sa.String(length=100), nullable=False),
        sa.Column("barcode", sa.String(length=100), nullable=True),
        sa.Column("shopify_product_id", sa.String(length=50), nullable=True),
        # Weight fields
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("weight_unit", sa.String(length=20), nullable=True),
        # Size field
        sa.Column("size", sa.String(length=50), nullable=True),
        # Original product information fields
        sa.Column("original_title", sa.String(length=200), nullable=True),
        sa.Column("original_description", sa.Text(), nullable=True),
        sa.Column("original_product_type", sa.String(length=100), nullable=True),
        sa.Column("original_vendor", sa.String(length=100), nullable=True),
        # User and status fields
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("is_approved", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_second_hand_products_id"), "second_hand_products", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_second_hand_products_tenant_id"),
        "second_hand_products",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_second_hand_products_barcode"),
        "second_hand_products",
        ["barcode"],
        unique=False,
    )
    op.create_index(
        op.f("ix_second_hand_products_original_sku"),
        "second_hand_products",
        ["original_sku"],
        unique=False,
    )

    # Create second_hand_product_images table
    op.create_table(
        "second_hand_product_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["second_hand_products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_second_hand_product_images_id"),
        "second_hand_product_images",
        ["id"],
        unique=False,
    )

    # Create a default tenant (without hardcoded secrets)
    # Note: Shopify credentials should be set via environment variables or admin interface
    default_tenant_id = str(uuid.uuid4())
    op.execute(
        f"""
        INSERT INTO tenants (id, name, subdomain, is_active, created_at)
        VALUES ('{default_tenant_id}', 'Default Tenant', 'default', true, now())
        """
    )


def downgrade() -> None:
    """Drop all tables."""
    # Drop tables in reverse order of creation to handle foreign key constraints
    op.drop_index(
        op.f("ix_second_hand_product_images_id"),
        table_name="second_hand_product_images",
    )
    op.drop_table("second_hand_product_images")

    op.drop_index(
        op.f("ix_second_hand_products_original_sku"), table_name="second_hand_products"
    )
    op.drop_index(
        op.f("ix_second_hand_products_barcode"), table_name="second_hand_products"
    )
    op.drop_index(
        op.f("ix_second_hand_products_tenant_id"), table_name="second_hand_products"
    )
    op.drop_index(op.f("ix_second_hand_products_id"), table_name="second_hand_products")
    op.drop_table("second_hand_products")

    op.drop_index(op.f("ix_cart_items_id"), table_name="cart_items")
    op.drop_table("cart_items")

    op.drop_index(op.f("ix_carts_tenant_id"), table_name="carts")
    op.drop_index(op.f("ix_carts_id"), table_name="carts")
    op.drop_table("carts")

    op.drop_index(op.f("ix_products_tenant_id"), table_name="products")
    op.drop_index(op.f("ix_products_id"), table_name="products")
    op.drop_table("products")

    op.drop_index(op.f("ix_discounts_tenant_id"), table_name="discounts")
    op.drop_index(op.f("ix_discounts_id"), table_name="discounts")
    op.drop_table("discounts")

    op.drop_index(op.f("ix_users_tenant_id"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_tenants_domain"), table_name="tenants")
    op.drop_index(op.f("ix_tenants_subdomain"), table_name="tenants")
    op.drop_index(op.f("ix_tenants_id"), table_name="tenants")
    op.drop_table("tenants")

    # Drop enum types
    sa.Enum(name="cartstatus").drop(op.get_bind())
