"""
Tests unitarios para RewardService.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from services.reward_service import RewardService
from services.package_service import PackageService
from models.models import Reward, RewardType, UserRewardHistory


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
        balance = service.besito_service.get_balance(sample_user.id)
        assert balance == 50

    @pytest.mark.asyncio
    async def test_deliver_reward_package(self, db_session, sample_user, sample_package, mock_bot):
        """Test entregar recompensa de paquete decrementa stock y envía archivos"""
        pkg_service = PackageService(db_session)
        pkg_service.add_file_to_package(sample_package.id, "file1", "photo")
        sample_package.reward_stock = 1
        db_session.commit()

        service = RewardService(db_session)
        reward = service.create_reward_package("Pkg Reward", "Desc", sample_package.id)

        success, msg = await service.deliver_reward(mock_bot, sample_user.id, reward.id)

        assert success is True
        mock_bot.send_message.assert_called_once()
        mock_bot.send_photo.assert_called_once()

        # Verificar que el stock de recompensas se decrementó via model method
        refreshed_pkg = pkg_service.get_package(sample_package.id)
        assert refreshed_pkg.reward_stock == 0

    @pytest.mark.asyncio
    async def test_deliver_reward_package_out_of_stock(self, db_session, sample_user, sample_package, mock_bot):
        """Test entregar paquete sin stock retorna False"""
        sample_package.reward_stock = 0
        db_session.commit()

        service = RewardService(db_session)
        reward = service.create_reward_package("Pkg Reward", "Desc", sample_package.id)

        success, msg = await service.deliver_reward(mock_bot, sample_user.id, reward.id)

        assert success is False
        assert "agotado" in msg.lower() or "no disponible" in msg.lower()

    @pytest.mark.asyncio
    async def test_deliver_reward_vip_access(self, db_session, sample_user, sample_tariff, mock_bot):
        """Test entregar recompensa VIP genera token y envía mensaje con URL"""
        service = RewardService(db_session)
        reward = service.create_reward_vip("VIP Reward", "Desc", sample_tariff.id)
        mock_bot.get_me = AsyncMock(return_value=MagicMock(username="lucien_bot"))

        success, msg = await service.deliver_reward(mock_bot, sample_user.id, reward.id)

        assert success is True
        assert "VIP" in msg
        mock_bot.send_message.assert_called_once()
        # Verificar que el mensaje incluye el enlace con el token
        call_args = mock_bot.send_message.call_args
        assert "https://t.me/lucien_bot?start=" in call_args.kwargs["text"]


@pytest.mark.unit
class TestRewardServiceHistory:
    """Tests para historial y estadísticas"""

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

        assert stats['reward_name'] == "Test"
        assert stats['type'] == "besitos"
        assert stats['total_deliveries'] == 2

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
