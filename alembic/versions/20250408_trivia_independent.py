"""Add independent promotions support (stub — already applied in production)

Revision ID: 20250408_trivia_independent
Revises: 20250408_make_trivia_promotion_nullable
Create Date: 2025-04-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20250408_trivia_independent'
down_revision: Union[str, None] = '20250408_make_trivia_promotion_nullable'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
