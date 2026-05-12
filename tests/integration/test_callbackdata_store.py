"""
Tests de integración para callbacks Store migrateados.

Verifica que los CallbackData migrados funcionan correctamente:
- ProductDetailCallback
- DirectBuyCallback
- ConfirmDirectBuyCallback
- StoreCategoryCallback
- ProductPreviewCallback
"""
import pytest
from unittest.mock import MagicMock

from keyboards.callback_data import (
    ProductDetailCallback,
    DirectBuyCallback,
    ConfirmDirectBuyCallback,
    StoreCategoryCallback,
    ProductPreviewCallback,
)


class TestProductDetailCallback:
    """Tests para ProductDetailCallback."""

    def test_callback_packs_correctly(self):
        """ProductDetailCallback.pack() genera el string esperado."""
        product_id = 42
        callback = ProductDetailCallback(product_id=product_id)
        packed = callback.pack()

        # Formato esperado: "product_detail:42"
        assert packed == "product_detail:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes product_id."""
        for product_id in [1, 10, 100, 999]:
            callback = ProductDetailCallback(product_id=product_id)
            packed = callback.pack()
            assert packed == f"product_detail:{product_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable (API pública de aiogram)."""
        callback_filter = ProductDetailCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = ProductDetailCallback(product_id=123)
        packed = callback.pack()

        # Parse manual para verificar
        prefix, product_id_str = packed.split(":")
        assert prefix == "product_detail"
        assert int(product_id_str) == 123


class TestDirectBuyCallback:
    """Tests para DirectBuyCallback."""

    def test_callback_packs_correctly(self):
        """DirectBuyCallback.pack() genera el string esperado."""
        product_id = 42
        callback = DirectBuyCallback(product_id=product_id)
        packed = callback.pack()

        # Formato esperado: "direct_buy:42"
        assert packed == "direct_buy:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes product_id."""
        for product_id in [1, 10, 100, 999]:
            callback = DirectBuyCallback(product_id=product_id)
            packed = callback.pack()
            assert packed == f"direct_buy:{product_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = DirectBuyCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = DirectBuyCallback(product_id=456)
        packed = callback.pack()

        prefix, product_id_str = packed.split(":")
        assert prefix == "direct_buy"
        assert int(product_id_str) == 456


class TestConfirmDirectBuyCallback:
    """Tests para ConfirmDirectBuyCallback."""

    def test_callback_packs_correctly(self):
        """ConfirmDirectBuyCallback.pack() genera el string esperado."""
        product_id = 42
        callback = ConfirmDirectBuyCallback(product_id=product_id)
        packed = callback.pack()

        # Formato esperado: "confirm_direct_buy:42"
        assert packed == "confirm_direct_buy:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes product_id."""
        for product_id in [1, 10, 100, 999]:
            callback = ConfirmDirectBuyCallback(product_id=product_id)
            packed = callback.pack()
            assert packed == f"confirm_direct_buy:{product_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = ConfirmDirectBuyCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = ConfirmDirectBuyCallback(product_id=789)
        packed = callback.pack()

        prefix, product_id_str = packed.split(":")
        assert prefix == "confirm_direct_buy"
        assert int(product_id_str) == 789


class TestStoreCategoryCallback:
    """Tests para StoreCategoryCallback."""

    def test_callback_packs_correctly(self):
        """StoreCategoryCallback.pack() genera el string esperado."""
        category_id = 1
        callback = StoreCategoryCallback(category_id=category_id)
        packed = callback.pack()

        # Formato esperado: "store_category:1"
        assert packed == "store_category:1"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes category_id."""
        for category_id in [1, 5, 20, 100]:
            callback = StoreCategoryCallback(category_id=category_id)
            packed = callback.pack()
            assert packed == f"store_category:{category_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = StoreCategoryCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = StoreCategoryCallback(category_id=3)
        packed = callback.pack()

        prefix, category_id_str = packed.split(":")
        assert prefix == "store_category"
        assert int(category_id_str) == 3


class TestProductPreviewCallback:
    """Tests para ProductPreviewCallback."""

    def test_callback_packs_correctly(self):
        """ProductPreviewCallback.pack() genera el string esperado."""
        product_id = 42
        callback = ProductPreviewCallback(product_id=product_id)
        packed = callback.pack()

        # Formato esperado: "product_preview:42"
        assert packed == "product_preview:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes product_id."""
        for product_id in [1, 10, 100, 999]:
            callback = ProductPreviewCallback(product_id=product_id)
            packed = callback.pack()
            assert packed == f"product_preview:{product_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = ProductPreviewCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = ProductPreviewCallback(product_id=555)
        packed = callback.pack()

        prefix, product_id_str = packed.split(":")
        assert prefix == "product_preview"
        assert int(product_id_str) == 555


class TestCallbackNoCollisions:
    """Tests para verificar que no hay colisiones entre callbacks."""

    def test_no_collision_product_detail_vs_direct_buy(self):
        """ProductDetail y DirectBuy no collsionan."""
        product_id = 1
        pd_cb = ProductDetailCallback(product_id=product_id)
        db_cb = DirectBuyCallback(product_id=product_id)

        assert pd_cb.pack() != db_cb.pack()
        assert "product_detail" in pd_cb.pack()
        assert "direct_buy" in db_cb.pack()

    def test_no_collision_direct_buy_vs_confirm(self):
        """DirectBuy y ConfirmDirectBuy no collisionan."""
        product_id = 1
        db_cb = DirectBuyCallback(product_id=product_id)
        confirm_cb = ConfirmDirectBuyCallback(product_id=product_id)

        assert db_cb.pack() != confirm_cb.pack()
        assert "direct_buy" in db_cb.pack()
        assert "confirm_direct_buy" in confirm_cb.pack()

    def test_no_collision_detail_vs_preview(self):
        """ProductDetail y ProductPreview no collisionan."""
        product_id = 1
        detail_cb = ProductDetailCallback(product_id=product_id)
        preview_cb = ProductPreviewCallback(product_id=product_id)

        assert detail_cb.pack() != preview_cb.pack()
        assert "product_detail" in detail_cb.pack()
        assert "product_preview" in preview_cb.pack()

    def test_no_collision_category(self):
        """StoreCategory es único."""
        category_id = 1
        category_cb = StoreCategoryCallback(category_id=category_id)

        # No debe igualar ningún otro callback
        assert "store_category" in category_cb.pack()
        assert "store_category" not in ProductDetailCallback(product_id=1).pack()


class TestCallbackIntegrationWithProducts:
    """Tests de integración con productos."""

    def test_product_detail_callback_id_matches_product(self, db_session, sample_store_product):
        """ProductDetailCallback usa el ID correcto del producto."""
        callback = ProductDetailCallback(product_id=sample_store_product.id)
        packed = callback.pack()

        assert f"product_detail:{sample_store_product.id}" == packed

    def test_direct_buy_callback_id_matches_product(self, db_session, sample_store_product):
        """DirectBuyCallback usa el ID correcto del producto."""
        callback = DirectBuyCallback(product_id=sample_store_product.id)
        packed = callback.pack()

        assert f"direct_buy:{sample_store_product.id}" == packed

    def test_confirm_direct_buy_callback_id_matches_product(self, db_session, sample_store_product):
        """ConfirmDirectBuyCallback usa el ID correcto del producto."""
        callback = ConfirmDirectBuyCallback(product_id=sample_store_product.id)
        packed = callback.pack()

        assert f"confirm_direct_buy:{sample_store_product.id}" == packed

    def test_product_preview_callback_id_matches_product(self, db_session, sample_store_product):
        """ProductPreviewCallback usa el ID correcto del producto."""
        callback = ProductPreviewCallback(product_id=sample_store_product.id)
        packed = callback.pack()

        assert f"product_preview:{sample_store_product.id}" == packed


class TestFullStoreFlow:
    """Tests del flujo completo de compra."""

    def test_full_store_flow_detail_to_buy(self, db_session, sample_store_product):
        """Flujo: Detail → DirectBuy → Confirm."""
        product_id = sample_store_product.id

        # Step 1: Ver detalle del producto
        detail_callback = ProductDetailCallback(product_id=product_id)
        detail_packed = detail_callback.pack()

        # Step 2: Hacer click en comprar (sin confirmado)
        buy_callback = DirectBuyCallback(product_id=product_id)
        buy_packed = buy_callback.pack()

        # Step 3: Confirmar la compra
        confirm_callback = ConfirmDirectBuyCallback(product_id=product_id)
        confirm_packed = confirm_callback.pack()

        # Verificar formato correcto
        assert detail_packed == f"product_detail:{product_id}"
        assert buy_packed == f"direct_buy:{product_id}"
        assert confirm_packed == f"confirm_direct_buy:{product_id}"

    def test_full_flow_with_preview(self, db_session, sample_store_product):
        """Flujo completo con preview."""
        product_id = sample_store_product.id

        # Detail → Preview → Buy → Confirm
        detail_cb = ProductDetailCallback(product_id=product_id)
        preview_cb = ProductPreviewCallback(product_id=product_id)
        buy_cb = DirectBuyCallback(product_id=product_id)
        confirm_cb = ConfirmDirectBuyCallback(product_id=product_id)

        # Todos contienen el mismo product_id
        assert detail_cb.pack().split(":")[1] == str(product_id)
        assert preview_cb.pack().split(":")[1] == str(product_id)
        assert buy_cb.pack().split(":")[1] == str(product_id)
        assert confirm_cb.pack().split(":")[1] == str(product_id)

    def test_store_category_independent_flow(self, db_session):
        """Flujo de categoría es independiente."""
        category_id = 42

        category_cb = StoreCategoryCallback(category_id=category_id)
        category_packed = category_cb.pack()

        assert category_packed == f"store_category:{category_id}"

    def test_callback_chain_in_store_flow(self, db_session, sample_store_product):
        """Callback chain en el flujo de tienda."""
        product_id = sample_store_product.id
        category_id = 1

        # 1. Ver categorías
        category_packed = StoreCategoryCallback(category_id=category_id).pack()

        # 2. Ver detalle de producto
        detail_packed = ProductDetailCallback(product_id=product_id).pack()

        # 3. Preview
        preview_packed = ProductPreviewCallback(product_id=product_id).pack()

        # 4. Comprar
        buy_packed = DirectBuyCallback(product_id=product_id).pack()

        # 5. Confirmar
        confirm_packed = ConfirmDirectBuyCallback(product_id=product_id).pack()

        # Verificar todas las transiciones
        assert "store_category" in category_packed
        assert "product_detail" in detail_packed
        assert "product_preview" in preview_packed
        assert "direct_buy" in buy_packed
        assert "confirm_direct_buy" in confirm_packed


class TestCallbackDataFormat:
    """Tests del formato exacto."""

    def test_product_detail_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = ProductDetailCallback(product_id=1)
        packed = cb.pack()
        assert packed == "product_detail:1"

    def test_direct_buy_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = DirectBuyCallback(product_id=1)
        packed = cb.pack()
        assert packed == "direct_buy:1"

    def test_confirm_direct_buy_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = ConfirmDirectBuyCallback(product_id=1)
        packed = cb.pack()
        assert packed == "confirm_direct_buy:1"

    def test_store_category_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = StoreCategoryCallback(category_id=1)
        packed = cb.pack()
        assert packed == "store_category:1"

    def test_product_preview_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = ProductPreviewCallback(product_id=1)
        packed = cb.pack()
        assert packed == "product_preview:1"