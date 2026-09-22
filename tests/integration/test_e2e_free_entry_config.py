"""
E2E Free ENTRY config sources — acceptance delay + anti-dup + ritual/welcome payloads.

Contrato:
- Delay de aceptación = Channel.wait_time_minutes (misma fuente que create_pending_request).
- Delay ritual = FREE_RITUAL_DELAY_SECONDS (scheduler_service).
- Mensajes = LucienVoice / build_*_payload (sin literales duplicados en el test).
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from handlers.free_channel_handlers import handle_join_request
from models.models import Channel, ChannelType, PendingRequest, User, UserRole
from services.channel_grant import build_approval_payload, build_welcome_payload, grant_pending_request
from services.channel_service import ChannelService
from services.scheduler_service import FREE_RITUAL_DELAY_SECONDS
from utils.lucien_voice import LucienVoice

pytestmark = [pytest.mark.integration]


def _make_join_request(*, user_id: int, chat_id: int, username="e2euser", first_name="E2E"):
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    return SimpleNamespace(
        from_user=SimpleNamespace(
            id=user_id,
            username=username,
            first_name=first_name,
            last_name=None,
        ),
        chat=SimpleNamespace(id=chat_id),
        user_chat_id=user_id,
        bot=bot,
    )


@pytest.mark.asyncio
async def test_e2e_first_join_accepts_using_channel_wait_time_minutes(
    db_session, mock_bot
):
    """1ª solicitud → pending → ready por wait_time_minutes → grant/aceptado.

    El delay se lee desde Channel.wait_time_minutes (DB), no desde un literal del test.
    """
    channel = Channel(
        channel_id=-1005551001,
        channel_name="Free E2E Config",
        channel_type=ChannelType.FREE,
        is_active=True,
        wait_time_minutes=2,  # valor de fixture DB; el assert lee este campo
        invite_link="https://t.me/+E2EFreeInvite",
        approval_message=None,
        welcome_message=None,
    )
    user = User(
        telegram_id=5551001,
        username="e2efirst",
        first_name="First",
        role=UserRole.USER,
    )
    db_session.add_all([channel, user])
    db_session.commit()
    db_session.refresh(channel)
    db_session.refresh(user)

    # Fuente canónica del delay de aceptación (misma que create_pending_request)
    acceptance_delay_minutes = channel.wait_time_minutes
    assert acceptance_delay_minutes == channel.wait_time_minutes
    assert FREE_RITUAL_DELAY_SECONDS > 0  # ritual delay compartido (no aceptación TG)

    svc = ChannelService(db_session)
    before = datetime.now(UTC)
    request = svc.create_pending_request(
        user_id=user.telegram_id,
        channel_id=channel.id,
        username=user.username,
        first_name=user.first_name,
        user_chat_id=user.telegram_id,
    )
    after = datetime.now(UTC)

    # scheduled_approval_at = now + Channel.wait_time_minutes (tolerancia de reloj)
    expected_min = before + timedelta(minutes=acceptance_delay_minutes)
    expected_max = after + timedelta(minutes=acceptance_delay_minutes)
    scheduled = request.scheduled_approval_at
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=UTC)
    assert expected_min <= scheduled <= expected_max
    assert request.status == "pending"

    # Aún no ready mientras falte el delay del canal
    assert request.id not in {r.id for r in svc.get_ready_to_approve()}

    # Avanzar el reloj de aprobación usando el mismo wait_time leído del canal
    request.scheduled_approval_at = datetime.now(UTC) - timedelta(
        minutes=acceptance_delay_minutes
    )
    db_session.commit()

    ready = svc.get_ready_to_approve()
    assert any(r.id == request.id for r in ready)

    # Payloads desde las mismas builders del runtime (fallback LucienVoice)
    expected_ritual = build_approval_payload(channel)
    expected_welcome = build_welcome_payload(channel)
    assert expected_ritual == LucienVoice.free_entry_ritual(channel.channel_name)
    assert LucienVoice.free_entry_welcome(channel.channel_name) in expected_welcome
    assert channel.invite_link in expected_welcome

    mock_bot.reset_mock()
    result = await grant_pending_request(db_session, request, mock_bot)
    assert result.success is True

    db_session.refresh(request)
    assert request.status == "approved"
    assert request.approved_at is not None

    mock_bot.approve_chat_join_request.assert_awaited_once_with(
        chat_id=channel.channel_id, user_id=user.telegram_id
    )
    mock_bot.send_message.assert_awaited()
    welcome_call = mock_bot.send_message.await_args
    assert welcome_call.kwargs["text"] == expected_welcome
    assert welcome_call.kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_e2e_second_join_sends_lucien_impatient_exact(db_session):
    """2ª ChatJoinRequest con pending existente → texto EXACTO free_entry_impatient."""
    channel = Channel(
        channel_id=-1005551002,
        channel_name="Free E2E Dup",
        channel_type=ChannelType.FREE,
        is_active=True,
        wait_time_minutes=5,
    )
    user = User(
        telegram_id=5551002,
        username="e2edup",
        first_name="Dup",
        role=UserRole.USER,
    )
    db_session.add_all([channel, user])
    db_session.commit()
    db_session.refresh(channel)
    db_session.refresh(user)

    svc = ChannelService(db_session)
    svc.create_pending_request(
        user_id=user.telegram_id,
        channel_id=channel.id,
        username=user.username,
        first_name=user.first_name,
    )

    join_req = _make_join_request(user_id=user.telegram_id, chat_id=channel.channel_id)

    # Handler construye UserService/ChannelService propios → inyectar sesión de test
    user_svc = MagicMock()
    user_svc.get_or_create_user.return_value = user
    user_svc.close = MagicMock()

    channel_svc = ChannelService(db_session)
    # close no debe cerrar la sesión compartida del fixture
    channel_svc.close = MagicMock()  # type: ignore[method-assign]

    sched = MagicMock()
    sched.schedule_free_welcome = MagicMock()

    with (
        patch("handlers.free_channel_handlers.UserService", return_value=user_svc),
        patch("handlers.free_channel_handlers.ChannelService", return_value=channel_svc),
        patch("handlers.free_channel_handlers.get_scheduler", return_value=sched),
    ):
        await handle_join_request(join_req)

    expected = LucienVoice.free_entry_impatient(channel.channel_name or "Los Kinkys")
    join_req.bot.send_message.assert_awaited_once()
    call = join_req.bot.send_message.await_args
    assert call.kwargs["chat_id"] == user.telegram_id
    assert call.kwargs["text"] == expected
    assert call.kwargs["parse_mode"] == "HTML"

    # No debe re-programar ritual ni crear otra pending
    sched.schedule_free_welcome.assert_not_called()
    pending = (
        db_session.query(PendingRequest)
        .filter(
            PendingRequest.user_id == user.telegram_id,
            PendingRequest.channel_id == channel.id,
            PendingRequest.status == "pending",
        )
        .all()
    )
    assert len(pending) == 1


@pytest.mark.asyncio
async def test_e2e_schedule_free_welcome_uses_shared_ritual_delay(mock_bot):
    """schedule_free_welcome usa FREE_RITUAL_DELAY_SECONDS (no literal 30 en el test)."""
    from services.scheduler_service import SchedulerService

    scheduler = SchedulerService(mock_bot)
    with patch.object(scheduler._scheduler, "add_job") as mock_add_job:
        before = datetime.now(UTC)
        scheduler.schedule_free_welcome(999, -1005551003)
        after = datetime.now(UTC)

    trigger = mock_add_job.call_args.kwargs["trigger"]
    run_date = trigger.run_date
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=UTC)

    expected_min = before + timedelta(seconds=FREE_RITUAL_DELAY_SECONDS)
    expected_max = after + timedelta(seconds=FREE_RITUAL_DELAY_SECONDS)
    assert expected_min <= run_date <= expected_max
