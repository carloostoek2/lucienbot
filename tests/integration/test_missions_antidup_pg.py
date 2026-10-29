"""Antiduplicados de misiones sobre PostgreSQL REAL (SQLite no prueba FOR UPDATE,
índices parciales ni la migración).

Se salta si no hay ``LUCIEN_TEST_PG_URL``. **DESTRUCTIVO** sobre esa base: borra y
recrea el schema ``public``. Solo acepta hosts locales (localhost/127.0.0.1).

    LUCIEN_TEST_PG_URL=postgresql://postgres@localhost:54329/lucien_throwaway \
        pytest tests/integration/test_missions_antidup_pg.py --no-cov
"""

import asyncio
import os
import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

PG_URL = os.getenv("LUCIEN_TEST_PG_URL")
ROOT = Path(__file__).resolve().parents[2]
PREV_HEAD = "20260917_subscription_token_id_nullable"
THIS_REV = "20261029_mission_progress_unique"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not PG_URL, reason="LUCIEN_TEST_PG_URL no definido"),
]


def _alembic(*args: str) -> None:
    env = {**os.environ, "DATABASE_URL": PG_URL, "BOT_TOKEN": os.getenv("BOT_TOKEN", "x")}
    res = subprocess.run(
        [sys.executable, "-m", "alembic", *args], cwd=ROOT, env=env, capture_output=True, text=True
    )
    assert res.returncode == 0, res.stderr[-3000:]


@pytest.fixture(scope="module")
def pg_engine():
    url = make_url(PG_URL)
    assert url.host in ("localhost", "127.0.0.1"), "solo bases locales desechables"
    engine = sa.create_engine(PG_URL)
    with engine.begin() as conn:
        conn.execute(sa.text("DROP SCHEMA public CASCADE"))
        conn.execute(sa.text("CREATE SCHEMA public"))
        # Las revisiones de este repo superan los 32 chars por defecto de alembic.
        conn.execute(sa.text("CREATE TABLE alembic_version (version_num VARCHAR(255) PRIMARY KEY)"))
    _alembic("upgrade", PREV_HEAD)
    yield engine
    engine.dispose()


def _seed_duplicates(conn) -> dict:
    mid = conn.execute(
        sa.text(
            "INSERT INTO missions (name, mission_type, target_value, frequency, is_active) "
            "VALUES ('dup', 'REACTION_COUNT', 1, 'RECURRING', false) RETURNING id"
        )
    ).scalar()
    ins = sa.text(
        "INSERT INTO user_mission_progress (user_id, mission_id, current_value, target_value, "
        "is_completed, completed_at, last_reference_id) "
        "VALUES (:u, :m, :cv, 1, :done, :cat, :ref) RETURNING id"
    )
    ids = [
        conn.execute(
            ins, {"u": 1, "m": mid, "cv": 0, "done": False, "cat": None, "ref": None}
        ).scalar(),
        conn.execute(
            ins, {"u": 1, "m": mid, "cv": 1, "done": True, "cat": "2026-04-06 12:00+00", "ref": 7}
        ).scalar(),
        conn.execute(
            ins,
            {"u": 1, "m": mid, "cv": 1, "done": True, "cat": "2026-04-06 10:00+00", "ref": None},
        ).scalar(),
        conn.execute(
            ins, {"u": 2, "m": mid, "cv": 0, "done": False, "cat": None, "ref": None}
        ).scalar(),
    ]
    conn.execute(
        sa.text(
            "INSERT INTO besito_balances (user_id, balance, total_earned, "
            "total_spent) VALUES (1, 0, 0, 0)"
        )
    )
    tx = sa.text(
        "INSERT INTO besito_transactions (user_id, amount, type, source, description, "
        "reference_id) VALUES (1, :a, :t, 'MISSION', :d, 900)"
    )
    # Histórico de abril: crédito duplicado + DEBIT compensatorio del fix 2026-10-29.
    conn.execute(tx, {"a": 5, "t": "CREDIT", "d": "Recompensa: X"})
    conn.execute(tx, {"a": 5, "t": "CREDIT", "d": "Recompensa: X"})
    conn.execute(tx, {"a": -5, "t": "DEBIT", "d": "fix-2026-10-29 dup-mission ref=900"})
    return {"mission_id": mid, "ids": ids}


def _check_migration_dedups_and_creates_constraints(pg_engine):
    with pg_engine.begin() as conn:
        seed = _seed_duplicates(conn)

    _alembic("upgrade", "head")

    with pg_engine.begin() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT id, user_id, is_completed, completed_at, last_reference_id "
                "FROM user_mission_progress WHERE mission_id = :m ORDER BY user_id"
            ),
            {"m": seed["mission_id"]},
        ).fetchall()
        assert len(rows) == 2  # una por usuario
        keeper = rows[0]
        assert keeper.id == seed["ids"][1]  # completada, menor id entre completadas
        assert keeper.is_completed is True
        # completed_at fusionado = el más antiguo de las completadas (10:00 UTC)
        assert keeper.completed_at == datetime(2026, 4, 6, 10, tzinfo=UTC)
        assert keeper.last_reference_id == 7
        assert conn.execute(
            sa.text("SELECT 1 FROM pg_constraint WHERE conname='uq_user_mission_progress'")
        ).first()
        assert conn.execute(
            sa.text("SELECT 1 FROM pg_indexes WHERE indexname='uq_besito_tx_mission_reward_credit'")
        ).first()

    # Nuevo crédito duplicado de recompensa de misión: rechazado.
    tx = sa.text(
        "INSERT INTO besito_transactions (user_id, amount, type, source, description, "
        "reference_id) VALUES (1, :a, :t, 'MISSION', :d, 901)"
    )
    with pg_engine.begin() as conn:
        conn.execute(tx, {"a": 5, "t": "CREDIT", "d": "Recompensa: Y"})
    with pytest.raises(sa.exc.IntegrityError), pg_engine.begin() as conn:
        conn.execute(tx, {"a": 5, "t": "CREDIT", "d": "Recompensa: Y"})
    # DEBIT compensatorio y logro de historia con el mismo ref: permitidos.
    with pg_engine.begin() as conn:
        conn.execute(tx, {"a": -5, "t": "DEBIT", "d": "fix-2026-10-29 dup-mission ref=901"})
        conn.execute(tx, {"a": 3, "t": "CREDIT", "d": "Logro desbloqueado: Z"})

    # Progreso duplicado: rechazado.
    with pytest.raises(sa.exc.IntegrityError), pg_engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO user_mission_progress (user_id, mission_id, current_value, "
                "target_value) VALUES (2, :m, 0, 1)"
            ),
            {"m": seed["mission_id"]},
        )

    # Downgrade + upgrade otra vez: idempotente.
    _alembic("downgrade", PREV_HEAD)
    _alembic("upgrade", "head")
    _alembic("upgrade", "head")


def _check_concurrent_first_progress_creates_one_row_and_one_payout(pg_engine):
    """Dos hilos (sesiones separadas) incrementan a la vez el primer progreso."""
    _alembic("upgrade", "head")
    from models.models import (
        BesitoTransaction,
        Mission,
        MissionFrequency,
        MissionType,
        Reward,
        RewardType,
        TransactionSource,
        UserMissionProgress,
    )
    from services.mission_service import MissionService

    session_factory = sessionmaker(bind=pg_engine)
    with session_factory() as db:
        reward = Reward(name="R", reward_type=RewardType.BESITOS, besito_amount=5, is_active=True)
        db.add(reward)
        db.flush()
        mission = Mission(
            name="race",
            mission_type=MissionType.STORE_PURCHASE,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=reward.id,
            is_active=True,
        )
        db.add(mission)
        db.commit()
        mission_id = mission.id

    uid = 555
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def worker(ref: int) -> None:
        try:
            barrier.wait()
            with session_factory() as db:
                bot = AsyncMock()
                asyncio.run(
                    MissionService(db).increment_progress_and_deliver(
                        uid, MissionType.STORE_PURCHASE, bot=bot, reference_id=ref
                    )
                )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(r,)) for r in (1, 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not errors, errors

    with session_factory() as db:
        assert (
            db.query(UserMissionProgress).filter_by(user_id=uid, mission_id=mission_id).count() == 1
        )
        assert (
            db.query(BesitoTransaction)
            .filter_by(user_id=uid, source=TransactionSource.MISSION)
            .count()
            == 1
        )


def test_missions_antidup_on_postgres(pg_engine):
    """Un solo test (secuencial) para que xdist no reparta pasos que comparten la BD."""
    _check_migration_dedups_and_creates_constraints(pg_engine)
    _check_concurrent_first_progress_creates_one_row_and_one_payout(pg_engine)
