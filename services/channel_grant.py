"""
Orquestación compartida de grant/reject para scheduler y admin.

ID duality:
- PendingRequest.channel_id / callbacks admin → DB PK (Channel.id)
- approve_chat_join_request / decline_chat_join_request → Telegram chat ID (Channel.channel_id)
"""

import html
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.orm import Session

from keyboards.inline_keyboards import social_links_keyboard
from models.models import Channel, PendingRequest
from utils.lucien_voice import LucienVoice

logger = logging.getLogger(__name__)

TELEGRAM_INVITE_RE = re.compile(r"^https://t\.me/[\w/+.-]+$")


def is_valid_telegram_invite_link(link: str) -> bool:
    """Valida formato de enlace de invitación Telegram."""
    return bool(TELEGRAM_INVITE_RE.match(link))


@dataclass
class GrantResult:
    success: bool
    request_id: int
    error: str | None = None


@dataclass
class ApproveAllResult:
    approved: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def resolve_channel_message(
    channel: Channel,
    field_name: str,
    default_fn: Callable[[str], str],
    channel_name: str,
) -> str:
    """Usa mensaje custom del canal si no vacío; si no, default_fn(channel_name)."""
    custom = getattr(channel, field_name, None)
    if custom and str(custom).strip():
        return custom
    return default_fn(channel_name)


def append_invite_link(message: str, invite_link: str | None) -> str:
    """Append invite link if valid https://t.me/ URL; escape for HTML payloads."""
    if not invite_link:
        return message
    if not TELEGRAM_INVITE_RE.match(invite_link):
        logger.warning(f"Invalid invite_link format, skipping append: {invite_link!r}")
        return message
    return f"{message}\n{html.escape(invite_link)}"


def build_welcome_payload(channel: Channel) -> str:
    """Welcome resuelto + append invite_link si existe y es válido."""
    channel_name = channel.channel_name or "Los Kinkys"
    message = resolve_channel_message(
        channel, "welcome_message", LucienVoice.free_entry_welcome, channel_name
    )
    return append_invite_link(message, channel.invite_link)


def build_approval_payload(channel: Channel) -> str:
    """Mensaje ritual (approval_message) resuelto para job de 30s."""
    channel_name = channel.channel_name or "Los Kinkys"
    return resolve_channel_message(
        channel, "approval_message", LucienVoice.free_entry_ritual, channel_name
    )


def _commit_request_approved(db: Session, request: PendingRequest) -> None:
    request.status = "approved"
    request.approved_at = datetime.now(UTC)
    db.commit()


def _commit_request_rejected(db: Session, request: PendingRequest) -> None:
    request.status = "rejected"
    db.commit()


async def _send_welcome_after_grant(bot, request: PendingRequest, channel: Channel) -> None:
    from utils.telegram_delivery import resolve_private_chat_id

    try:
        message = build_welcome_payload(channel)
        dm_chat_id = resolve_private_chat_id(request.user_id, request.user_chat_id)
        await bot.send_message(
            chat_id=dm_chat_id,
            text=message,
            parse_mode="HTML",
            reply_markup=social_links_keyboard(),
        )
        logger.info(
            f"channel_grant | welcome_sent | user_id={request.user_id} | "
            f"channel_tg={channel.channel_id}"
        )
    except TelegramForbiddenError:
        logger.warning(
            f"channel_grant | welcome_forbidden | user_id={request.user_id} | "
            f"channel_tg={channel.channel_id}"
        )
        return
    except Exception as e:
        logger.error(f"Error enviando bienvenida a user={request.user_id}: {e}")


async def grant_pending_request(db: Session, request: PendingRequest, bot) -> GrantResult:
    """Aprueba en Telegram, commit BD y envía welcome. Misma semántica que scheduler."""
    request_id = request.id
    user_id = request.user_id
    try:
        channel = request.channel
        if not channel or not channel.is_active:
            return GrantResult(
                success=False,
                request_id=request_id,
                error="channel inactive or missing",
            )

        await bot.approve_chat_join_request(chat_id=channel.channel_id, user_id=user_id)
        _commit_request_approved(db, request)
        await _send_welcome_after_grant(bot, request, channel)

        logger.info(
            f"channel_grant | approved | request_id={request_id} | "
            f"user_id={user_id} | channel_tg={channel.channel_id}"
        )
        return GrantResult(success=True, request_id=request_id)

    except TelegramForbiddenError as e:
        err = str(e)
        _commit_request_rejected(db, request)
        logger.warning(
            f"channel_grant | forbidden_terminal | request_id={request_id} | "
            f"user_id={user_id} | error={err[:120]} | result=rejected_terminal"
        )
        return GrantResult(success=False, request_id=request_id, error=err)
    except TelegramBadRequest as e:
        err = str(e)
        if "USER_ALREADY_PARTICIPANT" in err:
            _commit_request_approved(db, request)
            logger.info(
                f"channel_grant | already_participant | request_id={request_id} | "
                f"user_id={user_id}"
            )
            return GrantResult(success=True, request_id=request_id)
        if "USER_CHANNELS_TOO_MUCH" in err:
            try:
                await bot.decline_chat_join_request(
                    chat_id=channel.channel_id, user_id=user_id
                )
            except Exception as decl_err:
                logger.warning(
                    f"channel_grant | channels_limit_decline_failed | request_id={request_id} | "
                    f"user_id={user_id} | error={decl_err}"
                )
            _commit_request_rejected(db, request)
            logger.warning(
                f"channel_grant | channels_limit | request_id={request_id} | "
                f"user_id={user_id} | result=rejected_terminal"
            )
            return GrantResult(success=False, request_id=request_id, error=err)
        logger.error(f"Error aprobando solicitud {request_id}: {e}")
        db.rollback()
        return GrantResult(success=False, request_id=request_id, error=str(e))
    except Exception as e:
        logger.error(f"Error aprobando solicitud {request_id}: {e}")
        db.rollback()
        return GrantResult(success=False, request_id=request_id, error=str(e))


async def reject_pending_request(db: Session, request: PendingRequest, bot) -> bool:
    """Declina en Telegram y marca status rejected en BD."""
    request_id = request.id
    user_id = request.user_id
    try:
        channel = request.channel
        if not channel:
            return False

        await bot.decline_chat_join_request(chat_id=channel.channel_id, user_id=user_id)
        request.status = "rejected"
        db.commit()
        logger.info(
            f"channel_grant | rejected | request_id={request_id} | "
            f"user_id={user_id} | channel_tg={channel.channel_id}"
        )
        return True
    except Exception as e:
        logger.error(f"Error rechazando solicitud {request_id}: {e}")
        db.rollback()
        return False
