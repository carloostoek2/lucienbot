"""
Tests unitarios para reward_user_handlers.

Cubre:
- show_available_rewards: lista vacía y con recompensas, idempotencia
- reward_detail: detalle de recompensa con mision asociada, idempotencia, no encontrada
"""

from unittest.mock import MagicMock, patch

import pytest

from models.models import RewardType

pytestmark = [pytest.mark.unit]


class TestShowAvailableRewards:
    """Tests para show_available_rewards.
    (skip-dupe tests and their idempotency_cache patches removed in gsd-mw-hardening phase 5;
     dedup is now the responsibility of the global IdempotencyMiddleware.)

    Tests ported to 1-service pattern (get_service + MissionService only) + pure formatting via get_reward_emoji. Arch-enforcer note addressed.
    """

    @patch("handlers.reward_user_handlers.get_service")
    async def test_empty_rewards_shows_empty_message(self, mock_get_service, make_callback):
        """Cuando no hay recompensas, muestra mensaje vacío."""
        mock_instance = MagicMock()
        mock_instance.get_available_rewards_for_user.return_value = []
        mock_get_service.return_value.__enter__.return_value = mock_instance
        cb = make_callback(data="rewards_list")

        from handlers.reward_user_handlers import show_available_rewards

        await show_available_rewards(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay recompensas" in text

    @patch("handlers.reward_user_handlers.get_service")
    async def test_displays_rewards_list(self, mock_get_service, make_callback):
        """Muestra lista de recompensas disponibles con botones."""
        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Test Mission"
        mock_reward = MagicMock()
        mock_reward.name = "Test Reward"
        # Config for real pure get_reward_emoji (called from _build_rewards_buttons)
        mock_reward.reward_type = RewardType.BESITOS
        mock_reward.besito_amount = 10
        mock_instance = MagicMock()
        mock_instance.get_available_rewards_for_user.return_value = [
            {"mission": mock_mission, "reward": mock_reward, "progress": None}
        ]
        mock_get_service.return_value.__enter__.return_value = mock_instance
        cb = make_callback(data="rewards_list")

        from handlers.reward_user_handlers import show_available_rewards

        await show_available_rewards(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Recompensas Disponibles" in text

    @patch("handlers.reward_user_handlers.get_service")
    async def test_calls_service_with_user_id(self, mock_get_service, make_callback):
        """Llama a get_available_rewards_for_user con el user_id correcto."""
        mock_instance = MagicMock()
        mock_instance.get_available_rewards_for_user.return_value = []
        mock_get_service.return_value.__enter__.return_value = mock_instance
        cb = make_callback(data="rewards_list")

        from handlers.reward_user_handlers import show_available_rewards

        await show_available_rewards(cb)

        mock_instance.get_available_rewards_for_user.assert_called_once_with(123456789)

    @patch("handlers.reward_user_handlers.get_service")
    async def test_closes_service_via_context_manager(self, mock_get_service, make_callback):
        """El contexto cierra el servicio al salir (ported from closes_both)."""
        mock_instance = MagicMock()
        mock_instance.get_available_rewards_for_user.return_value = []
        mock_get_service.return_value.__enter__.return_value = mock_instance
        cb = make_callback(data="rewards_list")

        from handlers.reward_user_handlers import show_available_rewards

        await show_available_rewards(cb)

        mock_get_service.return_value.__exit__.assert_called_once()


class TestRewardDetail:
    """Tests para reward_detail - detalle de recompensa.
    (skip-dupe tests and their idempotency_cache patches removed in gsd-mw-hardening phase 5;
     the guard logic is now in the global IdempotencyMiddleware.)

    Tests ported to 1-service pattern (get_service + MissionService only) + pure formatting via get_reward_emoji. Arch-enforcer note addressed.
    """

    @patch("handlers.reward_user_handlers.get_service")
    async def test_mission_not_found_shows_alert(self, mock_get_service, make_callback):
        """Cuando no se encuentra la misión, muestra alerta."""
        mock_instance = MagicMock()
        mock_instance.get_mission.return_value = None
        mock_get_service.return_value.__enter__.return_value = mock_instance
        cb = make_callback(data="reward_user_detail:999")

        from handlers.reward_user_handlers import reward_detail
        from keyboards.callback_data import RewardUserDetailCallback

        await reward_detail(cb, RewardUserDetailCallback(mission_id=999))

        cb.answer.assert_called_once_with("Recompensa no encontrada", show_alert=True)

    @patch("handlers.reward_user_handlers.get_service")
    async def test_mission_without_reward_shows_alert(self, mock_get_service, make_callback):
        """Cuando la misión no tiene reward (relationship), muestra alerta."""
        mock_mission = MagicMock()
        mock_mission.reward_id = None
        mock_mission.reward = None
        mock_instance = MagicMock()
        mock_instance.get_mission.return_value = mock_mission
        mock_get_service.return_value.__enter__.return_value = mock_instance
        cb = make_callback(data="reward_user_detail:1")

        from handlers.reward_user_handlers import reward_detail
        from keyboards.callback_data import RewardUserDetailCallback

        await reward_detail(cb, RewardUserDetailCallback(mission_id=1))

        cb.answer.assert_called_once_with("Recompensa no encontrada", show_alert=True)

    @patch("handlers.reward_user_handlers.get_service")
    async def test_displays_reward_detail(self, mock_get_service, make_callback):
        """Muestra detalles completos de la recompensa con su misión."""
        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Mission One"
        mock_mission.description = "Complete the task"
        mock_mission.target_value = 10
        mock_mission.reward_id = 5

        mock_reward = MagicMock()
        mock_reward.name = "Gold Reward"
        mock_reward.description = "A shiny reward"
        # For real pure get_reward_emoji via relationship
        mock_reward.reward_type = RewardType.BESITOS
        mock_reward.besito_amount = 0
        mock_mission.reward = mock_reward

        mock_progress = MagicMock()
        mock_progress.current_value = 3
        mock_progress.is_completed = False

        mock_instance = MagicMock()
        mock_instance.get_mission.return_value = mock_mission
        mock_instance.get_or_create_progress.return_value = mock_progress
        mock_get_service.return_value.__enter__.return_value = mock_instance

        from keyboards.callback_data import RewardUserDetailCallback

        cb = make_callback(data="reward_user_detail:1")

        from handlers.reward_user_handlers import reward_detail

        await reward_detail(cb, RewardUserDetailCallback(mission_id=1))

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Gold Reward" in text
        assert "Mission One" in text
        assert "Complete the task" in text

    @patch("handlers.reward_user_handlers.get_service")
    async def test_shows_completed_status(self, mock_get_service, make_callback):
        """Muestra estado completado cuando progress.is_completed es True."""
        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Mission"
        mock_mission.description = None
        mock_mission.target_value = 5
        mock_mission.reward_id = 5

        mock_reward = MagicMock()
        mock_reward.name = "Reward"
        mock_reward.description = None
        mock_reward.reward_type = RewardType.BESITOS
        mock_reward.besito_amount = 0
        mock_mission.reward = mock_reward

        mock_progress = MagicMock()
        mock_progress.current_value = 5
        mock_progress.is_completed = True

        mock_instance = MagicMock()
        mock_instance.get_mission.return_value = mock_mission
        mock_instance.get_or_create_progress.return_value = mock_progress
        mock_get_service.return_value.__enter__.return_value = mock_instance

        from keyboards.callback_data import RewardUserDetailCallback

        cb = make_callback(data="reward_user_detail:1")

        from handlers.reward_user_handlers import reward_detail

        await reward_detail(cb, RewardUserDetailCallback(mission_id=1))

        text = cb.message.edit_text.call_args[0][0]
        assert "completada" in text.lower()

    @patch("handlers.reward_user_handlers.get_service")
    async def test_shows_progress_bar_when_incomplete(self, mock_get_service, make_callback):
        """Muestra barra de progreso cuando la misión no está completada."""
        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Mission"
        mock_mission.description = None
        mock_mission.target_value = 10
        mock_mission.reward_id = 5

        mock_reward = MagicMock()
        mock_reward.name = "Reward"
        mock_reward.description = None
        mock_reward.reward_type = RewardType.BESITOS
        mock_reward.besito_amount = 0
        mock_mission.reward = mock_reward

        mock_progress = MagicMock()
        mock_progress.current_value = 3
        mock_progress.is_completed = False

        mock_instance = MagicMock()
        mock_instance.get_mission.return_value = mock_mission
        mock_instance.get_or_create_progress.return_value = mock_progress
        mock_get_service.return_value.__enter__.return_value = mock_instance

        from keyboards.callback_data import RewardUserDetailCallback

        cb = make_callback(data="reward_user_detail:1")

        from handlers.reward_user_handlers import reward_detail

        await reward_detail(cb, RewardUserDetailCallback(mission_id=1))

        text = cb.message.edit_text.call_args[0][0]
        assert "Progreso" in text
        assert "3 / 10" in text

    @patch("handlers.reward_user_handlers.get_service")
    async def test_calls_service_with_correct_params(self, mock_get_service, make_callback):
        """Llama a los servicios con los parámetros correctos (solo MissionService via get_service)."""
        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Mission"
        mock_mission.description = "Desc"
        mock_mission.target_value = 10
        mock_mission.reward_id = 5

        mock_reward = MagicMock()
        mock_reward.name = "Reward"
        mock_reward.description = "Desc"
        mock_reward.reward_type = RewardType.BESITOS
        mock_reward.besito_amount = 0
        mock_mission.reward = mock_reward

        mock_progress = MagicMock()
        mock_progress.current_value = 0
        mock_progress.is_completed = False

        mock_instance = MagicMock()
        mock_instance.get_mission.return_value = mock_mission
        mock_instance.get_or_create_progress.return_value = mock_progress
        mock_get_service.return_value.__enter__.return_value = mock_instance

        from keyboards.callback_data import RewardUserDetailCallback

        cb = make_callback(data="reward_user_detail:1")

        from handlers.reward_user_handlers import reward_detail

        await reward_detail(cb, RewardUserDetailCallback(mission_id=1))

        mock_instance.get_mission.assert_called_once_with(1)
        mock_instance.get_or_create_progress.assert_called_once_with(123456789, 1)

    @patch("handlers.reward_user_handlers.get_service")
    async def test_closes_service_via_context_manager(self, mock_get_service, make_callback):
        """El contexto cierra el servicio al salir (ported from closes_both_services)."""
        mock_mission = MagicMock()
        mock_mission.id = 1
        mock_mission.name = "Mission"
        mock_mission.description = "Desc"
        mock_mission.target_value = 10
        mock_mission.reward_id = 5

        mock_reward = MagicMock()
        mock_reward.name = "Reward"
        mock_reward.description = "Desc"
        mock_reward.reward_type = RewardType.BESITOS
        mock_reward.besito_amount = 0
        mock_mission.reward = mock_reward

        mock_instance = MagicMock()
        mock_instance.get_mission.return_value = mock_mission
        mock_instance.get_or_create_progress.return_value = MagicMock(
            current_value=0, is_completed=False
        )
        mock_get_service.return_value.__enter__.return_value = mock_instance

        from keyboards.callback_data import RewardUserDetailCallback

        cb = make_callback(data="reward_user_detail:1")

        from handlers.reward_user_handlers import reward_detail

        await reward_detail(cb, RewardUserDetailCallback(mission_id=1))

        mock_get_service.return_value.__exit__.assert_called_once()


class TestRewardUserPureHelpers:
    """Tests para los helpers puros extraídos de reward_user_handlers (Item 7 / arch-enforcer LOC)."""

    def test_compute_reward_status_text_completed(self):
        from handlers.reward_user_handlers import compute_reward_status_text

        progress = MagicMock(is_completed=True)
        mission = MagicMock()
        assert "completada" in compute_reward_status_text(progress, mission).lower()

    def test_compute_reward_status_text_in_progress(self):
        from handlers.reward_user_handlers import compute_reward_status_text

        progress = MagicMock(is_completed=False, current_value=3)
        mission = MagicMock(target_value=10)
        status = compute_reward_status_text(progress, mission)
        assert "Progreso" in status
        assert "3 / 10" in status

    def test_build_reward_detail_keyboard(self):
        from handlers.reward_user_handlers import build_reward_detail_keyboard

        kb = build_reward_detail_keyboard(42)
        assert len(kb.inline_keyboard) == 2
        assert "Ver mision" in kb.inline_keyboard[0][0].text
        assert "Volver a recompensas" in kb.inline_keyboard[1][0].text
        # cb data packed contains mission_id
        assert "42" in kb.inline_keyboard[0][0].callback_data

    def test_build_progress_bar_edges(self):
        from handlers.reward_user_handlers import _build_progress_bar

        assert _build_progress_bar(0, 10)[1] == 0
        assert _build_progress_bar(5, 10)[1] == 50
        assert _build_progress_bar(10, 10)[1] == 100

    def test_compute_reward_status_text_with_none_descs_progress_path(self):
        """Cubre path de progreso con descs None (helper puro no debe crashear; usa defaults en caller)."""
        from handlers.reward_user_handlers import compute_reward_status_text

        progress = MagicMock(is_completed=False, current_value=1)
        mission = MagicMock(target_value=5)
        status = compute_reward_status_text(progress, mission)
        assert "Progreso" in status
        assert "1 / 5" in status

    def test_build_rewards_buttons_pure_status_emoji_truncation_cb_and_real_emoji_various_types(
        self,
    ):
        """Pure unit for supporting list button builder (covers status_emoji 🔒/✨, name[:30] trunc, packed cb, real get_reward_emoji via RewardType attrs for BESITOS/PACKAGE/VIP). Item7 pure helpers coverage per recs."""
        from handlers.reward_user_handlers import _build_rewards_buttons
        from models.models import RewardType

        # BESITOS in-progress -> ✨ + real emoji (post-assign to avoid MagicMock 'name' kwarg gotcha per gold patterns in file)
        m1 = MagicMock()
        m1.id = 10
        m1.name = "A very long mission reward name that will truncate at thirty chars"
        r1 = MagicMock()
        r1.reward_type = RewardType.BESITOS
        r1.besito_amount = 42
        r1.name = m1.name
        p1 = MagicMock(is_completed=False)
        # PACKAGE completed -> 🔒 + real emoji
        m2 = MagicMock()
        m2.id = 20
        m2.name = "ShortPkg"
        r2 = MagicMock()
        r2.reward_type = RewardType.PACKAGE
        r2.besito_amount = None
        r2.name = "ShortPkg"
        p2 = MagicMock(is_completed=True)
        # VIP no progress -> ✨
        m3 = MagicMock()
        m3.id = 30
        m3.name = "VIPAccess"
        r3 = MagicMock()
        r3.reward_type = RewardType.VIP_ACCESS
        r3.besito_amount = None
        r3.name = "VIPAccess"
        data = [
            {"mission": m1, "reward": r1, "progress": p1},
            {"mission": m2, "reward": r2, "progress": p2},
            {"mission": m3, "reward": r3, "progress": None},
        ]
        buttons = _build_rewards_buttons(data)
        assert len(buttons) == 3
        # first: ✨ (not completed) + 💋 from real pure + truncated name
        t0 = buttons[0][0].text
        assert "✨" in t0 and "💋" in t0
        assert (
            "A very long mission reward nam" in t0
        )  # name[:30] truncation visible (30 char prefix)
        assert "reward_user_detail:10" in buttons[0][0].callback_data
        # second: 🔒 (completed) + 📦
        t1 = buttons[1][0].text
        assert "🔒" in t1 and "📦" in t1 and "ShortPkg" in t1
        assert "reward_user_detail:20" in buttons[1][0].callback_data
        # third: ✨ + 👑
        t2 = buttons[2][0].text
        assert "✨" in t2 and "👑" in t2 and "VIPAccess" in t2
        assert "reward_user_detail:30" in buttons[2][0].callback_data
