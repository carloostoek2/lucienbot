"""Add game_records table for minijuegos

Revision ID: c32861733e54
Revises: 756121049a4a
Create Date: 2026-04-06 11:19:22.778185

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c32861733e54'
down_revision: Union[str, None] = '756121049a4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create game_records table
    op.create_table('game_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('game_type', sa.String(length=20), nullable=False),
    sa.Column('result', sa.String(length=50), nullable=False),
    sa.Column('payout', sa.Integer(), nullable=True),
    sa.Column('played_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # Add indexes manually
    op.create_index('ix_game_records_id', 'game_records', ['id'])
    op.create_index('ix_game_records_user_id', 'game_records', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_game_records_user_id', table_name='game_records')
    op.drop_index('ix_game_records_id', table_name='game_records')
    op.drop_table('game_records')