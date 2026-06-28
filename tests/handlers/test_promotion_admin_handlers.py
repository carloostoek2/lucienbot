"""
Tests unitarios para promotion_admin_handlers.

Cubre handlers del panel de administracion de promociones:
- admin_promotions_menu: menu principal admin
- CreatePromotionWizard: FSM de creacion (5 pasos + confirmacion)
- list_promotions: listado de todas las promociones
- toggle_promotion: activar/desactivar promocion
- delete_promotion_confirm: confirmacion y eliminacion
- show_pending_interests / show_promotion_interests: intereses
- show_blocked_users / unblock_user: gestion de bloqueos
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch
from datetime import datetime

from tests.helpers import model_mock
from services.promotion_service import PromotionService
from models.models import Package, Promotion

pytestmark = [pytest.mark.unit]


def _mock_promo_ctx(mock_get_service):
    """Mock get_service(PromotionService) context manager con autospec."""
    svc = create_autospec(PromotionService, spec_set=True, instance=True)
    mock_get_service.return_value.__enter__.return_value = svc
    return svc


class TestAdminPromotionsMenu:
    """Tests para admin_promotions_menu — menu principal de administracion."""

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_shows_menu_with_stats(self, mock_get_service, make_callback):
        """Muestra el menu con estadisticas correctas."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion_stats.return_value = {
            "active_promotions": 3,
            "total_promotions": 10,
            "pending_interests": 5,
            "attended_interests": 8,
            "blocked_users": 2,
        }

        cb = make_callback(data="admin_promotions")

        from handlers.promotion_admin_handlers import admin_promotions_menu
        await admin_promotions_menu(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "3" in text
        assert "10" in text
        assert "5" in text
        assert "8" in text
        assert "2" in text
        cb.answer.assert_called_once()

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_calls_answer(self, mock_get_service, make_callback):
        """Siempre llama a callback.answer()."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion_stats.return_value = {
            "active_promotions": 0, "total_promotions": 0,
            "pending_interests": 0, "attended_interests": 0, "blocked_users": 0,
        }

        cb = make_callback(data="admin_promotions")

        from handlers.promotion_admin_handlers import admin_promotions_menu
        await admin_promotions_menu(cb)

        cb.answer.assert_called_once()


class TestCreatePromotionStart:
    """Tests para create_promotion_start — inicio del wizard."""

    async def test_sets_waiting_name_state(self, make_callback, make_fsm_context):
        """Establece el estado waiting_name y muestra instrucciones."""
        cb = make_callback(data="create_promotion")
        fsm = await make_fsm_context()

        from handlers.promotion_admin_handlers import create_promotion_start, PromotionWizardStates
        await create_promotion_start(cb, fsm)

        state = await fsm.get_state()
        assert state == PromotionWizardStates.waiting_name
        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()

    async def test_shows_step_1_message(self, make_callback, make_fsm_context):
        """Muestra mensaje del paso 1 con instrucciones."""
        cb = make_callback(data="create_promotion")
        fsm = await make_fsm_context()

        from handlers.promotion_admin_handlers import create_promotion_start
        await create_promotion_start(cb, fsm)

        text = cb.message.edit_text.call_args[0][0]
        assert "Paso 1 de 5" in text
        assert "nombre" in text.lower()


class TestProcessPromotionName:
    """Tests para process_promotion_name — paso 1: nombre."""

    async def test_rejects_short_name(self, make_message, make_fsm_context):
        """Nombre menor a 3 caracteres muestra error y no avanza."""
        from handlers.promotion_admin_handlers import process_promotion_name, PromotionWizardStates
        msg = make_message(text="AB")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_name)
        await process_promotion_name(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "3 caracteres" in text
        state = await fsm.get_state()
        assert state == PromotionWizardStates.waiting_name

    async def test_accepts_valid_name_and_advances(self, make_message, make_fsm_context):
        """Nombre valido guarda en state y avanza a waiting_description."""
        from handlers.promotion_admin_handlers import process_promotion_name, PromotionWizardStates
        msg = make_message(text="Coleccion Primavera")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_name)
        await process_promotion_name(msg, fsm)

        data = await fsm.get_data()
        assert data["name"] == "Coleccion Primavera"
        state = await fsm.get_state()
        assert state == PromotionWizardStates.waiting_description
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Paso 2 de 5" in text


class TestProcessPromotionDescription:
    """Tests para process_promotion_description — paso 2: descripcion."""

    async def test_skip_sets_none_and_advances(self, make_message, make_fsm_context):
        """/skip establece description=None y avanza a selecting_source."""
        from handlers.promotion_admin_handlers import process_promotion_description, PromotionWizardStates
        msg = make_message(text="/skip")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_description)
        await process_promotion_description(msg, fsm)

        data = await fsm.get_data()
        assert data["description"] is None
        state = await fsm.get_state()
        assert state == PromotionWizardStates.selecting_source
        msg.answer.assert_called_once()

    async def test_with_description_saves_and_advances(self, make_message, make_fsm_context):
        """Descripcion textual se guarda y avanza a selecting_source."""
        from handlers.promotion_admin_handlers import process_promotion_description, PromotionWizardStates
        msg = make_message(text="Una experiencia exclusiva de contenido curado")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_description)
        await process_promotion_description(msg, fsm)

        data = await fsm.get_data()
        assert data["description"] == "Una experiencia exclusiva de contenido curado"
        state = await fsm.get_state()
        assert state == PromotionWizardStates.selecting_source
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Paso 3 de 5" in text


class TestSelectPackageSource:
    """Tests para select_package_source — seleccion de paquete.
    Ported to 1-service pattern (get_service(PromotionService) only + delegate for packages in wizard) + pure UI helpers.
    Arch-enforcer note addressed. Precedent item 8/9/34.
    """

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_no_packages_shows_empty_message(self, mock_get_service, make_callback, make_fsm_context):
        """Sin paquetes disponibles, muestra mensaje y boton manual."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_available_packages_for_promo_wizard.return_value = []

        cb = make_callback(data="promo_select_package")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.selecting_source)

        from handlers.promotion_admin_handlers import select_package_source
        await select_package_source(cb, fsm)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay colecciones" in text
        # State should NOT have changed (stays in selecting_source)
        state = await fsm.get_state()
        assert state == PromotionWizardStates.selecting_source

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_with_packages_advances_to_selecting_package(self, mock_get_service, make_callback, make_fsm_context):
        """Con paquetes disponibles, avanza a selecting_package."""
        from handlers.promotion_admin_handlers import select_package_source, PromotionWizardStates

        mock_pkg = model_mock(Package)
        mock_pkg.id = 1
        mock_pkg.name = "Test Package"
        mock_pkg.is_active = True
        mock_pkg.files = [MagicMock()]
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_available_packages_for_promo_wizard.return_value = [mock_pkg]

        cb = make_callback(data="promo_select_package")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.selecting_source)

        await select_package_source(cb, fsm)

        cb.message.edit_text.assert_called_once()
        state = await fsm.get_state()
        assert state == PromotionWizardStates.selecting_package
        cb.answer.assert_called_once()


class TestSelectManualFiles:
    """Tests para select_manual_files — entrada manual de archivos."""

    async def test_sets_waiting_manual_files_state(self, make_callback, make_fsm_context):
        """Establece estado waiting_manual_files y muestra instrucciones."""
        from handlers.promotion_admin_handlers import select_manual_files, PromotionWizardStates

        cb = make_callback(data="promo_manual_files")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.selecting_source)

        await select_manual_files(cb, fsm)

        state = await fsm.get_state()
        assert state == PromotionWizardStates.waiting_manual_files
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Paso 3 de 5" in text
        assert "archivos" in text.lower()
        cb.answer.assert_called_once()


class TestProcessManualFiles:
    """Tests para process_manual_files — procesar numero de archivos."""

    async def test_rejects_invalid_number(self, make_message, make_fsm_context):
        """Valor no numerico muestra error."""
        from handlers.promotion_admin_handlers import process_manual_files, PromotionWizardStates
        msg = make_message(text="quince")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_manual_files)
        await process_manual_files(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "numero valido" in text
        state = await fsm.get_state()
        assert state == PromotionWizardStates.waiting_manual_files

    async def test_rejects_negative_number(self, make_message, make_fsm_context):
        """Numero negativo muestra error."""
        from handlers.promotion_admin_handlers import process_manual_files, PromotionWizardStates
        msg = make_message(text="-5")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_manual_files)
        await process_manual_files(msg, fsm)

        msg.answer.assert_called_once()
        state = await fsm.get_state()
        assert state == PromotionWizardStates.waiting_manual_files

    async def test_accepts_zero(self, make_message, make_fsm_context):
        """Cero es valido y avanza a waiting_price."""
        from handlers.promotion_admin_handlers import process_manual_files, PromotionWizardStates
        msg = make_message(text="0")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_manual_files)
        await process_manual_files(msg, fsm)

        data = await fsm.get_data()
        assert data["manual_file_count"] == 0
        assert data["package_id"] is None
        state = await fsm.get_state()
        assert state == PromotionWizardStates.waiting_price

    async def test_accepts_valid_number_and_advances(self, make_message, make_fsm_context):
        """Numero valido guarda en state y avanza a waiting_price."""
        from handlers.promotion_admin_handlers import process_manual_files, PromotionWizardStates
        msg = make_message(text="15")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_manual_files)
        await process_manual_files(msg, fsm)

        data = await fsm.get_data()
        assert data["manual_file_count"] == 15
        assert data["package_id"] is None
        state = await fsm.get_state()
        assert state == PromotionWizardStates.waiting_price
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Paso 4 de 5" in text


class TestSelectPackageForPromotion:
    """Tests para select_package_for_promotion — seleccion de paquete en wizard."""

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_selects_package_and_advances_to_price(self, mock_get_service, make_callback, make_fsm_context):
        """Selecciona paquete, guarda en state y avanza a waiting_price."""
        mock_context = MagicMock()
        mock_get_service.return_value = mock_context

        cb = make_callback(data="promo_select_pkg:1")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.selecting_package)

        from handlers.promotion_admin_handlers import select_package_for_promotion
        from keyboards.callback_data import SelectPkgPromoCallback
        await select_package_for_promotion(cb, fsm, SelectPkgPromoCallback(pkg_id=42))

        data = await fsm.get_data()
        assert data["package_id"] == 42
        assert data["manual_file_count"] is None
        state = await fsm.get_state()
        assert state == PromotionWizardStates.waiting_price
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Paso 4 de 5" in text
        cb.answer.assert_called_once()


class TestProcessPromotionPrice:
    """Tests para process_promotion_price — paso 4: precio."""

    async def test_rejects_invalid_price(self, make_message, make_fsm_context):
        """Precio no numerico muestra error."""
        from handlers.promotion_admin_handlers import process_promotion_price, PromotionWizardStates
        msg = make_message(text="gratis")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_price)
        await process_promotion_price(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "numero valido" in text
        state = await fsm.get_state()
        assert state == PromotionWizardStates.waiting_price

    async def test_rejects_zero_or_negative(self, make_message, make_fsm_context):
        """Precio 0 o negativo muestra error."""
        from handlers.promotion_admin_handlers import process_promotion_price, PromotionWizardStates
        msg = make_message(text="0")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_price)
        await process_promotion_price(msg, fsm)

        msg.answer.assert_called_once()
        state = await fsm.get_state()
        assert state == PromotionWizardStates.waiting_price

    async def test_converts_to_cents_and_advances(self, make_message, make_fsm_context):
        """Precio valido se convierte a centavos y avanza a waiting_dates."""
        from handlers.promotion_admin_handlers import process_promotion_price, PromotionWizardStates
        msg = make_message(text="299")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_price)
        await process_promotion_price(msg, fsm)

        data = await fsm.get_data()
        assert data["price_mxn"] == 29900  # 299 * 100
        state = await fsm.get_state()
        assert state == PromotionWizardStates.waiting_dates
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Paso 5 de 5" in text


class TestPromotionNoDates:
    """Tests para promotion_no_dates — sin fechas de vigencia."""

    async def test_sets_dates_to_none_and_shows_confirmation(self, make_callback, make_fsm_context):
        """Establece start/end_date=None y llama a confirmacion."""
        cb = make_callback(data="promo_no_dates")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_dates)
        await fsm.update_data(name="Test", description="Desc", price_mxn=99900)

        from handlers.promotion_admin_handlers import promotion_no_dates
        await promotion_no_dates(cb, fsm)

        data = await fsm.get_data()
        assert data["start_date"] is None
        assert data["end_date"] is None
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "confirmar" in text.lower() or "Forjar" in text
        state = await fsm.get_state()
        assert state == PromotionWizardStates.confirming
        cb.answer.assert_called_once()


class TestProcessPromotionDates:
    """Tests para process_promotion_dates — procesar fechas."""

    async def test_valid_dates_calls_confirmation(self, make_message, make_fsm_context):
        """Fechas validas actualizan state y llaman a confirmacion."""
        msg = make_message(text="INICIO: 2026-04-01\nFIN: 2026-04-30")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_dates)
        await fsm.update_data(name="Test", description="Desc", price_mxn=99900)

        from handlers.promotion_admin_handlers import process_promotion_dates
        await process_promotion_dates(msg, fsm)

        data = await fsm.get_data()
        assert data["start_date"] is not None
        assert data["start_date"].strftime("%Y-%m-%d") == "2026-04-01"
        assert data["end_date"] is not None
        assert data["end_date"].strftime("%Y-%m-%d") == "2026-04-30"
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "confirmar" in text.lower() or "Forjar" in text

    async def test_only_start_date_is_accepted(self, make_message, make_fsm_context):
        """Solo INICIO sin FIN tambien es valido."""
        msg = make_message(text="INICIO: 2026-04-01")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_dates)
        await fsm.update_data(name="Test", description="Desc", price_mxn=99900)

        from handlers.promotion_admin_handlers import process_promotion_dates
        await process_promotion_dates(msg, fsm)

        data = await fsm.get_data()
        assert data["start_date"] is not None
        assert data["end_date"] is None

    async def test_invalid_format_shows_error(self, make_message, make_fsm_context):
        """Formato invalido muestra mensaje de error."""
        msg = make_message(text="INICIO: 01-04-2026")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_dates)

        from handlers.promotion_admin_handlers import process_promotion_dates
        await process_promotion_dates(msg, fsm)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Formato incorrecto" in text or "YYYY-MM-DD" in text

    async def test_empty_text_shows_error(self, make_message, make_fsm_context):
        """Texto vacio o sin formato valido muestra error."""
        msg = make_message(text="")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.waiting_dates)

        from handlers.promotion_admin_handlers import process_promotion_dates
        await process_promotion_dates(msg, fsm)

        msg.answer.assert_called_once()


class TestShowPromotionConfirmation:
    """Tests para show_promotion_confirmation — helper de confirmacion."""

    async def test_shows_confirmation_with_all_fields(self, make_callback, make_fsm_context):
        """Muestra confirmacion con nombre, descripcion, precio y archivos."""
        cb = make_callback(data="test")
        fsm = await make_fsm_context()
        await fsm.update_data(
            name="Coleccion Primavera",
            description="Una coleccion curada",
            price_mxn=99900,
            manual_file_count=5,
            package_id=None,
            start_date=None,
            end_date=None,
        )

        from handlers.promotion_admin_handlers import show_promotion_confirmation, PromotionWizardStates
        await show_promotion_confirmation(cb, fsm)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Coleccion Primavera" in text
        assert "Una coleccion curada" in text
        assert "$999.00 MXN" in text
        assert "5" in text
        assert "Sin fechas" in text
        state = await fsm.get_state()
        assert state == PromotionWizardStates.confirming

    async def test_shows_package_source(self, make_callback, make_fsm_context):
        """Con package_id, muestra texto de coleccion existente."""
        cb = make_callback(data="test")
        fsm = await make_fsm_context()
        await fsm.update_data(
            name="Test",
            description="Desc",
            price_mxn=50000,
            manual_file_count=None,
            package_id=1,
            start_date=None,
            end_date=None,
        )

        from handlers.promotion_admin_handlers import show_promotion_confirmation
        await show_promotion_confirmation(cb, fsm)

        text = cb.message.edit_text.call_args[0][0]
        assert "coleccion existente" in text.lower()

    async def test_with_dates(self, make_callback, make_fsm_context):
        """Muestra fechas cuando estan configuradas."""
        cb = make_callback(data="test")
        fsm = await make_fsm_context()
        await fsm.update_data(
            name="Test",
            description="Desc",
            price_mxn=29900,
            manual_file_count=1,
            package_id=None,
            start_date=datetime(2026, 4, 1),
            end_date=datetime(2026, 4, 30),
        )

        from handlers.promotion_admin_handlers import show_promotion_confirmation
        await show_promotion_confirmation(cb, fsm)

        text = cb.message.edit_text.call_args[0][0]
        assert "2026-04-01" in text
        assert "2026-04-30" in text

    async def test_with_message_target(self, make_message, make_fsm_context):
        """Cuando target es Message, usa msg.answer en vez de edit_text."""
        msg = make_message(text="test")
        fsm = await make_fsm_context()
        await fsm.update_data(
            name="Test",
            description="Desc",
            price_mxn=10000,
            manual_file_count=1,
        )

        from handlers.promotion_admin_handlers import show_promotion_confirmation
        await show_promotion_confirmation(msg, fsm)

        msg.answer.assert_called_once()
        msg.edit_text.assert_not_called()


class TestConfirmCreatePromotion:
    """Tests para confirm_create_promotion — creacion final."""

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_creates_promotion_successfully(self, mock_get_service, make_callback, make_fsm_context):
        """Crea la promocion y muestra mensaje de exito."""
        mock_promo = model_mock(Promotion)
        mock_promo.name = "Coleccion Primavera"
        mock_promo.price_display = "$999.00 MXN"
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.create_promotion.return_value = mock_promo

        cb = make_callback(data="confirm_create_promotion")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.confirming)
        await fsm.update_data(
            name="Coleccion Primavera",
            description="Una coleccion curada",
            package_id=1,
            manual_file_count=None,
            price_mxn=99900,
            created_by=123456789,
            start_date=None,
            end_date=None,
        )

        from handlers.promotion_admin_handlers import confirm_create_promotion
        await confirm_create_promotion(cb, fsm)

        mock_promo_svc.create_promotion.assert_called_once_with(
            name="Coleccion Primavera",
            description="Una coleccion curada",
            package_id=1,
            manual_file_count=None,
            price_mxn=99900,
            created_by=123456789,
            start_date=None,
            end_date=None,
        )
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "forjada" in text.lower()
        assert "Coleccion Primavera" in text
        state = await fsm.get_state()
        assert state is None
        cb.answer.assert_called_once()

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_handles_creation_exception(self, mock_get_service, make_callback, make_fsm_context):
        """Cuando create_promotion lanza excepcion, muestra error."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.create_promotion.side_effect = Exception("DB error")

        cb = make_callback(data="confirm_create_promotion")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.confirming)
        await fsm.update_data(name="Test", price_mxn=10000)

        from handlers.promotion_admin_handlers import confirm_create_promotion
        await confirm_create_promotion(cb, fsm)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "inesperado" in text.lower()
        state = await fsm.get_state()
        assert state is None
        cb.answer.assert_called_once()

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_clears_state_on_success(self, mock_get_service, make_callback, make_fsm_context):
        """Limpia el estado FSM despues de crear."""
        mock_promo = model_mock(Promotion)
        mock_promo.name = "Test"
        mock_promo.price_display = "$100 MXN"
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.create_promotion.return_value = mock_promo

        cb = make_callback(data="confirm_create_promotion")
        fsm = await make_fsm_context()
        await fsm.set_state(PromotionWizardStates.confirming)
        await fsm.update_data(name="Test", price_mxn=10000)

        from handlers.promotion_admin_handlers import confirm_create_promotion
        await confirm_create_promotion(cb, fsm)

        state = await fsm.get_state()
        assert state is None


class TestListPromotions:
    """Tests para list_promotions — listado de promociones."""

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_shows_empty_message_when_no_promotions(self, mock_get_service, make_callback):
        """Cuando no hay promociones, muestra mensaje de vacio."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_all_promotions.return_value = []

        cb = make_callback(data="list_promotions")

        from handlers.promotion_admin_handlers import list_promotions
        await list_promotions(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "vacio" in text.lower()
        cb.answer.assert_called_once()

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_lists_promotions_with_status(self, mock_get_service, make_callback):
        """Muestra promociones con su estado activo/inactivo."""
        mock_active = model_mock(Promotion)
        mock_active.name = "Promo Activa"
        mock_active.is_active = True
        mock_active.price_display = "$999.00 MXN"

        mock_inactive = model_mock(Promotion)
        mock_inactive.name = "Promo Inactiva"
        mock_inactive.is_active = False
        mock_inactive.price_display = "$500.00 MXN"

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_all_promotions.return_value = [mock_active, mock_inactive]

        cb = make_callback(data="list_promotions")

        from handlers.promotion_admin_handlers import list_promotions
        await list_promotions(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Promo Activa" in text
        assert "Promo Inactiva" in text
        assert "$999.00 MXN" in text
        assert "$500.00 MXN" in text
        cb.answer.assert_called_once()

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_calls_get_all_promotions(self, mock_get_service, make_callback):
        """Llama a get_all_promotions sin filtro."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_all_promotions.return_value = []

        cb = make_callback(data="list_promotions")

        from handlers.promotion_admin_handlers import list_promotions
        await list_promotions(cb)

        mock_promo_svc.get_all_promotions.assert_called_once()


class TestTogglePromotion:
    """Tests para toggle_promotion — activar/desactivar promocion."""

    @patch("handlers.promotion_admin_handlers.promotion_admin_detail")
    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_toggles_active_to_inactive(self, mock_get_service, mock_detail, make_callback):
        """Promocion activa se desactiva."""
        mock_promo = model_mock(Promotion)
        mock_promo.id = 1
        mock_promo.is_active = True
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion.return_value = mock_promo

        from keyboards.callback_data import TogglePromoCallback
        cb = make_callback(data=TogglePromoCallback(promo_id=1).pack())

        from handlers.promotion_admin_handlers import toggle_promotion
        await toggle_promotion(cb, TogglePromoCallback(promo_id=1))

        mock_promo_svc.update_promotion.assert_called_once_with(1, is_active=False)
        cb.answer.assert_called_with("Experiencia desactivada")
        mock_detail.assert_called_once()

    @patch("handlers.promotion_admin_handlers.promotion_admin_detail")
    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_toggles_inactive_to_active(self, mock_get_service, mock_detail, make_callback):
        """Promocion inactiva se activa."""
        mock_promo = model_mock(Promotion)
        mock_promo.id = 1
        mock_promo.is_active = False
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion.return_value = mock_promo

        from keyboards.callback_data import TogglePromoCallback
        cb = make_callback(data=TogglePromoCallback(promo_id=1).pack())

        from handlers.promotion_admin_handlers import toggle_promotion
        await toggle_promotion(cb, TogglePromoCallback(promo_id=1))

        mock_promo_svc.update_promotion.assert_called_once_with(1, is_active=True)
        cb.answer.assert_called_with("Experiencia activada")

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_promotion_not_found_shows_alert(self, mock_get_service, make_callback):
        """Promocion no encontrada muestra alerta."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion.return_value = None

        from keyboards.callback_data import TogglePromoCallback
        cb = make_callback(data=TogglePromoCallback(promo_id=999).pack())

        from handlers.promotion_admin_handlers import toggle_promotion
        await toggle_promotion(cb, TogglePromoCallback(promo_id=999))

        cb.answer.assert_called_once_with("Experiencia no encontrada", show_alert=True)
        mock_promo_svc.update_promotion.assert_not_called()


class TestDeletePromotionConfirm:
    """Tests para delete_promotion_confirm — eliminacion de promocion."""

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_unconfirmed_shows_confirmation(self, mock_get_service, make_callback):
        """Sin confirmacion, muestra dialogo de confirmacion."""
        mock_context = MagicMock()
        mock_get_service.return_value = mock_context

        from keyboards.callback_data import PromoDeleteCallback
        cb_data = PromoDeleteCallback(promo_id=1, confirmed=False)
        cb = make_callback(data=cb_data.pack())

        from handlers.promotion_admin_handlers import delete_promotion_confirm
        await delete_promotion_confirm(cb, cb_data)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "seguro" in text.lower()
        cb.answer.assert_called_once()

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_confirmed_deletes_successfully(self, mock_get_service, make_callback):
        """Confirmado y eliminacion exitosa, muestra mensaje."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.delete_promotion.return_value = True

        from keyboards.callback_data import PromoDeleteCallback
        cb_data = PromoDeleteCallback(promo_id=1, confirmed=True)
        cb = make_callback(data=cb_data.pack())

        from handlers.promotion_admin_handlers import delete_promotion_confirm
        await delete_promotion_confirm(cb, cb_data)

        mock_promo_svc.delete_promotion.assert_called_once_with(1)
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "eliminada" in text.lower()
        cb.answer.assert_called_once()

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_confirmed_delete_fails_shows_error(self, mock_get_service, make_callback):
        """Confirmado pero eliminacion falla, muestra error."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.delete_promotion.return_value = False

        from keyboards.callback_data import PromoDeleteCallback
        cb_data = PromoDeleteCallback(promo_id=1, confirmed=True)
        cb = make_callback(data=cb_data.pack())

        from handlers.promotion_admin_handlers import delete_promotion_confirm
        await delete_promotion_confirm(cb, cb_data)

        mock_promo_svc.delete_promotion.assert_called_once_with(1)
        text = cb.message.edit_text.call_args[0][0]
        assert "eliminar" in text.lower() or "pudo" in text.lower()


class TestShowPendingInterests:
    """Tests para show_pending_interests — intereses pendientes."""

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_empty_shows_empty_message(self, mock_get_service, make_callback):
        """Sin intereses pendientes, muestra mensaje."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_pending_interests.return_value = []

        cb = make_callback(data="promo_pending_interests")

        from handlers.promotion_admin_handlers import show_pending_interests
        await show_pending_interests(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay" in text
        cb.answer.assert_called_once()

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_shows_pending_interests_list(self, mock_get_service, make_callback):
        """Muestra lista de intereses pendientes."""
        mock_interest = MagicMock()
        mock_interest.id = 1
        mock_interest.username = "testuser"
        mock_interest.first_name = "Test"
        mock_interest.user_id = 123
        mock_interest.promotion = MagicMock()
        mock_interest.promotion.name = "Promo Test"

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_pending_interests.return_value = [mock_interest]

        cb = make_callback(data="promo_pending_interests")

        from handlers.promotion_admin_handlers import show_pending_interests
        await show_pending_interests(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "testuser" in text
        assert "Promo Test" in text
        cb.answer.assert_called_once()

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_calls_get_pending_interests(self, mock_get_service, make_callback):
        """Llama a get_pending_interests()."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_pending_interests.return_value = []

        cb = make_callback(data="promo_pending_interests")

        from handlers.promotion_admin_handlers import show_pending_interests
        await show_pending_interests(cb)

        mock_promo_svc.get_pending_interests.assert_called_once()


class TestShowPromotionInterests:
    """Tests para show_promotion_interests — intereses de promocion especifica."""

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_promotion_not_found_shows_alert(self, mock_get_service, make_callback):
        """Promocion no encontrada muestra alerta."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion.return_value = None

        from keyboards.callback_data import PromoInterestsCallback
        cb = make_callback(data=PromoInterestsCallback(promo_id=999).pack())

        from handlers.promotion_admin_handlers import show_promotion_interests
        await show_promotion_interests(cb, PromoInterestsCallback(promo_id=999))

        cb.answer.assert_called_once_with("Experiencia no encontrada", show_alert=True)

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_no_pending_shows_empty_message(self, mock_get_service, make_callback):
        """Sin intereses pendientes, muestra mensaje."""
        mock_promo = model_mock(Promotion)
        mock_promo.name = "Promo Test"
        mock_promo.interests = []

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion.return_value = mock_promo

        from keyboards.callback_data import PromoInterestsCallback
        cb = make_callback(data=PromoInterestsCallback(promo_id=1).pack())

        from handlers.promotion_admin_handlers import show_promotion_interests
        await show_promotion_interests(cb, PromoInterestsCallback(promo_id=1))

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay expresiones pendientes" in text
        cb.answer.assert_called_once()

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_shows_pending_interests_for_promotion(self, mock_get_service, make_callback):
        """Muestra intereses pendientes de la promocion."""
        from models.models import InterestStatus

        mock_interest = MagicMock()
        mock_interest.id = 1
        mock_interest.username = "testuser"
        mock_interest.first_name = "Test"
        mock_interest.user_id = 123
        mock_interest.status = InterestStatus.PENDING

        mock_promo = model_mock(Promotion)
        mock_promo.name = "Promo Test"
        mock_promo.interests = [mock_interest]

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion.return_value = mock_promo

        from keyboards.callback_data import PromoInterestsCallback
        cb = make_callback(data=PromoInterestsCallback(promo_id=1).pack())

        from handlers.promotion_admin_handlers import show_promotion_interests
        await show_promotion_interests(cb, PromoInterestsCallback(promo_id=1))

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "1" in text
        cb.answer.assert_called_once()


class TestShowBlockedUsers:
    """Tests para show_blocked_users — usuarios bloqueados."""

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_empty_shows_empty_message(self, mock_get_service, make_callback):
        """Sin usuarios bloqueados, muestra mensaje."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_blocked_users.return_value = []

        cb = make_callback(data="promo_blocked_users")

        from handlers.promotion_admin_handlers import show_blocked_users
        await show_blocked_users(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "No hay" in text
        cb.answer.assert_called_once()

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_shows_blocked_users_list(self, mock_get_service, make_callback):
        """Muestra lista de usuarios bloqueados."""
        mock_blocked = MagicMock()
        mock_blocked.user_id = 123
        mock_blocked.username = "blockeduser"
        mock_blocked.first_name = "Blocked"

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_blocked_users.return_value = [mock_blocked]

        cb = make_callback(data="promo_blocked_users")

        from handlers.promotion_admin_handlers import show_blocked_users
        await show_blocked_users(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "blockeduser" in text or "Blocked" in text
        cb.answer.assert_called_once()


class TestUnblockUser:
    """Tests para unblock_user — desbloqueo de usuario."""

    @patch("handlers.promotion_admin_handlers.show_blocked_users")
    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_unblock_successful_redirects(self, mock_get_service, mock_show_blocked, make_callback):
        """Desbloqueo exitoso redirige a show_blocked_users."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.unblock_user.return_value = True

        from keyboards.callback_data import UnblockUserCallback
        cb = make_callback(data=UnblockUserCallback(user_id=123).pack())

        from handlers.promotion_admin_handlers import unblock_user
        await unblock_user(cb, UnblockUserCallback(user_id=123))

        mock_promo_svc.unblock_user.assert_called_once_with(123)
        cb.answer.assert_called_once_with("✅ Restriccion levantada")
        mock_show_blocked.assert_called_once()

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_unblock_failure_shows_error(self, mock_get_service, make_callback):
        """Desbloqueo fallido muestra alerta de error."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.unblock_user.return_value = False

        from keyboards.callback_data import UnblockUserCallback
        cb = make_callback(data=UnblockUserCallback(user_id=999).pack())

        from handlers.promotion_admin_handlers import unblock_user
        await unblock_user(cb, UnblockUserCallback(user_id=999))

        cb.answer.assert_called_once_with("Error al levantar restriccion", show_alert=True)


class TestShowBlockedUserDetail:
    """Tests para show_blocked_user_detail — detalle de usuario bloqueado."""

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_shows_blocked_user_info(self, mock_get_service, make_callback):
        """Muestra informacion detallada del usuario bloqueado."""
        mock_blocked = MagicMock()
        mock_blocked.user_id = 123
        mock_blocked.username = "testuser"
        mock_blocked.first_name = "Test"
        mock_blocked.is_permanent = True
        mock_blocked.reason = "Comportamiento inapropiado"
        mock_blocked.blocked_at = datetime(2026, 3, 15, 10, 30)

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_blocked_user_info.return_value = mock_blocked

        from keyboards.callback_data import BlockedUserDetailCallback
        cb = make_callback(data=BlockedUserDetailCallback(user_id=123).pack())

        from handlers.promotion_admin_handlers import show_blocked_user_detail
        await show_blocked_user_detail(cb, BlockedUserDetailCallback(user_id=123))

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "123" in text
        assert "testuser" in text
        assert "Comportamiento inapropiado" in text
        assert "2026-03-15 10:30" in text
        cb.answer.assert_called_once()

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_user_not_found_shows_alert(self, mock_get_service, make_callback):
        """Usuario bloqueado no encontrado muestra alerta."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_blocked_user_info.return_value = None

        from keyboards.callback_data import BlockedUserDetailCallback
        cb = make_callback(data=BlockedUserDetailCallback(user_id=999).pack())

        from handlers.promotion_admin_handlers import show_blocked_user_detail
        await show_blocked_user_detail(cb, BlockedUserDetailCallback(user_id=999))

        cb.answer.assert_called_once_with("Visitante no encontrado", show_alert=True)


class TestPromotionAdminDetail:
    """Tests para promotion_admin_detail — detalle de promocion admin."""

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_shows_promotion_detail(self, mock_get_service, make_callback):
        """Muestra detalle completo de la promocion con intereses."""
        from models.models import InterestStatus, PromotionStatus

        mock_interest = MagicMock()
        mock_interest.status = InterestStatus.PENDING

        mock_promo = model_mock(Promotion)
        mock_promo.name = "Promo Test"
        mock_promo.description = "Descripcion"
        mock_promo.price_display = "$999.00 MXN"
        mock_promo.is_active = True
        mock_promo.is_available = True
        mock_promo.file_count = 5
        mock_promo.interests = [mock_interest]

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion.return_value = mock_promo

        from keyboards.callback_data import PromoDetailCallback
        cb = make_callback(data=PromoDetailCallback(promo_id=1).pack())

        from handlers.promotion_admin_handlers import promotion_admin_detail
        await promotion_admin_detail(cb, PromoDetailCallback(promo_id=1))

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Promo Test" in text
        assert "$999.00 MXN" in text
        assert "1" in text
        cb.answer.assert_called_once()

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_promotion_not_found_shows_alert(self, mock_get_service, make_callback):
        """Promocion no encontrada muestra alerta."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion.return_value = None

        from keyboards.callback_data import PromoDetailCallback
        cb = make_callback(data=PromoDetailCallback(promo_id=999).pack())

        from handlers.promotion_admin_handlers import promotion_admin_detail
        await promotion_admin_detail(cb, PromoDetailCallback(promo_id=999))

        cb.answer.assert_called_once_with("Experiencia no encontrada", show_alert=True)


class TestPromotionStats:
    """Tests para promotion_stats — estadisticas de promociones."""

    @patch("handlers.promotion_admin_handlers.get_service")
    async def test_shows_statistics(self, mock_get_service, make_callback):
        """Muestra estadisticas completas."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion_stats.return_value = {
            "active_promotions": 3,
            "total_promotions": 10,
            "pending_interests": 5,
            "attended_interests": 8,
            "total_interests": 15,
            "blocked_users": 2,
        }

        cb = make_callback(data="promo_stats")

        from handlers.promotion_admin_handlers import promotion_stats
        await promotion_stats(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "3" in text
        assert "10" in text
        assert "5" in text
        assert "8" in text
        assert "15" in text
        assert "2" in text
        cb.answer.assert_called_once()


# Necesario para evitar NameError en la referencia de clase inline de los handlers
from handlers.promotion_admin_handlers import PromotionWizardStates


class TestPromotionAdminPureHelpers:
    """Pure helper tests for promotion admin wizard/list/detail (import inside, no @patch on puros).
    10+ cases covering exact UI strings, cbs, Paso X de 5, Lucien, empty, buttons, price, file texts.
    Precedent item 8/9/34 + port for 1-service.
    """

    def test_build_promotion_confirm_text_basic(self):
        from handlers.promotion_admin_handlers import build_promotion_confirm_text_and_keyboard
        data = {"name": "Test Exp", "description": "Desc", "price_mxn": 29900, "manual_file_count": 5}
        text, kb = build_promotion_confirm_text_and_keyboard(data)
        assert "🎩 <b>Lucien:</b>" in text
        assert "✨ <b>Test Exp</b>" in text
        assert "📝 Desc" in text
        assert "💰 <b>Inversion:</b> $299.00 MXN" in text
        assert "📁 <b>Archivos:</b> 5 (definido manualmente)" in text
        assert "✅ Forjar experiencia" in str(kb.inline_keyboard)

    def test_build_promotion_confirm_text_with_package(self):
        from handlers.promotion_admin_handlers import build_promotion_confirm_text_and_keyboard
        data = {"name": "Pkg Exp", "description": None, "price_mxn": 10000, "package_id": 42}
        text, kb = build_promotion_confirm_text_and_keyboard(data)
        assert "Sin descripcion" in text
        assert "📁 <b>Contenido:</b> De coleccion existente" in text
        assert "$100.00 MXN" in text

    def test_build_promotion_confirm_text_no_files(self):
        from handlers.promotion_admin_handlers import build_promotion_confirm_text_and_keyboard
        data = {"name": "Empty", "price_mxn": 0}
        text, _ = build_promotion_confirm_text_and_keyboard(data)
        assert "No especificado" in text

    def test_compute_file_text_for_confirm(self):
        from handlers.promotion_admin_handlers import compute_file_text_for_confirm
        assert "definido manualmente" in compute_file_text_for_confirm(3, None)
        assert "De coleccion existente" in compute_file_text_for_confirm(None, 1)
        assert "No especificado" in compute_file_text_for_confirm(None, None)

    def test_compute_promotion_price_display(self):
        from handlers.promotion_admin_handlers import compute_promotion_price_display
        assert compute_promotion_price_display(99900) == "$999.00 MXN"
        assert "0.00" in compute_promotion_price_display(0)

    def test_compute_dates_text(self):
        from handlers.promotion_admin_handlers import compute_dates_text
        from datetime import datetime
        assert "Sin fechas" in compute_dates_text(None, None)
        d = datetime(2026, 4, 1)
        assert "Inicio: 2026-04-01" in compute_dates_text(d, None)

    def test_build_promotion_step_text(self):
        from handlers.promotion_admin_handlers import build_promotion_step_text
        txt = build_promotion_step_text(3, "Definir el contenido", "Elija...", "15")
        assert "Paso 3 de 5" in txt
        assert "Lucien" not in txt  # header by caller
        assert "Ejemplo: 15" in txt

    def test_build_promotion_list_entry_and_button(self):
        from handlers.promotion_admin_handlers import build_promotion_list_entry_and_button
        p = model_mock(Promotion)
        p.is_active = True
        p.name = "Test Promo"
        p.price_display = "$100.00 MXN"
        p.id = 1
        entry, btns = build_promotion_list_entry_and_button(p)
        assert "✅ <b>Test Promo</b>" in entry
        assert "💰 $100.00 MXN" in entry
        assert "PromoDetailCallback" in str(btns) or len(btns) > 0

    def test_build_promotion_detail_text_and_keyboard(self):
        from handlers.promotion_admin_handlers import build_promotion_detail_text_and_keyboard
        p = model_mock(Promotion)
        p.name = "DetailP"
        p.description = None
        p.price_display = "$50.00 MXN"
        p.is_active = True
        p.is_available = True
        p.file_count = 3
        p.interests = []
        p.id = 99
        text, kb = build_promotion_detail_text_and_keyboard(p)
        assert "✨ <b>DetailP</b>" in text
        assert "Sin descripcion" in text
        assert "📦 Archivos: 3" in text
        assert "Estado: ✅ Activa" in text

    def test_build_interest_list_text_and_buttons_emptyish(self):
        from handlers.promotion_admin_handlers import build_interest_list_text_and_buttons
        text, buttons = build_interest_list_text_and_buttons([])
        assert "Expresiones pendientes: 0" in text
        assert len(buttons) == 1  # only back

    def test_build_blocked_user_text_and_keyboard(self):
        from handlers.promotion_admin_handlers import build_blocked_user_text_and_keyboard
        u = MagicMock()
        u.username = "baduser"
        u.first_name = None
        u.user_id = 7
        text, buttons = build_blocked_user_text_and_keyboard([u])
        assert "🚫 <b>Visitantes restringidos: 1</b>" in text
        assert "baduser" in text
        assert len(buttons) >= 2

    def test_pure_helpers_import_inside_no_side(self):
        # ensure importable standalone
        from handlers.promotion_admin_handlers import compute_promotion_price_display
        assert "$1.00" in compute_promotion_price_display(100)
