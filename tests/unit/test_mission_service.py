"""
Tests unitarios para MissionService.
"""
import pytest
from datetime import datetime, timedelta

from services.mission_service import MissionService
from models.models import MissionType, MissionFrequency, UserMissionProgress


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
            frequency=MissionFrequency.ONE_TIME
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

        missions = service.get_missions_by_type(MissionType.SEND_BESITOS)

        assert len(missions) >= 1
        for mission in missions:
            assert mission.mission_type == MissionType.SEND_BESITOS

    def test_update_mission(self, db_session, sample_mission):
        """Test actualizar misión"""
        service = MissionService(db_session)

        result = service.update_mission(
            sample_mission.id,
            name="Updated Mission Name",
            target_value=20
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

        progress = service.get_or_create_progress(sample_user.id, sample_mission.id)

        assert progress is not None
        assert progress.user_id == sample_user.id
        assert progress.mission_id == sample_mission.id
        assert progress.current_value == 0
        assert progress.target_value == sample_mission.target_value
        assert progress.is_completed is False

    def test_get_or_create_progress_existing(self, db_session, sample_mission_progress):
        """Test obtener progreso existente"""
        service = MissionService(db_session)

        progress = service.get_or_create_progress(
            sample_mission_progress.user_id,
            sample_mission_progress.mission_id
        )

        assert progress is not None
        assert progress.id == sample_mission_progress.id
        assert progress.current_value == sample_mission_progress.current_value

    def test_get_user_progress(self, db_session, sample_mission_progress):
        """Test obtener progreso de usuario en misión"""
        service = MissionService(db_session)

        progress = service.get_user_progress(
            sample_mission_progress.user_id,
            sample_mission_progress.mission_id
        )

        assert progress is not None
        assert progress.id == sample_mission_progress.id

    def test_get_user_all_progress(self, db_session, sample_user, sample_mission):
        """Test obtener todo el progreso de un usuario"""
        service = MissionService(db_session)

        # Crear progreso para el usuario
        service.get_or_create_progress(sample_user.id, sample_mission.id)

        progress_list = service.get_user_all_progress(sample_user.id)

        assert len(progress_list) >= 1

    def test_get_user_active_missions(self, db_session, sample_user, sample_mission):
        """Test obtener misiones activas de usuario con progreso"""
        service = MissionService(db_session)

        # Crear progreso
        service.get_or_create_progress(sample_user.id, sample_mission.id)

        active_missions = service.get_user_active_missions(sample_user.id)

        assert len(active_missions) >= 1
        # Verificar estructura del resultado
        for item in active_missions:
            assert 'mission' in item
            assert 'progress' in item
            assert 'percentage' in item


@pytest.mark.unit
class TestMissionIncrement:
    """Tests para incrementar progreso"""

    def test_increment_progress(self, db_session, sample_user, sample_mission):
        """Test incrementar progreso de misión"""
        service = MissionService(db_session)

        # Crear progreso inicial
        progress = service.get_or_create_progress(sample_user.id, sample_mission.id)
        initial_value = progress.current_value

        # Incrementar progreso
        completed = service.increment_progress(
            sample_user.id,
            MissionType.SEND_BESITOS,
            amount=1
        )

        # Verificar que se incrementó
        updated = service.get_user_progress(sample_user.id, sample_mission.id)
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
            frequency=MissionFrequency.ONE_TIME
        )

        # Incrementar hasta completar
        service.increment_progress(sample_user.id, MissionType.REACTION_COUNT, amount=2)

        # Verificar que se completó
        progress = service.get_user_progress(sample_user.id, mission.id)
        assert progress.is_completed is True
        assert progress.completed_at is not None

    def test_increment_progress_recurring_mission(self, db_session, sample_user):
        """Test misión recurrente se reinicia al completarse"""
        service = MissionService(db_session)

        # Crear misión recurrente
        mission = service.create_mission(
            name="Recurring Mission",
            description="Recurring test",
            mission_type=MissionType.DAILY_GIFT_TOTAL,
            target_value=1,
            frequency=MissionFrequency.RECURRING
        )

        # Completar una vez
        service.increment_progress(sample_user.id, MissionType.DAILY_GIFT_TOTAL, amount=1)

        # Verificar completada
        progress = service.get_user_progress(sample_user.id, mission.id)
        assert progress.is_completed is True

        # Incrementar de nuevo (debería reiniciarse)
        service.increment_progress(sample_user.id, MissionType.DAILY_GIFT_TOTAL, amount=1)

        # Verificar reinicio
        progress = service.get_user_progress(sample_user.id, mission.id)
        # Después del reinicio y nuevo incremento, debería estar completada de nuevo
        assert progress.is_completed is True

    def test_set_progress(self, db_session, sample_user, sample_mission):
        """Test establecer progreso a valor específico"""
        service = MissionService(db_session)

        # Crear progreso
        service.get_or_create_progress(sample_user.id, sample_mission.id)

        # Establecer progreso
        progress = service.set_progress(sample_user.id, sample_mission.id, 8)

        assert progress is not None
        assert progress.current_value == 8
        assert progress.is_completed is False  # 8 < 10 (target_value)

    def test_set_progress_completes(self, db_session, sample_user, sample_mission):
        """Test que set_progress marca como completada si alcanza el objetivo"""
        service = MissionService(db_session)

        # Crear progreso
        service.get_or_create_progress(sample_user.id, sample_mission.id)

        # Establecer progreso que completa la misión
        progress = service.set_progress(sample_user.id, sample_mission.id, 15)

        assert progress.current_value == 15
        assert progress.is_completed is True
        assert progress.completed_at is not None


@pytest.mark.unit
class TestMissionStats:
    """Tests para estadísticas de misiones"""

    def test_get_mission_stats(self, db_session, sample_mission, sample_user):
        """Test obtener estadísticas de misión"""
        service = MissionService(db_session)

        # Crear progreso para el usuario
        service.get_or_create_progress(sample_user.id, sample_mission.id)

        stats = service.get_mission_stats(sample_mission.id)

        assert stats is not None
        assert stats['mission_name'] == sample_mission.name
        assert stats['total_users'] >= 1
        assert 'completed' in stats
        assert 'in_progress' in stats
        assert 'completion_rate' in stats

    def test_get_mission_stats_not_found(self, db_session):
        """Test estadísticas de misión inexistente"""
        service = MissionService(db_session)

        stats = service.get_mission_stats(99999)

        assert stats == {}
