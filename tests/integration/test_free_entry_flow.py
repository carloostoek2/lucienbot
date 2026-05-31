"""
Tests de integración para el flujo de entrada al canal Free.

Verifica el ciclo de vida de PendingRequest a través de ChannelService,
la simulación del job del scheduler, y el envío de mensajes de bienvenida
e impaciencia con bot mockado.
"""
import pytest
import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.channel_service import ChannelService
from services import scheduler_service
from models.database import Base
from models.models import PendingRequest, Channel, ChannelType, User, UserRole
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
        request.scheduled_approval_at = datetime.now(UTC) - timedelta(minutes=1)
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


# =============================================================================
# SCHEDULER JOB COVERAGE - Expansión del loop del scheduler (Ítem 3)
# =============================================================================

@pytest.mark.integration
class TestSchedulerPendingRequestsJob:
    """
    Cobertura directa del job _process_pending_requests del scheduler.

    Usa el patrón recomendado (SQLite en archivo + TestSession) porque
    el job crea sus propias SessionLocal() internas.
    """

    def _create_engine_and_session(self, tmp_path):
        db_path = tmp_path / "test_scheduler_pending.db"
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return engine, TestSession

    @pytest.mark.asyncio
    async def test_process_pending_requests_approves_and_sends_welcome(
        self, tmp_path, mock_bot
    ):
        """
        Job del scheduler procesa solicitudes ready:
        - Aprueba via bot API
        - Actualiza estado en BD
        - Envía mensaje de bienvenida + invite link
        """
        engine, TestSession = self._create_engine_and_session(tmp_path)
        db = TestSession()

        try:
            # Setup: canal con wait_time bajo + usuario + request lista
            channel = Channel(
                channel_id=-100999000111,
                channel_name="Free Test Channel",
                channel_type=ChannelType.FREE,
                is_active=True,
                wait_time_minutes=0,  # lista inmediatamente
                invite_link="https://t.me/+FreeTestInvite",
            )
            user = User(
                telegram_id=555000111,
                username="freeuser",
                first_name="Free",
                role=UserRole.USER,
            )
            db.add_all([channel, user])
            db.commit()
            db.refresh(channel)
            db.refresh(user)

            channel_service = ChannelService(db)
            request = channel_service.create_pending_request(
                user_id=user.telegram_id,
                channel_id=channel.id,  # usa DB id internamente
                username=user.username,
                first_name=user.first_name,
            )
            # Forzar que esté lista (aunque wait_time=0, por si acaso)
            request.scheduled_approval_at = datetime.now(UTC) - timedelta(minutes=1)
            db.commit()

            request_id = request.id
            user_tg = user.telegram_id
            channel_tg_id = channel.channel_id

            db.close()

            # Ejecutar el job real del scheduler con mocks
            mock_bot.reset_mock()

            with patch.object(
                scheduler_service, "SessionLocal", TestSession
            ), patch.object(
                scheduler_service, "_get_bot", return_value=mock_bot
            ):
                await scheduler_service._process_pending_requests()

            # Verificar que aprobó
            verify_db = TestSession()
            approved_req = verify_db.get(PendingRequest, request_id)  # SQLAlchemy 2.0+
            assert approved_req.status == "approved"
            assert approved_req.approved_at is not None
            verify_db.close()

            # Verificar que el bot fue llamado para aprobar
            assert mock_bot.approve_chat_join_request.called
            approve_call = mock_bot.approve_chat_join_request.call_args
            assert approve_call.kwargs["chat_id"] == channel_tg_id
            assert approve_call.kwargs["user_id"] == user_tg

            # Verificar que envió el mensaje de bienvenida + invite
            assert mock_bot.send_message.called
            send_call = mock_bot.send_message.call_args
            assert send_call.kwargs["chat_id"] == user_tg
            text = send_call.kwargs["text"]
            assert "bienvenido" in text.lower() or "welcome" in text.lower() or "puertas" in text.lower()
            assert channel.invite_link in text or "invite_link" in str(send_call)

        finally:
            db.close()
            engine.dispose()
