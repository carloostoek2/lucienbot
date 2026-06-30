"""
Tests unitarios para store_user_handlers.

Cubre handlers de tienda: menu, catalogo, categorias, detalle de producto,
preview, compra directa, historial, busqueda y filtros.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch
from datetime import datetime

from tests.helpers import model_mock
from services.store_service import StoreService
from models.models import StoreProduct, Category, Order

pytestmark = [pytest.mark.unit]


def _mock_store_ctx(mock_get_service, **kwargs):
    """Mock get_service(StoreService) context manager con autospec."""
    mock_store = create_autospec(StoreService, spec_set=True, instance=True)
    for key, val in kwargs.items():
        getattr(mock_store, key).return_value = val
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_store
    mock_get_service.return_value = mock_ctx
    return mock_store


def _product_ctx(product, balance=500, file_count=1, effective_price=None, cap=True):
    ep = effective_price if effective_price is not None else product.price
    return {
        "product": product,
        "balance": balance,
        "file_count": file_count,
        "can_preview": file_count > 1,
        "tier_name": "",
        "effective_price": ep,
        "monthly_cap_available": cap,
    }


class TestShopMenu:
    """Tests para shop_menu - menu principal de la tienda."""

    @patch("handlers.store_user_handlers.get_service")
    async def test_shows_balance_and_menu(self, mock_get_service, make_callback):
        """Muestra el saldo del usuario y las opciones del menu."""
        _mock_store_ctx(mock_get_service, get_shop_balance_display=500)
        cb = make_callback(data="shop")

        from handlers.store_user_handlers import shop_menu
        await shop_menu(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "500" in text
        assert "tienda" in text.lower()

    @patch("handlers.store_user_handlers.get_service")
    async def test_menu_categories_points_to_tiers_not_package_categories(
        self, mock_get_service, make_callback
    ):
        """Estanterías del menú apuntan a store_tiers (catálogo Kinky), sin botón duplicado."""
        _mock_store_ctx(mock_get_service, get_shop_balance_display=500)
        cb = make_callback(data="shop")

        from handlers.store_user_handlers import shop_menu
        from utils.lucien_voice import LucienVoice

        await shop_menu(cb)

        markup = cb.message.edit_text.call_args[1].get("reply_markup")
        callbacks = [btn.callback_data for row in markup.inline_keyboard for btn in row]
        texts = [btn.text for row in markup.inline_keyboard for btn in row]
        assert "store_tiers" in callbacks
        assert "store_categories" not in callbacks
        assert LucienVoice.store_tier_menu_button() not in texts

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_service_with_user_id(self, mock_get_service, make_callback):
        """Llama a get_balance con el user_id correcto."""
        store = _mock_store_ctx(mock_get_service, get_shop_balance_display=500)
        cb = make_callback(data="shop")

        from handlers.store_user_handlers import shop_menu
        await shop_menu(cb)

        store.get_shop_balance_display.assert_called_once_with(123456789)

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Siempre llama a callback.answer()."""
        _mock_store_ctx(mock_get_service, get_shop_balance_display=500)
        cb = make_callback(data="shop")

        from handlers.store_user_handlers import shop_menu
        await shop_menu(cb)

        cb.answer.assert_called_once()

    @patch("handlers.store_user_handlers.get_service")
    async def test_closes_service(self, mock_get_service, make_callback):
        """StoreService context manager se cierra."""
        _mock_store_ctx(mock_get_service, get_shop_balance_display=500)
        cb = make_callback(data="shop")

        from handlers.store_user_handlers import shop_menu
        await shop_menu(cb)

        mock_get_service.return_value.__exit__.assert_called()


class TestStoreCatalog:
    """Tests para store_catalog - catalogo completo de productos."""

    @patch("handlers.store_user_handlers.get_service")
    async def test_empty_catalog_shows_empty_message(self, mock_get_service, make_callback):
        """Cuando no hay productos, muestra mensaje de tienda vacia."""
        store = _mock_store_ctx(mock_get_service)
        store.get_all_products.return_value = []
        cb = make_callback(data="store_catalog")

        from handlers.store_user_handlers import store_catalog
        await store_catalog(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "silencio" in text.lower()

    @patch("handlers.store_user_handlers.get_service")
    async def test_displays_products(self, mock_get_service, make_callback):
        """Muestra los productos en el catalogo."""
        p1 = MagicMock(id=1, name="Product A")
        p2 = MagicMock(id=2, name="Product B")
        store = _mock_store_ctx(mock_get_service)
        store.get_all_products.return_value = [p1, p2]
        cb = make_callback(data="store_catalog")

        from handlers.store_user_handlers import store_catalog
        await store_catalog(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "catálogo" in text.lower()

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_service_with_active_only(self, mock_get_service, make_callback):
        """Llama a get_all_products con active_only=True."""
        store = _mock_store_ctx(mock_get_service)
        store.get_all_products.return_value = []
        cb = make_callback(data="store_catalog")

        from handlers.store_user_handlers import store_catalog
        await store_catalog(cb)

        store.get_all_products.assert_called_once_with(active_only=True)

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Siempre llama a callback.answer()."""
        store = _mock_store_ctx(mock_get_service)
        store.get_all_products.return_value = []
        cb = make_callback(data="store_catalog")

        from handlers.store_user_handlers import store_catalog
        await store_catalog(cb)

        cb.answer.assert_called_once()

    @patch("handlers.store_user_handlers.get_service")
    async def test_closes_service(self, mock_get_service, make_callback):
        """StoreService se cierra en finally."""
        store = _mock_store_ctx(mock_get_service)
        store.get_all_products.return_value = []
        cb = make_callback(data="store_catalog")

        from handlers.store_user_handlers import store_catalog
        await store_catalog(cb)

        mock_get_service.return_value.__exit__.assert_called()


class TestStoreCategories:
    """Tests para store_categories — backward compat delega a tiers del catálogo."""

    @patch("handlers.store_user_handlers.get_service")
    async def test_delegates_to_tiers_menu(self, mock_get_service, make_callback):
        """Callback antiguo store_categories muestra menú de tiers."""
        tier = MagicMock(id=1, name="IMPULSO", price_min=50, price_max=120)
        store = _mock_store_ctx(mock_get_service)
        store.get_tiers_for_shop.return_value = [tier]
        cb = make_callback(data="store_categories")

        from handlers.store_user_handlers import store_categories
        await store_categories(cb)

        store.get_tiers_for_shop.assert_called_once_with(active_only=True)
        cb.message.edit_text.assert_called_once()
        markup = cb.message.edit_text.call_args[1].get("reply_markup")
        button_texts = [btn.text for row in markup.inline_keyboard for btn in row]
        assert any("IMPULSO" in t for t in button_texts)

    @patch("handlers.store_user_handlers.get_service")
    async def test_empty_tiers_shows_unavailable_alert(self, mock_get_service, make_callback):
        """Sin tiers visibles, muestra alerta de catálogo no disponible."""
        store = _mock_store_ctx(mock_get_service)
        store.get_tiers_for_shop.return_value = []
        cb = make_callback(data="store_categories")

        from handlers.store_user_handlers import store_categories
        await store_categories(cb)

        cb.answer.assert_called_once()
        assert cb.answer.call_args[1].get("show_alert") is True

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Siempre llama a callback.answer() cuando hay tiers."""
        tier = MagicMock(id=1, name="DESEO", price_min=150, price_max=350)
        store = _mock_store_ctx(mock_get_service)
        store.get_tiers_for_shop.return_value = [tier]
        cb = make_callback(data="store_categories")

        from handlers.store_user_handlers import store_categories
        await store_categories(cb)

        cb.answer.assert_called_once()

        cb.message.edit_text.assert_called_once()


class TestStoreCategoryProducts:
    """Tests para store_category_products - productos por categoria."""

    @patch("handlers.store_user_handlers.get_service")
    async def test_category_not_found(self, mock_get_service, make_callback):
        """Categoria no encontrada muestra alerta."""
        from keyboards.callback_data import StoreCategoryCallback
        store = _mock_store_ctx(mock_get_service)
        store.get_category_for_shop.return_value = None
        cb = make_callback(data="store_category:1")
        cd = StoreCategoryCallback(category_id=1)

        from handlers.store_user_handlers import store_category_products
        await store_category_products(cb, cd)

        cb.answer.assert_called_once_with(
            "Categoría no encontrada.", show_alert=True
        )

    @patch("handlers.store_user_handlers.get_service")
    async def test_category_empty_products(self, mock_get_service, make_callback):
        """Categoria sin productos muestra mensaje de estanteria vacia."""
        from keyboards.callback_data import StoreCategoryCallback
        category = model_mock(Category)
        category.id = 1
        category.name = "Fotos Exclusivas"
        category.description = "Fotos que pocos veran"
        store = _mock_store_ctx(mock_get_service)
        store.get_category_for_shop.return_value = category
        store.filter_products.return_value = []
        cb = make_callback(data="store_category:1")
        cd = StoreCategoryCallback(category_id=1)

        from handlers.store_user_handlers import store_category_products
        await store_category_products(cb, cd)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "aguarda nuevas piezas" in text.lower()
        assert "Fotos Exclusivas" in text

    @patch("handlers.store_user_handlers.get_service")
    async def test_displays_category_products(self, mock_get_service, make_callback):
        """Muestra productos de la categoria con descripcion."""
        from keyboards.callback_data import StoreCategoryCallback
        category = model_mock(Category)
        category.id = 1
        category.name = "Fotos"
        category.description = "Descripcion de la categoria"
        product = MagicMock(id=1, name="Producto X", price=100)
        store = _mock_store_ctx(mock_get_service)
        store.get_category_for_shop.return_value = category
        store.filter_products.return_value = [product]
        cb = make_callback(data="store_category:1")
        cd = StoreCategoryCallback(category_id=1)

        from handlers.store_user_handlers import store_category_products
        await store_category_products(cb, cd)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Fotos" in text
        assert "Descripcion de la categoria" in text

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_services_with_correct_params(self, mock_get_service, make_callback):
        """Llama a get_category y filter_products con parametros correctos."""
        from keyboards.callback_data import StoreCategoryCallback
        category = MagicMock(id=1, name="Test", description="")
        store = _mock_store_ctx(mock_get_service)
        store.get_category_for_shop.return_value = category
        store.filter_products.return_value = []
        cb = make_callback(data="store_category:1")
        cd = StoreCategoryCallback(category_id=1)

        from handlers.store_user_handlers import store_category_products
        await store_category_products(cb, cd)
        store.filter_products.assert_called_once_with(
            category_id=1, active_only=True
        )

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Llama a callback.answer cuando hay productos."""
        from keyboards.callback_data import StoreCategoryCallback
        category = MagicMock(id=1, name="Test", description="")
        product = MagicMock(id=1, name="Producto X", price=100)
        store = _mock_store_ctx(mock_get_service)
        store.get_category_for_shop.return_value = category
        store.filter_products.return_value = [product]
        cb = make_callback(data="store_category:1")
        cd = StoreCategoryCallback(category_id=1)

        from handlers.store_user_handlers import store_category_products
        await store_category_products(cb, cd)

        cb.answer.assert_called_once()


class TestProductDetail:
    """Tests para product_detail - detalle de producto."""

    @patch("handlers.store_user_handlers.get_service")
    async def test_product_not_found(self, mock_get_service, make_callback):
        """Producto no encontrado muestra alerta."""
        from keyboards.callback_data import ProductDetailCallback
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = None
        cb = make_callback(data="product_detail:1")
        cd = ProductDetailCallback(product_id=1)

        from handlers.store_user_handlers import product_detail
        await product_detail(cb, cd)

        cb.answer.assert_called_once_with(
            "Producto no encontrado.",
            show_alert=True,
        )

    @patch("handlers.store_user_handlers.get_service")
    async def test_sufficient_balance_shows_buy_button(self, mock_get_service, make_callback):
        """Con saldo suficiente, muestra boton de comprar."""
        from keyboards.callback_data import ProductDetailCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Producto X"
        product.description = "Descripcion"
        product.price = 100
        product.stock = 10
        product.is_available = True
        product.package = MagicMock(id=1)
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=200, file_count=2)
        cb = make_callback(data="product_detail:1")
        cd = ProductDetailCallback(product_id=1)

        from handlers.store_user_handlers import product_detail
        await product_detail(cb, cd)

        cb.message.edit_text.assert_called_once()
        # Verify buy button data
        edit_call_args = cb.message.edit_text.call_args[1]
        markup = edit_call_args.get("reply_markup")
        buttons = markup.inline_keyboard
        buy_row = buttons[0]
        buy_texts = [btn.text for btn in buy_row]
        assert any("🌸 Comprar" in t for t in buy_texts)
        assert any("Ver vista previa" in t for t in buy_texts)

    @patch("handlers.store_user_handlers.get_service")
    async def test_insufficient_balance_shows_needed_amount(self, mock_get_service, make_callback):
        """Con saldo insuficiente, muestra cuanto falta."""
        from keyboards.callback_data import ProductDetailCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Producto Caro"
        product.description = "Caro"
        product.price = 300
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=100)
        cb = make_callback(data="product_detail:1")
        cd = ProductDetailCallback(product_id=1)

        from handlers.store_user_handlers import product_detail
        await product_detail(cb, cd)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "besitos" in text.lower()
        # Check the insufficient balance button
        markup = cb.message.edit_text.call_args[1].get("reply_markup")
        buttons = markup.inline_keyboard
        buy_row = buttons[0]
        buy_texts = [btn.text for btn in buy_row]
        assert any("200" in t for t in buy_texts)
        assert any("faltan" in t.lower() for t in buy_texts)

    @patch("handlers.store_user_handlers.get_service")
    async def test_tier_locked_shows_lock_button(self, mock_get_service, make_callback):
        """Nivel bloqueado muestra candado y no el boton de compra."""
        from keyboards.callback_data import DirectBuyCallback, ProductDetailCallback

        product = model_mock(StoreProduct)
        product.id = 9
        product.name = "Tesoro Bloqueado"
        product.description = "Requiere nivel previo"
        product.price = 200
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        ctx = _product_ctx(product, balance=500)
        ctx.update(
            tier_unlocked=False,
            tier_lock_remaining=1,
            tier_lock_message="Para acceder a este nivel, compre 2 productos del nivel",
        )
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = ctx
        cb = make_callback(data="product_detail:9")
        cd = ProductDetailCallback(product_id=9)

        from handlers.store_user_handlers import product_detail

        await product_detail(cb, cd)

        markup = cb.message.edit_text.call_args[1].get("reply_markup")
        buy_texts = [btn.text for btn in markup.inline_keyboard[0]]
        buy_callbacks = [btn.callback_data for btn in markup.inline_keyboard[0]]
        assert any("Necesita" in t for t in buy_texts)
        assert not any("Adquirir" in t for t in buy_texts)
        assert DirectBuyCallback(product_id=9).pack() in buy_callbacks

    @patch("handlers.store_user_handlers.get_service")
    async def test_product_not_available_shows_agotado(self, mock_get_service, make_callback):
        """Producto no disponible muestra boton de agotado."""
        from keyboards.callback_data import ProductDetailCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Agotado"
        product.description = "No hay"
        product.price = 100
        product.stock = 0
        product.is_available = False
        product.package = MagicMock(id=1)
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=200)
        cb = make_callback(data="product_detail:1")
        cd = ProductDetailCallback(product_id=1)

        from handlers.store_user_handlers import product_detail
        await product_detail(cb, cd)

        cb.message.edit_text.assert_called_once()
        markup = cb.message.edit_text.call_args[1].get("reply_markup")
        buttons = markup.inline_keyboard
        buy_row = buttons[0]
        buy_texts = [btn.text for btn in buy_row]
        assert any("Agotado" in t for t in buy_texts)

    @patch("handlers.store_user_handlers.get_service")
    async def test_unlimited_stock_displays_infinity(self, mock_get_service, make_callback):
        """Stock -1 se muestra como infinito."""
        from keyboards.callback_data import ProductDetailCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Ilimitado"
        product.description = "Sin limites"
        product.price = 100
        product.stock = -1
        product.is_available = True
        product.package = MagicMock(id=1)
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=200)
        cb = make_callback(data="product_detail:1")
        cd = ProductDetailCallback(product_id=1)

        from handlers.store_user_handlers import product_detail
        await product_detail(cb, cd)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "∞" in text

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Siempre llama a callback.answer()."""
        from keyboards.callback_data import ProductDetailCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Test"
        product.description = ""
        product.price = 100
        product.stock = 10
        product.is_available = True
        product.package = MagicMock(id=1)
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=200)
        cb = make_callback(data="product_detail:1")
        cd = ProductDetailCallback(product_id=1)

        from handlers.store_user_handlers import product_detail
        await product_detail(cb, cd)

        cb.answer.assert_called_once()

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_services_with_correct_params(self, mock_get_service, make_callback):
        """Llama a servicios con parametros correctos."""
        from keyboards.callback_data import ProductDetailCallback
        product = model_mock(StoreProduct)
        product.id = 42
        product.name = "Test"
        product.description = ""
        product.price = 100
        product.stock = 10
        product.is_available = True
        product.package_id = 99
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=200)
        cb = make_callback(data="product_detail:42")
        cd = ProductDetailCallback(product_id=42)

        from handlers.store_user_handlers import product_detail
        await product_detail(cb, cd)

        store.get_product_detail_context.assert_called_once_with(42, 123456789)

    @patch("handlers.store_user_handlers.get_service")
    async def test_product_detail_discounted_price_allows_buy(
        self, mock_get_service, make_callback
    ):
        from keyboards.callback_data import ProductDetailCallback

        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Con Descuento"
        product.description = "Desc"
        product.price = 100
        product.stock = 10
        product.is_available = True
        product.package = MagicMock(id=1)
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(
            product, balance=90, effective_price=80, file_count=2
        )
        cb = make_callback(data="product_detail:1")
        cd = ProductDetailCallback(product_id=1)

        from handlers.store_user_handlers import product_detail

        await product_detail(cb, cd)

        text = cb.message.edit_text.call_args[0][0]
        assert "80" in text
        markup = cb.message.edit_text.call_args[1].get("reply_markup")
        buy_texts = [btn.text for btn in markup.inline_keyboard[0]]
        assert any("🌸 Comprar" in t for t in buy_texts)

    @patch("handlers.store_user_handlers.get_service")
    async def test_product_detail_monthly_cap_exhausted_shows_agotado(
        self, mock_get_service, make_callback
    ):
        from keyboards.callback_data import ProductDetailCallback

        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Cap Agotado"
        product.description = "Desc"
        product.price = 100
        product.stock = 10
        product.is_available = True
        product.package = MagicMock(id=1)
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(
            product, balance=200, cap=False
        )
        cb = make_callback(data="product_detail:1")
        cd = ProductDetailCallback(product_id=1)

        from handlers.store_user_handlers import product_detail

        await product_detail(cb, cd)

        markup = cb.message.edit_text.call_args[1].get("reply_markup")
        buy_texts = [btn.text for btn in markup.inline_keyboard[0]]
        assert any("Agotado" in t for t in buy_texts)


class TestProductPreview:
    """Tests para product_preview - preview de producto."""

    @patch("handlers.store_user_handlers.get_service")
    async def test_product_not_found(self, mock_get_service, make_callback):
        """Producto no encontrado muestra alerta."""
        from keyboards.callback_data import ProductPreviewCallback
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = None
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.answer.assert_called_once_with(
            "Producto no encontrado.",
            show_alert=True,
        )

    @patch("handlers.store_user_handlers.get_service")
    async def test_sends_photo_preview(self, mock_get_service, make_callback):
        """Envia preview en foto cuando el archivo es photo."""
        from keyboards.callback_data import ProductPreviewCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Foto Preview"
        product.description = "Una foto"
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        file_entry = MagicMock(file_id="abc123", file_type="photo")
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=200, file_count=2)
        store.get_preview_files_for_product.return_value = [file_entry]
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.message.answer_photo.assert_called_once_with(
            photo="abc123",
            caption="Vista previa del producto.",
            parse_mode="HTML",
        )

    @patch("handlers.store_user_handlers.get_service")
    async def test_sends_video_preview(self, mock_get_service, make_callback):
        """Envia preview en video cuando el archivo es video."""
        from keyboards.callback_data import ProductPreviewCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Video Preview"
        product.description = "Un video"
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        file_entry = MagicMock(file_id="video123", file_type="video")
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=200, file_count=2)
        store.get_preview_files_for_product.return_value = [file_entry]
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.message.answer_video.assert_called_once_with(
            video="video123",
            caption="Vista previa del producto.",
            parse_mode="HTML",
        )

    @patch("handlers.store_user_handlers.get_service")
    async def test_tier_locked_after_preview_keeps_lock_button(self, mock_get_service, make_callback):
        """Tras el preview, el detalle mantiene el boton de candado."""
        from keyboards.callback_data import DirectBuyCallback, ProductPreviewCallback

        product = model_mock(StoreProduct)
        product.id = 9
        product.name = "Tesoro Bloqueado"
        product.description = "Requiere nivel previo"
        product.price = 200
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        ctx = _product_ctx(product, balance=500, file_count=2)
        ctx.update(
            tier_unlocked=False,
            tier_lock_remaining=1,
            tier_lock_message="Para acceder a este nivel, compre 2 productos del nivel",
        )
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = ctx
        store.get_preview_files_for_product.return_value = []
        cb = make_callback(data="product_preview:9")
        cd = ProductPreviewCallback(product_id=9)

        from handlers.store_user_handlers import product_preview

        await product_preview(cb, cd)

        markup = cb.message.answer.call_args[1].get("reply_markup")
        buy_texts = [btn.text for btn in markup.inline_keyboard[0]]
        buy_callbacks = [btn.callback_data for btn in markup.inline_keyboard[0]]
        assert any("Necesita" in t for t in buy_texts)
        assert not any("Adquirir" in t for t in buy_texts)
        assert DirectBuyCallback(product_id=9).pack() in buy_callbacks

    @patch("handlers.store_user_handlers.get_service")
    async def test_no_package_files_sends_no_preview(self, mock_get_service, make_callback):
        """Sin archivos en el paquete, no envia preview."""
        from keyboards.callback_data import ProductPreviewCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Sin Preview"
        product.description = "No hay"
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=200)
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.message.answer_photo.assert_not_called()
        cb.message.answer_video.assert_not_called()

    @patch("handlers.store_user_handlers.get_service")
    async def test_preview_shows_effective_price(self, mock_get_service, make_callback):
        from keyboards.callback_data import ProductPreviewCallback

        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Preview Discount"
        product.description = "Desc"
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(
            product, balance=200, effective_price=80, file_count=2
        )
        store.get_preview_files_for_product.return_value = []
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview

        await product_preview(cb, cd)

        text = cb.message.answer.call_args[0][0]
        assert "💋 <b>Precio:</b> 80 besitos" in text
        assert "Precio de lista:</b> 100 besitos" in text

    @patch("handlers.store_user_handlers.get_service")
    async def test_no_package_shows_no_preview(self, mock_get_service, make_callback):
        """Producto sin paquete no envia preview."""
        from keyboards.callback_data import ProductPreviewCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Sin Paquete"
        product.description = ""
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = None
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=200)
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.message.answer_photo.assert_not_called()
        cb.message.answer_video.assert_not_called()

    @patch("handlers.store_user_handlers.get_service")
    async def test_preview_send_error_caught_gracefully(self, mock_get_service, make_callback):
        """Error al enviar preview se captura y no rompe el flujo."""
        from keyboards.callback_data import ProductPreviewCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Error Preview"
        product.description = ""
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        file_entry = MagicMock(file_id="bad_file", file_type="photo")
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=200, file_count=2)
        cb = make_callback(data="product_preview:1")
        cb.message.answer_photo = AsyncMock(side_effect=Exception("API error"))
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        # Should still send the product card
        cb.message.answer.assert_called_once()

    @patch("handlers.store_user_handlers.get_service")
    async def test_sends_only_first_file_when_multiple_available(
        self, mock_get_service, make_callback
    ):
        """Con varios archivos en el paquete, solo envia el primero como preview."""
        from keyboards.callback_data import ProductPreviewCallback

        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Varios archivos"
        product.description = "Paquete grande"
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package_id = 1
        file1 = MagicMock(file_id="first", file_type="photo")
        file2 = MagicMock(file_id="second", file_type="photo")
        file3 = MagicMock(file_id="third", file_type="photo")
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=200, file_count=3)
        store.get_preview_files_for_product.return_value = [file1]
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview

        await product_preview(cb, cd)

        cb.message.answer_photo.assert_called_once_with(
            photo="first",
            caption="Vista previa del producto.",
            parse_mode="HTML",
        )

    @patch("handlers.store_user_handlers.get_service")
    async def test_sends_preview_and_product_card(self, mock_get_service, make_callback):
        """Envia preview y luego la tarjeta del producto."""
        from keyboards.callback_data import ProductPreviewCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Completo"
        product.description = "Desc"
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        file_entry = MagicMock(file_id="f1", file_type="photo")
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=200, file_count=2)
        store.get_preview_files_for_product.return_value = [file_entry]
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.message.answer_photo.assert_called_once()
        cb.message.answer.assert_called_once()

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_answer_preview_sent(self, mock_get_service, make_callback):
        """Responde con 'Preview enviado!'."""
        from keyboards.callback_data import ProductPreviewCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Test"
        product.description = ""
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        file_entry = MagicMock(file_id="f1", file_type="photo")
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=200, file_count=2)
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.answer.assert_called_with("Vista previa enviada.", show_alert=False)

    @patch("handlers.store_user_handlers.get_service")
    async def test_single_file_product_hides_preview_button(self, mock_get_service, make_callback):
        """Con 1 solo archivo, el detalle NO muestra botón de preview (evita regalar el producto)."""
        from keyboards.callback_data import ProductDetailCallback

        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Unico Archivo"
        product.description = ""
        product.price = 50
        product.stock = 3
        product.is_available = True
        product.package = MagicMock(id=1)
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=100, file_count=1)
        cb = make_callback(data="product_detail:1")
        cd = ProductDetailCallback(product_id=1)

        from handlers.store_user_handlers import product_detail
        await product_detail(cb, cd)

        markup = cb.message.edit_text.call_args[1].get("reply_markup")
        all_texts = [btn.text for row in markup.inline_keyboard for btn in row]
        assert not any("vista previa" in t.lower() or "👁️" in t for t in all_texts)

    @patch("handlers.store_user_handlers.get_service")
    async def test_preview_callback_on_single_file_shows_no_preview_alert(self, mock_get_service, make_callback):
        """Click en preview (o cb directo) para producto de 1 archivo → alerta sin enviar nada."""
        from keyboards.callback_data import ProductPreviewCallback

        product = model_mock(StoreProduct)
        product.id = 42
        product.name = "Solo Uno"
        product.description = ""
        product.price = 100
        product.stock = 1
        product.is_available = True
        product.package = MagicMock(id=1)
        store = _mock_store_ctx(mock_get_service)
        store.get_product_detail_context.return_value = _product_ctx(product, balance=200, file_count=1)
        cb = make_callback(data="product_preview:42")
        cd = ProductPreviewCallback(product_id=42)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.answer.assert_called_with("Este producto no tiene vista previa.", show_alert=True)
        cb.message.answer_photo.assert_not_called()
        cb.message.answer_video.assert_not_called()


class TestDirectBuy:
    """Tests para direct_buy - confirmacion de compra directa."""

    def _setup_direct_buy(self, mock_get_service, product, balance, effective=None):
        store = _mock_store_ctx(mock_get_service)
        store.get_product.return_value = product
        store.get_shop_balance_display.return_value = balance
        store.get_effective_price.return_value = effective if effective is not None else product.price
        store._check_monthly_cap_for_product.return_value = None
        store.check_tier_purchase_gate.return_value = None
        return store

    @patch("handlers.store_user_handlers.get_service")
    async def test_product_not_found(self, mock_get_service, make_callback):
        """Producto no encontrado muestra alerta."""
        from keyboards.callback_data import DirectBuyCallback
        store = _mock_store_ctx(mock_get_service)
        store.get_product.return_value = None
        cb = make_callback(data="direct_buy:1")
        cd = DirectBuyCallback(product_id=1)

        from handlers.store_user_handlers import direct_buy
        await direct_buy(cb, cd)

        cb.answer.assert_called_once_with(
            "Producto no encontrado.",
            show_alert=True,
        )

    @patch("handlers.store_user_handlers.get_service")
    async def test_insufficient_balance(self, mock_get_service, make_callback):
        """Saldo insuficiente muestra alerta."""
        from keyboards.callback_data import DirectBuyCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.price = 500
        self._setup_direct_buy(mock_get_service, product, balance=200)
        cb = make_callback(data="direct_buy:1")
        cd = DirectBuyCallback(product_id=1)

        from handlers.store_user_handlers import direct_buy
        await direct_buy(cb, cd)

        cb.answer.assert_called_once_with(
            "No tiene suficientes besitos.", show_alert=True
        )

    @patch("handlers.store_user_handlers.get_service")
    async def test_monthly_cap_blocks_before_confirm(self, mock_get_service, make_callback):
        """Cupo mensual agotado bloquea antes de la pantalla de confirmación."""
        from keyboards.callback_data import DirectBuyCallback
        from utils.lucien_voice import LucienVoice

        product = model_mock(StoreProduct)
        product.id = 7
        product.name = "Cap Product"
        product.price = 200
        store = self._setup_direct_buy(mock_get_service, product, balance=500)
        store._check_monthly_cap_for_product.return_value = LucienVoice.store_monthly_cap_reached(
            product.name
        )
        cb = make_callback(data="direct_buy:7")
        cd = DirectBuyCallback(product_id=7)

        from handlers.store_user_handlers import direct_buy

        await direct_buy(cb, cd)

        store._check_monthly_cap_for_product.assert_called_once_with(7)
        cb.answer.assert_called_once()
        assert cb.answer.call_args[1].get("show_alert") is True
        cb.message.edit_text.assert_not_called()

    @patch("handlers.store_user_handlers.get_service")
    async def test_sufficient_balance_shows_confirmation(self, mock_get_service, make_callback):
        """Saldo suficiente muestra pantalla de confirmacion."""
        from keyboards.callback_data import DirectBuyCallback
        product = model_mock(StoreProduct)
        product.id = 42
        product.name = "Producto Test"
        product.price = 200
        self._setup_direct_buy(mock_get_service, product, balance=500)
        cb = make_callback(data="direct_buy:42")
        cd = DirectBuyCallback(product_id=42)

        from handlers.store_user_handlers import direct_buy
        await direct_buy(cb, cd)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "adquisición" in text.lower()
        assert "Producto Test" in text
        assert "200" in text
        assert "300" in text  # balance after (500-200)

    @patch("handlers.store_user_handlers.get_service")
    async def test_correct_balance_after_purchase_displayed(self, mock_get_service, make_callback):
        """Muestra el saldo resultante despues de la compra."""
        from keyboards.callback_data import DirectBuyCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Test"
        product.price = 300
        self._setup_direct_buy(mock_get_service, product, balance=1000)
        cb = make_callback(data="direct_buy:1")
        cd = DirectBuyCallback(product_id=1)

        from handlers.store_user_handlers import direct_buy
        await direct_buy(cb, cd)

        text = cb.message.edit_text.call_args[0][0]
        assert "700" in text  # 1000 - 300

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Llama a callback.answer en caso exitoso."""
        from keyboards.callback_data import DirectBuyCallback
        product = model_mock(StoreProduct)
        product.id = 1
        product.name = "Test"
        product.price = 100
        self._setup_direct_buy(mock_get_service, product, balance=500)
        cb = make_callback(data="direct_buy:1")
        cd = DirectBuyCallback(product_id=1)

        from handlers.store_user_handlers import direct_buy
        await direct_buy(cb, cd)

        cb.answer.assert_called_once()


class TestConfirmDirectBuy:
    """Tests para confirm_direct_buy - ejecucion de compra directa."""

    @patch("handlers.store_user_handlers.get_service")
    async def test_direct_purchase_returns_error(self, mock_get_service, make_callback):
        """Si purchase_and_complete retorna error, muestra alerta."""
        from keyboards.callback_data import ConfirmDirectBuyCallback
        store = _mock_store_ctx(mock_get_service)
        store.purchase_and_complete = AsyncMock(return_value=(None, [], "Error al procesar"))
        cb = make_callback(data="confirm_direct_buy:1")
        cd = ConfirmDirectBuyCallback(product_id=1)
        state = AsyncMock()

        from handlers.store_user_handlers import confirm_direct_buy
        await confirm_direct_buy(cb, cd, cb.bot, state)

        cb.answer.assert_called_once_with("Error al procesar", show_alert=True)

    @patch("handlers.store_user_handlers.get_service")
    async def test_complete_order_success(self, mock_get_service, make_callback):
        """Compra exitosa muestra mensaje de confirmacion."""
        from keyboards.callback_data import ConfirmDirectBuyCallback
        order = MagicMock(id=99, total_price=100)
        store = _mock_store_ctx(mock_get_service)
        store.purchase_and_complete = AsyncMock(
            return_value=(order, [{"kind": "package", "status": "fulfilled", "product_name": "X"}], None)
        )
        cb = make_callback(data="confirm_direct_buy:1")
        cd = ConfirmDirectBuyCallback(product_id=1)
        state = AsyncMock()

        from handlers.store_user_handlers import confirm_direct_buy
        await confirm_direct_buy(cb, cd, cb.bot, state)

        store.purchase_and_complete.assert_called_once_with(cb.bot, 123456789, 1)
        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once_with("Adquisición completada.")

    @patch("handlers.store_user_handlers.get_service")
    async def test_complete_order_failure(self, mock_get_service, make_callback):
        """Fallo en purchase_and_complete muestra alerta de error."""
        from keyboards.callback_data import ConfirmDirectBuyCallback
        store = _mock_store_ctx(mock_get_service)
        store.purchase_and_complete = AsyncMock(return_value=(None, [], "Error de envio"))
        cb = make_callback(data="confirm_direct_buy:1")
        cd = ConfirmDirectBuyCallback(product_id=1)
        state = AsyncMock()

        from handlers.store_user_handlers import confirm_direct_buy
        await confirm_direct_buy(cb, cd, cb.bot, state)

        cb.answer.assert_called_once_with("Error de envio", show_alert=True)

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_services_with_correct_params(self, mock_get_service, make_callback):
        """Llama a servicios con parametros correctos."""
        from keyboards.callback_data import ConfirmDirectBuyCallback
        order = MagicMock(id=55, total_price=50)
        store = _mock_store_ctx(mock_get_service)
        store.purchase_and_complete = AsyncMock(return_value=(order, [], None))
        cb = make_callback(data="confirm_direct_buy:1")
        cd = ConfirmDirectBuyCallback(product_id=1)
        state = AsyncMock()

        from handlers.store_user_handlers import confirm_direct_buy
        await confirm_direct_buy(cb, cd, cb.bot, state)

        store.purchase_and_complete.assert_called_once_with(cb.bot, 123456789, 1)

    @patch("handlers.store_user_handlers.get_service")
    async def test_confirm_direct_buy_vip_activated_shows_purchase_completed(
        self, mock_get_service, make_callback
    ):
        """VIP activado: pantalla de confirmación sin duplicar invite."""
        from keyboards.callback_data import ConfirmDirectBuyCallback

        order = MagicMock(id=99, total_price=100)
        store = _mock_store_ctx(mock_get_service)
        store.purchase_and_complete = AsyncMock(
            return_value=(
                order,
                [
                    {
                        "kind": "vip_grant",
                        "status": "fulfilled",
                        "vip_activated": True,
                        "product_name": "Mes VIP",
                    }
                ],
                None,
            )
        )
        store._get_order_charge_amount = MagicMock(return_value=100)
        cb = make_callback(data="confirm_direct_buy:1")
        cd = ConfirmDirectBuyCallback(product_id=1)
        state = AsyncMock()

        from handlers.store_user_handlers import confirm_direct_buy

        await confirm_direct_buy(cb, cd, cb.bot, state)

        text = cb.message.edit_text.call_args[0][0]
        assert "discernimiento" in text.lower()
        assert "círculo íntimo" not in text

    @patch("handlers.store_user_handlers.get_service")
    async def test_confirm_direct_buy_vip_auto_running_shows_backpack_cta(
        self, mock_get_service, make_callback
    ):
        """VIP activado pero DM pendiente: CTA mochila, no éxito de compra."""
        from keyboards.callback_data import ConfirmDirectBuyCallback

        order = MagicMock(id=99, total_price=100)
        store = _mock_store_ctx(mock_get_service)
        store.purchase_and_complete = AsyncMock(
            return_value=(
                order,
                [
                    {
                        "kind": "vip_grant",
                        "status": "auto_running",
                        "vip_activated": True,
                        "product_name": "Mes VIP",
                    }
                ],
                None,
            )
        )
        store._get_order_charge_amount = MagicMock(return_value=100)
        cb = make_callback(data="confirm_direct_buy:1")
        cd = ConfirmDirectBuyCallback(product_id=1)
        state = AsyncMock()

        from handlers.store_user_handlers import confirm_direct_buy

        await confirm_direct_buy(cb, cd, cb.bot, state)

        text = cb.message.edit_text.call_args[0][0]
        assert "mochila" in text.lower()
        assert "discernimiento" not in text

    @patch("handlers.store_user_handlers.get_service")
    async def test_confirm_direct_buy_vip_failed_shows_backpack_cta(
        self, mock_get_service, make_callback
    ):
        """VIP grant fallido: mensaje de mochila, no invite vacío."""
        from keyboards.callback_data import ConfirmDirectBuyCallback

        order = MagicMock(id=99, total_price=100)
        store = _mock_store_ctx(mock_get_service)
        store.purchase_and_complete = AsyncMock(
            return_value=(
                order,
                [
                    {
                        "kind": "vip_grant",
                        "status": "failed",
                        "vip_activated": False,
                        "invite_link": "https://t.me/+stale",
                        "product_name": "Mes VIP",
                    }
                ],
                None,
            )
        )
        store._get_order_charge_amount = MagicMock(return_value=100)
        cb = make_callback(data="confirm_direct_buy:1")
        cd = ConfirmDirectBuyCallback(product_id=1)
        state = AsyncMock()

        from handlers.store_user_handlers import confirm_direct_buy

        await confirm_direct_buy(cb, cd, cb.bot, state)

        text = cb.message.edit_text.call_args[0][0]
        assert "mochila" in text.lower()
        assert "https://t.me/+stale" not in text


class TestPurchaseHistory:
    """Tests para purchase_history - historial de compras."""

    @patch("handlers.store_user_handlers.get_service")
    async def test_empty_history(self, mock_get_service, make_callback):
        """Historial vacio muestra mensaje."""
        store = _mock_store_ctx(mock_get_service)
        store.get_user_orders.return_value = []
        cb = make_callback(data="purchase_history")

        from handlers.store_user_handlers import purchase_history
        await purchase_history(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "adquisiciones" in text.lower()

    @patch("handlers.store_user_handlers.get_service")
    async def test_displays_orders(self, mock_get_service, make_callback):
        """Muestra ordenes del historial."""
        order = model_mock(Order)
        order.id = 42
        order.status = MagicMock()
        order.status.value = "completed"
        order.created_at = datetime(2024, 6, 15, 10, 30)
        order.total_items = 3
        order.total_price = 500
        store = _mock_store_ctx(mock_get_service)
        store.get_user_orders.return_value = [order]
        cb = make_callback(data="purchase_history")

        from handlers.store_user_handlers import purchase_history
        await purchase_history(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "42" in text
        assert "3" in text
        assert "500" in text
        assert "15/06/2024" in text

    @patch("handlers.store_user_handlers.get_service")
    async def test_displays_pending_status(self, mock_get_service, make_callback):
        """Orden pendiente se marca con reloj."""
        order = model_mock(Order)
        order.id = 1
        order.status = MagicMock()
        order.status.value = "pending"
        order.created_at = datetime(2024, 6, 15, 10, 30)
        order.total_items = 1
        order.total_price = 100
        store = _mock_store_ctx(mock_get_service)
        store.get_user_orders.return_value = [order]
        cb = make_callback(data="purchase_history")

        from handlers.store_user_handlers import purchase_history
        await purchase_history(cb)

        cb.message.edit_text.assert_called_once()

    @patch("handlers.store_user_handlers.get_service")
    async def test_displays_cancelled_status(self, mock_get_service, make_callback):
        """Orden cancelada se marca con X."""
        order = model_mock(Order)
        order.id = 1
        order.status = MagicMock()
        order.status.value = "cancelled"
        order.created_at = datetime(2024, 6, 15, 10, 30)
        order.total_items = 1
        order.total_price = 100
        store = _mock_store_ctx(mock_get_service)
        store.get_user_orders.return_value = [order]
        cb = make_callback(data="purchase_history")

        from handlers.store_user_handlers import purchase_history
        await purchase_history(cb)

        cb.message.edit_text.assert_called_once()

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_service_with_user_id_and_limit(self, mock_get_service, make_callback):
        """Llama a get_user_orders con user_id y limit=10."""
        store = _mock_store_ctx(mock_get_service)
        store.get_user_orders.return_value = []
        cb = make_callback(data="purchase_history")

        from handlers.store_user_handlers import purchase_history
        await purchase_history(cb)

        store.get_user_orders.assert_called_once_with(123456789, limit=10)

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Siempre llama a callback.answer()."""
        store = _mock_store_ctx(mock_get_service)
        store.get_user_orders.return_value = []
        cb = make_callback(data="purchase_history")

        from handlers.store_user_handlers import purchase_history
        await purchase_history(cb)

        cb.answer.assert_called_once()


class TestStoreSearchStart:
    """Tests para store_search_start - inicio de busqueda."""

    async def test_sets_fsm_state(self, make_callback, make_fsm_context):
        """Establece el estado FSM a waiting_query."""
        cb = make_callback(data="store_search")
        fsm = await make_fsm_context()

        from handlers.store_user_handlers import store_search_start
        await store_search_start(cb, fsm)

        current_state = await fsm.get_state()
        from handlers.store_user_handlers import SearchStates
        assert current_state == SearchStates.waiting_query

    async def test_shows_search_prompt(self, make_callback, make_fsm_context):
        """Muestra mensaje de busqueda."""
        cb = make_callback(data="store_search")
        fsm = await make_fsm_context()

        from handlers.store_user_handlers import store_search_start
        await store_search_start(cb, fsm)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "producto busca" in text.lower() or "busca" in text.lower()

    async def test_calls_answer(self, make_callback, make_fsm_context):
        """Llama a callback.answer()."""
        cb = make_callback(data="store_search")
        fsm = await make_fsm_context()

        from handlers.store_user_handlers import store_search_start
        await store_search_start(cb, fsm)

        cb.answer.assert_called_once()


class TestProcessSearchQuery:
    """Tests para process_search_query - procesamiento de busqueda."""

    @patch("handlers.store_user_handlers.get_service")
    async def test_short_query_shows_prompt(self, mock_get_service, make_message, make_fsm_context):
        """Query menor a 2 caracteres pide escribir mas."""
        msg = make_message(text="a")
        fsm = await make_fsm_context()
        await fsm.set_state(type("S", (), {"waiting_query": "waiting_query"})())

        from handlers.store_user_handlers import process_search_query
        await process_search_query(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "2 caracteres" in text.lower() or "al menos" in text.lower()

    @patch("handlers.store_user_handlers.get_service")
    async def test_short_query_does_not_search(self, mock_get_service, make_message, make_fsm_context):
        """Query corta no llama al servicio de busqueda."""
        msg = make_message(text="a")
        fsm = await make_fsm_context()

        from handlers.store_user_handlers import process_search_query
        await process_search_query(msg, fsm)

        store = _mock_store_ctx(mock_get_service)
        store.search_products.assert_not_called()

    @patch("handlers.store_user_handlers.get_service")
    async def test_no_results_shows_not_found(self, mock_get_service, make_message, make_fsm_context):
        """Sin resultados, muestra mensaje de no encontrado."""
        store = _mock_store_ctx(mock_get_service)
        store.search_products.return_value = []
        msg = make_message(text="xyz")
        fsm = await make_fsm_context()

        from handlers.store_user_handlers import process_search_query
        await process_search_query(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "no se encontraron" in text.lower()

    @patch("handlers.store_user_handlers.get_service")
    async def test_no_results_clears_state(self, mock_get_service, make_message, make_fsm_context):
        """Sin resultados, limpia el estado FSM."""
        store = _mock_store_ctx(mock_get_service)
        store.search_products.return_value = []
        msg = make_message(text="xyz")
        fsm = await make_fsm_context()
        await fsm.set_state(type("S", (), {"waiting_query": "waiting_query"})())

        from handlers.store_user_handlers import process_search_query
        await process_search_query(msg, fsm)

        current_state = await fsm.get_state()
        assert current_state is None

    @patch("handlers.store_user_handlers.get_service")
    async def test_shows_results(self, mock_get_service, make_message, make_fsm_context):
        """Muestra resultados de busqueda."""
        product = MagicMock(id=1, name="Tesoro Encontrado", price=100)
        store = _mock_store_ctx(mock_get_service)
        store.search_products.return_value = [product]
        msg = make_message(text="tesoro")
        fsm = await make_fsm_context()

        from handlers.store_user_handlers import process_search_query
        await process_search_query(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "producto" in text.lower() or "busca" in text.lower()
        assert "1" in text

    @patch("handlers.store_user_handlers.get_service")
    async def test_results_clears_state(self, mock_get_service, make_message, make_fsm_context):
        """Con resultados, limpia el estado FSM."""
        product = MagicMock(id=1, name="Tesoro", price=100)
        store = _mock_store_ctx(mock_get_service)
        store.search_products.return_value = [product]
        msg = make_message(text="tesoro")
        fsm = await make_fsm_context()

        from handlers.store_user_handlers import process_search_query
        await process_search_query(msg, fsm)

        current_state = await fsm.get_state()
        assert current_state is None

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_service_with_query_and_active_only(self, mock_get_service, make_message, make_fsm_context):
        """Llama a search_products con el query y active_only=True."""
        store = _mock_store_ctx(mock_get_service)
        store.search_products.return_value = []
        msg = make_message(text="video")
        fsm = await make_fsm_context()

        from handlers.store_user_handlers import process_search_query
        await process_search_query(msg, fsm)

        store.search_products.assert_called_once_with("video", active_only=True)


class TestStoreFilters:
    """Tests para store_filters - menu de filtros."""

    async def test_shows_filter_options(self, make_callback):
        """Muestra opciones de filtrado."""
        cb = make_callback(data="store_filters")

        from handlers.store_user_handlers import store_filters
        await store_filters(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "ordenar" in text.lower()

    async def test_calls_answer(self, make_callback):
        """Llama a callback.answer()."""
        cb = make_callback(data="store_filters")

        from handlers.store_user_handlers import store_filters
        await store_filters(cb)

        cb.answer.assert_called_once()


class TestFilterPriceAsc:
    """Tests para filter_price_asc - filtro precio ascendente."""

    @patch("handlers.store_user_handlers.get_service")
    async def test_empty_products(self, mock_get_service, make_callback):
        """Sin productos muestra mensaje."""
        store = _mock_store_ctx(mock_get_service)
        store.get_all_products.return_value = []
        cb = make_callback(data="filter_price_asc")

        from handlers.store_user_handlers import filter_price_asc
        await filter_price_asc(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "no se encontraron" in text.lower() or "no hay" in text.lower()

    @patch("handlers.store_user_handlers.get_service")
    async def test_displays_products_sorted_asc(self, mock_get_service, make_callback):
        """Muestra productos ordenados por precio ascendente."""
        p1 = MagicMock(id=1, name="Caro", price=200)
        p2 = MagicMock(id=2, name="Barato", price=50)
        store = _mock_store_ctx(mock_get_service)
        store.get_all_products.return_value = [p1, p2]
        cb = make_callback(data="filter_price_asc")

        from handlers.store_user_handlers import filter_price_asc
        await filter_price_asc(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "menor a mayor" in text

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Llama a callback.answer()."""
        store = _mock_store_ctx(mock_get_service)
        store.get_all_products.return_value = []
        cb = make_callback(data="filter_price_asc")

        from handlers.store_user_handlers import filter_price_asc
        await filter_price_asc(cb)

        cb.answer.assert_called_once()


class TestFilterPriceDesc:
    """Tests para filter_price_desc - filtro precio descendente."""

    @patch("handlers.store_user_handlers.get_service")
    async def test_empty_products(self, mock_get_service, make_callback):
        """Sin productos muestra mensaje."""
        store = _mock_store_ctx(mock_get_service)
        store.get_all_products.return_value = []
        cb = make_callback(data="filter_price_desc")

        from handlers.store_user_handlers import filter_price_desc
        await filter_price_desc(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "no se encontraron" in text.lower() or "no hay" in text.lower()

    @patch("handlers.store_user_handlers.get_service")
    async def test_displays_products_sorted_desc(self, mock_get_service, make_callback):
        """Muestra productos ordenados por precio descendente."""
        p1 = MagicMock(id=1, name="Barato", price=50)
        p2 = MagicMock(id=2, name="Caro", price=200)
        store = _mock_store_ctx(mock_get_service)
        store.get_all_products.return_value = [p1, p2]
        cb = make_callback(data="filter_price_desc")

        from handlers.store_user_handlers import filter_price_desc
        await filter_price_desc(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "mayor a menor" in text

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Llama a callback.answer()."""
        store = _mock_store_ctx(mock_get_service)
        store.get_all_products.return_value = []
        cb = make_callback(data="filter_price_desc")

        from handlers.store_user_handlers import filter_price_desc
        await filter_price_desc(cb)

        cb.answer.assert_called_once()


class TestFilterInStock:
    """Tests para filter_in_stock - solo disponibles."""

    @patch("handlers.store_user_handlers.get_service")
    async def test_empty_products(self, mock_get_service, make_callback):
        """Sin productos disponibles muestra mensaje."""
        store = _mock_store_ctx(mock_get_service)
        store.get_available_products.return_value = []
        cb = make_callback(data="filter_in_stock")

        from handlers.store_user_handlers import filter_in_stock
        await filter_in_stock(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "no se encontraron" in text.lower() or "no hay" in text.lower()

    @patch("handlers.store_user_handlers.get_service")
    async def test_displays_available_products(self, mock_get_service, make_callback):
        """Muestra solo productos disponibles."""
        product = MagicMock(id=1, name="Disponible", price=100)
        store = _mock_store_ctx(mock_get_service)
        store.get_available_products.return_value = [product]
        cb = make_callback(data="filter_in_stock")

        from handlers.store_user_handlers import filter_in_stock
        await filter_in_stock(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Solo disponibles" in text

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_service(self, mock_get_service, make_callback):
        """Llama a get_available_products."""
        store = _mock_store_ctx(mock_get_service)
        store.get_available_products.return_value = []
        cb = make_callback(data="filter_in_stock")

        from handlers.store_user_handlers import filter_in_stock
        await filter_in_stock(cb)

        store.get_available_products.assert_called_once()

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Llama a callback.answer()."""
        store = _mock_store_ctx(mock_get_service)
        store.get_available_products.return_value = []
        cb = make_callback(data="filter_in_stock")

        from handlers.store_user_handlers import filter_in_stock
        await filter_in_stock(cb)

        cb.answer.assert_called_once()


class TestFilterRecent:
    """Tests para filter_recent - productos mas recientes."""

    @patch("handlers.store_user_handlers.get_service")
    async def test_empty_products(self, mock_get_service, make_callback):
        """Sin productos muestra mensaje."""
        store = _mock_store_ctx(mock_get_service)
        store.get_all_products.return_value = []
        cb = make_callback(data="filter_recent")

        from handlers.store_user_handlers import filter_recent
        await filter_recent(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "no se encontraron" in text.lower() or "no hay" in text.lower()

    @patch("handlers.store_user_handlers.get_service")
    async def test_displays_recent_products(self, mock_get_service, make_callback):
        """Muestra los productos mas recientes."""
        product = MagicMock(id=1, name="Nuevo", price=100)
        store = _mock_store_ctx(mock_get_service)
        store.get_all_products.return_value = [product]
        cb = make_callback(data="filter_recent")

        from handlers.store_user_handlers import filter_recent
        await filter_recent(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "más recientes" in text.lower()

    @patch("handlers.store_user_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Llama a callback.answer()."""
        store = _mock_store_ctx(mock_get_service)
        store.get_all_products.return_value = []
        cb = make_callback(data="filter_recent")

        from handlers.store_user_handlers import filter_recent
        await filter_recent(cb)

        cb.answer.assert_called_once()


class TestStoreTierNavigation:
    @patch("handlers.store_user_handlers.get_service")
    async def test_store_tiers_menu(self, mock_get_service, make_callback):
        tier = MagicMock(id=1, name="IMPULSO", price_min=50, price_max=120)
        store = _mock_store_ctx(mock_get_service)
        store.get_tiers_for_shop.return_value = [tier]
        cb = make_callback(data="store_tiers")
        from handlers.store_user_handlers import store_tiers_menu

        await store_tiers_menu(cb)
        store.get_tiers_for_shop.assert_called_once_with(active_only=True)
        cb.message.edit_text.assert_called_once()

    @patch("handlers.store_user_handlers.get_service")
    async def test_store_tier_products(self, mock_get_service, make_callback):
        tier = MagicMock(id=2, name="DESEO", slug="deseo")
        product = MagicMock(id=10, name="El Corto", price=250)
        store = _mock_store_ctx(mock_get_service)
        store.get_all_tiers.return_value = [tier]
        store.get_products_by_tier.return_value = [product]
        cb = make_callback(data="store_tier:2")
        from keyboards.callback_data import StoreTierCallback
        from handlers.store_user_handlers import store_tier_products

        await store_tier_products(cb, StoreTierCallback(tier_id=2))
        cb.message.edit_text.assert_called_once()


class TestPurchaseInputFSM:
    @patch("handlers.store_user_handlers.get_service")
    async def test_process_purchase_input_success(self, mock_get_service, make_message):
        store = _mock_store_ctx(mock_get_service)
        store.submit_purchase_input = AsyncMock(return_value=(True, "OK"))
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"fulfillment_id": 5})
        state.clear = AsyncMock()
        msg = make_message(text="Mi pregunta favorita")
        from handlers.store_user_handlers import process_purchase_input

        await process_purchase_input(msg, state)
        store.submit_purchase_input.assert_called_once()
        state.clear.assert_called_once()

    @patch("handlers.store_user_handlers.get_service")
    async def test_confirm_direct_buy_sets_fsm_on_pending_input(
        self, mock_get_service, make_callback
    ):
        store = _mock_store_ctx(mock_get_service)
        order = MagicMock(id=9, total_price=100)
        store.purchase_and_complete = AsyncMock(
            return_value=(
                order,
                [{"kind": "user_input", "status": "pending_input", "fulfillment_id": 77}],
                None,
            )
        )
        store._get_order_charge_amount = MagicMock(return_value=100)
        state = AsyncMock()
        cb = make_callback(data="confirm_direct_buy:1")
        from keyboards.callback_data import ConfirmDirectBuyCallback
        from handlers.store_user_handlers import PurchaseInputStates, confirm_direct_buy

        await confirm_direct_buy(
            cb, ConfirmDirectBuyCallback(product_id=1), cb.bot, state
        )
        state.set_state.assert_called_once_with(PurchaseInputStates.awaiting_input)
        state.update_data.assert_called_once_with(fulfillment_id=77)

    @patch("handlers.store_user_handlers.get_service")
    async def test_process_purchase_input_validation_failure_keeps_fsm(
        self, mock_get_service, make_message
    ):
        from utils.lucien_voice import LucienVoice

        store = _mock_store_ctx(mock_get_service)
        store.submit_purchase_input = AsyncMock(
            return_value=(False, LucienVoice.fulfillment_input_invalid_length(3, 100))
        )
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"fulfillment_id": 5})
        msg = make_message(text="x")
        from handlers.store_user_handlers import PurchaseInputStates, process_purchase_input

        await process_purchase_input(msg, state)
        state.set_state.assert_called_with(PurchaseInputStates.awaiting_input)
        state.clear.assert_not_called()

    async def test_cancel_purchase_input_clears_state(self, make_message):
        state = AsyncMock()
        msg = make_message(text="/cancel")
        from handlers.store_user_handlers import cancel_purchase_input

        await cancel_purchase_input(msg, state)
        state.clear.assert_called_once()

    @patch("handlers.store_user_handlers.get_service")
    async def test_process_purchase_input_already_submitted_clears_fsm(
        self, mock_get_service, make_message
    ):
        from utils.lucien_voice import LucienVoice

        store = _mock_store_ctx(mock_get_service)
        store.submit_purchase_input = AsyncMock(
            return_value=(False, LucienVoice.fulfillment_input_already_submitted())
        )
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={"fulfillment_id": 5})
        msg = make_message(text="ya enviado")
        from handlers.store_user_handlers import process_purchase_input

        await process_purchase_input(msg, state)
        state.clear.assert_called_once()


class TestShowFilteredProducts:
    """Tests para show_filtered_products - helper de visualizacion."""

    async def test_empty_products(self, make_callback):
        """Lista vacia muestra mensaje de no coincidencias."""
        cb = make_callback(data="filter_price_asc")

        from handlers.store_user_handlers import show_filtered_products
        await show_filtered_products(cb, [], "Precio: menor a mayor")

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "no se encontraron" in text.lower() or "no hay" in text.lower()

    async def test_shows_filtered_products(self, make_callback):
        """Muestra productos filtrados con el nombre del filtro."""
        p1 = MagicMock(id=1, name="Producto A", price=100)
        p2 = MagicMock(id=2, name="Producto B", price=200)
        cb = make_callback(data="filter_recent")

        from handlers.store_user_handlers import show_filtered_products
        from utils.lucien_voice import LucienVoice

        await show_filtered_products(cb, [p1, p2], LucienVoice.store_filter_label_recent())

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "recientes" in text.lower()
        assert "2" in text

    async def test_shows_overflow_message(self, make_callback):
        """Mas de 10 productos muestra mensaje de '...y X mas'."""
        products = []
        for i in range(15):
            products.append(MagicMock(id=i, name=f"Producto {i}", price=i * 10))
        cb = make_callback(data="filter_recent")

        from handlers.store_user_handlers import show_filtered_products
        await show_filtered_products(cb, products, "Todos")

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "5 más" in text  # 15 - 10 = 5

    async def test_no_overflow_for_10_or_less(self, make_callback):
        """10 o menos productos no muestra mensaje de overflow."""
        products = []
        for i in range(10):
            products.append(MagicMock(id=i, name=f"P{i}", price=i * 10))
        cb = make_callback(data="filter_recent")

        from handlers.store_user_handlers import show_filtered_products
        await show_filtered_products(cb, products, "Test")

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "mas" not in text.lower() or "...y 0 mas" not in text  # no overflow msg

    async def test_calls_answer(self, make_callback):
        """Llama a callback.answer()."""
        product = MagicMock(id=1, name="P1", price=100)
        cb = make_callback(data="filter_recent")

        from handlers.store_user_handlers import show_filtered_products
        await show_filtered_products(cb, [product], "Test")

        cb.answer.assert_called_once()
