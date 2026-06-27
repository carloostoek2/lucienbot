"""
Cache de Idempotencia para Callbacks de Telegram.

Evita que Telegram reintente el mismo callback dos veces (doble ejecución).
"""
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # For optional redis type only (no top runtime dep); import inside TYPE_CHECKING per pattern
    from redis.asyncio import Redis


class IdempotencyCache:
    """
    Cache en memoria para marcar callbacks como procesados (o Redis SET NX EX cuando se provee).

    TTL de 60 segundos cubre el caso de reintentos de Telegram.
    Para producción con múltiples instancias, usar Redis.
    # Item 1/35 + exact fallback per impact
    """

    def __init__(self, ttl_seconds: int = 60, redis: "Redis | None" = None):
        self._seen: dict[str, float] = {}
        self.ttl = ttl_seconds
        self._redis = redis

    def is_duplicate(self, callback_id: str) -> bool:
        """Retorna True si el callback ya fue procesado. (in-mem path only; used by global for test compat)"""
        now = time.monotonic()
        self._seen = {k: v for k, v in self._seen.items() if now - v < self.ttl}

        if callback_id in self._seen:
            return True

        self._seen[callback_id] = now
        return False

    async def check_and_mark(self, callback_id: str) -> bool:
        """Async: True si dupe (skip). Redis: SET NX EX atomic (guarantees skip before handler/credit).
        Fallback: delegates to sync is_duplicate (exact current in-mem).
        """
        if self._redis:
            key = f"idem:{callback_id}"
            # atomic set-if-not-exist + ttl; result None => existed => dupe
            result = await self._redis.set(key, "1", ex=self.ttl, nx=True)
            return result is None
        else:
            return self.is_duplicate(callback_id)

    def mark_processed(self, callback_id: str) -> None:
        """Marca un callback como procesado (no necesitado si is_duplicate ya lo marca)."""
        self._seen[callback_id] = time.monotonic()


# Instancia global para usar en handlers
idempotency_cache = IdempotencyCache()


# =============================================================================
# IdempotencyMiddleware (gsd-mw-hardening phase 3)
# =============================================================================

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)


class IdempotencyMiddleware(BaseMiddleware):
    """
    Middleware de idempotencia para callbacks de Telegram.

    Previene doble ejecución cuando Telegram reintenta el mismo CallbackQuery
    (común en entornos con latencia o reintentos automáticos del cliente).

    - Solo actúa sobre CallbackQuery (los reintentos de TG afectan principalmente CBs)
    - Usa IdempotencyCache (global for fallback/test patch compat; per-instance with redis)
    - Redis path (when provided): atomic SET NX EX
    - En caso de duplicado: hace answer() (ack al cliente para que no quede "cargando")
      y corta la cadena (NO llama al handler) → evita lógica duplicada / besitos duplicados etc.
      GUARANTEE: skip before any handler/credit path (critical for gamif no-dupe)
    - Pass-through completo para Messages y para el primer (no-dupe) CallbackQuery
    - Robusto ante fallos de answer() (no propaga, solo loguea warning)
    - Loggea toda acción importante siguiendo convención del proyecto:
      módulo, acción, user_id, resultado
    # Item 1/35 + exact fallback per impact
    """

    def __init__(self, redis: "Redis | None" = None):
        self._redis = redis
        if redis is not None:
            # per-instance cache with redis for distributed dedup
            self._cache = IdempotencyCache(ttl_seconds=60, redis=redis)
        else:
            # global for in-mem + tests that patch("...idempotency_cache")
            self._cache = idempotency_cache

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        if isinstance(event, CallbackQuery):
            cb_id = event.id
            if cb_id:
                # redis path uses async check+mark (SET NX EX); fallback/global uses is_duplicate direct for patch compat in tests + exact in-mem
                if self._redis:
                    is_dupe = await self._cache.check_and_mark(cb_id)
                else:
                    is_dupe = self._cache.is_duplicate(cb_id)
                if is_dupe:
                    user_id = event.from_user.id if event.from_user else "?"
                    logger.info(
                        f"idempotency_middleware | skip_duplicate | user_id={user_id} | "
                        f"result=skipped callback_id={cb_id}"
                    )
                    try:
                        await event.answer()
                    except Exception as e:
                        logger.warning(
                            f"idempotency_middleware | answer_failed_on_skip | user_id={user_id} | "
                            f"error={str(e)[:80]} callback_id={cb_id}"
                        )
                    return  # critical: do not invoke handler for duplicate callback (guarantees skip before any credit on dupe CB across instances)

        # Pass-through for everything else (first-seen CBs, all Messages, other events)
        return await handler(event, data)
