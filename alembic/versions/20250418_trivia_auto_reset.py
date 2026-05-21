"""Add auto-reset for duration-based promotions (stub — already applied in production)

Revision ID: 20250418_trivia_auto_reset
Revises: 20250418_trivia_duration
Create Date: 2025-04-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20250418_trivia_auto_reset'
down_revision: Union[str, None] = '20250418_trivia_duration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
