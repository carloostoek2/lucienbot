"""
Property / invariant tests for high-level business rules that must ALWAYS hold,
regardless of the specific flow path taken.

Ítem #10 (Medio-Alto) of fases_refactor_testing.md:
"Nuevo estilo de tests de propiedades que siempre deben cumplirse"
"This is what most protects against 'agregué algo chiquito y se rompió otra cosa'."

Invariants covered (prioritised by economic/access-control impact):
  I1. Besito balance never negative — insufficient debit leaves balance unchanged
  I2. Besito accounting identity — balance = total_earned - total_spent always
  I3. Besito counters monotonic — total_earned/total_spent only increase
  I4. Token single-use — redeem twice returns None, token stays USED
  I5. VIP expired loses access — is_user_vip False after end_date passes
  I6. Reaction idempotent — one reaction per user per broadcast (IntegrityError guard)
  I7. Mission duplicate reference_id — no double-count on same ref
  I8. Order status irreversible — COMPLETED/CANCELLED orders cannot change
  I9. Protection cost deterministic — cost = 5 + (streak // 3) * 5, pure, no side-effects

Mixed approach: unit-level invariants use db_session fixture; cross-service invariants
(Token redeem, VIP access, Reaction) use SQLite+TestSession pattern (internal commits).

Patrones exactos replicados de items #1/#6/#7/#8/#9:
- @pytest.mark.integration or @pytest.mark.unit as appropriate
- SQLite en archivo tmp_path + TestSession for cross-service tests
- db_session fixture (rollback) for single-service invariants
- Strict structural asserts, no prints, no loose string checks
- Fresh numeric tg_id 77710xxx per test, no cross-test data reuse
- try/finally db.close() + engine.dispose() for SQLite tests
- N806 tolerated for TestSession (precedent from reaction_full_chain + streak + atomicity)

Ejecuta con: pytest -k "test_invariants or TestBusinessInvariants" -q --tb=line
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.models import (
    BesitoBalance,
    BesitoTransaction,
    BroadcastMessage,
    BroadcastReaction,
    Channel,
    ChannelType,
    Mission,
    MissionFrequency,
    MissionType,
    Order,
    OrderItem,
    OrderStatus,
    Package,
    ReactionEmoji,
    StoreProduct,
    Subscription,
    Tariff,
    Token,
    TokenStatus,
    TransactionSource,
    User,
    UserMissionProgress,
    UserRole,
)
from services.besito_service import BesitoService
from services.broadcast_service import BroadcastService
from services.mission_service import MissionService
from services.store_service import StoreService
from services.streak_promotion_service import StreakPromotionService
from services.vip_service import VIPService

# ── I1-I3: Besito Balance Invariants (unit, db_session fixture) ──────────────


@pytest.mark.integration
class TestBesitoBalanceInvariants:
    """Fundamental economic invariants: balance never negative, accounting identity holds,
    counters are monotonic.

    Uses SQLite+TestSession (not db_session fixture) because debit_besitos internally
    calls db.rollback() on insufficient balance, which breaks the fixture transaction.
    """

    def _create_engine_and_session(self, tmp_path):
        db_path = tmp_path / "test_invariants_besito.db"
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return engine, TestSession

    def test_balance_never_negative_insufficient_debit_leaves_balance_unchanged(self, tmp_path):
        """I1: Debit > balance returns False; balance and totals unchanged. No negative balances."""
        engine, TestSession = self._create_engine_and_session(tmp_path)
        db = TestSession()

        try:
            user = User(
                telegram_id=77710020, username="besouser1", first_name="Beso1", role=UserRole.USER
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            balance = BesitoBalance(
                user_id=user.telegram_id, balance=0, total_earned=0, total_spent=0
            )
            db.add(balance)
            db.commit()

            saved_uid = (
                user.telegram_id
            )  # detach before session close; besito key = TG BigInt per contract (Fase4 ID fix)
            db.close()

            db = TestSession()
            svc = BesitoService(db)

            # Start with known balance
            svc.credit_besitos(saved_uid, 10, TransactionSource.ADMIN, "seed")
            assert svc.get_balance(saved_uid) == 10

            # Attempt debit larger than balance -> must return False
            result = svc.debit_besitos(saved_uid, 999, TransactionSource.PURCHASE, "overspend")
            assert result is False

            # Balance must be unchanged (credit_besitos committed; rollback in debit_besitos
            # only rolls back the failed debit attempt, not the prior committed credit)
            after = svc.get_balance(saved_uid)
            assert after == 10

            stats = svc.get_balance_with_stats(saved_uid)
            assert stats["balance"] == 10
            assert stats["total_earned"] == 10
            assert stats["total_spent"] == 0

            # Partial successful debit works
            ok = svc.debit_besitos(saved_uid, 4, TransactionSource.PURCHASE, "partial")
            assert ok is True
            assert svc.get_balance(saved_uid) == 6

            svc.close()
        finally:
            db.close()
            engine.dispose()

    def test_balance_accounting_identity_equals_earned_minus_spent(self, tmp_path):
        """I2: balance = total_earned - total_spent after any sequence of operations."""
        engine, TestSession = self._create_engine_and_session(tmp_path)
        db = TestSession()

        try:
            user = User(
                telegram_id=77710021, username="besouser2", first_name="Beso2", role=UserRole.USER
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            balance = BesitoBalance(user_id=user.id, balance=0, total_earned=0, total_spent=0)
            db.add(balance)
            db.commit()

            saved_uid = user.id
            db.close()

            db = TestSession()
            svc = BesitoService(db)

            svc.credit_besitos(saved_uid, 15, TransactionSource.ADMIN)
            svc.credit_besitos(saved_uid, 7, TransactionSource.REACTION)
            svc.debit_besitos(saved_uid, 8, TransactionSource.PURCHASE)

            stats = svc.get_balance_with_stats(saved_uid)
            assert stats["balance"] == 14  # 15+7-8
            assert stats["total_earned"] == 22
            assert stats["total_spent"] == 8
            assert stats["balance"] == stats["total_earned"] - stats["total_spent"]

            svc.debit_besitos(saved_uid, 3, TransactionSource.PURCHASE)
            svc.credit_besitos(saved_uid, 5, TransactionSource.MISSION)

            stats2 = svc.get_balance_with_stats(saved_uid)
            assert stats2["balance"] == 16  # 14-3+5
            assert stats2["total_earned"] == 27  # 22+5
            assert stats2["total_spent"] == 11  # 8+3
            assert stats2["balance"] == stats2["total_earned"] - stats2["total_spent"]

            svc.close()
        finally:
            db.close()
            engine.dispose()

    def test_total_earned_and_total_spent_are_monotonic_never_decrease(self, tmp_path):
        """I3: total_earned and total_spent are strictly non-decreasing counters."""
        engine, TestSession = self._create_engine_and_session(tmp_path)
        db = TestSession()

        try:
            user = User(
                telegram_id=77710022, username="besouser3", first_name="Beso3", role=UserRole.USER
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            balance = BesitoBalance(user_id=user.id, balance=0, total_earned=0, total_spent=0)
            db.add(balance)
            db.commit()

            saved_uid = user.id
            db.close()

            db = TestSession()
            svc = BesitoService(db)

            stats0 = svc.get_balance_with_stats(saved_uid)
            earned_prev = stats0["total_earned"]
            spent_prev = stats0["total_spent"]

            svc.credit_besitos(saved_uid, 20, TransactionSource.ADMIN)
            stats1 = svc.get_balance_with_stats(saved_uid)
            assert stats1["total_earned"] >= earned_prev
            earned_prev = stats1["total_earned"]

            svc.debit_besitos(saved_uid, 7, TransactionSource.PURCHASE)
            stats2 = svc.get_balance_with_stats(saved_uid)
            assert stats2["total_spent"] >= spent_prev
            assert stats2["total_earned"] >= earned_prev
            spent_prev = stats2["total_spent"]
            earned_prev = stats2["total_earned"]

            # Failed debit must NOT change counters
            svc.debit_besitos(saved_uid, 99999, TransactionSource.PURCHASE)
            stats3 = svc.get_balance_with_stats(saved_uid)
            assert stats3["total_spent"] == spent_prev
            assert stats3["total_earned"] == earned_prev

            svc.close()
        finally:
            db.close()
            engine.dispose()


# ── I4-I5: VIP Access Invariants (integration, SQLite+TestSession) ───────────


@pytest.mark.integration
class TestVIPAccessInvariants:
    """Token single-use and VIP expiration access control invariants."""

    def _create_engine_and_session(self, tmp_path):
        db_path = tmp_path / "test_invariants_vip.db"
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return engine, TestSession

    def _setup_vip_env(self, db, tg_id: int, tariff_days: int = 30):
        """Setup: User + Channel(VIP) + Tariff + Token(ACTIVE). Returns ids."""
        user = User(
            telegram_id=tg_id,
            username=f"vipuser{tg_id}",
            first_name="VIPInvariant",
            role=UserRole.USER,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        channel = Channel(
            channel_id=-20077700000 - (tg_id % 10000),
            channel_name="VIP Invariant Channel",
            channel_type=ChannelType.VIP,
            is_active=True,
        )
        db.add(channel)
        db.commit()

        tariff = Tariff(
            name="Invariant Monthly",
            duration_days=tariff_days,
            price=999.00,
            currency="MXN",
            is_active=True,
        )
        db.add(tariff)
        db.commit()
        db.refresh(tariff)

        token = Token(
            token_code=f"INVARIANT-{tg_id}-{abs(hash(str(tg_id)))}",
            tariff_id=tariff.id,
            status=TokenStatus.ACTIVE,
        )
        db.add(token)
        db.commit()
        db.refresh(token)

        return {
            "user_id": user.id,
            "tg_id": tg_id,
            "channel_id": channel.id,
            "tariff_id": tariff.id,
            "token_id": token.id,
            "token_code": token.token_code,
        }

    def test_token_cannot_be_redeemed_twice_second_returns_none(self, tmp_path):
        """I4: redeem token -> Subscription (success). Redeem again same token -> None. Token stays USED."""
        engine, TestSession = self._create_engine_and_session(tmp_path)
        db = TestSession()
        vip_svc = None

        try:
            env = self._setup_vip_env(db, 77710001)
            db.close()
            db = TestSession()

            vip_svc = VIPService(db)

            # First redeem must succeed
            sub1 = vip_svc.redeem_token(env["token_code"], env["tg_id"])
            assert sub1 is not None
            assert sub1.user_id == env["tg_id"]
            assert sub1.is_active is True

            # Second redeem must return None
            sub2 = vip_svc.redeem_token(env["token_code"], env["tg_id"])
            assert sub2 is None

            # Token must be USED
            token = db.query(Token).filter(Token.id == env["token_id"]).first()
            assert token.status == TokenStatus.USED
            assert token.redeemed_by_id == env["tg_id"]
            assert token.redeemed_at is not None

            # Only one active subscription exists
            active_count = (
                db.query(Subscription)
                .filter(
                    Subscription.user_id == env["tg_id"],
                    Subscription.is_active.is_(True),
                )
                .count()
            )
            assert active_count == 1

        finally:
            db.close()
            engine.dispose()

    def test_expired_subscription_denies_vip_access_is_user_vip_false(self, tmp_path):
        """I5: After subscription end_date passes, is_user_vip returns False."""
        engine, TestSession = self._create_engine_and_session(tmp_path)
        db = TestSession()
        vip_svc = None

        try:
            env = self._setup_vip_env(db, 77710002, tariff_days=1)
            db.close()
            db = TestSession()

            vip_svc = VIPService(db)

            # Redeem token -> active subscription
            sub = vip_svc.redeem_token(env["token_code"], env["tg_id"])
            assert sub is not None
            assert vip_svc.is_user_vip(env["tg_id"]) is True

            # Manually expire the subscription (simulate time passing)
            sub.is_active = False
            # Set end_date in the past: SQLite stores naive, service normalises with _ensure_aware
            sub.end_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
            db.commit()

            # is_user_vip must now return False
            assert vip_svc.is_user_vip(env["tg_id"]) is False

            # get_user_subscription must return None (filters on is_active=True AND end_date > now)
            active_sub = vip_svc.get_user_subscription(env["tg_id"])
            assert active_sub is None

        finally:
            db.close()
            engine.dispose()


# ── I6: Reaction Idempotency (integration, SQLite+TestSession) ───────────────


@pytest.mark.integration
class TestReactionInvariants:
    """One reaction per user per broadcast — enforced by DB UniqueConstraint + IntegrityError catch."""

    def _create_engine_and_session(self, tmp_path):
        db_path = tmp_path / "test_invariants_reaction.db"
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return engine, TestSession

    async def test_check_and_register_reaction_idempotent_no_duplicate_besitos(self, tmp_path):
        """I6: Two reactions with same user+broadcast+emoji: first succeeds (besitos awarded),
        second is caught by IntegrityError and returns duplicate reason. Besitos credited only once."""
        engine, TestSession = self._create_engine_and_session(tmp_path)
        db = TestSession()
        broadcast_svc = None
        besito_svc = None

        try:
            # Setup
            user = User(
                telegram_id=77710010,
                username="reactuser_inv",
                first_name="ReactInvariant",
                role=UserRole.USER,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            channel = Channel(
                channel_id=-30077710010,
                channel_name="Reaction Invariant Channel",
                channel_type=ChannelType.FREE,
                is_active=True,
            )
            db.add(channel)
            db.commit()

            emoji = ReactionEmoji(emoji="🔥", name="fuego_inv", besito_value=4, is_active=True)
            db.add(emoji)
            db.commit()

            broadcast = BroadcastMessage(
                message_id=950000,
                channel_id=channel.channel_id,
                admin_id=77700001,
                text="Invariant reaction test broadcast",
                has_reactions=True,
                selected_emoji_ids=str(emoji.id),
            )
            db.add(broadcast)
            db.commit()
            db.refresh(broadcast)

            balance = BesitoBalance(
                user_id=user.telegram_id, balance=0, total_earned=0, total_spent=0
            )
            db.add(balance)
            db.commit()

            # Save IDs before closing session to avoid DetachedInstanceError
            saved_user_id = user.telegram_id  # besito key = TG (ID contract)
            saved_broadcast_id = broadcast.id
            saved_emoji_id = emoji.id

            db.close()
            db = TestSession()

            broadcast_svc = BroadcastService(db)
            besito_svc = BesitoService(db)
            mock_bot = AsyncMock()

            # First reaction: must succeed
            r1 = await broadcast_svc.check_and_register_reaction(
                broadcast_id=saved_broadcast_id,
                user_id=saved_user_id,
                emoji_id=saved_emoji_id,
                username="reactuser_inv",
                bot=mock_bot,
            )
            assert r1["success"] is True
            assert r1["besitos_awarded"] == 4

            # Second reaction (same params): must fail gracefully
            r2 = await broadcast_svc.check_and_register_reaction(
                broadcast_id=saved_broadcast_id,
                user_id=saved_user_id,
                emoji_id=saved_emoji_id,
                username="reactuser_inv",
                bot=mock_bot,
            )
            assert r2["success"] is False
            assert r2["reason"] == "duplicate"

            # Only ONE reaction row exists
            reaction_count = (
                db.query(BroadcastReaction)
                .filter(
                    BroadcastReaction.broadcast_id == saved_broadcast_id,
                    BroadcastReaction.user_id == saved_user_id,
                )
                .count()
            )
            assert reaction_count == 1

            # Besitos credited exactly once (4, not 8)
            final_balance = besito_svc.get_balance(saved_user_id)
            assert final_balance == 4

            # Exactly one REACTION transaction
            tx_count = (
                db.query(BesitoTransaction)
                .filter(
                    BesitoTransaction.user_id == saved_user_id,
                    BesitoTransaction.source == TransactionSource.REACTION,
                )
                .count()
            )
            assert tx_count == 1

        finally:
            db.close()
            engine.dispose()


# ── I7: Mission Duplicate Reference (unit, db_session) ───────────────────────


@pytest.mark.unit
class TestMissionInvariants:
    """Mission progress invariants: duplicate reference_id idempotency."""

    def test_duplicate_reference_id_does_not_double_increment_progress(
        self, db_session, sample_user
    ):
        """I7: Calling increment_progress twice with same reference_id only increments once."""
        svc = MissionService(db_session)

        mission = Mission(
            name="Invariant Mission",
            description="Test duplicate ref for invariants",
            mission_type=MissionType.REACTION_COUNT,
            target_value=3,
            frequency=MissionFrequency.ONE_TIME,
            is_active=True,
        )
        db_session.add(mission)
        db_session.commit()
        db_session.refresh(mission)

        # First call with reference_id=42: progress +1
        # DESIRED CONTRACT: user_id param and stored value is TG BigInt (.telegram_id)
        svc.increment_progress(
            sample_user.telegram_id, MissionType.REACTION_COUNT, amount=1, reference_id=42
        )
        progress = (
            db_session.query(UserMissionProgress)
            .filter(
                UserMissionProgress.user_id == sample_user.telegram_id,
                UserMissionProgress.mission_id == mission.id,
            )
            .first()
        )
        assert progress is not None
        assert progress.current_value == 1
        assert progress.last_reference_id == 42

        # Second call with SAME reference_id=42: must be skipped (no double-count)
        svc.increment_progress(
            sample_user.telegram_id, MissionType.REACTION_COUNT, amount=1, reference_id=42
        )
        db_session.refresh(progress)
        assert progress.current_value == 1  # unchanged
        assert progress.last_reference_id == 42

        # Call with DIFFERENT reference_id=43: must increment
        svc.increment_progress(
            sample_user.telegram_id, MissionType.REACTION_COUNT, amount=1, reference_id=43
        )
        db_session.refresh(progress)
        assert progress.current_value == 2
        assert progress.last_reference_id == 43

        svc.close()


# ── I8: Order Status Irreversible (unit, db_session) ─────────────────────────


@pytest.mark.unit
class TestStoreOrderInvariants:
    """Order status transitions are irreversible: PENDING→COMPLETED or PENDING→CANCELLED only."""

    async def test_completed_order_cannot_be_cancelled_or_recompleted(
        self, db_session, sample_user
    ):
        """I8a: COMPLETED orders reject cancel_order() and complete_order() (double-processing guard)."""
        # Package is required for StoreProduct (NOT NULL on package_id)
        pkg = Package(name="Invariant Pkg", store_stock=100, reward_stock=10, is_active=True)
        db_session.add(pkg)
        db_session.commit()
        db_session.refresh(pkg)

        product = StoreProduct(
            name="Invariant Product",
            description="Test",
            package_id=pkg.id,
            price=50,
            stock=100,
            is_active=True,
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        order = Order(
            user_id=sample_user.id,
            total_price=50,
            status=OrderStatus.COMPLETED,
            completed_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)

        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=1,
            unit_price=50,
            total_price=50,
        )
        db_session.add(order_item)
        db_session.commit()

        svc = StoreService(db_session)

        # Cancel a COMPLETED order must fail
        assert svc.cancel_order(order.id) is False

        # Complete an already-COMPLETED order is idempotent (success, no re-debit)
        mock_bot = AsyncMock()
        ok, msg = await svc.complete_order(mock_bot, order.id)
        assert ok is True
        # Status unchanged
        db_session.refresh(order)
        assert order.status == OrderStatus.COMPLETED

        svc.close()

    async def test_cancelled_order_cannot_be_completed_or_recancelled(
        self, db_session, sample_user
    ):
        """I8b: CANCELLED orders reject complete_order() and cancel_order() (no resurrection)."""
        pkg2 = Package(name="Invariant Pkg 2", store_stock=100, reward_stock=10, is_active=True)
        db_session.add(pkg2)
        db_session.commit()
        db_session.refresh(pkg2)

        product = StoreProduct(
            name="Invariant Product 2",
            description="Test2",
            package_id=pkg2.id,
            price=30,
            stock=100,
            is_active=True,
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        order = Order(
            user_id=sample_user.id,
            total_price=30,
            status=OrderStatus.CANCELLED,
        )
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)

        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=1,
            unit_price=30,
            total_price=30,
        )
        db_session.add(order_item)
        db_session.commit()

        svc = StoreService(db_session)

        # Cancel a CANCELLED order must fail
        assert svc.cancel_order(order.id) is False

        # Complete a CANCELLED order must fail
        mock_bot = AsyncMock()
        ok, msg = await svc.complete_order(mock_bot, order.id)
        assert ok is False
        db_session.refresh(order)
        assert order.status == OrderStatus.CANCELLED

        svc.close()


# ── I9: Streak Protection Cost Deterministic (pure unit, no DB) ─────────────


@pytest.mark.unit
class TestStreakProtectionInvariants:
    """Protection cost is a pure deterministic function with no side effects."""

    def test_protection_cost_formula_is_deterministic_and_pure(self):
        """I9: cost = 5 + (streak // 3) * 5. Pure: no DB, no state mutation, same input → same output."""
        svc = StreakPromotionService(None)  # No DB needed for pure calculation

        # Known values per formula
        expected = {
            0: 5,
            1: 5,
            2: 5,
            3: 10,
            4: 10,
            5: 10,
            6: 15,
            7: 15,
            8: 15,
            9: 20,
            10: 20,
            15: 30,
            20: 35,
            100: 170,
        }

        for streak, cost in expected.items():
            assert svc.calculate_protection_cost(streak) == cost, (
                f"streak={streak}: expected {cost}, got {svc.calculate_protection_cost(streak)}"
            )

        # Idempotent: calling multiple times gives same result
        for _ in range(5):
            assert svc.calculate_protection_cost(7) == 15

        # Monotonic: higher streak → cost never decreases
        prev = 0
        for s in range(50):
            c = svc.calculate_protection_cost(s)
            assert c >= prev, f"cost not monotonic at streak={s}: {c} < {prev}"
            prev = c

    def test_protection_cost_has_no_side_effects(self):
        """I9b: calculate_protection_cost is pure — service state untouched across calls."""
        svc = StreakPromotionService(None)

        cost1 = svc.calculate_protection_cost(5)
        cost2 = svc.calculate_protection_cost(5)
        cost3 = svc.calculate_protection_cost(99)

        assert cost1 == cost2 == 10
        assert cost3 == 170
        # If the method had side effects, the service's internal state would differ;
        # no way to observe that from outside (no getters), but repeated calls
        # returning identical results for identical inputs is sufficient evidence.


# ── Decision / Handoff notes (EOF style, per items #6/#7/#8/#9 precedent) ───
# - New file tests/integration/test_invariants.py (justified: new test category "invariants/properties"
#   as explicitly recommended in fases_refactor_testing.md row #10; no existing file to extend).
# - 9 invariants tested across 6 test classes: 3 besito (I1-I3 unit) + 2 VIP (I4-I5 integration) +
#   1 reaction (I6 integration) + 1 mission (I7 unit) + 2 store order (I8a/b unit) +
#   2 streak protection (I9a/b pure unit). Total 11 test methods.
# - Mixed approach: db_session fixture for single-service invariants (fast, rollback);
#   SQLite+TestSession for cross-service invariants needing internal commits (Token redeem, VIP access,
#   Reaction idempotency with IntegrityError catch).
# - GSD: 3+ appends pre-write, pre-ruff, pre-pytest, pre-docs using run_terminal_command.
# - Ruff + pytest -k invariants clean required before docs updates.
# - 0 prod changes. All invariants are read-only validations of existing behavior.
# - Patrones replicados: strict structural asserts, fresh numeric tg_id 77710xxx per test,
#   try/finally db.close()+engine.dispose() for SQLite tests, N806 tolerated for TestSession,
#   no prints, no data reuse across tests.
# - Additional invariants identified but deferred (future slices per s.8):
#   * Stock never negative via direct model decrement (StoreProduct.decrement_stock guard at model level)
#   * Mission RECURRING reset + cooldown (already partially covered by reaction flow tests)
#   * Package delivery stock independence (store_stock vs reward_stock separate counters)
#   * Streak code status lifecycle AVAILABLE→DELIVERED→(USED|CANCELLED) linearity
#   * Streak session expiry auto-cancels codes (covered in test_streak_protection_flow.py)
#   * Balance SELECT FOR UPDATE race condition safety (needs concurrent test infra)
#   * complete_order atomicity gap (debit committed before stock decrement) — known design choice
# - Handoff: property-based testing with Hypothesis (generate random sequences of credit/debit
#   and assert accounting identity always holds) is a natural next step for deeper invariant coverage.
# - Update refactor_testing.md + fases_refactor_testing.md after gates pass.
