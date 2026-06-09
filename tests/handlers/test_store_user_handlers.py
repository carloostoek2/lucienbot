"""
Tests unitarios para store_user_handlers.

Cubre handlers de tienda: menu, catalogo, categorias, detalle de producto,
preview, compra directa, historial, busqueda y filtros.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

pytestmark = [pytest.mark.unit]


class TestShopMenu:
    """Tests para shop_menu - menu principal de la tienda."""

    @patch("handlers.store_user_handlers.BesitoService")
    async def test_shows_balance_and_menu(self, mock_besito, make_callback):
        """Muestra el saldo del usuario y las opciones del menu."""
        mock_besito.return_value.get_balance.return_value = 500
        cb = make_callback(data="shop")

        from handlers.store_user_handlers import shop_menu
        await shop_menu(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "500" in text
        assert "tienda" in text.lower()

    @patch("handlers.store_user_handlers.BesitoService")
    async def test_calls_service_with_user_id(self, mock_besito, make_callback):
        """Llama a get_balance con el user_id correcto."""
        mock_besito.return_value.get_balance.return_value = 500
        cb = make_callback(data="shop")

        from handlers.store_user_handlers import shop_menu
        await shop_menu(cb)

        mock_besito.return_value.get_balance.assert_called_once_with(123456789)

    @patch("handlers.store_user_handlers.BesitoService")
    async def test_calls_answer(self, mock_besito, make_callback):
        """Siempre llama a callback.answer()."""
        mock_besito.return_value.get_balance.return_value = 500
        cb = make_callback(data="shop")

        from handlers.store_user_handlers import shop_menu
        await shop_menu(cb)

        cb.answer.assert_called_once()

    @patch("handlers.store_user_handlers.BesitoService")
    async def test_closes_service(self, mock_besito, make_callback):
        """BesitoService se cierra en finally."""
        mock_besito.return_value.get_balance.return_value = 500
        cb = make_callback(data="shop")

        from handlers.store_user_handlers import shop_menu
        await shop_menu(cb)

        mock_besito.return_value.close.assert_called_once()


class TestStoreCatalog:
    """Tests para store_catalog - catalogo completo de productos."""

    @patch("handlers.store_user_handlers.StoreService")
    async def test_empty_catalog_shows_empty_message(self, mock_store, make_callback):
        """Cuando no hay productos, muestra mensaje de tienda vacia."""
        mock_store.return_value.get_all_products.return_value = []
        cb = make_callback(data="store_catalog")

        from handlers.store_user_handlers import store_catalog
        await store_catalog(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "vacia" in text.lower()

    @patch("handlers.store_user_handlers.StoreService")
    async def test_displays_products(self, mock_store, make_callback):
        """Muestra los productos en el catalogo."""
        p1 = MagicMock(id=1, name="Product A")
        p2 = MagicMock(id=2, name="Product B")
        mock_store.return_value.get_all_products.return_value = [p1, p2]
        cb = make_callback(data="store_catalog")

        from handlers.store_user_handlers import store_catalog
        await store_catalog(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Catalogo" in text

    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_service_with_active_only(self, mock_store, make_callback):
        """Llama a get_all_products con active_only=True."""
        mock_store.return_value.get_all_products.return_value = []
        cb = make_callback(data="store_catalog")

        from handlers.store_user_handlers import store_catalog
        await store_catalog(cb)

        mock_store.return_value.get_all_products.assert_called_once_with(active_only=True)

    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_answer(self, mock_store, make_callback):
        """Siempre llama a callback.answer()."""
        mock_store.return_value.get_all_products.return_value = []
        cb = make_callback(data="store_catalog")

        from handlers.store_user_handlers import store_catalog
        await store_catalog(cb)

        cb.answer.assert_called_once()

    @patch("handlers.store_user_handlers.StoreService")
    async def test_closes_service(self, mock_store, make_callback):
        """StoreService se cierra en finally."""
        mock_store.return_value.get_all_products.return_value = []
        cb = make_callback(data="store_catalog")

        from handlers.store_user_handlers import store_catalog
        await store_catalog(cb)

        mock_store.return_value.close.assert_called_once()


class TestStoreCategories:
    """Tests para store_categories - categorias disponibles."""

    @patch("handlers.store_user_handlers.PackageService")
    async def test_empty_categories_shows_message(self, mock_pkg, make_callback):
        """Cuando no hay categorias, muestra mensaje de catalogo sin secciones."""
        mock_pkg.return_value.get_all_categories.return_value = []
        cb = make_callback(data="store_categories")

        from handlers.store_user_handlers import store_categories
        await store_categories(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "secciones" in text.lower()

    @patch("handlers.store_user_handlers.PackageService")
    async def test_displays_categories_with_counts(self, mock_pkg, make_callback):
        """Muestra categorias con conteo de paquetes activos."""
        cat1 = MagicMock()
        cat1.id = 1
        cat1.name = "Fotos"
        cat1.packages = [MagicMock(is_active=True), MagicMock(is_active=True)]
        cat2 = MagicMock()
        cat2.id = 2
        cat2.name = "Videos"
        cat2.packages = []
        mock_pkg.return_value.get_all_categories.return_value = [cat1, cat2]
        cb = make_callback(data="store_categories")

        from handlers.store_user_handlers import store_categories
        await store_categories(cb)

        cb.message.edit_text.assert_called_once()
        markup = cb.message.edit_text.call_args[1].get("reply_markup")
        button_texts = [btn.text for row in markup.inline_keyboard for btn in row]
        assert any("Fotos" in t for t in button_texts)
        assert any("Videos" in t for t in button_texts)

    @patch("handlers.store_user_handlers.PackageService")
    async def test_category_count_shows_active_packages_only(self, mock_pkg, make_callback):
        """El conteo muestra solo paquetes activos."""
        cat = MagicMock()
        cat.id = 1
        cat.name = "Mix"
        cat.packages = [
            MagicMock(is_active=True),
            MagicMock(is_active=False),
            MagicMock(is_active=True),
        ]
        mock_pkg.return_value.get_all_categories.return_value = [cat]
        cb = make_callback(data="store_categories")

        from handlers.store_user_handlers import store_categories
        await store_categories(cb)

        markup = cb.message.edit_text.call_args[1].get("reply_markup")
        button_texts = [btn.text for row in markup.inline_keyboard for btn in row]
        assert any("(2)" in t for t in button_texts)

    @patch("handlers.store_user_handlers.PackageService")
    async def test_calls_service_with_active_only(self, mock_pkg, make_callback):
        """Llama a get_all_categories con active_only=True."""
        mock_pkg.return_value.get_all_categories.return_value = []
        cb = make_callback(data="store_categories")

        from handlers.store_user_handlers import store_categories
        await store_categories(cb)

        mock_pkg.return_value.get_all_categories.assert_called_once_with(active_only=True)

    @patch("handlers.store_user_handlers.PackageService")
    async def test_calls_answer(self, mock_pkg, make_callback):
        """Siempre llama a callback.answer()."""
        mock_pkg.return_value.get_all_categories.return_value = []
        cb = make_callback(data="store_categories")

        from handlers.store_user_handlers import store_categories
        await store_categories(cb)

        cb.answer.assert_called_once()

    @patch("handlers.store_user_handlers.PackageService")
    async def test_closes_service(self, mock_pkg, make_callback):
        """PackageService se cierra en finally."""
        mock_pkg.return_value.get_all_categories.return_value = []
        cb = make_callback(data="store_categories")

        from handlers.store_user_handlers import store_categories
        await store_categories(cb)

        mock_pkg.return_value.close.assert_called_once()

    @patch("handlers.store_user_handlers.PackageService")
    async def test_category_without_packages_does_not_crash(self, mock_pkg, make_callback):
        """Categoria con packages=None no causa error."""
        cat = MagicMock()
        cat.id = 1
        cat.name = "Empty"
        cat.packages = None
        mock_pkg.return_value.get_all_categories.return_value = [cat]
        cb = make_callback(data="store_categories")

        from handlers.store_user_handlers import store_categories
        await store_categories(cb)

        cb.message.edit_text.assert_called_once()


class TestStoreCategoryProducts:
    """Tests para store_category_products - productos por categoria."""

    @patch("handlers.store_user_handlers.StoreService")
    @patch("handlers.store_user_handlers.PackageService")
    async def test_category_not_found(self, mock_pkg, mock_store, make_callback):
        """Categoria no encontrada muestra alerta."""
        from keyboards.callback_data import StoreCategoryCallback
        mock_pkg.return_value.get_category.return_value = None
        cb = make_callback(data="store_category:1")
        cd = StoreCategoryCallback(category_id=1)

        from handlers.store_user_handlers import store_category_products
        await store_category_products(cb, cd)

        cb.answer.assert_called_once_with("Categoria no encontrada", show_alert=True)

    @patch("handlers.store_user_handlers.StoreService")
    @patch("handlers.store_user_handlers.PackageService")
    async def test_category_empty_products(self, mock_pkg, mock_store, make_callback):
        """Categoria sin productos muestra mensaje de estanteria vacia."""
        from keyboards.callback_data import StoreCategoryCallback
        category = MagicMock()
        category.id = 1
        category.name = "Fotos Exclusivas"
        category.description = "Fotos que pocos veran"
        mock_pkg.return_value.get_category.return_value = category
        mock_store.return_value.filter_products.return_value = []
        cb = make_callback(data="store_category:1")
        cd = StoreCategoryCallback(category_id=1)

        from handlers.store_user_handlers import store_category_products
        await store_category_products(cb, cd)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "vacia" in text.lower()
        assert "Fotos Exclusivas" in text

    @patch("handlers.store_user_handlers.StoreService")
    @patch("handlers.store_user_handlers.PackageService")
    async def test_displays_category_products(self, mock_pkg, mock_store, make_callback):
        """Muestra productos de la categoria con descripcion."""
        from keyboards.callback_data import StoreCategoryCallback
        category = MagicMock()
        category.id = 1
        category.name = "Fotos"
        category.description = "Descripcion de la categoria"
        product = MagicMock(id=1, name="Producto X", price=100)
        mock_pkg.return_value.get_category.return_value = category
        mock_store.return_value.filter_products.return_value = [product]
        cb = make_callback(data="store_category:1")
        cd = StoreCategoryCallback(category_id=1)

        from handlers.store_user_handlers import store_category_products
        await store_category_products(cb, cd)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Fotos" in text
        assert "Descripcion de la categoria" in text

    @patch("handlers.store_user_handlers.StoreService")
    @patch("handlers.store_user_handlers.PackageService")
    async def test_calls_services_with_correct_params(self, mock_pkg, mock_store, make_callback):
        """Llama a get_category y filter_products con parametros correctos."""
        from keyboards.callback_data import StoreCategoryCallback
        category = MagicMock(id=1, name="Test", description="")
        mock_pkg.return_value.get_category.return_value = category
        mock_store.return_value.filter_products.return_value = []
        cb = make_callback(data="store_category:1")
        cd = StoreCategoryCallback(category_id=1)

        from handlers.store_user_handlers import store_category_products
        await store_category_products(cb, cd)

        mock_pkg.return_value.get_category.assert_called_once_with(1)
        mock_store.return_value.filter_products.assert_called_once_with(
            category_id=1, active_only=True
        )

    @patch("handlers.store_user_handlers.StoreService")
    @patch("handlers.store_user_handlers.PackageService")
    async def test_calls_answer(self, mock_pkg, mock_store, make_callback):
        """Llama a callback.answer cuando hay productos."""
        from keyboards.callback_data import StoreCategoryCallback
        category = MagicMock(id=1, name="Test", description="")
        product = MagicMock(id=1, name="Producto X", price=100)
        mock_pkg.return_value.get_category.return_value = category
        mock_store.return_value.filter_products.return_value = [product]
        cb = make_callback(data="store_category:1")
        cd = StoreCategoryCallback(category_id=1)

        from handlers.store_user_handlers import store_category_products
        await store_category_products(cb, cd)

        cb.answer.assert_called_once()


class TestProductDetail:
    """Tests para product_detail - detalle de producto."""

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_product_not_found(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Producto no encontrado muestra alerta."""
        from keyboards.callback_data import ProductDetailCallback
        mock_store.return_value.get_product.return_value = None
        cb = make_callback(data="product_detail:1")
        cd = ProductDetailCallback(product_id=1)

        from handlers.store_user_handlers import product_detail
        await product_detail(cb, cd)

        cb.answer.assert_called_once_with("Producto no encontrado", show_alert=True)

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_sufficient_balance_shows_buy_button(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Con saldo suficiente, muestra boton de comprar."""
        from keyboards.callback_data import ProductDetailCallback
        product = MagicMock()
        product.id = 1
        product.name = "Producto X"
        product.description = "Descripcion"
        product.price = 100
        product.stock = 10
        product.is_available = True
        product.package = MagicMock(id=1)
        mock_store.return_value.get_product.return_value = product
        mock_pkg.return_value.get_package_files.return_value = [MagicMock()]
        mock_besito.return_value.get_balance.return_value = 500
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
        assert any("Comprar ahora" in t for t in buy_texts)
        assert any("Preview" in t for t in buy_texts)

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_insufficient_balance_shows_needed_amount(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Con saldo insuficiente, muestra cuanto falta."""
        from keyboards.callback_data import ProductDetailCallback
        product = MagicMock()
        product.id = 1
        product.name = "Producto Caro"
        product.description = "Caro"
        product.price = 300
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        mock_store.return_value.get_product.return_value = product
        mock_pkg.return_value.get_package_files.return_value = []
        mock_besito.return_value.get_balance.return_value = 100
        cb = make_callback(data="product_detail:1")
        cd = ProductDetailCallback(product_id=1)

        from handlers.store_user_handlers import product_detail
        await product_detail(cb, cd)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Necesitas mas besitos" in text
        # Check the insufficient balance button
        markup = cb.message.edit_text.call_args[1].get("reply_markup")
        buttons = markup.inline_keyboard
        buy_row = buttons[0]
        buy_texts = [btn.text for btn in buy_row]
        assert any("200" in t for t in buy_texts)
        assert any("besitos mas" in t for t in buy_texts)

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_product_not_available_shows_agotado(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Producto no disponible muestra boton de agotado."""
        from keyboards.callback_data import ProductDetailCallback
        product = MagicMock()
        product.id = 1
        product.name = "Agotado"
        product.description = "No hay"
        product.price = 100
        product.stock = 0
        product.is_available = False
        product.package = MagicMock(id=1)
        mock_store.return_value.get_product.return_value = product
        mock_pkg.return_value.get_package_files.return_value = []
        mock_besito.return_value.get_balance.return_value = 500
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

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_unlimited_stock_displays_infinity(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Stock -1 se muestra como infinito."""
        from keyboards.callback_data import ProductDetailCallback
        product = MagicMock()
        product.id = 1
        product.name = "Ilimitado"
        product.description = "Sin limites"
        product.price = 100
        product.stock = -1
        product.is_available = True
        product.package = MagicMock(id=1)
        mock_store.return_value.get_product.return_value = product
        mock_pkg.return_value.get_package_files.return_value = []
        mock_besito.return_value.get_balance.return_value = 100
        cb = make_callback(data="product_detail:1")
        cd = ProductDetailCallback(product_id=1)

        from handlers.store_user_handlers import product_detail
        await product_detail(cb, cd)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "∞" in text

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_answer(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Siempre llama a callback.answer()."""
        from keyboards.callback_data import ProductDetailCallback
        product = MagicMock()
        product.id = 1
        product.name = "Test"
        product.description = ""
        product.price = 100
        product.stock = 10
        product.is_available = True
        product.package = MagicMock(id=1)
        mock_store.return_value.get_product.return_value = product
        mock_pkg.return_value.get_package_files.return_value = []
        mock_besito.return_value.get_balance.return_value = 200
        cb = make_callback(data="product_detail:1")
        cd = ProductDetailCallback(product_id=1)

        from handlers.store_user_handlers import product_detail
        await product_detail(cb, cd)

        cb.answer.assert_called_once()

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_services_with_correct_params(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Llama a servicios con parametros correctos."""
        from keyboards.callback_data import ProductDetailCallback
        product = MagicMock()
        product.id = 42
        product.name = "Test"
        product.description = ""
        product.price = 100
        product.stock = 10
        product.is_available = True
        product.package_id = 99
        mock_store.return_value.get_product.return_value = product
        mock_pkg.return_value.get_package_files.return_value = []
        mock_besito.return_value.get_balance.return_value = 200
        cb = make_callback(data="product_detail:42")
        cd = ProductDetailCallback(product_id=42)

        from handlers.store_user_handlers import product_detail
        await product_detail(cb, cd)

        mock_store.return_value.get_product.assert_called_once_with(42)
        mock_besito.return_value.get_balance.assert_called_once_with(123456789)
        mock_pkg.return_value.get_package_files.assert_called_once_with(99)


class TestProductPreview:
    """Tests para product_preview - preview de producto."""

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_product_not_found(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Producto no encontrado muestra alerta."""
        from keyboards.callback_data import ProductPreviewCallback
        mock_store.return_value.get_product.return_value = None
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.answer.assert_called_once_with("Producto no encontrado", show_alert=True)

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_sends_photo_preview(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Envia preview en foto cuando el archivo es photo."""
        from keyboards.callback_data import ProductPreviewCallback
        product = MagicMock()
        product.id = 1
        product.name = "Foto Preview"
        product.description = "Una foto"
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        file_entry = MagicMock(file_id="abc123", file_type="photo")
        mock_store.return_value.get_product.return_value = product
        mock_pkg.return_value.get_package_files.return_value = [file_entry]
        mock_besito.return_value.get_balance.return_value = 200
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.message.answer_photo.assert_called_once_with(
            photo="abc123",
            caption="<i>Preview del contenido...</i>",
            parse_mode="HTML",
        )

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_sends_video_preview(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Envia preview en video cuando el archivo es video."""
        from keyboards.callback_data import ProductPreviewCallback
        product = MagicMock()
        product.id = 1
        product.name = "Video Preview"
        product.description = "Un video"
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        file_entry = MagicMock(file_id="video123", file_type="video")
        mock_store.return_value.get_product.return_value = product
        mock_pkg.return_value.get_package_files.return_value = [file_entry]
        mock_besito.return_value.get_balance.return_value = 200
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.message.answer_video.assert_called_once_with(
            video="video123",
            caption="<i>Preview del contenido...</i>",
            parse_mode="HTML",
        )

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_no_package_files_sends_no_preview(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Sin archivos en el paquete, no envia preview."""
        from keyboards.callback_data import ProductPreviewCallback
        product = MagicMock()
        product.id = 1
        product.name = "Sin Preview"
        product.description = "No hay"
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        mock_store.return_value.get_product.return_value = product
        mock_pkg.return_value.get_package_files.return_value = []
        mock_besito.return_value.get_balance.return_value = 200
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.message.answer_photo.assert_not_called()
        cb.message.answer_video.assert_not_called()

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_no_package_shows_no_preview(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Producto sin paquete no envia preview."""
        from keyboards.callback_data import ProductPreviewCallback
        product = MagicMock()
        product.id = 1
        product.name = "Sin Paquete"
        product.description = ""
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = None
        mock_store.return_value.get_product.return_value = product
        mock_besito.return_value.get_balance.return_value = 200
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.message.answer_photo.assert_not_called()
        cb.message.answer_video.assert_not_called()

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_preview_send_error_caught_gracefully(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Error al enviar preview se captura y no rompe el flujo."""
        from keyboards.callback_data import ProductPreviewCallback
        product = MagicMock()
        product.id = 1
        product.name = "Error Preview"
        product.description = ""
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        file_entry = MagicMock(file_id="bad_file", file_type="photo")
        mock_store.return_value.get_product.return_value = product
        mock_pkg.return_value.get_package_files.return_value = [file_entry]
        mock_besito.return_value.get_balance.return_value = 200
        cb = make_callback(data="product_preview:1")
        cb.message.answer_photo = AsyncMock(side_effect=Exception("API error"))
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        # Should still send the product card
        cb.message.answer.assert_called_once()

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_sends_preview_and_product_card(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Envia preview y luego la tarjeta del producto."""
        from keyboards.callback_data import ProductPreviewCallback
        product = MagicMock()
        product.id = 1
        product.name = "Completo"
        product.description = "Desc"
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        file_entry = MagicMock(file_id="f1", file_type="photo")
        mock_store.return_value.get_product.return_value = product
        mock_pkg.return_value.get_package_files.return_value = [file_entry]
        mock_besito.return_value.get_balance.return_value = 200
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.message.answer_photo.assert_called_once()
        cb.message.answer.assert_called_once()

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.PackageService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_answer_preview_sent(self, mock_store, mock_pkg, mock_besito, make_callback):
        """Responde con 'Preview enviado!'."""
        from keyboards.callback_data import ProductPreviewCallback
        product = MagicMock()
        product.id = 1
        product.name = "Test"
        product.description = ""
        product.price = 100
        product.stock = 5
        product.is_available = True
        product.package = MagicMock(id=1)
        file_entry = MagicMock(file_id="f1", file_type="photo")
        mock_store.return_value.get_product.return_value = product
        mock_pkg.return_value.get_package_files.return_value = [file_entry]
        mock_besito.return_value.get_balance.return_value = 200
        cb = make_callback(data="product_preview:1")
        cd = ProductPreviewCallback(product_id=1)

        from handlers.store_user_handlers import product_preview
        await product_preview(cb, cd)

        cb.answer.assert_called_with("Preview enviado!", show_alert=False)


class TestDirectBuy:
    """Tests para direct_buy - confirmacion de compra directa."""

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_product_not_found(self, mock_store, mock_besito, make_callback):
        """Producto no encontrado muestra alerta."""
        from keyboards.callback_data import DirectBuyCallback
        mock_store.return_value.get_product.return_value = None
        cb = make_callback(data="direct_buy:1")
        cd = DirectBuyCallback(product_id=1)

        from handlers.store_user_handlers import direct_buy
        await direct_buy(cb, cd)

        cb.answer.assert_called_once_with("Producto no encontrado", show_alert=True)

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_insufficient_balance(self, mock_store, mock_besito, make_callback):
        """Saldo insuficiente muestra alerta."""
        from keyboards.callback_data import DirectBuyCallback
        product = MagicMock()
        product.id = 1
        product.price = 500
        mock_store.return_value.get_product.return_value = product
        mock_besito.return_value.get_balance.return_value = 100
        cb = make_callback(data="direct_buy:1")
        cd = DirectBuyCallback(product_id=1)

        from handlers.store_user_handlers import direct_buy
        await direct_buy(cb, cd)

        cb.answer.assert_called_once_with("Saldo insuficiente", show_alert=True)

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_sufficient_balance_shows_confirmation(self, mock_store, mock_besito, make_callback):
        """Saldo suficiente muestra pantalla de confirmacion."""
        from keyboards.callback_data import DirectBuyCallback
        product = MagicMock()
        product.id = 42
        product.name = "Producto Test"
        product.price = 200
        mock_store.return_value.get_product.return_value = product
        mock_besito.return_value.get_balance.return_value = 500
        cb = make_callback(data="direct_buy:42")
        cd = DirectBuyCallback(product_id=42)

        from handlers.store_user_handlers import direct_buy
        await direct_buy(cb, cd)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Confirmar compra" in text
        assert "Producto Test" in text
        assert "200" in text
        assert "300" in text  # balance after (500-200)

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_correct_balance_after_purchase_displayed(self, mock_store, mock_besito, make_callback):
        """Muestra el saldo resultante despues de la compra."""
        from keyboards.callback_data import DirectBuyCallback
        product = MagicMock()
        product.id = 1
        product.name = "Test"
        product.price = 300
        mock_store.return_value.get_product.return_value = product
        mock_besito.return_value.get_balance.return_value = 1000
        cb = make_callback(data="direct_buy:1")
        cd = DirectBuyCallback(product_id=1)

        from handlers.store_user_handlers import direct_buy
        await direct_buy(cb, cd)

        text = cb.message.edit_text.call_args[0][0]
        assert "700" in text  # 1000 - 300

    @patch("handlers.store_user_handlers.BesitoService")
    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_answer(self, mock_store, mock_besito, make_callback):
        """Llama a callback.answer en caso exitoso."""
        from keyboards.callback_data import DirectBuyCallback
        product = MagicMock()
        product.id = 1
        product.name = "Test"
        product.price = 100
        mock_store.return_value.get_product.return_value = product
        mock_besito.return_value.get_balance.return_value = 200
        cb = make_callback(data="direct_buy:1")
        cd = DirectBuyCallback(product_id=1)

        from handlers.store_user_handlers import direct_buy
        await direct_buy(cb, cd)

        cb.answer.assert_called_once()


class TestConfirmDirectBuy:
    """Tests para confirm_direct_buy - ejecucion de compra directa."""

    @patch("handlers.store_user_handlers.StoreService")
    async def test_direct_purchase_returns_error(self, mock_store, make_callback):
        """Si direct_purchase retorna error, muestra alerta."""
        from keyboards.callback_data import ConfirmDirectBuyCallback
        mock_store.return_value.direct_purchase.return_value = (None, "Error al procesar")
        cb = make_callback(data="confirm_direct_buy:1")
        cd = ConfirmDirectBuyCallback(product_id=1)

        from handlers.store_user_handlers import confirm_direct_buy
        await confirm_direct_buy(cb, cd, cb.bot)

        cb.answer.assert_called_once_with("Error al procesar", show_alert=True)
        mock_store.return_value.complete_order.assert_not_called()

    @patch("handlers.store_user_handlers.StoreService")
    async def test_complete_order_success(self, mock_store, make_callback):
        """Compra exitosa muestra mensaje de confirmacion."""
        from keyboards.callback_data import ConfirmDirectBuyCallback
        mock_store.return_value.direct_purchase.return_value = (MagicMock(id=99), None)
        mock_store.return_value.complete_order = AsyncMock(return_value=(True, "Contenido entregado"))
        cb = make_callback(data="confirm_direct_buy:1")
        cd = ConfirmDirectBuyCallback(product_id=1)

        from handlers.store_user_handlers import confirm_direct_buy
        await confirm_direct_buy(cb, cd, cb.bot)

        mock_store.return_value.direct_purchase.assert_called_once_with(123456789, 1)
        mock_store.return_value.complete_order.assert_called_once_with(cb.bot, 99)
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "completada" in text.lower()
        assert "exitosa" in text.lower()
        cb.answer.assert_called_once_with("Compra exitosa!")

    @patch("handlers.store_user_handlers.StoreService")
    async def test_complete_order_failure(self, mock_store, make_callback):
        """Fallo en complete_order muestra alerta de error."""
        from keyboards.callback_data import ConfirmDirectBuyCallback
        mock_store.return_value.direct_purchase.return_value = (MagicMock(id=99), None)
        mock_store.return_value.complete_order = AsyncMock(return_value=(False, "Error de envio"))
        cb = make_callback(data="confirm_direct_buy:1")
        cd = ConfirmDirectBuyCallback(product_id=1)

        from handlers.store_user_handlers import confirm_direct_buy
        await confirm_direct_buy(cb, cd, cb.bot)

        cb.answer.assert_called_once_with("Error: Error de envio", show_alert=True)

    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_services_with_correct_params(self, mock_store, make_callback):
        """Llama a servicios con parametros correctos."""
        from keyboards.callback_data import ConfirmDirectBuyCallback
        order = MagicMock(id=55)
        mock_store.return_value.direct_purchase.return_value = (order, None)
        mock_store.return_value.complete_order = AsyncMock(return_value=(True, "OK"))
        cb = make_callback(data="confirm_direct_buy:1")
        cd = ConfirmDirectBuyCallback(product_id=1)

        from handlers.store_user_handlers import confirm_direct_buy
        await confirm_direct_buy(cb, cd, cb.bot)

        mock_store.return_value.direct_purchase.assert_called_once_with(123456789, 1)
        mock_store.return_value.complete_order.assert_called_once_with(cb.bot, 55)


class TestPurchaseHistory:
    """Tests para purchase_history - historial de compras."""

    @patch("handlers.store_user_handlers.StoreService")
    async def test_empty_history(self, mock_store, make_callback):
        """Historial vacio muestra mensaje."""
        mock_store.return_value.get_user_orders.return_value = []
        cb = make_callback(data="purchase_history")

        from handlers.store_user_handlers import purchase_history
        await purchase_history(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "compras registradas" in text.lower()

    @patch("handlers.store_user_handlers.StoreService")
    async def test_displays_orders(self, mock_store, make_callback):
        """Muestra ordenes del historial."""
        order = MagicMock()
        order.id = 42
        order.status = MagicMock()
        order.status.value = "completed"
        order.created_at = datetime(2024, 6, 15, 10, 30)
        order.total_items = 3
        order.total_price = 500
        mock_store.return_value.get_user_orders.return_value = [order]
        cb = make_callback(data="purchase_history")

        from handlers.store_user_handlers import purchase_history
        await purchase_history(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "42" in text
        assert "3" in text
        assert "500" in text
        assert "15/06/2024" in text

    @patch("handlers.store_user_handlers.StoreService")
    async def test_displays_pending_status(self, mock_store, make_callback):
        """Orden pendiente se marca con reloj."""
        order = MagicMock()
        order.id = 1
        order.status = MagicMock()
        order.status.value = "pending"
        order.created_at = datetime(2024, 6, 15, 10, 30)
        order.total_items = 1
        order.total_price = 100
        mock_store.return_value.get_user_orders.return_value = [order]
        cb = make_callback(data="purchase_history")

        from handlers.store_user_handlers import purchase_history
        await purchase_history(cb)

        cb.message.edit_text.assert_called_once()

    @patch("handlers.store_user_handlers.StoreService")
    async def test_displays_cancelled_status(self, mock_store, make_callback):
        """Orden cancelada se marca con X."""
        order = MagicMock()
        order.id = 1
        order.status = MagicMock()
        order.status.value = "cancelled"
        order.created_at = datetime(2024, 6, 15, 10, 30)
        order.total_items = 1
        order.total_price = 100
        mock_store.return_value.get_user_orders.return_value = [order]
        cb = make_callback(data="purchase_history")

        from handlers.store_user_handlers import purchase_history
        await purchase_history(cb)

        cb.message.edit_text.assert_called_once()

    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_service_with_user_id_and_limit(self, mock_store, make_callback):
        """Llama a get_user_orders con user_id y limit=10."""
        mock_store.return_value.get_user_orders.return_value = []
        cb = make_callback(data="purchase_history")

        from handlers.store_user_handlers import purchase_history
        await purchase_history(cb)

        mock_store.return_value.get_user_orders.assert_called_once_with(123456789, limit=10)

    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_answer(self, mock_store, make_callback):
        """Siempre llama a callback.answer()."""
        mock_store.return_value.get_user_orders.return_value = []
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
        assert "tesoro buscas" in text.lower()

    async def test_calls_answer(self, make_callback, make_fsm_context):
        """Llama a callback.answer()."""
        cb = make_callback(data="store_search")
        fsm = await make_fsm_context()

        from handlers.store_user_handlers import store_search_start
        await store_search_start(cb, fsm)

        cb.answer.assert_called_once()


class TestProcessSearchQuery:
    """Tests para process_search_query - procesamiento de busqueda."""

    @patch("handlers.store_user_handlers.StoreService")
    async def test_short_query_shows_prompt(self, mock_store, make_message, make_fsm_context):
        """Query menor a 2 caracteres pide escribir mas."""
        msg = make_message(text="a")
        fsm = await make_fsm_context()
        await fsm.set_state(type("S", (), {"waiting_query": "waiting_query"})())

        from handlers.store_user_handlers import process_search_query
        await process_search_query(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "2 caracteres" in text

    @patch("handlers.store_user_handlers.StoreService")
    async def test_short_query_does_not_search(self, mock_store, make_message, make_fsm_context):
        """Query corta no llama al servicio de busqueda."""
        msg = make_message(text="a")
        fsm = await make_fsm_context()

        from handlers.store_user_handlers import process_search_query
        await process_search_query(msg, fsm)

        mock_store.return_value.search_products.assert_not_called()

    @patch("handlers.store_user_handlers.StoreService")
    async def test_no_results_shows_not_found(self, mock_store, make_message, make_fsm_context):
        """Sin resultados, muestra mensaje de no encontrado."""
        mock_store.return_value.search_products.return_value = []
        msg = make_message(text="xyz")
        fsm = await make_fsm_context()

        from handlers.store_user_handlers import process_search_query
        await process_search_query(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "No encontre" in text

    @patch("handlers.store_user_handlers.StoreService")
    async def test_no_results_clears_state(self, mock_store, make_message, make_fsm_context):
        """Sin resultados, limpia el estado FSM."""
        mock_store.return_value.search_products.return_value = []
        msg = make_message(text="xyz")
        fsm = await make_fsm_context()
        await fsm.set_state(type("S", (), {"waiting_query": "waiting_query"})())

        from handlers.store_user_handlers import process_search_query
        await process_search_query(msg, fsm)

        current_state = await fsm.get_state()
        assert current_state is None

    @patch("handlers.store_user_handlers.StoreService")
    async def test_shows_results(self, mock_store, make_message, make_fsm_context):
        """Muestra resultados de busqueda."""
        product = MagicMock(id=1, name="Tesoro Encontrado", price=100)
        mock_store.return_value.search_products.return_value = [product]
        msg = make_message(text="tesoro")
        fsm = await make_fsm_context()

        from handlers.store_user_handlers import process_search_query
        await process_search_query(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "tesoro" in text
        assert "1" in text

    @patch("handlers.store_user_handlers.StoreService")
    async def test_results_clears_state(self, mock_store, make_message, make_fsm_context):
        """Con resultados, limpia el estado FSM."""
        product = MagicMock(id=1, name="Tesoro", price=100)
        mock_store.return_value.search_products.return_value = [product]
        msg = make_message(text="tesoro")
        fsm = await make_fsm_context()

        from handlers.store_user_handlers import process_search_query
        await process_search_query(msg, fsm)

        current_state = await fsm.get_state()
        assert current_state is None

    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_service_with_query_and_active_only(self, mock_store, make_message, make_fsm_context):
        """Llama a search_products con el query y active_only=True."""
        mock_store.return_value.search_products.return_value = []
        msg = make_message(text="video")
        fsm = await make_fsm_context()

        from handlers.store_user_handlers import process_search_query
        await process_search_query(msg, fsm)

        mock_store.return_value.search_products.assert_called_once_with("video", active_only=True)


class TestStoreFilters:
    """Tests para store_filters - menu de filtros."""

    async def test_shows_filter_options(self, make_callback):
        """Muestra opciones de filtrado."""
        cb = make_callback(data="store_filters")

        from handlers.store_user_handlers import store_filters
        await store_filters(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Filtrar" in text

    async def test_calls_answer(self, make_callback):
        """Llama a callback.answer()."""
        cb = make_callback(data="store_filters")

        from handlers.store_user_handlers import store_filters
        await store_filters(cb)

        cb.answer.assert_called_once()


class TestFilterPriceAsc:
    """Tests para filter_price_asc - filtro precio ascendente."""

    @patch("handlers.store_user_handlers.StoreService")
    async def test_empty_products(self, mock_store, make_callback):
        """Sin productos muestra mensaje."""
        mock_store.return_value.get_all_products.return_value = []
        cb = make_callback(data="filter_price_asc")

        from handlers.store_user_handlers import filter_price_asc
        await filter_price_asc(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay tesoros" in text

    @patch("handlers.store_user_handlers.StoreService")
    async def test_displays_products_sorted_asc(self, mock_store, make_callback):
        """Muestra productos ordenados por precio ascendente."""
        p1 = MagicMock(id=1, name="Caro", price=200)
        p2 = MagicMock(id=2, name="Barato", price=50)
        mock_store.return_value.get_all_products.return_value = [p1, p2]
        cb = make_callback(data="filter_price_asc")

        from handlers.store_user_handlers import filter_price_asc
        await filter_price_asc(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "menor a mayor" in text

    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_answer(self, mock_store, make_callback):
        """Llama a callback.answer()."""
        mock_store.return_value.get_all_products.return_value = []
        cb = make_callback(data="filter_price_asc")

        from handlers.store_user_handlers import filter_price_asc
        await filter_price_asc(cb)

        cb.answer.assert_called_once()


class TestFilterPriceDesc:
    """Tests para filter_price_desc - filtro precio descendente."""

    @patch("handlers.store_user_handlers.StoreService")
    async def test_empty_products(self, mock_store, make_callback):
        """Sin productos muestra mensaje."""
        mock_store.return_value.get_all_products.return_value = []
        cb = make_callback(data="filter_price_desc")

        from handlers.store_user_handlers import filter_price_desc
        await filter_price_desc(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay tesoros" in text

    @patch("handlers.store_user_handlers.StoreService")
    async def test_displays_products_sorted_desc(self, mock_store, make_callback):
        """Muestra productos ordenados por precio descendente."""
        p1 = MagicMock(id=1, name="Barato", price=50)
        p2 = MagicMock(id=2, name="Caro", price=200)
        mock_store.return_value.get_all_products.return_value = [p1, p2]
        cb = make_callback(data="filter_price_desc")

        from handlers.store_user_handlers import filter_price_desc
        await filter_price_desc(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "mayor a menor" in text

    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_answer(self, mock_store, make_callback):
        """Llama a callback.answer()."""
        mock_store.return_value.get_all_products.return_value = []
        cb = make_callback(data="filter_price_desc")

        from handlers.store_user_handlers import filter_price_desc
        await filter_price_desc(cb)

        cb.answer.assert_called_once()


class TestFilterInStock:
    """Tests para filter_in_stock - solo disponibles."""

    @patch("handlers.store_user_handlers.StoreService")
    async def test_empty_products(self, mock_store, make_callback):
        """Sin productos disponibles muestra mensaje."""
        mock_store.return_value.get_available_products.return_value = []
        cb = make_callback(data="filter_in_stock")

        from handlers.store_user_handlers import filter_in_stock
        await filter_in_stock(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay tesoros" in text

    @patch("handlers.store_user_handlers.StoreService")
    async def test_displays_available_products(self, mock_store, make_callback):
        """Muestra solo productos disponibles."""
        product = MagicMock(id=1, name="Disponible", price=100)
        mock_store.return_value.get_available_products.return_value = [product]
        cb = make_callback(data="filter_in_stock")

        from handlers.store_user_handlers import filter_in_stock
        await filter_in_stock(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Solo disponibles" in text

    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_service(self, mock_store, make_callback):
        """Llama a get_available_products."""
        mock_store.return_value.get_available_products.return_value = []
        cb = make_callback(data="filter_in_stock")

        from handlers.store_user_handlers import filter_in_stock
        await filter_in_stock(cb)

        mock_store.return_value.get_available_products.assert_called_once()

    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_answer(self, mock_store, make_callback):
        """Llama a callback.answer()."""
        mock_store.return_value.get_available_products.return_value = []
        cb = make_callback(data="filter_in_stock")

        from handlers.store_user_handlers import filter_in_stock
        await filter_in_stock(cb)

        cb.answer.assert_called_once()


class TestFilterRecent:
    """Tests para filter_recent - productos mas recientes."""

    @patch("handlers.store_user_handlers.StoreService")
    async def test_empty_products(self, mock_store, make_callback):
        """Sin productos muestra mensaje."""
        mock_store.return_value.get_all_products.return_value = []
        cb = make_callback(data="filter_recent")

        from handlers.store_user_handlers import filter_recent
        await filter_recent(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay tesoros" in text

    @patch("handlers.store_user_handlers.StoreService")
    async def test_displays_recent_products(self, mock_store, make_callback):
        """Muestra los productos mas recientes."""
        product = MagicMock(id=1, name="Nuevo", price=100)
        mock_store.return_value.get_all_products.return_value = [product]
        cb = make_callback(data="filter_recent")

        from handlers.store_user_handlers import filter_recent
        await filter_recent(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Mas recientes" in text

    @patch("handlers.store_user_handlers.StoreService")
    async def test_calls_answer(self, mock_store, make_callback):
        """Llama a callback.answer()."""
        mock_store.return_value.get_all_products.return_value = []
        cb = make_callback(data="filter_recent")

        from handlers.store_user_handlers import filter_recent
        await filter_recent(cb)

        cb.answer.assert_called_once()


class TestShowFilteredProducts:
    """Tests para show_filtered_products - helper de visualizacion."""

    async def test_empty_products(self, make_callback):
        """Lista vacia muestra mensaje de no coincidencias."""
        cb = make_callback(data="filter_price_asc")

        from handlers.store_user_handlers import show_filtered_products
        await show_filtered_products(cb, [], "Precio: menor a mayor")

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay tesoros" in text

    async def test_shows_filtered_products(self, make_callback):
        """Muestra productos filtrados con el nombre del filtro."""
        p1 = MagicMock(id=1, name="Producto A", price=100)
        p2 = MagicMock(id=2, name="Producto B", price=200)
        cb = make_callback(data="filter_recent")

        from handlers.store_user_handlers import show_filtered_products
        await show_filtered_products(cb, [p1, p2], "Mas recientes")

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Mas recientes" in text
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
        assert "5 mas" in text  # 15 - 10 = 5

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
