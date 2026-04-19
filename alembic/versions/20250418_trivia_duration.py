"""Add duration_minutes and started_at to TriviaPromotionConfig

Revision ID: 20250418_trivia_duration
Revises: 20250408_trivia_independent
Create Date: 2025-04-18 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = '20250418_trivia_duration'
down_revision = '20250408_trivia_independent'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'trivia_promotion_configs',
        sa.Column('duration_minutes', sa.Integer(), nullable=True)
    )
    op.add_column(
        'trivia_promotion_configs',
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    # PostgreSQL doesn't support DROP COLUMN easily in all cases
    # But these nullable columns can be dropped
    op.drop_column('trivia_promotion_configs', 'started_at')
    op.drop_column('trivia_promotion_configs', 'duration_minutes')