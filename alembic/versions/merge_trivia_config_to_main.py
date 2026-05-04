"""Merge trivia_config into main line

Revision ID: merge_trivia_config_to_main
Revises: add_qs_to_trivia_promotion_config, add_trivia_config_table
Create Date: 2026-05-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'merge_trivia_config_to_main'
down_revision: Union[str, Sequence[str], None] = ('add_qs_to_trivia_promotion_config', 'add_trivia_config_table')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
