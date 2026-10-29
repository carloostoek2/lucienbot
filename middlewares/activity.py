"""Registra actividad del usuario para el recordatorio Free (informe #6).

Inner middleware (``data["handler"]`` ya resuelto): cuenta solo handlers de la lista
blanca y solo en chat privado. Las reacciones del canal (callbacks cuyo mensaje está en
un canal, ``handle_reaction``) quedan EXCLUIDAS de forma explícita. Best-effort: nunca
rompe el update. Registra siempre (aunque el flag esté apagado) para que, al encenderlo,
``bot_started_at`` y ``last_activity_at`` ya estén al día; el flag solo controla el envío.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)

# Módulos cuyos handlers cuentan como actividad: regalo diario, dados, trivia, tienda.
ACTIVITY_MODULES = frozenset(
    {
        "handlers.gamification_user_handlers",
        "handlers.game_user_handlers",
        "handlers.store_user_handlers",
    }
)
# Menú principal y /start.
ACTIVITY_HANDLERS = frozenset(
    {
        ("handlers.common_handlers", "cmd_start"),
        ("handlers.common_handlers", "back_to_main"),
    }
)
EXCLUDED_HANDLERS = frozenset({("handlers.gamification_user_handlers", "handle_reaction")})


def _chat_type(event: TelegramObject) -> str | None:
    if isinstance(event, Message):
        return event.chat.type if event.chat else None
    if isinstance(event, CallbackQuery):
        if event.message is not None and getattr(event.message, "chat", None) is not None:
            return event.message.chat.type
        return None  # inline mode / mensaje inaccesible: no cuenta
    return None


def classify(event: TelegramObject, handler_callback: Any) -> str | None:
    """None si no cuenta; "start" para /start; "activity" para el resto."""
    if handler_callback is None or _chat_type(event) != "private":
        return None
    key = (getattr(handler_callback, "__module__", ""), getattr(handler_callback, "__name__", ""))
    if key in EXCLUDED_HANDLERS:
        return None
    if key == ("handlers.common_handlers", "cmd_start"):
        return "start"
    if key in ACTIVITY_HANDLERS or key[0] in ACTIVITY_MODULES:
        return "activity"
    return None


class ActivityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        result = await handler(event, data)
        try:
            handler_obj = data.get("handler")
            kind = classify(event, getattr(handler_obj, "callback", None))
            user = getattr(event, "from_user", None)
            if kind and user is not None:
                from models.database import SessionLocal
                from services.inactivity_reminder_service import mark_started, touch_activity

                db = SessionLocal()
                try:
                    if kind == "start":
                        mark_started(db, user.id)
                    else:
                        touch_activity(db, user.id)
                finally:
                    db.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"activity_middleware | error={exc}")
        return result
