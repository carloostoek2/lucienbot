"""
Tests para vip_subscriber_admin_handlers — Phase 36.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from keyboards.callback_data import (
    SubscriberConfirmCallback,
    SubscriberExtendTariffCallback,
    SubscriberListCallback,
    SubscriberProfileCallback,
)

pytestmark = [pytest.mark.unit]


def _mock_vip_ctx(mock_get_service):
    from services.vip_service import VIPService

    svc = create_autospec(VIPService, spec_set=True, instance=True)
    mock_get_service.return_value.__enter__.return_value = svc
    return svc


def _mock_besito_ctx(mock_get_service):
    from services.besito_service import BesitoService

    svc = create_autospec(BesitoService, spec_set=True, instance=True)
    mock_get_service.return_value.__enter__.return_value = svc
    return svc


class TestPureHelpers:
    def test_clamp_subscriber_page_bounds(self):
        from handlers.vip_subscriber_admin_handlers import clamp_subscriber_page

        assert clamp_subscriber_page(0, 0) == 0
        assert clamp_subscriber_page(5, 10) == 1  # 10 items, 2 pages
        assert clamp_subscriber_page(99, 5) == 0

    def test_build_subscriber_list_text_empty(self):
        from handlers.vip_subscriber_admin_handlers import build_subscriber_list_text

        text = build_subscriber_list_text([], 0, 0)
        assert "No hay miembros" in text

    def test_build_subscriber_list_text_with_subs(self):
        from handlers.vip_subscriber_admin_handlers import build_subscriber_list_text

        sub = MagicMock()
        sub.user = MagicMock(username="vipuser", first_name=None)
        sub.user_id = 123
        sub.end_date = datetime(2026, 12, 31, tzinfo=UTC)
        text = build_subscriber_list_text([sub], 0, 1)
        assert "vipuser" in text
        assert "31/12/2026" in text

    def test_format_subscriber_display_name_no_double_escape(self):
        from handlers.vip_subscriber_admin_handlers import (
            build_subscriber_list_text,
            format_subscriber_display_name,
        )

        sub = MagicMock()
        sub.user = MagicMock(username=None, first_name="<script>")
        sub.user_id = 1
        sub.end_date = datetime(2026, 6, 1, tzinfo=UTC)
        assert format_subscriber_display_name(sub) == "<script>"
        text = build_subscriber_list_text([sub], 0, 1)
        assert "&lt;script&gt;" in text
        assert "&amp;lt;" not in text

    def test_validate_fsm_subscription_id_pure(self):
        from handlers.vip_subscriber_admin_handlers import validate_fsm_subscription_id

        assert validate_fsm_subscription_id({"target_subscription_id": 5}, 5) is True
        assert validate_fsm_subscription_id({"target_subscription_id": 5}, 9) is False

    def test_build_subscriber_profile_text(self):
        from handlers.vip_subscriber_admin_handlers import build_subscriber_profile_text

        snapshot = {
            "display_name": "@test",
            "user_id": 42,
            "besitos_balance": 100,
            "tariff_name": "Mensual",
            "expiry_iso": "01/07/2026",
            "days_remaining": 30,
        }
        text = build_subscriber_profile_text(snapshot)
        assert "42" in text
        assert "100" in text
        assert "Mensual" in text


class TestSubscriberListCallback:
    def test_subscriber_list_callback_pack_unpack(self):
        cb = SubscriberListCallback(channel_id=5, page=2)
        packed = cb.pack()
        assert packed == "sub_list:5:2"
        assert SubscriberListCallback.unpack(packed).channel_id == 5
        assert SubscriberListCallback.unpack(packed).page == 2


@patch("handlers.vip_subscriber_admin_handlers.is_admin", return_value=False)
@patch("handlers.vip_subscriber_admin_handlers.get_service")
async def test_open_subscriber_list_requires_admin(
    mock_get_service, _mock_is_admin, make_callback
):
    from handlers.vip_subscriber_admin_handlers import open_subscriber_list

    cb = make_callback(data=SubscriberListCallback(channel_id=0, page=0).pack())
    cbdata = SubscriberListCallback(channel_id=0, page=0)
    await open_subscriber_list(cb, cbdata)
    cb.answer.assert_called_once_with("Acceso denegado", show_alert=True)
    mock_get_service.assert_not_called()


@patch("handlers.vip_subscriber_admin_handlers.is_admin", return_value=True)
@patch("handlers.vip_subscriber_admin_handlers.get_service")
async def test_open_subscriber_list_exactly_1_svc(
    mock_get_service, _mock_is_admin, make_callback
):
    from handlers.vip_subscriber_admin_handlers import open_subscriber_list

    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.get_subscriber_list_page.return_value = ([], 0)
    cb = make_callback(data=SubscriberListCallback(channel_id=0, page=0).pack())
    cbdata = SubscriberListCallback(channel_id=0, page=0)
    await open_subscriber_list(cb, cbdata)
    mock_svc.get_subscriber_list_page.assert_called_once()
    cb.message.edit_text.assert_called_once()


@patch("handlers.vip_subscriber_admin_handlers.is_admin", return_value=True)
@patch("handlers.vip_subscriber_admin_handlers.get_service")
async def test_open_subscriber_profile_exactly_1_svc(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    from handlers.vip_subscriber_admin_handlers import open_subscriber_profile

    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.get_subscriber_admin_snapshot.return_value = {
        "subscription_id": 1,
        "user_id": 123,
        "display_name": "@u",
        "besitos_balance": 50,
        "tariff_name": "T",
        "expiry_iso": "01/01/2027",
        "days_remaining": 10,
        "channel_db_id": 1,
    }
    fsm = await make_fsm_context()
    await fsm.update_data(besito_amount=99, target_subscription_id=2)
    cb = make_callback(data=SubscriberProfileCallback(subscription_id=1).pack())
    cbdata = SubscriberProfileCallback(subscription_id=1)
    await open_subscriber_profile(cb, fsm, cbdata)
    mock_svc.get_subscriber_admin_snapshot.assert_called_once_with(1)
    assert await fsm.get_data() == {}


@patch("handlers.vip_subscriber_admin_handlers.is_admin", return_value=True)
@patch("handlers.vip_subscriber_admin_handlers.get_service")
async def test_open_subscriber_profile_not_found(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    from handlers.vip_subscriber_admin_handlers import open_subscriber_profile

    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.get_subscriber_admin_snapshot.return_value = None
    fsm = await make_fsm_context()
    cb = make_callback(data=SubscriberProfileCallback(subscription_id=999).pack())
    cbdata = SubscriberProfileCallback(subscription_id=999)
    await open_subscriber_profile(cb, fsm, cbdata)
    cb.answer.assert_called_once_with("Suscriptor no encontrado", show_alert=True)
    cb.message.edit_text.assert_not_called()


@patch("handlers.vip_subscriber_admin_handlers.is_admin", return_value=True)
async def test_select_extend_tariff_rejects_invalid_tariff(
    _mock_is_admin, make_callback, make_fsm_context
):
    from handlers.vip_subscriber_admin_handlers import select_extend_tariff

    fsm = await make_fsm_context()
    await fsm.update_data(
        target_subscription_id=1,
        tariff_map={2: {"name": "Mensual", "days": 30}},
    )
    cb = make_callback(data=SubscriberExtendTariffCallback(subscription_id=1, tariff_id=99).pack())
    cbdata = SubscriberExtendTariffCallback(subscription_id=1, tariff_id=99)
    await select_extend_tariff(cb, fsm, cbdata)
    cb.answer.assert_called_once_with("Tarifa inválida", show_alert=True)
    cb.message.edit_text.assert_not_called()


@patch("handlers.vip_subscriber_admin_handlers.is_admin", return_value=True)
@patch("handlers.vip_subscriber_admin_handlers.get_service")
async def test_confirm_extend_fail_shows_error(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    from handlers.vip_subscriber_admin_handlers import (
        SubscriberAdminStates,
        confirm_subscriber_extend,
    )

    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.grant_internal_vip_access_for_subscription = AsyncMock(
        return_value=(False, None, {"error": "tariff_inactive"})
    )
    fsm = await make_fsm_context()
    await fsm.update_data(
        selected_tariff_id=2,
        target_subscription_id=1,
        target_display="@u",
        selected_tariff_name="Mensual",
        selected_tariff_days=30,
    )
    await fsm.set_state(SubscriberAdminStates.extend_confirming)
    cb = make_callback(data=SubscriberConfirmCallback(action="extend", subscription_id=1).pack())
    cbdata = SubscriberConfirmCallback(action="extend", subscription_id=1)
    await confirm_subscriber_extend(cb, fsm, cbdata)
    text = cb.message.edit_text.call_args[0][0]
    assert "extender" in text.lower() or "no pude" in text.lower()


@patch("handlers.vip_subscriber_admin_handlers.is_admin", return_value=True)
@patch("handlers.vip_subscriber_admin_handlers.get_service")
async def test_confirm_extend_calls_grant_internal_only(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    from handlers.vip_subscriber_admin_handlers import (
        SubscriberAdminStates,
        confirm_subscriber_extend,
    )

    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.grant_internal_vip_access_for_subscription = AsyncMock(
        return_value=(True, MagicMock(), {})
    )
    fsm = await make_fsm_context()
    await fsm.update_data(
        selected_tariff_id=2,
        target_subscription_id=1,
        target_display="@u",
        selected_tariff_name="Mensual",
        selected_tariff_days=30,
    )
    await fsm.set_state(SubscriberAdminStates.extend_confirming)
    cb = make_callback(data=SubscriberConfirmCallback(action="extend", subscription_id=1).pack())
    cbdata = SubscriberConfirmCallback(action="extend", subscription_id=1)
    await confirm_subscriber_extend(cb, fsm, cbdata)
    mock_svc.grant_internal_vip_access_for_subscription.assert_called_once_with(1, 2)
    assert mock_svc.get_subscriber_admin_snapshot.call_count == 0


@patch("handlers.vip_subscriber_admin_handlers.is_admin", return_value=True)
@patch("handlers.vip_subscriber_admin_handlers.get_service")
async def test_confirm_kick_calls_admin_revoke_with_bot(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    from handlers.vip_subscriber_admin_handlers import (
        SubscriberAdminStates,
        confirm_subscriber_kick,
    )

    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.admin_revoke_subscription = AsyncMock(
        return_value=(True, "kicked", {"subscription_id": 1})
    )
    fsm = await make_fsm_context()
    await fsm.update_data(target_display="@u", target_subscription_id=1)
    await fsm.set_state(SubscriberAdminStates.kick_confirming)
    cb = make_callback(data=SubscriberConfirmCallback(action="kick", subscription_id=1).pack())
    cb.bot = AsyncMock()
    cbdata = SubscriberConfirmCallback(action="kick", subscription_id=1)
    await confirm_subscriber_kick(cb, fsm, cbdata)
    mock_svc.admin_revoke_subscription.assert_called_once_with(cb.bot, 1, cb.from_user.id)


@patch("handlers.vip_subscriber_admin_handlers.is_admin", return_value=True)
@patch("handlers.vip_subscriber_admin_handlers.get_service")
async def test_confirm_kick_deactivated_only_messaging(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    from handlers.vip_subscriber_admin_handlers import (
        SubscriberAdminStates,
        confirm_subscriber_kick,
    )

    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.admin_revoke_subscription = AsyncMock(
        return_value=(True, "deactivated_only", {"subscription_id": 1})
    )
    fsm = await make_fsm_context()
    await fsm.update_data(target_display="@multi", target_subscription_id=1)
    await fsm.set_state(SubscriberAdminStates.kick_confirming)
    cb = make_callback(data=SubscriberConfirmCallback(action="kick", subscription_id=1).pack())
    cb.bot = AsyncMock()
    cbdata = SubscriberConfirmCallback(action="kick", subscription_id=1)
    await confirm_subscriber_kick(cb, fsm, cbdata)
    text = cb.message.edit_text.call_args[0][0]
    assert "otra suscripción activa" in text.lower()


@patch("handlers.vip_subscriber_admin_handlers.is_admin", return_value=True)
@patch("handlers.vip_subscriber_admin_handlers.get_service")
async def test_confirm_kick_channel_inactive_messaging(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    from handlers.vip_subscriber_admin_handlers import (
        SubscriberAdminStates,
        confirm_subscriber_kick,
    )

    mock_svc = _mock_vip_ctx(mock_get_service)
    mock_svc.admin_revoke_subscription = AsyncMock(
        return_value=(True, "channel_inactive", {"subscription_id": 1})
    )
    fsm = await make_fsm_context()
    await fsm.update_data(target_display="@u", target_subscription_id=1)
    await fsm.set_state(SubscriberAdminStates.kick_confirming)
    cb = make_callback(data=SubscriberConfirmCallback(action="kick", subscription_id=1).pack())
    cb.bot = AsyncMock()
    cbdata = SubscriberConfirmCallback(action="kick", subscription_id=1)
    await confirm_subscriber_kick(cb, fsm, cbdata)
    text = cb.message.edit_text.call_args[0][0]
    assert "canal" in text.lower() and "inactivo" in text.lower()


@patch("handlers.vip_subscriber_admin_handlers.is_admin", return_value=True)
@patch("handlers.vip_subscriber_admin_handlers.get_service")
@patch("handlers.vip_subscriber_admin_handlers.notify_forward_besitos_result", new_callable=AsyncMock)
async def test_confirm_grant_besitos_exactly_1_svc(
    _mock_notify, mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    from handlers.vip_subscriber_admin_handlers import (
        SubscriberAdminStates,
        confirm_subscriber_grant_besitos,
    )

    mock_svc = _mock_besito_ctx(mock_get_service)
    mock_svc.grant_manual_admin_besitos.return_value = (True, 200)
    fsm = await make_fsm_context()
    await fsm.update_data(
        target_user_id=555, besito_amount=25, target_subscription_id=1
    )
    await fsm.set_state(SubscriberAdminStates.besitos_grant_confirming)
    cb = make_callback(
        data=SubscriberConfirmCallback(action="grant_besitos", subscription_id=1).pack()
    )
    cb.bot = AsyncMock()
    cbdata = SubscriberConfirmCallback(action="grant_besitos", subscription_id=1)
    await confirm_subscriber_grant_besitos(cb, fsm, cbdata)
    mock_svc.grant_manual_admin_besitos.assert_called_once_with(555, 25, cb.from_user.id)


@patch("handlers.vip_subscriber_admin_handlers.is_admin", return_value=True)
@patch("handlers.vip_subscriber_admin_handlers.get_service")
async def test_confirm_debit_besitos_exactly_1_svc(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    from handlers.vip_subscriber_admin_handlers import (
        SubscriberAdminStates,
        confirm_subscriber_debit_besitos,
    )

    mock_svc = _mock_besito_ctx(mock_get_service)
    mock_svc.debit_manual_admin_besitos.return_value = (True, 75)
    fsm = await make_fsm_context()
    await fsm.update_data(
        target_user_id=555,
        besito_amount=25,
        target_display="@u",
        target_subscription_id=1,
    )
    await fsm.set_state(SubscriberAdminStates.besitos_debit_confirming)
    cb = make_callback(
        data=SubscriberConfirmCallback(action="debit_besitos", subscription_id=1).pack()
    )
    cbdata = SubscriberConfirmCallback(action="debit_besitos", subscription_id=1)
    await confirm_subscriber_debit_besitos(cb, fsm, cbdata)
    mock_svc.debit_manual_admin_besitos.assert_called_once_with(555, 25, cb.from_user.id)


@patch("handlers.vip_subscriber_admin_handlers.is_admin", return_value=True)
@patch("handlers.vip_subscriber_admin_handlers.get_service")
async def test_confirm_debit_besitos_fail_shows_error(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    from handlers.vip_subscriber_admin_handlers import (
        SubscriberAdminStates,
        confirm_subscriber_debit_besitos,
    )

    mock_svc = _mock_besito_ctx(mock_get_service)
    mock_svc.debit_manual_admin_besitos.return_value = (False, 0)
    fsm = await make_fsm_context()
    await fsm.update_data(
        target_user_id=555,
        besito_amount=25,
        target_display="@u",
        target_subscription_id=1,
    )
    await fsm.set_state(SubscriberAdminStates.besitos_debit_confirming)
    cb = make_callback(
        data=SubscriberConfirmCallback(action="debit_besitos", subscription_id=1).pack()
    )
    cbdata = SubscriberConfirmCallback(action="debit_besitos", subscription_id=1)
    await confirm_subscriber_debit_besitos(cb, fsm, cbdata)
    text = cb.message.edit_text.call_args[0][0]
    assert "insuficiente" in text.lower() or "inválida" in text.lower()


@patch("handlers.vip_subscriber_admin_handlers.is_admin", return_value=True)
@patch("handlers.vip_subscriber_admin_handlers.get_service")
async def test_confirm_rejects_fsm_subscription_mismatch(
    mock_get_service, _mock_is_admin, make_callback, make_fsm_context
):
    from handlers.vip_subscriber_admin_handlers import (
        SubscriberAdminStates,
        confirm_subscriber_kick,
    )

    _mock_vip_ctx(mock_get_service)
    fsm = await make_fsm_context()
    await fsm.update_data(target_subscription_id=99)
    await fsm.set_state(SubscriberAdminStates.kick_confirming)
    cb = make_callback(data=SubscriberConfirmCallback(action="kick", subscription_id=1).pack())
    cbdata = SubscriberConfirmCallback(action="kick", subscription_id=1)
    await confirm_subscriber_kick(cb, fsm, cbdata)
    cb.answer.assert_called_with("Contexto expirado. Vuelva al perfil.", show_alert=True)
    mock_get_service.assert_not_called()
