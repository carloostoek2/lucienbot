"""Add missing promotion_id FK on streak_sessions

Revision ID: 20260523_fix_streak_sessions_fk
Revises: 20260523_streak_sessions_table
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260523_fix_streak_sessions_fk'
down_revision: Union[str, None] = '20260523_streak_sessions_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Check if constraint already exists (avoids crash on re-run)
    cons = inspector.get_foreign_keys('streak_sessions')
    if any(c['name'] == 'fk_streak_sessions_promotion' for c in cons):
        return

    with op.batch_alter_table('streak_sessions', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_streak_sessions_promotion',
            'streak_promotions',
            ['promotion_id'], ['id']
        )


def downgrade() -> None:
    with op.batch_alter_table('streak_sessions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_streak_sessions_promotion', type_='foreignkey')
