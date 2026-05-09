# Phase 16: Trivias Temáticas - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Extender el sistema de trivia existente (Fase 14 — Minijuegos) con soporte para categorías temáticas, un sistema de mazo de preguntas sin repetición, y recompensas por racha de respuestas correctas.

**Lo nuevo:**
- Categorías de preguntas como archivos JSON separados, activables por administración
- Mazo por usuario con draw sin repetición y reinicio diario
- Bonus de besitos por hitos de racha (3, 5, 7, 10)
- Activación/desactivación de categorías desde el panel de admin con interfaz visual

**Lo que NO cambia:**
- Las preguntas generales existentes (`preguntas.json`) continúan siendo el mazo por defecto
- Los límites diarios actuales se mantienen (Free=5, VIP=10)
- Trivia VIP (preguntas sobre Diana con 5 besitos) sigue funcionando igual
- La trivia temática NO es visible para usuarios — solo el admin sabe cuándo está activa

</domain>

<decisions>
## Implementation Decisions

### Modelo de Categorías
- **D-01:** Las categorías son archivos JSON separados, ej: `preguntas_halloween.json`, `preguntas_navidena.json`. El nombre del archivo es el identificador de la categoría.
- **D-02:** Las categorías son **invisibles para los usuarios** — son herramientas internas de administración para dinámicas y eventos especiales.
- **D-03:** `docs/preguntas.json` se mantiene intacto como el mazo "general" por defecto.

### Sistema de Mazo
- **D-04:** Draw sin repetición: cada usuario tiene su propio registro de preguntas respondidas por día. Una pregunta ya respondida no se vuelve a mostrar hasta el reinicio diario.
- **D-05:** El mazo se reinicia cada 24h (sigue el patrón de límites diarios existente).
- **D-06:** Cuando una categoría temática está activa, **reemplaza completamente** al mazo general (no se combinan). Solo una categoría activa a la vez.
- **D-07:** Por defecto (sin categoría activa), siempre se usa el mazo general de `preguntas.json`.
- **D-08:** El mazo es independiente de los límites diarios — solo controla que no se repitan preguntas dentro de la sesión diaria.

### Recompensas por Racha
- **D-09:** Besitos bonus al alcanzar hitos de racha (además del besito base por respuesta correcta):
  - Racha de 3: +2 besitos (normal) / +4 (VIP)
  - Racha de 5: +5 besitos (normal) / +10 (VIP)
  - Racha de 7: +10 besitos (normal) / +20 (VIP)
  - Racha de 10: +20 besitos (normal) / +40 (VIP)
- **D-10:** Los hitos son los mismos para trivia normal y VIP. VIP recibe el doble de bonus.
- **D-11:** La racha se reinicia al fallar una respuesta (mismo comportamiento actual).

### Integración con Trivia Existente
- **D-12:** Durante una dinámica temática, aparece un **botón especial visible** en el menú de juegos (ej: "🎃 Trivia de Halloween") con nombre personalizado. No reemplaza el botón de trivia general.
- **D-13:** La trivia temática tiene **límites diarios independientes** de la general. No consume los intentos de la trivia normal.
- **D-14:** El admin gestiona categorías desde el panel de administración existente con interfaz visual de botones inline. Opciones: activar categoría, desactivar, programar por fecha, ver estado actual.
- **D-15:** Las preguntas las prepara Diana/equipo externamente como archivos JSON. El admin no crea preguntas desde el bot.

### Claude's Discretion
- Los montos exactos de bonus de racha pueden ajustarse por balance si se considera necesario durante implementación/pruebas.
- El formato específico del botón temático en el menú de juegos (nombre, ícono) queda a discreción de implementación.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Trivia existente (Fase 14 base)
- `services/game_service.py` — GameService con trivia actual, límites diarios, rachas, carga de preguntas
- `handlers/game_user_handlers.py` — Handlers de trivia existentes: game_trivia, trivia_answer, trivia_vip
- `keyboards/inline_keyboards.py` — Teclados inline: trivia_keyboard, trivia_vip_keyboard, game_menu_keyboard

### Pools de preguntas existentes
- `docs/preguntas.json` — ~80 preguntas generales (mazo por defecto)
- `docs/preguntas_vip.json` — ~48 preguntas sobre Diana (trivia VIP)

### Modelos
- `models/models.py` — GameRecord, TransactionSource (para registrar jugadas de trivia temática)

### Arquitectura y reglas
- `CLAUDE.md` — Reglas de proyecto, layers handlers/services/models
- `@architecture.md` — Separación de capas
- `@rules.md` — Límite 50 líneas, naming, logging
- `services/CLAUDE.md` — Reglas de services
- `handlers/CLAUDE.md` — Reglas de handlers

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GameService` — Servicio existente con métodos de trivia: `load_trivia_questions()`, `get_random_question()`, `check_trivia_answer()`, `play_trivia()`. El nuevo sistema debe extenderlo o ser un service hermano.
- `GameRecord` — Modelo existente para registrar jugadas. Usar mismo modelo con un nuevo `game_type` para trivia temática.
- `game_menu_keyboard` — Teclado del menú de juegos. Habrá que extenderlo para mostrar botón de categoría activa condicionalmente.
- Sistema de streak existente: `_get_trivia_streak()`, `_get_streak_message()` — reutilizar lógica para calcular racha y milestones.

### Established Patterns
- Las preguntas se cargan desde archivos JSON en `docs/` usando `Path("docs/preguntas.json")`
- Los límites diarios se verifican contando `GameRecord` del día actual
- Servicios se usan via `get_service(GameService)` context manager
- Mensajes de LucienVoice usan `@staticmethod`, parse_mode="HTML"

### Integration Points
- Menú de juegos (`game_user_handlers.py::game_menu`) — donde aparecerá el botón dinámico de categoría activa
- Panel admin existente — nuevo botón "🎯 Mazos de Trivia" para gestión de categorías
- Scheduler (APScheduler) — para activación/desactivación automática por fecha programada
- `GameRecord` con nuevo `game_type` (ej: `'trivia_tematica'`) para límites independientes

</code_context>

<specifics>
## Specific Ideas

- Cuando una categoría está activa, el menú de juegos muestra un botón extra con nombre personalizado (ej: "🎃 Trivia de Halloween", "❄️ Trivia Navideña")
- El admin debe poder ver: qué categoría está activa, cuántas preguntas tiene, y cuándo termina si está programada
- La activación programada usaría el scheduler existente (APScheduler con SQLAlchemyJobStore)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---
*Phase: 16-Trivias Temáticas*
*Context gathered: 2026-05-09*
