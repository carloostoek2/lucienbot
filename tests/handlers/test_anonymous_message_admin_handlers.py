"""
Tests for anonymous_message_admin_handlers — view marks unread as read.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from keyboards.callback_data import AnonViewCallback
from models.models import AnonymousMessageStatus

pytestmark = [pytest.mark.unit]


@pytest.mark.asyncio
@patch("handlers.anonymous_message_admin_handlers.AnonymousMessageService")
async def test_view_anonymous_message_marks_unread_as_read(
    mock_service_cls, make_callback, make_user
):
    """view_anonymous_message must assign enum status, not mutate Enum.value."""
    from unittest.mock import MagicMock

    from handlers.anonymous_message_admin_handlers import view_anonymous_message

    admin = make_user(user_id=42)
    cb = make_callback(user=admin)
    cb_data = AnonViewCallback(message_id=7)

    msg = MagicMock()
    msg.status = AnonymousMessageStatus.UNREAD
    msg.content = "susurro vip"
    msg.created_at = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
    msg.admin_reply = None

    svc = mock_service_cls.return_value
    svc.get_message.return_value = msg
    svc.mark_as_read.return_value = True

    await view_anonymous_message(cb, cb_data)

    svc.mark_as_read.assert_called_once_with(7, 42)
    assert msg.status == AnonymousMessageStatus.READ
    # Regression: never mutate enum .value (raises AttributeError on real enums)
    assert msg.status.value == "read"
    cb.message.edit_text.assert_called_once()
    text = cb.message.edit_text.call_args[0][0]
    assert "susurro vip" in text
    assert "Leído" in text
    cb.answer.assert_called_once()
    svc.close.assert_called_once()


@pytest.mark.asyncio
@patch("handlers.anonymous_message_admin_handlers.AnonymousMessageService")
async def test_view_anonymous_message_already_read_skips_mark(
    mock_service_cls, make_callback, make_user
):
    from unittest.mock import MagicMock

    from handlers.anonymous_message_admin_handlers import view_anonymous_message

    admin = make_user(user_id=42)
    cb = make_callback(user=admin)
    cb_data = AnonViewCallback(message_id=8)

    msg = MagicMock()
    msg.status = AnonymousMessageStatus.READ
    msg.content = "ya visto"
    msg.created_at = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)
    msg.admin_reply = None

    svc = mock_service_cls.return_value
    svc.get_message.return_value = msg

    await view_anonymous_message(cb, cb_data)

    svc.mark_as_read.assert_not_called()
    assert msg.status == AnonymousMessageStatus.READ
    cb.message.edit_text.assert_called_once()
    text = cb.message.edit_text.call_args[0][0]
    assert "ya visto" in text


@pytest.mark.asyncio
@patch("handlers.anonymous_message_admin_handlers.AnonymousMessageService")
async def test_view_anonymous_message_missing_answers_alert(
    mock_service_cls, make_callback, make_user
):
    from handlers.anonymous_message_admin_handlers import view_anonymous_message

    cb = make_callback(user=make_user(user_id=42))
    cb_data = AnonViewCallback(message_id=404)

    svc = mock_service_cls.return_value
    svc.get_message.return_value = None

    await view_anonymous_message(cb, cb_data)

    cb.answer.assert_called_once_with("Mensaje no encontrado", show_alert=True)
    cb.message.edit_text.assert_not_called()
    svc.close.assert_called_once()
