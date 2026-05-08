"""
Middleware de Error Handler Global para Lucien Bot.

Captura toda excepción no manejada, responde al usuario con mensaje genérico,
y loggea con contexto completo para debug.
"""
import logging
import traceback
from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseMiddleware):
    """
    Middleware global que captura excepciones no manejadas en cualquier handler.

    - Loggea con contexto completo (user_id, event_type, error, traceback)
    - Responde al usuario con mensaje genérico (no revela detalles técnicos)
    - Nopropaga la excepción (previene cuelgues del dispatcher)
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            user_id = self._extract_user_id(event)
            event_type = type(event).__name__

            logger.error(
                f"Unhandled exception | user_id={user_id} | "
                f"event_type={event_type} | error={e}\n"
                f"{traceback.format_exc()}"
            )

            try:
                await self._respond_error(event)
            except Exception as respond_error:
                logger.warning(
                    f"ErrorHandler: también falló al responder: {respond_error}"
                )

    def _extract_user_id(self, event: TelegramObject) -> int | None:
        if isinstance(event, (Message, CallbackQuery)):
            return event.from_user.id if event.from_user else None
        return None

    async def _respond_error(self, event: TelegramObject) -> None:
        if isinstance(event, Message):
            await event.answer(
                "⚠️ Ocurrió un error inesperado. Por favor intenta de nuevo."
            )
        elif isinstance(event, CallbackQuery):
            await event.answer(
                "⚠️ Error al procesar. Intenta de nuevo.",
                show_alert=True
            )
