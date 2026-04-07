"""Add trivia to transaction_source enum

Revision ID: 20250406_add_trivia_to_transaction_source
Revises: c32861733e54
Create Date: 2026-04-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20250406_add_trivia_to_transaction_source'
down_revision: Union[str, None] = 'c32861733e54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enum name constant
ENUM_NAME = 'transactionsource'
TABLE_NAME = 'besito_transactions'
COLUMN_NAME = 'source'

# Current enum values in the database (before this migration)
EXISTING_VALUES = [
    'REACTION',
    'DAILY_GIFT',
    'MISSION',
    'PURCHASE',
    'ADMIN',
    'ANONYMOUS_MESSAGE',
    'GAME'
]

# New value to add
NEW_VALUE = 'TRIVIA'


def upgrade() -> None:
    """Add TRIVIA value to transactionsource enum.

    PostgreSQL requires explicit ALTER TYPE for enum modifications.
    SQLite uses TEXT for enums natively, so no changes needed.
    """
    # Get database dialect
    dialect = op.get_context().dialect.name

    if dialect == 'postgresql':
        # PostgreSQL: Use ALTER TYPE to add new enum value
        # This is the proper way to extend enums in PostgreSQL
        op.execute(f"ALTER TYPE {ENUM_NAME} ADD VALUE IF NOT EXISTS '{NEW_VALUE}'")
    else:
        # SQLite: No action needed - enums are stored as TEXT
        # The application layer handles enum validation via SQLAlchemy
        pass


def downgrade() -> None:
    """Remove TRIVIA value from transactionsource enum.

    PostgreSQL does not support removing enum values directly.
    Requires recreating the enum (complex operation with data migration).
    SQLite: No action needed.
    """
    dialect = op.get_context().dialect.name

    if dialect == 'postgresql':
        # PostgreSQL does not support DROP VALUE for enums
        # To properly downgrade, we would need to:
        # 1. Create a new enum without TRIVIA
        # 2. Convert column to text/varchar
        # 3. Update any rows using TRIVIA to a valid value
        # 4. Drop old enum, rename new enum
        # 5. Convert column back to enum

        # Check if there are any rows using TRIVIA
        result = op.get_bind().execute(
            sa.text(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE {COLUMN_NAME} = '{NEW_VALUE}'")
        ).scalar()

        if result > 0:
            raise RuntimeError(
                f"Cannot downgrade: {result} transaction(s) exist with source='{NEW_VALUE}'. "
                f"Manual intervention required: update or delete these records first."
            )

        # Note: Even without data, PostgreSQL doesn't support DROP VALUE
        # This is a limitation of PostgreSQL enums
        # The enum will remain with TRIVIA as an allowed value
        pass
    else:
        # SQLite: No action needed
        pass
