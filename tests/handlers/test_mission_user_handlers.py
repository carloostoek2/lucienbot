"""
Tests unitarios para mission_user_handlers.

Cubre:
- show_my_missions: lista de misiones activas (vacía y con datos)
- mission_detail: detalle de una misión (no encontrada, varios tipos de recompensa)
- claim_mission_reward: stub "en desarrollo"
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = [pytest.mark.unit]


class TestShowMyMissions:
    """Tests para show_my_missions - lista de misiones activas."""

    @patch("handlers.mission_user_handlers.get_service")
    async def test_empty_missions_shows_empty_message(self, mock_get_service, make_callback):
        """Cuando no hay misiones activas, muestra mensaje vacío."""
        mock_instance = MagicMock()
        mock_instance.get_user_active_missions.return_value = []
        mock_get_service.return_value.__enter__.return_value = mock_instance
        cb = make_callback(data="my_missions")

        from handlers.mission_user_handlers import show_my_missions
        await show_my_missions(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "desafios" in text.lower()
        cb.answer.assert_called_once()

    @patch("handlers.mission_user_handlers.get_service")
    async def test_displays_active_missions_with_progress_bars(self, mock_get_service, make_callback):
        """Muestra misiones activas con barras de progreso."""
        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Test Mission"
        mock_mission.description = "Do something"
        mock_mission.target_value = 10

        mock_progress = MagicMock()
        mock_progress.current_value = 5
        mock_progress.is_completed = False

        mock_instance = MagicMock()
        mock_instance.get_user_active_missions.return_value = [
            {"mission": mock_mission, "progress": mock_progress, "percentage": 50}
        ]
        mock_get_service.return_value.__enter__.return_value = mock_instance
        cb = make_callback(data="my_missions")

        from handlers.mission_user_handlers import show_my_missions
        await show_my_missions(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Test Mission" in text
        assert "50%" in text
        assert "5" in text
        assert "10" in text
        cb.answer.assert_called_once()

    @patch("handlers.mission_user_handlers.get_service")
    async def test_calls_service_with_user_id(self, mock_get_service, make_callback):
        """Llama a get_user_active_missions con el user_id correcto."""
        mock_instance = MagicMock()
        mock_instance.get_user_active_missions.return_value = []
        mock_get_service.return_value.__enter__.return_value = mock_instance
        cb = make_callback(data="my_missions")

        from handlers.mission_user_handlers import show_my_missions
        await show_my_missions(cb)

        mock_instance.get_user_active_missions.assert_called_once_with(123456789)

    @patch("handlers.mission_user_handlers.get_service")
    async def test_closes_service_via_context_manager(self, mock_get_service, make_callback):
        """El contexto cierra el servicio al salir."""
        mock_instance = MagicMock()
        mock_instance.get_user_active_missions.return_value = []
        mock_get_service.return_value.__enter__.return_value = mock_instance
        cb = make_callback(data="my_missions")

        from handlers.mission_user_handlers import show_my_missions
        await show_my_missions(cb)

        mock_get_service.return_value.__exit__.assert_called_once()


class TestMissionDetail:
    """Tests para mission_detail - detalle de una misión."""

    @patch("handlers.mission_user_handlers.get_service")
    async def test_mission_not_found_shows_alert(self, mock_get_service, make_callback):
        """Cuando no se encuentra la misión, muestra alerta."""
        mock_instance = MagicMock()
        mock_instance.get_mission.return_value = None
        mock_get_service.return_value.__enter__.return_value = mock_instance

        from keyboards.callback_data import MissionDetailCallback
        cb = make_callback(data=MissionDetailCallback(mission_id=999).pack())

        from handlers.mission_user_handlers import mission_detail
        await mission_detail(cb, MissionDetailCallback(mission_id=999))

        cb.answer.assert_called_once_with("Mision no encontrada", show_alert=True)
        cb.message.edit_text.assert_not_called()

    @patch("handlers.mission_user_handlers.get_service")
    async def test_displays_mission_detail_without_reward(self, mock_get_service, make_callback):
        """Muestra detalles completos de la misión sin recompensa."""
        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Test Mission"
        mock_mission.description = "Do something"
        mock_mission.target_value = 10
        mock_mission.reward = None

        mock_progress = MagicMock()
        mock_progress.current_value = 5
        mock_progress.is_completed = False

        mock_instance = MagicMock()
        mock_instance.get_mission.return_value = mock_mission
        mock_instance.get_or_create_progress.return_value = mock_progress
        mock_get_service.return_value.__enter__.return_value = mock_instance

        from keyboards.callback_data import MissionDetailCallback
        cb = make_callback(data=MissionDetailCallback(mission_id=1).pack())

        from handlers.mission_user_handlers import mission_detail
        await mission_detail(cb, MissionDetailCallback(mission_id=1))

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Test Mission" in text
        assert "Do something" in text
        assert "5 / 10" in text
        assert "Sin recompensa" in text
        cb.answer.assert_called_once()

    @patch("handlers.mission_user_handlers.get_service")
    async def test_shows_besitos_reward(self, mock_get_service, make_callback):
        """Muestra recompensa de tipo besitos."""
        mock_reward = MagicMock()
        mock_reward.reward_type.value = "besitos"
        mock_reward.besito_amount = 50
        mock_reward.name = "Beso Bonus"

        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Mission"
        mock_mission.description = "Desc"
        mock_mission.target_value = 10
        mock_mission.reward = mock_reward

        mock_progress = MagicMock()
        mock_progress.current_value = 10
        mock_progress.is_completed = True

        mock_instance = MagicMock()
        mock_instance.get_mission.return_value = mock_mission
        mock_instance.get_or_create_progress.return_value = mock_progress
        mock_get_service.return_value.__enter__.return_value = mock_instance

        from keyboards.callback_data import MissionDetailCallback
        cb = make_callback(data=MissionDetailCallback(mission_id=1).pack())

        from handlers.mission_user_handlers import mission_detail
        await mission_detail(cb, MissionDetailCallback(mission_id=1))

        text = cb.message.edit_text.call_args[0][0]
        assert "50 besitos" in text

    @patch("handlers.mission_user_handlers.get_service")
    async def test_shows_package_reward(self, mock_get_service, make_callback):
        """Muestra recompensa de tipo paquete."""
        mock_reward = MagicMock()
        mock_reward.reward_type.value = "package"
        mock_reward.name = "Premium Pack"
        mock_reward.besito_amount = 0

        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Mission"
        mock_mission.description = "Desc"
        mock_mission.target_value = 5
        mock_mission.reward = mock_reward

        mock_progress = MagicMock()
        mock_progress.current_value = 3
        mock_progress.is_completed = False

        mock_instance = MagicMock()
        mock_instance.get_mission.return_value = mock_mission
        mock_instance.get_or_create_progress.return_value = mock_progress
        mock_get_service.return_value.__enter__.return_value = mock_instance

        from keyboards.callback_data import MissionDetailCallback
        cb = make_callback(data=MissionDetailCallback(mission_id=1).pack())

        from handlers.mission_user_handlers import mission_detail
        await mission_detail(cb, MissionDetailCallback(mission_id=1))

        text = cb.message.edit_text.call_args[0][0]
        assert "Paquete: Premium Pack" in text

    @patch("handlers.mission_user_handlers.get_service")
    async def test_shows_vip_reward(self, mock_get_service, make_callback):
        """Muestra recompensa de tipo VIP."""
        mock_reward = MagicMock()
        mock_reward.reward_type.value = "vip_access"
        mock_reward.name = "VIP Gold"

        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Mission"
        mock_mission.description = "Desc"
        mock_mission.target_value = 5
        mock_mission.reward = mock_reward

        mock_progress = MagicMock()
        mock_progress.current_value = 0
        mock_progress.is_completed = False

        mock_instance = MagicMock()
        mock_instance.get_mission.return_value = mock_mission
        mock_instance.get_or_create_progress.return_value = mock_progress
        mock_get_service.return_value.__enter__.return_value = mock_instance

        from keyboards.callback_data import MissionDetailCallback
        cb = make_callback(data=MissionDetailCallback(mission_id=1).pack())

        from handlers.mission_user_handlers import mission_detail
        await mission_detail(cb, MissionDetailCallback(mission_id=1))

        text = cb.message.edit_text.call_args[0][0]
        assert "Acceso VIP: VIP Gold" in text

    @patch("handlers.mission_user_handlers.get_service")
    async def test_calls_service_with_correct_params(self, mock_get_service, make_callback):
        """Llama a get_mission y get_or_create_progress con los IDs correctos."""
        mock_mission = MagicMock()
        mock_mission.id = 42
        mock_mission.name = "Mission"
        mock_mission.description = "Desc"
        mock_mission.target_value = 10
        mock_mission.reward = None

        mock_instance = MagicMock()
        mock_instance.get_mission.return_value = mock_mission
        mock_instance.get_or_create_progress.return_value = MagicMock(
            current_value=0, is_completed=False
        )
        mock_get_service.return_value.__enter__.return_value = mock_instance

        from keyboards.callback_data import MissionDetailCallback
        cb = make_callback(data=MissionDetailCallback(mission_id=42).pack())

        from handlers.mission_user_handlers import mission_detail
        await mission_detail(cb, MissionDetailCallback(mission_id=42))

        mock_instance.get_mission.assert_called_once_with(42)
        mock_instance.get_or_create_progress.assert_called_once_with(123456789, 42)

    @patch("handlers.mission_user_handlers.get_service")
    async def test_closes_service_via_context_manager(self, mock_get_service, make_callback):
        """El contexto cierra el servicio al salir."""
        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Mission"
        mock_mission.description = "Desc"
        mock_mission.target_value = 10
        mock_mission.reward = None

        mock_instance = MagicMock()
        mock_instance.get_mission.return_value = mock_mission
        mock_instance.get_or_create_progress.return_value = MagicMock(
            current_value=0, is_completed=False
        )
        mock_get_service.return_value.__enter__.return_value = mock_instance

        from keyboards.callback_data import MissionDetailCallback
        cb = make_callback(data=MissionDetailCallback(mission_id=1).pack())

        from handlers.mission_user_handlers import mission_detail
        await mission_detail(cb, MissionDetailCallback(mission_id=1))

        mock_get_service.return_value.__exit__.assert_called_once()


class TestClaimMissionReward:
    """Tests para claim_mission_reward - stub."""

    async def test_shows_in_development_alert(self, make_callback):
        """Muestra alerta de funcionalidad en desarrollo."""
        cb = make_callback(data="claim_mission_reward")

        from handlers.mission_user_handlers import claim_mission_reward
        await claim_mission_reward(cb)

        cb.answer.assert_called_once_with("Funcion en desarrollo", show_alert=True)
