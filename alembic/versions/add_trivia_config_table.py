"""Add trivia config table (stub — already applied in production)

Revision ID: add_trivia_config_table
Revises: trivia_discount_system
Create Date: 2025-04-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'add_trivia_config_table'
down_revision: Union[str, None] = 'trivia_discount_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
