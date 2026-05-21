"""Add trivia discount system tables (stub — already applied in production)

Revision ID: trivia_discount_system
Revises: 20250407_add_game_and_anon_enum
Create Date: 2025-04-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'trivia_discount_system'
down_revision: Union[str, None] = '20250407_add_game_and_anon_enum'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
