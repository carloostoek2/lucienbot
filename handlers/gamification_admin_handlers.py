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
    ChangeButtonDescCallback,
    ChangeButtonLabelCallback,
    ChangeButtonUrlCallback,
    ChangeEmojiValueCallback,
    DeleteButtonCallback,
    EditButtonCallback,
    EditEmojiCallback,
    ToggleButtonCallback,
    ToggleEmojiCallback,
)
from keyboards.inline_keyboards import back_keyboard, cancel_keyboard
from handlers.vip_handlers import (
    notify_forward_besitos_result,
    parse_positive_besito_amount,
    parse_positive_telegram_user_id,
)
from services.besito_service import BesitoService, MAX_ADMIN_BESITO_GRANT
from services.broadcast_service import BroadcastService
from services import get_service
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


class ButtonConfigStates(StatesGroup):
    """Estados para el wizard completo de gestión de botones de enlace extra."""
    waiting_label = State()
    waiting_url = State()
    waiting_description = State()  # opcional
    edit_waiting_field = State()   # para edición de label/url/desc


class AdminBesitoGrantStates(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()
    confirming = State()


# ==================== MENU DE GAMIFICACION ADMIN ====================


@router.callback_query(F.data == "admin_gamification", lambda cb: is_admin(cb.from_user.id))
async def admin_gamification_menu(callback: CallbackQuery):
    """Menu principal de gamificacion para admins"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💋 Configurar besitos", callback_data="config_besitos")],
            [InlineKeyboardButton(text="🔗 Botones de enlace para publicaciones", callback_data="config_buttons")],
            [InlineKeyboardButton(text="📢 Enviar broadcast", callback_data="send_broadcast")],
            [
                InlineKeyboardButton(
                    text="🎁 Configurar regalo diario", callback_data="config_daily_gift"
                )
            ],
            [InlineKeyboardButton(text="📦 Gestionar paquetes", callback_data="manage_packages")],
            [
                InlineKeyboardButton(
                    text="🌱 Configurar nurture (secuencias post-VIP)",
                    callback_data="manage_nurture",
                )
            ],
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

    # Botones de enlace extra (definir primero - catálogo reusable, máx 1 por publicación)
    with get_service(BroadcastService) as bs:
        try:
            btns = bs.get_all_buttons(active_only=False)
        except Exception:
            btns = []
    text += f"\nBotones de enlace extra ({len(btns)}):\n"
    for b in btns[:3]:
        st = "✅" if b.is_active else "❌"
        text += f"  {st} {b.label}\n"
    if not btns:
        text += "  (catálogo vacío)\n"

    keyboard_buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="💋 Otorgar besitos a visitante",
                    callback_data="admin_grant_besitos",
                )
            ],
            [InlineKeyboardButton(text="➕ Agregar emoji", callback_data="add_emoji")],
            [InlineKeyboardButton(text="🔗 Gestionar botones de enlace", callback_data="config_buttons")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_gamification")],
        ]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ==================== OTORGAR BESITOS MANUAL (MENÚ ADMIN) ====================


@router.callback_query(F.data == "admin_grant_besitos", lambda cb: is_admin(cb.from_user.id))
async def admin_grant_besitos_start(callback: CallbackQuery, state: FSMContext):
    """Inicia otorgamiento manual de besitos desde menú admin (0 svc)."""
    admin_id = callback.from_user.id
    logger.info(f"{__name__} | iniciar_grant_besitos_menu | user_id={admin_id}")
    await callback.message.edit_text(
        LucienVoice.admin_besitos_grant_user_id_prompt(),
        reply_markup=cancel_keyboard("config_besitos"),
        parse_mode="HTML",
    )
    await state.set_state(AdminBesitoGrantStates.waiting_user_id)
    await callback.answer()


@router.message(AdminBesitoGrantStates.waiting_user_id, lambda m: is_admin(m.from_user.id))
async def process_admin_besito_user_id(message: Message, state: FSMContext):
    """Captura ID del visitante y pide cantidad (0 svc)."""
    target_user_id = parse_positive_telegram_user_id(message.text)
    if target_user_id is None:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n<i>ID inválido. Indique un número entero positivo de Telegram.</i>",
            reply_markup=cancel_keyboard("config_besitos"),
            parse_mode="HTML",
        )
        return
    admin_id = message.from_user.id
    logger.info(
        f"{__name__} | capturar_id_grant_besitos_menu | user_id={admin_id} | "
        f"target_user_id={target_user_id}"
    )
    await state.update_data(grant_target_user_id=target_user_id)
    await message.answer(
        LucienVoice.admin_besitos_grant_amount_prompt(target_user_id),
        reply_markup=cancel_keyboard("config_besitos"),
        parse_mode="HTML",
    )
    await state.set_state(AdminBesitoGrantStates.waiting_amount)


@router.message(AdminBesitoGrantStates.waiting_amount, lambda m: is_admin(m.from_user.id))
async def process_admin_besito_amount(message: Message, state: FSMContext):
    """Captura cantidad y muestra confirmación (0 svc)."""
    amount = parse_positive_besito_amount(message.text)
    if amount is None:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Cantidad inválida. Indique un entero entre 1 y {MAX_ADMIN_BESITO_GRANT}.</i>",
            reply_markup=cancel_keyboard("config_besitos"),
            parse_mode="HTML",
        )
        return
    data = await state.get_data()
    target_user_id = data.get("grant_target_user_id")
    admin_id = message.from_user.id
    logger.info(
        f"{__name__} | capturar_cantidad_grant_besitos_menu | user_id={admin_id} | "
        f"target_user_id={target_user_id} | amount={amount}"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Confirmar", callback_data="admin_besito_grant_confirm"),
                InlineKeyboardButton(text="❌ Cancelar", callback_data="config_besitos"),
            ]
        ]
    )
    await message.answer(
        LucienVoice.admin_besitos_grant_confirm_text(target_user_id, amount),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await state.update_data(besito_amount=amount)
    await state.set_state(AdminBesitoGrantStates.confirming)


@router.callback_query(
    AdminBesitoGrantStates.confirming,
    F.data == "admin_besito_grant_confirm",
    lambda cb: is_admin(cb.from_user.id),
)
async def confirm_admin_besito_grant(callback: CallbackQuery, state: FSMContext):
    """Confirma y ejecuta grant besitos (EXACTLY 1 svc) + notificación al visitante."""
    data = await state.get_data()
    target_user_id = data.get("grant_target_user_id")
    amount = data.get("besito_amount")
    admin_id = callback.from_user.id
    logger.info(
        f"{__name__} | confirmar_grant_besitos_menu | user_id={admin_id} | "
        f"target_user_id={target_user_id} | amount={amount}"
    )
    if not target_user_id or not amount:
        await callback.answer("Datos incompletos", show_alert=True)
        await state.clear()
        return
    ok, balance = False, 0
    with get_service(BesitoService) as besito_service:
        ok, balance = besito_service.grant_manual_admin_besitos(target_user_id, amount, admin_id)
    await notify_forward_besitos_result(
        callback.bot,
        callback.message,
        target_user_id,
        ok,
        amount,
        balance,
        admin_id,
        success_keyboard=back_keyboard("config_besitos"),
    )
    await state.clear()
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


@router.message(EmojiConfigStates.waiting_emoji, lambda msg: is_admin(msg.from_user.id))
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


# ==================== CONFIGURAR BOTONES DE ENLACE (wizard completo para catálogo) ====================


@router.callback_query(F.data == "config_buttons", lambda cb: is_admin(cb.from_user.id))
async def config_buttons_menu(callback: CallbackQuery):
    """Lista completa + acciones para gestionar botones de enlace extra (definir primero)."""
    with get_service(BroadcastService) as broadcast_service:
        buttons = broadcast_service.get_all_buttons(active_only=False)

    text = (
        "🎩 Lucien:\n\n"
        "Catálogo de botones de enlace personalizados.\n"
        "Estos se pueden adjuntar (máximo uno) a las publicaciones broadcast.\n\n"
        "Botones configurados:\n\n"
    )

    keyboard_buttons = []

    for btn in buttons:
        status = "✅" if btn.is_active else "❌"
        text += f"{status} {btn.label}\n"
        if btn.description:
            text += f"   ({btn.description[:60]})\n"
        text += f"   → {btn.url[:55]}...\n\n"

        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{btn.label} Editar",
                    callback_data=EditButtonCallback(button_id=btn.id).pack(),
                )
            ]
        )

    if not buttons:
        text += "(Aún no hay botones definidos. Agregue el primero.)\n\n"

    keyboard_buttons.extend(
        [
            [InlineKeyboardButton(text="➕ Agregar botón de enlace", callback_data="add_button")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_gamification")],
        ]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise

    await callback.answer()


@router.callback_query(F.data == "add_button", lambda cb: is_admin(cb.from_user.id))
async def add_button_start(callback: CallbackQuery, state: FSMContext):
    """Inicia el wizard para definir un nuevo botón de enlace (label + url)."""
    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "Vamos a forjar un nuevo botón de enlace para las publicaciones de Diana...\n\n"
        "Paso 1 de 2: Envíe el texto visible del botón.\n\n"
        "Máximo ~64 caracteres. Ejemplos:\n"
        "• Ver catálogo VIP\n"
        "• Únete al Diván\n"
        "• Más sobre este arquetipo",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(ButtonConfigStates.waiting_label)
    await callback.answer()


@router.message(ButtonConfigStates.waiting_label, lambda msg: is_admin(msg.from_user.id))
async def process_button_label(message: Message, state: FSMContext):
    """Procesa el label del botón."""
    label = (message.text or "").strip()
    if not (1 <= len(label) <= 64):
        await message.answer(
            "🎩 Lucien:\n\nEl texto del botón debe tener entre 1 y 64 caracteres.",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(label=label)

    await message.answer(
        "🎩 Lucien:\n\n"
        "Perfecto. Ahora el enlace.\n\n"
        "Paso 2 de 2: Envíe el enlace de Telegram o URL.\n\n"
        "Acepta: https://t.me/...  o  tg://...",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(ButtonConfigStates.waiting_url)


@router.message(ButtonConfigStates.waiting_url, lambda msg: is_admin(msg.from_user.id))
async def process_button_url(message: Message, state: FSMContext):
    """Crea el botón tras recibir la URL."""
    url = (message.text or "").strip()
    if not url or len(url) > 500:
        await message.answer(
            "🎩 Lucien:\n\nEl enlace no puede estar vacío y debe ser razonable.",
            reply_markup=cancel_keyboard(),
        )
        return

    data = await state.get_data()
    label = data["label"]

    with get_service(BroadcastService) as broadcast_service:
        try:
            button = broadcast_service.create_broadcast_button(label=label, url=url)
            logger.info(f"gamification_admin_handlers | add_button | admin_id={message.from_user.id} | button_id={button.id} | label={label}")
        except Exception as e:
            logger.error(f"Error creando botón: {e}")
            await message.answer(
                LucienVoice.error_message("crear el botón de enlace"),
                reply_markup=back_keyboard("config_buttons"),
            )
            await state.clear()
            return

    await message.answer(
        f"🎩 Lucien:\n\n"
        f"El botón ha sido forjado en el reino...\n\n"
        f"✅ Botón configurado:\n"
        f"   • Texto: {button.label}\n"
        f"   • Enlace: {button.url}\n\n"
        f"Los custodios podrán elegirlo (a lo sumo uno) al enviar publicaciones.",
        reply_markup=back_keyboard("config_buttons"),
    )

    await state.clear()


@router.callback_query(EditButtonCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def edit_button(callback: CallbackQuery, callback_data: EditButtonCallback):
    """Muestra menú de edición para un botón existente."""
    button_id = callback_data.button_id

    with get_service(BroadcastService) as broadcast_service:
        button = broadcast_service.get_broadcast_button(button_id)

    if not button:
        await callback.answer("Botón no encontrado", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Cambiar texto (label)",
                    callback_data=ChangeButtonLabelCallback(button_id=button_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔗 Cambiar enlace (url)",
                    callback_data=ChangeButtonUrlCallback(button_id=button_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Cambiar descripción",
                    callback_data=ChangeButtonDescCallback(button_id=button_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{'Desactivar' if button.is_active else 'Activar'}",
                    callback_data=ToggleButtonCallback(button_id=button_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Eliminar",
                    callback_data=DeleteButtonCallback(button_id=button_id).pack(),
                )
            ],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="config_buttons")],
        ]
    )

    status = "✅ Activo" if button.is_active else "❌ Inactivo"
    desc = button.description or "(sin descripción de admin)"

    await callback.message.edit_text(
        f"🎩 Lucien:\n\n"
        f"Editando botón de enlace...\n\n"
        f"**{button.label}**\n"
        f"   • Enlace: {button.url}\n"
        f"   • Descripción: {desc}\n"
        f"   • Estado: {status}\n\n"
        f"¿Qué desea modificar?",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(ToggleButtonCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def toggle_button(callback: CallbackQuery, callback_data: ToggleButtonCallback):
    """Activa o desactiva un botón."""
    button_id = callback_data.button_id

    with get_service(BroadcastService) as broadcast_service:
        success = broadcast_service.toggle_broadcast_button(button_id)

    if success:
        await callback.answer("Estado del botón actualizado")
        # Refrescar la vista de edición
        # Re-construir edit view
        with get_service(BroadcastService) as broadcast_service:
            button = broadcast_service.get_broadcast_button(button_id)
        if button:
            # Re-invoke the edit view logic (simple re-send)
            cb_data = EditButtonCallback(button_id=button_id)
            # hack to refresh: call the edit handler indirectly by faking
            # For cleanliness we just answer and user can go back
            pass
    else:
        await callback.answer("No se pudo cambiar el estado", show_alert=True)

    # For simplicity, go back to list
    with get_service(BroadcastService) as broadcast_service:
        buttons = broadcast_service.get_all_buttons(active_only=False)

    # Rebuild list quickly
    text = "🎩 Lucien:\n\nCatálogo actualizado.\n\n"
    kbs = []
    for b in buttons:
        st = "✅" if b.is_active else "❌"
        text += f"{st} {b.label}\n"
        kbs.append([InlineKeyboardButton(text=f"{b.label} Editar", callback_data=EditButtonCallback(button_id=b.id).pack())])

    kbs.extend([
        [InlineKeyboardButton(text="➕ Agregar botón de enlace", callback_data="add_button")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_gamification")],
    ])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kbs))
    await callback.answer()


# Handlers para cambiar campos (usando FSM + data["editing_button_id"] + field)
# Para mantener handlers pequeños, usamos F.data startswith + state


@router.callback_query(ChangeButtonLabelCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def change_button_label_start(callback: CallbackQuery, callback_data: ChangeButtonLabelCallback, state: FSMContext):
    await state.update_data(editing_button_id=callback_data.button_id, editing_field="label")
    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "Envíe el nuevo texto para el botón (1-64 caracteres):",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(ButtonConfigStates.edit_waiting_field)
    await callback.answer()


@router.callback_query(ChangeButtonUrlCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def change_button_url_start(callback: CallbackQuery, callback_data: ChangeButtonUrlCallback, state: FSMContext):
    await state.update_data(editing_button_id=callback_data.button_id, editing_field="url")
    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "Envíe el nuevo enlace:",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(ButtonConfigStates.edit_waiting_field)
    await callback.answer()


@router.callback_query(ChangeButtonDescCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def change_button_desc_start(callback: CallbackQuery, callback_data: ChangeButtonDescCallback, state: FSMContext):
    await state.update_data(editing_button_id=callback_data.button_id, editing_field="description")
    await callback.message.edit_text(
        "🎩 Lucien:\n\n"
        "Envíe la nueva descripción para uso interno de los custodios (o '-' para borrar):",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(ButtonConfigStates.edit_waiting_field)
    await callback.answer()


@router.message(ButtonConfigStates.edit_waiting_field, lambda msg: is_admin(msg.from_user.id))
async def process_button_field_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    button_id = data.get("editing_button_id")
    field = data.get("editing_field")
    value = (message.text or "").strip()

    if field == "description" and value == "-":
        value = None

    if not button_id or not field:
        await state.clear()
        return

    with get_service(BroadcastService) as broadcast_service:
        if field == "label":
            ok = broadcast_service.update_broadcast_button(button_id, label=value)
        elif field == "url":
            ok = broadcast_service.update_broadcast_button(button_id, url=value)
        elif field == "description":
            ok = broadcast_service.update_broadcast_button(button_id, description=value)
        else:
            ok = False

    if ok:
        await message.answer(
            "🎩 Lucien:\n\nCampo actualizado correctamente.",
            reply_markup=back_keyboard("config_buttons"),
        )
    else:
        await message.answer(
            LucienVoice.error_message("actualizar el botón"),
            reply_markup=back_keyboard("config_buttons"),
        )

    await state.clear()


@router.callback_query(DeleteButtonCallback.filter(), lambda cb: is_admin(cb.from_user.id))
async def delete_button(callback: CallbackQuery, callback_data: DeleteButtonCallback):
    button_id = callback_data.button_id

    if not callback_data.confirmed:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Sí, eliminar",
                        callback_data=DeleteButtonCallback(button_id=button_id, confirmed=True).pack(),
                    )
                ],
                [InlineKeyboardButton(text="❌ Cancelar", callback_data="config_buttons")],
            ]
        )
        await callback.message.edit_text(
            "🎩 Lucien:\n\n"
            "¿Está seguro de eliminar este botón?\n\n"
            "Los broadcasts existentes que ya lo usaron conservarán el enlace.\n"
            "Esta acción no se puede deshacer.",
            reply_markup=keyboard,
        )
        await callback.answer()
        return

    # confirmed
    with get_service(BroadcastService) as broadcast_service:
        success = broadcast_service.delete_broadcast_button(button_id)

    if success:
        await callback.answer("Botón eliminado")
    else:
        await callback.answer("No se pudo eliminar", show_alert=True)

    # Refresh list
    with get_service(BroadcastService) as broadcast_service:
        buttons = broadcast_service.get_all_buttons(active_only=False)

    text = "🎩 Lucien:\n\nCatálogo actualizado.\n\n"
    kbs = []
    for b in buttons:
        st = "✅" if b.is_active else "❌"
        text += f"{st} {b.label}\n"
        kbs.append([InlineKeyboardButton(text=f"{b.label} Editar", callback_data=EditButtonCallback(button_id=b.id).pack())])
    kbs.extend([
        [InlineKeyboardButton(text="➕ Agregar botón de enlace", callback_data="add_button")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="admin_gamification")],
    ])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kbs))
    await callback.answer()


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
