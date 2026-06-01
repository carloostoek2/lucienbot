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
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = [pytest.mark.unit]


class TestNarrativeMenu:
    """Tests para narrative_menu — menu principal de narrativa."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_not_started_no_archetype_shows_start_button(
        self, mock_get_service, make_callback
    ):
        """Sin historia iniciada y sin arquetipo: muestra mensaje con 'Comenzar'."""
        mock_story = MagicMock()
        mock_story.has_started_story.return_value = False
        mock_story.get_user_archetype.return_value = None
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

        cb = make_callback(data="narrative")

        from handlers.story_user_handlers import narrative_menu
        await narrative_menu(cb)

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
        mock_story = MagicMock()
        mock_story.has_started_story.return_value = True
        mock_archetype = MagicMock()
        mock_archetype.value = "explorador"
        mock_story.get_user_archetype.return_value = mock_archetype
        mock_progress = MagicMock()
        mock_progress.current_chapter = 2
        mock_story.get_user_progress.return_value = mock_progress
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

        cb = make_callback(data="narrative")

        from handlers.story_user_handlers import narrative_menu
        await narrative_menu(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Bienvenido de vuelta" in text
        assert "Capitulo 2" in text
        assert "Explorador" in text
        cb.answer.assert_called_once()

    @patch("handlers.story_user_handlers.get_service")
    async def test_started_no_archetype(self, mock_get_service, make_callback):
        """Con historia iniciada pero sin arquetipo: no muestra texto de arquetipo."""
        mock_story = MagicMock()
        mock_story.has_started_story.return_value = True
        mock_story.get_user_archetype.return_value = None
        mock_progress = MagicMock()
        mock_progress.current_chapter = 1
        mock_story.get_user_progress.return_value = mock_progress
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

        cb = make_callback(data="narrative")

        from handlers.story_user_handlers import narrative_menu
        await narrative_menu(cb)

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
        mock_story = MagicMock()
        mock_story.has_started_story.return_value = True
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

        cb = make_callback(data="start_story")

        from handlers.story_user_handlers import start_story, continue_story
        with patch("handlers.story_user_handlers.continue_story") as mock_continue:
            await start_story(cb)
            mock_continue.assert_called_once_with(cb)

    @patch("handlers.story_user_handlers.get_service")
    async def test_no_starting_node_shows_placeholder(
        self, mock_get_service, make_callback
    ):
        """Sin nodo inicial, muestra mensaje de 'aun siendo tejidos'."""
        mock_story = MagicMock()
        mock_story.has_started_story.return_value = False
        mock_story.get_starting_node.return_value = None
        mock_story.create_user_progress.return_value = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

        cb = make_callback(data="start_story")

        from handlers.story_user_handlers import start_story
        await start_story(cb)

        mock_story.create_user_progress.assert_called_once()
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "siendo tejidos" in text.lower()
        cb.answer.assert_called_once()

    @patch("handlers.story_user_handlers.get_service")
    async def test_with_starting_node_shows_node(
        self, mock_get_service, make_callback
    ):
        """Con nodo inicial, llama a show_node."""
        mock_story = MagicMock()
        mock_story.has_started_story.return_value = False
        mock_node = MagicMock()
        mock_node.id = 1
        mock_story.get_starting_node.return_value = mock_node
        mock_story.create_user_progress.return_value = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

        cb = make_callback(data="start_story")

        from handlers.story_user_handlers import start_story
        with patch("handlers.story_user_handlers.show_node") as mock_show:
            await start_story(cb)
            mock_story.create_user_progress.assert_called_once_with(123456789, 1)
            mock_show.assert_called_once_with(cb, 1)


class TestContinueStory:
    """Tests para continue_story — continuar historia."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_with_progress_shows_node(
        self, mock_get_service, make_callback
    ):
        """Con progreso y current_node_id, muestra el nodo."""
        mock_story = MagicMock()
        mock_progress = MagicMock()
        mock_progress.current_node_id = 3
        mock_story.get_user_progress.return_value = mock_progress
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

        cb = make_callback(data="continue_story")

        from handlers.story_user_handlers import continue_story
        with patch("handlers.story_user_handlers.show_node") as mock_show:
            await continue_story(cb)
            mock_show.assert_called_once_with(cb, 3)

    @patch("handlers.story_user_handlers.get_service")
    async def test_without_progress_routes_to_start(
        self, mock_get_service, make_callback
    ):
        """Sin progreso o sin current_node_id, llama a start_story."""
        mock_story = MagicMock()
        mock_story.get_user_progress.return_value = None
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

        cb = make_callback(data="continue_story")

        from handlers.story_user_handlers import continue_story
        with patch("handlers.story_user_handlers.start_story") as mock_start:
            await continue_story(cb)
            mock_start.assert_called_once_with(cb)


class TestGoToNode:
    """Tests para go_to_node — navegacion a nodo especifico."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_calls_show_node_with_node_id(
        self, mock_get_service, make_callback
    ):
        """Llama a show_node con el node_id del callback_data."""
        mock_story = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

        cb = make_callback(data="story_continue:5")

        from keyboards.callback_data import ContinueStoryCallback
        cb_data = ContinueStoryCallback(node_id=5)

        from handlers.story_user_handlers import go_to_node
        with patch("handlers.story_user_handlers.show_node") as mock_show:
            await go_to_node(cb, cb_data)
            mock_show.assert_called_once_with(cb, 5)


class TestMakeChoice:
    """Tests para make_choice — procesar eleccion del usuario."""

    @patch("handlers.story_user_handlers.VIPService")
    @patch("handlers.story_user_handlers.get_service")
    async def test_choice_not_found_shows_alert(
        self, mock_get_service, mock_vip_svc, make_callback
    ):
        """Opcion no encontrada: muestra alerta 'ya no esta disponible'."""
        mock_story = MagicMock()
        mock_story.get_choice.return_value = None
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

        cb = make_callback(data="story_choice:99")

        from keyboards.callback_data import StoryChoiceCallback
        cb_data = StoryChoiceCallback(choice_id=99)

        from handlers.story_user_handlers import make_choice
        await make_choice(cb, cb_data)

        cb.answer.assert_called_once_with("Esa opcion ya no esta disponible", show_alert=True)

    @patch("handlers.story_user_handlers.VIPService")
    @patch("handlers.story_user_handlers.get_service")
    async def test_successful_choice_advances_node(
        self, mock_get_service, mock_vip_svc, make_callback
    ):
        """Opcion valida con next_node_id: llama a advance_to_node y show_node."""
        mock_story = MagicMock()
        mock_choice = MagicMock()
        mock_choice.next_node_id = 10
        mock_choice.additional_cost = 0
        mock_story.get_choice.return_value = mock_choice
        mock_story.advance_to_node.return_value = (True, None, MagicMock())
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context
        mock_vip_svc.return_value.is_user_vip.return_value = False

        cb = make_callback(data="story_choice:1")

        from keyboards.callback_data import StoryChoiceCallback
        cb_data = StoryChoiceCallback(choice_id=1)

        from handlers.story_user_handlers import make_choice
        with patch("handlers.story_user_handlers.show_node") as mock_show:
            await make_choice(cb, cb_data)

        mock_story.advance_to_node.assert_called_once_with(
            user_id=123456789, node_id=10, choice_id=1, is_vip=False
        )
        mock_show.assert_called_once_with(cb, 10)

    @patch("handlers.story_user_handlers.VIPService")
    @patch("handlers.story_user_handlers.get_service")
    async def test_advance_failure_shows_alert(
        self, mock_get_service, mock_vip_svc, make_callback
    ):
        """advance_to_node retorna fallo: muestra alerta con el mensaje."""
        mock_story = MagicMock()
        mock_choice = MagicMock()
        mock_choice.next_node_id = 10
        mock_story.get_choice.return_value = mock_choice
        mock_story.advance_to_node.return_value = (False, "No tienes suficientes besitos", None)
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context
        mock_vip_svc.return_value.is_user_vip.return_value = False

        cb = make_callback(data="story_choice:1")

        from keyboards.callback_data import StoryChoiceCallback
        cb_data = StoryChoiceCallback(choice_id=1)

        from handlers.story_user_handlers import make_choice
        await make_choice(cb, cb_data)

        cb.answer.assert_called_once_with("No tienes suficientes besitos", show_alert=True)

    @patch("handlers.story_user_handlers.VIPService")
    @patch("handlers.story_user_handlers.get_service")
    async def test_choice_end_of_story(
        self, mock_get_service, mock_vip_svc, make_callback
    ):
        """Opcion sin next_node_id: muestra mensaje de fin de historia."""
        mock_story = MagicMock()
        mock_choice = MagicMock()
        mock_choice.next_node_id = None
        mock_story.get_choice.return_value = mock_choice
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context
        mock_vip_svc.return_value.is_user_vip.return_value = False

        cb = make_callback(data="story_choice:1")

        from keyboards.callback_data import StoryChoiceCallback
        cb_data = StoryChoiceCallback(choice_id=1)

        from handlers.story_user_handlers import make_choice
        await make_choice(cb, cb_data)

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
        mock_story = MagicMock()
        mock_story.get_archetype_quiz_questions.return_value = mock_questions
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

        cb = make_callback(data="discover_archetype")
        fsm = await make_fsm_context()

        from handlers.story_user_handlers import start_archetype_quiz
        with patch("handlers.story_user_handlers.show_quiz_question") as mock_show:
            await start_archetype_quiz(cb, fsm)

        data = await fsm.get_data()
        assert data["quiz_answers"] == []
        assert data["current_question"] == 0
        mock_show.assert_called_once_with(cb, fsm)


class TestProcessQuizAnswer:
    """Tests para process_quiz_answer — procesar respuesta del cuestionario."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_appends_answer_and_advances(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Agrega la respuesta al estado y avanza a la siguiente pregunta."""
        mock_story = MagicMock()
        mock_story.get_archetype_quiz_questions.return_value = [
            {"question": "Q1?", "options": [{"text": "A", "points": {"a": 3}}]},
            {"question": "Q2?", "options": [{"text": "B", "points": {"b": 3}}]},
        ]
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

        cb = make_callback(data="quiz_answer:0")
        fsm = await make_fsm_context()
        await fsm.update_data(quiz_answers=[], current_question=0)

        from keyboards.callback_data import QuizAnswerCallback
        cb_data = QuizAnswerCallback(answer_idx=2)

        from handlers.story_user_handlers import process_quiz_answer
        with patch("handlers.story_user_handlers.show_quiz_question") as mock_show:
            await process_quiz_answer(cb, fsm, cb_data)

        data = await fsm.get_data()
        assert data["quiz_answers"] == [2]
        assert data["current_question"] == 1
        mock_show.assert_called_once_with(cb, fsm)


class TestViewMyArchetype:
    """Tests para view_my_archetype — ver arquetipo del usuario."""

    @patch("handlers.story_user_handlers.get_service")
    async def test_no_archetype_shows_discover_prompt(
        self, mock_get_service, make_callback
    ):
        """Sin arquetipo: muestra mensaje para descubrirlo."""
        mock_story = MagicMock()
        mock_story.get_user_archetype.return_value = None
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

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
        mock_story = MagicMock()
        mock_archetype = MagicMock()
        mock_archetype.value = "seductor"
        mock_story.get_user_archetype.return_value = mock_archetype
        mock_story.get_archetype_description.return_value = "Una descripcion del seductor"
        mock_progress = MagicMock()
        mock_progress.visited_nodes = "[1, 2, 3]"
        mock_story.get_user_progress.return_value = mock_progress
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

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
        mock_story = MagicMock()
        mock_story.get_user_achievements.return_value = []
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

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
        mock_story = MagicMock()
        mock_ua = MagicMock()
        mock_ua.achievement.name = "El Primer Paso"
        mock_ua.achievement.description = "Completa tu primer fragmento"
        mock_ua.unlocked_at.strftime.return_value = "15/06/2024"
        mock_story.get_user_achievements.return_value = [mock_ua]
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_story
        mock_get_service.return_value = mock_context

        cb = make_callback(data="my_story_achievements")

        from handlers.story_user_handlers import my_story_achievements
        await my_story_achievements(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "El Primer Paso" in text
        assert "15/06/2024" in text
        cb.answer.assert_called_once()
