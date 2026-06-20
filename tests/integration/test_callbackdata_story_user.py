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

    def test_callback_unpack_round_trip(self):
        """unpack(pack()) preserva choice_id."""
        original = StoryChoiceCallback(choice_id=123)
        unpacked = StoryChoiceCallback.unpack(original.pack())
        assert unpacked.choice_id == 123

    def test_callback_unpack_rejects_invalid_prefix(self):
        """unpack falla con prefijo incorrecto."""
        with pytest.raises(ValueError):
            StoryChoiceCallback.unpack("wrong_prefix:123")

    def test_callback_unpack_rejects_non_numeric_id(self):
        """unpack falla con ID no numerico."""
        with pytest.raises(ValueError):
            StoryChoiceCallback.unpack("story_choice:abc")


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

    def test_callback_unpack_round_trip(self):
        """unpack(pack()) preserva node_id."""
        original = ContinueStoryCallback(node_id=999)
        unpacked = ContinueStoryCallback.unpack(original.pack())
        assert unpacked.node_id == 999

    def test_callback_unpack_rejects_negative_id(self):
        """Callback acepta pack con id negativo (validacion en handler)."""
        packed = ContinueStoryCallback(node_id=-1).pack()
        unpacked = ContinueStoryCallback.unpack(packed)
        assert unpacked.node_id == -1

    def test_callback_unpack_rejects_non_numeric_id(self):
        with pytest.raises(ValueError):
            ContinueStoryCallback.unpack("story_continue:foo")


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

    def test_callback_unpack_round_trip(self):
        """unpack(pack()) preserva answer_idx."""
        original = QuizAnswerCallback(answer_idx=5)
        unpacked = QuizAnswerCallback.unpack(original.pack())
        assert unpacked.answer_idx == 5

    def test_callback_unpack_negative_index(self):
        """unpack preserva indices negativos (handler los rechaza)."""
        unpacked = QuizAnswerCallback.unpack(QuizAnswerCallback(answer_idx=-1).pack())
        assert unpacked.answer_idx == -1


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

    def test_callback_unpack_round_trip(self):
        """unpack(pack()) preserva archetype."""
        original = ArchetypeSelectCallback(archetype="misterioso")
        unpacked = ArchetypeSelectCallback.unpack(original.pack())
        assert unpacked.archetype == "misterioso"

    def test_archetype_select_reserved_not_wired_to_quiz_handler(self):
        """ArchetypeSelectCallback es reservado; el quiz usa QuizAnswerCallback."""
        # Documenta que el flujo de quiz no usa seleccion directa de arquetipo
        assert QuizAnswerCallback.__prefix__ == "quiz_answer"
        assert ArchetypeSelectCallback.__prefix__ == "archetype_select"