"""Antiduplicados de misiones: dedup + UNIQUE(user_id, mission_id) en user_mission_progress.

Revision ID: 20261029_mission_progress_unique
Revises: 20260917_subscription_token_id_nullable
Create Date: 2026-10-29

Qué hace (en orden, dentro de la transacción de ``alembic upgrade head``):

1. **Limpieza determinista de duplicados** en ``user_mission_progress``. Por cada
   (user_id, mission_id) con más de una fila se conserva UNA fila ("keeper"):
   la completada si la hay, luego la de mayor ``current_value`` y, a igualdad,
   la de menor ``id``. Al keeper se le fusionan:
     - ``completed_at``: el MÁS ANTIGUO entre las filas completadas (conservador:
       hace que una entrega ya registrada cuente como hecha y no se vuelva a pagar);
     - ``last_reference_id``: el suyo o, si es NULL, el de la fila más reciente;
     - ``started_at``: el más antiguo.
   El resto se borra. ``user_reward_history`` no tiene FK a progress: no hay cascada.
2. ``UNIQUE (user_id, mission_id)`` con nombre ``uq_user_mission_progress``
   (idempotente por existencia; **sin tragar errores**: si falla, el deploy falla).
3. Índice único parcial en ``besito_transactions`` para créditos de recompensas de
   misión: ``(user_id, reference_id) WHERE source='MISSION' AND type='CREDIT'
   AND description LIKE 'Recompensa:%' AND id > <max(id) al migrar>``.
   - Solo ``CREDIT``: las filas compensatorias del fix 2026-10-29 son ``DEBIT`` con
     el mismo ``reference_id`` y no deben chocar.
   - ``id > cutoff``: el histórico de abril todavía tiene créditos duplicados
     (compensados con DEBIT, no borrados); el índice protege solo filas nuevas.
   - ``description LIKE 'Recompensa:%'``: excluye los logros de historia
     (``Logro desbloqueado: ...``), que también usan ``source=MISSION`` con
     ``reference_id=achievement.id`` (otro espacio de ids, hallazgo G5).
   Solo PostgreSQL (SQLite no lo necesita para tests).

Re-ejecutar es seguro: sin duplicados no borra nada y ambos objetos se crean solo
si no existen.
"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

logger = logging.getLogger("alembic.runtime.migration")

revision: str = "20261029_mission_progress_unique"
down_revision: str | None = "20260917_subscription_token_id_nullable"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UQ_NAME = "uq_user_mission_progress"
TX_INDEX_NAME = "uq_besito_tx_mission_reward_credit"


def _aware_key(value):
    """Orden estable para datetimes posiblemente None."""
    return (value is None, value)


def pick_keeper_and_merge(rows: list[dict]) -> tuple[dict, list[int]]:
    """Función pura: elige la fila a conservar y calcula los valores fusionados.

    ``rows`` son dicts con id, is_completed, current_value, completed_at,
    last_reference_id, started_at, last_updated. Retorna (cambios_del_keeper, ids_a_borrar).
    """
    ordered = sorted(
        rows,
        key=lambda r: (not bool(r["is_completed"]), -(r["current_value"] or 0), r["id"]),
    )
    keeper = ordered[0]
    others = ordered[1:]

    completed_ats = [r["completed_at"] for r in rows if r["is_completed"] and r["completed_at"]]
    completed_at = min(completed_ats) if completed_ats else keeper["completed_at"]

    last_ref = keeper["last_reference_id"]
    if last_ref is None:
        with_ref = [r for r in rows if r["last_reference_id"] is not None]
        if with_ref:
            newest = sorted(
                with_ref, key=lambda r: (_aware_key(r["last_updated"]), r["id"]), reverse=True
            )[0]
            last_ref = newest["last_reference_id"]

    started = [r["started_at"] for r in rows if r["started_at"] is not None]
    started_at = min(started) if started else keeper["started_at"]

    changes = {
        "id": keeper["id"],
        "completed_at": completed_at if keeper["is_completed"] else keeper["completed_at"],
        "last_reference_id": last_ref,
        "started_at": started_at,
    }
    return changes, [r["id"] for r in others]


def dedup_user_mission_progress(conn) -> tuple[int, int]:
    """Fusiona y borra duplicados. Retorna (grupos, filas_borradas)."""
    groups = conn.execute(
        sa.text(
            "SELECT user_id, mission_id FROM user_mission_progress "
            "GROUP BY user_id, mission_id HAVING COUNT(*) > 1 ORDER BY user_id, mission_id"
        )
    ).fetchall()
    deleted = 0
    for user_id, mission_id in groups:
        rows = [
            dict(r._mapping)
            for r in conn.execute(
                sa.text(
                    "SELECT id, is_completed, current_value, completed_at, last_reference_id, "
                    "started_at, last_updated FROM user_mission_progress "
                    "WHERE user_id = :u AND mission_id = :m ORDER BY id"
                ),
                {"u": user_id, "m": mission_id},
            )
        ]
        changes, to_delete = pick_keeper_and_merge(rows)
        conn.execute(
            sa.text(
                "UPDATE user_mission_progress SET completed_at = :completed_at, "
                "last_reference_id = :last_reference_id, started_at = :started_at WHERE id = :id"
            ),
            changes,
        )
        if to_delete:
            conn.execute(
                sa.text("DELETE FROM user_mission_progress WHERE id IN :ids").bindparams(
                    sa.bindparam("ids", expanding=True)
                ),
                {"ids": to_delete},
            )
            deleted += len(to_delete)
        logger.info(
            "user_mission_progress dedup | user_id=%s mission_id=%s keeper=%s deleted=%s",
            user_id,
            mission_id,
            changes["id"],
            to_delete,
        )
    return len(groups), deleted


def _pg_constraint_exists(conn, name: str) -> bool:
    return (
        conn.execute(
            sa.text(
                "SELECT 1 FROM pg_constraint WHERE conname = :n "
                "AND conrelid = 'user_mission_progress'::regclass"
            ),
            {"n": name},
        ).first()
        is not None
    )


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    groups, deleted = dedup_user_mission_progress(conn)
    logger.info("user_mission_progress dedup | groups=%s rows_deleted=%s", groups, deleted)

    if dialect == "postgresql":
        if not _pg_constraint_exists(conn, UQ_NAME):
            op.execute(
                sa.text(
                    f"ALTER TABLE user_mission_progress "
                    f"ADD CONSTRAINT {UQ_NAME} UNIQUE (user_id, mission_id)"
                )
            )
        if not _pg_constraint_exists(conn, UQ_NAME):  # verificación ruidosa
            raise RuntimeError(f"{UQ_NAME} no quedó creada")

        cutoff = conn.execute(
            sa.text("SELECT COALESCE(MAX(id), 0) FROM besito_transactions")
        ).scalar()
        op.execute(
            sa.text(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {TX_INDEX_NAME} "
                f"ON besito_transactions (user_id, reference_id) "
                f"WHERE source = 'MISSION' AND type = 'CREDIT' AND reference_id IS NOT NULL "
                f"AND description LIKE 'Recompensa:%' AND id > {int(cutoff)}"
            )
        )
        logger.info("%s ensured (id cutoff=%s)", TX_INDEX_NAME, cutoff)
    else:
        insp = sa.inspect(conn)
        names = {uc["name"] for uc in insp.get_unique_constraints("user_mission_progress")}
        if UQ_NAME not in names:
            with op.batch_alter_table("user_mission_progress") as batch_op:
                batch_op.create_unique_constraint(UQ_NAME, ["user_id", "mission_id"])


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute(sa.text(f"DROP INDEX IF EXISTS {TX_INDEX_NAME}"))
        op.execute(
            sa.text(f"ALTER TABLE user_mission_progress DROP CONSTRAINT IF EXISTS {UQ_NAME}")
        )
    else:
        insp = sa.inspect(conn)
        names = {uc["name"] for uc in insp.get_unique_constraints("user_mission_progress")}
        if UQ_NAME in names:
            with op.batch_alter_table("user_mission_progress") as batch_op:
                batch_op.drop_constraint(UQ_NAME, type_="unique")
