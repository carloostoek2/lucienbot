"""Add question_set_id to trivia_promotion_configs (stub — already applied in production)

Revision ID: add_qs_to_trivia_promotion_config
Revises: 205ae3e4b36a
Create Date: 2025-06-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'add_qs_to_trivia_promotion_config'
down_revision: Union[str, None] = '205ae3e4b36a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
