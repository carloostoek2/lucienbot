"""Pure helpers for broadcast text formatting (native entities + HTML)."""

from __future__ import annotations

import html
import re
from typing import Sequence

from aiogram.types import MessageEntity
from aiogram.utils.text_decorations import html_decoration

# Telegram HTML subset used by admins when typing tags manually.
_HTML_TAG_RE = re.compile(
    r"</?(?:b|strong|i|em|u|ins|s|strike|del|code|pre|a|tg-spoiler|tg-emoji|blockquote)"
    r"(?:\s[^>]*)?>",
    re.IGNORECASE,
)


def resolve_broadcast_text_to_html(
    text: str | None,
    entities: Sequence[MessageEntity] | None = None,
) -> str:
    """
    Normalize broadcast body to HTML for channel send.

    - Native Telegram formatting (entities) → HTML via aiogram unparse.
    - Manual HTML tags kept as-is.
    - Plain text escaped so parse_mode=HTML is always safe.

    Función pura.
    """
    body = text or ""
    if not body:
        return ""
    if entities:
        return html_decoration.unparse(body, list(entities))
    if _HTML_TAG_RE.search(body):
        return body
    return html.escape(body)


def extract_message_text_and_entities(message) -> tuple[str, list[MessageEntity] | None]:
    """
    Pull text/caption and matching entities from a Telegram Message-like object.

    Función pura respecto al input (no side-effects).
    """
    if getattr(message, "text", None) is not None:
        text = message.text or ""
        entities = getattr(message, "entities", None)
        return text, list(entities) if entities else None
    if getattr(message, "caption", None) is not None:
        text = message.caption or ""
        entities = getattr(message, "caption_entities", None)
        return text, list(entities) if entities else None
    return "", None
