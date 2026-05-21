"""Add discount_percentage to discount_codes (stub — already applied in production)

Revision ID: 587b677147b4
Revises: c3d6143dc098
Create Date: 2026-05-04 12:05:36.633455
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '587b677147b4'
down_revision: Union[str, None] = 'c3d6143dc098'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
