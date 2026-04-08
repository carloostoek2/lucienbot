"""Add trivia discount system tables

Revision ID: trivia_discount_system
Revises: 20250407_add_game_and_anon_enum
Create Date: 2025-04-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'trivia_discount_system'
down_revision = '20250407_add_game_and_anon_enum'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type if not exists (PostgreSQL)
    # Note: SQLite doesn't support enum types, we use String instead

    # Create trivia_promotion_configs table
    op.create_table(
        'trivia_promotion_configs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('promotion_id', sa.Integer(), sa.ForeignKey('promotions.id'), nullable=False),
        sa.Column('discount_percentage', sa.Integer(), nullable=False),
        sa.Column('required_streak', sa.Integer(), default=5, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('max_codes', sa.Integer(), default=5),
        sa.Column('codes_claimed', sa.Integer(), default=0),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_trivia_promotion_configs_id', 'trivia_promotion_configs', ['id'])
    op.create_index('ix_trivia_promotion_configs_promotion_id', 'trivia_promotion_configs', ['promotion_id'])

    # Create discount_codes table
    op.create_table(
        'discount_codes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('config_id', sa.Integer(), sa.ForeignKey('trivia_promotion_configs.id'), nullable=False),
        sa.Column('code', sa.String(20), nullable=False, unique=True),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(100), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('promotion_id', sa.Integer(), sa.ForeignKey('promotions.id'), nullable=False),
        sa.Column('status', sa.String(20), default='active'),  # active, used, expired, cancelled
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_discount_codes_id', 'discount_codes', ['id'])
    op.create_index('ix_discount_codes_code', 'discount_codes', ['code'])
    op.create_index('ix_discount_codes_user_id', 'discount_codes', ['user_id'])
    op.create_index('ix_discount_codes_config_id', 'discount_codes', ['config_id'])

    # Add discount_code_id to game_records
    op.add_column('game_records',
        sa.Column('discount_code_id', sa.Integer(), sa.ForeignKey('discount_codes.id'), nullable=True)
    )


def downgrade() -> None:
    # Remove discount_code_id from game_records
    op.drop_column('game_records', 'discount_code_id')

    # Drop discount_codes table
    op.drop_index('ix_discount_codes_config_id', table_name='discount_codes')
    op.drop_index('ix_discount_codes_user_id', table_name='discount_codes')
    op.drop_index('ix_discount_codes_code', table_name='discount_codes')
    op.drop_index('ix_discount_codes_id', table_name='discount_codes')
    op.drop_table('discount_codes')

    # Drop trivia_promotion_configs table
    op.drop_index('ix_trivia_promotion_configs_promotion_id', table_name='trivia_promotion_configs')
    op.drop_index('ix_trivia_promotion_configs_id', table_name='trivia_promotion_configs')
    op.drop_table('trivia_promotion_configs')
