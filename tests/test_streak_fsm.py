"""Tests for streak FSM state transitions (Phase 18)."""
import json
import pytest
from unittest.mock import patch
from models.models import StreakPromotionCodeStatus
from services.game_service import GameService
from services.streak_promotion_service import StreakPromotionService


class TestGameServiceSessionState:
    @patch('services.besito_service.BesitoService.has_sufficient_balance', return_value=True)
    def test_incorrect_with_protection_available(self, mock_has_balance, db_session, sample_streak_promotion):
        """When user has active session and fails, session_state should offer protection."""
        svc = StreakPromotionService(db_session)
        session = svc._get_or_create_session(11111, sample_streak_promotion.id)
        # Session exists but protection not used

        game_svc = GameService(db_session)
        state = game_svc._build_streak_failure_state(11111, 5)
        assert state is not None
        assert state['action'] == 'offer_protection'
        assert state['protection_cost'] == 10  # streak=5 -> 5+ (5//3)*5 = 5+5=10
        assert state['streak'] == 5

    def test_incorrect_with_protection_used(self, db_session, sample_streak_promotion):
        """When protection already used and user fails again, codes get cancelled."""
        svc = StreakPromotionService(db_session)
        session = svc._get_or_create_session(22222, sample_streak_promotion.id)
        session.protection_used = True
        db_session.flush()

        game_svc = GameService(db_session)
        state = game_svc._build_streak_failure_state(22222, 7)
        assert state is not None
        assert state['action'] == 'cancelled'
        assert state['streak_reset_to'] == 0

    def test_incorrect_no_session(self, db_session):
        """No session active -> no session_state."""
        game_svc = GameService(db_session)
        state = game_svc._build_streak_failure_state(33333, 3)
        assert state is None

    @patch('services.besito_service.BesitoService.has_sufficient_balance', return_value=False)
    def test_incorrect_no_besitos_sets_timeout(self, mock_has_balance, db_session, sample_streak_promotion):
        """When user has no besitos for protection, timeout is set."""
        svc = StreakPromotionService(db_session)
        session = svc._get_or_create_session(44444, sample_streak_promotion.id)

        game_svc = GameService(db_session)
        state = game_svc._build_streak_failure_state(44444, 3)
        assert state is not None
        assert state['action'] == 'timeout'
        assert 'expires_at' in state

    def test_claim_with_session_offers_retire(self, db_session, sample_streak_promotion):
        """When a code is claimed, session_state should offer retire."""
        svc = StreakPromotionService(db_session)
        session = svc._get_or_create_session(55555, sample_streak_promotion.id)

        game_svc = GameService(db_session)
        promo_code_info = {"code": "TEST-CODE", "discount_pct": 50, "promotion_name": "Test"}
        state = game_svc._build_streak_claim_state(55555, promo_code_info)
        assert state is not None
        assert state['action'] == 'offer_retire'
        assert state['code'] == promo_code_info

    def test_claim_in_risk_mode_stays_in_risk(self, db_session, sample_streak_promotion):
        """When in risk mode, claiming another code shows claimed_in_risk."""
        svc = StreakPromotionService(db_session)
        session = svc._get_or_create_session(66666, sample_streak_promotion.id)
        session.is_in_risk_mode = True
        db_session.flush()

        game_svc = GameService(db_session)
        promo_code_info = {"code": "TEST-CODE-2", "discount_pct": 75, "promotion_name": "Test"}
        state = game_svc._build_streak_claim_state(66666, promo_code_info)
        assert state is not None
        assert state['action'] == 'claimed_in_risk'
