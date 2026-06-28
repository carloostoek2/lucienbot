"""
Tests unitarios para promotion_user_handlers.

Cubre handlers de ofertas/promociones para usuarios:
- offers_menu: menu principal de ofertas
- offers_catalog: catalogo de promociones disponibles
- view_offer_detail: detalle de promocion
- express_interest: sistema "Me Interesa"
- my_offers_history: historial de intereses
- notify_admins_about_interest: notificacion a administradores
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from tests.helpers import model_mock
from models.models import Promotion

pytestmark = [pytest.mark.unit]


def _mock_promo_ctx(mock_get_service):
    """Mock get_service(PromotionService) context manager con autospec."""
    from services.promotion_service import PromotionService

    svc = create_autospec(PromotionService, spec_set=True, instance=True)
    mock_get_service.return_value.__enter__.return_value = svc
    return svc


class TestOffersMenu:
    """Tests para offers_menu — menu principal de ofertas/promociones."""

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_shows_menu_with_counts(self, mock_get_service, make_callback):
        """Muestra el menu con conteo de promociones e intereses."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_available_promotions.return_value = [MagicMock(), MagicMock()]
        mock_promo_svc.get_user_interest_history.return_value = [MagicMock()]

        cb = make_callback(data="offers")

        from handlers.promotion_user_handlers import offers_menu

        await offers_menu(cb)

        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_calls_service_methods(self, mock_get_service, make_callback):
        """Llama a get_available_promotions y get_user_interest_history."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_available_promotions.return_value = []
        mock_promo_svc.get_user_interest_history.return_value = []

        cb = make_callback(data="offers")

        from handlers.promotion_user_handlers import offers_menu

        await offers_menu(cb)

        mock_promo_svc.get_available_promotions.assert_called_once()
        mock_promo_svc.get_user_interest_history.assert_called_once_with(123456789)
        cb.answer.assert_called_once()


class TestOffersCatalog:
    """Tests para offers_catalog — catalogo de promociones disponibles."""

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_empty_catalog_shows_empty_message(self, mock_get_service, make_callback):
        """Cuando no hay promociones, muestra mensaje de vacio."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_available_promotions.return_value = []

        cb = make_callback(data="offers_catalog")

        from handlers.promotion_user_handlers import offers_catalog

        await offers_catalog(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "vacio" in text.lower()
        cb.answer.assert_called_once()

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_shows_promotions_with_details(self, mock_get_service, make_callback):
        """Muestra promociones con nombre, precio, archivos y descripcion."""
        mock_promo = model_mock(Promotion)
        mock_promo.id = 1
        mock_promo.name = "Coleccion Primavera"
        mock_promo.price_display = "$999.00 MXN"
        mock_promo.file_count = 5
        mock_promo.description = "Una coleccion curada de momentos exclusivos"

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_available_promotions.return_value = [mock_promo]
        mock_promo_svc.is_user_blocked.return_value = False

        cb = make_callback(data="offers_catalog")

        from handlers.promotion_user_handlers import offers_catalog

        await offers_catalog(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Coleccion Primavera" in text
        assert "$999.00 MXN" in text
        assert "5" in text
        assert "Una coleccion curada" in text
        cb.answer.assert_called_once()

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_shows_blocked_message(self, mock_get_service, make_callback):
        """Usuario bloqueado ve mensaje de restriccion."""
        mock_promo = model_mock(Promotion)
        mock_promo.id = 1
        mock_promo.name = "Test Promo"
        mock_promo.price_display = "$100.00 MXN"
        mock_promo.file_count = 1
        mock_promo.description = "Descripcion"

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_available_promotions.return_value = [mock_promo]
        mock_promo_svc.is_user_blocked.return_value = True

        cb = make_callback(data="offers_catalog")

        from handlers.promotion_user_handlers import offers_catalog

        await offers_catalog(cb)

        text = cb.message.edit_text.call_args[0][0]
        assert "restricciones" in text.lower()

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_truncates_long_description(self, mock_get_service, make_callback):
        """Descripcion larga se trunca a 50 caracteres."""
        long_desc = "a" * 100
        mock_promo = model_mock(Promotion)
        mock_promo.id = 1
        mock_promo.name = "Test"
        mock_promo.price_display = "$100 MXN"
        mock_promo.file_count = 1
        mock_promo.description = long_desc

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_available_promotions.return_value = [mock_promo]
        mock_promo_svc.is_user_blocked.return_value = False

        cb = make_callback(data="offers_catalog")

        from handlers.promotion_user_handlers import offers_catalog

        await offers_catalog(cb)

        text = cb.message.edit_text.call_args[0][0]
        assert "..." in text


class TestViewOfferDetail:
    """Tests para view_offer_detail — detalle de una promocion."""

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_promotion_not_found_shows_alert(self, mock_get_service, make_callback):
        """Promocion no encontrada muestra alerta."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion.return_value = None

        cb = make_callback(data="view_offer:999")

        from handlers.promotion_user_handlers import view_offer_detail
        from keyboards.callback_data import ViewOfferCallback

        await view_offer_detail(cb, ViewOfferCallback(promo_id=999))

        cb.answer.assert_called_once_with(
            "Esa oferta parece haberse... desvanecido.", show_alert=True
        )

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_promotion_not_available_shows_alert(self, mock_get_service, make_callback):
        """Promocion no disponible muestra alerta."""
        mock_promo = model_mock(Promotion)
        mock_promo.is_available = False
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion.return_value = mock_promo

        cb = make_callback(data="view_offer:1")

        from handlers.promotion_user_handlers import view_offer_detail
        from keyboards.callback_data import ViewOfferCallback

        await view_offer_detail(cb, ViewOfferCallback(promo_id=1))

        cb.answer.assert_called_once_with("Esa oportunidad ya no esta disponible.", show_alert=True)

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_shows_promotion_detail(self, mock_get_service, make_callback):
        """Muestra detalle completo de la promocion."""
        mock_promo = model_mock(Promotion)
        mock_promo.id = 1
        mock_promo.name = "Coleccion Primavera"
        mock_promo.description = "Una coleccion curada"
        mock_promo.price_display = "$999.00 MXN"
        mock_promo.file_count = 3
        mock_promo.is_available = True

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion.return_value = mock_promo
        mock_promo_svc.has_user_expressed_interest.return_value = False
        mock_promo_svc.is_user_blocked.return_value = False

        cb = make_callback(data="view_offer:1")

        from handlers.promotion_user_handlers import view_offer_detail
        from keyboards.callback_data import ViewOfferCallback

        await view_offer_detail(cb, ViewOfferCallback(promo_id=1))

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Coleccion Primavera" in text
        assert "$999.00 MXN" in text
        assert "3" in text
        cb.answer.assert_called_once()

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_shows_has_interest_message(self, mock_get_service, make_callback):
        """Usuario ya expreso interes, muestra mensaje diferente."""
        mock_promo = model_mock(Promotion)
        mock_promo.id = 1
        mock_promo.name = "Test Promo"
        mock_promo.price_display = "$100.00 MXN"
        mock_promo.file_count = 1
        mock_promo.is_available = True

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion.return_value = mock_promo
        mock_promo_svc.has_user_expressed_interest.return_value = True
        mock_promo_svc.is_user_blocked.return_value = False

        cb = make_callback(data="view_offer:1")

        from handlers.promotion_user_handlers import view_offer_detail
        from keyboards.callback_data import ViewOfferCallback

        await view_offer_detail(cb, ViewOfferCallback(promo_id=1))

        text = cb.message.edit_text.call_args[0][0]
        assert "notificada" in text.lower()

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_shows_blocked_message(self, mock_get_service, make_callback):
        """Usuario bloqueado ve mensaje de limitaciones."""
        mock_promo = model_mock(Promotion)
        mock_promo.id = 1
        mock_promo.name = "Test"
        mock_promo.price_display = "$100 MXN"
        mock_promo.file_count = 1
        mock_promo.is_available = True

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion.return_value = mock_promo
        mock_promo_svc.has_user_expressed_interest.return_value = False
        mock_promo_svc.is_user_blocked.return_value = True

        cb = make_callback(data="view_offer:1")

        from handlers.promotion_user_handlers import view_offer_detail
        from keyboards.callback_data import ViewOfferCallback

        await view_offer_detail(cb, ViewOfferCallback(promo_id=1))

        text = cb.message.edit_text.call_args[0][0]
        assert "limitaciones" in text.lower()

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_calls_service_with_correct_id(self, mock_get_service, make_callback):
        """Llama a get_promotion con el ID correcto."""
        mock_promo = model_mock(Promotion)
        mock_promo.is_available = True
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_promotion.return_value = mock_promo
        mock_promo_svc.has_user_expressed_interest.return_value = False
        mock_promo_svc.is_user_blocked.return_value = False

        cb = make_callback(data="view_offer:42")

        from handlers.promotion_user_handlers import view_offer_detail
        from keyboards.callback_data import ViewOfferCallback

        await view_offer_detail(cb, ViewOfferCallback(promo_id=42))

        mock_promo_svc.get_promotion.assert_called_once_with(42)


class TestExpressInterest:
    """Tests para express_interest — sistema 'Me Interesa'."""

    @patch("handlers.promotion_user_handlers.notify_admins_about_interest")
    @patch("handlers.promotion_user_handlers.get_service")
    async def test_blocked_user_shows_alert(self, mock_get_service, mock_notify, make_callback):
        """Usuario bloqueado no puede expresar interes."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.is_user_blocked.return_value = True

        cb = make_callback(data="offer_interest:1")
        bot = AsyncMock()

        from handlers.promotion_user_handlers import express_interest
        from keyboards.callback_data import OfferInterestCallback

        await express_interest(cb, OfferInterestCallback(promo_id=1), bot)

        cb.answer.assert_called_once_with(
            "No puede expresar interes. Hay restricciones en su cuenta.", show_alert=True
        )
        mock_promo_svc.express_interest.assert_not_called()
        mock_notify.assert_not_called()

    @patch("handlers.promotion_user_handlers.notify_admins_about_interest")
    @patch("handlers.promotion_user_handlers.get_service")
    async def test_already_expressed_shows_alert(
        self, mock_get_service, mock_notify, make_callback
    ):
        """Usuario ya expreso interes, muestra alerta."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.is_user_blocked.return_value = False
        mock_promo_svc.has_user_expressed_interest.return_value = True

        cb = make_callback(data="offer_interest:1")
        bot = AsyncMock()

        from handlers.promotion_user_handlers import express_interest
        from keyboards.callback_data import OfferInterestCallback

        await express_interest(cb, OfferInterestCallback(promo_id=1), bot)

        cb.answer.assert_called_once_with(
            "Ya ha expresado interes en esta experiencia.", show_alert=True
        )
        mock_notify.assert_not_called()

    @patch("handlers.promotion_user_handlers.notify_admins_about_interest")
    @patch("handlers.promotion_user_handlers.get_service")
    async def test_unsuccessful_interest_shows_error(
        self, mock_get_service, mock_notify, make_callback
    ):
        """express_interest retorna fallo, muestra error."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.is_user_blocked.return_value = False
        mock_promo_svc.has_user_expressed_interest.return_value = False
        mock_promo_svc.express_interest.return_value = (False, "Error al registrar", None)

        cb = make_callback(data="offer_interest:1")
        bot = AsyncMock()

        from handlers.promotion_user_handlers import express_interest
        from keyboards.callback_data import OfferInterestCallback

        await express_interest(cb, OfferInterestCallback(promo_id=1), bot)

        cb.answer.assert_called_once_with("Error al registrar", show_alert=True)
        mock_notify.assert_not_called()

    @patch("handlers.promotion_user_handlers.notify_admins_about_interest")
    @patch("handlers.promotion_user_handlers.get_service")
    @patch("handlers.promotion_user_handlers.bot_config")
    async def test_successful_interest_with_creator(
        self, mock_config, mock_get_service, mock_notify, make_callback
    ):
        """Interes exitoso con CREATOR_USERNAME configurado."""
        mock_interest = MagicMock()
        mock_interest.id = 1
        mock_interest.username = "testuser"

        mock_promo = model_mock(Promotion)
        mock_promo.name = "Coleccion Primavera"
        mock_promo.price_display = "$999.00 MXN"

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.is_user_blocked.return_value = False
        mock_promo_svc.has_user_expressed_interest.return_value = False
        mock_promo_svc.express_interest.return_value = (True, "OK", mock_interest)
        mock_promo_svc.get_promotion.return_value = mock_promo
        mock_config.CREATOR_USERNAME = "dianita"

        cb = make_callback(data="offer_interest:1")
        bot = AsyncMock()

        from handlers.promotion_user_handlers import express_interest
        from keyboards.callback_data import OfferInterestCallback

        await express_interest(cb, OfferInterestCallback(promo_id=1), bot)

        mock_notify.assert_called_once_with(bot, mock_interest, mock_promo)
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Coleccion Primavera" in text
        assert "registrado" in text.lower()
        cb.answer.assert_called_once_with("Interes registrado")

    @patch("handlers.promotion_user_handlers.notify_admins_about_interest")
    @patch("handlers.promotion_user_handlers.get_service")
    @patch("handlers.promotion_user_handlers.bot_config")
    async def test_successful_interest_no_creator(
        self, mock_config, mock_get_service, mock_notify, make_callback
    ):
        """Sin CREATOR_USERNAME, no muestra boton de contacto."""
        mock_interest = MagicMock()
        mock_interest.id = 1
        mock_interest.username = "testuser"

        mock_promo = model_mock(Promotion)
        mock_promo.name = "Test Promo"
        mock_promo.price_display = "$100.00 MXN"

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.is_user_blocked.return_value = False
        mock_promo_svc.has_user_expressed_interest.return_value = False
        mock_promo_svc.express_interest.return_value = (True, "OK", mock_interest)
        mock_promo_svc.get_promotion.return_value = mock_promo
        mock_config.CREATOR_USERNAME = ""

        cb = make_callback(data="offer_interest:1")
        bot = AsyncMock()

        from handlers.promotion_user_handlers import express_interest
        from keyboards.callback_data import OfferInterestCallback

        await express_interest(cb, OfferInterestCallback(promo_id=1), bot)

        text = cb.message.edit_text.call_args[0][0]
        assert "Contactar" not in text
        mock_notify.assert_called_once()

    @patch("handlers.promotion_user_handlers.notify_admins_about_interest")
    @patch("handlers.promotion_user_handlers.get_service")
    async def test_calls_express_interest_with_user_data(
        self, mock_get_service, mock_notify, make_callback, db_session
    ):
        """Llama a express_interest con datos correctos del usuario (usa servicio real)."""
        # Reduction: real PromotionService instead of MagicMock for promo_svc methods (post Item4 reduce mocks)
        from models.models import Promotion, PromotionStatus
        from services.promotion_service import PromotionService

        promo = Promotion(
            name="Test Promo",
            description="desc",
            price_mxn=10000,
            is_active=True,
            status=PromotionStatus.ACTIVE,
        )
        db_session.add(promo)
        db_session.commit()
        db_session.refresh(promo)

        real_svc = PromotionService(db_session)
        mock_context = MagicMock()
        mock_context.__enter__.return_value = real_svc
        mock_get_service.return_value = mock_context

        cb = make_callback(data=f"offer_interest:{promo.id}")
        bot = AsyncMock()

        from handlers.promotion_user_handlers import express_interest
        from keyboards.callback_data import OfferInterestCallback

        await express_interest(cb, OfferInterestCallback(promo_id=promo.id), bot)

        # Verify DB side effect (real flow) instead of mock call assert
        from models.models import PromotionInterest

        interest = (
            db_session.query(PromotionInterest)
            .filter(
                PromotionInterest.user_id == 123456789, PromotionInterest.promotion_id == promo.id
            )
            .first()
        )
        assert interest is not None
        assert interest.username == "testuser"
        assert interest.first_name == "Test"
        assert interest.last_name is None


class TestMyOffersHistory:
    """Tests para my_offers_history — historial de intereses."""

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_empty_history_shows_empty_message(self, mock_get_service, make_callback):
        """Sin historial, muestra mensaje de vacio."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_user_interest_history.return_value = []

        cb = make_callback(data="my_offers_history")

        from handlers.promotion_user_handlers import my_offers_history

        await my_offers_history(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "no ha expresado" in text.lower()
        cb.answer.assert_called_once()

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_shows_interests_with_status_and_date(self, mock_get_service, make_callback):
        """Muestra intereses con estado y fecha."""
        mock_promo = model_mock(Promotion)
        mock_promo.name = "Coleccion Primavera"

        mock_interest = MagicMock()
        mock_interest.promotion = mock_promo
        mock_interest.status = MagicMock()
        mock_interest.status.value = "pending"
        mock_interest.created_at = datetime(2026, 3, 15)

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_user_interest_history.return_value = [mock_interest]

        cb = make_callback(data="my_offers_history")

        from handlers.promotion_user_handlers import my_offers_history

        await my_offers_history(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Coleccion Primavera" in text
        assert "15/03/2026" in text
        assert "Pending" in text
        cb.answer.assert_called_once()

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_shows_attended_and_blocked_statuses(self, mock_get_service, make_callback):
        """Muestra diferentes estados con sus emojis."""
        mock_promo1 = model_mock(Promotion)
        mock_promo1.name = "Promo Atendida"
        mock_interest1 = MagicMock()
        mock_interest1.promotion = mock_promo1
        mock_interest1.status = MagicMock()
        mock_interest1.status.value = "attended"
        mock_interest1.created_at = datetime(2026, 3, 15)

        mock_promo2 = model_mock(Promotion)
        mock_promo2.name = "Promo Bloqueada"
        mock_interest2 = MagicMock()
        mock_interest2.promotion = mock_promo2
        mock_interest2.status = MagicMock()
        mock_interest2.status.value = "blocked"
        mock_interest2.created_at = datetime(2026, 3, 10)

        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_user_interest_history.return_value = [mock_interest1, mock_interest2]

        cb = make_callback(data="my_offers_history")

        from handlers.promotion_user_handlers import my_offers_history

        await my_offers_history(cb)

        text = cb.message.edit_text.call_args[0][0]
        assert "Promo Atendida" in text
        assert "Promo Bloqueada" in text
        assert "Attended" in text or "attended" in text
        assert "Blocked" in text or "blocked" in text

    @patch("handlers.promotion_user_handlers.get_service")
    async def test_calls_service_with_user_id(self, mock_get_service, make_callback):
        """Llama a get_user_interest_history con el user_id correcto."""
        mock_promo_svc = _mock_promo_ctx(mock_get_service)
        mock_promo_svc.get_user_interest_history.return_value = []

        cb = make_callback(data="my_offers_history")

        from handlers.promotion_user_handlers import my_offers_history

        await my_offers_history(cb)

        mock_promo_svc.get_user_interest_history.assert_called_once_with(123456789)


class TestNotifyAdminsAboutInterest:
    """Tests para notify_admins_about_interest — notificacion a administradores."""

    @patch("handlers.promotion_user_handlers.bot_config")
    async def test_sends_to_all_admins(self, mock_config):
        """Envia notificacion a cada admin en ADMIN_IDS."""
        mock_config.ADMIN_IDS = [111, 222, 333]
        bot = AsyncMock()
        mock_interest = MagicMock()
        mock_interest.username = "testuser"
        mock_interest.first_name = "Test"
        mock_interest.last_name = "User"
        mock_interest.user_id = 123456789
        mock_interest.created_at = datetime(2026, 3, 15, 10, 30)

        mock_promo = model_mock(Promotion)
        mock_promo.name = "Coleccion Primavera"
        mock_promo.price_display = "$999.00 MXN"

        from handlers.promotion_user_handlers import notify_admins_about_interest

        await notify_admins_about_interest(bot, mock_interest, mock_promo)

        assert bot.send_message.call_count == 3
        admin_ids_called = {call.kwargs["chat_id"] for call in bot.send_message.await_args_list}
        assert admin_ids_called == {111, 222, 333}

    @patch("handlers.promotion_user_handlers.bot_config")
    async def test_handles_send_failure_gracefully(self, mock_config):
        """Error al enviar a un admin no interrumpe el resto."""
        mock_config.ADMIN_IDS = [111, 222]
        bot = AsyncMock()
        bot.send_message.side_effect = [Exception("API error"), None]

        mock_interest = MagicMock()
        mock_interest.username = "testuser"
        mock_interest.first_name = "Test"
        mock_interest.last_name = None
        mock_interest.user_id = 123456789
        mock_interest.created_at = datetime(2026, 3, 15, 10, 30)

        mock_promo = model_mock(Promotion)
        mock_promo.name = "Promo"
        mock_promo.price_display = "$100.00 MXN"

        from handlers.promotion_user_handlers import notify_admins_about_interest

        await notify_admins_about_interest(bot, mock_interest, mock_promo)

        assert bot.send_message.call_count == 2

    @patch("handlers.promotion_user_handlers.bot_config")
    async def test_includes_interest_and_promo_details(self, mock_config):
        """El mensaje incluye detalles del interes y la promocion."""
        mock_config.ADMIN_IDS = [111]
        bot = AsyncMock()
        mock_interest = MagicMock()
        mock_interest.username = "testuser"
        mock_interest.first_name = "Test"
        mock_interest.last_name = "User"
        mock_interest.user_id = 123456789
        mock_interest.created_at = datetime(2026, 3, 15, 10, 30)

        mock_promo = model_mock(Promotion)
        mock_promo.name = "Promo Test"
        mock_promo.price_display = "$500.00 MXN"

        from handlers.promotion_user_handlers import notify_admins_about_interest

        await notify_admins_about_interest(bot, mock_interest, mock_promo)

        text = bot.send_message.call_args[1]["text"]
        assert "testuser" in text or "Test User" in text
        assert "Promo Test" in text
        assert "$500.00 MXN" in text
        assert "2026-03-15 10:30" in text

    @patch("handlers.promotion_user_handlers.bot_config")
    async def test_no_admins_no_errors(self, mock_config):
        """ADMIN_IDS vacio no causa errores."""
        mock_config.ADMIN_IDS = []
        bot = AsyncMock()
        mock_interest = MagicMock()
        mock_interest.username = "testuser"
        mock_interest.first_name = "Test"
        mock_interest.user_id = 123
        mock_interest.created_at = datetime(2026, 3, 15, 10, 30)

        mock_promo = model_mock(Promotion)
        mock_promo.name = "Promo"
        mock_promo.price_display = "$100 MXN"

        from handlers.promotion_user_handlers import notify_admins_about_interest

        await notify_admins_about_interest(bot, mock_interest, mock_promo)

        bot.send_message.assert_not_called()

    @patch("handlers.promotion_user_handlers.bot_config")
    async def test_uses_first_and_last_name_when_available(self, mock_config):
        """Usa first_name + last_name como user_display si estan disponibles."""
        mock_config.ADMIN_IDS = [111]
        bot = AsyncMock()
        mock_interest = MagicMock()
        mock_interest.username = "testuser"
        mock_interest.first_name = "Test"
        mock_interest.last_name = "User"
        mock_interest.user_id = 123456789
        mock_interest.created_at = datetime(2026, 3, 15, 10, 30)

        mock_promo = model_mock(Promotion)
        mock_promo.name = "Promo"
        mock_promo.price_display = "$100 MXN"

        from handlers.promotion_user_handlers import notify_admins_about_interest

        await notify_admins_about_interest(bot, mock_interest, mock_promo)

        text = bot.send_message.call_args[1]["text"]
        assert "Test User" in text

    @patch("handlers.promotion_user_handlers.bot_config")
    async def test_uses_username_fallback_when_no_name(self, mock_config):
        """Usa username como fallback si no hay first_name."""
        mock_config.ADMIN_IDS = [111]
        bot = AsyncMock()
        mock_interest = MagicMock()
        mock_interest.username = "someuser"
        mock_interest.first_name = None
        mock_interest.last_name = None
        mock_interest.user_id = 123456789
        mock_interest.created_at = datetime(2026, 3, 15, 10, 30)

        mock_promo = model_mock(Promotion)
        mock_promo.name = "Promo"
        mock_promo.price_display = "$100 MXN"

        from handlers.promotion_user_handlers import notify_admins_about_interest

        await notify_admins_about_interest(bot, mock_interest, mock_promo)

        text = bot.send_message.call_args[1]["text"]
        assert "someuser" in text
