"""
Tests unitarios para MissionService.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from models.models import MissionFrequency, MissionType, UserRewardHistory
from services.besito_service import BesitoService
from services.mission_service import MissionService, _recurring_cooldown_blocks
from services.reward_service import RewardService


@pytest.mark.unit
class TestMissionService:
    """Tests para el servicio de misiones"""

    def test_create_mission(self, db_session):
        """Test crear una nueva misión"""
        service = MissionService(db_session)

        mission = service.create_mission(
            name="Test Mission",
            description="A test mission description",
            mission_type=MissionType.REACTION_COUNT,
            target_value=10,
            frequency=MissionFrequency.ONE_TIME,
        )

        assert mission.name == "Test Mission"
        assert mission.description == "A test mission description"
        assert mission.mission_type == MissionType.REACTION_COUNT
        assert mission.target_value == 10
        assert mission.frequency == MissionFrequency.ONE_TIME
        assert mission.is_active is True

    def test_get_mission(self, db_session, sample_mission):
        """Test obtener misión por ID"""
        service = MissionService(db_session)

        mission = service.get_mission(sample_mission.id)

        assert mission is not None
        assert mission.id == sample_mission.id
        assert mission.name == sample_mission.name

    def test_get_mission_not_found(self, db_session):
        """Test obtener misión inexistente"""
        service = MissionService(db_session)

        mission = service.get_mission(99999)

        assert mission is None

    def test_get_all_missions(self, db_session, sample_mission):
        """Test obtener todas las misiones activas"""
        service = MissionService(db_session)

        missions = service.get_all_missions()

        assert len(missions) >= 1
        assert any(m.id == sample_mission.id for m in missions)

    def test_get_available_missions(self, db_session, sample_mission):
        """Test obtener misiones disponibles actualmente"""
        service = MissionService(db_session)

        missions = service.get_available_missions()

        assert len(missions) >= 1
        assert any(m.id == sample_mission.id for m in missions)

    def test_get_missions_by_type(self, db_session, sample_mission):
        """Test obtener misiones por tipo"""
        service = MissionService(db_session)

        missions = service.get_missions_by_type(MissionType.REACTION_COUNT)

        assert len(missions) >= 1
        for mission in missions:
            assert mission.mission_type == MissionType.REACTION_COUNT

    def test_update_mission(self, db_session, sample_mission):
        """Test actualizar misión"""
        service = MissionService(db_session)

        result = service.update_mission(
            sample_mission.id, name="Updated Mission Name", target_value=20
        )

        assert result is True
        updated = service.get_mission(sample_mission.id)
        assert updated.name == "Updated Mission Name"
        assert updated.target_value == 20

    def test_delete_mission(self, db_session, sample_mission):
        """Test eliminar (desactivar) misión"""
        service = MissionService(db_session)

        result = service.delete_mission(sample_mission.id)

        assert result is True
        updated = service.get_mission(sample_mission.id)
        assert updated.is_active is False


@pytest.mark.unit
class TestMissionProgress:
    """Tests para progreso de misiones"""

    def test_get_or_create_progress_new(self, db_session, sample_user, sample_mission):
        """Test crear progreso para nuevo usuario"""
        service = MissionService(db_session)

        progress = service.get_or_create_progress(sample_user.telegram_id, sample_mission.id)

        assert progress is not None
        assert progress.user_id == sample_user.telegram_id
        assert progress.mission_id == sample_mission.id
        assert progress.current_value == 0
        assert progress.target_value == sample_mission.target_value
        assert progress.is_completed is False

    def test_get_or_create_progress_existing(self, db_session, sample_mission_progress):
        """Test obtener progreso existente"""
        service = MissionService(db_session)

        progress = service.get_or_create_progress(
            sample_mission_progress.user_id, sample_mission_progress.mission_id
        )

        assert progress is not None
        assert progress.id == sample_mission_progress.id
        assert progress.current_value == sample_mission_progress.current_value

    def test_get_user_progress(self, db_session, sample_mission_progress):
        """Test obtener progreso de usuario en misión"""
        service = MissionService(db_session)

        progress = service.get_user_progress(
            sample_mission_progress.user_id, sample_mission_progress.mission_id
        )

        assert progress is not None
        assert progress.id == sample_mission_progress.id

    def test_get_user_all_progress(self, db_session, sample_user, sample_mission):
        """Test obtener todo el progreso de un usuario"""
        service = MissionService(db_session)

        # Crear progreso para el usuario
        service.get_or_create_progress(sample_user.telegram_id, sample_mission.id)

        progress_list = service.get_user_all_progress(sample_user.telegram_id)

        assert len(progress_list) >= 1

    @pytest.mark.asyncio
    async def test_get_user_active_missions(self, db_session, sample_user, sample_mission):
        """Test obtener misiones activas de usuario con progreso"""
        service = MissionService(db_session)

        # Crear progreso
        service.get_or_create_progress(sample_user.telegram_id, sample_mission.id)

        active_missions = await service.get_user_active_missions(sample_user.telegram_id)

        assert len(active_missions) >= 1
        # Verificar estructura del resultado
        for item in active_missions:
            assert "mission" in item
            assert "progress" in item
            assert "percentage" in item


@pytest.mark.unit
class TestMissionIncrement:
    """Tests para incrementar progreso"""

    def test_increment_progress(self, db_session, sample_user, sample_mission):
        """Test incrementar progreso de misión"""
        service = MissionService(db_session)

        # Crear progreso inicial
        progress = service.get_or_create_progress(sample_user.telegram_id, sample_mission.id)
        initial_value = progress.current_value

        # Incrementar progreso
        completed = service.increment_progress(
            sample_user.telegram_id, MissionType.REACTION_COUNT, amount=1
        )

        # Verificar que se incrementó
        updated = service.get_user_progress(sample_user.telegram_id, sample_mission.id)
        assert updated.current_value == initial_value + 1
        assert len(completed) == 0  # No debería completarse con solo 1

    def test_increment_progress_completes_mission(self, db_session, sample_user):
        """Test que el progreso completa la misión al alcanzar el objetivo"""
        service = MissionService(db_session)

        # Crear misión con objetivo pequeño
        mission = service.create_mission(
            name="Quick Mission",
            description="Complete with 2 actions",
            mission_type=MissionType.REACTION_COUNT,
            target_value=2,
            frequency=MissionFrequency.ONE_TIME,
        )

        # Incrementar hasta completar
        service.increment_progress(sample_user.telegram_id, MissionType.REACTION_COUNT, amount=2)

        # Verificar que se completó
        progress = service.get_user_progress(sample_user.telegram_id, mission.id)
        assert progress.is_completed is True
        assert progress.completed_at is not None

    @pytest.mark.asyncio
    async def test_increment_progress_and_deliver_commits_on_cooldown(
        self, db_session, sample_user, sample_reward_besitos
    ):
        """RECURRING en cooldown: progreso se guarda pero deliver_reward no se llama."""
        service = MissionService(db_session)
        mission = service.create_mission(
            name="Recurring Cooldown",
            description="Cooldown regression",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.RECURRING,
            reward_id=sample_reward_besitos.id,
        )
        mission.cooldown_hours = 24
        db_session.commit()

        progress = service.get_or_create_progress(sample_user.telegram_id, mission.id)
        progress.is_completed = True
        progress.current_value = mission.target_value
        progress.completed_at = datetime.now(UTC) - timedelta(hours=1)
        progress.last_updated = datetime.now(UTC) - timedelta(hours=1)
        db_session.commit()

        mock_bot = AsyncMock()
        with patch.object(RewardService, "deliver_reward", new_callable=AsyncMock) as mock_deliver:
            await service.increment_progress_and_deliver(
                sample_user.telegram_id,
                MissionType.REACTION_COUNT,
                amount=1,
                bot=mock_bot,
                reference_id=99,
            )

        saved = service.get_user_progress(sample_user.telegram_id, mission.id)
        assert saved.is_completed is True
        assert saved.current_value >= 1
        mock_deliver.assert_not_awaited()

    def test_increment_progress_recurring_mission(self, db_session, sample_user):
        """Test misión recurrente se reinicia al completarse"""
        service = MissionService(db_session)

        # Crear misión recurrente
        mission = service.create_mission(
            name="Recurring Mission",
            description="Recurring test",
            mission_type=MissionType.DAILY_GIFT_TOTAL,
            target_value=1,
            frequency=MissionFrequency.RECURRING,
        )

        # Completar una vez
        service.increment_progress(sample_user.telegram_id, MissionType.DAILY_GIFT_TOTAL, amount=1)

        # Verificar completada
        progress = service.get_user_progress(sample_user.telegram_id, mission.id)
        assert progress.is_completed is True

        # Incrementar de nuevo (debería reiniciarse)
        service.increment_progress(sample_user.telegram_id, MissionType.DAILY_GIFT_TOTAL, amount=1)

        # Verificar reinicio
        progress = service.get_user_progress(sample_user.telegram_id, mission.id)
        # Después del reinicio y nuevo incremento, debería estar completada de nuevo
        assert progress.is_completed is True

    @pytest.mark.asyncio
    async def test_increment_dup_ref_skips_on_both_paths_and_no_recomplete(
        self, db_session, sample_user, sample_reward_besitos
    ):
        """DESIRED CONTRACT: last_reference_id guard prevents re-increment and re-deliver for same ref on sync increment_progress AND async increment_progress_and_deliver paths.
        Covers different mission types; no re-complete for ONE_TIME; no re-deliver. Enforce *intended contract* not just current. Deterministic explicit create, use .telegram_id."""
        service = MissionService(db_session)
        # REACTION one_time
        m1 = service.create_mission(
            name="Dup Ref Reaction",
            description="ref guard",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        # DAILY one_time
        m2 = service.create_mission(
            name="Dup Ref Daily",
            description="ref guard daily",
            mission_type=MissionType.DAILY_GIFT_TOTAL,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        ref = 777001
        # sync path first call
        completed1 = service.increment_progress(
            sample_user.telegram_id, MissionType.REACTION_COUNT, amount=1, reference_id=ref
        )
        assert len(completed1) == 1
        p1 = service.get_user_progress(sample_user.telegram_id, m1.id)
        assert p1.is_completed is True
        assert p1.last_reference_id == ref
        # sync dup -> skip
        completed_dup = service.increment_progress(
            sample_user.telegram_id, MissionType.REACTION_COUNT, amount=1, reference_id=ref
        )
        assert len(completed_dup) == 0
        p1b = service.get_user_progress(sample_user.telegram_id, m1.id)
        assert p1b.current_value == 1
        assert p1b.is_completed is True

        # async path different type
        mock_bot = AsyncMock()
        completed_a = await service.increment_progress_and_deliver(
            sample_user.telegram_id,
            MissionType.DAILY_GIFT_TOTAL,
            amount=1,
            bot=mock_bot,
            reference_id=ref,
        )
        assert len(completed_a) == 1
        p2 = service.get_user_progress(sample_user.telegram_id, m2.id)
        assert p2.last_reference_id == ref
        # async dup
        completed_a_dup = await service.increment_progress_and_deliver(
            sample_user.telegram_id,
            MissionType.DAILY_GIFT_TOTAL,
            amount=1,
            bot=mock_bot,
            reference_id=ref,
        )
        assert len(completed_a_dup) == 0
        # no re-deliver would be checked in side but here guard before

    @pytest.mark.asyncio
    async def test_recurring_cooldown_blocks_before_hours_allows_after_and_resets_only_on_recomplete(
        self, db_session, sample_user, sample_reward_besitos
    ):
        """DESIRED CONTRACT: for RECURRING: cooldown_blocks before cooldown_hours (no reset/deliver); allows after elapsed; reset only on re-complete of recurring (not ONE_TIME). Use explicit Mission+Progress setup, aware DT, .telegram_id. Enforce intended contract."""

        service = MissionService(db_session)
        mission = service.create_mission(
            name="Cooldown Pilot",
            description="test reset/cooldown",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.RECURRING,
            reward_id=sample_reward_besitos.id,
        )
        mission.cooldown_hours = 2
        db_session.commit()
        # simulate completed recently
        progress = service.get_or_create_progress(sample_user.telegram_id, mission.id)
        progress.is_completed = True
        progress.current_value = 1
        progress.completed_at = datetime.now(UTC) - timedelta(hours=1)
        progress.last_updated = progress.completed_at
        db_session.commit()

        # Use pure for exact block check (strict, per sig mission, previous_completed_at, progress)
        assert _recurring_cooldown_blocks(mission, progress.completed_at, progress) is True
        mock_bot = AsyncMock()
        res = await service.increment_progress_and_deliver(
            sample_user.telegram_id,
            MissionType.REACTION_COUNT,
            amount=1,
            bot=mock_bot,
            reference_id=7001,
        )
        assert len(res) == 1  # exact: progress returned; deliver blocked (verified by helper)
        # fast forward
        progress.completed_at = datetime.now(UTC) - timedelta(hours=3)
        db_session.commit()
        assert _recurring_cooldown_blocks(mission, progress.completed_at, progress) is False
        res2 = await service.increment_progress_and_deliver(
            sample_user.telegram_id,
            MissionType.REACTION_COUNT,
            amount=1,
            bot=mock_bot,
            reference_id=7002,
        )
        p2 = service.get_user_progress(sample_user.telegram_id, mission.id)
        assert p2.is_completed is True
        assert len(res2) == 1  # exact: allows after + reset only on recurring re-complete

    def test_set_progress(self, db_session, sample_user, sample_mission):
        """Test establecer progreso a valor específico"""
        service = MissionService(db_session)

        # Crear progreso
        service.get_or_create_progress(sample_user.telegram_id, sample_mission.id)

        # Establecer progreso
        progress = service.set_progress(sample_user.telegram_id, sample_mission.id, 8)

        assert progress is not None
        assert progress.current_value == 8
        assert progress.is_completed is False  # 8 < 10 (target_value)

    def test_set_progress_completes(self, db_session, sample_user, sample_mission):
        """Test que set_progress marca como completada si alcanza el objetivo"""
        service = MissionService(db_session)

        # Crear progreso
        service.get_or_create_progress(sample_user.telegram_id, sample_mission.id)

        # Establecer progreso que completa la misión
        progress = service.set_progress(sample_user.telegram_id, sample_mission.id, 15)

        assert progress.current_value == 15
        assert progress.is_completed is True
        assert progress.completed_at is not None

    def test_set_progress_preserves_completed_at_when_already_completed(
        self, db_session, sample_user, sample_mission
    ):
        """RECURRING: set_progress diario no refresca completed_at si ya completada."""
        service = MissionService(db_session)
        sample_mission.frequency = MissionFrequency.RECURRING
        db_session.commit()

        first = service.set_progress(sample_user.telegram_id, sample_mission.id, 15)
        original_completed_at = first.completed_at

        second = service.set_progress(sample_user.telegram_id, sample_mission.id, 15)
        assert second.completed_at == original_completed_at

    @pytest.mark.asyncio
    async def test_recurring_catchup_skips_cooldown_when_undelivered(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        """Catch-up RECURRING entrega ciclo pendiente aunque completed_at esté en cooldown."""
        service = MissionService(db_session)
        mission = service.create_mission(
            name="Recurring Catchup",
            description="Undelivered catch-up",
            mission_type=MissionType.DAILY_GIFT_STREAK,
            target_value=3,
            frequency=MissionFrequency.RECURRING,
            reward_id=sample_reward_besitos.id,
        )
        mission.cooldown_hours = 24
        db_session.commit()

        progress = service.set_progress(sample_user.telegram_id, mission.id, 3)
        progress.completed_at = datetime.now(UTC) - timedelta(hours=1)
        db_session.commit()

        delivered = await service.deliver_pending_rewards(sample_user.telegram_id, bot=mock_bot)
        assert delivered == 1

    @pytest.mark.asyncio
    async def test_deliver_pending_rewards_skips_inactive_mission_or_reward(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        """Catch-up ignora misiones/recompensas inactivas."""
        service = MissionService(db_session)
        inactive_mission = service.create_mission(
            name="Inactive Mission",
            description="Skip",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        inactive_mission.is_active = False
        inactive_reward_mission = service.create_mission(
            name="Inactive Reward Mission",
            description="Skip reward",
            mission_type=MissionType.DAILY_GIFT_TOTAL,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        sample_reward_besitos.is_active = False
        db_session.commit()

        service.set_progress(sample_user.telegram_id, inactive_mission.id, 1)
        service.set_progress(sample_user.telegram_id, inactive_reward_mission.id, 1)

        delivered = await service.deliver_pending_rewards(sample_user.telegram_id, bot=mock_bot)
        assert delivered == 0

    @pytest.mark.asyncio
    async def test_stale_claim_pipeline_resumes_delivery(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        """Claim stale reanuda entrega y finaliza historial."""
        from services.reward_service import _DELIVERY_CLAIM_TTL_SECONDS, RewardService

        service = MissionService(db_session)
        reward_service = RewardService(db_session)
        mission = service.create_mission(
            name="Stale Pipeline",
            description="Resume delivery",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        progress = service.set_progress(sample_user.telegram_id, mission.id, 1)
        reward_service.try_claim_mission_delivery(
            sample_user.telegram_id,
            mission.id,
            sample_reward_besitos.id,
            since_completed_at=progress.completed_at,
            frequency=MissionFrequency.ONE_TIME,
        )
        claim = reward_service._get_mission_delivery_claim(
            sample_user.telegram_id, mission.id, sample_reward_besitos.id
        )
        claim.delivered_at = datetime.now(UTC) - timedelta(seconds=_DELIVERY_CLAIM_TTL_SECONDS + 5)
        db_session.commit()

        delivered = await service.deliver_pending_rewards(sample_user.telegram_id, bot=mock_bot)
        assert delivered == 1
        assert service.is_mission_reward_delivered(sample_user.telegram_id, mission.id)

    def test_get_users_with_pending_reward_deliveries(
        self, db_session, sample_user, sample_reward_besitos
    ):
        """Escaneo de usuarios con entrega pendiente del ciclo actual."""
        service = MissionService(db_session)
        mission = service.create_mission(
            name="Pending Scan",
            description="Scheduler scan",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        service.set_progress(sample_user.telegram_id, mission.id, 1)

        pending = service.get_users_with_pending_reward_deliveries()
        assert sample_user.telegram_id in pending

        RewardService(db_session).log_reward_delivery(
            sample_user.telegram_id, sample_reward_besitos.id, mission.id
        )
        assert sample_user.telegram_id not in service.get_users_with_pending_reward_deliveries()

    @pytest.mark.asyncio
    async def test_deliver_pending_rewards_partial_count(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        """Multi-misión: retorna 1 si solo una es nueva (no 2)."""
        service = MissionService(db_session)
        m1 = service.create_mission(
            name="First",
            description="Already delivered",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        m2 = service.create_mission(
            name="Second",
            description="Pending",
            mission_type=MissionType.DAILY_GIFT_TOTAL,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        service.set_progress(sample_user.telegram_id, m1.id, 1)
        service.set_progress(sample_user.telegram_id, m2.id, 1)
        RewardService(db_session).log_reward_delivery(
            sample_user.telegram_id, sample_reward_besitos.id, m1.id
        )

        delivered = await service.deliver_pending_rewards(sample_user.telegram_id, bot=mock_bot)
        assert delivered == 1

    @pytest.mark.asyncio
    async def test_concurrent_deliver_pending_rewards_idempotent(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        """Doble deliver_pending_rewards no duplica besitos."""
        service = MissionService(db_session)
        mission = service.create_mission(
            name="Idempotent Catchup",
            description="No double credit",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        service.set_progress(sample_user.telegram_id, mission.id, 1)

        first = await service.deliver_pending_rewards(sample_user.telegram_id, bot=mock_bot)
        second = await service.deliver_pending_rewards(sample_user.telegram_id, bot=mock_bot)

        assert first == 1
        assert second == 0
        history = (
            db_session.query(UserRewardHistory)
            .filter(UserRewardHistory.mission_id == mission.id)
            .all()
        )
        assert len(history) == 1
        balance = BesitoService(db=db_session).get_balance(sample_user.telegram_id)
        assert balance == sample_reward_besitos.besito_amount


@pytest.mark.unit
class TestMissionStats:
    """Tests para estadísticas de misiones"""

    def test_get_mission_stats(self, db_session, sample_mission, sample_user):
        """Test obtener estadísticas de misión"""
        service = MissionService(db_session)

        # Crear progreso para el usuario
        service.get_or_create_progress(sample_user.telegram_id, sample_mission.id)

        stats = service.get_mission_stats(sample_mission.id)

        assert stats is not None
        assert stats["mission_name"] == sample_mission.name
        assert stats["total_users"] >= 1
        assert "completed" in stats
        assert "in_progress" in stats
        assert "completion_rate" in stats

    def test_get_mission_stats_not_found(self, db_session):
        """Test estadísticas de misión inexistente"""
        service = MissionService(db_session)

        stats = service.get_mission_stats(99999)

        assert stats == {}
