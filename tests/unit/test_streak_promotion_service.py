"""Unit tests for StreakPromotionService -- Phase 17."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from services.streak_promotion_service import StreakPromotionService
from models.models import (
    StreakPromotion,
    StreakPromotionCode,
    StreakPromotionCodeStatus,
    StreakPromotionStatus,
    StreakPromotionRedemption,
    BesitoBalance,
    GameRecord,
)


@pytest.mark.unit
class TestStreakPromotionService:
    """Tests for StreakPromotionService covering creation, claiming, activation,
    and GameService integration hook."""

    def test_create_promotion_with_levels(self, db_session):
        """Verify promotion creation with multiple levels generates codes."""
        service = StreakPromotionService(db_session)
        levels = [
            {"consecutive_required": 3, "discount_pct": 10, "codes_available": 5},
            {"consecutive_required": 5, "discount_pct": 20, "codes_available": 3},
            {"consecutive_required": 10, "discount_pct": 30, "codes_available": 1},
        ]
        promo = service.create_promotion(
            name="Test Levels Promotion",
            description="Promo with 3 levels",
            levels=levels,
            duration_mode="dates",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
        )
        assert promo is not None
        assert promo.name == "Test Levels Promotion"
        assert len(promo.levels) == 3
        total_codes = 0
        for level in promo.levels:
            codes = [
                c for c in level.codes
            ]
            assert len(codes) == level.codes_available
            total_codes += len(codes)
        assert total_codes == 5 + 3 + 1

    def test_claim_for_streak_delivers_code(self, db_session):
        """Verify eligible streak returns code dict with code, discount_pct, promotion_name."""
        service = StreakPromotionService(db_session)
        levels = [
            {"consecutive_required": 5, "discount_pct": 20, "codes_available": 3},
        ]
        promo = service.create_promotion(
            name="Streak Claim Test",
            description="Desc",
            levels=levels,
            duration_mode="dates",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
        )
        promo.is_active = True
        promo.status = StreakPromotionStatus.ACTIVE
        db_session.commit()

        result = service.claim_for_streak(
            user_id=123, game_type="trivia", streak=5
        )
        assert result is not None
        assert "code" in result
        assert "discount_pct" in result
        assert "promotion_name" in result
        assert result["discount_pct"] == 20
        assert result["promotion_name"] == "Streak Claim Test"

        # Verify code status updated
        code = (
            db_session.query(StreakPromotionCode)
            .filter(StreakPromotionCode.code_value == result["code"])
            .first()
        )
        assert code is not None
        assert code.status == StreakPromotionCodeStatus.DELIVERED

        # Verify redemption record exists
        redemption = (
            db_session.query(StreakPromotionRedemption)
            .filter(StreakPromotionRedemption.user_id == 123)
            .first()
        )
        assert redemption is not None
        assert redemption.streak_achieved == 5

    def test_prevent_duplicate_claim(self, db_session):
        """Verify D-15: second claim for same user+level returns None."""
        service = StreakPromotionService(db_session)
        levels = [
            {"consecutive_required": 5, "discount_pct": 20, "codes_available": 5},
        ]
        promo = service.create_promotion(
            name="Dupe Test",
            description="Desc",
            levels=levels,
            duration_mode="dates",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
        )
        promo.is_active = True
        promo.status = StreakPromotionStatus.ACTIVE
        db_session.commit()

        # First claim succeeds
        result1 = service.claim_for_streak(
            user_id=123, game_type="trivia", streak=5
        )
        assert result1 is not None

        # Second claim for same user+streak returns None (duplicate prevention)
        result2 = service.claim_for_streak(
            user_id=123, game_type="trivia", streak=5
        )
        assert result2 is None

    def test_code_uniqueness(self, db_session):
        """Verify D-11: all generated codes are unique across the promotion."""
        service = StreakPromotionService(db_session)
        levels = [
            {"consecutive_required": 3, "discount_pct": 10, "codes_available": 10},
            {"consecutive_required": 5, "discount_pct": 20, "codes_available": 5},
        ]
        promo = service.create_promotion(
            name="Uniqueness Test",
            description="Desc",
            levels=levels,
            duration_mode="dates",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
        )
        all_codes = []
        for level in promo.levels:
            for code in level.codes:
                all_codes.append(code.code_value)
        assert len(set(all_codes)) == len(all_codes)

    def test_inactive_promotion_does_not_deliver(self, db_session):
        """Verify D-06: inactive promos do not return codes."""
        service = StreakPromotionService(db_session)
        levels = [
            {"consecutive_required": 3, "discount_pct": 10, "codes_available": 5},
        ]
        service.create_promotion(
            name="Inactive Test",
            description="Desc",
            levels=levels,
            duration_mode="dates",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
        )
        # Do NOT activate the promotion
        result = service.claim_for_streak(
            user_id=123, game_type="trivia", streak=3
        )
        assert result is None

    def test_available_count_reflects_delivered(self, db_session):
        """Verify D-13: remaining = codes_available - delivered."""
        service = StreakPromotionService(db_session)
        levels = [
            {"consecutive_required": 5, "discount_pct": 20, "codes_available": 10},
        ]
        promo = service.create_promotion(
            name="Count Test",
            description="Desc",
            levels=levels,
            duration_mode="dates",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
        )
        promo.is_active = True
        promo.status = StreakPromotionStatus.ACTIVE
        db_session.commit()

        # Claim 3 times with different users
        for uid in [1, 2, 3]:
            result = service.claim_for_streak(
                user_id=uid, game_type="trivia", streak=5
            )
            assert result is not None

        stats = service.get_redemption_stats(promo.id)
        assert len(stats["levels"]) == 1
        level_stats = stats["levels"][0]
        assert level_stats["total_codes"] == 10
        assert level_stats["delivered_count"] == 3
        assert level_stats["remaining"] == 7

    def test_promotion_with_dates_mode(self, db_session):
        """Verify dates-duration mode promotion appears in active promotions."""
        service = StreakPromotionService(db_session)
        now = datetime.utcnow()
        levels = [
            {"consecutive_required": 3, "discount_pct": 10, "codes_available": 3},
        ]
        promo = service.create_promotion(
            name="Dates Mode Promo",
            description="Desc",
            levels=levels,
            duration_mode="dates",
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
        )
        assert promo.duration_mode == "dates"
        assert promo.start_date is not None
        assert promo.end_date is not None

        # Before activation, should NOT appear in active promotions
        active = service.get_active_promotions()
        assert promo not in active

        # Activate
        service.activate(promo.id)
        active = service.get_active_promotions()
        assert promo in active

        # Deactivate and verify removal
        service.deactivate(promo.id)
        active = service.get_active_promotions()
        assert promo not in active

    def test_promotion_with_relative_duration(self, db_session):
        """Verify relative-duration promotion stores duration_hours correctly."""
        service = StreakPromotionService(db_session)
        levels = [
            {"consecutive_required": 3, "discount_pct": 10, "codes_available": 3},
        ]
        promo = service.create_promotion(
            name="Relative Duration Promo",
            description="Desc",
            levels=levels,
            duration_mode="relative",
            duration_hours=24,
        )
        assert promo.duration_mode == "relative"
        assert promo.duration_hours == 24

    def test_promotion_activation_deactivation(self, db_session):
        """Verify activate()/deactivate() toggle is_active and status."""
        service = StreakPromotionService(db_session)
        levels = [
            {"consecutive_required": 3, "discount_pct": 10, "codes_available": 3},
        ]
        promo = service.create_promotion(
            name="Toggle Test",
            description="Desc",
            levels=levels,
            duration_mode="dates",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
        )
        # Initial state
        assert promo.is_active is False
        assert promo.status == StreakPromotionStatus.PENDING

        # Activate
        result = service.activate(promo.id)
        assert result is True
        db_session.refresh(promo)
        assert promo.is_active is True
        assert promo.status == StreakPromotionStatus.ACTIVE

        # Deactivate
        result = service.deactivate(promo.id)
        assert result is True
        db_session.refresh(promo)
        assert promo.is_active is False
        assert promo.status == StreakPromotionStatus.EXPIRED

    def test_claim_via_game_service_streak_check(self, db_session):
        """Verify GameService hook integration: correct answer triggers promo code."""
        from services.game_service import GameService

        # 1. Create an active streak promotion with level at streak=1
        streak_service = StreakPromotionService(db_session)
        levels = [
            {"consecutive_required": 1, "discount_pct": 10, "codes_available": 3},
        ]
        promo = streak_service.create_promotion(
            name="Game Hook Promo",
            description="Integration test promo",
            levels=levels,
            duration_mode="dates",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
        )
        promo.is_active = True
        promo.status = StreakPromotionStatus.ACTIVE
        db_session.commit()
        streak_service.close()

        # 2. Create a GameService and mock question loading
        game_service = GameService(db_session)
        mock_question = {
            "question": "Test trivia question?",
            "opts": ["Correct Answer", "Wrong A", "Wrong B"],
            "answer": 0,
        }

        with patch.object(game_service, "load_trivia_questions",
                          return_value=[mock_question]):
            # Get a random question (uses mocked load)
            question, q_idx = game_service.get_random_question()
            assert question is not None
            assert q_idx >= 0

            # Simulate correct answer (answer_idx=0, which matches question['answer']=0)
            result = game_service.play_trivia(
                user_id=99999, question_idx=q_idx, answer_idx=0
            )

            # Verify promo_code is returned with valid data
            assert "promo_code" in result
            assert result["promo_code"] is not None
            assert "code" in result["promo_code"]
            assert "discount_pct" in result["promo_code"]
            assert "promotion_name" in result["promo_code"]
            assert result["promo_code"]["discount_pct"] == 10
            assert result["promo_code"]["promotion_name"] == "Game Hook Promo"

        game_service.close()
