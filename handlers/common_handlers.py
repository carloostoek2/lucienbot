"""
Handlers Comunes - Lucien Bot

Handlers para comandos básicos y flujos generales.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from keyboards.inline_keyboards import (
    admin_menu_keyboard,
    main_menu_keyboard,
    returning_user_keyboard,
    vip_access_keyboard,
)
from services import get_service
from services.mission_service import MissionService
from services.user_service import UserService
from services.vip_service import VIPService
from utils.admin import is_admin
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)
router = Router()


def _redact_start_log_args(args: str | None) -> str:
    """Redact sensitive deep-link tokens; log presence/length only."""
    if not args:
        return "none"
    if args == "free":
        return "free"
    return f"token(len={len(args)})"


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handler para el comando /start"""
    user = message.from_user
    args = message.text.split()[1] if len(message.text.split()) > 1 else None

    user_service = UserService()
    vip_service = VIPService()

    logger.info(
        f"/start recibido - user_id={user.id}, args={_redact_start_log_args(args)}"
    )

    try:
        # Verificar si es deep link "free"
        if args == "free":
            logger.info(f"Detectado args='free' para user_id={user.id}")

            # Verificar si el usuario es miembro del canal VIP
            vip_channel = vip_service.get_vip_channel()
            is_vip_member = False
            if vip_channel:
                try:
                    chat_member = await message.bot.get_chat_member(
                        chat_id=vip_channel.channel_id, user_id=user.id
                    )
                    is_vip_member = chat_member.status in ["member", "administrator", "creator"]
                    logger.info(f"Usuario {user.id} membresía VIP: {chat_member.status}")
                except Exception as e:
                    logger.warning(f"No se pudo verificar membresía VIP para user {user.id}: {e}")

            # Si es miembro VIP, enviar mensaje especial
            if is_vip_member:
                await message.answer(LucienVoice.vip_member_free_link_greeting(), parse_mode="HTML")
                return

            # Si no es VIP, verificar si es usuario existente para flujo de "viejo conocido"
            existing_user = user_service.get_user(user.id)
            logger.info(f"Usuario existente: {existing_user is not None}")
            if not existing_user:
                # Es un "viejo conocido" - ya estaba en el canal antes del bot
                user_service.create_user(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                )
                await message.answer(
                    LucienVoice.returning_user_greeting(),
                    reply_markup=returning_user_keyboard(),
                    parse_mode="HTML",
                )
                return

            # Si ya existe y no es VIP, tratar como /start normal
            logger.info(f"Usuario {user.id} ya existe, ignorando parámetro 'free'")
            args = None

        # Registrar/actualizar usuario (para todos los demás casos)
        db_user = user_service.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        # Best-effort: entregas de misiones pendientes al volver
        try:
            with get_service(MissionService) as mission_service:
                await mission_service.deliver_pending_rewards(user.id, bot=message.bot)
        except Exception as exc:
            logger.warning(
                f"common_handlers | pending_rewards_catchup | user_id={user.id} | error={exc}"
            )

        # Verificar si es token de acceso VIP
        if args:
            subscription = await vip_service.redeem_token_with_missions(
                args, user.id, bot=message.bot
            )

            if subscription:
                invite_link = await vip_service.create_vip_invite_link(
                    message.bot, user.id, allow_fallback=True
                )
                await message.answer(
                    LucienVoice.vip_direct_access(invite_link),
                    reply_markup=vip_access_keyboard(),
                    parse_mode="HTML",
                )
                return
            else:
                # Validar token para mensaje específico
                token, error = vip_service.validate_token(args)
                if error == "used":
                    await message.answer(LucienVoice.token_used(), parse_mode="HTML")
                elif error == "expired":
                    await message.answer(LucienVoice.token_expired(), parse_mode="HTML")
                elif error == "invalid":
                    await message.answer(LucienVoice.token_invalid(), parse_mode="HTML")
                return

        # Verificar si es administrador (ADMIN_IDS + role en BD via utils.admin)
        if is_admin(user.id):
            await message.answer(
                LucienVoice.admin_greeting(), reply_markup=admin_menu_keyboard(), parse_mode="HTML"
            )
        else:
            # Verificar si es VIP
            is_vip = vip_service.is_user_vip(user.id)

            await message.answer(
                LucienVoice.greeting(user.first_name),
                reply_markup=main_menu_keyboard(is_vip),
                parse_mode="HTML",
            )
    finally:
        if user_service:
            user_service.close()
        if vip_service:
            vip_service.close()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handler para el comando /help"""
    help_text = """🎩 <b>Lucien - Guardián de los Secretos de Diana</b>

<i>Permíteme explicarle los misterios a su disposición...</i>

<b>Comandos disponibles:</b>
/start - Iniciar conversación conmigo
/help - Mostrar esta ayuda

<b>Para acceder al vestíbulo (Free):</b>
1. Haga clic en el enlace del canal
2. Pulse "Solicitar acceso"
3. Espere el tiempo indicado
4. ¡Será aceptado automáticamente!

<b>Para acceder a El Diván (VIP):</b>
1. Obtenga un enlace único del custodio
2. Haga clic en el enlace
3. Su membresía se activará automáticamente

<i>Diana observa con interés su participación...</i>"""

    await message.answer(help_text, parse_mode="HTML")


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Volver al menú principal (o admin según rol)"""
    user = callback.from_user

    if is_admin(user.id):
        # Administradores se quedan en su panel
        await callback.message.edit_text(
            LucienVoice.admin_greeting(), reply_markup=admin_menu_keyboard(), parse_mode="HTML"
        )
        await callback.answer()
        return

    # Verificar si es VIP (solo para visitantes)
    vip_service = VIPService()
    try:
        is_vip = vip_service.is_user_vip(user.id)

        await callback.message.edit_text(
            LucienVoice.greeting(user.first_name),
            reply_markup=main_menu_keyboard(is_vip),
            parse_mode="HTML",
        )
    finally:
        vip_service.close()
    try:
        await callback.answer()
    except Exception as e:
        # Callback query expired, ignore
        logger.debug(f"callback.answer() expirada en back_to_main para user {user.id}: {e}")


@router.callback_query(F.data == "back_to_admin", lambda cb: is_admin(cb.from_user.id))
async def back_to_admin(callback: CallbackQuery):
    """Volver al menú de administrador"""
    await callback.message.edit_text(
        LucienVoice.admin_greeting(), reply_markup=admin_menu_keyboard(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery):
    """Cancelar acción actual"""
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n<i>Acción cancelada. Diana aprecia la deliberación...</i>",
        parse_mode="HTML",
    )
    await callback.answer("Acción cancelada")


@router.callback_query(F.data.in_({"profile", "narrative"}))
async def coming_soon_features(callback: CallbackQuery):
    """Features aún no implementadas"""
    user = callback.from_user
    if is_admin(user.id):
        await callback.message.edit_text(
            LucienVoice.admin_greeting(), reply_markup=admin_menu_keyboard(), parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            LucienVoice.coming_soon(), reply_markup=main_menu_keyboard(), parse_mode="HTML"
        )
    await callback.answer()
