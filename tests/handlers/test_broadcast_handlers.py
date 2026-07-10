"""Tests para handlers de broadcast — envío robusto en un solo paso."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Chat, Message as TgMessage, User

from handlers.broadcast_handlers import (
    confirm_and_send_broadcast,
    validate_broadcast_content_for_send,
)


def _make_confirm_callback():
    user = User(id=999, is_bot=False, first_name="Admin")
    chat = Chat(id=999, type="private")
    message = MagicMock(spec=TgMessage)
    message.edit_text = AsyncMock()
    message.chat = chat
    callback = MagicMock()
    callback.from_user = user
    callback.message = message
    callback.answer = AsyncMock()
    callback.data = "confirm_broadcast"
    return callback


@pytest.mark.asyncio
class TestConfirmAndSendBroadcast:
    @patch("handlers.broadcast_handlers.get_service")
    async def test_rejects_empty_text_without_attachment(self, mock_get_service):
        """Validación bloquea envío texto vacío sin adjunto (broadcast #20)."""
        mock_ctx = MagicMock()
        mock_get_service.return_value = mock_ctx
        state = AsyncMock()
        state.get_data = AsyncMock(
            return_value={
                "channel_id": -100123,
                "text": "",
                "has_attachment": False,
                "selected_emojis": [1],
            }
        )
        bot = AsyncMock()
        callback = _make_confirm_callback()

        await confirm_and_send_broadcast(callback, state, bot)

        callback.answer.assert_awaited_once()
        alert_text = callback.answer.await_args.args[0] if callback.answer.await_args.args else ""
        assert "texto" in alert_text.lower()
        mock_ctx.__enter__.return_value.create_broadcast_message.assert_not_called()
        bot.send_message.assert_not_awaited()

    @patch("handlers.broadcast_handlers.get_service")
    async def test_sends_with_markup_in_single_step(self, mock_get_service):
        """Un solo send_message con reply_markup; sin edit_message_reply_markup."""
        broadcast_svc = MagicMock()
        broadcast_svc.create_broadcast_message.return_value = MagicMock(id=42)
        broadcast_svc.get_reaction_emoji.return_value = MagicMock(id=1, emoji="💋")
        broadcast_svc.update_broadcast_message_id.return_value = True
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = broadcast_svc
        mock_get_service.return_value = mock_ctx

        sent = MagicMock(message_id=777)
        bot = AsyncMock()
        bot.send_message = AsyncMock(return_value=sent)
        bot.edit_message_reply_markup = AsyncMock()

        state = AsyncMock()
        state.get_data = AsyncMock(
            return_value={
                "channel_id": -100123,
                "channel_name": "Test",
                "text": "Hola reino",
                "has_attachment": False,
                "selected_emojis": [1],
                "is_protected": False,
            }
        )
        state.clear = AsyncMock()
        callback = _make_confirm_callback()

        await confirm_and_send_broadcast(callback, state, bot)

        bot.send_message.assert_awaited_once()
        kwargs = bot.send_message.await_args.kwargs
        assert kwargs.get("reply_markup") is not None
        assert kwargs.get("parse_mode") == "HTML"
        bot.edit_message_reply_markup.assert_not_awaited()
        broadcast_svc.update_broadcast_message_id.assert_called_once_with(42, 777)
        state.clear.assert_awaited_once()

    @patch("handlers.broadcast_handlers.get_service")
    async def test_allows_attachment_with_empty_caption(self, mock_get_service):
        """Foto sin caption es válida y usa send_photo."""
        broadcast_svc = MagicMock()
        broadcast_svc.create_broadcast_message.return_value = MagicMock(id=7)
        broadcast_svc.update_broadcast_message_id.return_value = True
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = broadcast_svc
        mock_get_service.return_value = mock_ctx

        bot = AsyncMock()
        bot.send_photo = AsyncMock(return_value=MagicMock(message_id=55))

        state = AsyncMock()
        state.get_data = AsyncMock(
            return_value={
                "channel_id": -100123,
                "channel_name": "Test",
                "text": "",
                "has_attachment": True,
                "attachment_type": "photo",
                "attachment_file_id": "file_abc",
                "selected_emojis": [],
                "is_protected": False,
            }
        )
        state.clear = AsyncMock()
        callback = _make_confirm_callback()

        await confirm_and_send_broadcast(callback, state, bot)

        bot.send_photo.assert_awaited_once()
        assert bot.send_photo.await_args.kwargs.get("parse_mode") == "HTML"
        bot.send_message.assert_not_awaited()


class TestValidateBroadcastContentForSend:
    def test_requires_text_when_no_attachment(self):
        assert validate_broadcast_content_for_send({"text": "  ", "has_attachment": False})

    def test_allows_text_only(self):
        assert validate_broadcast_content_for_send({"text": "Hola", "has_attachment": False}) is None

    def test_allows_attachment_without_text(self):
        assert (
            validate_broadcast_content_for_send(
                {
                    "text": "",
                    "has_attachment": True,
                    "attachment_file_id": "file_x",
                }
            )
            is None
        )