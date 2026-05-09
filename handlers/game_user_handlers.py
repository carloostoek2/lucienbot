"""
Handlers de Minijuegos - Lucien Bot

Maneja los flujos de usuario para dados y trivia.
"""
import logging

from aiogram import Router
from aiogram.types import CallbackQuery
from keyboards.inline_keyboards import (
    game_menu_keyboard,
    dice_play_keyboard,
    trivia_keyboard,
    trivia_vip_keyboard,
    trivia_vip_result_keyboard,
    trivia_tematica_keyboard,
    trivia_tematica_result_keyboard
)
from services import get_service, GameService

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(lambda c: c.data == "game_menu")
async def game_menu(callback: CallbackQuery):
    """Muestra menú de minijuegos"""
    user_id = callback.from_user.id

    with get_service(GameService) as service:
        data = service.get_menu_data(user_id)
        tematica_info = service.get_active_tematica_info()

    tematica_button = None
    if tematica_info:
        tematica_button = (tematica_info['display_name'], "game_trivia_tematica")

    text = (
        f"🎩 Lucien: <b>{data['title']}</b>\n\n"
        f"{data['subtitle']}\n\n"
        f"<b>Dados:</b> {data['dice_description']}\n"
        f"<i>{data['remaining_dice']} de {data['limit_dice']} disponibles</i>\n\n"
        f"<b>Trivia:</b> {data['trivia_description']}\n"
        f"<i>{data['remaining_trivia']} de {data['limit_trivia']} disponibles</i>\n\n"
        f"{data['footer']}"
    )

    await callback.message.edit_text(
        text, reply_markup=game_menu_keyboard(tematica_button=tematica_button)
    )
    await callback.answer()
    if tematica_info:
        logger.info(f"game_user_handlers - game_menu - {user_id} - shown with tematica:{tematica_info['category_id']}")
    else:
        logger.info(f"game_user_handlers - game_menu - {user_id} - shown")


@router.callback_query(lambda c: c.data == "game_dice")
async def game_dice(callback: CallbackQuery):
    """Muestra interfaz de dados"""
    user_id = callback.from_user.id

    with get_service(GameService) as service:
        data = service.get_dice_entry_data(user_id)

    text = (
        f"<b>{data['title']}</b>\n\n"
        f"{data['intro']}\n\n"
        f"{data['rules']}\n\n"
        f"<i>Oportunidades restantes: {data['remaining']} de {data['limit']}</i>"
    )

    await callback.message.edit_text(text, reply_markup=dice_play_keyboard())
    await callback.answer()
    logger.info(f"game_user_handlers - game_dice - {user_id} - shown")


@router.callback_query(lambda c: c.data == "dice_play")
async def dice_play(callback: CallbackQuery):
    """Procesa lanzamiento de dados"""
    user_id = callback.from_user.id

    with get_service(GameService) as service:
        result = service.play_dice_game(user_id)

    await callback.message.edit_text(
        result['message'],
        reply_markup=dice_play_keyboard()
    )
    await callback.answer()
    logger.info(f"game_user_handlers - dice_play - {user_id} - completed")


@router.callback_query(lambda c: c.data == "game_trivia")
async def game_trivia(callback: CallbackQuery):
    """Inicia trivia con pregunta aleatoria"""
    user_id = callback.from_user.id

    with get_service(GameService) as service:
        data = service.get_trivia_entry_data(user_id)

        if not data['can_play']:
            await callback.message.edit_text(
                data['limit_message'],
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

        question, question_idx = service.get_random_question()

        if question is None:
            await callback.message.edit_text(
                "Las preguntas están en el taller de Lucien. Regresa más tarde.",
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

    counter_text = data['counter_template'].format(
        remaining=data['remaining'],
        limit=data['limit']
    )

    streak_text = ""
    if data['current_streak'] > 0:
        streak_text = f"\n🔥 Racha actual: {data['current_streak']}"

    text = (
        f"<b>{data['title']}</b>{streak_text}\n\n"
        f"{data['intro']}\n\n"
        f"<i>{counter_text}</i>\n\n"
        f"❓ <b>Pregunta:</b> {question['q']}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=trivia_keyboard(question, question_idx)
    )
    await callback.answer()
    logger.info(f"game_user_handlers - game_trivia - {user_id} - shown")


@router.callback_query(lambda c: c.data.startswith("trivia_answer_"))
async def trivia_answer(callback: CallbackQuery):
    """Procesa respuesta de trivia"""
    user_id = callback.from_user.id

    parts = callback.data.split("_")
    answer_idx = int(parts[2])
    question_idx = int(parts[3])

    with get_service(GameService) as service:
        result = service.play_trivia(user_id, question_idx, answer_idx)

    await callback.message.edit_text(
        result['message'],
        reply_markup=game_menu_keyboard()
    )
    await callback.answer()
    logger.info(f"game_user_handlers - trivia_answer - {user_id} - correct:{result['correct']}")


# ==================== TRIVIA VIP ====================

@router.callback_query(lambda c: c.data == "game_trivia_vip")
async def game_trivia_vip(callback: CallbackQuery):
    """Inicia trivia VIP con pregunta aleatoria"""
    user_id = callback.from_user.id

    with get_service(GameService) as service:
        data = service.get_trivia_vip_entry_data(user_id)

        if not data['can_play']:
            await callback.message.edit_text(
                data['limit_message'],
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

        question, question_idx = service.get_random_vip_question()

        if question is None:
            await callback.message.edit_text(
                "Las preguntas secretas están en el taller de Lucien. Regresa más tarde.",
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

    counter_text = data['counter_template'].format(
        remaining=data['remaining'],
        limit=data['limit']
    )

    streak_text = ""
    if data['current_streak'] > 0:
        streak_text = f"\n🔥 Tu racha VIP: {data['current_streak']}"

    text = (
        f"<b>{data['title']}</b>{streak_text}\n\n"
        f"{data['intro']}\n\n"
        f"<i>{counter_text}</i>\n\n"
        f"👑 <b>Pregunta Secreta:</b> {question['q']}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=trivia_vip_keyboard(question, question_idx)
    )
    await callback.answer()
    logger.info(f"game_user_handlers - game_trivia_vip - {user_id} - shown")


@router.callback_query(lambda c: c.data.startswith("trivia_vip_answer_"))
async def trivia_vip_answer(callback: CallbackQuery):
    """Procesa respuesta de trivia VIP"""
    user_id = callback.from_user.id

    parts = callback.data.split("_")
    answer_idx = int(parts[3])
    question_idx = int(parts[4])

    with get_service(GameService) as service:
        result = service.play_trivia_vip(user_id, question_idx, answer_idx)

    await callback.message.edit_text(
        result['message'],
        reply_markup=trivia_vip_result_keyboard()
    )
    await callback.answer()
    logger.info(f"game_user_handlers - trivia_vip_answer - {user_id} - correct:{result['correct']}, besitos:{result['besitos']}")


# ==================== TRIVIA TEMATICA (PHASE 16) ====================

@router.callback_query(lambda c: c.data == "game_trivia_tematica")
async def game_trivia_tematica(callback: CallbackQuery):
    """Inicia trivia tematica con pregunta aleatoria de categoria activa."""
    user_id = callback.from_user.id

    with get_service(GameService) as service:
        tematica_info = service.get_active_tematica_info()

        if not tematica_info:
            await callback.message.edit_text(
                "No hay dinamicas tematicas activas en este momento.",
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

        category_id = tematica_info['category_id']
        data = service.get_trivia_tematica_entry_data(user_id)

        if not data['can_play']:
            await callback.message.edit_text(
                data['limit_message'],
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

        question, question_idx = service.get_random_tematica_question(user_id, category_id)

        if question is None:
            await callback.message.edit_text(
                "Los pergaminos tematicos estan en el taller de Lucien.",
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return
        if question_idx == -2:
            exhausted_msg = service._select_template(
                service.TRIVIA_TEMATICA_TEMPLATES['deck_exhausted']
            )
            await callback.message.edit_text(
                exhausted_msg,
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

    counter_text = data['counter_template'].format(
        remaining=data['remaining'],
        limit=data['limit']
    )

    streak_text = ""
    if data['current_streak'] > 0:
        streak_text = f"\n🔥 Racha tematica: {data['current_streak']}"

    text = (
        f"<b>{tematica_info['display_name']}</b>{streak_text}\n\n"
        f"{data['intro']}\n\n"
        f"<i>{counter_text}</i>\n\n"
        f"\U0001f3ad <b>Pregunta Tematica:</b> {question['q']}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=trivia_tematica_keyboard(question, question_idx)
    )
    await callback.answer()
    logger.info(f"game_user_handlers - game_trivia_tematica - {user_id} - shown - category:{category_id}")


@router.callback_query(lambda c: c.data.startswith("trivia_tematica_answer_"))
async def trivia_tematica_answer(callback: CallbackQuery):
    """Procesa respuesta de trivia tematica."""
    user_id = callback.from_user.id

    parts = callback.data.split("_")
    answer_idx = int(parts[3])
    question_idx = int(parts[4])

    if answer_idx < 0 or answer_idx > 3:
        await callback.answer("Opcion invalida.", show_alert=True)
        return

    with get_service(GameService) as service:
        tematica_info = service.get_active_tematica_info()
        if not tematica_info:
            await callback.message.edit_text(
                "La dinamica tematica ha finalizado.",
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

        result = service.play_trivia_tematica(
            user_id, question_idx, answer_idx, tematica_info['category_id']
        )

    await callback.message.edit_text(
        result['message'],
        reply_markup=trivia_tematica_result_keyboard()
    )
    await callback.answer()
    logger.info(
        f"game_user_handlers - trivia_tematica_answer - {user_id} - "
        f"correct:{result['correct']}, besitos:{result['besitos']}, "
        f"bonus:{result.get('streak_bonus', 0)}"
    )
