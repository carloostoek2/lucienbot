"""Safe message edit helpers for Telegram/aiogram.

edit_text fails on photo/video/document messages (even with caption).
Admin flows often attach inline keyboards to media previews; navigating
back must not crash with "there is no text in the message to edit".
"""

from __future__ import annotations

import logging
from typing import Any

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

logger = logging.getLogger(__name__)


def _is_media_message(message: Message) -> bool:
    return bool(
        message.photo
        or message.video
        or message.document
        or message.animation
        or message.audio
        or message.voice
        or message.video_note
        or message.sticker
    )


async def edit_or_send_text(message: Message, text: str, **kwargs: Any) -> Message:
    """Edit message text when possible; otherwise send a new text message.

    If the current message is media (or edit_text is rejected), deletes the
    old message when possible and answers with a fresh text message so menus
    stay on editable text messages.
    """
    can_try_edit = message.text is not None and not _is_media_message(message)

    if can_try_edit:
        try:
            return await message.edit_text(text, **kwargs)
        except TelegramBadRequest as exc:
            err = str(exc).lower()
            if not (
                "no text" in err
                or "message can't be edited" in err
                or "message to edit not found" in err
            ):
                raise
            logger.info("edit_or_send_text: edit_text failed (%s); sending new message", exc)

    try:
        await message.delete()
    except Exception as exc:  # best-effort cleanup of stale media keyboards
        logger.debug("edit_or_send_text: could not delete old message: %s", exc)

    return await message.answer(text, **kwargs)
