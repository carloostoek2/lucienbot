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
from keyboards.inline_keyboards import main_menu_keyboard, admin_menu_keyboard
from utils.lucien_voice import LucienVoice
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handler para el comando /start"""
    user = message.from_user
    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    
    # Registrar/actualizar usuario
    user_service = UserService()
    db_user = user_service.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Verificar si es token de acceso VIP
    if args:
        vip_service = VIPService()
        subscription = vip_service.redeem_token(args, user.id)

        if subscription:
            # Token válido - activar VIP
            await message.answer(
                LucienVoice.vip_activated(
                    subscription.token.tariff.name,
                    subscription.end_date
                ),
                parse_mode="HTML"
            )

            # Generar enlace de un solo uso para el canal VIP
            vip_channel = vip_service.get_vip_channel()
            if vip_channel:
                try:
                    # Crear link de invitación de un solo uso
                    invite_link = await message.bot.create_chat_invite_link(
                        chat_id=vip_channel.channel_id,
                        name=f"VIP {user.id}",
                        creates_join_request=False,
                        member_limit=1  # Link de un solo uso
                    )
                    await message.answer(
                        f"🔗 <b>Su enlace de acceso exclusivo:</b>\n\n"
                        f"{invite_link.invite_link}\n\n"
                        f"<i>Diana le espera en el círculo íntimo...</i>",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Error creando invite link: {e}")
                    # Si falla, usar el link guardado del canal
                    if vip_channel.invite_link:
                        await message.answer(
                            f"🔗 <b>Su enlace de acceso exclusivo:</b>\n\n"
                            f"{vip_channel.invite_link}\n\n"
                            f"<i>Diana le espera en el círculo íntimo...</i>",
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
        vip_service = VIPService()
        is_vip = vip_service.is_user_vip(user.id)
        
        await message.answer(
            LucienVoice.greeting(user.first_name),
            reply_markup=main_menu_keyboard(is_vip),
            parse_mode="HTML"
        )


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

<b>Para acceder al círculo exclusivo (VIP):</b>
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
    is_vip = vip_service.is_user_vip(user.id)
    
    await callback.message.edit_text(
        LucienVoice.greeting(user.first_name),
        reply_markup=main_menu_keyboard(is_vip),
        parse_mode="HTML"
    )
    await callback.answer()


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


@router.callback_query(F.data.in_({"profile", "narrative", "vip_area"}))
async def coming_soon_features(callback: CallbackQuery):
    """Features aún no implementadas"""
    await callback.message.edit_text(
        LucienVoice.coming_soon(),
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
