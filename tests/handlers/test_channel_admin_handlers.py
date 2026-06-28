"""
Tests para channel_handlers — Phase 30 Channel Admin Hardening.
"""

from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

from tests.helpers import model_mock
from models.models import Channel, PendingRequest

import pytest

from handlers.channel_handlers import (
    build_messages_menu_keyboard,
    build_pending_list_text,
    build_pending_requests_keyboard,
    format_pending_request_line,
    parse_custom_message_text,
    parse_wait_minutes,
    truncate_message_preview,
)
from keyboards.callback_data import (
    ApproveAllCallback,
    ApproveOneCallback,
    ConfigMessagesCallback,
    ConfirmRejectCallback,
    PendingPageCallback,
    RejectOneCallback,
)
from services.channel_grant import ApproveAllResult, GrantResult
from services.channel_service import ChannelService

pytestmark = [pytest.mark.unit]


def _mock_channel_ctx(mock_get_service):
    """Mock get_service(ChannelService) context manager con autospec."""
    svc = create_autospec(ChannelService, spec_set=True, instance=True)
    mock_get_service.return_value.__enter__.return_value = svc
    return svc


class TestPureHelpers:
    def test_parse_wait_minutes_valid_invalid(self):
        assert parse_wait_minutes("7") == 7
        assert parse_wait_minutes("1440") == 1440
        assert parse_wait_minutes("0") is None
        assert parse_wait_minutes("2000") is None
        assert parse_wait_minutes("abc") is None

    def test_truncate_message_preview(self):
        assert "(default Lucien)" in truncate_message_preview("")
        long_text = "x" * 200
        assert len(truncate_message_preview(long_text)) == 120

    def test_format_pending_request_line_escapes_html(self):
        req = model_mock(PendingRequest)
        req.username = None
        req.first_name = "<script>"
        req.scheduled_approval_at = MagicMock(strftime=MagicMock(return_value="12:00"))
        line = format_pending_request_line(req, 1)
        assert "<script>" not in line
        assert "&lt;script&gt;" in line

    def test_parse_custom_message_text(self):
        msg = MagicMock()
        msg.text = "  quitar  "
        assert parse_custom_message_text(msg) is None
        msg.text = "   "
        assert parse_custom_message_text(msg) is None
        msg.text = "custom"
        assert parse_custom_message_text(msg) == "custom"
        msg.text = None
        assert parse_custom_message_text(msg) is False

    def test_build_pending_requests_keyboard_pagination(self):
        requests = [
            MagicMock(id=i, user_id=100 + i, username=f"u{i}", first_name=None) for i in range(8)
        ]
        kb = build_pending_requests_keyboard(
            channel_db_id=1, requests=requests, page=0, total_count=10
        )
        approve_rows = [
            row for row in kb.inline_keyboard if len(row) == 2 and row[0].text.startswith("✅")
        ]
        assert len(approve_rows) == 8
        flat = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert PendingPageCallback(channel_id=1, page=1).pack() in flat

    def test_build_pending_list_text_uses_format_line(self):
        req = model_mock(PendingRequest)
        req.username = "user1"
        req.first_name = None
        req.scheduled_approval_at = MagicMock(strftime=MagicMock(return_value="09:00"))
        text = build_pending_list_text(1, [req], page=0, total_pages=1)
        assert "user1" in text

    def test_build_messages_menu_keyboard_renders(self):
        kb = build_messages_menu_keyboard(42)
        flat = [btn.text for row in kb.inline_keyboard for btn in row]
        assert "📨 Editar ritual" in flat
        assert "👋 Editar bienvenida" in flat
        assert "👁 Ver actuales" in flat
        assert "♻️ Restaurar defaults" in flat


class TestAdminGuards:
    @patch("handlers.channel_handlers.get_service")
    @patch("handlers.channel_handlers.is_admin", return_value=False)
    async def test_non_admin_callback_rejected(
        self, _mock_is_admin, mock_get_service, make_callback
    ):
        """list_channels deniega no-admin sin llamar al servicio."""
        from handlers.channel_handlers import list_channels

        cb = make_callback(data="list_channels")
        await list_channels(cb)

        cb.answer.assert_called_once_with("Acceso denegado", show_alert=True)
        mock_get_service.assert_not_called()

    @patch("handlers.channel_handlers.is_admin", return_value=False)
    @patch("handlers.channel_handlers.get_service")
    async def test_non_admin_message_fsm_rejected(
        self, mock_get_service, _mock_is_admin, make_message
    ):
        """FSM wait custom deniega no-admin y limpia state."""
        from handlers.channel_handlers import process_custom_wait_time

        msg = make_message(text="7")
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"channel_id": 1})
        state.clear = AsyncMock()

        await process_custom_wait_time(msg, state)

        msg.answer.assert_called_once()
        state.clear.assert_called_once()
        mock_get_service.assert_not_called()


class TestConfigMessagesHandlers:
    @patch("handlers.channel_handlers.get_service")
    async def test_config_messages_menu_renders(self, mock_get_service, make_callback):
        from handlers.channel_handlers import config_messages_menu

        mock_channel = model_mock(Channel)
        mock_channel.channel_name = "Test Vestíbulo"
        mock_svc = _mock_channel_ctx(mock_get_service)
        mock_svc.get_channel_by_db_id.return_value = mock_channel

        cb = make_callback()
        cb_data = ConfigMessagesCallback(channel_id=5)
        state = AsyncMock()

        await config_messages_menu(cb, state, cb_data)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Test Vestíbulo" in text

    @patch("handlers.channel_handlers.get_service")
    async def test_save_welcome_message_calls_service(self, mock_get_service, make_message):
        from handlers.channel_handlers import save_welcome_message

        mock_svc = _mock_channel_ctx(mock_get_service)

        msg = make_message(text="Bienvenida custom")
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"channel_id": 3})

        with patch("handlers.channel_handlers.is_admin", return_value=True):
            await save_welcome_message(msg, state)

        mock_svc.update_welcome_message.assert_called_once_with(3, "Bienvenida custom")

    @patch("handlers.channel_handlers.get_service")
    async def test_save_welcome_message_blank_saves_none(self, mock_get_service, make_message):
        from handlers.channel_handlers import save_welcome_message

        mock_svc = _mock_channel_ctx(mock_get_service)

        msg = make_message(text="   ")
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"channel_id": 3})

        with patch("handlers.channel_handlers.is_admin", return_value=True):
            await save_welcome_message(msg, state)

        mock_svc.update_welcome_message.assert_called_once_with(3, None)


class TestIndividualApproveReject:
    @patch("handlers.channel_handlers._render_pending_list", new_callable=AsyncMock)
    @patch("handlers.channel_handlers.get_service")
    async def test_approve_one_calls_service_with_bot(
        self, mock_get_service, mock_render, make_callback
    ):
        from handlers.channel_handlers import approve_one_request

        mock_req = model_mock(PendingRequest)
        mock_req.username = "testuser"
        mock_req.first_name = None
        mock_svc = _mock_channel_ctx(mock_get_service)
        mock_svc.get_valid_pending_request.return_value = mock_req
        mock_svc.approve_request_now = AsyncMock(
            return_value=GrantResult(success=True, request_id=10)
        )

        cb = make_callback()
        cb_data = ApproveOneCallback(request_id=10, channel_id=2, page=1)

        await approve_one_request(cb, cb_data)

        mock_svc.approve_request_now.assert_called_once_with(10, 2, cb.bot)
        mock_render.assert_called_once_with(cb, 2, page=1)
        cb.answer.assert_called_once()
        toast = cb.answer.call_args[0][0]
        assert "<b>" not in toast
        assert "admitido" in toast

    @patch("handlers.channel_handlers.get_service")
    async def test_approve_one_none_request_plain_toast(
        self, mock_get_service, make_callback
    ):
        """approve_one con request inválida usa toast plain-text sin HTML."""
        from handlers.channel_handlers import approve_one_request

        mock_svc = _mock_channel_ctx(mock_get_service)
        mock_svc.get_valid_pending_request.return_value = None

        cb = make_callback()
        cb_data = ApproveOneCallback(request_id=99, channel_id=2, page=0)

        await approve_one_request(cb, cb_data)

        cb.answer.assert_called_once()
        toast = cb.answer.call_args[0][0]
        assert "<" not in toast
        mock_svc.approve_request_now.assert_not_called()

    @patch("handlers.channel_handlers.get_service")
    async def test_reject_one_requires_confirmation(self, mock_get_service, make_callback):
        from handlers.channel_handlers import reject_one_request

        mock_req = model_mock(PendingRequest)
        mock_req.username = "testuser"
        mock_req.first_name = "Test"
        mock_svc = _mock_channel_ctx(mock_get_service)
        mock_svc.get_valid_pending_request.return_value = mock_req

        cb = make_callback()
        cb_data = RejectOneCallback(request_id=7, channel_id=4, page=2)

        await reject_one_request(cb, cb_data)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "@testuser" in text
        confirm_cb = ConfirmRejectCallback(request_id=7, channel_id=4, page=2).pack()
        cancel_cb = PendingPageCallback(channel_id=4, page=2).pack()
        markup = cb.message.edit_text.call_args[1]["reply_markup"]
        flat = [btn.callback_data for row in markup.inline_keyboard for btn in row]
        assert confirm_cb in flat
        assert cancel_cb in flat

    @patch("handlers.channel_handlers._render_pending_list", new_callable=AsyncMock)
    @patch("handlers.channel_handlers.get_service")
    async def test_confirm_reject_success(self, mock_get_service, mock_render, make_callback):
        from handlers.channel_handlers import confirm_reject_request

        mock_svc = _mock_channel_ctx(mock_get_service)
        mock_svc.reject_request_now = AsyncMock(return_value=True)

        cb = make_callback()
        cb_data = ConfirmRejectCallback(request_id=5, channel_id=3, page=1)

        await confirm_reject_request(cb, cb_data)

        mock_svc.reject_request_now.assert_called_once_with(5, 3, cb.bot)
        mock_render.assert_called_once_with(cb, 3, page=1)
        cb.answer.assert_called_once()

    @patch("handlers.channel_handlers._render_pending_list", new_callable=AsyncMock)
    @patch("handlers.channel_handlers.get_service")
    async def test_confirm_reject_failure_single_answer(
        self, mock_get_service, mock_render, make_callback
    ):
        from handlers.channel_handlers import confirm_reject_request

        mock_svc = _mock_channel_ctx(mock_get_service)
        mock_svc.reject_request_now = AsyncMock(return_value=False)

        cb = make_callback()
        cb_data = ConfirmRejectCallback(request_id=5, channel_id=3, page=0)

        await confirm_reject_request(cb, cb_data)

        cb.answer.assert_called_once()
        assert cb.answer.call_args[1].get("show_alert") is True
        assert "<" not in cb.answer.call_args[0][0]

    @patch("handlers.channel_handlers.get_service")
    async def test_confirm_reject_success_plain_toast(
        self, mock_get_service, make_callback
    ):
        from handlers.channel_handlers import confirm_reject_request

        mock_req = model_mock(PendingRequest)
        mock_req.username = "doneuser"
        mock_req.first_name = None
        mock_svc = _mock_channel_ctx(mock_get_service)
        mock_svc.get_valid_pending_request.return_value = mock_req
        mock_svc.reject_request_now = AsyncMock(return_value=True)

        cb = make_callback()
        cb_data = ConfirmRejectCallback(request_id=5, channel_id=3, page=1)

        with patch(
            "handlers.channel_handlers._render_pending_list", new_callable=AsyncMock
        ):
            await confirm_reject_request(cb, cb_data)

        toast = cb.answer.call_args[0][0]
        assert "<" not in toast
        assert "doneuser" in toast


class TestApproveAllHandler:
    @patch("handlers.channel_handlers.get_service")
    async def test_approve_all_requests_surfaces_errors(self, mock_get_service, make_callback):
        from handlers.channel_handlers import approve_all_requests

        mock_svc = _mock_channel_ctx(mock_get_service)
        mock_svc.approve_all_pending_now = AsyncMock(
            return_value=ApproveAllResult(approved=1, failed=1, errors=["req 2: boom"])
        )

        cb = make_callback()
        cb_data = ApproveAllCallback(channel_id=9)

        await approve_all_requests(cb, cb_data)

        text = cb.message.edit_text.call_args[0][0]
        assert "req 2" in text
        cb.answer.assert_called_once()

    @patch("handlers.channel_handlers.get_service")
    async def test_approve_all_empty_batch(self, mock_get_service, make_callback):
        from handlers.channel_handlers import approve_all_requests

        mock_svc = _mock_channel_ctx(mock_get_service)
        mock_svc.count_pending_requests.return_value = 0

        cb = make_callback()
        cb_data = ApproveAllCallback(channel_id=9)

        await approve_all_requests(cb, cb_data)

        mock_svc.approve_all_pending_now.assert_not_called()
        toast = cb.answer.call_args[0][0]
        assert "<" not in toast
        assert "pendientes" in toast.lower()

    @patch("handlers.channel_handlers.get_service")
    async def test_approve_all_all_failed_alert(self, mock_get_service, make_callback):
        from handlers.channel_handlers import approve_all_requests

        mock_svc = _mock_channel_ctx(mock_get_service)
        mock_svc.approve_all_pending_now = AsyncMock(
            return_value=ApproveAllResult(approved=0, failed=2, errors=["req 1: err"])
        )

        cb = make_callback()
        cb_data = ApproveAllCallback(channel_id=9)

        await approve_all_requests(cb, cb_data)

        cb.answer.assert_called_once()
        assert cb.answer.call_args[1].get("show_alert") is True
        assert "<" not in cb.answer.call_args[0][0]


class TestPendingPagination:
    @patch("handlers.channel_handlers.get_service")
    async def test_pending_list_pagination(self, mock_get_service, make_callback):
        from handlers.channel_handlers import pending_page_nav

        mock_svc = _mock_channel_ctx(mock_get_service)
        mock_svc.count_pending_requests.return_value = 20
        mock_svc.get_pending_requests_by_channel.return_value = [MagicMock()] * 20

        cb = make_callback()
        cb_data = PendingPageCallback(channel_id=1, page=1)

        await pending_page_nav(cb, cb_data)

        cb.message.edit_text.assert_called_once()
        assert mock_svc.count_pending_requests.called
