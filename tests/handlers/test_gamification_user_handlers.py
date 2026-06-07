"""
Tests unitarios para gamification_user_handlers.

Verifica que los handlers:
1. Llaman al servicio correcto con los parámetros adecuados
2. Responden con el mensaje esperado
3. Manejan correctamente los errores del servicio
4. Cierran el servicio (close) en todos los casos
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime

pytestmark = [pytest.mark.unit]


class TestShowBalance:
    """Tests para show_balance - consulta de saldo de besitos."""

    @patch("handlers.gamification_user_handlers.BesitoService")
    async def test_calls_service_with_user_id(self, mock_besito, make_callback):
        """Llama a get_balance_with_stats con el user_id correcto."""
        mock_besito.return_value.get_balance_with_stats.return_value = {
            "balance": 500, "total_earned": 1000, "total_spent": 500
        }
        cb = make_callback(data="my_balance")

        from handlers.gamification_user_handlers import show_balance
        await show_balance(cb)

        mock_besito.return_value.get_balance_with_stats.assert_called_once_with(123456789)

    @patch("handlers.gamification_user_handlers.BesitoService")
    async def test_displays_balance_correctly(self, mock_besito, make_callback):
        """El texto de respuesta incluye el saldo del usuario."""
        mock_besito.return_value.get_balance_with_stats.return_value = {
            "balance": 500, "total_earned": 1000, "total_spent": 500
        }
        cb = make_callback(data="my_balance")

        from handlers.gamification_user_handlers import show_balance
        await show_balance(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "500" in text
        assert "1000" in text

    @patch("handlers.gamification_user_handlers.BesitoService")
    async def test_calls_answer(self, mock_besito, make_callback):
        """Siempre llama a callback.answer()."""
        mock_besito.return_value.get_balance_with_stats.return_value = {
            "balance": 500, "total_earned": 1000, "total_spent": 500
        }
        cb = make_callback(data="my_balance")

        from handlers.gamification_user_handlers import show_balance
        await show_balance(cb)

        cb.answer.assert_called_once()

    @patch("handlers.gamification_user_handlers.BesitoService")
    async def test_closes_service(self, mock_besito, make_callback):
        """El servicio se cierra después de usar."""
        mock_besito.return_value.get_balance_with_stats.return_value = {
            "balance": 500, "total_earned": 1000, "total_spent": 500
        }
        cb = make_callback(data="my_balance")

        from handlers.gamification_user_handlers import show_balance
        await show_balance(cb)

        mock_besito.return_value.close.assert_called_once()


class TestTransactionHistory:
    """Tests para show_transaction_history."""

    @patch("handlers.gamification_user_handlers.BesitoService")
    async def test_empty_history_shows_empty_message(self, mock_besito, make_callback):
        """Cuando no hay transacciones, muestra mensaje de historial vacío."""
        mock_besito.return_value.get_transaction_history.return_value = []
        cb = make_callback(data="transaction_history")

        from handlers.gamification_user_handlers import show_transaction_history
        await show_transaction_history(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "vacío" in text.lower()

    @patch("handlers.gamification_user_handlers.BesitoService")
    async def test_calls_service_with_correct_args(self, mock_besito, make_callback):
        """Llama a get_transaction_history con el user_id y limit=10."""
        mock_besito.return_value.get_transaction_history.return_value = []
        cb = make_callback(data="transaction_history")

        from handlers.gamification_user_handlers import show_transaction_history
        await show_transaction_history(cb)

        mock_besito.return_value.get_transaction_history.assert_called_once_with(
            123456789, limit=10
        )

    @patch("handlers.gamification_user_handlers.BesitoService")
    async def test_displays_transactions(self, mock_besito, make_callback):
        """Muestra las transacciones formateadas correctamente."""
        mock_tx = MagicMock()
        mock_tx.amount = 50
        mock_tx.created_at = datetime(2024, 6, 15, 10, 30)
        mock_tx.source = MagicMock()
        mock_tx.source.value = "daily_gift"

        mock_besito.return_value.get_transaction_history.return_value = [mock_tx]
        cb = make_callback(data="transaction_history")

        from handlers.gamification_user_handlers import show_transaction_history
        await show_transaction_history(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "+50" in text
        assert "Regalo diario" in text

    @patch("handlers.gamification_user_handlers.BesitoService")
    async def test_closes_service(self, mock_besito, make_callback):
        """El servicio se cierra después de usar."""
        mock_besito.return_value.get_transaction_history.return_value = []
        cb = make_callback(data="transaction_history")

        from handlers.gamification_user_handlers import show_transaction_history
        await show_transaction_history(cb)

        mock_besito.return_value.close.assert_called_once()


class TestDailyGiftMenu:
    """Tests para daily_gift_menu."""

    @patch("handlers.gamification_user_handlers.DailyGiftService")
    async def test_shows_claim_button_when_available(self, mock_gift, make_callback):
        """Cuando can_claim=True, muestra botón de reclamar."""
        mock_gift.return_value.can_claim.return_value = (True, None, "Puedes reclamar")
        mock_gift.return_value.get_gift_amount.return_value = 10
        cb = make_callback(data="daily_gift")

        from handlers.gamification_user_handlers import daily_gift_menu
        await daily_gift_menu(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Reclamar" in text or "10" in text

    @patch("handlers.gamification_user_handlers.DailyGiftService")
    async def test_shows_wait_message_when_not_available(self, mock_gift, make_callback):
        """Cuando can_claim=False, muestra mensaje de espera."""
        mock_gift.return_value.can_claim.return_value = (
            False, 3600, "Vuelve en 1 hora"
        )
        cb = make_callback(data="daily_gift")

        from handlers.gamification_user_handlers import daily_gift_menu
        await daily_gift_menu(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Vuelve" in text

    @patch("handlers.gamification_user_handlers.DailyGiftService")
    async def test_closes_service(self, mock_gift, make_callback):
        """El servicio se cierra después de usar."""
        mock_gift.return_value.can_claim.return_value = (True, None, "Puedes reclamar")
        cb = make_callback(data="daily_gift")

        from handlers.gamification_user_handlers import daily_gift_menu
        await daily_gift_menu(cb)

        mock_gift.return_value.close.assert_called_once()


class TestClaimDailyGift:
    """Tests para claim_daily_gift."""

    @patch("handlers.gamification_user_handlers.DailyGiftService")
    async def test_successful_claim_shows_success(self, mock_gift, make_callback):
        """Cuando claim_gift retorna éxito, muestra mensaje positivo."""
        mock_gift.return_value.claim_gift.return_value = (
            True, 10, "Has recibido 10 besitos"
        )
        cb = make_callback(data="claim_gift")

        from handlers.gamification_user_handlers import claim_daily_gift
        await claim_daily_gift(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "reclamado" in text.lower() or "besitos" in text

    @patch("handlers.gamification_user_handlers.DailyGiftService")
    async def test_failed_claim_shows_error(self, mock_gift, make_callback):
        """Cuando claim_gift retorna fallo, muestra mensaje de error."""
        mock_gift.return_value.claim_gift.return_value = (
            False, 0, "Ya reclamaste hoy"
        )
        cb = make_callback(data="claim_gift")

        from handlers.gamification_user_handlers import claim_daily_gift
        await claim_daily_gift(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Ya reclamaste" in text

    @patch("handlers.gamification_user_handlers.DailyGiftService")
    async def test_calls_service_with_user_id(self, mock_gift, make_callback):
        """Llama a claim_gift con el user_id correcto."""
        mock_gift.return_value.claim_gift.return_value = (True, 10, "OK")
        cb = make_callback(data="claim_gift")

        from handlers.gamification_user_handlers import claim_daily_gift
        await claim_daily_gift(cb)

        mock_gift.return_value.claim_gift.assert_called_once_with(123456789)

    @patch("handlers.gamification_user_handlers.DailyGiftService")
    async def test_closes_service(self, mock_gift, make_callback):
        """El servicio se cierra después de usar."""
        mock_gift.return_value.claim_gift.return_value = (True, 10, "OK")
        cb = make_callback(data="claim_gift")

        from handlers.gamification_user_handlers import claim_daily_gift
        await claim_daily_gift(cb)

        mock_gift.return_value.close.assert_called_once()


class TestHandleReaction:
    """Tests para handle_reaction - reacciones a broadcasts."""

    def _make_callback_data(self, broadcast_id=1, emoji_id=2):
        from keyboards.callback_data import ReactionCallback
        return ReactionCallback(broadcast_id=broadcast_id, emoji_id=emoji_id)

    # test_skips_when_duplicate_callback removed in gsd-mw-hardening phase 5
    # (idempotency now centralized in IdempotencyMiddleware; handler no longer has the guard)

    @patch("handlers.gamification_user_handlers.BroadcastService")
    async def test_registers_reaction(
        self, mock_broadcast, make_callback
    ):
        """Llama a check_and_register_reaction con parámetros correctos."""
        # (idempotency_cache patch removed - phase 5 centralized in middleware)
        mock_instance = mock_broadcast.return_value
        mock_instance.check_and_register_reaction = AsyncMock(return_value={
            "besitos_awarded": 5
        })
        mock_instance.get_broadcast.return_value = MagicMock(has_reactions=False)
        cb = make_callback(data="react:1:2")

        from handlers.gamification_user_handlers import handle_reaction
        await handle_reaction(cb, self._make_callback_data())

        mock_instance.check_and_register_reaction.assert_called_once()
        _, kwargs = mock_instance.check_and_register_reaction.call_args
        assert kwargs["broadcast_id"] == 1
        assert kwargs["emoji_id"] == 2
        assert kwargs["user_id"] == 123456789

    @patch("handlers.gamification_user_handlers.BroadcastService")
    async def test_shows_besitos_awarded(
        self, mock_broadcast, make_callback
    ):
        """Responde con la cantidad de besitos ganados."""
        # (no longer patches idempotency_cache - centralized mw in phase 5)
        mock_instance = mock_broadcast.return_value
        mock_instance.check_and_register_reaction = AsyncMock(return_value={
            "besitos_awarded": 5
        })
        mock_instance.get_broadcast.return_value = MagicMock(has_reactions=False)
        cb = make_callback(data="react:1:2")

        from handlers.gamification_user_handlers import handle_reaction
        await handle_reaction(cb, self._make_callback_data())

        cb.answer.assert_called_with("¡+5 besitos! 💋")

    @patch("handlers.gamification_user_handlers.BroadcastService")
    async def test_shows_alert_when_already_reacted(
        self, mock_broadcast, make_callback
    ):
        """Si el usuario ya reaccionó, muestra alerta."""
        # (no longer patches idempotency_cache - centralized mw in phase 5)
        mock_instance = mock_broadcast.return_value
        mock_instance.check_and_register_reaction = AsyncMock(return_value=None)
        cb = make_callback(data="react:1:2")

        from handlers.gamification_user_handlers import handle_reaction
        await handle_reaction(cb, self._make_callback_data())

        cb.answer.assert_called_with("Ya reaccionaste a este mensaje", show_alert=True)

    @patch("handlers.gamification_user_handlers.BroadcastService")
    async def test_updates_reaction_counts(
        self, mock_broadcast, make_callback
    ):
        """Cuando has_reactions=True, actualiza los contadores."""
        # (no longer patches idempotency_cache - centralized mw in phase 5)
        mock_instance = mock_broadcast.return_value
        mock_instance.check_and_register_reaction = AsyncMock(return_value={
            "besitos_awarded": 5
        })
        mock_instance.update_reaction_message = AsyncMock()
        mock_instance.get_broadcast.return_value = MagicMock(
            has_reactions=True, channel_id=-100, message_id=42
        )
        mock_instance.get_selected_emoji_ids.return_value = [1, 2]
        mock_instance.get_reactions_by_broadcast.return_value = []
        mock_instance.get_reaction_emoji.side_effect = [
            MagicMock(emoji="💋"), MagicMock(emoji="❤️")
        ]
        cb = make_callback(data="react:1:2")

        from handlers.gamification_user_handlers import handle_reaction
        await handle_reaction(cb, self._make_callback_data())

        mock_instance.update_reaction_message.assert_called_once()

    @patch("handlers.gamification_user_handlers.BroadcastService")
    async def test_closes_service(
        self, mock_broadcast, make_callback
    ):
        """El servicio se cierra después de usar."""
        # (no longer patches idempotency_cache - centralized mw in phase 5)
        mock_instance = mock_broadcast.return_value
        mock_instance.check_and_register_reaction = AsyncMock(return_value=None)
        cb = make_callback(data="react:1:2")

        from handlers.gamification_user_handlers import handle_reaction
        await handle_reaction(cb, self._make_callback_data())

        mock_instance.close.assert_called_once()
