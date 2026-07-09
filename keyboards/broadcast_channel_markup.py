"""Unified pure markup builders for broadcast channel reactions (send + refresh)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.callback_data import ReactionCallback

if TYPE_CHECKING:
    from models.models import BroadcastButton


def chunk_reaction_buttons(
    buttons: list[InlineKeyboardButton], max_per_row: int = 8
) -> list[list[InlineKeyboardButton]]:
    """Divide botones inline en filas de máximo max_per_row. Función pura."""
    return [buttons[i : i + max_per_row] for i in range(0, len(buttons), max_per_row)]


def calculate_emoji_counts_from_reactions(reactions: list) -> dict[int, int]:
    """Calcula el mapa de conteos de emojis a partir de reacciones registradas. Función pura."""
    emoji_counts: dict[int, int] = {}
    for r in reactions:
        if r.reaction_emoji:
            emoji_id_val = r.reaction_emoji.id
            emoji_counts[emoji_id_val] = emoji_counts.get(emoji_id_val, 0) + 1
    return emoji_counts


def build_channel_reaction_markup(
    broadcast_id: int,
    emoji_entries: list[tuple[int, str]],
    *,
    emoji_counts: dict[int, int] | None = None,
    extra_button: BroadcastButton | None = None,
) -> InlineKeyboardMarkup | None:
    """Construye markup unificado: reacciones (send o refresh) + botón URL extra. Función pura."""
    rows: list[list[InlineKeyboardButton]] = []
    if emoji_entries:
        reaction_buttons = []
        for emoji_id, emoji_char in emoji_entries:
            if emoji_counts is None:
                text = emoji_char
            else:
                count = emoji_counts.get(emoji_id, 0)
                text = f"{emoji_char} {count}" if count > 0 else emoji_char
            reaction_buttons.append(
                InlineKeyboardButton(
                    text=text,
                    callback_data=ReactionCallback(
                        broadcast_id=broadcast_id, emoji_id=emoji_id
                    ).pack(),
                )
            )
        if reaction_buttons:
            rows.extend(chunk_reaction_buttons(reaction_buttons))
    if extra_button:
        rows.append([InlineKeyboardButton(text=extra_button.label, url=extra_button.url)])
    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_send_reaction_markup(
    broadcast_id: int,
    selected_emoji_ids: list[int],
    get_emoji,
) -> InlineKeyboardMarkup | None:
    """Construye teclado de reacciones para envío de broadcast (orphan path parity). Función pura."""
    buttons = []
    for emoji_id in selected_emoji_ids:
        emoji = get_emoji(emoji_id)
        if emoji:
            buttons.append(
                InlineKeyboardButton(
                    text=f"{emoji.emoji}",
                    callback_data=ReactionCallback(
                        broadcast_id=broadcast_id, emoji_id=emoji.id
                    ).pack(),
                )
            )
    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def build_broadcast_send_markup(
    broadcast_id: int,
    selected_emoji_ids: list[int],
    extra_button,
    get_emoji,
) -> InlineKeyboardMarkup | None:
    """Wrapper send-path; delega a build_channel_reaction_markup. Función pura."""
    emoji_entries = []
    for eid in selected_emoji_ids:
        em = get_emoji(eid)
        if em:
            emoji_entries.append((em.id, em.emoji))
    return build_channel_reaction_markup(
        broadcast_id,
        emoji_entries,
        emoji_counts=None,
        extra_button=extra_button,
    )
