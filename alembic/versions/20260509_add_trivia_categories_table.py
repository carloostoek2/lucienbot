"""add_trivia_categories_table

Revision ID: 20260509_add_trivia_categories
Revises: 20250407_add_game_and_anon_enum
Create Date: 2026-05-09 18:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260509_add_trivia_categories'
down_revision: Union[str, None] = '20250407_add_game_and_anon_enum'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create trivia_categories table for thematic trivia category state."""
    op.create_table('trivia_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scheduled_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category_id')
    )
    op.create_index('ix_trivia_categories_id', 'trivia_categories', ['id'])
    op.create_index('ix_trivia_categories_category_id', 'trivia_categories', ['category_id'])


def downgrade() -> None:
    """Drop trivia_categories table."""
    op.drop_index('ix_trivia_categories_category_id', table_name='trivia_categories')
    op.drop_index('ix_trivia_categories_id', table_name='trivia_categories')
    op.drop_table('trivia_categories')
