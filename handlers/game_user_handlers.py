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
    trivia_keyboard
)
from services.game_service import GameService

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(lambda c: c.data == "game_menu")
async def game_menu(callback: CallbackQuery):
    """Muestra menú de minijuegos"""
    service = GameService()
    user_id = callback.from_user.id

    # Mostrar límites del usuario
    limits = service.get_daily_limits(user_id)
    is_vip = service.is_user_vip(user_id)
    vip_status = "✨ VIP" if is_vip else "Visitante"

    await callback.message.edit_text(
        text=f"🎮 <b>Minijuegos</b> — {vip_status}\n\n"
             f"Límites de hoy:\n"
             f"• Dados: {limits['dice_limit']}\n"
             f"• Trivia: {limits['trivia_limit']}\n\n"
             f"Elige tu juego:",
        reply_markup=game_menu_keyboard()
    )
    await callback.answer()
    service.close()
    logger.info(f"game_user_handlers - game_menu - {user_id} - shown")


@router.callback_query(lambda c: c.data == "game_dice")
async def game_dice(callback: CallbackQuery):
    """Muestra interfaz de dados"""
    await callback.message.edit_text(
        text="🎲 <b>Juego de Dados</b>\n\n"
             "Lanza los dados y gana besitos:\n"
             "• Pares (ambos pares): +1 besito 💋\n"
             "• Dobles (iguales): +1 besito 💋",
        reply_markup=dice_play_keyboard()
    )
    await callback.answer()
    logger.info(f"game_user_handlers - game_dice - {callback.from_user.id} - shown")


@router.callback_query(lambda c: c.data == "dice_play")
async def dice_play(callback: CallbackQuery):
    """Procesa lanzamiento de dados"""
    user_id = callback.from_user.id
    service = GameService()

    result = service.play_dice_game(user_id)

    if result.get('limit_reached'):
        # Límite alcanzado - mensaje según tipo de usuario
        is_vip = service.is_user_vip(user_id)
        if is_vip:
            message = result['message']
        else:
            message = result['message'] + "\n\n" \
                     "¿Podrías ser parte del círculo íntimo? " \
                     "Los VIP tienen beneficios doubles..."
    else:
        # Resultado normal
        message = result['message']

        # Agregar contextual según victoria/derrota
        if result.get('won'):
            if result.get('win_type') == 'pairs':
                message += "\n\n¡Los números pares te favorecen!"
            else:
                message += "\n\n¡Exactamente igual! Doble suerte."
        else:
            message += "\n\nLucien observa...下次会有 más fortuna."

    await callback.message.edit_text(message, reply_markup=dice_play_keyboard())
    await callback.answer()
    service.close()


@router.callback_query(lambda c: c.data == "game_trivia")
async def game_trivia(callback: CallbackQuery):
    """Inicia trivia con pregunta aleatoria"""
    service = GameService()
    user_id = callback.from_user.id

    # Verificar límites
    can_play, played, limit, limit_msg = service.can_play(user_id, 'trivia')
    if not can_play:
        is_vip = service.is_user_vip(user_id)
        if not is_vip:
            limit_msg += "\n\n¿Imaginas tener el double de oportunidades?"
        await callback.message.edit_text(limit_msg, reply_markup=game_menu_keyboard())
        await callback.answer()
        service.close()
        return

    question, question_idx = service.get_random_question()

    if question is None:
        await callback.message.edit_text(
            "Las preguntas están en el taller de Lucien. Regresa más tarde.",
            reply_markup=game_menu_keyboard()
        )
        await callback.answer()
        service.close()
        return

    text = f"❓ <b>Trivia</b>\n\n" \
           f"Pregunta: {question['q']}\n\n" \
           f"Selecciona tu respuesta:"

    await callback.message.edit_text(
        text=text,
        reply_markup=trivia_keyboard(question, question_idx)
    )
    await callback.answer()
    service.close()
    logger.info(f"game_user_handlers - game_trivia - {user_id} - shown")


@router.callback_query(lambda c: c.data.startswith("trivia_answer_"))
async def trivia_answer(callback: CallbackQuery):
    """Procesa respuesta de trivia"""
    user_id = callback.from_user.id

    # Parse callback_data: trivia_answer_{answer_idx}_{question_idx}
    parts = callback.data.split("_")
    answer_idx = int(parts[2])
    question_idx = int(parts[3])

    service = GameService()
    result = service.play_trivia(user_id, question_idx, answer_idx)

    if result.get('limit_reached'):
        is_vip = service.is_user_vip(user_id)
        if not is_vip:
            result['message'] += "\n\nLos caminos de VIP siempre tienen más oportunidades..."
        await callback.message.edit_text(result['message'], reply_markup=game_menu_keyboard())
        await callback.answer()
        service.close()
        return

    await callback.message.edit_text(result['message'], reply_markup=game_menu_keyboard())
    await callback.answer()
    service.close()