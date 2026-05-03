"""Add question_set_id to trivia_promotion_configs

Revision ID: add_qs_to_trivia_promotion_config
Revises: 205ae3e4b36a
Create Date: 2026-05-03 20:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_qs_to_trivia_promotion_config'
down_revision: Union[str, None] = '205ae3e4b36a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'trivia_promotion_configs',
        sa.Column('question_set_id', sa.Integer(), sa.ForeignKey('question_sets.id'), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('trivia_promotion_configs', 'question_set_id')