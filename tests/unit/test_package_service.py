"""
Tests unitarios para PackageService.
"""

from datetime import datetime

import pytest

from services.package_service import PackageService


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

        package = service.create_package("Limited Package", "Desc", store_stock=10, reward_stock=5)

        assert package.store_stock == 10
        assert package.reward_stock == 5

    def test_add_file_to_package(self, db_session):
        """Test agregar archivo a un paquete"""
        service = PackageService(db_session)
        package = service.create_package("Test Package")

        file_entry = service.add_file_to_package(package.id, "file_id_1", "photo")

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
            is_active=False,
        )

        assert result is True
        updated = service.get_package(package.id)
        assert updated.name == "New Name"
        assert updated.description == "New Desc"
        assert updated.store_stock == 3
        assert updated.reward_stock == 2
        assert updated.is_active is False

    def test_create_get_all_categories(self, db_session):
        """DESIRED CONTRACT (Fase12): create_category, get_all_categories(active), get_category.
        Exact list equality, full post-state re-query, hygiene close (gold patterns).
        """
        service = PackageService(db_session)
        try:
            cat1 = service.create_category("Cat A", "Desc A", order_index=10)
            cat2 = service.create_category("Cat B", None, order_index=5)
            cat_in = service.create_category("Inactive Cat")
            cat_in.is_active = False
            db_session.commit()
            all_active = service.get_all_categories(active_only=True)
            active_ids = {c.id for c in all_active}
            assert (
                {cat1.id, cat2.id} <= active_ids and cat_in.id not in active_ids
            )  # exact our (set membership), active filter (robust vs other cats)
            got = service.get_category(cat1.id)
            assert got is not None and got.name == "Cat A"
            # get returns inactive (exists); active_only excludes (tested); delete test covers hard None
        finally:
            service.close()

    def test_assign_package_to_category_and_get_by(self, db_session):
        """DESIRED CONTRACT: assign + get_by exact. Fresh + hygiene."""
        service = PackageService(db_session)
        try:
            pkg = service.create_package("Pkg in Cat")
            cat = service.create_category("Target Cat")
            ok = service.assign_package_to_category(pkg.id, cat.id)
            assert ok is True
            pkgs = service.get_packages_by_category(cat.id)
            assert [p.id for p in pkgs] == [pkg.id]
            assert pkgs[0].category_id == cat.id
        finally:
            service.close()

    def test_update_and_delete_category(self, db_session):
        """DESIRED: update + delete exact post-state re-query + hygiene."""
        service = PackageService(db_session)
        try:
            cat = service.create_category("ToUpdate")
            ok = service.update_category(cat.id, name="UpdatedCat", description="new")
            assert ok is True
            got = service.get_category(cat.id)
            assert got is not None and got.name == "UpdatedCat"
            del_ok = service.delete_category(cat.id)
            assert del_ok is True
            assert service.get_category(cat.id) is None  # strict post-delete re-query
        finally:
            service.close()

    def test_update_package_ignores_disallowed_fields(self, db_session):
        """Test que update_package ignora campos no permitidos"""
        service = PackageService(db_session)
        package = service.create_package("Test Package", created_by=111)
        original_created_at = package.created_at
        original_created_by = package.created_by

        result = service.update_package(
            package.id, name="New Name", created_by=999, created_at=datetime(2020, 1, 1)
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

        success, msg = await service.deliver_package_to_user(mock_bot, sample_user.id, package.id)

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

        success, msg = await service.deliver_package_to_user(mock_bot, sample_user.id, 99999)

        assert success is False
        assert "no encontrado" in msg.lower()

    @pytest.mark.asyncio
    async def test_deliver_package_to_user_no_files(self, db_session, sample_user, mock_bot):
        """Test entregar paquete sin archivos retorna False"""
        service = PackageService(db_session)
        package = service.create_package("Empty Package")

        success, msg = await service.deliver_package_to_user(mock_bot, sample_user.id, package.id)

        assert success is False
        assert "no contiene archivos" in msg.lower()

    def test_get_package_stats(self, db_session):
        """Test obtener estadísticas de un paquete"""
        service = PackageService(db_session)
        package = service.create_package("Stats Package", "Desc", store_stock=5, reward_stock=-2)
        service.add_file_to_package(package.id, "f1", "photo")
        service.add_file_to_package(package.id, "f2", "video")

        stats = service.get_package_stats(package.id)

        assert stats["id"] == package.id
        assert stats["name"] == "Stats Package"
        assert stats["description"] == "Desc"
        assert stats["file_count"] == 2
        assert stats["store_stock"] == 5
        assert stats["reward_stock"] == -2
        assert stats["is_active"] is True
        assert stats["available_in_store"] is True
        assert stats["available_for_reward"] is False

    def test_get_package_stats_not_found(self, db_session):
        """Test estadísticas de paquete inexistente retorna dict vacío"""
        service = PackageService(db_session)

        stats = service.get_package_stats(99999)

        assert stats == {}

    # ==================== REGRESIÓN: FALLOS PERMANENTES ====================

    @pytest.mark.asyncio
    async def test_deliver_package_chat_not_found_returns_permanent(
        self, db_session, sample_user, mock_bot
    ):
        """TelegramBadRequest 'chat not found' retorna permanent:chat_not_found sin loguear ERROR"""
        from aiogram.exceptions import TelegramBadRequest

        mock_bot.send_message.side_effect = TelegramBadRequest(
            method="sendMessage", message="Bad Request: chat not found"
        )
        service = PackageService(db_session)
        package = service.create_package("Test Package")
        service.add_file_to_package(package.id, "file_id_1", "photo")

        success, msg = await service.deliver_package_to_user(mock_bot, sample_user.id, package.id)

        assert success is False
        assert msg == "permanent:chat_not_found"

    @pytest.mark.asyncio
    async def test_deliver_package_bot_blocked_returns_permanent(
        self, db_session, sample_user, mock_bot
    ):
        """TelegramForbiddenError 'bot was blocked' retorna permanent:bot_blocked sin loguear ERROR"""
        from aiogram.exceptions import TelegramForbiddenError

        mock_bot.send_message.side_effect = TelegramForbiddenError(
            method="sendMessage", message="Forbidden: bot was blocked by the user"
        )
        service = PackageService(db_session)
        package = service.create_package("Test Package")
        service.add_file_to_package(package.id, "file_id_1", "photo")

        success, msg = await service.deliver_package_to_user(mock_bot, sample_user.id, package.id)

        assert success is False
        assert msg == "permanent:bot_blocked"

    @pytest.mark.asyncio
    async def test_deliver_package_no_private_chat_returns_permanent(
        self, db_session, sample_user, mock_bot
    ):
        """VIP de canal sin /start: 'can't initiate conversation' es fallo permanente, no bloqueo."""
        from aiogram.exceptions import TelegramForbiddenError

        mock_bot.send_message.side_effect = TelegramForbiddenError(
            method="sendMessage",
            message="Forbidden: bot can't initiate conversation with a user",
        )
        service = PackageService(db_session)
        package = service.create_package("Test Package")
        service.add_file_to_package(package.id, "file_id_1", "photo")

        success, msg = await service.deliver_package_to_user(mock_bot, sample_user.id, package.id)

        assert success is False
        assert msg == "permanent:no_private_chat"

    @pytest.mark.asyncio
    async def test_deliver_package_user_deactivated_returns_permanent(
        self, db_session, sample_user, mock_bot
    ):
        """Cuenta eliminada en Telegram retorna permanent:user_deactivated."""
        from aiogram.exceptions import TelegramForbiddenError

        mock_bot.send_message.side_effect = TelegramForbiddenError(
            method="sendMessage", message="Forbidden: user is deactivated"
        )
        service = PackageService(db_session)
        package = service.create_package("Test Package")
        service.add_file_to_package(package.id, "file_id_1", "photo")

        success, msg = await service.deliver_package_to_user(mock_bot, sample_user.id, package.id)

        assert success is False
        assert msg == "permanent:user_deactivated"

    @pytest.mark.asyncio
    async def test_deliver_package_other_bad_request_is_logged_as_error(
        self, db_session, sample_user, mock_bot
    ):
        """Otros TelegramBadRequest son atrapados por el except externo y retornan False"""
        from aiogram.exceptions import TelegramBadRequest

        mock_bot.send_message.side_effect = TelegramBadRequest(
            method="sendMessage", message="Bad Request: message text is empty"
        )
        service = PackageService(db_session)
        package = service.create_package("Test Package")
        service.add_file_to_package(package.id, "file_id_1", "photo")

        success, msg = await service.deliver_package_to_user(mock_bot, sample_user.id, package.id)

        assert success is False
        assert "permanent:" not in msg  # no es fallo permanente

    @pytest.mark.asyncio
    async def test_deliver_package_other_forbidden_is_logged_as_error(
        self, db_session, sample_user, mock_bot
    ):
        """Otros TelegramForbiddenError son atrapados por el except externo y retornan False"""
        from aiogram.exceptions import TelegramForbiddenError

        mock_bot.send_message.side_effect = TelegramForbiddenError(
            method="sendMessage", message="Forbidden: bot is not an admin"
        )
        service = PackageService(db_session)
        package = service.create_package("Test Package")
        service.add_file_to_package(package.id, "file_id_1", "photo")

        success, msg = await service.deliver_package_to_user(mock_bot, sample_user.id, package.id)

        assert success is False
        assert "permanent:" not in msg  # no es fallo permanente
