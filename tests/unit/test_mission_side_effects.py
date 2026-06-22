"""Tests para side-effects de misiones y helpers de racha diaria."""

import html
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.models import MissionFrequency, MissionType, UserRewardHistory
from services.besito_service import BesitoService
from services.mission_service import (
    MissionService,
    calculate_daily_gift_streak_from_dates,
    run_mission_side_effects_isolated,
)
from services.vip_service import VIPService


@pytest.mark.unit
class TestMissionSideEffects:
    def test_calculate_daily_gift_streak_from_dates(self):
        today = date(2026, 6, 16)
        dates = {today, today - timedelta(days=1), today - timedelta(days=2)}
        assert calculate_daily_gift_streak_from_dates(dates, today) == 3

    def test_calculate_daily_gift_streak_breaks_on_gap(self):
        today = date(2026, 6, 16)
        dates = {today, today - timedelta(days=2)}
        assert calculate_daily_gift_streak_from_dates(dates, today) == 1

    @pytest.mark.asyncio
    async def test_run_mission_side_effects_isolated_retries_then_succeeds(self):
        with patch(
            "services.mission_service.MissionService.increment_progress_and_deliver",
            new_callable=AsyncMock,
        ) as mock_increment:
            mock_increment.side_effect = [RuntimeError("db glitch"), []]
            count = await run_mission_side_effects_isolated(
                123456789,
                MissionType.REACTION_COUNT,
                reference_id=99,
            )
            assert count == 0
            assert mock_increment.await_count == 2

    @pytest.mark.asyncio
    async def test_increment_commits_progress_before_deliver(
        self, db_session, sample_user, sample_reward_besitos
    ):
        """Progreso debe persistir aunque deliver_reward falle."""
        service = MissionService(db_session)
        mission = service.create_mission(
            name="Commit Before Deliver",
            description="Regression",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        mock_bot = AsyncMock()

        with patch.object(
            MissionService,
            "_deliver_mission_reward_if_allowed",
            new_callable=AsyncMock,
            side_effect=RuntimeError("deliver boom"),
        ):
            try:
                await service.increment_progress_and_deliver(
                    sample_user.telegram_id,
                    MissionType.REACTION_COUNT,
                    amount=1,
                    bot=mock_bot,
                    reference_id=501,
                )
            except RuntimeError:
                pass

        progress = service.get_user_progress(sample_user.telegram_id, mission.id)
        assert progress is not None
        assert progress.is_completed is True
        assert progress.current_value == 1

    @pytest.mark.asyncio
    async def test_vip_redeem_auto_delivers_mission_reward(
        self,
        db_session,
        sample_user,
        sample_token,
        sample_vip_channel,
        mock_bot,
    ):
        """VIP redeem → misión VIP_ACTIVE → besitos + historial + mensaje Lucien."""
        mission_service = MissionService(db_session)
        from services.reward_service import RewardService

        rs = RewardService(db_session)
        reward = rs.create_reward_besitos("VIP Mission Reward", "Desc", 25)
        mission = mission_service.create_mission(
            name="Activar VIP",
            description="Active VIP",
            mission_type=MissionType.VIP_ACTIVE,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=reward.id,
        )

        vip_service = VIPService(db_session)
        subscription = await vip_service.redeem_token_with_missions(
            sample_token.token_code, sample_user.telegram_id, bot=mock_bot
        )
        assert subscription is not None

        progress = mission_service.get_user_progress(sample_user.telegram_id, mission.id)
        assert progress is not None
        assert progress.is_completed is True

        history = (
            db_session.query(UserRewardHistory)
            .filter(
                UserRewardHistory.user_id == sample_user.telegram_id,
                UserRewardHistory.mission_id == mission.id,
            )
            .all()
        )
        assert len(history) == 1
        balance = BesitoService(db=db_session).get_balance(sample_user.telegram_id)
        assert balance == 25
        # deliver_reward + celebration message
        assert mock_bot.send_message.await_count >= 1

    @pytest.mark.asyncio
    async def test_deliver_pending_rewards_retries_after_stock_failure(
        self, db_session, sample_user, sample_package, mock_bot
    ):
        """Catch-up entrega tras fallo inicial por stock agotado."""
        from services.package_service import PackageService
        from services.reward_service import RewardService

        sample_package.reward_stock = 0
        db_session.commit()

        mission_service = MissionService(db_session)
        rs = RewardService(db_session)
        reward = rs.create_reward_package("Pkg Mission", "Desc", sample_package.id)
        mission = mission_service.create_mission(
            name="Reaction Pkg",
            description="Get package",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=reward.id,
        )

        await mission_service.increment_progress_and_deliver(
            sample_user.telegram_id,
            MissionType.REACTION_COUNT,
            amount=1,
            bot=mock_bot,
            reference_id=9001,
        )
        progress = mission_service.get_user_progress(sample_user.telegram_id, mission.id)
        assert progress.is_completed is True
        assert (
            db_session.query(UserRewardHistory)
            .filter(UserRewardHistory.mission_id == mission.id)
            .count()
            == 0
        )

        sample_package.reward_stock = 1
        db_session.commit()
        pkg_service = PackageService(db_session)
        pkg_service.add_file_to_package(sample_package.id, "f1", "photo")
        db_session.commit()

        delivered = await mission_service.deliver_pending_rewards(
            sample_user.telegram_id, bot=mock_bot
        )
        assert delivered == 1
        assert (
            db_session.query(UserRewardHistory)
            .filter(UserRewardHistory.mission_id == mission.id)
            .count()
            == 1
        )

    @pytest.mark.asyncio
    async def test_idempotency_one_time_no_duplicate_besitos(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        """Segunda entrega ONE_TIME no duplica besitos."""
        mission_service = MissionService(db_session)
        mission = mission_service.create_mission(
            name="Once Only",
            description="One time",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        await mission_service.increment_progress_and_deliver(
            sample_user.telegram_id,
            MissionType.REACTION_COUNT,
            amount=1,
            bot=mock_bot,
            reference_id=8001,
        )
        balance_after_first = BesitoService(db=db_session).get_balance(sample_user.telegram_id)

        count2 = await mission_service.deliver_pending_rewards(
            sample_user.telegram_id, bot=mock_bot
        )
        balance_after_second = BesitoService(db=db_session).get_balance(sample_user.telegram_id)

        assert count2 == 0
        assert balance_after_first == balance_after_second == sample_reward_besitos.besito_amount

    @pytest.mark.asyncio
    async def test_package_mission_auto_deliver_sends_celebration(
        self, db_session, sample_user, sample_package, mock_bot
    ):
        """Primera entrega de paquete por misión: historial + mensaje Lucien."""
        from services.package_service import PackageService
        from services.reward_service import RewardService

        sample_package.reward_stock = 1
        db_session.commit()
        PackageService(db_session).add_file_to_package(sample_package.id, "f1", "photo")
        db_session.commit()

        mission_service = MissionService(db_session)
        rs = RewardService(db_session)
        reward = rs.create_reward_package("Pkg Auto", "Desc", sample_package.id)
        mission = mission_service.create_mission(
            name="Pkg Mission",
            description="Auto package",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=reward.id,
        )

        await mission_service.increment_progress_and_deliver(
            sample_user.telegram_id,
            MissionType.REACTION_COUNT,
            amount=1,
            bot=mock_bot,
            reference_id=9100,
        )

        history_count = (
            db_session.query(UserRewardHistory)
            .filter(UserRewardHistory.mission_id == mission.id)
            .count()
        )
        assert history_count == 1
        celebration_calls = [
            c
            for c in mock_bot.send_message.await_args_list
            if c.kwargs.get("parse_mode") == "HTML"
            and "Pkg Mission" in c.kwargs.get("text", c.args[1] if len(c.args) > 1 else "")
        ]
        assert len(celebration_calls) >= 1

    @pytest.mark.asyncio
    async def test_apply_daily_gift_mission_updates_idempotent(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        """Doble apply_daily_gift_mission_updates no re-entrega."""
        mission_service = MissionService(db_session)
        mission = mission_service.create_mission(
            name="Daily Total",
            description="Once",
            mission_type=MissionType.DAILY_GIFT_TOTAL,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        from datetime import UTC, datetime

        from models.models import DailyGiftClaim

        db_session.add(
            DailyGiftClaim(
                user_id=sample_user.telegram_id,
                besitos_received=5,
                claimed_at=datetime.now(UTC),
            )
        )
        db_session.commit()

        await mission_service.apply_daily_gift_mission_updates(
            sample_user.telegram_id, bot=mock_bot
        )
        await mission_service.apply_daily_gift_mission_updates(
            sample_user.telegram_id, bot=mock_bot
        )

        history = (
            db_session.query(UserRewardHistory)
            .filter(UserRewardHistory.mission_id == mission.id)
            .all()
        )
        assert len(history) == 1

    @pytest.mark.asyncio
    async def test_celebration_message_escapes_html_in_mission_name(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        """Nombre de misión con < & \" se escapa en mensaje de celebración."""
        mission_service = MissionService(db_session)
        mission = mission_service.create_mission(
            name='Mission <script> & "X"',
            description="Escape test",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        await mission_service.increment_progress_and_deliver(
            sample_user.telegram_id,
            MissionType.REACTION_COUNT,
            amount=1,
            bot=mock_bot,
            reference_id=77001,
        )
        celebration = [
            c for c in mock_bot.send_message.await_args_list if c.kwargs.get("parse_mode") == "HTML"
        ]
        assert celebration
        text = celebration[-1].kwargs.get("text", "")
        assert "<script>" not in text
        assert html.escape('Mission <script> & "X"') in text

    @pytest.mark.asyncio
    async def test_vip_mission_auto_deliver_sends_celebration(
        self, db_session, sample_user, sample_tariff, sample_vip_channel, mock_bot
    ):
        """Primera entrega VIP por misión VIP_ACTIVE: historial + mensaje Lucien."""
        from services.reward_service import RewardService

        mock_bot.get_me = AsyncMock(return_value=MagicMock(username="lucien_bot"))
        mission_service = MissionService(db_session)
        rs = RewardService(db_session)
        reward = rs.create_reward_vip("VIP Auto", "Desc", sample_tariff.id)
        mission = mission_service.create_mission(
            name="VIP Mission",
            description="Auto VIP",
            mission_type=MissionType.VIP_ACTIVE,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=reward.id,
        )

        completed = await mission_service.apply_vip_active_mission_updates(
            sample_user.telegram_id, bot=mock_bot
        )
        assert completed == 1

        history_count = (
            db_session.query(UserRewardHistory)
            .filter(UserRewardHistory.mission_id == mission.id)
            .count()
        )
        assert history_count == 1
        celebration_calls = [
            c
            for c in mock_bot.send_message.await_args_list
            if c.kwargs.get("parse_mode") == "HTML" and "VIP Mission" in c.kwargs.get("text", "")
        ]
        assert len(celebration_calls) >= 1

    @pytest.mark.asyncio
    async def test_dup_ref_guard_prevents_re_deliver_on_and_deliver_path(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        """DESIRED CONTRACT: ref guard on increment_progress_and_deliver prevents re-complete + re-deliver for same ref (no double reward). Enforce *intended contract* not just current impl. Explicit deterministic Mission+Reward+user TG."""
        mission_service = MissionService(db_session)
        mission = mission_service.create_mission(
            name="Dup Ref No Redeliver",
            description="guard + deliver",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        ref = 888002
        # first
        await mission_service.increment_progress_and_deliver(
            sample_user.telegram_id,
            MissionType.REACTION_COUNT,
            amount=1,
            bot=mock_bot,
            reference_id=ref,
        )
        bal1 = BesitoService(db=db_session).get_balance(sample_user.telegram_id)
        hist1 = (
            db_session.query(UserRewardHistory)
            .filter(UserRewardHistory.mission_id == mission.id)
            .count()
        )
        assert bal1 == sample_reward_besitos.besito_amount
        assert hist1 == 1
        # dup ref
        await mission_service.increment_progress_and_deliver(
            sample_user.telegram_id,
            MissionType.REACTION_COUNT,
            amount=1,
            bot=mock_bot,
            reference_id=ref,
        )
        bal2 = BesitoService(db=db_session).get_balance(sample_user.telegram_id)
        hist2 = (
            db_session.query(UserRewardHistory)
            .filter(UserRewardHistory.mission_id == mission.id)
            .count()
        )
        assert bal2 == bal1  # no double
        assert hist2 == 1  # no re history
        p = mission_service.get_user_progress(sample_user.telegram_id, mission.id)
        assert p.is_completed is True
        assert p.last_reference_id == ref
