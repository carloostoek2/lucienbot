"""
Tests unitarios para gamification_user_handlers.

Verifica que los handlers:
1. Llaman al servicio correcto con los parámetros adecuados
2. Responden con el mensaje esperado
3. Manejan correctamente los errores del servicio
4. Cierran el servicio (close) en todos los casos
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

from tests.helpers import model_mock
from models.models import BesitoTransaction, BroadcastReaction
from services.besito_service import BesitoService
from services.broadcast_service import BroadcastService
from services.daily_gift_service import DailyGiftService

import pytest

pytestmark = [pytest.mark.unit]


def _mock_gamification_ctx(mock_get_service, service_class):
    """Mock get_service(service_class) context manager con autospec."""
    svc = create_autospec(service_class, spec_set=True, instance=True)
    mock_get_service.return_value.__enter__.return_value = svc
    return svc


class TestShowBalance:
    """Tests para show_balance - consulta de saldo de besitos."""

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_calls_service_with_user_id(self, mock_get_service, make_callback):
        """Llama a get_balance_with_stats con el user_id correcto."""
        mock_instance = _mock_gamification_ctx(mock_get_service, BesitoService)
        mock_instance.get_balance_with_stats.return_value = {
            "balance": 500,
            "total_earned": 1000,
            "total_spent": 500,
        }
        cb = make_callback(data="my_balance")

        from handlers.gamification_user_handlers import show_balance

        await show_balance(cb)

        mock_instance.get_balance_with_stats.assert_called_once_with(123456789)

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_displays_balance_correctly(self, mock_get_service, make_callback):
        """El texto de respuesta incluye el saldo del usuario."""
        mock_instance = _mock_gamification_ctx(mock_get_service, BesitoService)
        mock_instance.get_balance_with_stats.return_value = {
            "balance": 500,
            "total_earned": 1000,
            "total_spent": 500,
        }
        cb = make_callback(data="my_balance")

        from handlers.gamification_user_handlers import show_balance

        await show_balance(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "500" in text
        assert "1000" in text

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Siempre llama a callback.answer()."""
        mock_instance = _mock_gamification_ctx(mock_get_service, BesitoService)
        mock_instance.get_balance_with_stats.return_value = {
            "balance": 500,
            "total_earned": 1000,
            "total_spent": 500,
        }
        cb = make_callback(data="my_balance")

        from handlers.gamification_user_handlers import show_balance

        await show_balance(cb)

        cb.answer.assert_called_once()

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_closes_service_via_context_manager(self, mock_get_service, make_callback):
        """El contexto cierra el servicio al salir."""
        mock_instance = _mock_gamification_ctx(mock_get_service, BesitoService)
        mock_instance.get_balance_with_stats.return_value = {
            "balance": 500,
            "total_earned": 1000,
            "total_spent": 500,
        }
        cb = make_callback(data="my_balance")

        from handlers.gamification_user_handlers import show_balance

        await show_balance(cb)

        mock_get_service.return_value.__exit__.assert_called_once()


class TestTransactionHistory:
    """Tests para show_transaction_history."""

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_empty_history_shows_empty_message(self, mock_get_service, make_callback):
        """Cuando no hay transacciones, muestra mensaje de historial vacío."""
        mock_instance = _mock_gamification_ctx(mock_get_service, BesitoService)
        mock_instance.get_transaction_history.return_value = []
        cb = make_callback(data="transaction_history")

        from handlers.gamification_user_handlers import show_transaction_history

        await show_transaction_history(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "vacío" in text.lower()

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_calls_service_with_correct_args(self, mock_get_service, make_callback):
        """Llama a get_transaction_history con el user_id y limit=10."""
        mock_instance = _mock_gamification_ctx(mock_get_service, BesitoService)
        mock_instance.get_transaction_history.return_value = []
        cb = make_callback(data="transaction_history")

        from handlers.gamification_user_handlers import show_transaction_history

        await show_transaction_history(cb)

        mock_instance.get_transaction_history.assert_called_once_with(123456789, limit=10)

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_displays_transactions(self, mock_get_service, make_callback):
        """Muestra las transacciones formateadas correctamente."""
        mock_tx = model_mock(BesitoTransaction)
        mock_tx.amount = 50
        mock_tx.created_at = datetime(2024, 6, 15, 10, 30)
        mock_tx.source = MagicMock()
        mock_tx.source.value = "daily_gift"

        mock_instance = _mock_gamification_ctx(mock_get_service, BesitoService)
        mock_instance.get_transaction_history.return_value = [mock_tx]
        cb = make_callback(data="transaction_history")

        from handlers.gamification_user_handlers import show_transaction_history

        await show_transaction_history(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "+50" in text
        assert "Regalo diario" in text

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_closes_service_via_context_manager(self, mock_get_service, make_callback):
        """El contexto cierra el servicio al salir."""
        mock_instance = _mock_gamification_ctx(mock_get_service, BesitoService)
        mock_instance.get_transaction_history.return_value = []
        cb = make_callback(data="transaction_history")

        from handlers.gamification_user_handlers import show_transaction_history

        await show_transaction_history(cb)

        mock_get_service.return_value.__exit__.assert_called_once()


class TestDailyGiftMenu:
    """Tests para daily_gift_menu."""

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_shows_claim_button_when_available(self, mock_get_service, make_callback):
        """Cuando can_claim=True, muestra botón de reclamar."""
        mock_instance = _mock_gamification_ctx(mock_get_service, DailyGiftService)
        mock_instance.can_claim.return_value = (True, None, "Puedes reclamar")
        mock_instance.get_gift_amount.return_value = 10
        cb = make_callback(data="daily_gift")

        from handlers.gamification_user_handlers import daily_gift_menu

        await daily_gift_menu(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Reclamar" in text or "10" in text

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_shows_wait_message_when_not_available(self, mock_get_service, make_callback):
        """Cuando can_claim=False, muestra mensaje de espera."""
        mock_instance = _mock_gamification_ctx(mock_get_service, DailyGiftService)
        mock_instance.can_claim.return_value = (False, 3600, "Vuelve en 1 hora")
        cb = make_callback(data="daily_gift")

        from handlers.gamification_user_handlers import daily_gift_menu

        await daily_gift_menu(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Vuelve" in text

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_closes_service_via_context_manager(self, mock_get_service, make_callback):
        """El contexto cierra el servicio al salir."""
        mock_instance = _mock_gamification_ctx(mock_get_service, DailyGiftService)
        mock_instance.can_claim.return_value = (True, None, "Puedes reclamar")
        cb = make_callback(data="daily_gift")

        from handlers.gamification_user_handlers import daily_gift_menu

        await daily_gift_menu(cb)

        mock_get_service.return_value.__exit__.assert_called_once()


class TestClaimDailyGift:
    """Tests para claim_daily_gift."""

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_successful_claim_shows_success(self, mock_get_service, make_callback):
        """Cuando claim_gift retorna éxito, muestra mensaje positivo."""
        mock_instance = _mock_gamification_ctx(mock_get_service, DailyGiftService)
        mock_instance.claim_gift_with_missions = AsyncMock(
            return_value=(True, 10, "Has recibido 10 besitos")
        )
        cb = make_callback(data="claim_gift")

        from handlers.gamification_user_handlers import claim_daily_gift

        await claim_daily_gift(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "reclamado" in text.lower() or "besitos" in text

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_failed_claim_shows_error(self, mock_get_service, make_callback):
        """Cuando claim_gift retorna fallo, muestra mensaje de error."""
        mock_instance = _mock_gamification_ctx(mock_get_service, DailyGiftService)
        mock_instance.claim_gift_with_missions = AsyncMock(
            return_value=(False, 0, "Ya reclamaste hoy")
        )
        cb = make_callback(data="claim_gift")

        from handlers.gamification_user_handlers import claim_daily_gift

        await claim_daily_gift(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Ya reclamaste" in text

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_calls_service_with_user_id(self, mock_get_service, make_callback):
        """Llama a claim_gift_with_missions con el user_id correcto."""
        mock_instance = _mock_gamification_ctx(mock_get_service, DailyGiftService)
        mock_instance.claim_gift_with_missions = AsyncMock(return_value=(True, 10, "OK"))
        cb = make_callback(data="claim_gift")

        from handlers.gamification_user_handlers import claim_daily_gift

        await claim_daily_gift(cb)

        mock_instance.claim_gift_with_missions.assert_awaited_once_with(
            123456789, bot=cb.bot
        )

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_closes_service_via_context_manager(self, mock_get_service, make_callback):
        """El contexto cierra el servicio al salir."""
        mock_instance = _mock_gamification_ctx(mock_get_service, DailyGiftService)
        mock_instance.claim_gift_with_missions = AsyncMock(return_value=(True, 10, "OK"))
        cb = make_callback(data="claim_gift")

        from handlers.gamification_user_handlers import claim_daily_gift

        await claim_daily_gift(cb)

        mock_get_service.return_value.__exit__.assert_called_once()


class TestHandleReaction:
    """Tests para handle_reaction - reacciones a broadcasts."""

    def _make_callback_data(self, broadcast_id=1, emoji_id=2):
        from keyboards.callback_data import ReactionCallback

        return ReactionCallback(broadcast_id=broadcast_id, emoji_id=emoji_id)

    # test_skips_when_duplicate_callback removed in gsd-mw-hardening phase 5
    # (idempotency now centralized in IdempotencyMiddleware; handler no longer has the guard)

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_registers_reaction(self, mock_get_service, make_callback):
        """Llama a check_and_register_reaction con parámetros correctos."""
        # (idempotency_cache patch removed - phase 5 centralized in middleware)
        mock_instance = _mock_gamification_ctx(mock_get_service, BroadcastService)
        mock_instance.check_and_register_reaction = AsyncMock(
            return_value={"success": True, "besitos_awarded": 5}
        )
        mock_instance.get_broadcast.return_value = MagicMock(has_reactions=False)
        cb = make_callback(data="react:1:2")

        from handlers.gamification_user_handlers import handle_reaction

        await handle_reaction(cb, self._make_callback_data())

        mock_instance.check_and_register_reaction.assert_called_once()
        _, kwargs = mock_instance.check_and_register_reaction.call_args
        assert kwargs["broadcast_id"] == 1
        assert kwargs["emoji_id"] == 2
        assert kwargs["user_id"] == 123456789
        assert kwargs["channel_id"] == -1001
        assert kwargs["message_id"] == 100

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_shows_besitos_awarded(self, mock_get_service, make_callback):
        """Responde con la cantidad de besitos ganados."""
        # (no longer patches idempotency_cache - centralized mw in phase 5)
        mock_instance = _mock_gamification_ctx(mock_get_service, BroadcastService)
        mock_instance.check_and_register_reaction = AsyncMock(
            return_value={"success": True, "besitos_awarded": 5}
        )
        mock_instance.get_broadcast.return_value = MagicMock(has_reactions=False)
        cb = make_callback(data="react:1:2")

        from handlers.gamification_user_handlers import handle_reaction

        await handle_reaction(cb, self._make_callback_data())

        cb.answer.assert_called_with("¡+5 besitos! 💋")

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_shows_alert_when_already_reacted(self, mock_get_service, make_callback):
        """Si el usuario ya reaccionó, muestra alerta."""
        # (no longer patches idempotency_cache - centralized mw in phase 5)
        mock_instance = _mock_gamification_ctx(mock_get_service, BroadcastService)
        mock_instance.check_and_register_reaction = AsyncMock(
            return_value={"success": False, "reason": "duplicate"}
        )
        cb = make_callback(data="react:1:2")

        from handlers.gamification_user_handlers import handle_reaction

        await handle_reaction(cb, self._make_callback_data())

        cb.answer.assert_called_with("Ya reaccionaste a este mensaje", show_alert=True)

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_shows_credit_failed_message(self, mock_get_service, make_callback):
        """Muestra mensaje distinto cuando falla el crédito de besitos."""
        mock_instance = _mock_gamification_ctx(mock_get_service, BroadcastService)
        mock_instance.check_and_register_reaction = AsyncMock(
            return_value={"success": False, "reason": "credit_failed"}
        )
        cb = make_callback(data="react:1:2")

        from handlers.gamification_user_handlers import handle_reaction

        await handle_reaction(cb, self._make_callback_data())

        cb.answer.assert_called_with(
            "No pudimos registrar tu reacción. Inténtalo de nuevo.", show_alert=True
        )

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_updates_reaction_counts(self, mock_get_service, make_callback):
        """Cuando has_reactions=True, actualiza los contadores."""
        # (no longer patches idempotency_cache - centralized mw in phase 5)
        mock_instance = _mock_gamification_ctx(mock_get_service, BroadcastService)
        mock_instance.check_and_register_reaction = AsyncMock(
            return_value={"success": True, "besitos_awarded": 5}
        )
        mock_instance.update_reaction_message = AsyncMock(return_value=True)
        mock_instance.get_broadcast.return_value = MagicMock(
            has_reactions=True, channel_id=-100, message_id=42, extra_button_id=None
        )
        mock_instance.get_selected_emoji_ids.return_value = [1, 2]
        mock_instance.get_reactions_by_broadcast.return_value = []
        mock_instance.get_reaction_emoji.side_effect = [MagicMock(emoji="💋"), MagicMock(emoji="❤️")]
        cb = make_callback(data="react:1:2")

        from handlers.gamification_user_handlers import handle_reaction

        await handle_reaction(cb, self._make_callback_data(broadcast_id=1, emoji_id=2))

        mock_instance.update_reaction_message.assert_called_once()
        _, kwargs = mock_instance.update_reaction_message.call_args
        assert kwargs["channel_id"] == -100
        assert kwargs["message_id"] == 42
        button_data = kwargs["new_markup"].inline_keyboard[0][0].callback_data
        from keyboards.callback_data import ReactionCallback

        unpacked = ReactionCallback.unpack(button_data)
        assert unpacked.broadcast_id == 1

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_refresh_preserves_extra_button_url_row(self, mock_get_service):
        """Si broadcast tiene extra_button_id, el markup de refresh incluye fila URL (no solo reacciones)."""
        mock_instance = _mock_gamification_ctx(mock_get_service, BroadcastService)
        # broadcast con extra
        mock_broadcast = MagicMock(
            has_reactions=True,
            channel_id=-100,
            message_id=99,
            extra_button_id=7,
        )
        mock_instance.get_broadcast.return_value = mock_broadcast
        mock_instance.get_selected_emoji_ids.return_value = [10]
        mock_instance.get_reactions_by_broadcast.return_value = []
        mock_emoji = MagicMock(emoji="🔥", id=10)
        mock_instance.get_reaction_emoji.return_value = mock_emoji
        # simular botón extra
        mock_button = MagicMock(label="🔗 Link", url="https://t.me/foo")
        mock_instance.get_broadcast_button.return_value = mock_button
        mock_instance.update_reaction_message = AsyncMock(return_value=True)

        from handlers.gamification_user_handlers import refresh_reaction_markup_counts
        from aiogram.types import InlineKeyboardMarkup

        await refresh_reaction_markup_counts(mock_instance, MagicMock(), mock_broadcast, 99)

        mock_instance.update_reaction_message.assert_called_once()
        _, call_kwargs = mock_instance.update_reaction_message.call_args
        new_markup: InlineKeyboardMarkup = call_kwargs["new_markup"]
        # Debe tener 2 filas: reacciones + url
        assert len(new_markup.inline_keyboard) == 2
        # segunda fila es url button
        url_btn = new_markup.inline_keyboard[1][0]
        assert url_btn.url == "https://t.me/foo"
        assert url_btn.text == "🔗 Link"
        # primera fila tiene callback (reaccion)
        assert "callback_data" in str(new_markup.inline_keyboard[0][0].callback_data) or hasattr(new_markup.inline_keyboard[0][0], "callback_data")

    @patch("handlers.gamification_user_handlers.get_service")
    async def test_closes_service_via_context_manager(self, mock_get_service, make_callback):
        """El contexto cierra el servicio al salir."""
        # (no longer patches idempotency_cache - centralized mw in phase 5)
        mock_instance = _mock_gamification_ctx(mock_get_service, BroadcastService)
        mock_instance.check_and_register_reaction = AsyncMock(
            return_value={"success": False, "reason": "duplicate"}
        )
        cb = make_callback(data="react:1:2")

        from handlers.gamification_user_handlers import handle_reaction

        await handle_reaction(cb, self._make_callback_data())

        mock_get_service.return_value.__exit__.assert_called_once()

    @pytest.mark.parametrize(
        "markup_result",
        [False, True],
        ids=["markup_failure", "message_not_modified"],
    )
    @patch("handlers.gamification_user_handlers.get_service")
    async def test_answers_callback_when_markup_update_fails(
        self, mock_get_service, make_callback, markup_result
    ):
        """Besitos ya acreditados: callback.answer() aunque falle o no modifique el markup."""
        mock_instance = _mock_gamification_ctx(mock_get_service, BroadcastService)
        mock_instance.check_and_register_reaction = AsyncMock(
            return_value={"success": True, "besitos_awarded": 5}
        )
        mock_instance.update_reaction_message = AsyncMock(return_value=markup_result)
        mock_instance.get_broadcast.return_value = MagicMock(
            has_reactions=True, channel_id=-100, message_id=42
        )
        mock_instance.get_selected_emoji_ids.return_value = [1]
        mock_instance.get_reactions_by_broadcast.return_value = []
        mock_instance.get_reaction_emoji.return_value = MagicMock(emoji="💋")
        cb = make_callback(data="react:1:2")

        from handlers.gamification_user_handlers import handle_reaction

        await handle_reaction(cb, self._make_callback_data())

        cb.answer.assert_called_with("¡+5 besitos! 💋")

    async def test_handles_missing_message(self, make_callback):
        """Si callback.message es None, responde con error sin llamar al servicio."""
        cb = make_callback(data="react:1:2")
        cb.message = None

        with patch("handlers.gamification_user_handlers.get_service") as mock_get_service:
            from handlers.gamification_user_handlers import handle_reaction

            await handle_reaction(cb, self._make_callback_data())

            mock_get_service.assert_not_called()

        cb.answer.assert_called_with(
            "No pudimos procesar tu reacción. Inténtalo de nuevo.", show_alert=True
        )

    @pytest.mark.parametrize(
        "reason,expected_message",
        [
            ("duplicate", "Ya reaccionaste a este mensaje"),
            ("credit_failed", "No pudimos registrar tu reacción. Inténtalo de nuevo."),
            ("invalid_broadcast", "Este mensaje ya no está disponible para reaccionar."),
            ("message_mismatch", "Este mensaje ya no está disponible para reaccionar."),
            ("no_reactions", "Este mensaje no acepta reacciones."),
            ("inactive_emoji", "Esta reacción no está disponible en este mensaje."),
            ("emoji_not_allowed", "Esta reacción no está disponible en este mensaje."),
            ("invalid_emoji", "Emoji no válido."),
            ("error", "No pudimos procesar tu reacción. Inténtalo de nuevo."),
        ],
    )
    @patch("handlers.gamification_user_handlers.get_service")
    async def test_shows_failure_message_per_reason(
        self, mock_get_service, make_callback, reason, expected_message
    ):
        """Cada reason del servicio muestra el mensaje Lucien correcto."""
        mock_instance = _mock_gamification_ctx(mock_get_service, BroadcastService)
        mock_instance.check_and_register_reaction = AsyncMock(
            return_value={"success": False, "reason": reason}
        )
        cb = make_callback(data="react:1:2")

        from handlers.gamification_user_handlers import handle_reaction

        await handle_reaction(cb, self._make_callback_data())

        cb.answer.assert_called_with(expected_message, show_alert=True)


class TestReactionFailureMessage:
    """Tests para el helper puro reaction_failure_message."""

    @pytest.mark.parametrize(
        "reason,expected",
        [
            ("duplicate", "Ya reaccionaste a este mensaje"),
            ("credit_failed", "No pudimos registrar tu reacción. Inténtalo de nuevo."),
            ("unknown_reason", "No pudimos procesar tu reacción. Inténtalo de nuevo."),
        ],
    )
    def test_maps_reason_to_message(self, reason, expected):
        from handlers.gamification_user_handlers import reaction_failure_message

        assert reaction_failure_message(reason) == expected


class TestCalculateEmojiCountsFromReactions:
    """Tests para el helper puro extraído de handle_reaction (Item 2)."""

    def test_returns_empty_dict_for_no_reactions(self):
        from handlers.gamification_user_handlers import calculate_emoji_counts_from_reactions

        assert calculate_emoji_counts_from_reactions([]) == {}

    def test_counts_single_reaction(self):
        from handlers.gamification_user_handlers import calculate_emoji_counts_from_reactions

        r = model_mock(BroadcastReaction, reaction_emoji=MagicMock(id=7))
        assert calculate_emoji_counts_from_reactions([r]) == {7: 1}

    def test_aggregates_multiple_reactions_same_emoji(self):
        from handlers.gamification_user_handlers import calculate_emoji_counts_from_reactions

        r1 = model_mock(BroadcastReaction, reaction_emoji=MagicMock(id=1))
        r2 = model_mock(BroadcastReaction, reaction_emoji=MagicMock(id=1))
        r3 = model_mock(BroadcastReaction, reaction_emoji=MagicMock(id=2))
        assert calculate_emoji_counts_from_reactions([r1, r2, r3]) == {1: 2, 2: 1}

    def test_ignores_reactions_without_reaction_emoji(self):
        from handlers.gamification_user_handlers import calculate_emoji_counts_from_reactions

        r = model_mock(BroadcastReaction, reaction_emoji=None)
        assert calculate_emoji_counts_from_reactions([r]) == {}

    def test_returns_dict_int_int(self):
        from handlers.gamification_user_handlers import calculate_emoji_counts_from_reactions

        r = model_mock(BroadcastReaction, reaction_emoji=MagicMock(id=3))
        result = calculate_emoji_counts_from_reactions([r])
        assert isinstance(result, dict)
        assert all(isinstance(k, int) and isinstance(v, int) for k, v in result.items())
