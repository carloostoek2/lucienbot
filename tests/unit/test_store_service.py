"""
Tests unitarios para StoreService.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from services.store_service import StoreService
from models.models import StoreProduct, CartItem, Order, OrderItem, OrderStatus, Package, BesitoBalance


@pytest.mark.unit
class TestStoreService:
    def test_create_product(self, db_session):
        service = StoreService(db_session)
        pkg = Package(name="Test Package", description="Desc", is_active=True)
        db_session.add(pkg)
        db_session.commit()
        db_session.refresh(pkg)
        product = service.create_product(name="Test", description="Desc", package_id=pkg.id, price=100)
        assert product.name == "Test"
        assert product.stock == -1

    def test_get_product(self, db_session, sample_store_product):
        service = StoreService(db_session)
        p = service.get_product(sample_store_product.id)
        assert p is not None
        assert p.id == sample_store_product.id

    def test_get_product_not_found(self, db_session):
        service = StoreService(db_session)
        p = service.get_product(99999)
        assert p is None

    def test_get_available_products(self, db_session, sample_store_product):
        service = StoreService(db_session)
        # Make one unavailable
        sample_store_product.stock = 0
        db_session.commit()
        available = service.get_available_products()
        assert not any(p.id == sample_store_product.id for p in available)

    def test_update_product(self, db_session, sample_store_product):
        service = StoreService(db_session)
        result = service.update_product(sample_store_product.id, name="Updated", price=200)
        assert result is True
        updated = service.get_product(sample_store_product.id)
        assert updated.name == "Updated"
        assert updated.price == 200

    def test_delete_product(self, db_session, sample_store_product):
        service = StoreService(db_session)
        product_id = sample_store_product.id
        result = service.delete_product(product_id)
        assert result is True
        assert service.get_product(product_id) is None

    def test_add_to_cart(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        success, msg = service.add_to_cart(sample_user.id, sample_store_product.id, quantity=2)
        assert success is True
        items = service.get_cart_items(sample_user.id)
        assert any(i.product_id == sample_store_product.id and i.quantity == 2 for i in items)

    def test_add_to_cart_existing_updates_quantity(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=1)
        success, msg = service.add_to_cart(sample_user.id, sample_store_product.id, quantity=2)
        assert success is True
        items = service.get_cart_items(sample_user.id)
        assert items[0].quantity == 3

    def test_get_cart_total(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=2)
        total = service.get_cart_total(sample_user.id)
        assert total == sample_store_product.price * 2

    def test_remove_from_cart(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        service.add_to_cart(sample_user.id, sample_store_product.id)
        items = service.get_cart_items(sample_user.id)
        result = service.remove_from_cart(sample_user.id, items[0].id)
        assert result is True
        assert len(service.get_cart_items(sample_user.id)) == 0

    def test_create_order_empty_cart(self, db_session, sample_user):
        service = StoreService(db_session)
        order, error = service.create_order(sample_user.id)
        assert order is None
        assert "vacio" in error.lower() or "empty" in error.lower()

    def test_create_order_insufficient_stock(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        sample_store_product.stock = 1
        db_session.commit()
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=5)
        order, error = service.create_order(sample_user.id)
        assert order is None
        assert "stock" in error.lower()

    def test_create_order_insufficient_balance(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        balance = BesitoBalance(user_id=sample_user.id, balance=0, total_earned=0, total_spent=0)
        db_session.add(balance)
        db_session.commit()
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=1)
        order, error = service.create_order(sample_user.id)
        assert order is None
        assert "saldo" in error.lower() or "balance" in error.lower() or "insufficient" in error.lower()

    def test_create_order_success(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        balance = BesitoBalance(user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0)
        db_session.add(balance)
        db_session.commit()
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=2)
        order, error = service.create_order(sample_user.id)
        assert order is not None
        assert order.status == OrderStatus.PENDING
        assert order.total_price == sample_store_product.price * 2
        assert len(order.items) == 1

    @pytest.mark.asyncio
    async def test_complete_order_success(self, db_session, sample_user, sample_store_product, mock_bot):
        service = StoreService(db_session)
        balance = BesitoBalance(user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0)
        db_session.add(balance)
        db_session.commit()
        # Set finite stock
        sample_store_product.stock = 5
        db_session.commit()
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=2)
        order, _ = service.create_order(sample_user.id)
        success, msg = await service.complete_order(mock_bot, order.id)
        assert success is True
        db_session.refresh(order)
        assert order.status == OrderStatus.COMPLETED
        db_session.refresh(sample_store_product)
        assert sample_store_product.stock == 3
        assert service.besito_service.get_balance(sample_user.id) == 9999 - order.total_price

    @pytest.mark.asyncio
    async def test_complete_order_unlimited_stock(self, db_session, sample_user, sample_store_product, mock_bot):
        service = StoreService(db_session)
        balance = BesitoBalance(user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0)
        db_session.add(balance)
        db_session.commit()
        sample_store_product.stock = -1
        db_session.commit()
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=1)
        order, _ = service.create_order(sample_user.id)
        success, msg = await service.complete_order(mock_bot, order.id)
        assert success is True
        db_session.refresh(sample_store_product)
        assert sample_store_product.stock == -1

    @pytest.mark.asyncio
    async def test_complete_order_already_processed(self, db_session, sample_user, sample_store_product, mock_bot):
        service = StoreService(db_session)
        balance = BesitoBalance(user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0)
        db_session.add(balance)
        db_session.commit()
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=1)
        order, _ = service.create_order(sample_user.id)
        await service.complete_order(mock_bot, order.id)
        success, msg = await service.complete_order(mock_bot, order.id)
        assert success is False

    def test_cancel_order(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        balance = BesitoBalance(user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0)
        db_session.add(balance)
        db_session.commit()
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=1)
        order, _ = service.create_order(sample_user.id)
        result = service.cancel_order(order.id)
        assert result is True
        db_session.refresh(order)
        assert order.status == OrderStatus.CANCELLED

    def test_get_store_stats(self, db_session, sample_store_product):
        service = StoreService(db_session)
        stats = service.get_store_stats()
        assert stats['total_products'] >= 1
        assert 'available_products' in stats
        assert 'total_orders' in stats

    def test_get_all_products(self, db_session, sample_store_product):
        service = StoreService(db_session)
        all_products = service.get_all_products(active_only=False)
        assert len(all_products) >= 1
        assert any(p.id == sample_store_product.id for p in all_products)

    def test_get_all_products_active_only(self, db_session, sample_package):
        service = StoreService(db_session)
        inactive = StoreProduct(name="Inactive", description="Desc", package_id=sample_package.id, price=100, is_active=False)
        db_session.add(inactive)
        db_session.commit()
        active_products = service.get_all_products(active_only=True)
        assert not any(p.id == inactive.id for p in active_products)

    def test_search_products(self, db_session, sample_store_product):
        service = StoreService(db_session)
        results = service.search_products("Test")
        assert any(p.id == sample_store_product.id for p in results)
        results = service.search_products("xyznonexistent")
        assert len(results) == 0

    def test_get_products_by_price_range(self, db_session, sample_package):
        service = StoreService(db_session)
        cheap = service.create_product(name="Cheap", description="Desc", package_id=sample_package.id, price=50)
        expensive = service.create_product(name="Expensive", description="Desc", package_id=sample_package.id, price=500)
        mid_range = service.get_products_by_price_range(min_price=40, max_price=100)
        assert any(p.id == cheap.id for p in mid_range)
        assert not any(p.id == expensive.id for p in mid_range)

    def test_filter_products(self, db_session, sample_store_product, sample_package):
        service = StoreService(db_session)
        filtered = service.filter_products(min_price=50, max_price=200)
        assert any(p.id == sample_store_product.id for p in filtered)
        filtered = service.filter_products(min_price=500)
        assert not any(p.id == sample_store_product.id for p in filtered)

    def test_update_cart_quantity(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=1)
        items = service.get_cart_items(sample_user.id)
        result = service.update_cart_quantity(sample_user.id, items[0].id, quantity=5)
        assert result is True
        items = service.get_cart_items(sample_user.id)
        assert items[0].quantity == 5

    def test_update_cart_quantity_to_zero_removes(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=1)
        items = service.get_cart_items(sample_user.id)
        result = service.update_cart_quantity(sample_user.id, items[0].id, quantity=0)
        assert result is True
        assert len(service.get_cart_items(sample_user.id)) == 0

    def test_clear_cart(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=2)
        result = service.clear_cart(sample_user.id)
        assert result is True
        assert len(service.get_cart_items(sample_user.id)) == 0

    def test_get_cart_items_count(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        assert service.get_cart_items_count(sample_user.id) == 0
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=3)
        assert service.get_cart_items_count(sample_user.id) == 1

    def test_direct_purchase_success(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        balance = BesitoBalance(user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0)
        db_session.add(balance)
        db_session.commit()
        order, error = service.direct_purchase(sample_user.id, sample_store_product.id)
        assert order is not None
        assert error is None
        assert order.status == OrderStatus.PENDING
        assert order.total_price == sample_store_product.price

    def test_direct_purchase_product_not_found(self, db_session, sample_user):
        service = StoreService(db_session)
        order, error = service.direct_purchase(sample_user.id, 99999)
        assert order is None
        assert error is not None

    def test_direct_purchase_unavailable(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        sample_store_product.is_active = False
        db_session.commit()
        order, error = service.direct_purchase(sample_user.id, sample_store_product.id)
        assert order is None
        assert error is not None

    def test_direct_purchase_insufficient_stock(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        sample_store_product.stock = 0
        db_session.commit()
        order, error = service.direct_purchase(sample_user.id, sample_store_product.id)
        assert order is None
        # Cuando stock es 0, el producto no está disponible
        assert "disponible" in error.lower() or "stock" in error.lower()

    def test_direct_purchase_insufficient_balance(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        balance = BesitoBalance(user_id=sample_user.id, balance=0, total_earned=0, total_spent=0)
        db_session.add(balance)
        db_session.commit()
        order, error = service.direct_purchase(sample_user.id, sample_store_product.id)
        assert order is None
        assert "saldo" in error.lower() or "balance" in error.lower()

    def test_get_order(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        balance = BesitoBalance(user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0)
        db_session.add(balance)
        db_session.commit()
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=1)
        created_order, _ = service.create_order(sample_user.id)
        retrieved = service.get_order(created_order.id)
        assert retrieved is not None
        assert retrieved.id == created_order.id

    def test_get_user_orders(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        balance = BesitoBalance(user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0)
        db_session.add(balance)
        db_session.commit()
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=1)
        order, _ = service.create_order(sample_user.id)
        orders = service.get_user_orders(sample_user.id)
        assert len(orders) >= 1
        assert any(o.id == order.id for o in orders)

    def test_get_low_stock_products(self, db_session, sample_package):
        service = StoreService(db_session)
        low_stock = StoreProduct(name="Low Stock", description="Desc", package_id=sample_package.id, price=100, stock=2, low_stock_threshold=5, is_active=True)
        normal_stock = StoreProduct(name="Normal", description="Desc", package_id=sample_package.id, price=100, stock=10, low_stock_threshold=5, is_active=True)
        db_session.add_all([low_stock, normal_stock])
        db_session.commit()
        low_products = service.get_low_stock_products()
        assert any(p.id == low_stock.id for p in low_products)
        assert not any(p.id == normal_stock.id for p in low_products)

    def test_get_out_of_stock_products(self, db_session, sample_package):
        service = StoreService(db_session)
        out_of_stock = StoreProduct(name="Out", description="Desc", package_id=sample_package.id, price=100, stock=0, is_active=True)
        in_stock = StoreProduct(name="In", description="Desc", package_id=sample_package.id, price=100, stock=5, is_active=True)
        db_session.add_all([out_of_stock, in_stock])
        db_session.commit()
        out_products = service.get_out_of_stock_products()
        assert any(p.id == out_of_stock.id for p in out_products)
        assert not any(p.id == in_stock.id for p in out_products)

    def test_check_stock_alert_out_of_stock(self, db_session, sample_package):
        service = StoreService(db_session)
        product = StoreProduct(name="Out", description="Desc", package_id=sample_package.id, price=100, stock=0, is_active=True)
        db_session.add(product)
        db_session.commit()
        alert = service.check_stock_alert(product.id)
        assert alert['alert'] is True
        assert alert['status'] == 'out'

    def test_check_stock_alert_low(self, db_session, sample_package):
        service = StoreService(db_session)
        product = StoreProduct(name="Low", description="Desc", package_id=sample_package.id, price=100, stock=2, low_stock_threshold=5, is_active=True)
        db_session.add(product)
        db_session.commit()
        alert = service.check_stock_alert(product.id)
        assert alert['alert'] is True
        assert alert['status'] == 'low'

    def test_check_stock_alert_unlimited(self, db_session, sample_package):
        service = StoreService(db_session)
        product = StoreProduct(name="Unlimited", description="Desc", package_id=sample_package.id, price=100, stock=-1, is_active=True)
        db_session.add(product)
        db_session.commit()
        alert = service.check_stock_alert(product.id)
        assert alert['alert'] is False
        assert alert['status'] == 'unlimited'

    def test_check_stock_alert_normal(self, db_session, sample_package):
        service = StoreService(db_session)
        product = StoreProduct(name="Normal", description="Desc", package_id=sample_package.id, price=100, stock=10, low_stock_threshold=5, is_active=True)
        db_session.add(product)
        db_session.commit()
        alert = service.check_stock_alert(product.id)
        assert alert['alert'] is False
        assert alert['status'] == 'available'

    def test_update_low_stock_threshold(self, db_session, sample_store_product):
        service = StoreService(db_session)
        result = service.update_low_stock_threshold(sample_store_product.id, 10)
        assert result is True
        db_session.refresh(sample_store_product)
        assert sample_store_product.low_stock_threshold == 10

    def test_update_low_stock_threshold_invalid(self, db_session, sample_store_product):
        service = StoreService(db_session)
        result = service.update_low_stock_threshold(sample_store_product.id, -1)
        assert result is False

    def test_update_low_stock_threshold_product_not_found(self, db_session):
        service = StoreService(db_session)
        result = service.update_low_stock_threshold(99999, 10)
        assert result is False


    def test_close_service(self, db_session):
        """Test que el servicio cierra correctamente la sesión cuando la creó."""
        service = StoreService(db_session)
        # Como la sesión fue pasada externamente, no debería cerrarla
        service.close()
        # No debería lanzar excepción, pero no cierra sesión externa
        assert service.db is not None

    def test_cancel_order_not_found(self, db_session):
        service = StoreService(db_session)
        result = service.cancel_order(99999)
        assert result is False

    def test_cancel_order_not_pending(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        balance = BesitoBalance(user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0)
        db_session.add(balance)
        db_session.commit()
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=1)
        order, _ = service.create_order(sample_user.id)
        order.status = OrderStatus.COMPLETED
        db_session.commit()
        result = service.cancel_order(order.id)
        assert result is False

    def test_get_order_not_found(self, db_session):
        service = StoreService(db_session)
        order = service.get_order(99999)
        assert order is None


@pytest.mark.unit
class TestRaceConditions:
    @pytest.mark.asyncio
    async def test_complete_order_uses_select_for_update_on_product(self, db_session, sample_store_product, sample_user):
        """Verifica que complete_order usa with_for_update al consultar el producto."""
        service = StoreService(db_session)
        balance = BesitoBalance(user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0)
        db_session.add(balance)
        db_session.commit()
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=1)
        order, _ = service.create_order(sample_user.id)

        # Mock chain verification
        mock_query = MagicMock()
        mock_filtered = MagicMock()
        mock_lock = MagicMock()
        mock_first = MagicMock(return_value=sample_store_product)

        mock_query.filter.return_value = mock_filtered
        mock_filtered.with_for_update.return_value = mock_lock
        mock_lock.first.return_value = sample_store_product

        real_query = db_session.query

        def spy_query(model):
            if model is StoreProduct:
                return mock_query
            # fallback to real query for other models
            return real_query(model)

        with patch.object(db_session, 'query', spy_query):
            await service.complete_order(AsyncMock(), order.id)

        assert mock_filtered.with_for_update.called, "Debe usar SELECT FOR UPDATE en producto"
