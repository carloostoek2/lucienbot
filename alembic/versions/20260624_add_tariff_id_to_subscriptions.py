"""Add tariff_id (nullable) to subscriptions for direct Tariff association on internal grants.

This enables the relaxed convention:
- Manual distribution: still via Token (token_id required).
- Internal grants (missions, store VIP, admin forward, etc.): can associate directly to Tariff (tariff_id set, token_id may stay for audit/fallback or be omitted in future direct paths).

Revision ID: 20260624_add_tariff_id_to_subscriptions
Revises: 20260624_reinstate_broadcast_reaction_unique
Create Date: 2026-06-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260624_add_tariff_id_to_subscriptions"
down_revision: Union[str, None] = "20260624_reinstate_broadcast_reaction_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the column (nullable for back-compat with existing token-based subs)
    op.add_column(
        "subscriptions",
        sa.Column("tariff_id", sa.Integer(), nullable=True),
    )
    # Add FK (no cascade needed; tariff is reference data)
    op.create_foreign_key(
        "fk_subscriptions_tariff_id_tariffs",
        "subscriptions",
        "tariffs",
        ["tariff_id"],
        ["id"],
    )

    # Backfill from existing token->tariff for current rows (idempotent)
    # This ensures existing Subscriptions (all currently token-linked) get the tariff_id populated.
    op.execute(
        """
        UPDATE subscriptions
        SET tariff_id = tokens.tariff_id
        FROM tokens
        WHERE subscriptions.token_id = tokens.id
          AND subscriptions.tariff_id IS NULL
        """
    )


def downgrade() -> None:
    # Best-effort: we could null the column before drop, but SQLite/Postgres handle drop fine.
    op.drop_constraint(
        "fk_subscriptions_tariff_id_tariffs", "subscriptions", type_="foreignkey"
    )
    op.drop_column("subscriptions", "tariff_id")
