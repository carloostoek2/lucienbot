"""
Analytics Handlers - Lucien Bot

Comandos de estadisticas y exportacion para Custodios.
Solo Custodios (ADMIN_IDS) pueden acceder.
"""

import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from keyboards.inline_keyboards import back_keyboard
from services import HealthService, get_service
from services.analytics_service import AnalyticsService
from utils.admin import is_admin
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("stats"))
async def show_stats(message: Message):
    """Muestra dashboard completo de métricas y economía para Custodios."""
    if not is_admin(message.from_user.id):
        await message.answer(LucienVoice.analytics_access_denied(), parse_mode=ParseMode.HTML)
        return

    try:
        with get_service(AnalyticsService) as svc:
            dashboard = svc.get_dashboard_stats()
            economy = svc.get_economy_overview()
            attribution = svc.get_source_attribution()
            top = svc.get_top_earners(limit=8)
        await message.answer(
            LucienVoice.analytics_patterns_dashboard(dashboard, economy, attribution, top),
            parse_mode=ParseMode.HTML,
        )
        logger.info(f"analytics | stats_cmd | user_id={message.from_user.id} | result=shown")
    except Exception as e:
        logger.error(f"analytics | stats_cmd | user_id={message.from_user.id} | error={e}")
        await message.answer(LucienVoice.error_message())


@router.message(Command("economy"))
async def show_economy(message: Message):
    """Muestra reporte enfocado de economía de besitos (fuentes, flujo, top extractores)."""
    if not is_admin(message.from_user.id):
        await message.answer(LucienVoice.analytics_access_denied(), parse_mode=ParseMode.HTML)
        return

    try:
        with get_service(AnalyticsService) as svc:  # exactly 1 service
            economy = svc.get_economy_overview()
            attribution = svc.get_source_attribution()
            top = svc.get_top_earners(limit=10)
        await message.answer(
            LucienVoice.economy_report(economy, attribution, top),
            parse_mode=ParseMode.HTML,
        )
        logger.info(f"analytics | economy_cmd | user_id={message.from_user.id} | result=shown")
    except Exception as e:
        logger.error(f"analytics | economy_cmd | user_id={message.from_user.id} | error={e}")
        await message.answer(LucienVoice.error_message())


@router.message(Command("export"))
async def export_data(message: Message):
    """Exporta datos de visitantes como CSV."""
    if not is_admin(message.from_user.id):
        await message.answer(LucienVoice.analytics_access_denied(), parse_mode=ParseMode.HTML)
        return

    # Default to users export. "economy" reuses activity (sources included) for now; dedicated economy CSV in later slice.
    export_type = "users"
    args = message.text.split()
    if len(args) > 1 and args[1].lower() in ("users", "activity", "economy"):
        export_type = args[1].lower()
        if export_type == "economy":
            export_type = "activity"  # sources present in activity export

    try:
        with get_service(AnalyticsService) as svc:
            if export_type == "users":
                csv_path = svc.export_users_csv()
                filename = "visitantes_export.csv"
            else:
                csv_path = svc.export_activity_csv()
                filename = "actividad_export.csv"

        if csv_path is None:
            await message.answer(LucienVoice.export_no_data(), parse_mode=ParseMode.HTML)
            return

        # Send CSV via bot
        with open(csv_path, "rb") as f:
            await message.bot.send_document(
                chat_id=message.chat.id,
                document=f,
                caption=LucienVoice.export_ready(filename),
                parse_mode=ParseMode.HTML,
            )

        logger.info(f"Export sent to admin {message.from_user.id}: {filename}")

    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        await message.answer(LucienVoice.error_message())


@router.message(Command("health"))
async def health_cmd(message: Message):
    """Muestra el pulso del reino (salud/observabilidad) para Custodios. Item 11."""
    if not is_admin(message.from_user.id):
        await message.answer(LucienVoice.health_access_denied(), parse_mode=ParseMode.HTML)
        return

    try:
        with get_service(HealthService) as svc:  # exactly 1 service
            health = svc.get_overall_status()
        await message.answer(LucienVoice.system_health(health), parse_mode=ParseMode.HTML)
        logger.info(
            f"health | cmd | user_id={message.from_user.id} | overall={health.get('status')}"
        )
    except Exception as e:
        logger.error(f"health | cmd | user_id={message.from_user.id} | error={e}")
        await message.answer(LucienVoice.error_message())


@router.callback_query(F.data == "admin_health", lambda cb: is_admin(cb.from_user.id))
async def health_cb(callback: CallbackQuery):
    """Callback desde menú admin '🛡️ Pulso del reino'."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Acceso denegado", show_alert=True)
        return

    try:
        with get_service(HealthService) as svc:  # exactly 1 service
            health = svc.get_overall_status()
        await callback.message.answer(LucienVoice.system_health(health), parse_mode=ParseMode.HTML)
        await callback.answer()
        logger.info(
            f"health | cb | user_id={callback.from_user.id} | overall={health.get('status')}"
        )
    except Exception as e:
        logger.error(f"health | cb | user_id={callback.from_user.id} | error={e}")
        await callback.message.answer(LucienVoice.error_message())
        await callback.answer()


@router.callback_query(F.data == "admin_analytics", lambda cb: is_admin(cb.from_user.id))
async def admin_analytics(callback: CallbackQuery):
    """Callback desde menú admin '📊 Los patrones que revelan deseos'. Muestra el detalle completo (dashboard + economía desarrollada)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Acceso denegado", show_alert=True)
        return

    try:
        with get_service(AnalyticsService) as svc:  # exactly 1 service
            dashboard = svc.get_dashboard_stats()
            economy = svc.get_economy_overview()
            attribution = svc.get_source_attribution()
            top = svc.get_top_earners(limit=8)
        await callback.message.edit_text(
            LucienVoice.analytics_patterns_dashboard(dashboard, economy, attribution, top),
            reply_markup=back_keyboard("back_to_admin"),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer()
        logger.info(f"analytics | admin_analytics | user_id={callback.from_user.id} | result=shown")
    except Exception as e:
        logger.error(f"analytics | admin_analytics | user_id={callback.from_user.id} | error={e}")
        await callback.message.answer(LucienVoice.error_message())
        await callback.answer()
