"""
Analytics Handlers - Lucien Bot

Comandos de estadisticas y exportacion para Custodios.
Solo Custodios (ADMIN_IDS) pueden acceder.
"""
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from config.settings import bot_config
from services.analytics_service import AnalyticsService
from models.database import SessionLocal
from utils.lucien_voice import LucienVoice
import logging

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    """Check if user is a Custodio (admin)."""
    return user_id in bot_config.ADMIN_IDS


@router.message(Command("stats"))
async def show_stats(message: Message):
    """Muestra dashboard de metricas del bot."""
    if not is_admin(message.from_user.id):
        await message.answer(
            LucienVoice.analytics_access_denied(),
            parse_mode=ParseMode.HTML
        )
        return

    db = SessionLocal()
    try:
        svc = AnalyticsService(db)
        stats = svc.get_dashboard_stats()
        await message.answer(
            LucienVoice.analytics_dashboard(stats),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error showing stats: {e}")
        await message.answer(LucienVoice.error_message())
    finally:
        svc.close()


@router.message(Command("export"))
async def export_data(message: Message):
    """Exporta datos de visitantes como CSV."""
    if not is_admin(message.from_user.id):
        await message.answer(
            LucienVoice.analytics_access_denied(),
            parse_mode=ParseMode.HTML
        )
        return

    # Default to users export
    export_type = "users"
    args = message.text.split()
    if len(args) > 1 and args[1].lower() in ("users", "activity"):
        export_type = args[1].lower()

    db = SessionLocal()
    try:
        svc = AnalyticsService(db)

        if export_type == "users":
            csv_path = svc.export_users_csv()
            filename = "visitantes_export.csv"
        else:
            csv_path = svc.export_activity_csv()
            filename = "actividad_export.csv"

        if csv_path is None:
            await message.answer(
                LucienVoice.export_no_data(),
                parse_mode=ParseMode.HTML
            )
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
    finally:
        svc.close()
