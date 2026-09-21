"""Unit tests for Free→VIP first journey: welcome keyboard + Free game tip + Mes routing."""

from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest
from aiogram.types import InlineKeyboardButton

from keyboards.inline_keyboards import free_entry_welcome_keyboard, social_links_keyboard
from services.game_service import GameService
from services.store_service import StoreService
from utils.lucien_voice import LucienVoice

pytestmark = [pytest.mark.unit]


class TestFreeEntryWelcomeCopy:
    def test_welcome_has_cta_without_daily_limits(self):
        text = LucienVoice.free_entry_welcome("Los Kinkys")
        assert "Los Kinkys" in text
        assert "minijuegos" in text.lower() or "Minijuegos" in text or "jugando" in text
        assert "tienda" in text.lower()
        assert "El Diván" in text or "Diván" in text
        # Sin cifras de límites diarios en welcome
        assert "dados 10" not in text
        assert "trivia 5" not in text
        assert "2500" not in text

    def test_game_menu_vip_tip_has_numbers(self):
        tip = LucienVoice.free_game_menu_vip_tip()
        assert "dados 10" in tip
        assert "trivia 5" in tip
        assert "dados 20" in tip
        assert "trivia 10" in tip
        assert "Mes a Su Lado" in tip

    def test_store_soft_bridge_mentions_mes_and_price(self):
        cta = LucienVoice.store_soft_bridge_vip_cta()
        assert "Mes a Su Lado" in cta
        assert "2500" in cta
        assert "Diván" in cta or "El Diván" in cta


class TestFreeEntryWelcomeKeyboard:
    def test_includes_game_menu_and_shop_callbacks(self):
        kb = free_entry_welcome_keyboard()
        callbacks = []
        urls = []
        for row in kb.inline_keyboard:
            for btn in row:
                assert isinstance(btn, InlineKeyboardButton)
                if btn.callback_data:
                    callbacks.append(btn.callback_data)
                if btn.url:
                    urls.append(btn.url)
        assert "game_menu" in callbacks
        assert "shop" in callbacks
        assert "shop_mes_a_su_lado" in callbacks
        # Social links preserved
        social = social_links_keyboard()
        social_urls = {b.url for row in social.inline_keyboard for b in row if b.url}
        assert social_urls.issubset(set(urls))

    def test_can_omit_mes_button(self):
        kb = free_entry_welcome_keyboard(include_mes=False)
        callbacks = [b.callback_data for row in kb.inline_keyboard for b in row if b.callback_data]
        assert "game_menu" in callbacks
        assert "shop" in callbacks
        assert "shop_mes_a_su_lado" not in callbacks


class TestGameMenuFreeTip:
    def _menu_data(self, *, is_vip: bool):
        return {
            "title": "Minijuegos",
            "subtitle": "Elige tu diversión",
            "dice_description": "Lanza y gana",
            "remaining_dice": 5,
            "limit_dice": 10,
            "trivia_description": "Responde",
            "remaining_trivia": 3,
            "limit_trivia": 5,
            "footer": "¡Diviértete!",
            "is_vip": is_vip,
        }

    @patch("handlers.game_user_handlers.get_service")
    async def test_free_user_sees_vip_tip(self, mock_get_service, make_callback):
        mock_instance = create_autospec(GameService, spec_set=True, instance=True)
        mock_get_service.return_value.__enter__.return_value = mock_instance
        mock_instance.get_menu_data.return_value = self._menu_data(is_vip=False)
        mock_instance.get_active_special_info.return_value = None
        cb = make_callback(data="game_menu")

        from handlers.game_user_handlers import game_menu

        await game_menu(cb)

        text = cb.message.edit_text.call_args[0][0]
        assert "dados 10" in text
        assert "Mes a Su Lado" in text

    @patch("handlers.game_user_handlers.get_service")
    async def test_vip_user_skips_free_tip(self, mock_get_service, make_callback):
        mock_instance = create_autospec(GameService, spec_set=True, instance=True)
        mock_get_service.return_value.__enter__.return_value = mock_instance
        mock_instance.get_menu_data.return_value = self._menu_data(is_vip=True)
        mock_instance.get_active_special_info.return_value = None
        cb = make_callback(data="game_menu")

        from handlers.game_user_handlers import game_menu

        await game_menu(cb)

        text = cb.message.edit_text.call_args[0][0]
        assert "dados 10" not in text
        assert "Mes a Su Lado" not in text


class TestShopMesASuLadoRouting:
    @patch("handlers.store_user_handlers.get_service")
    async def test_opens_product_detail_when_found(self, mock_get_service, make_callback):
        mock_svc = create_autospec(StoreService, spec_set=True, instance=True)
        mock_get_service.return_value.__enter__.return_value = mock_svc
        product = MagicMock()
        product.id = 42
        mock_svc.get_product_by_name.return_value = product
        mock_svc.get_product_detail_context.return_value = {
            "product": product,
            "name": "Mes a Su Lado",
            "desc": "VIP",
            "price": 2500,
            "balance": 100,
            "stock_text": "OK",
            "file_count": 0,
            "tier": "",
            "list_price": None,
            "monthly_cap_available": True,
            "tier_lock_message": None,
            "can_preview": False,
            "is_available": True,
            "effective_price": 2500,
            "tier_unlocked": True,
        }
        cb = make_callback(data="shop_mes_a_su_lado")
        cb.message.edit_text = AsyncMock()

        with patch(
            "handlers.store_user_handlers._product_detail_card_and_buttons",
            return_value=("detalle Mes a Su Lado", []),
        ):
            from handlers.store_user_handlers import shop_mes_a_su_lado

            await shop_mes_a_su_lado(cb)

        mock_svc.get_product_by_name.assert_called_once_with("Mes a Su Lado")
        mock_svc.get_product_detail_context.assert_called_once_with(42, 123456789)
        cb.message.edit_text.assert_called_once()
        assert "Mes a Su Lado" in cb.message.edit_text.call_args[0][0]

    @patch("handlers.store_user_handlers.shop_menu", new_callable=AsyncMock)
    @patch("handlers.store_user_handlers.get_service")
    async def test_falls_back_to_shop_when_missing(
        self, mock_get_service, mock_shop_menu, make_callback
    ):
        mock_svc = create_autospec(StoreService, spec_set=True, instance=True)
        mock_get_service.return_value.__enter__.return_value = mock_svc
        mock_svc.get_product_by_name.return_value = None
        cb = make_callback(data="shop_mes_a_su_lado")

        from handlers.store_user_handlers import shop_mes_a_su_lado

        await shop_mes_a_su_lado(cb)

        mock_shop_menu.assert_awaited_once_with(cb)
