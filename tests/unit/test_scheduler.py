"""
Tests unitarios para SchedulerService.
"""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from services.scheduler_service import SchedulerService
from services.nurture_service import NurtureService  # for remove test if needed


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

        with patch.object(scheduler._scheduler, "add_job") as mock_add_job:
            scheduler.schedule_free_welcome(user_id, telegram_channel_id)

            call = mock_add_job.call_args
            assert call is not None, "add_job was not called"
            assert call.kwargs.get("id") == f"free_welcome_{user_id}_{telegram_channel_id}"
            assert call.kwargs["kwargs"]["channel_id"] == telegram_channel_id
            # El channel_id en kwargs DEBE ser el Telegram ID, no el DB PK
            assert call.kwargs["kwargs"]["channel_id"] != db_pk


@pytest.mark.unit
class TestSchedulerTriggers:
    """Tests para verificacion de triggers del scheduler"""

    def test_pending_requests_uses_interval_trigger(self):
        """Test que approve_join_requests usa IntervalTrigger de 30 segundos"""
        mock_bot = AsyncMock()
        mock_bot.token = "test_token"

        scheduler = SchedulerService(mock_bot)

        with patch.object(scheduler._scheduler, "add_job") as mock_add_job:
            import asyncio

            asyncio.run(scheduler.start())

            # Find the approve_join_requests job call
            approve_call = None
            for call in mock_add_job.call_args_list:
                if call.kwargs.get("id") == "approve_join_requests":
                    approve_call = call
                    break

            assert approve_call is not None, "approve_join_requests job not found"
            trigger = approve_call.kwargs["trigger"]
            assert isinstance(trigger, IntervalTrigger), (
                f"Expected IntervalTrigger, got {type(trigger)}"
            )
            assert trigger.interval.total_seconds() == 30, (
                f"Expected interval 30s, got {trigger.interval}"
            )

    def test_pending_mission_rewards_job_registered_on_start(self):
        """start() registra job pending_mission_rewards cada 30 min."""
        mock_bot = AsyncMock()
        mock_bot.token = "test_token"
        scheduler = SchedulerService(mock_bot)

        with patch.object(scheduler._scheduler, "add_job") as mock_add_job:
            import asyncio

            asyncio.run(scheduler.start())

            pending_call = None
            for call in mock_add_job.call_args_list:
                if call.kwargs.get("id") == "pending_mission_rewards":
                    pending_call = call
                    break

            assert pending_call is not None, "pending_mission_rewards job not found"
            trigger = (
                pending_call.kwargs.get("trigger")
                if pending_call.kwargs.get("trigger") is not None
                else (pending_call.args[1] if len(pending_call.args) > 1 else None)
            )
            assert isinstance(trigger, IntervalTrigger)
            assert trigger.interval.total_seconds() == 30 * 60

    def test_reset_monthly_store_caps_job_registered_on_start(self):
        """start() registra job reset_monthly_store_caps el día 1."""
        mock_bot = AsyncMock()
        mock_bot.token = "test_token"
        scheduler = SchedulerService(mock_bot)

        with patch.object(scheduler._scheduler, "add_job") as mock_add_job:
            import asyncio

            asyncio.run(scheduler.start())

            cap_call = None
            for call in mock_add_job.call_args_list:
                if call.kwargs.get("id") == "reset_monthly_store_caps":
                    cap_call = call
                    break

            assert cap_call is not None, "reset_monthly_store_caps job not found"
            assert cap_call.kwargs.get("day") == 1


@pytest.mark.unit
class TestPendingMissionRewardsJob:
    """Tests para job _process_pending_mission_rewards."""

    @pytest.mark.asyncio
    @patch("services.mission_service.MissionService")
    @patch("services.scheduler_service._get_bot")
    @patch("services.scheduler_service.SessionLocal")
    async def test_process_pending_mission_rewards_per_user(
        self, mock_session_local, mock_get_bot, mock_mission_service_cls
    ):
        """Scheduler invoca deliver_pending_rewards por usuario con error isolation."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_bot = AsyncMock()
        mock_get_bot.return_value = mock_bot

        mock_service = MagicMock()
        mock_service.get_users_with_pending_reward_deliveries.return_value = [111, 222]
        mock_service.deliver_pending_rewards = AsyncMock(side_effect=[2, RuntimeError("boom")])
        mock_mission_service_cls.return_value = mock_service

        from services.scheduler_service import _process_pending_mission_rewards

        await _process_pending_mission_rewards()

        mock_service.get_users_with_pending_reward_deliveries.assert_called_once()
        assert mock_service.deliver_pending_rewards.await_count == 2
        mock_service.deliver_pending_rewards.assert_any_await(111, bot=mock_bot)
        mock_service.deliver_pending_rewards.assert_any_await(222, bot=mock_bot)
        mock_db.close.assert_called_once()

    def test_schedule_free_welcome_uses_date_trigger(self):
        """Test que schedule_free_welcome usa DateTrigger con replace_existing=True"""
        mock_bot = AsyncMock()
        mock_bot.token = "test_token"

        scheduler = SchedulerService(mock_bot)

        with patch.object(scheduler._scheduler, "add_job") as mock_add_job:
            scheduler.schedule_free_welcome(12345, -100111222)

            assert mock_add_job.called, "add_job was not called"
            call = mock_add_job.call_args
            trigger = call.kwargs["trigger"]
            assert isinstance(trigger, DateTrigger), f"Expected DateTrigger, got {type(trigger)}"
            assert call.kwargs["id"] == "free_welcome_12345_-100111222"
            assert call.kwargs["replace_existing"] is True


class TestNurtureSchedulerGold:
    """R3 gold extension: schedule_nurture_step exact (job_id, DateTrigger, replace_existing) + remove with None (prefix)."""

    def test_schedule_nurture_step_uses_date_trigger_and_exact_id(self):
        mock_bot = AsyncMock()
        mock_bot.token = "test_token"
        scheduler = SchedulerService(mock_bot)

        with patch.object(scheduler._scheduler, "add_job") as mock_add_job:
            scheduler.schedule_nurture_step(12345, 99, datetime.now(UTC) + timedelta(hours=1))

            assert mock_add_job.called
            call = mock_add_job.call_args
            trigger = call.kwargs["trigger"]
            assert isinstance(trigger, DateTrigger)
            assert call.kwargs["id"] == "nurture_12345_99"
            assert call.kwargs["replace_existing"] is True
            assert call.kwargs["kwargs"]["user_id"] == 12345
            assert call.kwargs["kwargs"]["step_id"] == 99

    def test_remove_nurture_jobs_none_prefix(self):
        mock_bot = AsyncMock()
        mock_bot.token = "test_token"
        scheduler = SchedulerService(mock_bot)

        with patch.object(scheduler._scheduler, "remove_job") as mock_remove:
            with patch.object(scheduler._scheduler, "get_jobs") as mock_get:
                # simulate jobs
                j1 = MagicMock(id="nurture_12345_1")
                j2 = MagicMock(id="other_1")
                j3 = MagicMock(id="nurture_12345_2")
                mock_get.return_value = [j1, j2, j3]
                scheduler.remove_nurture_jobs(12345, step_ids=None)
                # should remove the two nurture_ for user
                assert mock_remove.call_count == 2
