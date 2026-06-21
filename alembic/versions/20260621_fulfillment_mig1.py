"""Fulfillment catalog migration 1 — tiers, fulfillments, product columns.

Revision ID: 20260621_fulfillment_mig1
Revises: 20260620_user_story_progress_unique
Create Date: 2026-06-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260621_fulfillment_mig1"
down_revision: Union[str, None] = "20260620_user_story_progress_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store_tiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("tagline", sa.Text(), nullable=True),
        sa.Column("price_min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_max", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("order_index", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_store_tiers_id", "store_tiers", ["id"])

    op.create_table(
        "order_fulfillments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_item_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column(
            "fulfillment_kind",
            sa.Enum(
                "package",
                "package_deferred",
                "user_input_manual",
                "early_access",
                "discount",
                "story_unlock",
                "vip_grant",
                "waitlist",
                "channel_honor",
                "scheduled_chat",
                name="fulfillmentkind",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending_input",
                "pending",
                "auto_running",
                "fulfilled",
                "failed",
                "cancelled",
                name="fulfillmentstatus",
            ),
            nullable=True,
        ),
        sa.Column("user_input", sa.Text(), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("fulfilled_by", sa.BigInteger(), nullable=True),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_result", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["store_products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_item_id", name="uq_order_fulfillment_order_item"),
    )
    op.create_index("ix_order_fulfillments_id", "order_fulfillments", ["id"])
    op.create_index("ix_order_fulfillments_user_id", "order_fulfillments", ["user_id"])

    op.create_table(
        "store_privileges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("order_fulfillment_id", sa.Integer(), nullable=False),
        sa.Column(
            "privilege_type",
            sa.Enum("early_access", "discount", name="privilegetype"),
            nullable=False,
        ),
        sa.Column("config", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["order_fulfillment_id"], ["order_fulfillments.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["store_products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_store_privileges_user_id", "store_privileges", ["user_id"])

    op.create_table(
        "store_waitlist_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("order_fulfillment_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum("active", "fulfilled", "expired", name="waitliststatus"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["order_fulfillment_id"], ["order_fulfillments.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["store_products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    deliverymode_enum = sa.Enum("auto", "manual", name="deliverymode")
    deliverymode_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "store_products",
        sa.Column(
            "delivery_mode",
            deliverymode_enum,
            nullable=False,
            server_default=sa.text("'auto'::deliverymode"),
        ),
    )
    op.add_column(
        "store_products",
        sa.Column(
            "fulfillment_kind",
            sa.Enum(
                "package",
                "package_deferred",
                "user_input_manual",
                "early_access",
                "discount",
                "story_unlock",
                "vip_grant",
                "waitlist",
                "channel_honor",
                "scheduled_chat",
                name="fulfillmentkind",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'package'::fulfillmentkind"),
        ),
    )

    with op.batch_alter_table("store_products") as batch_op:
        batch_op.add_column(sa.Column("tier_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("story_node_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("tariff_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("fulfillment_config", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("monthly_stock_cap", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"))
        batch_op.create_foreign_key("fk_store_products_tier", "store_tiers", ["tier_id"], ["id"])
        batch_op.create_foreign_key(
            "fk_store_products_story_node", "story_nodes", ["story_node_id"], ["id"]
        )
        batch_op.create_foreign_key("fk_store_products_tariff", "tariffs", ["tariff_id"], ["id"])

    op.execute(
        """
        INSERT INTO store_tiers (slug, name, tagline, price_min, price_max, order_index, is_active)
        VALUES
        ('impulso', 'IMPULSO', 'Vende curiosidad · Compra sin pensar', 50, 120, 1, true),
        ('deseo', 'DESEO', 'Vende acceso · El corazón del catálogo', 150, 350, 2, true),
        ('exclusivo', 'EXCLUSIVO', 'Vende completitud · Vale guardar para esto', 400, 700, 3, true),
        ('reservado', 'RESERVADO', 'Vende poder · Solo para los que llegaron lejos', 800, 1500, 4, true),
        ('mitico', 'MÍTICO', 'Vende leyenda · Stock limitado · Solo existe este mes', 2000, 5000, 5, true)
        """
    )


def downgrade() -> None:
    op.drop_column("store_products", "delivery_mode")
    op.drop_column("store_products", "fulfillment_kind")

    with op.batch_alter_table("store_products") as batch_op:
        batch_op.drop_constraint("fk_store_products_tariff", type_="foreignkey")
        batch_op.drop_constraint("fk_store_products_story_node", type_="foreignkey")
        batch_op.drop_constraint("fk_store_products_tier", type_="foreignkey")
        batch_op.drop_column("sort_order")
        batch_op.drop_column("monthly_stock_cap")
        batch_op.drop_column("fulfillment_config")
        batch_op.drop_column("tariff_id")
        batch_op.drop_column("story_node_id")
        batch_op.drop_column("tier_id")

    op.drop_table("store_waitlist_entries")
    op.drop_table("store_privileges")
    op.drop_index("ix_order_fulfillments_user_id", table_name="order_fulfillments")
    op.drop_index("ix_order_fulfillments_id", table_name="order_fulfillments")
    op.drop_table("order_fulfillments")
    op.drop_index("ix_store_tiers_id", table_name="store_tiers")
    op.drop_table("store_tiers")

    sa.Enum(name="deliverymode").drop(op.get_bind(), checkfirst=True)