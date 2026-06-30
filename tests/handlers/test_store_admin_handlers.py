"""
Tests unitarios para store_admin_handlers.

Cubre handlers del panel de administración de tienda:
- AdminStoreMenu: resumen y alertas de stock
- CreateProductWizard: FSM de 5 pasos + confirmación
- ListProducts: menú de niveles con conteo
- AdminListTierProducts: productos filtrados por nivel
- ToggleProduct: activar/desactivar producto
- HandleDeleteProduct: confirmación y eliminación
- StoreStats: estadísticas de tienda
"""

from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

from tests.helpers import model_mock
from models.models import StoreProduct, StoreTier

import pytest

from services.store_service import StoreService

pytestmark = [pytest.mark.unit]


def _mock_store_admin_ctx(mock_get_service):
    """Mock get_service(StoreService) context manager con autospec."""
    svc = create_autospec(StoreService, spec_set=True, instance=True)
    mock_get_service.return_value.__enter__.return_value = svc
    return svc


class TestAdminStoreMenu:
    """Tests para admin_store_menu — menú principal de administración de tienda."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_shows_store_menu_with_stats(self, mock_get_service, make_callback):
        """Muestra el menú con estadísticas correctas."""
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_store_stats.return_value = {
            "available_products": 5,
            "total_products": 10,
            "completed_orders": 20,
            "total_besitos_spent": 1500,
        }
        mock_store.get_low_stock_products.return_value = []
        mock_store.get_out_of_stock_products.return_value = []

        cb = make_callback(data="admin_store")

        from handlers.store_admin_handlers import admin_store_menu

        await admin_store_menu(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "5" in text
        assert "10" in text
        assert "20" in text
        assert "1500" in text
        cb.answer.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_shows_low_stock_warning(self, mock_get_service, make_callback):
        """Muestra advertencia cuando hay productos con stock bajo."""
        mock_low_product = model_mock(StoreProduct)
        mock_low_product.name = "Bajo Stock"
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_store_stats.return_value = {
            "available_products": 5,
            "total_products": 10,
            "completed_orders": 20,
            "total_besitos_spent": 1500,
        }
        mock_store.get_low_stock_products.return_value = [mock_low_product]
        mock_store.get_out_of_stock_products.return_value = []

        cb = make_callback(data="admin_store")

        from handlers.store_admin_handlers import admin_store_menu

        await admin_store_menu(cb)

        text = cb.message.edit_text.call_args[0][0]
        assert "Stock bajo" in text
        assert "1" in text

    @patch("handlers.store_admin_handlers.get_service")
    async def test_shows_out_of_stock_warning(self, mock_get_service, make_callback):
        """Muestra advertencia cuando hay productos agotados."""
        mock_out_product = model_mock(StoreProduct)
        mock_out_product.name = "Agotado"
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_store_stats.return_value = {
            "available_products": 5,
            "total_products": 10,
            "completed_orders": 20,
            "total_besitos_spent": 1500,
        }
        mock_store.get_low_stock_products.return_value = []
        mock_store.get_out_of_stock_products.return_value = [mock_out_product]

        cb = make_callback(data="admin_store")

        from handlers.store_admin_handlers import admin_store_menu

        await admin_store_menu(cb)

        text = cb.message.edit_text.call_args[0][0]
        assert "Agotados" in text
        assert "1" in text

    @patch("handlers.store_admin_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Siempre llama a callback.answer()."""
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_store_stats.return_value = {
            "available_products": 5,
            "total_products": 10,
            "completed_orders": 20,
            "total_besitos_spent": 1500,
        }
        mock_store.get_low_stock_products.return_value = []
        mock_store.get_out_of_stock_products.return_value = []

        cb = make_callback(data="admin_store")

        from handlers.store_admin_handlers import admin_store_menu

        await admin_store_menu(cb)

        cb.answer.assert_called_once()


class TestCreateProductStart:
    """Tests para create_product_start — inicio del wizard de creación."""

    async def test_sets_waiting_name_state(self, make_callback, make_fsm_context):
        """Establece el estado waiting_name y muestra instrucciones."""
        cb = make_callback(data="create_product")
        fsm = await make_fsm_context()

        from handlers.store_admin_handlers import ProductWizardStates, create_product_start

        await create_product_start(cb, fsm)

        state = await fsm.get_state()
        assert state == ProductWizardStates.waiting_name
        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()

    async def test_shows_step_1_message(self, make_callback, make_fsm_context):
        """Muestra mensaje del paso 1 con instrucciones."""
        cb = make_callback(data="create_product")
        fsm = await make_fsm_context()

        from handlers.store_admin_handlers import create_product_start

        await create_product_start(cb, fsm)

        text = cb.message.edit_text.call_args[0][0]
        assert "Paso 1 de 5" in text
        assert "Nombre" in text


class TestProcessProductName:
    """Tests para process_product_name — paso 1: nombre del producto."""

    async def test_rejects_short_name(self, make_message, make_fsm_context):
        """Nombre menor a 3 caracteres muestra error y no avanza."""
        from handlers.store_admin_handlers import ProductWizardStates, process_product_name

        msg = make_message(text="AB")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_name)
        await process_product_name(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "3 caracteres" in text
        state = await fsm.get_state()
        assert state == ProductWizardStates.waiting_name

    async def test_accepts_valid_name_and_advances(self, make_message, make_fsm_context):
        """Nombre válido guarda en state y avanza a waiting_description."""
        from handlers.store_admin_handlers import ProductWizardStates, process_product_name

        msg = make_message(text="Pack Fotos Marzo")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_name)
        await process_product_name(msg, fsm)

        data = await fsm.get_data()
        assert data["name"] == "Pack Fotos Marzo"
        state = await fsm.get_state()
        assert state == ProductWizardStates.waiting_description
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Paso 2 de 5" in text


class TestProcessProductDescription:
    """Tests para process_product_description — paso 2: descripción.
    Tests ported to 1-service pattern (get_service(StoreService) only + delegate for packages in wizard) + pure UI helpers (compute_stock_emoji_and_text etc). Arch-enforcer note (long funcs >50L, business logic/UI bloat in handlers, direct other svc in wizard) addressed. Precedent from item7 (reward) + item2/5/6.
    """

    @patch("handlers.store_admin_handlers.get_service")
    async def test_with_skip_sets_none(self, mock_get_service, make_message, make_fsm_context):
        """/skip establece description=None y muestra tiers."""
        from handlers.store_admin_handlers import ProductWizardStates, process_product_description

        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_tier = model_mock(StoreTier)
        mock_tier.id = 1
        mock_tier.name = "Reservado"
        mock_store.get_all_tiers.return_value = [mock_tier]

        msg = make_message(text="/skip")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_description)
        await process_product_description(msg, fsm)

        data = await fsm.get_data()
        assert data["description"] is None
        mock_store.get_all_tiers.assert_called_once()
        assert await fsm.get_state() == ProductWizardStates.selecting_tier

    @patch("handlers.store_admin_handlers.get_service")
    async def test_with_description_saves_it(
        self, mock_get_service, make_message, make_fsm_context
    ):
        """Descripción textual se guarda y se muestran tiers."""
        from handlers.store_admin_handlers import ProductWizardStates, process_product_description

        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_tier = model_mock(StoreTier)
        mock_tier.id = 1
        mock_tier.name = "Reservado"
        mock_store.get_all_tiers.return_value = [mock_tier]

        msg = make_message(text="Un pack de fotos exclusivas")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_description)
        await process_product_description(msg, fsm)

        data = await fsm.get_data()
        assert data["description"] == "Un pack de fotos exclusivas"
        mock_store.get_all_tiers.assert_called_once()
        assert await fsm.get_state() == ProductWizardStates.selecting_tier

    @patch("handlers.store_admin_handlers.get_service")
    async def test_no_tiers_clears_state(self, mock_get_service, make_message, make_fsm_context):
        """Sin tiers disponibles, limpia estado."""
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_all_tiers.return_value = []

        msg = make_message(text="Descripción test")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_description)

        from handlers.store_admin_handlers import process_product_description

        await process_product_description(msg, fsm)

        msg.answer.assert_called_once()
        assert await fsm.get_state() is None

    @patch("handlers.store_admin_handlers.get_service")
    async def test_advances_to_selecting_tier(
        self, mock_get_service, make_message, make_fsm_context
    ):
        """Con tiers disponibles, avanza a selecting_tier."""
        from handlers.store_admin_handlers import ProductWizardStates, process_product_description

        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_tier = model_mock(StoreTier)
        mock_tier.id = 2
        mock_tier.name = "Mitico"
        mock_store.get_all_tiers.return_value = [mock_tier]

        msg = make_message(text="Descripción")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_description)
        await process_product_description(msg, fsm)

        assert await fsm.get_state() == ProductWizardStates.selecting_tier
        mock_store.get_all_tiers.assert_called_once()


class TestProcessProductPrice:
    """Tests para process_product_price — paso 4: precio."""

    async def test_rejects_invalid_price(self, make_message, make_fsm_context):
        """Precio no numérico muestra error."""
        from handlers.store_admin_handlers import ProductWizardStates, process_product_price

        msg = make_message(text="caro")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_price)
        await process_product_price(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "numero valido" in text
        state = await fsm.get_state()
        assert state == ProductWizardStates.waiting_price

    async def test_rejects_zero_price(self, make_message, make_fsm_context):
        """Precio 0 muestra error."""
        from handlers.store_admin_handlers import ProductWizardStates, process_product_price

        msg = make_message(text="0")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_price)
        await process_product_price(msg, fsm)

        msg.answer.assert_called_once()
        state = await fsm.get_state()
        assert state == ProductWizardStates.waiting_price

    async def test_accepts_valid_price_and_advances(self, make_message, make_fsm_context):
        """Precio válido guarda en state y avanza a waiting_stock."""
        from handlers.store_admin_handlers import ProductWizardStates, process_product_price

        msg = make_message(text="150")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_price)
        await process_product_price(msg, fsm)

        data = await fsm.get_data()
        assert data["price"] == 150
        state = await fsm.get_state()
        assert state == ProductWizardStates.waiting_stock
        msg.answer.assert_called_once()


class TestProductStockUnlimited:
    """Tests para product_stock_unlimited — stock ilimitado en wizard."""

    async def test_sets_stock_unlimited_and_shows_confirmation(
        self, make_callback, make_fsm_context
    ):
        """Establece stock=-1 y llama a confirmación."""
        cb = make_callback(data="product_stock_unlimited")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_stock)
        await fsm.update_data(name="Test", description="Desc", price=100)

        from handlers.store_admin_handlers import product_stock_unlimited

        await product_stock_unlimited(cb, fsm)

        data = await fsm.get_data()
        assert data["stock"] == -1
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Cupo mensual" in text
        assert await fsm.get_state() == ProductWizardStates.waiting_monthly_cap
        cb.answer.assert_called_once()


class TestProductStockLimited:
    """Tests para product_stock_limited — solicitar cantidad limitada."""

    async def test_asks_for_quantity(self, make_callback, make_fsm_context):
        """Pide al usuario que indique la cantidad."""
        cb = make_callback(data="product_stock_limited")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_stock)

        from handlers.store_admin_handlers import product_stock_limited

        await product_stock_limited(cb, fsm)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "unidades" in text.lower()
        cb.answer.assert_called_once()


class TestProcessProductStock:
    """Tests para process_product_stock — paso 5: stock por mensaje."""

    async def test_rejects_invalid_stock(self, make_message, make_fsm_context):
        """Stock no numérico muestra error."""
        from handlers.store_admin_handlers import ProductWizardStates, process_product_stock

        msg = make_message(text="mucho")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_stock)
        await process_product_stock(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "numero valido" in text
        state = await fsm.get_state()
        assert state == ProductWizardStates.waiting_stock

    async def test_rejects_negative_stock(self, make_message, make_fsm_context):
        """Stock negativo muestra error."""
        from handlers.store_admin_handlers import ProductWizardStates, process_product_stock

        msg = make_message(text="-5")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_stock)
        await process_product_stock(msg, fsm)

        msg.answer.assert_called_once()
        state = await fsm.get_state()
        assert state == ProductWizardStates.waiting_stock

    async def test_accepts_valid_stock_and_shows_confirmation(self, make_message, make_fsm_context):
        """Stock válido guarda en state y muestra confirmación."""
        msg = make_message(text="50")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_stock)
        await fsm.update_data(name="Test", description="Desc", price=100)

        from handlers.store_admin_handlers import process_product_stock

        await process_product_stock(msg, fsm)

        data = await fsm.get_data()
        assert data["stock"] == 50
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Cupo mensual" in text
        assert await fsm.get_state() == ProductWizardStates.waiting_monthly_cap


class TestConfirmCreateProduct:
    """Tests para confirm_create_product — creación final del producto."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_creates_product_successfully(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Crea el producto y muestra mensaje de éxito."""
        mock_product = model_mock(StoreProduct)
        mock_product.name = "Pack Fotos"
        mock_product.price = 150
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.create_product.return_value = mock_product

        cb = make_callback(data="confirm_create_product")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.confirming)
        await fsm.update_data(
            name="Pack Fotos",
            description="Fotos exclusivas",
            package_id=1,
            price=150,
            stock=10,
        )

        from handlers.store_admin_handlers import confirm_create_product

        await confirm_create_product(cb, fsm)

        mock_store.create_product.assert_called_once()
        call_kwargs = mock_store.create_product.call_args.kwargs
        assert call_kwargs["name"] == "Pack Fotos"
        assert call_kwargs["package_id"] == 1
        assert call_kwargs["price"] == 150
        assert call_kwargs["stock"] == 10
        assert call_kwargs["created_by"] == 123456789
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "creado" in text.lower()
        assert "Pack Fotos" in text
        state = await fsm.get_state()
        assert state is None
        cb.answer.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_handles_creation_exception(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Cuando create_product lanza excepción, muestra error."""
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.create_product.side_effect = Exception("DB error")

        cb = make_callback(data="confirm_create_product")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.confirming)
        await fsm.update_data(
            name="Pack Fotos",
            description="Fotos exclusivas",
            package_id=1,
            price=150,
            stock=10,
        )

        from handlers.store_admin_handlers import confirm_create_product

        await confirm_create_product(cb, fsm)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Error" in text
        state = await fsm.get_state()
        assert state is None
        cb.answer.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_clears_state_on_success(self, mock_get_service, make_callback, make_fsm_context):
        """Limpia el estado FSM después de crear."""
        mock_product = model_mock(StoreProduct)
        mock_product.name = "Test"
        mock_product.price = 100
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.create_product.return_value = mock_product

        cb = make_callback(data="confirm_create_product")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.confirming)
        await fsm.update_data(name="Test", package_id=1, price=100, stock=5)

        from handlers.store_admin_handlers import confirm_create_product

        await confirm_create_product(cb, fsm)

        state = await fsm.get_state()
        assert state is None

    @patch("handlers.store_admin_handlers.get_service")
    async def test_creates_with_default_stock(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Usa stock por defecto -1 si no está en data."""
        mock_product = model_mock(StoreProduct)
        mock_product.name = "Test"
        mock_product.price = 100
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.create_product.return_value = mock_product

        cb = make_callback(data="confirm_create_product")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.confirming)
        await fsm.update_data(name="Test", package_id=1, price=100)

        from handlers.store_admin_handlers import confirm_create_product

        await confirm_create_product(cb, fsm)

        mock_store.create_product.assert_called_once()
        args = mock_store.create_product.call_args[1]
        assert args["stock"] == -1


class TestListProducts:
    """Tests para list_products — menú de niveles con conteo."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_shows_empty_message_when_no_products(self, mock_get_service, make_callback):
        """Cuando no hay tiers ni productos, muestra mensaje vacío."""
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_all_tiers.return_value = []
        mock_store.count_products_without_tier.return_value = 0

        cb = make_callback(data="list_products")

        from handlers.store_admin_handlers import list_products

        await list_products(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay productos" in text
        cb.answer.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_shows_tier_menu_with_product_counts(self, mock_get_service, make_callback):
        """Muestra niveles con nombre y conteo en cada botón."""
        tier_impulso = model_mock(StoreTier)
        tier_impulso.id = 1
        tier_impulso.name = "IMPULSO"
        tier_deseo = model_mock(StoreTier)
        tier_deseo.id = 2
        tier_deseo.name = "DESEO"

        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_all_tiers.return_value = [tier_impulso, tier_deseo]
        mock_store.count_products_without_tier.return_value = 0
        mock_store.count_products_by_tier.side_effect = lambda tid, active_only=False: {
            1: 3,
            2: 7,
        }[tid]

        cb = make_callback(data="list_products")

        from handlers.store_admin_handlers import list_products

        await list_products(cb)

        cb.message.edit_text.assert_called_once()
        kb = cb.message.edit_text.call_args[1]["reply_markup"]
        button_texts = [row[0].text for row in kb.inline_keyboard[:-1]]
        assert "IMPULSO (3)" in button_texts
        assert "DESEO (7)" in button_texts
        cb.answer.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_shows_sin_nivel_when_orphan_products_exist(
        self, mock_get_service, make_callback
    ):
        """Incluye botón Sin nivel si hay productos sin tier."""
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_all_tiers.return_value = []
        mock_store.count_products_without_tier.return_value = 2

        cb = make_callback(data="list_products")

        from handlers.store_admin_handlers import list_products

        await list_products(cb)

        kb = cb.message.edit_text.call_args[1]["reply_markup"]
        button_texts = [row[0].text for row in kb.inline_keyboard[:-1]]
        assert "Sin nivel (2)" in button_texts


class TestAdminListTierProducts:
    """Tests para admin_list_tier_products — productos filtrados por nivel."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_lists_tier_products_only(self, mock_get_service, make_callback):
        """Muestra solo productos del tier seleccionado."""
        tier = model_mock(StoreTier)
        tier.id = 2
        tier.name = "DESEO"

        mock_prod = model_mock(StoreProduct)
        mock_prod.id = 10
        mock_prod.name = "Producto Tier 2"
        mock_prod.is_active = True
        mock_prod.stock = 5
        mock_prod.is_low_stock = False
        mock_prod.price = 150

        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_all_tiers.return_value = [tier]
        mock_store.get_products_by_tier.return_value = [mock_prod]

        from keyboards.callback_data import AdminStoreTierCallback
        from handlers.store_admin_handlers import admin_list_tier_products

        cb = make_callback(data=AdminStoreTierCallback(tier_id=2).pack())
        await admin_list_tier_products(cb, AdminStoreTierCallback(tier_id=2))

        mock_store.get_products_by_tier.assert_called_once_with(2, active_only=False)
        text = cb.message.edit_text.call_args[0][0]
        assert "DESEO" in text
        assert "Producto Tier 2" in text

    @patch("handlers.store_admin_handlers.get_service")
    async def test_tier_not_found_shows_alert(self, mock_get_service, make_callback):
        """Tier inexistente muestra alerta."""
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_all_tiers.return_value = []

        from keyboards.callback_data import AdminStoreTierCallback
        from handlers.store_admin_handlers import admin_list_tier_products

        cb = make_callback(data=AdminStoreTierCallback(tier_id=99).pack())
        await admin_list_tier_products(cb, AdminStoreTierCallback(tier_id=99))

        cb.answer.assert_called_once()
        assert cb.answer.call_args[1].get("show_alert") is True

    @patch("handlers.store_admin_handlers.get_service")
    async def test_empty_tier_shows_no_products_message(self, mock_get_service, make_callback):
        """Tier sin productos muestra mensaje dedicado."""
        tier = model_mock(StoreTier)
        tier.id = 1
        tier.name = "IMPULSO"

        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_all_tiers.return_value = [tier]
        mock_store.get_products_by_tier.return_value = []

        from keyboards.callback_data import AdminStoreTierCallback
        from handlers.store_admin_handlers import admin_list_tier_products

        cb = make_callback(data=AdminStoreTierCallback(tier_id=1).pack())
        await admin_list_tier_products(cb, AdminStoreTierCallback(tier_id=1))

        text = cb.message.edit_text.call_args[0][0]
        assert "IMPULSO" in text
        assert "No hay productos" in text


class TestToggleProduct:
    """Tests para toggle_product — activar/desactivar producto."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_toggles_active_product_to_inactive(self, mock_get_service, make_callback):
        """Producto activo se desactiva y muestra detalle."""
        mock_product = model_mock(StoreProduct)
        mock_product.is_active = True
        mock_product.id = 1
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_product.return_value = mock_product

        from keyboards.callback_data import ToggleProductCallback

        cb_data = ToggleProductCallback(product_id=1)
        cb = make_callback(data=cb_data.pack())

        from handlers.store_admin_handlers import toggle_product

        await toggle_product(cb, cb_data)

        mock_store.update_product.assert_called_once_with(1, is_active=False)
        cb.answer.assert_any_call("Producto desactivado")

    @patch("handlers.store_admin_handlers.get_service")
    async def test_toggles_inactive_product_to_active(self, mock_get_service, make_callback):
        """Producto inactivo se activa y muestra detalle."""
        mock_product = model_mock(StoreProduct)
        mock_product.is_active = False
        mock_product.id = 1
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_product.return_value = mock_product

        from keyboards.callback_data import ToggleProductCallback

        cb_data = ToggleProductCallback(product_id=1)
        cb = make_callback(data=cb_data.pack())

        from handlers.store_admin_handlers import toggle_product

        await toggle_product(cb, cb_data)

        mock_store.update_product.assert_called_once_with(1, is_active=True)
        cb.answer.assert_any_call("Producto activado")

    @patch("handlers.store_admin_handlers.get_service")
    async def test_product_not_found_shows_alert(self, mock_get_service, make_callback):
        """Producto no encontrado muestra alerta."""
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_product.return_value = None

        from keyboards.callback_data import ToggleProductCallback

        cb_data = ToggleProductCallback(product_id=999)
        cb = make_callback(data=cb_data.pack())

        from handlers.store_admin_handlers import toggle_product

        await toggle_product(cb, cb_data)

        cb.answer.assert_called_once_with("Producto no encontrado", show_alert=True)
        mock_store.update_product.assert_not_called()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_calls_product_admin_detail_after_toggle(self, mock_get_service, make_callback):
        """Después de toggle, llama a product_admin_detail."""
        mock_product = model_mock(StoreProduct)
        mock_product.is_active = True
        mock_product.id = 1
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_product.return_value = mock_product

        from keyboards.callback_data import ToggleProductCallback

        cb_data = ToggleProductCallback(product_id=1)
        cb = make_callback(data=cb_data.pack())

        from handlers.store_admin_handlers import product_admin_detail, toggle_product

        original_detail = product_admin_detail

        patched_detail = AsyncMock()
        import handlers.store_admin_handlers as mod

        original = mod.product_admin_detail
        mod.product_admin_detail = patched_detail
        try:
            await toggle_product(cb, cb_data)
            patched_detail.assert_called_once()
        finally:
            mod.product_admin_detail = original


class TestHandleDeleteProduct:
    """Tests para handle_delete_product — eliminación de producto."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_unconfirmed_shows_confirmation(self, mock_get_service, make_callback):
        """Sin confirmación, muestra diálogo de confirmación."""
        mock_store = _mock_store_admin_ctx(mock_get_service)

        from keyboards.callback_data import DeleteProductCallback

        cb_data = DeleteProductCallback(product_id=1, confirmed=False)
        cb = make_callback(data=cb_data.pack())

        from handlers.store_admin_handlers import handle_delete_product

        await handle_delete_product(cb, cb_data)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "seguro" in text.lower()
        cb.answer.assert_called_once()
        mock_store.delete_product.assert_not_called()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_confirmed_deletes_successfully(self, mock_get_service, make_callback):
        """Confirmado y eliminación exitosa, muestra mensaje."""
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.delete_product.return_value = True

        from keyboards.callback_data import DeleteProductCallback

        cb_data = DeleteProductCallback(product_id=1, confirmed=True)
        cb = make_callback(data=cb_data.pack())

        from handlers.store_admin_handlers import handle_delete_product

        await handle_delete_product(cb, cb_data)

        mock_store.delete_product.assert_called_once_with(1)
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "eliminado" in text.lower()
        cb.answer.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_confirmed_delete_fails_shows_error(self, mock_get_service, make_callback):
        """Confirmado pero eliminación falla, muestra error."""
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.delete_product.return_value = False

        from keyboards.callback_data import DeleteProductCallback

        cb_data = DeleteProductCallback(product_id=1, confirmed=True)
        cb = make_callback(data=cb_data.pack())

        from handlers.store_admin_handlers import handle_delete_product

        await handle_delete_product(cb, cb_data)

        mock_store.delete_product.assert_called_once_with(1)
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Error" in text or "eliminar" in text
        cb.answer.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_calls_delete_product_with_correct_id(self, mock_get_service, make_callback):
        """Llama a delete_product con el product_id correcto."""
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.delete_product.return_value = True

        from keyboards.callback_data import DeleteProductCallback

        cb_data = DeleteProductCallback(product_id=42, confirmed=True)
        cb = make_callback(data=cb_data.pack())

        from handlers.store_admin_handlers import handle_delete_product

        await handle_delete_product(cb, cb_data)

        mock_store.delete_product.assert_called_once_with(42)


class TestStoreStats:
    """Tests para store_stats — estadísticas de la tienda."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_shows_store_statistics(self, mock_get_service, make_callback):
        """Muestra estadísticas completas de la tienda."""
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_store_stats.return_value = {
            "available_products": 8,
            "total_products": 15,
            "completed_orders": 25,
            "total_orders": 30,
            "total_besitos_spent": 2500,
        }

        cb = make_callback(data="store_stats")

        from handlers.store_admin_handlers import store_stats

        await store_stats(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "8" in text
        assert "15" in text
        assert "25" in text
        assert "30" in text
        assert "2500" in text
        assert "Estadisticas" in text
        cb.answer.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Siempre llama a callback.answer()."""
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_store_stats.return_value = {
            "available_products": 0,
            "total_products": 0,
            "completed_orders": 0,
            "total_orders": 0,
            "total_besitos_spent": 0,
        }

        cb = make_callback(data="store_stats")

        from handlers.store_admin_handlers import store_stats

        await store_stats(cb)

        cb.answer.assert_called_once()


class TestStoreAdminPureHelpers:
    """Tests para los helpers puros extraídos de store_admin_handlers (Item 8 / arch-enforcer long-funcs + 1svc)."""

    def test_compute_stock_emoji_and_text_unlimited(self):
        from handlers.store_admin_handlers import compute_stock_emoji_and_text

        emoji, text = compute_stock_emoji_and_text(-1)
        assert emoji == "♾️"
        assert text == "∞"

    def test_compute_stock_emoji_and_text_out_of_stock(self):
        from handlers.store_admin_handlers import compute_stock_emoji_and_text

        emoji, text = compute_stock_emoji_and_text(0)
        assert emoji == "🚨"
        assert text == "AGOTADO"

    def test_compute_stock_emoji_and_text_low_stock(self):
        from handlers.store_admin_handlers import compute_stock_emoji_and_text

        emoji, text = compute_stock_emoji_and_text(3, is_low_stock=True)
        assert emoji == "⚠️"
        assert text == "3"

    def test_compute_stock_emoji_and_text_normal(self):
        from handlers.store_admin_handlers import compute_stock_emoji_and_text

        emoji, text = compute_stock_emoji_and_text(10, is_low_stock=False)
        assert emoji == "📦"
        assert text == "10"

    def test_compute_restock_new_stock_from_unlimited(self):
        from handlers.store_admin_handlers import compute_restock_new_stock

        assert compute_restock_new_stock(-1, 5) == 5

    def test_compute_restock_new_stock_normal(self):
        from handlers.store_admin_handlers import compute_restock_new_stock

        assert compute_restock_new_stock(10, 3) == 13

    def test_build_product_detail_keyboard(self):
        from handlers.store_admin_handlers import build_product_detail_keyboard

        kb = build_product_detail_keyboard(42, is_active=True)
        assert len(kb.inline_keyboard) == 6
        assert "Editar" in kb.inline_keyboard[0][0].text
        assert "Desactivar" in kb.inline_keyboard[1][0].text
        assert "42" in kb.inline_keyboard[1][0].callback_data  # packed contains id
        assert "Reabastecer" in kb.inline_keyboard[2][0].text
        assert "list_products" in kb.inline_keyboard[5][0].callback_data

    def test_build_product_detail_keyboard_back_to_tier(self):
        from handlers.store_admin_handlers import build_product_detail_keyboard
        from keyboards.callback_data import AdminStoreTierCallback

        kb = build_product_detail_keyboard(42, is_active=True, tier_id=3)
        assert AdminStoreTierCallback(tier_id=3).pack() in kb.inline_keyboard[5][0].callback_data

    def test_build_admin_tier_menu_text_and_buttons(self):
        from handlers.store_admin_handlers import build_admin_tier_menu_text_and_buttons

        tier = model_mock(StoreTier)
        tier.id = 1
        tier.name = "IMPULSO"
        text, buttons = build_admin_tier_menu_text_and_buttons([(tier, 4)], sin_nivel_count=2)
        assert "Gabinete" in text
        assert buttons[0][0].text == "IMPULSO (4)"
        assert buttons[1][0].text == "Sin nivel (2)"
        assert buttons[2][0].callback_data == "admin_store"

    def test_build_product_edit_menu_text(self):
        from handlers.store_admin_handlers import build_product_edit_menu_text

        mock_product = model_mock(StoreProduct)
        mock_product.name = "Pack VIP"
        mock_product.description = "Contenido exclusivo"
        mock_product.price = 200
        mock_product.stock = 10
        mock_product.package.name = "Paquete Marzo"
        mock_product.tier.name = "DESEO"

        text = build_product_edit_menu_text(mock_product)
        assert "Pack VIP" in text
        assert "Contenido exclusivo" in text
        assert "DESEO" in text
        assert "Paquete Marzo" in text
        assert "200" in text
        assert "10" in text

    def test_build_product_edit_menu_keyboard(self):
        from handlers.store_admin_handlers import build_product_edit_menu_keyboard

        mock_product = model_mock(StoreProduct)
        mock_product.id = 7
        mock_product.fulfillment_kind = "package"

        kb = build_product_edit_menu_keyboard(mock_product)
        assert len(kb.inline_keyboard) == 7
        assert "Nombre" in kb.inline_keyboard[0][0].text
        assert "Nivel" in kb.inline_keyboard[2][0].text
        assert "Paquete" in kb.inline_keyboard[3][0].text
        assert "7" in kb.inline_keyboard[6][0].callback_data

    def test_build_wizard_tariff_keyboard(self):
        from handlers.store_admin_handlers import build_wizard_tariff_keyboard

        mock_tariff = MagicMock()
        mock_tariff.id = 2
        mock_tariff.name = "VIP 30 dias"
        mock_tariff.duration_days = 30

        kb = build_wizard_tariff_keyboard([mock_tariff])
        assert "VIP 30 dias" in kb.inline_keyboard[0][0].text
        assert "wiz_store_tariff" in kb.inline_keyboard[0][0].callback_data

    def test_build_wizard_story_node_keyboard(self):
        from handlers.store_admin_handlers import build_wizard_story_node_keyboard

        mock_node = MagicMock()
        mock_node.id = 5
        mock_node.title = "Capitulo 1"

        kb = build_wizard_story_node_keyboard([mock_node])
        assert "Capitulo 1" in kb.inline_keyboard[0][0].text
        assert "wiz_store_story" in kb.inline_keyboard[0][0].callback_data

    def test_build_product_edit_menu_vip_shows_tariff(self):
        from models.models import FulfillmentKind
        from handlers.store_admin_handlers import (
            build_product_edit_menu_keyboard,
            build_product_edit_menu_text,
        )

        mock_product = model_mock(StoreProduct)
        mock_product.id = 1
        mock_product.name = "VIP Pack"
        mock_product.description = "Desc"
        mock_product.price = 100
        mock_product.stock = 5
        mock_product.package = None
        mock_product.fulfillment_kind = FulfillmentKind.VIP_GRANT
        mock_product.tariff.name = "VIP Mensual"

        text = build_product_edit_menu_text(mock_product)
        assert "👑 Tarifa: VIP Mensual" in text

        kb = build_product_edit_menu_keyboard(mock_product)
        labels = [row[0].text for row in kb.inline_keyboard]
        assert "👑 Tarifa VIP" in labels

    def test_build_product_edit_menu_package_no_tariff_button(self):
        from models.models import FulfillmentKind
        from handlers.store_admin_handlers import build_product_edit_menu_keyboard

        mock_product = model_mock(StoreProduct)
        mock_product.id = 3
        mock_product.fulfillment_kind = FulfillmentKind.PACKAGE

        kb = build_product_edit_menu_keyboard(mock_product)
        labels = [row[0].text for row in kb.inline_keyboard]
        assert "👑 Tarifa VIP" not in labels

    def test_build_product_confirmation_includes_tariff_name(self):
        from handlers.store_admin_handlers import build_product_confirmation_text_and_keyboard

        data = {
            "name": "VIP Product",
            "description": "Desc",
            "price": 200,
            "stock": 10,
            "fulfillment_kind": "vip_grant",
            "tariff_name": "VIP 30 dias",
        }
        text, _kb = build_product_confirmation_text_and_keyboard(data)
        assert "VIP 30 dias" in text
        assert "👑 Tarifa" in text

    def test_build_product_confirmation_text_and_keyboard(self):
        from handlers.store_admin_handlers import build_product_confirmation_text_and_keyboard

        data = {"name": "Test", "description": None, "price": 100, "stock": -1}
        text, kb = build_product_confirmation_text_and_keyboard(data)
        assert "Resumen del producto" in text
        assert "Sin descripcion" in text
        assert "100" in text
        assert "Ilimitado" in text
        assert len(kb.inline_keyboard) == 2
        assert "Crear" in kb.inline_keyboard[0][0].text

    def test_build_product_list_entry_and_button(self):
        from handlers.store_admin_handlers import build_product_list_entry_and_button

        mock_product = model_mock(StoreProduct)
        mock_product.is_active = True
        mock_product.name = "Sample Product Name That Is Long"
        mock_product.stock = 7
        mock_product.is_low_stock = False
        mock_product.price = 50
        entry, button = build_product_list_entry_and_button(mock_product)
        assert "✅ Sample Product Name That Is Long" in entry
        assert "📦" in entry
        assert "7" in entry
        assert "50" in entry
        assert "Sample Product Name That Is Long"[:30] in button[0].text


class TestProductWizardFulfillmentSteps:
    """D3 wizard: tier → delivery_mode → fulfillment_kind routing."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_wizard_select_tier_advances_to_delivery_mode(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        mock_store = _mock_store_admin_ctx(mock_get_service)
        tier = MagicMock()
        tier.id = 3
        tier.name = "Reservado"
        mock_store.get_all_tiers.return_value = [tier]

        from handlers.store_admin_handlers import ProductWizardStates, wizard_select_tier

        cb = make_callback(data="wiz_tier:3")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.selecting_tier)

        await wizard_select_tier(cb, fsm)

        data = await fsm.get_data()
        assert data["tier_id"] == 3
        assert await fsm.get_state() == ProductWizardStates.selecting_delivery_mode
        cb.message.edit_text.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_wizard_select_delivery_mode_lists_kinds(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        from handlers.store_admin_handlers import ProductWizardStates, wizard_select_delivery_mode

        cb = make_callback(data="wiz_dm:manual")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.selecting_delivery_mode)

        await wizard_select_delivery_mode(cb, fsm)

        text = cb.message.edit_text.call_args[0][0]
        assert await fsm.get_state() == ProductWizardStates.selecting_fulfillment_kind
        markup = cb.message.edit_text.call_args[1]["reply_markup"]
        labels = [btn.text for row in markup.inline_keyboard for btn in row]
        assert "PKG_DEFERRED" in labels
        assert "CHANNEL_HONOR" in labels

    @patch("handlers.store_admin_handlers._wizard_prompt_package_selection", new_callable=AsyncMock)
    async def test_wizard_kind_package_deferred_prompts_package(
        self, mock_pkg_prompt, make_callback, make_fsm_context
    ):
        from models.models import FulfillmentKind
        from handlers.store_admin_handlers import ProductWizardStates, wizard_select_fulfillment_kind

        cb = make_callback(data=f"wiz_kind:{FulfillmentKind.PACKAGE_DEFERRED.value}")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.selecting_fulfillment_kind)

        await wizard_select_fulfillment_kind(cb, fsm)

        mock_pkg_prompt.assert_awaited_once()
        data = await fsm.get_data()
        assert data["fulfillment_kind"] == FulfillmentKind.PACKAGE_DEFERRED.value

    @patch("handlers.store_admin_handlers._wizard_prompt_tariff_selection", new_callable=AsyncMock)
    async def test_wizard_kind_vip_routes_payload(
        self, mock_tariff_prompt, make_callback, make_fsm_context
    ):
        from models.models import FulfillmentKind
        from handlers.store_admin_handlers import ProductWizardStates, wizard_select_fulfillment_kind

        cb = make_callback(data=f"wiz_kind:{FulfillmentKind.VIP_GRANT.value}")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.selecting_fulfillment_kind)

        await wizard_select_fulfillment_kind(cb, fsm)

        mock_tariff_prompt.assert_awaited_once()


class TestWizardSelectTariff:
    """Wizard: selección inline de tarifa VIP."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_callback_sets_tariff_and_advances_to_price(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        mock_tariff = MagicMock()
        mock_tariff.id = 2
        mock_tariff.name = "VIP 30 dias"
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_tariffs_for_product_wizard.return_value = [mock_tariff]

        from keyboards.callback_data import SelectTariffStoreWizardCallback
        from handlers.store_admin_handlers import ProductWizardStates, wizard_select_tariff

        cb_data = SelectTariffStoreWizardCallback(tariff_id=2)
        cb = make_callback(data=cb_data.pack())
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.selecting_tariff)

        await wizard_select_tariff(cb, fsm, cb_data)

        data = await fsm.get_data()
        assert data["tariff_id"] == 2
        assert data["tariff_name"] == "VIP 30 dias"
        assert await fsm.get_state() == ProductWizardStates.waiting_price
        mock_store.get_tariffs_for_product_wizard.assert_called_once()
        cb.answer.assert_called_once()


class TestWizardSelectStoryNode:
    """Wizard: selección inline de nodo narrativo."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_callback_sets_node_and_advances_to_price(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        mock_node = MagicMock()
        mock_node.id = 7
        mock_node.title = "Capitulo 1"
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_story_nodes_for_product_wizard.return_value = [mock_node]

        from keyboards.callback_data import SelectStoryNodeStoreWizardCallback
        from handlers.store_admin_handlers import ProductWizardStates, wizard_select_story_node

        cb_data = SelectStoryNodeStoreWizardCallback(story_node_id=7)
        cb = make_callback(data=cb_data.pack())
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.selecting_story_node)

        await wizard_select_story_node(cb, fsm, cb_data)

        data = await fsm.get_data()
        assert data["story_node_id"] == 7
        assert data["story_node_title"] == "Capitulo 1"
        assert await fsm.get_state() == ProductWizardStates.waiting_price
        mock_store.get_story_nodes_for_product_wizard.assert_called_once()
        cb.answer.assert_called_once()


class TestWizardEmptyTariffs:
    """Wizard: lista vacía de tarifas."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_empty_list_shows_no_tariffs_and_clears_fsm(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_tariffs_for_product_wizard.return_value = []

        from handlers.store_admin_handlers import _wizard_prompt_tariff_selection

        cb = make_callback()
        fsm = await make_fsm_context()
        await _wizard_prompt_tariff_selection(cb, fsm)

        text = cb.message.edit_text.call_args[0][0]
        assert "tarifas" in text.lower()
        markup = cb.message.edit_text.call_args[1]["reply_markup"]
        assert markup.inline_keyboard[0][0].callback_data == "admin_store"
        assert await fsm.get_state() is None
        mock_store.get_tariffs_for_product_wizard.assert_called_once()


class TestWizardEmptyStoryNodes:
    """Wizard: lista vacía de nodos narrativos."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_empty_list_shows_no_story_nodes(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_story_nodes_for_product_wizard.return_value = []

        from handlers.store_admin_handlers import _wizard_prompt_story_node_selection

        cb = make_callback()
        fsm = await make_fsm_context()
        await _wizard_prompt_story_node_selection(cb, fsm)

        text = cb.message.edit_text.call_args[0][0]
        assert "nodos" in text.lower()
        markup = cb.message.edit_text.call_args[1]["reply_markup"]
        assert markup.inline_keyboard[0][0].callback_data == "admin_store"
        assert await fsm.get_state() is None
        mock_store.get_story_nodes_for_product_wizard.assert_called_once()


class TestWizardRouteAfterKind:
    """Wizard: routing real tras selección de fulfillment kind."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_vip_grant_routes_to_tariff_selection(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        mock_tariff = MagicMock()
        mock_tariff.id = 1
        mock_tariff.name = "VIP 7 dias"
        mock_tariff.duration_days = 7
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_tariffs_for_product_wizard.return_value = [mock_tariff]

        from models.models import FulfillmentKind
        from handlers.store_admin_handlers import (
            ProductWizardStates,
            _wizard_route_after_kind,
        )

        cb = make_callback()
        fsm = await make_fsm_context()
        await _wizard_route_after_kind(cb, fsm, FulfillmentKind.VIP_GRANT.value)

        assert await fsm.get_state() == ProductWizardStates.selecting_tariff
        mock_store.get_tariffs_for_product_wizard.assert_called_once()
        cb.message.edit_text.assert_called_once()


class TestEditProductTariff:
    """Edición: tarifa VIP en producto VIP_GRANT."""

    def test_vip_menu_shows_tariff_button(self):
        from models.models import FulfillmentKind
        from handlers.store_admin_handlers import build_product_edit_menu_keyboard

        mock_product = model_mock(StoreProduct)
        mock_product.id = 10
        mock_product.fulfillment_kind = FulfillmentKind.VIP_GRANT

        kb = build_product_edit_menu_keyboard(mock_product)
        labels = [row[0].text for row in kb.inline_keyboard]
        assert "👑 Tarifa VIP" in labels

    @patch("handlers.store_admin_handlers.get_service")
    async def test_edit_tariff_updates_product(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.update_product.return_value = True

        from keyboards.callback_data import SelectTariffEditProductCallback
        from handlers.store_admin_handlers import (
            ProductEditStates,
            process_edit_product_tariff,
        )

        cb_data = SelectTariffEditProductCallback(product_id=10, tariff_id=3)
        cb = make_callback(data=cb_data.pack())
        fsm = await make_fsm_context()
        await fsm.set_state(ProductEditStates.selecting_tariff)

        await process_edit_product_tariff(cb, fsm, cb_data)

        mock_store.update_product.assert_called_once_with(10, tariff_id=3)
        assert await fsm.get_state() is None


class TestEditProductStoryNode:
    """Edición: nodo narrativo en producto STORY_UNLOCK."""

    def test_story_menu_shows_node_button(self):
        from models.models import FulfillmentKind
        from handlers.store_admin_handlers import build_product_edit_menu_keyboard

        mock_product = model_mock(StoreProduct)
        mock_product.id = 11
        mock_product.fulfillment_kind = FulfillmentKind.STORY_UNLOCK

        kb = build_product_edit_menu_keyboard(mock_product)
        labels = [row[0].text for row in kb.inline_keyboard]
        assert "📖 Nodo narrativo" in labels


class TestEditProductMenu:
    """Tests para edit_product_menu — menú de edición de producto."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_shows_edit_menu(self, mock_get_service, make_callback):
        mock_product = model_mock(StoreProduct)
        mock_product.name = "Producto Test"
        mock_product.description = "Desc"
        mock_product.price = 100
        mock_product.stock = -1
        mock_product.package.name = "Paquete A"

        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_product.return_value = mock_product

        from keyboards.callback_data import EditProductCallback

        cb_data = EditProductCallback(product_id=5)
        cb = make_callback(data=cb_data.pack())

        from handlers.store_admin_handlers import edit_product_menu

        await edit_product_menu(cb, cb_data)

        mock_store.get_product.assert_called_once_with(5)
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Producto Test" in text
        assert "Que campo deseas modificar" in text
        cb.answer.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_product_not_found(self, mock_get_service, make_callback):
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.get_product.return_value = None

        from keyboards.callback_data import EditProductCallback

        cb_data = EditProductCallback(product_id=999)
        cb = make_callback(data=cb_data.pack())

        from handlers.store_admin_handlers import edit_product_menu

        await edit_product_menu(cb, cb_data)

        cb.answer.assert_called_once_with("Producto no encontrado", show_alert=True)


class TestProcessEditProductName:
    """Tests para process_edit_product_name — edición de nombre."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_updates_name_successfully(self, mock_get_service, make_message, make_fsm_context):
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.update_product.return_value = True

        from handlers.store_admin_handlers import ProductEditStates, process_edit_product_name

        msg = make_message(text="Nuevo Nombre Producto")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductEditStates.waiting_name)
        await fsm.update_data(edit_product_id=3)

        await process_edit_product_name(msg, fsm)

        mock_store.update_product.assert_called_once_with(3, name="Nuevo Nombre Producto")
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "actualizado" in text.lower()
        assert await fsm.get_state() is None

    async def test_rejects_short_name(self, make_message, make_fsm_context):
        from handlers.store_admin_handlers import ProductEditStates, process_edit_product_name

        msg = make_message(text="AB")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductEditStates.waiting_name)
        await fsm.update_data(edit_product_id=3)

        await process_edit_product_name(msg, fsm)

        msg.answer.assert_called_once()
        assert "3 caracteres" in msg.answer.call_args[0][0]
        assert await fsm.get_state() == ProductEditStates.waiting_name


class TestProcessEditProductPrice:
    """Tests para process_edit_product_price — edición de precio."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_updates_price_successfully(self, mock_get_service, make_message, make_fsm_context):
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.update_product.return_value = True

        from handlers.store_admin_handlers import ProductEditStates, process_edit_product_price

        msg = make_message(text="250")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductEditStates.waiting_price)
        await fsm.update_data(edit_product_id=8)

        await process_edit_product_price(msg, fsm)

        mock_store.update_product.assert_called_once_with(8, price=250)
        msg.answer.assert_called_once()
        assert await fsm.get_state() is None

    async def test_rejects_invalid_price(self, make_message, make_fsm_context):
        from handlers.store_admin_handlers import ProductEditStates, process_edit_product_price

        msg = make_message(text="cero")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductEditStates.waiting_price)
        await fsm.update_data(edit_product_id=8)

        await process_edit_product_price(msg, fsm)

        msg.answer.assert_called_once()
        assert "numero valido" in msg.answer.call_args[0][0]


class TestProcessEditProductPackage:
    """Tests para process_edit_product_package — edición de paquete."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_updates_package_successfully(self, mock_get_service, make_callback, make_fsm_context):
        mock_store = _mock_store_admin_ctx(mock_get_service)
        mock_store.update_product.return_value = True

        from keyboards.callback_data import SelectPkgEditProductCallback
        from handlers.store_admin_handlers import ProductEditStates, process_edit_product_package

        cb_data = SelectPkgEditProductCallback(product_id=4, package_id=12)
        cb = make_callback(data=cb_data.pack())
        fsm = await make_fsm_context()
        await fsm.set_state(ProductEditStates.selecting_package)
        await process_edit_product_package(cb, fsm, cb_data)

        mock_store.update_product.assert_called_once_with(4, package_id=12)
        cb.message.edit_text.assert_called_once()
        assert await fsm.get_state() is None


# Necesario para evitar NameError en la referencia de clase inline de los handlers
from handlers.store_admin_handlers import ProductEditStates, ProductWizardStates
