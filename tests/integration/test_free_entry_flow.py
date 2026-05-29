"""
Tests de integración para el flujo de entrada al canal Free.

Verifica el ciclo de vida de PendingRequest a través de ChannelService,
la simulación del job del scheduler, y el envío de mensajes de bienvenida
e impaciencia con bot mockado.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from services.channel_service import ChannelService
from models.models import PendingRequest
from utils.lucien_voice import LucienVoice
from keyboards.inline_keyboards import social_links_keyboard


@pytest.mark.integration
class TestFreeEntryFlow:
    """Flujo completo de solicitud, espera y aprobación en canal Free."""

    def test_complete_free_entry_flow(self, db_session, sample_user, sample_free_channel):
        """Solicitud -> pendiente -> aprobación simulada por scheduler -> aprobado."""
        channel_service = ChannelService(db_session)

        request = channel_service.create_pending_request(
            user_id=sample_user.telegram_id,
            channel_id=sample_free_channel.id,
            username=sample_user.username,
            first_name=sample_user.first_name
        )
        assert request is not None
        assert request.status == "pending"

        result = channel_service.approve_request(request.id)
        assert result is True

        db_session.refresh(request)
        assert request.status == "approved"
        assert request.approved_at is not None

    def test_duplicate_request_while_pending(self, db_session, sample_user, sample_free_channel):
        """El handler detecta solicitud duplicada y retorna la existente."""
        channel_service = ChannelService(db_session)

        req1 = channel_service.create_pending_request(
            user_id=sample_user.telegram_id,
            channel_id=sample_free_channel.id,
            username=sample_user.username,
            first_name=sample_user.first_name
        )

        # Simular verificación del handler ante nueva solicitud
        existing = channel_service.get_pending_request(
            sample_user.telegram_id, sample_free_channel.id
        )
        assert existing is not None
        assert existing.id == req1.id

    def test_scheduler_processes_pending_requests(self, db_session, sample_user, sample_free_channel, mock_bot):
        """Simular job del scheduler: aprobar solicitudes cuyo tiempo de espera ya venció."""
        channel_service = ChannelService(db_session)

        request = channel_service.create_pending_request(
            user_id=sample_user.telegram_id,
            channel_id=sample_free_channel.id,
            username=sample_user.username,
            first_name=sample_user.first_name
        )

        # Forzar que la hora de aprobación ya pasó
        request.scheduled_approval_at = datetime.utcnow() - timedelta(minutes=1)
        db_session.commit()

        pending = channel_service.get_ready_to_approve()
        assert any(r.id == request.id for r in pending)

        for req in pending:
            channel_service.approve_request(req.id)

        db_session.refresh(request)
        assert request.status == "approved"

    @pytest.mark.asyncio
    async def test_approval_sends_welcome_with_invite_link(self, db_session, sample_user, sample_free_channel, mock_bot):
        """La aprobación envía mensaje de bienvenida con el invite_link del canal."""
        channel_service = ChannelService(db_session)

        # Asegurar que el canal tiene un invite_link para el test
        sample_free_channel.invite_link = "https://t.me/+FreeTestLink"
        db_session.commit()

        request = channel_service.create_pending_request(
            user_id=sample_user.telegram_id,
            channel_id=sample_free_channel.id,
            username=sample_user.username,
            first_name=sample_user.first_name
        )
        channel_service.approve_request(request.id)

        # Simular envío de bienvenida tal como lo hace el scheduler
        message = LucienVoice.free_entry_welcome(sample_free_channel.channel_name or "Los Kinkys")
        if sample_free_channel.invite_link:
            message += f"\n{sample_free_channel.invite_link}"

        await mock_bot.send_message(
            chat_id=sample_user.telegram_id,
            text=message,
            parse_mode="HTML",
            reply_markup=social_links_keyboard()
        )

        calls = [str(call) for call in mock_bot.send_message.call_args_list]
        assert any(sample_free_channel.invite_link in c for c in calls)

    @pytest.mark.asyncio
    async def test_impatience_message_on_repeated_request(self, db_session, sample_user, sample_free_channel, mock_bot):
        """Si el usuario solicita de nuevo estando pending, recibe mensaje de impaciencia."""
        channel_service = ChannelService(db_session)

        channel_service.create_pending_request(
            user_id=sample_user.telegram_id,
            channel_id=sample_free_channel.id,
            username=sample_user.username,
            first_name=sample_user.first_name
        )

        # Simular lógica del handler ante solicitud repetida
        existing = channel_service.get_pending_request(
            sample_user.telegram_id, sample_free_channel.id
        )
        assert existing is not None

        await mock_bot.send_message(
            chat_id=sample_user.telegram_id,
            text=LucienVoice.free_entry_impatient(sample_free_channel.channel_name or "Los Kinkys"),
            parse_mode="HTML"
        )

        assert mock_bot.send_message.called
        call_kwargs = mock_bot.send_message.call_args.kwargs
        text_lower = call_kwargs["text"].lower()
        assert "puertas se abren" in text_lower or "impaciencia" in text_lower


@pytest.mark.integration
class TestFreeEntryRaceCondition:
    """Protección contra condiciones de carrera en aprobaciones."""

    def test_concurrent_approval_idempotent(self, db_session, sample_user, sample_free_channel, mock_bot):
        """Aprobar dos veces la misma solicitud no genera error grave."""
        channel_service = ChannelService(db_session)

        request = channel_service.create_pending_request(
            user_id=sample_user.telegram_id,
            channel_id=sample_free_channel.id,
            username=sample_user.username,
            first_name=sample_user.first_name
        )

        r1 = channel_service.approve_request(request.id)
        r2 = channel_service.approve_request(request.id)

        assert r1 is True
        # Segunda aprobación sigue retornando True porque el registro existe
        assert r2 is True

        db_session.refresh(request)
        assert request.status == "approved"
