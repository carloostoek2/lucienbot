"""add unique constraint to broadcast_reactions

Revision ID: f7d08ca1ce1a
Revises: ea7e3c03df29
Create Date: 2026-04-06 22:53:28.088400

"""
from typing import Sequence, Union

from alembic import op, context
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7d08ca1ce1a'
down_revision: Union[str, None] = 'ea7e3c03df29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL: clean duplicates and add unique constraint
    # SQLite: base schema handles the table structure differently
    if context.get_context().dialect.name != 'sqlite':
        # Primero eliminar reacciones duplicadas, manteniendo solo la más reciente
        # para cada combinación de broadcast_id + user_id
        op.execute("""
            DELETE FROM broadcast_reactions
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM broadcast_reactions
                GROUP BY broadcast_id, user_id
            )
        """)

        # Agregar constraint único para prevenir reacciones duplicadas
        # Un usuario solo puede reaccionar una vez por mensaje de broadcast
        with op.batch_alter_table('broadcast_reactions', schema=None) as batch_op:
            batch_op.create_unique_constraint('uq_broadcast_user_reaction', ['broadcast_id', 'user_id'])
    # SQLite: pass (no-op, base schema and subsequent migrations handle table)


def downgrade() -> None:
    # Eliminar constraint único de reacciones
    if context.get_context().dialect.name != 'sqlite':
        with op.batch_alter_table('broadcast_reactions', schema=None) as batch_op:
            batch_op.drop_constraint('uq_broadcast_user_reaction', type_='unique')
    # SQLite: pass
