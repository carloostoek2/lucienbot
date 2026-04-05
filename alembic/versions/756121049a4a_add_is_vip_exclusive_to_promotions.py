"""add is_vip_exclusive to promotions

Revision ID: 756121049a4a
Revises: 41d674ac4f9a
Create Date: 2026-04-05 15:01:19.653347

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '756121049a4a'
down_revision: Union[str, None] = '41d674ac4f9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Solo agregar la columna is_vip_exclusive a promotions
    op.add_column('promotions', sa.Column('is_vip_exclusive', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('promotions', 'is_vip_exclusive')