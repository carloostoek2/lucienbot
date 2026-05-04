"""Add discount_tiers to trivia_promotion_configs

Revision ID: add_discount_tiers_to_trivia_promotion_config
Revises: merge_trivia_config_to_main
Create Date: 2026-05-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_discount_tiers_to_trivia_promotion_config'
down_revision: Union[str, Sequence[str], None] = 'merge_trivia_config_to_main'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'trivia_promotion_configs',
        sa.Column('discount_tiers', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('trivia_promotion_configs', 'discount_tiers')