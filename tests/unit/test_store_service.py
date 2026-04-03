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
        result = service.delete_product(sample_store_product.id)
        assert result is True
        assert service.get_product(sample_store_product.id).is_active is False

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
