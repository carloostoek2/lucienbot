"""add_status_to_trivia_promotion_config

Revision ID: c3d6143dc098
Revises: add_discount_tiers_to_trivia_promotion_config
Create Date: 2026-05-04 10:56:41.280694

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d6143dc098'
down_revision: Union[str, None] = 'add_discount_tiers_to_trivia_promotion_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'trivia_promotion_configs',
        sa.Column('status', sa.String(20), server_default='active', nullable=False)
    )
    # Actualizar registros existentes con is_active=False a 'expired'
    op.execute("UPDATE trivia_promotion_configs SET status = 'expired' WHERE is_active = false")
    # Actualizar registros existentes con is_active=True a 'active'
    op.execute("UPDATE trivia_promotion_configs SET status = 'active' WHERE is_active = true")


def downgrade() -> None:
    with op.batch_alter_table('trivia_promotion_configs') as batch_op:
        batch_op.drop_column('status')
