"""
Handlers Comunes - Lucien Bot

Handlers para comandos básicos y flujos generales.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatType
from config.settings import bot_config
from services.user_service import UserService
from services.vip_service import VIPService
from keyboards.inline_keyboards import main_menu_keyboard, admin_menu_keyboard, vip_entry_continue_keyboard, vip_entry_ready_keyboard, returning_user_keyboard
from utils.lucien_voice import LucienVoice
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handler para el comando /start"""
    user = message.from_user
    args = message.text.split()[1] if len(message.text.split()) > 1 else None

    user_service = UserService()
    vip_service = VIPService()

    logger.info(f"/start recibido - user_id={user.id}, args={args}, full_text='{message.text}'")

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
                        chat_id=vip_channel.channel_id,
                        user_id=user.id
                    )
                    is_vip_member = chat_member.status in ["member", "administrator", "creator"]
                    logger.info(f"Usuario {user.id} membresía VIP: {chat_member.status}")
                except Exception as e:
                    logger.warning(f"No se pudo verificar membresía VIP para user {user.id}: {e}")

            # Si es miembro VIP, enviar mensaje especial
            if is_vip_member:
                await message.answer(
                    LucienVoice.vip_member_free_link_greeting(),
                    parse_mode="HTML"
                )
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
                    last_name=user.last_name
                )
                await message.answer(
                    LucienVoice.returning_user_greeting(),
                    reply_markup=returning_user_keyboard(),
                    parse_mode="HTML"
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
            last_name=user.last_name
        )

        # Check for pending VIP entry ritual BEFORE token processing
        status, stage = vip_service.get_vip_entry_state(user.id)
        if status == "pending_entry":
            subscription = vip_service.get_active_subscription_for_entry(user.id)
            if not subscription:
                vip_service.clear_vip_entry_state(user.id)
                await message.answer(
                    LucienVoice.vip_entry_expired(),
                    parse_mode="HTML"
                )
                return
            if stage == 1:
                await message.answer(
                    LucienVoice.vip_entry_stage_1(),
                    reply_markup=vip_entry_continue_keyboard(),
                    parse_mode="HTML"
                )
            elif stage == 2:
                await message.answer(
                    LucienVoice.vip_entry_stage_2(),
                    reply_markup=vip_entry_ready_keyboard(),
                    parse_mode="HTML"
                )
            elif stage == 3:
                await message.answer(
                    LucienVoice.vip_entry_stage_3(),
                    parse_mode="HTML"
                )
                # Generate invite link for Stage 3
                vip_channel = vip_service.get_vip_channel()
                if vip_channel:
                    try:
                        invite_link = await message.bot.create_chat_invite_link(
                            chat_id=vip_channel.channel_id,
                            name=f"VIP {user.id}",
                            creates_join_request=False,
                            member_limit=1
                        )
                        await message.answer(
                            f"🔗 <b>Su enlace de acceso exclusivo:</b>\n\n"
                            f"{invite_link.invite_link}\n\n"
                            f"<i>Diana le espera en el círculo íntimo...</i>",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        logger.error(f"Error creando invite link para canal {vip_channel.channel_id}: {e}")
                        if vip_channel.invite_link:
                            await message.answer(
                                f"🔗 <b>Su enlace de acceso exclusivo:</b>\n\n"
                                f"{vip_channel.invite_link}\n\n"
                                f"<i>Diana le espera en el círculo íntimo...</i>",
                                parse_mode="HTML"
                            )
                        else:
                            await message.answer(
                                f"🎩 <b>Lucien:</b>\n\n"
                                f"<i>Disculpe, ha ocurrido un inconveniente técnico al generar su acceso...</i>\n\n"
                                f"Por favor, contacte a Diana directamente para que le proporcione acceso al canal.",
                                parse_mode="HTML"
                            )
                vip_service.complete_vip_entry(user.id)
            return

        # Verificar si es token de acceso VIP
        if args:
            subscription = vip_service.redeem_token(args, user.id)

            if subscription:
                # Token válido - start VIP entry ritual (Stage 1)
                await message.answer(
                    LucienVoice.vip_entry_stage_1(),
                    reply_markup=vip_entry_continue_keyboard(),
                    parse_mode="HTML"
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

        # Verificar si es administrador
        is_admin = user.id in bot_config.ADMIN_IDS or db_user.role.value == "admin"

        if is_admin:
            await message.answer(
                LucienVoice.admin_greeting(),
                reply_markup=admin_menu_keyboard(),
                parse_mode="HTML"
            )
        else:
            # Verificar si es VIP
            is_vip = vip_service.is_user_vip(user.id)

            await message.answer(
                LucienVoice.greeting(user.first_name),
                reply_markup=main_menu_keyboard(is_vip),
                parse_mode="HTML"
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
    """Volver al menú principal"""
    user = callback.from_user

    # Verificar si es VIP
    vip_service = VIPService()
    try:
        is_vip = vip_service.is_user_vip(user.id)

        await callback.message.edit_text(
            LucienVoice.greeting(user.first_name),
            reply_markup=main_menu_keyboard(is_vip),
            parse_mode="HTML"
        )
    finally:
        vip_service.close()
    try:
        await callback.answer()
    except Exception:
        # Callback query expired, ignore
        pass


@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    """Volver al menú de administrador"""
    await callback.message.edit_text(
        LucienVoice.admin_greeting(),
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery):
    """Cancelar acción actual"""
    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Acción cancelada. Diana aprecia la deliberación...</i>",
        parse_mode="HTML"
    )
    await callback.answer("Acción cancelada")


@router.callback_query(F.data.in_({"profile", "narrative"}))
async def coming_soon_features(callback: CallbackQuery):
    """Features aún no implementadas"""
    await callback.message.edit_text(
        LucienVoice.coming_soon(),
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
