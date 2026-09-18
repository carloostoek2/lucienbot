"""Make subscriptions.token_id nullable for internal VIP grants.

Internal grants (grant_internal_vip_access) create Subscriptions with token_id=None
and tariff_id set. Manual token redeem still sets token_id.

Revision ID: 20260917_subscription_token_id_nullable
Revises: 20260815_business_connections
Create Date: 2026-09-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260917_subscription_token_id_nullable"
down_revision: Union[str, None] = "20260815_business_connections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite needs batch_alter_table to change nullability (recreates table).
    with op.batch_alter_table("subscriptions", schema=None) as batch_op:
        batch_op.alter_column(
            "token_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    conn = op.get_bind()
    # Downgrade cannot restore NOT NULL while null token_id rows exist.
    # Best-effort: leave nulls as-is is unsafe; require no nulls or fail loudly.
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM subscriptions WHERE token_id IS NULL")
    )
    null_count = result.scalar() or 0
    if null_count:
        raise RuntimeError(
            f"Cannot downgrade: {null_count} subscription(s) have token_id NULL. "
            "Backfill or delete those rows before downgrading."
        )
    with op.batch_alter_table("subscriptions", schema=None) as batch_op:
        batch_op.alter_column(
            "token_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
