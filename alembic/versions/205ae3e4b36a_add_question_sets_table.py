"""Add question_sets table (stub — already applied in production)

Revision ID: 205ae3e4b36a
Revises: 20250418_trivia_auto_reset
Create Date: 2025-04-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '205ae3e4b36a'
down_revision: Union[str, None] = '20250418_trivia_auto_reset'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
