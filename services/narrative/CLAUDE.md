# Narrative Domain

Narrativa interactiva con arquetipos y nodos de historia.

## Services
- [story_service.py](../story_service.py) - Gestión narrativa

## Handlers
- [story_user_handlers.py](../../handlers/story_user_handlers.py) - Usuario
- [story_admin_handlers.py](../../handlers/story_admin_handlers.py) - Admin

## Modelos
- `StoryNode` - Nodos de narrativa
- `StoryChoice` - Opciones de decisión
- `UserStoryProgress` - Progreso por usuario
- `Archetype` - Arquetipos definidos
- `StoryAchievement` - Logros de narrativa
- `UserStoryAchievement` - Logros desbloqueados (relationship → `StoryAchievement`)

## StoryService API
```python
- create_node(...) / create_choice(...) / create_achievement(...)
- advance_to_node(user_id, node_id, choice_id=None, is_vip=None)
- can_access_node(user_id, node_id, is_vip=None, choice_id=None)
- validate_continue_transition(user_id, target_node_id)
- resolve_next_narrative_node(node_id)
- is_user_vip(user_id)  # delega a VIPService
- get_user_progress(user_id) / get_visited_node_count(user_id)
- grant_node_access(user_id, node_id, reference_fulfillment_id=None) — sin debit; idempotente; no avanza historia principal
- calculate_archetype(progress) / calculate_archetype_from_quiz(answers)
- get_archetype_quiz_questions() / assign_archetype_to_user(...)
- get_story_stats()
```

## Flujo Narrativo
```
Usuario → advance_to_node (besitos commit=False + progreso)
  → show_node (solo renderizado)
Elección → advance_to_node(..., choice_id=...) con validación de ownership
Continuar lineal → validate_continue_transition + advance_to_node
```

## Arquetipos
- Determina el contenido disponible por usuario
- Calculado basándose en decisiones tomadas y quiz
- Afecta gates en `can_access_node`

## Reglas de Negocio
- Nodo VIP: `StoryService.is_user_vip` (handlers usan solo StoryService)
- Progreso y besitos: un solo `db.commit()` en `advance_to_node`
- `additional_cost` en choices se suma al costo del nodo
- Logros: AND semantics en requisitos múltiples
- Revisitas a nodos ya en `visited_nodes`: sin re-cobro

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos existentes en story_service.py
4. Toda navegación forward pasa por `advance_to_node`

## Cross-domain notifications (EventBus PoC Item 1)
- Narrative es el **primer subscriptor** del evento "besitos_awarded" emitido por gamificación (BesitoService).
- El listener `on_besitos_awarded_from_gamification(payload)` vive en `story_service.py` (ownership del dominio narrative).
- Es puramente best-effort: loguea "narrative | besitos_awarded_received | user_id=... | amount=... | source=... | ref=..." ; puede crecer a lógica de progreso/hints por besitos acumulados (usando get_service(StoryService) si necesita sesión), **pero nunca debe llamar credit/debit besitos** (evita loops con el crédito inverso que `_grant_achievement` ya hace para rewards de logros).
- El registro es explícito y central en `bot.py` (on_startup, después de scheduler): `get_event_bus().register(EVENT_BESITOS_AWARDED, on_besitos_awarded_from_gamification)`.
- Errores del listener son tragados por el bus (no afectan al emisor ni a otros listeners).
- Ver `services/event_bus.py`, `bot.py` (registro), y `services/gamification/CLAUDE.md` (emisor).