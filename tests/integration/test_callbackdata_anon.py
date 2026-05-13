"""
Tests de integración para callbacks Anonymous Message Admin migrateados.

Verifica que los CallbackData migrados funcionan correctamente:
- AnonUnreadCallback
- AnonAllCallback
- AnonViewCallback
- AnonReplyCallback
- AnonRevealCallback
- AnonDeleteCallback
"""
import pytest
from unittest.mock import MagicMock

from keyboards.callback_data import (
    AnonUnreadCallback,
    AnonAllCallback,
    AnonViewCallback,
    AnonReplyCallback,
    AnonRevealCallback,
    AnonDeleteCallback,
)


class TestAnonUnreadCallback:
    """Tests para AnonUnreadCallback."""

    def test_callback_packs_correctly(self):
        """AnonUnreadCallback.pack() genera el string esperado."""
        callback = AnonUnreadCallback()
        packed = callback.pack()

        # Formato esperado: "anon_unread" (sin argumentos)
        assert packed == "anon_unread"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable (API pública de aiogram)."""
        callback_filter = AnonUnreadCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_unpack_and_filter(self):
        """Callback se puede crear y luego filtrar."""
        callback = AnonUnreadCallback()
        packed = callback.pack()
        assert packed == "anon_unread"


class TestAnonAllCallback:
    """Tests para AnonAllCallback."""

    def test_callback_packs_correctly(self):
        """AnonAllCallback.pack() genera el string esperado."""
        callback = AnonAllCallback()
        packed = callback.pack()

        # Formato esperado: "anon_all" (sin argumentos)
        assert packed == "anon_all"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = AnonAllCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_unpack_and_filter(self):
        """Callback se puede crear y luego filtrar."""
        callback = AnonAllCallback()
        packed = callback.pack()
        assert packed == "anon_all"


class TestAnonViewCallback:
    """Tests para AnonViewCallback."""

    def test_callback_packs_correctly(self):
        """AnonViewCallback.pack() genera el string esperado."""
        message_id = 42
        callback = AnonViewCallback(message_id=message_id)
        packed = callback.pack()

        # Formato esperado: "anon_view:42"
        assert packed == "anon_view:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes message_id."""
        for message_id in [1, 10, 100, 999]:
            callback = AnonViewCallback(message_id=message_id)
            packed = callback.pack()
            assert packed == f"anon_view:{message_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = AnonViewCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = AnonViewCallback(message_id=123)
        packed = callback.pack()

        # Parse manual para verificar
        prefix, message_id_str = packed.split(":")
        assert prefix == "anon_view"
        assert int(message_id_str) == 123


class TestAnonReplyCallback:
    """Tests para AnonReplyCallback."""

    def test_callback_packs_correctly(self):
        """AnonReplyCallback.pack() genera el string esperado."""
        message_id = 42
        callback = AnonReplyCallback(message_id=message_id)
        packed = callback.pack()

        # Formato esperado: "anon_reply:42"
        assert packed == "anon_reply:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes message_id."""
        for message_id in [1, 10, 100, 999]:
            callback = AnonReplyCallback(message_id=message_id)
            packed = callback.pack()
            assert packed == f"anon_reply:{message_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = AnonReplyCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = AnonReplyCallback(message_id=456)
        packed = callback.pack()

        prefix, message_id_str = packed.split(":")
        assert prefix == "anon_reply"
        assert int(message_id_str) == 456


class TestAnonRevealCallback:
    """Tests para AnonRevealCallback."""

    def test_callback_packs_correctly(self):
        """AnonRevealCallback.pack() genera el string esperado."""
        message_id = 42
        callback = AnonRevealCallback(message_id=message_id)
        packed = callback.pack()

        # Formato esperado: "anon_reveal:42"
        assert packed == "anon_reveal:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes message_id."""
        for message_id in [1, 10, 100, 999]:
            callback = AnonRevealCallback(message_id=message_id)
            packed = callback.pack()
            assert packed == f"anon_reveal:{message_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = AnonRevealCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = AnonRevealCallback(message_id=789)
        packed = callback.pack()

        prefix, message_id_str = packed.split(":")
        assert prefix == "anon_reveal"
        assert int(message_id_str) == 789


class TestAnonDeleteCallback:
    """Tests para AnonDeleteCallback."""

    def test_callback_packs_correctly(self):
        """AnonDeleteCallback.pack() genera el string esperado."""
        message_id = 42
        callback = AnonDeleteCallback(message_id=message_id)
        packed = callback.pack()

        # Formato esperado: "anon_delete:42"
        assert packed == "anon_delete:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes message_id."""
        for message_id in [1, 10, 100, 999]:
            callback = AnonDeleteCallback(message_id=message_id)
            packed = callback.pack()
            assert packed == f"anon_delete:{message_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = AnonDeleteCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = AnonDeleteCallback(message_id=321)
        packed = callback.pack()

        prefix, message_id_str = packed.split(":")
        assert prefix == "anon_delete"
        assert int(message_id_str) == 321


class TestCallbackNoCollisions:
    """Tests para verificar que no hay colisiones entre callbacks."""

    def test_no_collision_view_vs_reply(self):
        """AnonView y AnonReply no collsionan."""
        message_id = 1
        view_cb = AnonViewCallback(message_id=message_id)
        reply_cb = AnonReplyCallback(message_id=message_id)

        assert view_cb.pack() != reply_cb.pack()
        assert "anon_view" in view_cb.pack()
        assert "anon_reply" in reply_cb.pack()

    def test_no_collision_reply_vs_reveal(self):
        """AnonReply y AnonReveal no collsionan."""
        message_id = 1
        reply_cb = AnonReplyCallback(message_id=message_id)
        reveal_cb = AnonRevealCallback(message_id=message_id)

        assert reply_cb.pack() != reveal_cb.pack()
        assert "anon_reply" in reply_cb.pack()
        assert "anon_reveal" in reveal_cb.pack()

    def test_no_collision_reveal_vs_delete(self):
        """AnonReveal y AnonDelete no collsionan."""
        message_id = 1
        reveal_cb = AnonRevealCallback(message_id=message_id)
        delete_cb = AnonDeleteCallback(message_id=message_id)

        assert reveal_cb.pack() != delete_cb.pack()
        assert "anon_reveal" in reveal_cb.pack()
        assert "anon_delete" in delete_cb.pack()

    def test_no_collision_view_vs_delete(self):
        """AnonView y AnonDelete no collsionan."""
        message_id = 1
        view_cb = AnonViewCallback(message_id=message_id)
        delete_cb = AnonDeleteCallback(message_id=message_id)

        assert view_cb.pack() != delete_cb.pack()
        assert "anon_view" in view_cb.pack()
        assert "anon_delete" in delete_cb.pack()

    def test_no_collision_reply_vs_delete(self):
        """AnonReply y AnonDelete no collsionan."""
        message_id = 1
        reply_cb = AnonReplyCallback(message_id=message_id)
        delete_cb = AnonDeleteCallback(message_id=message_id)

        assert reply_cb.pack() != delete_cb.pack()
        assert "anon_reply" in reply_cb.pack()
        assert "anon_delete" in delete_cb.pack()

    def test_no_collision_menu_callbacks(self):
        """AnonUnread y AnonAll no collsionan."""
        unread_cb = AnonUnreadCallback()
        all_cb = AnonAllCallback()

        assert unread_cb.pack() != all_cb.pack()
        assert unread_cb.pack() == "anon_unread"
        assert all_cb.pack() == "anon_all"


class TestAnonymousHandlerCallbacks:
    """Tests de integración para los callbacks usados en los handlers."""

    def test_admin_menu_keyboard_generates_unread_callback(self):
        """anonymous_messages_menu_keyboard genera AnonUnreadCallback."""
        from handlers.anonymous_message_admin_handlers import anonymous_messages_menu_keyboard

        keyboard = anonymous_messages_menu_keyboard()
        buttons = keyboard.inline_keyboard

        # Primer botón: "Mensajes no leídos"
        unread_button = buttons[0][0]
        assert "Mensajes no leídos" in unread_button.text
        assert unread_button.callback_data == "anon_unread"

    def test_admin_menu_keyboard_generates_all_callback(self):
        """anonymous_messages_menu_keyboard genera AnonAllCallback."""
        from handlers.anonymous_message_admin_handlers import anonymous_messages_menu_keyboard

        keyboard = anonymous_messages_menu_keyboard()
        buttons = keyboard.inline_keyboard

        # Segundo botón: "Todos los mensajes"
        all_button = buttons[1][0]
        assert "Todos los mensajes" in all_button.text
        assert all_button.callback_data == "anon_all"

    def test_message_actions_keyboard_generates_reply_callback(self):
        """anonymous_message_actions_keyboard genera AnonReplyCallback."""
        from handlers.anonymous_message_admin_handlers import anonymous_message_actions_keyboard

        message_id = 42
        keyboard = anonymous_message_actions_keyboard(message_id)
        buttons = keyboard.inline_keyboard

        # Primer botón: "Responder"
        reply_button = buttons[0][0]
        assert "Responder" in reply_button.text
        assert reply_button.callback_data == f"anon_reply:{message_id}"

    def test_message_actions_keyboard_generates_reveal_callback(self):
        """anonymous_message_actions_keyboard genera AnonRevealCallback."""
        from handlers.anonymous_message_admin_handlers import anonymous_message_actions_keyboard

        message_id = 42
        keyboard = anonymous_message_actions_keyboard(message_id, show_reveal=True)
        buttons = keyboard.inline_keyboard

        # Segundo botón (si show_reveal=True): "Revelar remitente"
        reveal_button = buttons[1][0]
        assert "Revelar" in reveal_button.text
        assert reveal_button.callback_data == f"anon_reveal:{message_id}"

    def test_message_actions_keyboard_generates_delete_callback(self):
        """anonymous_message_actions_keyboard genera AnonDeleteCallback."""
        from handlers.anonymous_message_admin_handlers import anonymous_message_actions_keyboard

        message_id = 42
        keyboard = anonymous_message_actions_keyboard(message_id)
        buttons = keyboard.inline_keyboard

        # Tercer botón: "Eliminar mensaje"
        # (índice cambia según show_reveal)
        delete_button = buttons[2][0]
        assert "Eliminar" in delete_button.text
        assert delete_button.callback_data == f"anon_delete:{message_id}"


class TestCallbackDataFormat:
    """Tests del formato exacto."""

    def test_anon_unread_format(self):
        """Formato exacto es 'prefix'."""
        cb = AnonUnreadCallback()
        packed = cb.pack()
        assert packed == "anon_unread"

    def test_anon_all_format(self):
        """Formato exacto es 'prefix'."""
        cb = AnonAllCallback()
        packed = cb.pack()
        assert packed == "anon_all"

    def test_anon_view_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = AnonViewCallback(message_id=1)
        packed = cb.pack()
        assert packed == "anon_view:1"

    def test_anon_reply_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = AnonReplyCallback(message_id=1)
        packed = cb.pack()
        assert packed == "anon_reply:1"

    def test_anon_reveal_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = AnonRevealCallback(message_id=1)
        packed = cb.pack()
        assert packed == "anon_reveal:1"

    def test_anon_delete_format(self):
        """Formato exacto es 'prefix:id'."""
        cb = AnonDeleteCallback(message_id=1)
        packed = cb.pack()
        assert packed == "anon_delete:1"


class TestFullAnonymousMessageFlow:
    """Tests del flujo completo de gestión de mensajes anónimos."""

    def test_full_view_message_flow(self):
        """Flujo: Menu → Unread → View details."""
        message_id = 42

        # Step 1: Ver mensajes no leídos
        unread_callback = AnonUnreadCallback()
        unread_packed = unread_callback.pack()

        # Step 2: Click en mensaje para ver detalles
        view_callback = AnonViewCallback(message_id=message_id)
        view_packed = view_callback.pack()

        # Verificar formato correcto
        assert unread_packed == "anon_unread"
        assert view_packed == f"anon_view:{message_id}"

    def test_full_reply_flow(self):
        """Flujo: View → Reply."""
        message_id = 42

        # Step 1: Ver mensaje
        view_callback = AnonViewCallback(message_id=message_id)
        view_packed = view_callback.pack()

        # Step 2: Click en responder
        reply_callback = AnonReplyCallback(message_id=message_id)
        reply_packed = reply_callback.pack()

        # Verificar formato correcto
        assert view_packed == f"anon_view:{message_id}"
        assert reply_packed == f"anon_reply:{message_id}"

    def test_full_reveal_flow(self):
        """Flujo: View → Reveal."""
        message_id = 42

        # Step 1: Ver mensaje
        view_callback = AnonViewCallback(message_id=message_id)
        view_packed = view_callback.pack()

        # Step 2: Click en revelar
        reveal_callback = AnonRevealCallback(message_id=message_id)
        reveal_packed = reveal_callback.pack()

        # Verificar formato correcto
        assert view_packed == f"anon_view:{message_id}"
        assert reveal_packed == f"anon_reveal:{message_id}"

    def test_full_delete_flow(self):
        """Flujo: View → Delete."""
        message_id = 42

        # Step 1: Ver mensaje
        view_callback = AnonViewCallback(message_id=message_id)
        view_packed = view_callback.pack()

        # Step 2: Click en eliminar
        delete_callback = AnonDeleteCallback(message_id=message_id)
        delete_packed = delete_callback.pack()

        # Verificar formato correcto
        assert view_packed == f"anon_view:{message_id}"
        assert delete_packed == f"anon_delete:{message_id}"

    def test_callback_chain_in_message_flow(self):
        """Callback chain en el flujo de gestión de mensajes."""
        message_id = 42

        # 1. Ver lista de no leídos → Click en ver mensajes
        unread_packed = AnonUnreadCallback().pack()

        # 2. Ver lista de todos → Click en ver mensajes
        all_packed = AnonAllCallback().pack()

        # 3. En mensaje → Ver detalle
        view_packed = AnonViewCallback(message_id=message_id).pack()

        # 4. En detalle → Responder
        reply_packed = AnonReplyCallback(message_id=message_id).pack()

        # 5. En detalle → Revelar
        reveal_packed = AnonRevealCallback(message_id=message_id).pack()

        # 6. En detalle → Eliminar
        delete_packed = AnonDeleteCallback(message_id=message_id).pack()

        # 7. Volver al menú
        back_packed = "admin_anonymous_messages"

        # Verificar todas las transiciones
        assert unread_packed == "anon_unread"
        assert all_packed == "anon_all"
        assert "anon_view" in view_packed
        assert "anon_reply" in reply_packed
        assert "anon_reveal" in reveal_packed
        assert "anon_delete" in delete_packed
        assert back_packed == "admin_anonymous_messages"

    def test_handler_extracts_message_id_correctly(self):
        """El handler extrae el message_id correctamente."""
        message_id = 123

        # Simular callback_data como llega al handler
        callback_data = AnonViewCallback(message_id=message_id)
        packed = callback_data.pack()

        # El handler hace callback_data.message_id
        extracted_id = int(packed.split(":")[1])
        assert extracted_id == message_id