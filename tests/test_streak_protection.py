"""Tests for streak protection system (Phase 18)."""
import json
import pytest
from models.models import (
    StreakSession, StreakPromotionCodeStatus,
)
from services.streak_promotion_service import StreakPromotionService


class TestCalculateProtectionCost:
    def test_streak_0_costs_5(self, db_session):
        svc = StreakPromotionService(db_session)
        assert svc.calculate_protection_cost(0) == 5

    def test_streak_2_costs_5(self, db_session):
        svc = StreakPromotionService(db_session)
        assert svc.calculate_protection_cost(2) == 5

    def test_streak_3_costs_10(self, db_session):
        svc = StreakPromotionService(db_session)
        assert svc.calculate_protection_cost(3) == 10

    def test_streak_5_costs_10(self, db_session):
        svc = StreakPromotionService(db_session)
        assert svc.calculate_protection_cost(5) == 10

    def test_streak_6_costs_15(self, db_session):
        svc = StreakPromotionService(db_session)
        assert svc.calculate_protection_cost(6) == 15


class TestSessionManagement:
    def test_get_or_create_session_new(self, db_session, sample_streak_promotion):
        svc = StreakPromotionService(db_session)
        session = svc._get_or_create_session(99999, sample_streak_promotion.id)
        assert session is not None
        assert session.user_id == 99999
        assert session.promotion_id == sample_streak_promotion.id

    def test_get_or_create_session_reuses(self, db_session, sample_streak_promotion):
        svc = StreakPromotionService(db_session)
        s1 = svc._get_or_create_session(88888, sample_streak_promotion.id)
        s2 = svc._get_or_create_session(88888, sample_streak_promotion.id)
        assert s1.id == s2.id

    def test_get_active_session_returns_none_for_no_session(self, db_session):
        svc = StreakPromotionService(db_session)
        assert svc.get_active_session(77777) is None

    def test_cancel_session_codes(self, db_session, sample_streak_promotion):
        """Deliver a code via session, then cancel it."""
        svc = StreakPromotionService(db_session)
        from models.models import StreakPromotionCode
        code = db_session.query(StreakPromotionCode).filter(
            StreakPromotionCode.status == StreakPromotionCodeStatus.AVAILABLE
        ).first()
        assert code is not None

        # Simulate delivery through session
        session = svc._get_or_create_session(66666, sample_streak_promotion.id)
        code.status = StreakPromotionCodeStatus.DELIVERED
        code.user_id = 66666
        code.session_id = session.id
        session.codes_delivered = json.dumps([code.id])
        db_session.flush()

        # Cancel
        svc.cancel_session_codes(session.id)
        db_session.refresh(code)
        assert code.status == StreakPromotionCodeStatus.CANCELLED

    def test_close_session_retire_preserves_codes(self, db_session, sample_streak_promotion):
        svc = StreakPromotionService(db_session)
        from models.models import StreakPromotionCode
        code = db_session.query(StreakPromotionCode).filter(
            StreakPromotionCode.status == StreakPromotionCodeStatus.AVAILABLE
        ).first()
        code.status = StreakPromotionCodeStatus.DELIVERED
        code.user_id = 55555
        session = svc._get_or_create_session(55555, sample_streak_promotion.id)
        code.session_id = session.id
        session.codes_delivered = json.dumps([code.id])
        db_session.flush()

        svc.close_session(55555, retire=True)
        db_session.refresh(code)
        assert code.status == StreakPromotionCodeStatus.DELIVERED

    def test_close_session_no_retire_cancels_codes(self, db_session, sample_streak_promotion):
        svc = StreakPromotionService(db_session)
        from models.models import StreakPromotionCode
        code = db_session.query(StreakPromotionCode).filter(
            StreakPromotionCode.status == StreakPromotionCodeStatus.AVAILABLE
        ).first()
        code.status = StreakPromotionCodeStatus.DELIVERED
        code.user_id = 44444
        session = svc._get_or_create_session(44444, sample_streak_promotion.id)
        code.session_id = session.id
        session.codes_delivered = json.dumps([code.id])
        db_session.flush()

        svc.close_session(44444, retire=False)
        db_session.refresh(code)
        assert code.status == StreakPromotionCodeStatus.CANCELLED
