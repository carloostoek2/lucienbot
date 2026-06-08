# PLAN: Tests específicos para los tres sistemas críticos (Gamificación, Narrativa, Channel/VIP) — Item 4

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-06-08  
**Focus:** Tight, conservative, phased addition/expansion of targeted quality tests (~4-6 per critical system) for gamification (races/concurrencia, limits daily no-exceed, canjear recompensa deduct+tx, insuff graceful, get_service lifecycle), narrative (transiciones/FSM/arquetipo once-only + no overwrite, invalid branch graceful no corrupt, invalid cost/VIP trans rejected no partial, EventBus listener receive, FSM restore sim via make_fsm_context + progress persist), channel/VIP (grant/revoke, pay accede VIP + remove free cross, expire no error if not member, ban prop to both channels, offline grant/revoke via startup/expire check recovery, multi subs + partial expire, get_service lifecycle). Zero prod changes. Extend existing files only (no new domains, no broad E2E handlers unless critical for contract). Use gold patterns from impact report + codebase: file SQLite + TestSession (for cross/race/atomic with internal commits), make_user/make_callback/make_fsm_context + sample_* (with TG telegram_id enforcement per DESIRED CONTRACT), patch for EventBus (schedule_emit) + get_service, asyncio.gather(..., return_exceptions=True) + locks/FOR UPDATE for races (assert <=1 success), strict == / .count() / delta exact / "in" only for Lucien voice msgs, N806 tolerated for TestSession name (exact precedent), DESIRED CONTRACT docstrings quoting task bullets or ID contracts (TG BigInt for user keys vs internal PK .id), aware datetimes + _ensure_aware, try/finally db.close() + engine.dispose() + svc.close(). Integrate post-get_service (lifecycle owns/close in more units) + EventBus (narrative listener test) + middlewares (not core for these). 6 small phases with gates. Prepares Item 5 (Reduce direct Besito composition in RewardService via EventBus).

**Input principal (source of truth):** 
- Full impact-analyzer report: `.claude/agent-memory/impact-analyzer/item4-tests-gamification-narrative-vip.md` (executive gaps vs skill, exact recommended tests per system with code sketches, mapa de impacto on test files, risks flaky races/fixtures/ID duality, scope tight proposal 4-6/system using gold file-db + TestSession + make_ + DESIRED CONTRACT, post-get_service/EventBus context, 15-18 tests total, handoff notes).
- Precedents and gold: `.planning/phases/21-getservice-unification/PLAN.md` and `20-reward-gamif-rules-compliance/PLAN.md` (exact structure, GSD discipline, phases, DoD, safe points, self-check, instructions for executor); `.planning/phases/19-eventbus-poc/PLAN.md` + SUMMARY (EventBus PoC, narrative listener, patch schedule_emit, cross atomicity extension, DESIRED CONTRACT, no breakage critical systems); gsd logs (gsd-impact-item4-*, gsd-eventbus-poc-item1.log, gsd-reward-gamif-item2.log, gsd-getservice-unification.log); gold tests: `tests/integration/test_cross_service_atomicity.py` (full _create_engine_and_session tmp_path + TestSession reopen pre-svc, DESIRED CONTRACT TG ID comments, patch event_bus, strict dict/balance/progress asserts, N806 tolerance, happy + partial fail paths, try/finally dispose), `tests/integration/test_reaction_full_chain.py` + `test_reaction_mission_flow.py`, `tests/unit/test_broadcast_service_reaction_flow.py` (concurrent gather pilot for dup reaction, get_service usage, TestCheckAndRegisterReaction), `tests/unit/test_besito_service.py` (credit with EventBus patch, race-mock, insuff), `tests/unit/test_story_service.py` (atomic advance commit=False, archetype calc, branching), `tests/integration/test_vip_flows.py` + `test_vip_subscription_lifecycle.py` + `test_free_entry_flow.py` ( _ensure_aware, _create_user TG, redeem/expire/multi, scheduler pilots), `tests/unit/test_vip_service.py` + `test_channel_service.py`, conftest (db_session expire_on_commit=False, make_fsm_context MemoryStorage for restart sim, make_ factories, sample_vip/free/sub/balance/story/archetype/broadcast/reward/mission).
- Project rules: CLAUDE.md (3 systems critical, unit pure logic vs integration cross flows, GSD pre-log, logging "módulo | acción | user_id | resultado", no prod for test plans, exactly-1-service but here tests), rules.md (≤50 LOC, naming verb+context+result, anti-flaky), architecture.md (handlers→services→models), models/CLAUDE.md (no raw, tx for atomics, migrations), decisions.md (EventBus + mw), services/gamification/CLAUDE.md + narrative/CLAUDE.md (besitos_awarded post-credit, on_besitos listener best-effort, no direct credit from narr), services/CLAUDE.md, handlers/CLAUDE.md.
- Current state (post Item 21 get_service + Item 1 EventBus PoC + prior Top10 debt): strong foundation (atomicity gold, reaction chains, vip lifecycles, story atomic, besito units, invariants I1-6, broadcast concurrent pilot, get_service in some units, EventBus schedule in besito + listener in story PoC, ID contracts mostly fixed); gaps explicit in report (real concurrent beyond mocks/gather on SQLite, archetype immutability once-only, FSM restore sim, ban both channels, offline startup, pay+free-remove cross, invalid narrative branch/choice/trans, get_service lifecycle coverage in besito/daily/story/vip/channel units, EventBus listener test explicit).
- GSD enforcement: every pre-edit/pre-gate/pre-verif MUST append to dedicated log (see Instructions). No edits (even to PLAN) without pre-log precedent.

**GSD enforcement:** Executor MUST prefix **every** modification, gate, verification, ruff, pytest, grep, smoke, or summary step with a GSD log append (timestamp | PHASE | description) to `.planning/quick/gsd-critical-tests.log`. Use identical discipline and entry style as gsd-eventbus-poc-item1.log / gsd-reward-gamif-item2.log / gsd-getservice-unification.log / gsd-impact-item4-*.log (pre + post + counts). No edits without pre-log. Planner already did initial pre-create + pre-write entries.

---

## 1. Alcance preciso (In / Out explícito)

### En esta entrega (scope "tight" per analyzer recs + "smallest change" + precedents):
- **Gamification (target 5 tests, extend existing):**
  - `tests/unit/test_besito_service.py`: strengthen/add TestBesitoConcurrentRaces or similar (real-ish gather with file variant or shared + locks; explicit "no double credit" + tx count==1; + get_service lifecycle class TestBesitoServiceLifecycleOrGetServiceContext copying broadcast pattern: owned closes, db= not closed, exc path, no double).
  - `tests/unit/test_daily_gift_service.py`: extend for concurrent claim within 24h/cooldown → at most 1 success/credit (build on atomic pilot in cross); + lifecycle get_service if not present.
  - `tests/unit/test_game_service.py`: add 2-3: limits not exceeded (play_dice/trivia after DAILY_*_LIMIT_FREE/VIP records today → fail + no credit); concurrent plays respect limit (gather); win on correct deducts? (via reward path or direct tx; or "reward deduct + tx on win" via streak promo if overlaps). Use direct GameRecord inserts + patch load_questions for determinism; fresh TG 7770xxxx.
  - `tests/integration/test_cross_service_atomicity.py` (or test_reaction_full_chain if better): add "canjear recompensa descuenta correctamente y registra transacción MISSION" (happy path mission complete → deliver BESITOS/PACKAGE → balance delta + MISSION tx source present; leverages existing deliver_reward path).
  - Re-runs of existing reaction chains + atomicity as gates (0 regression).
- **Narrative (target 5 tests, extend existing):**
  - `tests/unit/test_story_service.py`: add 3-4 methods/tests: archetype assigned once on ending + never overwritten on re-advance/assign (setup progress with archetype, advance to another ending, assert unchanged; + assign_archetype_to_user idempotent); invalid branch/choice graceful no corrupt progress (bad choice_id → success False or prog unchanged, no points added, visited not polluted); invalid transition cost/VIP rejected no partial (cost_besitos high or required_vip → False + Lucien msg str, no debit, no progress update); optionally strengthen advance persists (post commit current_node_id/visited/chapter).
  - Narrative + EventBus: add test (in story unit or minimal integ) for on_besitos_awarded listener receives (patch "services.event_bus.schedule_emit" or call directly; assert logged, no mutation to besitos per contract; use get_service(StoryService) if wiring).
  - FSM restore sim + persist: add async test using make_fsm_context (create ctx, set quiz state + data e.g. answers/current_q, "restart" new ctx same key, assert state/data restored) + note that progress node persists in DB independent (cross with advance atomic test). (MemoryStorage sim; document no real Redis unless fakeredis).
  - Extend story atomic tests if needed for invalid paths.
- **Channel Admin / VIP (target 5-6 tests, extend existing):**
  - `tests/integration/test_vip_flows.py` + `test_vip_subscription_lifecycle.py` + `test_vip_complete_cycle.py` + `test_free_entry_flow.py`: add/extend for pay/redeem grants VIP sub + removes free pending/access (create free pending/sub, redeem token → sub VIP + assert no active free or channel leave); expire user not in channel no error (mock bot or integ, past sub, expire_subscription succeeds, no unban exc); ban propagates to VIP + free (via scheduler or direct, assert mock_bot.ban_chat_member called for both channel_ids); offline grant/revoke recovered on startup/expire check (create past active sub, get_expired, expire → inactive + entry cleared); multi subs + partial expire keeps active ones (2 subs diff channels/ends, expire one, assert other active + user still VIP via has_other or is_user_vip).
  - `tests/unit/test_vip_service.py` + `tests/unit/test_channel_service.py`: add 1-2 lifecycle get_service + offline/partial (copy owns pattern).
  - Re-runs of vip lifecycles + free_entry as gates.
- **Cross/general (get_service + EventBus + re-runs):**
  - Add TestServiceLifecycleOrGetServiceContext (or equiv) to unit files for besito, daily, story, vip, channel (4-6 cases each: owned close, db= not, exc still closes, no double, composer safe; use MagicMock Session or real via get_service(db=...) in integ).
  - `tests/unit/test_event_bus.py`: extend if needed for narrative listener isolation (fresh bus).
  - Re-runs targeted: cross_service_atomicity, reaction full/mission/limit chains, broadcast reaction flow (incl concurrent), vip complete/lifecycle/ritual/free_entry, story progress/advance, invariants, story_service unit, besito/daily/game units.
  - GSD pre every + ruff on all touched + broader smoke 0 reg expected.
- **Behavior/contracts:** All new tests use fresh numeric TG (7772xxxx or per env), explicit model creation (balance.user_id = tg, sub.user_id = tg, progress.user_id=tg, etc per DESIRED CONTRACT comments), file db for races/atomic/cross, strict asserts, DESIRED CONTRACT in docstrings. No change to prod contracts (besitos_awarded payload, reaction_result dict, is_user_vip, advance_to_node return (success, msg, prog), expire_subscription, etc.).
- **Artefacts:** This PLAN.md + GSD entries in log + (optional post) SUMMARY.md. Memory index already points to impact report.

**Archivos que se modificarán (exactos, por orden de fases; prefer extend, minimal adds):**
1. `.planning/quick/gsd-critical-tests.log` (all phases, pre only via echo; no "edit" of source).
2. `tests/unit/test_besito_service.py` (F2 gamif + lifecycle).
3. `tests/unit/test_daily_gift_service.py` (F2 + lifecycle).
4. `tests/unit/test_game_service.py` (F2 limits/race).
5. `tests/integration/test_cross_service_atomicity.py` (F2 redeem + gates).
6. `tests/unit/test_story_service.py` (F3 archetype/invalid/advance + EventBus + FSM sim).
7. `tests/integration/test_vip_flows.py` (and/or test_vip_subscription_lifecycle.py, test_free_entry_flow.py, test_vip_complete_cycle.py) (F4 cross + ban + offline + multi).
8. `tests/unit/test_vip_service.py` (F4 + lifecycle).
9. `tests/unit/test_channel_service.py` (F4 + lifecycle if relevant).
10. Possibly minimal: `tests/conftest.py` (only if critical fixture gap e.g. for game record or event_bus mock helper; prefer direct creation in tests per atomicity gold; document in GSD).
11. Touched units for get_service lifecycle (besito/daily/story/vip/channel as listed).
12. Re-runs/gates do not modify (except log).

**Fuera explícitamente (nada de scope creep):**
- **NO** prod code changes (0 services/handlers/models; tests only).
- **NO** new top-level test files (extend existing; if 1 minimal integ for narrative FSM cross justified only as last resort + GSD entry).
- **NO** full handler E2E or broad coverage % (focus services/contracts per task; "mensaje correcto" for insuff is secondary — cover via service return + voice str if cheap in story test).
- **NO** unrelated domains (trivia/streak new, promotions, store beyond redeem cross if overlaps atomic, backpack, etc.).
- **NO** real Redis/fakeredis unless already in env cheap (use Memory sim + note; progress DB persist is the contract).
- **NO** editing CLAUDEs/decisions/AGENTS/ROADMAP/docs except minimal handoff note if in refactor_testing.md (defer; scope tight to code + tests + this PLAN + log).
- **NO** broad "aumentar cobertura"; no property tests; no new markers unless in run_critical_tests.py (avoid).
- **NO** touching bot.py, middlewares (beyond noting they wrap concurrent), keyboards, alembic.
- **NO** changing contracts or adding defensive in prod for tests.

**Comportamiento observable:** N/A (tests only); existing flows (reactions credit/mission, daily claim, story advance/archetype/quiz, VIP redeem/expire/scheduler, free entry) must remain identical (0 regression in re-runs).

---

## 2. Fases ordenadas (6 fases pequeñas, secuenciales, con gates estrictos)

### Fase 1: Preparación (GSD log, baseline, fixtures/mocks confirm, patrones gold)
**Objective:** Establecer disciplina GSD para el Item (log ya tocado por planner), confirmar baseline de tests tocados (ruff + targeted pytest verdes pre-cambios), mapear fixtures/mocks existentes vs gaps del report (make_fsm, EventBus patch, file TestSession, fresh TG, get_service), preparar setups para races (gather + locks), FSM sim, offline (patch bot + past subs), ID contract enforcement. Sin cambios de lógica de tests aún. Safe point inicial.

**DoD checklist (marcar al completar):**
- [ ] Log `.planning/quick/gsd-critical-tests.log` existe con entries de planner + al menos 1 pre-F1 de executor.
- [ ] Baseline: ruff clean en archivos de test clave a tocar (besito, daily, game, story, vip_*, channel, cross_atomicity, broadcast_reaction_flow, free_entry, etc.).
- [ ] Baseline targeted pytest verdes para suites relevantes (sin -k broad aún): e.g. test_besito_service, test_daily_gift, test_game_service, test_story_service, test_vip_service + 1-2 integ vip/story/atomic (usar flags -p no:cov --override-ini="addopts=" -q --tb=line).
- [ ] Confirm gold patterns: grep o lectura rápida de DESIRED CONTRACT / TestSession / _create_engine / make_fsm_context / patch event_bus / gather return_exceptions / _ensure_aware / TG 7770xxxx en los golds; documentar en log.
- [ ] Mocks/fixtures list: EventBus patch ready (schedule_emit), get_service patch ready (for lifecycle), mock_bot ban/unban, sample_ + direct create for fresh TG; si falta algo crítico en conftest (e.g. game record helper) decidir "direct in test" vs add (prefer direct per gold atomicity).
- [ ] GSD pre + post entries para baseline.
- [ ] Safe point F1.

**Archivos:** Log + (lectura/grep; 0 edits a prod/tests en F1 salvo si baseline revela necesidad mínima de fixture — documentar).

**Cambios clave (bullets accionables):**
- Ejecutar comandos de baseline (ver Instructions para exactos).
- Grep en tests/ para "DESIRED CONTRACT|TestSession|make_fsm_context|schedule_emit|gather.*return_exceptions|_ensure_aware|7770" para confirmar patrones.
- Si se necesita fixture mínima (último recurso): pre-log + edit mínimo en conftest (e.g. add sample_game_record similar a sample_streak); justificar en GSD.
- Actualizar log con "F1 baseline verde + patterns confirmed + gaps: X Y Z (resolved via direct or minimal)".

**Tests que deben pasar antes de avanzar (gates de F1):**
- Ruff en touched test files (list in scope).
- `pytest tests/unit/test_besito_service.py tests/unit/test_daily_gift_service.py tests/unit/test_game_service.py tests/unit/test_story_service.py tests/unit/test_vip_service.py tests/unit/test_channel_service.py -q --tb=line -p no:cov --override-ini="addopts="`
- Spot integ: `pytest tests/integration/test_cross_service_atomicity.py tests/integration/test_vip_flows.py tests/integration/test_free_entry_flow.py -q --tb=line -p no:cov --override-ini="addopts="` (o -k subset si lentos).
- Grep confirm patrones + GSD entries.

**Riesgos + mitigaciones:**
- Riesgo: baseline ya tiene fails preexistentes (alembic, unrelated) → Mit: documentar en log; no contar como regression del Item; usar -k targeted.
- Riesgo: fixtures ID skew en story/game (sample use .id vs TG) → Mit: en F2+ usar fresh TG explícito + DESIRED comments; no fix samples global.
- Bajo: tiempo en baseline → Mit: targeted, paralelo si tool permite pero prefer secuencial para log.

**Safe point:** Baseline verde + patterns confirmed + "F1 safe point - ready for gamif tests; no test code changed yet". Reversible (nada editado en tests aún).

---

### Fase 2: Gamification tests (besito races/insuff/tx, daily concurrent claim, game limits, redeem deduct+tx, lifecycle get_service)
**Objective:** Implementar los 5 tests gamif recomendados + get_service lifecycle coverage en besito/daily units (y cross). Usar file db + TestSession para races/cross; gather para concurrent; patch EventBus; strict asserts; DESIRED CONTRACT. Fortalecer atomicity para "canjear recompensa". Re-runs de chains como gate.

**DoD checklist:**
- [ ] test_besito_service.py: al menos 1-2 nuevos tests/clases (concurrent no double credit using gather or file variant; insuff returns False + no tx; + TestBesitoServiceLifecycleOrGetServiceContext or equiv with 4-6 cases using get_service or direct owns).
- [ ] test_daily_gift_service.py: concurrent claim within cooldown → exactly 1 claim/credit (or at most 1); + lifecycle if applicable.
- [ ] test_game_service.py: 2+ tests for DAILY_*_LIMIT not exceeded (setup records today, play → fail + no tx/credit); concurrent plays respect limit; (bonus) win path registers tx or via redeem cross.
- [ ] test_cross_service_atomicity.py: new test or extension "test_reward_redemption_deducts_and_registers_mission_tx" (or equiv name) — mission complete → deliver → MISSION tx + balance delta exact; happy + note partials unchanged.
- [ ] All new tests use fresh TG (7772xxxx), explicit models or samples with TG enforcement, DESIRED CONTRACT in class/docstring quoting "sumar no excede", "canjear descuenta y registra", "sin saldo mensaje" (service level), "dos requests no duplican".
- [ ] Ruff limpio; GSD pre cada edit + pre-gate.
- [ ] Re-run targeted gamif/reaction/atomic gates verdes (0 nuevas regressions atribuibles).
- [ ] Safe point.

**Archivos:** Los 4 listados arriba (besito, daily, game, cross_atomicity).

**Cambios clave (bullets accionables, orden sugerido por service):**
- Para cada: pre-log GSD "pre-edit <file> (F2 gamif <test-name>) - <descripción + refs DoD + patron gold>".
- Copiar patrones exactos:
  - Para races/concurrent: de test_broadcast_service_reaction_flow.py (asyncio.gather tasks calling service, results filter success, assert len<=1, bal exact 1x, tx count==1); para file use _create_engine_and_session de cross_atomicity.
  - Para limits: setup loop GameRecord or direct for today, call play_*, assert not success or limit_reached, balance unchanged.
  - Para redeem: en cross_atomicity, despues de happy reaction → increment mission (ya hace), assert post deliver: tx with source=TransactionSource.MISSION, delta exact, reward delivered state.
  - Para lifecycle: copiar clase de broadcast unit (Test... with get_service patch or direct Service(db=) + with get_service(XXXService) as s: ... ; assert owns/close calls or not; exc path with pytest.raises + close called).
  - Patch: with patch("services.event_bus.schedule_emit") as mock: ... assert mock.called (best effort).
  - ID: user_id = 77728001; BesitoBalance(user_id=77728001 ...); sub.user_id = tg etc. Añadir comentario DESIRED CONTRACT (Fase4 gamif ID): ...
  - Fechas: usar datetime.now(UTC) aware o _naive_utc_now si servicio interno lo requiere (copiar de atomicity).
- Post edit por archivo: ruff --fix + format --check; smoke python -c "from tests.unit.test_xxx import ...; ..." o pytest targeted del archivo.
- Grep post para "DESIRED CONTRACT" en los nuevos tests.
- Al final F2: re-runs (ver gates) + GSD.

**Tests que deben pasar antes de avanzar:**
- Ruff en los 4 archivos.
- Suite completa por archivo + targeted new: e.g. `pytest tests/unit/test_besito_service.py -q --tb=line -p no:cov --override-ini="addopts="`
- `pytest tests/unit/test_daily_gift_service.py ...`
- `pytest tests/unit/test_game_service.py ...`
- `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="` (incl nuevo test).
- Re-run chains: `pytest -k "TestHandleReaction or TestFullReactionChain or TestReactionMissionFlow or TestReactionLimit or TestCrossServiceAtomicity or reaction or broadcast or atomic or gamif" -q --tb=line -p no:cov --override-ini="addopts="` (debe pasar limpio; documentar pre-existing unrelated).
- Grep: presencia de nuevos tests + DESIRED + TG fresh.

**Riesgos + mitigaciones:**
- Riesgo flaky races on SQLite (cooperative, no real contend, FOR UPDATE serializes) → Mit: assert <=1 (not exactly 1 hit); document "best-effort overlap; prod Postgres stronger contention"; keep mock + constraint as primary; small sleep(0) or separate sessions per task if possible (gold in broadcast concurrent already notes).
- Riesgo: game tests depend on internal _get_today_records or load_questions → Mit: patch load as existing tests do; direct GameRecord insert for limits (deterministic).
- Riesgo: redeem test assumes deliver path registers MISSION tx (may be in RewardService) → Mit: inspect existing atomic happy path; assert on BesitoTransaction source after full flow; if not explicit, strengthen existing or note.
- Mit general: targeted pytest, N806 doc, try/finally cleanup.

**Safe point:** Post-ruff + gamif suites + chains re-run + GSD "F2 safe point - gamif 5 tests + lifecycle added; 0 reg in reaction/atomic; races use gather+file; redeem cross covered". Reversible editando solo estos 4 test files.

---

### Fase 3: Narrative tests (arquetipo once-only, invalid branch/choice/trans, advance persist, FSM restore sim, EventBus listener)
**Objective:** Implementar los 5 tests narrative en story_service unit (extend) + FSM/EventBus. Usar make_fsm_context para sim restart (Memory key share); patch schedule_emit para listener; strict; DESIRED CONTRACT para "arquetipo una sola vez", "rama inválida graceful", "trans inválida rechazada", "FSM restaura". Re-runs de story progress/advance como gate.

**DoD checklist:**
- [ ] test_story_service.py: 4-5 nuevos tests/métodos con nombres claros (test_archetype_assigned_once_on_ending_never_overwritten, test_assign_archetype_idempotent_no_override, test_invalid_branch_choice_graceful_no_corrupt_progress, test_invalid_transition_cost_or_vip_rejected_no_partial, test_advance_to_node_persists_node_and_visited (si no cubierto), + async test_story_fsm_state_restores_after_simulated_restart usando make_fsm_context + note progress DB persist).
- [ ] EventBus listener: test_on_besitos_awarded_listener_receives_best_effort (patch schedule_emit o call story on_ handler; assert logged "narrative | besitos_awarded_received"; no side effect on besitos; use get_service(StoryService) per recent).
- [ ] Todos usan fresh TG, explicit StoryNode/Progress/Archetype creation, DESIRED CONTRACT docstring.
- [ ] Ruff; GSD pre; LOC de funcs de test no aplica (tests).
- [ ] Re-runs story + related gates verdes.
- [ ] Safe point.

**Archivos:** Principalmente `tests/unit/test_story_service.py` (extend clase existente o nueva TestStoryArchetypeImmutability / TestStoryInvalidTransitions / TestStoryFSMEventBus).

**Cambios clave:**
- Pre-log por edit.
- Copiar patrones de story atomic actual (setup node with cost_besitos / required_vip / is_ending, progress, balance; call advance_to_node(uid, node.id, choice_id=bad); assert success False, msg contains "besitos" or "VIP", prog is None or unchanged, no tx created for invalid).
- Para once-only: setup progress.archetype = EXPLORADOR; commit; advance to ending2; refresh; assert == EXPLORADOR (no recalced).
- Para FSM: (async def) ctx1 = await make_fsm_context(user_id=77720001); await ctx1.set_state("story:quiz"); await ctx1.update_data({"answers":[1,3,2], "current_q":3}); ctx2 = await make_fsm_context(user_id=77720001); state=await ctx2.get_state(); data=await ctx2.get_data(); assert state=="story:quiz"; assert data["answers"]==[1,3,2]. Comentar: "MemoryStorage sim for bot restart; real progress persists in DB via advance_to_node (tested separately)".
- Para EventBus: with patch("services.event_bus.schedule_emit") as m: ... (o from services.story_service import on_besitos... ; await on_... ({"user_id":7772, "amount":5, ...})); logger capture or assert m.called; nota "best effort, no mutation per contract".
- Añadir DESIRED CONTRACT en docstrings de clases/tests quoting bullets del task/report.
- Post: ruff; pytest targeted del archivo; grep DESIRED + "archetype" + "invalid".
- Re-run: pytest -k "story or TestStoryService or advance_to_node or archetype" ...

**Tests gates:**
- Ruff + `pytest tests/unit/test_story_service.py -q --tb=line -p no:cov --override-ini="addopts="`
- Re-runs story progress/advance + any cross that touches story (atomicity if has narrative side, mission_e2e if overlaps).
- Grep / inspección de nuevos tests + contratos.

**Riesgos + mitigaciones:**
- Riesgo: FSM test solo Memory (no Redis) → Mit: document "sim via shared key; for full Redis would require REDIS_URL or fakeredis; DB progress is the durable contract".
- Riesgo: listener PoC solo log → Mit: assert log or called; no assert side effects (per PoC contract); future unlocks would add but out of scope.
- Riesgo: archetype calc in quiz/ending hardcode → Mit: test via advance_to_node on ENDING node + assign; use ArchetypeType enum.
- Bajo: story tests a veces usaron .id → Mit: enforce TG en setups nuevos + DESIRED comment.

**Safe point:** Post gates + GSD "F3 safe point - narrative 5 tests + archetype immut + invalid graceful + FSM sim + EventBus listener; 0 reg story/advance". Reversible solo edits a test_story_service.py.

---

### Fase 4: Channel/VIP tests (pay+free remove, expire no-member, ban prop, offline recovery, multi/partial, lifecycle)
**Objective:** Implementar 5-6 tests VIP/channel cross + edges + ban + offline + multi. Extender integ vip_flow* + free_entry + units vip/channel. Usar mock_bot para ban/assert calls both ch; past subs + expire; redeem cross free/VIP; get_service lifecycle. Re-runs vip lifecycles + free_entry.

**DoD checklist:**
- [ ] Al menos 5-6 nuevos tests o extensiones fuertes en los integ vip/free + units: test_redeem_vip_grants_and_removes_free, test_expire_not_in_channel_no_error, test_ban_propagates_vip_and_free (assert_any_call both), test_offline_grant_recovered_on_startup_expire_check, test_multiple_subscriptions_partial_expire_keeps_active, + lifecycle owns/get_service en vip/channel units.
- [ ] Setups usan _create_user o direct con TG, sample_vip_channel + sample_free_channel, sample_tariff/token/sub expired/past; _ensure_aware para compares; mock_bot con ban/unban.
- [ ] DESIRED CONTRACT en tests quoting "pay accede + remove free", "expirado sin error si no en canal", "ban propaga ambos", "grant/revoke offline funciona", "multi + partial".
- [ ] Ruff + GSD + gates re-run vip/free verdes.
- [ ] Safe point.

**Archivos:** `tests/integration/test_vip_flows.py`, `tests/integration/test_vip_subscription_lifecycle.py`, `tests/integration/test_free_entry_flow.py`, `tests/integration/test_vip_complete_cycle.py` (extend 2-3 principales), `tests/unit/test_vip_service.py`, `tests/unit/test_channel_service.py`.

**Cambios clave:**
- Pre-log por archivo.
- Para cross pay+free: setup free pending or sub + vip token; redeem_token or equiv → assert sub created for vip ch; assert no pending active for free or channel_service marks removed/leave.
- Para expire no err: sub past + is_active=True, user not member (mock or just call expire_subscription(sub.id)); assert result True; no exc from bot.unban (use side_effect or just don't assert call if offline).
- Para ban prop: patch scheduler or call exposed (e.g. via VIPService or import from scheduler bits if public; or direct in integ with mock_bot); after "ban flow" assert mock_bot.ban_chat_member.assert_any_call(chat_id=vip_ch.channel_id, user_id=uid); same for free_ch.
- Para offline: create sub end_date=past, is_active=True; expired = vip.get_expired_subscriptions(); assert any; then expire; re-query inactive + vip_entry cleared (per startup check contract).
- Para multi/partial: 2 subs, diff ch/end; expire one (by id or date); assert other remains is_active=True; user still "VIP" via has_active or is_user_vip on other ch.
- Lifecycle: similar to F2, add class TestVIPServiceLifecycle... with get_service(db=) etc.
- Usar helpers existentes del file (_now, _ensure_aware, _create_user, _future, _past) — copiar estilo.
- Post edit: ruff; pytest targeted por file o -k "vip or free_entry or TestVIP or expire or redeem".
- Re-runs obligatorios de vip complete/lifecycle/ritual + free_entry.

**Tests gates:**
- Ruff en archivos vip/free.
- `pytest tests/integration/test_vip_flows.py tests/integration/test_vip_subscription_lifecycle.py tests/integration/test_free_entry_flow.py -q --tb=line -p no:cov --override-ini="addopts="` (o -k "vip or free or redeem or expire or ban or offline or multi").
- `pytest tests/unit/test_vip_service.py tests/unit/test_channel_service.py ...`
- Re-run broader: `pytest -k "vip or channel or free_entry or TestVIP or subscription_lifecycle" ...`
- Grep DESIRED + TG enforcement.

**Riesgos + mitigaciones:**
- Riesgo: ban flow private in scheduler → Mit: use patch on bot, call public methods on VIP/Channel or import _process if exposed for test; or integ that exercises scheduler path with real time (but use past dates); document.
- Riesgo: "remove free" on redeem may be in handler (clear pending) or channel_service → Mit: assert at service level (no active pending for user on free ch) or cross check with PendingRequest query; if handler, note as integration via free_entry test.
- Riesgo: tz naive in subs → Mit: use _ensure_aware + aware now() as in existing vip tests.
- Bajo: scheduler tests lentos → Mit: targeted, mock time if needed but prefer date setup.

**Safe point:** Post gates + GSD "F4 safe point - VIP/channel 5-6 edges + ban + offline + multi + pay+free + lifecycle; 0 reg in vip lifecycles/free". Reversible edits solo en test files vip/channel.

---

### Fase 5: Integration/cross + get_service coverage + re-runs targeted + gates
**Objective:** Completar cobertura get_service lifecycle (si no en units de F2/F4), re-ejecutar todas las gold integrations críticas que tocan los 3 sistemas (atomicity, reaction chains, vip lifecycles, story advance/archetype, invariants, broadcast reaction concurrent), broader smoke filtrado, confirmar 0 regressions nuevas. Gates finales por sistema + cross.

**DoD checklist:**
- [ ] get_service lifecycle cubierta en besito/daily/story/vip/channel units (al menos 4-6 casos por; si no en F2/F4, agregar aquí).
- [ ] Re-runs completos targeted: cross_service_atomicity (full incl nuevo redeem), reaction full/mission/limit + handler TestHandleReaction, broadcast reaction flow (incl concurrent), vip complete/lifecycle/ritual/free_entry/subscription, story_service unit + any progress, invariants (I1-3 besito, I4 token, I5 VIP, I6 reaction), daily/game units, story/vip atomic paths.
- [ ] Broader smoke: `pytest -k "gamif or story or vip or channel or besito or daily or game or reaction or atomic or mission or free_entry or invariants" -q --tb=line -p no:cov --override-ini="addopts="` (exit 0 o documentar unrelated pre-exist).
- [ ] Ruff limpio en todos los archivos tocados en Item.
- [ ] GSD entries + "F5 cross + re-runs done".
- [ ] Safe point.

**Archivos:** Ninguno nuevo (solo re-runs + log; si lifecycle faltante, units ya listados).

**Cambios clave:** Solo ejecución de comandos (ver Instructions). GSD pre cada pytest/ruff/grep grande. Si unrelated fail (alembic_heads etc), documentar pero no contar como regression Item 4.

**Tests gates:** Los re-runs + broader smoke + ruff. Contar "0 nuevas regressions atribuibles a tests agregados".

**Riesgos:** Integ lentas → Mit: targeted -k primero, luego combinado; -p no:cov; background si tool soporta pero log secuencial prefer.

**Safe point:** Re-runs + smoke verdes + GSD "F5 safe point - all critical chains 0 reg; get_service + EventBus covered; 3 systems protected".

---

### Fase 6: Verificación final, criterios, self-check + handoff
**Objective:** Confirmar scope completo limpio/medible/listo para arch-enforcer re-scan + test-guardian (correr los tests críticos listados). Completar GSD log con self-check PASSED explícito + lista de "tests críticos a re-correr en futuro". Opcional SUMMARY.md. Hand off para Item 5 (EventBus Reward).

**DoD checklist:**
- [ ] Todos los archivos tocados (test units/integs listados) pasan ruff check + format --check.
- [ ] Grep global o por sistema: presencia de DESIRED CONTRACT en nuevos tests; fresh TG 777x en setups de races/atomic/vip/story; 0 "sample_user.id" en nuevos setups (TG en su lugar donde contract exige).
- [ ] Conteo aproximado de tests agregados/extendidos ~15-18 (o por sistema 4-6+); listar en log.
- [ ] Re-runs finales de targeted críticos (repetir F5 commands + smoke).
- [ ] GSD log tiene entradas para cada fase + pre-gates + self-check al final con estructura: lista de fases/DoD/gates/archivos modificados/tests que pasaron/reglas verificadas (1-service no aplica aquí pero contracts sí; LOC no para tests; logging en tests si agregamos prints no, pero service logs indirect; GSD discipline seguida)/desviaciones (si las)/tests críticos para futuro (los mismos integ + units + nuevos tests de races/archetype/invalid/edges + get_service lifecycle + EventBus listener)/"Item 4 closed. Ready for gsd-executor Item 5 (Reduce direct Besito composition in RewardService via EventBus) + arch-enforcer + test-guardian".
- [ ] Self-check explícito "Self-Check: PASSED".
- [ ] (Opcional) SUMMARY.md en el dir de la phase con executive + refs al log + comandos de re-verif (sigue precedente phases/20/19/21).
- [ ] Safe point final + criterio de éxito del plan.

**Archivos:** Ninguno nuevo (log + opcional SUMMARY; edits ya hechos).

**Cambios clave:** Solo verificación + echo al log. Usar run_terminal para comandos gate final + conteos.

**Tests gates:** Targeted finales + ruff global touched + broader smoke filtrado + self-check.

**Riesgos:** Ninguno nuevo (verif).

**Safe point final + criterio de éxito:** Todos DoD F6 + self-check PASSED en log. El plan completo + log GSD son evidencia para siguiente agente (gsd-executor Item 5 o arch-enforcer/test-guardian). 0 breakage en critical systems; tests específicos protegen las bullets del task (races, archetype, FSM, ban, offline, pay+free, invalid narr, redeem, limits, get_service, EventBus).

---

## 3. Estrategia de tests general

- **Unit para lógica pura (limits, archetype once, invalid branch, get_service owns/close, EventBus register/emit isolation):** db_session (in-mem rollback + expire_on_commit=False); direct model inserts con TG explícito; patch load_questions / schedule_emit / besito internals si needed; strict return dicts / state / counts.
- **Integration para flujos cross (atomicity, reaction chains, races con commits internos, VIP redeem/expire/scheduler, FSM + progress persist, ban prop, offline recovery):** file SQLite tmp_path + TestSession (gold exact de atomicity/reaction_full/streak); reopen db=TestSession() post setup commits antes de svc calls (porque credit/claim/advance/broadcast/reward hacen commit propio + SessionLocal internos); @pytest.mark.integration + @pytest.mark.asyncio; fresh TG por test (77708xxx etc); mock_bot=AsyncMock(); try/finally: db.close(); engine.dispose(); svc.close() with suppress; N806 tolerated + docstring "exact precedent".
- **Races/concurrencia:** asyncio.gather( task1, task2, return_exceptions=True ); filter successes or exceptions; assert len<=1 (o count success <=1); balance/tx exact 1x; usar file db si in-mem coopera demasiado; locks/FOR UPDATE ya en prod (besito); document "SQLite best-effort; prod Postgres contend".
- **FSM restore:** make_fsm_context (MemoryStorage real); mismo user_id/chat_id → same StorageKey → load; sim "restart" creando ctx2 después de ctx1 set; combinar con DB persist (advance_to_node) para contrato durable.
- **EventBus:** patch("services.event_bus.schedule_emit") en emitter tests (besito/credit); para listener: fresh InternalEventBus() o patch + call on_ handler o register mock listener; assert called/logged; best-effort (no raise, no mutation per contract).
- **get_service lifecycle:** copiar patrón broadcast unit (Test...LifecycleOrGetServiceContext); with patch("...get_service") o direct Service(db=passed) + with get_service(Svc) as s: ... ; assert owns/close or not closed; exc path pytest.raises + close still; composer subs safe (owns=False when shared db).
- **ID contract (critical per prior fixes + report):** todos setups nuevos: user keys = telegram_id (tg_id var); balance.user_id=tg, sub.user_id=tg, claim.user_id=tg, progress.user_id=tg, reaction.user_id=tg, game.user_id=tg, etc. Añadir comentario "DESIRED CONTRACT (Item 4 / Fase4 gamif ID): ... matching models + handlers + sample_balance post-fix. PK .id internal only."
- **DESIRED CONTRACT + strict:** docstring por clase/test quoting bullet del task o contrato (e.g. "advance persiste", "arquetipo una sola vez", "rama inválida no rompe"); asserts == not "in" (salvo msgs voz Lucien), deltas exact, .count()==1 o len(results)<=1, state is True/False, no loose.
- **Gates:** siempre -p no:cov --override-ini="addopts=" para exit limpio (precedente phases); targeted -k primero; broader smoke al final; ruff pre/post edit; GSD pre cada.
- **Cobertura logging:** no asertado en tests usualmente; gate inspección manual durante edits + mención en GSD.
- **Precedente --override-ini + N806:** atómico en atomicity/reaction/streak; tolerar + documentar.
- **No scope creep en tests:** solo los ~15-18 targeted; re-runs protegen chains existentes.

---

## 4. Decisiones de diseño (el executor debe confirmar o registrar desviación en el primer GSD entry de la fase relevante)

1. **Nombres de tests:** Seguir sketches del report + convención (test_<verbo>_<contexto>_<resultado>): e.g. test_concurrent_credits_use_for_update_no_double, test_archetype_assigned_once_on_ending_never_overwritten, test_invalid_branch_choice_graceful_no_corrupt_progress, test_redeem_vip_grants_vip_sub_and_removes_free_pending_or_access, test_ban_user_propagates_to_vip_and_free, test_offline_grant_recovered_on_startup_expire_check, test_play_dice_does_not_exceed_daily_limit_free, test_reward_redemption_deducts_and_registers_mission_tx, test_story_fsm_state_restores_after_simulated_restart, test_on_besitos_awarded_listener_receives_best_effort. Confirmar en GSD F2/F3/F4 primer entry; ajustar si nombre ya existe (agregar _via_gather o _after_get_service_unif).
2. **Cómo mock EventBus:** patch("services.event_bus.schedule_emit") (como en besito credit test y atomicity F4 extension); para listener test: o bien call directamente la función on_ registrada en story (si expuesta) o fresh bus = InternalEventBus(); bus.register(EVENT..., mock_listener); await bus.emit(...); o patch en story_service. Preferir patch schedule_emit para "receive" best effort. Documentar "best effort, errors swallowed, no mutation to besitos".
3. **Fixtures para restart FSM:** Usar make_fsm_context tal cual (MemoryStorage); sim restart = crear ctx2 con mismo user_id/chat_id (mismo StorageKey); no tocar REDIS_URL. Para full Redis: document "requeriría fakeredis o env; DB progress es el contrato durable (probado en advance atomic)". Si se quiere un test con real RedisStorage, condicionar en if REDIS but scope tight → Memory sim suficiente + nota.
4. **Concurrent setups (races):** Para besito/credit/reaction: gather de 2+ tasks llamando credit_besitos o check_and_register_reaction (con shared db o file per task si coop issue); para daily: gather de 2 claim_gift con mismo user dentro cooldown; para game: gather plays. Siempre return_exceptions=True; assert len([r for r in if success or not exc]) <=1 ; bal/tx exact 1x. Usar file+TestSession si in-mem no contende visiblemente. Copiar de broadcast concurrent + atomicity _create.
5. **get_service lifecycle tests:** Nombre de clase Test<Domain>ServiceLifecycleOrGetServiceContext (o TestServiceLifecycle para broadcast-like); copiar estructura exacta del broadcast unit (tests de owned vs passed db, exc path, no double close, composer subs). Ubicación: agregar al final del unit file (besito, daily, story, vip, channel). Usar MagicMock para Session en unit puro; real get_service(db=TestSession()) en integ si se quiere.
6. **DESIRED CONTRACT placement:** En docstring de la clase TestXXX (como en atomicity TestCrossServiceAtomicity y broadcast TestCheckAndRegisterReaction) + comentarios inline en setups ID-critical. Citar bullets del task o "ID contract: user_id stores TG BigInt (telegram_id) per model FK...".
7. **Tolerancia N806 TestSession:** Exact precedent (atomicity, reaction_full, streak); dejar nombre TestSession = sessionmaker... ; añadir comentario en _create o al inicio de clase "N806 tolerated for TestSession (exact precedent from test_cross_service_atomicity.py + reaction_full_chain.py)".
8. **Uso de tmp_path vs db_session:** file+TestSession SOLO para cross/race/atomic con internal commits (credit, claim, advance, broadcast, reward deliver, scheduler expire); db_session (in-mem) para units puros (besito credit simple, story advance con mock debit, game limits, archetype, invalid, lifecycle owns con mocks).
9. **Log file GSD:** `.planning/quick/gsd-critical-tests.log`. Formato:
   ```
   === 2026-06-08Txx:xx:xx+00:00 | PHASE 2 | GSD pre-edit tests/unit/test_besito_service.py (F2 concurrent race) - Agregar test_concurrent_credits... + lifecycle class; copiar gather de broadcast_reaction_flow + DESIRED TG; DoD refs.
   ```
   (o pre-ruff, pre-pytest -k "besito or atomic", pre-grep "DESIRED", pre-final-self-check). Apuntar 5-10+ entries por fase.
10. **Comandos concretos:** Ver sección Instrucciones abajo. Siempre con -p no:cov --override-ini="addopts=" para pytest targeted. Para LOC no aplica (tests); para smoke: python -c "import ...; print('ok')".
11. **Si se necesita 1 archivo nuevo (e.g. test_story_progress_integ.py):** Solo como último recurso (report permite "o add to"); justificar brevemente en GSD F3; mantener mínimo (solo FSM + persist cross); preferir extender test_story_service.py o test_mission_e2e.py si se solapa.
12. **Orden dentro fase:** Un archivo a la vez o batch barato; gates intermedios por service si se quiere (e.g. besito done → gate → daily); pero F2 puede batch gamif ya que todos gamif. F4 batch vip integs.
13. **Cualquier desviación:** Registrar en GSD entry de la fase + nota breve al final del PLAN o en SUMMARY.

Cualquier decisión que difiera de lo anterior debe registrarse en el GSD log + nota breve al final del PLAN o en SUMMARY posterior.

---

## 5. Criterios de verificación + gates finales

**Criterios de éxito del Item (medibles, para self-check del executor):**
- ~4-6 tests por sistema (total ~15-18) agregados/extendidos en los archivos listados; todos pasan.
- Tests cubren explícitamente los bullets del task/report: races/concurrencia (gather + <=1), limits no exceed, canjear deduct+tx, archetype once-only + no change, invalid branch/choice/trans graceful no partial, FSM restore sim (Memory), EventBus listener receive, pay+free remove cross, expire no err if not member, ban prop both channels, offline grant/revoke recovery, multi/partial expire, get_service lifecycle owns/close/exc (besito/daily/story/vip/channel), advance persist.
- Re-runs de gold chains (atomicity, reaction full/mission/limit, broadcast concurrent, vip lifecycles/ritual/free_entry, story advance, invariants, units besito/daily/game/story/vip) pasan sin regressions atribuibles a los tests nuevos.
- Ruff limpio en todos los archivos tocados.
- Verificaciones de reglas/patrones: grep "DESIRED CONTRACT" presente en nuevos tests; fresh TG 777x en race/atomic/vip/story setups; N806 tolerance documented; file+TestSession usado donde internal commits; patch EventBus/get_service; make_fsm usado; _ensure_aware donde tz; strict asserts (==, deltas, <=1, not "in" salvo voz).
- GSD log completo con pre-entries (5-10+/fase) + self-check "PASSED" + lista explícita de "tests críticos a re-correr en el futuro para estos cambios" (los mismos integ + units + los nuevos races/archetype/invalid/edges/lifecycle/listener) + "Item 4 closed. Ready for gsd-executor of Item 5 (Reduce direct Besito composition in RewardService via EventBus) + arch-enforcer re-scan (enfocado en tests de 3 sistemas) + test-guardian (correr los tests críticos listados)".
- 0 prod changes; 0 scope creep; comportamiento de flujos existentes idéntico (re-runs verdes).
- Safe point final documentado; item listo para siguiente en batch (Item 5) y guardians.

**Gates por fase (ver secciones de fases para detalles):**
- Pre-edit: GSD log entry.
- Post-edit: ruff + targeted pytest (cuando aplique) + smoke + grep/LOC (si helper) + GSD entry de resultado.
- Avanzar solo si gate verde (o documentar desviación menor).
- F5/F6: re-runs obligatorios + broader smoke + self-check.

**Comando combinado sugerido para gates finales (adaptar por fase; targeted primero):**
```
./venv/bin/python -m pytest -k "besito or daily_gift or game or story or vip or channel or cross_service_atomicity or reaction or broadcast or atomic or free_entry or invariants or TestCrossServiceAtomicity or TestFullReactionChain or TestReactionMissionFlow or TestHandleReaction or TestVIP or subscription_lifecycle or advance_to_node or archetype" -q --tb=line -p no:cov --override-ini="addopts="
```
Para suites específicas: `pytest tests/unit/test_besito_service.py ...` (con flags).

---

## Instrucciones para el gsd-executor

Este PLAN.md es tu prompt de ejecución. Síguelo al pie de la letra, sin scope creep. El trabajo es para UNA persona (tú) + disciplina GSD total. El flujo continúa automáticamente con gsd-executor para este Item 4, luego el siguiente del batch (Item 5: Reduce direct Besito composition in RewardService via EventBus).

1. **GSD discipline (non-negotiable, como en todas las phases exitosas):**
   - ANTES de **cualquier** modificación (search_replace/write/edit en tests o log), antes de ruff, pytest, grep de verif, smoke, o resumen: append al log.
   - Log: `.planning/quick/gsd-critical-tests.log`
   - Crea el archivo si no existe (planner ya lo tocó; primer entry de executor puede ser confirm).
   - Formato de entry (copia estilo de gsd-eventbus-poc-item1.log / gsd-reward-gamif-item2.log / gsd-getservice-unification.log / gsd-impact-item4-*.log):
     ```
     === 2026-06-08Txx:xx:xx+00:00 | PHASE 2 | GSD pre-edit tests/unit/test_besito_service.py (F2 concurrent + lifecycle) - Agregar test_concurrent_credits_use_for_update_no_double + TestBesitoServiceLifecycleOrGetServiceContext; copiar gather+DESIRED de broadcast_reaction_flow + atomicity; refs DoD F2.
     ```
     Luego ejecuta el comando de edit/tool.
   - También pre-gate (pre-pytest, pre-ruff, pre-grep "DESIRED CONTRACT|777", pre-final-self-check).
   - Cuenta las entradas; apunta a 5-10+ por fase (como precedentes). Al final del Item el log debe tener el self-check completo.
   - Usa `run_terminal_command` con `echo "=== $(date -Iseconds) | PHASE N | ..." >> .planning/quick/gsd-critical-tests.log` (o printf). Nunca edites sin pre-log.

2. **Orden estricto:** Ejecuta Fase 1 completa (con gates) → gates F1 → Fase 2 (gamif, un service/test a la vez o batch) → gates F2 → Fase 3 (narrative) → gates → Fase 4 (channel/vip) → gates → Fase 5 (cross + re-runs) → gates → Fase 6 (verif final + self-check). **No saltes fases ni hagas "todo de una".** Marca DoD mentalmente o en el log al completar cada checklist. Al final de cada fase documenta "F<N> safe point" en log.

3. **Herramientas y comandos concretos (usa run_terminal_command para estos):**
   - GSD logs: `echo "=== $(date -Iseconds) | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados>" >> .planning/quick/gsd-critical-tests.log`
   - Mkdir (si planner no lo hizo, pero ya existe): `mkdir -p .planning/phases/22-critical-tests-three-systems`
   - Ruff: `./venv/bin/python -m ruff check <file> --fix` ; luego `./venv/bin/python -m ruff format --check <file>` (o apply).
   - Pytest targeted (siempre con estos flags para exit limpio): `./venv/bin/python -m pytest <path or -k "expr"> -q --tb=line -p no:cov --override-ini="addopts="`
     - Ejemplos:
       - `pytest tests/unit/test_besito_service.py -q --tb=line -p no:cov --override-ini="addopts="`
       - `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="`
       - `pytest -k "TestHandleReaction or TestFullReactionChain or TestReactionMissionFlow or TestReactionLimit or TestCrossServiceAtomicity or reaction or broadcast or atomic or gamif or story or vip or channel or free_entry or invariants or besito or daily or game or advance_to_node or archetype" -q --tb=line -p no:cov --override-ini="addopts="`
       - Para suites vip: `pytest tests/integration/test_vip_flows.py tests/integration/test_vip_subscription_lifecycle.py tests/integration/test_free_entry_flow.py -q --tb=line -p no:cov --override-ini="addopts="`
   - Grep de reglas/patrones: `grep -n "DESIRED CONTRACT\|TestSession\|make_fsm_context\|schedule_emit\|gather.*return_exceptions\|_ensure_aware\|7770\|7772" tests/unit/test_besito_service.py tests/unit/test_story_service.py tests/integration/test_cross_service_atomicity.py tests/integration/test_vip_flows.py ... | head -20`
   - Smokes: `python -c "from tests.unit.test_besito_service import TestBesitoService; print('import ok')"; python -c "from services import get_service; from services.besito_service import BesitoService; print('get_service ok')"`
   - LOC (si helper en test, raro): `python -c 'import inspect; from handlers... import ...; src=inspect.getsourcelines(func)[0]; print("LOC:", len(src))'` (no aplica usualmente).
   - Para contar tests nuevos al final: `grep -c "def test_" tests/unit/test_besito_service.py ...` o similar + diff vs baseline.
   - Evita sleeps; usa comandos directos. Si tool permite background para integ lentas, úsalo pero log secuencial.

4. **Patrones a copiar (no reinventar):**
   - Gold DB cross/race/atomic: copia EXACTA de `tests/integration/test_cross_service_atomicity.py` (_create_engine_and_session(tmp_path), TestSession = sessionmaker..., db=TestSession(), setup con tg_id=77708xxx explicit models, db.close(); db=TestSession() reopen pre svc, try/finally db.close(); engine.dispose(); svc.close(), DESIRED CONTRACT comments on TG vs PK, N806 tolerance comment, patch("services.event_bus.schedule_emit"), strict == on dict keys / balance delta / progress.is_completed / tx source / len<=1).
   - Concurrent races: copia de `tests/unit/test_broadcast_service_reaction_flow.py` (asyncio.gather(tasks, return_exceptions=True), filter successes, assert len(successes) <=1, bal/tx exact 1x; usa file si in-mem coopera).
   - FSM sim: copia uso de make_fsm_context en handlers tests o story; create ctx1 set state/data, ctx2 same key, assert restored. Comentar Memory sim + DB persist cross.
   - VIP tz/ID: copia de `tests/integration/test_vip_flows.py` (_ensure_aware, _create_user con TG, _now/_future/_past, explicit Subscription(user_id=tg, channel_id=pk), sample_vip + sample_free).
   - EventBus: copia de besito unit (with patch schedule_emit as mock: credit... ; assert mock.called) + event_bus.py DESIRED CONTRACT (fresh bus for isolation, gather return_exceptions, best effort, no raise to caller).
   - get_service lifecycle: copia de `tests/unit/test_broadcast_service_reaction_flow.py` (clase Test... con with patch get_service or direct; __enter__ / owns / close / exc path / no double; composer subs).
   - Story atomic/invalid: copia de `tests/unit/test_story_service.py` actual (setup node cost/ending/vip, progress, balance TG; call advance; assert success/False + msg + prog None/unchanged; mock debit with commit=False).
   - ID enforcement: "DESIRED CONTRACT (Item 4 / post Fase4): user_id stores TG BigInt (telegram_id value) per models (BesitoBalance.user_id BigInteger... no FK to users.id/PK), real handler flows (from_user.id), besito_service credit/debit keys, and VIP/channel ID contract fixes. Matches sample_user.telegram_id; never the internal PK .id."
   - Logging GSD: "pre-" + descripción + qué se valida después (ruff/pytest/grep) + patrones copiados.
   - Safe points + self-check al final del log (como en Item 1/2/21): lista fases/DoD/gates/archivos/tests/rules/desviaciones/tests críticos/"Item closed. Ready for ... Item 5 + arch-enforcer + test-guardian".
   - Precedentes de PLAN/GSD: `.planning/phases/21-getservice-unification/PLAN.md`, `.planning/phases/20-reward-gamif-rules-compliance/PLAN.md`, `.planning/phases/19-eventbus-poc/PLAN.md` + 19-*-SUMMARY.md, gsd logs citados.

5. **Decisiones (sección 4 del PLAN):** Al inicio de la fase relevante (primer GSD entry de la fase), registra qué decidiste para nombres de tests, cómo mockeaste EventBus (patch vs fresh), si usaste file o in-mem para cada race, si agregaste fixture a conftest (prefer no), cómo manejaste ban flow privado (patch o import), etc. Si difieres del "preferido", explica brevemente (mantén espíritu tight + gold).

6. **Gates y re-runs:** 
   - Corre los targeted pytest con los flags exactos de arriba.
   - Si un unrelated fail preexistente aparece (ej. alembic_heads u otro en broader), documéntalo en log pero **no lo cuentes como regression del Item 4**.
   - Re-run de chains de reacción + atomic + vip lifecycles + story + broadcast concurrent + units es obligatorio en F5 (y spot en F2/F3/F4 después de edits).
   - Siempre GSD pre- antes del pytest/ruff/grep grande.
   - Al final F6: re-ejecuta los combinados + broader smoke filtrado por los 3 sistemas + keywords de tests nuevos.

7. **Alcance (recuerda siempre):** Solo edita los archivos listados en "Archivos que se modificarán" + el log GSD + (este PLAN ya está) + opcional SUMMARY.md al final. Si sientes la tentación de "agregar más tests para cobertura" o "limpiar otros" o "tocar prod para hacer tests más fáciles", detente: scope tight para esta entrega (4-6 por sistema, extend existing, 0 prod, prepara Item 5 EventBus Reward). El analyzer recomendó empezar tight con estos 3 sistemas + gold patterns.

8. **Al final del Item (F6):**
   - Completa el self-check en el log (lista de fases, DoD cumplidos, archivos modificados, tests que pasaron, reglas verificadas (DESIRED, TG, file+TestSession, gather, patch, make_fsm, N806 doc, etc.), desviaciones (si las hubo), tests críticos a re-correr en futuro (lista explícita de los nuevos + golds), "Item 4 closed. Ready for gsd-executor of Item 5 (Reduce direct Besito composition in RewardService via EventBus) + arch-enforcer re-scan (tests de 3 sistemas) + test-guardian (correr los tests críticos listados)".
   - (Opcional pero recomendado) Produce `.planning/phases/22-critical-tests-three-systems/SUMMARY.md` con executive + refs al log GSD + comandos de re-verificación (sigue estructura de phases/20 o 19 o 21).
   - Confirma en log: "Self-Check: PASSED".
   - El siguiente agente (gsd-executor Item 5 o arch-enforcer/test-guardian) usará el log + este PLAN + los tests agregados como fuente de verdad.

9. **Si algo no está claro o difiere del "reporte del analyzer":** El prompt del usuario + este PLAN (basado en discovery + el reporte completo en .claude/.../item4-...md) es la fuente de verdad. Pregunta solo si un gate bloquea por ambigüedad real de nombre/firma/contrato o fixture; de lo contrario, elige conservadoramente siguiendo precedentes (atomicity gold, broadcast concurrent, vip _ensure_aware, story atomic, EventBus patch, make_fsm, get_service lifecycle de broadcast) y registra la elección en GSD.

**¡Ejecuta con disciplina total. Cierra el Item 4 de tests críticos de forma limpia, segura, medible y con trazabilidad GSD completa. Los 3 sistemas críticos (gamification, narrative, channel/VIP) quedarán mejor protegidos contra regressions en races, transiciones, edges y post-get_service/EventBus, listos para Item 5 y guardians.**

---

**Fin del PLAN para 22-critical-tests-three-systems (Item 4).**

Referencias rápidas para el executor (actualizar con líneas reales durante ejecución si cambian):
- Impact report (source of truth): `.claude/agent-memory/impact-analyzer/item4-tests-gamification-narrative-vip.md`
- Gold cross/race: `tests/integration/test_cross_service_atomicity.py` (líneas 71-86 _create, 153 DESIRED, 175+ tests, 194 patch event, 199+ setup tg 77708, try/finally).
- Concurrent gather: `tests/unit/test_broadcast_service_reaction_flow.py` (TestCheckAndRegisterReaction + concurrent pilots).
- Story atomic: `tests/unit/test_story_service.py` (TestStoryServiceAtomicity, advance commit=False, archetype).
- VIP gold: `tests/integration/test_vip_flows.py` (_ensure_aware, _create_user TG, redeem/expire/lifecycle).
- EventBus: `services/event_bus.py` (DESIRED CONTRACT 33-41, schedule_emit, gather return_exceptions, fresh in tests).
- FSM fixture: `tests/conftest.py` (make_fsm_context 671-683, MemoryStorage).
- get_service + lifecycle precedent: `tests/unit/test_broadcast_service_reaction_flow.py` + services/__init__.py get_service.
- Game limits: `services/game_service.py` (DAILY_DICE_LIMIT_FREE=10 etc, play_dice_game, play_trivia*).
- Precedentes PLAN: `.planning/phases/21-getservice-unification/PLAN.md`, `20-reward-gamif-rules-compliance/PLAN.md`, `19-eventbus-poc/PLAN.md`.
- GSD log para este Item: `.planning/quick/gsd-critical-tests.log`
- Reglas: `CLAUDE.md`, `rules.md`, `architecture.md`, `handlers/CLAUDE.md`, `services/CLAUDE.md`, `models/CLAUDE.md`, `decisions.md`.
- Next batch: Item 5 Reduce direct Besito composition in RewardService via EventBus (post este).

Listo para gsd-executor. Ejecuta F1 → ... → F6 con GSD pre en cada paso. Self-Check: PASSED al final.
