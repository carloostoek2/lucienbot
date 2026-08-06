"""Pure validators for broadcast reaction registration (read-only, no DB writes)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.models import BroadcastMessage, ReactionEmoji


def validate_broadcast_exists_for_reaction(broadcast: BroadcastMessage | None) -> str | None:
    """Valida que el broadcast exista. Función pura."""
    if not broadcast:
        return "invalid_broadcast"
    return None


def validate_broadcast_context_match(
    broadcast: BroadcastMessage,
    channel_id: int | None,
    message_id: int | None,
) -> str | None:
    """Valida channel_id y message_id contra el broadcast. Función pura."""
    if channel_id is not None and broadcast.channel_id != channel_id:
        return "message_mismatch"
    if message_id is not None and broadcast.message_id != message_id:
        return "message_mismatch"
    return None


def validate_reaction_emoji_allowed(
    emoji: ReactionEmoji | None,
    emoji_id: int,
    selected_ids: list[int],
) -> str | None:
    """Valida emoji activo y permitido en el broadcast. Función pura."""
    if not emoji:
        return "invalid_emoji"
    if not emoji.is_active:
        return "inactive_emoji"
    if emoji_id not in selected_ids:
        return "emoji_not_allowed"
    return None


def validate_reaction_not_duplicate(has_user_reacted: bool) -> str | None:
    """Valida que el usuario no haya reaccionado ya. Función pura."""
    if has_user_reacted:
        return "duplicate"
    return None


def should_heal_message_id(
    broadcast: BroadcastMessage,
    channel_id: int | None,
    message_id: int | None,
) -> bool:
    """Detecta un broadcast en tracking_failed (message_id=0) reparable desde el callback.

    Solo se repara cuando el broadcast quedó en 0 (el envío a Telegram pudo llegar pero
    el ID nunca se registró), el callback pertenece al mismo canal y trae un message_id
    real (>0). Función pura.
    """
    if broadcast.message_id != 0:
        return False
    if channel_id is None or broadcast.channel_id != channel_id:
        return False
    if not message_id or message_id <= 0:
        return False
    return True
