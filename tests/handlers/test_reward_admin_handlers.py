"""
Tests unitarios para reward_admin_handlers.

Cubre puros extraidos para wizard/list/detail (Item 2/34).
"""

from unittest.mock import MagicMock

import pytest

from tests.helpers import model_mock
from models.models import Package, Reward, RewardType, Tariff

pytestmark = [pytest.mark.unit]


class TestRewardAdminPureHelpers:
    """Tests para los helpers puros extraidos de reward_admin_handlers (Item 2/34 / arch-enforcer LOC).
    Precedent item7/8/9: import inside, no @patch on puros, UI 1:1 pins, verb+context+result.
    """

    def test_build_reward_confirm_text_with_besitos(self):
        from handlers.reward_admin_handlers import build_reward_confirm_text_and_keyboard

        data = {
            "name": "Test",
            "description": "Desc",
            "reward_type": RewardType.BESITOS,
            "besito_amount": 50,
        }
        text, kb = build_reward_confirm_text_and_keyboard(data)
        assert "Resumen de la recompensa" in text
        assert "Test" in text
        assert "50 besitos" in text
        assert len(kb.inline_keyboard) == 2
        assert "✅ Crear" in kb.inline_keyboard[0][0].text

    def test_build_reward_confirm_text_with_package(self):
        from handlers.reward_admin_handlers import build_reward_confirm_text_and_keyboard

        pkg = model_mock(Package)
        pkg.name = "PkgX"
        data = {"name": "P", "description": None, "reward_type": RewardType.PACKAGE}
        text, _ = build_reward_confirm_text_and_keyboard(data, pkg=pkg)
        assert "Paquete: PkgX" in text
        assert "Sin descripcion" in text

    def test_build_reward_confirm_text_with_tariff(self):
        from handlers.reward_admin_handlers import build_reward_confirm_text_and_keyboard

        tariff = model_mock(Tariff)
        tariff.name = "VIP30"
        data = {"name": "V", "description": "d", "reward_type": RewardType.VIP_ACCESS}
        text, _ = build_reward_confirm_text_and_keyboard(data, tariff=tariff)
        assert "VIP: VIP30" in text

    def test_build_package_selection_text_and_buttons_empty(self):
        from handlers.reward_admin_handlers import build_package_selection_text_and_buttons

        text, buttons = build_package_selection_text_and_buttons([])
        assert "No hay paquetes disponibles" in text
        assert any("Crear nuevo paquete" in b[0].text for b in buttons)

    def test_build_package_selection_text_and_buttons_with_pkgs(self):
        from handlers.reward_admin_handlers import build_package_selection_text_and_buttons

        p1 = model_mock(Package)
        p1.id = 1
        p1.name = "P1"
        p1.file_count = 3
        p1.reward_stock = -1
        p2 = model_mock(Package)
        p2.id = 2
        p2.name = "P2"
        p2.file_count = 1
        p2.reward_stock = 5
        _, buttons = build_package_selection_text_and_buttons([p1, p2])
        assert len(buttons) == 4  # 2 pkgs + create + cancel
        assert "P1 (3 archivos, stock: ∞)" in buttons[0][0].text
        assert "P2 (1 archivos, stock: 5)" in buttons[1][0].text

    def test_build_tariff_selection_buttons(self):
        from handlers.reward_admin_handlers import build_tariff_selection_buttons

        t = model_mock(Tariff)
        t.id = 9
        t.name = "T"
        t.duration_days = 30
        buttons = build_tariff_selection_buttons([t])
        assert len(buttons) == 2
        assert "T (30 dias)" in buttons[0][0].text
        assert "Cancelar" in buttons[1][0].text

    def test_build_pkg_confirmation_text_and_keyboard(self):
        from handlers.reward_admin_handlers import build_pkg_confirmation_text_and_keyboard

        data = {"pkg_name": "X", "pkg_description": None, "pkg_files": [{}], "pkg_reward_stock": -1}
        text, kb = build_pkg_confirmation_text_and_keyboard(data)
        assert "Resumen del paquete" in text
        assert "Ilimitado" in text
        assert len(kb.inline_keyboard) == 2

    def test_build_reward_list_entry_and_button(self):
        from handlers.reward_admin_handlers import build_reward_list_entry_and_button

        r = model_mock(Reward, is_active=True, name="A" * 40, id=5)
        entry, button = build_reward_list_entry_and_button(r)
        assert "✅" in entry
        assert "A" * 30 in entry  # truncated
        assert "5" in button[0].callback_data

    def test_build_reward_detail_text_and_keyboard_active_package(self):
        from handlers.reward_admin_handlers import build_reward_detail_text_and_keyboard

        pkg = model_mock(Package)
        pkg.name = "Pkg"
        r = model_mock(Reward)
        r.is_active = True
        r.name = "R"
        r.description = None
        rt = MagicMock()
        rt.value = "package"
        r.reward_type = rt
        r.package = pkg
        r.tariff = None
        r.besito_amount = None
        text, kb = build_reward_detail_text_and_keyboard(r)
        assert "R" in text
        assert "Sin descripcion" in text
        assert "Paquete: Pkg" in text
        assert "Desactivar" in kb.inline_keyboard[0][0].text
        assert "Eliminar" in kb.inline_keyboard[1][0].text

    def test_build_reward_delete_confirm_keyboard(self):
        from handlers.reward_admin_handlers import build_reward_delete_confirm_keyboard

        kb = build_reward_delete_confirm_keyboard(7)
        assert len(kb.inline_keyboard) == 2
        assert "Si, eliminar" in kb.inline_keyboard[0][0].text
        assert "7" in kb.inline_keyboard[0][0].callback_data

    def test_compute_reward_type_text_branches(self):
        from handlers.reward_admin_handlers import compute_reward_type_text

        assert "10 besitos" in compute_reward_type_text(RewardType.BESITOS, besito_amount=10)
        pkg = model_mock(Package)
        pkg.name = "P"
        assert "Paquete: P" in compute_reward_type_text(RewardType.PACKAGE, pkg=pkg)
        tariff = model_mock(Tariff)
        tariff.name = "T"
        assert "VIP: T" in compute_reward_type_text(RewardType.VIP_ACCESS, tariff=tariff)

    def test_build_back_only_keyboard(self):
        from handlers.reward_admin_handlers import build_back_only_keyboard

        kb = build_back_only_keyboard()
        assert "Volver" in kb.inline_keyboard[0][0].text

    def test_build_reward_created_and_error_text(self):
        from handlers.reward_admin_handlers import (
            build_reward_created_text,
            build_reward_error_text,
        )

        r = model_mock(Reward, name="X", reward_type=MagicMock(value="besitos"))
        assert "creada exitosamente" in build_reward_created_text(r)
        assert "Error al crear" in build_reward_error_text()
