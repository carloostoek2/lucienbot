"""Handler tests for backpack fulfillment callbacks."""

from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

pytestmark = [pytest.mark.unit]


def _mock_backpack_ctx(mock_get_service, **methods):
    """Mock get_service(BackpackService) context manager con autospec."""
    from services.backpack_service import BackpackService

    svc = create_autospec(BackpackService, spec_set=True, instance=True)
    for name, val in methods.items():
        getattr(svc, name).return_value = val
    ctx = MagicMock()
    ctx.__enter__.return_value = svc
    ctx.__exit__.return_value = False
    mock_get_service.return_value = ctx
    return svc


class TestBackpackFulfillmentCallbacks:
    @patch("handlers.backpack_handler.get_service")
    async def test_fulfillment_retry_success(self, mock_get_service, make_callback):
        svc = _mock_backpack_ctx(
            mock_get_service,
            retry_fulfillment_delivery=(True, "Entregado"),
        )
        from keyboards.callback_data import BackpackFulfillmentRetryCallback

        cb_data = BackpackFulfillmentRetryCallback(fulfillment_id=42)
        cb = make_callback(data=cb_data.pack())

        from handlers.backpack_handler import callback_fulfillment_retry

        await callback_fulfillment_retry(cb, cb_data)

        svc.retry_fulfillment_delivery.assert_awaited_once_with(cb.bot, cb.from_user.id, 42)
        cb.answer.assert_called_once()
        toast = cb.answer.call_args[0][0]
        assert "<" not in toast
        assert "Entregado" in toast

    @patch("handlers.backpack_handler.get_service")
    async def test_fulfillment_retry_strips_html_from_toast(
        self, mock_get_service, make_callback
    ):
        svc = _mock_backpack_ctx(
            mock_get_service,
            retry_fulfillment_delivery=(True, "<b>Entregado</b> con éxito"),
        )
        from keyboards.callback_data import BackpackFulfillmentRetryCallback

        cb_data = BackpackFulfillmentRetryCallback(fulfillment_id=1)
        cb = make_callback(data=cb_data.pack())
        from handlers.backpack_handler import callback_fulfillment_retry

        await callback_fulfillment_retry(cb, cb_data)

        toast = cb.answer.call_args[0][0]
        assert "<b>" not in toast
        assert "Entregado" in toast

    @patch("handlers.backpack_handler.get_service")
    async def test_activate_vip_shows_link(self, mock_get_service, make_callback):
        svc = _mock_backpack_ctx(
            mock_get_service,
            resend_vip_invite_for_fulfillment=(True, "VIP access message"),
        )
        from keyboards.callback_data import BackpackActivateVipCallback

        cb_data = BackpackActivateVipCallback(fulfillment_id=7)
        cb = make_callback(data=cb_data.pack())

        from handlers.backpack_handler import callback_resend_vip_invite

        await callback_resend_vip_invite(cb, cb_data)

        svc.resend_vip_invite_for_fulfillment.assert_awaited_once_with(
            cb.bot, cb.from_user.id, 7
        )
        cb.message.answer.assert_awaited_once()
        cb.answer.assert_called_once()

    @patch("handlers.backpack_handler.get_service")
    async def test_read_chapter_requires_node(self, mock_get_service, make_callback):
        svc = _mock_backpack_ctx(
            mock_get_service,
            get_fulfillment_detail={"product_name": "Capítulo", "auto_result": {}},
        )
        from keyboards.callback_data import BackpackReadChapterCallback

        cb_data = BackpackReadChapterCallback(fulfillment_id=3)
        cb = make_callback(data=cb_data.pack())

        from handlers.backpack_handler import callback_read_chapter

        await callback_read_chapter(cb, cb_data)

        cb.answer.assert_called_once()
        assert cb.answer.call_args[1].get("show_alert") is True

    @patch("handlers.story_user_handlers.show_node", new_callable=AsyncMock)
    @patch("handlers.backpack_handler.get_service")
    async def test_read_chapter_delegates_to_story_node(
        self, mock_get_service, mock_show_node, make_callback
    ):
        _mock_backpack_ctx(
            mock_get_service,
            get_fulfillment_detail={"auto_result": {"node_id": 42}},
        )
        from keyboards.callback_data import BackpackReadChapterCallback

        cb_data = BackpackReadChapterCallback(fulfillment_id=3)
        cb = make_callback(data=cb_data.pack())

        from handlers.backpack_handler import callback_read_chapter

        await callback_read_chapter(cb, cb_data)

        mock_show_node.assert_awaited_once()
        assert mock_show_node.call_args[0][1] == 42

    @patch("handlers.backpack_handler.get_service")
    async def test_submit_input_start_sets_fsm(self, mock_get_service, make_callback):
        svc = _mock_backpack_ctx(
            mock_get_service,
            get_fulfillment_input_prompt=(True, "<i>Escriba su respuesta</i>"),
        )
        from keyboards.callback_data import BackpackSubmitInputCallback

        cb_data = BackpackSubmitInputCallback(fulfillment_id=15)
        cb = make_callback(data=cb_data.pack())
        state = AsyncMock()

        from handlers.backpack_handler import BackpackInputStates, callback_submit_input_start

        await callback_submit_input_start(cb, cb_data, state)

        svc.get_fulfillment_input_prompt.assert_called_once_with(cb.from_user.id, 15)
        state.set_state.assert_called_once_with(BackpackInputStates.awaiting_input)
        state.update_data.assert_awaited_once_with(fulfillment_id=15)
        cb.message.answer.assert_awaited_once()

    @patch("handlers.backpack_handler.get_service")
    async def test_submit_input_start_rejects_invalid(self, mock_get_service, make_callback):
        _mock_backpack_ctx(
            mock_get_service,
            get_fulfillment_input_prompt=(False, "Ya enviado"),
        )
        from keyboards.callback_data import BackpackSubmitInputCallback

        cb_data = BackpackSubmitInputCallback(fulfillment_id=15)
        cb = make_callback(data=cb_data.pack())
        state = AsyncMock()

        from handlers.backpack_handler import callback_submit_input_start

        await callback_submit_input_start(cb, cb_data, state)

        state.set_state.assert_not_called()
        cb.answer.assert_called_once_with("Ya enviado", show_alert=True)

    @patch("handlers.backpack_handler.get_service")
    async def test_process_backpack_input_submits(self, mock_get_service, make_message):
        svc = _mock_backpack_ctx(
            mock_get_service,
            submit_fulfillment_input=(True, "Recibido"),
        )
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"fulfillment_id": 9})
        msg = make_message(text="Mi pregunta para Diana")

        from handlers.backpack_handler import process_backpack_input

        await process_backpack_input(msg, state)

        svc.submit_fulfillment_input.assert_awaited_once_with(
            msg.bot, msg.from_user.id, 9, "Mi pregunta para Diana"
        )
        state.clear.assert_awaited_once()

    @patch("handlers.backpack_handler.get_service")
    async def test_view_waitlist_shows_position(self, mock_get_service, make_callback):
        svc = _mock_backpack_ctx(
            mock_get_service,
            get_fulfillment_detail={"auto_result": {"position": 5}},
        )
        from keyboards.callback_data import BackpackViewWaitlistCallback

        cb_data = BackpackViewWaitlistCallback(fulfillment_id=9)
        cb = make_callback(data=cb_data.pack())

        from handlers.backpack_handler import callback_view_waitlist

        await callback_view_waitlist(cb, cb_data)

        svc.get_fulfillment_detail.assert_called_once_with(cb.from_user.id, 9)
        cb.message.answer.assert_awaited_once()
        cb.answer.assert_called_once()

    @patch("handlers.backpack_handler.BackpackService")
    async def test_deliver_package_delegates_to_service(self, MockBackpack, make_callback):
        inst = MockBackpack.return_value
        inst.deliver_package_content = AsyncMock(return_value=(True, "ok"))

        from keyboards.callback_data import BackpackDeliverCallback

        cb_data = BackpackDeliverCallback(package_id=12)
        cb = make_callback(data=cb_data.pack())

        from handlers.backpack_handler import callback_deliver_package

        await callback_deliver_package(cb, cb_data)

        inst.deliver_package_content.assert_awaited_once_with(cb.bot, cb.from_user.id, 12)
        inst.close.assert_called_once()


class TestBackpackInputFSM:
    async def test_cancel_backpack_input_clears_state(self, make_message):
        state = AsyncMock()
        msg = make_message(text="/cancel")
        from handlers.backpack_handler import cancel_backpack_input

        await cancel_backpack_input(msg, state)
        state.clear.assert_awaited_once()

    @patch("handlers.backpack_handler.get_service")
    async def test_process_backpack_input_validation_failure_keeps_fsm(
        self, mock_get_service, make_message
    ):
        from utils.lucien_voice import LucienVoice

        svc = _mock_backpack_ctx(
            mock_get_service,
            submit_fulfillment_input=(False, LucienVoice.fulfillment_input_invalid_length(3, 100)),
        )
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"fulfillment_id": 5})
        msg = make_message(text="x")
        from handlers.backpack_handler import BackpackInputStates, process_backpack_input

        await process_backpack_input(msg, state)

        svc.submit_fulfillment_input.assert_awaited_once()
        state.set_state.assert_called_with(BackpackInputStates.awaiting_input)
        state.clear.assert_not_called()

    @patch("handlers.backpack_handler.get_service")
    async def test_process_backpack_input_already_submitted_clears_fsm(
        self, mock_get_service, make_message
    ):
        from utils.lucien_voice import LucienVoice

        _mock_backpack_ctx(
            mock_get_service,
            submit_fulfillment_input=(False, LucienVoice.fulfillment_input_already_submitted()),
        )
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"fulfillment_id": 5})
        msg = make_message(text="ya enviado")
        from handlers.backpack_handler import process_backpack_input

        await process_backpack_input(msg, state)
        state.clear.assert_awaited_once()


class TestBuildPurchaseDetailKeyboard:
    def test_package_deferred_fulfilled_shows_ver_contenido(self):
        from handlers.backpack_handler import build_purchase_detail_keyboard

        purchase = {
            "fulfillment_kind": "package_deferred",
            "fulfillment_status": "fulfilled",
            "auto_result": {"package_id": 99},
            "actions_available": [],
        }
        kb = build_purchase_detail_keyboard(purchase)
        labels = [btn.text for row in kb.inline_keyboard for btn in row]
        assert "📂 Ver Contenido" in labels

    def test_vip_activate_button_when_action_available(self):
        from handlers.backpack_handler import build_purchase_detail_keyboard

        purchase = {
            "actions_available": ["resend_vip_invite"],
            "fulfillment_id": 1,
        }
        kb = build_purchase_detail_keyboard(purchase)
        labels = [btn.text for row in kb.inline_keyboard for btn in row]
        assert "🔗 Reenviar acceso VIP" in labels

    def test_submit_input_button_when_action_available(self):
        from handlers.backpack_handler import build_purchase_detail_keyboard

        purchase = {
            "actions_available": ["submit_input"],
            "fulfillment_id": 5,
        }
        kb = build_purchase_detail_keyboard(purchase)
        labels = [btn.text for row in kb.inline_keyboard for btn in row]
        assert "🌸 Enviar a Diana" in labels
