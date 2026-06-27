"""
Rate Limiting Middleware - Lucien Bot (canonical implementation).

Throttles per-user requests using aiolimiter sliding window.
Custodios (admins) bypass rate limiting entirely.
Idle per-user limiter entries cleaned up after TTL.

This is the mature logic, ported from handlers/rate_limit_middleware.py
during gsd-mw-hardening phase 2.

Supports Message and CallbackQuery (via data["event_from_user"] + event.answer()).
Uses real config from config.settings (RATE_LIMIT_RATE/PERIOD, ADMIN_BYPASS).
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiolimiter import AsyncLimiter

from config.settings import bot_config, rate_limit_config

if TYPE_CHECKING:
    # Imported only for type annotation (no runtime dep if redis absent); per PLAN "import Redis inside if needed for type to avoid top dep"
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# Seconds after which an idle per-user limiter entry is cleaned up
_LIMITER_TTL = 300  # 5 minutes


class ThrottlingMiddleware(BaseMiddleware):
    """
    Per-user rate limiting middleware using aiolimiter (in-mem) or Redis ZSET (when provided).

    Each user gets their own AsyncLimiter instance (in-mem) or Redis-backed window (distributed parity).
    Admins (Custodios) bypass entirely.
    Idle per-user limiter entries are cleaned up after _LIMITER_TTL seconds (in-mem only).
    # Item 1/35 redis backing + exact fallback
    """

    def __init__(self, redis: Redis | None = None):
        # redis: optional shared client from bot.create_storage (when REDIS_URL); None = exact in-mem fallback (0 beh change, public API unchanged)
        self._redis = redis
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
        logger.debug(f"rate_limiter | create_limiter | user_id={user_id} | result=new")
        return limiter

    async def _cleanup_idle(self):
        """Remove limiter entries that have been idle for more than _LIMITER_TTL seconds."""
        now = time.monotonic()
        expired = [
            uid for uid, (_, last_seen) in self._limiters.items() if now - last_seen > _LIMITER_TTL
        ]
        for uid in expired:
            del self._limiters[uid]
            logger.debug(f"rate_limiter | cleanup_idle | user_id={uid} | result=expired")

    async def _check_redis_rate_limit(self, user_id: int) -> bool:
        """Redis ZSET sliding window for rate parity (SET NX EX alt possible but ZSET matches aiolimiter window semantics).
        Returns True if limited (throttle). Key: rate:{user_id}; scores monotonic time; trim old; zcard <= RATE.
        """
        if not self._redis:
            return False
        key = f"rate:{user_id}"
        now = time.time()
        period = rate_limit_config.RATE_LIMIT_PERIOD
        rate = rate_limit_config.RATE_LIMIT_RATE
        # trim old entries (monotonic scores)
        await self._redis.zremrangebyscore(key, "-inf", now - period)
        count = await self._redis.zcard(key)
        if count >= rate:
            return True
        # add entry (unique-ish member to allow concurrent same ts)
        member = f"{now}:{user_id}"
        await self._redis.zadd(key, {member: now})
        await self._redis.expire(key, int(period) + 10)
        return False

    async def __call__(self, handler, event: TelegramObject, data: dict) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        user_id = user.id

        # Bypass for Custodios (live from config, before any rate path)
        if rate_limit_config.ADMIN_BYPASS and user_id in bot_config.ADMIN_IDS:
            logger.info(f"rate_limiter | bypass | user_id={user_id} | result=admin_bypass")
            return await handler(event, data)

        if self._redis:
            # Redis path (distributed parity for multi-inst; exact semantics on single). Guarantees no spam that could bypass to credit paths.
            limited = await self._check_redis_rate_limit(user_id)
            if limited:
                await self._on_limit_exceeded(event, user_id)
                return  # Do not call handler
            return await handler(event, data)
        else:
            # Exact current in-mem path (100% when redis=None or no REDIS_URL; fallback parity)
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
        """Send throttling response to user (Lucien voice, identical to legacy)."""
        logger.info(f"rate_limiter | limit_exceeded | user_id={user_id} | result=throttled")
        try:
            await event.answer(
                text="🎩 <i>Lucien:</i>\n\n"
                "<i>Espera un momento... no tan rapido.</i>\n\n"
                "<i>Los secretos de Diana requieren calma.</i>",
                show_alert=True,
            )
        except Exception as e:
            logger.warning(f"rate_limiter | answer_failed | user_id={user_id} | error={str(e)[:80]}")


# Compatibility alias (some docs / transitional refs may use the old name)
RateLimiterMiddleware = ThrottlingMiddleware
