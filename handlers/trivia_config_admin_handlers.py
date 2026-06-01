"""
Handlers de Configuracion de Trivias - Lucien Bot

Menu principal de Trivias y configuracion de limites de intentos.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import TriviaConfigFieldCallback
from keyboards.inline_keyboards import back_keyboard, cancel_keyboard, trivia_admin_keyboard
from services import TriviaConfigService, get_service
from utils.admin import is_admin

logger = logging.getLogger(__name__)
router = Router()


class TriviaConfigStates(StatesGroup):
    waiting_field = State()
    waiting_value = State()


# ==================== MENU PRINCIPAL DE TRIVIAS ====================


@router.callback_query(F.data == "admin_trivia", lambda cb: is_admin(cb.from_user.id))
async def admin_trivia_menu(callback: CallbackQuery):
    """Menu principal de administracion de Trivias."""
    await callback.message.edit_text(
        "🎯 <b>Trivias</b>\n\n"
        "Lucien gestiona los dominios de la trivia...\n\n"
        "Seleccione que desea administrar:",
        reply_markup=trivia_admin_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
    logger.info(f"trivia_config_admin - admin_trivia_menu - {callback.from_user.id}")


# ==================== CONFIGURACION DE TRIVIAS ====================


def _config_keyboard(config: dict) -> InlineKeyboardMarkup:
    """Teclado con los valores de configuracion editables."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"Dados Free: {config['dice_limit_free']} | VIP: {config['dice_limit_vip']}",
                callback_data=TriviaConfigFieldCallback(field_key="dice").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Trivia Free: {config['trivia_limit_free']} | VIP: {config['trivia_limit_vip']}",
                callback_data=TriviaConfigFieldCallback(field_key="trivia").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Trivia VIP: {config['trivia_vip_limit']} (solo VIP)",
                callback_data=TriviaConfigFieldCallback(field_key="trivia_vip").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Trivia Simple Free: {config['trivia_simple_limit_free']} | VIP: {config['trivia_simple_limit_vip']}",
                callback_data=TriviaConfigFieldCallback(field_key="trivia_simple").pack(),
            )
        ],
        [InlineKeyboardButton(text="🔙 Volver a Trivias", callback_data="admin_trivia")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


FIELD_LABELS = {
    "dice": ("Dados", "dice_limit_free", "dice_limit_vip", False),
    "trivia": ("Trivia", "trivia_limit_free", "trivia_limit_vip", False),
    "trivia_vip": ("Trivia VIP", "trivia_vip_limit", None, True),
    "trivia_simple": (
        "Trivia Simple",
        "trivia_simple_limit_free",
        "trivia_simple_limit_vip",
        False,
    ),
}


@router.callback_query(F.data == "admin_trivia_config", lambda cb: is_admin(cb.from_user.id))
async def admin_trivia_config(callback: CallbackQuery):
    """Muestra la configuracion actual de limites de trivia."""
    with get_service(TriviaConfigService) as service:
        config = service.get_config()

    await callback.message.edit_text(
        "⚙️ <b>Configuración de Trivias</b>\n\n"
        "Lucien ajusta los límites diarios de intentos...\n\n"
        "Seleccione el tipo de juego para modificar sus límites:",
        reply_markup=_config_keyboard(config),
        parse_mode="HTML",
    )
    await callback.answer()
    logger.info(f"trivia_config_admin - admin_trivia_config - {callback.from_user.id}")


@router.callback_query(TriviaConfigFieldCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def trivia_config_select_field(
    callback: CallbackQuery, callback_data: TriviaConfigFieldCallback, state: FSMContext
):
    """Solicita el nuevo valor para el campo seleccionado."""
    field_key = callback_data.field_key
    label, free_key, vip_key, vip_only = FIELD_LABELS[field_key]

    await state.update_data(field_key=field_key)

    with get_service(TriviaConfigService) as service:
        config = service.get_config()

    if vip_only:
        text = (
            f"⚙️ <b>Configurar {label}</b>\n\n"
            f"Límite actual: <b>{config[free_key]}</b> intentos\n\n"
            f"Indique el nuevo límite (número entero, 0 o más):"
        )
    else:
        text = (
            f"⚙️ <b>Configurar {label}</b>\n\n"
            f"Límite Free actual: <b>{config[free_key]}</b> intentos\n"
            f"Límite VIP actual: <b>{config[vip_key]}</b> intentos\n\n"
            f"Indique los nuevos valores en formato: <b>free vip</b>\n"
            f"Ejemplo: <b>5 10</b> para 5 intentos free y 10 VIP"
        )

    await callback.message.edit_text(text, reply_markup=cancel_keyboard(), parse_mode="HTML")
    await state.set_state(TriviaConfigStates.waiting_value)
    await callback.answer()


@router.message(TriviaConfigStates.waiting_value)
async def trivia_config_process_value(message: Message, state: FSMContext):
    """Procesa el nuevo valor de limite."""
    data = await state.get_data()
    field_key = data["field_key"]
    label, free_key, vip_key, vip_only = FIELD_LABELS[field_key]

    try:
        parts = message.text.strip().split()
        if vip_only:
            if len(parts) != 1:
                raise ValueError("Se requiere un solo valor")
            vip_val = int(parts[0])
            if vip_val < 0:
                raise ValueError("Debe ser >= 0")
            kwargs = {free_key: vip_val}
        else:
            if len(parts) != 2:
                raise ValueError("Se requieren dos valores (free vip)")
            free_val = int(parts[0])
            vip_val = int(parts[1])
            if free_val < 0 or vip_val < 0:
                raise ValueError("Deben ser >= 0")
            kwargs = {free_key: free_val, vip_key: vip_val}
    except ValueError as e:
        await message.answer(
            f"🎩 Lucien:\n\nValor inválido ({e}). Intente de nuevo...",
            reply_markup=cancel_keyboard(),
        )
        return

    with get_service(TriviaConfigService) as service:
        service.update_config(admin_id=message.from_user.id, **kwargs)

    await state.clear()
    await message.answer(
        f"🎩 Lucien:\n\n✅ <b>{label}</b> actualizado correctamente.\n\n"
        f"Los nuevos límites ya están en vigor.",
        reply_markup=back_keyboard("admin_trivia_config"),
        parse_mode="HTML",
    )
    logger.info(
        f"trivia_config_admin - process_value - {message.from_user.id} - "
        f"field:{field_key} kwargs:{kwargs}"
    )
