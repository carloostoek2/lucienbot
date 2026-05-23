"""Add streak_sessions table and session_id FK

Revision ID: 20260523_streak_sessions_table
Revises: 20260523_streak_protection_enums
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260523_streak_sessions_table'
down_revision: Union[str, None] = '20260523_streak_protection_enums'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'streak_sessions',
        sa.Column('id', sa.Uuid(), primary_key=True, index=True),
        sa.Column('user_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('promotion_id', sa.Integer(), nullable=False),
        sa.Column('is_in_risk_mode', sa.Boolean(), default=False),
        sa.Column('protection_used', sa.Boolean(), default=False),
        sa.Column('codes_delivered', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    with op.batch_alter_table('streak_promotion_codes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('session_id', sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            'fk_streak_promotion_codes_session',
            'streak_sessions',
            ['session_id'], ['id']
        )


def downgrade() -> None:
    with op.batch_alter_table('streak_promotion_codes', schema=None) as batch_op:
        batch_op.drop_constraint('fk_streak_promotion_codes_session', type_='foreignkey')
        batch_op.drop_column('session_id')
    op.drop_table('streak_sessions')
