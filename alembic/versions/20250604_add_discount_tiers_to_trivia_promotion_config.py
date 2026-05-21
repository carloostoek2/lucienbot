"""Add tiered discount system (stub — already applied in production)

Revision ID: add_discount_tiers_to_trivia_promotion_config
Revises: merge_trivia_config_to_main
Create Date: 2025-06-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'add_discount_tiers_to_trivia_promotion_config'
down_revision: Union[str, Sequence[str], None] = 'merge_trivia_config_to_main'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
