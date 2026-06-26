"""
Dedicated E2E integration tests for store purchase complete_order / fulfillment paths
+ discount / tier / cap using TestSession/file pattern (copy atomic gold verbatim).

Covers (per PLAN Item 3 / mapeo store E2E scope):
- success complete_order (debit PURCHASE, COMPLETE, stock, post fulfillment best-effort)
- insufficient after effective discount
- monthly cap exhausted
- tier locked (REQUIRED_PREV_TIER_PURCHASES=2)

Pattern copied AL PIE DE LA LETRA from tests/unit/test_store_service.py TestStorePurchaseAtomicGold:
- SQLite file + TestSession (N806 tolerated + docstring)
- fresh numeric TG 77709xxx telegram_id (telegram_id as user_id per DESIRED CONTRACT)
- explicit models (User, BesitoBalance, Package, StoreProduct, Order, BesitoTransaction, StoreTier, etc.)
- try/finally reopen db2 + re-query for visibility post internal commits
- external patch ONLY on "services.fulfillment_service.PackageService" .deliver_package_to_user
- "credit survives deliver False" / post-commit best-effort semantics
- real DB state asserts (order COMPLETE, tx PURCHASE, balance delta, stock)
- 1-line/guard for balance inspect (copy daily/cross/Item10 precedent)

0 prod changes. Atomic gold untouched (100%). Re-runs of golds required after.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.models import (
    BesitoBalance,
    BesitoTransaction,
    FulfillmentKind,
    FulfillmentStatus,
    Order,
    OrderFulfillment,
    OrderItem,
    OrderStatus,
    Package,
    PrivilegeType,
    StorePrivilege,
    StoreProduct,
    StoreTier,
    TransactionSource,
    TransactionType,
    User,
    UserRole,
)
from services.besito_service import BesitoService
from services.store_service import (
    REQUIRED_PREV_TIER_PURCHASES,
    StoreService,
)


@pytest.mark.integration
class TestStorePurchaseE2EIntegration:
    """E2E integration for complete_order + discount/tier/cap paths (real DB + external patch only)."""

    def _create_engine_and_session(self, tmp_path: Path):
        """SQLite file + TestSession (verbatim gold pattern from atomic gold / cross)."""
        db_path = tmp_path / "test_store_purchase_e2e.db"
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # noqa: N806 (tolerated per atomic gold / reaction patterns)
        return engine, TestSession

    def _seed_discount_privilege_chain(self, db, user_id: int, product_id: int, pct: int = 20):
        """Minimal full FK chain for StorePrivilege (order+item+fulfillment+privilege)."""
        order = Order(
            user_id=user_id,
            total_items=1,
            total_price=100,
            status=OrderStatus.COMPLETED,
        )
        db.add(order)
        db.flush()
        item = OrderItem(
            order_id=order.id,
            product_id=product_id,
            product_name="disc",
            quantity=1,
            unit_price=100,
            total_price=100,
        )
        db.add(item)
        db.flush()
        row = OrderFulfillment(
            order_item_id=item.id,
            user_id=user_id,
            product_id=product_id,
            fulfillment_kind=FulfillmentKind.PRIVILEGE_DISCOUNT,
            status=FulfillmentStatus.FULFILLED,
        )
        db.add(row)
        db.flush()
        db.add(
            StorePrivilege(
                user_id=user_id,
                product_id=product_id,
                order_fulfillment_id=row.id,
                privilege_type=PrivilegeType.DISCOUNT,
                config=f'{{"discount_pct": {pct}}}',
                expires_at=datetime.now(UTC) + timedelta(days=30),
            )
        )
        db.commit()

    def _seed_tier(self, db, name: str, order_index: int):
        tier = StoreTier(
            name=name,
            slug=name.lower().replace(" ", "-"),
            order_index=order_index,
            is_active=True,
        )
        db.add(tier)
        db.commit()
        db.refresh(tier)
        return tier

    def _create_prior_purchase_at_tier(self, db, user_id: int, tier_index: int):
        """Create a completed purchase at given tier level to count toward REQUIRED_PREV."""
        pkg = Package(name=f"PriorPkg{tier_index}", is_active=True)
        db.add(pkg)
        db.commit()
        db.refresh(pkg)
        product = StoreProduct(
            name=f"PriorProd{tier_index}",
            price=10,
            stock=-1,
            package_id=pkg.id,
            is_active=True,
            tier_id=None,  # count via level, not strict FK here
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        # Minimal completed order + item for count_user_purchases_at_tier_level logic (level based)
        order = Order(
            user_id=user_id,
            total_items=1,
            total_price=10,
            status=OrderStatus.COMPLETED,
        )
        db.add(order)
        db.flush()
        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=1,
            unit_price=10,
            total_price=10,
        )
        db.add(item)
        db.commit()
        return product

    @pytest.mark.asyncio
    async def test_complete_order_success_debit_complete_stock_tx_and_post_best_effort(
        self, tmp_path: Path, mock_bot
    ):
        """Success: debit PURCHASE + COMPLETE + stock + tx; post-commit fulfillment best-effort (patched external only)."""
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        db = TestSession()
        try:
            tg = 77709030
            user = User(
                telegram_id=tg,
                username="e2ebuyer",
                first_name="E2E",
                role=UserRole.USER,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            saved_tg = user.telegram_id

            balance = BesitoBalance(
                user_id=saved_tg, balance=1000, total_earned=1000, total_spent=0
            )
            db.add(balance)
            db.commit()

            pkg = Package(name="E2E Pkg", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)

            product = StoreProduct(
                name="E2E Prod",
                price=123,
                stock=5,
                package_id=pkg.id,
                is_active=True,
            )
            db.add(product)
            db.commit()
            db.refresh(product)

            service = StoreService(db=db)
            service.add_to_cart(saved_tg, product.id, quantity=1)
            order, _ = service.create_order(saved_tg)
            assert order is not None
            assert order.status == OrderStatus.PENDING

            with patch("services.fulfillment_service.PackageService") as mock_pkg_cls:
                inst = mock_pkg_cls.return_value
                inst.deliver_package_to_user = AsyncMock(return_value=(True, ""))
                success, msg = await service.complete_order(mock_bot, order.id)
            assert success is True

            db2 = TestSession()
            try:
                re_order = db2.query(Order).filter_by(id=order.id).first()
                re_prod = db2.query(StoreProduct).filter_by(id=product.id).first()
                txs = (
                    db2.query(BesitoTransaction)
                    .filter_by(user_id=saved_tg, source=TransactionSource.PURCHASE)
                    .all()
                )

                assert re_order is not None
                assert re_order.status == OrderStatus.COMPLETED
                assert re_order.completed_at is not None
                assert re_prod.stock == 4
                assert len(txs) == 1
                assert txs[0].amount == -123
                assert txs[0].type == TransactionType.DEBIT
                assert txs[0].reference_id == order.id

                # 1-line/guard port post Item10 local (copy daily precedent in cross; arch-enforcer); was service.besito_service  # noqa: E501
                bal = (
                    BesitoService(db=db2).get_balance(saved_tg)
                    if not hasattr(service, "besito_service")
                    else service.besito_service.get_balance(saved_tg)
                )  # noqa: E501
                assert bal == 1000 - 123

                inst.deliver_package_to_user.assert_called()
            finally:
                db2.close()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_complete_order_insufficient_after_effective_discount(
        self, tmp_path: Path, mock_bot
    ):
        """Discount active: effective < list; balance < effective -> insufficient (no COMPLETE, no tx)."""
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        db = TestSession()
        try:
            tg = 77709031
            user = User(telegram_id=tg, username="discbuyer", role=UserRole.USER)
            db.add(user)
            db.commit()
            db.refresh(user)
            saved_tg = user.telegram_id

            balance = BesitoBalance(user_id=saved_tg, balance=79, total_earned=100, total_spent=0)
            db.add(balance)
            db.commit()

            pkg = Package(name="Disc Pkg", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)

            product = StoreProduct(
                name="Disc Prod", price=100, stock=5, package_id=pkg.id, is_active=True
            )
            db.add(product)
            db.commit()
            db.refresh(product)

            # Seed 20% discount -> effective 80; balance=79 < effective
            self._seed_discount_privilege_chain(db, saved_tg, product.id, pct=20)

            service = StoreService(db=db)
            order, err = service.direct_purchase(saved_tg, product.id)
            # direct_purchase checks effective via _apply_discount for balance? In current impl balance check inside complete uses effective.
            # To hit insufficient after effective, go through purchase_and_complete or direct then complete.
            if order is None:
                # Some paths error early on list price; ensure we reach effective debit check.
                # Fallback: create pending order manually then complete (debit path uses effective).
                order = Order(
                    user_id=saved_tg,
                    total_items=1,
                    total_price=100,
                    status=OrderStatus.PENDING,
                )
                db.add(order)
                db.flush()
                item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    quantity=1,
                    unit_price=100,
                    total_price=100,
                )
                db.add(item)
                db.commit()
                db.refresh(order)

            with patch("services.fulfillment_service.PackageService"):
                success, msg = await service.complete_order(mock_bot, order.id)

            assert success is False
            assert "insuficiente" in (msg or "").lower() or "saldo" in (msg or "").lower()

            db2 = TestSession()
            try:
                re_order = db2.query(Order).filter_by(id=order.id).first()
                txs = (
                    db2.query(BesitoTransaction)
                    .filter_by(user_id=saved_tg, source=TransactionSource.PURCHASE)
                    .all()
                )
                assert re_order.status == OrderStatus.PENDING
                assert len(txs) == 0
            finally:
                db2.close()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_direct_purchase_monthly_cap_exhausted_blocks(self, tmp_path: Path, mock_bot):
        """monthly_stock_cap exhausted -> direct_purchase returns cap error; no order created."""
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        db = TestSession()
        try:
            tg = 77709032
            user = User(telegram_id=tg, username="capbuyer", role=UserRole.USER)
            db.add(user)
            db.commit()
            db.refresh(user)
            saved_tg = user.telegram_id

            balance = BesitoBalance(
                user_id=saved_tg, balance=1000, total_earned=1000, total_spent=0
            )
            db.add(balance)
            db.commit()

            pkg = Package(name="Cap Pkg", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)

            product = StoreProduct(
                name="Cap Prod",
                price=50,
                stock=-1,
                package_id=pkg.id,
                is_active=True,
                monthly_stock_cap=1,
            )
            db.add(product)
            db.commit()
            db.refresh(product)

            # Create one fulfilled this month to exhaust cap (via FulfillmentService path count)
            from services.fulfillment_service import (
                FulfillmentService,  # noqa: F401 (for future or doc; count via rows)
            )

            _ = FulfillmentService(db)
            # Minimal fulfillment row for this product (current month)
            # The is_monthly_cap_available counts fulfillments for product in current month
            dummy_order = Order(
                user_id=saved_tg,
                total_items=1,
                total_price=50,
                status=OrderStatus.COMPLETED,
                completed_at=datetime.now(UTC),
            )
            db.add(dummy_order)
            db.flush()
            dummy_item = OrderItem(
                order_id=dummy_order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=1,
                unit_price=50,
                total_price=50,
            )
            db.add(dummy_item)
            db.flush()
            dummy_fulfill = OrderFulfillment(
                order_item_id=dummy_item.id,
                user_id=saved_tg,
                product_id=product.id,
                fulfillment_kind=FulfillmentKind.PACKAGE,
                status=FulfillmentStatus.FULFILLED,
            )
            db.add(dummy_fulfill)
            db.commit()

            service = StoreService(db=db)
            order, err = service.direct_purchase(saved_tg, product.id)
            assert order is None
            assert err is not None
            assert (
                "cap" in (err or "").lower()
                or "mensual" in (err or "").lower()
                or "límite" in (err or "").lower()
            )
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_direct_purchase_tier_locked_blocks(self, tmp_path: Path, mock_bot):
        """Tier locked (REQUIRED_PREV=2 not met) -> direct_purchase returns tier lock error; no order."""
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        db = TestSession()
        try:
            tg = 77709033
            user = User(telegram_id=tg, username="tierbuyer", role=UserRole.USER)
            db.add(user)
            db.commit()
            db.refresh(user)
            saved_tg = user.telegram_id

            balance = BesitoBalance(
                user_id=saved_tg, balance=1000, total_earned=1000, total_spent=0
            )
            db.add(balance)
            db.commit()

            pkg = Package(name="Tier Pkg", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)

            # Tiers: 0 (base), 1 (locked)
            _ = self._seed_tier(db, "Base", 0)
            t1 = self._seed_tier(db, "Elite", 1)

            product = StoreProduct(
                name="Tier Prod",
                price=200,
                stock=-1,
                package_id=pkg.id,
                is_active=True,
                tier_id=t1.id,  # requires prev tier purchases
            )
            db.add(product)
            db.commit()
            db.refresh(product)

            # Give only 1 purchase at prev tier (need 2 per REQUIRED_PREV_TIER_PURCHASES)
            self._create_prior_purchase_at_tier(db, saved_tg, 0)

            service = StoreService(db=db)
            order, err = service.direct_purchase(saved_tg, product.id)
            assert order is None
            assert err is not None
            assert (
                "nivel" in (err or "").lower()
                or "tier" in (err or "").lower()
                or str(REQUIRED_PREV_TIER_PURCHASES) in (err or "")
            )
        finally:
            db.close()
            engine.dispose()
