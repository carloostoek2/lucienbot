"""
Handlers de Gamificacion para Administradores - Lucien Bot

Handlers para configuracion de gamificacion desde el panel de admin.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.callback_data import (
    ChangeEmojiValueCallback,
    EditEmojiCallback,
    ToggleEmojiCallback,
)
from keyboards.inline_keyboards import back_keyboard, cancel_keyboard
from services.besito_service import BesitoService
from services.broadcast_service import BroadcastService
from services.daily_gift_service import DailyGiftService
from utils.admin import is_admin
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class EmojiConfigStates(StatesGroup):
    waiting_emoji = State()
    waiting_name = State()
    waiting_value = State()
    edit_waiting_value = State()


class DailyGiftConfigStates(StatesGroup):
    waiting_amount = State()


# ==================== MENU DE GAMIFICACION ADMIN ====================


@router.callback_query(F.data == "admin_gamification", lambda cb: is_admin(cb.from_user.id))
async def admin_gamification_menu(callback: CallbackQuery):
    """Menu principal de gamificacion para admins"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💋 Configurar besitos", callback_data="config_besitos")],
            [InlineKeyboardButton(text="📢 Enviar broadcast", callback_data="send_broadcast")],
            [
                InlineKeyboardButton(
                    text="🎁 Configurar regalo diario", callback_data="config_daily_gift"
                )
            ],
            [InlineKeyboardButton(text="📦 Gestionar paquetes", callback_data="manage_packages")],
            [InlineKeyboardButton(text="🎮 Gestionar misiones", callback_data="admin_missions")],
            [InlineKeyboardButton(text="🛒 Gestionar tienda", callback_data="admin_store")],
            [InlineKeyboardButton(text="📊 Estadisticas", callback_data="gamification_stats")],
            [InlineKeyboardButton(text="🔙 Volver al sanctum", callback_data="back_to_admin")],
        ]
    )

    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "El sistema de recompensas que cultiva devocion...\n\n"
        "Que aspecto de la gamificacion desea calibrar?",
        reply_markup=keyboard,
    )
    await callback.answer()


# ==================== CONFIGURAR BESITOS / EMOJIS ====================


@router.callback_query(F.data == "config_besitos", lambda cb: is_admin(cb.from_user.id))
async def config_besitos_menu(callback: CallbackQuery):
    """Menu de configuracion de besitos y emojis"""
    broadcast_service = BroadcastService()
    try:
        emojis = broadcast_service.get_all_emojis(active_only=False)
    finally:
        broadcast_service.close()

    text = (
        "🎩 Lucien:\n\nLos fragmentos de atencion que Diana otorga...\n\nEmojis configurados:\n\n"
    )

    keyboard_buttons = []

    for emoji in emojis:
        status = "✅" if emoji.is_active else "❌"
        text += f"{status} {emoji.emoji} = {emoji.besito_value} besitos"
        if emoji.name:
            text += f" ({emoji.name})"
        text += "\n"

        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{emoji.emoji} Editar",
                    callback_data=EditEmojiCallback(emoji_id=emoji.id).pack(),
                )
            ]
        )

    keyboard_buttons.extend(
        [
            [InlineKeyboardButton(text="➕ Agregar emoji", callback_data="add_emoji")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_gamification")],
        ]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "add_emoji", lambda cb: is_admin(cb.from_user.id))
async def add_emoji_start(callback: CallbackQuery, state: FSMContext):
    """Inicia el flujo de agregar emoji"""
    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "Vamos a configurar un nuevo emoji de reaccion...\n\n"
        "Paso 1 de 3: Envie el emoji que desea agregar.\n\n"
        "Ejemplos: 💋 ❤️ 🔥 👍",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(EmojiConfigStates.waiting_emoji)
    await callback.answer()


@router.message(EmojiConfigStates.waiting_emoji)
async def process_emoji(message: Message, state: FSMContext):
    """Procesa el emoji ingresado"""
    emoji_char = message.text.strip()

    # Validar que sea un solo emoji (aproximado)
    if len(emoji_char) > 2:
        await message.answer(
            "🎩 Lucien:\n\nPor favor, envie solo un emoji...", reply_markup=cancel_keyboard()
        )
        return

    await state.update_data(emoji=emoji_char)

    await message.answer(
        "🎩 Lucien:\n\n"
        "Excelente. Ahora un nombre descriptivo...\n\n"
        "Paso 2 de 3: Nombre del emoji\n\n"
        "Ejemplo: Beso, Corazon, Fuego",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(EmojiConfigStates.waiting_name)


@router.message(EmojiConfigStates.waiting_name)
async def process_emoji_name(message: Message, state: FSMContext):
    """Procesa el nombre del emoji"""
    name = message.text.strip()
    await state.update_data(name=name)

    await message.answer(
        "🎩 Lucien:\n\n"
        "Finalmente, el valor en besitos...\n\n"
        "Paso 3 de 3: Valor de besitos\n\n"
        "Ejemplo: 5 para 5 besitos",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(EmojiConfigStates.waiting_value)


@router.message(EmojiConfigStates.waiting_value)
async def process_emoji_value(message: Message, state: FSMContext):
    """Procesa el valor y crea el emoji"""
    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError("Valor debe ser positivo")
    except ValueError:
        await message.answer(
            "🎩 Lucien:\n\nPor favor, indique un numero valido mayor a cero...",
            reply_markup=cancel_keyboard(),
        )
        return

    data = await state.get_data()

    broadcast_service = BroadcastService()

    try:
        emoji = broadcast_service.create_reaction_emoji(
            emoji=data["emoji"], name=data["name"], besito_value=value
        )

        await message.answer(
            f"🎩 Lucien:\n\n"
            f"El emoji ha sido registrado en los archivos de Diana...\n\n"
            f"✅ Emoji configurado:\n"
            f"   • Emoji: {emoji.emoji}\n"
            f"   • Nombre: {emoji.name}\n"
            f"   • Valor: {emoji.besito_value} besitos\n\n"
            f"Los visitantes podran usarlo en las reacciones.",
            reply_markup=back_keyboard("config_besitos"),
        )

    except Exception as e:
        logger.error(f"Error creando emoji: {e}")
        await message.answer(
            LucienVoice.error_message("la configuracion del emoji"),
            reply_markup=back_keyboard("config_besitos"),
        )

    await state.clear()


@router.callback_query(EditEmojiCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def edit_emoji(callback: CallbackQuery, callback_data: EditEmojiCallback):
    """Editar un emoji existente"""
    emoji_id = callback_data.emoji_id

    broadcast_service = BroadcastService()
    try:
        emoji = broadcast_service.get_reaction_emoji(emoji_id)
    finally:
        broadcast_service.close()

    if not emoji:
        await callback.answer("Emoji no encontrado", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Cambiar valor",
                    callback_data=ChangeEmojiValueCallback(emoji_id=emoji_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{'Desactivar' if emoji.is_active else 'Activar'}",
                    callback_data=ToggleEmojiCallback(emoji_id=emoji_id).pack(),
                )
            ],
            [InlineKeyboardButton(text="🗑️ Eliminar", callback_data=f"delete_emoji_{emoji_id}")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="config_besitos")],
        ]
    )

    status = "✅ Activo" if emoji.is_active else "❌ Inactivo"

    await callback.message.edit_text(
        f"🎩 Lucien:\n\n"
        f"Editando emoji...\n\n"
        f"{emoji.emoji} {emoji.name or 'Sin nombre'}\n"
        f"   • Valor: {emoji.besito_value} besitos\n"
        f"   • Estado: {status}\n\n"
        f"Que desea modificar?",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(ToggleEmojiCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def toggle_emoji(callback: CallbackQuery, callback_data: ToggleEmojiCallback):
    """Activa/desactiva un emoji"""
    emoji_id = callback_data.emoji_id

    broadcast_service = BroadcastService()
    try:
        success = broadcast_service.toggle_emoji(emoji_id)
    finally:
        broadcast_service.close()

    if success:
        await callback.answer("Estado actualizado")
        # Reconstruir callback para volver a editar el emoji
        callback.data = EditEmojiCallback(emoji_id=emoji_id).pack()
        await edit_emoji(callback, EditEmojiCallback(emoji_id=emoji_id))
    else:
        await callback.answer("Error al actualizar", show_alert=True)


@router.callback_query(ChangeEmojiValueCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def change_emoji_value_start(
    callback: CallbackQuery, callback_data: ChangeEmojiValueCallback, state: FSMContext
):
    """Inicia cambio de valor de emoji"""
    await state.update_data(emoji_id=callback_data.emoji_id)

    broadcast_service = BroadcastService()
    try:
        emoji = broadcast_service.get_reaction_emoji(callback_data.emoji_id)
    finally:
        broadcast_service.close()

    await callback.message.edit_text(
        f"🎩 Lucien:\n\n"
        f"Indique el nuevo valor en besitos para {emoji.emoji}:\n\n"
        f"Valor actual: {emoji.besito_value} besitos\n\n"
        "Ejemplo: 10",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(EmojiConfigStates.edit_waiting_value)
    await callback.answer()


@router.message(EmojiConfigStates.edit_waiting_value)
async def process_emoji_value_edit(message: Message, state: FSMContext):
    """Procesa el nuevo valor del emoji"""
    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError("Valor debe ser positivo")
    except ValueError:
        await message.answer(
            "🎩 Lucien:\n\nPor favor, indique un numero valido mayor a cero...",
            reply_markup=cancel_keyboard(),
        )
        return

    data = await state.get_data()
    emoji_id = data["emoji_id"]

    broadcast_service = BroadcastService()
    try:
        success = broadcast_service.update_emoji_value(emoji_id, value)
    finally:
        broadcast_service.close()

    if success:
        await message.answer(
            f"🎩 Lucien:\n\nEl valor ha sido actualizado a {value} besitos.",
            reply_markup=back_keyboard("config_besitos"),
        )
    else:
        await message.answer(
            LucienVoice.error_message("actualizar el valor del emoji"),
            reply_markup=back_keyboard("config_besitos"),
        )

    await state.clear()


# ==================== CONFIGURAR REGALO DIARIO ====================


@router.callback_query(F.data == "config_daily_gift", lambda cb: is_admin(cb.from_user.id))
async def config_daily_gift(callback: CallbackQuery):
    """Configuracion del regalo diario"""
    gift_service = DailyGiftService()
    try:
        config = gift_service.get_config()
    finally:
        gift_service.close()

    status = "✅ Activo" if config.is_active else "❌ Inactivo"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Cantidad: {config.besito_amount} besitos",
                    callback_data="change_gift_amount",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{'Desactivar' if config.is_active else 'Activar'}",
                    callback_data="toggle_daily_gift",
                )
            ],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_gamification")],
        ]
    )

    await callback.message.edit_text(
        f"🎩 Lucien:\n\n"
        f"La generosidad diaria de Diana...\n\n"
        f"🎁 Configuracion del Regalo Diario:\n"
        f"   • Cantidad: {config.besito_amount} besitos\n"
        f"   • Estado: {status}\n\n"
        f"Los visitantes pueden reclamar esto una vez cada 24 horas.",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "change_gift_amount", lambda cb: is_admin(cb.from_user.id))
async def change_gift_amount_start(callback: CallbackQuery, state: FSMContext):
    """Inicia cambio de cantidad del regalo"""
    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "Cuantos besitos otorgara Diana cada dia?\n\n"
        "Indique la cantidad de besitos para el regalo diario:\n\n"
        "Ejemplo: 15",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(DailyGiftConfigStates.waiting_amount)
    await callback.answer()


@router.message(DailyGiftConfigStates.waiting_amount)
async def process_gift_amount(message: Message, state: FSMContext):
    """Procesa la nueva cantidad"""
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError("Cantidad debe ser positiva")
    except ValueError:
        await message.answer(
            "🎩 Lucien:\n\nPor favor, indique un numero valido mayor a cero...",
            reply_markup=cancel_keyboard(),
        )
        return

    gift_service = DailyGiftService()
    gift_service.update_config(amount, admin_id=message.from_user.id)

    await message.answer(
        f"🎩 Lucien:\n\n"
        f"La generosidad de Diana ha sido ajustada...\n\n"
        f"✅ Regalo diario actualizado: {amount} besitos\n\n"
        f"Los visitantes recibiran esta cantidad al reclamar.",
        reply_markup=back_keyboard("config_daily_gift"),
    )
    await state.clear()


@router.callback_query(F.data == "toggle_daily_gift", lambda cb: is_admin(cb.from_user.id))
async def toggle_daily_gift(callback: CallbackQuery):
    """Activa/desactiva el regalo diario"""
    gift_service = DailyGiftService()
    is_active = gift_service.toggle_daily_gift()

    status = "activado" if is_active else "desactivado"
    await callback.answer(f"Regalo diario {status}")

    await config_daily_gift(callback)


# ==================== ESTADISTICAS ====================


@router.callback_query(F.data == "gamification_stats", lambda cb: is_admin(cb.from_user.id))
async def gamification_stats(callback: CallbackQuery):
    """Estadisticas de gamificacion"""
    besito_service = BesitoService()
    gift_service = DailyGiftService()
    try:
        total_besitos = besito_service.get_total_besitos_in_circulation()
        top_users = besito_service.get_top_users(limit=5)
        claims_today = gift_service.get_total_claims_today()
        besitos_given_today = gift_service.get_total_besitos_given_today()
    finally:
        besito_service.close()
        gift_service.close()

    text = (
        "🎩 Lucien:\n\n"
        "Los patrones de la devocion acumulada...\n\n"
        "📊 Estadisticas de Gamificacion:\n\n"
        f"💋 Besitos en circulacion: {total_besitos}\n\n"
        f"🎁 Regalos hoy:\n"
        f"   • Reclamos: {claims_today}\n"
        f"   • Besitos entregados: {besitos_given_today}\n\n"
        f"🏆 Top visitantes:\n"
    )

    for i, user in enumerate(top_users, 1):
        text += f"   {i}. ID:{user.user_id} - {user.balance} besitos\n"

    await callback.message.edit_text(text, reply_markup=back_keyboard("admin_gamification"))
    await callback.answer()
