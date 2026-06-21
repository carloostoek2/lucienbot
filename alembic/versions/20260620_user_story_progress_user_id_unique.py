"""
Add unique constraint on user_story_progress.user_id.

Revision ID: 20260620_user_story_progress_unique
Revises: 20260617_trivia_besitos_caps
Create Date: 2026-06-20

Prevents concurrent first-insert races in advance_to_node from creating
duplicate progress rows (and double-debit) for the same Telegram user.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260620_user_story_progress_unique"
down_revision: Union[str, None] = "20260617_trivia_besitos_caps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove duplicate progress rows before adding the constraint (keep lowest id).
    op.execute(
        """
        DELETE FROM user_story_progress
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM user_story_progress
            GROUP BY user_id
        )
        """
    )
    # SQLite: ALTER CONSTRAINT not supported — use batch copy-and-move.
    with op.batch_alter_table("user_story_progress", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_user_story_progress_user_id",
            ["user_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("user_story_progress", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_user_story_progress_user_id",
            type_="unique",
        )