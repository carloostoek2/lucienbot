"""Sync missing schema columns from production (stub — already applied in production)

Revision ID: 202505070000
Revises: 73702d0a06be
Create Date: 2026-05-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '202505070000'
down_revision: Union[str, None] = '73702d0a06be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
