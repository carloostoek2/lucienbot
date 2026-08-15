"""Handler de business_connection (Fase 6 link)."""
import logging

from aiogram import Router
from aiogram.types import BusinessConnection

from config.settings import bot_config
from services.link_notifier import LinkNotifier

logger = logging.getLogger(__name__)
router = Router()


@router.business_connection()
async def handle_business_connection(bc: BusinessConnection) -> None:
    """Persist the owner's business connection. Flag OFF = no-op (identical behavior)."""
    if not bot_config.FEATURE_LINK_ENABLED:
        return
    LinkNotifier.upsert_business_connection(bc)
