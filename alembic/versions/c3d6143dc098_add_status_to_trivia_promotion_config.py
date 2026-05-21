"""Add status to trivia promotion config (stub — already applied in production)

Revision ID: c3d6143dc098
Revises: add_discount_tiers_to_trivia_promotion_config
Create Date: 2025-06-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c3d6143dc098'
down_revision: Union[str, None] = 'add_discount_tiers_to_trivia_promotion_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
