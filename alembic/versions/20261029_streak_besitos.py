"""Streak risk mode pays besitos: enum STREAK_REWARD, payout columns, trivia_config amounts

Revision ID: 20261029_streak_besitos
Revises: 20261029_mission_progress_unique
Create Date: 2026-10-29

- transactionsource += 'STREAK_REWARD' (PG guarda enums por NOMBRE, en mayúsculas).
- streak_sessions += retired_at, completed_at, payout_besitos, payout_paid_at (nullable).
- trivia_config += streak_retire_besitos (15), streak_complete_besitos (30), NOT NULL con
  server_default para que la fila existente quede con los valores aprobados.

Idempotente: cada columna se agrega solo si no existe (re-ejecución tras fallo parcial).
Downgrade: borra columnas; el valor del enum queda (PG no soporta DROP VALUE).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261029_streak_besitos"
down_revision: str | None = "20261029_mission_progress_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SESSION_COLUMNS = (
    ("retired_at", lambda: sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True)),
    (
        "completed_at",
        lambda: sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    ),
    ("payout_besitos", lambda: sa.Column("payout_besitos", sa.Integer(), nullable=True)),
    (
        "payout_paid_at",
        lambda: sa.Column("payout_paid_at", sa.DateTime(timezone=True), nullable=True),
    ),
)

_CONFIG_COLUMNS = (
    (
        "streak_retire_besitos",
        lambda: sa.Column(
            "streak_retire_besitos", sa.Integer(), nullable=False, server_default="15"
        ),
    ),
    (
        "streak_complete_besitos",
        lambda: sa.Column(
            "streak_complete_besitos", sa.Integer(), nullable=False, server_default="30"
        ),
    ),
)


def _existing_columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        op.execute("ALTER TYPE transactionsource ADD VALUE IF NOT EXISTS 'STREAK_REWARD'")

    for table, columns in (
        ("streak_sessions", _SESSION_COLUMNS),
        ("trivia_config", _CONFIG_COLUMNS),
    ):
        existing = _existing_columns(table)
        missing = [factory() for name, factory in columns if name not in existing]
        if missing:
            with op.batch_alter_table(table) as batch:
                for column in missing:
                    batch.add_column(column)


def downgrade() -> None:
    for table, columns in (
        ("trivia_config", _CONFIG_COLUMNS),
        ("streak_sessions", _SESSION_COLUMNS),
    ):
        existing = _existing_columns(table)
        present = [name for name, _ in columns if name in existing]
        if present:
            with op.batch_alter_table(table) as batch:
                for name in present:
                    batch.drop_column(name)
