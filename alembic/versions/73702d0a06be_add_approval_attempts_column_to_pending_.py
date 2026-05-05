"""Add approval_attempts column to pending_requests

Revision ID: 73702d0a06be
Revises: 587b677147b4
Create Date: 2026-05-04 20:13:49.873024

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '73702d0a06be'
down_revision: Union[str, None] = '587b677147b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'pending_requests',
        sa.Column('approval_attempts', sa.Integer(), server_default='0', nullable=False)
    )


def downgrade() -> None:
    op.drop_column('pending_requests', 'approval_attempts')
