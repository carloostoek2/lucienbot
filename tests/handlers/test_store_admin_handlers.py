"""
Tests unitarios para store_admin_handlers.

Cubre handlers del panel de administración de tienda:
- AdminStoreMenu: resumen y alertas de stock
- CreateProductWizard: FSM de 5 pasos + confirmación
- ListProducts: listado de todos los productos
- ToggleProduct: activar/desactivar producto
- HandleDeleteProduct: confirmación y eliminación
- StoreStats: estadísticas de tienda
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestAdminStoreMenu:
    """Tests para admin_store_menu — menú principal de administración de tienda."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_shows_store_menu_with_stats(self, mock_get_service, make_callback):
        """Muestra el menú con estadísticas correctas."""
        mock_store = MagicMock()
        mock_store.get_store_stats.return_value = {
            "available_products": 5,
            "total_products": 10,
            "completed_orders": 20,
            "total_besitos_spent": 1500,
        }
        mock_store.get_low_stock_products.return_value = []
        mock_store.get_out_of_stock_products.return_value = []
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
        mock_low_product = MagicMock()
        mock_low_product.name = "Bajo Stock"
        mock_store = MagicMock()
        mock_store.get_store_stats.return_value = {
            "available_products": 5,
            "total_products": 10,
            "completed_orders": 20,
            "total_besitos_spent": 1500,
        }
        mock_store.get_low_stock_products.return_value = [mock_low_product]
        mock_store.get_out_of_stock_products.return_value = []
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

        cb = make_callback(data="admin_store")

        from handlers.store_admin_handlers import admin_store_menu

        await admin_store_menu(cb)

        text = cb.message.edit_text.call_args[0][0]
        assert "Stock bajo" in text
        assert "1" in text

    @patch("handlers.store_admin_handlers.get_service")
    async def test_shows_out_of_stock_warning(self, mock_get_service, make_callback):
        """Muestra advertencia cuando hay productos agotados."""
        mock_out_product = MagicMock()
        mock_out_product.name = "Agotado"
        mock_store = MagicMock()
        mock_store.get_store_stats.return_value = {
            "available_products": 5,
            "total_products": 10,
            "completed_orders": 20,
            "total_besitos_spent": 1500,
        }
        mock_store.get_low_stock_products.return_value = []
        mock_store.get_out_of_stock_products.return_value = [mock_out_product]
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

        cb = make_callback(data="admin_store")

        from handlers.store_admin_handlers import admin_store_menu

        await admin_store_menu(cb)

        text = cb.message.edit_text.call_args[0][0]
        assert "Agotados" in text
        assert "1" in text

    @patch("handlers.store_admin_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Siempre llama a callback.answer()."""
        mock_store = MagicMock()
        mock_store.get_store_stats.return_value = {
            "available_products": 5,
            "total_products": 10,
            "completed_orders": 20,
            "total_besitos_spent": 1500,
        }
        mock_store.get_low_stock_products.return_value = []
        mock_store.get_out_of_stock_products.return_value = []
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
        """/skip establece description=None y muestra paquetes."""
        from handlers.store_admin_handlers import ProductWizardStates, process_product_description

        mock_store = MagicMock()
        mock_pkg = MagicMock()
        mock_pkg.id = 1
        mock_pkg.name = "Test Pkg"
        mock_pkg.file_count = 5
        mock_pkg.store_stock = -1
        mock_store.get_available_packages_for_store.return_value = [mock_pkg]
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

        msg = make_message(text="/skip")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_description)
        await process_product_description(msg, fsm)

        data = await fsm.get_data()
        assert data["description"] is None
        mock_store.get_available_packages_for_store.assert_called_once()
        mock_get_service.return_value.__exit__.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_with_description_saves_it(
        self, mock_get_service, make_message, make_fsm_context
    ):
        """Descripción textual se guarda y se muestran paquetes."""
        from handlers.store_admin_handlers import ProductWizardStates, process_product_description

        mock_store = MagicMock()
        mock_pkg = MagicMock()
        mock_pkg.id = 1
        mock_pkg.name = "Test Pkg"
        mock_pkg.file_count = 5
        mock_pkg.store_stock = -1
        mock_store.get_available_packages_for_store.return_value = [mock_pkg]
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

        msg = make_message(text="Un pack de fotos exclusivas")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_description)
        await process_product_description(msg, fsm)

        data = await fsm.get_data()
        assert data["description"] == "Un pack de fotos exclusivas"
        mock_store.get_available_packages_for_store.assert_called_once()
        mock_get_service.return_value.__exit__.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_no_packages_shows_error(self, mock_get_service, make_message, make_fsm_context):
        """Sin paquetes disponibles, muestra error y limpia estado."""
        mock_store = MagicMock()
        mock_store.get_available_packages_for_store.return_value = []
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

        msg = make_message(text="Descripción test")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_description)

        from handlers.store_admin_handlers import process_product_description

        await process_product_description(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "No hay paquetes" in text
        state = await fsm.get_state()
        assert state is None
        mock_get_service.return_value.__exit__.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_advances_to_selecting_package(
        self, mock_get_service, make_message, make_fsm_context
    ):
        """Con paquetes disponibles, avanza a selecting_package."""
        from handlers.store_admin_handlers import ProductWizardStates, process_product_description

        mock_store = MagicMock()
        mock_pkg = MagicMock()
        mock_pkg.id = 1
        mock_pkg.name = "Test Pkg"
        mock_pkg.file_count = 5
        mock_pkg.store_stock = -1
        mock_store.get_available_packages_for_store.return_value = [mock_pkg]
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

        msg = make_message(text="Descripción")
        fsm = await make_fsm_context()
        await fsm.set_state(ProductWizardStates.waiting_description)
        await process_product_description(msg, fsm)

        state = await fsm.get_state()
        assert state == ProductWizardStates.selecting_package
        mock_store.get_available_packages_for_store.assert_called_once()
        mock_get_service.return_value.__exit__.assert_called_once()


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
        assert "Resumen" in text
        assert "Ilimitado" in text
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
        assert "Resumen" in text


class TestConfirmCreateProduct:
    """Tests para confirm_create_product — creación final del producto."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_creates_product_successfully(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Crea el producto y muestra mensaje de éxito."""
        mock_product = MagicMock()
        mock_product.name = "Pack Fotos"
        mock_product.price = 150
        mock_store = MagicMock()
        mock_store.create_product.return_value = mock_product
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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

        mock_store.create_product.assert_called_once_with(
            name="Pack Fotos",
            description="Fotos exclusivas",
            package_id=1,
            price=150,
            stock=10,
            created_by=123456789,
        )
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
        mock_store = MagicMock()
        mock_store.create_product.side_effect = Exception("DB error")
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
        mock_product = MagicMock()
        mock_product.name = "Test"
        mock_product.price = 100
        mock_store = MagicMock()
        mock_store.create_product.return_value = mock_product
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
        mock_product = MagicMock()
        mock_product.name = "Test"
        mock_product.price = 100
        mock_store = MagicMock()
        mock_store.create_product.return_value = mock_product
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
    """Tests para list_products — listado de todos los productos."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_shows_empty_message_when_no_products(self, mock_get_service, make_callback):
        """Cuando no hay productos, muestra mensaje vacío."""
        mock_store = MagicMock()
        mock_store.get_all_products.return_value = []
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

        cb = make_callback(data="list_products")

        from handlers.store_admin_handlers import list_products

        await list_products(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay productos" in text
        cb.answer.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_lists_products_with_status(self, mock_get_service, make_callback):
        """Muestra productos con su estado y stock."""
        mock_prod_active = MagicMock()
        mock_prod_active.name = "Producto Activo"
        mock_prod_active.is_active = True
        mock_prod_active.stock = -1
        mock_prod_active.is_low_stock = False
        mock_prod_active.price = 100

        mock_prod_inactive = MagicMock()
        mock_prod_inactive.name = "Producto Inactivo"
        mock_prod_inactive.is_active = False
        mock_prod_inactive.stock = 0
        mock_prod_inactive.is_low_stock = False
        mock_prod_inactive.price = 50

        mock_store = MagicMock()
        mock_store.get_all_products.return_value = [mock_prod_active, mock_prod_inactive]
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

        cb = make_callback(data="list_products")

        from handlers.store_admin_handlers import list_products

        await list_products(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Producto Activo" in text
        assert "Producto Inactivo" in text
        assert "100" in text
        cb.answer.assert_called_once()

    @patch("handlers.store_admin_handlers.get_service")
    async def test_calls_get_all_products_with_active_only_false(
        self, mock_get_service, make_callback
    ):
        """Llama a get_all_products(active_only=False)."""
        mock_store = MagicMock()
        mock_store.get_all_products.return_value = []
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

        cb = make_callback(data="list_products")

        from handlers.store_admin_handlers import list_products

        await list_products(cb)

        mock_store.get_all_products.assert_called_once_with(active_only=False)


class TestToggleProduct:
    """Tests para toggle_product — activar/desactivar producto."""

    @patch("handlers.store_admin_handlers.get_service")
    async def test_toggles_active_product_to_inactive(self, mock_get_service, make_callback):
        """Producto activo se desactiva y muestra detalle."""
        mock_product = MagicMock()
        mock_product.is_active = True
        mock_product.id = 1
        mock_store = MagicMock()
        mock_store.get_product.return_value = mock_product
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
        mock_product = MagicMock()
        mock_product.is_active = False
        mock_product.id = 1
        mock_store = MagicMock()
        mock_store.get_product.return_value = mock_product
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
        mock_store = MagicMock()
        mock_store.get_product.return_value = None
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
        mock_product = MagicMock()
        mock_product.is_active = True
        mock_product.id = 1
        mock_store = MagicMock()
        mock_store.get_product.return_value = mock_product
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
        mock_store = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
        mock_store = MagicMock()
        mock_store.delete_product.return_value = True
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
        mock_store = MagicMock()
        mock_store.delete_product.return_value = False
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
        mock_store = MagicMock()
        mock_store.delete_product.return_value = True
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
        mock_store = MagicMock()
        mock_store.get_store_stats.return_value = {
            "available_products": 8,
            "total_products": 15,
            "completed_orders": 25,
            "total_orders": 30,
            "total_besitos_spent": 2500,
        }
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
        mock_store = MagicMock()
        mock_store.get_store_stats.return_value = {
            "available_products": 0,
            "total_products": 0,
            "completed_orders": 0,
            "total_orders": 0,
            "total_besitos_spent": 0,
        }
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_store
        mock_get_service.return_value = mock_context

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
        assert len(kb.inline_keyboard) == 5
        assert "Desactivar" in kb.inline_keyboard[0][0].text
        assert "42" in kb.inline_keyboard[0][0].callback_data  # packed contains id
        assert "Reabastecer" in kb.inline_keyboard[1][0].text
        assert "list_products" in kb.inline_keyboard[4][0].callback_data

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

        mock_product = MagicMock()
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


# Necesario para evitar NameError en la referencia de clase inline de los handlers
from handlers.store_admin_handlers import ProductWizardStates
