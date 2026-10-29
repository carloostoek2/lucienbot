"""Free inactivity reminder: users activity columns, feature_activations, conservative backfill

Revision ID: 20261029_free_inactivity_reminder
Revises: 20261029_streak_besitos
Create Date: 2026-10-29

- users += bot_started_at, last_activity_at, last_inactivity_reminder_at, bot_blocked_at.
- feature_activations(key PK, activated_at): cuándo se encendió el flag por primera vez.
- Índice para el job: users(last_activity_at) [PG: parcial WHERE bot_started_at IS NOT NULL
  AND bot_blocked_at IS NULL].
- Backfill CONSERVADOR de bot_started_at = created_at solo para usuarios con evidencia de
  haber usado el bot en privado (regalo diario, juegos, órdenes, transacciones que no son
  de reacción/admin/misión, o un token VIP canjeado). Los de solo join-request quedan NULL
  hasta su próximo /start. last_activity_at y last_inactivity_reminder_at quedan NULL: el
  job mide desde max(last_activity_at, activación del flag), así que nadie recibe nada
  antes de 3 días después de encender el flag.

Idempotente (columnas/tabla/índice solo si faltan; el backfill solo toca NULL).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261029_free_inactivity_reminder"
down_revision: str | None = "20261029_streak_besitos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_USER_COLUMNS = (
    "bot_started_at",
    "last_activity_at",
    "last_inactivity_reminder_at",
    "bot_blocked_at",
)
_INDEX = "ix_users_inactivity_candidates"

# Evidencia de uso del bot en chat privado (por telegram_id). Fuentes de besitos por NOMBRE.
_EVIDENCE = (
    ("daily_gift_claims", "SELECT user_id FROM daily_gift_claims"),
    ("game_records", "SELECT user_id FROM game_records"),
    ("orders", "SELECT user_id FROM orders"),
    (
        "besito_transactions",
        "SELECT user_id FROM besito_transactions WHERE source IN "
        "('DAILY_GIFT', 'GAME', 'TRIVIA', 'PURCHASE', 'STREAK_PROTECTION')",
    ),
    ("tokens", "SELECT redeemed_by_id FROM tokens WHERE redeemed_by_id IS NOT NULL"),
)


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indexes(table: str) -> set[str]:
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    missing = [c for c in _USER_COLUMNS if c not in _columns("users")]
    if missing:
        with op.batch_alter_table("users") as batch:
            for name in missing:
                batch.add_column(sa.Column(name, sa.DateTime(timezone=True), nullable=True))

    if "feature_activations" not in _tables():
        op.create_table(
            "feature_activations",
            sa.Column("key", sa.String(64), primary_key=True),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        )

    if _INDEX not in _indexes("users"):
        if is_pg:
            op.execute(
                f"CREATE INDEX IF NOT EXISTS {_INDEX} ON users (last_activity_at) "
                "WHERE bot_started_at IS NOT NULL AND bot_blocked_at IS NULL"
            )
        else:
            op.create_index(_INDEX, "users", ["last_activity_at"])

    tables = _tables()
    evidence = " UNION ".join(sql for table, sql in _EVIDENCE if table in tables)
    if evidence:
        bind.execute(
            sa.text(
                "UPDATE users SET bot_started_at = COALESCE(created_at, CURRENT_TIMESTAMP) "
                f"WHERE bot_started_at IS NULL AND telegram_id IN ({evidence})"  # nosec B608
            )
        )


def downgrade() -> None:
    if _INDEX in _indexes("users"):
        op.drop_index(_INDEX, table_name="users")
    if "feature_activations" in _tables():
        op.drop_table("feature_activations")
    present = [c for c in _USER_COLUMNS if c in _columns("users")]
    if present:
        with op.batch_alter_table("users") as batch:
            for name in present:
                batch.drop_column(name)
