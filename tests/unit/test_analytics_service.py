import csv
import os
from datetime import UTC, datetime, timedelta

import pytest

from models.models import (
    BesitoBalance,
    BesitoTransaction,
    Subscription,
    TransactionSource,
    TransactionType,
    User,
    UserRole,
)
from services.analytics_service import AnalyticsService


@pytest.mark.unit
class TestAnalyticsService:
    def test_get_dashboard_stats_keys(self, db_session):
        service = AnalyticsService(db_session)
        stats = service.get_dashboard_stats()
        assert set(stats.keys()) == {
            "total_users",
            "active_vip",
            "total_besitos",
            "expiring_soon",
            "new_today",
        }

    def test_get_dashboard_stats_total_besitos(self, db_session, sample_user, sample_admin):
        """DESIRED CONTRACT: user_id in BesitoBalance always matches User.telegram_id (TG BigInt, not PK .id)."""
        service = AnalyticsService(db_session)
        bb1 = BesitoBalance(
            user_id=sample_user.telegram_id, balance=100, total_earned=100, total_spent=0
        )
        bb2 = BesitoBalance(
            user_id=sample_admin.telegram_id, balance=200, total_earned=200, total_spent=0
        )
        db_session.add(bb1)
        db_session.add(bb2)
        db_session.commit()
        stats = service.get_dashboard_stats()
        assert stats["total_besitos"] == 300

    def test_get_dashboard_stats_expiring_soon(
        self, db_session, sample_user, sample_vip_channel, sample_token
    ):
        """DESIRED CONTRACT: Subscription.user_id = TG BigInt (telegram_id)."""
        service = AnalyticsService(db_session)
        sub = Subscription(
            user_id=sample_user.telegram_id,
            channel_id=sample_vip_channel.id,
            token_id=sample_token.id,
            end_date=datetime.now(UTC) + timedelta(hours=12),
            is_active=True,
        )
        db_session.add(sub)
        db_session.commit()
        stats = service.get_dashboard_stats()
        assert stats["expiring_soon"] >= 1

    def test_get_dashboard_stats_new_today(self, db_session):
        """DESIRED CONTRACT: new users keyed by TG; analytics uses telegram_id."""
        service = AnalyticsService(db_session)
        fresh_tg = 77709001
        user = User(telegram_id=fresh_tg, username="todayuser", role=UserRole.USER)
        db_session.add(user)
        db_session.commit()
        stats = service.get_dashboard_stats()
        assert stats["new_today"] >= 1

    def test_export_users_csv(self, db_session, sample_user):
        """DESIRED CONTRACT: export uses TG keys; service close hygiene even for injected.
        NOTE (pre-existing security): uses NamedTemporaryFile(delete=False) + no unlink; PII lingers on disk. Canary comment for when fixed (tests-only; no prod this tirón).
        """
        service = AnalyticsService(db_session)
        try:
            path = service.export_users_csv()
            assert path is not None
            assert os.path.exists(path)
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert "telegram_id" in reader.fieldnames
                assert any(r["telegram_id"] == str(sample_user.telegram_id) for r in rows)
        finally:
            service.close()  # no-op for injected but documents contract

    def test_export_users_csv_no_users(self, db_session):
        service = AnalyticsService(db_session)
        # Delete all users directly
        db_session.query(User).delete()
        db_session.commit()
        assert service.export_users_csv() is None

    def test_export_activity_csv(self, db_session, sample_user):
        """DESIRED CONTRACT: Besito* user_id = telegram_id TG (not .id); tx reflects TG."""
        service = AnalyticsService(db_session)
        bb = BesitoBalance(
            user_id=sample_user.telegram_id, balance=10, total_earned=10, total_spent=0
        )
        db_session.add(bb)
        db_session.commit()
        tx = BesitoTransaction(
            user_id=sample_user.telegram_id,
            amount=10,
            type=TransactionType.CREDIT,
            source=TransactionSource.DAILY_GIFT,
        )
        db_session.add(tx)
        db_session.commit()
        path = service.export_activity_csv()
        assert path is not None
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert "amount" in reader.fieldnames
            assert any(r["user_id"] == str(sample_user.telegram_id) for r in rows)

    def test_export_activity_csv_no_transactions(self, db_session):
        service = AnalyticsService(db_session)
        db_session.query(BesitoTransaction).delete()
        db_session.commit()
        assert service.export_activity_csv() is None

    # ==================== Slice 1 economy stats tests ====================
    def test_get_economy_overview_keys_and_values(self, db_session, sample_user):
        """DESIRED CONTRACT: economy reads use TG keys; best-effort read-only."""
        service = AnalyticsService(db_session)
        bb = BesitoBalance(
            user_id=sample_user.telegram_id, balance=50, total_earned=120, total_spent=70
        )
        db_session.add(bb)
        db_session.commit()
        stats = service.get_economy_overview(window_days=None)
        assert stats["status"] == "ok"
        assert stats["total_ever_earned"] == 120
        assert stats["total_ever_spent"] == 70
        assert stats["circulation"] == 50
        assert stats["net_flow"] == 50
        assert "burn_rate_pct" in stats
        assert stats["window_days"] is None

    def test_get_source_attribution_credits_only(self, db_session, sample_user):
        """DESIRED CONTRACT: attribution aggregates by TG user_id keys (credits only)."""
        service = AnalyticsService(db_session)
        bb = BesitoBalance(
            user_id=sample_user.telegram_id, balance=0, total_earned=0, total_spent=0
        )
        db_session.add(bb)
        db_session.commit()
        tx1 = BesitoTransaction(
            user_id=sample_user.telegram_id,
            amount=30,
            type=TransactionType.CREDIT,
            source=TransactionSource.REACTION,
        )
        tx2 = BesitoTransaction(
            user_id=sample_user.telegram_id,
            amount=20,
            type=TransactionType.CREDIT,
            source=TransactionSource.DAILY_GIFT,
        )
        tx3 = BesitoTransaction(
            user_id=sample_user.telegram_id,
            amount=-10,
            type=TransactionType.DEBIT,
            source=TransactionSource.PURCHASE,
        )
        db_session.add_all([tx1, tx2, tx3])
        db_session.commit()
        attr = service.get_source_attribution(window_days=None)
        assert attr["status"] == "ok"
        sources = {s["source"]: s for s in attr["sources"]}
        assert "reaction" in sources
        assert sources["reaction"]["total"] == 30
        assert sources["daily_gift"]["total"] == 20
        # Only CREDITs counted
        assert attr["total_credits"] == 50
        # % check
        assert any(s["pct"] > 0 for s in attr["sources"])

    def test_get_top_earners_order_and_net(self, db_session, sample_user, sample_admin):
        """DESIRED CONTRACT: top earners ordered by earned, use TG keys."""
        service = AnalyticsService(db_session)
        b1 = BesitoBalance(
            user_id=sample_user.telegram_id, balance=10, total_earned=150, total_spent=140
        )
        b2 = BesitoBalance(
            user_id=sample_admin.telegram_id, balance=200, total_earned=300, total_spent=100
        )
        db_session.add_all([b1, b2])
        db_session.commit()
        top = service.get_top_earners(limit=5)
        assert len(top) >= 2
        # Highest earned first
        assert top[0]["total_earned"] == 300
        assert top[0]["net"] == 200
        assert top[1]["total_earned"] == 150
        assert "username" in top[0]

    def test_get_economy_methods_degraded_on_error(self, db_session):
        service = AnalyticsService(db_session)
        # Force error path (best-effort) - direct assign on _get_db is documented test seam for internal error injection (public API would require heavier mocking of queries; aligns with Health/Analytics read-only best-effort pattern)
        original = service._get_db

        def boom():
            raise RuntimeError("simulated")

        service._get_db = boom
        try:
            ov = service.get_economy_overview()
            sa = service.get_source_attribution()
            te = service.get_top_earners()
            assert ov["status"] == "degraded"
            assert sa["status"] == "degraded"
            assert te == []  # empty list on error for top (per impl)
        finally:
            service._get_db = original
