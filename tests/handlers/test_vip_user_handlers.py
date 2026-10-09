"""
Tests unitarios para vip_user_handlers.

Cubre la cabecera del menú de El Diván: sello de suscripción (tarifa, vencimiento,
días restantes) para VIP y aviso para quien ya no está activo (decisión 2026-10).
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit]


class TestVipAreaMenu:
    """Cabecera de El Diván con el estado de la suscripción."""

    @patch("handlers.vip_user_handlers.VIPService")
    async def test_vip_muestra_sello_de_suscripcion(self, mock_vip_svc, make_callback):
        mock_vip_svc.return_value.get_vip_menu_status.return_value = {
            "is_vip": True,
            "tariff_name": "Mes a Su Lado",
            "expiry": datetime(2026, 10, 31, tzinfo=UTC),
            "days_remaining": 23,
        }
        cb = make_callback(data="vip_area")

        from handlers.vip_user_handlers import vip_area_menu

        await vip_area_menu(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Su suscripción: <b>Mes a Su Lado</b>" in text
        assert "Válida hasta: 31/10/2026 · Días restantes: 23" in text
        cb.answer.assert_called_once()

    @patch("handlers.vip_user_handlers.VIPService")
    async def test_no_vip_muestra_aviso_sin_sello(self, mock_vip_svc, make_callback):
        mock_vip_svc.return_value.get_vip_menu_status.return_value = {
            "is_vip": False,
            "tariff_name": None,
            "expiry": None,
            "days_remaining": 0,
        }
        cb = make_callback(data="vip_area")

        from handlers.vip_user_handlers import vip_area_menu

        await vip_area_menu(cb)

        text = cb.message.edit_text.call_args[0][0]
        assert "no está activa" in text
        assert "💎 Su suscripción" not in text
        assert "Días restantes" not in text
