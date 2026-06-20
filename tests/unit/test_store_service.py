"""
Tests unitarios para StoreService.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.models import (
    BesitoBalance,
    BesitoTransaction,
    Category,
    Order,
    OrderStatus,
    Package,
    StoreProduct,
    TransactionSource,
    TransactionType,
    User,
    UserRole,
)
from services.besito_service import (
    BesitoService,  # minimal for 1-line/guard port post Item10 local (copy daily precedent); counted in delta per tight
)
from services.store_service import StoreService


@pytest.mark.unit
class TestStoreService:
    def test_create_product(self, db_session):
        service = StoreService(db_session)
        pkg = Package(name="Test Package", description="Desc", is_active=True)
        db_session.add(pkg)
        db_session.commit()
        db_session.refresh(pkg)
        product = service.create_product(
            name="Test", description="Desc", package_id=pkg.id, price=100
        )
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

    def test_update_product_package_id(self, db_session, sample_store_product):
        service = StoreService(db_session)
        new_pkg = Package(name="Nuevo Paquete", description="Desc", is_active=True)
        db_session.add(new_pkg)
        db_session.commit()
        db_session.refresh(new_pkg)

        result = service.update_product(sample_store_product.id, package_id=new_pkg.id)
        assert result is True
        updated = service.get_product(sample_store_product.id)
        assert updated.package_id == new_pkg.id

    def test_update_product_rejects_inactive_package(self, db_session, sample_store_product):
        service = StoreService(db_session)
        inactive_pkg = Package(name="Inactivo", description="Desc", is_active=False)
        db_session.add(inactive_pkg)
        db_session.commit()
        db_session.refresh(inactive_pkg)

        result = service.update_product(sample_store_product.id, package_id=inactive_pkg.id)
        assert result is False

    def test_get_packages_for_product_edit_includes_current_package(
        self, db_session, sample_store_product
    ):
        service = StoreService(db_session)
        current_pkg = db_session.get(Package, sample_store_product.package_id)
        current_pkg.is_active = False
        current_pkg.store_stock = 0
        db_session.commit()

        packages = service.get_packages_for_product_edit(sample_store_product.id)
        package_ids = {pkg.id for pkg in packages}
        assert sample_store_product.package_id in package_ids

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

    def test_add_to_cart_existing_updates_quantity(
        self, db_session, sample_user, sample_store_product
    ):
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
        assert (
            "saldo" in error.lower()
            or "balance" in error.lower()
            or "insufficient" in error.lower()
        )

    def test_create_order_success(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        balance = BesitoBalance(
            user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0
        )
        db_session.add(balance)
        db_session.commit()
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=2)
        order, error = service.create_order(sample_user.id)
        assert order is not None
        assert order.status == OrderStatus.PENDING
        assert order.total_price == sample_store_product.price * 2
        assert len(order.items) == 1

    @pytest.mark.asyncio
    async def test_complete_order_success(
        self, db_session, sample_user, sample_store_product, mock_bot
    ):
        service = StoreService(db_session)
        balance = BesitoBalance(
            user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0
        )
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
        assert (
            (
                BesitoService(db=db_session).get_balance(sample_user.id)
                if not hasattr(service, "besito_service")
                else service.besito_service.get_balance(sample_user.id)
            )
            == 9999 - order.total_price
        )  # 1-line/guard port post Item10 local (copy daily precedent in cross; arch-enforcer); was service.besito_service

    @pytest.mark.asyncio
    async def test_complete_order_unlimited_stock(
        self, db_session, sample_user, sample_store_product, mock_bot
    ):
        service = StoreService(db_session)
        balance = BesitoBalance(
            user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0
        )
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
    async def test_complete_order_already_processed(
        self, db_session, sample_user, sample_store_product, mock_bot
    ):
        service = StoreService(db_session)
        balance = BesitoBalance(
            user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0
        )
        db_session.add(balance)
        db_session.commit()
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=1)
        order, _ = service.create_order(sample_user.id)
        await service.complete_order(mock_bot, order.id)
        success, msg = await service.complete_order(mock_bot, order.id)
        assert success is True, "second complete is idempotent success"
        assert db_session.query(BesitoTransaction).filter_by(user_id=sample_user.id).count() == 1

    def test_cancel_order(self, db_session, sample_user, sample_store_product):
        service = StoreService(db_session)
        balance = BesitoBalance(
            user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0
        )
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
        assert stats["total_products"] >= 1
        assert "available_products" in stats
        assert "total_orders" in stats


@pytest.mark.unit
class TestRaceConditions:
    @pytest.mark.asyncio
    async def test_complete_order_uses_select_for_update_on_product(
        self, db_session, sample_store_product, sample_user
    ):
        """Verifica que complete_order usa with_for_update al consultar el producto."""
        service = StoreService(db_session)
        balance = BesitoBalance(
            user_id=sample_user.id, balance=9999, total_earned=9999, total_spent=0
        )
        db_session.add(balance)
        db_session.commit()
        service.add_to_cart(sample_user.id, sample_store_product.id, quantity=1)
        order, _ = service.create_order(sample_user.id)

        # Mock chain verification
        mock_query = MagicMock()
        mock_filtered = MagicMock()
        mock_lock = MagicMock()

        mock_query.filter.return_value = mock_filtered
        mock_filtered.with_for_update.return_value = mock_lock
        mock_lock.first.return_value = sample_store_product

        real_query = db_session.query

        def spy_query(model):
            if model is StoreProduct:
                return mock_query
            # fallback to real query for other models
            return real_query(model)

        with patch.object(db_session, "query", spy_query):
            await service.complete_order(AsyncMock(), order.id)

        assert mock_filtered.with_for_update.called, "Debe usar SELECT FOR UPDATE en producto"


# =============================================================================
# GOLD PILOT: Atomic purchase contract (Fase 6 Alta #1)
# Copy verbatim pattern from test_besito_service.py / test_daily_gift_service.py / cross_service_atomicity
# SQLite file + TestSession (for internal commits in debit + complete)
# fresh numeric TG telegram_id (77709xxx), explicit models, saved_tg pre close/reopen, strict re-query, try/finally dispose
# DESIRED CONTRACT docstring
# N806 tolerated ONLY for TestSession (exact precedent)
# =============================================================================


@pytest.mark.unit
class TestStorePurchaseAtomicGold:
    """Gold pilots for store purchase atomicity per Fase6 contract deseado.

    DESIRED CONTRACT:
    - complete_order atomic DB phase: recheck balance -> debit_besitos(PURCHASE, commit=False) ->
      product.with_for_update() stock decr -> order COMPLETE + completed_at -> single db.commit()
    - On failure before commit: db.rollback() (debit, stock, order status unchanged)
    - Post-commit best-effort: deliver_package_to_user per item; TG fail -> besitos charged +
      stock decremented + order COMPLETED (redelivery via backpack)
    - Uses local on-demand BesitoService(db=shared) per Item10 store precedent.
    - TG BigInt: user_id = telegram_id (not PK .id)
    - Note: Backpack/reward history visibility is cross-domain (asserted in test_backpack_service + invariants I8); this pilot protects the core atomic debit+COMPLETE path.
    - DEFENSIVE (pre-existing purchase TOCTOU/races in store_service): asserts the debit + with_for_update(product) + PURCHASE tx path. Full concurrency simulation belongs in cross/invariants tests. Pre-existing prod contract not altered by this tirón.
    """

    def _create_engine_and_session(self, tmp_path: Path):
        """SQLite file + TestSession (verbatim gold pattern from besito/daily/cross)."""
        db_path = tmp_path / "test_store_atomic_purchase.db"
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # noqa: N806 (precedent in gold atomicity/reaction_full patterns)
        return engine, TestSession

    @pytest.mark.asyncio
    async def test_complete_order_atomic_debit_sticks_and_order_complete(
        self, tmp_path: Path, mock_bot
    ):
        """Happy path: debit + stock + deliver + COMPLETE succeed. Post-reopen strict re-query verifies."""
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        db = TestSession()
        try:
            # Explicit fresh TG numeric (77709xxx) + models (DESIRED: telegram_id as user_id)
            tg = 77709010
            user = User(
                telegram_id=tg,
                username="storebuyer",
                first_name="Store",
                last_name="Buyer",
                role=UserRole.USER,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            saved_tg = user.telegram_id  # before any close/reopen

            balance = BesitoBalance(
                user_id=saved_tg, balance=1000, total_earned=1000, total_spent=0
            )
            db.add(balance)
            db.commit()

            pkg = Package(
                name="Atomic Package",
                description="test",
                store_stock=-1,
                reward_stock=-1,
                is_active=True,
            )
            db.add(pkg)
            db.commit()
            db.refresh(pkg)

            product = StoreProduct(
                name="Atomic Product",
                description="gold",
                price=150,
                stock=5,
                package_id=pkg.id,
                is_active=True,
                low_stock_threshold=2,
            )
            db.add(product)
            db.commit()
            db.refresh(product)

            # Service with shared TestSession db (no owns)
            service = StoreService(db=db)
            service.package_service = MagicMock()  # avoid real deliver side
            service.package_service.deliver_package_to_user = AsyncMock()

            # cart + order
            service.add_to_cart(saved_tg, product.id, quantity=1)
            order, err = service.create_order(saved_tg)
            assert order is not None
            assert order.status == OrderStatus.PENDING

            # complete (async)
            success, msg = await service.complete_order(mock_bot, order.id)
            assert success is True

            # Strict re-query post internal commits (use fresh session)
            db2 = TestSession()
            try:
                re_bal = db2.query(BesitoBalance).filter_by(user_id=saved_tg).first()
                re_order = db2.query(Order).filter_by(id=order.id).first()
                re_prod = db2.query(StoreProduct).filter_by(id=product.id).first()

                assert re_bal is not None
                assert re_bal.balance == 1000 - 150, "debit PURCHASE must persist"
                assert re_bal.total_spent == 150
                assert re_order is not None
                assert re_order.status == OrderStatus.COMPLETED
                assert re_order.completed_at is not None
                assert re_prod.stock == 4
                txs = (
                    db2.query(BesitoTransaction)
                    .filter_by(user_id=saved_tg, source=TransactionSource.PURCHASE)
                    .all()
                )
                assert len(txs) == 1
                assert txs[0].amount == -150
                assert txs[0].type == TransactionType.DEBIT
                assert txs[0].reference_id == order.id
                # deliver called (best effort)
                service.package_service.deliver_package_to_user.assert_called()
            finally:
                db2.close()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_complete_order_partial_post_debit_debit_survives(self, tmp_path: Path, mock_bot):
        """Post-commit deliver fail: atomic phase commits debit+stock+COMPLETE; TG delivery best-effort.
        DEFENSIVE (pre-existing purchase races/TOCTOU): asserts debit + for_update(product) path + PURCHASE tx.
        Full race simulation is out of scope here (see cross/invariants)."""
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        db = TestSession()
        try:
            tg = 77709011
            user = User(
                telegram_id=tg,
                username="partialbuyer",
                first_name="Partial",
                last_name="Buyer",
                role=UserRole.USER,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            saved_tg = user.telegram_id

            balance = BesitoBalance(user_id=saved_tg, balance=500, total_earned=500, total_spent=0)
            db.add(balance)
            db.commit()

            pkg = Package(name="Partial Pkg", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)

            product = StoreProduct(
                name="Partial Prod", price=50, stock=10, package_id=pkg.id, is_active=True
            )
            db.add(product)
            db.commit()
            db.refresh(product)

            service = StoreService(db=db)
            service.package_service = MagicMock()
            service.package_service.deliver_package_to_user = AsyncMock(
                side_effect=Exception("deliver fail sim")
            )

            service.add_to_cart(saved_tg, product.id, quantity=1)
            order, _ = service.create_order(saved_tg)

            # Note: complete_order does recheck + debit_besitos (internal commit) then product.with_for_update()
            # for stock decr, then deliver (best-effort, exception here does not rollback the atomic DB phase in current impl).
            # This pilot protects the debit + for_update(product) + PURCHASE tx + COMPLETED state.
            # Full concurrency/race coverage (TOCTOU etc.) is in cross_service_atomicity + invariants tests.
            success, _ = await service.complete_order(mock_bot, order.id)
            assert success is True, "DB phase must succeed even when TG delivery fails post-commit"

            db3 = TestSession()
            try:
                re_bal = db3.query(BesitoBalance).filter_by(user_id=saved_tg).first()
                re_order = db3.query(Order).filter_by(id=order.id).first()
                re_prod = db3.query(StoreProduct).filter_by(id=product.id).first()
                assert re_bal.balance == 500 - 50
                assert re_bal.total_spent == 50
                assert re_prod.stock == 9
                assert re_order is not None
                assert re_order.status == OrderStatus.COMPLETED
                assert re_order.completed_at is not None
                txs = (
                    db3.query(BesitoTransaction)
                    .filter_by(user_id=saved_tg, source=TransactionSource.PURCHASE)
                    .all()
                )
                assert len(txs) == 1
                assert txs[0].amount == -50
                assert txs[0].reference_id == order.id
                service.package_service.deliver_package_to_user.assert_called()
            finally:
                db3.close()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_complete_order_insufficient_stock_at_complete(self, tmp_path: Path, mock_bot):
        """Stock depleted between create_order and complete_order aborts atomic phase."""
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        db = TestSession()
        try:
            tg = 77709014
            user = User(telegram_id=tg, username="stockfail", role=UserRole.USER)
            db.add(user)
            db.commit()
            saved_tg = user.telegram_id

            balance = BesitoBalance(user_id=saved_tg, balance=500, total_earned=500, total_spent=0)
            db.add(balance)
            db.commit()

            pkg = Package(name="StockFail Pkg", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)

            product = StoreProduct(
                name="StockFail Prod", price=50, stock=1, package_id=pkg.id, is_active=True
            )
            db.add(product)
            db.commit()
            db.refresh(product)

            service = StoreService(db=db)
            service.package_service = MagicMock()
            service.package_service.deliver_package_to_user = AsyncMock()

            service.add_to_cart(saved_tg, product.id, quantity=1)
            order, _ = service.create_order(saved_tg)
            product.stock = 0
            db.commit()

            success, msg = await service.complete_order(mock_bot, order.id)
            assert success is False
            assert "pago" in msg.lower()

            db3 = TestSession()
            try:
                assert db3.query(BesitoBalance).filter_by(user_id=saved_tg).first().balance == 500
                assert db3.query(Order).filter_by(id=order.id).first().status == OrderStatus.PENDING
                assert db3.query(BesitoTransaction).filter_by(user_id=saved_tg).count() == 0
            finally:
                db3.close()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_complete_order_missing_product_rolls_back(self, tmp_path: Path, mock_bot):
        """Missing product row at complete time aborts atomic phase."""
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        db = TestSession()
        try:
            tg = 77709015
            user = User(telegram_id=tg, username="missingprod", role=UserRole.USER)
            db.add(user)
            db.commit()
            saved_tg = user.telegram_id

            balance = BesitoBalance(user_id=saved_tg, balance=500, total_earned=500, total_spent=0)
            db.add(balance)
            db.commit()

            pkg = Package(name="Missing Pkg", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)

            product = StoreProduct(
                name="Missing Prod", price=50, stock=10, package_id=pkg.id, is_active=True
            )
            db.add(product)
            db.commit()
            db.refresh(product)
            product_id = product.id

            service = StoreService(db=db)
            service.package_service = MagicMock()
            service.package_service.deliver_package_to_user = AsyncMock()

            service.add_to_cart(saved_tg, product_id, quantity=1)
            order, _ = service.create_order(saved_tg)

            real_query = db.query

            def spy_query(model):
                if model is StoreProduct:
                    mock_q = MagicMock()
                    mock_q.filter.return_value.with_for_update.return_value.first.return_value = (
                        None
                    )
                    return mock_q
                return real_query(model)

            with patch.object(db, "query", spy_query):
                success, _ = await service.complete_order(mock_bot, order.id)
            assert success is False

            db3 = TestSession()
            try:
                assert db3.query(BesitoBalance).filter_by(user_id=saved_tg).first().balance == 500
                assert db3.query(Order).filter_by(id=order.id).first().status == OrderStatus.PENDING
                assert db3.query(BesitoTransaction).filter_by(user_id=saved_tg).count() == 0
            finally:
                db3.close()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_complete_order_delivers_per_quantity(self, tmp_path: Path, mock_bot):
        """quantity=2 triggers two deliver calls."""
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        db = TestSession()
        try:
            tg = 77709016
            user = User(telegram_id=tg, username="qtybuyer", role=UserRole.USER)
            db.add(user)
            db.commit()
            saved_tg = user.telegram_id

            balance = BesitoBalance(user_id=saved_tg, balance=500, total_earned=500, total_spent=0)
            db.add(balance)
            db.commit()

            pkg = Package(name="Qty Pkg", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)

            product = StoreProduct(
                name="Qty Prod", price=50, stock=10, package_id=pkg.id, is_active=True
            )
            db.add(product)
            db.commit()
            db.refresh(product)

            service = StoreService(db=db)
            service.package_service = MagicMock()
            service.package_service.deliver_package_to_user = AsyncMock(return_value=(True, ""))

            service.add_to_cart(saved_tg, product.id, quantity=2)
            order, _ = service.create_order(saved_tg)
            success, _ = await service.complete_order(mock_bot, order.id)
            assert success is True

            assert service.package_service.deliver_package_to_user.call_count == 2

            db2 = TestSession()
            try:
                re_bal = db2.query(BesitoBalance).filter_by(user_id=saved_tg).first()
                re_order = db2.query(Order).filter_by(id=order.id).first()
                re_prod = db2.query(StoreProduct).filter_by(id=product.id).first()
                assert re_bal.balance == 500 - 100
                assert re_bal.total_spent == 100
                assert re_order.status == OrderStatus.COMPLETED
                assert re_order.completed_at is not None
                assert re_prod.stock == 8
                txs = (
                    db2.query(BesitoTransaction)
                    .filter_by(user_id=saved_tg, source=TransactionSource.PURCHASE)
                    .all()
                )
                assert len(txs) == 1
                assert txs[0].amount == -100
                assert txs[0].type == TransactionType.DEBIT
                assert txs[0].reference_id == order.id
            finally:
                db2.close()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_complete_order_deliver_tuple_failure_still_commits(
        self, tmp_path: Path, mock_bot
    ):
        """deliver (False, msg) post-commit does not roll back DB phase."""
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        db = TestSession()
        try:
            tg = 77709017
            user = User(telegram_id=tg, username="tuplefail", role=UserRole.USER)
            db.add(user)
            db.commit()
            saved_tg = user.telegram_id

            balance = BesitoBalance(user_id=saved_tg, balance=500, total_earned=500, total_spent=0)
            db.add(balance)
            db.commit()

            pkg = Package(name="Tuple Pkg", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)

            product = StoreProduct(
                name="Tuple Prod", price=50, stock=10, package_id=pkg.id, is_active=True
            )
            db.add(product)
            db.commit()
            db.refresh(product)

            service = StoreService(db=db)
            service.package_service = MagicMock()
            service.package_service.deliver_package_to_user = AsyncMock(
                return_value=(False, "deliver fail")
            )

            service.add_to_cart(saved_tg, product.id, quantity=1)
            order, _ = service.create_order(saved_tg)
            success, _ = await service.complete_order(mock_bot, order.id)
            assert success is True

            db3 = TestSession()
            try:
                re_order = db3.query(Order).filter_by(id=order.id).first()
                assert re_order.status == OrderStatus.COMPLETED
                assert db3.query(BesitoTransaction).filter_by(user_id=saved_tg).count() == 1
            finally:
                db3.close()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_complete_order_double_complete_idempotent(self, tmp_path: Path, mock_bot):
        """Second complete_order returns success with single PURCHASE tx."""
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        db = TestSession()
        try:
            tg = 77709018
            user = User(telegram_id=tg, username="doublebuyer", role=UserRole.USER)
            db.add(user)
            db.commit()
            saved_tg = user.telegram_id

            balance = BesitoBalance(user_id=saved_tg, balance=500, total_earned=500, total_spent=0)
            db.add(balance)
            db.commit()

            pkg = Package(name="Double Pkg", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)

            product = StoreProduct(
                name="Double Prod", price=50, stock=10, package_id=pkg.id, is_active=True
            )
            db.add(product)
            db.commit()
            db.refresh(product)

            service = StoreService(db=db)
            service.package_service = MagicMock()
            service.package_service.deliver_package_to_user = AsyncMock(return_value=(True, ""))

            service.add_to_cart(saved_tg, product.id, quantity=1)
            order, _ = service.create_order(saved_tg)

            success1, _ = await service.complete_order(mock_bot, order.id)
            success2, _ = await service.complete_order(mock_bot, order.id)
            assert success1 is True
            assert success2 is True

            db3 = TestSession()
            try:
                txs = (
                    db3.query(BesitoTransaction)
                    .filter_by(user_id=saved_tg, source=TransactionSource.PURCHASE)
                    .all()
                )
                assert len(txs) == 1
            finally:
                db3.close()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_complete_order_insufficient_balance_at_complete(self, tmp_path: Path, mock_bot):
        """Pre-try balance guard rejects complete without debiting."""
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        db = TestSession()
        try:
            tg = 77709012
            user = User(
                telegram_id=tg,
                username="rollbackbuyer",
                first_name="Rollback",
                last_name="Buyer",
                role=UserRole.USER,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            saved_tg = user.telegram_id

            balance = BesitoBalance(user_id=saved_tg, balance=100, total_earned=100, total_spent=0)
            db.add(balance)
            db.commit()

            pkg = Package(name="Rollback Pkg", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)

            product = StoreProduct(
                name="Rollback Prod", price=50, stock=10, package_id=pkg.id, is_active=True
            )
            db.add(product)
            db.commit()
            db.refresh(product)

            service = StoreService(db=db)
            service.package_service = MagicMock()
            service.package_service.deliver_package_to_user = AsyncMock()

            service.add_to_cart(saved_tg, product.id, quantity=1)
            order, _ = service.create_order(saved_tg)
            assert order is not None

            # Simular carrera: saldo suficiente al crear orden, insuficiente al completar
            balance.balance = 30
            db.commit()

            success, msg = await service.complete_order(mock_bot, order.id)
            assert success is False
            assert "insuficiente" in msg.lower() or "pago" in msg.lower()

            db3 = TestSession()
            try:
                re_bal = db3.query(BesitoBalance).filter_by(user_id=saved_tg).first()
                re_order = db3.query(Order).filter_by(id=order.id).first()
                re_prod = db3.query(StoreProduct).filter_by(id=product.id).first()
                assert re_bal.balance == 30, "debit failure must not change balance"
                assert re_bal.total_spent == 0
                assert re_prod.stock == 10
                assert re_order.status == OrderStatus.PENDING
                assert re_order.completed_at is None
                service.package_service.deliver_package_to_user.assert_not_called()
                assert db3.query(BesitoTransaction).filter_by(user_id=saved_tg).count() == 0
            finally:
                db3.close()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_complete_order_debit_failure_rolls_back(self, tmp_path: Path, mock_bot):
        """debit_besitos(commit=False) returning False rolls back without PURCHASE tx."""
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        db = TestSession()
        try:
            tg = 77709013
            user = User(
                telegram_id=tg,
                username="debitfailbuyer",
                first_name="DebitFail",
                last_name="Buyer",
                role=UserRole.USER,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            saved_tg = user.telegram_id

            balance = BesitoBalance(user_id=saved_tg, balance=500, total_earned=500, total_spent=0)
            db.add(balance)
            db.commit()

            pkg = Package(name="DebitFail Pkg", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)

            product = StoreProduct(
                name="DebitFail Prod", price=50, stock=10, package_id=pkg.id, is_active=True
            )
            db.add(product)
            db.commit()
            db.refresh(product)

            service = StoreService(db=db)
            service.package_service = MagicMock()
            service.package_service.deliver_package_to_user = AsyncMock()

            service.add_to_cart(saved_tg, product.id, quantity=1)
            order, _ = service.create_order(saved_tg)
            assert order is not None

            with patch.object(BesitoService, "debit_besitos", return_value=False):
                success, msg = await service.complete_order(mock_bot, order.id)

            assert success is False
            assert "pago" in msg.lower()

            db3 = TestSession()
            try:
                re_bal = db3.query(BesitoBalance).filter_by(user_id=saved_tg).first()
                re_order = db3.query(Order).filter_by(id=order.id).first()
                re_prod = db3.query(StoreProduct).filter_by(id=product.id).first()
                assert re_bal.balance == 500
                assert re_bal.total_spent == 0
                assert re_prod.stock == 10
                assert re_order.status == OrderStatus.PENDING
                assert re_order.completed_at is None
                assert db3.query(BesitoTransaction).filter_by(user_id=saved_tg).count() == 0
                service.package_service.deliver_package_to_user.assert_not_called()
            finally:
                db3.close()
        finally:
            db.close()
            engine.dispose()

    def test_search_products(self, db_session):
        """DESIRED CONTRACT Fase12: search by name/desc ilike returns matches, filters active.
        Fresh explicit data, exact list equality (gold precedent strict ==/lists).
        """
        pkg = Package(name="SearchPkg", is_active=True)
        db_session.add(pkg)
        db_session.commit()
        db_session.refresh(pkg)
        prod = StoreProduct(
            name="UniqueSearchNameXYZ123",
            description="desc",
            package_id=pkg.id,
            price=100,
            stock=5,
            is_active=True,
        )
        db_session.add(prod)
        inactive = StoreProduct(
            name="UniqueSearchNameXYZ123",
            description="desc",
            package_id=pkg.id,
            price=100,
            stock=5,
            is_active=False,
        )
        db_session.add(inactive)
        db_session.commit()
        service = StoreService(db_session)
        try:
            results = service.search_products("UniqueSearchNameXYZ123")
            assert [p.id for p in results] == [prod.id]  # exact, only active
            no = service.search_products("NONEXISTENTQUERYZZZ999")
            assert no == []
        finally:
            service.close()

    def test_filter_products_and_by_category(self, db_session):
        """DESIRED: filter multi-crit (cat, price, in_stock) + get_by_category via pkg.cat. Exact lists (no fixture mut, fresh)."""
        cat = Category(name="FilterCatX", is_active=True)
        db_session.add(cat)
        db_session.commit()
        db_session.refresh(cat)
        pkg = Package(name="FilterPkgX", is_active=True, category_id=cat.id)
        db_session.add(pkg)
        db_session.commit()
        db_session.refresh(pkg)
        prod = StoreProduct(name="FProd", package_id=pkg.id, price=1234, stock=3, is_active=True)
        db_session.add(prod)
        db_session.commit()
        db_session.refresh(prod)
        service = StoreService(db_session)
        try:
            by_cat = service.get_products_by_category(cat.id)
            assert [p.id for p in by_cat] == [prod.id]
            filtered = service.filter_products(
                category_id=cat.id, min_price=1000, max_price=2000, in_stock_only=True
            )
            assert [p.id for p in filtered] == [prod.id]
            out_price = service.filter_products(min_price=9999)
            assert [p.id for p in out_price] == []
        finally:
            service.close()

    def test_stock_helpers_and_low_stock(self, db_session):
        """DESIRED: compute pure stock emoji/text + product props is_low_stock/stock_status. Fresh prod."""
        from services.store_service import compute_stock_emoji_and_text

        pkg = Package(name="StockPkg", is_active=True)
        db_session.add(pkg)
        db_session.commit()
        db_session.refresh(pkg)
        prod = StoreProduct(
            name="SProd",
            package_id=pkg.id,
            price=10,
            stock=2,
            is_active=True,
            low_stock_threshold=5,
        )
        db_session.add(prod)
        db_session.commit()
        db_session.refresh(prod)
        service = StoreService(db_session)
        try:
            assert compute_stock_emoji_and_text(-1) == ("♾️", "∞")
            assert compute_stock_emoji_and_text(0) == ("🚨", "AGOTADO")
            assert compute_stock_emoji_and_text(3, is_low_stock=True) == ("⚠️", "3")
            assert compute_stock_emoji_and_text(10) == ("📦", "10")
            assert prod.is_low_stock is True
            assert prod.stock_status == "low"
            prod.stock = -1
            db_session.commit()
            db_session.refresh(prod)
            assert prod.stock_status == "unlimited"
        finally:
            service.close()
