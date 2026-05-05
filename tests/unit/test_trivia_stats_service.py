"""
Tests unitarios para TriviaStatsService.
"""
import pytest
import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from services.trivia_stats_service import TriviaStatsService
from models.models import (
    TriviaPromotionConfig,
    DiscountCode,
    DiscountCodeStatus,
    GameRecord,
    QuestionSet,
    User,
    Promotion,
    TransactionSource,
)


@pytest.mark.unit
class TestTriviaStatsService:
    """Tests para TriviaStatsService"""

    def _create_promo_config(self, db_session, name="Test Promo", status="active", max_codes=10,
                             duration_minutes=None, discount_tiers=None, discount_percentage=50,
                             required_streak=5):
        """Helper to create a TriviaPromotionConfig."""
        config = TriviaPromotionConfig(
            name=name,
            status=status,
            is_active=status == "active",
            max_codes=max_codes,
            codes_claimed=0,
            discount_percentage=discount_percentage,
            required_streak=required_streak,
            duration_minutes=duration_minutes,
            discount_tiers=discount_tiers,
            created_by=123456789,
            start_date=datetime.utcnow(),
        )
        db_session.add(config)
        db_session.commit()
        return config

    def _create_user(self, db_session, user_id=111, username="testuser", first_name="Test"):
        """Helper to create a User."""
        user = User(id=user_id, telegram_id=111111 + user_id, username=username, first_name=first_name)
        db_session.add(user)
        db_session.commit()
        return user

    def _create_game_records(self, db_session, user_id, game_type, count, correct_count):
        """Helper to create GameRecords with specified correct/incorrect ratio."""
        for i in range(count):
            payout = 1 if i < correct_count else 0
            result = "correct" if i < correct_count else "incorrect"
            record = GameRecord(
                user_id=user_id,
                game_type=game_type,
                result=result,
                payout=payout,
                played_at=datetime.utcnow() - timedelta(hours=i)
            )
            db_session.add(record)
        db_session.commit()

    # ─── get_promotion_stats ───────────────────────────────────────────────────

    def test_get_promotion_stats_not_found(self, db_session):
        """Debe retornar dict vacío si la promoción no existe."""
        service = TriviaStatsService(db_session)
        result = service.get_promotion_stats(99999)
        assert result == {}

    def test_get_promotion_stats_with_no_codes(self, db_session):
        """Debe retornar stats correctos para promoción sin códigos."""
        config = self._create_promo_config(db_session)
        service = TriviaStatsService(db_session)

        result = service.get_promotion_stats(config.id)

        assert result["id"] == config.id
        assert result["name"] == config.name
        assert result["status"] == "active"
        assert result["total_codes"] == 0
        assert result["codes_by_status"]["active"] == 0
        assert result["used_percentage"] == 0.0

    def test_get_promotion_stats_with_codes(self, db_session):
        """Debe contar correctamente códigos por status."""
        config = self._create_promo_config(db_session, max_codes=5)
        user = self._create_user(db_session)

        for i, status in enumerate([
            DiscountCodeStatus.ACTIVE, DiscountCodeStatus.USED,
            DiscountCodeStatus.ACTIVE, DiscountCodeStatus.CANCELLED
        ]):
            code = DiscountCode(
                config_id=config.id,
                code=f"TRI-00{i}XX",
                user_id=user.id,
                status=status,
                generated_at=datetime.utcnow(),
                discount_percentage=50
            )
            db_session.add(code)
        db_session.commit()
        config.codes_claimed = 1
        db_session.commit()

        service = TriviaStatsService(db_session)
        result = service.get_promotion_stats(config.id)

        assert result["total_codes"] == 4
        assert result["codes_by_status"]["active"] == 2
        assert result["codes_by_status"]["used"] == 1
        assert result["codes_by_status"]["cancelled"] == 1

    def test_get_promotion_stats_used_percentage(self, db_session):
        """Debe calcular correctamente el porcentaje usado."""
        config = self._create_promo_config(db_session, max_codes=10)
        user = self._create_user(db_session)

        for i in range(3):
            code = DiscountCode(
                config_id=config.id,
                code=f"TRI-USED{i}X",
                user_id=user.id,
                status=DiscountCodeStatus.USED,
                generated_at=datetime.utcnow(),
                discount_percentage=50
            )
            db_session.add(code)
        db_session.commit()
        config.codes_claimed = 3
        db_session.commit()

        service = TriviaStatsService(db_session)
        result = service.get_promotion_stats(config.id)

        assert result["used_percentage"] == 30.0

    # ─── get_user_trivia_stats ────────────────────────────────────────────────

    def test_get_user_trivia_stats_user_not_found(self, db_session):
        """Debe retornar dict vacío si el usuario no existe."""
        service = TriviaStatsService(db_session)
        result = service.get_user_trivia_stats(99999)
        assert result == {}

    def test_get_user_trivia_stats_correct_incorrect_calculation(self, db_session):
        """Debe calcular correctamente correct_answers e incorrect_answers."""
        user = self._create_user(db_session)
        self._create_game_records(db_session, user.id, "trivia", count=10, correct_count=7)

        service = TriviaStatsService(db_session)
        result = service.get_user_trivia_stats(user.id)

        assert result["user_id"] == user.id
        stats = result["stats"]["trivia"]
        assert stats["total_plays"] == 10
        assert stats["correct_answers"] == 7
        assert stats["incorrect_answers"] == 3
        assert stats["correctness_rate"] == 70.0

    def test_get_user_trivia_stats_streak_calculation(self, db_session):
        """Debe calcular correctamente current_streak y max_streak."""
        user = self._create_user(db_session)
        # All correct (all payout=1) → streak unbroken
        self._create_game_records(db_session, user.id, "trivia", count=5, correct_count=5)

        service = TriviaStatsService(db_session)
        result = service.get_user_trivia_stats(user.id)

        stats = result["stats"]["trivia"]
        # All 5 correct: current_streak=5 (all today), max_streak=5
        assert stats["current_streak"] == 5
        assert stats["max_streak"] == 5

    def test_get_user_trivia_stats_codes_count(self, db_session):
        """Debe contar códigos activos y usados del usuario."""
        user = self._create_user(db_session)
        config = self._create_promo_config(db_session)

        for i, status in enumerate([DiscountCodeStatus.ACTIVE, DiscountCodeStatus.USED, DiscountCodeStatus.ACTIVE]):
            code = DiscountCode(
                config_id=config.id,
                code=f"TRI-CODE{i}X",
                user_id=user.id,
                status=status,
                generated_at=datetime.utcnow(),
                discount_percentage=50
            )
            db_session.add(code)
        db_session.commit()

        service = TriviaStatsService(db_session)
        result = service.get_user_trivia_stats(user.id)

        assert result["stats"]["trivia"]["codes_earned"] == 2
        assert result["stats"]["trivia"]["codes_used"] == 1

    # ─── Rankings ─────────────────────────────────────────────────────────────

    def test_get_top_scorers_empty(self, db_session):
        """Debe retornar lista vacía si no hay registros."""
        service = TriviaStatsService(db_session)
        result = service.get_top_scorers()
        assert result == []

    def test_get_top_scorers_with_data(self, db_session):
        """Debe retornar top scorers ordenados por correct answers."""
        user1 = self._create_user(db_session, user_id=101, username="alice")
        user2 = self._create_user(db_session, user_id=102, username="bob")

        # user1: 10 correct, user2: 5 correct
        self._create_game_records(db_session, user1.id, "trivia", count=10, correct_count=10)
        self._create_game_records(db_session, user2.id, "trivia", count=5, correct_count=5)

        service = TriviaStatsService(db_session)
        result = service.get_top_scorers(limit=10)

        assert len(result) == 2
        assert result[0]["user_id"] == user1.id
        assert result[0]["rank"] == 1
        assert result[1]["user_id"] == user2.id
        assert result[1]["rank"] == 2

    def test_get_top_streaks_empty(self, db_session):
        """Debe retornar lista vacía si no hay streaks."""
        service = TriviaStatsService(db_session)
        result = service.get_top_streaks()
        assert result == []

    def test_get_top_streaks_with_data(self, db_session):
        """Debe retornar top streaks ordenados."""
        user1 = self._create_user(db_session, user_id=201, username="charlie")
        user2 = self._create_user(db_session, user_id=202, username="diana")

        # user1: max streak 8, user2: max streak 3
        self._create_game_records(db_session, user1.id, "trivia", count=8, correct_count=8)
        self._create_game_records(db_session, user2.id, "trivia", count=3, correct_count=3)

        service = TriviaStatsService(db_session)
        result = service.get_top_streaks(limit=10)

        assert len(result) == 2
        assert result[0]["user_id"] == user1.id
        assert result[0]["value"] == 8
        assert result[1]["user_id"] == user2.id
        assert result[1]["value"] == 3

    def test_get_top_codes_redeemed_empty(self, db_session):
        """Debe retornar lista vacía si no hay códigos usados."""
        service = TriviaStatsService(db_session)
        result = service.get_top_codes_redeemed()
        assert result == []

    def test_get_top_codes_redeemed_with_data(self, db_session):
        """Debe retornar top usuarios por códigos usados."""
        user1 = self._create_user(db_session, user_id=301, username="eve")
        user2 = self._create_user(db_session, user_id=302, username="fran")
        config = self._create_promo_config(db_session)

        for i in range(3):
            code = DiscountCode(config_id=config.id, code=f"TRI-USED{i}EVE", user_id=user1.id,
                               status=DiscountCodeStatus.USED, generated_at=datetime.utcnow(),
                               discount_percentage=50)
            db_session.add(code)
        for i in range(1):
            code = DiscountCode(config_id=config.id, code=f"TRI-USED{i}FRAN", user_id=user2.id,
                               status=DiscountCodeStatus.USED, generated_at=datetime.utcnow(),
                               discount_percentage=50)
            db_session.add(code)
        db_session.commit()

        service = TriviaStatsService(db_session)
        result = service.get_top_codes_redeemed(limit=10)

        assert len(result) == 2
        assert result[0]["user_id"] == user1.id
        assert result[0]["value"] == 3
        assert result[1]["user_id"] == user2.id
        assert result[1]["value"] == 1

    # ─── CSV Exports ────────────────────────────────────────────────────────────

    def test_export_promotions_csv_no_promotions(self, db_session):
        """Debe retornar None si no hay promociones."""
        service = TriviaStatsService(db_session)
        result = service.export_promotions_csv()
        assert result is None

    def test_export_promotions_csv_with_promotions(self, db_session):
        """Debe generar CSV con datos de promociones."""
        self._create_promo_config(db_session, name="CSV Test Promo")
        service = TriviaStatsService(db_session)

        result = service.export_promotions_csv()

        assert result is not None
        assert result.endswith(".csv")
        with open(result) as f:
            content = f.read()
            assert "name" in content
            assert "CSV Test Promo" in content
        os.unlink(result)

    def test_export_users_stats_csv_no_users(self, db_session):
        """Debe retornar None si no hay usuarios con trivia."""
        service = TriviaStatsService(db_session)
        result = service.export_users_stats_csv()
        assert result is None

    def test_export_rankings_csv(self, db_session):
        """Debe generar CSV con rankings (top scorers, streaks, codes)."""
        user = self._create_user(db_session)
        self._create_game_records(db_session, user.id, "trivia", count=5, correct_count=5)

        service = TriviaStatsService(db_session)
        result = service.export_rankings_csv()

        assert result is not None
        assert result.endswith(".csv")
        with open(result) as f:
            content = f.read()
            assert "TOP SCORERS" in content
            assert "TOP STREAKS" in content
            assert "TOP CODES" in content
        os.unlink(result)

    # ─── Dashboard ──────────────────────────────────────────────────────────────

    def test_get_full_dashboard_empty(self, db_session):
        """Debe retornar dashboard vacío si no hay datos."""
        service = TriviaStatsService(db_session)
        result = service.get_full_dashboard()

        assert result["promotions"] == []
        assert result["users_summary"]["total_trivia_users"] == 0
        assert result["rankings"]["top_scorers"] == []
        assert result["rankings"]["top_streaks"] == []
        assert result["rankings"]["top_codes"] == []

    def test_get_full_dashboard_with_data(self, db_session):
        """Debe retornar dashboard completo con datos."""
        user = self._create_user(db_session)
        self._create_game_records(db_session, user.id, "trivia", count=5, correct_count=4)
        config = self._create_promo_config(db_session)

        service = TriviaStatsService(db_session)
        result = service.get_full_dashboard()

        assert len(result["promotions"]) >= 1
        assert result["users_summary"]["total_trivia_users"] == 1
        assert "avg_correctness_rate" in result["users_summary"]
