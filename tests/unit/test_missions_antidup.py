"""Antiduplicados de misiones (PR-5a/5b): UNIQUE de progreso, cooldown real,
reloj único, claims en vuelo, backlog viejo y logros vs recompensas (G1–G9)."""

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from models.models import (
    BesitoTransaction,
    MissionFrequency,
    MissionType,
    Reward,
    RewardType,
    TransactionSource,
    UserMissionProgress,
    UserRewardHistory,
)
from services.besito_service import BesitoService
from services.mission_service import PENDING_DELIVERY_MAX_AGE, MissionService
from services.reward_service import (
    _DELIVERY_CLAIM_MARKER,
    _PACKAGE_SENDING_MARKER,
    RewardService,
)

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20261029_mission_progress_unique.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("mig_20261029", MIGRATION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mission_credits(db, uid):
    return (
        db.query(BesitoTransaction).filter_by(user_id=uid, source=TransactionSource.MISSION).count()
    )


def _mk_mission(service, reward_id, *, frequency=MissionFrequency.ONE_TIME, cooldown=None):
    mission = service.create_mission(
        name="AntiDup",
        description="x",
        mission_type=MissionType.REACTION_COUNT,
        target_value=1,
        frequency=frequency,
        reward_id=reward_id,
    )
    mission.cooldown_hours = cooldown
    service.db.commit()
    return mission


class TestMigrationDedupPure:
    def test_keeper_is_completed_then_max_value_then_min_id(self):
        mod = _load_migration()
        t0 = datetime(2026, 4, 6, 12, tzinfo=UTC)
        rows = [
            {
                "id": 5,
                "is_completed": False,
                "current_value": 9,
                "completed_at": None,
                "last_reference_id": None,
                "started_at": t0,
                "last_updated": t0,
            },
            {
                "id": 7,
                "is_completed": True,
                "current_value": 1,
                "completed_at": t0 + timedelta(hours=2),
                "last_reference_id": None,
                "started_at": t0 + timedelta(hours=1),
                "last_updated": t0 + timedelta(hours=2),
            },
            {
                "id": 6,
                "is_completed": True,
                "current_value": 1,
                "completed_at": t0 + timedelta(hours=1),
                "last_reference_id": 42,
                "started_at": t0 + timedelta(hours=1),
                "last_updated": t0 + timedelta(hours=3),
            },
        ]
        changes, deleted = mod.pick_keeper_and_merge(rows)
        assert changes["id"] == 6  # completada, mismo valor que 7, menor id
        assert sorted(deleted) == [5, 7]
        assert changes["completed_at"] == t0 + timedelta(hours=1)  # el más antiguo
        assert changes["last_reference_id"] == 42
        assert changes["started_at"] == t0

    def test_keeper_merges_reference_from_newest_row(self):
        mod = _load_migration()
        t0 = datetime(2026, 4, 6, tzinfo=UTC)
        rows = [
            {
                "id": 1,
                "is_completed": False,
                "current_value": 3,
                "completed_at": None,
                "last_reference_id": None,
                "started_at": t0,
                "last_updated": t0,
            },
            {
                "id": 2,
                "is_completed": False,
                "current_value": 1,
                "completed_at": None,
                "last_reference_id": 10,
                "started_at": t0,
                "last_updated": t0 + timedelta(minutes=1),
            },
            {
                "id": 3,
                "is_completed": False,
                "current_value": 1,
                "completed_at": None,
                "last_reference_id": 11,
                "started_at": t0,
                "last_updated": t0 + timedelta(minutes=2),
            },
        ]
        changes, deleted = mod.pick_keeper_and_merge(rows)
        assert changes["id"] == 1
        assert changes["last_reference_id"] == 11
        assert changes["completed_at"] is None
        assert deleted == [2, 3]


class TestProgressUniqueness:
    def test_duplicate_progress_row_violates_unique(self, db_session, sample_user, sample_mission):
        uid = sample_user.telegram_id
        db_session.add(
            UserMissionProgress(user_id=uid, mission_id=sample_mission.id, target_value=1)
        )
        db_session.commit()
        db_session.add(
            UserMissionProgress(user_id=uid, mission_id=sample_mission.id, target_value=1)
        )
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_race_safe_insert_returns_existing_row(self, db_session, sample_user, sample_mission):
        """Si otra transacción ya creó la fila, el insert choca y se relee la ganadora."""
        service = MissionService(db_session)
        uid = sample_user.telegram_id
        first = service.get_or_create_progress(uid, sample_mission.id)
        again = service._insert_progress_race_safe(uid, sample_mission, lock=True)
        assert again.id == first.id
        assert db_session.query(UserMissionProgress).filter_by(user_id=uid).count() == 1


class TestStaleCompletions:
    @pytest.mark.asyncio
    async def test_catch_up_expires_old_undelivered_completion(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        service = MissionService(db_session)
        mission = _mk_mission(service, sample_reward_besitos.id)
        uid = sample_user.telegram_id
        progress = service.set_progress(uid, mission.id, 1)
        progress.completed_at = datetime.now(UTC) - PENDING_DELIVERY_MAX_AGE - timedelta(hours=1)
        db_session.commit()

        assert service.get_users_with_pending_reward_deliveries() == []
        assert await service.deliver_pending_rewards(uid, bot=mock_bot) == 0
        assert _mission_credits(db_session, uid) == 0
        p = service.get_user_progress(uid, mission.id)
        assert p.is_completed is False and p.current_value == 0

    @pytest.mark.asyncio
    async def test_recent_undelivered_completion_is_still_paid_once(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        service = MissionService(db_session)
        mission = _mk_mission(service, sample_reward_besitos.id)
        uid = sample_user.telegram_id
        progress = service.set_progress(uid, mission.id, 1)
        progress.completed_at = datetime.now(UTC) - timedelta(hours=2)
        db_session.commit()

        assert await service.deliver_pending_rewards(uid, bot=mock_bot) == 1
        assert await service.deliver_pending_rewards(uid, bot=mock_bot) == 0
        assert _mission_credits(db_session, uid) == 1

    @pytest.mark.asyncio
    async def test_reactivation_expires_backlog_and_pays_nothing(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        """Reactivar no paga completaciones acumuladas mientras estuvo apagada (G8)."""
        service = MissionService(db_session)
        mission = _mk_mission(service, sample_reward_besitos.id)
        uid = sample_user.telegram_id
        service.update_mission(mission.id, is_active=False)
        service.set_progress(uid, mission.id, 1)  # completada sin entrega (recién)
        assert service.count_pending_completions(mission.id) == 1

        service.update_mission(mission.id, is_active=True)

        assert service.count_pending_completions(mission.id) == 0
        assert await service.deliver_pending_rewards(uid, bot=mock_bot) == 0
        assert _mission_credits(db_session, uid) == 0

    def test_inflight_vip_claim_is_not_expired(
        self, db_session, sample_user, sample_reward_besitos
    ):
        service = MissionService(db_session)
        mission = _mk_mission(service, sample_reward_besitos.id)
        uid = sample_user.telegram_id
        service.update_mission(mission.id, is_active=False)
        service.set_progress(uid, mission.id, 1)
        db_session.add(
            UserRewardHistory(
                user_id=uid,
                reward_id=sample_reward_besitos.id,
                mission_id=mission.id,
                details="token:99",
            )
        )
        db_session.commit()
        service.update_mission(mission.id, is_active=True)
        assert service.get_user_progress(uid, mission.id).is_completed is True


class TestInflightClaims:
    @pytest.mark.asyncio
    async def test_fresh_claim_older_than_old_ttl_still_blocks(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        """Un claim de 2 min (antes 'stale' con TTL 60 s) sigue en vuelo: no re-entrega."""
        service = MissionService(db_session)
        rs = RewardService(db_session)
        mission = _mk_mission(service, sample_reward_besitos.id)
        uid = sample_user.telegram_id
        progress = service.set_progress(uid, mission.id, 1)
        assert rs.try_claim_mission_delivery(
            uid,
            mission.id,
            sample_reward_besitos.id,
            since_completed_at=progress.completed_at,
            frequency=MissionFrequency.ONE_TIME,
        )
        claim = rs._get_mission_delivery_claim(uid, mission.id, sample_reward_besitos.id)
        claim.delivered_at = datetime.now(UTC) - timedelta(seconds=120)
        db_session.commit()

        assert await service.deliver_pending_rewards(uid, bot=mock_bot) == 0
        assert _mission_credits(db_session, uid) == 0

    @pytest.mark.asyncio
    async def test_package_resume_after_crash_does_not_resend(
        self, db_session, sample_user, sample_package, mock_bot
    ):
        reward = Reward(
            name="Pkg", reward_type=RewardType.PACKAGE, package_id=sample_package.id, is_active=True
        )
        db_session.add(reward)
        db_session.commit()
        service = MissionService(db_session)
        mission = _mk_mission(service, reward.id)
        uid = sample_user.telegram_id
        service.set_progress(uid, mission.id, 1)
        db_session.add(
            UserRewardHistory(
                user_id=uid,
                reward_id=reward.id,
                mission_id=mission.id,
                details=_PACKAGE_SENDING_MARKER,
            )
        )
        db_session.commit()
        claim = db_session.query(UserRewardHistory).filter_by(mission_id=mission.id).one()
        claim.delivered_at = datetime.now(UTC) - timedelta(hours=1)
        db_session.commit()

        with patch(
            "services.package_service.PackageService.deliver_package_to_user",
            new_callable=AsyncMock,
            return_value=(True, "ok"),
        ) as send:
            assert await service.deliver_pending_rewards(uid, bot=mock_bot) == 1
            send.assert_not_called()
        assert service.is_mission_reward_delivered(uid, mission.id)

    @pytest.mark.asyncio
    async def test_package_failure_releases_claim_for_retry(
        self, db_session, sample_user, sample_package, mock_bot
    ):
        reward = Reward(
            name="Pkg2",
            reward_type=RewardType.PACKAGE,
            package_id=sample_package.id,
            is_active=True,
        )
        db_session.add(reward)
        db_session.commit()
        service = MissionService(db_session)
        mission = _mk_mission(service, reward.id)
        uid = sample_user.telegram_id
        service.set_progress(uid, mission.id, 1)
        with patch(
            "services.package_service.PackageService.deliver_package_to_user",
            new_callable=AsyncMock,
            return_value=(False, "temporal"),
        ):
            assert await service.deliver_pending_rewards(uid, bot=mock_bot) == 0
        assert db_session.query(UserRewardHistory).filter_by(mission_id=mission.id).count() == 0


class TestAchievementVsMissionReference:
    @pytest.mark.asyncio
    async def test_story_credit_with_same_reference_does_not_block_mission(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        """G5: un logro (source=MISSION, ref=achievement.id) con el mismo id que el claim
        no debe hacer creer que la misión ya pagó."""
        service = MissionService(db_session)
        mission = _mk_mission(service, sample_reward_besitos.id)
        uid = sample_user.telegram_id
        service.set_progress(uid, mission.id, 1)
        next_claim_id = (db_session.query(UserRewardHistory.id).count() or 0) + 1
        BesitoService(db_session).credit_besitos(
            uid,
            3,
            TransactionSource.MISSION,
            description="Logro desbloqueado: Algo",
            reference_id=next_claim_id,
        )
        assert await service.deliver_pending_rewards(uid, bot=mock_bot) == 1
        credits = (
            db_session.query(BesitoTransaction)
            .filter(
                BesitoTransaction.user_id == uid, BesitoTransaction.description.like("Recompensa:%")
            )
            .count()
        )
        assert credits == 1

    def test_has_mission_credit_ignores_story_achievement_with_same_id(
        self, db_session, sample_user, sample_reward_besitos
    ):
        service = MissionService(db_session)
        rs = RewardService(db_session)
        mission = _mk_mission(service, sample_reward_besitos.id)
        uid = sample_user.telegram_id
        progress = service.set_progress(uid, mission.id, 1)
        assert rs.try_claim_mission_delivery(
            uid,
            mission.id,
            sample_reward_besitos.id,
            since_completed_at=progress.completed_at,
            frequency=MissionFrequency.ONE_TIME,
        )
        claim = rs._get_mission_delivery_claim(uid, mission.id, sample_reward_besitos.id)
        BesitoService(db_session).credit_besitos(
            uid,
            3,
            TransactionSource.MISSION,
            description="Logro desbloqueado: Algo",
            reference_id=claim.id,
        )
        assert (
            rs._has_mission_besitos_credit(uid, sample_reward_besitos.id, mission_id=mission.id)
            is False
        )


class TestLegacyIncrement:
    def test_duplicate_reference_checked_before_recurring_reset(
        self, db_session, sample_user, sample_reward_besitos
    ):
        """G7: el mismo reference_id no cuenta dos veces aunque la misión esté completada."""
        service = MissionService(db_session)
        mission = _mk_mission(service, None, frequency=MissionFrequency.RECURRING)
        uid = sample_user.telegram_id
        assert len(service.increment_progress(uid, MissionType.REACTION_COUNT, reference_id=1)) == 1
        assert service.increment_progress(uid, MissionType.REACTION_COUNT, reference_id=1) == []
        p = service.get_user_progress(uid, mission.id)
        assert p.is_completed is True and p.last_reference_id == 1

    @pytest.mark.asyncio
    async def test_recurring_with_pending_reward_is_not_reset(
        self, db_session, sample_user, sample_reward_besitos
    ):
        """G9: un ciclo completado sin entregar no se pierde con un nuevo incremento."""
        service = MissionService(db_session)
        mission = _mk_mission(
            service, sample_reward_besitos.id, frequency=MissionFrequency.RECURRING
        )
        uid = sample_user.telegram_id
        with patch("services.mission_service.resolve_delivery_bot", return_value=None):
            await service.increment_progress_and_deliver(
                uid, MissionType.REACTION_COUNT, reference_id=1
            )
            await service.increment_progress_and_deliver(
                uid, MissionType.REACTION_COUNT, reference_id=2
            )
        p = service.get_user_progress(uid, mission.id)
        assert p.is_completed is True and p.last_reference_id == 1


def test_delivery_claim_marker_constant_unchanged():
    assert _DELIVERY_CLAIM_MARKER == "__delivery_claim__"
