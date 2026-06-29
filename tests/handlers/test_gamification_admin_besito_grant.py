"""Tests for admin menu besito grant flow (gamification_admin_handlers)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from keyboards.inline_keyboards import back_keyboard


def _mock_besito_ctx(mock_get_service):
    mock_svc = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_svc)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    mock_get_service.return_value = mock_ctx
    return mock_svc


@patch("handlers.gamification_admin_handlers.is_admin", return_value=True)
@patch("handlers.gamification_admin_handlers.get_service")
async def test_confirm_admin_besito_grant_calls_1_svc_and_notifies_visitor(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    """Menu confirm: EXACTLY 1 grant + bot.send_message to visitor."""
    fsm = await make_fsm_context()
    await fsm.update_data(grant_target_user_id=424242, besito_amount=30)

    cb = make_callback(data="admin_besito_grant_confirm")
    cb.bot = AsyncMock()
    cb.bot.send_message = AsyncMock()

    mock_svc = _mock_besito_ctx(mock_get_service)
    mock_svc.grant_manual_admin_besitos.return_value = (True, 130)

    from handlers.gamification_admin_handlers import (
        AdminBesitoGrantStates,
        confirm_admin_besito_grant,
    )

    await fsm.set_state(AdminBesitoGrantStates.confirming)
    await confirm_admin_besito_grant(cb, fsm)

    mock_svc.grant_manual_admin_besitos.assert_called_once_with(424242, 30, cb.from_user.id)
    cb.bot.send_message.assert_called_once()
    call = cb.bot.send_message.call_args
    assert call.kwargs.get("chat_id") == 424242
    assert "30" in call.kwargs.get("text", "")
    assert "gesto especial" in call.kwargs.get("text", "").lower()
    data_after = await fsm.get_data()
    assert data_after == {} or "besito_amount" not in str(data_after)


def test_parse_positive_telegram_user_id_pure():
    from handlers.vip_handlers import parse_positive_telegram_user_id

    assert parse_positive_telegram_user_id("123456789") == 123456789
    assert parse_positive_telegram_user_id("0") is None
    assert parse_positive_telegram_user_id("-1") is None
    assert parse_positive_telegram_user_id("abc") is None


def test_lucien_voice_admin_besitos_granted_notify():
    from utils.lucien_voice import LucienVoice

    text = LucienVoice.admin_besitos_granted_visitor_notify(25, 100)
    assert "25" in text
    assert "100" in text
    assert "Lucien" in text
    assert "gesto especial" in text.lower()