"""
Tests de integración para Gamification Admin CallbackData migrateados.

Verifica que los CallbackData migrados funcionan correctamente:
- EditEmojiCallback
- ToggleEmojiCallback
"""
import pytest
from unittest.mock import MagicMock

from keyboards.callback_data import (
    EditEmojiCallback,
    ToggleEmojiCallback,
)


class TestEditEmojiCallback:
    """Tests para EditEmojiCallback - editar emoji existente."""

    def test_callback_packs_correctly(self):
        """EditEmojiCallback.pack() genera el string esperado."""
        emoji_id = 7
        callback = EditEmojiCallback(emoji_id=emoji_id)
        packed = callback.pack()

        # Formato esperado: "edit_emoji:7"
        assert packed == f"edit_emoji:{emoji_id}"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes emoji_id."""
        test_ids = [1, 5, 10, 50, 100, 999]
        for emoji_id in test_ids:
            callback = EditEmojiCallback(emoji_id=emoji_id)
            packed = callback.pack()
            assert packed == f"edit_emoji:{emoji_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable (API pública de aiogram)."""
        callback_filter = EditEmojiCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        emoji_id = 42
        callback = EditEmojiCallback(emoji_id=emoji_id)
        packed = callback.pack()

        prefix, emoji_id_str = packed.split(":")
        assert prefix == "edit_emoji"
        assert int(emoji_id_str) == emoji_id

    def test_extract_emoji_id_from_packed(self):
        """Valores pueden ser extraídos del packed string."""
        packed = "edit_emoji:99"
        prefix, emoji_id_str = packed.split(":")

        assert prefix == "edit_emoji"
        extracted_id = int(emoji_id_str)
        assert extracted_id == 99

    def test_callback_preserves_id_on_repack(self):
        """El ID se preserva al re-empaquetar."""
        original_id = 123
        callback = EditEmojiCallback(emoji_id=original_id)
        packed = callback.pack()

        # Recrear el callback desde el packed string
        prefix, emoji_id_str = packed.split(":")
        new_id = int(emoji_id_str)

        assert new_id == original_id


class TestToggleEmojiCallback:
    """Tests para ToggleEmojiCallback - activar/desactivar emoji."""

    def test_callback_packs_correctly(self):
        """ToggleEmojiCallback.pack() genera el string esperado."""
        emoji_id = 7
        callback = ToggleEmojiCallback(emoji_id=emoji_id)
        packed = callback.pack()

        # Formato esperado: "toggle_emoji:7"
        assert packed == f"toggle_emoji:{emoji_id}"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes emoji_id."""
        test_ids = [1, 5, 10, 50, 100, 999]
        for emoji_id in test_ids:
            callback = ToggleEmojiCallback(emoji_id=emoji_id)
            packed = callback.pack()
            assert packed == f"toggle_emoji:{emoji_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable (API pública de aiogram)."""
        callback_filter = ToggleEmojiCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        emoji_id = 42
        callback = ToggleEmojiCallback(emoji_id=emoji_id)
        packed = callback.pack()

        prefix, emoji_id_str = packed.split(":")
        assert prefix == "toggle_emoji"
        assert int(emoji_id_str) == emoji_id

    def test_extract_emoji_id_from_packed(self):
        """Valores pueden ser extraídos del packed string."""
        packed = "toggle_emoji:88"
        prefix, emoji_id_str = packed.split(":")

        assert prefix == "toggle_emoji"
        extracted_id = int(emoji_id_str)
        assert extracted_id == 88


class TestEmojiCallbackNoCollision:
    """Tests para verificar que los callbacks de emoji no colisionan."""

    def test_edit_and_toggle_have_different_prefixes(self):
        """EditEmoji y ToggleEmoji tienen prefixes diferentes."""
        edit_callback = EditEmojiCallback(emoji_id=1)
        toggle_callback = ToggleEmojiCallback(emoji_id=1)

        edit_packed = edit_callback.pack()
        toggle_packed = toggle_callback.pack()

        assert edit_packed != toggle_packed
        assert "edit_emoji" in edit_packed
        assert "toggle_emoji" in toggle_packed

    def test_same_id_different_callbacks_different_output(self):
        """Mismo ID genera salida diferente para cada tipo."""
        same_emoji_id = 42

        edit_callback = EditEmojiCallback(emoji_id=same_emoji_id)
        toggle_callback = ToggleEmojiCallback(emoji_id=same_emoji_id)

        assert edit_callback.pack() != toggle_callback.pack()

    def test_different_ids_maintain_uniqueness(self):
        """IDs diferentes mantienen uniqueness."""
        test_pairs = [(1, 2), (10, 20), (100, 200)]

        for edit_id, toggle_id in test_pairs:
            edit_callback = EditEmojiCallback(emoji_id=edit_id)
            toggle_callback = ToggleEmojiCallback(emoji_id=toggle_id)

            edit_packed = edit_callback.pack()
            toggle_packed = toggle_callback.pack()

            # Verificar que no hay colisión cuando IDs son distintos
            assert edit_packed != toggle_packed


class TestEmojiCallbackIntegration:
    """Tests de integración para uso real con handlers."""

    def test_callback_data_matches_handler_usage(self):
        """El callback genera el mismo formato usado en el handler."""
        # Basado en el uso en gamification_admin_handlers.py
        emoji_id = 123
        expected_packed = f"edit_emoji:{emoji_id}"
        actual_packed = EditEmojiCallback(emoji_id=emoji_id).pack()

        assert actual_packed == expected_packed

    def test_toggle_callback_data_matches_handler_usage(self):
        """El callback genera el mismo formato usado para toggle."""
        # Basado en el uso en gamification_admin_handlers.py
        emoji_id = 456
        expected_packed = f"toggle_emoji:{emoji_id}"
        actual_packed = ToggleEmojiCallback(emoji_id=emoji_id).pack()

        assert actual_packed == expected_packed