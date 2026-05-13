"""
Tests de integración para Story User CallbackData migrateados.

Verifica que los CallbackData migrados funcionan correctamente:
- StoryChoiceCallback
- ContinueStoryCallback
- QuizAnswerCallback
- ArchetypeSelectCallback
"""
import pytest

from keyboards.callback_data import (
    StoryChoiceCallback,
    ContinueStoryCallback,
    QuizAnswerCallback,
    ArchetypeSelectCallback,
)


class TestStoryChoiceCallback:
    """Tests para StoryChoiceCallback."""

    def test_callback_packs_correctly(self):
        """StoryChoiceCallback.pack() genera el string esperado."""
        choice_id = 42
        callback = StoryChoiceCallback(choice_id=choice_id)
        packed = callback.pack()

        # Formato esperado: "story_choice:42"
        assert packed == "story_choice:42"

    def test_callback_packs_with_different_ids(self):
        """Funciona con diferentes choice_id."""
        for choice_id in [1, 10, 100, 999]:
            callback = StoryChoiceCallback(choice_id=choice_id)
            packed = callback.pack()
            assert packed == f"story_choice:{choice_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable (API pública de aiogram)."""
        callback_filter = StoryChoiceCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = StoryChoiceCallback(choice_id=123)
        packed = callback.pack()

        # Parse manual para verificar
        prefix, choice_id_str = packed.split(":")
        assert prefix == "story_choice"
        assert int(choice_id_str) == 123


class TestContinueStoryCallback:
    """Tests para ContinueStoryCallback."""

    def test_callback_packs_correctly(self):
        """ContinueStoryCallback.pack() genera el string esperado."""
        node_id = 7
        callback = ContinueStoryCallback(node_id=node_id)
        packed = callback.pack()

        # Formato esperado: "story_continue:7"
        assert packed == "story_continue:7"

    def test_callback_packs_with_different_node_ids(self):
        """Funciona con diferentes node_id."""
        for node_id in [1, 5, 50, 500]:
            callback = ContinueStoryCallback(node_id=node_id)
            packed = callback.pack()
            assert packed == f"story_continue:{node_id}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = ContinueStoryCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = ContinueStoryCallback(node_id=999)
        packed = callback.pack()

        prefix, node_id_str = packed.split(":")
        assert prefix == "story_continue"
        assert int(node_id_str) == 999


class TestQuizAnswerCallback:
    """Tests para QuizAnswerCallback."""

    def test_callback_packs_correctly(self):
        """QuizAnswerCallback.pack() genera el string esperado."""
        answer_idx = 3
        callback = QuizAnswerCallback(answer_idx=answer_idx)
        packed = callback.pack()

        # Formato esperado: "quiz_answer:3"
        assert packed == "quiz_answer:3"

    def test_callback_packs_with_all_valid_indices(self):
        """Funciona con todos los índices válidos (0-5 para el quiz de 6 opciones)."""
        for answer_idx in range(6):
            callback = QuizAnswerCallback(answer_idx=answer_idx)
            packed = callback.pack()
            assert packed == f"quiz_answer:{answer_idx}"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = QuizAnswerCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = QuizAnswerCallback(answer_idx=5)
        packed = callback.pack()

        prefix, answer_idx_str = packed.split(":")
        assert prefix == "quiz_answer"
        assert int(answer_idx_str) == 5


class TestArchetypeSelectCallback:
    """Tests para ArchetypeSelectCallback."""

    def test_callback_packs_correctly_seductor(self):
        """ArchetypeSelectCallback.pack() genera el string esperado para seductor."""
        archetype = "seductor"
        callback = ArchetypeSelectCallback(archetype=archetype)
        packed = callback.pack()

        # Formato esperado: "archetype_select:seductor"
        assert packed == "archetype_select:seductor"

    def test_callback_packs_correctly_explorador(self):
        """Funciona para el arquetipo explorador."""
        archetype = "explorador"
        callback = ArchetypeSelectCallback(archetype=archetype)
        packed = callback.pack()

        assert packed == "archetype_select:explorador"

    def test_callback_packs_correctly_intrepido(self):
        """Funciona para el arquetipo intrépido."""
        archetype = "intrepido"
        callback = ArchetypeSelectCallback(archetype=archetype)
        packed = callback.pack()

        assert packed == "archetype_select:intrepido"

    def test_callback_packs_correctly_misterioso(self):
        """Funciona para el arquetipo misterioso."""
        archetype = "misterioso"
        callback = ArchetypeSelectCallback(archetype=archetype)
        packed = callback.pack()

        assert packed == "archetype_select:misterioso"

    def test_callback_packs_correctly_observer(self):
        """Funciona para el arquetipo observador."""
        archetype = "observer"
        callback = ArchetypeSelectCallback(archetype=archetype)
        packed = callback.pack()

        assert packed == "archetype_select:observer"

    def test_callback_packs_correctly_devoto(self):
        """Funciona para el arquetipo devoto."""
        archetype = "devoto"
        callback = ArchetypeSelectCallback(archetype=archetype)
        packed = callback.pack()

        assert packed == "archetype_select:devoto"

    def test_callback_filter_is_callable(self):
        """El filter es un objeto callable."""
        callback_filter = ArchetypeSelectCallback.filter()
        assert callback_filter is not None
        assert callable(callback_filter)

    def test_callback_parses_correctly(self):
        """Callback se puede parsear correctamente."""
        callback = ArchetypeSelectCallback(archetype="misterioso")
        packed = callback.pack()

        prefix, archetype_str = packed.split(":")
        assert prefix == "archetype_select"
        assert archetype_str == "misterioso"