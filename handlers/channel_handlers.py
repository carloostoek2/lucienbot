"""
Handlers de Canales - Lucien Bot

Gestión de registro y configuración de canales.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from keyboards.callback_data import (
    ApproveAllCallback,
    ChannelDetailCallback,
    ChannelTypeCallback,
    ConfigInviteCallback,
    ConfigWaitCallback,
    ConfirmDeleteChannelCallback,
    DeleteChannelCallback,
    PendingReqCallback,
    WaitTimeCallback,
)
from keyboards.inline_keyboards import (
    back_keyboard,
    channel_actions_keyboard,
    channel_management_keyboard,
    channel_type_keyboard,
    confirmation_keyboard,
    wait_time_keyboard,
)
from services.channel_service import ChannelService
from utils.lucien_voice import LucienVoice

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
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Para registrar un nuevo dominio en los archivos de Diana,\n"
        "necesito que reenvíe cualquier mensaje del canal objetivo.</i>\n\n"
        "📋 <b>Instrucciones:</b>\n"
        "1. Vaya al canal que desea registrar\n"
        "2. Reenvíe cualquier mensaje de ese canal aquí\n"
        "3. Yo extraeré el ID automáticamente\n\n"
        "<i>Esto me permitirá identificar el dominio correctamente...</i>",
        reply_markup=back_keyboard("admin_channels"),
        parse_mode="HTML",
    )
    await state.set_state(ChannelStates.waiting_channel_message)
    await callback.answer()


@router.message(ChannelStates.waiting_channel_message, F.forward_from_chat)
async def process_channel_message(message: Message, state: FSMContext):
    """Procesa el mensaje reenviado del canal"""
    forwarded_chat = message.forward_from_chat

    if not forwarded_chat:
        await message.answer(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>No pude identificar el origen de ese mensaje.\n"
            "Asegúrese de reenviar desde el canal directamente...</i>",
            parse_mode="HTML",
        )
        return

    # Guardar datos del canal
    await state.update_data(
        channel_id=forwarded_chat.id,
        channel_name=forwarded_chat.title or forwarded_chat.username or "Canal sin nombre",
    )

    await message.answer(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>He detectado el siguiente dominio:</i>\n\n"
        f"📋 <b>Nombre:</b> {forwarded_chat.title or 'Sin nombre'}\n"
        f"🆔 <b>ID:</b> <code>{forwarded_chat.id}</code>\n\n"
        f"<i>¿Desea registrar este canal en los archivos de Diana?</i>",
        reply_markup=confirmation_keyboard("confirm_channel", "admin_channels"),
        parse_mode="HTML",
    )
    await state.set_state(ChannelStates.confirming_channel)


@router.callback_query(ChannelStates.confirming_channel, F.data == "confirm_channel")
async def confirm_channel(callback: CallbackQuery, state: FSMContext):
    """Confirma el registro del canal y pide tipo"""
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Excelente. Ahora, ¿qué tipo de dominio es este?</i>\n\n"
        "🚪 <b>Vestíbulo (Free):</b> Acceso con tiempo de espera\n"
        "👑 <b>El Diván (VIP):</b> Acceso mediante tokens",
        reply_markup=channel_type_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(ChannelStates.selecting_channel_type)
    await callback.answer()


@router.callback_query(ChannelStates.selecting_channel_type, ChannelTypeCallback.filter())
async def set_channel_type(
    callback: CallbackQuery, state: FSMContext, callback_data: ChannelTypeCallback
):
    """Establece el tipo de canal y registra"""
    channel_type = callback_data.action
    data = await state.get_data()

    channel_service = ChannelService()

    try:
        channel = channel_service.create_channel(
            channel_id=data["channel_id"],
            channel_name=data["channel_name"],
            channel_type=channel_type,
        )

        logger.info(
            f"Canal registrado: {channel.channel_name} (ID: {channel.id}) por admin {callback.from_user.id}"
        )

        await callback.message.edit_text(
            LucienVoice.admin_channel_registered(data["channel_name"], channel_type),
            reply_markup=channel_management_keyboard(),
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Error registrando canal: {e}")
        await callback.message.edit_text(
            LucienVoice.error_message("el registro del canal"),
            reply_markup=channel_management_keyboard(),
            parse_mode="HTML",
        )
    finally:
        channel_service.close()

    await state.clear()
    await callback.answer()


# ==================== LISTAR CANALES ====================


@router.callback_query(F.data == "list_channels")
async def list_channels(callback: CallbackQuery):
    """Lista todos los canales registrados"""
    channel_service = ChannelService()
    try:
        channels = channel_service.get_all_channels()

        if not channels:
            await callback.message.edit_text(
                LucienVoice.admin_channel_list([]),
                reply_markup=channel_management_keyboard(),
                parse_mode="HTML",
            )
            await callback.answer()
            return

        # Mostrar lista con botones para cada canal
        text = LucienVoice.admin_channel_list(channels)

        # Agregar botones para cada canal
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        from keyboards.callback_data import ChannelDetailCallback

        buttons = []
        for ch in channels:
            emoji = "🚪" if ch.channel_type.value == "free" else "👑"
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{emoji} {ch.channel_name or 'Sin nombre'}",
                        callback_data=ChannelDetailCallback(channel_id=ch.id).pack(),
                    )
                ]
            )

        buttons.append([InlineKeyboardButton(text="🔙 Volver", callback_data="admin_channels")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    finally:
        channel_service.close()
    await callback.answer()


@router.callback_query(ChannelDetailCallback.filter())
async def channel_detail(callback: CallbackQuery, callback_data: ChannelDetailCallback):
    """Muestra detalles y acciones de un canal"""
    channel_id = callback_data.channel_id

    channel_service = ChannelService()
    try:
        channel = channel_service.get_channel_by_db_id(channel_id)

        if not channel:
            await callback.answer("Canal no encontrado", show_alert=True)
            return

        type_text = "Vestíbulo" if channel.channel_type.value == "free" else "Círculo VIP"
        type_emoji = "🚪" if channel.channel_type.value == "free" else "👑"

        pending_count = (
            channel_service.count_pending_requests(channel_id)
            if channel.channel_type.value == "free"
            else 0
        )

        text = f"""🎩 <b>Lucien:</b>

<i>Detalles del dominio seleccionado...</i>

{type_emoji} <b>{channel.channel_name or "Sin nombre"}</b>
📋 <b>Tipo:</b> {type_text}
🆔 <b>ID:</b> <code>{channel.channel_id}</code>
"""

        if channel.channel_type.value == "free":
            text += f"⏱️ <b>Tiempo de espera:</b> {channel.wait_time_minutes} minutos\n"
            text += f"👥 <b>Solicitudes pendientes:</b> {pending_count}\n"

        text += "\n<i>¿Qué desea hacer con este dominio?</i>"

        await callback.message.edit_text(
            text,
            reply_markup=channel_actions_keyboard(channel_id, channel.channel_type.value),
            parse_mode="HTML",
        )
    finally:
        channel_service.close()
    await callback.answer()


# ==================== CONFIGURAR TIEMPO DE ESPERA ====================


@router.callback_query(ConfigWaitCallback.filter())
async def config_wait_time(
    callback: CallbackQuery, state: FSMContext, callback_data: ConfigWaitCallback
):
    """Configura tiempo de espera para canal Free"""
    channel_id = callback_data.channel_id
    await state.update_data(channel_id=channel_id)

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>¿Cuánta paciencia requerirán los visitantes de este vestíbulo?</i>\n\n"
        "Seleccione el tiempo de espera antes de la aceptación automática:",
        reply_markup=wait_time_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(ChannelStates.configuring_wait_time)
    await callback.answer()


@router.callback_query(ChannelStates.configuring_wait_time, WaitTimeCallback.filter())
async def set_wait_time(
    callback: CallbackQuery, state: FSMContext, callback_data: WaitTimeCallback
):
    """Establece el tiempo de espera"""
    data = callback_data.minutes

    if data == "custom":
        await callback.message.edit_text(
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Indíqueme el tiempo de espera deseado en minutos...</i>\n\n"
            "Ejemplo: <code>7</code> para 7 minutos",
            reply_markup=back_keyboard(),
            parse_mode="HTML",
        )
        return

    minutes = int(data)
    state_data = await state.get_data()
    channel_id = state_data["channel_id"]

    channel_service = ChannelService()
    try:
        channel_service.update_wait_time(channel_id, minutes)

        await callback.message.edit_text(
            LucienVoice.admin_wait_time_updated(minutes),
            reply_markup=back_keyboard(ChannelDetailCallback(channel_id=channel_id).pack()),
            parse_mode="HTML",
        )
    finally:
        channel_service.close()
    await state.clear()
    await callback.answer()


# ==================== CONFIGURAR ENLACE DE INVITACIÓN ====================


@router.callback_query(ConfigInviteCallback.filter())
async def config_invite_link_start(
    callback: CallbackQuery, state: FSMContext, callback_data: ConfigInviteCallback
):
    """Inicia la configuración del enlace de invitación"""
    channel_id = callback_data.channel_id

    channel_service = ChannelService()
    try:
        channel = channel_service.get_channel_by_db_id(channel_id)

        current = (
            f"\n\n<i>Enlace actual:</i> <code>{channel.invite_link or 'No configurado'}</code>"
            if channel
            else ""
        )

        await state.update_data(channel_id=channel_id)

        await callback.message.edit_text(
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Proporcione el enlace de invitación para este vestíbulo.</i>\n\n"
            f"<i>Puede ser un enlace permanente o un enlace con期限:</i>\n"
            f"<code>https://t.me/+ABC123xyz</code>\n"
            f"<code>https://t.me/srtakinky</code>{current}\n\n"
            f'<i>Envíe el enlace o escriba "quitar" para eliminarlo.</i>',
            reply_markup=back_keyboard(ChannelDetailCallback(channel_id=channel_id).pack()),
            parse_mode="HTML",
        )
    finally:
        channel_service.close()
    await state.set_state(ChannelStates.configuring_invite_link)
    await callback.answer()


@router.message(ChannelStates.configuring_invite_link)
async def process_invite_link(message: Message, state: FSMContext):
    """Procesa el enlace de invitación ingresado"""
    text = message.text.strip()

    link = None if text.lower() == "quitar" else text

    data = await state.get_data()
    channel_id = data["channel_id"]

    channel_service = ChannelService()
    try:
        channel_service.update_invite_link(channel_id, link)

        channel = channel_service.get_channel_by_db_id(channel_id)
        name = channel.channel_name if channel else "este vestíbulo"

        if link:
            await message.answer(
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>El enlace de invitación para <b>{name}</b> ha sido actualizado.</i>\n\n"
                f"🔗 <code>{link}</code>\n\n"
                f"<i>Este enlace se enviará a los visitantes al ser aprobados.</i>",
                reply_markup=back_keyboard(ChannelDetailCallback(channel_id=channel_id).pack()),
                parse_mode="HTML",
            )
        else:
            await message.answer(
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>El enlace de invitación para <b>{name}</b> ha sido eliminado.</i>\n\n"
                f"<i>Los visitantes no recibirán enlace al ser aprobados.</i>",
                reply_markup=back_keyboard(ChannelDetailCallback(channel_id=channel_id).pack()),
                parse_mode="HTML",
            )
    finally:
        channel_service.close()

    await state.clear()


# ==================== APROBAR SOLICITUDES PENDIENTES ====================


@router.callback_query(PendingReqCallback.filter())
async def view_pending_requests(callback: CallbackQuery, callback_data: PendingReqCallback):
    """Ver solicitudes pendientes de un canal"""
    channel_id = callback_data.channel_id

    channel_service = ChannelService()
    try:
        requests = channel_service.get_pending_requests_by_channel(channel_id)
        count = len(requests)

        await callback.message.edit_text(
            LucienVoice.admin_pending_requests(count, requests),
            reply_markup=back_keyboard(ChannelDetailCallback(channel_id=channel_id).pack()),
            parse_mode="HTML",
        )
    finally:
        channel_service.close()
    await callback.answer()


@router.callback_query(ApproveAllCallback.filter())
async def approve_all_requests(callback: CallbackQuery, callback_data: ApproveAllCallback):
    """Aprueba todas las solicitudes pendientes de un canal"""
    channel_id = callback_data.channel_id

    channel_service = ChannelService()
    try:
        count = channel_service.approve_all_pending(channel_id)

        await callback.message.edit_text(
            LucienVoice.admin_requests_cleared(count),
            reply_markup=back_keyboard(ChannelDetailCallback(channel_id=channel_id).pack()),
            parse_mode="HTML",
        )
    finally:
        channel_service.close()
    await callback.answer(f"{count} solicitudes aprobadas")


# ==================== ELIMINAR CANAL ====================


@router.callback_query(DeleteChannelCallback.filter())
async def delete_channel_confirm(callback: CallbackQuery, callback_data: DeleteChannelCallback):
    """Confirma eliminación de canal"""
    channel_id = callback_data.channel_id

    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>¿Está seguro de que desea remover este dominio de los archivos de Diana?</i>\n\n"
        "⚠️ <b>Esta acción no se puede deshacer.</b>",
        reply_markup=confirmation_keyboard(
            ConfirmDeleteChannelCallback(channel_id=channel_id).pack(),
            ChannelDetailCallback(channel_id=channel_id).pack(),
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ConfirmDeleteChannelCallback.filter())
async def delete_channel(callback: CallbackQuery, callback_data: ConfirmDeleteChannelCallback):
    """Elimina el canal"""
    channel_id = callback_data.channel_id

    channel_service = ChannelService()
    try:
        channel = channel_service.get_channel_by_db_id(channel_id)

        if channel:
            channel_name = channel.channel_name
            channel_service.delete_channel(channel_id)
            logger.info(
                f"Canal eliminado: {channel_name} (ID: {channel_id}) por admin {callback.from_user.id}"
            )

            await callback.message.edit_text(
                LucienVoice.admin_channel_deleted(channel_name),
                reply_markup=channel_management_keyboard(),
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(
                LucienVoice.error_message("la eliminación"),
                reply_markup=channel_management_keyboard(),
                parse_mode="HTML",
            )
    finally:
        channel_service.close()

    await callback.answer()
