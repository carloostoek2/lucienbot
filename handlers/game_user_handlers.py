"""
Handlers de Minijuegos - Lucien Bot

Maneja los flujos de usuario para dados y trivia.
"""
import logging

from aiogram import Router
from aiogram.types import CallbackQuery
from keyboards.callback_data import (
    TriviaAnswerCallback,
    TriviaVipAnswerCallback,
    TriviaSimpleAnswerCallback,
)
from keyboards.inline_keyboards import (
    game_menu_keyboard,
    dice_play_keyboard,
    trivia_keyboard,
    trivia_vip_keyboard,
    trivia_vip_result_keyboard,
    trivia_simple_keyboard,
    trivia_simple_result_keyboard
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
        special_info = service.get_active_special_info()

    special_button = None
    if special_info:
        special_button = (special_info['display_name'], "game_trivia_simple")

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
        text, reply_markup=game_menu_keyboard(special_button=special_button)
    )
    await callback.answer()
    if special_info:
        logger.info(f"game_user_handlers - game_menu - {user_id} - shown with special:{special_info['category_id']}")
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


@router.callback_query(TriviaAnswerCallback.filter())
async def trivia_answer(callback: CallbackQuery, callback_data: TriviaAnswerCallback):
    """Procesa respuesta de trivia"""
    user_id = callback.from_user.id
    answer_idx = callback_data.answer_idx
    question_idx = callback_data.question_idx

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


@router.callback_query(TriviaVipAnswerCallback.filter())
async def trivia_vip_answer(callback: CallbackQuery, callback_data: TriviaVipAnswerCallback):
    """Procesa respuesta de trivia VIP"""
    user_id = callback.from_user.id
    answer_idx = callback_data.answer_idx
    question_idx = callback_data.question_idx

    with get_service(GameService) as service:
        result = service.play_trivia_vip(user_id, question_idx, answer_idx)

    await callback.message.edit_text(
        result['message'],
        reply_markup=trivia_vip_result_keyboard()
    )
    await callback.answer()
    logger.info(f"game_user_handlers - trivia_vip_answer - {user_id} - correct:{result['correct']}, besitos:{result['besitos']}")


# ==================== TRIVIA ESPECIAL (PHASE 16) ====================

@router.callback_query(lambda c: c.data == "game_trivia_simple")
async def game_trivia_simple(callback: CallbackQuery):
    """Inicia trivia especial con pregunta aleatoria de categoria activa."""
    user_id = callback.from_user.id

    with get_service(GameService) as service:
        special_info = service.get_active_special_info()

        if not special_info:
            await callback.message.edit_text(
                "No hay dinamicas especiales activas en este momento.",
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

        category_id = special_info['category_id']
        data = service.get_trivia_simple_entry_data(user_id)

        if not data['can_play']:
            await callback.message.edit_text(
                data['limit_message'],
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

        question, question_idx = service.get_random_simple_question(user_id, category_id)

        if question is None:
            await callback.message.edit_text(
                "Los pergaminos especiales estan en el taller de Lucien.",
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return
        if question_idx == -2:
            exhausted_msg = service._select_template(
                service.TRIVIA_SIMPLE_TEMPLATES['deck_exhausted']
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
        streak_text = f"\n🔥 Racha special: {data['current_streak']}"

    text = (
        f"<b>{special_info['display_name']}</b>{streak_text}\n\n"
        f"{data['intro']}\n\n"
        f"<i>{counter_text}</i>\n\n"
        f"\U0001f3ad <b>Pregunta Especial:</b> {question['q']}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=trivia_simple_keyboard(question, question_idx)
    )
    await callback.answer()
    logger.info(f"game_user_handlers - game_trivia_simple - {user_id} - shown - category:{category_id}")


@router.callback_query(TriviaSimpleAnswerCallback.filter())
async def trivia_simple_answer(callback: CallbackQuery, callback_data: TriviaSimpleAnswerCallback):
    """Procesa respuesta de trivia especial."""
    user_id = callback.from_user.id
    answer_idx = callback_data.answer_idx
    question_idx = callback_data.question_idx

    if answer_idx < 0 or answer_idx > 3:
        await callback.answer("Opcion invalida.", show_alert=True)
        return

    with get_service(GameService) as service:
        special_info = service.get_active_special_info()
        if not special_info:
            await callback.message.edit_text(
                "La dinamica especial ha finalizado.",
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

        result = service.play_trivia_simple(
            user_id, question_idx, answer_idx, special_info['category_id']
        )

    await callback.message.edit_text(
        result['message'],
        reply_markup=trivia_simple_result_keyboard()
    )
    await callback.answer()
    logger.info(
        f"game_user_handlers - trivia_simple_answer - {user_id} - "
        f"correct:{result['correct']}, besitos:{result['besitos']}, "
        f"bonus:{result.get('streak_bonus', 0)}"
    )
