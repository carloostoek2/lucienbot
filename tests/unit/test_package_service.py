"""
Tests unitarios para PackageService.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from services.package_service import PackageService
from models.models import Package, PackageFile


@pytest.mark.unit
class TestPackageService:
    """Tests para el servicio de paquetes"""

    def test_create_package_default_stocks(self, db_session):
        """Test crear paquete con stocks por defecto"""
        service = PackageService(db_session)

        package = service.create_package("Test Package", "Description")

        assert package is not None
        assert package.name == "Test Package"
        assert package.description == "Description"
        assert package.store_stock == -1
        assert package.reward_stock == -1
        assert package.is_active is True

    def test_create_package_finite_stocks(self, db_session):
        """Test crear paquete con stocks finitos"""
        service = PackageService(db_session)

        package = service.create_package(
            "Limited Package", "Desc",
            store_stock=10, reward_stock=5
        )

        assert package.store_stock == 10
        assert package.reward_stock == 5

    def test_add_file_to_package(self, db_session):
        """Test agregar archivo a un paquete"""
        service = PackageService(db_session)
        package = service.create_package("Test Package")

        file_entry = service.add_file_to_package(
            package.id, "file_id_1", "photo"
        )

        assert file_entry is not None
        assert file_entry.package_id == package.id
        assert file_entry.file_id == "file_id_1"
        assert file_entry.file_type == "photo"

    def test_get_package(self, db_session):
        """Test obtener paquete por ID"""
        service = PackageService(db_session)
        package = service.create_package("Test Package")

        result = service.get_package(package.id)

        assert result is not None
        assert result.id == package.id
        assert result.name == "Test Package"

    def test_get_available_packages_for_store_excludes_out_of_stock(self, db_session):
        """Test obtener paquetes disponibles en tienda excluye agotados"""
        service = PackageService(db_session)
        active_unlimited = service.create_package("Active Unlimited")
        active_finite = service.create_package("Active Finite", store_stock=1, reward_stock=1)
        out_of_stock = service.create_package("Out of Stock", store_stock=0, reward_stock=0)
        inactive_pkg = service.create_package("Inactive", store_stock=5, reward_stock=5)
        inactive_pkg.is_active = False
        db_session.commit()

        available = service.get_available_packages_for_store()
        available_ids = {p.id for p in available}

        assert active_unlimited.id in available_ids
        assert active_finite.id in available_ids
        assert out_of_stock.id not in available_ids
        assert inactive_pkg.id not in available_ids

    def test_get_available_packages_for_rewards_excludes_unavailable(self, db_session):
        """Test obtener paquetes para recompensas excluye no disponibles (-2)"""
        service = PackageService(db_session)
        unlimited = service.create_package("Unlimited", store_stock=-1, reward_stock=-1)
        finite = service.create_package("Finite", store_stock=5, reward_stock=3)
        unavailable = service.create_package("Unavailable", store_stock=-2, reward_stock=-2)

        available = service.get_available_packages_for_rewards()
        available_ids = {p.id for p in available}

        assert unlimited.id in available_ids
        assert finite.id in available_ids
        assert unavailable.id not in available_ids

    def test_update_package_allowed_fields(self, db_session):
        """Test actualizar campos permitidos de un paquete"""
        service = PackageService(db_session)
        package = service.create_package("Old Name", "Old Desc", store_stock=5, reward_stock=5)

        result = service.update_package(
            package.id,
            name="New Name",
            description="New Desc",
            store_stock=3,
            reward_stock=2,
            is_active=False
        )

        assert result is True
        updated = service.get_package(package.id)
        assert updated.name == "New Name"
        assert updated.description == "New Desc"
        assert updated.store_stock == 3
        assert updated.reward_stock == 2
        assert updated.is_active is False

    def test_update_package_ignores_disallowed_fields(self, db_session):
        """Test que update_package ignora campos no permitidos"""
        service = PackageService(db_session)
        package = service.create_package("Test Package", created_by=111)
        original_created_at = package.created_at
        original_created_by = package.created_by

        result = service.update_package(
            package.id,
            name="New Name",
            created_by=999,
            created_at=datetime(2020, 1, 1)
        )

        assert result is True
        updated = service.get_package(package.id)
        assert updated.name == "New Name"
        # created_by y created_at no están en allowed_fields
        assert updated.created_by == original_created_by
        assert updated.created_at == original_created_at

    def test_delete_package_sets_inactive(self, db_session):
        """Test eliminar paquete lo marca como inactivo"""
        service = PackageService(db_session)
        package = service.create_package("To Delete")

        result = service.delete_package(package.id)

        assert result is True
        updated = service.get_package(package.id)
        assert updated.is_active is False

    def test_remove_file_from_package(self, db_session):
        """Test eliminar archivo de un paquete"""
        service = PackageService(db_session)
        package = service.create_package("Test Package")
        file_entry = service.add_file_to_package(package.id, "file_id_1", "photo")

        result = service.remove_file_from_package(file_entry.id)

        assert result is True
        assert service.get_package_files(package.id) == []

    def test_decrement_store_stock_finite(self, db_session):
        """Test decrementar stock finito de tienda"""
        service = PackageService(db_session)
        package = service.create_package("Test", store_stock=3, reward_stock=3)

        result = service.decrement_store_stock(package.id)

        assert result is True
        assert service.get_package(package.id).store_stock == 2

    def test_decrement_store_stock_unlimited(self, db_session):
        """Test decrementar stock ilimitado (-1) retorna True sin cambiar valor"""
        service = PackageService(db_session)
        package = service.create_package("Test", store_stock=-1, reward_stock=-1)

        result = service.decrement_store_stock(package.id)

        assert result is True
        assert service.get_package(package.id).store_stock == -1

    def test_decrement_store_stock_unavailable(self, db_session):
        """Test decrementar stock no disponible (-2) retorna False"""
        service = PackageService(db_session)
        package = service.create_package("Test", store_stock=-2, reward_stock=-2)

        result = service.decrement_store_stock(package.id)

        assert result is False
        assert service.get_package(package.id).store_stock == -2

    def test_add_store_stock_increases_finite(self, db_session):
        """Test agregar stock a tienda incrementa valor finito"""
        service = PackageService(db_session)
        package = service.create_package("Test", store_stock=5, reward_stock=5)

        result = service.add_store_stock(package.id, 3)

        assert result is True
        assert service.get_package(package.id).store_stock == 8

    @pytest.mark.asyncio
    async def test_deliver_package_to_user_success(self, db_session, sample_user, mock_bot):
        """Test entregar paquete agrupa fotos/videos en media_group y envía resto individual"""
        from aiogram.types import InputMediaPhoto, InputMediaVideo
        service = PackageService(db_session)
        package = service.create_package("Special Package", "A gift")
        service.add_file_to_package(package.id, "file_id_1", "photo")
        service.add_file_to_package(package.id, "file_id_2", "video")
        service.add_file_to_package(package.id, "file_id_3", "animation")
        service.add_file_to_package(package.id, "file_id_4", "document", file_name="doc.pdf")

        success, msg = await service.deliver_package_to_user(
            mock_bot, sample_user.id, package.id
        )

        assert success is True
        assert "Special Package" in msg
        mock_bot.send_message.assert_called_once()
        # Fotos y videos se agrupan en media_group
        mock_bot.send_media_group.assert_called_once()
        call_args = mock_bot.send_media_group.call_args
        media = call_args.kwargs.get("media") or call_args[1].get("media")
        assert len(media) == 2
        assert isinstance(media[0], InputMediaPhoto)
        assert isinstance(media[1], InputMediaVideo)
        # Animaciones y documentos se envían individualmente
        mock_bot.send_animation.assert_called_once()
        mock_bot.send_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_deliver_package_to_user_not_found(self, db_session, sample_user, mock_bot):
        """Test entregar paquete inexistente retorna False"""
        service = PackageService(db_session)

        success, msg = await service.deliver_package_to_user(
            mock_bot, sample_user.id, 99999
        )

        assert success is False
        assert "no encontrado" in msg.lower()

    @pytest.mark.asyncio
    async def test_deliver_package_to_user_no_files(self, db_session, sample_user, mock_bot):
        """Test entregar paquete sin archivos retorna False"""
        service = PackageService(db_session)
        package = service.create_package("Empty Package")

        success, msg = await service.deliver_package_to_user(
            mock_bot, sample_user.id, package.id
        )

        assert success is False
        assert "no contiene archivos" in msg.lower()

    def test_get_package_stats(self, db_session):
        """Test obtener estadísticas de un paquete"""
        service = PackageService(db_session)
        package = service.create_package("Stats Package", "Desc", store_stock=5, reward_stock=-2)
        service.add_file_to_package(package.id, "f1", "photo")
        service.add_file_to_package(package.id, "f2", "video")

        stats = service.get_package_stats(package.id)

        assert stats['id'] == package.id
        assert stats['name'] == "Stats Package"
        assert stats['description'] == "Desc"
        assert stats['file_count'] == 2
        assert stats['store_stock'] == 5
        assert stats['reward_stock'] == -2
        assert stats['is_active'] is True
        assert stats['available_in_store'] is True
        assert stats['available_for_reward'] is False

    def test_get_package_stats_not_found(self, db_session):
        """Test estadísticas de paquete inexistente retorna dict vacío"""
        service = PackageService(db_session)

        stats = service.get_package_stats(99999)

        assert stats == {}
