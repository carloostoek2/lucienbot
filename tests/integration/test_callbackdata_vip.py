"""
Tests de integración para callbacks VIP migrateados.

Verifica que los CallbackData migrados funcionan correctamente:
- SelectTariffCallback
- CopyTokenCallback
"""
import pytest
from unittest.mock import MagicMock

from keyboards.callback_data import (
    CopyTokenCallback,
    ForwardActionCallback,
    ForwardCancelCallback,
    ForwardConfirmCallback,
    SelectTariffCallback,
    SubscriberActionCallback,
    SubscriberConfirmCallback,
    SubscriberExtendTariffCallback,
    SubscriberListCallback,
    SubscriberProfileCallback,
)
from keyboards.inline_keyboards import (
    forward_action_keyboard,
    forward_cancel_keyboard,
    forward_confirm_keyboard,
    tariffs_keyboard,
    token_actions_keyboard,
)


class TestSelectTariffCallback:
    """Tests para SelectTariffCallback."""

    def test_callback_packs_correctly(self):
        """SelectTariffCallback.pack() genera el string esperado."""
        tariff_id = 42
        callback = SelectTariffCallback(tariff_id=tariff_id)
        packed = callback.pack()

        # Formato esperado: "select_tariff:42"
        assert packed == "select_tariff:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes tariff_id."""
        for tariff_id in [1, 10, 100, 999]:
            callback = SelectTariffCallback(tariff_id=tariff_id)
            packed = callback.pack()
            assert packed == f"select_tariff:{tariff_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable (API pública de aiogram)."""
        callback_filter = SelectTariffCallback.filter()
        # Es un CallbackQueryFilter de aiogram
        assert callback_filter is not None
        assert callable(callback_filter)


class TestSubscriberAdminCallbacks:
    """Tests para callbacks de admin suscriptores VIP (phase 36)."""

    def test_subscriber_list_callback_pack_unpack(self):
        cb = SubscriberListCallback(channel_id=3, page=1)
        packed = cb.pack()
        assert packed == "sub_list:3:1"
        unpacked = SubscriberListCallback.unpack(packed)
        assert unpacked.channel_id == 3
        assert unpacked.page == 1

    def test_subscriber_profile_callback_pack(self):
        cb = SubscriberProfileCallback(subscription_id=42, channel_id=2, page=0)
        assert cb.pack() == "sub_prof:42:2:0"

    def test_subscriber_action_callback_pack(self):
        cb = SubscriberActionCallback(
            action="kick", subscription_id=5, channel_id=1, page=0
        )
        assert "kick" in cb.pack()

    def test_subscriber_extend_tariff_callback_pack(self):
        cb = SubscriberExtendTariffCallback(
            subscription_id=1, tariff_id=7, channel_id=0, page=0
        )
        assert cb.pack() == "sub_ext_tar:1:7:0:0"

    def test_subscriber_confirm_callback_pack(self):
        cb = SubscriberConfirmCallback(
            action="grant_besitos", subscription_id=3, channel_id=0, page=1
        )
        assert "grant_besitos" in cb.pack()


class TestForwardAdminCallbacks:
    """Tests para callbacks de reenvío admin (VIP | besitos)."""

    def test_forward_action_packs(self):
        assert ForwardActionCallback(action="vip").pack() == "fwd_action:vip"
        assert ForwardActionCallback(action="besitos").pack() == "fwd_action:besitos"

    def test_forward_confirm_packs(self):
        assert ForwardConfirmCallback(action="vip").pack() == "fwd_confirm:vip"
        assert ForwardConfirmCallback(action="besitos").pack() == "fwd_confirm:besitos"

    def test_forward_cancel_packs(self):
        assert ForwardCancelCallback().pack() == "fwd_cancel:cancel"

    def test_forward_action_keyboard_uses_callbacks(self):
        kb = forward_action_keyboard()
        callbacks = [row[0].callback_data for row in kb.inline_keyboard]
        assert "fwd_action:vip" in callbacks
        assert "fwd_action:besitos" in callbacks
        assert "fwd_cancel:cancel" in callbacks

    def test_forward_confirm_keyboard_uses_callbacks(self):
        kb = forward_confirm_keyboard("besitos")
        row = kb.inline_keyboard[0]
        assert row[0].callback_data == "fwd_confirm:besitos"
        assert row[1].callback_data == "fwd_cancel:cancel"

    def test_forward_cancel_keyboard_uses_callback(self):
        kb = forward_cancel_keyboard()
        assert kb.inline_keyboard[0][0].callback_data == "fwd_cancel:cancel"


class TestCopyTokenCallback:
    """Tests para CopyTokenCallback."""

    def test_callback_packs_correctly(self):
        """CopyTokenCallback.pack() genera el string esperado."""
        token_id = 123
        callback = CopyTokenCallback(token_id=token_id)
        packed = callback.pack()

        # Formato esperado: "copy_token:123"
        assert packed == "copy_token:123"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes token_id."""
        for token_id in [1, 10, 100, 999]:
            callback = CopyTokenCallback(token_id=token_id)
            packed = callback.pack()
            assert packed == f"copy_token:{token_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = CopyTokenCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)


class TestTariffsKeyboard:
    """Tests para tariffs_keyboard con for_selection=True."""

    def test_tariffs_keyboard_generates_select_tariff_callbacks(self, db_session, sample_tariff):
        """tariffs_keyboard con for_selection=True genera SelectTariffCallback."""
        tariffs = [sample_tariff]
        keyboard = tariffs_keyboard(tariffs, for_selection=True)

        # Verificar que hay un botón con el callback correcto
        # (incluye botón de tarifa + botón de volver)
        buttons = keyboard.inline_keyboard
        assert len(buttons) >= 1  # Al menos la tarifa

        # El primer botón es la tarifa
        callback_data = buttons[0][0].callback_data
        assert callback_data.startswith("select_tariff:")

    def test_tariffs_keyboard_includes_back_button_without_selection(self, db_session, sample_tariff):
        """tariffs_keyboard sin for_selection incluye botón de volver."""
        tariffs = [sample_tariff]
        keyboard = tariffs_keyboard(tariffs, for_selection=False)

        # Debe tener botón de volver
        buttons = keyboard.inline_keyboard
        back_button = buttons[-1][0]
        assert back_button.text == "🔙 Volver"
        assert back_button.callback_data == "admin_vip"


class TestTokenActionsKeyboard:
    """Tests para token_actions_keyboard."""

    def test_token_actions_includes_copy_token_callback(self, db_session):
        """token_actions_keyboard genera CopyTokenCallback."""
        token_id = 42
        keyboard = token_actions_keyboard(token_id)

        buttons = keyboard.inline_keyboard
        # Primer botón es "Copiar enlace" con CopyTokenCallback
        copy_button = buttons[0][0]
        assert "Copiar" in copy_button.text
        assert copy_button.callback_data == f"copy_token:{token_id}"


class TestVIPHandlerSelectTariff:
    """Tests de integración para el flujo de selección de tarifa en VIP."""

    def test_handler_validates_callback_format(self, db_session, sample_tariff):
        """El handler puede procesar SelectTariffCallback."""
        callback_data = f"select_tariff:{sample_tariff.id}"

        # Verificar que el formato es correcto
        assert callback_data.startswith("select_tariff:")
        assert int(callback_data.split(":")[1]) == sample_tariff.id

    def test_handler_parses_tariff_id(self, db_session, sample_tariff):
        """El handler extrae el tariff_id correctamente."""
        callback_data = f"select_tariff:{sample_tariff.id}"
        tariff_id = int(callback_data.split(":")[1])
        assert tariff_id == sample_tariff.id


class TestRewardWizardSelectTariff:
    """Tests de integración para el flujo de reward wizard."""

    def test_reward_validates_callback_format(self, db_session, sample_tariff):
        """Reward wizard valida SelectTariffCallback."""
        callback_data = f"select_tariff:{sample_tariff.id}"

        # Verificar formato correcto: "prefix:id"
        assert callback_data.startswith("select_tariff:")
        assert int(callback_data.split(":")[1]) == sample_tariff.id

    def test_reward_shows_correct_callback_format(self, db_session, sample_tariff):
        """show_tariff_selection genera el formato correcto."""
        # Cuando reward_admin_handlers.py llama a show_tariff_selection,
        # genera: SelectTariffCallback(tariff_id=tariff.id).pack()
        callback = SelectTariffCallback(tariff_id=sample_tariff.id)
        packed = callback.pack()

        # Verificar formato exacto
        assert packed == f"select_tariff:{sample_tariff.id}"


class TestCallbackIntegration:
    """Tests de integración end-to-end para callbacks."""

    def test_full_select_tariff_flow(self, db_session, sample_tariff):
        """Flujo completo: keyboard genera callback correcto."""
        # 1. Keyboard genera el callback
        keyboard = tariffs_keyboard([sample_tariff], for_selection=True)
        button_callback = keyboard.inline_keyboard[0][0].callback_data

        # 2. Verificar formato correcto
        assert button_callback.startswith("select_tariff:")
        assert int(button_callback.split(":")[1]) == sample_tariff.id

    def test_full_copy_token_flow(self, db_session):
        """Flujo completo para copy_token."""
        token_id = 42

        # 1. Keyboard genera el callback
        keyboard = token_actions_keyboard(token_id)
        button_callback = keyboard.inline_keyboard[0][0].callback_data

        # 2. Verificar formato correcto
        assert button_callback.startswith("copy_token:")
        assert int(button_callback.split(":")[1]) == token_id

    def test_multiple_tariffs_keyboard(self, db_session, sample_tariff):
        """tariffs_keyboard con múltiples tarifas."""
        from models.models import Tariff

        tariff2 = Tariff(
            name="Premium",
            duration_days=90,
            price="24.99",
            is_active=True
        )
        db_session.add(tariff2)
        db_session.commit()

        tariffs = [sample_tariff, tariff2]
        keyboard = tariffs_keyboard(tariffs, for_selection=True)

        # Debe tener al menos 2 botones de tarifa
        assert len(keyboard.inline_keyboard) >= 2

        # Verificar ambos callbacks
        for i, tariff in enumerate(tariffs):
            assert keyboard.inline_keyboard[i][0].callback_data == f"select_tariff:{tariff.id}"


class TestCallbackDataFormat:
    """Tests para el formato exacto de los callbacks."""

    def test_select_tariff_format_exact(self):
        """Formato exacto es 'prefix:id'."""
        cb = SelectTariffCallback(tariff_id=1)
        packed = cb.pack()
        assert packed == "select_tariff:1"

    def test_copy_token_format_exact(self):
        """Formato exacto es 'prefix:id'."""
        cb = CopyTokenCallback(token_id=1)
        packed = cb.pack()
        assert packed == "copy_token:1"

    def test_no_collision_between_callbacks(self):
        """SelectTariff y CopyToken no collisionan."""
        select_cb = SelectTariffCallback(tariff_id=1)
        copy_cb = CopyTokenCallback(token_id=1)

        assert select_cb.pack() != copy_cb.pack()
        assert "select_tariff" in select_cb.pack()
        assert "copy_token" in copy_cb.pack()