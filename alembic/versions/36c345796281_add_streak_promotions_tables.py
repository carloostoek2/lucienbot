"""add streak promotions tables

Revision ID: 36c345796281
Revises: 20260509_add_trivia_categories
Create Date: 2026-05-10 02:25:32.331798

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36c345796281'
down_revision: Union[str, None] = '20260509_add_trivia_categories'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create streak_promotions, streak_promotion_levels, streak_promotion_codes, streak_promotion_redemptions."""
    op.create_table('streak_promotions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('duration_mode', sa.String(length=10), nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_hours', sa.Integer(), nullable=True),
        sa.Column('category_id', sa.String(length=50), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'ACTIVE', 'EXPIRED', 'PAUSED', name='streakpromotionstatus'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('include_general', sa.Boolean(), nullable=True),
        sa.Column('include_vip', sa.Boolean(), nullable=True),
        sa.Column('include_simple', sa.Boolean(), nullable=True),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('streak_promotions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_streak_promotions_id'), ['id'], unique=False)

    op.create_table('streak_promotion_levels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('promotion_id', sa.Integer(), nullable=False),
        sa.Column('consecutive_required', sa.Integer(), nullable=False),
        sa.Column('discount_pct', sa.Integer(), nullable=False),
        sa.Column('codes_available', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['promotion_id'], ['streak_promotions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('streak_promotion_levels', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_streak_promotion_levels_id'), ['id'], unique=False)

    op.create_table('streak_promotion_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('level_id', sa.Integer(), nullable=False),
        sa.Column('code_value', sa.String(length=50), nullable=False),
        sa.Column('status', sa.Enum('AVAILABLE', 'DELIVERED', 'USED', name='streakpromotioncodestatus'), nullable=True),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('used_by_admin', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['level_id'], ['streak_promotion_levels.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('streak_promotion_codes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_streak_promotion_codes_code_value'), ['code_value'], unique=True)
        batch_op.create_index(batch_op.f('ix_streak_promotion_codes_id'), ['id'], unique=False)

    op.create_table('streak_promotion_redemptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('level_id', sa.Integer(), nullable=False),
        sa.Column('code_id', sa.Integer(), nullable=False),
        sa.Column('streak_achieved', sa.Integer(), nullable=False),
        sa.Column('redeemed_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['code_id'], ['streak_promotion_codes.id'], ),
        sa.ForeignKeyConstraint(['level_id'], ['streak_promotion_levels.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'level_id', name='uq_streak_redemption_user_level')
    )
    with op.batch_alter_table('streak_promotion_redemptions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_streak_promotion_redemptions_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_streak_promotion_redemptions_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    """Drop streak_promotions, streak_promotion_levels, streak_promotion_codes, streak_promotion_redemptions."""
    with op.batch_alter_table('streak_promotion_redemptions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_streak_promotion_redemptions_user_id'))
        batch_op.drop_index(batch_op.f('ix_streak_promotion_redemptions_id'))

    op.drop_table('streak_promotion_redemptions')
    with op.batch_alter_table('streak_promotion_codes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_streak_promotion_codes_id'))
        batch_op.drop_index(batch_op.f('ix_streak_promotion_codes_code_value'))

    op.drop_table('streak_promotion_codes')
    with op.batch_alter_table('streak_promotion_levels', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_streak_promotion_levels_id'))

    op.drop_table('streak_promotion_levels')
    with op.batch_alter_table('streak_promotions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_streak_promotions_id'))

    op.drop_table('streak_promotions')
