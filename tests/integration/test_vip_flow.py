"""
Tests de integración para el flujo VIP completo.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from services.vip_service import VIPService
from services.channel_service import ChannelService
from models.models import TokenStatus, ChannelType


@pytest.mark.integration
class TestVIPFlow:
    """Tests de integración para flujo VIP completo"""

    def test_complete_vip_flow(self, db_session, sample_admin, sample_user):
        """Test flujo VIP completo: crear tarifa -> generar token -> canjear -> verificar suscripción"""
        vip_service = VIPService(db_session)
        channel_service = ChannelService(db_session)

        # 1. Crear canal VIP
        vip_channel = channel_service.create_channel(
            channel_id=-100999888777,
            channel_name="VIP Integration Test",
            channel_type=ChannelType.VIP
        )
        assert vip_channel is not None

        # 2. Crear tarifa
        tariff = vip_service.create_tariff(
            name="Monthly VIP",
            duration_days=30,
            price="19.99",
            currency="USD"
        )
        assert tariff is not None
        assert tariff.duration_days == 30

        # 3. Generar token
        token = vip_service.generate_token(tariff.id, expires_in_days=7)
        assert token is not None
        assert token.status == TokenStatus.ACTIVE
        assert token.tariff_id == tariff.id

        # 4. Validar token
        validated_token, error = vip_service.validate_token(token.token_code)
        assert error is None
        assert validated_token is not None
        assert validated_token.id == token.id

        # 5. Canjear token
        subscription = vip_service.redeem_token(token.token_code, sample_user.id)
        assert subscription is not None
        assert subscription.user_id == sample_user.id
        assert subscription.channel_id == vip_channel.id
        assert subscription.is_active is True

        # 6. Verificar token marcado como usado
        updated_token = vip_service.get_token(token.id)
        assert updated_token.status == TokenStatus.USED
        assert updated_token.redeemed_by_id == sample_user.id
        assert updated_token.redeemed_at is not None

        # 7. Verificar que el usuario es VIP
        is_vip = vip_service.is_user_vip(sample_user.id)
        assert is_vip is True

        # 8. Verificar suscripción activa
        user_subscription = vip_service.get_user_subscription(sample_user.id)
        assert user_subscription is not None
        assert user_subscription.id == subscription.id

        # 9. Verificar fecha de expiración (30 días desde ahora)
        expected_end = datetime.utcnow() + timedelta(days=30)
        assert abs((subscription.end_date - expected_end).total_seconds()) < 60

    def test_token_expiration_flow(self, db_session, sample_tariff, sample_user):
        """Test flujo de expiración de token"""
        vip_service = VIPService(db_session)

        # Generar token con expiración muy corta (ya expirado)
        token = vip_service.generate_token(sample_tariff.id, expires_in_days=-1)

        # Intentar validar token expirado
        validated_token, error = vip_service.validate_token(token.token_code)
        assert error == "expired"
        assert validated_token is None

        # Intentar canjear token expirado
        subscription = vip_service.redeem_token(token.token_code, sample_user.id)
        assert subscription is None

    def test_token_already_used_flow(self, db_session, sample_token, sample_user, sample_vip_channel):
        """Test flujo de token ya usado"""
        vip_service = VIPService(db_session)

        # Canjear token por primera vez
        subscription1 = vip_service.redeem_token(sample_token.token_code, sample_user.id)
        assert subscription1 is not None

        # Intentar canjear el mismo token de nuevo
        subscription2 = vip_service.redeem_token(sample_token.token_code, sample_user.id)
        assert subscription2 is None

    def test_subscription_expiration_detection(self, db_session, sample_user, sample_vip_channel, sample_token):
        """Test detección de suscripciones expiradas"""
        vip_service = VIPService(db_session)

        # Crear suscripción expirada
        from models.models import Subscription
        expired_subscription = Subscription(
            user_id=sample_user.id,
            channel_id=sample_vip_channel.id,
            token_id=sample_token.id,
            end_date=datetime.utcnow() - timedelta(days=1),
            is_active=True  # Aún marcada como activa
        )
        db_session.add(expired_subscription)
        db_session.commit()

        # Verificar que aparece en suscripciones expiradas
        expired = vip_service.get_expired_subscriptions()
        assert any(s.id == expired_subscription.id for s in expired)

        # Expirar la suscripción
        result = vip_service.expire_subscription(expired_subscription.id)
        assert result is True

        # Verificar que ya no está activa
        updated = vip_service.get_subscription(expired_subscription.id)
        assert updated.is_active is False

    def test_reminder_system_flow(self, db_session, sample_user, sample_vip_channel, sample_token):
        """Test flujo de sistema de recordatorios"""
        vip_service = VIPService(db_session)

        # Crear suscripción que vence pronto (12 horas)
        from models.models import Subscription
        subscription = Subscription(
            user_id=sample_user.id,
            channel_id=sample_vip_channel.id,
            token_id=sample_token.id,
            end_date=datetime.utcnow() + timedelta(hours=12),
            is_active=True,
            reminder_sent=False
        )
        db_session.add(subscription)
        db_session.commit()

        # Verificar que aparece en suscripciones por vencer
        expiring = vip_service.get_expiring_subscriptions(hours=24)
        assert any(s.id == subscription.id for s in expiring)

        # Marcar recordatorio como enviado
        result = vip_service.mark_reminder_sent(subscription.id)
        assert result is True

        # Verificar que ya no aparece (reminder_sent = True)
        expiring = vip_service.get_expiring_subscriptions(hours=24)
        assert not any(s.id == subscription.id for s in expiring)

    def test_multiple_tariffs_tokens(self, db_session, sample_admin):
        """Test múltiples tarifas y tokens"""
        vip_service = VIPService(db_session)

        # Crear múltiples tarifas
        tariff_weekly = vip_service.create_tariff("Weekly", 7, "4.99")
        tariff_monthly = vip_service.create_tariff("Monthly", 30, "14.99")
        tariff_yearly = vip_service.create_tariff("Yearly", 365, "99.99")

        # Generar tokens para cada tarifa
        token_weekly = vip_service.generate_token(tariff_weekly.id)
        token_monthly = vip_service.generate_token(tariff_monthly.id)
        token_yearly = vip_service.generate_token(tariff_yearly.id)

        # Verificar que cada token está asociado a la tarifa correcta
        assert token_weekly.tariff_id == tariff_weekly.id
        assert token_monthly.tariff_id == tariff_monthly.id
        assert token_yearly.tariff_id == tariff_yearly.id

        # Verificar lista de tokens por tarifa
        weekly_tokens = vip_service.get_tokens_by_tariff(tariff_weekly.id)
        assert len(weekly_tokens) == 1
        assert weekly_tokens[0].id == token_weekly.id

    def test_active_subscriptions_filtering(self, db_session, sample_user, sample_vip_channel, sample_token):
        """Test filtrado de suscripciones activas"""
        vip_service = VIPService(db_session)

        # Crear suscripción activa
        from models.models import Subscription
        active_subscription = Subscription(
            user_id=sample_user.id,
            channel_id=sample_vip_channel.id,
            token_id=sample_token.id,
            end_date=datetime.utcnow() + timedelta(days=30),
            is_active=True
        )
        db_session.add(active_subscription)

        # Crear suscripción inactiva
        inactive_subscription = Subscription(
            user_id=sample_user.id + 1,
            channel_id=sample_vip_channel.id,
            token_id=sample_token.id,
            end_date=datetime.utcnow() + timedelta(days=30),
            is_active=False
        )
        db_session.add(inactive_subscription)
        db_session.commit()

        # Verificar que solo la activa aparece
        active = vip_service.get_active_subscriptions()
        assert any(s.id == active_subscription.id for s in active)
        assert not any(s.id == inactive_subscription.id for s in active)


@pytest.mark.integration
class TestVIPRaceConditions:
    """Tests de integración para verificar protección contra race conditions"""

    def test_concurrent_token_redemption(self, db_session, sample_tariff, sample_vip_channel):
        """Test que el token no puede ser canjeado dos veces (race condition)"""
        vip_service = VIPService(db_session)

        from models.models import User, Token

        # Crear token directamente
        token = Token(
            token_code="CONCURRENT123",
            tariff_id=sample_tariff.id,
            status=TokenStatus.ACTIVE
        )
        db_session.add(token)
        db_session.commit()
        token_code = token.token_code

        # Crear dos usuarios diferentes
        user1 = User(telegram_id=111111, username="user1")
        user2 = User(telegram_id=222222, username="user2")
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()
        user1_id = user1.id

        # Mock clase que simula la cadena query().filter().with_for_update().first()
        class MockTokenQuery:
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

        mock_token_chain = MockTokenQuery(token)

        with patch.object(db_session, 'query', return_value=mock_token_chain):
            # Simular canje simultáneo (en la realidad sería concurrente)
            subscription1 = vip_service.redeem_token(token_code, user1_id)

            # Intentar canjear de nuevo (debería fallar)
            subscription2 = vip_service.redeem_token(token_code, user2.id)

            # Solo uno debería tener éxito
            assert subscription1 is not None
            assert subscription2 is None

            # Verificar que se usó SELECT FOR UPDATE
            assert mock_token_chain.with_for_update_called

