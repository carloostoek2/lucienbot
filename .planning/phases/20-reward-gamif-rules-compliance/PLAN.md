# PLAN: Reward handlers 1-service compliance + pure helpers extraction (Item 2)

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-06-07  
**Focus:** Tight, conservative remediation of two arch-enforcer notes: (a) reward_user_handlers.py (show_available_rewards + reward_detail) must call **exactly 1 service** using the modern `get_service` + relationship pattern (as proven in mission_user_handlers); (b) extract pure helper(s) from `handle_reaction` (gamification_user_handlers) **and** ensure reward-side functions respect ≤50 LOC rule. Minimal support change only in reward_service.py (promote get_reward_emoji to top-level pure function with backward-compatible delegate).  
**Input principal (source of truth):** Impact-analyzer report for Item 2 (executive summary + detailed impact map with exact files, low risks, tight scope recommendations, critical tests list, preferred design: "usar relationship + pure emoji + get_service(MissionService) en los handlers de reward; extract pure helper en reaction") + handoff notes in `.planning/phases/19-eventbus-poc/19-eventbus-poc-SUMMARY.md` (section "Preparación para Item 2") + explicit arch-enforcer NOTES in `tests/handlers/test_reward_user_handlers.py` + current source (reward_user_handlers, gamification_user_handlers handle_reaction at 52 LOC, reward_service get_reward_emoji, mission_user_handlers pattern, models relationships, get_service in services/__init__.py) + CLAUDE.md / architecture.md / rules.md / handlers/CLAUDE.md.  
**GSD enforcement:** Executor MUST prefix **every** modification / pre-gate / verification with a GSD log append (timestamp | PHASE | description) to the Item 2 log file (see Instructions section). Use the same discipline as gsd-eventbus-poc-item1.log and gsd-mw-hardening.

---

## 1. Alcance preciso (In / Out explícito)

### En esta entrega (scope "tight" per analyzer + user spec):
- **Soporte mínimo en `services/reward_service.py`**: Promover `get_reward_emoji` a función pura top-level (module-level `def get_reward_emoji(reward: Reward) -> tuple[str, str]`). Mantener método de instancia como delegate backward-compatible (para que cualquier caller existente de `reward_svc.get_reward_emoji(...)` siga funcionando sin cambios).
- **Refactor de handlers (exactly 1 service)**:
  - `handlers/reward_user_handlers.py`: `show_available_rewards` y `reward_detail` (y el helper interno `_build_rewards_buttons` usado por ellos) deben llamar **exactamente 1 service** vía `with get_service(MissionService) as ...` (patrón idéntico a mission_user_handlers). 
    - Usar **relationship** (`mission.reward`) para acceso a Reward en `reward_detail` (en lugar de `reward_service.get_reward(mission.reward_id)`).
    - Usar la **pure emoji function** importada (`from services.reward_service import get_reward_emoji`) para formateo (en lugar de `RewardService().get_reward_emoji` o `reward_service.get...`).
  - Remover **todas** las instanciaciones directas / imports de `RewardService` del módulo de handlers (y del código de las dos funciones + helper).
  - Usar context manager → eliminar closes manuales de servicios.
- **Extracción de helpers puros para ≤50 LOC**:
  - En `handlers/gamification_user_handlers.py`: Extraer helper(s) puro(s) del cuerpo de `handle_reaction` (actualmente 52 líneas) de forma que la función `handle_reaction` quede ≤50 líneas fuente. El helper principal recomendado: `calculate_emoji_counts_from_reactions(reactions: list) -> dict[int, int]` (puro, opera solo sobre datos de reacciones; sin side-effects, sin DB, sin async). Opcionalmente un segundo helper pequeño y puro para construcción de lista de emojis dado un lookup (para mantener el handler limpio). El comportamiento de refresh de UI (cálculo de emoji_counts + emojis + llamada a `reactions_keyboard_with_counts` + `update_reaction_message`) debe ser **idéntico**.
  - En el lado de reward: revisar helpers existentes (`_build_rewards_buttons`, `_build_*`) durante la edición; si alguna excede o roza el límite tras cambios, extraer sub-helper puro mínimo (pero scope tight prioriza no hacerlo si no es necesario para pasar ≤50).
- **Actualización de tests de handlers**:
  - Port completo de `tests/handlers/test_reward_user_handlers.py` al nuevo patrón: parches sobre `get_service` (como en `test_mission_user_handlers.py`), mocks de contexto `__enter__`/`__exit__`, configuración de mocks para que la pure `get_reward_emoji` funcione (setear `.reward_type`, `.besito_amount` etc. en los MagicMock de reward), uso de `mission.reward = mock_reward` para el acceso por relationship, remoción de parches y asserts sobre RewardService, actualización de tests de close a patrón de context manager, remoción/actualización de los NOTE (arch-enforcer visibility) en los docstrings de clases.
  - Adición de **nuevos tests unitarios para el/los pure helper(s) de reactions** (en `tests/handlers/test_gamification_user_handlers.py`, clase nueva o extensión de TestHandleReaction; casos: vacío, conteos agregados, reacciones sin reaction_emoji, etc.). Los tests del helper deben poder correr sin parches pesados de servicio (puro = fácil de testear).
  - Re-ejecución explícita de **reaction chains** (TestHandleReaction + integrations: TestFullReactionChain, TestReactionMissionFlow, TestReactionLimit, TestCrossServiceAtomicity reaction paths, etc.) para confirmar que el refresh de UI sigue produciendo exactamente el mismo new_markup y llamadas.
- **Comportamiento observable idéntico**: La lista/detalle de rewards produce el mismo texto, botones y emojis que antes. El refresh de conteos de reacciones en broadcasts produce el mismo markup y se llama de la misma forma.
- **Cumplimiento de reglas**: Handlers llaman exactly 1 service; funciones ≤50 LOC; logging en formato "módulo | acción | user_id | resultado" para acciones importantes (agregar/actualizar durante las ediciones donde falte); get_service context manager preferido; sin lógica de negocio en handlers; sin acceso DB fuera de models.
- Artefacto de planificación: este `PLAN.md` + entradas GSD en log de Item 2.

### Fuera explícitamente (nada de scope creep, per "tight" recs + "nada más"):
- **NO** tocar `services/mission_service.py` (ni su `get_available_rewards_for_user`, aunque internamente use RewardService para poblar los dicts; eso es responsabilidad del servicio, el handler ahora llama solo a MissionService).
- **NO** otros handlers, ni reward_admin_handlers, ni ningún otro archivo que use RewardService.get_reward_emoji (el delegate asegura compatibilidad; no los editamos).
- **NO** cambios en modelos, relaciones (la relationship `Mission.reward` ya existe y se usa en mission_detail), ni Alembic.
- **NO** cambios en `services/__init__.py` (no es necesario exportar la pura; import directo del submódulo es el patrón usado en mission_user_handlers).
- **NO** edición de docs (CLAUDEs, decisions.md, AGENTS, etc.), ROADMAP, ni SUMMARY de esta fase (eso lo haría un paso posterior si se requiere; scope se limita a código + tests de handlers + este PLAN + log GSD).
- **NO** nuevos servicios, ni refactor de get_available_rewards_for_user para usar relationship internamente, ni cambios en entrega de rewards.
- **NO** tocar middlewares, bot.py, keyboards, ni nada fuera de los 5 archivos listados (2 handlers + 1 service + 2 test handlers).
- **NO** agregar tests de service para el emoji puro (solo los de handler + nuevos para el reaction helper).
- **NO** modificar flujos de claim o backpack que también tocan rewards.

**Archivos que se modificarán (exactos, por orden de fases):**
1. `services/reward_service.py` (F1)
2. `handlers/reward_user_handlers.py` (F2)
3. `handlers/gamification_user_handlers.py` (F3)
4. `tests/handlers/test_reward_user_handlers.py` (F4)
5. `tests/handlers/test_gamification_user_handlers.py` (F5, adición de tests del helper)

---

## 2. Fases ordenadas (5 fases pequeñas, secuenciales, con gates)

### Fase 1: Soporte mínimo en RewardService (promover get_reward_emoji a pura top-level + delegate)

**Objective:** Hacer que la lógica de emoji sea una función pura importable sin instanciar servicio, mientras se preserva 100% compatibilidad backward para cualquier código existente que llame `svc.get_reward_emoji(r)`. Esto habilita a los handlers de reward a no depender de RewardService en absoluto.

**DoD checklist (marcar al completar):**
- [ ] Función pura `get_reward_emoji(reward: Reward) -> tuple[str, str]` definida a nivel de módulo en `services/reward_service.py` (lógica idéntica al método actual; sin self, sin side-effects).
- [ ] Método de instancia `def get_reward_emoji(self, reward: Reward)` ahora es un delegate de 1 línea que llama a la pura (sin duplicar lógica).
- [ ] Imports necesarios ya presentes (Reward, RewardType desde models.models; logging no requerido en pura).
- [ ] Sin cambios de comportamiento: para un Reward dado, el retorno (emoji, gives) es idéntico antes/después.
- [ ] Ruff limpio en el archivo (`./venv/bin/python -m ruff check services/reward_service.py` y format si aplica).
- [ ] Smoke de import + llamada básica (python -c o equivalente en log) pasa sin errores.
- [ ] GSD pre-edit + pre-gate entries en el log de Item 2.
- [ ] Safe point alcanzado (ver abajo).

**Archivos:** `services/reward_service.py`

**Cambios clave (bullets accionables, orden sugerido):**
- Localizar el método actual (alrededor de líneas 108-116).
- Insertar **antes** de la clase (o justo después de los imports y logger, antes de `class RewardService:`) la definición:
  ```python
  def get_reward_emoji(reward: Reward) -> tuple[str, str]:
      """Retorna (emoji, description) según tipo de recompensa. Función pura (sin estado ni side-effects)."""
      if reward.reward_type == RewardType.BESITOS:
          return "💋", f"{reward.besito_amount} besitos"
      elif reward.reward_type == RewardType.PACKAGE:
          return "📦", f"Paquete exclusivo: {reward.name}"
      elif reward.reward_type == RewardType.VIP_ACCESS:
          return "👑", f"Acceso VIP: {reward.name}"
      return "🎁", ""
  ```
- Reemplazar el cuerpo del método dentro de la clase por:
  ```python
  def get_reward_emoji(self, reward: Reward) -> tuple[str, str]:
      """Retorna (emoji, description) según tipo de recompensa. Delegate a la función pura top-level para mantener compatibilidad."""
      return get_reward_emoji(reward)
  ```
- (Opcional pero recomendado para claridad) Añadir comentario arriba del delegate: "# Backward-compatible delegate added for Item 2 (arch-enforcer 1-service rule for reward handlers)."
- Pre-log GSD antes del edit.
- Post-edit: ruff check + format apply si necesario + smoke import.
- Confirmar que la lógica de los 4 casos (besitos/package/vip/default) es idéntica.

**Tests que deben pasar antes de avanzar (gates de F1):**
- Ruff en el archivo: exit 0.
- Smoke básico (no debe romper imports de reward_service en ningún lado): `./venv/bin/python -c "from services.reward_service import RewardService, get_reward_emoji; print('import ok'); print(get_reward_emoji)"` (o con MagicMock simple para ejecución).
- Cualquier test existente que ejercite indirectamente el método vía mocks (los de reward handlers) seguirán pasando en F4 cuando se porten; para F1 basta que no haya syntax/import breakage. Si hay tests unit de reward_service que llamen al método, deben seguir verdes (correr `pytest tests/ -k "reward" -q --tb=line -p no:cov --override-ini="addopts="` es seguro y recomendado, pero no bloqueante si solo mocks).
- Grep para confirmar la pura existe y el delegate llama: `grep -n "def get_reward_emoji" services/reward_service.py` (debe mostrar 2: la pura y el método).

**Riesgos + mitigaciones:**
- Riesgo bajo: callers existentes de la API de instancia (RewardService().get_reward_emoji) se rompen → Mitigación: el delegate preserva firma y comportamiento exacto. (El analyzer reportó riesgos bajos.)
- Riesgo: duplicación accidental de lógica → Mitigación: el cuerpo solo vive en la pura; delegate es 1-línea. Revisión visual en edit.
- Ningún test directo del emoji method sin mocks actualmente en scope (los tests de handlers lo mockeaban); el port en F4 validará la pura indirectamente.

**Safe point:** Después de ruff + smoke verde + GSD log entry de "F1 safe point". El archivo reward_service.py tiene la pura + delegate; ningún otro archivo modificado aún. Reversible con 1-line revert del delegate si algo falla después.

---

### Fase 2: Refactor handlers de reward a exactly-1-service (get_service + relationship + pure emoji)

**Objective:** Hacer que `show_available_rewards` y `reward_detail` cumplan la regla "exactly 1 service" (MissionService vía get_service context manager). Eliminar toda dependencia de RewardService del handler. Usar `mission.reward` (relationship ya existente y probada en mission_detail) + la función pura de emoji. Mantener texto, botones y comportamiento 100% idénticos.

**DoD checklist:**
- [ ] Imports actualizados: `from services import get_service`, `from services.mission_service import MissionService`, `from services.reward_service import get_reward_emoji`; **0** menciones a `RewardService` (ni import ni instanciación) en `handlers/reward_user_handlers.py`.
- [ ] `show_available_rewards` usa `with get_service(MissionService) as mission_service:` (sin instanciación directa, sin closes manuales de dos servicios).
- [ ] `_build_rewards_buttons` usa `get_reward_emoji(reward)` (pura) en lugar de `RewardService().get...`.
- [ ] `reward_detail` usa `with get_service(...)`, obtiene reward vía `mission.reward` (relationship), usa `get_reward_emoji` pura; chequeo `if not mission or not mission.reward:` (o equivalente que preserve semántica de "no encontrada").
- [ ] Funciones resultantes + helpers ≤50 LOC (verificación post-edit).
- [ ] Logging: agregar/actualizar logs de acciones importantes en formato "reward_user_handlers | show_available_rewards | user_id=... | count=..." y similar para reward_detail (si no existían; el mw ya cubre idempotencia).
- [ ] Comportamiento idéntico: mismos textos en _build_*, mismos botones (con status_emoji + reward_emoji + name), mismos callbacks.
- [ ] GSD pre + gates verdes antes de marcar F2 done.
- [ ] Safe point.

**Archivos:** `handlers/reward_user_handlers.py`

**Cambios clave (bullets accionables):**
- Reemplazar los imports de services al inicio (líneas ~14-15):
  ```python
  from services import get_service
  from services.mission_service import MissionService
  from services.reward_service import get_reward_emoji
  # (eliminar: from services.reward_service import RewardService)
  ```
- Refactor `show_available_rewards` (líneas ~72-99):
  - user_id = ...
  - `with get_service(MissionService) as mission_service:`
    - rewards_data = mission_service.get_available_rewards_for_user(user_id)
    - if not rewards_data: ... (edit_text + _safe_answer)
    - text = _build...
    - buttons = _build_rewards_buttons(rewards_data)
    - ... append volver, keyboard, edit_text, _safe_answer
  - (eliminar las dos líneas de instanciación + finally con dos closes)
- Actualizar `_build_rewards_buttons` (línea ~166):
  - `reward_emoji, _ = get_reward_emoji(reward)`  # antes: RewardService().get...
- Refactor `reward_detail` (líneas ~103-158):
  - `with get_service(MissionService) as mission_service:`
    - mission = mission_service.get_mission(mission_id)
    - if not mission or not mission.reward:
        _safe_answer_alert(..., "Recompensa no encontrada")
        return
    - # reward = reward_service.get_reward(...)  ← ELIMINAR
    - progress = mission_service.get_or_create_progress(user_id, mission_id)
    - bar, percentage = ...
    - reward_emoji, reward_gives = get_reward_emoji(mission.reward)  # o asignar reward = mission.reward primero
    - ... construir status_text, text = _build..., keyboard con MissionDetailCallback y volver a rewards_list, edit_text, _safe_answer
  - (eliminar instanciación reward_service + finally closes)
- Agregar logging estándar (ejemplos; ubicar en puntos clave dentro del with, después de obtener datos exitosos):
  - `logger.info(f"reward_user_handlers | show_available_rewards | user_id={user_id} | count={len(rewards_data)}")`
  - Similar para reward_detail: `logger.info(f"reward_user_handlers | reward_detail | user_id={user_id} | mission_id={mission_id} | completed={progress.is_completed}")`
- Verificar que los helpers puros existentes (_build_reward_detail_text, _build_progress_bar, _build_rewards_buttons, _safe_*) siguen <50 y preferentemente no introducen lógica de negocio.
- Post-edit: ruff check + apply format; conteo LOC de las dos funciones principales (deben ser cortas).
- Grep de verificación: `grep -n "RewardService" handlers/reward_user_handlers.py` → 0 resultados (o solo en comentarios históricos si se dejan para trazabilidad, pero preferible 0).

**Tests que deben pasar antes de avanzar:**
- Ruff en handlers/reward_user_handlers.py (y su test, aunque el test se actualiza en F4).
- Smoke de import del handler: `./venv/bin/python -c "from handlers.reward_user_handlers import show_available_rewards, reward_detail, get_reward_emoji; print('ok')"` (get_reward_emoji no se exporta del handler, pero el import del módulo debe resolver la pura).
- (Los tests funcionales del handler se gatean en F4 después del port; aquí basta que el módulo cargue y las funciones sean callables sin errores de nombre.)

**Riesgos + mitigaciones:**
- Riesgo: `mission.reward` lazy-load falla o devuelve None inesperadamente en runtime (mientras que get_reward anterior filtraba) → Mitigación: relationship ya probada en mission_user_handlers::mission_detail (línea ~106: `if mission.reward:`); el get_mission devuelve instancia attached a la sesión del service; para casos sin reward_id ya se short-circuitaba. En F4 los tests cubrirán el path "without reward" seteando explícitamente `.reward = None`.
- Riesgo: comportamiento de "recompensa inactiva" difiere (el list filtra active adentro de mission_svc; detail no lo hacía) → Mitigación: mantener exactamente la misma condición de guard que antes (`if not mission or not mission.reward`); no agregar chequeos de is_active en el handler (eso sería lógica extra). Scope tight.
- Riesgo: logging nuevo introduce ruido o formato inconsistente → Mitigación: seguir exactamente el patrón de otros handlers/services ("módulo | acción | user_id= | resultado"); usar el mismo logger del módulo.
- Bajo: _build_rewards_buttons ahora llama pura síncrona (antes instanciaba servicio innecesariamente) → mejora.

**Safe point:** Post-ruff + grep "RewardService" = 0 en el handler + GSD entry "F2 safe point - reward handlers now 1-service via MissionService + pure emoji + rel". El handler recompila y las dos rutas (list vacía, list con items, detail con/sin reward) son sintácticamente correctas. Reversible editando solo este archivo.

---

### Fase 3: Extraer helpers puros en handle_reaction (gamification) + ≤50 LOC + logging compliant + UI idéntica

**Objective:** Reducir `handle_reaction` de 52 líneas a ≤50 extrayendo helpers puros para la lógica de conteo y construcción de datos de emojis (la parte "UI refresh data prep"). Preservar exactamente el mismo comportamiento de actualización de markup de reacciones. Añadir/estandarizar logging.

**DoD checklist:**
- [ ] Helper(s) puro(s) definidos en `handlers/gamification_user_handlers.py` (al menos `calculate_emoji_counts_from_reactions(reactions: list) -> dict[int, int]`; idealmente también uno para build de emojis list si ayuda al conteo LOC y es puro dado lookup).
- [ ] `handle_reaction` fuente ≤50 líneas (verificado con conteo post-extracción; usar python inspect o wc en la def).
- [ ] El cálculo de `emoji_counts` y `emojis` + la decisión `if emojis: new_markup = reactions_keyboard_with_counts(...)` + await update_reaction_message producen **exactamente** los mismos valores y llamadas que antes de la extracción.
- [ ] Logging actualizado en la línea de "Reaction processed" (o añadida) al formato estándar: `f"gamification_user_handlers | handle_reaction | user_id={user.id} | broadcast_id={broadcast_id} | emoji={emoji_id} | besitos={besitos}"`.
- [ ] Helpers puros: sin imports de DB/session, sin side effects (el de counts es 100% puro sobre datos; el de build_emojis acepta callable de lookup pero no hace IO por sí mismo).
- [ ] Ruff limpio en el archivo.
- [ ] GSD pre + gates (incluyendo al menos un test de reacción existente que ejercite el refresh path).
- [ ] Safe point.

**Archivos:** `handlers/gamification_user_handlers.py`

**Cambios clave (bullets accionables):**
- Añadir los helpers cerca del bloque de reacciones (después de los otros helpers o antes de la sección # REACCIONES), con nombres que sigan la convención (verbo + contexto + resultado):
  ```python
  def calculate_emoji_counts_from_reactions(reactions: list) -> dict[int, int]:
      """Calcula el mapa de conteos de emojis a partir de reacciones registradas. Función pura."""
      emoji_counts: dict[int, int] = {}
      for r in reactions:
          if r.reaction_emoji:
              emoji_id_val = r.reaction_emoji.id
              emoji_counts[emoji_id_val] = emoji_counts.get(emoji_id_val, 0) + 1
      return emoji_counts
  ```
  (Opcional, si ayuda al LOC y se considera "puro helper"):
  ```python
  def build_emojis_list(selected_emoji_ids: list[int], get_reaction_emoji) -> list[tuple[int, str]]:
      """Construye lista (emoji_id, emoji_str) usando el lookup provisto (puro respecto al mapping)."""
      emojis: list[tuple[int, str]] = []
      for emoji_id in selected_emoji_ids:
          emoji_obj = get_reaction_emoji(emoji_id)
          if emoji_obj:
              emojis.append((emoji_id, emoji_obj.emoji))
      return emojis
  ```
- En `handle_reaction`, dentro del `if broadcast and broadcast.has_reactions:` (después de obtener selected y reactions):
  ```python
  emoji_counts = calculate_emoji_counts_from_reactions(reactions)
  emojis = build_emojis_list(selected_emoji_ids, broadcast_service.get_reaction_emoji) if 'build...' else [el loop original simplificado]
  if emojis:
      new_markup = ...
      await ...
  ```
  (Si solo extraes el de counts, el loop de emojis puede quedar pero más corto; el conteo de líneas total de la función debe bajar a <=50.)
- Reemplazar/actualizar el logger.info existente por el formato estándar.
- Post-extracción: medir LOC de la función:
  - Ejemplo: `python -c 'import inspect; from handlers.gamification_user_handlers import handle_reaction; src=inspect.getsourcelines(handle_reaction)[0]; print(len(src))'`
  - Debe ser <=50. Si queda 51-52 por docstring o comentarios, recortar docstring del helper o comentarios inline (mantener contrato) siguiendo precedente de F2 en eventbus-poc (LOC trim de credit_besitos).
- Ruff + format.
- Confirmar que tests de reacción que ejercitan el update path (test_updates_reaction_counts en el handler test) siguen esperando las mismas llamadas (el helper no cambia el contrato observable del handler).

**Tests que deben pasar antes de avanzar:**
- Ruff en gamification_user_handlers.py.
- Al menos 1 test existente del path de refresh: e.g. `pytest tests/handlers/test_gamification_user_handlers.py::TestHandleReaction::test_updates_reaction_counts -q --tb=line -p no:cov --override-ini="addopts="` (pasa con el comportamiento idéntico).
- Conteo LOC <=50 en handle_reaction.
- Grep o inspección: la lógica de conteo ya no está inline (o está delegada al helper).

**Riesgos + mitigaciones:**
- Riesgo: helper "puro" accidentalmente captura estado o hace que el refresh difiera (p.ej. orden de emojis) → Mitigación: los helpers replican exactamente los loops originales; tests de reacción re-ejecutados en F5 validarán el markup resultante (aunque los tests actuales mockean get_reaction_emoji y verifican que update fue llamado, no el contenido exacto del markup; para "idéntico" el executor puede agregar assert temporal o inspeccionar new_markup en un test, pero scope tight → basta con re-run de chains que ejercitan el código real).
- Riesgo: LOC sigue >50 por boilerplate del with/try/finally + logs → Mitigación: la extracción del bloque de 8-10 líneas de conteo + posible build reduce lo suficiente (de 52 a ~40-45 estimado); trim de comentarios/docstrings como último recurso (precedente establecido).
- Riesgo medio-bajo: nuevos helpers sin tests hasta F5 → Mitigación: F3 solo requiere que el handler refactorizado no rompa los tests existentes del handler; los tests del helper son gate de F5.

**Safe point:** Post-ruff + LOC<=50 verificado + GSD "F3 safe point - handle_reaction <=50 via pure helpers; UI refresh behavior preserved". El archivo gamification compila; el test de updates_reaction_counts sigue pasando (demuestra que el path de refresh no se rompió).

---

### Fase 4: Port de tests de reward_user_handlers al patrón 1-service + get_service + cleanup de notas arch-enforcer

**Objective:** Actualizar `test_reward_user_handlers.py` para que los tests reflejen (y protejan) el nuevo diseño "exactly 1 service". Remover la necesidad de mockear RewardService; portar a parches de get_service + context; configurar mocks para que la pure emoji funcione; actualizar docstrings/NOTEs; hacer que todos los tests pasen con comportamiento idéntico.

**DoD checklist:**
- [ ] 0 parches de `RewardService` en el archivo de tests (ni @patch ni referencias directas en setups/asserts para las funciones bajo test).
- [ ] Todos los tests usan `@patch("handlers.reward_user_handlers.get_service")` + `mock_get_service.return_value.__enter__.return_value = mock_instance`.
- [ ] Setups configuran `mock_instance.get_available_rewards_for_user`, `get_mission`, `get_or_create_progress` según corresponda.
- [ ] Para paths de detail: `mock_mission.reward = mock_reward` (y `mock_mission.reward_id` puede mantenerse para compatibilidad de otros asserts si los hay, pero no se usa para fetch).
- [ ] Para que `get_reward_emoji` (pura, real) retorne valores útiles: se setean attrs en los mock_reward (`.reward_type = RewardType.XXX`, `.besito_amount`, `.name` etc.). Import de RewardType en el test si se usa.
- [ ] Tests de close actualizados a patrón de context (assert en `__exit__` o en el mock_instance.close si el context lo propaga; ver precedente en test_mission_user_handlers).
- [ ] Removidas o reescritas las secciones NOTE (arch-enforcer visibility) y comentarios que decían "orchestrates two services", "pre-existing 2-svc", "protects against claims of '1 service pure'".
- [ ] Todos los asserts de texto, llamadas a edit_text/answer, y parámetros de servicio (user_id, mission_id) se mantienen y pasan.
- [ ] Ruff limpio en el test.
- [ ] GSD pre + gate: la suite completa de este archivo pasa verde.
- [ ] Safe point.

**Archivos:** `tests/handlers/test_reward_user_handlers.py`

**Cambios clave (bullets accionables, por clase):**
- Actualizar docstrings de `TestShowAvailableRewards` y `TestRewardDetail`: reemplazar los NOTE de arch-enforcer por algo como: "Tests ported to 1-service pattern (get_service + MissionService only) + pure formatting via get_reward_emoji. Arch-enforcer note addressed."
- En cada test de TestShowAvailableRewards:
  - Cambiar decoradores a solo `@patch("handlers.reward_user_handlers.get_service")`
  - Dentro: 
    ```python
    mock_instance = MagicMock()
    mock_get_service.return_value.__enter__.return_value = mock_instance
    mock_mission = MagicMock(id=1, name=..., )
    mock_reward = MagicMock(name="Test Reward")
    # Configurar para pure get_reward_emoji (usado en _build_rewards_buttons)
    mock_reward.reward_type = RewardType.BESITOS   # o PACKAGE etc. según test
    mock_reward.besito_amount = 10
    mock_instance.get_available_rewards_for_user.return_value = [{"mission": mock_mission, "reward": mock_reward, "progress": None}]
    ...
    await ...
    # asserts en edit_text, etc.
    # Remover: mock_reward_svc.return_value.get_reward_emoji.assert_called()
    ```
  - Para test_closes... : renombrar o reimplementar como test de context manager (similar a test_closes_service_via_context_manager en mission tests: assert __exit__ called).
- En TestRewardDetail (los ~10 tests):
  - Mismo patrón de patch get_service.
  - Para tests que antes hacían `mock_reward_svc.return_value.get_reward.return_value = mock_reward` y `get_reward_emoji=...`:
    - Ahora: `mock_mission = MagicMock(...) ; mock_mission.reward_id = 5 ; mock_reward = MagicMock(...) ; mock_mission.reward = mock_reward`
    - Setear en mock_reward los campos necesarios para get_reward_emoji + para que el texto incluya name/desc (ya lo hacen la mayoría).
    - Para el test "mission_without_reward": `mock_mission.reward_id = None ; mock_mission.reward = None`
    - Remover todos los `mock_reward_svc.return_value.get_reward.assert...`, `get_reward_emoji.assert`, y los closes de reward_svc.
  - Actualizar `test_calls_service_with_correct_params`: asserts solo sobre los métodos de mission (get_mission, get_or_create_progress); ya no hay get_reward en reward svc.
  - En setups de progress/completed: siguen iguales.
- Añadir al top del test (si no está): `from models.models import RewardType` para los setups de .reward_type (o usar strings si el pure compara con .value, pero del código del pure es Enum directo: `== RewardType.BESITOS`).
- Mantener el pytestmark y la estructura de clases.
- Post-port: correr la suite completa del archivo; todos deben pasar con textos idénticos.

**Tests que deben pasar antes de avanzar:**
- `./venv/bin/python -m pytest tests/handlers/test_reward_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` → todos verdes (actualmente ~14 tests entre las dos clases).
- Ruff en el test file.
- Grep post: `grep -n "RewardService" tests/handlers/test_reward_user_handlers.py | grep -v "NOTE\|arch-enforcer\|pre-existing"` → preferiblemente 0 en código activo.

**Riesgos + mitigaciones:**
- Riesgo: tests que confiaban en el mock de get_reward_emoji ahora ejecutan la real y fallan por attrs faltantes en MagicMock → Mitigación: configurar explícitamente `.reward_type` y campos dependientes (besito_amount / name) en cada setup que llega a _build o detail text. 5-10 minutos de setup por test.
- Riesgo: el test "without reward" falla porque MagicMock.reward es truthy por defecto → Mitigación: setear explícitamente `.reward = None` en ese test (documentado en cambios).
- Riesgo: asserts de closes de "ambos" fallan → Mitigación: reescribir a asserts de context/__exit__ o single close; alinear con patrón mission tests.
- Bajo: RewardType import → si choca, usar el enum value string y ajustar, pero el pure hace `== RewardType.BESITOS` (Enum), así que hay que usar la instancia del enum.

**Safe point:** Suite de reward_user_handlers verde post-port + ruff + GSD "F4 safe point - reward handler tests ported to 1-service + pure emoji; arch-enforcer notes cleaned". Confirma que el comportamiento de UI de rewards list/detail es idéntico.

---

### Fase 5: Nuevos tests para pure helper de reactions + re-run de reaction chains + gates targeted + verificación final

**Objective:** Añadir cobertura explícita del helper puro extraído (para que test-guardian tenga algo que correr en el futuro). Re-ejecutar las cadenas de reacción completas para confirmar zero regression en el refresh de UI. Gates finales de ruff + pytest targeted + confirmación de reglas (1 service, LOC, logging). Self-check y safe point final del Item.

**DoD checklist:**
- [ ] Nuevos tests para el helper (al menos 4-5 casos: empty, single, aggregate, ignore missing reaction_emoji, tipo de retorno) en `tests/handlers/test_gamification_user_handlers.py`. Los tests importan/ejecutan la función real (puro = sin mocks de servicio necesarios para el helper mismo).
- [ ] Re-runs de:
  - tests de handler de reacción (TestHandleReaction completo).
  - reaction chains de integración (TestFullReactionChain, TestReactionMissionFlow, TestReactionLimit, paths en TestCrossServiceAtomicity, TestInvariants si aplican, etc.).
  - (Opcional pero recomendado) el combinado que el handoff de Item 1 ya documentó, filtrando por reaction/gamif.
- [ ] Ruff limpio en todos los archivos tocados en el Item (service + 2 handlers + 2 tests).
- [ ] Verificación de reglas: 
  - `grep -n "RewardService" handlers/reward_user_handlers.py` → 0 (activo).
  - `python -c 'import inspect; from handlers.gamification_user_handlers import handle_reaction; print("handle_reaction LOC:", len(inspect.getsourcelines(handle_reaction)[0]))'` → <=50.
  - Logging en formato estándar presente en las funciones editadas (spot check).
- [ ] GSD entries completas para F5 + log final de Item con self-check PASSED + handoff notes (tests críticos a re-correr en el futuro para estos helpers/handlers).
- [ ] Safe point final + criterio de éxito del plan.

**Archivos:** `tests/handlers/test_gamification_user_handlers.py` (solo adición de tests; no se tocan los tests existentes de handle_reaction)

**Cambios clave:**
- Añadir al final del archivo (después de la última clase) o dentro de una extensión de TestHandleReaction:
  ```python
  class TestCalculateEmojiCountsFromReactions:
      """Tests para el helper puro extraído de handle_reaction (Item 2)."""

      def test_returns_empty_dict_for_no_reactions(self):
          from handlers.gamification_user_handlers import calculate_emoji_counts_from_reactions
          assert calculate_emoji_counts_from_reactions([]) == {}

      def test_counts_single_reaction(self):
          from handlers.gamification_user_handlers import calculate_emoji_counts_from_reactions
          r = MagicMock()
          r.reaction_emoji = MagicMock(id=7)
          assert calculate_emoji_counts_from_reactions([r]) == {7: 1}

      def test_aggregates_multiple_reactions_same_emoji(self):
          from handlers.gamification_user_handlers import calculate_emoji_counts_from_reactions
          r1 = MagicMock(reaction_emoji=MagicMock(id=1))
          r2 = MagicMock(reaction_emoji=MagicMock(id=1))
          r3 = MagicMock(reaction_emoji=MagicMock(id=2))
          assert calculate_emoji_counts_from_reactions([r1, r2, r3]) == {1: 2, 2: 1}

      def test_ignores_reactions_without_reaction_emoji(self):
          from handlers.gamification_user_handlers import calculate_emoji_counts_from_reactions
          r = MagicMock(reaction_emoji=None)
          assert calculate_emoji_counts_from_reactions([r]) == {}

      # (si se extrajo el segundo helper, tests equivalentes para build_emojis_list con side_effect o MagicMock del lookup)
  ```
- (Usar import inside test funcs para seguir el patrón del archivo, que hace `from handlers... import handle_reaction` dentro de cada test.)
- No se modifican los tests de handle_reaction existentes (solo se añaden).
- Ejecutar los re-runs (ver estrategia de tests abajo).
- Post: actualizar el log de Item 2 con resumen de gates + lista de tests críticos para el futuro (similar al handoff de Item 1).

**Tests que deben pasar antes de marcar Item completo:**
- La suite de gamification_user_handlers (o al menos TestHandleReaction + la nueva clase) verde.
- Los reaction chains integrations seleccionados (lista en sección 4).
- Ruff en los 5 archivos.
- Los verificadores de reglas (grep LOC, 0 RewardService en handler, etc.).

**Riesgos + mitigaciones:**
- Riesgo: tests del helper fallan por nombre equivocado o firma → Mitigación: el nombre y firma se deciden/confirman en "Decisiones de diseño" (ver sección 5); el executor ajusta los tests al nombre final elegido.
- Riesgo: re-runs de chains muestran flakes preexistentes (no causados por este Item) → Mitigación: usar `-p no:cov --override-ini="addopts=" -q --tb=line`; documentar si hay 1 unrelated fail (precedente en Item 1: alembic_heads); enfocar en "0 regressions atribuibles a los helpers".
- Riesgo de tiempo: chains de integración pueden ser lentas → Mitigación: priorizar los targeted de handler primero, luego los -k específicos de reaction; el PLAN permite targeted combinados como en el handoff de Item 1.

**Safe point final:** Todos los gates de F5 verdes + GSD log con "F5 FINAL + self-check PASSED" + lista de tests críticos a re-correr en cambios futuros a estos handlers/helpers. Item 2 cerrado.

---

## 3. Estrategia de tests (port + nuevos + re-runs)

**Port de reward handlers (F4):**
- Seguir exactamente el patrón de `tests/handlers/test_mission_user_handlers.py` (parches de get_service, __enter__ devuelve la instancia mock, __exit__ assertions en tests de cierre).
- Configurar los mocks de reward con los atributos que la pure `get_reward_emoji` necesita (ver RewardType enum: BESITOS/PACKAGE/VIP_ACCESS; campos besito_amount, name, etc.).
- Usar `mock_mission.reward = mock_reward` para el acceso por relationship en reward_detail.
- Actualizar/eliminar asserts que solo existían para "proteger la visibilidad del 2-svc".
- Mantener cobertura de todos los paths: empty list, list con items, detail con progreso, completed, sin reward, not found, closes, llamadas con ids correctos, textos producidos.

**Nuevos tests para pure helper de reactions (F5):**
- Ubicación: `tests/handlers/test_gamification_user_handlers.py` (mismo archivo que ya tiene TestHandleReaction; mantiene todo co-localizado y evita nuevos archivos per scope tight).
- Enfoque: unit tests puros del helper (datos de entrada falsos con MagicMock mínimos que solo tengan .reaction_emoji.id).
- Casos mínimos: vacío → {}, una reacción → {id:1}, múltiples mismos id agregan conteo, reacciones con reaction_emoji=None se ignoran, retorno es dict[int,int].
- Si se extraen dos helpers, cubrir ambos.
- Estos tests sirven como "test-guardian" para el helper: cualquier refactor futuro del conteo de reacciones debe pasar estos.

**Re-run de reaction chains (F5, y spot en F3):**
- Handler level: `pytest tests/handlers/test_gamification_user_handlers.py -k "HandleReaction or handle_reaction or TestHandleReaction" -q --tb=line -p no:cov --override-ini="addopts="`
- Integrations críticas (gold paths que ejercitan el refresh de UI post-reacción):
  - `pytest -k "TestFullReactionChain or reaction_full or TestReactionMissionFlow or TestReactionLimit or TestCrossServiceAtomicity" -q --tb=line -p no:cov --override-ini="addopts="`
  - Si el combinado del handoff de Item 1 es reusable: adaptarlo filtrando por "reaction or broadcast or TestCheckAndRegister or gamif".
- Objetivo: confirmar que el código de refresh (ahora delegando a helpers puros) produce las mismas llamadas a update_reaction_message, con los mismos argumentos construidos a partir de los mocks del servicio (get_selected, get_reactions_by_broadcast, get_reaction_emoji).
- (Nota: los tests de integración actuales no siempre asertan el contenido exacto del new_markup, solo que se llamó; para "idéntico" el executor puede, si lo desea y es cheap, inspeccionar el call_args del update en un test de handler, pero no es requerido por scope si los tests existentes siguen pasando y el código replica los loops.)

**Gates generales por fase / final:**
- Ruff: `./venv/bin/python -m ruff check <file> && ./venv/bin/python -m ruff format --check <file>` (o apply en pre si se sigue el precedente de ruff pre-edit).
- Pytest targeted limpio (sin cov para exit code estable).
- Grep de reglas: 0 "RewardService" en reward_user_handlers.py; LOC de handle_reaction <=50; imports de get_service presentes.
- (Opcional para executor) smoke de bot import o registro de routers si se quiere, pero no es necesario per scope (no se toca bot.py).

**Cobertura de logging requirement:** Los tests no asertan logs usualmente (salvo en middleware tests); el gate es manual grep o inspección durante las ediciones + inclusión en el log de GSD.

---

## 4. Decisiones de diseño que el executor debe confirmar (o registrar desviación)

1. **Nombre del helper principal de reactions:** `calculate_emoji_counts_from_reactions` (sigue el ejemplo del proyecto `calculate_user_besitos_from_reactions`). Confirmar o elegir alternativa (e.g. `build_reaction_emoji_counts`, `compute_emoji_counts_from_reactions`) y documentar en el primer GSD entry de F3. Si se extrae segundo helper: `build_emojis_list` (con callable) o mantener inline el loop de emojis si el LOC ya está bajo con solo el de counts.
2. **Delegate backward-compatible para get_reward_emoji:** Sí, 1-línea delegando a la pura (como se especifica). Ubicación: pura a nivel módulo (antes de la clase o después de imports); método dentro de la clase con docstring que menciona "delegate for Item 2 / arch-enforcer". Confirmar que no se rompe ningún import circular (no debería, reward_service ya importa de models).
3. **Logging en los handlers editados:** Agregar/estandarizar logs en formato "módulo | acción | user_id= | resultado" para las acciones principales (show_available_rewards, reward_detail, handle_reaction). Si los handlers actualmente delegan logging a middleware, mínimo es actualizar el log existente en handle_reaction. Confirmar formato con ejemplos de otros servicios/handlers (e.g. "reward_user_handlers | reward_detail | user_id=123 | mission_id=5 | completed=False").
4. **Patrón de tests para pure emoji en reward tests:** Ejecutar la real `get_reward_emoji` sobre MagicMocks configurados con `.reward_type` y campos (opción preferida para simplicidad y "pure" semantics). Alternativa: `@patch("handlers.reward_user_handlers.get_reward_emoji")` en los tests de handler si se quiere aislar completamente el formatting. Preferir la primera a menos que cause complejidad excesiva en setups.
5. **Chequeo de relationship en reward_detail:** Usar `if not mission or not mission.reward:` (consistente con mission_detail). Mantener el mensaje de alert "Recompensa no encontrada". No agregar chequeo de `reward.is_active` aquí (diferiría de comportamiento previo en detail; list ya filtra).
6. **Conteo estricto de ≤50 LOC:** Usar `inspect.getsourcelines(func)[0]` (cuenta líneas de la def inclusive) o equivalente `sed -n 'X,Yp' | wc -l`. Si queda en 51 por docstring, aplicar trim de docstring del helper (mantener contrato) + comentario de "extracted for LOC rule (Item 2)", precedente de credit_besitos en Item 1. No dejar >50.
7. **Actualización de docstrings de tests de reward:** Limpiar las notas de "2-svc" y "arch-enforcer visibility" para reflejar el estado post-fix. Dejar un comentario histórico breve si se desea ("pre-Item 2 this orchestrated two services; now 1-service per arch-enforcer remediation").
8. **Log file para GSD de Item 2:** Usar `.planning/quick/gsd-reward-gamif-item2.log` (o nombre consistente que el executor prefiera y documente en el primer entry). Cada pre-edit/pre-gate/pre-verif debe hacer `echo "=== $(date -Iseconds) | PHASE N | GSD pre-... - <descripción corta>" >> <logfile>"` (o usar run_terminal_command con comando echo/printf). Al final del Item, el log debe tener entradas para cada acción significativa (como los 44+ de Item 1).
9. **Si se necesita un segundo helper para emojis en reaction:** Solo si el conteo de LOC de handle_reaction no baja suficiente con el de counts solo. El helper de build puede ser "puro" aceptando el callable de lookup (sin hacer IO). Si no se extrae, documentar por qué el LOC ya cumplía.
10. **No exportar la pura en services/__init__.py:** Confirmado por scope (import directo del módulo es suficiente y usado en el codebase). No editar __init__.

Cualquier decisión que difiera de lo anterior debe registrarse en el GSD log + (si se permite fuera de scope estricto) en una nota breve al final del PLAN o en SUMMARY posterior.

---

## 5. Criterios de verificación + gates finales

**Criterios de éxito del Item (medibles, para self-check del executor):**
- Los dos handlers de reward (show_available_rewards, reward_detail) y su helper _build_rewards_buttons no contienen ninguna referencia activa a RewardService (import o uso).
- Usan exclusivamente `get_service(MissionService)` vía context manager (with) + relationship para reward + pure get_reward_emoji importada.
- handle_reaction <=50 LOC fuente; helpers puros extraídos y usados para la prep de datos de UI de reacciones.
- Todos los tests en `test_reward_user_handlers.py` pasan post-port (sin mocks de RewardService, con get_service, con relationship setup, con pure emoji ejecutándose real sobre mocks configurados).
- Nuevos tests del helper de reaction existen y pasan.
- Re-runs de reaction chains (handler + integrations relevantes) pasan sin regressions atribuibles a la extracción.
- Ruff clean en los 5 archivos modificados.
- Verificaciones de reglas:
  - `grep -c "RewardService" handlers/reward_user_handlers.py` (activo) == 0
  - LOC handle_reaction <=50
  - Logging formato presente en paths editados (spot check manual o grep).
- GSD log de Item 2 tiene pre-entries para cada edit/gate + self-check PASSED al final.
- Comportamiento de usuario final idéntico (lista y detalle de rewards muestran mismos emojis/nombres/textos; reacciones actualizan conteos del mensaje exactamente como antes).

**Gates por fase (ver secciones de fases para detalles):**
- Pre-edit: GSD log entry.
- Post-edit: ruff + targeted pytest (cuando aplique) + smoke + grep/LOC checks + GSD entry de resultado.
- Avanzar solo si gate verde.

**Comando combinado sugerido para gates finales de reacción (adaptar del handoff Item 1):**
```
./venv/bin/python -m pytest -k "reaction or broadcast or TestHandleReaction or TestFullReactionChain or TestReactionMissionFlow or TestReactionLimit or TestCrossServiceAtomicity or gamif" -q --tb=line -p no:cov --override-ini="addopts="
```

---

## Instrucciones para el siguiente agente (gsd-executor)

Sigue este PLAN al pie de la letra. Este documento es el prompt de ejecución.

1. **GSD discipline (non-negotiable):**
   - Antes de **cualquier** modificación de archivo (incluyendo creates de dirs si aplica, pero el dir del phase ya existe), o antes de gates/verifs significativos: append al log de Item 2.
   - Log recomendado: `.planning/quick/gsd-reward-gamif-item2.log`
   - Formato de entry (copiar estilo del de Item 1):
     ```
     === 2026-06-07Txx:xx:xx+00:00 | PHASE N | GSD pre-edit <archivo> (<motivo corto>) - <descripción de lo que se va a hacer, refs a DoD, LOC si aplica>
     ```
     Luego el comando de edit.
   - También pre-ruff, pre-pytest, pre-grep-verif, pre-final-summary (si produces SUMMARY), pre-self-check.
   - Cuenta las entradas; apunta a tener varias por fase (como 5-10+ totales para el Item).

2. **Orden estricto:** Ejecuta Fase 1 → gates → Fase 2 → gates → ... → Fase 5. No saltes ni hagas "todo de una". Marca DoD mentalmente o en el log.

3. **Herramientas y comandos:**
   - Usa `run_terminal_command` para mkdir (si necesitas), echo para logs GSD, ruff, pytest, grep, python -c para smokes/LOC, sed/wc si ayuda al conteo.
   - Para edits: usa las herramientas de edición disponibles (search_replace / write / etc. según tu contexto; el PLAN no prescribe la herramienta exacta de patch, solo el resultado deseado).
   - Para verificar LOC post F3: usa el python inspect snippet provisto en la Fase 3.
   - Para confirmar 1-service: grep en el handler de reward.

4. **Patrones a copiar (no reinventar):**
   - Patrón get_service + with + mock en tests: copia de `tests/handlers/test_mission_user_handlers.py` (los tests de show_my_missions, mission_detail, closes via __exit__).
   - Extracción de helper para LOC: copia el espíritu de lo hecho en F2 de Item 1 (besito_service: helper privado `_schedule...` + llamada 1-línea; trim de docstring para encajar <=50).
   - Logging: "módulo | acción | user_id=... | resultado=...".
   - Voz/estilo: no aplica directamente (esto es refactor interno), pero si tocas mensajes de usuario mantén idénticos.
   - GSD log entries detalladas con "pre-" + descripción de intento + qué se valida después.

5. **Decisiones a confirmar (sección 5 del PLAN):** Al inicio de la fase relevante (o en el primer GSD entry de la fase), registra en el log qué nombre de helper elegiste, si extraes 1 o 2, cómo manejas el logging, etc. Si difieres del "preferido", explica brevemente por qué (y que se mantiene el espíritu).

6. **Gates y re-runs:** 
   - Corre los targeted de pytest con `-p no:cov --override-ini="addopts="` para obtener exit limpio (precedente establecido).
   - Si un unrelated fail preexistente aparece (ej. alembic_heads), documéntalo; no lo cuentes como regression del Item.
   - Re-run de chains de reacción es obligatorio en F5 (y spot-check en F3 después de la extracción).

7. **Alcance (recuerda siempre):** Solo edita los 5 archivos listados + el log GSD + (este PLAN ya está escrito por el planner). No toques mission_service, __init__, docs, bot.py, etc. Si sientes la tentación de "limpiar más", detente: scope tight para cerrar las dos notas del arch-enforcer con mínimo riesgo.

8. **Al final del Item:**
   - Self-check similar al de Item 1 (lista de fases, DoD, gates, desviaciones, archivos modificados, tests que pasaron, estado de reglas, handoff de "tests críticos a re-correr en el futuro para estos handlers/helpers").
   - Si el proceso produce un SUMMARY.md en el dir de la phase (como en phases/19-...), hazlo solo si el tiempo y las convenciones lo permiten; el mínimo requerido es el log GSD completo + los 5 archivos + que los criterios de verificación se cumplan.
   - Confirma en el log final: "Self-Check: PASSED" + "Item 2 closed. Ready for arch-enforcer re-scan + test-guardian".

9. **Si algo no está claro o el analyzer report tiene detalles que difieren:** El prompt del usuario + este PLAN (basado en el reporte descrito + handoff + notas en tests + código actual) es la fuente de verdad. Pregunta solo si un gate bloquea por ambigüedad de nombre/firma; de lo contrario, elige conservadoramente siguiendo precedentes y registra.

**¡Ejecuta con disciplina. Cierra las notas del arch-enforcer de forma limpia, segura y medible.**

---

**Fin del PLAN para Item 2 (reward + gamif rules compliance).**

Referencias rápidas para el executor:
- Patrón mission: `handlers/mission_user_handlers.py` (imports get_service + with, relationship `mission.reward` en mission_detail).
- get_service: `services/__init__.py:69` (context manager).
- Relación: `models/models.py:548` (Mission.reward) + `625` (Reward.missions).
- get_reward_emoji actual: `services/reward_service.py:108`.
- handle_reaction: `handlers/gamification_user_handlers.py:194` (52 LOC actuales).
- Tests reward actuales + notas arch-enforcer: `tests/handlers/test_reward_user_handlers.py:19-23,65-67,104-107`.
- Handoff Item 1: `.planning/phases/19-eventbus-poc/19-eventbus-poc-SUMMARY.md:122-137`.
- Reglas: `CLAUDE.md`, `rules.md`, `architecture.md`, `handlers/CLAUDE.md`.
- Precedente de extracción LOC + GSD log: `.planning/quick/gsd-eventbus-poc-item1.log` (entries de F2).

Listo para gsd-executor.