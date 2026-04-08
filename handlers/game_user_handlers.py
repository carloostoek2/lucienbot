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
    trivia_vip_result_keyboard
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

    text = (
        f"🎩 Lucien: <b>{data['title']}</b>\n\n"
        f"{data['subtitle']}\n\n"
        f"<b>Dados:</b> {data['dice_description']}\n"
        f"<i>{data['remaining_dice']} de {data['limit_dice']} disponibles</i>\n\n"
        f"<b>Trivia:</b> {data['trivia_description']}\n"
        f"<i>{data['remaining_trivia']} de {data['limit_trivia']} disponibles</i>\n\n"
        f"{data['footer']}"
    )

    await callback.message.edit_text(text, reply_markup=game_menu_keyboard())
    await callback.answer()
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

    # Información de descuento por racha
    discount_info = data.get('discount_info')
    discount_text = ""
    if discount_info:
        needed = max(0, discount_info['required_streak'] - data['current_streak'])
        discount_text = f"\n\n🎁 <b>Promoción por racha:</b>\n"
        discount_text += f"• Racha requerida: {discount_info['required_streak']} ({needed} más para desbloquear)\n"
        discount_text += f"• Descuentos disponibles: {discount_info['available_codes']} de {discount_info['total_codes']}"
        if discount_info.get('user_has_code'):
            discount_text += f"\n• Tu código: <code>{discount_info['user_code']}</code>"

    text = (
        f"<b>{data['title']}</b>{streak_text}\n\n"
        f"{data['intro']}\n\n"
        f"<i>{counter_text}</i>{discount_text}\n\n"
        f"❓ <b>Pregunta:</b> {question['q']}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=trivia_keyboard(question, question_idx),
        parse_mode="HTML"
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

    # Construir mensaje enriquecido si hay descuento
    message = result['message']
    discount = result.get('discount_code')
    if discount and discount.get('code'):
        message += f"\n\n🎁 <b>¡DESCUENTO DESBLOQUEADO!</b>\n\n"
        message += f"📋 <b>Código:</b> <code>{discount['code']}</code>\n"
        message += f"💰 <b>Descuento:</b> {discount['discount_percentage']}% en {discount['promotion_name']}\n\n"
        message += "<i>Usa este código al comprar la promoción.</i>"

    await callback.message.edit_text(
        message,
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

    # Construir mensaje enriquecido si hay descuento
    message = result['message']
    discount = result.get('discount_code')
    if discount and discount.get('code'):
        message += f"\n\n🎁 <b>¡DESCUENTO DESBLOQUEADO!</b>\n\n"
        message += f"📋 <b>Código:</b> <code>{discount['code']}</code>\n"
        message += f"💰 <b>Descuento:</b> {discount['discount_percentage']}% en {discount['promotion_name']}\n\n"
        message += "<i>Usa este código al comprar la promoción.</i>"

    await callback.message.edit_text(
        message,
        reply_markup=trivia_vip_result_keyboard()
    )
    await callback.answer()
    logger.info(f"game_user_handlers - trivia_vip_answer - {user_id} - correct:{result['correct']}, besitos:{result['besitos']}")
