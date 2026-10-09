"""
Tests del copy VIP directo (decisión de producto 2026-10).

Cubre:
- Sello de suscripción para las cabeceras de menú (principal y El Diván).
- `greeting(..., vip_seal=...)`: el sello se inserta sin alterar el saludo.
- `vip_direct_access`: activación nueva vs extensión vs degradación sin términos.

Todo son funciones puras: sin DB ni mocks de servicio.
"""

from datetime import UTC, datetime

import pytest

from utils.lucien_voice import LucienVoice

pytestmark = [pytest.mark.unit]

EXPIRY = datetime(2026, 10, 31, 5, 0, tzinfo=UTC)


class TestVipMenuSeal:
    """Sello de suscripción de las cabeceras (2 líneas con etiquetas)."""

    def test_incluye_tarifa_vencimiento_y_dias(self):
        seal = LucienVoice.vip_menu_seal("Mes a Su Lado", EXPIRY, 23)
        assert seal == (
            "💎 Su suscripción: <b>Mes a Su Lado</b>\n"
            "Válida hasta: 31/10/2026 · Días restantes: 23"
        )

    def test_sin_tarifa_omite_el_nombre(self):
        seal = LucienVoice.vip_menu_seal(None, EXPIRY, 5)
        assert seal == "💎 Su suscripción\nVálida hasta: 31/10/2026 · Días restantes: 5"

    def test_escapa_html_de_la_tarifa(self):
        seal = LucienVoice.vip_menu_seal("Plan <VIP>", EXPIRY, 1)
        assert "Plan &lt;VIP&gt;" in seal
        assert "<VIP>" not in seal


class TestVipMenuSealFromStatus:
    """Envoltorio que decide si hay sello a partir del estado VIP del servicio."""

    def test_none_cuando_no_es_vip(self):
        assert LucienVoice.vip_menu_seal_from_status({"is_vip": False, "expiry": EXPIRY}) is None

    def test_none_cuando_falta_el_vencimiento(self):
        assert LucienVoice.vip_menu_seal_from_status({"is_vip": True, "expiry": None}) is None

    def test_none_cuando_el_estado_es_vacio(self):
        assert LucienVoice.vip_menu_seal_from_status(None) is None

    def test_renderiza_el_sello_desde_el_estado(self):
        seal = LucienVoice.vip_menu_seal_from_status(
            {
                "is_vip": True,
                "tariff_name": "Mes a Su Lado",
                "expiry": EXPIRY,
                "days_remaining": 23,
            }
        )
        assert seal is not None
        assert "Su suscripción: <b>Mes a Su Lado</b>" in seal
        assert "Días restantes: 23" in seal


class TestGreetingWithSeal:
    """El saludo no cambia si no hay sello; con sello lo inserta antes de la pregunta."""

    def test_sin_sello_conserva_el_saludo(self):
        text = LucienVoice.greeting("Carlos")
        assert "Su suscripción" not in text
        assert text.endswith("¿En qué puedo asistirle hoy?")

    def test_con_sello_inserta_el_bloque(self):
        seal = LucienVoice.vip_menu_seal("Mes a Su Lado", EXPIRY, 23)
        text = LucienVoice.greeting("Carlos", vip_seal=seal)
        assert "Su suscripción: <b>Mes a Su Lado</b>" in text
        assert "Días restantes: 23" in text
        assert text.index("Su suscripción") < text.index("¿En qué puedo asistirle hoy?")


class TestVipDirectAccessCopy:
    """Mensaje de acceso: formato claro y apertura distinta al extender."""

    def test_activacion_nueva_usa_bienvenida_y_bloque_claro(self):
        text = LucienVoice.vip_direct_access(
            "https://t.me/+x",
            tariff_name="Mes a Su Lado",
            expiration_date=EXPIRY,
            days_remaining=23,
        )
        assert "<i>Bienvenido a El Diván.</i>" in text
        assert "Su suscripción: <b>Mes a Su Lado</b>" in text
        assert "Válida hasta: 31/10/2026" in text
        assert "Días restantes: 23" in text
        assert "🔗 <b>Su enlace de activación</b> (expira en 7 días)" in text
        assert "https://t.me/+x" in text
        assert text.endswith("Diana lo espera entre los selectos.</i>")

    def test_extension_cambia_la_apertura(self):
        text = LucienVoice.vip_direct_access(
            "https://t.me/+x",
            tariff_name="Mes a Su Lado",
            expiration_date=EXPIRY,
            days_remaining=54,
            is_extension=True,
        )
        assert "<i>Su tiempo en El Diván ha sido extendido.</i>" in text
        assert "Bienvenido a El Diván." not in text
        assert "Días restantes: 54" in text

    def test_sin_terminos_degrada_a_bienvenida_simple(self):
        text = LucienVoice.vip_direct_access()
        assert "<i>Bienvenido a El Diván.</i>" in text
        assert "Su suscripción" not in text
        assert "Su enlace de activación" not in text

    def test_reenvio_conserva_apertura_de_bienvenida(self):
        text = LucienVoice.vip_direct_access(
            "https://t.me/+r",
            tariff_name="Test Tariff",
            expiration_date=EXPIRY,
            days_remaining=3,
        )
        assert "Bienvenido a El Diván." in text
        assert "Días restantes: 3" in text
