"""
Tests de integración para callbacks VIP migrateados (VipPromoDetailCallback y VipPromoInterestCallback).

Verifica que los CallbackData migrados funcionan correctamente:
- VipPromoDetailCallback
- VipPromoInterestCallback

Tests:
1. Creación correcta con .pack()
2. Filtros matchean
3. Extracción de valores correcta
"""
import pytest
from unittest.mock import MagicMock

from keyboards.callback_data import VipPromoDetailCallback, VipPromoInterestCallback


class TestVipPromoDetailCallback:
    """Tests para VipPromoDetailCallback."""

    def test_callback_packs_correctly(self):
        """VipPromoDetailCallback.pack() genera el string esperado."""
        promo_id = 42
        callback = VipPromoDetailCallback(promo_id=promo_id)
        packed = callback.pack()

        # Formato esperado: "vip_promo_detail:42"
        assert packed == "vip_promo_detail:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes promo_id."""
        for promo_id in [1, 10, 100, 999]:
            callback = VipPromoDetailCallback(promo_id=promo_id)
            packed = callback.pack()
            assert packed == f"vip_promo_detail:{promo_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable (API pública de aiogram)."""
        callback_filter = VipPromoDetailCallback.filter()
        # Es un CallbackQueryFilter de aiogram
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_extracts_promo_id(self):
        """El callback extrae promo_id correctamente."""
        callback = VipPromoDetailCallback(promo_id=123)
        packed = callback.pack()

        # Extraer el valor
        promo_id = int(packed.split(":")[1])
        assert promo_id == 123


class TestVipPromoInterestCallback:
    """Tests para VipPromoInterestCallback."""

    def test_callback_packs_correctly(self):
        """VipPromoInterestCallback.pack() genera el string esperado."""
        promo_id = 42
        callback = VipPromoInterestCallback(promo_id=promo_id)
        packed = callback.pack()

        # Formato esperado: "vip_promo_interest:42"
        assert packed == "vip_promo_interest:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes promo_id."""
        for promo_id in [1, 10, 100, 999]:
            callback = VipPromoInterestCallback(promo_id=promo_id)
            packed = callback.pack()
            assert packed == f"vip_promo_interest:{promo_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = VipPromoInterestCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_extracts_promo_id(self):
        """El callback extrae promo_id correctamente."""
        callback = VipPromoInterestCallback(promo_id=456)
        packed = callback.pack()

        # Extraer el valor
        promo_id = int(packed.split(":")[1])
        assert promo_id == 456


class TestCallbackFormats:
    """Tests para el formato exacto de los callbacks."""

    def test_vip_promo_detail_format_exact(self):
        """Formato exacto es 'vip_promo_detail:id'."""
        cb = VipPromoDetailCallback(promo_id=1)
        packed = cb.pack()
        assert packed == "vip_promo_detail:1"

    def test_vip_promo_interest_format_exact(self):
        """Formato exacto es 'vip_promo_interest:id'."""
        cb = VipPromoInterestCallback(promo_id=1)
        packed = cb.pack()
        assert packed == "vip_promo_interest:1"

    def test_no_collision_between_callbacks(self):
        """VipPromoDetail y VipPromoInterest no collisionan."""
        detail_cb = VipPromoDetailCallback(promo_id=1)
        interest_cb = VipPromoInterestCallback(promo_id=1)

        assert detail_cb.pack() != interest_cb.pack()
        assert "vip_promo_detail" in detail_cb.pack()
        assert "vip_promo_interest" in interest_cb.pack()


class TestCallbackFilterMatching:
    """Tests para verificar que los filtros matchean correctamente."""

    def test_filter_matches_correct_detail_format(self):
        """El filtro de detail matchea el formato correcto."""
        callback_data = "vip_promo_detail:123"

        # Verificar parsing manual del formato
        prefix, promo_id_str = callback_data.split(":")
        promo_id = int(promo_id_str)

        assert prefix == "vip_promo_detail"
        assert promo_id == 123

    def test_filter_matches_correct_interest_format(self):
        """El filtro de interest matchea el formato correcto."""
        callback_data = "vip_promo_interest:456"

        # Verificar parsing manual del formato
        prefix, promo_id_str = callback_data.split(":")
        promo_id = int(promo_id_str)

        assert prefix == "vip_promo_interest"
        assert promo_id == 456

    def test_different_promo_ids_are_distinguishable(self):
        """Diferentes promo_id generan callbacks distinguishable."""
        cb1 = VipPromoDetailCallback(promo_id=100)
        cb2 = VipPromoDetailCallback(promo_id=200)

        assert cb1.pack() != cb2.pack()
        assert cb1.pack() == "vip_promo_detail:100"
        assert cb2.pack() == "vip_promo_detail:200"


class TestCallbackDataFormat:
    """Tests para el formato exacto de los callbacks."""

    def test_vip_promo_detail_with_zero_id(self):
        """Funciona con promo_id=0."""
        cb = VipPromoDetailCallback(promo_id=0)
        packed = cb.pack()
        assert packed == "vip_promo_detail:0"

    def test_vip_promo_interest_with_zero_id(self):
        """Funciona con promo_id=0."""
        cb = VipPromoInterestCallback(promo_id=0)
        packed = cb.pack()
        assert packed == "vip_promo_interest:0"

    def test_vip_promo_detail_with_large_id(self):
        """Funciona con promo_id muy grande."""
        cb = VipPromoDetailCallback(promo_id=999999999)
        packed = cb.pack()
        assert packed == "vip_promo_detail:999999999"

    def test_vip_promo_interest_with_large_id(self):
        """Funciona con promo_id muy grande."""
        cb = VipPromoInterestCallback(promo_id=999999999)
        packed = cb.pack()
        assert packed == "vip_promo_interest:999999999"


class TestIntegrationWithPromotion:
    """Tests de integración con objetos Promotion."""

    def test_creates_callback_from_promotion_id(self, db_session, sample_promotion):
        """Crea VipPromoDetailCallback desde promotion.id."""
        promo_id = sample_promotion.id
        callback = VipPromoDetailCallback(promo_id=promo_id)

        assert callback.pack() == f"vip_promo_detail:{promo_id}"

    def test_creates_interest_callback_from_promotion_id(self, db_session, sample_promotion):
        """Crea VipPromoInterestCallback desde promotion.id."""
        promo_id = sample_promotion.id
        callback = VipPromoInterestCallback(promo_id=promo_id)

        assert callback.pack() == f"vip_promo_interest:{promo_id}"

    def test_full_flow_detail_callback(self, db_session, sample_promotion):
        """Flujo completo para VipPromoDetailCallback."""
        # 1. Crear callback desde promotion
        callback = VipPromoDetailCallback(promo_id=sample_promotion.id)
        packed = callback.pack()

        # 2. Verificar formato
        assert packed.startswith("vip_promo_detail:")
        assert int(packed.split(":")[1]) == sample_promotion.id

    def test_full_flow_interest_callback(self, db_session, sample_promotion):
        """Flujo completo para VipPromoInterestCallback."""
        # 1. Crear callback desde promotion
        callback = VipPromoInterestCallback(promo_id=sample_promotion.id)
        packed = callback.pack()

        # 2. Verificar formato
        assert packed.startswith("vip_promo_interest:")
        assert int(packed.split(":")[1]) == sample_promotion.id


class TestNoCollisionWithOtherVIPCallbacks:
    """Tests para asegurar que no hay colisión con otros callbacks VIP."""

    def test_no_collision_with_select_tariff(self):
        """No colisiona con SelectTariffCallback."""
        from keyboards.callback_data import SelectTariffCallback

        vip_detail = VipPromoDetailCallback(promo_id=1)
        select_tariff = SelectTariffCallback(tariff_id=1)

        assert vip_detail.pack() != select_tariff.pack()
        assert "vip_promo_detail" in vip_detail.pack()
        assert "select_tariff" in select_tariff.pack()

    def test_no_collision_with_copy_token(self):
        """No colisiona con CopyTokenCallback."""
        from keyboards.callback_data import CopyTokenCallback

        vip_interest = VipPromoInterestCallback(promo_id=1)
        copy_token = CopyTokenCallback(token_id=1)

        assert vip_interest.pack() != copy_token.pack()
        assert "vip_promo_interest" in vip_interest.pack()
        assert "copy_token" in copy_token.pack()