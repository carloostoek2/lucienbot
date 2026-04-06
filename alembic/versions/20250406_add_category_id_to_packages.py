"""
Add category_id to packages table and create categories table

Revision ID: 20250406_add_category_id_to_packages
Revises: 20250406_manual_file_count
Create Date: 2026-04-06

Esta migración:
1. Crea la tabla categories (si no existe)
2. Agrega columna category_id a packages (nullable)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250406_add_category_id_to_packages'
down_revision: Union[str, None] = '20250406_manual_file_count'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Crear tabla categories si no existe
    op.create_table('categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Agregar columna category_id a packages
    op.add_column('packages', sa.Column('category_id', sa.Integer(), nullable=True))
    op.create_index('ix_packages_category_id', 'packages', ['category_id'])

    # Agregar foreign key
    op.create_foreign_key('fk_packages_category_id', 'packages', 'categories',
                         ['category_id'], ['id'])


def downgrade() -> None:
    # Eliminar foreign key primero
    op.drop_constraint('fk_packages_category_id', 'packages', type_='foreignkey')

    # Eliminar índice en category_id
    op.drop_index('ix_packages_category_id', table_name='packages')

    # Eliminar columna category_id
    op.drop_column('packages', 'category_id')

    # Eliminar tabla categories
    op.drop_index('ix_categories_name', table_name='categories')
    op.drop_table('categories')