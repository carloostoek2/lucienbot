"""add trivia_config table

Revision ID: 20260510_add_trivia_config
Revises: 36c345796281
Create Date: 2026-05-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260510_add_trivia_config'
down_revision: Union[str, None] = '36c345796281'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create trivia_config table for configurable game limits."""
    op.create_table('trivia_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dice_limit_free', sa.Integer(), nullable=False, server_default=sa.text('10')),
        sa.Column('dice_limit_vip', sa.Integer(), nullable=False, server_default=sa.text('20')),
        sa.Column('trivia_limit_free', sa.Integer(), nullable=False, server_default=sa.text('5')),
        sa.Column('trivia_limit_vip', sa.Integer(), nullable=False, server_default=sa.text('10')),
        sa.Column('trivia_vip_limit', sa.Integer(), nullable=False, server_default=sa.text('5')),
        sa.Column('trivia_simple_limit_free', sa.Integer(), nullable=False, server_default=sa.text('5')),
        sa.Column('trivia_simple_limit_vip', sa.Integer(), nullable=False, server_default=sa.text('10')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trivia_config_id', 'trivia_config', ['id'])


def downgrade() -> None:
    """Drop trivia_config table."""
    op.drop_index('ix_trivia_config_id', table_name='trivia_config')
    op.drop_table('trivia_config')
