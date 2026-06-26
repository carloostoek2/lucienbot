# PLAN: Test gaps/hygiene clusters — explicit caps in gamif (limits in service + tests), FSM restart real Redis sim, deeper VIP/channel edges, full handler E2E "mensaje correcto" Lucien voice on insuff (Item 3/34 / third of new pool of 4)

**Type:** gsd-planner output (for gsd-executor + hardener seq: arch-enforcer + test-guardian + documentador at pool close)  
**Date:** 2026-06-26  
**Focus:** Ultra-tight, tests-only (or minimal hardening for explicit caps hygiene) per HARDENING_ROADMAP sec5 "Proposed Next #4" (listed as #3/4 in current pool context) + "33 mapeo remaining gaps" (test coverage media: caps, FSM restart, VIP/channel edges, handler E2E insuff Lucien) + initial analysis + pool33 close. "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."  

High-value hygiene for 3 crit (gamif caps/limits, narrative FSM/archetype/quiz restart, channel-VIP edges) + contracts (atomicity/EventBus/get_service). Use proven patterns from pool33 (gamif int + store int/E2E: real svc injection via class patch, TestSession/file + N806+doc+777+explicit models+try/finally+external patch ONLY+1-line/guard exact+DESIRED+UI 1:1) + story atomic/FSM golds (archetype immut + DESIRED+777+imm/FSM, invalid trans no partial, FSM EventBus, atomic debit commit=False, achievement) + cross + daily atomic (hasattr guards + fallback) + reaction golds + vip flows. GSD pre every; self-check PASSED + pool phrase verbatim at close; arch: PASS/PASS WITH NOTES 0 crit; test-guardian "suite protege adecuadamente"; 0/0/0 (0 prod/0 beh/0 atomicity); 0 attr reg; protects 3 crit + contracts via re-runs only. Hand-off after tests green + self-check → arch + testg + documentador + Item 4.

**Input principal (MANDATORY full read first):**  
- `.planning/HARDENING_ROADMAP.md` (sec5 gaps "More explicit max limits/global caps in gamif; full FSM restart with real Redis sim; more invalid narrative + EventBus desbloqueo tests; deeper channel/VIP (multi-tariff edges, free pending after VIP expire); full handler E2E for "mensaje correcto" (Lucien voice on insufficient)" + Proposed Next + pool33 entry + pool phrase + 3 crit + metrics).  
- Precedents: `tests/handlers/test_gamification_user_handlers_integration.py` (full: pytestmark=integration, real_svc=XXXService(db_session), `with patch("handlers.xxx.XXXService") as mock: mock.return_value = real_svc`, handler→real svc→DB→UI 1:1 exact Lucien strings/keywords/emojis, fixtures, make_*, sample_*); pool33 `tests/handlers/test_store_user_handlers_integration.py` + `tests/integration/test_store_purchase_integration.py` (class patch real, TestSession/file + N806 tol+doc+777 tg+explicit models+try/finally+re-query+external patch ONLY+1-line/guard exact comment + DESIRED CONTRACT + "credit survives" style + UI 1:1 pins + real DB asserts); `tests/unit/test_story_service.py` (TestStoryArchetypeImmutability + DESIRED+777+explicit balance, TestStoryInvalidTransitions no partial, TestStoryServiceAtomicity debit commit=False, TestStoryFSMEventBus, TestStoryAchievementAtomicity, TestStoryNarrativeGoldFase6); `tests/integration/test_cross_service_atomicity.py` (full gold + patch schedule_emit + DESIRED + strict + "credit survives deliver False" + "post-credit best effort (misiones + listeners)"); daily atomic + reaction_* (full_chain/limit/mission) + vip_* (complete_cycle/flows/ritual/subscription_lifecycle) + invariants; recent hardener PLANS (33/34-item1/34-reward/27/28/29 + gsd logs + SUMMARIES) for GSD pre format, self-check structure, pool phrase, handoff, "copy al pie", risks+mit, safe points.  
- Relevant sources (MANDATORY): `services/besito_service.py` (caps/limits, debit/credit, has_sufficient_balance, get_balance); `handlers/gamification_user_handlers.py` (insuff messages if any, balance flows); `handlers/store_user_handlers.py` + `services/store_service.py` (insuff "Saldo insuficiente" + LucienVoice.store_balance_insufficient_alert() "Moneda especial insuficiente."); `services/story_service.py` (FSM, quiz/archetype calc/assign/once-only, advance_to_node, restart/restore, invalid branches); `services/vip_service.py` + `services/channel_service.py` (multi-tariff, expire, pending after expire, ban, grant/revoke); `handlers/vip_handlers.py` + channel/free handlers (edges); `services/trivia_config_service.py` (explicit dice/trivia limits: dice_limit_free/vip, trivia_*_limit_free/vip); `services/daily_gift_service.py` (once-per-day claim logic + guards); `tests/unit/test_besito_service.py`, `tests/unit/test_daily_gift_service.py`, `tests/unit/test_story_service.py`, `tests/unit/test_vip_service.py`, `tests/unit/test_channel_service.py`, `tests/integration/test_reaction_limit.py` (documents NO daily reaction limit — gap hygiene), `tests/test_streak_fsm.py`, `tests/integration/test_vip_*.py`, bot.py (create_storage Memory/Redis); fixtures (db_session, make_callback/make_user, sample_* , TestSession if needed).  
- 33 mapeo remaining gaps clusters (via ROADMAP sec5 + pool33 close note): test gaps/hygiene after store+promo reality (tienda/promo done); focus caps, FSM, VIP/channel edges, handler E2E insuff.

**Precedents obligatorios (copiar AL PIE DE LA LETRA):**  
- Gamif int style + pool33 store int: pytestmark=[pytest.mark.integration]; real_svc = XXXService(db_session); `with patch("handlers.xxx.XXXService") as MockX: MockX.return_value = real_svc`; call handler; assert UI text 1:1 (Lucien strings/keywords preserved); sample fixtures with telegram_id contract; 1-line/guard for balance if inspect: `bal = (BesitoService(db=db_session).get_balance(tg) if not hasattr(svc, "besito_service") else svc.besito_service.get_balance(tg))` with comment "# 1-line/guard port post Item10 local (copy daily precedent in cross; arch-enforcer); was service.besito_service".  
- Store E2E + atomic gold: TestSession/file (N806 tolerated + docstring), fresh TG 7770xxxx, explicit models (User/BesitoBalance/...), try/finally reopen/re-query, external patch ONLY (e.g. PackageService.deliver), "credit survives deliver False" / post best-effort, strict asserts, DESIRED CONTRACT docstring.  
- Story golds: archetype immut (once-only), invalid graceful no partial, FSM restore sim, EventBus listener, atomic debit commit=False.  
- Daily atomic: hasattr guards + fallback for lazy besito.  
- GSD pre-log: `=== $(date -Iseconds) | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie de la letra>` appended to `.planning/quick/gsd-34-test-gaps-hygiene.log` BEFORE every edit/gate/ruff/pytest/grep/smoke/self-check; wc -l tracked.  
- self-check PASSED full structure at final phase (phases/DoD/gates/archivos/tests passed/reglas verificadas (GSD pre every, scope tight, 3 crit protected via re-runs, copy precedents, UI 1:1, integration style, 1-line/guard if any, 0/0/0)/desviaciones/tests críticos/"Item 3/34 closed. Third of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. ... Ready for arch-enforcer re-scan (enfocado en test gaps/hygiene: caps + insuff E2E Lucien + FSM/VIP edges) + test-guardian (correr golds listados) + documentador (update ROADMAP + learnings + agent-memory) + gsd-executor del Item 4 del pool").  
- Arch: PASS or PASS WITH NOTES (0 critical). Test-guardian: "suite protege adecuadamente" + re-runs golds exactos. Pool phrase verbatim at every close + self-check + handoff. "0 attributable regressions".

**GSD enforcement (non-negotiable):**  
Executor MUST prefix **every** modification, gate, verification, ruff, pytest, grep, smoke, self-check, or summary step with GSD log append (timestamp | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie de la letra from gamif int + store E2E + story golds + 1-line/guard + daily guards + impact/ROADMAP>) to `.planning/quick/gsd-34-test-gaps-hygiene.log`. Use python -c for long/quoted safety. wc -l after. Planner pre-entries done (INIT + pre-mkdir + pre-write). No edits (even to PLAN or log beyond appends) without pre-log. "Planner did INIT + pre-mkdir + pre-write."

---

## 1. Alcance preciso (In / Out explícito; ultra tight per ROADMAP sec5 + 33 mapeo clusters + 0/0/0)

### En esta entrega (Item 3/34 third of new pool of 4; tests-only or minimal hardening for explicit caps; 0 prod/0 behavior/0 atomicity; 3 crit + contracts protected; source = ROADMAP sec5 + precedents):
- **Explicit caps in gamif (limits in service + tests):**  
  Add/extend tests that exercise and make explicit the configured limits (trivia_config_service dice/trivia daily limits free/VIP; daily gift once-per-day claim; any per-broadcast reaction limits or document absence per existing test_reaction_limit.py; game minijuego caps if wired). Use real services (TriviaConfigService or equivalent, DailyGiftService, BroadcastService, GameService) + db fixtures. Prefer integration or targeted unit with real svc. If hygiene requires, small pure helper in besito_service or trivia_config (verb+context+result, stateless, "Función pura...") e.g. `compute_effective_daily_limit(user_is_vip, config)` — only if needed to slim or centralize for testability; 0 beh change. Pin limits in asserts (e.g. config["dice_limit_free"] == 10). Re-use daily atomic guards pattern if lazy. 1-line/guard if balance involved. UI 1:1 if handler paths touched. Re-runs protect gamif golds.

- **Full handler E2E "mensaje correcto" Lucien voice on insuff (gamif/store):**  
  Extend `tests/handlers/test_store_user_handlers_integration.py` (or targeted) with cases asserting exact Lucien message on insuff: e.g. after effective price > balance, `cb.answer.assert_called()` or edit_text contains `LucienVoice.store_balance_insufficient_alert()` ("Moneda especial insuficiente.") or equivalent in flow (direct_buy/confirm). Use real StoreService + class patch + real balance/product seeds (telegram_id contract).  
  For gamif domain: locate debit/insuff paths surfaced via gamif or game handlers (e.g. game protection "Besitos insuficientes para la proteccion." or story paid node advance insuff if handler shows; broadcast reaction if any). Add 1-2 integration tests (real svc class patch) asserting the exact answer/edit_text message the user sees (Lucien or current string pinned 1:1). If current code uses raw string instead of LucienVoice, test pins current (hygiene note; 0 change). Copy pool33 insuff branch style + UI 1:1. 1-line/guard if post-insuff balance inspect. Re-runs store/gamif related.

- **FSM restart real Redis sim + deeper VIP/channel edges:**  
  FSM restart: add/extend tests (e.g. in `tests/test_streak_fsm.py` or new targeted for story quiz FSM) simulating restart (fresh MemoryStorage or re-instantiate storage/FSM context per bot.py create_storage logic; or note "real Redis sim via env if REDIS_URL, fallback Memory as in bot.py"). Verify narrative/archetype state (once-only quiz, progress not lost, invalid after restart graceful), streak session state survives or resets correctly per existing logic. Use real services + explicit 777 tg. Copy story FSM gold + DESIRED patterns.  
  Deeper VIP/channel edges (integration style): add cases exercising multi-tariff subs, VIP expire + free pending request behavior, ban propagation to both channels, pay→VIP then remove free access, offline/expire-no-error-if-gone (if not covered). Use real VIPService/ChannelService (or handler int if entrypoint), TestSession/file if atomic visible (grant/revoke), external patch only for TG calls. Assert DB state + no crash. Re-runs vip flows + channel related.  
  0 prod change. 1-line/guard + external only + UI 1:1 if applicable.

**Archivos que se modificarán / crearán (exactos; 0 other):**
- `.planning/quick/gsd-34-test-gaps-hygiene.log` (GSD pre + wc + self-check + pool phrase every phase).  
- `tests/handlers/test_store_user_handlers_integration.py` (extend; insuff E2E Lucien pins for store).  
- `tests/handlers/test_gamification_user_handlers_integration.py` or `tests/handlers/test_game_user_handlers_integration.py` (if exists; add/ extend for gamif domain insuff messages if surfaced; else minimal new tight integration for game protection insuff).  
- `tests/unit/test_besito_service.py` or `tests/unit/test_trivia_config_service.py` or `tests/integration/` (add explicit caps/limits tests; prefer minimal touch to existing gold files; new targeted if needed e.g. TestGamifCaps or extend daily/reaction).  
- `tests/test_streak_fsm.py` or `tests/integration/test_story_fsm_restart.py` (tight; FSM restart sim).  
- `tests/integration/test_vip_flows.py` or `tests/integration/test_channel_*.py` or new tight `tests/integration/test_vip_channel_edges.py` (deeper edges; reuse/extend).  
- `.planning/phases/34-test-gaps-hygiene/` (this PLAN.md + opt *-SUMMARY.md post + arch/testg reports).  
- (Docs minimal via documentador at pool close only: ROADMAP append, agent-memory report, MEMORY pointer; no manual mid-item).

**Fuera explícitamente (no scope creep):**  
- **NO** prod code (0 writes to handlers/*.py, services/*.py, bot.py, models; grep confirm post).  
- **NO** change to golds of 3 crit (cross_service_atomicity, reaction_*, daily atomic, story atomic/imm/FSM/achievement, vip_*, invariants, mission_e2e, free_entry, store atomic gold; only re-run).  
- **NO** new models/alembic.  
- **NO** broad "add all missing caps impl" (only test existing + hygiene if pure for testability; 0 beh).  
- **NO** other flows (store purchase beyond insuff, promo, mission user beyond edges if any, admin, etc.).  
- **NO** edit CLAUDEs/decisions/ROADMAP except via documentador at close.  
- **NO** touch callbackdata tests.  
- **NO** mutation of contracts (1 svc via get_service in prod remains; tests class-patch to inject real; EventBus "MUST NOT mutate"; atomic golds untouched).  
- 0 new deps (no fakeredis; use MemoryStorage sim or conditional Redis if present in env).

**Comportamiento observable (tests only):** Existing prod flows identical. New/ported tests exercise real paths for caps (assert configured limits enforced/returned), insuff messages (exact Lucien or pinned strings), FSM restart (state survives/graceful), VIP/channel edges (multi/expire/ban/pending). Golds protected 0 attributable reg. 0 user-visible change. 3 crit + atomicity/EventBus/get_service 0 impact.

---

## 2. Fases (strict order; 4-6 small per cluster; safe points; DoD per phase; GSD pre every)

**Pool/Item context:** Item 3/34 (third of new pool of 4 after Item 1/34 user-flows + Item 2/34 reward-admin closed clean). Pool phrase verbatim in all artifacts + self-checks + handoffs. Focus: caps (gamif), E2E insuff Lucien (gamif/store), FSM restart sim + VIP/channel edges. After gates + self-check: handoff to arch-enforcer (focus: test gaps/hygiene + real svc + 1-line/guard + UI 1:1 + 0 impact 3 crit) + test-guardian (re-run golds list) + documentador (ROADMAP + learnings) + gsd-executor Item 4.

### F1 prep/GSD/baseline (GSD pre)
- GSD pre-log.  
- Read MANDATORY: this PLAN full + ROADMAP (sec5 + pool33 + phrase) + gamif_integration.py full + store int + store E2E full + 33-PLAN + 34-item1-PLAN + 34-reward-PLAN + 27/28/29 + gsd/SUMMARIES (GSD style, self-check, copy al pie, handoff, pool) + current unit/integration tests for caps (trivia_config, daily, reaction_limit, besito), insuff (store/gamif/game), FSM (streak_fsm, story unit FSM), VIP/channel edges (vip flows, channel) + story golds (atomic/imm/FSM) + handlers sources for insuff messages (store_user, gamif_user, game_user) + services (besito, store, story, vip, channel, daily, trivia_config) + fixtures + bot.py storage.  
- Baseline ruff on target test files.  
- Baseline targeted pytest exact flags (`-q --tb=line -p no:cov --override-ini="addopts="`): gamif unit + integration spot, story unit full (archetype/imm/invalid/atomic/FSM/achievement), cross atomicity spot, reaction_full_chain + limit + mission, daily atomic, vip flows (3+), invariants I8, broader `-k "gamif or story or vip or channel or atomic or daily or reaction or mission or store or cap or limit or fsm or insuff or trivia or streak"`.  
- Greps: current caps/limits usage (trivia_config, daily claim, besito), insuff strings ("Saldo insuficiente", "Moneda especial insuficiente", "Besitos insuficientes"), FSM/storage (MemoryStorage/Redis), VIP/channel edge coverage (multi, expire, pending, ban).  
- Confirm fixtures (balances telegram_id=777, products, nodes, missions, rewards, tariffs, channels, configs with limits). Confirm golds list + re-run cmds.  
- "F1 safe point". DoD marked. 0 edits to prod.

### F2 explicit caps in gamif (limits in service + tests) (GSD pre every edit)
- GSD pre.  
- Add/extend tests (target: `tests/unit/test_trivia_config_service.py` or `tests/unit/test_besito_service.py` or new tight integration if handler flow; minimal): real service (TriviaConfigService/DailyGiftService/BroadcastService) + db; assert explicit limits returned/enforced (e.g. dice_limit_free=10, trivia_limit_vip=10, daily claim once via date or UNIQUE, reaction get_user_reactions limit=20 or absence per existing test_reaction_limit); use real config seeds. If small pure needed for hygiene (e.g. compute limit), extract verb+context+result "Función pura..." + Test*PureHelpers import-inside (copy 27/26/25 pattern); otherwise pure tests not required. 1-line/guard if balance. ruff. Targeted pytest on touched + spot gamif/daily. Grep caps exercised + no prod touch. "F2 safe point". DoD marked.

### F3 full handler E2E "mensaje correcto" Lucien on insuff gamif/store (GSD pre)
- GSD pre.  
- Extend `tests/handlers/test_store_user_handlers_integration.py` (TestDirectBuy/Confirm insuff paths): real StoreService + class patch; seed balance < effective price; call direct_buy/confirm; assert cb.answer text or edit contains exact "Moneda especial insuficiente." (or current LucienVoice.store_balance_insufficient_alert()); UI 1:1 per pool33; 1-line/guard if balance post.  
- For gamif: add/extend integration (e.g. test_game_user_handlers_integration.py or gamif int) for paths that surface insuff (game protection "Besitos insuficientes para la proteccion." or equivalent); real svc (GameService or Besito via handler), class patch, assert exact answer/edit 1:1. If no direct gamif handler insuff, add minimal E2E in store context or note. Copy pool33 insuff branch + UI 1:1. ruff; pytest new + spot store/gamif; grep no prod. "F3 safe point". DoD marked.

### F4 FSM restart real Redis sim + deeper VIP/channel edges (GSD pre)
- GSD pre.  
- FSM restart: extend `tests/test_streak_fsm.py` or add tight `tests/integration/test_fsm_restart_sim.py` (or story-focused): use MemoryStorage (per bot.py fallback) or conditional RedisStorage if REDIS_URL; simulate restart (new storage instance or clear key scope); verify story quiz/archetype once-only, progress state, streak session state, invalid after restart graceful. Real services + 777 tg + explicit seeds. Copy story FSM gold + DESIRED. External only if any. ruff; pytest + re-run story unit. "F4a safe point".  
- VIP/channel edges: extend `tests/integration/test_vip_flows.py` or `tests/integration/test_vip_subscription_lifecycle.py` or new tight edges file: real VIPService/ChannelService; cases for multi-tariff (two active?), expire + pending free entry behavior, ban-both-channels, pay→VIP+remove-free, expire-no-error-if-gone. TestSession/file if atomic (N806+doc+777+try/finally+external patch for TG if needed). Assert DB + no crash. Re-run vip golds. "F4b safe point". DoD marked.

### F5 gates + re-runs + rules verif (GSD pre every)
- GSD pre every.  
- ruff on touched (new/extended tests; pre N806 tol in TestSession files per gold).  
- Re-execute exact golds list (see section 3).  
- Bot smoke (import handlers/services; storage create).  
- Grep 0 prod changes (handlers/services untouched); 0 new models; 1-line/guard comments exact if present; integration style (class patch real svc); UI 1:1 strings; caps tests assert explicit limits; FSM sim uses Memory/Redis per bot; Lucien or pinned insuff messages asserted.  
- Rules verif: GSD pre every + wc, scope tight per listed files + log + PLAN, 3 crit protected via re-runs (no writes in crit paths), precedents al pie (gamif int + store E2E + story golds + 1-line/guard + daily guards + UI 1:1), 0/0/0, get_service 1 call unchanged in prod, N806 tol documented in TestSession. "F5 safe point". DoD marked.

### F6 self-check PASSED + handoff (GSD pre)
- GSD pre.  
- Append full self-check structure to log + opt SUMMARY.md (mirror 33/28/27): phases/DoD/gates/archivos/tests passed; reglas verificadas (GSD pre every + wc, scope tight per PLAN/ROADMAP, 3 crit protected via re-runs/greps, precedents copiados al pie, UI 1:1, integration real svc + class patch + 1-line/guard, caps explicit in tests, insuff E2E Lucien pinned, FSM sim + VIP/channel edges added, 0 prod touch, 0 attr reg); desviaciones (pre-exist only non-reg: e.g. N806 tol in golds, daily concurrent flake, no daily reaction limit as documented); tests críticos para futuro (list); "Item 3/34 closed. Third of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch-enforcer re-scan (enfocado en test gaps/hygiene: explicit caps gamif + full handler E2E Lucien insuff + FSM restart sim + deeper VIP/channel edges; 0 impact 3 crit) + test-guardian (correr golds listados exact) + documentador (update ROADMAP + extract learnings + agent-memory/documentador/ + MEMORY.md pointer) + gsd-executor del Item 4 del pool de 4".  
- Self-check PASSED. Pool phrase verbatim. Launch arch + testg + documentador per hardener if orchestrated. Explicit next: Item 4.

---

## 3. Golds to re-run (exact; after each relevant phase + final; 0 attributable regressions target)

Use exact flags from precedents: `-q --tb=line -p no:cov --override-ini="addopts="`

- Gamif unit + integration: `pytest tests/unit/test_besito_service.py tests/unit/test_daily_gift_service.py tests/handlers/test_gamification_user_handlers_integration.py -q --tb=line -p no:cov --override-ini="addopts="`
- Cross + atomic: `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="` (full; patch schedule_emit if in scope)
- Reaction golds: `pytest tests/integration/test_reaction_full_chain.py tests/integration/test_reaction_mission_flow.py tests/integration/test_reaction_limit.py -q --tb=line -p no:cov --override-ini="addopts="`
- Daily atomic: `pytest tests/integration/test_streak_protection_flow.py -k "daily" -q --tb=line -p no:cov --override-ini="addopts="` (or specific daily atomic if separate)
- Story golds (unit + FSM): `pytest tests/unit/test_story_service.py -q --tb=line -p no:cov --override-ini="addopts="` (archetype/imm/invalid/atomic/FSM/achievement)
- VIP + channel: `pytest tests/integration/test_vip_complete_cycle.py tests/integration/test_vip_flow.py tests/integration/test_vip_flows.py tests/integration/test_vip_ritual_flow.py tests/integration/test_vip_subscription_lifecycle.py tests/unit/test_vip_service.py tests/unit/test_channel_service.py -q --tb=line -p no:cov --override-ini="addopts="`
- Invariants + mission e2e (side-effect protect): `pytest tests/integration/test_invariants.py tests/integration/test_mission_e2e.py -q --tb=line -p no:cov --override-ini="addopts="`
- Broader smoke: `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "gamif or story or vip or channel or atomic or daily or reaction or mission or store or cap or limit or fsm or insuff or trivia or streak or purchase or balance" --maxfail=5`
- Spot after ports: atomic gold if touched (store), cross, story FSM, vip flows.
- Bot smoke + listener reg if any new (unlikely): `python -c "import bot; print('bot import OK')"`

Re-runs mandatory at F5 + final; spot after F2/F3/F4. Pre-exist (daily concurrent flake, N806 in golds, some VIP xfail) doc non-reg only. 0 attributable.

---

## 4. Riesgos + mitigación (0 impact; orthogonal)

- Risk: Accidental prod touch → Mit: GSD pre every + grep 0 writes in F5 + git diff/collect confirm; scope lists exact test files only.  
- Risk: Gold mutation (e.g. edit atomic class) → Mit: "100% untouched" + re-run verbatim + 1-line/guard only with exact comment; TestSession new files ok.  
- Risk: N806 in new TestSession files → Mit: tol + docstring per gold precedent; ruff allows in those.  
- Risk: FSM sim not "real Redis" → Mit: use MemoryStorage as bot.py fallback (explicit in test); if REDIS_URL present in env use it; document "sim". No new deps.  
- Risk: Insuff message not Lucien in current code → Mit: test pins exact current (hygiene); 0 change to prod strings.  
- Risk: Pre-exist flakes (daily concurrent, some VIP) → Mit: doc non-reg; do not xfail new; re-runs only.  
- Risk: Scope creep to impl caps → Mit: "tests-only or minimal hardening for explicit (pure if needed)"; 0 beh; In/Out strict.  
- Overall: orthogonal tests (no writes to crit paths); re-runs protect atomicity/EventBus/get_service/3 crit (gamif credits/reactions/daily/missions untouched; narrative progress/archetypes/FSM/quiz; channel pending/approve/expire/bans/subs + VIP grant/revoke). "0 attributable regressions".

---

## 5. Success criteria (medibles)

- GSD pre + wc: >=1 per phase + total log lines tracked; every edit/gate has entry.  
- Tests added/extended: caps (explicit limits asserted for trivia/daily/reaction), insuff E2E (store + gamif domain, exact messages 1:1), FSM restart (sim + state), VIP/channel edges (multi/expire/pending/ban >=2-3 cases).  
- Golds re-runs: all listed green (pre-exist only non-attrib); 0 attributable regressions.  
- Arch: PASS or PASS WITH NOTES (0 critical).  
- Test-guardian: "suite protege adecuadamente".  
- Self-check: PASSED full + pool phrase + "Item 3/34 closed. Third..." + handoff.  
- 0/0/0: 0 prod/0 beh/0 atomicity (git/grep confirm); UI 1:1; integration style + real svc + class patch + 1-line/guard (if any) + TestSession (if any) + UI 1:1 + external only.  
- 3 crit + contracts: protected (re-runs + 0 writes in gamif credit/reaction/daily/mission, narrative FSM/archetype/progress, channel-VIP pending/approve/expire/ban/subs + VIP grant).  
- Ruff clean on touched (N806 tol only in TestSession per precedent).  
- Review: 0 open issues post (if loop).  
- Traceability: PLAN + gsd log + self-check + arch/testg reports + documentador update + ROADMAP append + pool phrase verbatim.

---

**Handoff (after F6 self-check PASSED):**  
"Item 3/34 closed. Third of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch-enforcer re-scan (enfocado en test gaps/hygiene: explicit caps in gamif + full handler E2E mensaje correcto Lucien on insuff + FSM restart real Redis sim + deeper VIP/channel edges; 0/0/0; 3 crit + contracts protected) + test-guardian (correr golds listados) + documentador (update ROADMAP + learnings + .claude/agent-memory/documentador/ + MEMORY.md) + gsd-executor Item 4 del pool."

**Self-check template for executor (fill at F6; append to log + SUMMARY if created):**

```
=== SELF-CHECK PASSED (Item 3/34) ===
Phases: F1 prep (read + baseline + greps + F1 safe) ... F6 (self-check + handoff) — all DoD marked, safe points passed.
Gates: ruff (touched), pytest (new + golds re-runs), grep (0 prod, integration style, 1-line comments, UI 1:1), bot smoke, LOC if puros.
Archivos: .planning/quick/gsd-34-test-gaps-hygiene.log (wc=XXX), listed test files (new/extended), PLAN.md, (opt SUMMARY).
Tests passed: <list counts per file + golds green>.
Reglas verificadas:
- GSD pre every + wc tracked
- Scope tight (tests-only/min hardening per In/Out + listed files only)
- 3 crit protected (re-runs + 0 writes in crit paths)
- Precedents copiados al pie (gamif int + store E2E/TestSession + 1-line/guard exact + story golds + daily guards + UI 1:1)
- Integration style (class patch real svc, real DB, UI 1:1 Lucien)
- 0/0/0 (0 prod/0 beh/0 atomicity; git/grep)
- get_service 1 call unchanged in prod
- N806 tol only in TestSession files + doc
- Pool phrase verbatim
- 0 attr reg
Desviaciones: (pre-exist only: N806 in golds, daily flake, no daily reaction limit as documented in reaction_limit.py — non-reg)
Tests críticos para futuro: caps explicit, insuff E2E, FSM restart, VIP/channel edges (list files)
"Item 3/34 closed. Third of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch-enforcer re-scan (enfocado en test gaps/hygiene...) + test-guardian + documentador + Item 4."
Self-check: PASSED
```

**Fin del PLAN para Item 3/34. Ejecutable, tight, listo para gsd-executor.**
