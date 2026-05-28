"""Add is_gift column to tokens table

Revision ID: 20260528_add_is_gift_to_tokens
Revises: 20260523_fix_streak_sessions_fk
Create Date: 2026-05-28

"""
from alembic import op
import sqlalchemy as sa

revision: str = "20260528_add_is_gift_to_tokens"
down_revision: str = "20260523_fix_streak_sessions_fk"
branch_labels: None = None
depends_on: None = None


def column_exists(table: str, column: str) -> bool:
    """Check if a column exists (cross-dialect)."""
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "sqlite":
        rows = bind.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
        return any(row[1] == column for row in rows)
    # PostgreSQL / others
    from sqlalchemy import inspect
    inspector = inspect(bind)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not column_exists("tokens", "is_gift"):
        op.add_column("tokens", sa.Column("is_gift", sa.Boolean(), nullable=True))
        op.execute("UPDATE tokens SET is_gift = FALSE")


def downgrade() -> None:
    if column_exists("tokens", "is_gift"):
        op.drop_column("tokens", "is_gift")
