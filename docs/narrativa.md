# Módulo de Narrativa - Lucien Bot

**Alcance:** Únicamente el módulo de narrativa (historia interactiva, nodos, elecciones, arquetipos, progreso, logros y cuestionario). Excluye detalles profundos de otros dominios excepto las interacciones explícitas de integración. Se cubre cómo se comunica con gamificación (besitos + EventBus) y con administración de canales (vía VIP gates).

**Dominio:** Narrativa (`StoryService`). Experiencia de "Fragmentos de la Historia" de Diana. Arquetipos que se calculan por decisiones, nodos con requisitos (VIP, arquetipo, costo en besitos), progreso persistente, logros con recompensas.

**Arquitectura local:** `handlers/story_*_handlers.py` (routing + FSM + un solo `get_service(StoryService)` por entrypoint) → `services/story_service.py` (dueño del dominio: nodos, choices, progreso, quiz hardcoded, achievements, besitos costs/rewards) → models. VIP vía `StoryService.is_user_vip()` (delega internamente a VIPService; handlers **no** importan VIPService). BesitoService instancia propia para débitos/créditos atómicos.

**Entrypoint usuario:** Menú "narrative" → start/continue, quiz de arquetipo, logros. Admin: "admin_narrative" → wizards de nodos/choices/arquetipos/achievements + stats.

---

## Módulos Principales

| Módulo | Archivo | Responsabilidad |
|--------|---------|-----------------|
| Handlers Usuario | `handlers/story_user_handlers.py` | Menú narrativa, start/continue story, `show_node` (solo renderizado), choices (`StoryChoiceCallback` → `advance_to_node`), quiz FSM (`ArchetypeQuizStates`), achievements view. Un `get_service(StoryService)` por handler; `story_service` se pasa a helpers de render (`_render_node`, `show_quiz_question`, `calculate_and_show_archetype`) sin `get_service` anidado. |
| Handlers Admin | `handlers/story_admin_handlers.py` | Menú admin (`admin_narrative`), full wizards FSM (NodeWizardStates, ChoiceWizardStates, ArchetypeWizardStates, AchievementWizardStates), list/toggle/delete nodes, manage choices/archetypes/achievements, stats. `is_admin` guards + `with get_service(StoryService)`. |
| StoryService (core) | `services/story_service.py` | CRUD nodos/choices/archetypes/achievements, `can_access_node` (VIP + arquetipo + besitos cost checks), `advance_to_node` (atomic: debit commit=False + puntos arquetipo + progreso + logros), quiz methods (hardcoded questions + `calculate_archetype_from_quiz`), `_grant_achievement` (credits besitos o package), EventBus listener ownership, stats, archetype calc. Mantiene `self.besito_service = BesitoService(self.db)`. |
| Modelos | `models/models.py` | `NodeType`, `ArchetypeType` (6 arquetipos), `StoryNode`, `StoryChoice`, `UserStoryProgress` (**`UniqueConstraint` en `user_id`**), `Archetype`, `StoryAchievement`, `UserStoryAchievement`. |
| Soporte cross | `services/vip_service.py` (delegado por StoryService), `services/besito_service.py`, `services/event_bus.py` (listener). | Registro explícito en bot.py. |
| Documentación | `services/narrative/CLAUDE.md` | Contrato EventBus, reglas VIP/arquetipo, flujos básicos. |

**Notas de construcción:**
- Handlers: `with get_service(StoryService) as story_service:` (exact 1 service principal); VIP vía `story_service.is_user_vip()` — **nunca** `VIPService()` en handlers.
- Service mantiene BesitoService propio (para débitos atómicos con `commit=False` y créditos de logros).
- Quiz de arquetipo está **hardcodeado** en el servicio (`get_archetype_quiz_questions` + `calculate_archetype_from_quiz`).
- Atomicidad en `advance_to_node`: besitos debit + progreso + puntos + commit único; logros post-commit.
- `UserStoryProgress.user_id` tiene constraint único; carrera concurrente en primer avance se resuelve con `IntegrityError` + retry con `FOR UPDATE`.
- EventBus: narrative es **primer subscriptor** (ownership del listener en este dominio).
- **Lucien voice:** prefijo `🎩 <b>Lucien:</b>` inline en handlers para UI interactiva; `LucienVoice` se usa en mensajes de servicio (`can_access_node`, denegaciones). Centralización total en `LucienVoice` queda diferida (ver §Decisiones diferidas).

---

## Modelos Clave (extracto)

```python
class NodeType(enum.StrEnum):
    NARRATIVE = "narrative"
    DECISION = "decision"
    ENDING = "ending"
    QUIZ = "quiz"  # En grafo: botón "Iniciar cuestionario" → discover_archetype

class UserStoryProgress(Base):
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_story_progress_user_id"),)
    user_id  # BigInteger, UNIQUE — una fila de progreso por usuario Telegram
    current_node_id, archetype, *_points (6), visited_nodes (JSON), current_chapter, ...
```

Relaciones permiten grafo de nodos (choices apuntan a next_node), historial de visitas, cálculo de arquetipo dominante por puntos acumulados en elecciones.

---

## StoryService — API Principal

### Nodos
- `create_node(...)`, `get_node`, `get_all_nodes`, `get_nodes_by_chapter`, `get_starting_node`, `update_node`, `delete_node`

### Choices / Decisiones
- `create_choice(...)`, `get_choice`, `get_node_choices`, `update_choice`, `delete_choice`

### Progreso y Acceso
- `get_user_progress(user_id)`, `get_or_create_progress(user_id)`, `create_user_progress(user_id, starting_node_id=None)`
- `has_started_story(user_id) -> bool`
- `is_user_vip(user_id) -> bool` — delega a VIPService (handlers usan solo StoryService).
- `validate_continue_transition(user_id, target_node_id)` — sucesor lineal desde nodo actual (`order_in_chapter`).
- `resolve_next_narrative_node(node_id)` — inferencia lineal por `order_in_chapter` en el mismo capítulo.
- `can_access_node(user_id, node_id, is_vip=None, choice_id=None) -> tuple[bool, str | None]`:
  - Checks: node active, required_vip, required_archetype, balance.
  - Pay-once: nodos en `visited_nodes` no re-exigen `cost_besitos`; `additional_cost` de elección se valida en avance.
- `advance_to_node(user_id, node_id, choice_id=None, is_vip=None) -> tuple[bool, str | None, progress | None]`:
  - `_validate_choice_transition` (ownership + destino; terminal exige `target == choice.node_id`).
  - `can_access_node` → `_execute_advance_transaction` (`FOR UPDATE` progreso, primer insert con retry en `IntegrityError`, débito pay-once + additional_cost, commit).
  - `_check_achievements` best-effort post-commit (errores no revierten navegación).

### Arquetipos y Quiz
- `get_archetype_quiz_questions()` (hardcoded), `calculate_archetype_from_quiz(answers)`, `apply_quiz_scores_to_progress`, `assign_archetype_to_user` (inmutable tras primera asignación).

### Logros (Achievements)
- `create_achievement(...)` acepta `reward_package_id`; wizard admin solo pide `reward_besitos` (paquete vía API/DB directa — ver §Decisiones diferidas).
- `_grant_achievement`: besitos vía `credit_besitos` (commit propio); paquete validado y marcado `reward_delivered=False`.

### Estadísticas
- `get_story_stats() -> dict`

---

## Flujos Principales

### Flujo Usuario (interactivo)
1. Menú narrativa → si no started: "Comenzar la historia" o "Descubrir arquetipo".
2. `start_story` / `continue_story` → `advance_to_node` (si aplica) → `show_node(current_node_id, story_service)`.
3. `show_node` (**solo renderizado**, sin mutar progreso ni besitos):
   - Obtiene node + choices.
   - `story_service.can_access_node(user_id, node_id)` (VIP resuelto internamente si `is_vip` omitido).
   - Si denegado: mensaje con razón (VIP, arquetipo, costo besitos).
   - Muestra título + `node.content` (HTML admin-trusted) + costo si aplica.
   - Si `ENDING`: botón "Ver mi arquetipo".
   - Si `QUIZ`: botón "Iniciar cuestionario" → `discover_archetype` (quiz FSM separado).
   - Si choices: botones con `StoryChoiceCallback`.
   - Si no choices y no ending/quiz: "Continuar" vía `ContinueStoryCallback` → `validate_continue_transition` + `advance_to_node`.
4. Choice callback → `advance_to_node(user_id, target_node_id, choice_id)`.
5. Quiz: "Descubrir mi arquetipo" → FSM answering → `calculate_and_show_archetype` → assign + mostrar.
6. Logros: lista desbloqueados.

**Toda navegación forward muta estado vía `advance_to_node`.** `show_node` no valida reachability del grafo (defense-in-depth diferido — ver §Límites de confianza).

### Flujo Admin (wizards FSM)
- Crear nodo: title → content → tipo (NARRATIVE/DECISION/ENDING/QUIZ) → capítulo → requisitos → costo besitos → confirmar.
- Gestionar logros: name, reqs por node/archetype/chapter, `reward_besitos` (sin picker de paquete en wizard).

---

## Límites de Confianza (Trust Boundaries)

| Superficie | Modelo de confianza | Justificación |
|------------|---------------------|---------------|
| `node.content` HTML | **Admin-trusted** | Solo Custodios crean/editan nodos vía wizard admin (`is_admin`). Se renderiza sin sanitizar en `show_node` para permitir formato rico. Títulos y razones de denegación sí usan `html.escape`. |
| Reachability en `show_node` | **Service-gated en avance** | `advance_to_node` valida transiciones (choice ownership, `validate_continue_transition`). `show_node` solo muestra el nodo ya autorizado o el `current_node_id` del progreso. Saltos arbitrarios no pasan por handlers de avance. |
| VIP | **Delegado en StoryService** | Handlers nunca llaman VIPService directamente. |

---

## Cómo se Otorgan / Gastan Besitos

**Gastos:** `advance_to_node` → `debit_besitos(..., commit=False)` + commit conjunto con progreso.

**Ingresos:** `_grant_achievement` → `credit_besitos(..., source=MISSION)` post-commit del avance principal. `credit_besitos` no expone `commit=False`; el logro y el crédito comparten transacción implícita del servicio de besitos. Duplicados de logro se manejan con `IntegrityError` en `UserStoryAchievement`.

---

## Cómo se Comunica con Gamificación

- Débitos para acceso a nodos costosos (atomic con progreso).
- Créditos automáticos por logros (`source=MISSION`).
- **EventBus:** narrative es primer subscriptor de `EVENT_BESITOS_AWARDED`. Listener `on_besitos_awarded_from_gamification` es observacional — **MUST NOT** mutar besitos.

---

## Cómo se Comunica con Administración de Canales

- Gate VIP: `StoryService.is_user_vip(user_id)` antes de `can_access_node`.
- **No hay llamadas directas a ChannelService** desde narrativa.
- Membresía VIP materializada como `Subscription` a canal VIP (dominio canales).

---

## Logging

Formato estándar en handlers y servicio:
```
story_user_handlers | <acción> | user_id=<id> | result=<ok|denied|...>
story_service | <acción> | user_id=<id> | result=<ok|denied|...>
```

Entrypoints con logging: `narrative_menu`, `start_story`, `continue_story`, `show_node`, `go_to_node`, `make_choice`, `start_archetype_quiz`, `process_quiz_answer`, `calculate_archetype`, `view_my_archetype`, `my_story_achievements`, `advance_to_node`, `grant_achievement`.

---

## Decisiones Diferidas (WONTFIX documentado)

| Tema | Decisión | Justificación |
|------|----------|---------------|
| StoryService ~958 LOC (God object) | **WONTFIX** | Fuera de alcance del fix pass narrativa. Dominio cohesivo; split solo si se extrae quiz provider. |
| 12–16 funciones >50 LOC en handlers/admin | **WONTFIX** | Residual en wizards admin FSM (bulk UI). Helpers puros ya extraídos en user handlers. |
| LucienVoice centralización total | **WONTFIX** | Handlers usan prefijo Lucien inline + escape selectivo; `LucienVoice` cubre mensajes de servicio. Migración masiva sin beneficio UX. |
| Reachability en `show_node` | **WONTFIX** | Defense-in-depth redundante: avance ya valida transiciones; `show_node` recibe nodos post-`advance_to_node` o `current_node_id`. |
| HTML raw en `node.content` | **WONTFIX (intencional)** | Feature admin: contenido rico. Trust boundary documentada arriba. |
| `_grant_achievement` split-commit | **WONTFIX** | `BesitoService.credit_besitos` no soporta `commit=False`; `IntegrityError` cubre carrera de logros duplicados. |
| Wizard `reward_package_id` | **WONTFIX** | Campo soportado en modelo/API (`create_achievement`); picker UI diferido — configuración vía edición directa o futuro paso wizard. |
| Sucesor lineal `order_in_chapter` | **WONTFIX (by design)** | Capítulos lineales sin elecciones usan inferencia por orden; grafos ramificados usan `StoryChoice`. Documentado en `resolve_next_narrative_node`. |
| `NodeType.QUIZ` in-graph | **FIXED** | Nodos QUIZ muestran botón "Iniciar cuestionario" → `discover_archetype`. |

---

## Mapa de Cobertura de Tests

| Área | Archivo | Cobertura |
|------|---------|-----------|
| Atomicidad advance + debit commit=False | `tests/unit/test_story_service.py` | `TestStoryServiceAtomicity`, gold Fase6 |
| Gates VIP/arquetipo/costo | `tests/unit/test_story_service.py` | `TestStoryAccessGatesPhase6` |
| Transiciones inválidas / IDOR | `tests/unit/test_story_service.py` | `TestStoryInvalidTransitions`, `TestChoiceIdor` |
| Logros + besitos | `tests/unit/test_story_service.py` | `TestStoryAchievementAtomicity`, `TestCheckAchievements` |
| Quiz cálculo | `tests/unit/test_story_service.py` | `TestArchetypeQuizPhase6` |
| Progreso único concurrente | `tests/unit/test_story_service.py` | `TestConcurrentProgressUnique` |
| Handlers usuario | `tests/handlers/test_story_user_handlers.py` | Menú, start/continue, choices, show_node, quiz, arquetipo, logros |
| Quiz completion handler | `tests/handlers/test_story_user_handlers.py` | `TestQuizCompletion` |
| Admin deny (filtro router) | `tests/handlers/test_story_user_handlers.py` | `TestAdminDeny` |
| EventBus no-mutación | `tests/unit/test_story_service.py` | `test_on_besitos_awarded_listener_does_not_mutate_besitos` |

---

## Reglas y Gotchas

- **Handlers:** Siempre `with get_service(StoryService)`; pasar `story_service` a helpers — sin `get_service` anidado.
- **Atomicidad crítica:** Débito `commit=False` + commit único en `advance_to_node`.
- **Progreso único:** `UniqueConstraint(user_id)` + retry en `IntegrityError` al primer insert concurrente.
- **Quiz hardcoded:** En servicio, no en DB.
- **Arquetipo:** Once-only; no se sobrescribe tras asignación.
- **Custodios:** Filtro `lambda cb: not is_admin(...)` en todos los entrypoints usuario — admins usan panel admin narrativa.

**Fin del documento — solo módulo de narrativa.**