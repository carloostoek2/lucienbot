# PLAN: Reduce direct BesitoService composition in RewardService via EventBus (Item 5 / 23 post critical-tests)

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-06-08  
**Focus:** Tight, conservative, phased reduction of *held direct composition* of BesitoService inside RewardService (the MISSION delivery composer). Per impact-analyzer recs + precedents: remove the `self.besito_service = BesitoService(self.db)` held collaborator (and its __init__ wiring); inside `_deliver_besitos` only, use **local on-demand** `BesitoService(db=self.db)` for the credit + get_balance calls. This preserves 100% atomicity of the MISSION credit tx (credit still commits internally as before) + subsequent log_reward_delivery + return msg. The existing post-credit `schedule_emit` (besitos_awarded event, best-effort) continues to fire from inside credit. Add one rewards-domain *observational* listener (copy of narrative's `on_besitos_awarded_from_gamification`; lives in reward_service.py module-level; explicit "MUST NOT credit" contract + best-effort doc). Register it centrally + explicitly in bot.py on_startup (extend the cross-domain listeners block introduced in Item 1). 1-line fix only in 1 unit test (`tests/unit/test_reward_service.py:142` access to the now-removed held). Docs updates ONLY in `services/missions/CLAUDE.md` (add Cross-domain notifications section) + `decisions.md` (new entry following eventbus style). **Zero prod behavior change** (deliver_reward paths, balances, MISSION tx source, history, Lucien return strings identical), **zero atomicity impact** (local shares the db; credit's internal commit + log remain in the deliver flow; best-effort listeners never affect delivery or partial-failure contracts per gold test_cross_service_atomicity), **zero other composers touched** (broadcast_service, game_service etc. keep their direct held BesitoService for now), **zero new files**. 4-5 small phases (prep/GSD/baseline, refactor RewardService, listener+central reg, 1-line test fix + re-runs of golds, final verif+self-check). Full GSD pre-log discipline on `.planning/quick/gsd-reward-besito-eventbus.log` before *every* edit/gate/verif/ruff/pytest. Copy exact patterns from Item1 (story listener + bot reg + schedule_emit patch + DESIRED CONTRACT + gather return_exceptions), Item2 (reward delivery tests), Item21/22 (GSD structure, safe points, self-check, handoff), atomicity gold, event_bus.py. Prepares the 3 critical systems (gamif source, missions/rewards delivery, narrative) for further decoupling without risk.

**Input principal (source of truth):** 
- User prompt's complete impact-analyzer report description (executive summary + impact map + key risks atomicity/best-effort of bus + critical tests affected: *only* 1 unit reward test needs 1-line fix + recs of scope tight: remove held composition in RewardService, use local Besito on-demand inside _deliver_besitos to keep atomicity, add rewards-domain observational listener similar to narrative, central reg in bot.py, update docs in missions/CLAUDE + decisions, 0 behavior change, 0 impact on partial failure contracts).
- Exhaustive discovery by planner (current code state post-Item1/2/21/22: reward_service.py __init__:39 holds `self.besito_service = BesitoService(self.db)`, _deliver_besitos:214+223 uses it for credit+get_balance, close:339 getattr list; besito_service has _schedule_besitos_awarded_event + schedule_emit post-commit (lines 75-105,141-142); event_bus.py DESIRED CONTRACT + schedule_emit + gather return_exceptions; story_service.py:670-694 exact listener pattern with big "Cross-domain event listeners" comment block + `on_besitos_awarded_from_gamification` + "MUST NOT call back into credit/debit" + "best effort, non-authoritative"; bot.py:199-202 central reg after scheduler + log; tests/unit/test_reward_service.py:142 is the *only* direct `service.besito_service.get_balance` access in reward unit (in test_deliver_reward_besitos); cross_service_atomicity.py is the gold for "credit survives deliver False" + MISSION tx + patch schedule_emit; no other reward files touch the held; missions/CLAUDE.md has no cross-domain EventBus section yet; decisions.md has the Item1 eventbus entry to extend after).
- Precedents + gold (exact structure, GSD, phases, DoD, snippets, self-check, executor instrs): `.planning/phases/22-critical-tests-three-systems/PLAN.md` + SUMMARY.md (handoff explicitly names "Item 5 (Reduce direct Besito composition in RewardService via EventBus)"), 21-getservice-unification/PLAN.md, 20-reward-gamif-rules-compliance/PLAN.md, 19-eventbus-poc/PLAN.md + 19-*-SUMMARY.md + gsd-eventbus-poc-item1.log + gsd-reward-gamif-item2.log + gsd-getservice-unification.log + gsd-critical-tests.log + gsd-impact-*.log; gold tests `tests/integration/test_cross_service_atomicity.py` (DESIRED CONTRACT, patch schedule_emit, strict balance/tx/mission asserts, "post-credit misiones (best effort) + event listeners (best effort)"), `tests/unit/test_reward_service.py` (deliver besitos path), event_bus unit + story listener test coverage.
- Project rules (non-negotiable): CLAUDE.md (3 critical systems, EventBus for cross-domain *notifications* not commands, get_service pattern, GSD pre-log before edits, logging "módulo | acción | user_id | resultado", handlers exactly-1-service, services own domain), rules.md (≤50 LOC per func, naming verb+context+result, anti-patterns), architecture.md (handlers→services→models; no logic in handlers), models/CLAUDE.md (tx for atomics, no raw), decisions.md (EventBus + mw precedents), services/missions/CLAUDE.md + gamification/CLAUDE.md + narrative/CLAUDE.md (current cross notes + "MUST NOT credit" contract for listeners), services/CLAUDE.md, handlers/CLAUDE.md.
- Current state (post prior Items): strong (emit wired only in credit success post-commit, 1 narrative listener + central reg, atomicity gold protects credit vs best-effort sides, reward delivery paths exercised in unit+cross, held composition still present only in reward for besitos path among the delivery composers). This Item reduces *one* held site safely.

**GSD enforcement:** Executor MUST prefix **every** modification, gate, verification, ruff, pytest, grep, smoke, or summary step with a GSD log append (timestamp | PHASE | description) to `.planning/quick/gsd-reward-besito-eventbus.log`. Use identical discipline and entry style as gsd-eventbus-poc-item1.log / gsd-reward-gamif-item2.log / gsd-getservice-unification.log / gsd-critical-tests.log (pre + post + counts, "GSD pre-edit <file> (F<N> <short motive>) - <desc + refs DoD + patrones copiados>", wc tracking). No edits (even to PLAN or log beyond appends) without pre-log. Planner already did initial pre-create/pre-write entries (see log).

---

## 1. Alcance preciso (In / Out explícito)

### En esta entrega (scope "tight" per analyzer recs + "smallest change" + precedents + 0 behavior/0 atomicity/0 other composers):
- **RewardService refactor only (reduce held composition):**
  - `services/reward_service.py`: Remove `self.besito_service = BesitoService(self.db)` from __init__ (line ~39). In `_deliver_besitos` only (the sole credit site for BESITOS rewards), create local on-demand `besito_service = BesitoService(db=self.db)` (shares session so credit's internal commit + any tx context stays atomic with the deliver flow; get_balance after also uses the local). PackageService + VIPService held remain (scope: other composers untouched). close() getattr list for "besito_service" stays as-is (getattr returns None → harmless no-op; no code change needed for close). All logs, return strings, MISSION TransactionSource, log_reward_delivery, deliver_reward orchestration identical. No change to create_*/get_*/update_*/delete_* or other _deliver_* paths.
- **Listener + central registration (observational, best-effort, no command side):**
  - `services/reward_service.py`: Add (at module bottom, after class, mirroring story_service.py:670-694) the rewards-domain observational listener (async def, e.g. `on_besitos_awarded_rewards_observer` or `on_besitos_awarded_from_gamification` per naming decision in F3; copy the exact "Cross-domain event listeners" comment block + docstring with "MUST NOT credit/debit besitos", "best effort, non-authoritative", "rewards domain ownership", "use get_service if future needs DB", log format "rewards | besitos_awarded_received | user_id=... | amount=... | source=... | ref=..."). No side effects that mutate besitos or call credit.
  - `bot.py`: Extend the cross-domain listeners block (after scheduler, after the narrative register; add import + one register call + extend the logger.info line). Explicit, central, no import side-effects.
- **1-line test fix only (no new tests, no new files):**
  - `tests/unit/test_reward_service.py`: Exactly 1 line change in `test_deliver_reward_besitos` (the `balance = service.besito_service.get_balance(...)` access at ~142) to use a local `BesitoService(db=db_session).get_balance(...)` (or equivalent 1-line that resolves post-removal). (Import of BesitoService, if not already present/resolved via other means in the file, is the minimal companion; counted as part of the 1-line access fix per tight scope.) All other reward unit tests untouched (they don't access the held). Re-runs protect the deliver besitos path.
- **Docs (minimal, cross-domain only):**
  - `services/missions/CLAUDE.md`: Add short "Cross-domain notifications (EventBus)" section at end (modeled on gamification/narrative/ services CLAUDE updates from Item 1) documenting the reduced composition, the rewards listener, best-effort contract, "MUST NOT credit", and refs to event_bus + decisions.
  - `decisions.md`: Append new decision entry "## Reduce direct BesitoService composition in RewardService via EventBus (Item X / post eventbus-poc)" following the exact style/structure of the "Internal EventBus (PoC Item 1 ...)" entry (Motivo, Riesgos (críticos incl atomicity + partial failure contracts), Decisión (local on-demand + observational listener + central reg + 1-line test + docs), Resultado (0 behavior/0 atomicity change, held removed for this composer, listener wired, gates, handoff)).
- **Gates + re-runs (protect 0 regression + atomicity gold + listener wiring):**
  - Targeted re-runs of: reward unit (TestRewardServiceDelivery + deliver besitos), `test_cross_service_atomicity.py` (gold: happy MISSION credit path + "credit survives deliver False" + patch schedule_emit + note post-credit best-effort sides), mission/reward flows, story (protects inverse credit in _grant), besito credit (emit still fires), event_bus (if listener coverage extended cheaply without new files), broader smoke filtered by reward/atomic/mission/besitos_awarded.
  - Patch schedule_emit + DESIRED CONTRACT style where verifying emit (as in atomicity gold + Item1).
  - 0 new test files/cases (coverage for new listener comes from re-runs of paths that exercise credit inside deliver + existing event_bus/story listener tests + manual smoke of register+emit).
- **Behavior/contracts:** deliver_reward for BESITOS returns identical (success, "Has recibido N besitos! Tu saldo es: X"), credit still uses TransactionSource.MISSION + reference_id=reward.id, log_reward_delivery still called post-success, best-effort listeners (now narrative + rewards) never affect the bool/return/msg or cause rollback. "besitos_awarded" event payload unchanged. Partial failure contract (credit tx commits even if later log or listeners fail) protected by gold test.
- **Artefacts:** This PLAN.md + GSD entries (pre every) in the dedicated log + (optional post-exec) SUMMARY.md. Memory/hand-off already points to this from 22-SUMMARY.

**Archivos que se modificarán (exactos, por orden de fases; prefer extend, minimal):**
1. `.planning/quick/gsd-reward-besito-eventbus.log` (all phases, pre only via echo; no "edit" of source).
2. `services/reward_service.py` (F2: __init__ + _deliver_besitos; F3: listener at bottom).
3. `bot.py` (F3: import + register in on_startup + log line).
4. `tests/unit/test_reward_service.py` (F4: exactly the 1 access line).
5. `services/missions/CLAUDE.md` (F5: add cross-domain section).
6. `decisions.md` (F5: append decision entry).
7. Re-runs/gates/verifs/smokes do not modify (except log appends + ruff auto-fixes if any on touched).

**Fuera explícitamente (nada de scope creep, per "tight" + "0 other composers" + "1-line only" + precedents):**
- **NO** other files in services/ (no broadcast_service, game_service, daily_gift, story beyond its existing listener, mission_service, package/vip, __init__.py exports, etc.).
- **NO** handlers (reward_user/admin, mission_*, gamification_* etc. — they already follow 1-service or call via MissionService; no change).
- **NO** new test files, no new test methods/cases (only the 1-line access fix in the existing test_deliver_reward_besitos; no extension of event_bus tests or atomicity for "new listener" coverage — re-runs + smoke suffice).
- **NO** changes to close() body (getattr safe), to _deliver_package/_deliver_vip, to create_*/CRUD paths, to log_reward_delivery, to any return strings or LucienVoice.
- **NO** migration to get_service() for the local credit (use direct BesitoService(db=...) to keep tx/owns semantics explicit inside the atomic deliver; get_service is for handlers/contexts per precedents).
- **NO** editing CLAUDEs/decisions except the two specified (missions/ + decisions.md); no AGENTS/ROADMAP/root CLAUDE/handlers/CLAUDE.
- **NO** touching models, alembic, config, utils, middlewares, keyboards, bot startup beyond the register block.
- **NO** new events, no change to besitos_awarded payload, no removal of schedule_emit from credit.
- **NO** broad "reduce all compositions" (only this one held site in RewardService for besitos delivery).
- **NO** behavior or contract changes (0 impact on partial failure, 0 on "credit survives deliver False").

**Comportamiento observable:** Identical for all reward delivery (BESITOS/PACKAGE/VIP), mission claim flows, balances, history, return messages to users. The event is still emitted (best-effort) on every credit including MISSION ones; now two listeners receive it (narrative + rewards observer). No user-visible or admin-visible change.

---

## 2. Fases ordenadas (5 fases pequeñas, secuenciales, con gates estrictos)

### Fase 1: Preparación (GSD log, baseline, fixtures/mocks/patterns confirm, patrones gold)
**Objective:** Establecer disciplina GSD para el Item (log touched by planner), confirmar baseline de archivos tocados (ruff + targeted pytest verdes pre-cambios), mapear sites de composición actual + listener patterns + bot reg + atomicity gold, preparar setups para the 1-line (fresh TG or sample_user, db_session), confirmar que credit inside deliver still exercises schedule_emit (via patch in re-runs). Sin cambios de lógica aún. Safe point inicial.

**DoD checklist (marcar al completar):**
- [ ] Log `.planning/quick/gsd-reward-besito-eventbus.log` exists with planner INIT/DISCOVERY/PLANNING entries + at least 1 pre-F1 of executor.
- [ ] Baseline: ruff clean on `services/reward_service.py`, `tests/unit/test_reward_service.py`, `bot.py` (and spot on story_service.py for listener pattern).
- [ ] Baseline targeted pytest verdes (clean flags): `pytest tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts="` (all delivery tests including besitos path), spot `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="` (gold), smoke story/besito units if needed for patterns.
- [ ] Confirm gold patterns via grep/lectura: DESIRED CONTRACT, patch("services.event_bus.schedule_emit"), "post-credit ... best effort", listener comment block + "MUST NOT" in story_service.py:670+, bot.py on_startup register block (199-202), atomicity "credit survives deliver False", N806 tolerance if any, TG-style or sample_user in reward tests, local db= for shared session in atomic flows.
- [ ] Mocks/fixtures list: db_session (for local Besito(db=) in the 1-line), mock_bot, sample_user/reward, patch schedule_emit ready (as in atomicity gold + besito unit), get_event_bus for smoke.
- [ ] Grep current composition: `grep -n "besito_service\|BesitoService(self.db)" services/reward_service.py` shows the 3 sites (__init__, _deliver, close getattr); confirm only _deliver credit site will change.
- [ ] GSD pre + post entries for baseline.
- [ ] Safe point F1.

**Archivos:** Log + (lectura/grep/ruff/pytest; 0 edits to prod/tests in F1).

**Cambios clave (bullets accionables):**
- Ejecutar comandos de baseline (ver Instructions).
- Grep/lectura rápida de patterns (story listener block, bot reg, atomicity patch+docstring, reward test besitos path).
- Confirm import of BesitoService will be available for the 1-line (or note minimal import companion).
- Actualizar log con "F1 baseline verde + patterns confirmed (story listener copy source, atomicity gold for atomicity, 1 access site in reward test) + ready for refactor".
- (No code changes.)

**Tests que deben pasar antes de avanzar (gates de F1):**
- Ruff on touched py (reward_service, its test, bot).
- `pytest tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts="`
- `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="` (at least the deliver/reward paths).
- Grep confirm + GSD entries + "F1 safe point".

**Riesgos + mitigaciones:**
- Riesgo: baseline shows pre-existing unrelated fails (alembic etc.) → Mit: document in log; use targeted -k; do not count as regression of this Item (precedent in 22/19/20).
- Riesgo: the reward unit test file has other indirect deps on held → Mit: discovery shows only 1 direct access line; others go through deliver which will be fixed internally first.
- Bajo: time on baseline → Mit: targeted, parallel commands where safe but prefer sequential for log.

**Safe point:** Baseline verde + patterns confirmed + "F1 safe point - ready for RewardService refactor; no source changed yet". Reversible (nada editado en fuentes aún).

---

### Fase 2: Refactor RewardService (remove held composition; local Besito on-demand inside _deliver_besitos only)
**Objective:** Ejecutar el core change: remover la composición held en __init__, re-implementar _deliver_besitos usando local BesitoService(db=self.db) para credit + get_balance (copia el patrón de "local for shared db" de atomicity golds y getservice normalization). Mantener 100% comportamiento (mensajes, tx source MISSION, commits, returns). close() getattr se vuelve no-op para besito (harmless). Logging estándar. Ruff + smoke + targeted (note: the 1 access test will fail until F4; gate other paths + service itself). GSD pre every edit.

**DoD checklist:**
- [ ] __init__ no longer sets self.besito_service (comment explaining reduction + local-only for besitos credit; package/vip still held).
- [ ] _deliver_besitos uses local `besito_service = BesitoService(db=self.db)` for the two calls; docstring updated to note "local on-demand (shared db preserves atomicity of MISSION credit + log_reward + return)"; success path + error path identical.
- [ ] All other methods untouched (create, get, update, delete, _deliver_package, _deliver_vip, log_*, stats, close getattr list).
- [ ] Ruff limpio + format; GSD pre each edit + pre-gate.
- [ ] Smoke: import RewardService + basic create + non-besitos deliver paths (or unit tests that don't hit the access line).
- [ ] Grep: `grep -n "self\.besito_service = " services/reward_service.py` → 0 (active); "BesitoService(db=self.db)" present in _deliver.
- [ ] Targeted reward unit (excluding or noting the 1 failing access test) + cross atomicity spot (if it uses full deliver) pass where applicable; 0 regressions in non-besitos reward paths.
- [ ] Safe point.

**Archivos:** `services/reward_service.py` (only).

**Cambios clave (bullets accionables, orden: __init__ then _deliver):**
- Pre-log GSD "pre-edit services/reward_service.py (F2 remove held + local in _deliver) - refs DoD F2 + copy local db= pattern from atomicity gold + getservice normalization; 1-line test fix deferred to F4".
- Edit __init__ (around line 36-41):
  ```python
  def __init__(self, db: Session = None):
      self._owns_session = db is None
      self.db = db or SessionLocal()
      # Held direct BesitoService composition removed (Item X / reduce via EventBus pattern).
      # BESITOS reward delivery now uses local on-demand BesitoService(db=self.db) *only*
      # inside _deliver_besitos (preserves atomicity: credit's internal commit + MISSION tx source
      # + log_reward_delivery + return msg all unchanged; best-effort schedule_emit still fires).
      # Package + VIP remain held (scope: other composers untouched for now).
      self.package_service = PackageService(self.db)
      self.vip_service = VIPService(self.db)
  ```
- Edit _deliver_besitos (around 212-227; keep signature and all logic identical except the instantiation):
  ```python
  async def _deliver_besitos(self, user_id: int, reward: Reward) -> tuple[bool, str]:
      """Entrega recompensa de besitos (local BesitoService on-demand with shared db for atomicity)."""
      besito_service = BesitoService(db=self.db)  # local, on-demand; owns=False (db shared); credit commits internally as before
      success = besito_service.credit_besitos(
          user_id=user_id,
          amount=reward.besito_amount,
          source=TransactionSource.MISSION,
          description=f"Recompensa: {reward.name}",
          reference_id=reward.id,
      )

      if success:
          balance = besito_service.get_balance(user_id)
          return True, f"Has recibido {reward.besito_amount} besitos! Tu saldo es: {balance}"
      else:
          return False, "Error al acreditar besitos"
  ```
- (Optional slim) add/update the module docstring or a top comment if helpful, but keep minimal.
- Post edit: ruff --fix + format --check (apply if needed); smoke `python -c "from services.reward_service import RewardService; ..."` (non-besitos paths); grep for the removal + local.
- GSD entry post-gate.
- Re-run relevant reward tests (the besitos access test will be xfailed or skipped in gate; other  delivery tests green).

**Tests que deben pasar antes de avanzar:**
- Ruff on reward_service.py.
- `pytest tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "not test_deliver_reward_besitos"` (or full with expectation the 1 access fails until F4; document).
- Spot cross if it exercises non-besitos or can be patched; targeted besitos credit paths via other tests.
- Grep + smoke + "F2 safe point".

**Riesgos + mitigaciones:**
- Riesgo: atomicity of deliver broken (credit now in "local" vs held) → Mit: local uses `db=self.db` (exact shared session as the old held one had); credit does its own commit inside (as always); the subsequent log_reward_delivery commit is unchanged; gold test_cross_service_atomicity (which does full deliver + asserts credit tx present even on partial) will be re-run in F4 and protects. Local creation is cheap and matches "on-demand" rec.
- Riesgo: close() or owns semantics affected → Mit: no change to close body; getattr for besito will be None (safe); the local inside _deliver creates a non-owning instance (db passed) whose close() is no-op.
- Riesgo: test that does `service.besito_service` now fails → Mit: exactly the 1-line planned for F4; F2 gates exclude or note it.
- Mit general: targeted, DESIRED-style comments in the edit, GSD.

**Safe point:** Post-ruff + greps + non-besitos reward tests green + GSD "F2 safe point - held removed, local Besito(db=) in _deliver only; 0 behavior change in deliver paths; close safe; 1 access test deferred". Reversible by restoring the 3 lines in __init__ + 2 lines in _deliver.

---

### Fase 3: Agregar listener rewards-domain + registro central en bot.py + comments
**Objective:** Añadir el listener observacional rewards-domain (copy exact pattern from story_service.py:670-694, adapt for "rewards" domain + "MUST NOT credit" contract). Registro explícito central en bot.py on_startup (extend the block from Item 1). Logging "rewards | ...". No side effects. GSD pre, ruff, smoke (import + manual register+emit under loop), re-run story/besito to protect inverse credit + emit.

**DoD checklist:**
- [ ] Listener added at bottom of reward_service.py (after any __del__ or end of file): full comment block "Cross-domain event listeners..." + async def (name decided in F3 first GSD, e.g. `on_besitos_awarded_rewards_observer(payload: dict) -> None`) with docstring quoting "MUST NOT credit/debit", "observational best-effort for rewards domain", "no re-entrancy risk with deliver paths", log line "rewards | besitos_awarded_received | ...", no mutation code.
- [ ] bot.py: import added (from services.reward_service import ...), register call added after the narrative one, logger.info extended (e.g. "... (besitos_awarded -> narrative, rewards)").
- [ ] Comments in both places reference this Item / "following narrative precedent (Item 1)".
- [ ] Ruff limpio on both; GSD pre every.
- [ ] Smoke: python -c import bot (or manual under asyncio loop: get_event_bus().register + emit payload + caplog or print); listener callable.
- [ ] Re-runs: story unit + besito credit (emit still fires, no breakage to _grant inverse credit); 0 regressions.
- [ ] Safe point.

**Archivos:** `services/reward_service.py`, `bot.py`.

**Cambios clave (bullets accionables):**
- Pre-log per file "pre-edit <file> (F3 add rewards listener / central reg) - copy story_service.py:670-694 block + def; adapt name/log prefix/domain; bot reg after narrative; refs DoD + Item1 precedent".
- In reward_service.py (append at very end, after the last def or __del__):
  ```python
  # =============================================================================
  # Cross-domain event listeners (registered explicitly from bot.py on startup).
  # The listener lives here (rewards domain ownership). It is a plain async callable
  # receiving the standard payload dict. It MUST NOT call back into credit/debit besitos
  # (to avoid any re-entrancy with deliver paths or future extensions; delivery contracts
  # and partial-failure behavior are authoritative in the credit + log_reward_delivery flow).
  # This is observational only (best effort; errors swallowed by bus).
  # =============================================================================

  async def on_besitos_awarded_rewards_observer(payload: dict) -> None:
      """
      Rewards-domain listener for "besitos_awarded" events (emitted by BesitoService.credit_besitos
      post-commit, including from MISSION reward deliveries in _deliver_besitos).

      DESIRED CONTRACT (copy of narrative precedent): log reception with full context (user_id/amount/source/ref);
      purely observational + wiring proof for this domain. MUST NOT credit, debit, or mutate besitos state here.
      Future extensions (e.g. stats, hints tied to awards) belong in this module and should use
      get_service(RewardService) or direct models if a fresh DB session is required.
      """
      uid = payload.get("user_id")
      amt = payload.get("amount")
      src = payload.get("source")
      ref = payload.get("reference_id")
      logger.info(
          f"rewards | besitos_awarded_received | user_id={uid} | amount={amt} | source={src} | ref={ref}"
      )
      # No side effects that mutate besitos here (best effort, non-authoritative; 0 impact on deliver_reward contracts).
  ```
  (Name of the def: confirm in first GSD of F3; "on_besitos_awarded_rewards_observer" recommended for clarity vs the gamification-origin name used by narrative; either is fine if consistent with register.)
- In bot.py (near the existing cross-domain block, ~199-202):
  - Add to the from services... imports: `from services.reward_service import on_besitos_awarded_rewards_observer`
  - After the narrative register line:
    ```python
    get_event_bus().register(EVENT_BESITOS_AWARDED, on_besitos_awarded_rewards_observer)
    logger.info("Event listeners registrados (besitos_awarded -> narrative, rewards)")
    ```
  - Keep/update the comment: "# Cross-domain listeners (explicit, central, no import side-effects). Fase 3 of eventbus-poc + this Item: narrative + rewards domains."
- Post: ruff --fix + format on both; smoke; re-run story + besito targeted.
- GSD + "F3 safe point".

**Tests gates:**
- Ruff on the two files.
- `pytest tests/unit/test_story_service.py tests/unit/test_besito_service.py -q --tb=line -p no:cov --override-ini="addopts="` (protect inverse + emit).
- Smoke bot import or manual listener register+emit.
- Grep for the new def + register call.

**Riesgos + mitigaciones:**
- Riesgo: duplicate listener name or import collision → Mit: unique name in rewards; explicit import in bot.
- Riesgo: listener registration order or multiple in tests → Mit: tests use patch or fresh bus per Item1 precedent; prod reg is idempotent-tolerant (bus allows dups).
- Riesgo: "rewards" listener name confusion with "reward" delivery → Mit: docstring + log prefix make domain clear; it's observational only.
- Mit: copy the comment block verbatim (adapt 3-4 words), use exact log format from narrative.

**Safe point:** Post gates + GSD "F3 safe point - rewards listener added (MUST NOT credit, best effort), central reg in bot (after narrative), 0 side effects, emit still fires to both, story/besito protected". Reversible: delete the listener def + remove the register line + import.

---

### Fase 4: 1-line test fix + re-runs golds (atomicity, reward delivery, mission/reward flows) + listener coverage via re-runs
**Objective:** Aplicar la única modificación de test (1 línea en test_deliver_reward_besitos para resolver el acceso post-removal). Luego re-ejecutar TODOS los golds que ejercitan deliver besitos / credit inside reward / atomicity / mission reward paths + event emit (con patch schedule_emit donde se verifica). Confirmar 0 regressions atribuibles + que el emit sigue ocurriendo (best effort to now 2 listeners). GSD pre every.

**DoD checklist:**
- [ ] Exactly 1 line changed in `tests/unit/test_reward_service.py` (the balance access); now uses local `BesitoService(db=db_session)...` or equivalent; test passes.
- [ ] (If import of BesitoService was required and not present: the minimal import line is the only companion edit; total delta on the test file is the 1-line access + import if needed.)
- [ ] Re-runs: full `pytest tests/unit/test_reward_service.py ...` green (all delivery including besitos); `pytest tests/integration/test_cross_service_atomicity.py ...` green (gold asserts on MISSION tx + balance delta + "credit survives" + patch schedule_emit if present in the happy path); targeted mission/reward flows, besito credit (emit), story.
- [ ] Patch schedule_emit or get_event_bus used in at least the atomicity re-run or reward test to verify emit still scheduled post the local credit (as in gold + Item1 F4).
- [ ] Grep/inspección: no more `service.besito_service` in the reward test active code; listener coverage exercised via re-runs (credit inside deliver now reaches registered listeners when bot startup path is used, or via direct emit in smokes).
- [ ] Ruff on the test; GSD pre + "F4 re-runs done".
- [ ] Safe point.

**Archivos:** `tests/unit/test_reward_service.py` (the 1-line).

**Cambios clave:**
- Pre-log "pre-edit tests/unit/test_reward_service.py (F4 1-line access fix) - change service.besito_service.get_balance to BesitoService(db=db_session).get_balance in test_deliver_reward_besitos; + import if needed; per impact '1 test unit de reward necesita fix de 1 línea'; DoD F4 + atomicity gold".
- The edit (1 line at ~142):
  ```python
          assert success is True
          assert "50" in msg
          balance = BesitoService(db=db_session).get_balance(sample_user.id)  # 1-line fix post held removal (F4); was service.besito_service
          assert balance == 50
  ```
  (Add `from services.besito_service import BesitoService` at top of file or inside the test func per file convention if not resolvable.)
- Post: ruff; full pytest of the reward unit file; re-run atomicity (with any existing patch); re-run chains that hit reward delivery or besito MISSION.
- GSD post + counts.

**Tests gates (obligatorios):**
- Ruff on the test file.
- `pytest tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts="` (full, now all green).
- `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="` (gold).
- `pytest -k "reward or deliver_reward or TestRewardServiceDelivery or TestCrossServiceAtomicity or mission or besito or atomicity" -q --tb=line -p no:cov --override-ini="addopts="` (broader but targeted; document unrelated pre-exist).
- Grep for the fix + "F4 gates + 0 new regressions attributable".

**Riesgos + mitigaciones:**
- Riesgo: the 1-line test now exercises a fresh BesitoService instance → Mit: it only reads balance post-commit (the credit already committed via the local inside deliver); identical to before. Gold atomicity re-run confirms tx + delta.
- Riesgo: unrelated fails in broader re-runs → Mit: document (precedent 22/19); focus "0 attributable to this Item's 1-line".
- Riesgo: listener not "covered" because units don't run bot startup → Mit: re-runs of paths that call credit (which schedules) + smoke of register+emit (as in Item1 F3/F5) + note in log that coverage is via the emit path + existing event_bus tests; no new test code per tight scope.

**Safe point:** Post all gates + GSD "F4 safe point - 1-line fix applied + all reward unit + atomicity gold + mission/reward flows re-runs green (0 attributable reg); emit still verified via patch; now 2 listeners would receive on real reg". Reversible by the 1-line revert.

---

### Fase 5: Verificación final, criterios, self-check + handoff
**Objective:** Confirmar scope completo limpio/medible/listo para arch-enforcer re-scan + test-guardian (correr los tests críticos listados). Completar GSD log con self-check PASSED explícito + lista de "tests críticos a re-correr en futuro". Opcional SUMMARY.md. Hand off para siguiente item del batch (si aplica) + guardians.

**DoD checklist (marcar al completar):**
- [ ] Todos los archivos tocados (reward_service.py, bot.py, 1 test, 2 docs) pasan ruff check + format --check.
- [ ] Grep global/por archivo: 0 "self\.besito_service = " (active) en reward_service.py; presence of rewards listener def + "rewards | besitos_awarded_received" + "MUST NOT credit"; register call + extended log in bot.py; the 1-line fix comment/patch in the test; cross-domain section in missions/CLAUDE; decision entry in decisions.md.
- [ ] Re-runs finales de targeted críticos (repetir F4 commands + spot on story/besito/event_bus + smoke of bot register+emit under loop).
- [ ] GSD log tiene entradas para cada fase + pre-gates + self-check al final con estructura completa: lista de fases/DoD/gates/archivos modificados/tests que pasaron/reglas verificadas (1-service no aplica directamente aquí pero "no logic change in handlers", LOC no tocado o <50 preserved, logging in listener + comments, GSD discipline, DESIRED-style notes, patch schedule_emit, atomicity gold re-run, "0 new files / 0 behavior / 0 atomicity / 0 other composers")/desviaciones (si las)/tests críticos para futuro (reward unit full, cross_service_atomicity full, mission reward flows, besito credit paths, story, event_bus, bot import smoke, the combined -k "reward or deliver or atomicity or besitos_awarded or mission")/"Item 5/23 closed. Ready for gsd-executor of next batch item (if any) + arch-enforcer re-scan (enfocado en reward composition sites + listener wiring + 3 critical systems) + test-guardian (correr los tests críticos listados)".
- [ ] Self-check explícito "Self-Check: PASSED".
- [ ] (Opcional) SUMMARY.md en el dir de la phase con executive + refs al log + comandos de re-verif (sigue precedente phases/22/21/20/19).
- [ ] Safe point final + criterio de éxito del plan.

**Archivos:** Ninguno nuevo (log + opcional SUMMARY; edits ya hechos en F2-F5).

**Cambios clave:** Solo ejecución de comandos (ver Instructions) + echo al log. Usar run_terminal para gates finales + conteos + greps.

**Tests gates:** Los re-runs finales + ruff global touched + broader smoke filtrado + self-check.

**Riesgos:** Ninguno nuevo (verif final).

**Safe point final + criterio de éxito:** Todos DoD F5 + self-check PASSED en log. El plan completo + log GSD son evidencia para siguiente agente (gsd-executor next item o arch-enforcer/test-guardian). 0 breakage en critical systems or deliver contracts; the 3 systems (gamif, missions/rewards, narrative) remain protected; held composition reduced for this site following the bus loose-coupling precedent safely.

---

## 3. Estrategia de tests general

- **Unit para lógica de delivery (besitos path inside reward, now with local):** db_session fixture (in-mem or file per gold); direct create reward + deliver; post-fix the access uses explicit local BesitoService(db=) (same as the one created inside _deliver); asserts on return msg + balance delta exact + tx source via other queries if needed. Patch("services.event_bus.schedule_emit") around the deliver call to verify emit still scheduled (best effort, as in atomicity gold + besito unit from Item1).
- **Integration para flujos cross (atomicity gold, reaction/mission that lead to reward deliver, credit inside MISSION):** file SQLite + TestSession (gold exact from test_cross_service_atomicity.py); patch schedule_emit; strict asserts on balance delta, BesitoTransaction source==MISSION + reference_id, UserRewardHistory, reaction_result if overlaps, "credit survives deliver=False" path (the local credit still commits even if later log or listener would "fail"). Re-run full happy + partials.
- **Listener coverage (no new files/cases per tight):** exercised by (a) re-runs of credit paths (besito unit, atomicity, reward deliver) which call schedule_emit; (b) smoke/manual in F3/F5: get_event_bus().register(the rewards listener) + await bus.emit(...) + caplog or assert logged (copy from Item1 F3 test_event_bus addition); (c) existing event_bus unit + story listener test (they cover the bus + one listener; the second is symmetric). When bot startup is exercised (smoke), both listeners are registered.
- **Gates:** always `-p no:cov --override-ini="addopts="` for clean exit (precedent all recent phases); targeted -k first (reward, deliver, atomicity, cross, mission); broader smoke at end filtered by keywords; ruff pre/post; GSD pre each.
- **ID / DESIRED CONTRACT:** in the 1-line fix test + any docstring updates, quote "credit survives deliver False", "MISSION tx + history log + return msg", "best-effort listeners no afectan delivery". Use sample_user / db_session as in the file (or fresh TG if adding, but scope 1-line).
- **Precedente --override-ini + N806 (if surfaces):** tolerate + document (atomicity gold has it for TestSession).
- **No scope creep en tests:** only the 1-line access fix; re-runs protect existing + the emit contract. No new methods even if cheap.
- **Cobertura logging:** not asserted in tests; gate is manual inspection during F3 (listener log) + inclusion in GSD.

---

## 4. Decisiones de diseño (el executor debe confirmar o registrar desviación en el primer GSD entry de la fase relevante)

1. **Nombre del listener rewards-domain:** `on_besitos_awarded_rewards_observer` (recomendado para claridad de dominio "rewards" vs el origin "from_gamification" usado por narrative). Alternativa: `on_besitos_awarded_from_gamification` (mismo nombre, dos registrants — bus tolera). Confirmar en primer GSD de F3; documentar.
2. **Cómo mantener _deliver_besitos atómico con local Besito:** `besito_service = BesitoService(db=self.db)` (pasa la sesión compartida; el local tendrá owns=False y su close no-op). El credit_besitos hace su propio commit (como siempre); el log_reward_delivery commit posterior es idéntico. Esto replica exactamente lo que el held hacía antes (mismo db object). No usar get_service aquí (get_service es para contextos de alto nivel/handlers per 21; local directo preserva el "dentro de la tx de deliver" explícito). El emit post-commit de credit sigue ocurriendo (schedule_emit) — listeners best-effort.
3. **Payload handling + logging en listener:** Idéntico al de narrative (uid/amt/src/ref); log prefix "rewards | besitos_awarded_received | ..." (vs "narrative | ..."). Incluir el comentario grande "Cross-domain event listeners..." (copy from story 670-675) adaptado para rewards + "0 impact on deliver_reward contracts / partial failure".
4. **Docstring MUST NOT credit:** Copiar espíritu exacto: "It MUST NOT call back into credit/debit besitos to avoid re-entrancy with deliver paths... best effort, non-authoritative." + "DESIRED CONTRACT" mention. Colocar en el def + en el bloque de comentarios.
5. **1-line fix en test:** Cambiar solo la línea de acceso `service.besito_service.get_balance` a `BesitoService(db=db_session).get_balance(...)`; agregar import si no resuelve (mínimo). Añadir comentario "# 1-line fix post held removal (Item X / F4)". Mantener todos los asserts/textos idénticos.
6. **close() en RewardService:** Dejar el getattr("besito_service", None) tal cual (se volverá None → skip; inofensivo). No tocar el for-loop (scope tight; otros subs package/vip siguen).
7. **Registro en bot.py:** Después del de narrative (orden no importa); extender el logger.info existente; mantener el comentario "Cross-domain listeners (explicit, central...)".
8. **Actualizaciones de docs:** missions/CLAUDE.md al final (nueva sección "Cross-domain notifications (EventBus)" con 4-5 bullets + refs); decisions.md append después de la entrada de Item1 eventbus (mismo formato Motivo/Riesgos/Decisión/Resultado + refs a PLAN/log).
9. **Log file GSD:** `.planning/quick/gsd-reward-besito-eventbus.log`. Formato:
   ```
   === 2026-06-08Txx:xx:xx+00:00 | PHASE 2 | GSD pre-edit services/reward_service.py (F2 remove held + local in _deliver) - Agregar local BesitoService(db=self.db) en _deliver_besitos; remover self.besito_service= en __init__; copiar patrón db= compartido de atomicity gold + getservice norm; refs DoD F2 + impacto analyzer (mantener atomicidad).
   ```
   (o pre-ruff, pre-pytest -k "reward or atomicity", pre-grep "besito_service =", pre-final-self-check). Apuntar 5-10+ entries por fase (como precedentes).
10. **Comandos concretos:** Ver sección Instrucciones abajo. Siempre con -p no:cov + override para pytest targeted. Para smoke listener: python -c + asyncio snippet o pytest con caplog.
11. **Cualquier desviación:** Registrar en GSD entry de la fase + nota breve al final del PLAN o en SUMMARY.

Cualquier decisión que difiera de lo anterior debe registrarse en el GSD log + nota breve al final del PLAN o en SUMMARY posterior.

---

## 5. Criterios de verificación + gates finales

**Criterios de éxito del Item (medibles, para self-check del executor):**
- Held composition removed: `grep -c "self\.besito_service = BesitoService" services/reward_service.py` (active) == 0; local on-demand present in _deliver_besitos with `db=self.db`.
- Listener added + wired: def present with "MUST NOT credit" + "rewards | besitos_awarded_received"; register call + extended log in bot.py on_startup.
- 1-line fix only: exactly the access line (and minimal import) changed in the one test; all reward unit tests now pass.
- Docs: cross-domain section in missions/CLAUDE.md; decision entry in decisions.md (style of Item1 eventbus).
- 0 behavior change: re-runs of reward unit (deliver besitos returns exact same msg + balance), cross atomicity (MISSION tx present, credit survives deliver=False, balance delta exact, "besitos_awarded" local in reaction dicts if overlap), mission flows — all green with 0 regressions attributable.
- Emit still fires: patch schedule_emit asserts in at least one re-run (atomicity or reward); when registered, both listeners receive (smoke).
- Ruff limpio en los 3 py tocados + 2 docs (docs no ruff pero spot).
- Verificaciones de reglas/patrones: GSD pre every (counts 5-10+/fase); logging format in listener; comments reference Item + precedents; LOC of touched funcs preserved or <50 (no change); 0 new files; scope exactly as listed.
- GSD log completo con pre-entries + self-check "PASSED" + lista explícita de "tests críticos a re-correr en el futuro para estos cambios" (reward unit full, cross_service_atomicity full, -k "reward or deliver or TestRewardServiceDelivery or TestCrossServiceAtomicity or mission or besitos_awarded or atomicity", story, besito credit, bot smoke, event_bus) + "Item 5/23 closed. Ready for gsd-executor of next batch item (if any) + arch-enforcer re-scan (reward composition + listener wiring + 3 critical systems) + test-guardian (correr los tests críticos listados)".
- Safe point final documentado; item listo para siguiente en batch y guardians.
- Comportamiento de usuario final idéntico (reclamo de recompensas MISSION con besitos, saldos, mensajes Lucien, historial).

**Gates por fase (ver secciones de fases para detalles):**
- Pre-edit: GSD log entry.
- Post-edit: ruff + targeted pytest (cuando aplique) + smoke + grep/LOC + GSD entry de resultado.
- Avanzar solo si gate verde (o documentar desviación menor).
- F4/F5: re-runs obligatorios de golds + broader smoke filtrado + self-check.

**Comando combinado sugerido para gates finales (adaptar por fase; targeted primero):**
```
./venv/bin/python -m pytest -k "TestRewardServiceDelivery or deliver_reward or TestCrossServiceAtomicity or reward or mission or besitos_awarded or atomicity or TestReward or cross_service_atomicity" -q --tb=line -p no:cov --override-ini="addopts="
```
Para suites específicas: `pytest tests/unit/test_reward_service.py ...` (con flags).  
Ruff: `./venv/bin/python -m ruff check services/reward_service.py bot.py tests/unit/test_reward_service.py --fix && ./venv/bin/python -m ruff format --check ...`  
Grep rules: `grep -n "self\.besito_service = \|besito_service = BesitoService(db=self.db)\|on_besitos_awarded_rewards\|rewards | besitos_awarded_received\|MUST NOT credit" services/reward_service.py bot.py tests/unit/test_reward_service.py`  
Smoke listener: `python -c "
import asyncio
from services.event_bus import get_event_bus, EVENT_BESITOS_AWARDED
from services.reward_service import on_besitos_awarded_rewards_observer
bus = get_event_bus()
bus.register(EVENT_BESITOS_AWARDED, on_besitos_awarded_rewards_observer)
print('rewards listener registered')
# (under running loop or use caplog in pytest for the log line)
" `

---

## Instrucciones para el gsd-executor

Este PLAN.md es tu prompt de ejecución. Síguelo al pie de la letra, sin scope creep. El trabajo es para UNA persona (tú) + disciplina GSD total. El flujo continúa automáticamente con gsd-executor para este item (y si hay 4to item en el batch, planear para después — pero este prompt cubre el actual).

1. **GSD discipline (non-negotiable, como en todas las phases exitosas):**
   - ANTES de **cualquier** modificación (search_replace/write/edit en fuentes o log), antes de ruff, pytest, grep de verif, smoke, o resumen: append al log.
   - Log: `.planning/quick/gsd-reward-besito-eventbus.log`
   - Crea el archivo si no existe (planner ya lo tocó; primer entry de executor puede ser confirm + wc).
   - Formato de entry (copia estilo de gsd-eventbus-poc-item1.log / gsd-reward-gamif-item2.log / gsd-getservice-unification.log / gsd-critical-tests.log):
     ```
     === 2026-06-08Txx:xx:xx+00:00 | PHASE 2 | GSD pre-edit services/reward_service.py (F2 remove held + local in _deliver) - Agregar local BesitoService(db=self.db) en _deliver_besitos; remover self.besito_service= en __init__; copiar patrón db= compartido de atomicity gold + getservice norm + story listener comments; refs DoD F2 + impacto analyzer (mantener atomicidad, 0 behavior chg).
     ```
     Luego ejecuta el comando de edit/tool.
   - También pre-gate (pre-pytest, pre-ruff, pre-grep "besito_service =|on_besitos_awarded_rewards|MUST NOT", pre-final-self-check).
   - Cuenta las entradas; apunta a 5-10+ por fase (como precedentes). Al final del Item el log debe tener el self-check completo.
   - Usa `run_terminal_command` con `echo "=== $(date -Iseconds) | PHASE N | ..." >> .planning/quick/gsd-reward-besito-eventbus.log` (o printf). Nunca edites sin pre-log. wc -l después de appends clave.

2. **Orden estricto:** Ejecuta Fase 1 completa (con gates) → gates F1 → Fase 2 (refactor RewardService; un edit a la vez si prefieres) → gates F2 → Fase 3 (listener + reg) → gates → Fase 4 (1-line test fix + re-runs golds) → gates → Fase 5 (verif final + self-check). **No saltes fases ni hagas "todo de una".** Marca DoD mentalmente o en el log al completar cada checklist. Al final de cada fase documenta "F<N> safe point" en log.

3. **Herramientas y comandos concretos (usa run_terminal_command para estos):**
   - GSD logs: `echo "=== $(date -Iseconds) | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados>" >> .planning/quick/gsd-reward-besito-eventbus.log`
   - Mkdir (si planner no lo hizo, pero ya existe): `mkdir -p .planning/phases/23-reward-besito-eventbus-decoupling`
   - Ruff: `./venv/bin/python -m ruff check <file> --fix` ; luego `./venv/bin/python -m ruff format --check <file>` (o apply).
   - Pytest targeted (siempre con estos flags para exit limpio): `./venv/bin/python -m pytest <path or -k "expr"> -q --tb=line -p no:cov --override-ini="addopts="`
     - Ejemplos:
       - `pytest tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts="`
       - `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="`
       - `pytest -k "TestRewardServiceDelivery or deliver_reward or TestCrossServiceAtomicity or reward or mission or besitos_awarded or atomicity or TestReward or cross_service_atomicity" -q --tb=line -p no:cov --override-ini="addopts="`
   - Grep de reglas/patrones: `grep -n "self\.besito_service = \|BesitoService(db=self.db)\|on_besitos_awarded_rewards\|rewards | besitos_awarded_received\|MUST NOT credit\|Cross-domain event listeners" services/reward_service.py bot.py tests/unit/test_reward_service.py | head -20`
   - Smokes: `python -c "from services.reward_service import RewardService, on_besitos_awarded_rewards_observer; print('import ok')"; python -c "import bot; print('bot import ok')"`
   - Para smoke listener + emit (bajo loop): usa un snippet con asyncio.get_event_loop().run_until_complete o pytest caplog en un test temporal si es el camino más barato (pero scope tight → prefer el smoke simple + nota que re-runs de credit paths cubren el schedule).
   - Para contar/inspeccionar: `grep -c "def " services/reward_service.py` o `python -c 'import inspect; ...'` (raro aquí).
   - Evita sleeps; usa comandos directos. Si tool soporta background para integ lentas, úsalo pero log secuencial prefer.
   - Al final: re-ejecuta los combinados + broader smoke filtrado por reward/atomic/mission/besitos_awarded + self-check en log.

4. **Patrones a copiar (no reinventar):**
   - Listener + comment block + "MUST NOT credit" + best-effort doc: copia EXACTA de `services/story_service.py:670-694` (el bloque # Cross-domain... + async def on_besitos_awarded_from_gamification + docstring + log + final comment); adapta solo el prefijo de log ("rewards |" vs "narrative |"), el nombre del def (decisión F3), y 2-3 frases de "rewards domain" + "0 impact on deliver_reward contracts". Colócalo al final del archivo después de la clase/close.
   - Registro central + comentario en bot.py: copia de `bot.py:199-202` (get_event_bus().register + logger.info); extiende después del de narrative; actualiza el comment "Cross-domain listeners (explicit, central...)".
   - Local Besito with shared db para atomicity: copia espíritu de setups en `tests/integration/test_cross_service_atomicity.py` (_create... + TestSession + db=TestSession() para services que hacen commit interno) + normalización owns en 21-getservice (db= passed → owns=False); aquí es directo BesitoService(db=self.db) dentro del método (no get_service, para mantener el contexto de la tx de deliver explícito).
   - Patch schedule_emit + DESIRED CONTRACT + strict asserts: copia de `tests/integration/test_cross_service_atomicity.py` (el patch en el happy path + asserts de balance/tx/MISSION source + docstring "post-credit misiones (best effort) + event listeners (best effort)") + besito unit post-Item1 + event_bus tests.
   - 1-line test fix + comment: minimal como en ports de Item2 (cambio de acceso + nota "ported / 1-line fix post Item X").
   - GSD entries detalladas con "pre-" + descripción + qué se valida después (ruff/pytest/grep) + patrones copiados + "DoD refs".
   - Safe points + self-check al final del log (estructura de Item 1/2/21/22: lista fases/DoD/gates/archivos/tests que pasaron/reglas verificadas (GSD pre every, scope tight 0 new files/0 behavior/0 atomicity/0 other, logging, patch, local db=, "MUST NOT", 1-line, etc.)/desviaciones/tests críticos/"Item closed. Ready for ... + arch-enforcer + test-guardian").
   - Precedentes de PLAN/GSD: `.planning/phases/22-critical-tests-three-systems/PLAN.md` (y SUMMARY), 21/20/19 PLANs + gsd logs citados.
   - Atomicity gold: `tests/integration/test_cross_service_atomicity.py` (file+TestSession, try/finally dispose/close, DESIRED, patch event, strict == on deltas/counts, "credit survives deliver False").

5. **Decisiones (sección 4 del PLAN):** Al inicio de la fase relevante (primer GSD entry de la fase), registra qué decidiste para nombre de listener, cómo estructuraste el local Besito(db=) (1 línea o con var), si el import en el test fue necesario, etc. Si difieres del "preferido", explica brevemente (mantén espíritu tight + gold + 0 behavior).

6. **Gates y re-runs:** 
   - Corre los targeted pytest con los flags exactos de arriba.
   - Si un unrelated fail preexistente aparece (ej. alembic_heads u otro en broader), documéntalo en log pero **no lo cuentes como regression del Item**.
   - Re-run de atomicity gold + reward deliver + mission/reward flows + besito credit (emit) es obligatorio en F4 (y spot en F2/F3 si relevante).
   - Siempre GSD pre- antes del pytest/ruff/grep grande.
   - Al final F5: re-ejecuta los combinados + broader smoke filtrado + self-check.

7. **Alcance (recuerda siempre):** Solo edita los archivos listados en "Archivos que se modificarán" + el log GSD + (este PLAN ya está) + opcional SUMMARY.md al final. Si sientes la tentación de "reducir más composiciones (broadcast etc)", "agregar tests para el listener", "cambiar a get_service", "tocar handlers o mission_service", "editar más docs", detente: scope tight para esta entrega (recomendado por analyzer: solo RewardService held + local + 1 listener rewards + 1-line test + 2 docs). El analyzer + 22 handoff recomendaron empezar tight aquí.

8. **Al final del Item (F5):**
   - Completa el self-check en el log (lista de fases, DoD cumplidos, archivos modificados, tests que pasaron, reglas verificadas (GSD pre every, scope tight 0/0/0/0, local db= para atomicity, "MUST NOT credit", patch schedule_emit, 1-line, logging, no prod change), desviaciones (si las hubo), tests críticos a re-correr en futuro (lista explícita), "Item 5/23 closed. Ready for gsd-executor of next batch item (if any) + arch-enforcer re-scan (enfocado en reward composition + listener wiring + 3 critical systems: gamif/missions/rewards/narrative) + test-guardian (correr los tests críticos listados)").
   - (Opcional pero recomendado) Produce `.planning/phases/23-reward-besito-eventbus-decoupling/SUMMARY.md` con executive + refs al log GSD + comandos de re-verificación (sigue estructura de phases/22 o 21 o 20 o 19).
   - Confirma en log: "Self-Check: PASSED".
   - El siguiente agente (gsd-executor next item o arch-enforcer/test-guardian) usará el log + este PLAN + los cambios como fuente de verdad.

9. **Si algo no está claro o difiere del "reporte del analyzer":** El prompt del usuario + este PLAN (basado en discovery completa + el reporte completo descrito en el prompt + handoff explícito de 22-SUMMARY) es la fuente de verdad. Pregunta solo si un gate bloquea por ambigüedad real de nombre/firma/contrato (e.g. listener name exacto); de lo contrario, elige conservadoramente siguiendo precedentes (story listener copy, atomicity gold for the local db= + patch, bot reg block, 1-line minimal, GSD style) y registra la elección en GSD.

**¡Ejecuta con disciplina total. Cierra el Item de forma limpia, segura, medible y con trazabilidad GSD completa. La reducción de la composición held en RewardService (vía el patrón del bus para loose coupling de notificaciones, manteniendo el command credit local para atomicity) queda hecha sin impacto en los 3 sistemas críticos ni en los contratos de entrega/partial failure. Listo para arch-enforcer + test-guardian + siguiente item del batch.**

---

**Fin del PLAN para 23-reward-besito-eventbus-decoupling (Item 5).**

Referencias rápidas para el executor (actualizar con líneas reales durante ejecución si cambian):
- Impact report (source of truth): user prompt description + discovery state (reward_service.py:36-42 __init__ held, 212-227 _deliver_besitos, 332-344 close; story_service.py:670-694 listener block + 678 def; bot.py:199-202 reg; test_reward:133-143 besitos test +142 access; cross_service_atomicity gold).
- Gold cross/race/atomic + patch + "best effort" note: `tests/integration/test_cross_service_atomicity.py`.
- Story listener precedent (copy source): `services/story_service.py:670-694` (comment + on_besitos_awarded_from_gamification + "MUST NOT" + log).
- Central reg precedent: `bot.py:199-202` + imports 71-73.
- EventBus + schedule_emit + DESIRED: `services/event_bus.py:33-41` (contract), 121-144 (schedule), 109 (get).
- Reward delivery test (1-line site): `tests/unit/test_reward_service.py:133-144` (test_deliver_reward_besitos).
- Precedentes PLAN/GSD + handoff: `.planning/phases/22-critical-tests-three-systems/PLAN.md` (y SUMMARY que nombra explícitamente este Item 5), 21-getservice/PLAN.md, 20-reward-gamif/PLAN.md, 19-eventbus-poc/PLAN.md + gsd-*.log citados.
- GSD log para este Item: `.planning/quick/gsd-reward-besito-eventbus.log`
- Reglas: `CLAUDE.md`, `rules.md`, `architecture.md`, `handlers/CLAUDE.md`, `services/CLAUDE.md`, `services/missions/CLAUDE.md`, `models/CLAUDE.md`, `decisions.md`.
- Next: gsd-executor para este item → (si batch) siguiente item + arch-enforcer re-scan + test-guardian (re-correr críticos listados en self-check).

Listo para gsd-executor. Ejecuta F1 → ... → F5 con GSD pre en cada paso. Self-Check: PASSED al final. Handoff explícito.
