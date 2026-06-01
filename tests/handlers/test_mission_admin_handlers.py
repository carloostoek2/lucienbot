"""
Tests unitarios para mission_admin_handlers.

Cubre:
- admin_missions_menu: menu principal de gestion de misiones
- create_mission_start: inicio del wizard FSM
- process_mission_name: validacion y guardado del nombre
- process_mission_description: descripcion opcional con /skip
- select_mission_type: seleccion de tipo mediante callback
- process_mission_target: validacion del valor numerico
- select_frequency: seleccion de frecuencia con listado de recompensas
- select_reward_for_mission: seleccion de recompensa con resumen
- confirm_create_mission: creacion final con manejo de errores
- list_missions: listado completo de misiones
- mission_admin_detail: detalle individual con acciones
- toggle_mission: activar/desactivar mision
- delete_mission_confirm: eliminacion con confirmacion
- missions_stats: estadisticas generales
- mission_detail_stats: estadisticas detalladas por mision
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from keyboards.callback_data import (
    MissionDeleteCallback,
    MissionDetailCallback,
    MissionFreqSelectCallback,
    MissionStatsCallback,
    MissionToggleCallback,
    MissionTypeSelectCallback,
    SelectRewardMissionCallback,
)
from models.models import MissionFrequency, MissionType

pytestmark = [pytest.mark.unit]


class TestAdminMissionsMenu:
    """Tests para admin_missions_menu — menu principal de gestion de misiones."""

    async def test_shows_menu_text(self, make_callback):
        """Muestra el menu con opciones."""
        cb = make_callback(data="admin_missions")

        from handlers.mission_admin_handlers import admin_missions_menu
        await admin_missions_menu(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "desafios" in text.lower()
        cb.answer.assert_called_once()

    async def test_calls_answer(self, make_callback):
        """Siempre llama a callback.answer()."""
        cb = make_callback(data="admin_missions")

        from handlers.mission_admin_handlers import admin_missions_menu
        await admin_missions_menu(cb)

        cb.answer.assert_called_once()


class TestCreateMissionStart:
    """Tests para create_mission_start — inicio del wizard de creacion."""

    async def test_sets_waiting_name_state(self, make_callback, make_fsm_context):
        """Establece el estado waiting_name y muestra instrucciones."""
        cb = make_callback(data="create_mission")
        fsm = await make_fsm_context()

        from handlers.mission_admin_handlers import create_mission_start, MissionWizardStates
        await create_mission_start(cb, fsm)

        state = await fsm.get_state()
        assert state == MissionWizardStates.waiting_name
        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()

    async def test_shows_step_1_message(self, make_callback, make_fsm_context):
        """Muestra mensaje del paso 1 con instrucciones."""
        cb = make_callback(data="create_mission")
        fsm = await make_fsm_context()

        from handlers.mission_admin_handlers import create_mission_start
        await create_mission_start(cb, fsm)

        text = cb.message.edit_text.call_args[0][0]
        assert "Paso 1 de 6" in text
        assert "Nombre" in text


class TestProcessMissionName:
    """Tests para process_mission_name — paso 1: nombre de la mision."""

    async def test_rejects_short_name(self, make_message, make_fsm_context):
        """Nombre menor a 3 caracteres muestra error y no avanza."""
        from handlers.mission_admin_handlers import process_mission_name, MissionWizardStates
        msg = make_message(text="AB")
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.waiting_name)
        await process_mission_name(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "3 caracteres" in text
        state = await fsm.get_state()
        assert state == MissionWizardStates.waiting_name

    async def test_accepts_valid_name_and_advances(self, make_message, make_fsm_context):
        """Nombre valido guarda en state y avanza a waiting_description."""
        from handlers.mission_admin_handlers import process_mission_name, MissionWizardStates
        msg = make_message(text="Reacciona 10 veces")
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.waiting_name)
        await process_mission_name(msg, fsm)

        data = await fsm.get_data()
        assert data["name"] == "Reacciona 10 veces"
        state = await fsm.get_state()
        assert state == MissionWizardStates.waiting_description
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Paso 2 de 6" in text


class TestProcessMissionDescription:
    """Tests para process_mission_description — paso 2: descripcion."""

    async def test_skip_sets_none_and_advances(self, make_message, make_fsm_context):
        """/skip establece description=None y avanza a selecting_type."""
        from handlers.mission_admin_handlers import (
            process_mission_description, MissionWizardStates,
        )
        msg = make_message(text="/skip")
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.waiting_description)
        await process_mission_description(msg, fsm)

        data = await fsm.get_data()
        assert data["description"] is None
        state = await fsm.get_state()
        assert state == MissionWizardStates.selecting_type

    async def test_with_description_saves_and_advances(self, make_message, make_fsm_context):
        """Descripcion textual se guarda correctamente."""
        from handlers.mission_admin_handlers import (
            process_mission_description, MissionWizardStates,
        )
        msg = make_message(text="Reacciona a 10 mensajes de Diana")
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.waiting_description)
        await process_mission_description(msg, fsm)

        data = await fsm.get_data()
        assert data["description"] == "Reacciona a 10 mensajes de Diana"
        state = await fsm.get_state()
        assert state == MissionWizardStates.selecting_type
        msg.answer.assert_called_once()

    async def test_shows_type_selection_keyboard(self, make_message, make_fsm_context):
        """Incluye botones de seleccion de tipo."""
        from handlers.mission_admin_handlers import process_mission_description
        msg = make_message(text="Una descripcion")
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.waiting_description)
        await process_mission_description(msg, fsm)

        text = msg.answer.call_args[0][0]
        assert "Paso 3 de 6" in text
        assert "Tipo" in text


class TestSelectMissionType:
    """Tests para select_mission_type — paso 3: tipo de mision."""

    async def test_valid_type_saves_and_advances(self, make_callback, make_fsm_context):
        """Tipo valido se guarda en state y avanza a waiting_target."""
        from handlers.mission_admin_handlers import select_mission_type, MissionWizardStates
        cb_data = MissionTypeSelectCallback(mission_type=MissionType.REACTION_COUNT.value)
        cb = make_callback(data=cb_data.pack())
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.selecting_type)
        await select_mission_type(cb, fsm, cb_data)

        data = await fsm.get_data()
        assert data["mission_type"] == MissionType.REACTION_COUNT
        state = await fsm.get_state()
        assert state == MissionWizardStates.waiting_target
        cb.answer.assert_called_once()

    async def test_invalid_type_shows_alert(self, make_callback, make_fsm_context):
        """Tipo invalido muestra alerta y no avanza."""
        from handlers.mission_admin_handlers import select_mission_type, MissionWizardStates
        cb_data = MissionTypeSelectCallback(mission_type="invalid_type")
        cb = make_callback(data=cb_data.pack())
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.selecting_type)
        await select_mission_type(cb, fsm, cb_data)

        cb.answer.assert_called_once_with("Tipo invalido", show_alert=True)
        state = await fsm.get_state()
        assert state == MissionWizardStates.selecting_type

    async def test_shows_correct_example_text(self, make_callback, make_fsm_context):
        """Muestra el texto de ejemplo correcto para el tipo seleccionado."""
        cb_data = MissionTypeSelectCallback(mission_type=MissionType.STORE_PURCHASE.value)
        cb = make_callback(data=cb_data.pack())
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.selecting_type)

        from handlers.mission_admin_handlers import select_mission_type
        await select_mission_type(cb, fsm, cb_data)

        text = cb.message.edit_text.call_args[0][0]
        assert "Paso 4 de 6" in text
        assert "1 compra" in text


class TestProcessMissionTarget:
    """Tests para process_mission_target — paso 4: valor objetivo."""

    async def test_rejects_non_numeric(self, make_message, make_fsm_context):
        """Entrada no numerica muestra error."""
        from handlers.mission_admin_handlers import process_mission_target, MissionWizardStates
        msg = make_message(text="diez")
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.waiting_target)
        await process_mission_target(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "numero" in text.lower()
        state = await fsm.get_state()
        assert state == MissionWizardStates.waiting_target

    async def test_rejects_zero_or_negative(self, make_message, make_fsm_context):
        """Valor 0 o negativo muestra error."""
        from handlers.mission_admin_handlers import process_mission_target, MissionWizardStates
        msg = make_message(text="0")
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.waiting_target)
        await process_mission_target(msg, fsm)

        msg.answer.assert_called_once()
        state = await fsm.get_state()
        assert state == MissionWizardStates.waiting_target

    async def test_accepts_valid_target_and_advances(self, make_message, make_fsm_context):
        """Valor numerico valido guarda en state y avanza a selecting_frequency."""
        from handlers.mission_admin_handlers import process_mission_target, MissionWizardStates
        msg = make_message(text="10")
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.waiting_target)
        await process_mission_target(msg, fsm)

        data = await fsm.get_data()
        assert data["target_value"] == 10
        state = await fsm.get_state()
        assert state == MissionWizardStates.selecting_frequency
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Paso 5 de 6" in text


class TestSelectFrequency:
    """Tests para select_frequency — paso 5: frecuencia."""

    @patch("handlers.mission_admin_handlers.RewardService")
    async def test_invalid_frequency_shows_alert(
        self, mock_reward_svc, make_callback, make_fsm_context
    ):
        """Frecuencia invalida muestra alerta."""
        from handlers.mission_admin_handlers import select_frequency, MissionWizardStates
        cb_data = MissionFreqSelectCallback(frequency="invalid_freq")
        cb = make_callback(data=cb_data.pack())
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.selecting_frequency)
        await select_frequency(cb, fsm, cb_data)

        cb.answer.assert_called_once_with("Frecuencia invalida", show_alert=True)
        state = await fsm.get_state()
        assert state == MissionWizardStates.selecting_frequency

    @patch("handlers.mission_admin_handlers.RewardService")
    async def test_no_rewards_shows_empty_message(
        self, mock_reward_svc, make_callback, make_fsm_context
    ):
        """Sin recompensas configurables, muestra mensaje y limpia estado."""
        mock_reward_svc.return_value.get_all_rewards.return_value = []
        cb_data = MissionFreqSelectCallback(frequency=MissionFrequency.ONE_TIME.value)
        cb = make_callback(data=cb_data.pack())
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.selecting_frequency)

        from handlers.mission_admin_handlers import select_frequency
        await select_frequency(cb, fsm, cb_data)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay recompensas" in text
        state = await fsm.get_state()
        assert state is None
        cb.answer.assert_called_once()

    @patch("handlers.mission_admin_handlers.RewardService")
    async def test_with_rewards_advances_to_selecting_reward(
        self, mock_reward_svc, make_callback, make_fsm_context
    ):
        """Con recompensas disponibles, avanza a selecting_reward."""
        from handlers.mission_admin_handlers import select_frequency, MissionWizardStates
        mock_reward = MagicMock()
        mock_reward.id = 1
        mock_reward.name = "Test Reward"
        mock_reward.reward_type = MagicMock(value="besitos")
        mock_reward_svc.return_value.get_all_rewards.return_value = [mock_reward]

        cb_data = MissionFreqSelectCallback(frequency=MissionFrequency.RECURRING.value)
        cb = make_callback(data=cb_data.pack())
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.selecting_frequency)
        await select_frequency(cb, fsm, cb_data)

        data = await fsm.get_data()
        assert data["frequency"] == MissionFrequency.RECURRING
        state = await fsm.get_state()
        assert state == MissionWizardStates.selecting_reward
        mock_reward_svc.return_value.get_all_rewards.assert_called_once_with(active_only=True)
        cb.answer.assert_called_once()


class TestSelectRewardForMission:
    """Tests para select_reward_for_mission — paso 6: seleccion de recompensa."""

    @patch("handlers.mission_admin_handlers.RewardService")
    async def test_shows_summary_and_advances(
        self, mock_reward_svc, make_callback, make_fsm_context
    ):
        """Muestra resumen de la mision y avanza a confirming."""
        from handlers.mission_admin_handlers import select_reward_for_mission, MissionWizardStates
        mock_reward = MagicMock()
        mock_reward.name = "Test Reward"
        mock_reward.reward_type = MagicMock(value="besitos")
        mock_reward_svc.return_value.get_reward.return_value = mock_reward

        cb_data = SelectRewardMissionCallback(reward_id=1)
        cb = make_callback(data=cb_data.pack())
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.selecting_reward)
        await fsm.update_data(
            name="Test Mission",
            description="A test mission",
            mission_type=MissionType.REACTION_COUNT,
            target_value=10,
            frequency=MissionFrequency.ONE_TIME,
        )

        await select_reward_for_mission(cb, fsm, cb_data)

        data = await fsm.get_data()
        assert data["reward_id"] == 1
        state = await fsm.get_state()
        assert state == MissionWizardStates.confirming
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Resumen" in text
        assert "Test Mission" in text
        assert "10" in text
        assert "Test Reward" in text
        cb.answer.assert_called_once()

    @patch("handlers.mission_admin_handlers.RewardService")
    async def test_shows_frequency_as_una_vez(
        self, mock_reward_svc, make_callback, make_fsm_context
    ):
        """Muestra 'Una vez' cuando frequency es ONE_TIME y recompensa es nula."""
        mock_reward_svc.return_value.get_reward.return_value = None

        cb_data = SelectRewardMissionCallback(reward_id=1)
        cb = make_callback(data=cb_data.pack())
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.selecting_reward)
        await fsm.update_data(
            name="Test",
            description="Desc",
            mission_type=MissionType.REACTION_COUNT,
            target_value=5,
            frequency=MissionFrequency.ONE_TIME,
        )

        from handlers.mission_admin_handlers import select_reward_for_mission
        await select_reward_for_mission(cb, fsm, cb_data)

        text = cb.message.edit_text.call_args[0][0]
        assert "Una vez" in text
        assert "Ninguna" in text

    @patch("handlers.mission_admin_handlers.RewardService")
    async def test_shows_frequency_as_recurrente(
        self, mock_reward_svc, make_callback, make_fsm_context
    ):
        """Muestra 'Recurrente' cuando frequency es RECURRING."""
        mock_reward = MagicMock()
        mock_reward.name = "Bonus"
        mock_reward.reward_type = MagicMock(value="besitos")
        mock_reward_svc.return_value.get_reward.return_value = mock_reward

        cb_data = SelectRewardMissionCallback(reward_id=2)
        cb = make_callback(data=cb_data.pack())
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.selecting_reward)
        await fsm.update_data(
            name="Test",
            description="Desc",
            mission_type=MissionType.DAILY_GIFT_STREAK,
            target_value=7,
            frequency=MissionFrequency.RECURRING,
        )

        from handlers.mission_admin_handlers import select_reward_for_mission
        await select_reward_for_mission(cb, fsm, cb_data)

        text = cb.message.edit_text.call_args[0][0]
        assert "Recurrente" in text

    @patch("handlers.mission_admin_handlers.RewardService")
    async def test_handles_missing_description(
        self, mock_reward_svc, make_callback, make_fsm_context
    ):
        """Muestra 'Sin descripcion' cuando description es None."""
        mock_reward_svc.return_value.get_reward.return_value = None

        cb_data = SelectRewardMissionCallback(reward_id=1)
        cb = make_callback(data=cb_data.pack())
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.selecting_reward)
        await fsm.update_data(
            name="Test",
            description=None,
            mission_type=MissionType.VIP_ACTIVE,
            target_value=1,
            frequency=MissionFrequency.ONE_TIME,
        )

        from handlers.mission_admin_handlers import select_reward_for_mission
        await select_reward_for_mission(cb, fsm, cb_data)

        text = cb.message.edit_text.call_args[0][0]
        assert "Sin descripcion" in text


class TestConfirmCreateMission:
    """Tests para confirm_create_mission — creacion final de la mision."""

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_creates_mission_successfully(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Crea la mision y muestra mensaje de exito."""
        mock_mission = MagicMock()
        mock_mission.name = "Test Mission"
        mock_mission.mission_type = MagicMock(value="reaction_count")
        mock_mission.target_value = 10

        mock_mission_svc = MagicMock()
        mock_mission_svc.create_mission.return_value = mock_mission
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb = make_callback(data="confirm_create_mission")
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.confirming)
        await fsm.update_data(
            name="Test Mission",
            description="A test mission",
            mission_type=MissionType.REACTION_COUNT,
            target_value=10,
            reward_id=1,
            frequency=MissionFrequency.ONE_TIME,
        )

        from handlers.mission_admin_handlers import confirm_create_mission
        await confirm_create_mission(cb, fsm)

        mock_mission_svc.create_mission.assert_called_once_with(
            name="Test Mission",
            description="A test mission",
            mission_type=MissionType.REACTION_COUNT,
            target_value=10,
            reward_id=1,
            frequency=MissionFrequency.ONE_TIME,
            created_by=123456789,
        )
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "creada" in text.lower()
        assert "Test Mission" in text
        state = await fsm.get_state()
        assert state is None
        cb.answer.assert_called_once()

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_handles_creation_exception(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Cuando create_mission lanza excepcion, muestra error."""
        mock_mission_svc = MagicMock()
        mock_mission_svc.create_mission.side_effect = Exception("DB error")
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb = make_callback(data="confirm_create_mission")
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.confirming)
        await fsm.update_data(
            name="Test Mission",
            description="A test mission",
            mission_type=MissionType.REACTION_COUNT,
            target_value=10,
            reward_id=1,
            frequency=MissionFrequency.ONE_TIME,
        )

        from handlers.mission_admin_handlers import confirm_create_mission
        await confirm_create_mission(cb, fsm)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Error" in text
        state = await fsm.get_state()
        assert state is None
        cb.answer.assert_called_once()

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_clears_state_on_success(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Limpia el estado FSM despues de crear."""
        mock_mission = MagicMock()
        mock_mission.name = "Test"
        mock_mission.mission_type = MagicMock(value="reaction_count")
        mock_mission.target_value = 10

        mock_mission_svc = MagicMock()
        mock_mission_svc.create_mission.return_value = mock_mission
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb = make_callback(data="confirm_create_mission")
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.confirming)
        await fsm.update_data(name="Test", target_value=5, reward_id=1)

        from handlers.mission_admin_handlers import confirm_create_mission
        await confirm_create_mission(cb, fsm)

        state = await fsm.get_state()
        assert state is None

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_creates_with_default_fields(
        self, mock_get_service, make_callback, make_fsm_context
    ):
        """Usa None para campos opcionales si no estan en state."""
        mock_mission = MagicMock()
        mock_mission.name = "Test"
        mock_mission.mission_type = MagicMock(value="reaction_count")
        mock_mission.target_value = 10

        mock_mission_svc = MagicMock()
        mock_mission_svc.create_mission.return_value = mock_mission
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb = make_callback(data="confirm_create_mission")
        fsm = await make_fsm_context()
        await fsm.set_state(MissionWizardStates.confirming)
        await fsm.update_data(name="Test", target_value=5)

        from handlers.mission_admin_handlers import confirm_create_mission
        await confirm_create_mission(cb, fsm)

        args = mock_mission_svc.create_mission.call_args[1]
        assert args["description"] is None
        assert args["mission_type"] is None
        assert args["reward_id"] is None
        assert args["frequency"] is None


class TestListMissions:
    """Tests para list_missions — listado de todas las misiones."""

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_shows_empty_message_when_no_missions(
        self, mock_get_service, make_callback
    ):
        """Cuando no hay misiones, muestra mensaje vacio."""
        mock_mission_svc = MagicMock()
        mock_mission_svc.get_all_missions.return_value = []
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb = make_callback(data="list_missions")

        from handlers.mission_admin_handlers import list_missions
        await list_missions(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay misiones" in text
        cb.answer.assert_called_once()

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_lists_missions_with_status(self, mock_get_service, make_callback):
        """Muestra misiones con su estado."""
        mock_mission_active = MagicMock()
        mock_mission_active.name = "Mission Active"
        mock_mission_active.is_active = True
        mock_mission_active.mission_type = MagicMock(value="reaction_count")
        mock_mission_active.id = 1

        mock_mission_inactive = MagicMock()
        mock_mission_inactive.name = "Mission Inactive"
        mock_mission_inactive.is_active = False
        mock_mission_inactive.mission_type = MagicMock(value="daily_gift_streak")
        mock_mission_inactive.id = 2

        mock_mission_svc = MagicMock()
        mock_mission_svc.get_all_missions.return_value = [
            mock_mission_active, mock_mission_inactive
        ]
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb = make_callback(data="list_missions")

        from handlers.mission_admin_handlers import list_missions
        await list_missions(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Mission Active" in text
        assert "Mission Inactive" in text
        assert "✅" in text
        assert "❌" in text
        cb.answer.assert_called_once()

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_calls_get_all_missions_with_active_only_false(
        self, mock_get_service, make_callback
    ):
        """Llama a get_all_missions(active_only=False)."""
        mock_mission_svc = MagicMock()
        mock_mission_svc.get_all_missions.return_value = []
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb = make_callback(data="list_missions")

        from handlers.mission_admin_handlers import list_missions
        await list_missions(cb)

        mock_mission_svc.get_all_missions.assert_called_once_with(active_only=False)


class TestMissionAdminDetail:
    """Tests para mission_admin_detail — detalle de mision."""

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_mission_not_found_shows_alert(self, mock_get_service, make_callback):
        """Mision no encontrada muestra alerta."""
        mock_mission_svc = MagicMock()
        mock_mission_svc.get_mission.return_value = None
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb_data = MissionDetailCallback(mission_id=999)
        cb = make_callback(data=cb_data.pack())

        from handlers.mission_admin_handlers import mission_admin_detail
        await mission_admin_detail(cb, cb_data)

        cb.answer.assert_called_once_with("Mision no encontrada", show_alert=True)
        mock_mission_svc.get_mission.assert_called_once_with(999)

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_shows_mission_detail(self, mock_get_service, make_callback):
        """Muestra detalle completo de la mision."""
        mock_reward = MagicMock()
        mock_reward.name = "Test Reward"
        mock_reward.reward_type = MagicMock(value="besitos")

        mock_mission = MagicMock()
        mock_mission.name = "Test Mission"
        mock_mission.description = "A test description"
        mock_mission.is_active = True
        mock_mission.mission_type = MagicMock(value="reaction_count")
        mock_mission.target_value = 10
        mock_mission.id = 1
        mock_mission.frequency = MissionFrequency.ONE_TIME
        mock_mission.reward = mock_reward

        mock_mission_svc = MagicMock()
        mock_mission_svc.get_mission.return_value = mock_mission
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb_data = MissionDetailCallback(mission_id=1)
        cb = make_callback(data=cb_data.pack())

        from handlers.mission_admin_handlers import mission_admin_detail
        await mission_admin_detail(cb, cb_data)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Test Mission" in text
        assert "Test Reward" in text
        assert "10" in text
        assert "Una vez" in text
        assert "Activo" in text
        cb.answer.assert_called_once()

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_shows_no_reward_text(self, mock_get_service, make_callback):
        """Muestra 'Sin recompensa' cuando mision no tiene recompensa."""
        mock_mission = MagicMock()
        mock_mission.name = "Mission No Reward"
        mock_mission.description = "No reward"
        mock_mission.is_active = False
        mock_mission.mission_type = MagicMock(value="vip_active")
        mock_mission.target_value = 1
        mock_mission.id = 2
        mock_mission.frequency = MissionFrequency.RECURRING
        mock_mission.reward = None

        mock_mission_svc = MagicMock()
        mock_mission_svc.get_mission.return_value = mock_mission
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb_data = MissionDetailCallback(mission_id=2)
        cb = make_callback(data=cb_data.pack())

        from handlers.mission_admin_handlers import mission_admin_detail
        await mission_admin_detail(cb, cb_data)

        text = cb.message.edit_text.call_args[0][0]
        assert "Sin recompensa" in text
        assert "Inactivo" in text
        assert "Recurrente" in text


class TestToggleMission:
    """Tests para toggle_mission — activar/desactivar mision."""

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_mission_not_found_shows_alert(
        self, mock_get_service, make_callback
    ):
        """Mision no encontrada muestra alerta."""
        mock_mission_svc = MagicMock()
        mock_mission_svc.get_mission.return_value = None
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb_data = MissionToggleCallback(mission_id=999)
        cb = make_callback(data=cb_data.pack())

        from handlers.mission_admin_handlers import toggle_mission
        await toggle_mission(cb, cb_data)

        cb.answer.assert_called_once_with("Mision no encontrada", show_alert=True)
        mock_mission_svc.update_mission.assert_not_called()

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_toggles_active_to_inactive(
        self, mock_get_service, make_callback
    ):
        """Mision activa se desactiva."""
        mock_mission = MagicMock()
        mock_mission.is_active = True
        mock_mission.id = 1
        mock_mission.name = "Test"
        mock_mission.description = "Desc"
        mock_mission.mission_type = MagicMock(value="reaction_count")
        mock_mission.target_value = 10
        mock_mission.frequency = MissionFrequency.ONE_TIME
        mock_mission.reward = None

        mock_mission_svc = MagicMock()
        mock_mission_svc.get_mission.return_value = mock_mission
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb_data = MissionToggleCallback(mission_id=1)
        cb = make_callback(data=cb_data.pack())

        from handlers.mission_admin_handlers import toggle_mission
        await toggle_mission(cb, cb_data)

        mock_mission_svc.update_mission.assert_called_once_with(1, is_active=False)
        cb.answer.assert_any_call("Mision desactivada")

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_toggles_inactive_to_active(
        self, mock_get_service, make_callback
    ):
        """Mision inactiva se activa."""
        mock_mission = MagicMock()
        mock_mission.is_active = False
        mock_mission.id = 2
        mock_mission.name = "Test"
        mock_mission.description = "Desc"
        mock_mission.mission_type = MagicMock(value="reaction_count")
        mock_mission.target_value = 10
        mock_mission.frequency = MissionFrequency.ONE_TIME
        mock_mission.reward = None

        mock_mission_svc = MagicMock()
        mock_mission_svc.get_mission.return_value = mock_mission
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb_data = MissionToggleCallback(mission_id=2)
        cb = make_callback(data=cb_data.pack())

        from handlers.mission_admin_handlers import toggle_mission
        await toggle_mission(cb, cb_data)

        mock_mission_svc.update_mission.assert_called_once_with(2, is_active=True)
        cb.answer.assert_any_call("Mision activada")

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_toggle_shows_reward_in_detail(
        self, mock_get_service, make_callback
    ):
        """Despues de toggle, el detalle muestra la recompensa si existe."""
        mock_reward = MagicMock()
        mock_reward.name = "Test Reward"
        mock_reward.reward_type = MagicMock(value="besitos")

        mock_mission = MagicMock()
        mock_mission.is_active = True
        mock_mission.id = 3
        mock_mission.name = "Test"
        mock_mission.description = "Desc"
        mock_mission.mission_type = MagicMock(value="reaction_count")
        mock_mission.target_value = 10
        mock_mission.frequency = MissionFrequency.ONE_TIME
        mock_mission.reward = mock_reward

        mock_mission_svc = MagicMock()
        mock_mission_svc.get_mission.return_value = mock_mission
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb_data = MissionToggleCallback(mission_id=3)
        cb = make_callback(data=cb_data.pack())

        from handlers.mission_admin_handlers import toggle_mission
        await toggle_mission(cb, cb_data)

        text = cb.message.edit_text.call_args[0][0]
        assert "Test Reward" in text
        assert "besitos" in text


class TestDeleteMissionConfirm:
    """Tests para delete_mission_confirm — eliminacion de mision."""

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_unconfirmed_shows_confirmation_dialog(
        self, mock_get_service, make_callback
    ):
        """Sin confirmacion, muestra dialogo de confirmacion."""
        mock_mission_svc = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb_data = MissionDeleteCallback(mission_id=1, confirmed=False)
        cb = make_callback(data=cb_data.pack())

        from handlers.mission_admin_handlers import delete_mission_confirm
        await delete_mission_confirm(cb, cb_data)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "seguro" in text.lower()
        assert "eliminar" in text.lower()
        cb.answer.assert_called_once()
        mock_mission_svc.delete_mission.assert_not_called()

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_confirmed_deletes_successfully(
        self, mock_get_service, make_callback
    ):
        """Confirmado y eliminacion exitosa, muestra mensaje."""
        mock_mission_svc = MagicMock()
        mock_mission_svc.delete_mission.return_value = True
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb_data = MissionDeleteCallback(mission_id=1, confirmed=True)
        cb = make_callback(data=cb_data.pack())

        from handlers.mission_admin_handlers import delete_mission_confirm
        await delete_mission_confirm(cb, cb_data)

        mock_mission_svc.delete_mission.assert_called_once_with(1)
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "eliminada" in text.lower()
        cb.answer.assert_called_once()

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_confirmed_delete_fails_shows_error(
        self, mock_get_service, make_callback
    ):
        """Confirmado pero eliminacion falla, muestra error."""
        mock_mission_svc = MagicMock()
        mock_mission_svc.delete_mission.return_value = False
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb_data = MissionDeleteCallback(mission_id=1, confirmed=True)
        cb = make_callback(data=cb_data.pack())

        from handlers.mission_admin_handlers import delete_mission_confirm
        await delete_mission_confirm(cb, cb_data)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Error" in text
        cb.answer.assert_called_once()

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_calls_delete_with_correct_id(
        self, mock_get_service, make_callback
    ):
        """Llama a delete_mission con el mission_id correcto."""
        mock_mission_svc = MagicMock()
        mock_mission_svc.delete_mission.return_value = True
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb_data = MissionDeleteCallback(mission_id=42, confirmed=True)
        cb = make_callback(data=cb_data.pack())

        from handlers.mission_admin_handlers import delete_mission_confirm
        await delete_mission_confirm(cb, cb_data)

        mock_mission_svc.delete_mission.assert_called_once_with(42)


class TestMissionsStats:
    """Tests para missions_stats — estadisticas generales de misiones."""

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_shows_stats_with_active_missions(
        self, mock_get_service, make_callback
    ):
        """Muestra estadisticas con botones para misiones activas."""
        mock_mission_active = MagicMock()
        mock_mission_active.is_active = True
        mock_mission_active.name = "Active Mission"
        mock_mission_active.id = 1

        mock_mission_inactive = MagicMock()
        mock_mission_inactive.is_active = False
        mock_mission_inactive.name = "Inactive Mission"
        mock_mission_inactive.id = 2

        mock_mission_svc = MagicMock()
        mock_mission_svc.get_all_missions.return_value = [
            mock_mission_active, mock_mission_inactive
        ]
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb = make_callback(data="missions_stats")

        from handlers.mission_admin_handlers import missions_stats
        await missions_stats(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Estadisticas" in text
        assert "1" in text
        assert "2" in text
        cb.answer.assert_called_once()

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_shows_no_active_missions(self, mock_get_service, make_callback):
        """Sin misiones activas muestra estadisticas sin botones."""
        mock_mission_svc = MagicMock()
        mock_mission_svc.get_all_missions.return_value = []
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb = make_callback(data="missions_stats")

        from handlers.mission_admin_handlers import missions_stats
        await missions_stats(cb)

        text = cb.message.edit_text.call_args[0][0]
        assert "0" in text
        cb.answer.assert_called_once()


class TestMissionDetailStats:
    """Tests para mission_detail_stats — estadisticas detalladas de una mision."""

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_mission_not_found_shows_alert(
        self, mock_get_service, make_callback
    ):
        """Mision no encontrada muestra alerta."""
        mock_mission_svc = MagicMock()
        mock_mission_svc.get_mission_stats.return_value = {}
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb_data = MissionStatsCallback(mission_id=999)
        cb = make_callback(data=cb_data.pack())

        from handlers.mission_admin_handlers import mission_detail_stats
        await mission_detail_stats(cb, cb_data)

        cb.answer.assert_called_once_with("Mision no encontrada", show_alert=True)

    @patch("handlers.mission_admin_handlers.get_service")
    async def test_shows_mission_statistics(self, mock_get_service, make_callback):
        """Muestra estadisticas detalladas de la mision."""
        mock_stats = {
            "mission_name": "Test Mission",
            "total_users": 10,
            "completed": 7,
            "in_progress": 3,
            "completion_rate": 70.0,
        }
        mock_mission_svc = MagicMock()
        mock_mission_svc.get_mission_stats.return_value = mock_stats
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_mission_svc
        mock_get_service.return_value = mock_context

        cb_data = MissionStatsCallback(mission_id=1)
        cb = make_callback(data=cb_data.pack())

        from handlers.mission_admin_handlers import mission_detail_stats
        await mission_detail_stats(cb, cb_data)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Test Mission" in text
        assert "10" in text
        assert "7" in text
        assert "3" in text
        assert "70" in text
        cb.answer.assert_called_once()


from handlers.mission_admin_handlers import MissionWizardStates
