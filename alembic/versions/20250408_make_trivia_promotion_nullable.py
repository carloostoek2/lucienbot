"""Make trivia promotion nullable and add custom description

Revision ID: 20250408_trivia_independent
Revises: trivia_discount_system
Create Date: 2025-04-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250408_trivia_independent'
down_revision = 'trivia_discount_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make promotion_id nullable in trivia_promotion_configs
    op.alter_column(
        'trivia_promotion_configs',
        'promotion_id',
        existing_type=sa.Integer(),
        nullable=True
    )

    # Add custom_description column to trivia_promotion_configs
    op.add_column(
        'trivia_promotion_configs',
        sa.Column('custom_description', sa.String(500), nullable=True)
    )

    # Make promotion_id nullable in discount_codes
    op.alter_column(
        'discount_codes',
        'promotion_id',
        existing_type=sa.Integer(),
        nullable=True
    )


def downgrade() -> None:
    # Revert: make promotion_id NOT nullable in discount_codes
    op.alter_column(
        'discount_codes',
        'promotion_id',
        existing_type=sa.Integer(),
        nullable=False
    )

    # Remove custom_description column
    op.drop_column('trivia_promotion_configs', 'custom_description')

    # Revert: make promotion_id NOT nullable in trivia_promotion_configs
    op.alter_column(
        'trivia_promotion_configs',
        'promotion_id',
        existing_type=sa.Integer(),
        nullable=False
    )
