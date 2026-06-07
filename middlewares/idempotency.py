"""
Cache de Idempotencia para Callbacks de Telegram.

Evita que Telegram reintente el mismo callback dos veces (doble ejecución).
"""
import time
from typing import Optional


class IdempotencyCache:
    """
    Cache en memoria para marcar callbacks como procesados.

    TTL de 60 segundos cubre el caso de reintentos de Telegram.
    Para producción con múltiples instancias, usar Redis.
    """

    def __init__(self, ttl_seconds: int = 60):
        self._seen: dict[str, float] = {}
        self.ttl = ttl_seconds

    def is_duplicate(self, callback_id: str) -> bool:
        """Retorna True si el callback ya fue procesado."""
        now = time.monotonic()
        self._seen = {k: v for k, v in self._seen.items() if now - v < self.ttl}

        if callback_id in self._seen:
            return True

        self._seen[callback_id] = now
        return False

    def mark_processed(self, callback_id: str) -> None:
        """Marca un callback como procesado (no necesitado si is_duplicate ya lo marca)."""
        self._seen[callback_id] = time.monotonic()


# Instancia global para usar en handlers
idempotency_cache = IdempotencyCache()


# =============================================================================
# IdempotencyMiddleware (gsd-mw-hardening phase 3)
# =============================================================================

import logging
from typing import Any, Callable, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)


class IdempotencyMiddleware(BaseMiddleware):
    """
    Middleware de idempotencia para callbacks de Telegram.

    Previene doble ejecución cuando Telegram reintenta el mismo CallbackQuery
    (común en entornos con latencia o reintentos automáticos del cliente).

    - Solo actúa sobre CallbackQuery (los reintentos de TG afectan principalmente CBs)
    - Usa el IdempotencyCache global (TTL ~60s cubre reintentos)
    - En caso de duplicado: hace answer() (ack al cliente para que no quede "cargando")
      y corta la cadena (NO llama al handler) → evita lógica duplicada / besitos duplicados etc.
    - Pass-through completo para Messages y para el primer (no-dupe) CallbackQuery
    - Robusto ante fallos de answer() (no propaga, solo loguea warning)
    - Loggea toda acción importante siguiendo convención del proyecto:
      módulo, acción, user_id, resultado
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        if isinstance(event, CallbackQuery):
            cb_id = event.id
            if cb_id and idempotency_cache.is_duplicate(cb_id):
                user_id = event.from_user.id if event.from_user else "?"
                logger.info(
                    f"idempotency_middleware - skip_duplicate - {user_id} - "
                    f"callback_id={cb_id} - result: skipped (dupe cb)"
                )
                try:
                    await event.answer()
                except Exception as e:
                    logger.warning(
                        f"idempotency_middleware - answer_failed_on_skip - {user_id} - "
                        f"callback_id={cb_id} - error: {e}"
                    )
                return  # critical: do not invoke handler for duplicate callback

        # Pass-through for everything else (first-seen CBs, all Messages, other events)
        return await handler(event, data)
