"""
Tests de integración para callbacks Broadcast migrateados.

Verifica que los CallbackData migrados funcionan correctamente:
- BroadcastChannelCallback
- ToggleReactionCallback
- BroadcastProtectCallback
"""
import pytest
from unittest.mock import MagicMock

from keyboards.callback_data import (
    BroadcastChannelCallback,
    BroadcastProtectCallback,
    ReactionCallback,
    ToggleExtraButtonCallback,
    ToggleReactionCallback,
)


class TestBroadcastChannelCallback:
    """Tests para BroadcastChannelCallback."""

    def test_callback_packs_correctly(self):
        """BroadcastChannelCallback.pack() genera el string esperado."""
        channel_id = -1001234567890
        callback = BroadcastChannelCallback(channel_id=channel_id)
        packed = callback.pack()

        assert packed == f"bc_channel:{channel_id}"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes channel_id."""
        test_ids = [-1001234567890, -1000987654321, -1001111111111, 123]
        for channel_id in test_ids:
            callback = BroadcastChannelCallback(channel_id=channel_id)
            packed = callback.pack()
            assert packed == f"bc_channel:{channel_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable (API pública de aiogram)."""
        callback_filter = BroadcastChannelCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        channel_id = -1001234567890
        callback = BroadcastChannelCallback(channel_id=channel_id)
        packed = callback.pack()

        prefix, channel_id_str = packed.split(":")
        assert prefix == "bc_channel"
        assert int(channel_id_str) == channel_id

    def test_extract_channel_id_from_packed(self):
        """Valores pueden ser extraídos del packed string."""
        packed = "bc_channel:-1001234567890"
        prefix, channel_id_str = packed.split(":")

        assert prefix == "bc_channel"
        extracted_id = int(channel_id_str)
        assert extracted_id == -1001234567890


class TestToggleReactionCallback:
    """Tests para ToggleReactionCallback."""

    def test_callback_packs_correctly(self):
        """ToggleReactionCallback.pack() genera el string esperado."""
        emoji_id = 5
        callback = ToggleReactionCallback(emoji_id=emoji_id)
        packed = callback.pack()

        assert packed == f"bc_reaction:{emoji_id}"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes emoji_id."""
        test_ids = [1, 2, 3, 10, 99]
        for emoji_id in test_ids:
            callback = ToggleReactionCallback(emoji_id=emoji_id)
            packed = callback.pack()
            assert packed == f"bc_reaction:{emoji_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = ToggleReactionCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        emoji_id = 42
        callback = ToggleReactionCallback(emoji_id=emoji_id)
        packed = callback.pack()

        prefix, emoji_id_str = packed.split(":")
        assert prefix == "bc_reaction"
        assert int(emoji_id_str) == emoji_id

    def test_extract_emoji_id_from_packed(self):
        """Valores pueden ser extraídos del packed string."""
        packed = "bc_reaction:7"
        prefix, emoji_id_str = packed.split(":")

        assert prefix == "bc_reaction"
        extracted_id = int(emoji_id_str)
        assert extracted_id == 7


class TestBroadcastProtectCallback:
    """Tests para BroadcastProtectCallback."""

    def test_callback_packs_yes_action(self):
        """BroadcastProtectCallback.pack() con action='yes'."""
        callback = BroadcastProtectCallback(action="yes")
        packed = callback.pack()

        assert packed == "bc_protect:yes"

    def test_callback_packs_no_action(self):
        """BroadcastProtectCallback.pack() con action='no'."""
        callback = BroadcastProtectCallback(action="no")
        packed = callback.pack()

        assert packed == "bc_protect:no"

    def test_callback_packs_different_actions(self):
        """Funciona con diferentes actions."""
        test_actions = ["yes", "no", "confirm", "cancel"]
        for action in test_actions:
            callback = BroadcastProtectCallback(action=action)
            packed = callback.pack()
            assert packed == f"bc_protect:{action}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = BroadcastProtectCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        action = "yes"
        callback = BroadcastProtectCallback(action=action)
        packed = callback.pack()

        prefix, action_str = packed.split(":")
        assert prefix == "bc_protect"
        assert action_str == action

    def test_extract_action_from_packed(self):
        """Action puede ser extraída del packed string."""
        packed = "bc_protect:yes"
        prefix, action_str = packed.split(":")

        assert prefix == "bc_protect"
        assert action_str == "yes"


class TestReactionCallback:
    """Tests para ReactionCallback (botones de reacción en broadcasts enviados)."""

    def test_callback_packs_correctly(self):
        """ReactionCallback.pack() genera el formato react:broadcast_id:emoji_id."""
        packed = ReactionCallback(broadcast_id=5, emoji_id=3).pack()
        assert packed == "react:5:3"

    def test_callback_unpack_round_trip(self):
        """pack/unpack conserva broadcast_id y emoji_id."""
        original = ReactionCallback(broadcast_id=42, emoji_id=7)
        packed = original.pack()
        unpacked = ReactionCallback.unpack(packed)
        assert unpacked.broadcast_id == 42
        assert unpacked.emoji_id == 7

    def test_build_send_reaction_markup_uses_reaction_callback(self):
        """Helper de envío genera callback_data compatible con handle_reaction."""
        from handlers.broadcast_handlers import build_send_reaction_markup

        emoji = MagicMock()
        emoji.id = 3
        emoji.emoji = "💋"
        markup = build_send_reaction_markup(99, [3], lambda _eid: emoji)
        button = markup.inline_keyboard[0][0]
        unpacked = ReactionCallback.unpack(button.callback_data)
        assert unpacked.broadcast_id == 99
        assert unpacked.emoji_id == 3


class TestBroadcastCallbacksNoCollisions:
    """Tests para verificar que no hay colisiones entre callbacks."""

    def test_bc_channel_unique_prefix(self):
        """BroadcastChannelCallback usa prefix único."""
        test_channel_id = 12345
        callback = BroadcastChannelCallback(channel_id=test_channel_id)
        packed = callback.pack()

        assert packed.startswith("bc_channel:")
        assert "bc_reaction" not in packed
        assert "bc_protect" not in packed

    def test_bc_reaction_unique_prefix(self):
        """ToggleReactionCallback usa prefix único."""
        test_emoji_id = 7
        callback = ToggleReactionCallback(emoji_id=test_emoji_id)
        packed = callback.pack()

        assert packed.startswith("bc_reaction:")
        assert "bc_channel" not in packed
        assert "bc_protect" not in packed

    def test_bc_protect_unique_prefix(self):
        """BroadcastProtectCallback usa prefix único."""
        callback = BroadcastProtectCallback(action="yes")
        packed = callback.pack()

        assert packed.startswith("bc_protect:")
        assert "bc_channel" not in packed
        assert "bc_reaction" not in packed

    def test_bc_extra_unique_prefix(self):
        """ToggleExtraButtonCallback usa prefix único bc_extra."""
        cb0 = ToggleExtraButtonCallback(button_id=0)
        cb5 = ToggleExtraButtonCallback(button_id=5)
        assert cb0.pack().startswith("bc_extra:")
        assert cb5.pack().startswith("bc_extra:")
        assert "bc_channel" not in cb0.pack()
        assert "bc_reaction" not in cb5.pack()
        assert "bc_protect" not in cb0.pack()

    def test_no_prefix_collision_between_broadcasts(self):
        """No hay colisión de prefijos entre los callbacks broadcast (incluye bc_extra)."""
        callbacks = [
            BroadcastChannelCallback(channel_id=123),
            ToggleReactionCallback(emoji_id=5),
            BroadcastProtectCallback(action="yes"),
            ToggleExtraButtonCallback(button_id=0),
        ]

        packed_strings = [cb.pack() for cb in callbacks]
        unique_prefixes = set(packed.split(":")[0] for packed in packed_strings)

        assert len(unique_prefixes) == 4

    def test_no_packed_value_collision(self):
        """No hay colisión de valores enteros entre callbacks."""
        test_value = 12345

        # Mismo valor en diferentes callbacks debe dar strings distintos
        cb1 = BroadcastChannelCallback(channel_id=test_value)
        cb2 = ToggleReactionCallback(emoji_id=test_value)

        assert cb1.pack() != cb2.pack()
        assert cb1.pack() == f"bc_channel:{test_value}"
        assert cb2.pack() == f"bc_reaction:{test_value}"
class TestBroadcastPureHelpers:
    """Tests para helpers puros de markup combinado (reacciones + botón extra URL)."""

    def test_build_broadcast_send_markup_reactions_only(self):
        """Solo emojis → una fila con ReactionCallbacks, sin URL."""
        from handlers.broadcast_handlers import build_broadcast_send_markup
        from unittest.mock import MagicMock

        mock_emoji = MagicMock(id=1, emoji="💋")
        get_emoji = lambda eid: mock_emoji if eid == 1 else None
        markup = build_broadcast_send_markup(
            broadcast_id=42,
            selected_emoji_ids=[1],
            extra_button=None,
            get_emoji=get_emoji,
        )
        assert markup is not None
        assert len(markup.inline_keyboard) == 1
        btn = markup.inline_keyboard[0][0]
        assert btn.text == "💋"
        assert btn.callback_data.startswith("react:")

    def test_build_broadcast_send_markup_extra_only(self):
        """Sin emojis, con extra → fila única con url (sin callback)."""
        from handlers.broadcast_handlers import build_broadcast_send_markup

        class FakeBtn:
            label = "🔗 Más"
            url = "https://t.me/kinky"

        markup = build_broadcast_send_markup(
            broadcast_id=42,
            selected_emoji_ids=[],
            extra_button=FakeBtn(),
            get_emoji=lambda eid: None,
        )
        assert markup is not None
        assert len(markup.inline_keyboard) == 1
        btn = markup.inline_keyboard[0][0]
        assert btn.text == "🔗 Más"
        assert btn.url == "https://t.me/kinky"
        # no callback_data for url buttons
        assert getattr(btn, "callback_data", None) in (None, "")

    def test_build_broadcast_send_markup_combined(self):
        """Emojis + extra → 2 filas: reacciones (callbacks) + url."""
        from handlers.broadcast_handlers import build_broadcast_send_markup
        from unittest.mock import MagicMock

        mock_emoji = MagicMock(id=9, emoji="❤️")
        get_emoji = lambda eid: mock_emoji if eid == 9 else None

        class FakeBtn:
            label = "📎 Ver"
            url = "https://t.me/extra"

        markup = build_broadcast_send_markup(
            broadcast_id=99,
            selected_emoji_ids=[9],
            extra_button=FakeBtn(),
            get_emoji=get_emoji,
        )
        assert markup is not None
        assert len(markup.inline_keyboard) == 2
        # row 0: reaction
        assert markup.inline_keyboard[0][0].callback_data.startswith("react:")
        # row 1: url
        assert markup.inline_keyboard[1][0].url == "https://t.me/extra"

    def test_build_broadcast_send_markup_none(self):
        """Sin nada → None."""
        from handlers.broadcast_handlers import build_broadcast_send_markup
        markup = build_broadcast_send_markup(
            broadcast_id=1,
            selected_emoji_ids=[],
            extra_button=None,
            get_emoji=lambda eid: None,
        )
        assert markup is None
