# Módulo de Narrativa - Lucien Bot

**Alcance:** Únicamente el módulo de narrativa (historia interactiva, nodos, elecciones, arquetipos, progreso, logros y cuestionario). Excluye detalles profundos de otros dominios excepto las interacciones explícitas de integración. Se cubre cómo se comunica con gamificación (besitos + EventBus) y con administración de canales (vía VIP gates).

**Dominio:** Narrativa (`StoryService`). Experiencia de "Fragmentos de la Historia" de Diana. Arquetipos que se calculan por decisiones, nodos con requisitos (VIP, arquetipo, costo en besitos), progreso persistente, logros con recompensas.

**Arquitectura local:** `handlers/story_*_handlers.py` (routing + FSM + get_service(StoryService) + checks VIP externos) → `services/story_service.py` (dueño del dominio: nodos, choices, progreso, quiz hardcoded, achievements, besitos costs/rewards) → models (StoryNode, StoryChoice, UserStoryProgress con puntos por arquetipo, StoryAchievement, etc.). Usa BesitoService (instancia propia para débitos/créditos atómicos) y VIPService (en handlers para is_vip).

**Entrypoint usuario:** Menú "narrative" → start/continue, quiz de arquetipo, logros. Admin: "admin_narrative" → wizards de nodos/choices/arquetipos/achievements + stats.

---

## Módulos Principales

| Módulo | Archivo | Responsabilidad |
|--------|---------|-----------------|
| Handlers Usuario | `handlers/story_user_handlers.py` | Menú narrativa, start/continue story, `show_node` (con VIP check + can_access), choices (StoryChoiceCallback), quiz FSM (`ArchetypeQuizStates`), achievements view, calculate archetype. Usa `with get_service(StoryService)`, VIPService directo para `is_user_vip`. |
| Handlers Admin | `handlers/story_admin_handlers.py` | Menú admin (`admin_narrative`), full wizards FSM (NodeWizardStates, ChoiceWizardStates, ArchetypeWizardStates, AchievementWizardStates), list/toggle/delete nodes, manage choices/archetypes/achievements, stats. `is_admin` guards + `with get_service(StoryService)`. |
| StoryService (core) | `services/story_service.py` | CRUD nodos/choices/archetypes/achievements, `can_access_node` (VIP + arquetipo + besitos cost checks), `advance_to_node` (atomic: debit commit=False + puntos arquetipo + progreso + logros), quiz methods (hardcoded questions + `calculate_archetype_from_quiz`), `_grant_achievement` (credits besitos o package), EventBus listener ownership, stats, archetype calc. Mantiene `self.besito_service = BesitoService(self.db)`. |
| Modelos | `models/models.py` | `NodeType`, `ArchetypeType` (6 arquetipos), `StoryNode` (required_vip, cost_besitos, required_archetype, chapter, is_starting_node), `StoryChoice` (archetype_points, additional_cost), `UserStoryProgress` (puntos por arquetipo + JSON visited + current), `Archetype`, `StoryAchievement` (reward_besitos + package), `UserStoryAchievement`. |
| Soporte cross | `services/vip_service.py` (is_user_vip en handlers), `services/besito_service.py` (vía instancia propia del servicio para costos/recompensas), `services/event_bus.py` (listener). | Registro explícito en bot.py. |
| Documentación | `services/narrative/CLAUDE.md` | Contrato EventBus (listener ownership, MUST NOT mutate besitos), reglas VIP/arquetipo, flujos básicos. |

**Notas de construcción:**
- Handlers: `with get_service(StoryService) as story_service:` (exact 1 service principal) + VIPService para checks de acceso (patrón visto en otros).
- Service mantiene BesitoService propio (para débitos atómicos con `commit=False` y créditos de logros).
- Quiz de arquetipo está **hardcodeado** en el servicio (`get_archetype_quiz_questions` + `calculate_archetype_from_quiz`).
- Atomicidad en `advance_to_node`: besitos debit + progreso + puntos + commit único; logros post-commit.
- EventBus: narrative es **primer subscriptor** (ownership del listener en este dominio).
- Lucien voice en todos los textos/UI.

---

## Modelos Clave (extracto)

```python
class NodeType(enum.StrEnum):
    NARRATIVE = "narrative"
    DECISION = "decision"
    ENDING = "ending"
    QUIZ = "quiz"

class ArchetypeType(enum.StrEnum):
    SEDUCTOR = "seductor"
    OBSERVER = "observer"
    DEVOTO = "devoto"
    EXPLORADOR = "explorador"
    MISTERIOSO = "misterioso"
    INTREPIDO = "intrepido"

class StoryNode(Base):
    id, title, content
    node_type: NodeType
    required_archetype: ArchetypeType | None
    required_vip: bool = False
    cost_besitos: int = 0
    chapter, order_in_chapter
    is_active, is_starting_node
    choices = relationship(StoryChoice)
    # has_choices property

class StoryChoice(Base):
    node_id (FK), text, next_node_id (FK)
    choice_archetype: ArchetypeType | None
    archetype_points: int = 0
    additional_cost: int = 0

class UserStoryProgress(Base):
    user_id, current_node_id (FK), archetype: ArchetypeType | None
    seductor_points, observer_points, ... (6 campos)
    visited_nodes: Text (JSON list de IDs)
    current_chapter, started_at, last_interaction, completed_at
    # get_archetype_scores(), get_dominant_archetype()

class StoryAchievement(Base):
    icon, name, description
    required_node_id, required_archetype, required_chapter
    reward_besitos: int = 0, reward_package_id
    is_active

class UserStoryAchievement(Base):
    user_id, achievement_id (FK), unlocked_at, reward_delivered, reward_delivered_at
```

Relaciones permiten grafo de nodos (choices apuntan a next_node), historial de visitas, cálculo de arquetipo dominante por puntos acumulados en elecciones.

---

## StoryService — API Principal

### Nodos
- `create_node(title, content, node_type=NARRATIVE, chapter=1, order_in_chapter=0, required_archetype=None, required_vip=False, cost_besitos=0, is_starting_node=False, created_by=None)`
- `get_node(node_id)`, `get_all_nodes(active_only=True)`, `get_nodes_by_chapter(chapter)`, `get_starting_node()`
- `update_node(node_id, **kwargs)` (campos permitidos: title/content/type/chapter/reqs/cost/active/starting), `delete_node(node_id)`

### Choices / Decisiones
- `create_choice(node_id, text, next_node_id=None, choice_archetype=None, archetype_points=0, additional_cost=0)`
- `add_choice_to_node(...)` (alias)
- `get_choice(choice_id)`, `get_node_choices(node_id)`
- `update_choice`, `delete_choice`

### Progreso y Acceso
- `get_user_progress(user_id)`, `get_or_create_progress(user_id)`, `create_user_progress(user_id, starting_node_id=None)`
- `has_started_story(user_id) -> bool`
- `can_access_node(user_id, node_id, is_vip: bool = False) -> tuple[bool, str | None]`:
  - Checks: node active, required_vip (usa is_vip pasado), required_archetype (contra progress.archetype), cost_besitos (consulta balance vía besito_service).
  - Retorna razón en voz de Lucien si denegado.
- `advance_to_node(user_id, node_id, choice_id=None, is_vip: bool = False) -> tuple[bool, str | None, progress | None]`:
  - Llama can_access.
  - Si cost: `besito_service.debit_besitos(..., commit=False, source=PURCHASE)` (atomicidad con progreso).
  - Si choice: `_add_archetype_points` (sin commit).
  - Actualiza current_node, chapter, last_interaction, visited_nodes (JSON append si nuevo).
  - Si ENDING: completed_at + asigna dominant archetype si falta.
  - Commit atómico (besitos + progreso).
  - Post: `_check_achievements(user_id, progress)`.
- `_add_archetype_points(progress, choice)` (pura, muta el progress object).
- `_check_achievements`, `_grant_achievement` (ver abajo).

### Arquetipos y Quiz
- `create_archetype(...)`, `get_archetype(archetype_type)`, `get_all_archetypes()`
- `assign_archetype_to_user(user_id, archetype_type)`
- `get_user_archetype(user_id)`
- `calculate_archetype(progress) -> dominant`
- `get_archetype_description(archetype_type)`
- `get_archetype_quiz_questions() -> list[dict]` (hardcoded: preguntas con opciones que otorgan puntos a arquetipos).
- `calculate_archetype_from_quiz(answers: list[int]) -> ArchetypeType` (suma scores por opción, retorna max).

### Logros (Achievements)
- `create_achievement(name, description, required_node_id=None, required_archetype=None, required_chapter=None, reward_besitos=0, reward_package_id=None, ...)`
- `get_all_achievements(active_only=True)`, `get_user_achievements(user_id)`
- Internos: `_check_achievements` (por visited_node, archetype, chapter), `_grant_achievement`:
  - Crea UserStoryAchievement.
  - Si reward_besitos > 0: `besito_service.credit_besitos(..., source=TransactionSource.MISSION, ref=achievement.id)`.
  - (Package rewards se marcan pero entrega separada).

### Estadísticas y Utilidades
- `get_story_stats() -> dict` (total_nodes, total_chapters, total_users, completed_users, archetype_distribution, total_achievements).
- `update_node` etc. para admin.

**Patrón de servicio:** `__init__` crea BesitoService(self.db), `close()` solo si owns. No usa get_service internamente (dueño de sus interacciones besitos).

---

## Flujos Principales

### Flujo Usuario (interactivo)
1. Menú narrativa → si no started: "Comenzar la historia" (crea progress con starting_node) o "Descubrir arquetipo".
2. `start_story` / `continue_story` → `show_node(current_node_id)`.
3. `show_node`:
   - Obtiene node + choices.
   - `VIPService().is_user_vip(user_id)` → `story_service.can_access_node(..., is_vip)`.
   - Si denegado: mensaje con razón (VIP required, archetype required, costo besitos insuficiente).
   - Muestra título + content (con chapter), costo si aplica.
   - Si ENDING: botón "Ver mi arquetipo".
   - Si choices: botones con `StoryChoiceCallback(choice_id)` (muestra additional_cost si >0).
   - Si no choices y no ending: "Continuar".
4. Choice callback → `advance_to_node(user_id, next_node_id, choice_id, is_vip)` (en show_node posterior).
5. Quiz separado: "Descubrir mi arquetipo" → FSM answering (preguntas hardcoded del service) → `calculate_archetype_from_quiz` → assign + mostrar.
6. Logros: lista desbloqueados + rewards (besitos o paquete).

Progreso se actualiza automáticamente en advance (visited JSON, capítulo, arquetipo dominante al final o si no asignado).

### Flujo Admin (wizards FSM)
- Menú con stats (del service).
- Crear nodo: title → content → tipo (NARRATIVE/DECISION/ENDING/QUIZ) → capítulo → requisitos (arquetipo req, VIP req vía callbacks) → costo besitos → confirmar → create_node.
- Listar nodos → detail (toggle active, delete, add choices).
- Gestionar opciones: seleccionar nodo → crear choice (text, next_node, archetype_points, additional_cost).
- Gestionar arquetipos: crear/editar (tipo fijo del enum, name/desc/welcome).
- Gestionar logros: crear (name, reqs por node/archetype/chapter, reward_besitos o package).
- Stats detallados.

Todos los admin handlers usan `is_admin` + get_service(StoryService).

---

## Cómo se Otorgan / Gastan Besitos en Narrativa

**Gastos (débitos):**
- `advance_to_node` / `can_access_node`: si `node.cost_besitos > 0`, chequea balance y `debit_besitos(..., source=TransactionSource.PURCHASE, commit=False, ref=node.id)`.
- Razón: "Acceso a fragmento: {title}".
- Atomicidad explícita: debit sin commit, luego commit conjunto con progreso.

**Ingresos (créditos):**
- En `_grant_achievement` (llamado post-advance en _check_achievements): si `achievement.reward_besitos > 0`, `credit_besitos(..., source=TransactionSource.MISSION, description="Logro desbloqueado: {name}", ref=achievement.id)`.
- Logros se desbloquean por: completar nodo requerido (en visited), tener arquetipo requerido, alcanzar capítulo.
- (Achievements también pueden dar packages, pero besitos van directo a gamif vía BesitoService).

**Uso de BesitoService:** Instancia propia en __init__ del StoryService (no "local on-demand" como en otros dominios; narrative es consumidor/productor legítimo de besitos para su mecánica).

---

## Mapa de Narrativa (Flujos y Estructura)

```
Usuario
  │
  ├── Inicio / Quiz de Arquetipo (hardcoded en service)
  │   └─→ calculate_archetype_from_quiz(answers) → assign_archetype + puntos iniciales
  │
  ├── Progreso (UserStoryProgress)
  │   ├── current_node_id + visited_nodes (JSON)
  │   ├── 6 campos de puntos por arquetipo (acumulados por choices)
  │   └── dominant_archetype (calculado al final o al completar)
  │
  ├── Grafo de Historia
  │   StoryNode (capítulo/orden, tipo: NARRATIVE/DECISION/ENDING/QUIZ)
  │     ├── required_vip (gate)
  │     ├── required_archetype (gate)
  │     ├── cost_besitos (gate + debit)
  │     └── choices → StoryChoice (text, next_node, archetype_points, additional_cost)
  │
  ├── Avance
  │   show_node → can_access (VIPService.is_user_vip + story checks) 
  │     → advance_to_node (debit commit=False si costo + sumar puntos choice 
  │        + actualizar progreso/visited/chapter + commit atómico 
  │        + _check_achievements → _grant_achievement (credit besitos MISSION o package))
  │
  └── Logros y Fin
      Completar nodos/caps/arquetipos → desbloqueo + recompensa besitos
```

**Ciclos:** Decisiones suman puntos → arquetipo dominante → desbloquea nodos requeridos → logros → créditos besitos (vuelve a gamif) o packages. VIP gates vinculan a membresías (ver conexiones).

**Persistencia:** Todo en DB (progreso por usuario, visited como JSON para checks de logros).

---

## Cómo se Comunica con Gamificación

**Uso directo de Besitos (narrative como consumidor y productor limitado):**
- Débitos para acceso a nodos costosos (atomic con progreso vía commit=False).
- Créditos automáticos por logros desbloqueados (source=MISSION, para que se integren con historial/recompensas de gamif).
- En `_grant_achievement` se usa la instancia interna de BesitoService.

**EventBus (dirección gamificación → narrativa, best-effort):**
- Narrative **es el primer subscriptor** del evento `EVENT_BESITOS_AWARDED` (emitido por BesitoService.credit_besitos post-commit).
- Listener `on_besitos_awarded_from_gamification(payload)` vive en story_service.py (ownership del dominio narrativa).
- Comportamiento: puramente best-effort y observacional.
  - Loguea: `"narrative | besitos_awarded_received | user_id=... | amount=... | source=... | ref=..."`
  - **MUST NOT** llamar credit/debit besitos (evita loops/re-entrancy con `_grant_achievement` que ya otorga recompensas en besitos).
  - Futuro posible: lógica de progreso/hints por acumulación de besitos (usaría get_service si necesita sesión fresca).
- Registro explícito y central en `bot.py` (on_startup, después de scheduler).
- Errores del listener son tragados por el bus (gather return_exceptions); no afectan al emisor ni a otros listeners (rewards, broadcast, game, store).
- Ver services/event_bus.py (DESIRED CONTRACT) y services/gamification/CLAUDE.md (emisor).

**Otras interacciones:** 
- Logros de narrativa pueden entregar recompensas que alimentan de vuelta la economía de gamif (besitos via MISSION source).
- No hay mutación de besitos en el listener (contrato estricto).

---

## Cómo se Comunica con Administración de Canales

**Gate VIP (principal conexión, indirecta):**
- Muchos nodos tienen `required_vip=True`.
- En handlers (story_user_handlers): antes de mostrar o avanzar, se hace `VIPService().is_user_vip(user_id)`.
- Ese `is_vip` se pasa a `story_service.can_access_node(user_id, node_id, is_vip)`.
- Si el nodo lo requiere y no es VIP → deniega con `LucienVoice.story_fragment_vip_required()`.
- **No hay llamadas directas a ChannelService** dentro del módulo de narrativa.
- La membresía VIP (que habilita los nodos) se materializa como `Subscription` a un `Channel` de tipo VIP (ver módulo de administración de canales + VIPService.redeem).
- Canales VIP registrados/configurados (wait times, mensajes, approve) en el dominio de canales proveen el "acceso físico" + el flag is_vip que narrativa consume para gates de contenido narrativo.

**Otras notas:**
- Contenido narrativo VIP-only solo accesible si el usuario tiene suscripción activa a un canal VIP registrado.
- No hay broadcast/reacciones ni pending requests desde narrativa hacia canales.
- Free channels son irrelevantes para narrativa (solo VIP gates).

**Separación de dominios:** Narrative no gestiona canales ni suscripciones; solo verifica el estado VIP que proviene del ecosistema de canales/VIP (alimentado a su vez por recompensas de gamif/misiones).

---

## Reglas, Patrones y Gotchas

- **Handlers:** Siempre `with get_service(StoryService)` para lógica de dominio. VIPService separado solo para el flag is_vip en checks de acceso (no inyectado en service). is_admin en todos los admin entrypoints.
- **Atomicidad crítica:** Débito de besitos en advance_to_node usa `commit=False` + commit único con el update de progreso/puntos/visited. Tests verifican este flag.
- **EventBus contract (narrative ownership):** Listener debe ser no-mutante de besitos. Errores logueados y tragados.
- **Quiz hardcoded:** Lógica de preguntas/opciones/puntos vive dentro del servicio (no en DB). calculate_from_quiz es pura (dada lista de índices).
- **Arquetipo:** Se acumula por puntos de choices; se asigna automáticamente al completar (ENDING) o cuando se pide si aún no tiene. `get_dominant_archetype` en el modelo de progreso.
- **Logros:** Chequeo post-advance (por visited, archetype, chapter). Entrega de recompensa besitos es fire-and-forget (después del commit principal).
- **Acceso denegado:** Siempre retorna razón en voz de Lucien desde can_access_node (VIP, arquetipo, costo).
- **Persistencia de visitas:** visited_nodes como JSON array para checks de logros (sin normalizar a tabla separada).
- **Tests / Golds:** Cubiertos en patrones generales de atomicity cross (story debit commit=False + progreso), EventBus wiring, y cadenas besitos↔narrativa.
- **Antes de implementar:** Leer services/narrative/CLAUDE.md (EventBus + reglas), architecture.md, rules.md (≤50 LOC, logging), verificar quiz hardcoded y uso de commit=False en débitos.

**Fin del documento — solo módulo de narrativa.**

Construido con: grafo de nodos + puntos de arquetipo por elección + gates (VIP/arquetipo/costo) + progreso persistente + logros que cierran loop de recompensas (besitos vía gamif) + EventBus observacional ownership + verificación VIP vía servicio externo. Todo con atomicidad explícita donde besitos se cruzan con estado narrativo. Conexiones a canales puramente vía estado VIP (sin acoplamiento directo a ChannelService).