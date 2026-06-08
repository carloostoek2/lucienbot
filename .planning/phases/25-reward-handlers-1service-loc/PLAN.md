# PLAN: Consolidate reward_user_handlers to exactly 1 service + extract pure helpers for ≤50 LOC (Item 7 / first of new pool of 4, post-unification Besito hardening)

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-06-08  
**Focus:** Tight, conservative, phased consolidation of `handlers/reward_user_handlers.py` (show_available_rewards + reward_detail + supporting `_build_rewards_buttons`) so they call **exactly 1 service** (MissionService via standardized `with get_service(MissionService) as ...` context + `get_service` lifecycle). Use relationship access (`mission.reward`) for reward data (precedent: mission_user_handlers). Use pure top-level `get_reward_emoji(reward)` imported from `services.reward_service` (promoted in prior work). Extract 1-2 pure helpers (e.g. `compute_reward_status_text`, `build_reward_detail_keyboard`) to bring all functions ≤50 LOC source (reward_detail currently exactly 50 lines per inspect; arch-enforcer note on "functions exceeding 50 lines"). Minimal support/confirm in `services/reward_service.py` (pure `get_reward_emoji` top-level + 1-line delegate with "Backward-compatible delegate added for Item 2..." comment). Update only `tests/handlers/test_reward_user_handlers.py` (confirm "1 service" ports + add unit tests for extracted pure helpers). **0 changes in delivery/claim behavior** (deliver_reward, log_reward_delivery, auto-deliver in mission increment, backpack earned paths untouched). **0 other handlers touched**. **0 mission_service changes**. UI/render identical (exact texts, emojis, progress █░ bars, button labels `f"{status_emoji} {reward_emoji} {name[:30]}"`, callback packing, alerts, empty case). 3 critical systems (gamif/missions/rewards, narrative, channel/VIP) always in mind (this flow is read-only list/detail; 0 tx/credit/deliver). GSD pre-log discipline on `.planning/quick/gsd-reward-handlers-1service-loc.log` (and cross-ref the impact analyzer's gsd-impact-analyzer-item7-...log) before every edit/gate/verif. Follow structure/patrones/snippets **al pie de la letra** from successful precedents (phase20 Item2 / gsd-reward-gamif-item2.log for reward 1-service + pure emoji + ports + helper tests + LOC inspect + self-check; 23/24 for item phasing + batch language; 21 getservice for with/get_service patterns; mission_user_handlers.py + its tests for 1-service + rel; atomicity golds for -p no:cov --override-ini flags + targeted re-runs).

**Input principal (source of truth):** 
- Complete impact-analyzer report: `.claude/agent-memory/impact-analyzer/item7-reward-handlers-1service-loc.md` (executive summary, mapa de impacto with exact files: handlers/reward_user_handlers.py + services/reward_service.py for pure func + tests/handlers/test_reward_user_handlers.py; riesgos low due to precedents + tight scope; tests críticos; scope tight recomendado; design notes "MissionService vía get_service + rel access para reward data"; precedentes de item 2/5/6 y PLAN 20-reward-gamif-rules-compliance; "first of new pool of 4"; "0 changes in delivery/claim"; "add tests for helpers nuevos").
- Precedents + golds: `.planning/phases/20-reward-gamif-rules-compliance/PLAN.md` + its gsd-reward-gamif-item2.log (exact Item2 reward 1-service consolidation + pure emoji promotion + delegate + port of test_reward_user_handlers to get_service(Mission only) + rel setups + real pure emoji via .reward_type attrs + __exit__ closes + docstrings "Tests ported to 1-service pattern... Arch-enforcer note addressed" + new Test*PureHelpers class + re-runs + LOC inspect + self-check PASSED + critical tests list + handoff); `.planning/phases/23-reward-besito-eventbus-decoupling/PLAN.md` + SUMMARY + gsd-reward-besito-eventbus.log; `.planning/phases/24-remaining-besito-compositions/PLAN.md` + 24-*-SUMMARY.md (BATCH close language "4 items completed in this tirón (Item 6 final of max 4)", "Item 6/24 closed. BATCH...", self-check structure, GSD style); gsd-testing-debt-item5.log / item6.log (ports of docstrings + asserts to "1 service" + pure formatting); gsd-getservice-unification.log + 21-PLAN (with/get_service context patterns + __enter__/__exit__ mocks in tests); handlers/mission_user_handlers.py + test_mission_user_handlers.py (1 service + rel for reward in mission_detail; "if mission.reward"); current source (reward_user_handlers already uses get_service(Mission) + pure import + rel + no RewardService per grep/inspect; reward_detail exactly 50L; reward_service has pure top + delegate); impact report + MEMORY.md pointers; CLAUDE.md (root + handlers + services + models), rules.md (≤50 LOC, verb+context+result naming, logging "módulo | acción | user_id | resultado", exactly 1 service per handler entrypoint), architecture.md (handlers→services→models), decisions.md, AGENTS.md, services/missions/CLAUDE.md (rewards domain), models/CLAUDE.md (rels for access safe).

**GSD enforcement:** Executor MUST prefix **every** modification / pre-gate / verification / ruff / pytest / grep / smoke / self-check / summary with a GSD log append (timestamp | PHASE | description) to `.planning/quick/gsd-reward-handlers-1service-loc.log` (use the item7 impact one for cross-ref if needed). Use identical discipline, entry style, wc -l tracking, "pre-xxx <file> (F<N> <short motive>) - <desc + refs DoD + patrones copiados al pie de la letra>", and self-check structure as gsd-reward-gamif-item2.log (46+ entries, phases complete + SAFE POINT + FINAL self-check PASSED) / gsd-remaining-besito-compositions.log (BATCH note) / gsd-reward-besito-eventbus.log. No edits (even to PLAN/log beyond appends) without pre-log. Planner did INIT + pre-write (2 entries, wc tracked).

---

## 1. Alcance preciso (In / Out explícito + archivos exactos)

### En esta entrega (scope "tight" per impact report + user spec + "no creep" + precedents):
- **handlers/reward_user_handlers.py** (core): Ensure/keep exactly `with get_service(MissionService) as mission_service:` (1 call only per entrypoint). Use rel `mission.reward` (already in detail + "if not mission or not mission.reward"). Use pure `get_reward_emoji(reward)` (already imported top-level from services.reward_service; no RewardService anywhere — confirmed grep 0 matches). Extract 1-2 pure helpers to slim reward_detail (currently exactly 50 lines per inspect.getsourcelines; must be ≤50 strict post-extract; count includes def + docstring + body). Recommended extracts (copy logic 1:1 for identical render):
  - `compute_reward_status_text(progress, mission) -> str`: the ternary (completed vs f"\n📊 Progreso: {bar} {percentage}%\n   {current} / {target}").
  - `build_reward_detail_keyboard(mission_id: int) -> InlineKeyboardMarkup`: the buttons list with MissionDetailCallback + back to rewards_list.
  (Optionally a small pure for list button text/status if it helps LOC, but tight: only as needed for reward_detail.)
  Keep all other _build_* (list text, detail text, progress bar, _safe_*) as-is (already small/pure). Preserve: logs in format "reward_user_handlers | show_available_rewards | user_id=... | count=..." (and for detail), _EMPTY_REWARDS_TEXT, idempotency comments (gsd-mw-hardening phase 5), Lucien voice, exact strings/emoji/progress bar chars/status texts/button labels/cb data packing/truncation name[:30]. No new imports of RewardService; no DB; no biz logic (progress calc stays in service or pure format helpers). Post: verify no function >50 lines (inspect or wc on def-to-end); reward_detail ≤50.
- **services/reward_service.py** (soporte mínimo only): Ensure/confirm `get_reward_emoji(reward: Reward) -> tuple[str, str]` remains module-level pure top (before class; docstring: "Retorna (emoji, description) según tipo de recompensa. Función pura (sin estado ni side-effects)."; logic for BESITOS/PACKAGE/VIP_ACCESS/default identical to current). Keep the instance delegate (added for Item 2 / arch-enforcer):
  ```python
  # Backward-compatible delegate added for Item 2 (arch-enforcer 1-service rule for reward handlers).
  def get_reward_emoji(self, reward: Reward) -> tuple[str, str]:
      """Retorna (emoji, description) según tipo de recompensa. Delegate a la función pura top-level para mantener compatibilidad."""
      return get_reward_emoji(reward)
  ```
  0 changes to: deliver_reward / _deliver_* / log_reward_delivery / close / create_* / get_* / held subs (package/vip) / observer / anything in claim/delivery paths / atomicity contracts. (Already in current tree per analysis + item2 execution; this item confirms/ensures.)
- **tests/handlers/test_reward_user_handlers.py** (only its test file): Confirm/port: all tests patch `"handlers.reward_user_handlers.get_service"` (not RewardService). Mock context `__enter__`/`__exit__`. Setup mock_reward with `.reward_type`, `.besito_amount`, `.name` etc so **real pure** `get_reward_emoji` executes in _build (for list) and detail. Use `mock_mission.reward = mock_reward` for rel in detail tests. Update/refresh docstrings (keep/ensure "Tests ported to 1-service pattern (get_service + MissionService only) + pure formatting via get_reward_emoji. Arch-enforcer note addressed." + note removals of skip-dupe/idempotency per mw phase5). **Add**: new tests for extracted pure helpers (e.g. class `TestRewardUserPureHelpers`; cover empty/completed/progress for status_text, different RewardType for emoji+gives if render helpers touch, button texts/status_emoji + truncation + packed cb data, _build_progress_bar math 0/50/100/edge, _build_reward_detail_text with None descs). Keep: make_callback fixture, assertions on edit_text content (exact phrases like "Recompensas Disponibles", "completada", "Progreso", "3 / 10"), calls to get_mission/get_or_create_progress/get_available..., close via context. 0 direct RewardService mocks left in this file.
- **GSD + artefacts**: run_terminal append BEFORE every edit/write/gate/verif (to .planning/quick/gsd-reward-handlers-1service-loc.log); track wc -l; specific git add only touched (if committing); ruff/pytest gates with exact flags; self-check PASSED at end with full structure (phases/DoD/gates/archivos/tests/rules/desviaciones/critical tests list/"Item closed. Ready for arch-enforcer re-scan (enfocado en reward handlers 1svc + <=50L) + test-guardian (re-correr lista) + siguiente item del pool de 4").
- **Verification**: the 3 files ruff clean; handler test file 100% pass (behavior identical); critical list re-run (reward handler test + cross flows with reward/mission list/detail paths; atomicity/mission e2e spot if they exercise rewards UI indirectly); bot smoke (import bot or reward router); line counts <=50 (inspect post-extract); outputs match pre (via test asserts on strings); 0 change to deliver/claim (re-runs of cross_service_atomicity reward paths + mission flows protect).
- Memory: cross-ref impact report + this PLAN + GSD log entries.

**Archivos que se modificarán (exactos, por orden de fases; prefer extend, minimal):**
1. `.planning/quick/gsd-reward-handlers-1service-loc.log` (all phases, pre only via echo; no "edit" of source beyond appends).
2. `services/reward_service.py` (F2: min support/confirm pure top-level + delegate comment if polish needed).
3. `handlers/reward_user_handlers.py` (F3: extract 1-2 pure helpers + slim reward_detail; ensure 1svc explicit + logs + LOC<=50).
4. `tests/handlers/test_reward_user_handlers.py` (F4: confirm ports + add Test*PureHelpers class/tests).
5. Re-runs/gates/verifs/smokes do not modify (except ruff auto-fixes if any on touched + log appends).

**Fuera explícitamente (nada de scope creep, per "tight" + impact "0 otros handlers" + "0 mission_service changes" + "0 changes in delivery/claim" + "0 docs más allá de lo necesario para el item" + precedents):**
- **NO** otros handlers (backpack_handler.py, reward_admin_handlers.py, mission_user_handlers.py, gamification_*, common, broadcast, store_*, etc. — even if they touch rewards).
- **NO** mission_service.py (no refactor of get_available_rewards_for_user or increment_and_deliver; handler calls only the MissionService method; enrichment is service impl detail).
- **NO** backpack_service / its tests / reward_admin / reward_service unit tests / admin handlers (separate domains; legit use of RewardService for create/deliver/history).
- **NO** models, keyboards, callback_data, bot.py, services/__init__.py, utils, lucien_voice, middlewares.
- **NO** changes to deliver_reward, _deliver_*, log_reward_delivery, close logic, held services in RewardService, event listeners, atomicity contracts, claim flows, backpack earned rewards.
- **NO** new tests outside the reward_user test file (no service tests for emoji; no new integration files).
- **NO** edición de CLAUDEs, decisions.md, AGENTS, ROADMAP, fase_*, docs/, o cualquier .md excepto este PLAN + el log GSD (impact report + MEMORY already done by analyzer).
- **NO** broad "fix all reward handlers" or "touch mission_service for orchestration perception".
- **NO** behavior or contract changes (0 impact on claim/delivery/partial failure; UI identical).

**Comportamiento observable idéntico + reglas:** Lista y detalle de rewards producen el mismo texto, botones, emojis, barras de progreso, status ("completada" / "Progreso: █░░░░░░░░░ 30%\n   3 / 10"), alerts, navegación (link a mission detail + back), logs. Handlers llaman exactly 1 service (MissionService); funciones ≤50 LOC post-extract; logging en formato estándar para acciones importantes; get_service context manager; sin lógica de negocio en handlers; sin acceso DB fuera de models; pure helpers (no side effects, importable, fácil unit test, verb+context+result naming). 3 sistemas críticos protegidos (read-only info; 0 side effects en gamif credit / narrative / VIP-channel).

**Artefactos:** Este PLAN.md + entradas GSD completas en el log dedicado (pre every) + (si procede en executor) SUMMARY.md posterior (seguir precedente 24/23/20). Memory/hand-off ya apunta desde impact report + MEMORY.md.

---

## 2. Fases ordenadas (5-6 fases pequeñas, secuenciales, con gates estrictos)

### Fase 1: Preparación (GSD log init/confirm, baseline, fixtures/patterns, patrones gold, LOC actual, confirm 1svc ya en tree)

**Objective:** Establecer disciplina GSD para el Item (log touched by planner + executor first entries); confirmar baseline de archivos tocados (ruff clean + targeted pytest verde pre-cambios); mapear estado actual (1 service ya vía MissionService + rel + pure emoji import + 0 RewardService per grep; reward_detail exactamente 50L); confirmar fixtures (make_callback), patrones gold (get_service patch + __enter__/__exit__ from test_mission_user + item2 port; real pure emoji via mock_reward .reward_type=RewardType.BESITOS etc; mock_mission.reward= for rel); identificar los helpers a extraer (status_text + keyboard para reward_detail); confirmar UI strings exactas para pinning en nuevos tests de helpers; GSD pre/post (varias); "F1 safe point - baseline verde + ready for F2; no source changed yet".

**DoD checklist (marcar al completar):**
- [ ] Log `.planning/quick/gsd-reward-handlers-1service-loc.log` exists with planner INIT/pre-mkdir/pre-write entries (wc >=2) + at least 1 pre-F1 of executor.
- [ ] Baseline: ruff clean on the 3 target files (`./venv/bin/python -m ruff check handlers/reward_user_handlers.py services/reward_service.py tests/handlers/test_reward_user_handlers.py --fix && ./venv/bin/python -m ruff format --check ...`).
- [ ] Baseline targeted pytest verde (clean flags exact): `./venv/bin/python -m pytest tests/handlers/test_reward_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` (all ~14 tests in the 2 classes; expect green as ported in tree).
- [ ] Confirm gold patterns via grep/lectura + python inspect: current reward_detail LOC==50 (or 49-56 per count); grep -n "get_service(MissionService)" + "from services import get_service" + "from services.reward_service import get_reward_emoji" in handler (present); grep -n "RewardService" in handler ==0 (active); "if not mission or not mission.reward" present; mock patterns in test (get_service patch, __enter__, mock_mission.reward=, .reward_type on mock_reward for pure); strings like "Recompensas Disponibles", "completada", "Progreso", "3 / 10", "No hay recompensas" for pinning.
- [ ] Read precedents (item2 PLAN + gsd log excerpts for ports + helper extract + self-check; mission_user_handlers for 1svc+rel; 24 SUMMARY for BATCH close language to cite in final self-check).
- [ ] GSD pre + post entries for baseline (multiple; wc tracked).
- [ ] Safe point F1.

**Archivos:** Log + (lectura/grep/ruff/pytest/inspect; 0 edits to prod/tests in F1 except hygiene ruff if auto).

**Cambios clave (bullets accionables):**
- Ejecutar comandos de baseline (ver "Instrucciones para el gsd-executor" + sección 5).
- Grep/lectura rápida + python -c inspect for LOC + patterns (copy from item2 F2/F4 gates: `python -c 'import inspect; from handlers.reward_user_handlers import reward_detail; src=inspect.getsourcelines(reward_detail)[0]; print("LOC:", len(src))'`).
- Confirm import of RewardType in test (or add in F4 if needed for setups); make_callback from conftest.
- Actualizar log con "F1 baseline verde + patterns confirmed (1svc already via Mission get_service + rel + pure emoji; reward_detail=50L drives extract of compute_reward_status_text + build_reward_detail_keyboard; UI strings pinned; previous batch closed per 24-SUMMARY BATCH note; this is first of new pool of 4) + ready for F2".
- (No code changes in F1 logic.)

**Tests que deben pasar antes de avanzar (gates de F1):**
- Ruff on the 3 files (or 2 if hygiene only on test/handler).
- `pytest tests/handlers/test_reward_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` (full; 14/14 or current count).
- Grep/inspect confirm + GSD entries + "F1 safe point".
- (Optional) spot broader `pytest -k "reward or mission" -q --tb=line -p no:cov --override-ini="addopts="` for cross flows (no edit expected).

**Riesgos + mitigaciones:**
- Riesgo: baseline shows pre-existing unrelated fails (alembic, daily concurrent, etc.) → Mit: document in log (precedent 24/23/22/20/19 "do not count as regression"); use targeted -k; focus "0 attributable to this Item".
- Riesgo: LOC count varies by comments/docstring (50 exactly now) → Mit: use inspect.getsourcelines (incl def) as in item2 F3/F5; trim only if post-extract >50 (rare); mechanical extract of 5-10L status/keyboard will drop it.
- Bajo: time on baseline → Mit: targeted, parallel where safe but prefer sequential for log.

**Safe point:** Baseline verde + patterns confirmed (1svc + pure + rel + 50L on reward_detail) + "F1 safe point - ready for reward_service confirm + extract; no source changed yet". Reversible (nada editado en fuentes aún).

---

### Fase 2: Soporte mínimo en RewardService (confirmar/promover get_reward_emoji a pura top-level + delegate si pulido necesario)

**Objective:** Confirmar que la lógica de emoji es una función pura importable sin instanciar servicio (ya presente post-Item2), mientras se preserva 100% compatibilidad backward via delegate de 1 línea. Añadir/asegurar comentario "Backward-compatible delegate added for Item 2 (arch-enforcer 1-service rule for reward handlers)." si falta. Esto habilita (y mantiene) a los handlers de reward a no depender de RewardService en absoluto. Ruff + smoke + grep 2 defs + targeted reward tests (no blocking en handler tests pre-F4). GSD pre. Safe point.

**DoD checklist:**
- [ ] Función pura `get_reward_emoji(reward: Reward) -> tuple[str, str]` definida a nivel de módulo en `services/reward_service.py` (lógica idéntica; sin self, sin side-effects; docstring "Función pura (sin estado ni side-effects)").
- [ ] Método de instancia `def get_reward_emoji(self, reward: Reward)` es un delegate de 1 línea que llama a la pura; comentario de Item 2 / arch-enforcer presente (o añadido).
- [ ] Imports necesarios ya presentes (Reward, RewardType desde models.models).
- [ ] Sin cambios de comportamiento: para un Reward dado, el retorno (emoji, gives) es idéntico (smoke 4 branches: BESITOS/PACKAGE/VIP_ACCESS/default).
- [ ] Ruff limpio en el archivo.
- [ ] Smoke de import + llamada básica (pure + delegate + svc instance) pasa.
- [ ] Grep confirma la pura existe y el delegate llama: `grep -n "def get_reward_emoji" services/reward_service.py` (debe mostrar 2).
- [ ] GSD pre-edit + pre-gate entries en el log.
- [ ] Safe point.

**Archivos:** `services/reward_service.py`

**Cambios clave (bullets accionables, orden sugerido):**
- Pre-log GSD "pre-edit services/reward_service.py (F2 ensure pure top-level get_reward_emoji + delegate comment) - refs DoD F2 + copy from item2 PLAN F1 snippet + current tree (already pure at 22 + delegate at 125); if polish only add comment; read_file done pre".
- Si la pura no está (o para confirmar): insertar **antes** de la clase (después de logger):
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
- Reemplazar/asegurar el cuerpo del método dentro de la clase por el delegate de 1 línea + comentario:
  ```python
  # Backward-compatible delegate added for Item 2 (arch-enforcer 1-service rule for reward handlers).
  def get_reward_emoji(self, reward: Reward) -> tuple[str, str]:
      """Retorna (emoji, description) según tipo de recompensa. Delegate a la función pura top-level para mantener compatibilidad."""
      return get_reward_emoji(reward)
  ```
- Post-edit: ruff check + format apply si necesario + smoke import+call (4 branches + delegate on real svc + close).
- Grep verificación.
- (Si ya estaba perfecto: el "cambio" puede ser solo el GSD + confirm; ruff/smoke/grep siguen siendo gates.)

**Tests que deben pasar antes de avanzar (gates de F2):**
- Ruff en el archivo: exit 0.
- Smoke: `./venv/bin/python -c "from services.reward_service import RewardService, get_reward_emoji; from models.models import RewardType; from unittest.mock import MagicMock; ..."` (exercise pure 4 branches + delegate + svc; expect identical returns; no errors).
- Grep: `grep -n "def get_reward_emoji" services/reward_service.py` (exactly 2 matches).
- Targeted: `pytest tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "reward or emoji or deliver" | cat` (or full reward unit; non-blocking if only the handler port is pending).
- GSD + "F2 safe point".

**Riesgos + mitigaciones:**
- Riesgo bajo: callers existentes de la API de instancia se rompen → Mitigación: el delegate preserva firma y comportamiento exacto (precedent item2 ejecutado y tests passing).
- Riesgo: duplicación accidental → Mitigación: el cuerpo solo vive en la pura; delegate es 1-línea; revisión visual + smoke.
- Ningún test directo del emoji sin mocks en algunos sitios (los de handlers lo ejercitan vía real pure post-port); el port en F4 + re-runs validan.

**Safe point:** Post-ruff + smoke verde + grep 2 defs + GSD "F2 safe point - pure top-level + delegate confirmed (or polished with Item2 comment); 0 behavior change; only this file touched (reversible 1-line if needed)". Handler/service baseline ready for extract.

---

### Fase 3: Refactor handlers de reward (asegurar exactly-1-service + extraer helpers puros para ≤50 LOC; UI idéntica; logging)

**Objective:** En `reward_user_handlers.py`, asegurar que show_available_rewards y reward_detail (y _build_rewards_buttons) cumplan "exactly 1 service" (ya lo hacen vía MissionService get_service; confirmar/ pulir imports + with + rel + pure). Extraer 1-2 helpers puros (compute_reward_status_text, build_reward_detail_keyboard) del cuerpo de reward_detail (y show si roza) de forma que reward_detail quede ≤50 líneas fuente (ideal 45-48). Preservar exactamente el mismo render (textos, barras, botones, callbacks, alerts). Añadir/estandarizar logging en formato "reward_user_handlers | show_available_rewards | user_id=... | count=..." y similar para reward_detail. Ruff + inspect LOC + grep 0 RewardService + 1svc + GSD. Safe point.

**DoD checklist:**
- [ ] Imports: `from services import get_service`, `from services.mission_service import MissionService`, `from services.reward_service import get_reward_emoji`; **0** menciones a `RewardService` (grep -n "RewardService" ==0 active; ya confirmado en F1).
- [ ] show_available_rewards y reward_detail usan `with get_service(MissionService) as mission_service:` (ya; confirmar post cualquier hygiene).
- [ ] _build_rewards_buttons usa `get_reward_emoji(reward)` (pura; ya).
- [ ] reward_detail usa rel `mission.reward` + `if not mission or not mission.reward:` + `get_reward_emoji(mission.reward)`.
- [ ] Helpers puros extraídos: al menos `compute_reward_status_text(progress, mission) -> str` y `build_reward_detail_keyboard(mission_id: int) -> InlineKeyboardMarkup` (o nombres equivalentes verb+context+result); lógica copiada 1:1 desde el cuerpo (sin side effects, sin DB, sin async).
- [ ] reward_detail (y show/_build si aplican) fuente ≤50 líneas post-extract (verificado con `python -c 'import inspect; ...; print(len(inspect.getsourcelines(reward_detail)[0]))'` <=50; prefer <50 estricto).
- [ ] Logging estándar presente para las acciones clave dentro de los with (después de obtener datos exitosos).
- [ ] Comportamiento idéntico: mismos textos en _build_*, mismos botones (status_emoji + reward_emoji + name[:30]), mismos callbacks (MissionDetailCallback + back), mismas alerts, misma barra █░, mismos strings "completada"/"Progreso"/"3 / 10".
- [ ] GSD pre + gates (ruff, inspect LOC, grep 1svc + 0 RewardService, smoke import, targeted test pre-F4) verdes.
- [ ] Safe point.

**Archivos:** `handlers/reward_user_handlers.py`

**Cambios clave (bullets accionables + snippets/patrón a copiar al pie de la letra de item2 PLAN + current tree + mission precedent):**
- Pre-log GSD "pre-edit handlers/reward_user_handlers.py (F3 extract pure helpers + ensure 1svc) - refs DoD F3 + copy get_service+with+rel+pure from current (lines 14-16,78,107-109,115) + item2 PLAN F2 snippets + mission_user_handlers.py:90 (if mission.reward); extract status/keyboard to slim reward_detail from 50L; read pre done".
- Confirm/asegurar imports al inicio (ya correctos per F1; si hygiene):
  ```python
  from services import get_service
  from services.mission_service import MissionService
  from services.reward_service import get_reward_emoji
  # (0 RewardService)
  ```
- En reward_detail (alrededor de la construcción de status_text ~117-121 y buttons ~133-142): reemplazar el inline por llamadas a helpers puros (lógica copiada exacta):
  ```python
  status_text = compute_reward_status_text(progress, mission)
  ...
  keyboard = build_reward_detail_keyboard(mission.id)
  ```
- Insertar los helpers puros (cerca de otros _build_*, después de _build_progress_bar o antes de las routes; nombres verb+context+result; docstring "Función pura"):
  ```python
  def compute_reward_status_text(progress, mission) -> str:
      """Construye el texto de status (completada o barra de progreso) para el detalle de recompensa. Función pura."""
      if progress.is_completed:
          return "\n✅ ¡Mision completada! La recompensa ha sido entregada."
      bar, percentage = _build_progress_bar(progress.current_value, mission.target_value)
      return f"\n📊 Progreso: {bar} {percentage}%\n   {progress.current_value} / {mission.target_value}"

  def build_reward_detail_keyboard(mission_id: int) -> InlineKeyboardMarkup:
      """Construye el teclado inline para el detalle de recompensa (ver mision + volver)."""
      buttons = [
          [
              InlineKeyboardButton(
                  text="🎯 Ver mision",
                  callback_data=MissionDetailCallback(mission_id=mission_id).pack(),
              )
          ],
          [InlineKeyboardButton(text="🔙 Volver a recompensas", callback_data="rewards_list")],
      ]
      return InlineKeyboardMarkup(inline_keyboard=buttons)
  ```
  (Ajustar para que _build_progress_bar siga siendo usado; o inline el bar si ayuda LOC — pero mantener helpers pequeños.)
- Añadir/asegurar logs estándar (dentro del with, post data exitosa; copiar formato de item2 F2):
  ```python
  logger.info(f"reward_user_handlers | show_available_rewards | user_id={user_id} | count={len(rewards_data)}")
  logger.info(f"reward_user_handlers | reward_detail | user_id={user_id} | mission_id={mission_id} | completed={progress.is_completed}")
  ```
- Post-extract: ruff --fix + format --check (apply si dirty per precedent); inspect LOC de reward_detail (debe <=50); grep -n "RewardService" ==0; grep for the new def names; smoke import de las funcs + helpers.
- Confirmar que los helpers existentes (_build_reward_detail_text etc.) y los nuevos son puros o utils pequeños; UI render 1:1 (los tests de F4 pin exact phrases + bar math).
- (Si reward_detail queda en 50 por boilerplate, trim de docstring del helper o comentario "extracted for LOC rule (Item 7)" siguiendo precedente item2 F3 "trim de docstring para encajar <=50").

**Tests que deben pasar antes de avanzar:**
- Ruff en el handler.
- Smoke: `./venv/bin/python -c "from handlers.reward_user_handlers import show_available_rewards, reward_detail, compute_reward_status_text, build_reward_detail_keyboard; print('ok')"`
- Inspect LOC: `python -c 'import inspect; from handlers.reward_user_handlers import reward_detail; src=inspect.getsourcelines(reward_detail)[0]; print("reward_detail LOC:", len(src))'` → <=50.
- Grep: `grep -n "RewardService" handlers/reward_user_handlers.py` → 0 (active); `grep -n "get_service(MissionService)" ...` presente; `grep -n "compute_reward_status_text\|build_reward_detail_keyboard" ...` presente.
- (Los tests funcionales del handler se gatean en F4; aquí basta que el módulo cargue, helpers sean callables, y LOC ok. Un test spot de refresh si aplica pero tight: no requerido.)

**Riesgos + mitigaciones:**
- Riesgo: UI / render divergence after extract (status text, keyboard buttons, "completada", progress bar, cb data) → Mit: extraction is pure copy-paste of logic to new def; new helper tests in F4 have exact string/math asserts (copy from existing handler tests + impact "cover ... for status, ... button texts/status_emoji + ... + _build_progress_bar math"); re-run full Test* classes in F4; keep all consts.
- Riesgo: LOC sigue =50 por docstring/boilerplate → Mit: trim docstring del helper (mantener contrato) + comentario "extracted for <=50 LOC rule (Item 7 / arch-enforcer)", precedente item2 F3; usar inspect en gate.
- Riesgo: logging nuevo introduce ruido → Mit: seguir exactamente el patrón de item2 / otros handlers ("módulo | acción | user_id= | resultado"); mismo logger.
- Riesgo: rel access None cases → Mit: guard "if not mission or not mission.reward" ya presente + tests F4 cubren el path "without reward" seteando .reward=None explícitamente (precedent item2 F4).

**Safe point:** Post-ruff + LOC<=50 verificado via inspect + grep 0 RewardService + 1svc + GSD "F3 safe point - reward_detail <=50 via pure helpers (compute_reward_status_text + build_reward_detail_keyboard); 1 service only via MissionService get_service + rel + pure emoji; UI render identical; logging compliant". El handler recompila; tests de F4 validarán el contrato observable. Reversible editando solo este archivo (o inlining los helpers).

---

### Fase 4: Port/actualización de tests de reward_user_handlers + agregar tests para helpers puros extraídos

**Objective:** Actualizar/confirmar `test_reward_user_handlers.py` para que los tests reflejen (y protejan) el diseño "exactly 1 service" + pure helpers. Añadir clase `TestRewardUserPureHelpers` (o equivalente) con unit tests puros para los helpers extraídos (sin parches pesados; import inside per convención de archivos de test; cubrir branches de status, RewardTypes, buttons, progress bar, detail text). Remover cualquier residual 2-svc language. Ruff + full suite del archivo verde (comportamiento idéntico). GSD pre. Safe point.

**DoD checklist:**
- [ ] 0 parches de `RewardService` en el archivo de tests (ni @patch ni referencias directas en setups/asserts para las funciones bajo test; ya limpio per F1 pero confirmar).
- [ ] Todos los tests usan `@patch("handlers.reward_user_handlers.get_service")` + `mock_get_service.return_value.__enter__.return_value = mock_instance` + `__exit__` asserts en closes.
- [ ] Setups configuran mock_reward con `.reward_type = RewardType.BESITOS` (etc) + `.besito_amount` + `.name` para que la **real pure** get_reward_emoji se ejecute en _builds.
- [ ] Para paths de detail: `mock_mission.reward = mock_reward` (rel); sin-reward: `.reward = None`.
- [ ] Tests de close usan patrón de context (`__exit__` assert) per mission precedent + item2 F4.
- [ ] Docstrings de clases actualizadas/confirmadas: "Tests ported to 1-service pattern (get_service + MissionService only) + pure formatting via get_reward_emoji. Arch-enforcer note addressed."
- [ ] Nueva clase `TestRewardUserPureHelpers` (o Test*PureHelpers): tests unitarios para los helpers extraídos (al menos 5-6 casos: status completed vs in-progress with bar math, 3+ RewardType for emoji+gives via real pure or if render helpers, button text/status_emoji + truncation + packed cb data, progress bar edges 0/50/100, detail text with None descs; import inside test funcs per convención del archivo).
- [ ] Todos los asserts de texto, llamadas a edit_text/answer, y parámetros de servicio (user_id, mission_id) se mantienen y pasan (comportamiento idéntico).
- [ ] Ruff limpio en el test.
- [ ] GSD pre + gate: la suite completa del archivo pasa verde.
- [ ] Safe point.

**Archivos:** `tests/handlers/test_reward_user_handlers.py`

**Cambios clave (bullets accionables, por clase; copiar al pie de la letra de item2 F4 port + test_mission_user_handlers precedent):**
- Pre-log GSD "pre-edit tests/handlers/test_reward_user_handlers.py (F4 add pure helper tests + confirm ports) - refs DoD F4 + copy from item2 PLAN F4 (RewardType import, get_service patch, __enter__/__exit__, mock_mission.reward=, .reward_type for pure, docstrings 'ported...', closes to __exit__, NOTES cleaned) + item2 F5 TestCalculate... class (5 tests, import inside); read pre done".
- Añadir/confirmar al top (si no): `from models.models import RewardType`
- En TestShowAvailableRewards y TestRewardDetail (ya portados en tree; confirmar/refresh setups):
  - Cada test: `@patch("handlers.reward_user_handlers.get_service")`
  - `mock_instance = MagicMock(); mock_get_service.return_value.__enter__.return_value = mock_instance`
  - Para list: `mock_reward.reward_type = RewardType.BESITOS; mock_reward.besito_amount = 10`
  - Para detail: `mock_mission.reward = mock_reward; mock_reward.reward_type=...`
  - Closes: `mock_get_service.return_value.__exit__.assert_called_once()`
  - Asserts on mission methods only (get_mission, get_or_create_progress, get_available...); no reward_svc.
- Añadir al final del archivo (después de la última clase; patrón de item2 F5):
  ```python
  class TestRewardUserPureHelpers:
      """Tests para los helpers puros extraídos de reward_user_handlers (Item 7 / arch-enforcer LOC)."""

      def test_compute_reward_status_text_completed(self):
          from handlers.reward_user_handlers import compute_reward_status_text
          progress = MagicMock(is_completed=True)
          mission = MagicMock()
          assert "completada" in compute_reward_status_text(progress, mission).lower()

      def test_compute_reward_status_text_in_progress(self):
          from handlers.reward_user_handlers import compute_reward_status_text
          progress = MagicMock(is_completed=False, current_value=3)
          mission = MagicMock(target_value=10)
          status = compute_reward_status_text(progress, mission)
          assert "Progreso" in status
          assert "3 / 10" in status

      def test_build_reward_detail_keyboard(self):
          from handlers.reward_user_handlers import build_reward_detail_keyboard
          from keyboards.callback_data import MissionDetailCallback
          kb = build_reward_detail_keyboard(42)
          assert len(kb.inline_keyboard) == 2
          assert "Ver mision" in kb.inline_keyboard[0][0].text
          assert "Volver a recompensas" in kb.inline_keyboard[1][0].text
          # cb data packed contains mission_id
          assert "42" in kb.inline_keyboard[0][0].callback_data

      # + casos para _build_progress_bar si se considera helper a testear, RewardType branches vía real get_reward_emoji (o si un helper render lo usa), detail text con Nones, etc.
      def test_build_progress_bar_edges(self):
          from handlers.reward_user_handlers import _build_progress_bar
          assert _build_progress_bar(0, 10)[1] == 0
          assert _build_progress_bar(5, 10)[1] == 50
          assert _build_progress_bar(10, 10)[1] == 100
  ```
- (Usar import inside test funcs para seguir el patrón del archivo, que hace `from handlers... import reward_detail` dentro de cada test.)
- Post-add: ruff check + format (apply si dirty); full pytest del archivo; grep residual RewardService ==0; asserts de textos idénticos.

**Tests que deben pasar antes de avanzar:**
- `./venv/bin/python -m pytest tests/handlers/test_reward_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` → todos verdes (comportamiento idéntico: mismos textos, calls, alerts, params on mission only, __exit__).
- Ruff en el test file.
- Grep: `grep -n "RewardService" tests/handlers/test_reward_user_handlers.py | grep -v "NOTE\|arch-enforcer\|pre-existing"` → preferiblemente 0; get_service patches + RewardType + new helper tests presentes.

**Riesgos + mitigaciones:**
- Riesgo: tests que confiaban en mocks de get_reward_emoji ahora ejecutan la real y fallan por attrs faltantes → Mit: configurar explícitamente `.reward_type` y campos dependientes en cada setup (ya hecho en tree + item2 F4); 5-10 min por test pero precedentes existen.
- Riesgo: el test "without reward" falla porque MagicMock.reward es truthy → Mit: setear explícitamente `.reward = None` (documentado en item2 + impact).
- Riesgo: nuevos helper tests fallan por nombre/firma → Mit: nombres confirmados en F3 GSD1 + sección 4 del PLAN; ajustar en F4 primer GSD si difiere (mantener espíritu).
- Bajo: import RewardType → si choca, usar la instancia del enum (pure compara con RewardType.BESITOS directo).

**Safe point:** Suite de reward_user_handlers verde post-F4 (incl nuevos helper tests) + ruff + GSD "F4 safe point - reward handler tests confirmed ported to 1-service + pure emoji + rel; new TestRewardUserPureHelpers added + pass; arch-enforcer notes addressed; behavior identical". Confirma que el render de rewards list/detail (y helpers) es idéntico. Reversible restaurando setups viejos (pero no necesario).

---

### Fase 5: Re-runs de golds + verificación final de reglas + self-check + handoff (primero de nuevo pool de 4; batch anterior cerrado)

**Objective:** Re-ejecutar los golds que protegen el flujo de rewards (handler test full + cross flows reward/mission + atomicity/mission paths que tocan deliver/reward list indirectamente). Verificar reglas (1 service, LOC<=50, logging, pure helpers, 0 RewardService en handler). Completar GSD log con self-check PASSED explícito + lista de "tests críticos a re-correr en futuro". Confirmar en self-check/PLAN: "este es el primero de un nuevo pool de 4, y que el batch anterior de 4 quedó cerrado con tests pasando" (citar 24-SUMMARY "BATCH: 4 items completed in this tirón (Item 6 final of max 4)" + "Item 6/24 closed..." + self-check PASSED). Handoff a arch-enforcer/test-guardian + gsd-executor del siguiente item del pool. Safe point final.

**DoD checklist:**
- [ ] Re-runs: full `pytest tests/handlers/test_reward_user_handlers.py ...` green; targeted cross `pytest -k "reward or mission or TestReward or deliver_reward or TestCrossServiceAtomicity or TestMissionE2E" -q --tb=line -p no:cov --override-ini="addopts="` (o más amplio filtrado; documentar pre-exist unrelated); bot smoke `python -c "import bot; print('routers incl reward_user ok')" ` or equivalent.
- [ ] Ruff limpio en los 3 archivos tocados.
- [ ] Verificación de reglas (grep/inspect manual + en log):
  - `grep -n "RewardService" handlers/reward_user_handlers.py` → 0 (active).
  - `python -c 'import inspect; from handlers.reward_user_handlers import reward_detail; print("reward_detail LOC:", len(inspect.getsourcelines(reward_detail)[0]))'` → <=50.
  - Logging formato "reward_user_handlers | ..." presente en show + detail (spot o grep).
  - get_service(MissionService) + rel + pure emoji en handler; helpers puros usados + tests added.
  - 1 service rule + <=50 + logging + pure helpers + no biz logic en handler.
- [ ] GSD entries completas para F5 + log final con self-check PASSED + estructura completa (lista de fases/DoD/gates/archivos modificados/tests que pasaron/reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0 behavior chg, 1svc+rel+pure, LOC<=50, logging, pure helpers tests, no prod chg)/desviaciones/tests críticos para futuro (reward handler test full, cross reward/mission flows, atomicity reward paths, bot smoke, ruff+greps+LOC)/"Item 7/25 closed. First of new pool of 4. Previous batch of 4 (Item 6/24 remaining-besito + priors) closed with tests passing per 24-SUMMARY BATCH note + self-check PASSED. Ready for arch-enforcer re-scan (enfocado en reward handlers: exactly 1 service + <=50L + no RewardService) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4").
- [ ] Self-check explícito "Self-Check: PASSED".
- [ ] (Opcional pero recomendado) SUMMARY.md en el dir de la phase con executive + refs al log + comandos de re-verif (sigue estructura de 24/23/20/19).
- [ ] Safe point final + criterio de éxito del plan.

**Archivos:** Ninguno nuevo (solo log + opcional SUMMARY; los edits ya hechos en F2-F4).

**Cambios clave:** Solo ejecución de comandos (ver Instrucciones) + echo al log. Usar run_terminal para los gates finales + conteos + greps + self-check append.

**Tests gates (obligatorios):**
- Los re-runs targeted + full handler test.
- Ruff global en los 3.
- Greps + inspect LOC + smoke bot.
- GSD pre cada + "F5 FINAL + self-check PASSED + BATCH/POOL note".

**Riesgos + mitigaciones:**
- Riesgo: re-runs muestran flakes preexistentes (no causados por este Item) → Mit: usar -p no:cov --override-ini; documentar si hay 1 unrelated fail (precedente 24/23/22); enfocar "0 regressions atribuibles a los helpers o ports".
- Riesgo de tiempo: chains de integración lentas → Mit: priorizar targeted del handler test primero, luego -k específicos de reward/mission; el PLAN permite targeted combinados.
- Ninguno nuevo (verif final; scope tight).

**Safe point final + criterio de éxito:** Todos DoD de F5 + self-check PASSED en log con la nota explícita de "primero de nuevo pool de 4" + "batch anterior de 4 cerrado con tests pasando". El plan completo + log GSD son evidencia para el siguiente agente (gsd-executor next item o arch-enforcer/test-guardian). 0 breakage; UI idéntica; reglas cumplidas; 3 sistemas críticos (gamif/missions/rewards etc.) protegidos (read-only, 1 service, pure, <=50).

---

## 3. Estrategia de tests general (port + nuevos + re-runs)

**Confirmación de ports en test_reward_user_handlers (F4, ya en tree pero refresh):**
- Seguir exactamente el patrón de `tests/handlers/test_mission_user_handlers.py` (y el port de reward en phase20 F4 / item2 log): @patch("handlers.reward_user_handlers.get_service"), mock_get_service.return_value.__enter__.return_value = mock_instance, asserts en __exit__.assert_called (o en el mock_context), remoción de parches a RewardService (ya 0), mantener todos los asserts de UI (edit_text, answer, textos producidos como "Recompensas Disponibles"/"completada"/"Progreso"/"3 / 10", botones/callbacks) idénticos.
- Configurar los mocks de reward con los atributos que la pure `get_reward_emoji` necesita (RewardType enum: BESITOS/PACKAGE/VIP_ACCESS; campos besito_amount, name, etc.). Usar `mock_mission.reward = mock_reward` para el acceso por relationship en reward_detail (y .reward=None para el path sin reward).
- Actualizar/confirmar docstrings de clases a "Tests ported to 1-service pattern (get_service + MissionService only) + pure formatting via get_reward_emoji. Arch-enforcer note addressed." (ya presentes; refresh si residual 2-svc language).

**Nuevos tests para pure helpers extraídos (F4):**
- Ubicación: `tests/handlers/test_reward_user_handlers.py` (mismo archivo; mantiene todo co-localizado y evita nuevos archivos per scope tight + precedent item2 F5).
- Enfoque: unit tests puros del helper (datos de entrada falsos con MagicMock mínimos o simples objetos; no service mocks necesarios para los helpers mismos; import inside test funcs per convención del archivo).
- Casos mínimos (copiar espíritu de TestCalculateEmojiCountsFromReactions en item2 F5 + impact "cover empty/completed/progress for status, different RewardType for emoji+gives, button texts/status_emoji + truncation + packed cb data, _build_progress_bar math, detail text with Nones"):
  - status completed → contiene "completada".
  - status in-progress → contiene "Progreso", "X / Y", barra con █/░.
  - build keyboard → 2 botones, textos correctos, cb data packed con mission_id.
  - progress bar edges (0/50/100).
  - (si un helper render toca emoji) real get_reward_emoji via mock_reward attrs or direct call.
  - detail text construction with None descs (sin crashear, usa defaults).
- Estos tests sirven como "test-guardian" para los helpers: cualquier refactor futuro del render de rewards list/detail debe pasar estos.

**Re-runs de golds (F5, y spot en F1/F3/F4):**
- Handler level: `pytest tests/handlers/test_reward_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts="`
- Cross / mission-reward flows (gold paths que ejercitan list/detail o reward data): `pytest -k "reward or mission or TestReward or TestMission or deliver or TestCrossServiceAtomicity" -q --tb=line -p no:cov --override-ini="addopts="` (filtrar; documentar pre-exist unrelated como daily concurrent o alembic per precedent 24/23).
- Objetivo: confirmar que el código de render (ahora delegando a helpers puros) produce los mismos textos, botones, alerts, y que los calls a servicio siguen siendo solo MissionService via get_service.
- (Nota: los tests de integración actuales pueden no asertar el contenido exacto del UI de rewards list/detail directamente; para "idéntico" el executor usa los asserts existentes del handler test + nuevos helper tests que pin strings/math; re-runs de chains protegen indirectamente via mission/reward data paths.)

**Gates generales por fase / final:**
- Ruff: `./venv/bin/python -m ruff check <file> --fix` ; luego `./venv/bin/python -m ruff format --check <file>` (o apply en pre si se sigue el precedente de ruff pre-edit + hygiene como chore separado 0 logic).
- Pytest targeted limpio (sin cov para exit code estable): siempre con `-p no:cov --override-ini="addopts="` (precedente establecido en todos los golds 20/21/23/24 + item logs).
- Grep de reglas: 0 "RewardService" en reward_user_handlers.py (activo); LOC de reward_detail <=50 via inspect; imports de get_service + pure presentes; logging formato presente (spot); helpers puros usados + tests.
- (Opcional para executor) smoke de bot import o registro de routers si se quiere (`python -c "import bot; print('ok')" ` o equivalente para reward router), pero mínimo es el handler test + cross targeted.
- Cobertura de logging requirement: los tests no asertan logs usualmente (salvo en middleware tests); el gate es manual grep o inspección durante las ediciones + inclusión en el log de GSD.

---

## 4. Decisiones de diseño que el executor debe confirmar (o registrar desviación en el primer GSD entry de la fase relevante)

1. **Nombres de los helpers puros extraídos:** `compute_reward_status_text(progress, mission) -> str` (o `build_reward_status_text`); `build_reward_detail_keyboard(mission_id: int) -> InlineKeyboardMarkup`. (Siguen convención proyecto: verbo + contexto + resultado; cf. `calculate_emoji_counts_from_reactions` en item2 / `calculate_user_besitos_from_reactions` en codebase.) Confirmar o elegir alternativa equivalente en primer GSD de F3; documentar. Si se extrae un tercero (e.g. para button text en list), nombre similar y cubrir en tests.
2. **Delegate backward-compatible para get_reward_emoji:** Ya presente (Item2); en F2 solo confirmar + asegurar el comentario "# Backward-compatible delegate added for Item 2 (arch-enforcer 1-service rule for reward handlers)." + docstring del delegate. 1-línea; pura a nivel módulo antes de la clase.
3. **Logging en los handlers editados:** Agregar/confirmar logs en formato "módulo | acción | user_id=... | resultado=..." para show_available_rewards (con count) y reward_detail (con mission_id + completed). Si los handlers actualmente delegan logging a middleware, mínimo es asegurar el log existente dentro del with post-data. Confirmar formato con ejemplos de item2 / otros (e.g. "reward_user_handlers | reward_detail | user_id=123 | mission_id=5 | completed=False").
4. **Patrón de tests para pure emoji + helpers:** Ejecutar la real `get_reward_emoji` sobre MagicMocks configurados con `.reward_type` y campos (opción preferida para simplicidad y "pure" semantics; ya en tree + item2). Para los nuevos helpers de render: tests puros (import inside, mocks mínimos o datos simples); no patch del helper en los tests del handler (el handler test ya cubre el flujo completo vía real). Si se aísla, usar @patch local pero preferir real per "pure = fácil de testear".
5. **Chequeo de relationship en reward_detail:** Mantener `if not mission or not mission.reward:` (consistente con mission_detail en mission_user_handlers + item2). Mensaje de alert "Recompensa no encontrada". No agregar chequeos de is_active en el handler (scope tight; list ya filtra en service).
6. **Conteo estricto de ≤50 LOC:** Usar `inspect.getsourcelines(func)[0]` (cuenta líneas de la def inclusive) o equivalente `sed -n 'X,Yp' | wc -l`. Si queda en 51 por docstring, aplicar trim de docstring del helper (mantener contrato) + comentario de "extracted for LOC rule (Item 7 / arch-enforcer)", precedente de credit_besitos en Item1 + handle_reaction en item2 F3. No dejar >50. Verificar post-F3 y en F5 final.
7. **Actualización de docstrings de tests de reward:** Confirmar/refresh las notas de "1-service" y "Arch-enforcer note addressed" (ya en tree post-item2; asegurar que residual "2-svc" o "closes_both" language está limpia). Dejar comentario histórico breve si se desea ("pre-Item 2/7 this orchestrated...; now 1-service per arch-enforcer remediation").
8. **Log file para GSD de Item 7:** Usar `.planning/quick/gsd-reward-handlers-1service-loc.log` (o el item7 completo si el analyzer usó gsd-impact-analyzer-item7-reward-handlers-1service-loc.log; cross-ref ambos). Cada pre-edit/pre-gate/pre-verif debe hacer `echo "=== $(date -Iseconds) | PHASE N | GSD pre-... - <descripción corta refs DoD + patrones copiados>" >> <logfile>"` (o usar run_terminal_command con comando echo/printf). Al final del Item, el log debe tener entradas para cada acción significativa (como los 46+ de Item 2) + self-check PASSED + BATCH/POOL note.
9. **Si se necesita un segundo (o tercer) helper para render en rewards:** Solo si el conteo de LOC de reward_detail no baja suficiente con status + keyboard. El helper de button text en list (si se extrae) puede ser puro. Si no se extrae más, documentar por qué el LOC ya cumplía post los dos principales (tight scope prioriza mínimo).
10. **No exportar la pura en services/__init__.py:** Confirmado por scope (import directo del módulo es suficiente y usado en el codebase + item2). No editar __init__.
11. **Cualquier decisión que difiera:** Registrar en el GSD log + (si se permite fuera de scope estricto) en una nota breve al final del PLAN o en SUMMARY posterior. Elegir conservadoramente siguiendo precedentes (item2, mission handlers, impact examples).

Cualquier decisión que difiera de lo anterior debe registrarse en el GSD log + nota breve al final del PLAN o en SUMMARY.

---

## 5. Criterios de verificación + gates finales + lista de comandos

**Criterios de éxito del Item (medibles, para self-check del executor):**
- Los handlers de reward (show_available_rewards, reward_detail, _build_rewards_buttons) no contienen ninguna referencia activa a RewardService (import o uso) — grep ==0.
- Usan exclusivamente `get_service(MissionService)` vía context manager (with) + relationship para reward + pure get_reward_emoji importada; exactamente 1 service por entrypoint.
- reward_detail + helpers relevantes ≤50 LOC fuente (inspect <=50; prefer <50); helpers puros extraídos (compute_reward_status_text, build_reward_detail_keyboard o equivalentes verb+context+result) y usados para el render.
- Todos los tests en `test_reward_user_handlers.py` pasan post-F4 (con get_service, rel, pure emoji real, __exit__, nuevos helper tests; textos/calls/alerts/params idénticos).
- Re-runs de golds (handler test + cross reward/mission/atomicity paths) pasan sin regressions atribuibles a la extracción o ports.
- Ruff clean en los 3 archivos modificados.
- Verificaciones de reglas:
  - `grep -c "RewardService" handlers/reward_user_handlers.py` (activo) == 0
  - LOC reward_detail <=50 via inspect
  - Logging formato "reward_user_handlers | <action> | user_id=... | ..." presente en las dos rutas principales
  - 1 service + pure helpers + get_service context + rel access + no biz logic en handler
  - GSD pre every (counts 5-10+/fase target; wc tracked)
- GSD log completo con pre-entries + self-check "PASSED" + lista explícita de "tests críticos a re-correr en el futuro para estos handlers/helpers" (el handler test full; cross -k reward|mission|TestReward|TestMission|atomicity reward paths; bot smoke; ruff + greps + LOC verifiers) + nota "Item 7/25 closed. This is the first of a new pool of 4. The previous batch of 4 (ending with Item 6/24 remaining-besito-compositions) closed with tests passing, self-check PASSED, and explicit BATCH note per its SUMMARY and gsd log." + "Ready for arch-enforcer re-scan (enfocado en reward handlers: exactly 1 service + <=50L + no RewardService) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4".
- Comportamiento de usuario final idéntico (lista y detalle de rewards muestran mismos emojis/nombres/textos/barras/alertas/navegación; helpers no cambian el contrato observable).
- Safe point final documentado; item listo para guardians + siguiente del pool.

**Gates por fase (ver secciones de fases para detalles; siempre GSD pre antes):**
- Pre-edit / pre-gate / pre-verif / pre-ruff / pre-pytest / pre-grep / pre-smoke / pre-final: append al log.
- Post-edit: ruff + targeted pytest (cuando aplique) + smoke + grep/LOC checks + GSD entry de resultado.
- Avanzar solo si gate verde (o documentar desviación menor en log).
- F5: re-runs obligatorios de golds + broader smoke filtrado + self-check + BATCH/POOL note.

**Comandos concretos sugeridos (copiar al pie de la letra en ejecución; usar run_terminal_command):**
```
# GSD (siempre pre)
echo "=== $(date -Iseconds) | PHASE N | GSD pre-... <file> (<motivo>) - <desc + refs DoD + patrones copiados al pie de la letra de item2 PLAN F4 + gsd-reward-gamif-item2.log + 24 SUMMARY BATCH + impact report>" >> .planning/quick/gsd-reward-handlers-1service-loc.log
wc -l .planning/quick/gsd-reward-handlers-1service-loc.log

# Ruff (con --fix si hygiene)
./venv/bin/python -m ruff check handlers/reward_user_handlers.py services/reward_service.py tests/handlers/test_reward_user_handlers.py --fix
./venv/bin/python -m ruff format --check handlers/reward_user_handlers.py services/reward_service.py tests/handlers/test_reward_user_handlers.py

# Pytest targeted (siempre con estos flags para exit limpio; precedente todos los golds)
./venv/bin/python -m pytest tests/handlers/test_reward_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -m pytest -k "reward or mission or TestReward or TestMission or deliver or TestCrossServiceAtomicity or atomicity" -q --tb=line -p no:cov --override-ini="addopts="

# Grep rules + 1svc
grep -n "RewardService" handlers/reward_user_handlers.py
grep -n "get_service(MissionService)\|from services import get_service\|from services.reward_service import get_reward_emoji" handlers/reward_user_handlers.py
grep -n "compute_reward_status_text\|build_reward_detail_keyboard" handlers/reward_user_handlers.py

# LOC (inspect gold)
./venv/bin/python -c '
import inspect
from handlers.reward_user_handlers import reward_detail, show_available_rewards, _build_rewards_buttons
for name, fn in [("reward_detail", reward_detail), ("show_available_rewards", show_available_rewards), ("_build_rewards_buttons", _build_rewards_buttons)]:
    src = inspect.getsourcelines(fn)[0]
    print(f"{name} LOC: {len(src)}")
'

# Smoke import + pure + helpers
./venv/bin/python -c "
from handlers.reward_user_handlers import show_available_rewards, reward_detail, compute_reward_status_text, build_reward_detail_keyboard
from services.reward_service import get_reward_emoji, RewardService
print('imports + helpers ok')
from unittest.mock import MagicMock
from models.models import RewardType
r = MagicMock(reward_type=RewardType.BESITOS, besito_amount=10, name='Test')
print(get_reward_emoji(r))
print('pure ok')
"

# Bot smoke (router registration)
./venv/bin/python -c "
import bot
print('bot import + routers (incl reward_user) ok')
"

# Combined critical re-run (F5)
./venv/bin/python -m pytest -k "reward or mission or TestRewardUser or TestReward or TestMission or deliver or TestCrossServiceAtomicity or atomicity or TestMissionE2E" -q --tb=line -p no:cov --override-ini="addopts="
```

---

## Instrucciones para el gsd-executor

Este PLAN.md ES tu prompt de ejecución. Síguelo al pie de la letra, sin scope creep. El trabajo es para UNA persona (tú) + disciplina GSD total. El flujo debe continuar automáticamente con gsd-executor para este item (y luego los siguientes 3 del pool de 4). 

**CONFIRMACIÓN OBLIGATORIA (incluir en tu output final y en el self-check del log):** Este es el primero de un nuevo pool de 4 (Item 7 / 25-reward-handlers-1service-loc, post-unificación de Besito). El batch anterior de 4 quedó cerrado con tests pasando: ver .planning/phases/24-remaining-besito-compositions/24-remaining-besito-compositions-SUMMARY.md ("**BATCH:** 4 items completed in this tirón (Item 6 final of max 4). ... Item 6/24 closed. BATCH: 4 items completed in this tirón (final of max 4). **Status:** COMPLETE - Self-Check: PASSED") + su gsd-remaining-besito-compositions.log (self-check PASSED + BATCH COMPLETE NOTE al final) + re-runs verdes en F5 de ese item.

1. **GSD discipline (non-negotiable, como en todas las phases exitosas 20/21/23/24 + item2/5/6 logs):**
   - ANTES de **cualquier** modificación (search_replace/write/edit en fuentes o log o SUMMARY), antes de ruff, pytest, grep de verif, smoke, o resumen: append al log.
   - Log: `.planning/quick/gsd-reward-handlers-1service-loc.log` (cross-ref gsd-impact-analyzer-item7-reward-handlers-1service-loc.log del analyzer si útil).
   - Crea/append al archivo si necesario (planner ya hizo INIT + pre-mkdir + pre-write con 2 entries; wc tracked; primer entry de executor puede confirmar + wc).
   - Formato de entry (copia estilo **al pie de la letra** de gsd-reward-gamif-item2.log / gsd-remaining-besito-compositions.log / gsd-reward-besito-eventbus.log / gsd-getservice-unification.log):
     ```
     === 2026-06-08Txx:xx:xx+00:00 | PHASE 3 | GSD pre-edit handlers/reward_user_handlers.py (F3 extract pure helpers + ensure 1svc) - Agregar compute_reward_status_text + build_reward_detail_keyboard (puros, verb+context+result); slim reward_detail de 50L a <=50; mantener with get_service(MissionService) + rel mission.reward + pure get_reward_emoji; refs DoD F3 + copy snippets from item2 PLAN F2 (with+log+rel) + F3 (pure helper insert + body replace + inspect LOC) + current handler lines 100-150 + impact report helper examples; read pre done; patrones de item2/5/6.
     ```
     Luego ejecuta el comando de edit/tool.
   - También pre-gate (pre-pytest, pre-ruff, pre-grep "RewardService|get_service", pre-inspect LOC, pre-final-self-check, pre-SUMMARY si produces).
   - Cuenta las entradas; apunta a varias por fase (5-10+ totales por fase como precedentes item2 46+, 24 55+). Al final del Item el log debe tener el self-check completo + BATCH/POOL note.
   - Usa `run_terminal_command` con `echo "=== $(date -Iseconds) | PHASE N | ..." >> .planning/quick/gsd-reward-handlers-1service-loc.log` (o printf). Nunca edites sin pre-log. wc -l después de appends clave.

2. **Orden estricto:** Ejecuta Fase 1 → gates → Fase 2 → gates → Fase 3 → gates → Fase 4 → gates → Fase 5 (re-runs + verif final + self-check + POOL/BATCH confirm). **No saltes fases ni hagas "todo de una".** Marca DoD mentalmente o en el log al completar cada checklist. Al final de cada fase documenta "F<N> safe point" + "F<N> COMPLETE" en log (como item2 log).

3. **Herramientas y comandos concretos (usa run_terminal_command para estos; copia los de sección 5 + precedents):**
   - GSD logs + wc: `echo "..." >> log; wc -l log`
   - Mkdir (si planner no lo hizo completamente): `mkdir -p .planning/phases/25-reward-handlers-1service-loc`
   - Ruff: `./venv/bin/python -m ruff check <file> --fix` ; `./venv/bin/python -m ruff format --check <file>` (apply si "would reformat" como chore 0 logic per precedent 24/23).
   - Pytest targeted (siempre con estos flags para exit limpio): `./venv/bin/python -m pytest <path or -k "expr"> -q --tb=line -p no:cov --override-ini="addopts="`
     - Ejemplos exactos en sección 5 arriba + item2 F4/F5 / 24 F5.
   - Grep de reglas: `grep -n "RewardService" handlers/reward_user_handlers.py` (0); `grep -n "get_service(MissionService)\|from services.reward_service import get_reward_emoji" ...`; `grep -n "compute_reward_status_text\|build_reward_detail_keyboard" ...`
   - LOC (siempre inspect): `./venv/bin/python -c 'import inspect; from handlers.reward_user_handlers import reward_detail; src=inspect.getsourcelines(reward_detail)[0]; print("reward_detail LOC:", len(src))'`
   - Smokes: `./venv/bin/python -c "from handlers... import ...; from services.reward_service import get_reward_emoji; ..."` (4 branches pure + delegate + helpers); bot `python -c "import bot; print('ok')"`
   - Evita sleeps; usa comandos directos. Si tool soporta background para integ lentas, úsalo pero log secuencial prefer.
   - Al final: re-ejecuta los combinados + broader smoke filtrado por reward/mission + self-check en log + (opt) write de SUMMARY.

4. **Patrones a copiar (no reinventar; **al pie de la letra** de golds):**
   - Patrón get_service + with + mock en tests + closes __exit__: copia de `tests/handlers/test_mission_user_handlers.py` + item2 F4 port (RewardType import, get_service patch, mock_instance + __enter__, mock_mission.reward = , .reward_type for real pure, closes to __exit__, calls asserts on mission only, docstrings "ported to 1-service... Arch-enforcer note addressed", NOTES cleaned).
   - Extracción de helper puro para LOC + UI idéntica: copia espíritu + snippets de F3 de item2 (insert pure calculate_... near section; replace inline with call; docstring "Calcula... Función pura."; inspect LOC post; test refresh path green; 1 helper if suficiente; trim docstring si 51 por boilerplate + comentario "extracted for LOC rule (Item X)").
   - Logging: "módulo | acción | user_id=... | resultado=..." (copiar de item2 F2 logs para show/reward_detail + F3 para handle_reaction).
   - 1-line / min support + delegate comment: de item2 F1 (pura + delegate 1-line + "Backward-compatible delegate added for Item 2 (arch-enforcer...)").
   - GSD entries detalladas: "pre-xxx <file> (F<N> <motivo>) - <desc + refs DoD + patrones copiados al pie de la letra de item2 PLAN F4 + gsd-reward-gamif-item2.log + impact report helper examples + 24 SUMMARY BATCH>"; wc; style de item2 (46+ entries) y 24 (55+).
   - Safe points + self-check al final del log: estructura de item2 (lista fases/DoD/gates/archivos/tests que pasaron/reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0, 1svc+rel+pure, LOC<=50, logging, pure helpers tests, no prod chg)/desviaciones/tests críticos/"Item closed. Ready for ... + arch-enforcer + test-guardian + siguiente item del pool") + 24 BATCH note.
   - Precedentes PLAN/GSD + handoff + pool/batch: .planning/phases/20-.../PLAN.md + gsd-reward-gamif-item2.log (Item2 reward 1svc gold), 23/24 PLANs + SUMMARYs (BATCH "4 items completed in this tirón (Item 6 final of max 4)", "Item 6/24 closed. BATCH...", self-check), impact report .md (source of truth for scope/map/risks/tests/ "first of new pool of 4").
   - VOZ/estilo: handlers hablan vía textos ya existentes (Lucien voice preservado idéntico); no cambiar mensajes de usuario.
   - 3 sistemas críticos: siempre en mente (gamif/missions/rewards como el dominio aquí; narrative cross via events; channel/VIP); este item es read-only info (0 tx/credit/deliver/claim); re-runs de cross protegen.

5. **Decisiones (sección 4 del PLAN):** Al inicio de la fase relevante (primer GSD entry de la fase), registra qué decidiste para "nombre de helper", si trimmaste docstring para LOC, cómo manejaste logging, etc. Si difieres del "preferido", explica brevemente (mantén espíritu tight + gold + 0 behavior + UI idéntica).

6. **Gates y re-runs:** 
   - Corre los targeted pytest con los flags exactos de sección 5 ( -p no:cov --override-ini="addopts=" ).
   - Si un unrelated fail preexistente aparece (ej. alembic_heads, daily concurrent UNIQUE, cross daily !success pre patch en priors), documéntalo en log pero **no lo cuentes como regression del Item** (precedente 24/23/22/20/19 "Riesgo: baseline shows pre-existing unrelated fails ... document; do not count").
   - Re-run de handler test full + cross reward/mission flows es obligatorio en F5 (y spot en F1/F3/F4).
   - Siempre GSD pre- antes del pytest/ruff/grep grande.
   - Al final F5: re-ejecuta los combinados + broader smoke filtrado + self-check + POOL/BATCH confirm.

7. **Alcance (recuerda siempre):** Solo edita los archivos listados en "Archivos que se modificarán" + el log GSD + (este PLAN ya está) + opcional SUMMARY.md al final. Si sientes la tentación de "limpiar más handlers", "tocar mission_service para orchestration", "agregar tests fuera del reward_user test file", "editar CLAUDEs o decisions", "cambiar behavior de claim/delivery", detente: scope tight para esta entrega (recomendado por impact + "first of new pool of 4" + "0 otros handlers" + "0 changes in delivery/claim" + "0 mission_service changes"). El analyzer + user prompt + precedents recomiendan empezar tight aquí.

8. **Al final del Item (F5):**
   - Completa el self-check en el log (lista de fases, DoD cumplidos, archivos modificados, tests que pasaron, reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0, 1svc+rel+pure, LOC<=50 via inspect, logging, pure helpers tests, no prod chg), desviaciones (si las hubo; ej. ruff hygiene como chore 0 logic per 24), tests críticos para futuro (lista explícita), "Item 7/25 closed. This is the first of a new pool of 4. The previous batch of 4 (ending with Item 6/24 remaining-besito-compositions) closed with tests passing per 24-SUMMARY BATCH note + self-check PASSED. Ready for arch-enforcer re-scan (enfocado en reward handlers: exactly 1 service + <=50L + no RewardService) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4").
   - (Opcional pero recomendado) Produce `.planning/phases/25-reward-handlers-1service-loc/SUMMARY.md` con executive + refs al log + comandos de re-verificación (sigue estructura de 24/23/20/19).
   - Confirma en log: "Self-Check: PASSED".
   - El siguiente agente (gsd-executor next item o arch-enforcer/test-guardian) usará el log + este PLAN + los cambios como fuente de verdad.

9. **Si algo no está claro o difiere del "reporte del impact-analyzer" o user prompt:** El prompt del usuario + este PLAN (basado en discovery completa + el reporte completo en .claude/.../item7-...md + handoff de 24-SUMMARY + gsd logs de item2/5/6/24 + código actual + precedents PLAN 20/21/23) es la fuente de verdad. Pregunta solo si un gate bloquea por ambigüedad real de nombre/firma/contrato (e.g. nombre exacto del helper); de lo contrario, elige conservadoramente siguiendo precedentes (item2 ports + helper extract + LOC inspect + self-check, mission 1svc+rel, impact examples for status/keyboard, 24 BATCH language) y registra la elección en GSD.

**¡Ejecuta con disciplina total. Cierra el Item de forma limpia, segura, medible y con trazabilidad GSD completa. La consolidación de los reward handlers (1 service Mission-only + pure helpers para <=50L + tests) queda hecha sin impacto en los 3 sistemas críticos ni en los contratos de entrega/claim/partial failure. UI idéntica. Listo para arch-enforcer + test-guardian + siguiente item del pool de 4 (flujo continúa automáticamente).**

---

**Fin del PLAN para 25-reward-handlers-1service-loc (Item 7, first of new pool of 4).**

Referencias rápidas para el executor (actualizar con líneas reales durante ejecución si cambian):
- Impact report (source of truth): .claude/agent-memory/impact-analyzer/item7-reward-handlers-1service-loc.md (mapa, risks, scope 3 files, "first of new pool of 4", helper examples _compute... / _build..., tests add helper tests, 0 behavior/0 other handlers/0 mission_svc/0 delivery chg).
- Gold precedent for reward 1svc + pure emoji + ports + helper tests + LOC + self-check: .planning/phases/20-reward-gamif-rules-compliance/PLAN.md + .planning/quick/gsd-reward-gamif-item2.log (F1 pure+delegate, F2 handler 1svc+rel+pure+log, F4 port test_reward with get_service+rel+pure attrs+__exit__+docstrings "ported...", F5 new TestCalculate... class + re-runs + rules verif + self-check PASSED + critical list + handoff).
- Mission 1svc + rel precedent: handlers/mission_user_handlers.py (with get_service(MissionService), if mission.reward, reward_text via rel) + its test.
- get_service: services/__init__.py:69 (context manager _ServiceContext).
- Current state (post prior): handlers/reward_user_handlers.py (get_service Mission + pure import + rel + no RewardService; reward_detail 50L); services/reward_service.py (pure at ~22 + delegate at ~125 with Item2 comment); test file (docstrings already "ported to 1-service...", get_service patches, mock setups for pure+rel).
- BATCH close precedent (cite in F5 self-check): .planning/phases/24-remaining-besito-compositions/24-remaining-besito-compositions-SUMMARY.md ("BATCH: 4 items completed in this tirón (Item 6 final of max 4)", "Item 6/24 closed. BATCH...", self-check PASSED) + its gsd log (BATCH COMPLETE NOTE).
- GSD log para este Item: .planning/quick/gsd-reward-handlers-1service-loc.log (planner INIT + pre-write 2 entries; executor append pre every).
- Reglas + contexto: CLAUDE.md (root + handlers + services + models), rules.md, architecture.md, decisions.md, AGENTS.md, services/missions/CLAUDE.md, models/CLAUDE.md (rels safe), handlers/CLAUDE.md (1 service rule).
- Comandos + patrones: sección 5 + "Instrucciones" arriba + item2 log entries exactas.

Listo para gsd-executor. Ejecuta F1 → ... → F5 con GSD pre en cada paso + self-check PASSED + POOL/BATCH confirm al final. Handoff explícito.

**Hecho con 💋 para Diana (Señorita Kinky) — gsd-planner subagent (continuación del hardening post-unificación de Besito; first of new pool of 4).**
