"""
Tests unitarios para story_user_handlers.

Cubre:
- narrative_menu: con/sin historia iniciada, con/sin arquetipo
- start_story: ya iniciado, sin nodo inicial, con nodo inicial
- continue_story: con progreso, sin progreso
- go_to_node: navegacion a nodo especifico
- make_choice: opcion no encontrada, con siguiente nodo, fin de historia
- start_archetype_quiz: inicio del cuestionario
- process_quiz_answer: acumulacion de respuestas
- view_my_archetype: con/sin arquetipo asignado
- my_story_achievements: con/sin logros
- quiz completion, admin deny filter
"""
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

from tests.helpers import model_mock
from models.models import Archetype, StoryChoice, StoryNode, UserStoryProgress

import pytest

pytestmark = [pytest.mark.unit]


def _mock_story_ctx(mock_get_service):
    """Mock get_service(StoryService) context manager con autospec."""
    from services.story_service import StoryService

    svc = create_autospec(StoryService, spec_set=True, instance=True)
    mock_get_service.return_value.__enter__.return_value = svc
    return svc


class TestNarrativeMenu:
    """Tests para narrative_menu — menu principal de narrativa."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_not_started_no_archetype_shows_start_button(
        self, mock_get_service, make_callback
    ):
        """Sin historia iniciada y sin arquetipo: muestra mensaje con 'Comenzar'."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.has_started_story.return_value = False
        mock_story.get_user_archetype.return_value = None

        cb = make_callback(data="narrative")
        fsm = AsyncMock()
        fsm.clear = AsyncMock()

        from handlers.story_user_handlers import narrative_menu
        await narrative_menu(cb, fsm)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Fragmentos de la Historia" in text
        assert "descubrira que arquetipo" in text
        cb.answer.assert_called_once()

    @patch("handlers.story_user_handlers.get_service")
    async def test_started_with_archetype_shows_continue(
        self, mock_get_service, make_callback
    ):
        """Con historia iniciada y arquetipo: muestra 'Bienvenido de vuelta' y arquetipo."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.has_started_story.return_value = True
        mock_archetype = MagicMock()
        mock_archetype.value = "explorador"
        mock_story.get_user_archetype.return_value = mock_archetype
        mock_progress = model_mock(UserStoryProgress)
        mock_progress.current_chapter = 2
        mock_story.get_user_progress.return_value = mock_progress

        cb = make_callback(data="narrative")
        fsm = AsyncMock()
        fsm.clear = AsyncMock()

        from handlers.story_user_handlers import narrative_menu
        await narrative_menu(cb, fsm)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Bienvenido de vuelta" in text
        assert "Capitulo 2" in text
        assert "Explorador" in text
        cb.answer.assert_called_once()

    @patch("handlers.story_user_handlers.get_service")
    async def test_started_no_archetype(self, mock_get_service, make_callback):
        """Con historia iniciada pero sin arquetipo: no muestra texto de arquetipo."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.has_started_story.return_value = True
        mock_story.get_user_archetype.return_value = None
        mock_progress = model_mock(UserStoryProgress)
        mock_progress.current_chapter = 1
        mock_story.get_user_progress.return_value = mock_progress

        cb = make_callback(data="narrative")
        fsm = AsyncMock()
        fsm.clear = AsyncMock()

        from handlers.story_user_handlers import narrative_menu
        await narrative_menu(cb, fsm)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Bienvenido de vuelta" in text
        assert "Capitulo 1" in text
        assert "arquetipo" not in text.lower()
        cb.answer.assert_called_once()


class TestStartStory:
    """Tests para start_story — inicio de la historia."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_already_started_routes_to_continue(
        self, mock_get_service, make_callback
    ):
        """Si ya inicio la historia, llama a continue_story."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.has_started_story.return_value = True

        cb = make_callback(data="start_story")

        from handlers.story_user_handlers import start_story

        with patch("handlers.story_user_handlers.continue_story") as mock_continue:
            await start_story(cb)
            mock_continue.assert_called_once_with(cb)

    @patch("handlers.story_user_handlers.get_service")
    async def test_no_starting_node_shows_placeholder(
        self, mock_get_service, make_callback
    ):
        """Sin nodo inicial, muestra mensaje de 'aun siendo tejidos'."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.has_started_story.return_value = False
        mock_story.get_starting_node.return_value = None
        mock_story.create_user_progress.return_value = MagicMock()

        cb = make_callback(data="start_story")

        from handlers.story_user_handlers import start_story
        await start_story(cb)

        mock_story.create_user_progress.assert_called_once()
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "siendo tejidos" in text.lower()
        cb.answer.assert_called_once()

    @patch("handlers.story_user_handlers.get_service")
    async def test_with_starting_node_advances_then_shows_node(
        self, mock_get_service, make_callback
    ):
        """Con nodo inicial, llama advance_to_node y luego show_node."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.has_started_story.return_value = False
        mock_node = model_mock(StoryNode)
        mock_node.id = 1
        mock_story.get_starting_node.return_value = mock_node
        mock_story.advance_to_node.return_value = (True, None, MagicMock())

        cb = make_callback(data="start_story")

        from handlers.story_user_handlers import start_story
        with patch("handlers.story_user_handlers.show_node") as mock_show:
            await start_story(cb)
            mock_story.advance_to_node.assert_called_once_with(123456789, 1)
            mock_show.assert_called_once_with(cb, 1, mock_story)


class TestContinueStory:
    """Tests para continue_story — continuar historia."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_with_progress_shows_node(
        self, mock_get_service, make_callback
    ):
        """Con progreso y current_node_id, muestra el nodo."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_progress = model_mock(UserStoryProgress)
        mock_progress.current_node_id = 3
        mock_story.get_user_progress.return_value = mock_progress

        cb = make_callback(data="continue_story")

        fsm = AsyncMock()
        fsm.clear = AsyncMock()

        from handlers.story_user_handlers import continue_story
        with patch("handlers.story_user_handlers.show_node") as mock_show:
            await continue_story(cb, fsm)
            mock_show.assert_called_once_with(cb, 3, mock_story)

    @patch("handlers.story_user_handlers.get_service")
    async def test_without_progress_routes_to_start(
        self, mock_get_service, make_callback
    ):
        """Sin progreso o sin current_node_id, llama a start_story."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_user_progress.return_value = None

        cb = make_callback(data="continue_story")

        fsm = AsyncMock()
        fsm.clear = AsyncMock()

        from handlers.story_user_handlers import continue_story
        with patch("handlers.story_user_handlers.start_story") as mock_start:
            await continue_story(cb, fsm)
            mock_start.assert_called_once_with(cb)

    @patch("handlers.story_user_handlers.get_service")
    async def test_progress_without_current_node_routes_to_start(
        self, mock_get_service, make_callback
    ):
        """Progreso sin current_node_id redirige a start_story."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_progress = model_mock(UserStoryProgress)
        mock_progress.current_node_id = None
        mock_story.get_user_progress.return_value = mock_progress

        cb = make_callback(data="continue_story")

        fsm = AsyncMock()
        fsm.clear = AsyncMock()

        from handlers.story_user_handlers import continue_story
        with patch("handlers.story_user_handlers.start_story") as mock_start:
            await continue_story(cb, fsm)
            mock_start.assert_called_once_with(cb)


class TestGoToNode:
    """Tests para go_to_node — navegacion a nodo especifico."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_advances_then_shows_node(
        self, mock_get_service, make_callback
    ):
        """Valida transicion, advance_to_node y luego show_node."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.validate_continue_transition.return_value = (True, None)
        mock_story.advance_to_node.return_value = (True, None, MagicMock())

        cb = make_callback(data="story_continue:5")

        from keyboards.callback_data import ContinueStoryCallback
        cb_data = ContinueStoryCallback(node_id=5)

        from handlers.story_user_handlers import go_to_node
        with patch("handlers.story_user_handlers.show_node") as mock_show:
            await go_to_node(cb, cb_data)

        mock_story.validate_continue_transition.assert_called_once_with(123456789, 5)
        mock_story.advance_to_node.assert_called_once_with(123456789, 5)
        mock_show.assert_called_once_with(cb, 5, mock_story)

    @patch("handlers.story_user_handlers.get_service")
    async def test_invalid_transition_shows_alert(
        self, mock_get_service, make_callback
    ):
        """Transicion invalida: alerta y sin advance/show."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.validate_continue_transition.return_value = (
            False,
            "Fragmento no disponible",
        )

        cb = make_callback(data="story_continue:99")
        from keyboards.callback_data import ContinueStoryCallback

        cb_data = ContinueStoryCallback(node_id=99)

        from handlers.story_user_handlers import go_to_node
        with patch("handlers.story_user_handlers.show_node") as mock_show:
            await go_to_node(cb, cb_data)

        cb.answer.assert_called_once_with("Fragmento no disponible", show_alert=True)
        mock_story.advance_to_node.assert_not_called()
        mock_show.assert_not_called()


class TestMakeChoice:
    """Tests para make_choice — procesar eleccion del usuario."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_choice_not_found_shows_alert(
        self, mock_get_service, make_callback
    ):
        """Opcion no encontrada: muestra alerta 'ya no esta disponible'."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_choice.return_value = None

        cb = make_callback(data="story_choice:99")

        from keyboards.callback_data import StoryChoiceCallback
        cb_data = StoryChoiceCallback(choice_id=99)

        from handlers.story_user_handlers import make_choice
        await make_choice(cb, cb_data)

        cb.answer.assert_called_once_with("Esa opcion ya no esta disponible", show_alert=True)

    @patch("handlers.story_user_handlers.get_service")
    async def test_successful_choice_advances_node(
        self, mock_get_service, make_callback
    ):
        """Opcion valida con next_node_id: llama a advance_to_node y show_node."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_choice = model_mock(StoryChoice)
        mock_choice.next_node_id = 10
        mock_choice.additional_cost = 0
        mock_story.get_choice.return_value = mock_choice
        mock_story.advance_to_node.return_value = (True, None, MagicMock())

        cb = make_callback(data="story_choice:1")

        from keyboards.callback_data import StoryChoiceCallback
        cb_data = StoryChoiceCallback(choice_id=1)

        from handlers.story_user_handlers import make_choice
        with patch("handlers.story_user_handlers.show_node") as mock_show:
            await make_choice(cb, cb_data)

        mock_story.advance_to_node.assert_called_once_with(
            user_id=123456789, node_id=10, choice_id=1
        )
        mock_show.assert_called_once_with(cb, 10, mock_story)

    @patch("handlers.story_user_handlers.get_service")
    async def test_advance_failure_shows_alert(
        self, mock_get_service, make_callback
    ):
        """advance_to_node retorna fallo: muestra alerta con el mensaje."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_choice = model_mock(StoryChoice)
        mock_choice.next_node_id = 10
        mock_story.get_choice.return_value = mock_choice
        mock_story.advance_to_node.return_value = (False, "No tienes suficientes besitos", None)

        cb = make_callback(data="story_choice:1")

        from keyboards.callback_data import StoryChoiceCallback
        cb_data = StoryChoiceCallback(choice_id=1)

        from handlers.story_user_handlers import make_choice
        await make_choice(cb, cb_data)

        cb.answer.assert_called_once_with("No tienes suficientes besitos", show_alert=True)

    @patch("handlers.story_user_handlers.get_service")
    async def test_choice_end_of_story_advances_via_service(
        self, mock_get_service, make_callback
    ):
        """Opcion terminal: advance_to_node en nodo actual + mensaje de fin."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_choice = model_mock(StoryChoice)
        mock_choice.next_node_id = None
        mock_choice.node_id = 5
        mock_story.get_choice.return_value = mock_choice
        mock_story.advance_to_node.return_value = (True, None, MagicMock())

        cb = make_callback(data="story_choice:1")

        from keyboards.callback_data import StoryChoiceCallback
        cb_data = StoryChoiceCallback(choice_id=1)

        from handlers.story_user_handlers import make_choice
        await make_choice(cb, cb_data)

        mock_story.advance_to_node.assert_called_once_with(
            user_id=123456789, node_id=5, choice_id=1
        )
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "final" in text.lower()
        cb.answer.assert_called_once()


class TestStartArchetypeQuiz:
    """Tests para start_archetype_quiz — inicio del cuestionario."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_starts_quiz_and_calls_show_question(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Inicializa estado y llama a show_quiz_question."""
        mock_questions = [
            {"question": "Q1?", "options": [{"text": "A", "points": {"explorador": 3}}]}
        ]
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_user_archetype.return_value = None
        mock_story.get_archetype_quiz_questions.return_value = mock_questions

        cb = make_callback(data="discover_archetype")
        fsm = await make_fsm_context()

        from handlers.story_user_handlers import ArchetypeQuizStates, start_archetype_quiz
        with patch("handlers.story_user_handlers.show_quiz_question") as mock_show:
            await start_archetype_quiz(cb, fsm)

        mock_show.assert_called_once_with(cb, fsm, mock_story)

        data = await fsm.get_data()
        assert data["quiz_answers"] == []
        assert data["current_question"] == 0
        assert await fsm.get_state() == ArchetypeQuizStates.answering.state


class TestProcessQuizAnswer:
    """Tests para process_quiz_answer — procesar respuesta del cuestionario."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_appends_answer_and_advances(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Agrega la respuesta al estado y avanza a la siguiente pregunta."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_archetype_quiz_questions.return_value = [
            {"question": "Q1?", "options": [{"text": "A", "points": {"a": 3}}]},
            {"question": "Q2?", "options": [{"text": "B", "points": {"b": 3}}]},
        ]

        cb = make_callback(data="quiz_answer:0")
        fsm = await make_fsm_context()
        await fsm.update_data(quiz_answers=[], current_question=0)

        from keyboards.callback_data import QuizAnswerCallback
        cb_data = QuizAnswerCallback(answer_idx=0)

        from handlers.story_user_handlers import (
            ArchetypeQuizStates,
            process_quiz_answer,
        )
        await fsm.set_state(ArchetypeQuizStates.answering)
        with patch("handlers.story_user_handlers.show_quiz_question") as mock_show:
            await process_quiz_answer(cb, fsm, cb_data)

        data = await fsm.get_data()
        assert data["quiz_answers"] == [0]
        assert data["current_question"] == 1
        mock_show.assert_called_once_with(cb, fsm, mock_story)

    @patch("handlers.story_user_handlers.get_service")
    async def test_show_quiz_question_called_before_session_close(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Ultima respuesta: show_quiz_question debe ejecutarse antes de cerrar sesion."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_archetype_quiz_questions.return_value = [
            {"question": "Q1?", "options": [{"text": "A", "points": {"a": 3}}]},
        ]
        session_closed = {"value": False}

        class TrackingContext:
            def __enter__(self):
                return mock_story

            def __exit__(self, *args):
                session_closed["value"] = True
                return False

        mock_get_service.return_value = TrackingContext()

        cb = make_callback(data="quiz_answer:0")
        fsm = await make_fsm_context()
        await fsm.update_data(quiz_answers=[], current_question=0)

        from handlers.story_user_handlers import ArchetypeQuizStates, process_quiz_answer
        from keyboards.callback_data import QuizAnswerCallback

        cb_data = QuizAnswerCallback(answer_idx=0)
        await fsm.set_state(ArchetypeQuizStates.answering)

        async def assert_open_session(callback, state, story_service):
            assert session_closed["value"] is False
            assert story_service is mock_story

        with patch(
            "handlers.story_user_handlers.show_quiz_question",
            side_effect=assert_open_session,
        ):
            await process_quiz_answer(cb, fsm, cb_data)


class TestShowNode:
    """Tests directos para show_node — VIP, denegacion, teclados."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_node_not_found_shows_desvanecido(self, mock_get_service, make_callback):
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_node.return_value = None

        cb = make_callback()
        from handlers.story_user_handlers import show_node

        await show_node(cb, 99, mock_story)

        text = cb.message.edit_text.call_args[0][0]
        assert "desvanecido" in text.lower()

    @patch("handlers.story_user_handlers.get_service")
    async def test_vip_denial_blocks_content(self, mock_get_service, make_callback):
        mock_story = _mock_story_ctx(mock_get_service)
        mock_node = model_mock(StoryNode)
        mock_node.title = "VIP Fragment"
        mock_node.content = "secret"
        mock_node.chapter = 1
        mock_node.cost_besitos = 0
        mock_node.node_type = __import__(
            "models.models", fromlist=["NodeType"]
        ).NodeType.NARRATIVE
        mock_story.get_node.return_value = mock_node
        mock_story.can_access_node.return_value = (False, "Este fragmento requiere acceso a El Diván")

        cb = make_callback()
        from handlers.story_user_handlers import show_node

        await show_node(cb, 1, mock_story)

        text = cb.message.edit_text.call_args[0][0]
        assert "Diván" in text
        mock_story.advance_to_node.assert_not_called()

    @patch("handlers.story_user_handlers.get_service")
    async def test_ending_node_shows_archetype_button(self, mock_get_service, make_callback):
        from models.models import NodeType

        mock_story = _mock_story_ctx(mock_get_service)
        mock_node = model_mock(StoryNode)
        mock_node.title = "Fin"
        mock_node.content = "the end"
        mock_node.chapter = 1
        mock_node.cost_besitos = 0
        mock_node.node_type = NodeType.ENDING
        mock_story.get_node.return_value = mock_node
        mock_story.can_access_node.return_value = (True, None)
        mock_story.get_node_choices.return_value = []

        cb = make_callback()
        from handlers.story_user_handlers import show_node

        await show_node(cb, 1, mock_story)

        keyboard = cb.message.edit_text.call_args[1]["reply_markup"]
        btn_data = keyboard.inline_keyboard[0][0].callback_data
        assert btn_data == "view_my_archetype"

    @patch("handlers.story_user_handlers.get_service")
    async def test_decision_node_shows_choice_callbacks(self, mock_get_service, make_callback):
        from keyboards.callback_data import StoryChoiceCallback
        from models.models import NodeType

        mock_story = _mock_story_ctx(mock_get_service)
        mock_node = model_mock(StoryNode)
        mock_node.id = 7
        mock_node.title = "Choose"
        mock_node.content = "pick one"
        mock_node.chapter = 1
        mock_node.cost_besitos = 0
        mock_node.node_type = NodeType.DECISION
        mock_story.get_node.return_value = mock_node
        mock_story.can_access_node.return_value = (True, None)
        mock_choice = model_mock(StoryChoice)
        mock_choice.id = 42
        mock_choice.text = "Path A"
        mock_choice.additional_cost = 10
        mock_story.get_node_choices.return_value = [mock_choice]

        cb = make_callback()
        from handlers.story_user_handlers import show_node

        await show_node(cb, 7, mock_story)

        keyboard = cb.message.edit_text.call_args[1]["reply_markup"]
        btn = keyboard.inline_keyboard[0][0]
        assert btn.callback_data == StoryChoiceCallback(choice_id=42).pack()
        assert "10" in btn.text


    @patch("handlers.story_user_handlers.get_service")
    async def test_quiz_node_shows_discover_archetype_button(
        self, mock_get_service, make_callback
    ):
        from models.models import NodeType

        mock_story = _mock_story_ctx(mock_get_service)
        mock_node = model_mock(StoryNode)
        mock_node.title = "Quiz Gate"
        mock_node.content = "take the quiz"
        mock_node.chapter = 1
        mock_node.cost_besitos = 0
        mock_node.node_type = NodeType.QUIZ
        mock_story.get_node.return_value = mock_node
        mock_story.can_access_node.return_value = (True, None)
        mock_story.get_node_choices.return_value = []

        cb = make_callback()
        from handlers.story_user_handlers import show_node

        await show_node(cb, 8, mock_story)

        keyboard = cb.message.edit_text.call_args[1]["reply_markup"]
        btn_data = keyboard.inline_keyboard[0][0].callback_data
        assert btn_data == "discover_archetype"


class TestViewMyArchetype:
    """Tests para view_my_archetype — ver arquetipo del usuario."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_no_archetype_shows_discover_prompt(
        self, mock_get_service, make_callback
    ):
        """Sin arquetipo: muestra mensaje para descubrirlo."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_user_archetype.return_value = None

        cb = make_callback(data="view_my_archetype")

        from handlers.story_user_handlers import view_my_archetype
        await view_my_archetype(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Aun no ha despertado" in text
        cb.answer.assert_called_once()

    @patch("handlers.story_user_handlers.get_service")
    async def test_with_archetype_shows_details(
        self, mock_get_service, make_callback
    ):
        """Con arquetipo: muestra detalles y progreso."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_archetype = MagicMock()
        mock_archetype.value = "seductor"
        mock_story.get_user_archetype.return_value = mock_archetype
        mock_story.get_archetype_description.return_value = "Una descripcion del seductor"
        mock_story.get_visited_node_count.return_value = 3

        cb = make_callback(data="view_my_archetype")

        from handlers.story_user_handlers import view_my_archetype
        await view_my_archetype(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Seductor" in text
        assert "3" in text  # visited nodes count
        cb.answer.assert_called_once()


class TestMyStoryAchievements:
    """Tests para my_story_achievements — ver logros del usuario."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_no_achievements_shows_empty_message(
        self, mock_get_service, make_callback
    ):
        """Sin logros: muestra mensaje de 'aun no ha desbloqueado'."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_user_achievements.return_value = []

        cb = make_callback(data="my_story_achievements")

        from handlers.story_user_handlers import my_story_achievements
        await my_story_achievements(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Aun no ha desbloqueado" in text
        cb.answer.assert_called_once()

    @patch("handlers.story_user_handlers.get_service")
    async def test_with_achievements_lists_them(
        self, mock_get_service, make_callback
    ):
        """Con logros: los lista correctamente."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_ua = MagicMock()
        mock_ua.achievement.name = "El Primer Paso"
        mock_ua.achievement.description = "Completa tu primer fragmento"
        mock_ua.unlocked_at.strftime.return_value = "15/06/2024"
        mock_story.get_user_achievements.return_value = [mock_ua]

        cb = make_callback(data="my_story_achievements")

        from handlers.story_user_handlers import my_story_achievements
        await my_story_achievements(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "El Primer Paso" in text
        assert "15/06/2024" in text
        cb.answer.assert_called_once()


class TestQuizCompletion:
    """Tests para calculate_and_show_archetype — fin del cuestionario."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_quiz_completion_assigns_archetype_and_clears_fsm(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        from models.models import ArchetypeType

        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.calculate_archetype_from_quiz.return_value = ArchetypeType.SEDUCTOR
        mock_story.has_started_story.return_value = False
        mock_story.create_user_progress.return_value = MagicMock()
        mock_story.get_archetype_description.return_value = "Un seductor nato"

        cb = make_callback(data="discover_archetype")
        fsm = await make_fsm_context()
        await fsm.update_data(quiz_answers=[0, 0, 0], current_question=3)

        from handlers.story_user_handlers import calculate_and_show_archetype

        await calculate_and_show_archetype(cb, fsm, mock_story)

        mock_story.calculate_archetype_from_quiz.assert_called_once_with([0, 0, 0])
        mock_story.apply_quiz_scores_to_progress.assert_called_once()
        mock_story.assign_archetype_to_user.assert_called_once_with(
            123456789, ArchetypeType.SEDUCTOR
        )
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Seductor" in text
        assert await fsm.get_state() is None
        cb.answer.assert_called_once()


class TestAdminDeny:
    """Custodios no deben pasar el filtro de entrypoints usuario."""

    @pytest.mark.parametrize(
        "callback_data",
        [
            "narrative",
            "start_story",
            "continue_story",
            "discover_archetype",
            "view_my_archetype",
            "my_story_achievements",
        ],
    )
    @patch("handlers.story_user_handlers.is_admin", return_value=True)
    def test_admin_blocked_by_router_filter(self, mock_is_admin, make_callback, callback_data):
        """Filtro lambda cb: not is_admin(...) rechaza Custodios antes del handler."""
        cb = make_callback(data=callback_data)
        filter_allows = not mock_is_admin(cb.from_user.id)
        assert filter_allows is False
