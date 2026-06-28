"""
Tests unitarios para story_admin_handlers.

Cubre:
- admin_narrative_menu: menu principal con estadisticas
- create_node_start y wizard de 7 estados: NodeWizardStates
- list_nodes: listado de nodos
- manage_archetypes / manage_achievements
- toggle_node, delete_node_confirm
- manage_choices y choice wizard: ChoiceWizardStates
- archetype wizard: ArchetypeWizardStates
- achievement wizard: AchievementWizardStates
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

from tests.helpers import model_mock
from models.models import Archetype, ArchetypeType, NodeType, StoryNode

from services.story_service import StoryService

pytestmark = [pytest.mark.unit]


def _mock_story_ctx(mock_get_service):
    """Mock get_service(StoryService) context manager con autospec."""
    svc = create_autospec(StoryService, spec_set=True, instance=True)
    mock_get_service.return_value.__enter__.return_value = svc
    return svc


@pytest.fixture(autouse=True)
def _admin_user_for_wizard_tests(monkeypatch):
    """Los pasos FSM re-verifican is_admin; los fixtures de test no son custodios reales."""
    monkeypatch.setattr("handlers.story_admin_handlers.is_admin", lambda _uid: True)


class TestAdminNarrativeMenu:
    """Tests para admin_narrative_menu — menu de administracion de narrativa."""

    @patch("handlers.story_admin_handlers.get_service")
    async def test_shows_menu_with_stats(self, mock_get_service, make_callback):
        """Muestra el menu con estadisticas de la narrativa."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_story_stats.return_value = {
            "total_nodes": 10,
            "total_chapters": 3,
            "total_users": 50,
            "completed_users": 5,
            "total_achievements": 8,
        }

        cb = make_callback(data="admin_narrative")

        from handlers.story_admin_handlers import admin_narrative_menu
        await admin_narrative_menu(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "10" in text
        assert "3" in text
        assert "50" in text
        assert "5" in text
        assert "8" in text
        cb.answer.assert_called_once()


class TestCreateNodeWizard:
    """Tests para el wizard de creacion de nodo (NodeWizardStates)."""

    async def test_create_node_start_sets_state(self, make_callback, make_fsm_context):
        """Inicia el wizard estableciendo waiting_title."""
        cb = make_callback(data="create_node")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import create_node_start, NodeWizardStates
        await create_node_start(cb, fsm)

        state = await fsm.get_state()
        assert state == NodeWizardStates.waiting_title
        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()

    async def test_process_node_title_rejects_short(self, make_message, make_fsm_context):
        """Titulo menor a 3 caracteres muestra error y no avanza."""
        msg = make_message(text="AB")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import process_node_title, NodeWizardStates
        await fsm.set_state(NodeWizardStates.waiting_title)
        await process_node_title(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "3 caracteres" in text
        state = await fsm.get_state()
        assert state == NodeWizardStates.waiting_title

    async def test_process_node_title_accepts_valid(self, make_message, make_fsm_context):
        """Titulo valido guarda en state y avanza a waiting_content."""
        msg = make_message(text="El Primer Encuentro")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import process_node_title, NodeWizardStates
        await fsm.set_state(NodeWizardStates.waiting_title)
        await process_node_title(msg, fsm)

        data = await fsm.get_data()
        assert data["title"] == "El Primer Encuentro"
        state = await fsm.get_state()
        assert state == NodeWizardStates.waiting_content
        msg.answer.assert_called_once()

    async def test_process_node_content_rejects_short(self, make_message, make_fsm_context):
        """Contenido menor a 10 caracteres muestra error."""
        msg = make_message(text="Corto")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import process_node_content, NodeWizardStates
        await fsm.set_state(NodeWizardStates.waiting_content)
        await process_node_content(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "10 caracteres" in text

    async def test_process_node_content_accepts_valid(self, make_message, make_fsm_context):
        """Contenido valido guarda y avanza a selecting_type."""
        msg = make_message(text="Un texto largo y significativo para el fragmento")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import process_node_content, NodeWizardStates
        await fsm.set_state(NodeWizardStates.waiting_content)
        await process_node_content(msg, fsm)

        data = await fsm.get_data()
        assert data["content"] == msg.text
        state = await fsm.get_state()
        assert state == NodeWizardStates.selecting_type
        msg.answer.assert_called_once()

    async def test_select_node_type_saves_and_advances(self, make_callback, make_fsm_context):
        """Seleccion de tipo de nodo guarda y avanza a waiting_chapter."""
        cb = make_callback(data="story_node_type:narrative")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import select_node_type, NodeWizardStates
        from keyboards.callback_data import StoryNodeTypeCallback
        cb_data = StoryNodeTypeCallback(node_type=NodeType.NARRATIVE.value)
        await fsm.set_state(NodeWizardStates.selecting_type)
        await select_node_type(cb, fsm, cb_data)

        data = await fsm.get_data()
        assert data["node_type"] == NodeType.NARRATIVE
        state = await fsm.get_state()
        assert state == NodeWizardStates.waiting_chapter
        cb.answer.assert_called_once()

    async def test_process_node_chapter_rejects_non_number(self, make_message, make_fsm_context):
        """Capitulo no numerico muestra error."""
        msg = make_message(text="abc")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import process_node_chapter, NodeWizardStates
        await fsm.set_state(NodeWizardStates.waiting_chapter)
        await process_node_chapter(msg, fsm)

        msg.answer.assert_called_once()
        state = await fsm.get_state()
        assert state == NodeWizardStates.waiting_chapter

    async def test_process_node_chapter_rejects_less_than_one(self, make_message, make_fsm_context):
        """Capitulo menor a 1 muestra error."""
        msg = make_message(text="0")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import process_node_chapter, NodeWizardStates
        await fsm.set_state(NodeWizardStates.waiting_chapter)
        await process_node_chapter(msg, fsm)

        msg.answer.assert_called_once()
        state = await fsm.get_state()
        assert state == NodeWizardStates.waiting_chapter

    async def test_process_node_chapter_accepts_valid(self, make_message, make_fsm_context):
        """Capitulo valido guarda y avanza a waiting_order."""
        msg = make_message(text="3")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import process_node_chapter, NodeWizardStates
        await fsm.set_state(NodeWizardStates.waiting_chapter)
        await process_node_chapter(msg, fsm)

        data = await fsm.get_data()
        assert data["chapter"] == 3
        state = await fsm.get_state()
        assert state == NodeWizardStates.waiting_order
        msg.answer.assert_called_once()

    async def test_select_archetype_requirement_none(self, make_callback, make_fsm_context):
        """Seleccion 'none' establece required_archetype=None."""
        cb = make_callback(data="story_archetype_req:none")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import select_archetype_requirement, NodeWizardStates
        from keyboards.callback_data import StoryArchetypeReqCallback
        cb_data = StoryArchetypeReqCallback(archetype="none")
        await fsm.set_state(NodeWizardStates.waiting_requirements)
        await select_archetype_requirement(cb, fsm, cb_data)

        data = await fsm.get_data()
        assert data["required_archetype"] is None
        state = await fsm.get_state()
        assert state == NodeWizardStates.waiting_vip
        cb.answer.assert_called_once()

    async def test_select_node_vip_advances_to_cost(self, make_callback, make_fsm_context):
        """Seleccion VIP avanza al paso de costo."""
        cb = make_callback(data="node_vip_yes")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import select_node_vip, NodeWizardStates
        await fsm.set_state(NodeWizardStates.waiting_vip)
        await select_node_vip(cb, fsm)

        data = await fsm.get_data()
        assert data["required_vip"] is True
        state = await fsm.get_state()
        assert state == NodeWizardStates.waiting_cost

    async def test_node_cost_zero_sets_and_shows_confirmation(self, make_callback, make_fsm_context):
        """node_cost_zero establece costo 0 y muestra confirmacion."""
        cb = make_callback(data="node_cost_0")
        fsm = await make_fsm_context()
        await fsm.update_data(title="Test", content="Content", node_type=MagicMock(value="NARRATIVE"), chapter=1)

        from handlers.story_admin_handlers import node_cost_zero, NodeWizardStates
        await fsm.set_state(NodeWizardStates.waiting_cost)
        await node_cost_zero(cb, fsm)

        data = await fsm.get_data()
        assert data["cost_besitos"] == 0
        state = await fsm.get_state()
        assert state == NodeWizardStates.confirming
        cb.message.edit_text.assert_called_once()

    async def test_process_node_cost_accepts_valid(self, make_message, make_fsm_context):
        """Costo valido guarda y muestra confirmacion."""
        msg = make_message(text="50")
        fsm = await make_fsm_context()
        await fsm.update_data(title="Test", content="Content", node_type=MagicMock(value="NARRATIVE"), chapter=1)

        from handlers.story_admin_handlers import process_node_cost, NodeWizardStates
        await fsm.set_state(NodeWizardStates.waiting_cost)
        await process_node_cost(msg, fsm)

        data = await fsm.get_data()
        assert data["cost_besitos"] == 50
        state = await fsm.get_state()
        assert state == NodeWizardStates.confirming
        msg.answer.assert_called_once()

    async def test_process_node_cost_rejects_negative(self, make_message, make_fsm_context):
        """Costo negativo muestra error."""
        msg = make_message(text="-5")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import process_node_cost, NodeWizardStates
        await fsm.set_state(NodeWizardStates.waiting_cost)
        await process_node_cost(msg, fsm)

        msg.answer.assert_called_once()
        state = await fsm.get_state()
        assert state == NodeWizardStates.waiting_cost

    @patch("handlers.story_admin_handlers.get_service")
    async def test_confirm_create_node_success(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Confirmacion crea el nodo exitosamente."""
        mock_node = model_mock(StoryNode)
        mock_node.id = 1
        mock_node.title = "Test Node"
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.create_node.return_value = mock_node

        cb = make_callback(data="confirm_create_node")
        fsm = await make_fsm_context()
        await fsm.update_data(
            title="Test Node",
            content="Content here",
            node_type=NodeType.NARRATIVE,
            chapter=1,
            required_archetype=None,
            cost_besitos=0,
        )

        from handlers.story_admin_handlers import confirm_create_node, NodeWizardStates
        await fsm.set_state(NodeWizardStates.confirming)
        await confirm_create_node(cb, fsm)

        mock_story.create_node.assert_called_once_with(
            title="Test Node",
            content="Content here",
            node_type=NodeType.NARRATIVE,
            chapter=1,
            order_in_chapter=0,
            is_starting_node=False,
            required_archetype=None,
            required_vip=False,
            cost_besitos=0,
            created_by=123456789,
        )
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "forjado" in text.lower()
        state = await fsm.get_state()
        assert state is None
        cb.answer.assert_called_once()

    @patch("handlers.story_admin_handlers.get_service")
    async def test_confirm_create_node_exception_shows_error(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Error al crear nodo muestra mensaje de error."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.create_node.side_effect = Exception("DB Error")

        cb = make_callback(data="confirm_create_node")
        fsm = await make_fsm_context()
        await fsm.update_data(
            title="Test", content="Content", node_type=MagicMock(value="NARRATIVE"),
            chapter=1, required_archetype=None, cost_besitos=0,
        )

        from handlers.story_admin_handlers import confirm_create_node, NodeWizardStates
        await fsm.set_state(NodeWizardStates.confirming)
        await confirm_create_node(cb, fsm)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "inesperado" in text.lower()
        state = await fsm.get_state()
        assert state is None
        cb.answer.assert_called_once()


class TestListNodes:
    """Tests para list_nodes — listado de nodos."""

    @patch("handlers.story_admin_handlers.get_service")
    async def test_no_nodes_shows_empty(self, mock_get_service, make_callback):
        """Sin nodos: muestra mensaje de vacio."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_all_nodes.return_value = []

        cb = make_callback(data="list_nodes")

        from handlers.story_admin_handlers import list_nodes
        await list_nodes(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "vacios" in text.lower()
        cb.answer.assert_called_once()

    @patch("handlers.story_admin_handlers.get_service")
    async def test_lists_nodes_by_chapter(self, mock_get_service, make_callback):
        """Con nodos: los lista organizados por capitulo."""
        mock_node1 = model_mock(StoryNode)
        mock_node1.chapter = 1
        mock_node1.title = "Capitulo Uno"
        mock_node1.is_active = True
        mock_node1.node_type = MagicMock(value="NARRATIVE")

        mock_node2 = model_mock(StoryNode)
        mock_node2.chapter = 1
        mock_node2.title = "Segundo Fragmento"
        mock_node2.is_active = False
        mock_node2.node_type = MagicMock(value="DECISION")

        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_all_nodes.return_value = [mock_node1, mock_node2]

        cb = make_callback(data="list_nodes")

        from handlers.story_admin_handlers import list_nodes
        await list_nodes(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Capitulo 1" in text or "Capítulo 1" in text
        assert "Capitulo" in text
        cb.answer.assert_called_once()


class TestManageArchetypes:
    """Tests para manage_archetypes — gestion de arquetipos."""

    @patch("handlers.story_admin_handlers.get_service")
    async def test_shows_archetypes_list(self, mock_get_service, make_callback):
        """Muestra lista de arquetipos existentes."""
        mock_arch1 = model_mock(Archetype)
        mock_arch1.name = "El Explorador"
        mock_arch1.archetype_type = MagicMock()
        mock_arch1.archetype_type.value = "explorador"
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_all_archetypes.return_value = [mock_arch1]

        cb = make_callback(data="manage_archetypes")

        from handlers.story_admin_handlers import manage_archetypes
        await manage_archetypes(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "arquetipos" in text.lower()
        cb.answer.assert_called_once()


class TestManageAchievements:
    """Tests para manage_achievements — gestion de logros."""

    async def test_shows_achievement_menu(self, make_callback):
        """Muestra menu de gestion de logros."""
        cb = make_callback(data="manage_achievements")

        from handlers.story_admin_handlers import manage_achievements
        await manage_achievements(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "reconocimientos" in text.lower()
        cb.answer.assert_called_once()


class TestToggleNode:
    """Tests para toggle_node — activar/desactivar nodo."""

    @patch("handlers.story_admin_handlers.get_service")
    async def test_toggles_active_to_inactive(self, mock_get_service, make_callback):
        """Nodo activo se desactiva."""
        mock_node = model_mock(StoryNode)
        mock_node.is_active = True
        mock_node.id = 1
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_node.return_value = mock_node

        cb = make_callback(data="story_node_toggle:1")

        from keyboards.callback_data import StoryNodeToggleCallback
        cb_data = StoryNodeToggleCallback(node_id=1)

        from handlers.story_admin_handlers import toggle_node
        with patch("handlers.story_admin_handlers.node_detail") as mock_detail:
            await toggle_node(cb, cb_data)

        mock_story.update_node.assert_called_once_with(1, is_active=False)
        cb.answer.assert_called_once()

    @patch("handlers.story_admin_handlers.get_service")
    async def test_toggles_inactive_to_active(self, mock_get_service, make_callback):
        """Nodo inactivo se activa."""
        mock_node = model_mock(StoryNode)
        mock_node.is_active = False
        mock_node.id = 1
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_node.return_value = mock_node

        cb = make_callback(data="story_node_toggle:1")

        from keyboards.callback_data import StoryNodeToggleCallback
        cb_data = StoryNodeToggleCallback(node_id=1)

        from handlers.story_admin_handlers import toggle_node
        with patch("handlers.story_admin_handlers.node_detail") as mock_detail:
            await toggle_node(cb, cb_data)

        mock_story.update_node.assert_called_once_with(1, is_active=True)
        cb.answer.assert_called_once()

    @patch("handlers.story_admin_handlers.get_service")
    async def test_node_not_found_shows_alert(self, mock_get_service, make_callback):
        """Nodo no encontrado muestra alerta."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_node.return_value = None

        cb = make_callback(data="story_node_toggle:999")

        from keyboards.callback_data import StoryNodeToggleCallback
        cb_data = StoryNodeToggleCallback(node_id=999)

        from handlers.story_admin_handlers import toggle_node
        await toggle_node(cb, cb_data)

        cb.answer.assert_called_once_with("Fragmento no encontrado", show_alert=True)
        mock_story.update_node.assert_not_called()


class TestDeleteNode:
    """Tests para delete_node_confirm — eliminar nodo."""

    @patch("handlers.story_admin_handlers.get_service")
    async def test_unconfirmed_shows_confirmation(self, mock_get_service, make_callback):
        """Sin confirmacion, muestra dialogo de confirmacion."""
        mock_story = _mock_story_ctx(mock_get_service)

        cb = make_callback(data="story_node_delete:1")

        from keyboards.callback_data import StoryNodeDeleteCallback
        cb_data = StoryNodeDeleteCallback(node_id=1, confirmed=False)

        from handlers.story_admin_handlers import delete_node_confirm
        await delete_node_confirm(cb, cb_data)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "seguro" in text.lower()
        cb.answer.assert_called_once()
        mock_story.delete_node.assert_not_called()

    @patch("handlers.story_admin_handlers.get_service")
    async def test_confirmed_deletes_successfully(self, mock_get_service, make_callback):
        """Confirmado y eliminacion exitosa."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.delete_node.return_value = True

        cb = make_callback(data="story_node_delete:1")

        from keyboards.callback_data import StoryNodeDeleteCallback
        cb_data = StoryNodeDeleteCallback(node_id=1, confirmed=True)

        from handlers.story_admin_handlers import delete_node_confirm
        await delete_node_confirm(cb, cb_data)

        mock_story.delete_node.assert_called_once_with(1)
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "eliminado" in text.lower()
        cb.answer.assert_called_once()

    @patch("handlers.story_admin_handlers.get_service")
    async def test_confirmed_delete_fails_shows_error(self, mock_get_service, make_callback):
        """Confirmado pero eliminacion falla."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.delete_node.return_value = False

        cb = make_callback(data="story_node_delete:1")

        from keyboards.callback_data import StoryNodeDeleteCallback
        cb_data = StoryNodeDeleteCallback(node_id=1, confirmed=True)

        from handlers.story_admin_handlers import delete_node_confirm
        await delete_node_confirm(cb, cb_data)

        mock_story.delete_node.assert_called_once_with(1)
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "eliminar" in text.lower() or "No se pudo" in text
        cb.answer.assert_called_once()


class TestManageChoices:
    """Tests para manage_choices y choice wizard."""

    @patch("handlers.story_admin_handlers.get_service")
    async def test_no_decision_nodes_shows_empty(self, mock_get_service, make_callback):
        """Sin nodos de decision: muestra mensaje."""
        mock_node = model_mock(StoryNode)
        mock_node.node_type = MagicMock(value="NARRATIVE")
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_all_nodes.return_value = [mock_node]

        cb = make_callback(data="manage_choices")

        from handlers.story_admin_handlers import manage_choices
        await manage_choices(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay fragmentos de decision" in text
        cb.answer.assert_called_once()

    @patch("handlers.story_admin_handlers.get_service")
    async def test_lists_decision_nodes(self, mock_get_service, make_callback):
        """Con nodos de decision: los lista."""
        mock_node = model_mock(StoryNode)
        mock_node.node_type = NodeType.DECISION
        mock_node.id = 1
        mock_node.title = "Decision Point"
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_all_nodes.return_value = [mock_node]

        cb = make_callback(data="manage_choices")

        from handlers.story_admin_handlers import manage_choices
        await manage_choices(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Seleccione" in text
        cb.answer.assert_called_once()


class TestChoiceWizard:
    """Tests para el wizard de creacion de opciones (ChoiceWizardStates)."""

    @patch("handlers.story_admin_handlers.get_service")
    async def test_add_choices_start_sets_state(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Inicia el wizard de opcion estableciendo waiting_text."""
        mock_node = model_mock(StoryNode)
        mock_node.id = 1
        mock_node.title = "Test Node"
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_node.return_value = mock_node

        cb = make_callback(data="story_add_choices:1")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import add_choices_start, ChoiceWizardStates
        from keyboards.callback_data import StoryAddChoicesCallback
        cb_data = StoryAddChoicesCallback(node_id=1)
        await add_choices_start(cb, fsm, cb_data)

        data = await fsm.get_data()
        assert data["choice_node_id"] == 1
        state = await fsm.get_state()
        assert state == ChoiceWizardStates.waiting_text
        cb.answer.assert_called_once()

    @patch("handlers.story_admin_handlers.get_service")
    async def test_add_choices_start_node_not_found(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Nodo no encontrado: muestra alerta."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_node.return_value = None

        cb = make_callback(data="story_add_choices:999")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import add_choices_start
        from keyboards.callback_data import StoryAddChoicesCallback
        cb_data = StoryAddChoicesCallback(node_id=999)
        await add_choices_start(cb, fsm, cb_data)

        cb.answer.assert_called_once_with("Fragmento no encontrado", show_alert=True)

    async def test_process_choice_text_rejects_short(self, make_message, make_fsm_context):
        """Texto de opcion menor a 3 caracteres muestra error."""
        msg = make_message(text="AB")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import process_choice_text, ChoiceWizardStates
        await fsm.set_state(ChoiceWizardStates.waiting_text)
        await process_choice_text(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "3 caracteres" in text
        state = await fsm.get_state()
        assert state == ChoiceWizardStates.waiting_text

    @patch("handlers.story_admin_handlers.get_service")
    async def test_process_choice_text_accepts_valid(
        self, mock_get_service, make_message, make_fsm_context
    ):
        """Texto valido guarda y avanza a selecting_next_node."""
        mock_node = model_mock(StoryNode)
        mock_node.id = 1
        mock_node.title = "Target Node"
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_all_nodes.return_value = [mock_node]

        msg = make_message(text="Aceptar la invitacion")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import process_choice_text, ChoiceWizardStates
        await fsm.set_state(ChoiceWizardStates.waiting_text)
        await process_choice_text(msg, fsm)

        data = await fsm.get_data()
        assert data["choice_text"] == "Aceptar la invitacion"
        state = await fsm.get_state()
        assert state == ChoiceWizardStates.selecting_next_node
        msg.answer.assert_called_once()

    async def test_select_choice_next_node_saves(
        self, make_callback, make_fsm_context
    ):
        """Seleccion de siguiente nodo guarda y avanza a waiting_archetype_points."""
        cb = make_callback(data="story_choice_next:5")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import select_choice_next_node, ChoiceWizardStates
        from keyboards.callback_data import StoryChoiceNextCallback
        cb_data = StoryChoiceNextCallback(node_id=5)
        await fsm.set_state(ChoiceWizardStates.selecting_next_node)
        await select_choice_next_node(cb, fsm, cb_data)

        data = await fsm.get_data()
        assert data["choice_next_node_id"] == 5
        state = await fsm.get_state()
        assert state == ChoiceWizardStates.waiting_archetype_points
        cb.answer.assert_called_once()

    async def test_select_choice_archetype_points_none(
        self, make_callback, make_fsm_context
    ):
        """Seleccion 'none' para puntos de arquetipo guarda None y muestra confirmacion."""
        cb = make_callback(data="story_choice_pts:none")
        fsm = await make_fsm_context()
        await fsm.update_data(choice_text="Test", choice_next_node_id=5)

        from handlers.story_admin_handlers import select_choice_archetype_points, ChoiceWizardStates
        from keyboards.callback_data import StoryChoicePointsCallback
        cb_data = StoryChoicePointsCallback(archetype="none")
        await fsm.set_state(ChoiceWizardStates.waiting_archetype_points)
        await select_choice_archetype_points(cb, fsm, cb_data)

        data = await fsm.get_data()
        assert data["choice_archetype"] is None
        state = await fsm.get_state()
        assert state == ChoiceWizardStates.waiting_points_amount
        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()

    @patch("handlers.story_admin_handlers.get_service")
    async def test_confirm_create_choice_success(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Confirmacion crea la opcion exitosamente."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.create_choice.return_value = MagicMock(id=1)

        cb = make_callback(data="confirm_create_choice")
        fsm = await make_fsm_context()
        await fsm.update_data(
            choice_node_id=1,
            choice_text="Ir a la izquierda",
            choice_next_node_id=5,
            choice_archetype=None,
            choice_archetype_points=0,
            choice_additional_cost=10,
        )

        from handlers.story_admin_handlers import confirm_create_choice, ChoiceWizardStates
        await fsm.set_state(ChoiceWizardStates.confirming)
        await confirm_create_choice(cb, fsm)

        mock_story.create_choice.assert_called_once_with(
            node_id=1,
            text="Ir a la izquierda",
            next_node_id=5,
            choice_archetype=None,
            archetype_points=0,
            additional_cost=10,
        )
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "agregada" in text.lower()
        state = await fsm.get_state()
        assert state is None
        cb.answer.assert_called_once()


class TestArchetypeWizard:
    """Tests para el wizard de creacion de arquetipos (ArchetypeWizardStates)."""

    async def test_create_archetype_start_sets_state(self, make_callback, make_fsm_context):
        """Inicia wizard de arquetipo estableciendo selecting_type."""
        cb = make_callback(data="create_archetype")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import create_archetype_start, ArchetypeWizardStates
        await create_archetype_start(cb, fsm)

        state = await fsm.get_state()
        assert state == ArchetypeWizardStates.selecting_type
        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()

    @patch("handlers.story_admin_handlers.get_service")
    async def test_select_new_archetype_type_saves(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Seleccion de tipo de arquetipo guarda y avanza a waiting_name."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_archetype.return_value = None

        cb = make_callback(data="story_new_archetype:explorador")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import select_new_archetype_type, ArchetypeWizardStates
        from keyboards.callback_data import StoryNewArchetypeCallback
        cb_data = StoryNewArchetypeCallback(archetype="explorador")
        await fsm.set_state(ArchetypeWizardStates.selecting_type)
        await select_new_archetype_type(cb, fsm, cb_data)

        data = await fsm.get_data()
        assert data["archetype_type"].value == "explorador"
        state = await fsm.get_state()
        assert state == ArchetypeWizardStates.waiting_name
        cb.answer.assert_called_once()

    @patch("handlers.story_admin_handlers.get_service")
    async def test_select_new_archetype_type_already_exists(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Arquetipo ya existente muestra alerta."""
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.get_archetype.return_value = MagicMock()

        cb = make_callback(data="story_new_archetype:explorador")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import select_new_archetype_type
        from keyboards.callback_data import StoryNewArchetypeCallback
        cb_data = StoryNewArchetypeCallback(archetype="explorador")
        await select_new_archetype_type(cb, fsm, cb_data)

        cb.answer.assert_called_once_with("Este arquetipo ya esta definido", show_alert=True)

    async def test_process_archetype_name_accepts_valid(self, make_message, make_fsm_context):
        """Nombre valido guarda y avanza a waiting_description."""
        msg = make_message(text="El Explorador")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import process_archetype_name, ArchetypeWizardStates
        await fsm.set_state(ArchetypeWizardStates.waiting_name)
        await process_archetype_name(msg, fsm)

        data = await fsm.get_data()
        assert data["archetype_name"] == "El Explorador"
        state = await fsm.get_state()
        assert state == ArchetypeWizardStates.waiting_description
        msg.answer.assert_called_once()

    async def test_process_archetype_description_accepts_valid(self, make_message, make_fsm_context):
        """Descripcion valida guarda y avanza a waiting_welcome."""
        msg = make_message(text="Un aventurero curioso que busca descubrir los secretos")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import process_archetype_description, ArchetypeWizardStates
        await fsm.set_state(ArchetypeWizardStates.waiting_description)
        await process_archetype_description(msg, fsm)

        data = await fsm.get_data()
        assert data["archetype_description"] == msg.text
        state = await fsm.get_state()
        assert state == ArchetypeWizardStates.waiting_welcome
        msg.answer.assert_called_once()

    @patch("handlers.story_admin_handlers.get_service")
    async def test_confirm_create_archetype_success(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Confirmacion crea arquetipo exitosamente."""
        mock_archetype = MagicMock()
        mock_archetype.name = "El Explorador"
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.create_archetype.return_value = mock_archetype

        cb = make_callback(data="confirm_create_archetype")
        fsm = await make_fsm_context()
        await fsm.update_data(
            archetype_type=MagicMock(value="explorador"),
            archetype_name="El Explorador",
            archetype_description="Descripcion",
            archetype_welcome=None,
        )

        from handlers.story_admin_handlers import confirm_create_archetype, ArchetypeWizardStates
        await fsm.set_state(ArchetypeWizardStates.confirming)
        await confirm_create_archetype(cb, fsm)

        mock_story.create_archetype.assert_called_once()
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "definido" in text.lower()
        state = await fsm.get_state()
        assert state is None
        cb.answer.assert_called_once()


class TestAchievementWizard:
    """Tests para el wizard de creacion de logros (AchievementWizardStates)."""

    async def test_create_achievement_start_sets_state(self, make_callback, make_fsm_context):
        """Inicia wizard de logro estableciendo waiting_name."""
        cb = make_callback(data="create_achievement")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import create_achievement_start, AchievementWizardStates
        await create_achievement_start(cb, fsm)

        state = await fsm.get_state()
        assert state == AchievementWizardStates.waiting_name
        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()

    async def test_achievement_name_input_saves_and_advances(self, make_message, make_fsm_context):
        """Nombre del logro guarda y avanza a waiting_description."""
        msg = make_message(text="El Primer Paso")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import achievement_name_input, AchievementWizardStates
        await fsm.set_state(AchievementWizardStates.waiting_name)
        await achievement_name_input(msg, fsm)

        data = await fsm.get_data()
        assert data["achievement_name"] == "El Primer Paso"
        state = await fsm.get_state()
        assert state == AchievementWizardStates.waiting_description
        msg.answer.assert_called_once()

    async def test_achievement_description_input_saves_and_advances(self, make_message, make_fsm_context):
        """Descripcion del logro guarda y avanza a waiting_icon."""
        msg = make_message(text="Completa tu primer fragmento de historia")
        fsm = await make_fsm_context()

        from handlers.story_admin_handlers import achievement_description_input, AchievementWizardStates
        await fsm.set_state(AchievementWizardStates.waiting_description)
        await achievement_description_input(msg, fsm)

        data = await fsm.get_data()
        assert data["achievement_description"] == msg.text
        state = await fsm.get_state()
        assert state == AchievementWizardStates.waiting_icon
        msg.answer.assert_called_once()

    async def test_achievement_icon_input_saves_and_shows_confirm(self, make_message, make_fsm_context):
        """Icono guarda y muestra confirmacion."""
        msg = make_message(text="🌹")
        fsm = await make_fsm_context()
        await fsm.update_data(achievement_name="Test", achievement_description="Desc")

        from handlers.story_admin_handlers import achievement_icon_input, AchievementWizardStates
        await fsm.set_state(AchievementWizardStates.waiting_icon)
        await achievement_icon_input(msg, fsm)

        data = await fsm.get_data()
        assert data["achievement_icon"] == "🌹"
        state = await fsm.get_state()
        assert state == AchievementWizardStates.waiting_reward
        msg.answer.assert_called_once()

    @patch("handlers.story_admin_handlers.get_service")
    async def test_confirm_create_achievement_success(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Confirmacion crea logro exitosamente."""
        mock_achievement = MagicMock()
        mock_achievement.name = "El Primer Paso"
        mock_achievement.icon = "🌹"
        mock_story = _mock_story_ctx(mock_get_service)
        mock_story.create_achievement.return_value = mock_achievement

        cb = make_callback(data="confirm_create_achievement")
        fsm = await make_fsm_context()
        await fsm.update_data(
            achievement_name="El Primer Paso",
            achievement_description="Descripcion",
            achievement_icon="🌹",
            reward_besitos=25,
            required_chapter=2,
            required_archetype=None,
        )

        from handlers.story_admin_handlers import confirm_create_achievement, AchievementWizardStates
        await fsm.set_state(AchievementWizardStates.confirming)
        await confirm_create_achievement(cb, fsm)

        mock_story.create_achievement.assert_called_once_with(
            name="El Primer Paso",
            description="Descripcion",
            icon="🌹",
            required_node_id=None,
            required_chapter=2,
            required_archetype=None,
            reward_besitos=25,
            created_by=123456789,
        )
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "creado" in text.lower()
        state = await fsm.get_state()
        assert state is None
        cb.answer.assert_called_once()
