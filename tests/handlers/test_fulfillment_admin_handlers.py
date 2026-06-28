"""Tests para fulfillment_admin_handlers."""

from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from services.fulfillment_service import FulfillmentService

pytestmark = [pytest.mark.unit]


def _mock_fulfill_ctx(mock_get_service, **kwargs):
    """Mock get_service(FulfillmentService) context manager con autospec."""
    svc = create_autospec(FulfillmentService, spec_set=True, instance=True)
    for key, val in kwargs.items():
        getattr(svc, key).return_value = val
    ctx = MagicMock()
    ctx.__enter__.return_value = svc
    mock_get_service.return_value = ctx
    return svc


@pytest.fixture
def admin_user(make_user):
    return make_user(user_id=987654321)


class TestFulfillmentAdminMenu:
    @patch("handlers.fulfillment_admin_handlers.is_admin", return_value=True)
    @patch("handlers.fulfillment_admin_handlers.get_service")
    async def test_menu_renders(self, mock_get_service, _admin, make_callback, admin_user):
        cb = make_callback(data="fulfill_admin_menu", user=admin_user)
        from handlers.fulfillment_admin_handlers import fulfillment_admin_menu

        await fulfillment_admin_menu(cb)
        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()

    @patch("handlers.fulfillment_admin_handlers.is_admin", return_value=True)
    @patch("handlers.fulfillment_admin_handlers.get_service")
    async def test_menu_back_goes_to_store_admin(
        self, mock_get_service, _admin, make_callback, admin_user
    ):
        from handlers.fulfillment_admin_handlers import build_fulfillment_queue_menu_keyboard

        kb = build_fulfillment_queue_menu_keyboard()
        back_cb = kb.inline_keyboard[-1][0].callback_data
        assert back_cb == "admin_store"


class TestFulfillmentAdminQueue:
    @patch("handlers.fulfillment_admin_handlers.is_admin", return_value=True)
    @patch("handlers.fulfillment_admin_handlers.get_service")
    async def test_empty_queue_alert(self, mock_get_service, _admin, make_callback, admin_user):
        _mock_fulfill_ctx(mock_get_service, get_pending_queue=[])
        cb = make_callback(data="fulfill_admin_q:pending", user=admin_user)
        from keyboards.callback_data import FulfillmentAdminQueueCallback
        from handlers.fulfillment_admin_handlers import fulfillment_admin_queue_list

        await fulfillment_admin_queue_list(cb, FulfillmentAdminQueueCallback(status="pending"))
        cb.answer.assert_called_once()

    @patch("handlers.fulfillment_admin_handlers.is_admin", return_value=True)
    @patch("handlers.fulfillment_admin_handlers.get_service")
    async def test_queue_lists_items(self, mock_get_service, _admin, make_callback, admin_user):
        row = MagicMock()
        row.id = 7
        row.product = MagicMock(name="Test Product")
        _mock_fulfill_ctx(mock_get_service, get_pending_queue=[row])
        cb = make_callback(data="fulfill_admin_q:pending", user=admin_user)
        from keyboards.callback_data import FulfillmentAdminQueueCallback
        from handlers.fulfillment_admin_handlers import fulfillment_admin_queue_list

        await fulfillment_admin_queue_list(cb, FulfillmentAdminQueueCallback(status="pending"))
        cb.message.edit_text.assert_called_once()

    @patch("handlers.fulfillment_admin_handlers.is_admin", return_value=True)
    @patch("handlers.fulfillment_admin_handlers.get_service")
    async def test_item_detail_back_returns_to_filter_list(
        self, mock_get_service, _admin, make_callback, admin_user
    ):
        from types import SimpleNamespace

        row = SimpleNamespace(
            id=5,
            product=SimpleNamespace(name="Producto"),
            order_item=SimpleNamespace(order_id=12),
            user_id=444,
            status=SimpleNamespace(value="pending_fulfillment"),
            fulfillment_kind=SimpleNamespace(value="user_input_then_manual"),
            user_input=None,
        )
        _mock_fulfill_ctx(mock_get_service, get_fulfillment_by_id=row)
        cb = make_callback(data="fulfill_admin_item:5:fulfilled", user=admin_user)
        from keyboards.callback_data import FulfillmentAdminItemCallback
        from handlers.fulfillment_admin_handlers import fulfillment_admin_item_detail

        await fulfillment_admin_item_detail(
            cb, FulfillmentAdminItemCallback(fulfillment_id=5, filter_status="fulfilled")
        )
        kb = cb.message.edit_text.call_args[1]["reply_markup"]
        back_cb = kb.inline_keyboard[-1][0].callback_data
        assert "fulfilled" in back_cb
        assert "fulfill_admin_menu" not in back_cb


class TestFulfillmentAdminMark:
    @patch("handlers.fulfillment_admin_handlers.is_admin", return_value=True)
    @patch("handlers.fulfillment_admin_handlers.get_service")
    async def test_mark_fulfilled_fsm(self, mock_get_service, _admin, make_message, admin_user):
        svc = _mock_fulfill_ctx(mock_get_service)
        svc.admin_mark_fulfilled = AsyncMock(return_value=(True, "OK"))
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"fulfillment_id": 3})
        state.clear = AsyncMock()
        msg = make_message(text="Notas de entrega")
        msg.from_user = admin_user
        from handlers.fulfillment_admin_handlers import fulfillment_admin_mark_submit

        await fulfillment_admin_mark_submit(msg, state)
        svc.admin_mark_fulfilled.assert_called_once()


class TestFulfillmentAdminItemDetail:
    @patch("handlers.fulfillment_admin_handlers.is_admin", return_value=True)
    @patch("handlers.fulfillment_admin_handlers.get_service")
    async def test_item_not_found_alert(self, mock_get_service, _admin, make_callback, admin_user):
        _mock_fulfill_ctx(mock_get_service, get_fulfillment_by_id=None)
        cb = make_callback(data="fulfill_admin_item:99", user=admin_user)
        from keyboards.callback_data import FulfillmentAdminItemCallback
        from handlers.fulfillment_admin_handlers import fulfillment_admin_item_detail

        await fulfillment_admin_item_detail(cb, FulfillmentAdminItemCallback(fulfillment_id=99))
        cb.answer.assert_called_once()
        assert cb.answer.call_args[1].get("show_alert") is True

    @patch("handlers.fulfillment_admin_handlers.is_admin", return_value=True)
    @patch("handlers.fulfillment_admin_handlers.get_service")
    async def test_item_detail_escapes_user_input(
        self, mock_get_service, _admin, make_callback, admin_user
    ):
        from types import SimpleNamespace

        row = SimpleNamespace(
            id=5,
            product=SimpleNamespace(name="Producto"),
            order_item=SimpleNamespace(order_id=12),
            user_id=444,
            status=SimpleNamespace(value="pending_fulfillment"),
            fulfillment_kind=SimpleNamespace(value="user_input_then_manual"),
            user_input='<script>alert("x")</script>',
        )
        _mock_fulfill_ctx(mock_get_service, get_fulfillment_by_id=row)
        cb = make_callback(data="fulfill_admin_item:5", user=admin_user)
        from keyboards.callback_data import FulfillmentAdminItemCallback
        from handlers.fulfillment_admin_handlers import fulfillment_admin_item_detail

        await fulfillment_admin_item_detail(cb, FulfillmentAdminItemCallback(fulfillment_id=5))
        text = cb.message.edit_text.call_args[0][0]
        assert "&lt;script&gt;" in text
        assert "<script>" not in text

    @patch("handlers.fulfillment_admin_handlers.is_admin", return_value=True)
    @patch("handlers.fulfillment_admin_handlers.get_service")
    async def test_fulfilled_package_hides_deliver_button(
        self, mock_get_service, _admin, make_callback, admin_user
    ):
        from types import SimpleNamespace

        row = SimpleNamespace(
            id=8,
            product=SimpleNamespace(name="Pkg Product"),
            order_item=SimpleNamespace(order_id=20),
            user_id=555,
            status=SimpleNamespace(value="fulfilled"),
            fulfillment_kind=SimpleNamespace(value="package"),
            user_input=None,
        )
        _mock_fulfill_ctx(mock_get_service, get_fulfillment_by_id=row)
        cb = make_callback(data="fulfill_admin_item:8", user=admin_user)
        from keyboards.callback_data import FulfillmentAdminItemCallback
        from handlers.fulfillment_admin_handlers import fulfillment_admin_item_detail

        await fulfillment_admin_item_detail(cb, FulfillmentAdminItemCallback(fulfillment_id=8))
        kb = cb.message.edit_text.call_args[1]["reply_markup"]
        labels = [btn.text for row in kb.inline_keyboard for btn in row]
        assert "📦 Entregar paquete" not in labels


class TestFulfillmentAdminDeliver:
    @patch("handlers.fulfillment_admin_handlers.is_admin", return_value=True)
    @patch("handlers.fulfillment_admin_handlers.get_service")
    async def test_deliver_start_no_packages(self, mock_get_service, _admin, make_callback, admin_user):
        store_svc = MagicMock()
        store_svc.get_available_packages_for_store.return_value = []
        ctx = MagicMock()
        ctx.__enter__.return_value = store_svc
        mock_get_service.return_value = ctx
        cb = make_callback(data="fulfill_deliver_start:3", user=admin_user)
        from handlers.fulfillment_admin_handlers import fulfillment_admin_deliver_start

        state = AsyncMock()
        await fulfillment_admin_deliver_start(cb, state)
        cb.answer.assert_called_once()
        assert cb.answer.call_args[1].get("show_alert") is True

    @patch("handlers.fulfillment_admin_handlers.is_admin", return_value=True)
    @patch("handlers.fulfillment_admin_handlers.get_service")
    async def test_deliver_package_success(
        self, mock_get_service, _admin, make_callback, admin_user
    ):
        svc = _mock_fulfill_ctx(
            mock_get_service,
            admin_deliver_package_from_queue=(True, "Entregado"),
        )
        cb = make_callback(data="fulfill_deliver:1:2", user=admin_user)
        from keyboards.callback_data import FulfillmentAdminDeliverCallback
        from handlers.fulfillment_admin_handlers import fulfillment_admin_deliver_package

        await fulfillment_admin_deliver_package(
            cb, FulfillmentAdminDeliverCallback(fulfillment_id=1, package_id=2)
        )
        svc.admin_deliver_package_from_queue.assert_awaited_once()
        cb.message.edit_text.assert_called_once()

    @patch("handlers.fulfillment_admin_handlers.is_admin", return_value=True)
    @patch("handlers.fulfillment_admin_handlers.get_service")
    async def test_deliver_package_error_shows_alert(
        self, mock_get_service, _admin, make_callback, admin_user
    ):
        _mock_fulfill_ctx(mock_get_service, admin_deliver_package_from_queue=(False, "Error"))
        cb = make_callback(data="fulfill_deliver:1:2", user=admin_user)
        from keyboards.callback_data import FulfillmentAdminDeliverCallback
        from handlers.fulfillment_admin_handlers import fulfillment_admin_deliver_package

        await fulfillment_admin_deliver_package(
            cb, FulfillmentAdminDeliverCallback(fulfillment_id=1, package_id=2)
        )
        cb.answer.assert_called_once()
        assert cb.answer.call_args[1].get("show_alert") is True