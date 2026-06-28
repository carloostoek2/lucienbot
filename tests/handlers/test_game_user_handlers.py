"""
Tests unitarios para game_user_handlers.

Sigue patrón gold de test_gamification_user_handlers.py + test_mission_user_handlers.py + test_store_user_handlers.py:
- patch("handlers.game_user_handlers.get_service")
- mock_instance via __enter__
- with get_service(GameService) as  y StreakPromotionService
- Llama al servicio correcto, verifica args (user_id=123456789)
- Verifica respuestas edit_text / answer
- Cierra contexto (close)
- Cubre happy paths, límites, errores, streaks/protección
- pytestmark unit
- Import handler dentro del test

Prioridad alta: game_user_handlers tenía ~14% cobertura (la más baja), es el sistema de minijuegos (dados, trivia, rachas, protección) crítico para engagement + earnings.

Abarca el sistema completo de handlers de usuario para minijuegos.
"""

from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from services.game_service import GameService
from services.streak_promotion_service import StreakPromotionService

from keyboards.callback_data import (
    StreakProtectAcceptCallback,
    StreakProtectDeclineCallback,
    TriviaAnswerCallback,
    TriviaSimpleAnswerCallback,
    TriviaVipAnswerCallback,
)

pytestmark = [pytest.mark.unit]


def _mock_game_ctx(mock_get_service):
    """Helper para mockear el context de get_service(GameService) con autospec."""
    mock_instance = create_autospec(GameService, spec_set=True, instance=True)
    mock_get_service.return_value.__enter__.return_value = mock_instance
    return mock_instance


def _mock_streak_ctx(mock_get_service):
    """Helper para StreakPromotionService (usado en protection paths) con autospec."""
    mock_instance = create_autospec(StreakPromotionService, spec_set=True, instance=True)
    return mock_instance


class TestGameMenu:
    """Tests para game_menu."""

    @patch("handlers.game_user_handlers.get_service")
    async def test_shows_menu_with_data(self, mock_get_service, make_callback):
        mock_svc = _mock_game_ctx(mock_get_service)
        mock_svc.get_menu_data.return_value = {
            "title": "Minijuegos",
            "subtitle": "Elige tu diversión",
            "dice_description": "Lanza y gana",
            "remaining_dice": 5,
            "limit_dice": 10,
            "trivia_description": "Responde",
            "remaining_trivia": 3,
            "limit_trivia": 5,
            "footer": "¡Diviértete!",
        }
        mock_svc.get_active_special_info.return_value = None
        cb = make_callback(data="game_menu")

        from handlers.game_user_handlers import game_menu

        await game_menu(cb)

        mock_svc.get_menu_data.assert_called_once_with(123456789)
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Minijuegos" in text
        assert "5 de 10" in text
        cb.answer.assert_called_once()

    @patch("handlers.game_user_handlers.get_service")
    async def test_closes_service(self, mock_get_service, make_callback):
        mock_svc = _mock_game_ctx(mock_get_service)
        mock_svc.get_menu_data.return_value = {
            "title": "t",
            "subtitle": "s",
            "dice_description": "d",
            "remaining_dice": 0,
            "limit_dice": 1,
            "trivia_description": "t",
            "remaining_trivia": 0,
            "limit_trivia": 1,
            "footer": "",
        }
        mock_svc.get_active_special_info.return_value = None
        cb = make_callback(data="game_menu")

        from handlers.game_user_handlers import game_menu

        await game_menu(cb)

        mock_get_service.return_value.__exit__.assert_called_once()


class TestDice:
    """Tests para game_dice y dice_play."""

    @patch("handlers.game_user_handlers.get_service")
    async def test_game_dice_shows_entry(self, mock_get_service, make_callback):
        mock_svc = _mock_game_ctx(mock_get_service)
        mock_svc.get_dice_entry_data.return_value = {
            "title": "Dados",
            "intro": "Lanza los dados",
            "rules": "Gana besitos",
            "remaining": 4,
            "limit": 10,
        }
        cb = make_callback(data="game_dice")

        from handlers.game_user_handlers import game_dice

        await game_dice(cb)

        mock_svc.get_dice_entry_data.assert_called_once_with(123456789)
        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()

    @patch("handlers.game_user_handlers.get_service")
    async def test_dice_play_calls_service(self, mock_get_service, make_callback):
        mock_svc = _mock_game_ctx(mock_get_service)
        mock_svc.play_dice_game.return_value = {"message": "¡Ganaste 5 besitos!"}
        cb = make_callback(data="dice_play")

        from handlers.game_user_handlers import dice_play

        await dice_play(cb)

        mock_svc.play_dice_game.assert_called_once_with(123456789)
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Ganaste" in text
        cb.answer.assert_called_once()


class TestTriviaFlows:
    """Tests para trivia (free, vip, simple) entry + answer."""

    @patch("handlers.game_user_handlers.get_service")
    async def test_game_trivia_happy_path(self, mock_get_service, make_callback):
        mock_svc = _mock_game_ctx(mock_get_service)
        mock_svc.get_trivia_entry_data.return_value = {
            "can_play": True,
            "title": "Trivia",
            "intro": "Responde",
            "counter_template": "Quedan {remaining} de {limit}",
            "remaining": 2,
            "limit": 5,
            "current_streak": 3,
        }
        mock_svc.get_random_question.return_value = (
            {"q": "¿Capital de Francia?", "opts": ["Paris", "Londres", "Madrid", "Berlin"]},
            0,
        )
        cb = make_callback(data="game_trivia")

        from handlers.game_user_handlers import game_trivia

        await game_trivia(cb)

        mock_svc.get_trivia_entry_data.assert_called_once_with(123456789)
        cb.message.edit_text.assert_called_once()
        args, kwargs = cb.message.edit_text.call_args
        text = kwargs.get("text") or (args[0] if args else "")
        assert "Trivia" in text
        assert "3" in text  # streak
        cb.answer.assert_called_once()

    @patch("handlers.game_user_handlers.get_service")
    async def test_game_trivia_limit_reached(self, mock_get_service, make_callback):
        mock_svc = _mock_game_ctx(mock_get_service)
        mock_svc.get_trivia_entry_data.return_value = {
            "can_play": False,
            "limit_message": "Límite alcanzado hoy",
        }
        cb = make_callback(data="game_trivia")

        from handlers.game_user_handlers import game_trivia

        await game_trivia(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Límite" in text

    @patch("handlers.game_user_handlers.get_service")
    async def test_trivia_answer_correct(self, mock_get_service, make_callback):
        mock_svc = _mock_game_ctx(mock_get_service)
        mock_svc.play_trivia.return_value = {
            "correct": True,
            "message": "¡Correcto! +10 besitos",
            "new_streak": 4,
        }
        cb = make_callback(data="trivia:0:1")
        cd = TriviaAnswerCallback(question_idx=0, answer_idx=1)

        from handlers.game_user_handlers import trivia_answer

        await trivia_answer(cb, cd)

        mock_svc.play_trivia.assert_called_once()
        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()

    @patch("handlers.game_user_handlers.get_service")
    async def test_trivia_vip_and_simple_paths(self, mock_get_service, make_callback):
        mock_svc = _mock_game_ctx(mock_get_service)
        mock_svc.play_trivia_vip.return_value = {
            "message": "VIP ok",
            "correct": True,
            "besitos": 10,
        }
        cb = make_callback(data="trivia_vip:0:0")
        cd = TriviaVipAnswerCallback(question_idx=0, answer_idx=0)

        from handlers.game_user_handlers import trivia_vip_answer

        await trivia_vip_answer(cb, cd)
        mock_svc.play_trivia_vip.assert_called_once()

        mock_svc.play_trivia_simple.return_value = {
            "message": "Simple ok",
            "correct": True,
            "besitos": 5,
        }
        cb2 = make_callback(data="trivia_simple:0:1")
        cd2 = TriviaSimpleAnswerCallback(question_idx=0, answer_idx=1)
        from handlers.game_user_handlers import trivia_simple_answer

        await trivia_simple_answer(cb2, cd2)
        mock_svc.play_trivia_simple.assert_called_once()


class TestStreakProtection:
    """Tests para handlers de protección de rachas (critical flow)."""

    @patch("handlers.game_user_handlers._redirect_to_trivia", new_callable=AsyncMock)
    @patch("handlers.game_user_handlers.get_service")
    async def test_handle_protection_accept(self, mock_get_service, mock_redirect, make_callback):
        mock_svc = create_autospec(StreakPromotionService, spec_set=True, instance=True)
        mock_get_service.return_value.__enter__.return_value = mock_svc
        mock_svc.protect_streak.return_value = True
        mock_svc.calculate_protection_cost.return_value = 10
        cb = make_callback(data="streak_protect_accept:123")
        cd = StreakProtectAcceptCallback(session_id=123, streak=3, game_type="trivia")

        from handlers.game_user_handlers import handle_protection_accept

        await handle_protection_accept(cb, cd)

        mock_svc.protect_streak.assert_called_once()
        cb.answer.assert_called_once()

    @patch("handlers.game_user_handlers._redirect_to_trivia", new_callable=AsyncMock)
    @patch("handlers.game_user_handlers.get_service")
    async def test_handle_protection_decline(self, mock_get_service, mock_redirect, make_callback):
        mock_svc = create_autospec(StreakPromotionService, spec_set=True, instance=True)
        mock_get_service.return_value.__enter__.return_value = mock_svc
        mock_svc.get_active_session.return_value = MagicMock(id=99)
        cb = make_callback(data="streak_protect_decline:99")
        cd = StreakProtectDeclineCallback(session_id=99, streak=5, game_type="trivia")

        from handlers.game_user_handlers import handle_protection_decline

        await handle_protection_decline(cb, cd)

        mock_svc.get_active_session.assert_called_once()
        cb.answer.assert_called_once()

    @patch("handlers.game_user_handlers.get_service")
    async def test_handle_streak_retire(self, mock_get_service, make_callback):
        mock_svc = create_autospec(StreakPromotionService, spec_set=True, instance=True)
        session = MagicMock()
        session.codes_delivered = '["CODE1"]'
        mock_svc.get_active_session.return_value = session
        mock_get_service.return_value.__enter__.return_value = mock_svc
        cb = make_callback(data="streak_retire:1")
        # handler takes only callback (StreakRetireCallback used by router filter only)

        from handlers.game_user_handlers import handle_streak_retire

        await handle_streak_retire(cb)

        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()

    @patch("handlers.game_user_handlers.get_service")
    async def test_handle_streak_continue(self, mock_get_service, make_callback):
        mock_svc = create_autospec(StreakPromotionService, spec_set=True, instance=True)
        mock_get_service.return_value.__enter__.return_value = mock_svc
        cb = make_callback(data="streak_continue:1")

        from handlers.game_user_handlers import handle_streak_continue

        await handle_streak_continue(cb)

        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()


class TestRedirectAndEdges:
    """Misc edges y redirect helper paths."""

    @patch("handlers.game_user_handlers.get_service")
    async def test_game_trivia_vip_entry(self, mock_get_service, make_callback):
        mock_svc = _mock_game_ctx(mock_get_service)
        mock_svc.get_trivia_vip_entry_data.return_value = {
            "can_play": True,
            "title": "VIP",
            "intro": "",
            "counter_template": "",
            "remaining": 1,
            "limit": 1,
            "current_streak": 0,
        }
        mock_svc.get_random_vip_question.return_value = (
            {"q": "q", "opts": ["a", "b", "c", "d"]},
            0,
        )
        cb = make_callback(data="game_trivia_vip")

        from handlers.game_user_handlers import game_trivia_vip

        await game_trivia_vip(cb)

        cb.message.edit_text.assert_called_once()
