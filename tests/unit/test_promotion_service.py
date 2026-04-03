"""
Tests unitarios para PromotionService.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from services.promotion_service import PromotionService
from models.models import (
    PromotionStatus, InterestStatus, BlockedPromotionUser,
    PromotionInterest, Promotion
)


@pytest.mark.unit
class TestPromotionService:
    """Tests para el servicio de promociones"""

    def test_create_promotion(self, db_session, sample_package):
        """Test crear una promocion con precio en centavos MXN"""
        service = PromotionService(db_session)

        promotion = service.create_promotion(
            name="Promo Test",
            description="Una promocion de prueba",
            package_id=sample_package.id,
            price_mxn=99900,
            created_by=987654321
        )

        assert promotion.name == "Promo Test"
        assert promotion.price_mxn == 99900
        assert promotion.price_display == "$999.00 MXN"
        assert promotion.status == PromotionStatus.ACTIVE
        assert promotion.is_active is True

    def test_get_promotion(self, db_session, sample_promotion):
        """Test obtener promocion por ID"""
        service = PromotionService(db_session)

        promotion = service.get_promotion(sample_promotion.id)

        assert promotion is not None
        assert promotion.id == sample_promotion.id
        assert promotion.name == sample_promotion.name

    def test_get_available_promotions(self, db_session, sample_promotion):
        """Test obtener promociones disponibles filtra activas y fechas"""
        service = PromotionService(db_session)

        promotions = service.get_available_promotions()

        assert len(promotions) >= 1
        assert any(p.id == sample_promotion.id for p in promotions)

    def test_update_promotion_allowed_fields(self, db_session, sample_promotion):
        """Test actualizar campos permitidos de promocion"""
        service = PromotionService(db_session)

        result = service.update_promotion(
            sample_promotion.id,
            name="Updated Name",
            description="Updated Desc",
            price_mxn=49900,
            status=PromotionStatus.PAUSED,
            is_active=False
        )

        assert result is True
        updated = service.get_promotion(sample_promotion.id)
        assert updated.name == "Updated Name"
        assert updated.description == "Updated Desc"
        assert updated.price_mxn == 49900
        assert updated.status == PromotionStatus.PAUSED
        assert updated.is_active is False

    def test_pause_promotion(self, db_session, sample_promotion):
        """Test pausar promocion cambia status a PAUSED"""
        service = PromotionService(db_session)

        result = service.pause_promotion(sample_promotion.id)

        assert result is True
        updated = service.get_promotion(sample_promotion.id)
        assert updated.status == PromotionStatus.PAUSED

    def test_resume_promotion(self, db_session, sample_promotion):
        """Test reactivar promocion cambia status a ACTIVE"""
        service = PromotionService(db_session)
        service.pause_promotion(sample_promotion.id)

        result = service.resume_promotion(sample_promotion.id)

        assert result is True
        updated = service.get_promotion(sample_promotion.id)
        assert updated.status == PromotionStatus.ACTIVE

    def test_delete_promotion(self, db_session, sample_promotion):
        """Test eliminar promocion desactiva is_active"""
        service = PromotionService(db_session)

        result = service.delete_promotion(sample_promotion.id)

        assert result is True
        updated = service.get_promotion(sample_promotion.id)
        assert updated.is_active is False


@pytest.mark.unit
class TestPromotionInterest:
    """Tests para el sistema 'Me Interesa'"""

    def test_express_interest_success(self, db_session, sample_user, sample_promotion):
        """Test expresar interes crea PromotionInterest con status PENDING"""
        service = PromotionService(db_session)

        success, message, interest = service.express_interest(
            sample_user.id, sample_promotion.id,
            username=sample_user.username,
            first_name=sample_user.first_name,
            last_name=sample_user.last_name
        )

        assert success is True
        assert interest is not None
        assert interest.status == InterestStatus.PENDING
        assert interest.user_id == sample_user.id
        assert interest.promotion_id == sample_promotion.id

    def test_express_interest_blocked_user(self, db_session, sample_user, sample_promotion):
        """Test expresar interes falla para usuario bloqueado"""
        service = PromotionService(db_session)
        blocked = BlockedPromotionUser(
            user_id=sample_user.id,
            reason="Spam",
            is_permanent=True
        )
        db_session.add(blocked)
        db_session.commit()

        success, message, interest = service.express_interest(
            sample_user.id, sample_promotion.id
        )

        assert success is False
        assert interest is None
        assert "No puedes expresar interes" in message

    def test_express_interest_unavailable_promotion(self, db_session, sample_user, sample_promotion):
        """Test expresar interes falla para promocion no disponible"""
        service = PromotionService(db_session)
        service.pause_promotion(sample_promotion.id)

        success, message, interest = service.express_interest(
            sample_user.id, sample_promotion.id
        )

        assert success is False
        assert interest is None
        assert "no esta disponible" in message

    def test_express_interest_duplicate(self, db_session, sample_user, sample_promotion):
        """Test expresar interes falla si ya existe interes"""
        service = PromotionService(db_session)

        success1, _, interest1 = service.express_interest(
            sample_user.id, sample_promotion.id
        )
        assert success1 is True

        success2, message2, interest2 = service.express_interest(
            sample_user.id, sample_promotion.id
        )
        assert success2 is False
        assert interest2 is None
        assert "Ya has expresado interes" in message2

    def test_mark_interest_attended(self, db_session, sample_user, sample_promotion, sample_admin):
        """Test marcar interes como atendido actualiza status y attended_by"""
        service = PromotionService(db_session)

        _, _, interest = service.express_interest(
            sample_user.id, sample_promotion.id
        )
        result = service.mark_interest_attended(interest.id, sample_admin.telegram_id)

        assert result is True
        updated = service.get_interest(interest.id)
        assert updated.status == InterestStatus.ATTENDED
        assert updated.attended_by == sample_admin.telegram_id
        assert updated.attended_at is not None


@pytest.mark.unit
class TestPromotionBlocking:
    """Tests para bloqueo de usuarios en promociones"""

    def test_block_user(self, db_session, sample_user):
        """Test bloquear usuario crea BlockedPromotionUser"""
        service = PromotionService(db_session)

        blocked = service.block_user(
            sample_user.id,
            blocked_by=987654321,
            reason="Comportamiento inapropiado"
        )

        assert blocked is not None
        assert blocked.user_id == sample_user.id
        assert blocked.reason == "Comportamiento inapropiado"
        assert blocked.is_permanent is True

    def test_unblock_user(self, db_session, sample_user):
        """Test desbloquear usuario elimina el registro"""
        service = PromotionService(db_session)
        service.block_user(sample_user.id, blocked_by=987654321, reason="Test")

        result = service.unblock_user(sample_user.id)

        assert result is True
        assert service.is_user_blocked(sample_user.id) is False

    def test_block_user_updates_pending_interests(self, db_session, sample_user, sample_promotion):
        """Test bloquear usuario actualiza intereses pendientes a BLOCKED"""
        service = PromotionService(db_session)
        _, _, interest = service.express_interest(sample_user.id, sample_promotion.id)
        assert interest.status == InterestStatus.PENDING

        service.block_user(sample_user.id, blocked_by=987654321, reason="Test")

        db_session.refresh(interest)
        assert interest.status == InterestStatus.BLOCKED


@pytest.mark.unit
class TestPromotionStats:
    """Tests para estadisticas de promociones"""

    def test_get_promotion_stats(self, db_session, sample_promotion, sample_user):
        """Test obtener estadisticas de promociones"""
        service = PromotionService(db_session)
        service.express_interest(sample_user.id, sample_promotion.id)

        stats = service.get_promotion_stats()

        assert stats['total_promotions'] >= 1
        assert stats['active_promotions'] >= 1
        assert stats['total_interests'] >= 1
        assert stats['pending_interests'] >= 1
        assert 'attended_interests' in stats
        assert 'blocked_users' in stats


@pytest.mark.unit
class TestPromotionServiceRaceCondition:
    """Tests para verificar proteccion contra race conditions"""

    def test_express_interest_uses_select_for_update(self, db_session, sample_user, sample_promotion):
        """Test que express_interest usa SELECT FOR UPDATE"""
        service = PromotionService(db_session)

        # Primer query: is_user_blocked (BlockedPromotionUser)
        blocked_mock = MagicMock()
        blocked_mock.filter.return_value.first.return_value = None

        # Segundo query: get_promotion (Promotion)
        promotion_mock = MagicMock()
        promotion_mock.filter.return_value.first.return_value = sample_promotion

        # Tercer query: PromotionInterest con with_for_update
        interest_mock = MagicMock()
        interest_filtered = MagicMock()
        interest_with_lock = MagicMock()
        interest_with_lock.first.return_value = None
        interest_filtered.with_for_update.return_value = interest_with_lock
        interest_mock.filter.return_value = interest_filtered

        with patch.object(db_session, 'query', side_effect=[blocked_mock, promotion_mock, interest_mock]):
            service.express_interest(sample_user.id, sample_promotion.id)
            interest_filtered.with_for_update.assert_called()
