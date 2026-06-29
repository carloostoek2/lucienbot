"""Add user_chat_id to pending_requests for join-request DM window.

Revision ID: 20260629_user_chat_id
Revises: 20260624_add_tariff_id_to_subscriptions
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260629_user_chat_id"
down_revision: str | Sequence[str] | None = "20260624_add_tariff_id_to_subscriptions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pending_requests",
        sa.Column("user_chat_id", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pending_requests", "user_chat_id")