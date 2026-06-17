"""
Add besitos earning caps (daily/weekly) to trivia_config and correct flag to game_records.

Revision ID: 20260617_trivia_besitos_caps
Revises: 20260613_add_nurture_sequences
Create Date: 2026-06-17

- Adds four configurable earning limits (not play counts) to TriviaConfig:
  trivia_besitos_daily_free/vip + weekly_free/vip
- Adds `correct` boolean to GameRecord so streak calculations can recognize
  correct answers even when payout==0 due to earning caps.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260617_trivia_besitos_caps"
down_revision: Union[str, None] = "20260613_add_nurture_sequences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add earning cap columns to trivia_config (with safe defaults)
    op.add_column(
        "trivia_config",
        sa.Column("trivia_besitos_daily_free", sa.Integer(), nullable=False, server_default="10"),
    )
    op.add_column(
        "trivia_config",
        sa.Column("trivia_besitos_daily_vip", sa.Integer(), nullable=False, server_default="15"),
    )
    op.add_column(
        "trivia_config",
        sa.Column("trivia_besitos_weekly_free", sa.Integer(), nullable=False, server_default="30"),
    )
    op.add_column(
        "trivia_config",
        sa.Column("trivia_besitos_weekly_vip", sa.Integer(), nullable=False, server_default="40"),
    )

    # Add correct flag to game_records (allows streak to survive 0-payout correct answers under caps)
    op.add_column(
        "game_records",
        sa.Column("correct", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    # Remove in reverse order
    op.drop_column("game_records", "correct")
    op.drop_column("trivia_config", "trivia_besitos_weekly_vip")
    op.drop_column("trivia_config", "trivia_besitos_weekly_free")
    op.drop_column("trivia_config", "trivia_besitos_daily_vip")
    op.drop_column("trivia_config", "trivia_besitos_daily_free")