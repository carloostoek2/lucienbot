"""
Tests unitarios para VIPService.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from services.vip_service import VIPService
from models.models import TokenStatus, Subscription, Token


@pytest.mark.unit
class TestVIPService:
    """Tests para el servicio VIP"""

    def test_create_tariff(self, db_session):
        """Test crear una nueva tarifa"""
        service = VIPService(db_session)

        tariff = service.create_tariff(
            name="Test Monthly",
            duration_days=30,
            price="9.99",
            currency="USD"
        )

        assert tariff.name == "Test Monthly"
        assert tariff.duration_days == 30
        assert tariff.price == "9.99"
        assert tariff.currency == "USD"
        assert tariff.is_active is True

    def test_get_tariff(self, db_session, sample_tariff):
        """Test obtener tarifa por ID"""
        service = VIPService(db_session)

        tariff = service.get_tariff(sample_tariff.id)

        assert tariff is not None
        assert tariff.id == sample_tariff.id
        assert tariff.name == sample_tariff.name

    def test_get_tariff_not_found(self, db_session):
        """Test obtener tarifa inexistente"""
        service = VIPService(db_session)

        tariff = service.get_tariff(99999)

        assert tariff is None

    def test_get_all_tariffs(self, db_session, sample_tariff):
        """Test obtener todas las tarifas activas"""
        service = VIPService(db_session)

        tariffs = service.get_all_tariffs()

        assert len(tariffs) >= 1
        assert any(t.id == sample_tariff.id for t in tariffs)

    def test_update_tariff(self, db_session, sample_tariff):
        """Test actualizar tarifa"""
        service = VIPService(db_session)

        result = service.update_tariff(sample_tariff.id, name="Updated Name", price="19.99")

        assert result is True
        updated = service.get_tariff(sample_tariff.id)
        assert updated.name == "Updated Name"
        assert updated.price == "19.99"

    def test_deactivate_tariff(self, db_session, sample_tariff):
        """Test desactivar tarifa"""
        service = VIPService(db_session)

        result = service.deactivate_tariff(sample_tariff.id)

        assert result is True
        updated = service.get_tariff(sample_tariff.id)
        assert updated.is_active is False


@pytest.mark.unit
class TestTokenService:
    """Tests para gestión de tokens"""

    def test_generate_token(self, db_session, sample_tariff):
        """Test generar un token"""
        service = VIPService(db_session)

        token = service.generate_token(sample_tariff.id)

        assert token.token_code is not None
        assert len(token.token_code) > 0
        assert token.tariff_id == sample_tariff.id
        assert token.status == TokenStatus.ACTIVE

    def test_generate_token_with_expiration(self, db_session, sample_tariff):
        """Test generar token con fecha de expiración"""
        service = VIPService(db_session)

        token = service.generate_token(sample_tariff.id, expires_in_days=7)

        assert token.expires_at is not None
        expected_date = datetime.utcnow() + timedelta(days=7)
        # Permitir margen de 1 minuto
        assert abs((token.expires_at - expected_date).total_seconds()) < 60

    def test_generate_token_invalid_tariff(self, db_session):
        """Test generar token para tarifa inexistente"""
        service = VIPService(db_session)

        with pytest.raises(ValueError, match="Tarifa no encontrada"):
            service.generate_token(99999)

    def test_get_token_by_code(self, db_session, sample_token):
        """Test obtener token por código"""
        service = VIPService(db_session)

        token = service.get_token_by_code(sample_token.token_code)

        assert token is not None
        assert token.id == sample_token.id
        assert token.token_code == sample_token.token_code

    def test_validate_token_valid(self, db_session, sample_token):
        """Test validar token válido"""
        service = VIPService(db_session)

        token, error = service.validate_token(sample_token.token_code)

        assert token is not None
        assert error is None
        assert token.id == sample_token.id

    def test_validate_token_invalid(self, db_session):
        """Test validar token inválido"""
        service = VIPService(db_session)

        token, error = service.validate_token("INVALIDCODE")

        assert token is None
        assert error == "invalid"

    def test_validate_token_used(self, db_session, sample_used_token):
        """Test validar token ya usado"""
        service = VIPService(db_session)

        token, error = service.validate_token(sample_used_token.token_code)

        assert token is None
        assert error == "used"

    def test_validate_token_expired(self, db_session, sample_expired_token):
        """Test validar token expirado"""
        service = VIPService(db_session)

        token, error = service.validate_token(sample_expired_token.token_code)

        assert token is None
        assert error == "expired"

    def test_revoke_token(self, db_session, sample_token):
        """Test revocar token activo"""
        service = VIPService(db_session)

        result = service.revoke_token(sample_token.id)

        assert result is True
        revoked = service.get_token(sample_token.id)
        assert revoked.status == TokenStatus.EXPIRED

    def test_revoke_token_already_used(self, db_session, sample_used_token):
        """Test revocar token ya usado"""
        service = VIPService(db_session)

        result = service.revoke_token(sample_used_token.id)

        assert result is False


@pytest.mark.unit
class TestSubscriptionService:
    """Tests para gestión de suscripciones"""

    def test_redeem_token_success(self, db_session, sample_token, sample_user, sample_vip_channel):
        """Test canjear token exitosamente"""
        service = VIPService(db_session)

        subscription = service.redeem_token(sample_token.token_code, sample_user.id)

        assert subscription is not None
        assert subscription.user_id == sample_user.id
        assert subscription.channel_id == sample_vip_channel.id
        assert subscription.token_id == sample_token.id
        assert subscription.is_active is True

        # Verificar que el token fue marcado como usado
        token = service.get_token(sample_token.id)
        assert token.status == TokenStatus.USED
        assert token.redeemed_by_id == sample_user.id
        assert token.redeemed_at is not None

    def test_redeem_token_already_used(self, db_session, sample_used_token, sample_user):
        """Test canjear token ya usado"""
        service = VIPService(db_session)

        subscription = service.redeem_token(sample_used_token.token_code, sample_user.id)

        assert subscription is None

    def test_redeem_token_expired(self, db_session, sample_expired_token, sample_user):
        """Test canjear token expirado"""
        service = VIPService(db_session)

        subscription = service.redeem_token(sample_expired_token.token_code, sample_user.id)

        assert subscription is None

    def test_get_user_subscription(self, db_session, sample_subscription, sample_user):
        """Test obtener suscripción activa de usuario"""
        service = VIPService(db_session)

        subscription = service.get_user_subscription(sample_user.id)

        assert subscription is not None
        assert subscription.id == sample_subscription.id
        assert subscription.user_id == sample_user.id

    def test_is_user_vip_true(self, db_session, sample_subscription, sample_user):
        """Test verificar si usuario es VIP (sí lo es)"""
        service = VIPService(db_session)

        is_vip = service.is_user_vip(sample_user.id)

        assert is_vip is True

    def test_is_user_vip_false(self, db_session, sample_user):
        """Test verificar si usuario es VIP (no lo es)"""
        service = VIPService(db_session)

        is_vip = service.is_user_vip(sample_user.id)

        assert is_vip is False

    def test_expire_subscription(self, db_session, sample_subscription):
        """Test expirar una suscripción"""
        service = VIPService(db_session)

        result = service.expire_subscription(sample_subscription.id)

        assert result is True
        expired = service.get_subscription(sample_subscription.id)
        assert expired.is_active is False

    def test_get_expired_subscriptions(self, db_session, sample_expired_subscription):
        """Test obtener suscripciones expiradas"""
        service = VIPService(db_session)

        expired = service.get_expired_subscriptions()

        assert len(expired) >= 1
        assert any(s.id == sample_expired_subscription.id for s in expired)

    def test_get_expiring_subscriptions(self, db_session, sample_subscription):
        """Test obtener suscripciones por vencer"""
        service = VIPService(db_session)

        # La suscripción de sample tiene 30 días, no debería estar por vencer
        expiring = service.get_expiring_subscriptions(hours=24)

        # No debería incluir la suscripción de 30 días
        assert not any(s.id == sample_subscription.id for s in expiring)

    def test_mark_reminder_sent(self, db_session, sample_subscription):
        """Test marcar recordatorio enviado"""
        service = VIPService(db_session)

        result = service.mark_reminder_sent(sample_subscription.id)

        assert result is True
        updated = service.get_subscription(sample_subscription.id)
        assert updated.reminder_sent is True

    def test_get_vip_channel(self, db_session, sample_vip_channel):
        """Test obtener canal VIP"""
        service = VIPService(db_session)

        channel = service.get_vip_channel()

        assert channel is not None
        assert channel.id == sample_vip_channel.id


@pytest.mark.unit
class TestVIPServiceRaceCondition:
    """Tests para verificar protección contra race conditions"""

    def test_redeem_token_uses_select_for_update(self, db_session, sample_token, sample_user, sample_vip_channel):
        """Test que redeem_token usa SELECT FOR UPDATE"""
        service = VIPService(db_session)

        # Simular que el token está activo
        sample_token.status = TokenStatus.ACTIVE
        sample_token.expires_at = None
        token_code = sample_token.token_code

        # Clase mock que simula la cadena query().filter().with_for_update().first()
        class MockQueryChain:
            def __init__(self, result_token):
                self.result_token = result_token
                self.with_for_update_called = False

            def filter(self, *args, **kwargs):
                return self

            def with_for_update(self):
                self.with_for_update_called = True
                return self

            def first(self):
                return self.result_token

        mock_chain = MockQueryChain(sample_token)

        with patch.object(db_session, 'query', return_value=mock_chain):
            # Llamar al método
            service.redeem_token(token_code, sample_user.id)

            # Verificar que se llamó with_for_update
            assert mock_chain.with_for_update_called


@pytest.mark.unit
class TestVIPEntryState:
    """Tests para VIP entry state management (Phase 10)"""

    def test_redeem_token_sets_pending_entry(self, db_session, sample_token, sample_user, sample_vip_channel):
        """Test que redeem_token establece pending_entry en el usuario"""
        service = VIPService(db_session)

        subscription = service.redeem_token(sample_token.token_code, sample_user.telegram_id)

        assert subscription is not None
        db_session.refresh(sample_user)
        assert sample_user.vip_entry_status == "pending_entry"
        assert sample_user.vip_entry_stage == 1

    def test_get_vip_entry_state(self, db_session, sample_user):
        """Test obtener estado de entrada VIP"""
        sample_user.vip_entry_status = "pending_entry"
        sample_user.vip_entry_stage = 2
        db_session.commit()

        service = VIPService(db_session)
        status, stage = service.get_vip_entry_state(sample_user.telegram_id)

        assert status == "pending_entry"
        assert stage == 2

    def test_advance_vip_entry_stage(self, db_session, sample_user):
        """Test avanzar etapa de entrada VIP"""
        sample_user.vip_entry_status = "pending_entry"
        sample_user.vip_entry_stage = 1
        db_session.commit()

        service = VIPService(db_session)
        new_stage = service.advance_vip_entry_stage(sample_user.telegram_id)

        assert new_stage == 2
        db_session.refresh(sample_user)
        assert sample_user.vip_entry_stage == 2

    def test_advance_vip_entry_stage_bounds(self, db_session, sample_user):
        """Test que advance no supera el maximo de etapa 3"""
        sample_user.vip_entry_status = "pending_entry"
        sample_user.vip_entry_stage = 3
        db_session.commit()

        service = VIPService(db_session)
        new_stage = service.advance_vip_entry_stage(sample_user.telegram_id)

        assert new_stage == 3
        db_session.refresh(sample_user)
        assert sample_user.vip_entry_stage == 3

    def test_clear_vip_entry_state(self, db_session, sample_user):
        """Test limpiar estado de entrada VIP"""
        sample_user.vip_entry_status = "pending_entry"
        sample_user.vip_entry_stage = 2
        db_session.commit()

        service = VIPService(db_session)
        result = service.clear_vip_entry_state(sample_user.telegram_id)

        assert result is True
        db_session.refresh(sample_user)
        assert sample_user.vip_entry_status is None
        assert sample_user.vip_entry_stage is None

    def test_get_active_subscription_for_entry(self, db_session, sample_subscription, sample_user):
        """Test obtener suscripcion activa para entrada VIP"""
        service = VIPService(db_session)
        sub = service.get_active_subscription_for_entry(sample_user.id)

        assert sub is not None
        assert sub.id == sample_subscription.id

    def test_get_active_subscription_for_entry_expired(self, db_session, sample_user, sample_vip_channel, sample_token):
        """Test que no retorna suscripcion expirada"""
        from models.models import Subscription
        expired_sub = Subscription(
            user_id=sample_user.id,
            channel_id=sample_vip_channel.id,
            token_id=sample_token.id,
            end_date=datetime.utcnow() - timedelta(days=1),
            is_active=True
        )
        db_session.add(expired_sub)
        db_session.commit()

        service = VIPService(db_session)
        sub = service.get_active_subscription_for_entry(sample_user.id)

        assert sub is None

    def test_complete_vip_entry(self, db_session, sample_user):
        """Test completar entrada VIP"""
        sample_user.vip_entry_status = "pending_entry"
        sample_user.vip_entry_stage = 3
        db_session.commit()

        service = VIPService(db_session)
        result = service.complete_vip_entry(sample_user.telegram_id)

        assert result is True
        db_session.refresh(sample_user)
        assert sample_user.vip_entry_status == "active"
        assert sample_user.vip_entry_stage is None
