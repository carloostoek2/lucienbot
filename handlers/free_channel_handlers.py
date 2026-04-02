"""
Handlers de Canal Free - Lucien Bot

Gestiona las solicitudes de acceso a canales gratuitos.
"""
from aiogram import Router, F
from aiogram.types import ChatJoinRequest, ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION
from services.channel_service import ChannelService
from services.user_service import UserService
from services.scheduler_service import get_scheduler
from utils.lucien_voice import LucienVoice
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.chat_join_request()
async def handle_join_request(join_request: ChatJoinRequest):
    """
    Handler para solicitudes de unión a canales.
    Este es el punto de entrada principal para el flujo Free.
    """
    user = join_request.from_user
    chat = join_request.chat
    
    logger.info(f"Solicitud de unión: user={user.id}, chat={chat.id}")
    
    # Registrar/actualizar usuario
    user_service = UserService()
    user_service.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Verificar si el canal está registrado
    channel_service = ChannelService()
    channel = channel_service.get_channel_by_id(chat.id)
    
    if not channel:
        logger.warning(f"Canal {chat.id} no registrado en el sistema")
        return
    
    if not channel.is_active:
        logger.warning(f"Canal {chat.id} está inactivo")
        return
    
    # Verificar si ya hay una solicitud pendiente
    existing_request = channel_service.get_pending_request(user.id, channel.id)
    if existing_request:
        logger.info(f"Usuario {user.id} ya tiene solicitud pendiente")
        # Enviar mensaje de impaciencia
        await join_request.bot.send_message(
            chat_id=user.id,
            text=LucienVoice.free_entry_impatient(channel.channel_name or "Los Kinkys"),
            parse_mode="HTML"
        )
        return
    
    # Crear solicitud pendiente
    try:
        pending = channel_service.create_pending_request(
            user_id=user.id,
            channel_id=channel.id,
            username=user.username,
            first_name=user.first_name
        )

        # Programar mensaje ritual con delay de 30 segundos
        # IMPORTANTE: pasar chat.id (Telegram channel ID), no channel.id (DB PK).
        # _send_free_welcome_job usa get_channel_by_id que espera Telegram channel ID.
        scheduler = get_scheduler()
        if scheduler:
            scheduler.schedule_free_welcome(user.id, chat.id)

        logger.info(f"Solicitud pendiente creada: id={pending.id}, approve_at={pending.scheduled_approval_at}")

    except Exception as e:
        logger.error(f"Error procesando solicitud: {e}")


@router.chat_member(ChatMemberUpdatedFilter(LEAVE_TRANSITION))
async def handle_member_leave(event: ChatMemberUpdated):
    """
    Handler para cuando un usuario abandona el canal.
    Cancela cualquier solicitud pendiente.
    """
    user = event.from_user
    chat = event.chat
    
    logger.info(f"Usuario abandonó: user={user.id}, chat={chat.id}")
    
    # Verificar si el canal está registrado
    channel_service = ChannelService()
    channel = channel_service.get_channel_by_id(chat.id)
    
    if not channel:
        return
    
    # Cancelar solicitud pendiente si existe
    cancelled = channel_service.cancel_request(user.id, channel.id)
    if cancelled:
        logger.info(f"Solicitud cancelada para user={user.id}")
        
        # Notificar al usuario
        try:
            await event.bot.send_message(
                chat_id=user.id,
                text=LucienVoice.free_request_cancelled(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error notificando cancelación: {e}")


@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def handle_member_join(event: ChatMemberUpdated):
    """
    Handler para cuando un usuario es aceptado en el canal.
    """
    user = event.from_user
    chat = event.chat
    
    logger.info(f"Usuario aceptado: user={user.id}, chat={chat.id}")
    
    # Verificar si el canal está registrado
    channel_service = ChannelService()
    channel = channel_service.get_channel_by_id(chat.id)
    
    if not channel:
        return
    
    # Actualizar solicitud si existe
    pending = channel_service.get_pending_request(user.id, channel.id)
    if pending and pending.status == "pending":
        pending.status = "approved"
        pending.approved_at = datetime.utcnow()
        channel_service.db.commit()

        logger.info(f"Solicitud marcada como aprobada: id={pending.id}")

        # Enviar mensaje de bienvenida ritual con enlace
        try:
            message = LucienVoice.free_entry_welcome(channel.channel_name or "Los Kinkys")
            if channel.invite_link:
                message += f"\n{channel.invite_link}"
            await event.bot.send_message(
                chat_id=user.id,
                text=message,
                parse_mode="HTML",
                reply_markup=social_links_keyboard()
            )

            logger.info(f"Mensaje de bienvenida enviado a user={user.id}")
        except Exception as e:
            logger.error(f"Error enviando mensaje de bienvenida: {e}")
