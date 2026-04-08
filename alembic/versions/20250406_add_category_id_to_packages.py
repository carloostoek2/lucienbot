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
    # Verificar si la tabla categories ya existe (idempotente)
    conn = op.get_bind()

    # SQLite usa sqlite_master, PostgreSQL usa information_schema
    dialect = conn.dialect.name
    if dialect == 'sqlite':
        result = conn.execute(sa.text("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='categories'
        """))
        table_exists = result.fetchone() is not None
    else:
        result = conn.execute(sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'categories'
            )
        """))
        table_exists = result.scalar()

    if not table_exists:
        op.create_table(
            'categories',
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

    # Verificar si la columna category_id ya existe en packages (idempotente)
    dialect = conn.dialect.name
    column_exists = False
    if dialect == 'sqlite':
        result = conn.execute(sa.text("PRAGMA table_info(packages)"))
        columns = [row[1] for row in result.fetchall()]
        column_exists = 'category_id' in columns
    else:
        result = conn.execute(sa.text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'packages' AND column_name = 'category_id'
            )
        """))
        column_exists = result.scalar()

    if not column_exists:
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