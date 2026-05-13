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
    ToggleReactionCallback,
    BroadcastProtectCallback,
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

    def test_no_prefix_collision_between_broadcasts(self):
        """No hay colisión de prefijos entre los 3 callbacks."""
        callbacks = [
            BroadcastChannelCallback(channel_id=123),
            ToggleReactionCallback(emoji_id=5),
            BroadcastProtectCallback(action="yes"),
        ]

        packed_strings = [cb.pack() for cb in callbacks]
        unique_prefixes = set(packed.split(":")[0] for packed in packed_strings)

        assert len(unique_prefixes) == 3

    def test_no_packed_value_collision(self):
        """No hay colisión de valores enteros entre callbacks."""
        test_value = 12345

        # Mismo valor en diferentes callbacks debe dar strings distintos
        cb1 = BroadcastChannelCallback(channel_id=test_value)
        cb2 = ToggleReactionCallback(emoji_id=test_value)

        assert cb1.pack() != cb2.pack()
        assert cb1.pack() == f"bc_channel:{test_value}"
        assert cb2.pack() == f"bc_reaction:{test_value}"