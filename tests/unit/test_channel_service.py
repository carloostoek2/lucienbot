"""
Tests unitarios para ChannelService.
"""
import pytest
from datetime import datetime, timedelta

from services.channel_service import ChannelService
from models.models import ChannelType


@pytest.mark.unit
class TestChannelService:
    """Tests para el servicio de canales"""

    def test_create_channel_vip(self, db_session):
        """Test crear canal VIP"""
        service = ChannelService(db_session)

        channel = service.create_channel(
            channel_id=-1001234567890,
            channel_name="Canal VIP Test",
            channel_type=ChannelType.VIP
        )

        assert channel.channel_id == -1001234567890
        assert channel.channel_name == "Canal VIP Test"
        assert channel.channel_type == ChannelType.VIP
        assert channel.is_active is True
        assert channel.wait_time_minutes == 0  # VIP no tiene tiempo de espera

    def test_create_channel_free(self, db_session):
        """Test crear canal Free con tiempo de espera"""
        service = ChannelService(db_session)

        channel = service.create_channel(
            channel_id=-1000987654321,
            channel_name="Canal Free Test",
            channel_type=ChannelType.FREE,
            wait_time=5
        )

        assert channel.channel_type == ChannelType.FREE
        assert channel.wait_time_minutes == 5

    def test_get_channel_by_id(self, db_session, sample_vip_channel):
        """Test obtener canal por ID de Telegram"""
        service = ChannelService(db_session)

        channel = service.get_channel_by_id(sample_vip_channel.channel_id)

        assert channel is not None
        assert channel.id == sample_vip_channel.id
        assert channel.channel_name == sample_vip_channel.channel_name

    def test_get_channel_by_db_id(self, db_session, sample_vip_channel):
        """Test obtener canal por ID de base de datos"""
        service = ChannelService(db_session)

        channel = service.get_channel_by_db_id(sample_vip_channel.id)

        assert channel is not None
        assert channel.id == sample_vip_channel.id

    def test_get_all_channels(self, db_session, sample_vip_channel, sample_free_channel):
        """Test obtener todos los canales activos"""
        service = ChannelService(db_session)

        channels = service.get_all_channels()

        assert len(channels) >= 2
        channel_ids = [c.id for c in channels]
        assert sample_vip_channel.id in channel_ids
        assert sample_free_channel.id in channel_ids

    def test_get_free_channels(self, db_session, sample_free_channel):
        """Test obtener solo canales Free"""
        service = ChannelService(db_session)

        channels = service.get_free_channels()

        assert len(channels) >= 1
        for channel in channels:
            assert channel.channel_type == ChannelType.FREE

    def test_get_vip_channels(self, db_session, sample_vip_channel):
        """Test obtener solo canales VIP"""
        service = ChannelService(db_session)

        channels = service.get_vip_channels()

        assert len(channels) >= 1
        for channel in channels:
            assert channel.channel_type == ChannelType.VIP

    def test_delete_channel(self, db_session, sample_free_channel):
        """Test eliminar (desactivar) canal"""
        service = ChannelService(db_session)

        result = service.delete_channel(sample_free_channel.id)

        assert result is True
        # Verificar que ya no aparece en la lista
        channels = service.get_all_channels()
        channel_ids = [c.id for c in channels]
        assert sample_free_channel.id not in channel_ids

    def test_delete_channel_not_found(self, db_session):
        """Test eliminar canal inexistente"""
        service = ChannelService(db_session)

        result = service.delete_channel(99999)

        assert result is False

    def test_update_wait_time(self, db_session, sample_free_channel):
        """Test actualizar tiempo de espera de canal Free"""
        service = ChannelService(db_session)
        new_wait_time = 10

        result = service.update_wait_time(sample_free_channel.id, new_wait_time)

        assert result is True
        updated = service.get_channel_by_db_id(sample_free_channel.id)
        assert updated.wait_time_minutes == new_wait_time

    def test_update_wait_time_vip_channel(self, db_session, sample_vip_channel):
        """Test actualizar tiempo de espera de canal VIP (debería fallar)"""
        service = ChannelService(db_session)

        result = service.update_wait_time(sample_vip_channel.id, 5)

        assert result is False


@pytest.mark.unit
class TestPendingRequests:
    """Tests para solicitudes pendientes"""

    def test_create_pending_request(self, db_session, sample_user, sample_free_channel):
        """Test crear solicitud pendiente"""
        service = ChannelService(db_session)

        request = service.create_pending_request(
            user_id=sample_user.id,
            channel_id=sample_free_channel.id,
            username="testuser",
            first_name="Test"
        )

        assert request.user_id == sample_user.id
        assert request.channel_id == sample_free_channel.id
        assert request.username == "testuser"
        assert request.first_name == "Test"
        assert request.status == "pending"

        # Verificar que la fecha de aprobación programada está en el futuro
        expected_time = datetime.utcnow() + timedelta(minutes=sample_free_channel.wait_time_minutes)
        assert abs((request.scheduled_approval_at - expected_time).total_seconds()) < 60

    def test_create_pending_request_invalid_channel(self, db_session, sample_user):
        """Test crear solicitud para canal inexistente"""
        service = ChannelService(db_session)

        with pytest.raises(ValueError, match="Canal no encontrado"):
            service.create_pending_request(
                user_id=sample_user.id,
                channel_id=99999
            )

    def test_get_pending_request(self, db_session, sample_pending_request):
        """Test obtener solicitud pendiente específica"""
        service = ChannelService(db_session)

        request = service.get_pending_request(
            user_id=sample_pending_request.user_id,
            channel_id=sample_pending_request.channel_id
        )

        assert request is not None
        assert request.id == sample_pending_request.id
        assert request.status == "pending"

    def test_get_pending_requests_by_channel(self, db_session, sample_pending_request):
        """Test obtener solicitudes pendientes de un canal"""
        service = ChannelService(db_session)

        requests = service.get_pending_requests_by_channel(sample_pending_request.channel_id)

        assert len(requests) >= 1
        assert any(r.id == sample_pending_request.id for r in requests)

    def test_get_all_pending_requests(self, db_session, sample_pending_request):
        """Test obtener todas las solicitudes pendientes"""
        service = ChannelService(db_session)

        requests = service.get_all_pending_requests()

        assert len(requests) >= 1
        assert any(r.id == sample_pending_request.id for r in requests)

    def test_get_ready_to_approve(self, db_session, sample_free_channel, sample_user):
        """Test obtener solicitudes listas para aprobar"""
        service = ChannelService(db_session)

        # Crear una solicitud con tiempo ya vencido
        from models.models import PendingRequest
        request = PendingRequest(
            user_id=sample_user.id,
            channel_id=sample_free_channel.id,
            scheduled_approval_at=datetime.utcnow() - timedelta(minutes=1),
            status="pending"
        )
        db_session.add(request)
        db_session.commit()

        ready = service.get_ready_to_approve()

        assert len(ready) >= 1
        assert any(r.id == request.id for r in ready)

    def test_approve_request(self, db_session, sample_pending_request):
        """Test aprobar solicitud"""
        service = ChannelService(db_session)

        result = service.approve_request(sample_pending_request.id)

        assert result is True
        approved = db_session.query(type(sample_pending_request)).filter_by(id=sample_pending_request.id).first()
        assert approved.status == "approved"
        assert approved.approved_at is not None

    def test_cancel_request(self, db_session, sample_user, sample_free_channel):
        """Test cancelar solicitud"""
        service = ChannelService(db_session)

        # Crear una solicitud primero
        request = service.create_pending_request(
            user_id=sample_user.id,
            channel_id=sample_free_channel.id
        )

        result = service.cancel_request(sample_user.id, sample_free_channel.id)

        assert result is True
        cancelled = db_session.query(type(request)).filter_by(id=request.id).first()
        assert cancelled.status == "cancelled"

    def test_approve_all_pending(self, db_session, sample_free_channel):
        """Test aprobar todas las solicitudes pendientes de un canal"""
        service = ChannelService(db_session)

        # Crear algunas solicitudes
        from models.models import User
        for i in range(3):
            user = User(telegram_id=1000000 + i, username=f"user{i}")
            db_session.add(user)
            db_session.flush()
            service.create_pending_request(
                user_id=user.id,
                channel_id=sample_free_channel.id
            )

        count = service.approve_all_pending(sample_free_channel.id)

        assert count >= 3
        pending = service.get_pending_requests_by_channel(sample_free_channel.id)
        assert len(pending) == 0

    def test_count_pending_requests(self, db_session, sample_pending_request):
        """Test contar solicitudes pendientes"""
        service = ChannelService(db_session)

        count = service.count_pending_requests(sample_pending_request.channel_id)

        assert count >= 1

    def test_get_pending_request_returns_none_after_approval(self, db_session, sample_user, sample_free_channel):
        """Regression: after approval, get_pending_request should return None."""
        service = ChannelService(db_session)
        request = service.create_pending_request(
            user_id=sample_user.id,
            channel_id=sample_free_channel.id
        )
        service.approve_request(request.id)
        pending = service.get_pending_request(sample_user.id, sample_free_channel.id)
        assert pending is None
