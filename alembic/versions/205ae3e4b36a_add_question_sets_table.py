"""Add question_sets table

Revision ID: 205ae3e4b36a
Revises: 20250418_trivia_auto_reset
Create Date: 2026-05-01 16:50:18.330684

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '205ae3e4b36a'
down_revision: Union[str, None] = '20250418_trivia_auto_reset'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('question_sets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False, unique=True),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=False),
        sa.Column('is_override', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.add_column('promotions', sa.Column('question_set_id', sa.Integer(), sa.ForeignKey('question_sets.id'), nullable=True))


def downgrade() -> None:
    op.drop_column('promotions', 'question_set_id')
    op.drop_table('question_sets')
