"""
Middleware de Rate Limiting para Lucien Bot.

Protege contra spam de comandos, especialmente en minijuegos y besitos.
"""
import time
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class RateLimiterMiddleware(BaseMiddleware):
    """
    Middleware de rate limiting por usuario.

    Bloquea requests repetidos dentro de una ventana de tiempo.
    """

    def __init__(self, limit_seconds: float = 1.0):
        self.limit = limit_seconds
        self._last_call: dict[int, float] = {}

    async def __call__(self, handler, event: TelegramObject, data: dict):
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id

            if self._is_rate_limited(user_id):
                await event.answer(
                    "⏳ Espera un momento antes de volver a usar este comando."
                )
                return

        return await handler(event, data)

    def _is_rate_limited(self, user_id: int) -> bool:
        now = time.monotonic()
        last = self._last_call.get(user_id, 0)

        if now - last < self.limit:
            return True

        self._last_call[user_id] = now
        return False
