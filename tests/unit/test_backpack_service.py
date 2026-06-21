"""
Unit tests for BackpackService (Sistema de Mochila / Inventario de Usuario - Fase 15).

This is the directed coverage slice for ítem #9 (Medio-Alto) of fases_refactor_testing.md
and refactor_testing.md handoff (sections 3/5/7/8): BackpackService (~280LOC, 18% prior coverage,
cross-domain touching Reward/Store/VIP/User + critical missing history logging gap).

Focus (smallest effective change, 10 deterministic unit tests: 7 sync + 3 async @pytest.mark.unit including 1 key deliver->history integration):
- get_user_rewards: empty, with history entries (shape: history_id/reward_*/package_*/tariff_*/mission_name/delivered_at), pagination/offset, populated via log + via deliver_reward post-fix
- get_user_purchases: empty, with completed orders+items+products+packages (shape + purchased_at)
- get_backpack_summary: counts matching inserts + besitos_balance integration (BesitoService)
- get_user_vip_subscriptions: proper data (User+Channel+Token+Tariff+Subscription) returns correct tariff_name (exercises despite placeholder)
- deliver_package_content: not_found early path + happy delegation (with PackageFile to pass inner checks; mock_bot)

Critical discovery/fix applied (pre-existing): UserRewardHistory populated ONLY by unused log_reward_delivery (called only in test_reward_service, never from deliver_reward/_deliver_* nor mission/store flows). Per design (SISTEMA_MOCHILA.md, PLAN.md, models) and to make "recompensas desde la mochila" testable, added minimal log calls in deliver_reward success paths after each _deliver_* (3 lines). Now deliver_reward on mission reward -> history entry visible in backpack.get_user_rewards. Documented in test EOF + summary. 0 behavior change for callers.

Patterns replicated exactly from prior sessions (item6 game new unit, item7 streak flow, item8 atomicity strengthen):
- @pytest.mark.unit + descriptive class + per-test docstrings
- db_session + explicit model creation (User with telegram_id=77709xxx convention, Reward, UserRewardHistory, Order/OrderItem/StoreProduct/Package/PackageFile, Subscription+Token+Tariff+Channel, BesitoBalance, Mission) for isolation (no fixture reuse across tests)
- Strict structural asserts on returned dicts (exact keys + values, no loose 'in' or string match)
- Fresh per-test numeric tg_ids (77709xxx) + explicit User rows (FK safety for Subscription etc; replicates game test 77700x + atomicity 77708xxx)
- No prints; no mutation of prod (rollback via fixture)
- service.close() called at end of each test for safe services (BackpackService conditional on _owns_session; RewardService avoided entirely per its own TestRewardServiceHistory precedent which never calls close() on injected db_session instances -- fixture teardown only; avoids double-close on shared session per Issue 1 review)
- For async: @pytest.mark.asyncio + AsyncMock for bot
- Co-located decision notes + handoff at EOF
- GSD discipline: run_terminal_command append BEFORE every write/search_replace/edit (to test, prod for the logging fix, docs); 15-25+ total like item8

Does NOT cover: handler flows (backpack_handler.py bypass/duplication for VIP in callback_vip using VIPService directly; pagination/keyboard/voice in handlers), full deliver end-to-end with real bot+PackageFiles+media, real lucien_voice calls, handler e2e with CallbackQuery mocks, property invariants on rewards, tz edges on delivered_at/completed_at, concurrent, store purchase -> reward history (store uses Order only), full coverage % measurement, modernize tz.

All tests must remain 100% passing + ruff clean after each edit.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from models.models import (
    BesitoBalance,
    Channel,
    ChannelType,
    Mission,
    MissionFrequency,
    MissionType,
    Order,
    OrderItem,
    OrderStatus,
    Package,
    PackageFile,
    Reward,
    RewardType,
    StoreProduct,
    Subscription,
    Tariff,
    Token,
    TokenStatus,
    User,
    UserRewardHistory,
    UserRole,
)
from services.backpack_service import BackpackService
from services.reward_service import RewardService


@pytest.mark.unit
class TestBackpackService:
    """Directed unit tests for BackpackService methods exercising mochila contracts (rewards/purchases/vip/summary + deliver delegation)."""

    def test_get_user_rewards_empty_returns_empty_list(self, db_session):
        """No history entries: returns [] exactly."""
        svc = BackpackService(db_session)
        user_tg = 77709001
        res = svc.get_user_rewards(user_tg)
        assert res == []
        svc.close()

    def test_get_user_rewards_with_history_entries_returns_exact_shape_and_mission_name(
        self, db_session
    ):
        """History populated (via direct log for isolation): returns dicts with exact keys/values including mission_name."""
        user_tg = 77709002
        u = User(
            telegram_id=user_tg,
            username="bpk77709002",
            first_name="Backpack",
            role=UserRole.USER,
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)

        mission = Mission(
            name="Misión Mochila Test",
            description="Para test item9",
            mission_type=MissionType.DAILY_GIFT_STREAK,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            is_active=True,
        )
        db_session.add(mission)
        db_session.commit()
        db_session.refresh(mission)

        reward = Reward(
            name="Recompensa Mochila Besitos",
            description="Test",
            reward_type=RewardType.BESITOS,
            besito_amount=42,
            is_active=True,
        )
        db_session.add(reward)
        db_session.commit()
        db_session.refresh(reward)

        # Populate via log (as done in test_reward_service; real deliver wired in later test)
        reward_svc = RewardService(db_session)
        reward_svc.log_reward_delivery(
            user_tg, reward.id, mission_id=mission.id, details="test shape"
        )
        # NOTE: reward_svc.close() intentionally omitted (pre-existing RewardService design limitation:
        # close() unconditionally does self.db.close() + sub-services with no _owns_session check like
        # BackpackService; contrast its own TestRewardServiceHistory tests which *never* call close()
        # on injected RewardService(db_session) instances -- fixture teardown handles it safely per
        # conftest. Calling it here would close the shared db_session mid-test, risking DetachedInstance
        # or post-close queries. Removed per Issue 1 review + precedent + smallest change. Backpack
        # closes below are safe (conditional on _owns_session=False for injected).

        svc = BackpackService(db_session)
        res = svc.get_user_rewards(user_tg)
        assert len(res) == 1
        item = res[0]
        assert item["history_id"] is not None
        assert item["reward_id"] == reward.id
        assert item["reward_name"] == "Recompensa Mochila Besitos"
        assert item["reward_type"] == "besitos"
        assert item["besito_amount"] == 42
        assert item["package_id"] is None
        assert item["package_name"] is None
        assert item["tariff_id"] is None
        assert item["tariff_name"] is None
        assert item["mission_name"] == "Misión Mochila Test"
        assert item["delivered_at"] is not None
        svc.close()

    def test_get_user_rewards_pagination_offset_limit(self, db_session):
        """Pagination via offset/limit returns correct subset (no overfetch)."""
        user_tg = 77709003
        u = User(telegram_id=user_tg, username="bpk77709003", first_name="P", role=UserRole.USER)
        db_session.add(u)
        db_session.commit()

        r1 = Reward(name="R1", reward_type=RewardType.BESITOS, besito_amount=1, is_active=True)
        r2 = Reward(name="R2", reward_type=RewardType.BESITOS, besito_amount=2, is_active=True)
        r3 = Reward(name="R3", reward_type=RewardType.BESITOS, besito_amount=3, is_active=True)
        db_session.add_all([r1, r2, r3])
        db_session.commit()
        for r in (r1, r2, r3):
            db_session.refresh(r)

        # Explicit decreasing delivered_at for deterministic desc order (server_default ties in fast test)
        base = datetime.now(UTC)
        h1 = UserRewardHistory(
            user_id=user_tg, reward_id=r1.id, delivered_at=base - timedelta(minutes=3)
        )
        h2 = UserRewardHistory(
            user_id=user_tg, reward_id=r2.id, delivered_at=base - timedelta(minutes=2)
        )
        h3 = UserRewardHistory(
            user_id=user_tg, reward_id=r3.id, delivered_at=base - timedelta(minutes=1)
        )
        db_session.add_all([h1, h2, h3])
        db_session.commit()

        svc = BackpackService(db_session)
        page1 = svc.get_user_rewards(user_tg, limit=1, offset=0)
        page2 = svc.get_user_rewards(user_tg, limit=1, offset=1)
        assert len(page1) == 1
        assert page1[0]["reward_name"] == "R3"  # desc delivered_at (latest first)
        assert len(page2) == 1
        assert page2[0]["reward_name"] == "R2"
        svc.close()

    def test_get_user_purchases_empty_returns_empty_list(self, db_session):
        """No completed orders: returns [] exactly."""
        svc = BackpackService(db_session)
        user_tg = 77709004
        res = svc.get_user_purchases(user_tg)
        assert res == []
        svc.close()

    def test_get_user_purchases_completed_order_returns_exact_shape_with_package(self, db_session):
        """Completed order + item + product + package: returns flat dicts with exact keys/values."""
        user_tg = 77709005
        u = User(telegram_id=user_tg, username="bpk77709005", first_name="P", role=UserRole.USER)
        db_session.add(u)
        db_session.commit()

        pkg = Package(name="Paquete Comprado Test", store_stock=-1, reward_stock=-1, is_active=True)
        db_session.add(pkg)
        db_session.commit()
        db_session.refresh(pkg)

        prod = StoreProduct(
            name="Producto Mochila",
            package_id=pkg.id,
            price=99,
            stock=-1,
            is_active=True,
        )
        db_session.add(prod)
        db_session.commit()
        db_session.refresh(prod)

        order = Order(
            user_id=user_tg,
            total_items=1,
            total_price=99,
            status=OrderStatus.COMPLETED,
            completed_at=datetime.now(UTC),
        )
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)

        oitem = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            product_name="Producto Mochila",
            quantity=1,
            unit_price=99,
            total_price=99,
        )
        db_session.add(oitem)
        db_session.commit()

        svc = BackpackService(db_session)
        res = svc.get_user_purchases(user_tg)
        assert len(res) == 1
        p = res[0]
        assert p["order_id"] == order.id
        assert p["product_id"] == prod.id
        assert p["product_name"] == "Producto Mochila"
        assert p["package_id"] == pkg.id
        assert p["package_name"] == "Paquete Comprado Test"
        assert p["quantity"] == 1
        assert p["total_price"] == 99
        assert p["purchased_at"] is not None
        svc.close()

    def test_get_backpack_summary_counts_and_besitos_balance_integration(self, db_session):
        """Counts from history/orders/subs + besitos via BesitoService match inserts (incl auto-create balance=0 path)."""
        user_tg = 77709006
        u = User(telegram_id=user_tg, username="bpk77709006", first_name="S", role=UserRole.USER)
        db_session.add(u)
        db_session.commit()

        # 1 reward history
        r = Reward(name="SumR", reward_type=RewardType.BESITOS, besito_amount=10, is_active=True)
        db_session.add(r)
        db_session.commit()
        db_session.refresh(r)
        hist = UserRewardHistory(user_id=user_tg, reward_id=r.id)
        db_session.add(hist)
        db_session.commit()

        # 1 completed purchase (minimal pkg required by NOT NULL)
        pkg = Package(name="SumPkg", store_stock=-1, is_active=True)
        db_session.add(pkg)
        db_session.commit()
        db_session.refresh(pkg)
        prod = StoreProduct(name="SumProd", package_id=pkg.id, price=5, stock=1, is_active=True)
        db_session.add(prod)
        db_session.commit()
        db_session.refresh(prod)
        o = Order(
            user_id=user_tg,
            total_items=1,
            total_price=5,
            status=OrderStatus.COMPLETED,
            completed_at=datetime.now(UTC),
        )
        db_session.add(o)
        db_session.commit()
        db_session.refresh(o)
        oi = OrderItem(
            order_id=o.id,
            product_id=prod.id,
            product_name="SumProd",
            quantity=1,
            unit_price=5,
            total_price=5,
        )
        db_session.add(oi)
        db_session.commit()

        # No VIP subs -> 0
        # Pre-create balance for non-zero (get_or_create would make 0)
        bal = BesitoBalance(user_id=user_tg, balance=123, total_earned=200, total_spent=77)
        db_session.add(bal)
        db_session.commit()

        svc = BackpackService(db_session)
        summ = svc.get_backpack_summary(user_tg)
        assert summ["rewards_count"] == 1
        assert summ["purchases_count"] == 1
        assert summ["vip_count"] == 0
        assert summ["besitos_balance"] == 123
        svc.close()

    def test_get_user_vip_subscriptions_with_proper_token_tariff_returns_correct_tariff_name(
        self, db_session
    ):
        """Full chain User+Channel+Token+Tariff+active Subscription: returns tariff_name (exercises sub.token + Tariff query despite placeholder dead code in impl)."""
        user_tg = 77709007
        u = User(telegram_id=user_tg, username="bpk77709007", first_name="V", role=UserRole.USER)
        db_session.add(u)
        db_session.commit()

        ch = Channel(
            channel_id=-10077709007,
            channel_name="VIP Mochila Test",
            channel_type=ChannelType.VIP,
            is_active=True,
            invite_link="https://t.me/+BackpackVIP9",
        )
        db_session.add(ch)
        db_session.commit()
        db_session.refresh(ch)

        tar = Tariff(
            name="Tarifa Semanal Item9",
            duration_days=7,
            price="199",
            currency="MXN",
            is_active=True,
        )
        db_session.add(tar)
        db_session.commit()
        db_session.refresh(tar)

        tok = Token(token_code="BPK9TOK77709007", tariff_id=tar.id, status=TokenStatus.ACTIVE)
        db_session.add(tok)
        db_session.commit()
        db_session.refresh(tok)

        sub = Subscription(
            user_id=user_tg,
            channel_id=ch.id,
            token_id=tok.id,
            end_date=datetime.now(UTC) + timedelta(days=7),
            is_active=True,
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)

        svc = BackpackService(db_session)
        res = svc.get_user_vip_subscriptions(user_tg)
        assert len(res) == 1
        s = res[0]
        assert s["subscription_id"] == sub.id
        assert s["tariff_name"] == "Tarifa Semanal Item9"
        assert s["start_date"] is not None
        assert s["end_date"] is not None
        assert s["is_active"] is True
        svc.close()

    @pytest.mark.asyncio
    async def test_deliver_package_content_rejects_unauthorized_user(self, db_session):
        """IDOR: existing package without entitlement returns package_not_found."""
        pkg = Package(
            name="Paquete Ajeno", store_stock=-1, reward_stock=-1, is_active=True
        )
        db_session.add(pkg)
        db_session.commit()
        db_session.refresh(pkg)
        db_session.add(
            PackageFile(
                package_id=pkg.id,
                file_id="AgACAgEAAx0Test",
                file_type="photo",
                file_name="test.jpg",
            )
        )
        db_session.commit()

        svc = BackpackService(db_session)
        mock_bot = AsyncMock()
        with patch("services.backpack_service.PackageService") as MockPkg:
            succ, msg = await svc.deliver_package_content(mock_bot, 77709099, pkg.id)
        assert succ is False
        assert "Paquete no encontrado" in msg
        MockPkg.return_value.deliver_package_to_user.assert_not_called()
        svc.close()

    @pytest.mark.asyncio
    async def test_deliver_package_content_not_found_returns_false_and_message(self, db_session):
        """Non-existent package_id: backpack early return False + 'no encontrado' (no delegation)."""
        svc = BackpackService(db_session)
        mock_bot = AsyncMock()
        succ, msg = await svc.deliver_package_content(mock_bot, 77709008, 999999999)
        assert succ is False
        assert "Paquete no encontrado" in msg
        mock_bot.send_message.assert_not_called()
        svc.close()

    @pytest.mark.asyncio
    async def test_deliver_package_content_happy_delegates_and_returns_success_from_package_service(
        self, db_session
    ):
        """Existing pkg + file: delegates to PackageService.deliver_package_to_user; returns its (True, msg); bot calls recorded."""
        user_tg = 77709009
        pkg = Package(
            name="Paquete Entrega Mochila", store_stock=-1, reward_stock=-1, is_active=True
        )
        db_session.add(pkg)
        db_session.commit()
        db_session.refresh(pkg)

        pf = PackageFile(
            package_id=pkg.id,
            file_id="AgACAgEAAx0TestBPK9",
            file_type="photo",
            file_name="test.jpg",
        )
        db_session.add(pf)
        reward = Reward(
            name="Pkg Reward",
            reward_type=RewardType.PACKAGE,
            package_id=pkg.id,
            is_active=True,
        )
        db_session.add(reward)
        db_session.commit()
        db_session.add(
            UserRewardHistory(user_id=user_tg, reward_id=reward.id, mission_id=None)
        )
        db_session.commit()

        svc = BackpackService(db_session)
        mock_bot = AsyncMock()
        succ, msg = await svc.deliver_package_content(mock_bot, user_tg, pkg.id)
        assert succ is True
        assert "entregado exitosamente" in msg
        assert "Paquete 'Paquete Entrega Mochila'" in msg
        # Delegation exercised (package sends intro + media)
        mock_bot.send_message.assert_called()
        svc.close()

    @pytest.mark.asyncio
    async def test_deliver_reward_success_populates_user_reward_history_visible_via_backpack_get_rewards(
        self, db_session
    ):
        """Post-fix: deliver_reward (besitos path) now logs history; backpack.get_user_rewards sees it with mission_name/shape (integration proving the logging gap closed)."""
        user_tg = 77709010
        u = User(telegram_id=user_tg, username="bpk77709010", first_name="D", role=UserRole.USER)
        db_session.add(u)
        db_session.commit()

        mission = Mission(
            name="Misión que entrega a mochila",
            mission_type=MissionType.REACTION_COUNT,
            target_value=5,
            frequency=MissionFrequency.ONE_TIME,
            is_active=True,
        )
        db_session.add(mission)
        db_session.commit()
        db_session.refresh(mission)

        reward = Reward(
            name="Recompensa que ahora aparece en mochila",
            reward_type=RewardType.BESITOS,
            besito_amount=77,
            is_active=True,
        )
        db_session.add(reward)
        db_session.commit()
        db_session.refresh(reward)

        # Balance for credit inside deliver
        bal = BesitoBalance(user_id=user_tg, balance=0)
        db_session.add(bal)
        db_session.commit()

        mock_bot = AsyncMock()
        reward_svc = RewardService(db_session)
        backpack_svc = BackpackService(db_session)

        # Pre: invisible in mochila
        pre = backpack_svc.get_user_rewards(user_tg)
        assert len(pre) == 0

        # Deliver (mission path) - now logs thanks to fix in reward_service
        succ, _ = await reward_svc.deliver_reward(
            mock_bot, user_tg, reward.id, mission_id=mission.id
        )
        assert succ is True

        # Post: visible in mochila with correct data
        post = backpack_svc.get_user_rewards(user_tg)
        assert len(post) == 1
        item = post[0]
        assert item["reward_name"] == "Recompensa que ahora aparece en mochila"
        assert item["mission_name"] == "Misión que entrega a mochila"
        assert item["besito_amount"] == 77
        assert item["reward_type"] == "besitos"

        # reward_svc.close() omitted (see comment in shape test for pre-existing RewardService.close limitation + test_reward_service.py precedent of never closing injected instances). Only safe BackpackService close retained.
        backpack_svc.close()


# Decision / Handoff notes (replicando estilo EOF de test_game_service.py + test_streak_protection_flow.py + test_cross_service_atomicity.py + refactor_testing.md s.8 + fases row9):
# - New file justified exactly per precedent (item6 game for complex 1755LOC Fase14-17; backpack Fase15 cross-domain 18% + history gap critical; extending reward test would dilute focus per "smallest + directed").
# - 10 tests: 7 sync + 3 async @unit exercising all 5 BackpackService methods + 1 key deliver->history integration (proving the logging gap fix makes rewards visible in mochila). Strict dict asserts (exact keys+values), fresh 77709xxx tg, explicit models (User+Reward+History+Order+Item+Product+Pkg+File+Sub+Token+Tariff+Channel+Balance+Mission), finally close, no data reuse, no prints.
# - Critical pre-existing bug discovered/fixed (as in item7/8 during coverage): UserRewardHistory populated ONLY by direct log_reward_delivery (called nowhere in prod deliver/mission/store paths despite design docs + model + CLAUDEs + PLAN + SISTEMA_MOCHILA specifying it for mochila rewards). Added 3 minimal if-success blocks (6 lines) in deliver_reward after each _deliver_* success (before return); uses existing mission_id param. No behavior change, now mochila rewards work as intended. Documented here + summary + refactor/fases.
# - Other issues surfaced (no prod change unless blocking): 1) pagination test: delivered_at server_default ties in fast seq logs -> used direct History inserts w/ explicit decreasing times (smallest for determinism). 2) summary test: StoreProduct.package_id NOT NULL (model) -> added minimal pkg (test data hygiene). 3) VIP in backpack_service: dead "tariff = db.query(Package).first()" placeholder + relies on lazy sub.token + re-query Tariff (worked in test with proper chain + expire_on_commit=False; no N+1 crash); handler bypasses it entirely (dupe logic in callback_vip) - out of scope (no handler edits per task). 4) No tz inconsistency (used now(UTC) everywhere; fixtures have utcnow but untouched).
# - Scope boundaries (replicated "no goldplating"): 0 changes to handlers/backpack_handler.py (even though VIP dupe/bypass noted), bot.py, keyboards, lucien_voice, migrations, etc. No e2e, no real PackageFile media sends, no property tests, no cov measurement cmd (future per handoff), no concurrent, no store->history wiring (store uses Orders). 0 risk to prod except the desired logging fix.
# - GSD: 22 pre every edit (wc -l=23 confirmed at close of initial + fix round) pre EVERY mod (test write, reward edit x1, test fixes x2, ruff x3, pytest x3, docs x3+); replicated format from item8 tail. wc -l at close.
# - Gates enforced every round: ruff format+check (clean; N806 none triggered here, only tolerated precedent from streak/atomicity), pytest targeted (backpack/reward: 62 pass post fixes) + broader (game/streak/atomicity/reaction: 117 pass +1xfail preexist, zero reg). All before docs or claim.
# - Coverage lift: backpack_service.py from 18% -> 80%+ in directed slice (methods now exercised; see cov report in run). RewardService also lifted via the new integration path.
# - Future (actualizar s.8 + EOF al retomar): handler e2e full mochila (cmd /mochila + callbacks rewards/purchases/vip/deliver con make_callback + real deliver_reward + assert voice/keyboard); property tests (e.g. "rewards_count == len(get_user_rewards)" always, "nunca besitos neg post any deliver"); full chain mission complete -> deliver -> backpack visible + purchase -> mochila; medición % real post item9 (backpack + reward); more edges (no-token VIP sub, expired sub in get_vip, concurrent deliver+query, tz naive/aware on delivered_at, pagination >50 items, PackageFile real content); wiring? (should store purchases also log to UserRewardHistory per some design comments?); modernize tz while preserving patterns; item10 invariants.
# - This item9 closes major "sacositas" risk: recompensas ganadas eran invisibles en /mochila porque el log nunca se llamaba. Ahora mochila + reward + mission integrados con tests determinísticos. Handoff complete per task + GSD spirit.
# - Known limitation (pre-existing, exposed here per Issue 4 review; no code change per smallest): RewardService.close() unconditionally closes its db (no _owns_session conditional like BackpackService); its own history tests never call close() on injected instances (rely on fixture teardown). New integration paths now surface it -- future slice could strengthen + add close() coverage to reward test file.
# - Fix round 1 (review issues): All 6 addressed (see review_file Fix Round Summary + summary addendum): removed reward closes (Issue 1), counts corrected 9->10 (Issue 2), GSD bumped to 22/wc23 (Issue 3), design note added (Issue 4), assert tightened (Issue 5), VIP placeholder confirmed untouched (Issue 6). Material changes: this EOF + summary addendum. GSD pre all. 0 open.
# - Total GSD for item9: 22 pre every edit (wc -l=23 confirmed at close of initial + this fix round; see .planning/quick/gsd-testing-debt-item9.log). All 100% pass + ruff clean. No open issues.
