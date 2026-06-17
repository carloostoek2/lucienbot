"""
Handlers de Administración - Lucien Bot

Handlers para el panel de administración conversacional.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

from config.settings import bot_config
from keyboards.inline_keyboards import (
    back_keyboard,
    channel_management_keyboard,
    vip_management_keyboard,
)
from services.user_service import UserService
from utils.admin import is_admin

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


# ==================== MENÚ PRINCIPAL ADMIN ====================


@router.callback_query(F.data == "admin_channels", lambda cb: is_admin(cb.from_user.id))
async def admin_channels(callback: CallbackQuery):
    """Gestión de canales"""
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Los dominios bajo nuestra gestión...</i>\n\n"
        "¿Qué desea hacer con los vestíbulos y círculos de Diana?",
        reply_markup=channel_management_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_vip", lambda cb: is_admin(cb.from_user.id))
async def admin_vip(callback: CallbackQuery):
    """Gestión VIP"""
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n"
        "<i>El Diván donde Diana comparte sus secretos\n"
        "más íntimos con los selectos...</i>\n\n"
        "¿Cómo desea calibrar los privilegios VIP?",
        reply_markup=vip_management_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users", lambda cb: is_admin(cb.from_user.id))
async def admin_users(callback: CallbackQuery):
    """Gestión de usuarios"""
    user_service = UserService()
    try:
        users = user_service.get_all_users()

        text = f"""🎩 <b>Lucien:</b>

<i>Los visitantes bajo nuestra observación...</i>

📊 <b>Total de almas registradas:</b> {len(users)}

<i>Use el sistema de gestión de canales para ver detalles específicos.</i>"""
    finally:
        user_service.close()

    await callback.message.edit_text(
        text, reply_markup=back_keyboard("back_to_admin"), parse_mode="HTML"
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
        parse_mode="HTML",
    )
    await callback.answer()
