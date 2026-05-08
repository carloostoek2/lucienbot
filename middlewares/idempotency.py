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
