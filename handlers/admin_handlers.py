"""
Handlers de Administración - Lucien Bot

Handlers para el panel de administración conversacional.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config.settings import bot_config
from services.user_service import UserService
from services.channel_service import ChannelService
from services.vip_service import VIPService
from keyboards.inline_keyboards import (
    admin_menu_keyboard, channel_management_keyboard, 
    vip_management_keyboard, back_keyboard
)
from utils.lucien_voice import LucienVoice
import logging

logger = logging.getLogger(__name__)
router = Router()


# Estados para FSM
class AdminStates(StatesGroup):
    waiting_channel_message = State()
    waiting_tariff_name = State()
    waiting_tariff_days = State()
    waiting_tariff_price = State()
    waiting_custom_wait_time = State()


# Nota: Los filtros de admin se aplican en cada handler específico
# para no bloquear otros routers como el de gamificación de usuarios

# Función helper para verificar admin
def is_admin(user_id: int) -> bool:
    return user_id in bot_config.ADMIN_IDS


# ==================== MENÚ PRINCIPAL ADMIN ====================

@router.callback_query(F.data == "admin_channels", lambda cb: is_admin(cb.from_user.id))
async def admin_channels(callback: CallbackQuery):
    """Gestión de canales"""
    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>Los dominios bajo nuestra gestión...</i>\n\n"
        f"¿Qué desea hacer con los vestíbulos y círculos de Diana?",
        reply_markup=channel_management_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_vip", lambda cb: is_admin(cb.from_user.id))
async def admin_vip(callback: CallbackQuery):
    """Gestión VIP"""
    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>El Diván donde Diana comparte sus secretos\n"
        f"más íntimos con los selectos...</i>\n\n"
        f"¿Cómo desea calibrar los privilegios VIP?",
        reply_markup=vip_management_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users", lambda cb: is_admin(cb.from_user.id))
async def admin_users(callback: CallbackQuery):
    """Gestión de usuarios"""
    user_service = UserService()
    users = user_service.get_all_users()
    
    text = f"""🎩 <b>Lucien:</b>

<i>Los visitantes bajo nuestra observación...</i>

📊 <b>Total de almas registradas:</b> {len(users)}

<i>Use el sistema de gestión de canales para ver detalles específicos.</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("back_to_admin"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_analytics", lambda cb: is_admin(cb.from_user.id))
async def admin_analytics(callback: CallbackQuery):
    """Analytics"""
    channel_service = ChannelService()
    vip_service = VIPService()
    
    free_channels = len(channel_service.get_free_channels())
    vip_channels = len(channel_service.get_vip_channels())
    active_subs = len(vip_service.get_active_subscriptions())
    pending = channel_service.count_pending_requests()
    
    text = f"""🎩 <b>Lucien:</b>

<i>Los patrones que revelan los deseos ocultos...</i>

📊 <b>Métricas del Reino:</b>

🏛️ <b>Dominios:</b>
   • Vestíbulos (Free): {free_channels}
   • Círculos VIP: {vip_channels}

👥 <b>Visitantes:</b>
   • Suscriptores VIP activos: {active_subs}
   • En espera (Free): {pending}

<i>Diana observa estos números con... interés.</i>"""
    
    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("back_to_admin"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_settings", lambda cb: is_admin(cb.from_user.id))
async def admin_settings(callback: CallbackQuery):
    """Configuración del reino"""
    await callback.message.edit_text(
        f"🎩 <b>Lucien:</b>\n\n"
        f"<i>La calibración del reino...</i>\n\n"
        f"⚙️ <b>Configuración actual:</b>\n"
        f"   • Zona horaria: {bot_config.TIMEZONE}\n"
        f"   • Administradores: {len(bot_config.ADMIN_IDS)}\n\n"
        f"<i>Estas configuraciones se ajustan en las variables de entorno.</i>",
        reply_markup=back_keyboard("back_to_admin"),
        parse_mode="HTML"
    )
    await callback.answer()
