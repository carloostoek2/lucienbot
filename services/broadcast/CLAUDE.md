# Broadcast Domain

Sistema de reacciones con besitos a mensajes broadcast. **NO envía broadcasts** — eso lo hacen los handlers directamente con la API de Telegram. `BroadcastService` gestiona emojis, reacciones y estadísticas.

## Services
- `broadcast_service.py` — Emojis de reacción y registro de reacciones

## Handlers
- `broadcast_handlers.py` — Admin: wizard de 8 pasos para broadcast (texto, attachment, reacciones, protección)

## BroadcastService API

**Gestión de botones de enlace extra (catálogo "definir primero", máx 1 por broadcast):**
- `create_broadcast_button(label, url, description=None)`
- `get_broadcast_button(button_id)`
- `get_all_buttons(active_only=True)`
- `toggle_broadcast_button(button_id)`
- `update_broadcast_button(button_id, label=None, url=None, description=None)`
- `delete_broadcast_button(button_id)`

Admin wizard completo en `gamification_admin_handlers` (config_buttons + add/edit/toggle/delete flows) accesible desde el menú de gamificación y desde "Configurar besitos".

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

**Reacciones (production paths):**
```python
# Production orchestration — handler calls this (gamification_user_handlers.py)
process_channel_reaction(broadcast_id, user_id, emoji_id, *, username, bot,
                       channel_id, message_id) -> dict
# Atomic register + credit + mission best-effort
check_and_register_reaction(broadcast_id, user_id, emoji_id, *, username, bot,
                            channel_id, message_id) -> dict

# Read helpers
has_user_reacted(broadcast_id, user_id) -> bool  # 1 reacción por usuario por mensaje
get_reactions_by_broadcast(broadcast_id) -> list[BroadcastReaction]
get_user_reactions(user_id, limit=20) -> list[BroadcastReaction]
get_reaction_count(broadcast_id) -> int
get_broadcast_stats(broadcast_id) -> dict

# DEPRECATED — legacy sync; do not use in new code
register_reaction(broadcast_id, user_id, reaction_emoji_id) -> BroadcastReaction
```

### Return dict contract

**Success:**
```python
{"success": True, "besitos_awarded": N, "id", "broadcast_id", "user_id",
 "emoji_id", "emoji_char"}
```

**Failure:**
```python
{"success": False, "reason": "<code>"}
```

Reason codes: `duplicate`, `invalid_broadcast`, `no_reactions`, `message_mismatch`,
`invalid_emoji`, `inactive_emoji`, `emoji_not_allowed`, `credit_failed`, `error`

### Validators (`services/broadcast/reaction_validators.py`)

4 pure read-only functions (no DB writes):
- `validate_broadcast_exists_for_reaction`
- `validate_broadcast_context_match` — guards `channel_id` + `message_id` (incl.
  `message_id=0` after `tracking_failed`)
- `validate_reaction_emoji_allowed`
- `validate_reaction_not_duplicate`

### Markup (`keyboards/broadcast_channel_markup.py`)

- **Send:** `build_broadcast_send_markup` / `build_channel_reaction_markup(..., emoji_counts=None)`
- **Refresh:** `build_channel_reaction_markup` with counts dict (`"emoji count"` when N>0)
- **Extra URL:** `extra_button_id` on `BroadcastMessage` included in send + refresh
- Row order: reactions first (chunked 8/row), extra URL last

### Message ID tracking

- `create_broadcast_message(message_id=0)` then `update_broadcast_message_id` after TG send
- If update fails → `tracking_failed`; admin alert; row stays at `message_id=0`
- Reactions on that broadcast return `message_mismatch` (validator blocks stale context)

### Atomicity

- Reaction INSERT + credit in `check_and_register_reaction`; credit internal commit
  (split-tx by design — see `decisions.md` defer entry for `credit_besitos(commit=False)`)
- Mission delivery + markup refresh post-commit, best-effort
- `process_channel_reaction` wraps register + `build_channel_reaction_markup` +
  `update_reaction_message` on success

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

Visitante reacciona
    → handle_reaction (gamification_user_handlers.py)
    → get_service(BroadcastService) ×1
    → process_channel_reaction(broadcast_id, user_id, emoji_id, channel_id, message_id, bot, username)
        → check_and_register_reaction (validators → INSERT + credit + commit → missions best-effort)
        → on success: build_channel_reaction_markup + update_reaction_message (best-effort)
    → callback.answer from result dict (success / reason / besitos_awarded)
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

## Cross-domain notifications (EventBus) (Item 6 / reduce remaining besito composers)

- BroadcastService held direct BesitoService composition for REACTION credits reduced (only this high-volume composer + game/daily in same Item per tight scope; local on-demand `BesitoService(db=self.db)` *only* inside `register_reaction` and `check_and_register_reaction` (the atomic gold path used by handlers); preserves 100% atomicity of REACTION credit tx + reaction row + mission best-effort + return dict with "besitos_awarded" local; credit does its internal commit as before; best-effort schedule_emit still fires post-commit).
- Added broadcast-domain observational listener `on_besitos_awarded_broadcast_reaction_observer` at module bottom (copy of story_service.py:670-694 "Cross-domain event listeners" block + structure + "MUST NOT call back into credit/debit besitos" + "best effort, non-authoritative" + "DESIRED CONTRACT (copy of narrative precedent + Reward Item5)" + log "broadcast | besitos_awarded_received | user_id=..."; purely observational, 0 mutation, 0 re-entrancy risk with reaction credit paths (authoritative in check_and_register_reaction + mission best-effort); 0 impact on reaction contracts or partial failure behavior protected by gold test_cross_service_atomicity + reaction_mission_flow + test_reaction_full_chain).
- (GameService similarly: held reduced + `on_besitos_awarded_game_award_observer` added for win + streak bonus awards; same contract.)
- Central explicit registration in bot.py on_startup (after scheduler, after the narrative + rewards listeners from Item5; imports for both new observers + 2 register calls + extended logger.info "... (besitos_awarded -> narrative, rewards, broadcast, game)"; comment updated "Fase 3 of eventbus-poc + Item 5 + Item 6: narrative + rewards + broadcast + game domains").
- 0 behavior change (register_reaction / check_and_register_reaction return identical reaction dicts / besitos_awarded local / mission increments; no user-visible or admin-visible change); 0 atomicity impact (re-runs of golds + patch schedule_emit in atomicity happy + reaction paths green; "credit survives" partials + "post-credit misiones (best effort) + event listeners (best effort)" hold); 0 other composers touched.
- Refs: services/event_bus.py (DESIRED CONTRACT + schedule_emit + gather return_exceptions), decisions.md (new Item6 entry post Item5), .planning/phases/24-remaining-besito-compositions/PLAN.md + gsd-remaining-besito-compositions.log (GSD pre every, 5 phases, self-check PASSED + "BATCH: 4 items completed in this tirón (final)"), services/gamification/CLAUDE.md + services/missions/CLAUDE.md (sibling notes), test_cross_service_atomicity.py (gold for atomicity/partial/best-effort + TestSession + N806 + TG 777 + try/finally), test_reaction_mission_flow.py + full_chain + limit (reaction→credit→mission chains).
- See also services/gamification/CLAUDE.md (Item1 cross) and services/missions/CLAUDE.md (Item5 cross) for the 3 critical systems (gamif source, missions/rewards via atomic, narrative listener precedent).
