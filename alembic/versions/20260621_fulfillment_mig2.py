"""Fulfillment migration 2 — nullable package_id for manual kinds.

Revision ID: 20260621_fulfillment_mig2
Revises: 20260621_fulfillment_mig1
Create Date: 2026-06-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260621_fulfillment_mig2"
down_revision: Union[str, None] = "20260621_fulfillment_mig1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("store_products") as batch_op:
        batch_op.alter_column("package_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    # Dev-only: backfill NULL package_id before NOT NULL constraint.
    op.execute(
        "UPDATE store_products SET package_id = 1 WHERE package_id IS NULL"
    )
    with op.batch_alter_table("store_products") as batch_op:
        batch_op.alter_column("package_id", existing_type=sa.Integer(), nullable=False)