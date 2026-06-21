"""
Tests unitarios para RewardService.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from datetime import UTC, datetime, timedelta

from models.models import MissionFrequency, MissionType, RewardType, UserRewardHistory
from services.besito_service import BesitoService
from services.package_service import PackageService
from services.reward_service import RewardService


@pytest.mark.unit
class TestRewardServiceCreation:
    """Tests para creación de recompensas"""

    def test_create_reward_besitos(self, db_session):
        """Test crear recompensa de tipo besitos"""
        service = RewardService(db_session)

        reward = service.create_reward_besitos("Besitos Reward", "Desc", 50)

        assert reward is not None
        assert reward.name == "Besitos Reward"
        assert reward.reward_type == RewardType.BESITOS
        assert reward.besito_amount == 50
        assert reward.is_active is True

    def test_create_reward_package(self, db_session, sample_package):
        """Test crear recompensa de tipo paquete"""
        service = RewardService(db_session)

        reward = service.create_reward_package("Package Reward", "Desc", sample_package.id)

        assert reward is not None
        assert reward.reward_type == RewardType.PACKAGE
        assert reward.package_id == sample_package.id
        assert reward.is_active is True

    def test_create_reward_vip(self, db_session, sample_tariff):
        """Test crear recompensa de tipo acceso VIP"""
        service = RewardService(db_session)

        reward = service.create_reward_vip("VIP Reward", "Desc", sample_tariff.id)

        assert reward is not None
        assert reward.reward_type == RewardType.VIP_ACCESS
        assert reward.tariff_id == sample_tariff.id
        assert reward.is_active is True


@pytest.mark.unit
class TestRewardServiceQueries:
    """Tests para consultas de recompensas"""

    def test_get_reward(self, db_session):
        """Test obtener recompensa por ID"""
        service = RewardService(db_session)
        reward = service.create_reward_besitos("Test", "Desc", 10)

        result = service.get_reward(reward.id)

        assert result is not None
        assert result.id == reward.id

    def test_get_rewards_by_type(self, db_session):
        """Test filtrar recompensas por tipo"""
        service = RewardService(db_session)
        r1 = service.create_reward_besitos("B1", "D", 10)
        r2 = service.create_reward_besitos("B2", "D", 20)
        service.create_reward_vip("V1", "D", 1)

        besitos_rewards = service.get_rewards_by_type(RewardType.BESITOS)
        besitos_ids = {r.id for r in besitos_rewards}

        assert r1.id in besitos_ids
        assert r2.id in besitos_ids
        assert len([r for r in besitos_rewards if r.reward_type != RewardType.BESITOS]) == 0

    def test_update_reward(self, db_session):
        """Test actualizar recompensa"""
        service = RewardService(db_session)
        reward = service.create_reward_besitos("Old", "Desc", 10)

        result = service.update_reward(reward.id, name="New", besito_amount=25, is_active=False)

        assert result is True
        updated = service.get_reward(reward.id)
        assert updated.name == "New"
        assert updated.besito_amount == 25
        assert updated.is_active is False

    def test_delete_reward_sets_inactive(self, db_session):
        """Test eliminar recompensa la marca inactiva"""
        service = RewardService(db_session)
        reward = service.create_reward_besitos("To Delete", "Desc", 10)

        result = service.delete_reward(reward.id)

        assert result is True
        updated = service.get_reward(reward.id)
        assert updated.is_active is False


@pytest.mark.unit
class TestRewardServiceDelivery:
    """Tests para entrega de recompensas"""

    @pytest.mark.asyncio
    async def test_deliver_reward_missing_reward(self, db_session, sample_user, mock_bot):
        """Test entregar recompensa inexistente retorna False"""
        service = RewardService(db_session)

        success, msg = await service.deliver_reward(mock_bot, sample_user.id, 99999)

        assert success is False
        assert "no encontrada" in msg.lower()

    @pytest.mark.asyncio
    async def test_deliver_reward_inactive_reward(self, db_session, sample_user, mock_bot):
        """Test entregar recompensa inactiva retorna False"""
        service = RewardService(db_session)
        reward = service.create_reward_besitos("Inactive", "Desc", 10)
        reward.is_active = False
        db_session.commit()

        success, msg = await service.deliver_reward(mock_bot, sample_user.id, reward.id)

        assert success is False
        assert "inactiva" in msg.lower()

    @pytest.mark.asyncio
    async def test_deliver_reward_besitos(self, db_session, sample_user, mock_bot):
        """Test entregar recompensa de besitos acredita saldo"""
        service = RewardService(db_session)
        reward = service.create_reward_besitos("Besitos", "Desc", 50)

        success, msg = await service.deliver_reward(mock_bot, sample_user.id, reward.id)

        assert success is True
        assert "50" in msg
        balance = BesitoService(db=db_session).get_balance(
            sample_user.id
        )  # 1-line fix post held removal (F4); was service.besito_service
        assert balance == 50

    @pytest.mark.asyncio
    async def test_deliver_reward_package(self, db_session, sample_user, sample_package, mock_bot):
        """Test entregar recompensa de paquete decrementa stock y envía media_group"""
        from aiogram.types import InputMediaPhoto

        pkg_service = PackageService(db_session)
        pkg_service.add_file_to_package(sample_package.id, "file1", "photo")
        sample_package.reward_stock = 1
        db_session.commit()

        service = RewardService(db_session)
        reward = service.create_reward_package("Pkg Reward", "Desc", sample_package.id)

        success, msg = await service.deliver_reward(mock_bot, sample_user.id, reward.id)

        assert success is True
        mock_bot.send_message.assert_called_once()
        # Fotos se envían como media_group
        mock_bot.send_media_group.assert_called_once()
        call_args = mock_bot.send_media_group.call_args
        media = call_args.kwargs.get("media") or call_args[1].get("media")
        assert len(media) == 1
        assert isinstance(media[0], InputMediaPhoto)

        # Verificar que el stock de recompensas se decrementó via model method
        refreshed_pkg = pkg_service.get_package(sample_package.id)
        assert refreshed_pkg.reward_stock == 0

    @pytest.mark.asyncio
    async def test_deliver_reward_package_out_of_stock(
        self, db_session, sample_user, sample_package, mock_bot
    ):
        """Test entregar paquete sin stock retorna False"""
        sample_package.reward_stock = 0
        db_session.commit()

        service = RewardService(db_session)
        reward = service.create_reward_package("Pkg Reward", "Desc", sample_package.id)

        success, msg = await service.deliver_reward(mock_bot, sample_user.id, reward.id)

        assert success is False
        assert "agotado" in msg.lower() or "no disponible" in msg.lower()

    @pytest.mark.asyncio
    async def test_deliver_reward_package_rollback_on_telegram_failure(
        self, db_session, sample_user, sample_package, mock_bot
    ):
        """Fallo en Telegram revierte stock decrementado."""
        from services.package_service import PackageService

        pkg_service = PackageService(db_session)
        pkg_service.add_file_to_package(sample_package.id, "file1", "photo")
        sample_package.reward_stock = 1
        db_session.commit()
        package_id = sample_package.id

        service = RewardService(db_session)
        reward = service.create_reward_package("Pkg Rollback", "Desc", package_id)
        db_session.commit()
        mock_bot.send_message = AsyncMock(side_effect=RuntimeError("telegram down"))

        success, _msg = await service.deliver_reward(mock_bot, sample_user.id, reward.id)

        assert success is False
        from models.models import Package

        db_session.expire_all()
        refreshed = db_session.query(Package).filter(Package.id == package_id).first()
        assert refreshed is not None
        assert refreshed.reward_stock == 1

    @pytest.mark.asyncio
    async def test_deliver_reward_vip_reuses_token_on_retry(
        self, db_session, sample_user, sample_tariff, sample_vip_channel, mock_bot
    ):
        """Retry tras fallo de send reutiliza token y no duplica grant."""
        from services.mission_service import MissionService
        from services.vip_service import VIPService

        service = RewardService(db_session)
        reward = service.create_reward_vip("VIP Retry", "Desc", sample_tariff.id)
        ms = MissionService(db_session)
        mission = ms.create_mission(
            name="VIP Mission",
            description="Retry",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=reward.id,
        )
        progress = ms.set_progress(sample_user.id, mission.id, 1)
        service.try_claim_mission_delivery(
            sample_user.id,
            mission.id,
            reward.id,
            since_completed_at=progress.completed_at,
            frequency=MissionFrequency.ONE_TIME,
        )
        mock_bot.get_me = AsyncMock(return_value=MagicMock(username="lucien_bot"))
        mock_bot.send_message = AsyncMock(side_effect=[RuntimeError("send fail"), None])
        vip_svc = VIPService(db_session)

        with patch.object(
            vip_svc, "grant_vip_from_tariff", wraps=vip_svc.grant_vip_from_tariff
        ) as grant_spy, patch.object(
            vip_svc, "resend_vip_invite_for_user", wraps=vip_svc.resend_vip_invite_for_user
        ) as resend_spy:
            service.vip_service = vip_svc
            ok1, _ = await service.deliver_reward(
                mock_bot,
                sample_user.id,
                reward.id,
                mission_id=mission.id,
                history_claimed=True,
            )
            assert ok1 is False
            claim_after_fail = service._get_mission_delivery_claim(
                sample_user.id, mission.id, reward.id
            )
            assert claim_after_fail.details.startswith("token:")
            ok2, _ = await service.deliver_reward(
                mock_bot,
                sample_user.id,
                reward.id,
                mission_id=mission.id,
                history_claimed=True,
            )

        assert ok2 is True
        assert mock_bot.send_message.await_count == 2
        grant_spy.assert_awaited_once()
        resend_spy.assert_awaited_once()
        claim_final = service._get_mission_delivery_claim(
            sample_user.id, mission.id, reward.id
        )
        assert claim_final.details is None

    @pytest.mark.asyncio
    async def test_deliver_reward_vip_mission_fresh_claim_extends_already_vip(
        self, db_session, sample_user, sample_tariff, sample_vip_channel, mock_bot
    ):
        """__delivery_claim__ fresco + ya VIP debe grant (extender), no resend."""
        from services.mission_service import MissionService
        from services.vip_service import VIPService

        service = RewardService(db_session)
        reward = service.create_reward_vip("VIP Mission Extend", "Desc", sample_tariff.id)
        ms = MissionService(db_session)
        mission = ms.create_mission(
            name="VIP Extend Mission",
            description="Fresh claim extend",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=reward.id,
        )
        progress = ms.set_progress(sample_user.id, mission.id, 1)
        service.try_claim_mission_delivery(
            sample_user.id,
            mission.id,
            reward.id,
            since_completed_at=progress.completed_at,
            frequency=MissionFrequency.ONE_TIME,
        )
        vip_svc = VIPService(db_session)
        token = vip_svc.generate_token(sample_tariff.id)
        vip_svc.redeem_token(token.token_code, sample_user.id)
        sub_before = vip_svc.get_user_subscription(sample_user.id)
        end_before = sub_before.end_date

        mock_bot.get_me = AsyncMock(return_value=MagicMock(username="lucien_bot"))
        with patch.object(
            vip_svc, "resend_vip_invite_for_user", new_callable=AsyncMock
        ) as resend_mock:
            service.vip_service = vip_svc
            ok, _ = await service.deliver_reward(
                mock_bot,
                sample_user.id,
                reward.id,
                mission_id=mission.id,
                history_claimed=True,
            )

        assert ok is True
        resend_mock.assert_not_awaited()
        sub_after = vip_svc.get_user_subscription(sample_user.id)
        assert sub_after.end_date > end_before

    @pytest.mark.asyncio
    async def test_deliver_reward_vip_token_prefix_resend_only(
        self, db_session, sample_user, sample_tariff, sample_vip_channel, mock_bot
    ):
        """Claim token: + VIP activo reenvía invite sin nuevo grant."""
        from services.mission_service import MissionService
        from services.vip_service import VIPService

        service = RewardService(db_session)
        reward = service.create_reward_vip("VIP Token Retry", "Desc", sample_tariff.id)
        ms = MissionService(db_session)
        mission = ms.create_mission(
            name="VIP Token Mission",
            description="Resend only",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=reward.id,
        )
        progress = ms.set_progress(sample_user.id, mission.id, 1)
        service.try_claim_mission_delivery(
            sample_user.id,
            mission.id,
            reward.id,
            since_completed_at=progress.completed_at,
            frequency=MissionFrequency.ONE_TIME,
        )
        vip_svc = VIPService(db_session)
        token = vip_svc.generate_token(sample_tariff.id)
        vip_svc.redeem_token(token.token_code, sample_user.id)
        claim = service._get_mission_delivery_claim(sample_user.id, mission.id, reward.id)
        claim.details = f"token:{token.id}"
        db_session.commit()

        mock_bot.get_me = AsyncMock(return_value=MagicMock(username="lucien_bot"))
        with patch.object(
            vip_svc, "grant_vip_from_tariff", new_callable=AsyncMock
        ) as grant_mock, patch.object(
            vip_svc, "resend_vip_invite_for_user", wraps=vip_svc.resend_vip_invite_for_user
        ) as resend_spy:
            service.vip_service = vip_svc
            ok, _ = await service.deliver_reward(
                mock_bot,
                sample_user.id,
                reward.id,
                mission_id=mission.id,
                history_claimed=True,
            )

        assert ok is True
        grant_mock.assert_not_awaited()
        resend_spy.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deliver_reward_vip_invite_failure_retry_resends_not_regrants(
        self, db_session, sample_user, sample_tariff, sample_vip_channel, mock_bot
    ):
        """Partial metadata (invite fallido) marca token:; retry resend sin segundo grant."""
        from services.mission_service import MissionService
        from services.vip_service import VIPService

        service = RewardService(db_session)
        reward = service.create_reward_vip("VIP Invite Fail", "Desc", sample_tariff.id)
        ms = MissionService(db_session)
        mission = ms.create_mission(
            name="VIP Invite Fail Mission",
            description="Partial then retry",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=reward.id,
        )
        progress = ms.set_progress(sample_user.id, mission.id, 1)
        service.try_claim_mission_delivery(
            sample_user.id,
            mission.id,
            reward.id,
            since_completed_at=progress.completed_at,
            frequency=MissionFrequency.ONE_TIME,
        )
        vip_svc = VIPService(db_session)
        mock_bot.get_me = AsyncMock(return_value=MagicMock(username="lucien_bot"))
        mock_bot.create_chat_invite_link = AsyncMock(side_effect=Exception("TG fail"))

        with patch.object(
            vip_svc, "grant_vip_from_tariff", wraps=vip_svc.grant_vip_from_tariff
        ) as grant_spy, patch.object(
            vip_svc, "resend_vip_invite_for_user", wraps=vip_svc.resend_vip_invite_for_user
        ) as resend_spy:
            service.vip_service = vip_svc
            ok1, _ = await service.deliver_reward(
                mock_bot,
                sample_user.id,
                reward.id,
                mission_id=mission.id,
                history_claimed=True,
            )
            assert ok1 is False
            claim_after_fail = service._get_mission_delivery_claim(
                sample_user.id, mission.id, reward.id
            )
            assert claim_after_fail.details.startswith("token:")
            mock_bot.create_chat_invite_link = AsyncMock(
                return_value=MagicMock(invite_link="https://t.me/+retry")
            )
            ok2, _ = await service.deliver_reward(
                mock_bot,
                sample_user.id,
                reward.id,
                mission_id=mission.id,
                history_claimed=True,
            )

        assert ok2 is True
        grant_spy.assert_awaited_once()
        resend_spy.assert_awaited_once()
        claim_final = service._get_mission_delivery_claim(
            sample_user.id, mission.id, reward.id
        )
        assert claim_final.details is None

    @pytest.mark.asyncio
    async def test_deliver_besitos_no_double_credit_on_retry(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        """Besitos ya acreditados: retry no duplica transacción MISSION."""
        from models.models import BesitoTransaction, TransactionSource
        from services.mission_service import MissionService

        service = RewardService(db_session)
        ms = MissionService(db_session)
        mission = ms.create_mission(
            name="Besitos Retry",
            description="No double",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=sample_reward_besitos.id,
        )
        progress = ms.set_progress(sample_user.id, mission.id, 1)
        service.try_claim_mission_delivery(
            sample_user.id,
            mission.id,
            sample_reward_besitos.id,
            since_completed_at=progress.completed_at,
            frequency=MissionFrequency.ONE_TIME,
        )
        await service.deliver_reward(
            mock_bot,
            sample_user.id,
            sample_reward_besitos.id,
            mission_id=mission.id,
            history_claimed=True,
        )
        service.release_mission_delivery_claim(
            sample_user.id, mission.id, sample_reward_besitos.id
        )
        await service.deliver_reward(
            mock_bot,
            sample_user.id,
            sample_reward_besitos.id,
            mission_id=mission.id,
            history_claimed=True,
        )
        claim = service._get_mission_delivery_claim(
            sample_user.id, mission.id, sample_reward_besitos.id
        )
        tx_count = (
            db_session.query(BesitoTransaction)
            .filter(
                BesitoTransaction.user_id == sample_user.id,
                BesitoTransaction.source == TransactionSource.MISSION,
                BesitoTransaction.reference_id == claim.id,
            )
            .count()
        )
        assert tx_count == 1

    @pytest.mark.asyncio
    async def test_deliver_reward_vip_skips_resend_when_sent_prefix(
        self, db_session, sample_user, sample_tariff, sample_vip_channel, mock_bot
    ):
        """Retry con sent:vip_activated y VIP activo no reenvía mensaje."""
        from services.mission_service import MissionService
        from services.vip_service import VIPService

        service = RewardService(db_session)
        reward = service.create_reward_vip("VIP Sent", "Desc", sample_tariff.id)
        ms = MissionService(db_session)
        mission = ms.create_mission(
            name="VIP Sent Mission",
            description="No resend",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=reward.id,
        )
        progress = ms.set_progress(sample_user.id, mission.id, 1)
        service.try_claim_mission_delivery(
            sample_user.id,
            mission.id,
            reward.id,
            since_completed_at=progress.completed_at,
            frequency=MissionFrequency.ONE_TIME,
        )
        vip_svc = VIPService(db_session)
        token = vip_svc.generate_token(sample_tariff.id)
        vip_svc.redeem_token(token.token_code, sample_user.id)
        claim = service._get_mission_delivery_claim(sample_user.id, mission.id, reward.id)
        claim.details = f"sent:vip_activated:{token.id}"
        db_session.commit()

        mock_bot.get_me = AsyncMock(return_value=MagicMock(username="lucien_bot"))
        ok, _ = await service.deliver_reward(
            mock_bot, sample_user.id, reward.id, mission_id=mission.id, history_claimed=True
        )

        assert ok is True
        mock_bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_recurring_second_cycle_credits_besitos_again(
        self, db_session, sample_user, sample_reward_besitos, mock_bot
    ):
        """RECURRING segundo ciclo acredita besitos aunque el primero ya tuvo crédito MISSION."""
        from models.models import BesitoTransaction, TransactionSource
        from services.mission_service import MissionService

        service = RewardService(db_session)
        ms = MissionService(db_session)
        mission = ms.create_mission(
            name="Recurring Besitos",
            description="Second cycle credit",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.RECURRING,
            reward_id=sample_reward_besitos.id,
        )
        old_cycle = datetime(2026, 1, 1, tzinfo=UTC)
        new_cycle = datetime(2026, 6, 1, tzinfo=UTC)

        progress1 = ms.set_progress(sample_user.id, mission.id, 1)
        progress1.completed_at = old_cycle
        db_session.commit()
        service.try_claim_mission_delivery(
            sample_user.id,
            mission.id,
            sample_reward_besitos.id,
            since_completed_at=old_cycle,
            frequency=MissionFrequency.RECURRING,
        )
        await service.deliver_reward(
            mock_bot,
            sample_user.id,
            sample_reward_besitos.id,
            mission_id=mission.id,
            history_claimed=True,
            since_completed_at=old_cycle,
            frequency=MissionFrequency.RECURRING,
        )
        first_history = service._get_mission_delivery_claim(
            sample_user.id, mission.id, sample_reward_besitos.id
        )
        first_history.delivered_at = old_cycle
        db_session.commit()

        progress2 = ms.set_progress(sample_user.id, mission.id, 1)
        progress2.completed_at = new_cycle
        db_session.commit()
        service.try_claim_mission_delivery(
            sample_user.id,
            mission.id,
            sample_reward_besitos.id,
            since_completed_at=new_cycle,
            frequency=MissionFrequency.RECURRING,
        )
        ok, _ = await service.deliver_reward(
            mock_bot,
            sample_user.id,
            sample_reward_besitos.id,
            mission_id=mission.id,
            history_claimed=True,
            since_completed_at=new_cycle,
            frequency=MissionFrequency.RECURRING,
        )

        assert ok is True
        tx_count = (
            db_session.query(BesitoTransaction)
            .filter(
                BesitoTransaction.user_id == sample_user.id,
                BesitoTransaction.source == TransactionSource.MISSION,
            )
            .count()
        )
        assert tx_count == 2
        ref_ids = {
            tx.reference_id
            for tx in db_session.query(BesitoTransaction).filter(
                BesitoTransaction.user_id == sample_user.id,
                BesitoTransaction.source == TransactionSource.MISSION,
            )
        }
        assert len(ref_ids) == 2
        balance = BesitoService(db=db_session).get_balance(sample_user.id)
        assert balance == sample_reward_besitos.besito_amount * 2

    @pytest.mark.asyncio
    async def test_deliver_reward_vip_access(
        self, db_session, sample_user, sample_tariff, sample_vip_channel, mock_bot
    ):
        """Test entregar recompensa VIP activa membresía y envía acceso directo"""
        service = RewardService(db_session)
        reward = service.create_reward_vip("VIP Reward", "Desc", sample_tariff.id)
        mock_bot.get_me = AsyncMock(return_value=MagicMock(username="lucien_bot"))

        success, msg = await service.deliver_reward(mock_bot, sample_user.id, reward.id)

        assert success is True
        assert "VIP" in msg
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert "El Diván" in call_args.kwargs["text"] or "círculo íntimo" in call_args.kwargs["text"]
        assert call_args.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_deliver_reward_vip_extends_existing_subscription(
        self, db_session, sample_user, sample_tariff, sample_vip_channel, mock_bot
    ):
        """Misión VIP extiende suscripción existente vía grant_vip_from_tariff."""
        from services.vip_service import VIPService

        vip_svc = VIPService(db_session)
        token = vip_svc.generate_token(sample_tariff.id)
        vip_svc.redeem_token(token.token_code, sample_user.id)
        sub_before = vip_svc.get_user_subscription(sample_user.id)
        end_before = sub_before.end_date

        service = RewardService(db_session)
        reward = service.create_reward_vip("VIP Extend", "Desc", sample_tariff.id)
        ok, _ = await service.deliver_reward(mock_bot, sample_user.id, reward.id)

        assert ok is True
        sub_after = vip_svc.get_user_subscription(sample_user.id)
        assert sub_after.end_date > end_before


@pytest.mark.unit
class TestRewardServiceHistory:
    """Tests para historial y estadísticas"""

    def test_try_claim_mission_delivery_blocks_fresh_concurrent_claim(
        self, db_session, sample_user
    ):
        """Claim __delivery_claim__ fresco (<60s) bloquea invocación concurrente."""
        service = RewardService(db_session)
        reward = service.create_reward_besitos("Claim Test", "Desc", 10)
        from services.mission_service import MissionService

        ms = MissionService(db_session)
        mission = ms.create_mission(
            name="Claim Mission",
            description="Atomic claim",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=reward.id,
        )
        progress = ms.set_progress(sample_user.id, mission.id, 1)

        first = service.try_claim_mission_delivery(
            sample_user.id,
            mission.id,
            reward.id,
            since_completed_at=progress.completed_at,
            frequency=MissionFrequency.ONE_TIME,
        )
        concurrent = service.try_claim_mission_delivery(
            sample_user.id,
            mission.id,
            reward.id,
            since_completed_at=progress.completed_at,
            frequency=MissionFrequency.ONE_TIME,
        )
        service._finalize_delivery_claim(sample_user.id, mission.id, reward.id)
        blocked = service.try_claim_mission_delivery(
            sample_user.id,
            mission.id,
            reward.id,
            since_completed_at=progress.completed_at,
            frequency=MissionFrequency.ONE_TIME,
        )
        assert first is True
        assert concurrent is False
        assert blocked is False

    def test_try_claim_mission_delivery_resumes_stale_claim(self, db_session, sample_user):
        """Claim __delivery_claim__ stale (>=60s) es resumible."""
        from services.reward_service import _DELIVERY_CLAIM_TTL_SECONDS

        service = RewardService(db_session)
        reward = service.create_reward_besitos("Stale Claim", "Desc", 10)
        from services.mission_service import MissionService

        ms = MissionService(db_session)
        mission = ms.create_mission(
            name="Stale Mission",
            description="Resume stale",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=reward.id,
        )
        progress = ms.set_progress(sample_user.id, mission.id, 1)
        assert service.try_claim_mission_delivery(
            sample_user.id,
            mission.id,
            reward.id,
            since_completed_at=progress.completed_at,
            frequency=MissionFrequency.ONE_TIME,
        )
        claim = service._get_mission_delivery_claim(
            sample_user.id, mission.id, reward.id
        )
        claim.delivered_at = datetime.now(UTC) - timedelta(
            seconds=_DELIVERY_CLAIM_TTL_SECONDS + 5
        )
        db_session.commit()

        resumed = service.try_claim_mission_delivery(
            sample_user.id,
            mission.id,
            reward.id,
            since_completed_at=progress.completed_at,
            frequency=MissionFrequency.ONE_TIME,
        )
        assert resumed is True

    def test_try_claim_recurring_second_cycle_allows_new_claim(self, db_session, sample_user):
        """RECURRING: fila finalizada no bloquea nuevo claim en ciclo siguiente."""
        service = RewardService(db_session)
        reward = service.create_reward_besitos("Recurring", "Desc", 10)
        from services.mission_service import MissionService

        ms = MissionService(db_session)
        mission = ms.create_mission(
            name="Recurring Mission",
            description="Second cycle",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.RECURRING,
            reward_id=reward.id,
        )
        old_cycle = datetime(2026, 1, 1, tzinfo=UTC)
        new_cycle = datetime(2026, 6, 1, tzinfo=UTC)
        service.log_reward_delivery(sample_user.id, reward.id, mission.id)
        history = db_session.query(UserRewardHistory).first()
        history.delivered_at = old_cycle
        db_session.commit()

        progress = ms.set_progress(sample_user.id, mission.id, 1)
        progress.completed_at = new_cycle
        db_session.commit()

        claimed = service.try_claim_mission_delivery(
            sample_user.id,
            mission.id,
            reward.id,
            since_completed_at=new_cycle,
            frequency=MissionFrequency.RECURRING,
        )
        assert claimed is True

    def test_has_mission_reward_been_delivered_one_time(self, db_session, sample_user):
        """ONE_TIME: cualquier historial implica entregada."""
        service = RewardService(db_session)
        reward = service.create_reward_besitos("Test", "Desc", 10)
        assert service.has_mission_reward_been_delivered(sample_user.id, mission_id=5) is False
        service.log_reward_delivery(sample_user.id, reward.id, mission_id=5)
        assert service.has_mission_reward_been_delivered(sample_user.id, mission_id=5) is True

    def test_has_mission_reward_been_delivered_recurring_cycle(self, db_session, sample_user):
        """RECURRING: solo cuenta entregas del ciclo actual (completed_at)."""
        service = RewardService(db_session)
        reward = service.create_reward_besitos("Test", "Desc", 10)
        old_cycle = datetime(2026, 1, 1, tzinfo=UTC)
        new_cycle = datetime(2026, 6, 1, tzinfo=UTC)
        service.log_reward_delivery(sample_user.id, reward.id, mission_id=7)
        history = db_session.query(UserRewardHistory).first()
        history.delivered_at = old_cycle
        db_session.commit()

        assert (
            service.has_mission_reward_been_delivered(
                sample_user.id,
                7,
                since_completed_at=new_cycle,
                frequency=MissionFrequency.RECURRING,
            )
            is False
        )
        service.log_reward_delivery(sample_user.id, reward.id, mission_id=7)
        assert (
            service.has_mission_reward_been_delivered(
                sample_user.id,
                7,
                since_completed_at=new_cycle,
                frequency=MissionFrequency.RECURRING,
            )
            is True
        )

    def test_log_reward_delivery(self, db_session, sample_user):
        """Test registrar entrega de recompensa en historial"""
        service = RewardService(db_session)
        reward = service.create_reward_besitos("Test", "Desc", 10)

        service.log_reward_delivery(sample_user.id, reward.id, mission_id=1, details="test details")

        history = db_session.query(UserRewardHistory).all()
        assert len(history) == 1
        assert history[0].user_id == sample_user.id
        assert history[0].reward_id == reward.id
        assert history[0].mission_id == 1
        assert history[0].details == "test details"

    def test_get_reward_stats(self, db_session, sample_user):
        """Test obtener estadísticas de recompensa"""
        service = RewardService(db_session)
        reward = service.create_reward_besitos("Test", "Desc", 10)
        service.log_reward_delivery(sample_user.id, reward.id)
        service.log_reward_delivery(sample_user.id, reward.id)

        stats = service.get_reward_stats(reward.id)

        assert stats["reward_name"] == "Test"
        assert stats["type"] == "besitos"
        assert stats["total_deliveries"] == 2

    def test_get_reward_stats_not_found(self, db_session):
        """Test estadísticas de recompensa inexistente retorna dict vacío"""
        service = RewardService(db_session)

        stats = service.get_reward_stats(99999)

        assert stats == {}

    def test_get_user_reward_history(self, db_session, sample_user):
        """Test obtener historial de recompensas de un usuario"""
        service = RewardService(db_session)
        r1 = service.create_reward_besitos("R1", "D", 10)
        r2 = service.create_reward_besitos("R2", "D", 20)
        service.log_reward_delivery(sample_user.id, r1.id)
        service.log_reward_delivery(sample_user.id, r2.id)

        history = service.get_user_reward_history(sample_user.id)

        assert len(history) == 2
        reward_ids = {h.reward_id for h in history}
        assert r1.id in reward_ids
        assert r2.id in reward_ids
