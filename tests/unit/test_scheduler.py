"""
Tests unitarios para SchedulerService.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from services.scheduler_service import SchedulerService


@pytest.mark.unit
class TestScheduleFreeWelcomeChannelId:
    """Regression test: schedule_free_welcome debe recibir Telegram channel ID, no DB PK.

    Bug encontrado: handle_join_request pasaba channel.id (DB PK) a schedule_free_welcome,
    pero _send_free_welcome_job usa get_channel_by_id que espera Telegram channel ID.
    Esto causaba que el mensaje de 30s nunca se enviara porque channel lookup siempre
    fallaba (tabla Channel.channel_id = Telegram ID, no DB PK).
    """

    def test_schedule_free_welcome_receives_telegram_channel_id(self):
        """Verifica que schedule_free_welcome recibe el ID correcto (Telegram, no DB PK)."""
        mock_bot = AsyncMock()
        mock_bot.token = "test_token"

        scheduler = SchedulerService(mock_bot)

        telegram_channel_id = -1001234567890
        db_pk = 42  # Simula el DB PK que channel.id devolvería
        user_id = 111222333

        with patch.object(scheduler._scheduler, 'add_job') as mock_add_job:
            scheduler.schedule_free_welcome(user_id, telegram_channel_id)

            call = mock_add_job.call_args
            assert call is not None, "add_job was not called"
            assert call.kwargs.get('id') == f"free_welcome_{user_id}_{telegram_channel_id}"
            assert call.kwargs['kwargs']['channel_id'] == telegram_channel_id
            # El channel_id en kwargs DEBE ser el Telegram ID, no el DB PK
            assert call.kwargs['kwargs']['channel_id'] != db_pk


@pytest.mark.unit
class TestSchedulerTriggers:
    """Tests para verificacion de triggers del scheduler"""

    def test_pending_requests_uses_interval_trigger(self):
        """Test que approve_join_requests usa IntervalTrigger de 30 segundos"""
        mock_bot = AsyncMock()
        mock_bot.token = "test_token"

        scheduler = SchedulerService(mock_bot)

        with patch.object(scheduler._scheduler, 'add_job') as mock_add_job:
            import asyncio
            asyncio.run(scheduler.start())

            # Find the approve_join_requests job call
            approve_call = None
            for call in mock_add_job.call_args_list:
                if call.kwargs.get('id') == 'approve_join_requests':
                    approve_call = call
                    break

            assert approve_call is not None, "approve_join_requests job not found"
            trigger = approve_call.kwargs['trigger']
            assert isinstance(trigger, IntervalTrigger), f"Expected IntervalTrigger, got {type(trigger)}"
            assert trigger.interval.total_seconds() == 30, f"Expected interval 30s, got {trigger.interval}"

    def test_schedule_free_welcome_uses_date_trigger(self):
        """Test que schedule_free_welcome usa DateTrigger con replace_existing=True"""
        mock_bot = AsyncMock()
        mock_bot.token = "test_token"

        scheduler = SchedulerService(mock_bot)

        with patch.object(scheduler._scheduler, 'add_job') as mock_add_job:
            scheduler.schedule_free_welcome(12345, -100111222)

            assert mock_add_job.called, "add_job was not called"
            call = mock_add_job.call_args
            trigger = call.kwargs['trigger']
            assert isinstance(trigger, DateTrigger), f"Expected DateTrigger, got {type(trigger)}"
            assert call.kwargs['id'] == 'free_welcome_12345_-100111222'
            assert call.kwargs['replace_existing'] is True
