"""Gold tests G1–G8 for FulfillmentService (store fulfillment catalog)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.models import (
    BesitoBalance,
    DeliveryMode,
    FulfillmentKind,
    FulfillmentStatus,
    Order,
    OrderFulfillment,
    OrderItem,
    OrderStatus,
    Package,
    PrivilegeType,
    StoreProduct,
    StoreTier,
    StoreWaitlistEntry,
    StoryNode,
    Tariff,
    User,
    UserRole,
)
from services.backpack_service import BackpackService
from services.fulfillment_service import FulfillmentService
from services.story_service import StoryService
from services.store_service import StoreService
from utils.lucien_voice import LucienVoice


@pytest.mark.unit
class TestFulfillmentServiceGold:
    def _session(self, tmp_path: Path):
        db_path = tmp_path / "fulfillment_gold.db"
        engine = create_engine(
            f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # noqa: N806
        return engine, TestSession

    def _seed_package_product(self, db, tg: int, *, price: int = 50):
        user = User(telegram_id=tg, username="buyer", role=UserRole.USER)
        db.add(user)
        db.add(BesitoBalance(user_id=tg, balance=1000, total_earned=1000, total_spent=0))
        pkg = Package(name="Pkg", is_active=True)
        db.add(pkg)
        db.commit()
        db.refresh(pkg)
        product = StoreProduct(
            name="Auto Pkg",
            price=price,
            stock=10,
            package_id=pkg.id,
            delivery_mode=DeliveryMode.AUTO,
            fulfillment_kind=FulfillmentKind.PACKAGE,
            is_active=True,
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product, pkg

    @pytest.mark.asyncio
    async def test_g1_package_auto_debit_survives(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709101
            product, _ = self._seed_package_product(db, tg)
            store = StoreService(db=db)
            store.add_to_cart(tg, product.id, 1)
            order, _ = store.create_order(tg)
            mock_bot = AsyncMock()
            with patch(
                "services.fulfillment_service.PackageService"
            ) as MockPkg:
                inst = MockPkg.return_value
                inst.deliver_package_to_user = AsyncMock(return_value=(False, "tg fail"))
                success, _ = await store.complete_order(mock_bot, order.id)
            assert success is True
            db2 = TestSession()
            fulfill = (
                db2.query(OrderFulfillment)
                .filter(OrderFulfillment.user_id == tg)
                .first()
            )
            assert fulfill is not None
            assert fulfill.status == FulfillmentStatus.FAILED
            assert db2.query(Order).filter_by(id=order.id).first().status == OrderStatus.COMPLETED
            db2.close()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_g2_vip_grant_one_token_idempotent(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709102
            user = User(telegram_id=tg, role=UserRole.USER)
            db.add(user)
            tariff = Tariff(name="Mes VIP", duration_days=30, price="0", is_active=True)
            db.add(tariff)
            db.commit()
            db.refresh(tariff)
            pkg = Package(name="VIP placeholder", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)
            product = StoreProduct(
                name="Mes a Su Lado",
                price=100,
                stock=-1,
                package_id=pkg.id,
                delivery_mode=DeliveryMode.AUTO,
                fulfillment_kind=FulfillmentKind.VIP_GRANT,
                tariff_id=tariff.id,
                is_active=True,
            )
            db.add(product)
            db.commit()
            db.refresh(product)
            order = Order(user_id=tg, total_items=1, total_price=100, status=OrderStatus.COMPLETED)
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
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            mock_bot = AsyncMock()
            metadata = {
                "vip_activated": True,
                "subscription_id": 1,
                "invite_link": "https://t.me/+vipinvite",
                "tariff_name": tariff.name,
                "token_id": 99,
                "token_code": "ABC123",
            }
            with patch("services.fulfillment_service.VIPService") as MockVip:
                mock_vip = MockVip.return_value
                mock_vip.is_user_vip.return_value = False
                mock_vip.grant_vip_from_tariff = AsyncMock(
                    return_value=(True, "VIP activated", metadata)
                )
                mock_vip.resend_vip_invite_for_user = AsyncMock(
                    return_value=(True, "VIP resend", "https://t.me/+vipinvite")
                )
                ok1, _ = await svc.dispatch_fulfillment(mock_bot, row.id)
                row2 = svc.get_fulfillment_by_id(row.id)
                assert json.loads(row2.auto_result or "{}").get("vip_activated") is True
                row2.status = FulfillmentStatus.AUTO_IN_PROGRESS
                db.commit()
                ok2, _ = await svc.dispatch_fulfillment(mock_bot, row.id)
            assert ok1 and ok2
            mock_vip.grant_vip_from_tariff.assert_awaited_once()
            mock_vip.resend_vip_invite_for_user.assert_awaited_once()
            final_row = svc.get_fulfillment_by_id(row.id)
            assert final_row.status == FulfillmentStatus.FULFILLED
            auto = json.loads(final_row.auto_result or "{}")
            assert auto.get("vip_activated") is True
            assert "token_url" not in auto
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_vip_grant_already_vip_calls_grant_from_tariff(self, tmp_path: Path):
        """Compra nueva por usuario VIP activo debe extender vía grant_vip_from_tariff."""
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709152
            db.add(User(telegram_id=tg, role=UserRole.USER))
            tariff = Tariff(name="Mes VIP", duration_days=30, price="0", is_active=True)
            db.add(tariff)
            db.commit()
            db.refresh(tariff)
            pkg = Package(name="VIP placeholder", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)
            product = StoreProduct(
                name="Renovación VIP",
                price=100,
                stock=-1,
                package_id=pkg.id,
                delivery_mode=DeliveryMode.AUTO,
                fulfillment_kind=FulfillmentKind.VIP_GRANT,
                tariff_id=tariff.id,
                is_active=True,
            )
            db.add(product)
            db.commit()
            order = Order(user_id=tg, total_items=1, total_price=100, status=OrderStatus.COMPLETED)
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
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            mock_bot = AsyncMock()
            metadata = {
                "vip_activated": True,
                "subscription_id": 2,
                "invite_link": "https://t.me/+viprenew",
                "tariff_name": tariff.name,
                "token_id": 42,
            }
            with patch("services.fulfillment_service.VIPService") as MockVip:
                mock_vip = MockVip.return_value
                mock_vip.is_user_vip.return_value = True
                mock_vip.grant_vip_from_tariff = AsyncMock(
                    return_value=(True, "VIP renewed", metadata)
                )
                mock_vip.resend_vip_invite_for_user = AsyncMock()
                ok, _ = await svc.dispatch_fulfillment(mock_bot, row.id)
            assert ok is True
            mock_vip.grant_vip_from_tariff.assert_awaited_once()
            mock_vip.resend_vip_invite_for_user.assert_not_called()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_vip_grant_invite_failure_keeps_auto_in_progress_with_metadata(
        self, tmp_path: Path
    ):
        """Redeem OK + invite fallido: metadata parcial y AUTO_IN_PROGRESS para retry."""
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709153
            db.add(User(telegram_id=tg, role=UserRole.USER))
            tariff = Tariff(name="VIP", duration_days=30, price="0", is_active=True)
            db.add(tariff)
            db.commit()
            db.refresh(tariff)
            pkg = Package(name="VIP placeholder", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)
            product = StoreProduct(
                name="VIP Product",
                price=100,
                stock=-1,
                package_id=pkg.id,
                delivery_mode=DeliveryMode.AUTO,
                fulfillment_kind=FulfillmentKind.VIP_GRANT,
                tariff_id=tariff.id,
                is_active=True,
            )
            db.add(product)
            db.commit()
            order = Order(user_id=tg, total_items=1, total_price=100, status=OrderStatus.COMPLETED)
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
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            mock_bot = AsyncMock()
            partial = {
                "vip_activated": True,
                "subscription_id": 9,
                "invite_link": None,
                "tariff_name": tariff.name,
                "token_id": 7,
            }
            with patch("services.fulfillment_service.VIPService") as MockVip:
                MockVip.return_value.is_user_vip.return_value = False
                MockVip.return_value.grant_vip_from_tariff = AsyncMock(
                    return_value=(False, "invite failed", partial)
                )
                ok, _ = await svc.dispatch_fulfillment(mock_bot, row.id)
            assert ok is False
            refreshed = svc.get_fulfillment_by_id(row.id)
            assert refreshed.status == FulfillmentStatus.AUTO_IN_PROGRESS
            auto = json.loads(refreshed.auto_result or "{}")
            assert auto.get("vip_activated") is True
            assert auto.get("subscription_id") == 9
            assert auto.get("token_id") == 7
            enrichment = svc.build_purchase_enrichment(item.id)
            assert "resend_vip_invite" in enrichment["actions_available"]
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_vip_grant_failure_sets_failed_status(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709150
            db.add(User(telegram_id=tg, role=UserRole.USER))
            tariff = Tariff(name="VIP", duration_days=30, price="0", is_active=True)
            db.add(tariff)
            db.commit()
            db.refresh(tariff)
            pkg = Package(name="VIP placeholder", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)
            product = StoreProduct(
                name="VIP Product",
                price=100,
                stock=-1,
                package_id=pkg.id,
                delivery_mode=DeliveryMode.AUTO,
                fulfillment_kind=FulfillmentKind.VIP_GRANT,
                tariff_id=tariff.id,
                is_active=True,
            )
            db.add(product)
            db.commit()
            order = Order(user_id=tg, total_items=1, total_price=100, status=OrderStatus.COMPLETED)
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
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            mock_bot = AsyncMock()
            with patch("services.fulfillment_service.VIPService") as MockVip:
                MockVip.return_value.is_user_vip.return_value = False
                MockVip.return_value.grant_vip_from_tariff = AsyncMock(
                    return_value=(False, "activation failed", {})
                )
                ok, _ = await svc.dispatch_fulfillment(mock_bot, row.id)
            assert ok is False
            refreshed = svc.get_fulfillment_by_id(row.id)
            assert refreshed.status == FulfillmentStatus.FAILED
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_vip_grant_send_failure_keeps_auto_in_progress(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709151
            db.add(User(telegram_id=tg, role=UserRole.USER))
            tariff = Tariff(name="VIP", duration_days=30, price="0", is_active=True)
            db.add(tariff)
            db.commit()
            db.refresh(tariff)
            pkg = Package(name="VIP placeholder", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)
            product = StoreProduct(
                name="VIP Product",
                price=100,
                stock=-1,
                package_id=pkg.id,
                delivery_mode=DeliveryMode.AUTO,
                fulfillment_kind=FulfillmentKind.VIP_GRANT,
                tariff_id=tariff.id,
                is_active=True,
            )
            db.add(product)
            db.commit()
            order = Order(user_id=tg, total_items=1, total_price=100, status=OrderStatus.COMPLETED)
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
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            mock_bot = AsyncMock()
            mock_bot.send_message = AsyncMock(side_effect=RuntimeError("telegram down"))
            metadata = {
                "vip_activated": True,
                "subscription_id": 1,
                "invite_link": "https://t.me/+vipinvite",
                "tariff_name": tariff.name,
                "token_id": 1,
            }
            with patch("services.fulfillment_service.VIPService") as MockVip:
                MockVip.return_value.is_user_vip.return_value = False
                MockVip.return_value.grant_vip_from_tariff = AsyncMock(
                    return_value=(True, "VIP activated", metadata)
                )
                ok, _ = await svc.dispatch_fulfillment(mock_bot, row.id)
            assert ok is False
            refreshed = svc.get_fulfillment_by_id(row.id)
            assert refreshed.status == FulfillmentStatus.AUTO_IN_PROGRESS
            auto = json.loads(refreshed.auto_result or "{}")
            assert auto.get("vip_activated") is True
        finally:
            db.close()
            engine.dispose()

    def test_g3_story_unlock_zero_debit(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709103
            db.add(User(telegram_id=tg, role=UserRole.USER))
            node = StoryNode(title="Cap Exclusivo", content="...", is_active=True)
            db.add(node)
            db.commit()
            db.refresh(node)
            pkg = Package(name="Story placeholder", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)
            product = StoreProduct(
                name="Fragmento Historia",
                price=100,
                stock=-1,
                package_id=pkg.id,
                story_node_id=node.id,
                fulfillment_kind=FulfillmentKind.STORY_UNLOCK,
                is_active=True,
            )
            db.add(product)
            db.commit()
            order = Order(user_id=tg, total_items=1, total_price=100, status=OrderStatus.COMPLETED)
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
            fulfill = FulfillmentService(db=db)
            fulfill.create_fulfillments_for_order(order.id)
            row = fulfill.get_fulfillment_for_order_item(item.id)
            story = StoryService(db=db)
            with patch.object(story.besito_service, "debit_besitos") as mock_debit:
                story.grant_node_access(tg, node.id, reference_fulfillment_id=row.id)
            mock_debit.assert_not_called()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_g4_user_input_manual_transitions(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709104
            db.add(User(telegram_id=tg, role=UserRole.USER))
            pkg = Package(name="Manual placeholder", is_active=True)
            db.add(pkg)
            db.commit()
            db.refresh(pkg)
            product = StoreProduct(
                name="Una Pregunta",
                price=100,
                stock=-1,
                package_id=pkg.id,
                delivery_mode=DeliveryMode.MANUAL,
                fulfillment_kind=FulfillmentKind.USER_INPUT_THEN_MANUAL,
                fulfillment_config='{"min_length": 3, "max_length": 100}',
                is_active=True,
            )
            db.add(product)
            db.commit()
            order = Order(user_id=tg, total_items=1, total_price=100, status=OrderStatus.COMPLETED)
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
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            assert row.status == FulfillmentStatus.PENDING_INPUT
            mock_bot = AsyncMock()
            ok, _ = await svc.submit_user_input(
                mock_bot, row.id, tg, "¿Cuál es tu favorito?"
            )
            assert ok
            db.refresh(row)
            assert row.status == FulfillmentStatus.PENDING_FULFILLMENT
            ok2, _ = await svc.admin_mark_fulfilled(
                mock_bot, row.id, 999, "Entregado con cariño"
            )
            assert ok2
            assert svc.get_fulfillment_by_id(row.id).status == FulfillmentStatus.FULFILLED
            ok3, msg3 = await svc.admin_mark_fulfilled(mock_bot, row.id, 999, "again")
            assert not ok3
            assert msg3
        finally:
            db.close()
            engine.dispose()

    def test_g5_monthly_cap_blocks_then_allows(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709105
            product, _ = self._seed_package_product(db, tg)
            product.monthly_stock_cap = 1
            db.commit()
            svc = FulfillmentService(db=db)
            assert svc.is_monthly_cap_available(product.id) is True
            order = Order(
                user_id=tg,
                total_items=1,
                total_price=50,
                status=OrderStatus.COMPLETED,
                completed_at=datetime.now(UTC),
            )
            db.add(order)
            db.flush()
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=1,
                unit_price=50,
                total_price=50,
            )
            db.add(item)
            db.commit()
            assert svc.is_monthly_cap_available(product.id) is False
            next_month = datetime.now().month % 12 + 1
            year = datetime.now().year + (1 if next_month == 1 else 0)
            assert svc.count_monthly_sales(product.id, year, next_month) == 0
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_g6_fulfillment_not_in_atomic_tx(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709106
            product, _ = self._seed_package_product(db, tg, price=50)
            store = StoreService(db=db)
            store.add_to_cart(tg, product.id, 1)
            order, _ = store.create_order(tg)
            mock_bot = AsyncMock()
            order_status_at_create: list = []
            real_create = FulfillmentService.create_fulfillments_for_order

            def spy_create(self, order_id: int):
                row = self._get_db().query(Order).filter(Order.id == order_id).first()
                order_status_at_create.append(row.status if row else None)
                return real_create(self, order_id)

            with patch.object(
                FulfillmentService, "create_fulfillments_for_order", spy_create
            ):
                with patch("services.fulfillment_service.PackageService") as MockPkg:
                    MockPkg.return_value.deliver_package_to_user = AsyncMock(
                        return_value=(True, "")
                    )
                    await store.complete_order(mock_bot, order.id)
            assert order_status_at_create == [OrderStatus.COMPLETED]
            assert db.query(OrderFulfillment).count() >= 1
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_g7_backpack_status_display(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709107
            product, _ = self._seed_package_product(db, tg)
            store = StoreService(db=db)
            store.add_to_cart(tg, product.id, 1)
            order, _ = store.create_order(tg)
            mock_bot = AsyncMock()
            with patch(
                "services.fulfillment_service.PackageService"
            ) as MockPkg:
                MockPkg.return_value.deliver_package_to_user = AsyncMock(
                    return_value=(True, "")
                )
                await store.complete_order(mock_bot, order.id)
            backpack = BackpackService(db=db)
            purchases = backpack.get_user_purchases(tg)
            assert purchases
            assert purchases[0].get("status_display")
            assert purchases[0].get("fulfillment_id")
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_early_access_manual_delivery_mode_auto_dispatches(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709108
            db.add(User(telegram_id=tg, role=UserRole.USER))
            pkg = Package(name="EA placeholder", is_active=True)
            db.add(pkg)
            db.commit()
            product = StoreProduct(
                name="Ventaja",
                price=100,
                stock=-1,
                package_id=pkg.id,
                delivery_mode=DeliveryMode.MANUAL,
                fulfillment_kind=FulfillmentKind.PRIVILEGE_EARLY_ACCESS,
                fulfillment_config='{"early_access_hours": 12}',
                is_active=True,
            )
            db.add(product)
            db.commit()
            svc = FulfillmentService(db=db)
            order = Order(user_id=tg, total_items=1, total_price=100, status=OrderStatus.COMPLETED)
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
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            assert row.status == FulfillmentStatus.AUTO_IN_PROGRESS
            mock_bot = AsyncMock()
            ok, _ = await svc.dispatch_fulfillment(mock_bot, row.id)
            assert ok
            assert row.status == FulfillmentStatus.FULFILLED
        finally:
            db.close()
            engine.dispose()

    def test_waitlist_position_increments(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg1, tg2 = 77709109, 77709110
            db.add(User(telegram_id=tg1, role=UserRole.USER))
            db.add(User(telegram_id=tg2, role=UserRole.USER))
            pkg = Package(name="WL", is_active=True)
            db.add(pkg)
            db.commit()
            product = StoreProduct(
                name="La Lista",
                price=100,
                stock=-1,
                package_id=pkg.id,
                delivery_mode=DeliveryMode.MANUAL,
                fulfillment_kind=FulfillmentKind.WAITLIST_ENTRY,
                is_active=True,
            )
            db.add(product)
            db.commit()
            svc = FulfillmentService(db=db)
            for tg in (tg1, tg2):
                order = Order(user_id=tg, total_items=1, total_price=100, status=OrderStatus.COMPLETED)
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
                svc.create_fulfillments_for_order(order.id)
                row = svc.get_fulfillment_for_order_item(item.id)
                import asyncio

                asyncio.run(svc.dispatch_fulfillment(AsyncMock(), row.id))
            entries = db.query(StoreWaitlistEntry).filter_by(product_id=product.id).all()
            positions = sorted(e.position for e in entries)
            assert positions == [1, 2]
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_g5_direct_purchase_blocked_when_cap_exhausted(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709111
            product, _ = self._seed_package_product(db, tg)
            product.monthly_stock_cap = 1
            db.commit()
            store = StoreService(db=db)
            order, err = store.direct_purchase(tg, product.id)
            assert order is not None
            mock_bot = AsyncMock()
            with patch("services.fulfillment_service.PackageService") as MockPkg:
                MockPkg.return_value.deliver_package_to_user = AsyncMock(return_value=(True, ""))
                await store.complete_order(mock_bot, order.id)
            order2, err2 = store.direct_purchase(tg, product.id)
            assert order2 is None
            assert err2
        finally:
            db.close()
            engine.dispose()

    def test_build_purchase_enrichment_activate_vip_from_raw_auto_result(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709112
            product, _ = self._seed_package_product(db, tg)
            product.fulfillment_kind = FulfillmentKind.VIP_GRANT
            db.commit()
            order = Order(user_id=tg, total_items=1, total_price=50, status=OrderStatus.COMPLETED)
            db.add(order)
            db.flush()
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=1,
                unit_price=50,
                total_price=50,
            )
            db.add(item)
            db.commit()
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            row.status = FulfillmentStatus.FULFILLED
            row.auto_result = (
                '{"vip_activated": true, "invite_link": "https://t.me/+vip", '
                '"tariff_name": "VIP", "token_code": "secret"}'
            )
            db.commit()
            enrichment = svc.build_purchase_enrichment(item.id)
            assert "resend_vip_invite" in enrichment["actions_available"]
            assert "token_code" not in enrichment["auto_result"]
            assert "token_url" not in enrichment["auto_result"]
            assert enrichment["auto_result"].get("invite_link") == "https://t.me/+vip"
            assert "user_input" not in enrichment
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_admin_deliver_package_idempotent_on_fulfilled(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709113
            product, pkg = self._seed_package_product(db, tg)
            product.fulfillment_kind = FulfillmentKind.PACKAGE_DEFERRED
            db.commit()
            order = Order(user_id=tg, total_items=1, total_price=50, status=OrderStatus.COMPLETED)
            db.add(order)
            db.flush()
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=1,
                unit_price=50,
                total_price=50,
            )
            db.add(item)
            db.commit()
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            row.status = FulfillmentStatus.FULFILLED
            row.auto_result = f'{{"package_id": {pkg.id}}}'
            db.commit()
            mock_bot = AsyncMock()
            with patch("services.fulfillment_service.PackageService") as MockPkg:
                MockPkg.return_value.deliver_package_to_user = AsyncMock(return_value=(True, ""))
                ok, _ = await svc.admin_deliver_package_from_queue(
                    mock_bot, row.id, pkg.id, 999
                )
            assert ok is True
            MockPkg.return_value.deliver_package_to_user.assert_not_called()
        finally:
            db.close()
            engine.dispose()

    def _scan_no_user_spanish(self, module_path: str) -> None:
        import ast
        import importlib
        from pathlib import Path

        mod = importlib.import_module(module_path)
        source = Path(mod.__file__).read_text()
        tree = ast.parse(source)
        doc_lines: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)
            ):
                doc = ast.get_docstring(node)
                if doc:
                    doc_lines.update(line.strip() for line in doc.splitlines())

        in_docstring = False
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.count('"""') == 2 and stripped.startswith('"""'):
                continue
            if stripped.count('"""') % 2 == 1:
                in_docstring = not in_docstring
            if in_docstring or not stripped or stripped.startswith("#"):
                continue
            if (
                "logger." in stripped
                or "LucienVoice." in stripped
                or "InlineKeyboardButton(" in stripped
                or "callback_data=" in stripped
            ):
                continue
            if stripped in doc_lines:
                continue
            if any(ch in stripped for ch in "áéíóúñ¿¡"):
                pytest.fail(
                    f"{module_path}: possible Spanish user-facing string: {stripped}"
                )

    def test_g8_no_user_spanish_in_fulfillment_service(self):
        self._scan_no_user_spanish("services.fulfillment_service")

    def test_g8_no_user_spanish_in_store_admin_handlers(self):
        self._scan_no_user_spanish("handlers.store_admin_handlers")

    def test_g8_no_user_spanish_in_fulfillment_admin_handlers(self):
        self._scan_no_user_spanish("handlers.fulfillment_admin_handlers")

    def test_g8_no_user_spanish_in_store_user_handlers(self):
        self._scan_no_user_spanish("handlers.store_user_handlers")

    def test_g8_no_user_spanish_in_backpack_handler(self):
        self._scan_no_user_spanish("handlers.backpack_handler")

    def test_service_user_messages_use_lucien_voice_contracts(self):
        """Behavioral SC5 contract: known user-facing tuples come from LucienVoice."""
        from utils.lucien_voice import LucienVoice

        assert LucienVoice.fulfillment_admin_input_required() == (
            LucienVoice.fulfillment_admin_input_required()
        )
        assert LucienVoice.fulfillment_retry_not_allowed() == (
            LucienVoice.fulfillment_retry_not_allowed()
        )
        assert LucienVoice.fulfillment_admin_package_mismatch() == (
            LucienVoice.fulfillment_admin_package_mismatch()
        )

    @pytest.mark.asyncio
    async def test_admin_mark_fulfilled_rejects_pending_input_without_user_input(
        self, tmp_path: Path
    ):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709120
            db.add(User(telegram_id=tg, role=UserRole.USER))
            pkg = Package(name="Input placeholder", is_active=True)
            db.add(pkg)
            db.commit()
            product = StoreProduct(
                name="Pregunta",
                price=100,
                stock=-1,
                package_id=pkg.id,
                delivery_mode=DeliveryMode.MANUAL,
                fulfillment_kind=FulfillmentKind.USER_INPUT_THEN_MANUAL,
                is_active=True,
            )
            db.add(product)
            db.commit()
            order = Order(
                user_id=tg, total_items=1, total_price=100, status=OrderStatus.COMPLETED
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
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            assert row.status == FulfillmentStatus.PENDING_INPUT
            ok, msg = await svc.admin_mark_fulfilled(
                AsyncMock(), row.id, 999, "Sin input del visitante"
            )
            assert ok is False
            assert msg == LucienVoice.fulfillment_admin_input_required()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_submit_user_input_notifies_admin_with_escaped_input(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709121
            db.add(User(telegram_id=tg, role=UserRole.USER))
            pkg = Package(name="Notify placeholder", is_active=True)
            db.add(pkg)
            db.commit()
            product = StoreProduct(
                name="Manual",
                price=100,
                stock=-1,
                package_id=pkg.id,
                delivery_mode=DeliveryMode.MANUAL,
                fulfillment_kind=FulfillmentKind.USER_INPUT_THEN_MANUAL,
                fulfillment_config='{"min_length": 1, "max_length": 100}',
                is_active=True,
            )
            db.add(product)
            db.commit()
            order = Order(
                user_id=tg, total_items=1, total_price=100, status=OrderStatus.COMPLETED
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
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            mock_bot = AsyncMock()
            with patch("services.fulfillment_service.bot_config") as mock_cfg:
                mock_cfg.ADMIN_IDS = [111, 222]
                ok, _ = await svc.submit_user_input(
                    mock_bot, row.id, tg, '<script>alert("x")</script>'
                )
            assert ok is True
            assert mock_bot.send_message.await_count == 2
            admin_text = mock_bot.send_message.await_args_list[0].kwargs.get("text", "")
            assert "&lt;script&gt;" in admin_text
            assert "<script>" not in admin_text
        finally:
            db.close()
            engine.dispose()

    def test_resolve_input_prompt_key_mapping(self):
        from services.fulfillment_service import _resolve_input_prompt_key
        from utils.lucien_voice import LucienVoice

        assert _resolve_input_prompt_key({"input_type": "session_theme"}) == "session_theme"
        assert _resolve_input_prompt_key({"prompt_key": "credit_name"}) == "credit_name"
        assert LucienVoice.fulfillment_input_prompt_for_key("session_theme") == (
            LucienVoice.fulfillment_input_prompt_director()
        )
        assert LucienVoice.fulfillment_input_prompt_for_key("credit_name") == (
            LucienVoice.fulfillment_input_prompt_credits()
        )

    def test_build_purchase_enrichment_matrix(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709122
            product, pkg = self._seed_package_product(db, tg)
            order = Order(
                user_id=tg, total_items=1, total_price=50, status=OrderStatus.COMPLETED
            )
            db.add(order)
            db.flush()
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=1,
                unit_price=50,
                total_price=50,
            )
            db.add(item)
            db.commit()
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)

            row.status = FulfillmentStatus.FAILED
            row.auto_result = '{"errors": "internal", "admin_notes": "secret"}'
            db.commit()
            enrich = svc.build_purchase_enrichment(item.id)
            assert "retry_delivery" in enrich["actions_available"]
            assert "errors" not in enrich["auto_result"]
            assert "admin_notes" not in enrich["auto_result"]

            product.fulfillment_kind = FulfillmentKind.STORY_UNLOCK
            node = StoryNode(title="Cap", content="...", is_active=True)
            db.add(node)
            db.commit()
            row.fulfillment_kind = FulfillmentKind.STORY_UNLOCK
            row.status = FulfillmentStatus.FULFILLED
            row.auto_result = '{"story_node_id": 1}'
            db.commit()
            enrich2 = svc.build_purchase_enrichment(item.id)
            assert "read_chapter" in enrich2["actions_available"]

            product.fulfillment_kind = FulfillmentKind.WAITLIST_ENTRY
            row.fulfillment_kind = FulfillmentKind.WAITLIST_ENTRY
            row.auto_result = '{"position": 3}'
            db.commit()
            enrich3 = svc.build_purchase_enrichment(item.id)
            assert "view_waitlist" in enrich3["actions_available"]

            row.status = FulfillmentStatus.AUTO_IN_PROGRESS
            db.commit()
            enrich4 = svc.build_purchase_enrichment(item.id)
            assert "retry_delivery" not in enrich4["actions_available"]

            product.fulfillment_kind = FulfillmentKind.USER_INPUT_THEN_MANUAL
            row.fulfillment_kind = FulfillmentKind.USER_INPUT_THEN_MANUAL
            row.status = FulfillmentStatus.PENDING_INPUT
            db.commit()
            enrich5 = svc.build_purchase_enrichment(item.id)
            assert "submit_input" in enrich5["actions_available"]
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_sanitize_auto_result_strips_token_url(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709123
            product, _ = self._seed_package_product(db, tg)
            product.fulfillment_kind = FulfillmentKind.VIP_GRANT
            db.commit()
            order = Order(
                user_id=tg, total_items=1, total_price=50, status=OrderStatus.COMPLETED
            )
            db.add(order)
            db.flush()
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=1,
                unit_price=50,
                total_price=50,
            )
            db.add(item)
            db.commit()
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            row.status = FulfillmentStatus.AUTO_IN_PROGRESS
            row.auto_result = (
                '{"vip_activated": true, "invite_link": "https://t.me/+vip", '
                '"tariff_name": "VIP"}'
            )
            db.commit()
            enrichment = svc.build_purchase_enrichment(item.id)
            assert "resend_vip_invite" in enrichment["actions_available"]
            assert "token_code" not in enrichment["auto_result"]
            assert "token_url" not in enrichment["auto_result"]
            mock_bot = AsyncMock()
            with patch("services.fulfillment_service.VIPService") as MockVip:
                MockVip.return_value.resend_vip_invite_for_user = AsyncMock(
                    return_value=(True, "VIP access", "https://t.me/+fresh")
                )
                ok, msg = await svc.resend_vip_invite_for_fulfillment(
                    mock_bot, tg, row.id
                )
            assert ok is True
            assert "VIP" in msg
            refreshed = svc.get_fulfillment_by_id(row.id)
            assert refreshed.status == FulfillmentStatus.FULFILLED
        finally:
            db.close()
            engine.dispose()

    def test_build_purchase_enrichment_resend_on_failed_with_vip_activated(
        self, tmp_path: Path
    ):
        """FAILED + vip_activated expone resend_vip_invite para recuperación en mochila."""
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709154
            product, _ = self._seed_package_product(db, tg)
            product.fulfillment_kind = FulfillmentKind.VIP_GRANT
            db.commit()
            order = Order(
                user_id=tg, total_items=1, total_price=50, status=OrderStatus.COMPLETED
            )
            db.add(order)
            db.flush()
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=1,
                unit_price=50,
                total_price=50,
            )
            db.add(item)
            db.commit()
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            row.status = FulfillmentStatus.FAILED
            row.auto_result = (
                '{"vip_activated": true, "subscription_id": 3, "token_id": 8, '
                '"tariff_name": "VIP"}'
            )
            db.commit()
            enrichment = svc.build_purchase_enrichment(item.id)
            assert "resend_vip_invite" in enrichment["actions_available"]
        finally:
            db.close()
            engine.dispose()

    def test_monthly_cap_mx_timezone_boundary(self, tmp_path: Path):
        from datetime import timedelta

        from services.fulfillment_service import _MX_TZ, _mx_month_bounds

        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709124
            product, _ = self._seed_package_product(db, tg)
            product.monthly_stock_cap = 1
            db.commit()
            svc = FulfillmentService(db=db)
            now_mx = datetime.now(_MX_TZ)
            start_utc, end_utc = _mx_month_bounds(now_mx.year, now_mx.month)

            order_before = Order(
                user_id=tg,
                total_items=1,
                total_price=50,
                status=OrderStatus.COMPLETED,
                completed_at=start_utc - timedelta(seconds=1),
            )
            db.add(order_before)
            db.flush()
            db.add(
                OrderItem(
                    order_id=order_before.id,
                    product_id=product.id,
                    product_name=product.name,
                    quantity=1,
                    unit_price=50,
                    total_price=50,
                )
            )
            db.commit()
            assert svc.count_monthly_completed_order_items(product.id) == 0

            order_after = Order(
                user_id=tg,
                total_items=1,
                total_price=50,
                status=OrderStatus.COMPLETED,
                completed_at=start_utc,
            )
            db.add(order_after)
            db.flush()
            db.add(
                OrderItem(
                    order_id=order_after.id,
                    product_id=product.id,
                    product_name=product.name,
                    quantity=1,
                    unit_price=50,
                    total_price=50,
                )
            )
            db.commit()
            assert svc.count_monthly_completed_order_items(product.id) == 1
            assert svc.is_monthly_cap_available(product.id) is False
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_complete_order_reserves_monthly_cap_for_pending_order(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709125
            product, _ = self._seed_package_product(db, tg, price=50)
            product.monthly_stock_cap = 1
            db.commit()
            store = StoreService(db=db)
            store.add_to_cart(tg, product.id, 1)
            order1, _ = store.create_order(tg)
            store.add_to_cart(tg, product.id, 1)
            order2, _ = store.create_order(tg)
            mock_bot = AsyncMock()
            with patch("services.fulfillment_service.PackageService") as MockPkg:
                MockPkg.return_value.deliver_package_to_user = AsyncMock(
                    return_value=(True, "")
                )
                ok1, _ = await store.complete_order(mock_bot, order1.id)
            assert ok1 is True
            with patch("services.fulfillment_service.PackageService") as MockPkg:
                MockPkg.return_value.deliver_package_to_user = AsyncMock(
                    return_value=(True, "")
                )
                ok2, err2 = await store.complete_order(mock_bot, order2.id)
            assert ok2 is False
            assert err2
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_retry_fulfillment_rejects_non_failed(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709126
            product, _ = self._seed_package_product(db, tg)
            order = Order(
                user_id=tg, total_items=1, total_price=50, status=OrderStatus.COMPLETED
            )
            db.add(order)
            db.flush()
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=1,
                unit_price=50,
                total_price=50,
            )
            db.add(item)
            db.commit()
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            row.status = FulfillmentStatus.FULFILLED
            db.commit()
            ok, msg = await svc.retry_fulfillment_delivery(AsyncMock(), tg, row.id)
            assert ok is False
            assert msg == LucienVoice.fulfillment_retry_not_allowed()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_retry_fulfillment_limit_reached(self, tmp_path: Path):
        from services.fulfillment_service import _MAX_PACKAGE_RETRIES

        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709127
            product, _ = self._seed_package_product(db, tg)
            order = Order(
                user_id=tg, total_items=1, total_price=50, status=OrderStatus.COMPLETED
            )
            db.add(order)
            db.flush()
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=1,
                unit_price=50,
                total_price=50,
            )
            db.add(item)
            db.commit()
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            row.status = FulfillmentStatus.FAILED
            row.retry_count = _MAX_PACKAGE_RETRIES
            db.commit()
            ok, msg = await svc.retry_fulfillment_delivery(AsyncMock(), tg, row.id)
            assert ok is False
            assert msg == LucienVoice.fulfillment_retry_limit_reached()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_retry_fulfillment_cooldown_enforced(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709128
            product, _ = self._seed_package_product(db, tg)
            order = Order(
                user_id=tg, total_items=1, total_price=50, status=OrderStatus.COMPLETED
            )
            db.add(order)
            db.flush()
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=1,
                unit_price=50,
                total_price=50,
            )
            db.add(item)
            db.commit()
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            row.status = FulfillmentStatus.FAILED
            row.last_attempt_at = datetime.now(UTC)
            db.commit()
            ok, msg = await svc.retry_fulfillment_delivery(AsyncMock(), tg, row.id)
            assert ok is False
            assert msg == LucienVoice.fulfillment_retry_cooldown()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_admin_deliver_package_rejects_package_mismatch(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709129
            product, pkg = self._seed_package_product(db, tg)
            product.fulfillment_kind = FulfillmentKind.PACKAGE_DEFERRED
            db.commit()
            order = Order(
                user_id=tg, total_items=1, total_price=50, status=OrderStatus.COMPLETED
            )
            db.add(order)
            db.flush()
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=1,
                unit_price=50,
                total_price=50,
            )
            db.add(item)
            db.commit()
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            row.status = FulfillmentStatus.PENDING_FULFILLMENT
            db.commit()
            ok, msg = await svc.admin_deliver_package_from_queue(
                AsyncMock(), row.id, 99, 999
            )
            assert ok is False
            assert msg == LucienVoice.fulfillment_admin_package_mismatch()
        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_admin_deliver_package_rejects_invalid_kind(self, tmp_path: Path):
        engine, TestSession = self._session(tmp_path)
        db = TestSession()
        try:
            tg = 77709130
            product, _ = self._seed_package_product(db, tg)
            product.fulfillment_kind = FulfillmentKind.USER_INPUT_THEN_MANUAL
            db.commit()
            order = Order(
                user_id=tg, total_items=1, total_price=50, status=OrderStatus.COMPLETED
            )
            db.add(order)
            db.flush()
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=1,
                unit_price=50,
                total_price=50,
            )
            db.add(item)
            db.commit()
            svc = FulfillmentService(db=db)
            svc.create_fulfillments_for_order(order.id)
            row = svc.get_fulfillment_for_order_item(item.id)
            row.status = FulfillmentStatus.PENDING_FULFILLMENT
            db.commit()
            ok, msg = await svc.admin_deliver_package_from_queue(
                AsyncMock(), row.id, 1, 999
            )
            assert ok is False
            assert msg == LucienVoice.fulfillment_admin_deliver_invalid_kind()
        finally:
            db.close()
            engine.dispose()


@pytest.mark.unit
class TestLucienVoiceFulfillmentSecurity:
    def test_fulfillment_admin_queue_item_escapes_user_input(self):
        text = LucienVoice.fulfillment_admin_queue_item(
            "Producto",
            1,
            123,
            "pending",
            '<script>alert("x")</script>',
        )
        assert "&lt;script&gt;" in text
        assert "<script>" not in text

    def test_fulfillment_admin_queue_item_escapes_product_name(self):
        text = LucienVoice.fulfillment_admin_queue_item(
            '<b>Evil</b>',
            1,
            123,
            "pending",
            None,
        )
        assert "&lt;b&gt;Evil&lt;/b&gt;" in text
        assert "<b>Evil</b>" not in text

    def test_store_product_detail_escapes_name_and_description(self):
        text = LucienVoice.store_product_detail(
            '<img onerror="x">',
            "<script>desc</script>",
            100,
            "tier<script>",
        )
        assert "&lt;img" in text
        assert "<script>" not in text
        assert "tier&lt;script&gt;" in text

    def test_backpack_purchases_list_escapes_product_name(self):
        from datetime import UTC, datetime

        purchases = [
            {
                "product_name": '<img onerror="x">',
                "total_price": 50,
                "purchased_at": datetime.now(UTC),
                "status_display": "Cumplido",
            }
        ]
        text = LucienVoice.backpack_purchases_list(purchases)
        assert "&lt;img" in text
        assert "<img" not in text

    def test_backpack_purchase_detail_escapes_product_name(self):
        from datetime import UTC, datetime

        text = LucienVoice.backpack_purchase_detail(
            {
                "product_name": "<b>Evil</b>",
                "purchased_at": datetime.now(UTC),
                "total_price": 100,
                "status_display": "OK",
            }
        )
        assert "&lt;b&gt;Evil&lt;/b&gt;" in text

    def test_backpack_fulfillment_toast_strips_html(self):
        plain = LucienVoice.backpack_fulfillment_toast_success("<b>OK</b> listo")
        assert "<b>" not in plain
        assert "OK" in plain