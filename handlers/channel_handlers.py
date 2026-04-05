"""
Handlers de Canales - Lucien Bot

Gestión de registro y configuración de canales.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.channel_service import ChannelService
from services.user_service import UserService
from keyboards.inline_keyboards import (
    channel_type_keyboard, channel_actions_keyboard,
    channel_management_keyboard, confirmation_keyboard,
    wait_time_keyboard, back_keyboard
)
from utils.lucien_voice import LucienVoice
import logging

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class ChannelStates(StatesGroup):
    waiting_channel_message = State()
    confirming_channel = State()
    selecting_channel_type = State()
    configuring_wait_time = State()
    configuring_invite_link = State()


# ==================== REGISTRO DE CANAL ====================

@router.callback_query(F.data == "add_channel")
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    """Inicia el flujo de agregar canal"""
    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Para registrar un nuevo dominio en los archivos de Diana,\n"
        f"necesito que reenvíe cualquier mensaje del canal objetivo.</i>\n\n"
        f"📋 <b>Instrucciones:</b>\n"
        f"1. Vaya al canal que desea registrar\n"
        f"2. Reenvíe cualquier mensaje de ese canal aquí\n"
        f"3. Yo extraeré el ID automáticamente\n\n"
        f"<i>Esto me permitirá identificar el dominio correctamente...</i>",
        reply_markup=back_keyboard("admin_channels"),
        parse_mode="HTML"
    )
    await state.set_state(ChannelStates.waiting_channel_message)
    await callback.answer()


@router.message(ChannelStates.waiting_channel_message, F.forward_from_chat)
async def process_channel_message(message: Message, state: FSMContext):
    """Procesa el mensaje reenviado del canal"""
    forwarded_chat = message.forward_from_chat
    
    if not forwarded_chat:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>No pude identificar el origen de ese mensaje.\n"
            f"Asegúrese de reenviar desde el canal directamente...</i>",
            parse_mode="HTML"
        )
        return
    
    # Guardar datos del canal
    await state.update_data(
        channel_id=forwarded_chat.id,
        channel_name=forwarded_chat.title or forwarded_chat.username or "Canal sin nombre"
    )
    
    await message.answer(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>He detectado el siguiente dominio:</i>\n\n"
        f"📋 <b>Nombre:</b> {forwarded_chat.title or 'Sin nombre'}\n"
        f"🆔 <b>ID:</b> <code>{forwarded_chat.id}</code>\n\n"
        f"<i>¿Desea registrar este canal en los archivos de Diana?</i>",
        reply_markup=confirmation_keyboard("confirm_channel", "admin_channels"),
        parse_mode="HTML"
    )
    await state.set_state(ChannelStates.confirming_channel)


@router.callback_query(ChannelStates.confirming_channel, F.data == "confirm_channel")
async def confirm_channel(callback: CallbackQuery, state: FSMContext):
    """Confirma el registro del canal y pide tipo"""
    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Excelente. Ahora, ¿qué tipo de dominio es este?</i>\n\n"
        f"🚪 <b>Vestíbulo (Free):</b> Acceso con tiempo de espera\n"
        f"👑 <b>El Diván (VIP):</b> Acceso mediante tokens",
        reply_markup=channel_type_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ChannelStates.selecting_channel_type)
    await callback.answer()


@router.callback_query(ChannelStates.selecting_channel_type, F.data.startswith("channel_type_"))
async def set_channel_type(callback: CallbackQuery, state: FSMContext):
    """Establece el tipo de canal y registra"""
    channel_type = callback.data.replace("channel_type_", "")
    data = await state.get_data()
    
    channel_service = ChannelService()
    
    try:
        channel = channel_service.create_channel(
            channel_id=data['channel_id'],
            channel_name=data['channel_name'],
            channel_type=channel_type
        )
        
        await callback.message.edit_text(
            LucienVoice.admin_channel_registered(data['channel_name'], channel_type),
            reply_markup=channel_management_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error registrando canal: {e}")
        await callback.message.edit_text(
            LucienVoice.error_message("el registro del canal"),
            reply_markup=channel_management_keyboard(),
            parse_mode="HTML"
        )
    
    await state.clear()
    await callback.answer()


# ==================== LISTAR CANALES ====================

@router.callback_query(F.data == "list_channels")
async def list_channels(callback: CallbackQuery):
    """Lista todos los canales registrados"""
    channel_service = ChannelService()
    channels = channel_service.get_all_channels()
    
    if not channels:
        await callback.message.edit_text(
            LucienVoice.admin_channel_list([]),
            reply_markup=channel_management_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Mostrar lista con botones para cada canal
    text = LucienVoice.admin_channel_list(channels)
    
    # Agregar botones para cada canal
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for ch in channels:
        emoji = "🚪" if ch.channel_type.value == "free" else "👑"
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {ch.channel_name or 'Sin nombre'}",
            callback_data=f"channel_detail_{ch.id}"
        )])
    
    buttons.append([InlineKeyboardButton(
        text="🔙 Volver",
        callback_data="admin_channels"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("channel_detail_"))
async def channel_detail(callback: CallbackQuery):
    """Muestra detalles y acciones de un canal"""
    channel_id = int(callback.data.replace("channel_detail_", ""))
    
    channel_service = ChannelService()
    channel = channel_service.get_channel_by_db_id(channel_id)
    
    if not channel:
        await callback.answer("Canal no encontrado", show_alert=True)
        return
    
    type_text = "Vestíbulo" if channel.channel_type.value == "free" else "Círculo VIP"
    type_emoji = "🚪" if channel.channel_type.value == "free" else "👑"
    
    pending_count = channel_service.count_pending_requests(channel_id) if channel.channel_type.value == "free" else 0
    
    text = f"""🎩 <b>Lucien:</b>

<i>Detalles del dominio seleccionado...</i>

{type_emoji} <b>{channel.channel_name or 'Sin nombre'}</b>
📋 <b>Tipo:</b> {type_text}
🆔 <b>ID:</b> <code>{channel.channel_id}</code>
"""
    
    if channel.channel_type.value == "free":
        text += f"⏱️ <b>Tiempo de espera:</b> {channel.wait_time_minutes} minutos\n"
        text += f"👥 <b>Solicitudes pendientes:</b> {pending_count}\n"
    
    text += f"\n<i>¿Qué desea hacer con este dominio?</i>"
    
    await callback.message.edit_text(
        text,
        reply_markup=channel_actions_keyboard(channel_id, channel.channel_type.value),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== CONFIGURAR TIEMPO DE ESPERA ====================

@router.callback_query(F.data.startswith("config_wait_"))
async def config_wait_time(callback: CallbackQuery, state: FSMContext):
    """Configura tiempo de espera para canal Free"""
    channel_id = int(callback.data.replace("config_wait_", ""))
    await state.update_data(channel_id=channel_id)
    
    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>¿Cuánta paciencia requerirán los visitantes de este vestíbulo?</i>\n\n"
        f"Seleccione el tiempo de espera antes de la aceptación automática:",
        reply_markup=wait_time_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ChannelStates.configuring_wait_time)
    await callback.answer()


@router.callback_query(ChannelStates.configuring_wait_time, F.data.startswith("wait_"))
async def set_wait_time(callback: CallbackQuery, state: FSMContext):
    """Establece el tiempo de espera"""
    data = callback.data.replace("wait_", "")
    
    if data == "custom":
        await callback.message.edit_text(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Indíqueme el tiempo de espera deseado en minutos...</i>\n\n"
            f"Ejemplo: <code>7</code> para 7 minutos",
            reply_markup=back_keyboard(),
            parse_mode="HTML"
        )
        return
    
    minutes = int(data)
    state_data = await state.get_data()
    channel_id = state_data['channel_id']
    
    channel_service = ChannelService()
    channel_service.update_wait_time(channel_id, minutes)
    
    await callback.message.edit_text(
        LucienVoice.admin_wait_time_updated(minutes),
        reply_markup=back_keyboard(f"channel_detail_{channel_id}"),
        parse_mode="HTML"
    )
    await state.clear()
    await callback.answer()


# ==================== CONFIGURAR ENLACE DE INVITACIÓN ====================

@router.callback_query(F.data.startswith("config_invite_"))
async def config_invite_link_start(callback: CallbackQuery, state: FSMContext):
    """Inicia la configuración del enlace de invitación"""
    channel_id = int(callback.data.replace("config_invite_", ""))

    channel_service = ChannelService()
    channel = channel_service.get_channel_by_db_id(channel_id)

    current = f"\n\n<i>Enlace actual:</i> <code>{channel.invite_link or 'No configurado'}</code>" if channel else ""

    await state.update_data(channel_id=channel_id)

    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Proporcione el enlace de invitación para este vestíbulo.</i>\n\n"
        f"<i>Puede ser un enlace permanente o un enlace con期限:</i>\n"
        f"<code>https://t.me/+ABC123xyz</code>\n"
        f"<code>https://t.me/srtakinky</code>{current}\n\n"
        f"<i>Envíe el enlace o escriba \"quitar\" para eliminarlo.</i>",
        reply_markup=back_keyboard(f"channel_detail_{channel_id}"),
        parse_mode="HTML"
    )
    await state.set_state(ChannelStates.configuring_invite_link)
    await callback.answer()


@router.message(ChannelStates.configuring_invite_link)
async def process_invite_link(message: Message, state: FSMContext):
    """Procesa el enlace de invitación ingresado"""
    text = message.text.strip()

    if text.lower() == "quitar":
        link = None
    else:
        link = text

    data = await state.get_data()
    channel_id = data["channel_id"]

    channel_service = ChannelService()
    channel_service.update_invite_link(channel_id, link)

    channel = channel_service.get_channel_by_db_id(channel_id)
    name = channel.channel_name if channel else "este vestíbulo"

    if link:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>El enlace de invitación para <b>{name}</b> ha sido actualizado.</i>\n\n"
            f"🔗 <code>{link}</code>\n\n"
            f"<i>Este enlace se enviará a los visitantes al ser aprobados.</i>",
            reply_markup=back_keyboard(f"channel_detail_{channel_id}"),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>El enlace de invitación para <b>{name}</b> ha sido eliminado.</i>\n\n"
            f"<i>Los visitantes no recibirán enlace al ser aprobados.</i>",
            reply_markup=back_keyboard(f"channel_detail_{channel_id}"),
            parse_mode="HTML"
        )

    await state.clear()


# ==================== APROBAR SOLICITUDES PENDIENTES ====================

@router.callback_query(F.data.startswith("pending_req_"))
async def view_pending_requests(callback: CallbackQuery):
    """Ver solicitudes pendientes de un canal"""
    channel_id = int(callback.data.replace("pending_req_", ""))
    
    channel_service = ChannelService()
    requests = channel_service.get_pending_requests_by_channel(channel_id)
    count = len(requests)
    
    await callback.message.edit_text(
        LucienVoice.admin_pending_requests(count, requests),
        reply_markup=back_keyboard(f"channel_detail_{channel_id}"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("approve_all_"))
async def approve_all_requests(callback: CallbackQuery):
    """Aprueba todas las solicitudes pendientes de un canal"""
    channel_id = int(callback.data.replace("approve_all_", ""))
    
    channel_service = ChannelService()
    count = channel_service.approve_all_pending(channel_id)
    
    await callback.message.edit_text(
        LucienVoice.admin_requests_cleared(count),
        reply_markup=back_keyboard(f"channel_detail_{channel_id}"),
        parse_mode="HTML"
    )
    await callback.answer(f"{count} solicitudes aprobadas")


# ==================== ELIMINAR CANAL ====================

@router.callback_query(F.data.startswith("delete_channel_"))
async def delete_channel_confirm(callback: CallbackQuery):
    """Confirma eliminación de canal"""
    channel_id = int(callback.data.replace("delete_channel_", ""))
    
    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>¿Está seguro de que desea remover este dominio de los archivos de Diana?</i>\n\n"
        f"⚠️ <b>Esta acción no se puede deshacer.</b>",
        reply_markup=confirmation_keyboard(f"confirm_delete_{channel_id}", f"channel_detail_{channel_id}"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_channel(callback: CallbackQuery):
    """Elimina el canal"""
    channel_id = int(callback.data.replace("confirm_delete_", ""))
    
    channel_service = ChannelService()
    channel = channel_service.get_channel_by_db_id(channel_id)
    
    if channel:
        channel_name = channel.channel_name
        channel_service.delete_channel(channel_id)
        
        await callback.message.edit_text(
            LucienVoice.admin_channel_deleted(channel_name),
            reply_markup=channel_management_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            LucienVoice.error_message("la eliminación"),
            reply_markup=channel_management_keyboard(),
            parse_mode="HTML"
        )
    
    await callback.answer()
