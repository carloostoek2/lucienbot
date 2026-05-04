"""
Handlers de Minijuegos - Lucien Bot

Maneja los flujos de usuario para dados y trivia.
"""
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.inline_keyboards import (
    game_menu_keyboard,
    dice_play_keyboard,
    trivia_keyboard,
    trivia_vip_keyboard,
    trivia_vip_result_keyboard,
    discount_claim_keyboard,
    streak_choice_keyboard,
    streak_final_keyboard
)
from services import get_service, GameService

logger = logging.getLogger(__name__)

router = Router()


# Estados FSM para trivia con decisión de racha
class TriviaStreakStates(StatesGroup):
    waiting_streak_choice = State()
    streak_continue = State()  # Usuario eligió continuar, sigue jugando


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
                "🎩 Lucien:\n\n<i>Las preguntas están en el taller de Lucien.\nRegresa más tarde.</i>",
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return

    # Construir header con barra decorativa
    header = service._select_template(service.STREAK_TEMPLATES['entry_header'])

    # Construir línea de stats
    stats_line = f"🔥 Racha: {data['current_streak']}  •  📜 Intentos: {data['remaining']}/{data['limit']}"

    # Construir bloque de promoción si existe
    discount_info = data.get('discount_info')
    promotion_block = ""
    if discount_info and discount_info.get('promotion_id'):
        promo_header = service._select_template(service.STREAK_TEMPLATES['entry_promotion_bar'])
        promo_progress = service._build_streak_promotion_text(
            current_streak=data['current_streak'],
            required_streak=discount_info['required_streak'],
            discount=discount_info['discount_percentage'],
            time_remaining=discount_info.get('time_remaining')
        )
        no_promo_text = service._select_template(service.STREAK_TEMPLATES['entry_no_promotion'])
        promotion_block = f"\n{promo_header}\n{promo_progress}\n{no_promo_text}\n"

    # Construir texto final
    question_text = service._select_template(
        service.STREAK_TEMPLATES['entry_footer_question']
    ).format(question=question['q'])

    text = (
        f"{header}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{stats_line}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{promotion_block}"
        f"────────────────────────────\n"
        f"{question_text}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=trivia_keyboard(question, question_idx),
        parse_mode="HTML"
    )
    await callback.answer()
    logger.info(f"game_user_handlers - game_trivia - {user_id} - shown")


@router.callback_query(lambda c: c.data.startswith("trivia_answer_"))
async def trivia_answer(callback: CallbackQuery, state: FSMContext):
    """Procesa respuesta de trivia"""
    user_id = callback.from_user.id

    parts = callback.data.split("_")
    answer_idx = int(parts[2])
    question_idx = int(parts[3])

    # Verificar si está en modo streak_continue
    current_state = await state.get_state()
    is_streak_continue = current_state == TriviaStreakStates.streak_continue.state

    with get_service(GameService) as service:
        result = service.play_trivia(user_id, question_idx, answer_idx)

    message = result['message']
    tier_info = result.get('tier_info')

    # Caso especial: streak_continue + respuesta incorrecta = perder todo
    if is_streak_continue and not result['correct']:
        data = await state.get_data()
        config_id = data.get('current_config_id')
        tier_discount = data.get('current_tier_discount', 0)
        if config_id:
            with get_service(GameService) as svc:
                svc.invalidate_streak_code(user_id, config_id)
        await state.clear()
        keyboard = game_menu_keyboard()
        message = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>El silencio de una respuesta incorrecta es ensordecedor.</i>\n\n"
            f"Su descuento del <b>{tier_discount}%</b> se ha desvanecido.\n\n"
            "<i>La próximas preguntas esperarán su regreso.</i>"
        )
        await callback.message.edit_text(message, reply_markup=keyboard)
        await callback.answer()
        logger.info(f"game_user_handlers - trivia_answer - {user_id} - streak_continue_wrong")
        return

    # Caso especial: streak_continue + respuesta correcta sin nuevo tier = seguir jugando
    if is_streak_continue and result['correct'] and not tier_info:
        with get_service(GameService) as service:
            entry_data = service.get_trivia_entry_data(user_id)
            if not entry_data['can_play']:
                await state.clear()
                await callback.message.edit_text(
                    entry_data['limit_message'],
                    reply_markup=game_menu_keyboard()
                )
                await callback.answer()
                return

            question, question_idx = service.get_random_question()
            if question is None:
                await state.clear()
                await callback.message.edit_text(
                    "Las preguntas están en el taller de Lucien. Regresa más tarde.",
                    reply_markup=game_menu_keyboard()
                )
                await callback.answer()
                return

        data = await state.get_data()
        current_tier_streak = data.get('current_tier_streak', 0)
        next_tier_streak = data.get('next_tier_streak', 0) or (current_tier_streak + 5)

        # Incrementar streak acumulado en el estado
        new_streak = current_tier_streak + 1
        await state.update_data(current_tier_streak=new_streak)

        text = (
            f"🎯 <b>Continúa en su racha!</b>\n\n"
            f"Ha acumulado <b>{new_streak}</b> respuestas correctas.\n"
            f"Su próximo objetivo: <b>{next_tier_streak}</b> para el "
            f"<b>{data.get('next_tier_discount', 0)}%</b> de descuento.\n\n"
            f"Cuidado: si falla, perderá TODO el descuento acumulado.\n\n"
            f"❓ <b>Pregunta:</b> {question['q']}"
        )

        await state.set_state(TriviaStreakStates.streak_continue)

        keyboard = trivia_keyboard(question, question_idx)
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        logger.info(f"game_user_handlers - trivia_answer - {user_id} - streak_continue_correct:{new_streak}")
        return

    # Caso 1: Respuesta incorrecta (pierde TODO)
    if not result['correct']:
        keyboard = game_menu_keyboard()
        await callback.message.edit_text(message, reply_markup=keyboard)
        await callback.answer()
        logger.info(f"game_user_handlers - trivia_answer - {user_id} - wrong_answer streak_lost")
        return

    # Caso 2: Alcanzó un tier -需要进行选择
    if tier_info and tier_info.get('tier_reached'):
        current_tier = tier_info['current_tier']
        next_tier = tier_info.get('next_tier')
        is_final = tier_info.get('is_final', False)
        config_id = tier_info.get('config_id')

        current_discount = current_tier['discount']
        current_streak = current_tier['streak']

        # Caso 2a: Es el tier final (100% - GRATIS)
        if is_final:
            # Generar código 100% automáticamente
            with get_service(GameService) as service:
                discount = service._generate_tier_discount_code(user_id, config_id, 100)

            if discount and discount.get('code'):
                message += f"\n\n🏆 <b>¡DESCUENTO COMPLETO!</b>\n\n"
                message += f"📋 <b>Código:</b> <code>{discount['code']}</code>\n"
                message += f"💰 <b>Descuento:</b> 100% (GRATIS) en {discount['promotion_name']}\n\n"
                message += "<i>Usa este código para obtener el producto gratuitamente.</i>"
                keyboard = streak_final_keyboard()
            else:
                keyboard = game_menu_keyboard()
        else:
            # Caso 2b: Mostrar opciones de retirarse o continuar
            next_discount = next_tier['discount'] if next_tier else None
            tier_index = tier_info.get('tier_index', 1)

            message += f"\n\n🔥 <b>Nivel de descuento {tier_index}</b>\n\n"
            message += f"💰 Ha desbloqueado <b>{current_discount}%</b> de descuento.\n\n"
            message += "<i>¿Qué desea hacer?</i>"

            # Guardar estado para cuando regrese
            await state.update_data(
                streak_mode=True,
                current_tier_streak=current_streak,
                current_tier_discount=current_discount,
                current_config_id=config_id,
                next_tier_streak=next_tier['streak'] if next_tier else None,
                next_tier_discount=next_tier['discount'] if next_tier else None,
                tier_index=tier_index
            )
            await state.set_state(TriviaStreakStates.waiting_streak_choice)

            keyboard = streak_choice_keyboard(current_discount)

        await callback.message.edit_text(message, reply_markup=keyboard)
        await callback.answer()
        logger.info(f"game_user_handlers - trivia_answer - {user_id} - tier_reached:{current_discount}%")
        return

    # Caso 3: Respuesta correcta pero sin tier - volver al menú
    keyboard = game_menu_keyboard()
    await callback.message.edit_text(message, reply_markup=keyboard)
    await callback.answer()
    logger.info(f"game_user_handlers - trivia_answer - {user_id} - correct_no_tier")


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
        streak_text = f"\n🔥 Su racha VIP: {data['current_streak']}"

    # Información de descuento por racha
    discount_info = data.get('discount_info')
    discount_text = ""
    if discount_info:
        needed = max(0, discount_info['required_streak'] - data['current_streak'])
        discount_text = f"\n\n🎁 <b>Promoción por racha:</b>\n"
        discount_text += f"• Racha requerida: {discount_info['required_streak']} ({needed} más para desbloquear)\n"
        discount_text += f"• Descuentos disponibles: {discount_info['available_codes']} de {discount_info['total_codes']}"

        # Mostrar tiempo restante si es duración relativa
        if discount_info.get('time_remaining') and discount_info.get('is_duration_based'):
            discount_text += f"\n• ⏱️ Tiempo restante: {discount_info['time_remaining']}"

        if discount_info.get('user_has_code'):
            discount_text += f"\n• Su código: <code>{discount_info['user_code']}</code>"

    text = (
        f"<b>{data['title']}</b>{streak_text}\n\n"
        f"{data['intro']}\n\n"
        f"<i>{counter_text}</i>{discount_text}\n\n"
        f"👑 <b>Pregunta Secreta:</b> {question['q']}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=trivia_vip_keyboard(question, question_idx)
    )
    await callback.answer()
    logger.info(f"game_user_handlers - game_trivia_vip - {user_id} - shown")


@router.callback_query(lambda c: c.data.startswith("trivia_vip_answer_"))
async def trivia_vip_answer(callback: CallbackQuery, state: FSMContext):
    """Procesa respuesta de trivia VIP"""
    user_id = callback.from_user.id

    parts = callback.data.split("_")
    answer_idx = int(parts[3])
    question_idx = int(parts[4])

    # Verificar si está en modo streak_continue
    current_state = await state.get_state()
    is_streak_continue = current_state == TriviaStreakStates.streak_continue.state

    with get_service(GameService) as service:
        result = service.play_trivia_vip(user_id, question_idx, answer_idx)

    message = result['message']
    tier_info = result.get('tier_info')

    # Caso especial: streak_continue + respuesta incorrecta = perder todo
    if is_streak_continue and not result['correct']:
        data = await state.get_data()
        config_id = data.get('current_config_id')
        tier_discount = data.get('current_tier_discount', 0)
        if config_id:
            with get_service(GameService) as svc:
                svc.invalidate_streak_code(user_id, config_id)
        await state.clear()
        keyboard = game_menu_keyboard()
        message = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>El silencio de una respuesta incorrecta es ensordecedor.</i>\n\n"
            f"Su descuento del <b>{tier_discount}%</b> se ha desvanecido.\n\n"
            "<i>La próximas preguntas esperarán su regreso.</i>"
        )
        await callback.message.edit_text(message, reply_markup=keyboard)
        await callback.answer()
        logger.info(f"game_user_handlers - trivia_vip_answer - {user_id} - streak_continue_wrong")
        return

    # Caso especial: streak_continue + respuesta correcta sin nuevo tier = seguir jugando
    if is_streak_continue and result['correct'] and not tier_info:
        with get_service(GameService) as service:
            entry_data = service.get_trivia_vip_entry_data(user_id)
            if not entry_data['can_play']:
                await state.clear()
                await callback.message.edit_text(
                    entry_data['limit_message'],
                    reply_markup=game_menu_keyboard()
                )
                await callback.answer()
                return

            question, question_idx = service.get_random_vip_question()
            if question is None:
                await state.clear()
                await callback.message.edit_text(
                    "Las preguntas secretas están en el taller de Lucien. Regresa más tarde.",
                    reply_markup=game_menu_keyboard()
                )
                await callback.answer()
                return

        data = await state.get_data()
        current_tier_streak = data.get('current_tier_streak', 0)
        next_tier_streak = data.get('next_tier_streak', 0) or (current_tier_streak + 5)

        # Incrementar streak acumulado en el estado
        new_streak = current_tier_streak + 1
        await state.update_data(current_tier_streak=new_streak)

        text = (
            f"🎯 <b>Continúa en su racha!</b>\n\n"
            f"Ha acumulado <b>{new_streak}</b> respuestas correctas.\n"
            f"Su próximo objetivo: <b>{next_tier_streak}</b> para el "
            f"<b>{data.get('next_tier_discount', 0)}%</b> de descuento.\n\n"
            f"Cuidado: si falla, perderá TODO el descuento acumulado.\n\n"
            f"👑 <b>Pregunta Secreta:</b> {question['q']}"
        )

        await state.set_state(TriviaStreakStates.streak_continue)

        keyboard = trivia_vip_keyboard(question, question_idx)
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        logger.info(f"game_user_handlers - trivia_vip_answer - {user_id} - streak_continue_correct:{new_streak}")
        return

    # Caso 1: Respuesta incorrecta (pierde TODO)
    if not result['correct']:
        keyboard = game_menu_keyboard()
        await callback.message.edit_text(message, reply_markup=keyboard)
        await callback.answer()
        logger.info(f"game_user_handlers - trivia_vip_answer - {user_id} - wrong_answer streak_lost")
        return

    # Caso 2: Alcanzó un tier
    if tier_info and tier_info.get('tier_reached'):
        current_tier = tier_info['current_tier']
        next_tier = tier_info.get('next_tier')
        is_final = tier_info.get('is_final', False)
        config_id = tier_info.get('config_id')

        current_discount = current_tier['discount']
        current_streak = current_tier['streak']

        # Caso 2a: Es el tier final (100% - GRATIS)
        if is_final:
            with get_service(GameService) as service:
                discount = service._generate_tier_discount_code(user_id, config_id, 100)

            if discount and discount.get('code'):
                message += f"\n\n🏆 <b>¡DESCUENTO COMPLETO!</b>\n\n"
                message += f"📋 <b>Código:</b> <code>{discount['code']}</code>\n"
                message += f"💰 <b>Descuento:</b> 100% (GRATIS) en {discount['promotion_name']}\n\n"
                message += "<i>Usa este código para obtener el producto gratuitamente.</i>"
                keyboard = streak_final_keyboard()
            else:
                keyboard = game_menu_keyboard()
        else:
            # Caso 2b: Mostrar opciones
            next_discount = next_tier['discount'] if next_tier else None
            tier_index = tier_info.get('tier_index', 1)

            message += f"\n\n🔥 <b>Nivel de descuento {tier_index}</b>\n\n"
            message += f"💰 Ha desbloqueado <b>{current_discount}%</b> de descuento.\n\n"
            message += "<i>¿Qué desea hacer?</i>"

            await state.update_data(
                streak_mode=True,
                current_tier_streak=current_streak,
                current_tier_discount=current_discount,
                current_config_id=config_id,
                next_tier_streak=next_tier['streak'] if next_tier else None,
                next_tier_discount=next_tier['discount'] if next_tier else None,
                tier_index=tier_index,
                vip_mode=True
            )
            await state.set_state(TriviaStreakStates.waiting_streak_choice)

            keyboard = streak_choice_keyboard(current_discount)

        await callback.message.edit_text(message, reply_markup=keyboard)
        await callback.answer()
        logger.info(f"game_user_handlers - trivia_vip_answer - {user_id} - tier_reached:{current_discount}%")
        return

    # Caso 3: Correcto pero sin tier
    keyboard = trivia_vip_result_keyboard()
    await callback.message.edit_text(message, reply_markup=keyboard)
    await callback.answer()
    logger.info(f"game_user_handlers - trivia_vip_answer - {user_id} - correct_no_tier")


# ==================== STREAK DECISION HANDLERS ====================

@router.callback_query(F.data == "streak_retire", TriviaStreakStates.waiting_streak_choice)
async def streak_retire(callback: CallbackQuery, state: FSMContext):
    """Usuario elige retirarse con su descuento actual"""
    user_id = callback.from_user.id
    data = await state.get_data()

    config_id = data.get('current_config_id')
    discount_percentage = data.get('current_tier_discount')

    if not config_id or not discount_percentage:
        await callback.message.edit_text(
            "🎩 Lucien: Algo salió mal. Regresa al menú.",
            reply_markup=game_menu_keyboard()
        )
        await state.clear()
        await callback.answer()
        return

    with get_service(GameService) as service:
        discount = service._generate_tier_discount_code(user_id, config_id, discount_percentage)
        # Romper racha para que si vuelve a jugar, empiece desde 1
        game_type = 'trivia_vip' if data.get('vip_mode', False) else 'trivia'
        service.reset_trivia_streak(user_id, game_type)

    await state.clear()

    if discount and discount.get('code'):
        message = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"Ha asegurado su descuento del <b>{discount_percentage}%</b>.\n\n"
            f"📋 <b>Código:</b> <code>{discount['code']}</code>\n"
            f"💰 <b>Descuento:</b> {discount_percentage}% en {discount['promotion_name']}\n\n"
            f"<i>Usa este código al comprar la promoción.</i>"
        )
        keyboard = discount_claim_keyboard(discount['code'])
    else:
        message = (
            "🎩 <b>Lucien:</b>\n\n"
            "<i>No se pudo generar el código. Puede que ya no haya códigos disponibles.</i>"
        )
        keyboard = game_menu_keyboard()

    await callback.message.edit_text(message, reply_markup=keyboard)
    await callback.answer()
    logger.info(f"game_user_handlers - streak_retire - {user_id} - discount:{discount_percentage}%")


@router.callback_query(F.data == "streak_exit", TriviaStreakStates.waiting_streak_choice)
async def streak_exit(callback: CallbackQuery, state: FSMContext):
    """Usuario elige salir sin reclamar su descuento"""
    user_id = callback.from_user.id
    data = await state.get_data()

    tier_discount = data.get('current_tier_discount', 0)
    tier_index = data.get('tier_index', 0)

    await state.clear()

    message = (
        f"🎩 <b>Lucien:</b>\n\n"
        f"Su descuento del <b>{tier_discount}%</b> aguarda pacientemente.\n\n"
        "<i>Podrá reclamarlo cuando lo desee desde el menú.</i>"
    )
    keyboard = game_menu_keyboard()

    await callback.message.edit_text(message, reply_markup=keyboard)
    await callback.answer()
    logger.info(f"game_user_handlers - streak_exit - {user_id} - tier:{tier_index} discount:{tier_discount}%")


@router.callback_query(F.data == "streak_continue", TriviaStreakStates.waiting_streak_choice)
async def streak_continue(callback: CallbackQuery, state: FSMContext):
    """Usuario elige continuar para buscar mayor descuento"""
    user_id = callback.from_user.id
    data = await state.get_data()
    is_vip = data.get('vip_mode', False)

    # Verificar que aún tiene oportunidades
    with get_service(GameService) as service:
        if is_vip:
            entry_data = service.get_trivia_vip_entry_data(user_id)
        else:
            entry_data = service.get_trivia_entry_data(user_id)

        if not entry_data['can_play']:
            await callback.message.edit_text(
                entry_data['limit_message'],
                reply_markup=game_menu_keyboard()
            )
            await state.clear()
            await callback.answer()
            return

        question, question_idx = service.get_random_vip_question() if is_vip else service.get_random_question()

        if question is None:
            await callback.message.edit_text(
                "Las preguntas están en el taller de Lucien. Regresa más tarde.",
                reply_markup=game_menu_keyboard()
            )
            await state.clear()
            await callback.answer()
            return

    # Mostrar siguiente pregunta
    next_streak = data.get('current_tier_streak', 0)
    next_discount = data.get('next_tier_discount', 0)

    text = (
        f"🎯 <b>Continúa en su racha!</b>\n\n"
        f"Ha acumulado <b>{next_streak}</b> respuestas correctas.\n"
        f"Su próximo objetivo: <b>{next_streak + 5}</b> para el <b>{next_discount}%</b> de descuento.\n\n"
        f"Cuidado: si falla, perderá TODO el descuento acumulado.\n\n"
        f"❓ <b>Pregunta:</b> {question['q']}"
    )

    # Mantener el estado para la siguiente respuesta
    await state.set_state(TriviaStreakStates.streak_continue)

    if is_vip:
        keyboard = trivia_vip_keyboard(question, question_idx)
    else:
        keyboard = trivia_keyboard(question, question_idx)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()
    logger.info(f"game_user_handlers - streak_continue - {user_id} - next_question")


@router.callback_query(F.data == "streak_final_win")
async def streak_final_win(callback: CallbackQuery):
    """Usuario gana 100% - solo confirmar"""
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>El destino ha sido benevolent hacia usted. Su código de descuento completo le espera.</i>\n\n"
        "Puede usarlo cuando desee para obtener el producto gratuitamente.",
        reply_markup=game_menu_keyboard()
    )
    await callback.answer()
    logger.info(f"game_user_handlers - streak_final_win - {callback.from_user.id} - complete_win")
