"""
Rate Limiting Middleware - Lucien Bot

Throttles per-user requests using aiolimiter sliding window.
Custodios (admins) bypass rate limiting entirely.
"""
from aiolimiter import AsyncLimiter
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Any
from config.settings import rate_limit_config, bot_config
import logging

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Per-user rate limiting middleware using aiolimiter.

    Admins (Custodios) bypass entirely.
    Non-admin users are limited to RATE_LIMIT_RATE requests per RATE_LIMIT_PERIOD seconds.
    """

    def __init__(self):
        self.limiter = AsyncLimiter(
            max_rate=rate_limit_config.RATE_LIMIT_RATE,
            time_period=rate_limit_config.RATE_LIMIT_PERIOD,
        )

    async def __call__(self, handler, event: TelegramObject, data: dict) -> Any:
        # Extract user from event data
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        user_id = user.id

        # Bypass for Custodios
        if rate_limit_config.ADMIN_BYPASS and user_id in bot_config.ADMIN_IDS:
            return await handler(event, data)

        # Check rate limit
        try:
            async with self.limiter:
                return await handler(event, data)
        except Exception:
            # Rate limit exceeded
            await self._on_limit_exceeded(event, user_id)
            return  # Do not call handler

    async def _on_limit_exceeded(self, event: TelegramObject, user_id: int):
        """Send throttling response to user."""
        try:
            # Works for both Message and CallbackQuery (both have answer method)
            await event.answer(
                text="🎩 <i>Lucien:</i>\n\n"
                     "<i>Espera un momento... no tan rapido.</i>\n\n"
                     "<i>Los secretos de Diana requieren calma.</i>",
                show_alert=True
            )
        except Exception as e:
            logger.warning(f"Could not send throttling reply to {user_id}: {e}")
