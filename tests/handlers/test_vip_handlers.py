"""
Minimal targeted tests for VIP/besitos forward activation (handlers only).

Protects forward paths per test-guardian mandate:
- pure extract / build helpers (verb+context+result, "Función pura...")
- detection (forward_from + forward_origin) → action menu (0 svc)
- VIP branch: tariff select (0 svc), confirm (1 svc grant)
- besitos branch: amount parse, confirm (1 svc grant)
- direct send success + blocked fallback
- state clean always
- is_admin guards (via patch)
"""

from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest
from aiogram.types import MessageOriginUser

from keyboards.callback_data import (
    ForwardActionCallback,
    ForwardCancelCallback,
    ForwardConfirmCallback,
    SelectTariffCallback,
)

pytestmark = [pytest.mark.unit]


def _mock_vip_ctx(mock_get_service):
    """Mock get_service(VIPService) context manager con autospec."""
    from services.vip_service import VIPService

    svc = create_autospec(VIPService, spec_set=True, instance=True)
    mock_get_service.return_value.__enter__.return_value = svc
    return svc


def _mock_besito_ctx(mock_get_service):
    """Mock get_service(BesitoService) context manager con autospec."""
    from services.besito_service import BesitoService

    svc = create_autospec(BesitoService, spec_set=True, instance=True)
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
    """build_* VIP helpers are pure."""
    from handlers.vip_handlers import (
        build_forward_blocked_notify,
        build_forward_bot_access_link,
        build_forward_deep_link,
        build_forward_error_text,
        build_forward_manual_delivery_notify,
        build_forward_success_text,
    )

    assert "bloqueo" in build_forward_blocked_notify("https://t.me/x?start=TOK").lower()
    assert "completada" in build_forward_success_text().lower()
    manual = build_forward_manual_delivery_notify(
        "https://t.me/+invite",
        "https://t.me/bot?start=acceso_vip",
        "permanent:no_private_chat",
    )
    assert "https://t.me/+invite" in manual
    assert "acceso_vip" in manual
    assert "chat privado" in manual.lower()
    assert (
        "error" in build_forward_error_text("fail msg").lower()
        or "fail" in build_forward_error_text("fail msg").lower()
    )
    assert "start=ABC" in build_forward_deep_link("botu", "ABC")
    assert "contacta" in build_forward_deep_link(None, None).lower()
    assert "acceso_vip" in build_forward_bot_access_link("lucienbot")


def test_build_forward_besitos_helpers_pure():
    """build_* besitos helpers are pure."""
    from handlers.vip_handlers import (
        build_forward_action_menu_text,
        build_forward_besitos_confirm_text,
        build_forward_besitos_success_text,
        build_forward_besitos_visitor_notify,
        parse_positive_besito_amount,
    )
    from services.besito_service import MAX_ADMIN_BESITO_GRANT

    assert "424242" in build_forward_action_menu_text("Cand", 424242)
    assert "50 besitos" in build_forward_besitos_confirm_text("Cand", 424242, 50)
    assert "50" in build_forward_besitos_success_text(50, 150)
    notify = build_forward_besitos_visitor_notify(50, 150)
    assert "50" in notify
    assert "gesto especial" in notify.lower()
    assert parse_positive_besito_amount("50") == 50
    assert parse_positive_besito_amount("0") is None
    assert parse_positive_besito_amount("-1") is None
    assert parse_positive_besito_amount("abc") is None
    assert parse_positive_besito_amount(str(MAX_ADMIN_BESITO_GRANT + 1)) is None


# =============================================================================
# Handler flows (mock get_service + bot.send)
# =============================================================================


@patch("handlers.vip_handlers.is_admin", return_value=True)
async def test_process_forwarded_admin_candidate_shows_action_menu_0_svc(
    _mock_is_admin, make_message, make_fsm_context
):
    """Detection path shows action menu with 0 svc calls."""
    msg = make_message(text="forwarded candidate msg")
    fake = MagicMock()
    fake.id = 424242
    fake.full_name = "Test VIP Cand"
    fake.username = "vipcand"
    msg.forward_from = fake
    msg.forward_origin = None

    fsm = await make_fsm_context(user_id=424242)

    from handlers.vip_handlers import process_forwarded_admin_candidate

    with patch("handlers.vip_handlers.get_service") as mock_get_service:
        await process_forwarded_admin_candidate(msg, fsm)
        mock_get_service.assert_not_called()

    msg.answer.assert_called()
    ans_text = msg.answer.call_args[0][0]
    assert "424242" in ans_text
    data = await fsm.get_data()
    assert data.get("forward_target_user_id") == 424242
    assert "Test VIP Cand" in data.get("forward_target_display", "")


@patch("handlers.vip_handlers.is_admin", return_value=True)
@patch("handlers.vip_handlers.get_service")
async def test_select_forward_action_vip_uses_exactly_1_svc(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    """VIP action path calls tariffs svc once."""
    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.get_all_tariffs.return_value = [MagicMock(id=1, name="Mensual", duration_days=30)]

    cb = make_callback(data=ForwardActionCallback(action="vip").pack())
    fsm = await make_fsm_context()
    await fsm.update_data(forward_target_user_id=424242, forward_target_display="Cand")

    from handlers.vip_handlers import AdminForwardStates, select_forward_action_vip

    await fsm.set_state(AdminForwardStates.selecting_action)
    await select_forward_action_vip(cb, fsm)

    mock_get_service.assert_called_once()
    cb.message.edit_text.assert_called()
    st = await fsm.get_state()
    assert st is None or "vip_selecting_tariff" in str(st).lower()


@patch("handlers.vip_handlers.is_admin", return_value=True)
async def test_select_tariff_for_forward_vip_transitions_state_no_svc(
    _mock_is_admin, make_callback, make_fsm_context
):
    """Select tariff path (0 svc) updates data + state to confirming."""
    cb = make_callback(data="select_tariff:7")
    fsm = await make_fsm_context()
    await fsm.update_data(forward_target_user_id=424242, forward_target_display="Cand")

    cbdata = SelectTariffCallback(tariff_id=7)

    from handlers.vip_handlers import AdminForwardStates, select_tariff_for_forward_vip

    await fsm.set_state(AdminForwardStates.vip_selecting_tariff)
    await select_tariff_for_forward_vip(cb, fsm, callback_data=cbdata)

    cb.message.edit_text.assert_called_once()
    data = await fsm.get_data()
    assert data.get("selected_tariff_id") == 7
    st = await fsm.get_state()
    assert st is None or "confirm" in str(st).lower() or st == AdminForwardStates.vip_confirming


@patch("handlers.vip_handlers.is_admin", return_value=True)
@patch("handlers.vip_handlers.get_service")
async def test_confirm_forward_vip_activation_calls_exactly_1_grant_and_sends_direct(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    """Confirm VIP: EXACTLY 1 grant via get_service, direct send, state cleaned."""
    fsm = await make_fsm_context()
    await fsm.update_data(forward_target_user_id=424242, selected_tariff_id=1)

    cb = make_callback(data=ForwardConfirmCallback(action="vip").pack())
    cb.bot = AsyncMock()
    cb.bot.send_message = AsyncMock()
    cb.bot.get_me = AsyncMock(return_value=MagicMock(username="lucienbot"))

    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.grant_vip_from_tariff = AsyncMock(
        return_value=(
            True,
            "🎩 <b>Lucien:</b> Acceso VIP...",
            {
                "vip_activated": True,
                "invite_link": "https://t.me/+fwdinvite",
            },
        )
    )

    from handlers.vip_handlers import AdminForwardStates, confirm_forward_vip_activation

    await fsm.set_state(AdminForwardStates.vip_confirming)
    await confirm_forward_vip_activation(cb, fsm)

    mock_svc.grant_vip_from_tariff.assert_called_once_with(cb.bot, 424242, 1)
    cb.bot.send_message.assert_called_once()
    call = cb.bot.send_message.call_args
    assert call.kwargs.get("chat_id") == 424242
    data_after = await fsm.get_data()
    assert data_after == {} or "forward_target" not in str(data_after)
    cb.message.edit_text.assert_called()


@patch("handlers.vip_handlers.is_admin", return_value=True)
@patch("handlers.vip_handlers.get_service")
async def test_confirm_forward_besitos_calls_exactly_1_grant(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    """Confirm besitos: EXACTLY 1 grant_manual_admin_besitos, notify visitor."""
    fsm = await make_fsm_context()
    await fsm.update_data(forward_target_user_id=424242, besito_amount=25)

    cb = make_callback(data=ForwardConfirmCallback(action="besitos").pack())
    cb.bot = AsyncMock()
    cb.bot.send_message = AsyncMock()

    mock_svc = _mock_besito_ctx(mock_get_service)
    mock_svc.grant_manual_admin_besitos.return_value = (True, 125)

    from handlers.vip_handlers import AdminForwardStates, confirm_forward_besitos_grant

    await fsm.set_state(AdminForwardStates.besitos_confirming)
    await confirm_forward_besitos_grant(cb, fsm)

    mock_svc.grant_manual_admin_besitos.assert_called_once_with(424242, 25, cb.from_user.id)
    cb.bot.send_message.assert_called_once()
    data_after = await fsm.get_data()
    assert data_after == {} or "besito_amount" not in str(data_after)


@patch("handlers.vip_handlers.is_admin", return_value=True)
async def test_process_besitos_amount_invalid_rejects(_mock_is_admin, make_message, make_fsm_context):
    """Invalid amount does not advance FSM."""
    msg = make_message(text="not-a-number")
    fsm = await make_fsm_context()
    await fsm.update_data(forward_target_user_id=424242, forward_target_display="Cand")

    from handlers.vip_handlers import AdminForwardStates, process_besitos_amount_for_forward

    await fsm.set_state(AdminForwardStates.besitos_waiting_amount)
    await process_besitos_amount_for_forward(msg, fsm)

    msg.answer.assert_called()
    assert "inválida" in msg.answer.call_args[0][0].lower()
    st = await fsm.get_state()
    assert st is None or "besitos_waiting_amount" in str(st).lower()


@patch("handlers.vip_handlers.is_admin", return_value=True)
@patch("handlers.vip_handlers.get_service")
async def test_confirm_forward_vip_dm_fail_shares_invite_not_token(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    """Si el DM falla tras activar VIP, admin recibe invite link (no token ya usado)."""
    fsm = await make_fsm_context()
    await fsm.update_data(forward_target_user_id=424242, selected_tariff_id=1)

    cb = make_callback(data=ForwardConfirmCallback(action="vip").pack())
    cb.bot = AsyncMock()
    cb.bot.get_me = AsyncMock(return_value=MagicMock(username="lucienbot"))
    from aiogram.exceptions import TelegramForbiddenError

    cb.bot.send_message = AsyncMock(
        side_effect=TelegramForbiddenError(
            method="sendMessage", message="Forbidden: bot was blocked by the user"
        )
    )

    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.grant_vip_from_tariff = AsyncMock(
        return_value=(
            True,
            "🎩 <b>Lucien:</b> Acceso VIP...",
            {"vip_activated": True, "invite_link": "https://t.me/+manualinvite"},
        )
    )

    from handlers.vip_handlers import AdminForwardStates, confirm_forward_vip_activation

    await fsm.set_state(AdminForwardStates.vip_confirming)
    await confirm_forward_vip_activation(cb, fsm)

    fallback = cb.message.answer.call_args[0][0]
    assert "https://t.me/+manualinvite" in fallback
    assert "acceso_vip" in fallback
    assert "start=USEDTOKEN" not in fallback


def test_vip_forward_flow_unchanged_no_list_subscribers():
    """Regression: list_subscribers removed; forward helpers intact."""
    import inspect

    import handlers.vip_handlers as mod

    source = inspect.getsource(mod)
    assert 'F.data == "list_subscribers"' not in source
    assert "process_forwarded_admin_candidate" in source
    assert "confirm_forward_besitos_grant" in source
    assert "confirm_forward_vip_activation" in source


@patch("handlers.vip_handlers.is_admin", return_value=True)
async def test_cancel_forward_action_clears_state(_mock_is_admin, make_callback, make_fsm_context):
    """Cancel always clears state + returns to mgmt."""
    fsm = await make_fsm_context()
    await fsm.update_data(forward_target_user_id=42)

    cb = make_callback(data=ForwardCancelCallback().pack())

    from handlers.vip_handlers import cancel_forward_action

    await cancel_forward_action(cb, fsm)

    cb.message.edit_text.assert_called()
    assert await fsm.get_data() == {}
