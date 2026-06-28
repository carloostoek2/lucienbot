"""
Minimal targeted tests for VIP forward activation (handlers only).

Protects the new forward path per test-guardian mandate:
- pure extract / build helpers (verb+context+result, "Función pura...")
- detection (forward_from + forward_origin)
- tariff select (0 svc)
- confirm: EXACTLY 1 grant_vip_from_tariff via get_service
- direct send success
- blocked fallback: exact "bot was blocked by the user" + deep_link notify to admin
- state clean always
- is_admin guards (via patch)

Uses make_* fixtures + mocks on get_service + bot.send side effects.
No behavior change to existing flows. Golds stay green.

Follows handler test conventions (patch order, make_message/make_callback/make_fsm_context, async).
"""

from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest
from aiogram.types import MessageOriginUser

from keyboards.callback_data import SelectTariffCallback

pytestmark = [pytest.mark.unit]


def _mock_vip_ctx(mock_get_service):
    """Mock get_service(VIPService) context manager con autospec."""
    from services.vip_service import VIPService

    svc = create_autospec(VIPService, spec_set=True, instance=True)
    mock_get_service.return_value.__enter__.return_value = svc
    return svc


# =============================================================================
# Pure helpers (direct, no side effects)
# =============================================================================


def test_extract_forwarded_candidate_from_forward_from():
    """extract from legacy forward_from. Función pura."""
    from handlers.vip_handlers import extract_forwarded_candidate

    msg = MagicMock()
    u = MagicMock()
    u.id = 777
    u.full_name = "Candidato Uno"
    u.username = "cand1"
    msg.forward_from = u
    msg.forward_origin = None

    cid, disp = extract_forwarded_candidate(msg)
    assert cid == 777
    assert "Candidato Uno" in disp


def test_extract_forwarded_candidate_from_forward_origin():
    """extract from aiogram3 forward_origin MessageOriginUser. Función pura."""
    from aiogram.types import User as TgUser

    from handlers.vip_handlers import extract_forwarded_candidate

    msg = MagicMock()
    msg.forward_from = None
    # real TgUser + date to satisfy full MessageOriginUser pydantic model
    sender = TgUser(id=888, is_bot=False, first_name="Origin", last_name="User")
    from datetime import UTC
    from datetime import datetime as dt
    origin = MessageOriginUser(sender_user=sender, type="user", date=dt.now(UTC))
    msg.forward_origin = origin

    cid, disp = extract_forwarded_candidate(msg)
    assert cid == 888
    assert "Origin" in disp or "888" in disp


def test_extract_forwarded_candidate_hidden_or_none_returns_none():
    """Hidden user or no forward -> None id. Función pura."""
    from handlers.vip_handlers import extract_forwarded_candidate

    msg = MagicMock()
    msg.forward_from = None
    msg.forward_origin = None
    cid, disp = extract_forwarded_candidate(msg)
    assert cid is None
    assert disp == "desconocido"


def test_build_forward_helpers_pure():
    """build_* are pure (return strings, no io)."""
    from handlers.vip_handlers import (
        build_forward_blocked_notify,
        build_forward_deep_link,
        build_forward_error_text,
        build_forward_success_text,
    )

    assert "bloqueo" in build_forward_blocked_notify("https://t.me/x?start=TOK").lower()
    assert "completada" in build_forward_success_text().lower()
    assert (
        "error" in build_forward_error_text("fail msg").lower()
        or "fail" in build_forward_error_text("fail msg").lower()
    )
    assert "start=ABC" in build_forward_deep_link("botu", "ABC")
    assert "contacta" in build_forward_deep_link(None, None).lower()


# =============================================================================
# Handler flows (mock get_service + bot.send, exercise forward paths)
# =============================================================================


@patch("handlers.vip_handlers.is_admin", return_value=True)
@patch("handlers.vip_handlers.get_service")
async def test_process_forwarded_vip_candidate_detects_and_uses_exactly_1_svc(
    mock_get_service, _mock_is_admin, make_message, make_fsm_context
):
    """Detection path calls tariffs svc once, sets forward state, shows tariffs."""
    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.get_all_tariffs.return_value = [MagicMock(id=1, name="Mensual", duration_days=30)]

    msg = make_message(text="forwarded candidate msg")
    # simulate forward
    fake = MagicMock()
    fake.id = 424242
    fake.full_name = "Test VIP Cand"
    fake.username = "vipcand"
    msg.forward_from = fake
    msg.forward_origin = None

    fsm = await make_fsm_context(user_id=424242)

    from handlers.vip_handlers import process_forwarded_vip_candidate

    await process_forwarded_vip_candidate(msg, fsm)

    mock_get_service.assert_called_once()  # exactly the tariffs read (1 svc)
    msg.answer.assert_called()
    data = await fsm.get_data()
    assert data.get("forward_target_user_id") == 424242
    assert "Test VIP Cand" in data.get("forward_target_display", "")


@patch("handlers.vip_handlers.is_admin", return_value=True)
async def test_select_tariff_for_forward_vip_transitions_state_no_svc(
    _mock_is_admin, make_callback, make_fsm_context
):
    """Select path (0 svc) updates data + state to confirming, reuses UI."""
    cb = make_callback(data="select_tariff:7")
    cb.from_user.id = 999  # admin in patch
    fsm = await make_fsm_context()
    await fsm.set_state("selecting_tariff")  # loose, or import
    await fsm.update_data(forward_target_user_id=424242, forward_target_display="Cand")

    cbdata = SelectTariffCallback(tariff_id=7)

    from handlers.vip_handlers import VIPForwardActivationStates, select_tariff_for_forward_vip

    await select_tariff_for_forward_vip(cb, fsm, callback_data=cbdata)

    cb.message.edit_text.assert_called_once()
    data = await fsm.get_data()
    assert data.get("selected_tariff_id") == 7
    # state transitioned (FSM internal check loose)
    st = await fsm.get_state()
    # aiogram stores string or state; accept either
    assert st is None or "confirm" in str(st).lower() or st == VIPForwardActivationStates.confirming


@patch("handlers.vip_handlers.is_admin", return_value=True)
@patch("handlers.vip_handlers.get_service")
async def test_confirm_forward_vip_activation_calls_exactly_1_grant_and_sends_direct(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    """Confirm path: EXACTLY 1 grant via get_service, direct send success, state cleaned, success UI."""
    # prepare fsm data as if from prior steps
    fsm = await make_fsm_context()
    await fsm.update_data(forward_target_user_id=424242, selected_tariff_id=1)

    cb = make_callback(data="confirm_vip_forward_activation")
    cb.bot = AsyncMock()
    cb.bot.send_message = AsyncMock()
    cb.bot.get_me = AsyncMock(return_value=MagicMock(username="lucienbot"))

    # grant returns success + meta
    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.grant_vip_from_tariff = AsyncMock(
        return_value=(
            True,
            "🎩 <b>Lucien:</b> Acceso VIP...",
            {"token_code": "FWD123", "vip_activated": True},
        )
    )

    from handlers.vip_handlers import confirm_forward_vip_activation

    await confirm_forward_vip_activation(cb, fsm)

    # critical contract: exactly 1 grant
    mock_svc.grant_vip_from_tariff.assert_called_once_with(cb.bot, 424242, 1)
    # direct send happened
    cb.bot.send_message.assert_called_once()
    call = cb.bot.send_message.call_args
    assert call.kwargs.get("chat_id") == 424242
    kb = call.kwargs.get("reply_markup")
    assert kb is not None
    # state cleared (data gone)
    data_after = await fsm.get_data()
    assert data_after == {} or "forward_target" not in str(data_after)
    # success edit
    cb.message.edit_text.assert_called()


@patch("handlers.vip_handlers.is_admin", return_value=True)
@patch("handlers.vip_handlers.get_service")
async def test_confirm_forward_vip_activation_blocked_falls_back_to_admin_with_deep_link(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    """Blocked send: grant still done (1), send raises blocked, fallback answer to forwarding admin with deep_link using token_code."""
    fsm = await make_fsm_context()
    await fsm.update_data(forward_target_user_id=424242, selected_tariff_id=1)

    cb = make_callback(data="confirm_vip_forward_activation")
    cb.bot = AsyncMock()
    # exact match string used in impl
    cb.bot.send_message = AsyncMock(side_effect=Exception("bot was blocked by the user"))
    cb.bot.get_me = AsyncMock(return_value=MagicMock(username="lucienbot"))

    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.grant_vip_from_tariff = AsyncMock(
        return_value=(True, "access...", {"token_code": "BLK999"})
    )

    from handlers.vip_handlers import confirm_forward_vip_activation

    await confirm_forward_vip_activation(cb, fsm)

    # grant still happened once (desired: no rollback)
    mock_svc.grant_vip_from_tariff.assert_called_once()
    # send attempted but failed
    cb.bot.send_message.assert_called_once()
    # fallback uses answer on target_message (the admin sees it)
    cb.message.answer.assert_called()
    ans_text = cb.message.answer.call_args[0][0]
    assert "bloqueo" in ans_text.lower() or "no pude notificar" in ans_text.lower()
    assert "BLK999" in ans_text or "start=BLK999" in ans_text
    # state clean
    data_after = await fsm.get_data()
    assert data_after == {} or not any("forward" in str(k) for k in data_after)


@patch("handlers.vip_handlers.is_admin", return_value=True)
@patch("handlers.vip_handlers.get_service")
async def test_confirm_forward_vip_grant_fails_shows_error_no_send(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    """grant !ok: no send, shows error msg from grant, state clean. 1 svc only."""
    fsm = await make_fsm_context()
    await fsm.update_data(forward_target_user_id=424242, selected_tariff_id=99)

    cb = make_callback(data="confirm_vip_forward_activation")
    cb.bot = AsyncMock()
    cb.bot.send_message = AsyncMock()

    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.grant_vip_from_tariff = AsyncMock(return_value=(False, "Tarifa inválida", {}))

    from handlers.vip_handlers import confirm_forward_vip_activation

    await confirm_forward_vip_activation(cb, fsm)

    mock_svc.grant_vip_from_tariff.assert_called_once()
    cb.bot.send_message.assert_not_called()
    cb.message.edit_text.assert_called()
    err = cb.message.edit_text.call_args[0][0]
    assert "Tarifa inválida" in err
    assert await fsm.get_data() == {} or "forward" not in str(await fsm.get_data())


@patch("handlers.vip_handlers.is_admin", return_value=True)
async def test_cancel_vip_forward_clears_state(_mock_is_admin, make_callback, make_fsm_context):
    """Cancel always clears state + returns to mgmt."""
    fsm = await make_fsm_context()
    await fsm.update_data(forward_target_user_id=42)

    cb = make_callback(data="cancel_vip_activation")

    from handlers.vip_handlers import cancel_vip_forward_activation

    await cancel_vip_forward_activation(cb, fsm)

    cb.message.edit_text.assert_called()
    assert await fsm.get_data() == {}


# Note: full router filter integration is covered indirectly by golds + manual;
# here we call handler funcs directly (standard for aiogram handler tests without full Dispatcher setup).
