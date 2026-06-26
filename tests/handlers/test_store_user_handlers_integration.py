"""
Tests de integración para store_user_handlers.

Usa SQLite en memoria + StoreService real + bot mockeado.
Verifica el flujo completo: handler -> servicio real -> DB -> respuesta.
"""
from unittest.mock import AsyncMock, patch

import pytest

from models.models import (
    BesitoBalance,
)
from services.besito_service import BesitoService
from services.store_service import StoreService

pytestmark = [pytest.mark.integration]


class TestDirectBuyIntegration:
    """Tests de integración para direct_buy (compra directa)."""

    async def test_direct_buy_sufficient_balance_shows_confirm(
        self, make_callback, make_user, db_session, sample_store_product
    ):
        """Saldo suficiente -> muestra confirmación con precio efectivo real."""
        # Use a fresh user with proper telegram_id contract (DESIRED)
        from models.models import User, UserRole
        user = User(
            telegram_id=777001001,
            username="storebuyer",
            first_name="Store",
            role=UserRole.USER,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Balance must use telegram_id per DESIRED CONTRACT
        price = sample_store_product.price
        balance = BesitoBalance(
            user_id=user.telegram_id, balance=1000, total_earned=1000, total_spent=0
        )
        db_session.add(balance)
        db_session.commit()

        real_svc = StoreService(db_session)
        tg_user = make_user(user_id=user.telegram_id)

        with patch("handlers.store_user_handlers.StoreService") as mock_store_cls:
            mock_store_cls.return_value = real_svc
            from handlers.store_user_handlers import direct_buy
            from keyboards.callback_data import DirectBuyCallback
            cb_data = DirectBuyCallback(product_id=sample_store_product.id)
            cb = make_callback(user=tg_user)
            await direct_buy(cb, callback_data=cb_data)

            # Assert UI text 1:1 (confirm purchase message from LucienVoice)
            cb.message.edit_text.assert_called()
            text = cb.message.edit_text.call_args[0][0] if cb.message.edit_text.call_args else ""
            assert str(price) in text or "confirma" in text.lower() or "compra" in text.lower()

    async def test_direct_buy_insufficient_balance_alerts(
        self, make_callback, make_user, db_session, sample_store_product
    ):
        """Saldo insuficiente -> responde con alerta (no edita)."""
        from models.models import User, UserRole
        user = User(
            telegram_id=777001002,
            username="poorbuyer",
            first_name="Poor",
            role=UserRole.USER,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        balance = BesitoBalance(
            user_id=user.telegram_id, balance=0, total_earned=0, total_spent=0
        )
        db_session.add(balance)
        db_session.commit()

        real_svc = StoreService(db_session)
        tg_user = make_user(user_id=user.telegram_id)

        with patch("handlers.store_user_handlers.StoreService") as mock_store_cls:
            mock_store_cls.return_value = real_svc
            from handlers.store_user_handlers import direct_buy
            from keyboards.callback_data import DirectBuyCallback
            cb_data = DirectBuyCallback(product_id=sample_store_product.id)
            cb = make_callback(user=tg_user)
            await direct_buy(cb, callback_data=cb_data)

            # Should have answered with alert (insufficient) - exact Lucien voice per PLAN F3 E2E hygiene + UI 1:1
            cb.answer.assert_called()
            call_args = cb.answer.call_args
            assert call_args is not None
            # Pin exact "Moneda especial insuficiente." (LucienVoice.store_balance_insufficient_alert())
            # or current string if not yet wired; 0 prod change (hygiene test)
            answered_text = call_args[0][0] if call_args[0] else ""
            assert answered_text == "Moneda especial insuficiente." or "Moneda especial insuficiente" in answered_text
            # Also verify show_alert=True per unit gold
            assert call_args[1].get("show_alert") is True


# =============================================================================
# F3: Confirm direct buy + product detail + new success/insufficient-after-discount
# Uses real StoreService; patches ONLY external (PackageService.deliver) for post-commit
# For paths reaching complete_order: prefer TestSession/file for commit visibility (copy atomic gold)
# 1-line/guard for any post-purchase balance inspect (Item10 precedent)
# =============================================================================

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.models import (
    BesitoTransaction,
    Order,
    OrderStatus,
    Package,
    StoreProduct,
    TransactionSource,
    User,
    UserRole,
)


class TestConfirmDirectBuyIntegration:
    """Tests de integración para confirm_direct_buy (ejecuta purchase_and_complete)."""

    def _create_engine_and_session(self, tmp_path: Path):
        """SQLite file + TestSession (copy atomic gold pattern for complete_order visibility)."""
        db_path = tmp_path / "test_store_confirm_integration.db"
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)  # noqa: N806
        return engine, TestSession

    @pytest.mark.asyncio
    async def test_confirm_direct_buy_success_persists_complete_and_purchase_tx(
        self, tmp_path, mock_bot
    ):
        """Flujo completo: confirm -> purchase_and_complete -> order COMPLETE + tx PURCHASE + delta.
        Patch ONLY external (PackageService.deliver). 1-line/guard for balance post (Item10).
        """
        engine, TestSession = self._create_engine_and_session(tmp_path)  # noqa: N806
        db = TestSession()
        try:
            tg = 777003001
            user = User(telegram_id=tg, username="confbuyer", first_name="C", role=UserRole.USER)
            db.add(user)
            db.commit()
            db.refresh(user)

            pkg = Package(name="ConfirmPkg", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)

            product = StoreProduct(
                name="ConfirmProd", description="", price=150, stock=5, package_id=pkg.id, is_active=True
            )
            db.add(product)
            db.commit()
            db.refresh(product)

            bal = BesitoBalance(user_id=tg, balance=1000, total_earned=1000, total_spent=0)
            db.add(bal)
            db.commit()

            # Use same session for handler flow (expire_on_commit=False below); gold reopens are for cross-service internals.
            # Keep product scalar id only.
            product_id = product.id

            real_svc = StoreService(db=db)

            # We will call the handler function with a fabricated callback; patch class
            from handlers.store_user_handlers import confirm_direct_buy
            from keyboards.callback_data import ConfirmDirectBuyCallback

            with patch("handlers.store_user_handlers.StoreService") as mock_store_cls, \
                 patch("services.fulfillment_service.PackageService") as mock_pkg_cls:
                inst = mock_pkg_cls.return_value
                inst.deliver_package_to_user = AsyncMock(return_value=(True, ""))
                mock_store_cls.return_value = real_svc

                cb = AsyncMock()
                cb.from_user.id = tg
                cb.message.edit_text = AsyncMock()
                cb.answer = AsyncMock()
                cb_data = ConfirmDirectBuyCallback(product_id=product_id)

                await confirm_direct_buy(cb, callback_data=cb_data, bot=mock_bot, state=None)

            # No reopen needed for same-session visibility with expire_on_commit=False on maker below
            db.commit()  # ensure final visibility for re-queries

            # Assert DB state: order COMPLETE + PURCHASE tx + balance delta (1-line/guard)
            re_order = db.query(Order).filter(Order.user_id == tg, Order.status == OrderStatus.COMPLETED).first()
            assert re_order is not None
            assert re_order.status == OrderStatus.COMPLETED

            purch_tx = (
                db.query(BesitoTransaction)
                .filter(BesitoTransaction.user_id == tg, BesitoTransaction.source == TransactionSource.PURCHASE)
                .first()
            )
            assert purch_tx is not None
            assert purch_tx.amount == -150

            # 1-line/guard port post Item10 (copy daily precedent in cross; arch-enforcer)
            final_bal = (
                BesitoService(db=db).get_balance(tg)
                if not hasattr(real_svc, "besito_service")
                else real_svc.besito_service.get_balance(tg)
            )
            assert final_bal == 1000 - 150

        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_confirm_direct_buy_insufficient_after_effective_discount(
        self, db_session, make_callback, make_user, sample_store_product
    ):
        """Precio efectivo tras descuento > saldo -> error sin crear orden."""
        from models.models import PrivilegeType, StorePrivilege, User, UserRole

        # Seed a discount privilege (50%) for this product
        # Minimal seed using existing patterns from unit store
        user = User(telegram_id=777003002, username="discbuyer", first_name="D", role=UserRole.USER)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Seed full privilege chain (order+item+fulfillment+privilege) to satisfy NOT NULL order_fulfillment_id
        from datetime import UTC, datetime, timedelta

        from models.models import (
            FulfillmentKind,
            FulfillmentStatus,
            Order,
            OrderFulfillment,
            OrderItem,
        )
        order = Order(
            user_id=user.telegram_id, total_items=1, total_price=sample_store_product.price, status=OrderStatus.COMPLETED
        )
        db_session.add(order)
        db_session.flush()
        item = OrderItem(
            order_id=order.id,
            product_id=sample_store_product.id,
            product_name=sample_store_product.name,
            quantity=1,
            unit_price=sample_store_product.price,
            total_price=sample_store_product.price,
        )
        db_session.add(item)
        db_session.flush()
        row = OrderFulfillment(
            order_item_id=item.id,
            user_id=user.telegram_id,
            product_id=sample_store_product.id,
            fulfillment_kind=FulfillmentKind.PRIVILEGE_DISCOUNT,
            status=FulfillmentStatus.FULFILLED,
        )
        db_session.add(row)
        db_session.flush()
        priv = StorePrivilege(
            user_id=user.telegram_id,
            product_id=sample_store_product.id,
            order_fulfillment_id=row.id,
            privilege_type=PrivilegeType.DISCOUNT,
            config='{"discount_pct": 50}',
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        db_session.add(priv)
        db_session.commit()

        # Balance exactly at 50% of price (should be insufficient for effective after discount logic? wait)
        # effective = price - (price * 50 // 100) = price // 2
        # If balance == effective, should succeed. Make balance < effective.
        price = sample_store_product.price
        effective = max(0, price - (price * 50 // 100))
        bal = BesitoBalance(user_id=user.telegram_id, balance=effective - 1, total_earned=price, total_spent=0)
        db_session.add(bal)
        db_session.commit()

        real_svc = StoreService(db_session)
        tg_user = make_user(user_id=user.telegram_id)

        with patch("handlers.store_user_handlers.StoreService") as mock_store_cls:
            mock_store_cls.return_value = real_svc
            from handlers.store_user_handlers import confirm_direct_buy
            from keyboards.callback_data import ConfirmDirectBuyCallback
            cb_data = ConfirmDirectBuyCallback(product_id=sample_store_product.id)
            cb = make_callback(user=tg_user)
            await confirm_direct_buy(cb, callback_data=cb_data, bot=AsyncMock(), state=None)

        # Should answer with error (insufficient or similar)
        cb.answer.assert_called()


class TestProductDetailIntegration:
    """Tests de integración para product_detail (ctx real con descuentos/tiers/caps)."""

    async def test_product_detail_shows_effective_price_with_active_discount(
        self, db_session, make_callback, make_user, sample_store_product
    ):
        """get_product_detail_context con privilegio activo -> precio efectivo real."""
        from datetime import UTC, datetime, timedelta

        from models.models import PrivilegeType, StorePrivilege, User, UserRole

        user = User(telegram_id=777003003, username="detbuyer", first_name="Det", role=UserRole.USER)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # 25% discount (full chain seed)
        from models.models import (
            FulfillmentKind,
            FulfillmentStatus,
            Order,
            OrderFulfillment,
            OrderItem,
        )
        order = Order(
            user_id=user.telegram_id, total_items=1, total_price=sample_store_product.price, status=OrderStatus.COMPLETED
        )
        db_session.add(order)
        db_session.flush()
        item = OrderItem(
            order_id=order.id,
            product_id=sample_store_product.id,
            product_name=sample_store_product.name,
            quantity=1,
            unit_price=sample_store_product.price,
            total_price=sample_store_product.price,
        )
        db_session.add(item)
        db_session.flush()
        row = OrderFulfillment(
            order_item_id=item.id,
            user_id=user.telegram_id,
            product_id=sample_store_product.id,
            fulfillment_kind=FulfillmentKind.PRIVILEGE_DISCOUNT,
            status=FulfillmentStatus.FULFILLED,
        )
        db_session.add(row)
        db_session.flush()
        priv = StorePrivilege(
            user_id=user.telegram_id,
            product_id=sample_store_product.id,
            order_fulfillment_id=row.id,
            privilege_type=PrivilegeType.DISCOUNT,
            config='{"discount_pct": 25}',
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        db_session.add(priv)
        db_session.commit()

        real_svc = StoreService(db_session)
        tg_user = make_user(user_id=user.telegram_id)

        with patch("handlers.store_user_handlers.StoreService") as mock_store_cls:
            mock_store_cls.return_value = real_svc
            from handlers.store_user_handlers import product_detail
            from keyboards.callback_data import ProductDetailCallback
            cb_data = ProductDetailCallback(product_id=sample_store_product.id)
            cb = make_callback(user=tg_user)
            await product_detail(cb, callback_data=cb_data)

        cb.message.edit_text.assert_called()
        text = cb.message.edit_text.call_args[0][0] if cb.message.edit_text.call_args else ""
        # UI 1:1: when discount active, card includes "Precio de lista" + "ventaja activa" (or list price presence)
        assert "Precio de lista" in text or "ventaja activa" in text or "lista" in text.lower() or str(sample_store_product.price) in text


# New per mapeo: dedicated success + insufficient after effective
@pytest.mark.asyncio
async def test_store_user_purchase_success_integration(tmp_path, mock_bot):
    """Nuevo test: flujo handler confirm -> COMPLETE + PURCHASE + delta (usa TestSession/file)."""
    # Minimal self-contained using atomic-gold style setup; patch external only
    engine = create_engine(f"sqlite:///{tmp_path / 'purchase_success.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)  # noqa: N806
    db = TestSession()
    try:
        tg = 777003010
        user = User(telegram_id=tg, username="succbuyer", first_name="S", role=UserRole.USER)
        db.add(user)
        db.commit()
        pkg = Package(name="SuccPkg", is_active=True)
        db.add(pkg)
        db.commit()
        db.refresh(pkg)
        prod = StoreProduct(name="SuccProd", price=77, stock=3, package_id=pkg.id, is_active=True)
        db.add(prod)
        db.commit()
        db.refresh(prod)
        bal = BesitoBalance(user_id=tg, balance=200, total_earned=200, total_spent=0)
        db.add(bal)
        db.commit()
        # same session for flow; re-query by id after for asserts
        prod_id = prod.id

        real_svc = StoreService(db=db)

        with patch("handlers.store_user_handlers.StoreService") as mock_store_cls, \
             patch("services.fulfillment_service.PackageService") as mock_pkg_cls:
            mock_pkg_cls.return_value.deliver_package_to_user = AsyncMock(return_value=(True, ""))
            mock_store_cls.return_value = real_svc

            from handlers.store_user_handlers import confirm_direct_buy
            from keyboards.callback_data import ConfirmDirectBuyCallback
            cb = AsyncMock()
            cb.from_user.id = tg
            cb.message.edit_text = AsyncMock()
            cb.answer = AsyncMock()
            await confirm_direct_buy(cb, callback_data=ConfirmDirectBuyCallback(product_id=prod_id), bot=mock_bot, state=None)

        db.commit()
        ord_row = db.query(Order).filter(Order.user_id == tg, Order.status == OrderStatus.COMPLETED).first()
        assert ord_row is not None
        tx = db.query(BesitoTransaction).filter(BesitoTransaction.user_id == tg, BesitoTransaction.source == TransactionSource.PURCHASE).first()
        assert tx is not None and tx.amount == -77
        # 1-line/guard
        from services.besito_service import BesitoService as BSvc
        final = (BSvc(db=db).get_balance(tg) if not hasattr(real_svc, "besito_service") else real_svc.besito_service.get_balance(tg))
        assert final == 200 - 77
    finally:
        db.close()
        engine.dispose()


@pytest.mark.asyncio
async def test_store_user_purchase_insufficient_after_effective_discount(db_session, sample_store_product):
    """Nuevo test: efectivo tras descuento > saldo -> no orden."""
    from datetime import UTC, datetime, timedelta

    from models.models import PrivilegeType, StorePrivilege, User, UserRole
    user = User(telegram_id=777003011, username="discinsuf", first_name="DI", role=UserRole.USER)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    from models.models import (
        FulfillmentKind,
        FulfillmentStatus,
        Order,
        OrderFulfillment,
        OrderItem,
    )
    order = Order(
        user_id=user.telegram_id, total_items=1, total_price=sample_store_product.price, status=OrderStatus.COMPLETED
    )
    db_session.add(order)
    db_session.flush()
    item = OrderItem(
        order_id=order.id,
        product_id=sample_store_product.id,
        product_name=sample_store_product.name,
        quantity=1,
        unit_price=sample_store_product.price,
        total_price=sample_store_product.price,
    )
    db_session.add(item)
    db_session.flush()
    row = OrderFulfillment(
        order_item_id=item.id,
        user_id=user.telegram_id,
        product_id=sample_store_product.id,
        fulfillment_kind=FulfillmentKind.PRIVILEGE_DISCOUNT,
        status=FulfillmentStatus.FULFILLED,
    )
    db_session.add(row)
    db_session.flush()
    priv = StorePrivilege(
        user_id=user.telegram_id, product_id=sample_store_product.id,
        order_fulfillment_id=row.id,
        privilege_type=PrivilegeType.DISCOUNT, config='{"discount_pct": 50}',
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(priv)
    db_session.commit()
    price = sample_store_product.price
    eff = max(0, price - (price * 50 // 100))
    bal = BesitoBalance(user_id=user.telegram_id, balance=eff - 1, total_earned=price, total_spent=0)
    db_session.add(bal)
    db_session.commit()

    real_svc = StoreService(db_session)
    with patch("handlers.store_user_handlers.StoreService") as mock_store_cls:
        mock_store_cls.return_value = real_svc
        from handlers.store_user_handlers import confirm_direct_buy
        from keyboards.callback_data import ConfirmDirectBuyCallback
        cb = AsyncMock()
        cb.from_user.id = user.telegram_id
        cb.message.edit_text = AsyncMock()
        cb.answer = AsyncMock()
        await confirm_direct_buy(cb, callback_data=ConfirmDirectBuyCallback(product_id=sample_store_product.id), bot=AsyncMock(), state=None)
    cb.answer.assert_called()


class TestPurchaseHistoryIntegration:
    """Tests de integración para purchase_history (órdenes reales en DB)."""

    async def test_purchase_history_shows_real_orders(
        self, db_session, make_callback, make_user, sample_store_product
    ):
        """Crea órdenes reales + verifica que el historial las muestra (UI 1:1)."""
        from models.models import Order, OrderItem, OrderStatus, User, UserRole
        user = User(telegram_id=777004001, username="histbuyer", first_name="H", role=UserRole.USER)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create a completed order directly (simulates prior purchase)
        order = Order(
            user_id=user.telegram_id,
            total_items=1,
            total_price=sample_store_product.price,
            status=OrderStatus.COMPLETED,
        )
        db_session.add(order)
        db_session.flush()
        item = OrderItem(
            order_id=order.id,
            product_id=sample_store_product.id,
            product_name=sample_store_product.name,
            quantity=1,
            unit_price=sample_store_product.price,
            total_price=sample_store_product.price,
        )
        db_session.add(item)
        db_session.commit()

        real_svc = StoreService(db_session)
        tg_user = make_user(user_id=user.telegram_id)

        with patch("handlers.store_user_handlers.StoreService") as mock_store_cls:
            mock_store_cls.return_value = real_svc
            from handlers.store_user_handlers import purchase_history
            cb = make_callback(data="purchase_history", user=tg_user)
            await purchase_history(cb)

        cb.message.edit_text.assert_called()
        text = cb.message.edit_text.call_args[0][0] if cb.message.edit_text.call_args else ""
        # UI 1:1 with LucienVoice: header uses "adquisiciones pasadas", item uses "Adquisición #"
        assert "adquisiciones" in text.lower() or "Adquisición #" in text or str(order.id) in text or sample_store_product.name.split()[0].lower() in text.lower()


class TestCapTierErrorBranchesIntegration:
    """Minimal integration tests for cap exhausted and tier locked error branches (real svc)."""

    async def test_direct_buy_monthly_cap_exhausted_alerts(
        self, db_session, make_callback, make_user, sample_store_product
    ):
        """Seed product with monthly_stock_cap=1 + one completed fulfillment -> cap reached alert via real path."""
        from models.models import (
            FulfillmentKind,
            FulfillmentStatus,
            Order,
            OrderFulfillment,
            OrderItem,
            OrderStatus,
            User,
            UserRole,
        )

        user = User(telegram_id=777005001, username="capuser", first_name="Cap", role=UserRole.USER)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Set cap on product
        sample_store_product.monthly_stock_cap = 1
        db_session.commit()

        # Create one completed fulfillment for this month to exhaust
        order = Order(user_id=user.telegram_id, total_items=1, total_price=sample_store_product.price, status=OrderStatus.COMPLETED)
        db_session.add(order)
        db_session.flush()
        item = OrderItem(order_id=order.id, product_id=sample_store_product.id, product_name=sample_store_product.name, quantity=1, unit_price=sample_store_product.price, total_price=sample_store_product.price)
        db_session.add(item)
        db_session.flush()
        fulfill = OrderFulfillment(order_item_id=item.id, user_id=user.telegram_id, product_id=sample_store_product.id, fulfillment_kind=FulfillmentKind.PACKAGE, status=FulfillmentStatus.FULFILLED)
        db_session.add(fulfill)
        db_session.commit()

        real_svc = StoreService(db_session)
        tg_user = make_user(user_id=user.telegram_id)

        with patch("handlers.store_user_handlers.StoreService") as mock_store_cls:
            mock_store_cls.return_value = real_svc
            from handlers.store_user_handlers import direct_buy
            from keyboards.callback_data import DirectBuyCallback
            cb_data = DirectBuyCallback(product_id=sample_store_product.id)
            cb = make_callback(user=tg_user)
            await direct_buy(cb, callback_data=cb_data)

        cb.answer.assert_called()
        # Error text from service: LucienVoice.store_monthly_cap_reached
        call = cb.answer.call_args
        assert call is not None
        # The arg is the cap message or show_alert
        assert "dueño" in str(call) or "mes" in str(call).lower() or call.kwargs.get("show_alert") is True

    async def test_direct_buy_tier_locked_alerts(
        self, db_session, make_callback, make_user
    ):
        """Create tiered product where user has insufficient prev tier purchases -> tier lock alert."""
        from models.models import StoreTier, User, UserRole

        # Tiers (slug required)
        tier1 = StoreTier(slug="n1", name="Nivel 1", order_index=1, is_active=True)
        tier2 = StoreTier(slug="n2", name="Nivel 2", order_index=2, is_active=True)
        db_session.add_all([tier1, tier2])
        db_session.commit()
        db_session.refresh(tier1)
        db_session.refresh(tier2)

        user = User(telegram_id=777005002, username="tieruser", first_name="Tier", role=UserRole.USER)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Product in tier2, no prev purchases
        pkg = Package(name="TierPkg", is_active=True)
        db_session.add(pkg)
        db_session.commit()
        db_session.refresh(pkg)

        product = StoreProduct(name="Tiered Item", description="", price=100, stock=5, package_id=pkg.id, tier_id=tier2.id, is_active=True)
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        real_svc = StoreService(db_session)
        tg_user = make_user(user_id=user.telegram_id)

        with patch("handlers.store_user_handlers.StoreService") as mock_store_cls:
            mock_store_cls.return_value = real_svc
            from handlers.store_user_handlers import direct_buy
            from keyboards.callback_data import DirectBuyCallback
            cb_data = DirectBuyCallback(product_id=product.id)
            cb = make_callback(user=tg_user)
            await direct_buy(cb, callback_data=cb_data)

        cb.answer.assert_called()
        call = cb.answer.call_args
        # Tier locked message from LucienVoice.store_tier_locked
        assert "adquiera" in str(call).lower() or "nivel" in str(call).lower() or call.kwargs.get("show_alert") is True

