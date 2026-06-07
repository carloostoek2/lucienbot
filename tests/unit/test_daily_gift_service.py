"""
Tests unitarios para DailyGiftService.
"""

from datetime import UTC, datetime, timedelta

import pytest

from models.models import DailyGiftClaim
from services.daily_gift_service import DailyGiftService


@pytest.mark.unit
class TestDailyGiftConfig:
    """Tests para configuración del regalo diario"""

    def test_get_config_creates_default(self, db_session):
        """Test get_config crea configuración por defecto cuando no existe"""
        service = DailyGiftService(db_session)

        config = service.get_config()

        assert config is not None
        assert config.besito_amount == 10
        assert config.is_active is True

    def test_update_config(self, db_session, sample_admin):
        """Test actualizar configuración del regalo diario"""
        service = DailyGiftService(db_session)
        service.get_config()

        config = service.update_config(besito_amount=25, admin_id=sample_admin.telegram_id)

        assert config.besito_amount == 25
        assert config.updated_by == sample_admin.telegram_id

    def test_is_active(self, db_session):
        """Test verificar si el regalo diario está activo"""
        service = DailyGiftService(db_session)
        service.get_config()

        assert service.is_active() is True

        config = service.get_config()
        config.is_active = False
        db_session.commit()

        assert service.is_active() is False

    def test_get_gift_amount_active(self, db_session):
        """Test obtener cantidad de besitos cuando está activo"""
        service = DailyGiftService(db_session)
        service.get_config()

        assert service.get_gift_amount() == 10

    def test_get_gift_amount_inactive(self, db_session):
        """Test obtener cantidad de besitos cuando está inactivo retorna 0"""
        service = DailyGiftService(db_session)
        config = service.get_config()
        config.is_active = False
        db_session.commit()

        assert service.get_gift_amount() == 0


@pytest.mark.unit
class TestDailyGiftClaims:
    """Tests para reclamos del regalo diario"""

    def test_can_claim_first_time(self, db_session, sample_user):
        """Test primer reclamo siempre permite"""
        service = DailyGiftService(db_session)

        can_claim, remaining, msg = service.can_claim(sample_user.telegram_id)

        assert can_claim is True
        assert remaining is None
        assert "puedes reclamar" in msg.lower()

    def test_can_claim_cooldown_active(self, db_session, sample_user):
        """Test cooldown de 24 horas impide reclamo"""
        service = DailyGiftService(db_session)
        claim = DailyGiftClaim(
            user_id=sample_user.telegram_id,
            besitos_received=10,
            claimed_at=datetime.now(UTC) - timedelta(hours=1),
        )
        db_session.add(claim)
        db_session.commit()

        can_claim, remaining, msg = service.can_claim(sample_user.telegram_id)

        assert can_claim is False
        assert remaining is not None
        assert "debes esperar" in msg.lower()

    def test_can_claim_after_24_hours(self, db_session, sample_user):
        """Test después de 24 horas se puede reclamar de nuevo"""
        service = DailyGiftService(db_session)
        claim = DailyGiftClaim(
            user_id=sample_user.telegram_id,
            besitos_received=10,
            claimed_at=datetime.now(UTC) - timedelta(hours=25),
        )
        db_session.add(claim)
        db_session.commit()

        can_claim, remaining, msg = service.can_claim(sample_user.telegram_id)

        assert can_claim is True
        assert remaining is None

    def test_can_claim_inactive(self, db_session, sample_user):
        """Test cuando el regalo diario está inactivo no se puede reclamar"""
        service = DailyGiftService(db_session)
        config = service.get_config()
        config.is_active = False
        db_session.commit()

        can_claim, remaining, msg = service.can_claim(sample_user.telegram_id)

        assert can_claim is False
        assert "no está disponible" in msg.lower()

    def test_claim_gift_success(self, db_session, sample_user):
        """Test reclamar regalo acredita besitos y crea registro"""
        service = DailyGiftService(db_session)

        success, amount, msg = service.claim_gift(sample_user.telegram_id)

        assert success is True
        assert amount == 10
        balance = service.besito_service.get_balance(sample_user.telegram_id)
        assert balance == 10

        history = service.get_claim_history(sample_user.telegram_id)
        assert len(history) == 1
        assert history[0].besitos_received == 10

    def test_claim_gift_cooldown_blocks(self, db_session, sample_user):
        """Test reclamar durante cooldown falla"""
        service = DailyGiftService(db_session)
        claim = DailyGiftClaim(
            user_id=sample_user.telegram_id,
            besitos_received=10,
            claimed_at=datetime.now(UTC) - timedelta(hours=1),
        )
        db_session.add(claim)
        db_session.commit()

        success, amount, msg = service.claim_gift(sample_user.telegram_id)

        assert success is False
        assert amount is None
        assert "debes esperar" in msg.lower()

    def test_claim_gift_inactive(self, db_session, sample_user):
        """Test reclamar cuando está inactivo falla"""
        service = DailyGiftService(db_session)
        config = service.get_config()
        config.is_active = False
        db_session.commit()

        success, amount, msg = service.claim_gift(sample_user.telegram_id)

        assert success is False
        assert amount is None
        assert "no está disponible" in msg.lower()


@pytest.mark.unit
class TestDailyGiftStats:
    """Tests para estadísticas del regalo diario"""

    def test_get_total_claims_today(self, db_session, sample_user):
        """Test contar reclamos del día actual"""
        service = DailyGiftService(db_session)
        # Reclamo de hoy
        claim1 = DailyGiftClaim(user_id=sample_user.telegram_id, besitos_received=10)
        db_session.add(claim1)
        # Reclamo de ayer
        claim2 = DailyGiftClaim(
            user_id=sample_user.telegram_id,
            besitos_received=10,
            claimed_at=datetime.now(UTC) - timedelta(days=1),
        )
        db_session.add(claim2)
        db_session.commit()

        total = service.get_total_claims_today()

        assert total == 1

    def test_get_total_besitos_given_today(self, db_session, sample_user):
        """Test sumar besitos entregados hoy"""
        service = DailyGiftService(db_session)
        claim1 = DailyGiftClaim(user_id=sample_user.telegram_id, besitos_received=10)
        claim2 = DailyGiftClaim(user_id=999999, besitos_received=5)
        claim3 = DailyGiftClaim(
            user_id=sample_user.telegram_id,
            besitos_received=20,
            claimed_at=datetime.now(UTC) - timedelta(days=1),
        )
        db_session.add_all([claim1, claim2, claim3])
        db_session.commit()

        total = service.get_total_besitos_given_today()

        assert total == 15

    def test_get_claim_history_order(self, db_session, sample_user):
        """Test historial de reclamos ordenado descendente por fecha"""
        service = DailyGiftService(db_session)
        claim1 = DailyGiftClaim(
            user_id=sample_user.telegram_id,
            besitos_received=10,
            claimed_at=datetime.now(UTC) - timedelta(days=2),
        )
        claim2 = DailyGiftClaim(
            user_id=sample_user.telegram_id,
            besitos_received=10,
            claimed_at=datetime.now(UTC) - timedelta(days=1),
        )
        claim3 = DailyGiftClaim(
            user_id=sample_user.telegram_id, besitos_received=10, claimed_at=datetime.now(UTC)
        )
        db_session.add_all([claim1, claim2, claim3])
        db_session.commit()

        history = service.get_claim_history(sample_user.telegram_id)

        assert len(history) == 3
        assert history[0].claimed_at >= history[1].claimed_at >= history[2].claimed_at

    def test_get_claim_history_respects_limit(self, db_session, sample_user):
        """Test historial respeta el límite"""
        service = DailyGiftService(db_session)
        for i in range(5):
            claim = DailyGiftClaim(
                user_id=sample_user.telegram_id,
                besitos_received=10,
                claimed_at=datetime.now(UTC) - timedelta(hours=i),
            )
            db_session.add(claim)
        db_session.commit()

        history = service.get_claim_history(sample_user.telegram_id, limit=3)

        assert len(history) == 3
