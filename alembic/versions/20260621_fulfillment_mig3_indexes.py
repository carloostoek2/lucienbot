"""Fulfillment migration 3 — indexes on order_fulfillments.

Revision ID: 20260621_fulfillment_mig3
Revises: 20260621_fulfillment_mig2
Create Date: 2026-06-21
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260621_fulfillment_mig3"
down_revision: Union[str, None] = "20260621_fulfillment_mig2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_order_fulfillments_status", "order_fulfillments", ["status"])
    op.create_index(
        "ix_order_fulfillments_user_status", "order_fulfillments", ["user_id", "status"]
    )
    op.create_index(
        "ix_order_fulfillments_product_created",
        "order_fulfillments",
        ["product_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_order_fulfillments_product_created", table_name="order_fulfillments")
    op.drop_index("ix_order_fulfillments_user_status", table_name="order_fulfillments")
    op.drop_index("ix_order_fulfillments_status", table_name="order_fulfillments")