"""Sync anonymous_messages and broadcast_columns tables (stub — already applied in production)

Revision ID: 202505070001
Revises: 202505070000
Create Date: 2026-05-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '202505070001'
down_revision: Union[str, None] = '202505070000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
