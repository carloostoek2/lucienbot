"""Tests para handlers de broadcast — envío robusto en un solo paso."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Chat, User
from aiogram.types import Message as TgMessage

from handlers.broadcast_handlers import (
    confirm_and_send_broadcast,
    publish_broadcast_to_channel,
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

    @patch("handlers.broadcast_handlers.get_service")
    async def test_tracking_failed_shows_alert_without_success_notify(self, mock_get_service):
        """Mensaje enviado pero message_id no persistido: alerta admin, sin confirmación exitosa."""
        broadcast_svc = MagicMock()
        broadcast_svc.create_broadcast_message.return_value = MagicMock(id=42)
        broadcast_svc.get_reaction_emoji.return_value = MagicMock(id=1, emoji="💋")
        broadcast_svc.update_broadcast_message_id.return_value = False
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = broadcast_svc
        mock_get_service.return_value = mock_ctx

        sent = MagicMock(message_id=888)
        bot = AsyncMock()
        bot.send_message = AsyncMock(return_value=sent)

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
        broadcast_svc.update_broadcast_message_id.assert_called_once_with(42, 888)

        alert_calls = [
            c for c in callback.answer.await_args_list if c.args and "registrar el ID" in c.args[0]
        ]
        assert len(alert_calls) == 1
        assert alert_calls[0].kwargs.get("show_alert") is True

        edit_texts = [str(c.args[0]) for c in callback.message.edit_text.await_args_list if c.args]
        assert not any("exitosamente" in t.lower() for t in edit_texts)

        state.clear.assert_awaited_once()


@pytest.mark.asyncio
class TestPublishBroadcastToChannel:
    async def test_returns_tracking_failed_when_message_id_update_fails(self):
        """publish_broadcast_to_channel retorna tracking_failed si update_broadcast_message_id falla."""
        broadcast_svc = MagicMock()
        broadcast_svc.update_broadcast_message_id.return_value = False

        sent = MagicMock(message_id=999)
        bot = AsyncMock()
        bot.send_message = AsyncMock(return_value=sent)

        broadcast = MagicMock(id=7)
        data = {
            "channel_id": -100123,
            "text": "Hola",
            "has_attachment": False,
            "is_protected": False,
        }

        status, message_id = await publish_broadcast_to_channel(
            bot, broadcast_svc, broadcast, data, None
        )

        assert status == "tracking_failed"
        assert message_id == 999
        broadcast_svc.update_broadcast_message_id.assert_called_once_with(7, 999)


class TestBuildBroadcastPreviewText:
    """Preview del wizard: HTML válido siempre (regresión incidente 2026-09-21)."""

    def test_summary_lines_1_to_1(self):
        from handlers.broadcast_handlers import build_broadcast_preview_text

        info = build_broadcast_preview_text(
            {
                "text": "Hola reino",
                "channel_name": "Los Kinkys",
                "has_attachment": True,
                "attachment_type": "photo",
                "selected_emojis": [1, 2],
                "is_protected": True,
            },
            "Pide información aquí 🖤 (https://t.me/m/tvxkOxswODMx)",
        )
        assert "   • Canal: Los Kinkys" in info
        assert "   • Texto: ✅" in info
        assert "   • Adjunto: ✅ photo" in info
        assert "   • Reacciones: ✅" in info
        assert "   • Botón extra: Pide información aquí 🖤 (https://t.me/m/tvxkOxswODMx)" in info
        assert "   • Protección: 🔒 Sí" in info
        assert "<b>Preview del mensaje:</b>" in info

    def test_empty_optionals_render_crosses(self):
        from handlers.broadcast_handlers import build_broadcast_preview_text

        info = build_broadcast_preview_text({"text": "Hola", "channel_name": "Test"})
        assert "   • Adjunto: ❌" in info
        assert "   • Reacciones: ❌" in info
        assert "   • Botón extra: ❌" in info
        assert "   • Protección: ❌ No" in info

    def test_regression_never_emits_dangling_tag_at_500(self):
        """Caso exacto de producción: corte tras '<' + '...' del preview = '<...'."""
        from handlers.broadcast_handlers import build_broadcast_preview_text

        text = "x" * 499 + "<b>Promo VIP</b>"
        info = build_broadcast_preview_text({"text": text, "channel_name": "Los Kinkys"})
        assert "<..." not in info
        assert info.count("<") == info.count(">")

    def test_truncation_mark_only_when_text_exceeds_limit(self):
        from handlers.broadcast_handlers import build_broadcast_preview_text

        short = build_broadcast_preview_text({"text": "Hola corto", "channel_name": "Test"})
        long = build_broadcast_preview_text({"text": "y" * 700, "channel_name": "Test"})
        assert "Hola corto\n\n---\n\n<i>¿Desea enviar" in short
        assert "y" * 700 not in long
        assert "y" * 500 + "..." in long

    def test_loose_lt_survives_as_escaped_text(self):
        """Cadena completa del wizard: normalización al capturar → preview."""
        from handlers.broadcast_handlers import build_broadcast_preview_text
        from services.broadcast.text_format import resolve_broadcast_text_to_html

        stored = resolve_broadcast_text_to_html("<b>ok</b> y 5 < 10")
        info = build_broadcast_preview_text({"text": stored, "channel_name": "Test"})
        assert "<b>ok</b> y 5 &lt; 10" in info

    def test_channel_name_and_extra_button_are_escaped(self):
        from handlers.broadcast_handlers import build_broadcast_preview_text

        info = build_broadcast_preview_text(
            {"text": "Hola", "channel_name": "Ventas <3"}, "Botón <b>raro</b>"
        )
        assert "   • Canal: Ventas &lt;3" in info
        assert "   • Botón extra: Botón &lt;b&gt;raro&lt;/b&gt;" in info


@pytest.mark.asyncio
class TestShowBroadcastPreview:
    """El preview nunca debe bloquear el wizard por un HTML irreconocible."""

    def _make_callback(self):
        callback = MagicMock()
        callback.message = MagicMock(spec=TgMessage)
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        return callback

    def _make_state(self, text):
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"channel_id": -1001, "text": text})
        return state

    @patch("handlers.broadcast_handlers.get_service")
    async def test_sends_valid_html_with_long_text_and_loose_lt(self, mock_get_service):
        from handlers.broadcast_handlers import show_broadcast_preview
        from services.broadcast.text_format import resolve_broadcast_text_to_html

        mock_get_service.return_value = MagicMock()
        callback = self._make_callback()
        stored = resolve_broadcast_text_to_html("Kinkys <3 " + "x" * 600 + "<b>final</b>")
        state = self._make_state(stored)

        await show_broadcast_preview(callback, state)

        kwargs = callback.message.edit_text.await_args.kwargs
        assert kwargs.get("parse_mode") == "HTML"
        info = callback.message.edit_text.await_args.args[0]
        assert "&lt;3" in info
        assert "<..." not in info
        state.set_state.assert_awaited_once()

    @patch("handlers.broadcast_handlers.get_service")
    async def test_falls_back_to_plain_text_on_parse_error(self, mock_get_service):
        from aiogram.exceptions import TelegramBadRequest

        from handlers.broadcast_handlers import show_broadcast_preview

        mock_get_service.return_value = MagicMock()
        callback = self._make_callback()
        error = TelegramBadRequest(
            method=MagicMock(),
            message='Bad Request: can\'t parse entities: Unsupported start tag "..." '
            "at byte offset 850",
        )
        callback.message.edit_text = AsyncMock(side_effect=[error, None])
        state = self._make_state("<b>Promo</b>")

        await show_broadcast_preview(callback, state)

        assert callback.message.edit_text.await_count == 2
        retry_args = callback.message.edit_text.await_args
        assert "parse_mode" not in retry_args.kwargs
        assert retry_args.kwargs.get("reply_markup") is not None
        assert "Promo" in retry_args.args[0]
        assert "<b>" not in retry_args.args[0]
        state.set_state.assert_awaited_once()

    @patch("handlers.broadcast_handlers.get_service")
    async def test_other_errors_still_propagate(self, mock_get_service):
        from aiogram.exceptions import TelegramBadRequest

        from handlers.broadcast_handlers import show_broadcast_preview

        mock_get_service.return_value = MagicMock()
        callback = self._make_callback()
        callback.message.edit_text = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(), message="Bad Request: chat not found"
            )
        )
        state = self._make_state("Hola")

        with pytest.raises(TelegramBadRequest):
            await show_broadcast_preview(callback, state)


class TestValidateBroadcastContentForSend:
    def test_requires_text_when_no_attachment(self):
        assert validate_broadcast_content_for_send({"text": "  ", "has_attachment": False})

    def test_allows_text_only(self):
        assert (
            validate_broadcast_content_for_send({"text": "Hola", "has_attachment": False}) is None
        )

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
