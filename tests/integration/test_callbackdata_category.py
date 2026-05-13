"""
Tests de integración para callbacks Category Admin migrateados.

Verifica que los CallbackData migrados funcionan correctamente:
- CategoryAdminDetailCallback
- CategoryAdminToggleCallback
- CategoryAdminDeleteCallback
- CategoryAdminConfirmDeleteCallback
- CategoryAssignCallback
- PackageAssignCallback
"""
import pytest
from unittest.mock import MagicMock

from keyboards.callback_data import (
    CategoryAdminDetailCallback,
    CategoryAdminToggleCallback,
    CategoryAdminDeleteCallback,
    CategoryAdminConfirmDeleteCallback,
    CategoryAssignCallback,
    PackageAssignCallback,
)


class TestCategoryAdminDetailCallback:
    """Tests para CategoryAdminDetailCallback."""

    def test_callback_packs_correctly(self):
        """CategoryAdminDetailCallback.pack() genera el string esperado."""
        category_id = 42
        callback = CategoryAdminDetailCallback(category_id=category_id)
        packed = callback.pack()

        # Formato esperado: "cat_adm_detail:42"
        assert packed == "cat_adm_detail:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes category_id."""
        for category_id in [1, 10, 100, 999]:
            callback = CategoryAdminDetailCallback(category_id=category_id)
            packed = callback.pack()
            assert packed == f"cat_adm_detail:{category_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable (API pública de aiogram)."""
        callback_filter = CategoryAdminDetailCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = CategoryAdminDetailCallback(category_id=123)
        packed = callback.pack()

        # Parse manual para verificar
        prefix, category_id_str = packed.split(":")
        assert prefix == "cat_adm_detail"
        assert int(category_id_str) == 123


class TestCategoryAdminToggleCallback:
    """Tests para CategoryAdminToggleCallback."""

    def test_callback_packs_correctly(self):
        """CategoryAdminToggleCallback.pack() genera el string esperado."""
        category_id = 42
        callback = CategoryAdminToggleCallback(category_id=category_id)
        packed = callback.pack()

        # Formato esperado: "cat_adm_toggle:42"
        assert packed == "cat_adm_toggle:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes category_id."""
        for category_id in [1, 10, 100, 999]:
            callback = CategoryAdminToggleCallback(category_id=category_id)
            packed = callback.pack()
            assert packed == f"cat_adm_toggle:{category_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = CategoryAdminToggleCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = CategoryAdminToggleCallback(category_id=456)
        packed = callback.pack()

        prefix, category_id_str = packed.split(":")
        assert prefix == "cat_adm_toggle"
        assert int(category_id_str) == 456


class TestCategoryAdminDeleteCallback:
    """Tests para CategoryAdminDeleteCallback."""

    def test_callback_packs_correctly(self):
        """CategoryAdminDeleteCallback.pack() genera el string esperado."""
        category_id = 42
        callback = CategoryAdminDeleteCallback(category_id=category_id)
        packed = callback.pack()

        # Formato esperado: "cat_adm_delete:42"
        assert packed == "cat_adm_delete:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes category_id."""
        for category_id in [1, 10, 100, 999]:
            callback = CategoryAdminDeleteCallback(category_id=category_id)
            packed = callback.pack()
            assert packed == f"cat_adm_delete:{category_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = CategoryAdminDeleteCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = CategoryAdminDeleteCallback(category_id=789)
        packed = callback.pack()

        prefix, category_id_str = packed.split(":")
        assert prefix == "cat_adm_delete"
        assert int(category_id_str) == 789


class TestCategoryAdminConfirmDeleteCallback:
    """Tests para CategoryAdminConfirmDeleteCallback."""

    def test_callback_packs_correctly(self):
        """CategoryAdminConfirmDeleteCallback.pack() genera el string esperado."""
        category_id = 42
        callback = CategoryAdminConfirmDeleteCallback(category_id=category_id)
        packed = callback.pack()

        # Formato esperado: "cat_adm_confirm_del:42"
        assert packed == "cat_adm_confirm_del:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes category_id."""
        for category_id in [1, 10, 100, 999]:
            callback = CategoryAdminConfirmDeleteCallback(category_id=category_id)
            packed = callback.pack()
            assert packed == f"cat_adm_confirm_del:{category_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = CategoryAdminConfirmDeleteCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = CategoryAdminConfirmDeleteCallback(category_id=321)
        packed = callback.pack()

        prefix, category_id_str = packed.split(":")
        assert prefix == "cat_adm_confirm_del"
        assert int(category_id_str) == 321


class TestCategoryAssignCallback:
    """Tests para CategoryAssignCallback."""

    def test_callback_packs_correctly(self):
        """CategoryAssignCallback.pack() genera el string esperado."""
        category_id = 42
        callback = CategoryAssignCallback(category_id=category_id)
        packed = callback.pack()

        # Formato esperado: "cat_assign:42"
        assert packed == "cat_assign:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes category_id."""
        for category_id in [1, 5, 20, 100]:
            callback = CategoryAssignCallback(category_id=category_id)
            packed = callback.pack()
            assert packed == f"cat_assign:{category_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = CategoryAssignCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = CategoryAssignCallback(category_id=3)
        packed = callback.pack()

        prefix, category_id_str = packed.split(":")
        assert prefix == "cat_assign"
        assert int(category_id_str) == 3


class TestPackageAssignCallback:
    """Tests para PackageAssignCallback."""

    def test_callback_packs_correctly(self):
        """PackageAssignCallback.pack() genera el string esperado."""
        package_id = 42
        callback = PackageAssignCallback(package_id=package_id)
        packed = callback.pack()

        # Formato esperado: "pkg_assign:42"
        assert packed == "pkg_assign:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes package_id."""
        for package_id in [1, 10, 100, 999]:
            callback = PackageAssignCallback(package_id=package_id)
            packed = callback.pack()
            assert packed == f"pkg_assign:{package_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = PackageAssignCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = PackageAssignCallback(package_id=555)
        packed = callback.pack()

        prefix, package_id_str = packed.split(":")
        assert prefix == "pkg_assign"
        assert int(package_id_str) == 555


class TestCallbackNoCollisions:
    """Tests para verificar que no hay colisiones entre callbacks."""

    def test_no_collision_detail_vs_toggle(self):
        """CategoryAdminDetail y CategoryAdminToggle no collsionan."""
        category_id = 1
        detail_cb = CategoryAdminDetailCallback(category_id=category_id)
        toggle_cb = CategoryAdminToggleCallback(category_id=category_id)

        assert detail_cb.pack() != toggle_cb.pack()
        assert "cat_adm_detail" in detail_cb.pack()
        assert "cat_adm_toggle" in toggle_cb.pack()

    def test_no_collision_delete_vs_confirm_delete(self):
        """CategoryAdminDelete y CategoryAdminConfirmDelete no collisionan."""
        category_id = 1
        delete_cb = CategoryAdminDeleteCallback(category_id=category_id)
        confirm_cb = CategoryAdminConfirmDeleteCallback(category_id=category_id)

        assert delete_cb.pack() != confirm_cb.pack()
        assert "cat_adm_delete" in delete_cb.pack()
        assert "cat_adm_confirm_del" in confirm_cb.pack()

    def test_no_collision_toggle_vs_delete(self):
        """CategoryAdminToggle y CategoryAdminDelete no collisionan."""
        category_id = 1
        toggle_cb = CategoryAdminToggleCallback(category_id=category_id)
        delete_cb = CategoryAdminDeleteCallback(category_id=category_id)

        assert toggle_cb.pack() != delete_cb.pack()
        assert "cat_adm_toggle" in toggle_cb.pack()
        assert "cat_adm_delete" in delete_cb.pack()

    def test_no_collision_admin_vs_assign(self):
        """Callbacks admin y assign no collisionan."""
        category_id = 1
        admin_cb = CategoryAdminDetailCallback(category_id=category_id)
        assign_cb = CategoryAssignCallback(category_id=category_id)

        assert admin_cb.pack() != assign_cb.pack()
        assert "cat_adm_detail" in admin_cb.pack()
        assert "cat_assign" in assign_cb.pack()

    def test_no_collision_category_assign_vs_package_assign(self):
        """CategoryAssign y PackageAssign no collisionan."""
        category_id = 1
        package_id = 1
        cat_cb = CategoryAssignCallback(category_id=category_id)
        pkg_cb = PackageAssignCallback(package_id=package_id)

        assert cat_cb.pack() != pkg_cb.pack()
        assert "cat_assign" in cat_cb.pack()
        assert "pkg_assign" in pkg_cb.pack()


class TestCallbackIntegrationWithCategories:
    """Tests de integración con categorías."""

    def test_category_detail_callback_id_matches_category(self, db_session, sample_category):
        """CategoryAdminDetailCallback usa el ID correcto de la categoría."""
        callback = CategoryAdminDetailCallback(category_id=sample_category.id)
        packed = callback.pack()

        assert f"cat_adm_detail:{sample_category.id}" == packed

    def test_category_toggle_callback_id_matches_category(self, db_session, sample_category):
        """CategoryAdminToggleCallback usa el ID correcto de la categoría."""
        callback = CategoryAdminToggleCallback(category_id=sample_category.id)
        packed = callback.pack()

        assert f"cat_adm_toggle:{sample_category.id}" == packed

    def test_category_delete_callback_id_matches_category(self, db_session, sample_category):
        """CategoryAdminDeleteCallback usa el ID correcto de la categoría."""
        callback = CategoryAdminDeleteCallback(category_id=sample_category.id)
        packed = callback.pack()

        assert f"cat_adm_delete:{sample_category.id}" == packed

    def test_category_confirm_delete_callback_id_matches_category(self, db_session, sample_category):
        """CategoryAdminConfirmDeleteCallback usa el ID correcto de la categoría."""
        callback = CategoryAdminConfirmDeleteCallback(category_id=sample_category.id)
        packed = callback.pack()

        assert f"cat_adm_confirm_del:{sample_category.id}" == packed


class TestCallbackDataFormat:
    """Tests del formato exacto."""

    def test_category_admin_detail_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = CategoryAdminDetailCallback(category_id=1)
        packed = cb.pack()
        assert packed == "cat_adm_detail:1"

    def test_category_admin_toggle_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = CategoryAdminToggleCallback(category_id=1)
        packed = cb.pack()
        assert packed == "cat_adm_toggle:1"

    def test_category_admin_delete_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = CategoryAdminDeleteCallback(category_id=1)
        packed = cb.pack()
        assert packed == "cat_adm_delete:1"

    def test_category_admin_confirm_delete_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = CategoryAdminConfirmDeleteCallback(category_id=1)
        packed = cb.pack()
        assert packed == "cat_adm_confirm_del:1"

    def test_category_assign_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = CategoryAssignCallback(category_id=1)
        packed = cb.pack()
        assert packed == "cat_assign:1"

    def test_package_assign_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = PackageAssignCallback(package_id=1)
        packed = cb.pack()
        assert packed == "pkg_assign:1"


class TestFullCategoryFlow:
    """Tests del flujo completo de gestión de categoría."""

    def test_full_category_detail_flow(self, db_session, sample_category):
        """Flujo: List → Detail → Toggle."""
        category_id = sample_category.id

        # Step 1: Ver detalle de la categoría
        detail_callback = CategoryAdminDetailCallback(category_id=category_id)
        detail_packed = detail_callback.pack()

        # Step 2: Toggle (activar/desactivar)
        toggle_callback = CategoryAdminToggleCallback(category_id=category_id)
        toggle_packed = toggle_callback.pack()

        # Verificar formato correcto
        assert detail_packed == f"cat_adm_detail:{category_id}"
        assert toggle_packed == f"cat_adm_toggle:{category_id}"

    def test_full_category_delete_flow(self, db_session, sample_category):
        """Flujo: Detail → Delete → Confirm."""
        category_id = sample_category.id

        # Step 1: Ver detalle
        detail_callback = CategoryAdminDetailCallback(category_id=category_id)
        detail_packed = detail_callback.pack()

        # Step 2: Click en eliminar
        delete_callback = CategoryAdminDeleteCallback(category_id=category_id)
        delete_packed = delete_callback.pack()

        # Step 3: Confirmar eliminación
        confirm_callback = CategoryAdminConfirmDeleteCallback(category_id=category_id)
        confirm_packed = confirm_callback.pack()

        # Verificar formato correcto
        assert detail_packed == f"cat_adm_detail:{category_id}"
        assert delete_packed == f"cat_adm_delete:{category_id}"
        assert confirm_packed == f"cat_adm_confirm_del:{category_id}"

    def test_full_assign_package_flow(self, db_session, sample_category):
        """Flujo: Assign Category → Select Package → Confirm."""
        category_id = sample_category.id
        package_id = 1

        # Step 1: Seleccionar categoría
        category_callback = CategoryAssignCallback(category_id=category_id)
        category_packed = category_callback.pack()

        # Step 2: Seleccionar paquete
        package_callback = PackageAssignCallback(package_id=package_id)
        package_packed = package_callback.pack()

        # Verificar formato correcto
        assert category_packed == f"cat_assign:{category_id}"
        assert package_packed == f"pkg_assign:{package_id}"

    def test_callback_chain_in_category_flow(self, db_session, sample_category):
        """Callback chain en el flujo de gestión de categorías."""
        category_id = sample_category.id

        # 1. Ver lista de categorías → Click en categoría
        detail_packed = CategoryAdminDetailCallback(category_id=category_id).pack()

        # 2. En detalle → Toggle
        toggle_packed = CategoryAdminToggleCallback(category_id=category_id).pack()

        # 3. En detalle → Eliminar
        delete_packed = CategoryAdminDeleteCallback(category_id=category_id).pack()

        # 4. Confirmar eliminación
        confirm_packed = CategoryAdminConfirmDeleteCallback(category_id=category_id).pack()

        # 5. Volver a lista
        list_packed = "list_categories"

        # Verificar todas las transiciones
        assert "cat_adm_detail" in detail_packed
        assert "cat_adm_toggle" in toggle_packed
        assert "cat_adm_delete" in delete_packed
        assert "cat_adm_confirm_del" in confirm_packed
        assert list_packed == "list_categories"