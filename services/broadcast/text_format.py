"""Pure helpers for broadcast text formatting (native entities + HTML)."""

from __future__ import annotations

import html
import re
from collections.abc import Sequence

from aiogram.types import MessageEntity
from aiogram.utils.text_decorations import html_decoration

# Telegram HTML subset used by admins when typing tags manually.
_TAG_BODY = r"</?(?:b|strong|i|em|u|ins|s|strike|del|code|pre|a|tg-spoiler|tg-emoji|blockquote)"
_HTML_TAG_RE = re.compile(_TAG_BODY + r"(?:\s[^>]*)?>", re.IGNORECASE)

# Mismo subconjunto con grupo de captura: permite partir el texto conservando las etiquetas.
_HTML_TOKEN_RE = re.compile(f"({_HTML_TAG_RE.pattern})", re.IGNORECASE)

# Nombre de la etiqueta dentro de un token ya validado por _HTML_TAG_RE.
_TAG_NAME_RE = re.compile(r"</?([a-zA-Z-]+)")

# Longitud máxima del fragmento de mensaje que se muestra en el preview del wizard.
BROADCAST_PREVIEW_MAX_LENGTH = 500


def escape_broadcast_html_outside_tags(body: str) -> str:
    """
    Escapa el texto que queda FUERA de las etiquetas HTML de la whitelist.

    Las etiquetas válidas para Telegram se conservan; cualquier '<' que no abra una
    etiqueta soportada ('<3', '5 < 10', '<br>') se escapa, de modo que el resultado
    siempre es HTML parseable con parse_mode=HTML.

    Función pura.
    """
    parts = _HTML_TOKEN_RE.split(body)
    return "".join(part if index % 2 else html.escape(part) for index, part in enumerate(parts))


def close_open_broadcast_tags(snippet: str) -> str:
    """Cierra las etiquetas de whitelist que quedaron abiertas en el fragmento. Función pura."""
    stack: list[str] = []
    for raw_tag in _HTML_TAG_RE.findall(snippet):
        name = _TAG_NAME_RE.match(raw_tag).group(1).lower()
        if raw_tag.startswith("</"):
            if name in stack:
                stack = stack[: stack.index(name)]
        else:
            stack.append(name)
    return "".join(f"</{name}>" for name in reversed(stack))


def build_broadcast_preview_snippet(
    text: str, max_length: int = BROADCAST_PREVIEW_MAX_LENGTH
) -> str:
    """
    Recorta el HTML del broadcast para el preview sin partir ninguna etiqueta.

    Si el corte cae dentro de una etiqueta retrocede hasta antes del '<' y cierra las
    etiquetas que queden abiertas, para que el fragmento siga siendo HTML válido.

    Función pura.
    """
    if len(text) <= max_length:
        return text
    snippet = text[:max_length]
    last_open = snippet.rfind("<")
    if last_open > snippet.rfind(">"):
        snippet = snippet[:last_open]
    return snippet + close_open_broadcast_tags(snippet)


def strip_broadcast_html_to_plain_text(text: str) -> str:
    """
    Convierte HTML de broadcast a texto plano (red de seguridad del preview).

    Función pura.
    """
    return html.unescape(re.sub(r"<[^>]+>", "", text))


def resolve_broadcast_text_to_html(
    text: str | None,
    entities: Sequence[MessageEntity] | None = None,
) -> str:
    """
    Normalize broadcast body to HTML for channel send.

    - Native Telegram formatting (entities) → HTML via aiogram unparse.
    - Manual HTML tags kept as-is; el resto del texto se escapa.
    - Plain text escaped so parse_mode=HTML is always safe.

    Función pura.
    """
    body = text or ""
    if not body:
        return ""
    if entities:
        return html_decoration.unparse(body, list(entities))
    return escape_broadcast_html_outside_tags(body)


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
