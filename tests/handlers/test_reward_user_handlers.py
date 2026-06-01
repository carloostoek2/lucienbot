"""
Tests unitarios para reward_user_handlers.

Cubre:
- show_available_rewards: lista vacía y con recompensas, idempotencia
- reward_detail: detalle de recompensa con mision asociada, idempotencia, no encontrada
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = [pytest.mark.unit]


class TestShowAvailableRewards:
    """Tests para show_available_rewards."""

    @patch("handlers.reward_user_handlers.idempotency_cache")
    @patch("handlers.reward_user_handlers.MissionService")
    @patch("handlers.reward_user_handlers.RewardService")
    async def test_skips_when_duplicate(
        self, mock_reward_svc, mock_mission_svc, mock_idempotency, make_callback
    ):
        """Si idempotency_cache dice duplicado, retorna sin procesar."""
        mock_idempotency.is_duplicate.return_value = True
        cb = make_callback(data="rewards_list")

        from handlers.reward_user_handlers import show_available_rewards
        await show_available_rewards(cb)

        cb.answer.assert_called_once()
        cb.message.edit_text.assert_not_called()

    @patch("handlers.reward_user_handlers.idempotency_cache")
    @patch("handlers.reward_user_handlers.MissionService")
    @patch("handlers.reward_user_handlers.RewardService")
    async def test_empty_rewards_shows_empty_message(
        self, mock_reward_svc, mock_mission_svc, mock_idempotency, make_callback
    ):
        """Cuando no hay recompensas, muestra mensaje vacío."""
        mock_idempotency.is_duplicate.return_value = False
        mock_mission_svc.return_value.get_available_rewards_for_user.return_value = []
        cb = make_callback(data="rewards_list")

        from handlers.reward_user_handlers import show_available_rewards
        await show_available_rewards(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay recompensas" in text

    @patch("handlers.reward_user_handlers.idempotency_cache")
    @patch("handlers.reward_user_handlers.MissionService")
    @patch("handlers.reward_user_handlers.RewardService")
    async def test_displays_rewards_list(
        self, mock_reward_svc, mock_mission_svc, mock_idempotency, make_callback
    ):
        """Muestra lista de recompensas disponibles con botones."""
        mock_idempotency.is_duplicate.return_value = False
        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Test Mission"
        mock_reward = MagicMock()
        mock_reward.name = "Test Reward"
        mock_reward_svc.return_value.get_reward_emoji.return_value = ("🎁", "Gift")
        mock_mission_svc.return_value.get_available_rewards_for_user.return_value = [
            {"mission": mock_mission, "reward": mock_reward, "progress": None}
        ]
        cb = make_callback(data="rewards_list")

        from handlers.reward_user_handlers import show_available_rewards
        await show_available_rewards(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Recompensas Disponibles" in text

    @patch("handlers.reward_user_handlers.idempotency_cache")
    @patch("handlers.reward_user_handlers.MissionService")
    @patch("handlers.reward_user_handlers.RewardService")
    async def test_calls_service_with_user_id(
        self, mock_reward_svc, mock_mission_svc, mock_idempotency, make_callback
    ):
        """Llama a get_available_rewards_for_user con el user_id correcto."""
        mock_idempotency.is_duplicate.return_value = False
        mock_mission_svc.return_value.get_available_rewards_for_user.return_value = []
        cb = make_callback(data="rewards_list")

        from handlers.reward_user_handlers import show_available_rewards
        await show_available_rewards(cb)

        mock_mission_svc.return_value.get_available_rewards_for_user.assert_called_once_with(123456789)

    @patch("handlers.reward_user_handlers.idempotency_cache")
    @patch("handlers.reward_user_handlers.MissionService")
    @patch("handlers.reward_user_handlers.RewardService")
    async def test_closes_both_services(
        self, mock_reward_svc, mock_mission_svc, mock_idempotency, make_callback
    ):
        """Ambos servicios se cierran en finally."""
        mock_idempotency.is_duplicate.return_value = False
        mock_mission_svc.return_value.get_available_rewards_for_user.return_value = []
        cb = make_callback(data="rewards_list")

        from handlers.reward_user_handlers import show_available_rewards
        await show_available_rewards(cb)

        mock_mission_svc.return_value.close.assert_called_once()
        mock_reward_svc.return_value.close.assert_called_once()


class TestRewardDetail:
    """Tests para reward_detail - detalle de recompensa."""

    @patch("handlers.reward_user_handlers.idempotency_cache")
    @patch("handlers.reward_user_handlers.MissionService")
    @patch("handlers.reward_user_handlers.RewardService")
    async def test_skips_when_duplicate(
        self, mock_reward_svc, mock_mission_svc, mock_idempotency, make_callback
    ):
        """Si idempotency_cache dice duplicado, retorna sin procesar."""
        mock_idempotency.is_duplicate.return_value = True
        cb = make_callback(data="reward_user_detail:1")

        from keyboards.callback_data import RewardUserDetailCallback
        from handlers.reward_user_handlers import reward_detail
        await reward_detail(cb, RewardUserDetailCallback(mission_id=1))

        cb.answer.assert_called_once()
        cb.message.edit_text.assert_not_called()

    @patch("handlers.reward_user_handlers.idempotency_cache")
    @patch("handlers.reward_user_handlers.MissionService")
    @patch("handlers.reward_user_handlers.RewardService")
    async def test_mission_not_found_shows_alert(
        self, mock_reward_svc, mock_mission_svc, mock_idempotency, make_callback
    ):
        """Cuando no se encuentra la misión, muestra alerta."""
        mock_idempotency.is_duplicate.return_value = False
        mock_mission_svc.return_value.get_mission.return_value = None
        cb = make_callback(data="reward_user_detail:999")

        from keyboards.callback_data import RewardUserDetailCallback
        from handlers.reward_user_handlers import reward_detail
        await reward_detail(cb, RewardUserDetailCallback(mission_id=999))

        cb.answer.assert_called_once_with("Recompensa no encontrada", show_alert=True)

    @patch("handlers.reward_user_handlers.idempotency_cache")
    @patch("handlers.reward_user_handlers.MissionService")
    @patch("handlers.reward_user_handlers.RewardService")
    async def test_mission_without_reward_shows_alert(
        self, mock_reward_svc, mock_mission_svc, mock_idempotency, make_callback
    ):
        """Cuando la misión no tiene reward_id, muestra alerta."""
        mock_idempotency.is_duplicate.return_value = False
        mock_mission = MagicMock()
        mock_mission.reward_id = None
        mock_mission_svc.return_value.get_mission.return_value = mock_mission
        cb = make_callback(data="reward_user_detail:1")

        from keyboards.callback_data import RewardUserDetailCallback
        from handlers.reward_user_handlers import reward_detail
        await reward_detail(cb, RewardUserDetailCallback(mission_id=1))

        cb.answer.assert_called_once_with("Recompensa no encontrada", show_alert=True)

    @patch("handlers.reward_user_handlers.idempotency_cache")
    @patch("handlers.reward_user_handlers.MissionService")
    @patch("handlers.reward_user_handlers.RewardService")
    async def test_displays_reward_detail(
        self, mock_reward_svc, mock_mission_svc, mock_idempotency, make_callback
    ):
        """Muestra detalles completos de la recompensa con su misión."""
        mock_idempotency.is_duplicate.return_value = False

        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Mission One"
        mock_mission.description = "Complete the task"
        mock_mission.target_value = 10
        mock_mission.reward_id = 5

        mock_reward = MagicMock()
        mock_reward.name = "Gold Reward"
        mock_reward.description = "A shiny reward"

        mock_progress = MagicMock()
        mock_progress.current_value = 3
        mock_progress.is_completed = False

        mock_mission_svc.return_value.get_mission.return_value = mock_mission
        mock_mission_svc.return_value.get_or_create_progress.return_value = mock_progress
        mock_reward_svc.return_value.get_reward.return_value = mock_reward
        mock_reward_svc.return_value.get_reward_emoji.return_value = ("🥇", "Gold")

        from keyboards.callback_data import RewardUserDetailCallback
        cb = make_callback(data="reward_user_detail:1")

        from handlers.reward_user_handlers import reward_detail
        await reward_detail(cb, RewardUserDetailCallback(mission_id=1))

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Gold Reward" in text
        assert "Mission One" in text
        assert "Complete the task" in text

    @patch("handlers.reward_user_handlers.idempotency_cache")
    @patch("handlers.reward_user_handlers.MissionService")
    @patch("handlers.reward_user_handlers.RewardService")
    async def test_shows_completed_status(
        self, mock_reward_svc, mock_mission_svc, mock_idempotency, make_callback
    ):
        """Muestra estado completado cuando progress.is_completed es True."""
        mock_idempotency.is_duplicate.return_value = False

        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Mission"
        mock_mission.description = None
        mock_mission.target_value = 5
        mock_mission.reward_id = 5

        mock_reward = MagicMock()
        mock_reward.name = "Reward"
        mock_reward.description = None

        mock_progress = MagicMock()
        mock_progress.current_value = 5
        mock_progress.is_completed = True

        mock_mission_svc.return_value.get_mission.return_value = mock_mission
        mock_mission_svc.return_value.get_or_create_progress.return_value = mock_progress
        mock_reward_svc.return_value.get_reward.return_value = mock_reward
        mock_reward_svc.return_value.get_reward_emoji.return_value = ("🎁", "Gift")

        from keyboards.callback_data import RewardUserDetailCallback
        cb = make_callback(data="reward_user_detail:1")

        from handlers.reward_user_handlers import reward_detail
        await reward_detail(cb, RewardUserDetailCallback(mission_id=1))

        text = cb.message.edit_text.call_args[0][0]
        assert "completada" in text.lower()

    @patch("handlers.reward_user_handlers.idempotency_cache")
    @patch("handlers.reward_user_handlers.MissionService")
    @patch("handlers.reward_user_handlers.RewardService")
    async def test_shows_progress_bar_when_incomplete(
        self, mock_reward_svc, mock_mission_svc, mock_idempotency, make_callback
    ):
        """Muestra barra de progreso cuando la misión no está completada."""
        mock_idempotency.is_duplicate.return_value = False

        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Mission"
        mock_mission.description = None
        mock_mission.target_value = 10
        mock_mission.reward_id = 5

        mock_reward = MagicMock()
        mock_reward.name = "Reward"
        mock_reward.description = None

        mock_progress = MagicMock()
        mock_progress.current_value = 3
        mock_progress.is_completed = False

        mock_mission_svc.return_value.get_mission.return_value = mock_mission
        mock_mission_svc.return_value.get_or_create_progress.return_value = mock_progress
        mock_reward_svc.return_value.get_reward.return_value = mock_reward
        mock_reward_svc.return_value.get_reward_emoji.return_value = ("🎁", "Gift")

        from keyboards.callback_data import RewardUserDetailCallback
        cb = make_callback(data="reward_user_detail:1")

        from handlers.reward_user_handlers import reward_detail
        await reward_detail(cb, RewardUserDetailCallback(mission_id=1))

        text = cb.message.edit_text.call_args[0][0]
        assert "Progreso" in text
        assert "3 / 10" in text

    @patch("handlers.reward_user_handlers.idempotency_cache")
    @patch("handlers.reward_user_handlers.MissionService")
    @patch("handlers.reward_user_handlers.RewardService")
    async def test_calls_service_with_correct_params(
        self, mock_reward_svc, mock_mission_svc, mock_idempotency, make_callback
    ):
        """Llama a los servicios con los parámetros correctos."""
        mock_idempotency.is_duplicate.return_value = False

        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Mission"
        mock_mission.description = "Desc"
        mock_mission.target_value = 10
        mock_mission.reward_id = 5

        mock_reward = MagicMock()
        mock_reward.name = "Reward"
        mock_reward.description = "Desc"

        mock_progress = MagicMock()
        mock_progress.current_value = 0
        mock_progress.is_completed = False

        mock_mission_svc.return_value.get_mission.return_value = mock_mission
        mock_mission_svc.return_value.get_or_create_progress.return_value = mock_progress
        mock_reward_svc.return_value.get_reward.return_value = mock_reward
        mock_reward_svc.return_value.get_reward_emoji.return_value = ("🎁", "Gift")

        from keyboards.callback_data import RewardUserDetailCallback
        cb = make_callback(data="reward_user_detail:1")

        from handlers.reward_user_handlers import reward_detail
        await reward_detail(cb, RewardUserDetailCallback(mission_id=1))

        mock_mission_svc.return_value.get_mission.assert_called_once_with(1)
        mock_reward_svc.return_value.get_reward.assert_called_once_with(5)
        mock_mission_svc.return_value.get_or_create_progress.assert_called_once_with(123456789, 1)

    @patch("handlers.reward_user_handlers.idempotency_cache")
    @patch("handlers.reward_user_handlers.MissionService")
    @patch("handlers.reward_user_handlers.RewardService")
    async def test_closes_both_services(
        self, mock_reward_svc, mock_mission_svc, mock_idempotency, make_callback
    ):
        """Ambos servicios se cierran en finally."""
        mock_idempotency.is_duplicate.return_value = False

        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Mission"
        mock_mission.description = "Desc"
        mock_mission.target_value = 10
        mock_mission.reward_id = 5

        mock_reward = MagicMock()
        mock_reward.name = "Reward"
        mock_reward.description = "Desc"

        mock_mission_svc.return_value.get_mission.return_value = mock_mission
        mock_mission_svc.return_value.get_or_create_progress.return_value = MagicMock(
            current_value=0, is_completed=False
        )
        mock_reward_svc.return_value.get_reward.return_value = mock_reward
        mock_reward_svc.return_value.get_reward_emoji.return_value = ("🎁", "Gift")

        from keyboards.callback_data import RewardUserDetailCallback
        cb = make_callback(data="reward_user_detail:1")

        from handlers.reward_user_handlers import reward_detail
        await reward_detail(cb, RewardUserDetailCallback(mission_id=1))

        mock_mission_svc.return_value.close.assert_called_once()
        mock_reward_svc.return_value.close.assert_called_once()
