"""Add CANCELLED to streakpromotioncodestatus and STREAK_PROTECTION to transactionsource enums

Revision ID: 20260523_streak_protection_enums
Revises: 20260521_merge_chains
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260523_streak_protection_enums'
down_revision: Union[str, None] = '20260521_merge_chains'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_context().dialect.name
    if dialect == 'postgresql':
        op.execute("ALTER TYPE streakpromotioncodestatus ADD VALUE IF NOT EXISTS 'CANCELLED'")
        op.execute("ALTER TYPE transactionsource ADD VALUE IF NOT EXISTS 'STREAK_PROTECTION'")


def downgrade() -> None:
    # PostgreSQL does not support DROP VALUE for enums
    pass
