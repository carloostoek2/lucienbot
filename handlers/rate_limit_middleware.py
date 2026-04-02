"""
Rate Limiting Middleware - Lucien Bot

Throttles per-user requests using aiolimiter sliding window.
Custodios (admins) bypass rate limiting entirely.
"""
import asyncio
import time
from aiolimiter import AsyncLimiter
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Any
from config.settings import rate_limit_config, bot_config
import logging

logger = logging.getLogger(__name__)

# Seconds after which an idle per-user limiter entry is cleaned up
_LIMITER_TTL = 300  # 5 minutes


class ThrottlingMiddleware(BaseMiddleware):
    """
    Per-user rate limiting middleware using aiolimiter.

    Each user gets their own AsyncLimiter instance. Admins (Custodios) bypass entirely.
    Idle per-user limiter entries are cleaned up after _LIMITER_TTL seconds.
    """

    def __init__(self):
        self._limiters: dict[int, tuple[AsyncLimiter, float]] = {}
        self._lock = asyncio.Lock()

    def _get_limiter(self, user_id: int) -> AsyncLimiter:
        """Get or create a per-user AsyncLimiter. Returns (limiter, is_new)."""
        now = time.monotonic()
        if user_id in self._limiters:
            limiter, _ = self._limiters[user_id]
            self._limiters[user_id] = (limiter, now)
            return limiter
        limiter = AsyncLimiter(
            max_rate=rate_limit_config.RATE_LIMIT_RATE,
            time_period=rate_limit_config.RATE_LIMIT_PERIOD,
        )
        self._limiters[user_id] = (limiter, now)
        logger.debug(f"[rate_limit] Created per-user limiter for user {user_id}")
        return limiter

    async def _cleanup_idle(self):
        """Remove limiter entries that have been idle for more than _LIMITER_TTL seconds."""
        now = time.monotonic()
        expired = [
            uid for uid, (_, last_seen) in self._limiters.items()
            if now - last_seen > _LIMITER_TTL
        ]
        for uid in expired:
            del self._limiters[uid]
            logger.debug(f"[rate_limit] Cleaned up idle limiter for user {uid}")

    async def __call__(self, handler, event: TelegramObject, data: dict) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        user_id = user.id

        # Bypass for Custodios
        if rate_limit_config.ADMIN_BYPASS and user_id in bot_config.ADMIN_IDS:
            return await handler(event, data)

        async with self._lock:
            await self._cleanup_idle()
            limiter = self._get_limiter(user_id)

        try:
            async with limiter:
                return await handler(event, data)
        except Exception:
            await self._on_limit_exceeded(event, user_id)
            return  # Do not call handler

    async def _on_limit_exceeded(self, event: TelegramObject, user_id: int):
        """Send throttling response to user."""
        try:
            await event.answer(
                text="🎩 <i>Lucien:</i>\n\n"
                     "<i>Espera un momento... no tan rapido.</i>\n\n"
                     "<i>Los secretos de Diana requieren calma.</i>",
                show_alert=True
            )
        except Exception as e:
            logger.warning(f"Could not send throttling reply to {user_id}: {e}")
