"""Add relative duration support for promotions (stub — already applied in production)

Revision ID: 20250418_trivia_duration
Revises: 20250408_trivia_independent
Create Date: 2025-04-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20250418_trivia_duration'
down_revision: Union[str, None] = '20250408_trivia_independent'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
