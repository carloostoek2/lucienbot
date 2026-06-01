"""
Handlers de Administracion de Trivias Especiales - Lucien Bot

Handlers para gestion de categorias de trivia desde el panel admin.
Fase 16 - Trivias Especiales.
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.callback_data import TriviaCategoryActivateCallback
from services import TriviaCategoryService, get_service
from utils.admin import is_admin

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "admin_trivia_categories", lambda cb: is_admin(cb.from_user.id))
async def admin_trivia_categories_menu(callback: CallbackQuery):
    """Menu principal de gestion de categorias de trivia."""
    with get_service(TriviaCategoryService) as service:
        categories = service.discover_categories()
        active = service.get_active_category()

    text = "\U0001f3af <b>Mazos de Trivia</b>\n\n"
    if active:
        text += f"✨ <b>Activa:</b> {active['display_name']}\n\n"
    else:
        text += "\U0001f4ed <b>Sin categoria activa.</b> Usando mazo general.\n\n"

    buttons = []
    for cat in categories:
        is_active = active and active["category_id"] == cat["category_id"]
        btn_text = (
            f"{'✅ ' if is_active else ''}{cat['display_name']} ({cat['question_count']} preguntas)"
        )
        cb_data = TriviaCategoryActivateCallback(category_id=cat["category_id"]).pack()
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=cb_data)])

    if active:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="⛔ Desactivar categoria activa", callback_data="trivia_cat_deactivate"
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="\U0001f519 Volver a Trivias", callback_data="admin_trivia")]
    )

    await callback.message.edit_text(
        text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML"
    )
    await callback.answer()
    logger.info(
        f"trivia_admin_handlers - admin_trivia_categories_menu - {callback.from_user.id} - shown"
    )


@router.callback_query(
    TriviaCategoryActivateCallback.filter(), lambda cb: is_admin(cb.from_user.id)
)
async def trivia_category_activate(
    callback: CallbackQuery, callback_data: TriviaCategoryActivateCallback
):
    """Activa una categoria especial."""
    category_id = callback_data.category_id
    with get_service(TriviaCategoryService) as service:
        service.activate(category_id)
    await callback.answer(f"Categoria activada: {category_id}", show_alert=True)
    await admin_trivia_categories_menu(callback)
    logger.info(
        f"trivia_admin_handlers - trivia_category_activate - {callback.from_user.id} - category:{category_id}"
    )


@router.callback_query(F.data == "trivia_cat_deactivate", lambda cb: is_admin(cb.from_user.id))
async def trivia_category_deactivate(callback: CallbackQuery):
    """Desactiva la categoria activa."""
    with get_service(TriviaCategoryService) as service:
        service.deactivate()
    await callback.answer("Categoria desactivada. Usando mazo general.", show_alert=True)
    await admin_trivia_categories_menu(callback)
    logger.info(
        f"trivia_admin_handlers - trivia_category_deactivate - {callback.from_user.id} - deactivated"
    )
