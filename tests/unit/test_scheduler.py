"""
Tests unitarios para SchedulerService.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from services.scheduler_service import SchedulerService


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
