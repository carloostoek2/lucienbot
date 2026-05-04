"""
Handlers de Admin - Gestión de Trivias

Submenú que agrupa sets de preguntas, promociones por racha y configuración.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.admin_handlers import is_admin
from services.trivia_config_service import TriviaConfigService
import logging

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class TriviaConfigStates(StatesGroup):
    waiting_free_limit = State()
    waiting_vip_limit = State()
    waiting_vip_exclusive_limit = State()


# ==================== MENÚ PRINCIPAL DE TRIVIAS ====================

@router.callback_query(F.data == "admin_trivia_management", lambda cb: is_admin(cb.from_user.id))
async def admin_trivia_management_menu(callback: CallbackQuery):
    """Submenú de Gestión de Trivias"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📚 Sets de preguntas",
            callback_data="admin_question_sets"
        )],
        [InlineKeyboardButton(
            text="🔥 Promociones por racha",
            callback_data="admin_trivia_discount"
        )],
        [InlineKeyboardButton(
            text="⚙️ Configuración",
            callback_data="admin_trivia_config"
        )],
        [InlineKeyboardButton(
            text="🔙 Volver al sanctum",
            callback_data="back_to_admin"
        )]
    ])

    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "El arte de calibrar los exámenes de Diana...\n\n"
        "Que aspecto de las trivias desea administrar?",
        reply_markup=keyboard
    )
    await callback.answer()


# ==================== CONFIGURACIÓN DE TRIVIA ====================

@router.callback_query(F.data == "admin_trivia_config", lambda cb: is_admin(cb.from_user.id))
async def admin_trivia_config_menu(callback: CallbackQuery):
    """Configuración de límites de trivia"""
    trivia_service = TriviaConfigService()
    try:
        config = trivia_service.get_config()
    finally:
        trivia_service.close()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"Gratuitos: {config.daily_trivia_limit_free}/dia",
            callback_data="change_trivia_free_limit"
        )],
        [InlineKeyboardButton(
            text=f"VIP: {config.daily_trivia_limit_vip}/dia",
            callback_data="change_trivia_vip_limit"
        )],
        [InlineKeyboardButton(
            text=f"Trivia VIP exclusiva: {config.daily_trivia_vip_limit}/dia",
            callback_data="change_trivia_vip_exclusive_limit"
        )],
        [InlineKeyboardButton(
            text="🔙 Volver",
            callback_data="admin_trivia_management"
        )]
    ])

    await callback.message.edit_text(
        f"🎩 Lucien:\n\n"
        f"Los umbrales del examen de Diana según el visitante...\n\n"
        f"📊 Limites de Trivia:\n"
        f"   • Gratuitos: {config.daily_trivia_limit_free} oportunidades/dia\n"
        f"   • VIP: {config.daily_trivia_limit_vip} oportunidades/dia\n"
        f"   • VIP Exclusiva: {config.daily_trivia_vip_limit} oportunidades/dia\n\n"
        f"Presione un boton para modificar ese limite.",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "change_trivia_free_limit", lambda cb: is_admin(cb.from_user.id))
async def change_trivia_free_limit_start(callback: CallbackQuery, state: FSMContext):
    """Inicia cambio de limite para gratuitos"""
    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "Cuantas oportunidades de trivia tendran los visitantes gratuitos?\n\n"
        "Indique el numero de intentos diarios:\n\n"
        "Ejemplo: 7",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_trivia_config")]
        ])
    )
    await state.set_state(TriviaConfigStates.waiting_free_limit)
    await callback.answer()


@router.message(TriviaConfigStates.waiting_free_limit, lambda msg: is_admin(msg.from_user.id))
async def process_trivia_free_limit(message: Message, state: FSMContext):
    """Procesa el nuevo limite para gratuitos"""
    try:
        limit = int(message.text.strip())
        if limit < 0:
            raise ValueError("Cantidad debe ser cero o mayor")
    except ValueError:
        await message.answer(
            "🎩 Lucien:\n\n"
            "Por favor, indique un numero valido mayor o igual a cero...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_trivia_config")]
            ])
        )
        return

    trivia_service = TriviaConfigService()
    config = trivia_service.get_config()
    trivia_service.update_config(
        limit, config.daily_trivia_limit_vip, config.daily_trivia_vip_limit,
        admin_id=message.from_user.id
    )
    trivia_service.close()

    await message.answer(
        f"🎩 Lucien:\n\n"
        f"El velo se ha liftsado ligeramente...\n\n"
        f"✅ Limite para gratuitos: {limit} oportunidades/dia\n\n"
        f"Los visitantes no suscritos ahora tendran mas razones para unirse.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_trivia_config")]
        ])
    )
    await state.clear()


@router.callback_query(F.data == "change_trivia_vip_limit", lambda cb: is_admin(cb.from_user.id))
async def change_trivia_vip_limit_start(callback: CallbackQuery, state: FSMContext):
    """Inicia cambio de limite para VIP"""
    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "Cuantas oportunidades de trivia tendran los miembros VIP?\n\n"
        "Indique el numero de intentos diarios:\n\n"
        "Ejemplo: 15",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_trivia_config")]
        ])
    )
    await state.set_state(TriviaConfigStates.waiting_vip_limit)
    await callback.answer()


@router.message(TriviaConfigStates.waiting_vip_limit, lambda msg: is_admin(msg.from_user.id))
async def process_trivia_vip_limit(message: Message, state: FSMContext):
    """Procesa el nuevo limite para VIP"""
    try:
        limit = int(message.text.strip())
        if limit < 0:
            raise ValueError("Cantidad debe ser cero o mayor")
    except ValueError:
        await message.answer(
            "🎩 Lucien:\n\n"
            "Por favor, indique un numero valido mayor o igual a cero...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_trivia_config")]
            ])
        )
        return

    trivia_service = TriviaConfigService()
    config = trivia_service.get_config()
    trivia_service.update_config(
        config.daily_trivia_limit_free, limit, config.daily_trivia_vip_limit,
        admin_id=message.from_user.id
    )
    trivia_service.close()

    await message.answer(
        f"🎩 Lucien:\n\n"
        f"El favor de Diana se expande...\n\n"
        f"✅ Limite para VIP: {limit} oportunidades/dia\n\n"
        f"Sus favoritos recibiran mayor abundancia.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_trivia_config")]
        ])
    )
    await state.clear()


@router.callback_query(F.data == "change_trivia_vip_exclusive_limit", lambda cb: is_admin(cb.from_user.id))
async def change_trivia_vip_exclusive_limit_start(callback: CallbackQuery, state: FSMContext):
    """Inicia cambio de limite para trivia VIP exclusiva"""
    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "Cuantas oportunidades de trivia VIP exclusiva habra?\n\n"
        "Indique el numero de intentos diarios:\n\n"
        "Ejemplo: 5",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_trivia_config")]
        ])
    )
    await state.set_state(TriviaConfigStates.waiting_vip_exclusive_limit)
    await callback.answer()


@router.message(TriviaConfigStates.waiting_vip_exclusive_limit, lambda msg: is_admin(msg.from_user.id))
async def process_trivia_vip_exclusive_limit(message: Message, state: FSMContext):
    """Procesa el nuevo limite para trivia VIP exclusiva"""
    try:
        limit = int(message.text.strip())
        if limit < 0:
            raise ValueError("Cantidad debe ser cero o mayor")
    except ValueError:
        await message.answer(
            "🎩 Lucien:\n\n"
            "Por favor, indique un numero valido mayor o igual a cero...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_trivia_config")]
            ])
        )
        return

    trivia_service = TriviaConfigService()
    config = trivia_service.get_config()
    trivia_service.update_config(
        config.daily_trivia_limit_free, config.daily_trivia_limit_vip, limit,
        admin_id=message.from_user.id
    )
    trivia_service.close()

    await message.answer(
        f"🎩 Lucien:\n\n"
        f"El circulo intimo se ajusta...\n\n"
        f"✅ Limite VIP Exclusiva: {limit} oportunidades/dia\n\n"
        f"Solo los mas devotos accederan a estas preguntas.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_trivia_config")]
        ])
    )
    await state.clear()
