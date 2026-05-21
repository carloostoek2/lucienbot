"""Merge old main chain (202505070001) with new main chain (20260510_add_trivia_config)

Revision ID: 20260521_merge_chains
Revises: 202505070001, 20260510_add_trivia_config
Create Date: 2026-05-21

Bridges the production DB (which has the old trivia migration chain applied
up to 202505070001) with the new main branch chain (which has a reworked
trivia system starting from 20260509_add_trivia_categories_table).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20260521_merge_chains'
down_revision: Union[str, Sequence[str], None] = ('202505070001', '20260510_add_trivia_config')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
