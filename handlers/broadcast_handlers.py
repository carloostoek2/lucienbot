"""
Handlers de Broadcasting - Lucien Bot

Flujo conversacional completo para enviar mensajes con reacciones.
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config.settings import bot_config
from services.broadcast_service import BroadcastService
from services.channel_service import ChannelService
from keyboards.inline_keyboards import back_keyboard, confirmation_keyboard, cancel_keyboard, broadcast_back_keyboard
from utils.lucien_voice import LucienVoice
import logging

logger = logging.getLogger(__name__)
router = Router()


# Función helper para verificar admin
def is_admin(user_id: int) -> bool:
    return user_id in bot_config.ADMIN_IDS


# Estados para FSM
class BroadcastStates(StatesGroup):
    selecting_channel = State()
    waiting_text = State()
    waiting_attachment_decision = State()
    waiting_attachment = State()
    waiting_reaction_decision = State()
    selecting_reactions = State()
    waiting_protection_decision = State()
    confirming = State()


# ==================== INICIAR BROADCAST ====================

@router.callback_query(F.data == "send_broadcast", lambda cb: is_admin(cb.from_user.id))
async def send_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Inicia el flujo de broadcast - seleccionar canal"""
    channel_service = ChannelService()
    channels = channel_service.get_all_channels()
    
    if not channels:
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

<i>No hay dominios registrados para enviar mensajes...</i>

👉 <i>Registre un canal primero desde el panel de administración.</i>""",
            reply_markup=back_keyboard("admin_gamification"),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Crear botones para cada canal
    buttons = []
    for ch in channels:
        emoji = "🚪" if ch.channel_type.value == "free" else "👑"
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {ch.channel_name or 'Sin nombre'}",
            callback_data=f"broadcast_channel_{ch.channel_id}"
        )])
    
    buttons.append([InlineKeyboardButton(
        text="🔙 Cancelar",
        callback_data="admin_gamification"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        f"""🎩 <b>Lucien:</b>

<i>¿A qué dominio desea enviar su mensaje?</i>

📋 Seleccione el canal:""",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.selecting_channel)
    await callback.answer()


@router.callback_query(BroadcastStates.selecting_channel, F.data.startswith("broadcast_channel_"))
async def select_channel_for_broadcast(callback: CallbackQuery, state: FSMContext):
    """Canal seleccionado, pedir texto"""
    channel_id = int(callback.data.replace("broadcast_channel_", ""))
    
    channel_service = ChannelService()
    channel = channel_service.get_channel_by_id(channel_id)
    
    if not channel:
        await callback.answer("Canal no encontrado", show_alert=True)
        return
    
    await state.update_data(
        channel_id=channel_id,
        channel_name=channel.channel_name
    )
    
    try:
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

<i>Preparando mensaje para <b>{channel.channel_name}</b>...</i>

📋 <b>Paso 1 de 6:</b> Texto del mensaje

Envíe el texto que desea publicar. Puede usar formato HTML:
• &lt;b&gt;negrita&lt;/b&gt;
• &lt;i&gt;cursiva&lt;/i&gt;
• &lt;code&gt;código&lt;/code&gt;""",
            reply_markup=broadcast_back_keyboard("waiting_text"),
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass  # Ignorar error de mensaje no modificado
        else:
            raise
    await state.set_state(BroadcastStates.waiting_text)
    await callback.answer()


@router.message(BroadcastStates.waiting_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    """Procesa el texto del mensaje"""
    text = message.text or message.caption or ""
    
    await state.update_data(text=text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Adjuntar foto/archivo", callback_data="attach_yes")],
        [InlineKeyboardButton(text="⏭️ Omitir adjunto", callback_data="attach_no")],
        [InlineKeyboardButton(text="🔙 Volver al texto", callback_data="broadcast_back_text")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")]
    ])
    
    await message.answer(
        f"""🎩 <b>Lucien:</b>

<i>Texto recibido. ¿Desea incluir algún adjunto?</i>

📋 <b>Paso 2 de 6:</b> Adjunto

Puede agregar una foto, video o archivo al mensaje.""",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.waiting_attachment_decision)


@router.callback_query(BroadcastStates.waiting_attachment_decision, F.data == "broadcast_back_text")
async def back_to_text(callback: CallbackQuery, state: FSMContext):
    """Regresar a ingresar texto"""
    data = await state.get_data()
    try:
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

<i>Preparando mensaje para <b>{data.get('channel_name', 'Desconocido')}</b>...</i>

📋 <b>Paso 1 de 6:</b> Texto del mensaje

Envíe el texto que desea publicar. Puede usar formato HTML:
• &lt;b&gt;negrita&lt;/b&gt;
• &lt;i&gt;cursiva&lt;/i&gt;
• &lt;code&gt;código&lt;/code&gt;""",
            reply_markup=broadcast_back_keyboard("waiting_text"),
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.waiting_text)
    await callback.answer()


@router.callback_query(BroadcastStates.waiting_attachment_decision, F.data == "attach_yes")
async def want_attachment(callback: CallbackQuery, state: FSMContext):
    """Usuario quiere adjuntar algo"""
    try:
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

<i>Envíe la foto o archivo que desea adjuntar...</i>

📋 <b>Paso 2 de 6:</b> Adjunto

Puede enviar:
• Foto
• Video
• Documento/Archivo""",
            reply_markup=broadcast_back_keyboard("waiting_attachment"),
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.waiting_attachment)
    await callback.answer()


@router.callback_query(BroadcastStates.waiting_attachment_decision, F.data == "attach_no")
async def skip_attachment(callback: CallbackQuery, state: FSMContext):
    """Usuario omite adjunto"""
    await state.update_data(
        has_attachment=False,
        attachment_type=None,
        attachment_file_id=None
    )
    await ask_for_reactions(callback, state)


@router.message(BroadcastStates.waiting_attachment)
async def process_attachment(message: Message, state: FSMContext):
    """Procesa el archivo adjunto"""
    file_id = None
    attachment_type = None
    
    if message.photo:
        file_id = message.photo[-1].file_id  # Mejor calidad
        attachment_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        attachment_type = "video"
    elif message.document:
        file_id = message.document.file_id
        attachment_type = "document"
    elif message.animation:
        file_id = message.animation.file_id
        attachment_type = "animation"
    else:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>No pude reconocer el tipo de archivo.\n"
            f"Por favor envíe una foto, video o documento...</i>",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await state.update_data(
        has_attachment=True,
        attachment_type=attachment_type,
        attachment_file_id=file_id
    )
    
    await ask_for_reactions(message, state)


async def ask_for_reactions(target, state: FSMContext):
    """Pregunta si quiere agregar reacciones"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💋 Sí, agregar reacciones", callback_data="reaction_yes")],
        [InlineKeyboardButton(text="⏭️ No, sin reacciones", callback_data="reaction_no")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_attachment")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")]
    ])
    
    text = f"""🎩 <b>Lucien:</b>

<i>¿Desea incluir botones de reacción?</i>

📋 <b>Paso 3 de 6:</b> Reacciones

Los usuarios podrán reaccionar y recibir besitos."""
    
    try:
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    
    await state.set_state(BroadcastStates.waiting_reaction_decision)


@router.callback_query(BroadcastStates.waiting_reaction_decision, F.data == "broadcast_back_attachment")
async def back_to_attachment_decision(callback: CallbackQuery, state: FSMContext):
    """Regresar a decisión de adjunto"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Adjuntar foto/archivo", callback_data="attach_yes")],
        [InlineKeyboardButton(text="⏭️ Omitir adjunto", callback_data="attach_no")],
        [InlineKeyboardButton(text="🔙 Volver al texto", callback_data="broadcast_back_text")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")]
    ])
    
    try:
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

<i>¿Desea incluir algún adjunto?</i>

📋 <b>Paso 2 de 6:</b> Adjunto

Puede agregar una foto, video o archivo al mensaje.""",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.waiting_attachment_decision)
    await callback.answer()


@router.callback_query(BroadcastStates.waiting_reaction_decision, F.data == "reaction_yes")
async def want_reactions(callback: CallbackQuery, state: FSMContext):
    """Usuario quiere reacciones - mostrar emojis disponibles"""
    broadcast_service = BroadcastService()
    emojis = broadcast_service.get_all_emojis(active_only=True)
    
    if not emojis:
        try:
            await callback.message.edit_text(
                f"""🎩 <b>Lucien:</b>

<i>No hay emojis configurados para reacciones...</i>

👉 <i>Configure emojis primero desde "Configurar besitos".</i>""",
                reply_markup=back_keyboard("admin_gamification"),
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                raise
        await state.clear()
        await callback.answer()
        return
    
    # Guardar emojis seleccionados temporalmente
    await state.update_data(selected_emojis=[])
    
    await show_reaction_selection(callback, state)
    await callback.answer()


async def show_reaction_selection(callback: CallbackQuery, state: FSMContext):
    """Muestra la selección de emojis"""
    broadcast_service = BroadcastService()
    emojis = broadcast_service.get_all_emojis(active_only=True)
    data = await state.get_data()
    selected = data.get('selected_emojis', [])
    
    buttons = []
    for emoji in emojis:
        is_selected = emoji.id in selected
        check = "✅ " if is_selected else "⬜ "
        buttons.append([InlineKeyboardButton(
            text=f"{check}{emoji.emoji} = {emoji.besito_value} besitos",
            callback_data=f"toggle_reaction_{emoji.id}"
        )])
    
    buttons.append([InlineKeyboardButton(
        text="✅ Continuar",
        callback_data="reactions_selected"
    )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="broadcast_back_reactions"
    )])
    buttons.append([InlineKeyboardButton(
        text="❌ Cancelar",
        callback_data="admin_gamification"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

<i>Seleccione los emojis para este mensaje...</i>

📋 <b>Paso 3 de 6:</b> Reacciones

Toque para seleccionar/deseleccionar:""",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.selecting_reactions)


@router.callback_query(BroadcastStates.selecting_reactions, F.data == "broadcast_back_reactions")
async def back_from_reaction_selection(callback: CallbackQuery, state: FSMContext):
    """Regresar desde selección de reacciones"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💋 Sí, agregar reacciones", callback_data="reaction_yes")],
        [InlineKeyboardButton(text="⏭️ No, sin reacciones", callback_data="reaction_no")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_attachment")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")]
    ])
    
    try:
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

<i>¿Desea incluir botones de reacción?</i>

📋 <b>Paso 3 de 6:</b> Reacciones

Los usuarios podrán reaccionar y recibir besitos.""",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.waiting_reaction_decision)
    await callback.answer()


@router.callback_query(BroadcastStates.selecting_reactions, F.data.startswith("toggle_reaction_"))
async def toggle_reaction_selection(callback: CallbackQuery, state: FSMContext):
    """Toggle selección de emoji"""
    emoji_id = int(callback.data.replace("toggle_reaction_", ""))
    data = await state.get_data()
    selected = data.get('selected_emojis', [])
    
    if emoji_id in selected:
        selected.remove(emoji_id)
    else:
        selected.append(emoji_id)
    
    await state.update_data(selected_emojis=selected)
    await show_reaction_selection(callback, state)
    await callback.answer()


@router.callback_query(BroadcastStates.selecting_reactions, F.data == "reactions_selected")
async def reactions_selected(callback: CallbackQuery, state: FSMContext):
    """Emojis seleccionados, continuar"""
    data = await state.get_data()
    selected = data.get('selected_emojis', [])
    
    if not selected:
        await callback.answer("Seleccione al menos un emoji", show_alert=True)
        return
    
    await ask_for_protection(callback, state)
    await callback.answer()


@router.callback_query(BroadcastStates.waiting_reaction_decision, F.data == "reaction_no")
async def skip_reactions(callback: CallbackQuery, state: FSMContext):
    """Usuario no quiere reacciones"""
    await state.update_data(selected_emojis=[], has_reactions=False)
    await ask_for_protection(callback, state)
    await callback.answer()


async def ask_for_protection(target, state: FSMContext):
    """Pregunta por protección del mensaje"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔒 Proteger mensaje", callback_data="protect_yes")],
        [InlineKeyboardButton(text="⏭️ Sin protección", callback_data="protect_no")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_protection")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")]
    ])

    text = f"""🎩 <b>Lucien:</b>

<i>¿Desea proteger el mensaje?</i>

📋 <b>Paso 4 de 6:</b> Protección

🔒 <b>Proteger:</b> Impide copiar, reenviar y descargar el contenido.

⚠️ <b>Nota:</b> La protección solo funciona en canales con contenido protegido habilitado."""

    try:
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise

    await state.set_state(BroadcastStates.waiting_protection_decision)


@router.callback_query(BroadcastStates.waiting_protection_decision, F.data.startswith("protect_"))
async def set_protection(callback: CallbackQuery, state: FSMContext):
    """Establece protección y muestra preview"""
    is_protected = callback.data == "protect_yes"
    await state.update_data(is_protected=is_protected)
    
    await show_broadcast_preview(callback, state)
    await callback.answer()


@router.callback_query(BroadcastStates.waiting_protection_decision, F.data == "broadcast_back_protection")
async def back_from_protection(callback: CallbackQuery, state: FSMContext):
    """Regresar desde protección a reacciones"""
    data = await state.get_data()
    has_reactions = len(data.get('selected_emojis', [])) > 0
    
    if has_reactions:
        # Si tiene reacciones, volver a selección
        await state.update_data(selected_emojis=[])
        await show_reaction_selection(callback, state)
    else:
        # Si no tiene reacciones, volver a decisión de reacciones
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💋 Sí, agregar reacciones", callback_data="reaction_yes")],
            [InlineKeyboardButton(text="⏭️ No, sin reacciones", callback_data="reaction_no")],
            [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_attachment")],
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")]
        ])
        
        try:
            await callback.message.edit_text(
                f"""🎩 <b>Lucien:</b>

<i>¿Desea incluir botones de reacción?</i>

📋 <b>Paso 3 de 6:</b> Reacciones

Los usuarios podrán reaccionar y recibir besitos.""",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                raise
        await state.set_state(BroadcastStates.waiting_reaction_decision)
    await callback.answer()


async def show_broadcast_preview(callback: CallbackQuery, state: FSMContext):
    """Muestra preview del mensaje antes de enviar"""
    data = await state.get_data()
    
    # Construir preview
    preview_text = data.get('text', '')
    has_attachment = data.get('has_attachment', False)
    has_reactions = len(data.get('selected_emojis', [])) > 0
    is_protected = data.get('is_protected', False)
    
    info_text = f"""🎩 <b>Lucien:</b>

<i>Así se verá su mensaje en el canal...</i>

📋 <b>Resumen:</b>
   • Canal: {data.get('channel_name', 'Desconocido')}
   • Texto: {'✅' if preview_text else '❌'}
   • Adjunto: {'✅ ' + data.get('attachment_type', '') if has_attachment else '❌'}
   • Reacciones: {'✅' if has_reactions else '❌'}
   • Protección: {'🔒 Sí' if is_protected else '❌ No'}

---

<b>Preview del mensaje:</b>

{preview_text[:500]}{'...' if len(preview_text) > 500 else ''}

---

<i>¿Desea enviar este mensaje?</i>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Confirmar", callback_data="confirm_broadcast")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_preview")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")]
    ])
    
    try:
        await callback.message.edit_text(
            info_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.confirming)


@router.callback_query(BroadcastStates.confirming, F.data == "broadcast_back_preview")
async def back_from_preview(callback: CallbackQuery, state: FSMContext):
    """Regresar desde preview a protección"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔒 Proteger mensaje", callback_data="protect_yes")],
        [InlineKeyboardButton(text="⏭️ Sin protección", callback_data="protect_no")],
        [InlineKeyboardButton(text="🔙 Volver", callback_data="broadcast_back_protection")],
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_gamification")]
    ])
    
    try:
        await callback.message.edit_text(
            f"""🎩 <b>Lucien:</b>

<i>¿Desea proteger el mensaje?</i>

📋 <b>Paso 4 de 6:</b> Protección

🔒 <b>Proteger:</b> Impide copiar, reenviar y descargar el contenido.

⚠️ <b>Nota:</b> La protección solo funciona en canales con contenido protegido habilitado.""",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await state.set_state(BroadcastStates.waiting_protection_decision)
    await callback.answer()


@router.callback_query(BroadcastStates.confirming, F.data == "confirm_broadcast")
async def confirm_and_send_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Envía el mensaje al canal"""
    data = await state.get_data()
    
    channel_id = data.get('channel_id')
    text = data.get('text', '')
    has_attachment = data.get('has_attachment', False)
    attachment_type = data.get('attachment_type')
    attachment_file_id = data.get('attachment_file_id')
    selected_emojis = data.get('selected_emojis', [])
    is_protected = data.get('is_protected', False)
    
    broadcast_service = BroadcastService()
    
    try:
        # Construir teclado de reacciones
        reply_markup = None
        if selected_emojis:
            buttons = []
            for emoji_id in selected_emojis:
                emoji = broadcast_service.get_reaction_emoji(emoji_id)
                if emoji:
                    buttons.append([InlineKeyboardButton(
                        text=f"{emoji.emoji}",
                        callback_data=f"react_0_{emoji.id}"  # broadcast_id se actualizará después
                    )])
            if buttons:
                reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Enviar mensaje
        protect_content = is_protected
        
        if has_attachment and attachment_file_id:
            # Enviar con adjunto
            if attachment_type == "photo":
                sent_message = await bot.send_photo(
                    chat_id=channel_id,
                    photo=attachment_file_id,
                    caption=text,
                    reply_markup=reply_markup,
                    protect_content=protect_content
                )
            elif attachment_type == "video":
                sent_message = await bot.send_video(
                    chat_id=channel_id,
                    video=attachment_file_id,
                    caption=text,
                    reply_markup=reply_markup,
                    protect_content=protect_content
                )
            elif attachment_type == "document":
                sent_message = await bot.send_document(
                    chat_id=channel_id,
                    document=attachment_file_id,
                    caption=text,
                    reply_markup=reply_markup,
                    protect_content=protect_content
                )
            elif attachment_type == "animation":
                sent_message = await bot.send_animation(
                    chat_id=channel_id,
                    animation=attachment_file_id,
                    caption=text,
                    reply_markup=reply_markup,
                    protect_content=protect_content
                )
            else:
                sent_message = await bot.send_message(
                    chat_id=channel_id,
                    text=text,
                    reply_markup=reply_markup
                )
        else:
            # Enviar solo texto
            sent_message = await bot.send_message(
                chat_id=channel_id,
                text=text,
                reply_markup=reply_markup,
                protect_content=protect_content
            )
        
        # Registrar en base de datos
        broadcast = broadcast_service.create_broadcast_message(
            message_id=sent_message.message_id,
            channel_id=channel_id,
            admin_id=callback.from_user.id,
            text=text,
            has_attachment=has_attachment,
            attachment_type=attachment_type,
            attachment_file_id=attachment_file_id,
            has_reactions=len(selected_emojis) > 0,
            is_protected=is_protected
        )
        
        # Actualizar callback_data de los botones con el ID real del broadcast
        if reply_markup and selected_emojis:
            buttons = []
            for emoji_id in selected_emojis:
                emoji = broadcast_service.get_reaction_emoji(emoji_id)
                if emoji:
                    buttons.append([InlineKeyboardButton(
                        text=f"{emoji.emoji}",
                        callback_data=f"react_{broadcast.id}_{emoji.id}"
                    )])
            new_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            try:
                await bot.edit_message_reply_markup(
                    chat_id=channel_id,
                    message_id=sent_message.message_id,
                    reply_markup=new_markup
                )
            except Exception as e:
                if "message is not modified" in str(e).lower():
                    pass  # Ignorar si no hay cambios
                else:
                    logger.warning(f"Error actualizando reply markup: {e}")
        
        try:
            await callback.message.edit_text(
                f"""🎩 <b>Lucien:</b>

<i>El mensaje ha sido transmitido a los dominios de Diana...</i>

✅ <b>Broadcast enviado exitosamente.</b>

📊 <b>Detalles:</b>
   • Canal: {data.get('channel_name')}
   • Mensaje ID: <code>{sent_message.message_id}</code>
   • Reacciones: {'Sí' if selected_emojis else 'No'}

<i>Los visitantes podrán interactuar con él.</i>""",
                reply_markup=back_keyboard("admin_gamification"),
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                raise
        
        logger.info(f"Broadcast enviado: channel={channel_id}, message={sent_message.message_id}")
        
    except Exception as e:
        logger.error(f"Error enviando broadcast: {e}")
        try:
            await callback.message.edit_text(
                LucienVoice.error_message("el envío del mensaje"),
                reply_markup=back_keyboard("admin_gamification"),
                parse_mode="HTML"
            )
        except Exception as e2:
            if "message is not modified" in str(e2).lower():
                pass
            else:
                logger.error(f"Error mostrando mensaje de error: {e2}")
    
    await state.clear()
    await callback.answer()
