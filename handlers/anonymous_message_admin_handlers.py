"""
Handlers Admin para Mensajes Anónimos - Lucien Bot

Gestión de mensajes anónimos por parte de Diana (admin).
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config.settings import bot_config
from services.anonymous_message_service import AnonymousMessageService
from services.user_service import UserService
from keyboards.inline_keyboards import back_keyboard, admin_menu_keyboard
from utils.lucien_voice import LucienVoice
import logging

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class AnonymousReplyStates(StatesGroup):
    waiting_reply = State()


def is_admin(user_id: int) -> bool:
    """Verifica si el usuario es admin"""
    return user_id in bot_config.ADMIN_IDS


def anonymous_messages_menu_keyboard() -> InlineKeyboardMarkup:
    """Menú de gestión de mensajes anónimos"""
    buttons = [
        [InlineKeyboardButton(
            text="📨 Mensajes no leídos",
            callback_data="anon_unread"
        )],
        [InlineKeyboardButton(
            text="📋 Todos los mensajes",
            callback_data="anon_all"
        )],
        [InlineKeyboardButton(
            text="🔙 Volver al sanctum",
            callback_data="back_to_admin"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def anonymous_message_actions_keyboard(message_id: int, show_reveal: bool = True) -> InlineKeyboardMarkup:
    """Acciones disponibles para un mensaje anónimo"""
    buttons = [
        [InlineKeyboardButton(
            text="💬 Responder",
            callback_data=f"anon_reply_{message_id}"
        )]
    ]

    if show_reveal:
        buttons.append([InlineKeyboardButton(
            text="👁️ Revelar remitente",
            callback_data=f"anon_reveal_{message_id}"
        )])

    buttons.append([InlineKeyboardButton(
        text="🗑️ Eliminar mensaje",
        callback_data=f"anon_delete_{message_id}"
    )])

    buttons.append([InlineKeyboardButton(
        text="🔙 Volver a mensajes",
        callback_data="admin_anonymous_messages"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def anonymous_messages_list_keyboard(messages: list, show_sender: bool = False) -> InlineKeyboardMarkup:
    """Lista de mensajes con botones para ver detalles"""
    buttons = []

    for msg in messages:
        status_emoji = {
            "unread": "🔴",
            "read": "🟡",
            "replied": "🟢"
        }.get(msg.status.value, "⚪")

        # Preview del mensaje (primeros 30 chars)
        preview = msg.content[:30] + "..." if len(msg.content) > 30 else msg.content
        text = f"{status_emoji} {preview}"

        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"anon_view_{msg.id}"
        )])

    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="admin_anonymous_messages"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== MENÚ PRINCIPAL DE MENSAJES ANÓNIMOS ====================

@router.callback_query(F.data == "admin_anonymous_messages", lambda cb: is_admin(cb.from_user.id))
async def admin_anonymous_messages_menu(callback: CallbackQuery):
    """Menú de gestión de mensajes anónimos"""
    anon_service = AnonymousMessageService()
    try:
        counts = anon_service.get_message_count_by_status()

        text = f"""🎩 <b>Lucien:</b>

<i>Los susurros que llegan desde el círculo exclusivo...</i>

💌 <b>Mensajes Anónimos VIP</b>

📊 <b>Estadísticas:</b>
   🔴 No leídos: {counts.get('unread', 0)}
   🟡 Leídos: {counts.get('read', 0)}
   🟢 Respondidos: {counts.get('replied', 0)}

<i>Seleccione una opción para gestionar los mensajes.</i>"""

        await callback.message.edit_text(
            text,
            reply_markup=anonymous_messages_menu_keyboard(),
            parse_mode="HTML"
        )
    finally:
        anon_service.close()
    await callback.answer()


@router.callback_query(F.data == "anon_unread", lambda cb: is_admin(cb.from_user.id))
async def show_unread_messages(callback: CallbackQuery):
    """Muestra mensajes no leídos"""
    anon_service = AnonymousMessageService()
    try:
        messages = anon_service.get_unread_messages()

        if not messages:
            await callback.message.edit_text(
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>No hay susurros pendientes...</i>\n\n"
                f"📭 No hay mensajes anónimos sin leer.",
                reply_markup=anonymous_messages_menu_keyboard(),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        text = f"""🎩 <b>Lucien:</b>

<i>Mensajes anónimos que aguardan su atención...</i>

📨 <b>No leídos:</b> {len(messages)}

<i>Seleccione un mensaje para leerlo:</i>"""

        await callback.message.edit_text(
            text,
            reply_markup=anonymous_messages_list_keyboard(messages),
            parse_mode="HTML"
        )
    finally:
        anon_service.close()
    await callback.answer()


@router.callback_query(F.data == "anon_all", lambda cb: is_admin(cb.from_user.id))
async def show_all_messages(callback: CallbackQuery):
    """Muestra todos los mensajes"""
    anon_service = AnonymousMessageService()
    try:
        messages = anon_service.get_all_messages(limit=20)

        if not messages:
            await callback.message.edit_text(
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>El silencio reina en el círculo...</i>\n\n"
                f"📭 No hay mensajes anónimos registrados.",
                reply_markup=anonymous_messages_menu_keyboard(),
                parse_mode="HTML"
            )
            await callback.answer()
            return

        text = f"""🎩 <b>Lucien:</b>

<i>El archivo completo de susurros...</i>

📋 <b>Total de mensajes:</b> {len(messages)}

<i>Seleccione un mensaje para ver detalles:</i>"""

        await callback.message.edit_text(
            text,
            reply_markup=anonymous_messages_list_keyboard(messages),
            parse_mode="HTML"
        )
    finally:
        anon_service.close()
    await callback.answer()


@router.callback_query(F.data.startswith("anon_view_"), lambda cb: is_admin(cb.from_user.id))
async def view_anonymous_message(callback: CallbackQuery):
    """Muestra el contenido completo de un mensaje"""
    message_id = int(callback.data.replace("anon_view_", ""))
    admin_id = callback.from_user.id

    anon_service = AnonymousMessageService()
    try:
        message = anon_service.get_message(message_id)

        if not message:
            await callback.answer("Mensaje no encontrado", show_alert=True)
            return

        # Marcar como leído si estaba sin leer
        if message.status.value == "unread":
            anon_service.mark_as_read(message_id, admin_id)
            message.status.value = "read"  # Actualizar para mostrar correctamente

        status_emoji = {
            "unread": "🔴 No leído",
            "read": "🟡 Leído",
            "replied": "🟢 Respondido"
        }.get(message.status.value, "⚪")

        date_str = message.created_at.strftime("%d/%m/%Y %H:%M") if message.created_at else "Desconocida"

        text = f"""🎩 <b>Lucien:</b>

💌 <b>Mensaje Anónimo</b>

📅 <b>Fecha:</b> {date_str}
📊 <b>Estado:</b> {status_emoji}

💬 <b>Contenido:</b>
<blockquote>{message.content}</blockquote>"""

        if message.admin_reply:
            text += f"\n\n💬 <b>Su respuesta:</b>\n<blockquote>{message.admin_reply}</blockquote>"

        await callback.message.edit_text(
            text,
            reply_markup=anonymous_message_actions_keyboard(message_id),
            parse_mode="HTML"
        )
    finally:
        anon_service.close()
    await callback.answer()


@router.callback_query(F.data.startswith("anon_reveal_"), lambda cb: is_admin(cb.from_user.id))
async def reveal_anonymous_sender(callback: CallbackQuery):
    """Revela la identidad del remitente (solo para casos delicados)"""
    message_id = int(callback.data.replace("anon_reveal_", ""))

    anon_service = AnonymousMessageService()
    try:
        sender = anon_service.get_sender_info(message_id)
        message = anon_service.get_message(message_id)

        if not message or not sender:
            await callback.answer("No se pudo obtener información del remitente", show_alert=True)
            return

        # Información del remitente
        username = f"@{sender.username}" if sender.username else "Sin username"
        name = f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "Sin nombre"

        text = f"""🎩 <b>Lucien:</b>

<i>Información revelada del remitente...</i>

👤 <b>Remitente:</b>
   • ID: <code>{sender.telegram_id}</code>
   • Username: {username}
   • Nombre: {name}

⚠️ <b>Esta información es confidencial.</b>
Úsela solo si es absolutamente necesario.

💬 <b>Mensaje:</b>
<blockquote>{message.content[:100]}...</blockquote>"""

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔙 Volver al mensaje",
                callback_data=f"anon_view_{message_id}"
            )]
        ])

        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    finally:
        anon_service.close()
    await callback.answer()


@router.callback_query(F.data.startswith("anon_reply_"), lambda cb: is_admin(cb.from_user.id))
async def start_anonymous_reply(callback: CallbackQuery, state: FSMContext):
    """Inicia el flujo de respuesta a un mensaje anónimo"""
    message_id = int(callback.data.replace("anon_reply_", ""))

    await state.update_data(reply_message_id=message_id)

    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Escriba su respuesta al mensaje anónimo...</i>\n\n"
        f"💬 Esta respuesta será enviada al remitente.\n"
        f"Escriba su mensaje a continuación:",
        reply_markup=back_keyboard(f"anon_view_{message_id}"),
        parse_mode="HTML"
    )
    await state.set_state(AnonymousReplyStates.waiting_reply)
    await callback.answer()


@router.message(AnonymousReplyStates.waiting_reply)
async def process_anonymous_reply(message: Message, state: FSMContext):
    """Procesa la respuesta al mensaje anónimo"""
    data = await state.get_data()
    message_id = data.get("reply_message_id")

    if not message_id:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Ha ocurrido un error...</i>\n\n"
            f"No se encontró el mensaje al que responder.",
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML"
        )
        await state.clear()
        return

    reply_content = message.text.strip()

    if len(reply_content) < 1:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>La respuesta está vacía...</i>\n\n"
            f"Por favor, escriba una respuesta.",
            reply_markup=back_keyboard(f"anon_view_{message_id}"),
            parse_mode="HTML"
        )
        return

    anon_service = AnonymousMessageService()
    try:
        # Guardar respuesta en el mensaje
        success = anon_service.reply_to_message(message_id, message.from_user.id, reply_content)

        if not success:
            await message.answer(
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>No se pudo guardar la respuesta...</i>",
                reply_markup=admin_menu_keyboard(),
                parse_mode="HTML"
            )
            await state.clear()
            return

        # Obtener el mensaje para enviar la respuesta al remitente
        anon_message = anon_service.get_message(message_id)

        if anon_message and anon_message.sender_id:
            try:
                # Enviar respuesta al remitente
                await message.bot.send_message(
                    chat_id=anon_message.sender_id,
                    text=f"""🎩 <b>Lucien:</b>

<i>Diana ha respondido a su susurro...</i>

💬 <b>Su mensaje:</b>
<blockquote>{anon_message.content[:100]}{'...' if len(anon_message.content) > 100 else ''}</blockquote>

💌 <b>Respuesta de Diana:</b>
<blockquote>{reply_content}</blockquote>

<i>El círculo exclusivo agradece su confianza.</i>""",
                    parse_mode="HTML"
                )

                await message.answer(
                    f"🎩 <b>Lucien:</b>\n\n"
                    f"<i>Respuesta enviada exitosamente...</i>\n\n"
                    f"✅ El remitente ha recibido su respuesta.",
                    reply_markup=anonymous_messages_menu_keyboard(),
                    parse_mode="HTML"
                )

                logger.info(f"Respuesta enviada a mensaje anónimo {message_id} por admin {message.from_user.id}")

            except Exception as e:
                logger.error(f"Error enviando respuesta a usuario {anon_message.sender_id}: {e}")
                await message.answer(
                    f"🎩 <b>Lucien:</b>\n\n"
                    f"<i>La respuesta se guardó pero no se pudo enviar...</i>\n\n"
                    f"⚠️ El usuario puede haber bloqueado al bot.",
                    reply_markup=anonymous_messages_menu_keyboard(),
                    parse_mode="HTML"
                )
        else:
            await message.answer(
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>Respuesta guardada pero no se pudo contactar al remitente.</i>",
                reply_markup=anonymous_messages_menu_keyboard(),
                parse_mode="HTML"
            )
    finally:
        anon_service.close()

    await state.clear()


@router.callback_query(F.data.startswith("anon_delete_"), lambda cb: is_admin(cb.from_user.id))
async def delete_anonymous_message(callback: CallbackQuery):
    """Elimina un mensaje anónimo"""
    message_id = int(callback.data.replace("anon_delete_", ""))

    anon_service = AnonymousMessageService()
    try:
        success = anon_service.delete_message(message_id)

        if success:
            await callback.message.edit_text(
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>El susurro ha sido silenciado...</i>\n\n"
                f"🗑️ Mensaje eliminado.",
                reply_markup=anonymous_messages_menu_keyboard(),
                parse_mode="HTML"
            )
            logger.info(f"Mensaje anónimo {message_id} eliminado por admin {callback.from_user.id}")
        else:
            await callback.answer("No se pudo eliminar el mensaje", show_alert=True)
    finally:
        anon_service.close()
    await callback.answer()
