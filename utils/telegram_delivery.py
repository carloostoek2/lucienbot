"""
Helpers para entrega DM vía Telegram Bot API.

Centraliza resolución de chat_id (user.id vs user_chat_id de join request)
y clasificación de errores permanentes de Telegram.
"""

from __future__ import annotations

from dataclasses import dataclass

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError


@dataclass(frozen=True)
class DmProbeResult:
    """Resultado de un intento de send_message de diagnóstico."""

    chat_id: int
    success: bool
    permanent_code: str | None
    error_text: str | None


def resolve_private_chat_id(user_id: int, user_chat_id: int | None = None) -> int:
    """Elige el chat privado destino; prioriza user_chat_id de ChatJoinRequest."""
    return int(user_chat_id) if user_chat_id else int(user_id)


def classify_forbidden_error(exc: TelegramForbiddenError) -> tuple[bool, str | None]:
    """Clasifica TelegramForbiddenError en códigos permanent:* conocidos."""
    err_lower = str(exc).lower()
    if "bot was blocked" in err_lower:
        return True, "permanent:bot_blocked"
    if "can't initiate conversation" in err_lower:
        return True, "permanent:no_private_chat"
    if "user is deactivated" in err_lower:
        return True, "permanent:user_deactivated"
    return False, None


def classify_bad_request_error(exc: TelegramBadRequest) -> tuple[bool, str | None]:
    """Clasifica TelegramBadRequest en códigos permanent:* conocidos."""
    if "chat not found" in str(exc).lower():
        return True, "permanent:chat_not_found"
    return False, None


async def probe_send_message(bot, chat_id: int, text: str) -> DmProbeResult:
    """Envía un mensaje de prueba y devuelve resultado estructurado (sin raise)."""
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        return DmProbeResult(chat_id=chat_id, success=True, permanent_code=None, error_text=None)
    except TelegramForbiddenError as exc:
        is_perm, code = classify_forbidden_error(exc)
        return DmProbeResult(
            chat_id=chat_id,
            success=False,
            permanent_code=code if is_perm else None,
            error_text=str(exc),
        )
    except TelegramBadRequest as exc:
        is_perm, code = classify_bad_request_error(exc)
        return DmProbeResult(
            chat_id=chat_id,
            success=False,
            permanent_code=code if is_perm else None,
            error_text=str(exc),
        )
    except Exception as exc:  # pragma: no cover - diagnóstico best-effort
        return DmProbeResult(
            chat_id=chat_id, success=False, permanent_code=None, error_text=str(exc)
        )