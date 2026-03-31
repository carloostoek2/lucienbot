# Broadcast Domain

Sistema de reacciones con besitos a mensajes broadcast. **NO envía broadcasts** — eso lo hacen los handlers directamente con la API de Telegram. `BroadcastService` gestiona emojis, reacciones y estadísticas.

## Services
- `broadcast_service.py` — Emojis de reacción y registro de reacciones

## Handlers
- `broadcast_handlers.py` — Admin: wizard de 8 pasos para broadcast (texto, attachment, reacciones, protección)

## BroadcastService API

**Gestión de emojis de reacción:**
```python
create_reaction_emoji(emoji, name, besito_value) -> ReactionEmoji
get_reaction_emoji(emoji_id) -> ReactionEmoji
get_all_emojis(active_only=True) -> list[ReactionEmoji]
update_emoji_value(emoji_id, besito_value) -> bool
toggle_emoji(emoji_id) -> bool  # Activar/desactivar
delete_emoji(emoji_id) -> bool
```

**Registro de mensajes broadcast:**
```python
create_broadcast_message(message_id, channel_id, admin_id, text,
                         has_attachment, has_reactions, is_protected) -> BroadcastMessage
get_broadcast(broadcast_id) -> BroadcastMessage
get_recent_broadcasts(channel_id=None, limit=20) -> list[BroadcastMessage]
```

**Reacciones:**
```python
has_user_reacted(broadcast_id, user_id) -> bool  # 1 reacción por usuario por mensaje
register_reaction(broadcast_id, user_id, reaction_emoji_id) -> BroadcastReaction
get_reactions_by_broadcast(broadcast_id) -> list[BroadcastReaction]
get_user_reactions(user_id, limit=20) -> list[BroadcastReaction]
get_reaction_count(broadcast_id) -> int
get_broadcast_stats(broadcast_id) -> dict
```

## Flujo de Broadcast

```
Admin inicia broadcast
    → Selecciona canal (1-6)
    → Escribe texto
    → ¿Tiene attachment? Sí/No
    → ¿Tiene reacciones? Sí/No → Selecciona emojis
    → ¿Es protegido? Sí/No (protegido = no se puede reenviar)
    → Confirma y envía
    → Handler envía mensaje a canal via bot.send_message()

Visitante reacciona al mensaje
    → Handler recibe callback
    → BroadcastService.has_user_reacted() → ya reaccionó? → reject
    → BroadcastService.register_reaction()
    → BesitoService.credit_besitos() → acreditar besitos al visitante
```

## Reglas de Negocio
- **1 reacción por usuario por mensaje broadcast** (enforcement en `has_user_reacted`)
- Besitos se acreditan al reaccionar — configurable por emoji
- Mensaje protegido = `is_protected` previene reenvío
- Broadcast real (enviar a canal) se hace en el handler con Telegram API, no en el service

## Errores comunes a evitar
- ❌ `BroadcastService.broadcast_message()` — NO existe
- ❌ `BroadcastService.broadcast_to_vip()` — NO existe
- ✅ El handler usa `bot.send_message()` directamente

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. El envío de mensajes va en el handler, no en el service
4. Verifica métodos en `broadcast_service.py`
