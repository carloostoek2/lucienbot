"""Add trivia_config table for editable trivia limits

Revision ID: add_trivia_config_table
Revises: trivia_discount_system
Create Date: 2026-05-03

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_trivia_config_table'
down_revision = 'ea7e3c03df29'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'trivia_config',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('daily_trivia_limit_free', sa.Integer(), default=7, nullable=False),
        sa.Column('daily_trivia_limit_vip', sa.Integer(), default=15, nullable=False),
        sa.Column('daily_trivia_vip_limit', sa.Integer(), default=5, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by', sa.BigInteger(), nullable=True),
    )
    op.execute(
        "INSERT INTO trivia_config (id, daily_trivia_limit_free, daily_trivia_limit_vip, "
        "daily_trivia_vip_limit, is_active) VALUES (1, 7, 15, 5, true)"
    )


def downgrade() -> None:
    op.drop_table('trivia_config')
