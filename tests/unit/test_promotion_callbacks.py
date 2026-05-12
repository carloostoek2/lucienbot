"""
Tests de integración para los CallbackData de Promotion migrados.

Verifica pack/unpack, prefijos separados (admin vs user), flujo confirm,
y integración keyboards → handlers.
"""
import pytest
from keyboards.callback_data import (
    SelectPkgPromoCallback,
    PromoDetailCallback,
    TogglePromoCallback,
    PromoDeleteCallback,
    InterestDetailCallback,
    MarkAttendedCallback,
    BlockInterestCallback,
    PromoInterestsCallback,
    BlockedUserDetailCallback,
    UnblockUserCallback,
    ViewOfferCallback,
    OfferInterestCallback
)


class TestSelectPkgPromoCallback:
    """Selección de paquete para promoción"""

    def test_pack_with_pkg_id(self):
        """Pack genera callback string correcto"""
        cb = SelectPkgPromoCallback(pkg_id=42)
        packed = cb.pack()

        assert "promo_select_pkg" in packed
        assert "42" in packed

    def test_unpack_returns_correct_pkg_id(self):
        """Unpack retorna el pkg_id correcto"""
        packed = "promo_select_pkg:123"
        unpacked = SelectPkgPromoCallback.unpack(packed)

        assert unpacked.pkg_id == 123

    def test_roundtrip(self):
        """Pack → unpack preserva datos"""
        original = SelectPkgPromoCallback(pkg_id=999)
        unpacked = SelectPkgPromoCallback.unpack(original.pack())

        assert unpacked.pkg_id == 999


class TestPromoDetailCallback:
    """Detalle de promoción"""

    def test_pack_with_promo_id(self):
        """Pack genera callback string correcto"""
        cb = PromoDetailCallback(promo_id=5)
        packed = cb.pack()

        assert "promo_detail" in packed
        assert "5" in packed

    def test_unpack_returns_correct_promo_id(self):
        """Unpack retorna el promo_id correcto"""
        packed = "promo_detail:7"
        unpacked = PromoDetailCallback.unpack(packed)

        assert unpacked.promo_id == 7

    def test_roundtrip(self):
        """Pack → unpack preserva datos"""
        original = PromoDetailCallback(promo_id=100)
        unpacked = PromoDetailCallback.unpack(original.pack())

        assert unpacked.promo_id == 100


class TestTogglePromoCallback:
    """Activar/desactivar promoción"""

    def test_pack_enabled_true(self):
        """Pack con enabled=True"""
        cb = TogglePromoCallback(promo_id=1, enabled=True)
        packed = cb.pack()

        assert "toggle_promo" in packed
        assert "1" in packed

    def test_pack_enabled_false(self):
        """Pack con enabled=False"""
        cb = TogglePromoCallback(promo_id=1, enabled=False)
        packed = cb.pack()

        assert "toggle_promo" in packed

    def test_unpack_returns_values(self):
        """Unpack retorna valores correctos"""
        packed = TogglePromoCallback(promo_id=10, enabled=True).pack()
        unpacked = TogglePromoCallback.unpack(packed)

        assert unpacked.promo_id == 10
        assert unpacked.enabled is True

    def test_unpack_enabled_false(self):
        """Unpack retorna enabled=False correctamente"""
        packed = TogglePromoCallback(promo_id=10, enabled=False).pack()
        unpacked = TogglePromoCallback.unpack(packed)

        assert unpacked.enabled is False


class TestPromoDeleteCallback:
    """Eliminar promoción con confirmación"""

    def test_pack_confirmed_false(self):
        """Pack sin confirmar (primera vez)"""
        cb = PromoDeleteCallback(promo_id=1, confirmed=False)
        packed = cb.pack()

        assert "promo_del" in packed
        assert "1" in packed

    def test_pack_confirmed_true(self):
        """Pack confirmado (segunda vez)"""
        cb = PromoDeleteCallback(promo_id=1, confirmed=True)
        packed = cb.pack()

        assert "promo_del" in packed

    def test_unpack_confirmed_value(self):
        """Unpack retorna el valor de confirmed"""
        # Caso sin confirmar
        packed_no = PromoDeleteCallback(promo_id=5, confirmed=False).pack()
        unpacked_no = PromoDeleteCallback.unpack(packed_no)
        assert unpacked_no.confirmed is False

        # caso confirmado
        packed_yes = PromoDeleteCallback(promo_id=5, confirmed=True).pack()
        unpacked_yes = PromoDeleteCallback.unpack(packed_yes)
        assert unpacked_yes.confirmed is True

    def test_flujo_confirm_two_clicks(self):
        """Simula el flujo: click Sin Confirmar → click Confirmado"""
        # Paso 1: usuario hace click en "Eliminar" (sin confirmar)
        cb_step1 = PromoDeleteCallback(promo_id=42, confirmed=False)
        unpacked_step1 = PromoDeleteCallback.unpack(cb_step1.pack())

        # El handler debe mostrar teclado de confirmación
        assert unpacked_step1.confirmed is False

        # Paso 2: usuario confirma
        cb_step2 = PromoDeleteCallback(promo_id=42, confirmed=True)
        unpacked_step2 = PromoDeleteCallback.unpack(cb_step2.pack())

        # El handler debe ejecutar la eliminación
        assert unpacked_step2.confirmed is True


class TestInterestDetailCallback:
    """Detalle de expresión de interés"""

    def test_pack_with_interest_id(self):
        """Pack genera callback string correcto"""
        cb = InterestDetailCallback(interest_id=123)
        packed = cb.pack()

        assert "interest_detail" in packed
        assert "123" in packed

    def test_unpack_returns_correct_interest_id(self):
        """Unpack retorna el interest_id correcto"""
        packed = "interest_detail:456"
        unpacked = InterestDetailCallback.unpack(packed)

        assert unpacked.interest_id == 456


class TestMarkAttendedCallback:
    """Marcar interés como atendido (admin)"""

    def test_pack_with_interest_id(self):
        """Pack genera callback string correcto"""
        cb = MarkAttendedCallback(interest_id=99)
        packed = cb.pack()

        assert "adm_attended" in packed
        assert "99" in packed

    def test_unpack_returns_correct_interest_id(self):
        """Unpack retorna el interest_id correcto"""
        packed = "adm_attended:77"
        unpacked = MarkAttendedCallback.unpack(packed)

        assert unpacked.interest_id == 77


class TestBlockInterestCallback:
    """Bloquear usuario por interés"""

    def test_pack_confirmed_false(self):
        """Pack sin confirmar"""
        cb = BlockInterestCallback(user_id=111, confirmed=False)
        packed = cb.pack()

        assert "block_int" in packed
        assert "111" in packed

    def test_pack_confirmed_true(self):
        """Pack confirmado"""
        cb = BlockInterestCallback(user_id=111, confirmed=True)
        packed = cb.pack()

        assert "block_int" in packed

    def test_unpack_confirmed_value(self):
        """Unpack retorna valores correctos"""
        # Sin confirmar
        packed_no = BlockInterestCallback(user_id=222, confirmed=False).pack()
        unpacked_no = BlockInterestCallback.unpack(packed_no)
        assert unpacked_no.confirmed is False
        assert unpacked_no.user_id == 222

        # Confirmado
        packed_yes = BlockInterestCallback(user_id=222, confirmed=True).pack()
        unpacked_yes = BlockInterestCallback.unpack(packed_yes)
        assert unpacked_yes.confirmed is True


class TestPromoInterestsCallback:
    """Ver intereses de promoción"""

    def test_pack_with_promo_id(self):
        """Pack genera callback string correcto"""
        cb = PromoInterestsCallback(promo_id=33)
        packed = cb.pack()

        assert "promo_interests" in packed
        assert "33" in packed

    def test_unpack_returns_correct_promo_id(self):
        """Unpack retorna el promo_id correcto"""
        packed = "promo_interests:55"
        unpacked = PromoInterestsCallback.unpack(packed)

        assert unpacked.promo_id == 55


class TestBlockedUserDetailCallback:
    """Detalle de usuario bloqueado"""

    def test_pack_with_user_id(self):
        """Pack genera callback string correcto"""
        cb = BlockedUserDetailCallback(user_id=888)
        packed = cb.pack()

        assert "blocked_user_detail" in packed
        assert "888" in packed

    def test_unpack_returns_correct_user_id(self):
        """Unpack retorna el user_id correcto"""
        packed = "blocked_user_detail:999"
        unpacked = BlockedUserDetailCallback.unpack(packed)

        assert unpacked.user_id == 999


class TestUnblockUserCallback:
    """Desbloquear usuario"""

    def test_pack_with_user_id(self):
        """Pack genera callback string correcto"""
        cb = UnblockUserCallback(user_id=777)
        packed = cb.pack()

        assert "unblock_user" in packed
        assert "777" in packed

    def test_unpack_returns_correct_user_id(self):
        """Unpack retorna el user_id correcto"""
        packed = "unblock_user:666"
        unpacked = UnblockUserCallback.unpack(packed)

        assert unpacked.user_id == 666


class TestViewOfferCallback:
    """Ver detalle de oferta usuario"""

    def test_pack_with_promo_id(self):
        """Pack genera callback string correcto"""
        cb = ViewOfferCallback(promo_id=25)
        packed = cb.pack()

        assert "view_offer" in packed
        assert "25" in packed

    def test_unpack_returns_correct_promo_id(self):
        """Unpack retorna el promo_id correcto"""
        packed = "view_offer:50"
        unpacked = ViewOfferCallback.unpack(packed)

        assert unpacked.promo_id == 50


class TestOfferInterestCallback:
    """Expresar interés en oferta"""

    def test_pack_with_promo_id(self):
        """Pack genera callback string correcto"""
        cb = OfferInterestCallback(promo_id=15)
        packed = cb.pack()

        assert "offer_interest" in packed
        assert "15" in packed

    def test_unpack_returns_correct_promo_id(self):
        """Unpack retorna el promo_id correcto"""
        packed = "offer_interest:30"
        unpacked = OfferInterestCallback.unpack(packed)

        assert unpacked.promo_id == 30


class TestPrefixUniqueness:
    """Verifica que los callback strings no colisionan"""

    def test_admin_callbacks_unique_prefix(self):
        """Callback strings de admin tienen prefijos únicos"""
        callbacks = [
            PromoInterestsCallback(promo_id=1),
            MarkAttendedCallback(interest_id=1),
            BlockedUserDetailCallback(user_id=1),
            PromoDeleteCallback(promo_id=1, confirmed=False),
        ]

        prefixes = set()
        for cb in callbacks:
            # Extraer prefijo del packed string (antes de los dos puntos)
            prefix = cb.pack().split(":")[0]
            assert prefix not in prefixes, f"Prefijo duplicado: {prefix}"
            prefixes.add(prefix)

    def test_user_callbacks_unique_prefix(self):
        """Callback strings de user tienen prefijos únicos"""
        callbacks = [
            ViewOfferCallback(promo_id=1),
            OfferInterestCallback(promo_id=1),
        ]

        prefixes = set()
        for cb in callbacks:
            prefix = cb.pack().split(":")[0]
            assert prefix not in prefixes, f"Prefijo duplicado: {prefix}"
            prefixes.add(prefix)

    def test_admin_user_no_prefix_collision(self):
        """Prefijos admin no colisionan con user"""
        admin_cb = PromoInterestsCallback(promo_id=1)
        user_cb = ViewOfferCallback(promo_id=1)

        admin_prefix = admin_cb.pack().split(":")[0]
        user_prefix = user_cb.pack().split(":")[0]

        assert admin_prefix != user_prefix


class TestKeyboardIntegration:
    """Integración con inline_keyboards"""

    def test_packs_in_keyboards_work(self):
        """Verifica que los callbacks se generan correctamente para keyboards"""
        promo_id = 42

        # TogglePromo (activar/desactivar) - debe generar string válido
        toggle_cb = TogglePromoCallback(promo_id=promo_id, enabled=False)
        toggle_packed = toggle_cb.pack()
        assert "toggle_promo" in toggle_packed

        # Verificar unpack
        toggle_unpacked = TogglePromoCallback.unpack(toggle_packed)
        assert toggle_unpacked.promo_id == promo_id
        assert toggle_unpacked.enabled is False

        # PromoInterests (ver intereses)
        interests_cb = PromoInterestsCallback(promo_id=promo_id)
        interests_packed = interests_cb.pack()
        assert "promo_interests" in interests_packed

        # PromoDelete (eliminar)
        delete_cb = PromoDeleteCallback(promo_id=promo_id, confirmed=False)
        delete_packed = delete_cb.pack()
        assert "promo_del" in delete_packed

    def test_interest_packs_in_keyboards_work(self):
        """Verifica que los callbacks de interés funcionan"""
        interest_id = 1
        user_id = 123

        # MarkAttended
        attended_cb = MarkAttendedCallback(interest_id=interest_id)
        attended_packed = attended_cb.pack()
        attended_unpacked = MarkAttendedCallback.unpack(attended_packed)
        assert attended_unpacked.interest_id == interest_id

        # BlockInterest (sin confirmar primero)
        block_cb = BlockInterestCallback(user_id=user_id, confirmed=False)
        block_packed = block_cb.pack()
        block_unpacked = BlockInterestCallback.unpack(block_packed)
        assert block_unpacked.user_id == user_id
        assert block_unpacked.confirmed is False

    def test_user_offer_packs_work(self):
        """Verifica que los callbacks de oferta funcionan"""
        promo_id = 99

        # ViewOffer
        view_cb = ViewOfferCallback(promo_id=promo_id)
        view_packed = view_cb.pack()
        view_unpacked = ViewOfferCallback.unpack(view_packed)
        assert view_unpacked.promo_id == promo_id

        # OfferInterest
        interest_cb = OfferInterestCallback(promo_id=promo_id)
        interest_packed = interest_cb.pack()
        interest_unpacked = OfferInterestCallback.unpack(interest_packed)
        assert interest_unpacked.promo_id == promo_id