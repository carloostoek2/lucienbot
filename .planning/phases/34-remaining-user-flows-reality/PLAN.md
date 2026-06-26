# PLAN: Remaining user flows test reality hardening — story_user (narrativa CRÍTICO #2 primary), backpack fulfillment, mission_user claim/list/detail; new handler integration tests (real svc + db) + E2E where atomic visible (TestSession); 1-line/guard ports; 0/0/0 (tests-only, 0 prod/0 beh/0 atomicity); protect 3 crit (gamif/narrativa/canales-VIP) + atomicity/EventBus/get_service contracts; follow gamif int precedent + pool33 store int/E2E + atomic golds + 1-line/guard al pie; GSD pre every; self-check PASSED + pool phrase verbatim; arch: PASS/PASS WITH NOTES 0 crit; test-guardian "suite protege adecuadamente"; (Item 1/34 first of new pool of 4 after pool 33 closed; source: .grok/agent-memory/impact-analyzer/pool34-item1-user-flows-reality.md)

**Type:** gsd-planner output (for gsd-executor + hardener seq: arch-enforcer + test-guardian + documentador at pool close)  
**Date:** 2026-06-26  
**Focus:** Ultra-tight, tests-only hardening per impact-analyzer map (source of truth) + HARDENING_ROADMAP sec5 "Proposed Next #1" + pool33 close ("Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."). High reality value for narrativa (CRÍTICO #2: quiz/archetype calc+assign+once-only, advance_to_node atomic besitos+progress, invalid branches, FSM, achievements) + post-purchase (backpack fulfillment/retry/VIP resend/read chapter) + mission claim (deliver paths). Apply proven patterns from pool33 (store purchase int + E2E) + gamif int + atomic golds (TestSession/file, N806+doc, 777, explicit models, try/finally, external patch ONLY, 1-line/guard, DESIRED, "credit survives" style for story advance, UI 1:1) + 1-line/guard for Besito (Item10 precedent) + GSD pre + self-check + pool phrase + handoff. 0 prod change (no handlers/*.py, services/*.py touched). Re-run golds only (no mutation). 4-6 small phases per item. "Item 1/34 closed. First of new pool of 4."

**Input principal (MANDATORY full read first):**  
- `.grok/agent-memory/impact-analyzer/pool34-item1-user-flows-reality.md` (full; exec summary, ALTO risk for narrativa, tables for story/backpack/mission_user with mock counts 186/58/95, consumers, indirect chains, missing tests list, precautions 1-11 (TestSession, 1-line/guard, external patch only, archetype immut, invalid no partial, get_service class patch, UI 1:1, no touch golds), golds list exact, re-run cmds, tight scope recs: story primary (quiz/archetype/advance/choice/invalid/achievements/FSM), backpack (fulfillment_retry, resend_vip, read_chapter), mission (show_my/ detail/claim); "Pool anterior de 4 cerrado..."; "Ready for gsd-planner").  
- `.planning/HARDENING_ROADMAP.md` (pool33 entry + sec5 Proposed Next #1 + pool phrase + metrics + 3 crit always).  
- Precedents: `tests/handlers/test_gamification_user_handlers_integration.py` (full structure, pytestmark=integration, real_svc=XXXService(db_session), `with patch("handlers.xxx.XXXService") as mock: mock.return_value = real_svc`, full flow handler→real svc→DB→UI 1:1, fixtures, make_*, Lucien strings); pool33 `tests/handlers/test_store_user_handlers_integration.py` + `tests/integration/test_store_purchase_integration.py` (class patch real, TestSession/file + N806+doc+777+explicit models+try/finally+re-query+external patch only+1-line/guard exact comment + DESIRED, UI 1:1 pins); recent hardener PLANS (27/28/29/33) + their gsd logs + SUMMARIES for GSD pre format, self-check structure, pool phrase, handoff language, "copy al pie", risks+mit, safe points; story unit golds `tests/unit/test_story_service.py` (TestStoryArchetypeImmutability + DESIRED + 777 + explicit balance, TestStoryInvalidTransitions no partial, TestStoryServiceAtomicity debit commit=False, TestStoryFSMEventBus, TestStoryAchievementAtomicity, TestStoryNarrativeGoldFase6); 1-line/guard examples (cross atomicity 726/762, store unit ~210, daily guards).

**GSD enforcement (non-negotiable):**  
Executor MUST prefix **every** modification, gate, verification, ruff, pytest, grep, smoke, self-check, or summary step with GSD log append (timestamp | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie de la letra>) to `.planning/quick/gsd-34-item1-user-flows-reality.log` BEFORE action. Use python -c for long/quoted. wc -l after. Planner pre-entries done (INIT + pre-write). No edits without pre-log. "Planner did INIT + pre-mkdir + pre-write."

---

## 1. Alcance preciso (In / Out explícito; ultra tight per impact map + 0/0/0)

### En esta entrega (Item 1 of new pool of 4; tests-only; 0 prod/0 behavior/0 atomicity; 3 crit + contracts protected; source = impact map + ROADMAP):
- **Primary: story_user (narrativa CRÍTICO #2 — MÁXIMA PRIORIDAD)**  
  New file: `tests/handlers/test_story_user_handlers_integration.py`  
  - pytestmark=[pytest.mark.integration]  
  - Real flows via real StoryService(db_session) + class patch `with patch("handlers.story_user_handlers.StoryService") as MockS: MockS.return_value = real_svc`  
  - Cover: narrative_menu (not started/started + archetype/no), start_story/continue (real progress), go_to_node/make_choice (success + end + invalid graceful), archetype quiz start/process/complete (real calc+assign+once-only+clear FSM+UI), view_my_archetype, my_story_achievements (if seed grants), show_node (VIP deny, decision, ending).  
  - For paid advance (cost_besitos>0) or achievement credits: use TestSession/file or 1-line/guard + explicit seeds (nodes w/wo cost, choices, balance 777 tg, progress rows, achievements). Copy story atomic gold setups (DESIRED, 777, explicit balance, strict post-state).  
  - UI 1:1 exact (copy strings from current unit tests + handler: "Fragmentos de la Historia", "Bienvenido de vuelta", "Capitulo X", "descubrira que arquetipo", archetype names, "Sin recompensa", progress bars, choice texts, quiz questions, ending buttons).  
  - Re-runs: full story unit golds (archetype immut, invalid, atomicity, FSM, achievement atomic, narrative gold) + cross + reaction_mission + vip + broader.  
  - 0 prod change.

- **Secondary (tight):**  
  - `tests/handlers/test_backpack_handler_integration.py` (tight): fulfillment_retry (real), resend_vip_invite (real or external patch VIP), read_chapter (real node link + delegate to show_node), lists from real data (orders/rewards/vip). Use gamif/store int pattern.  
  - `tests/handlers/test_mission_user_handlers_integration.py` (tight): show_my_missions (real progress bars), mission_detail (progress + catchup), claim_mission_reward (real deliver_pending → reward visible; 1-line/guard if balance).  
  - Or minimal combine if scope forces; prioritize 1-2 key per to keep item small. Re-use fixtures (sample missions, rewards besitos/pkg/vip, orders, fulfillments).

- **Ports / E2E if visible atomic:**  
  - 1-line/guard ports (exact copy) in any new integration that inspects balance post-advance/claim/summary:  
    `bal = (BesitoService(db=db_session).get_balance(tg) if not hasattr(svc, "besito_service") else svc.besito_service.get_balance(tg))`  
    with comment "# 1-line/guard port post Item10 local (copy daily precedent in cross; arch-enforcer); was ...".  
  - If E2E atomic for story advance (besitos+progress same tx) or mission claim side: extend or add integration using TestSession/file pattern copy store E2E + story atomic gold verbatim (N806+doc, 777, explicit models User/BesitoBalance/UserStoryProgress/StoryNode/StoryChoice/BesitoTransaction, try/finally reopen/re-query, external patch ONLY if any delivery, re-query).  
  - No new golds; only additive integration + ports.

- **Files exact (by priority):**  
  - `.planning/quick/gsd-34-item1-user-flows-reality.log` (GSD pre + wc + self-check + pool phrase every phase).  
  - `tests/handlers/test_story_user_handlers_integration.py` (new; primary).  
  - `tests/handlers/test_backpack_handler_integration.py` (new; tight).  
  - `tests/handlers/test_mission_user_handlers_integration.py` (new; tight).  
  - (If E2E needed) `tests/integration/test_story_advance_integration.py` or reuse/extend existing (minimal; prefer in handler int or one new).  
  - `.planning/phases/34-remaining-user-flows-reality/` (this PLAN.md + opt *-SUMMARY.md post + arch/testg reports).  
  - (Docs minimal via documentador at pool close only: ROADMAP append, agent-memory report, MEMORY pointer; no manual mid-item).

- **Fuera explícito (no creep):**  
  - NO prod code (0 writes to handlers/story_user_handlers.py, backpack_handler.py, mission_user_handlers.py, story_service.py, backpack_service.py, mission_service.py, etc.; grep confirm).  
  - NO change to golds of 3 crit (story atomic/imm/FSM/achievement, cross_service_atomicity, reaction_*, daily atomic, vip_*, invariants, mission_e2e, free_entry; only re-run).  
  - NO other flows/handlers (gamif, store, promo, admin, etc.).  
  - NO new models/mig/listeners/reg/get_service changes/EventBus.  
  - NO broad mock reduction; only the listed flows per impact.  
  - NO edit CLAUDEs/decisions/ROADMAP except via documentador at close.  
  - NO touch callbackdata tests (packing only).  
  - 0 mutation of contracts (1 svc via get_service in prod remains; tests class-patch to inject real).

- **Observable (tests only):** Prod flows identical. New tests exercise real svc paths (handler → real Story/Mission/BackpackService → DB (progress/archetype/achievements/claims/orders) → UI reflects real state). Golds protected 0 attributable reg. 0 user-visible change. 3 crit + atomicity/EventBus/get_service 0 impact.

---

## 2. Fases (strict order; 4-6 small; safe points; DoD per phase; GSD pre every)

**Pool/Item context:** Item 1/34 (first of new pool of 4). Pool phrase verbatim in all artifacts + self-checks + handoffs. Focus story primary (crit#2) then backpack + mission. After Item1 gates + self-check: handoff to arch-enforcer (focus: story/backpack/mission handler int + real svc + 1-line ports + 0 impact 3 crit) + test-guardian (re-run golds) + documentador (ROADMAP + learnings) + gsd-executor Item 2 of pool.

### F1 prep/GSD/baseline (GSD pre)
- GSD pre-log.  
- Read MANDATORY: this PLAN full + impact map full + ROADMAP (pool33 + sec5) + gamif_integration.py full + store int + store E2E full + 33-PLAN full + 29/28/27/26/25 PLANs + their gsd/SUMMARIES (GSD style, self-check, copy al pie, handoff, pool) + current unit tests for story/backpack/mission_user (mock patterns, _mock_backpack_ctx, get_service patches) + story unit golds (atomic/imm/FSM/invalid/achievement setups + DESIRED) + handlers source (entrypoints + get_service calls + UI strings) + fixtures (db_session, make_callback/make_user, sample_* for story nodes/choices, missions, rewards, orders, tiers/privs if needed).  
- Baseline ruff on target test files + store/gamif int (for style).  
- Baseline targeted pytest exact flags (`-q --tb=line -p no:cov --override-ini="addopts="`): story unit full, cross atomicity spot, reaction_mission_flow, mission_e2e, daily atomic, vip flows, invariants I8, broader `-k "story or narrative or archetype or mission or backpack or fulfillment or reward or atomicity or reaction or daily or vip"`.  
- Greps: current mocks in story/backpack/mission tests (expect 186/58/95 patterns), get_service patches, _mock_* helpers, direct_buy/confirm style from pool33.  
- Confirm fixtures (story nodes w/wo cost, archetype seeds, mission progress, orders/fulfillments, BesitoBalance telegram_id match).  
- Confirm golds list + re-run cmds from impact.  
- "F1 safe point". DoD marked. 0 edits to prod.

### F2 create story integration skeleton + port narrative_menu + start/continue paths (GSD pre every edit)
- GSD pre.  
- Create `tests/handlers/test_story_user_handlers_integration.py` with module docstring mirroring gamif + store int ("Tests de integración para story_user_handlers. Usa SQLite + StoryService real + bot mockeado. Flujo completo: handler → svc real → DB (UserStoryProgress/archetype/achievements) → UI.").  
- Import: from unittest.mock import patch; pytest; models (UserStoryProgress, StoryNode, StoryChoice, StoryAchievement, User, BesitoBalance, etc.); StoryService; pytestmark=[pytest.mark.integration].  
- Add class TestNarrativeMenuIntegration + TestStartContinueStoryIntegration.  
- Tests: use real_svc = StoryService(db_session); with patch("handlers.story_user_handlers.StoryService") as MockS: MockS.return_value = real_svc; seed real nodes/progress/archetype/balance; call narrative_menu/start_story/continue_story (with fsm if needed); assert UI 1:1 ("Fragmentos...", "Bienvenido de vuelta", "Capitulo X", archetype name, start button, etc.); cb.answer/edit called.  
- For started paths: real has_started_story + get_user_progress visible.  
- Add 1-line/guard if balance inspect (post-advance later).  
- ruff; targeted pytest new file + story unit spot; grep for patch("handlers.story_user_handlers.StoryService") + real usage.  
- "F2 safe point". DoD marked. UI 1:1 verified.

### F3 port quiz + archetype assign + once-only + FSM + view paths (story) (GSD pre)
- GSD pre.  
- Extend integration: TestArchetypeQuizIntegration (start, process_answer accumulate, complete → calculate_and_show_archetype real calc + assign + once-only assert (re-complete does not overwrite; copy TestStoryArchetypeImmutability setup), clear FSM).  
- TestViewArchetypeAchievementsIntegration (real archetype + seed achievements from grants if possible).  
- Use real StoryService; patch class; assert quiz texts, archetype result, "ya tienes un arquetipo", achievements list.  
- If FSM restore needed: MemoryStorage sim or note (per impact).  
- ruff; pytest new + re-run story unit full (imm + FSM + achievement atomic + narrative gold).  
- "F3 safe point". DoD marked.

### F4 port advance/make_choice + invalid graceful + cost paths + possible E2E atomic (GSD pre)
- GSD pre.  
- Extend: TestMakeChoiceGoToIntegration (success advance, end of story, choice with extra cost, invalid branch → graceful no partial debit, progress unchanged, balance same; copy TestStoryInvalidTransitions + atomic setups).  
- For cost>0 paths: use TestSession/file pattern copy store E2E + story atomic gold verbatim (N806+docstring DESIRED CONTRACT, 777 tg, explicit models User/BesitoBalance/StoryNode/StoryChoice/UserStoryProgress/BesitoTransaction, try/finally reopen/re-query, external patch ONLY if any, re-query post; strict asserts on tx + progress + balance delta).  
- Or 1-line/guard for balance.  
- Assert no partial on invalid (balance same, progress same).  
- ruff; pytest integration + re-run cross atomicity + story atomic + reaction_mission + broader.  
- "F4 safe point". DoD marked. Atomic visible protected.

### F5 backpack + mission integration (tight) + 1-line guards + hygiene (GSD pre)
- GSD pre.  
- Create `tests/handlers/test_backpack_handler_integration.py` (tight 3-5 tests): fulfillment_retry success (real + status), resend_vip (real token/link or external VIP patch), read_chapter (real node_id roundtrip + delegate show_node), lists from real orders/rewards. Use _mock or direct class patch get_service(BackpackService) pattern; UI 1:1 (toasts without HTML, "adquisición", VIP link).  
- Create `tests/handlers/test_mission_user_handlers_integration.py` (tight): TestShowMyMissionsIntegration (real progress bars), TestMissionDetailIntegration (progress + catchup + reward shape besitos/pkg/vip), TestClaimMissionRewardIntegration (real deliver → reward visible; 1-line if balance). Patch class get_service(MissionService).  
- Ensure any balance inspect uses exact 1-line/guard + comment.  
- ruff + format; full pytest on new files; re-runs golds per impact (story full + cross + reaction_mission + daily + vip + invariants + broader -k).  
- Greps (patch class, real svc, 1-line comments, UI strings preserved).  
- "F5 safe point". DoD marked.

### F6 gates + re-runs + rules verif + self-check PASSED + handoff (GSD pre every)
- GSD pre.  
- ruff on all touched (new integration files + any ports).  
- Re-execute exact golds list from impact map + PLAN (story unit full, cross full, reaction_full_chain + reaction_mission_flow + reaction_limit, mission_e2e, daily atomic, vip_*, invariants, broader -k "story or narrative or archetype or mission or backpack or ... or atomicity or reaction or daily or vip").  
- Bot smoke (import handlers.story_user_handlers, backpack_handler, mission_user_handlers).  
- Greps: 0 prod changes (handlers/*_user*.py untouched); patch class present in new files; real svc usage; 1-line comments; UI strings 1:1; "Item 1/34" refs; no new writes in crit paths.  
- Rules verif (GSD pre every + wc, scope tight per listed files + log + PLAN, 3 crit protected via re-runs + greps, UI 1:1, 1 svc via get_service in prod unchanged, integration follows gamif/store int precedent exactly, 1-line ports present with comment, no prod chg, 0/0/0).  
- Full self-check PASSED in log + opt SUMMARY.md: phases/DoD/gates/archivos/tests passed; reglas verificadas (GSD pre every, scope tight, 3 crit + contracts protected, precedents copied al pie, UI 1:1, 0 prod/0 beh/0 atomicity); desviaciones (pre only, doc non-reg); tests críticos (exact golds list); "Item 1/34 closed. First of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch-enforcer re-scan (enfocado en story/backpack/mission handler integration + real svc + 1-line ports + 0 impact on 3 crit) + test-guardian (correr golds listados) + documentador (update ROADMAP + learnings + .grok/agent-memory/documentador/ report + MEMORY pointer) + gsd-executor del siguiente item del pool".  
- "F6 safe point". DoD marked. Pool phrase.

---

## 3. Copia patrones **al pie de la letra**

- **Handler integration style (gamif + pool33 store):** pytestmark=integration; real service instance injected via class patch on the handler module's XXXService; full flow handler → real svc → DB → edit_text/answer with exact UI text; no MagicMock returns for core data; fixtures real (nodes/choices/progress/archetype, missions/progress/rewards, orders/fulfillments + balance with telegram_id = user.telegram_id).  
- **Atomic/E2E gold (TestStorePurchaseAtomicGold + story unit atomic):** TestSession/file + N806 tol + docstring DESIRED CONTRACT; fresh numeric TG 7770xxxx; explicit models (User, BesitoBalance, StoryNode/Choice/Progress/Achievement/BesitoTransaction etc.); try/finally reopen db2 + re-query; "besitos tx + progress in same tx" (story advance) or "credit survives deliver False" style; external patch ONLY (if any delivery/notify); strict asserts on DB state post; 1-line/guard for balance.  
- **1-line/guard ports (Item10/28 + daily/cross + pool33):** exact `if not hasattr(svc, "besito_service") else ...` or `BesitoService(db=...) if not hasattr...`; comment "# 1-line/guard port post Item10 local (copy daily precedent in cross; arch-enforcer); was service.besito_service".  
- **GSD pre + wc + detailed:** timestamp | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie (gamif int + store int/E2E + story golds + 1-line + mapeo + pool phrase + 3 crit)>; pre every; wc after.  
- **Self-check + pool phrase + handoff:** full structure at F6; verbatim "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters..."; "Item 1/34 closed. First of new pool of 4."; explicit arch-enforcer + test-guardian + documentador + next executor.  
- **Arch + test-guardian verdicts:** arch "PASS" or "PASS WITH NOTES (0 critical)"; test-guardian "suite protege adecuadamente" + re-runs of listed golds.  
- **UI 1:1 + Lucien voice:** assert exact strings/emojis/buttons/cbs from prod/tests (see impact + current unit tests); no voice change.  
- **3 crit + contracts + logging + GSD:** explicit in every section.

---

## 4. Instrucciones para gsd-executor

1. **Read first (MANDATORY before any edit/gate):** This PLAN.md (full) + `.grok/agent-memory/impact-analyzer/pool34-item1-user-flows-reality.md` (full) + HARDENING_ROADMAP.md (pool33 + sec5) + precedents full (gamification_user_handlers_integration.py, store_user_handlers_integration.py + test_store_purchase_integration.py, 33-PLAN + gsd log + SUMMARY, 29/28/27/26/25 PLANs + gsd + SUMMARIES, story unit golds full, 1-line examples in cross/store/daily); current unit tests story/backpack/mission (mocks + strings); handlers source (story_user_handlers.py, backpack_handler.py, mission_user_handlers.py entrypoints + get_service + UI strings); fixtures conftest; story_service/backpack/mission_service (for understanding real paths, 0 touch); golds list from impact. Confirm 0 prod intent. Confirm golds match.

2. **GSD pre-log discipline (total):** BEFORE every mod (write/search_replace on test files/PLAN/log/SUMMARY), gate (ruff/pytest/grep/smoke/LOC/self-check): append "=== $(date -Iseconds) | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie de la letra (gamif int + store int/E2E + story atomic/imm/FSM + 1-line + impact mapeo + 3 crit protected + pool phrase)>" >> `.planning/quick/gsd-34-item1-user-flows-reality.log` (python -c safety); wc -l after. Track 5-10+ per phase. No exceptions.

3. **Tight scope (0 creep):** Only files listed in "Archivos" for this Item (new 3 integration tests + log + PLAN + opt SUMMARY). 0 prod code. 0 golds of 3 crit (re-run only). Re-verify via golds + greps (0 new writes in gamif/narr/channel paths).

4. **Copy al pie de la letra (every phase):** Gamif/store int pattern (class patch return real, full flow, pytestmark); atomic gold (TestSession, 777, try/finally, DESIRED, survives, post-credit/best-effort, patch external only); 1-line/guard exact comment; GSD pre + wc; self-check + pool phrase + handoff; UI 1:1; 3 crit + contracts cited.

5. **Phases strict (gated, safe points, DoD before advance):** Follow F1-F6 order; mark DoD in GSD at end of each (e.g. "F2 gates complete + safe point: ruff limpio; grep patch class + real service; pytest spot green; UI 1:1; 1-line guard present; F2 safe point - narrative_menu + start/continue integration; ready for F3. DoD all marked."). "F<N> safe point" log. Revertable (delete new test = clean; ports additive).

6. **Re-verify 3 crit + contracts + rules (every phase end + F6):** Re-run golds exact (story unit full + cross full w/ patch+DESIRED+TestSession+strict + reaction chains + mission_e2e + daily + vip + invariants + broader); greps (0 writes in crit paths; patch class; real svc; 1-lines; UI 1:1; pool phrase); ruff clean; bot smoke; rules (GSD pre every + wc, scope tight per PLAN, 3 crit protected, get_service 1 call in prod unchanged, integration follows precedent, no prod chg).

7. **Gates/commands (exact):** ruff check --fix + format --check; `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "..."` (exact from impact + PLAN); bot smoke `python -c "import handlers.story_user_handlers; ..."`; greps `-n -c -A`; GSD pre before each. Re-runs after ports/edits.

8. **Documentador at pool close (after Item1 if single or last of pool):** Explicit launch with prompt: "For pool 34-remaining-user-flows-reality close (Item 1/34): update HARDENING_ROADMAP.md (append completed + metrics + pool/BATCH notes + verbatim pool phrase); persist tirón report in .grok/agent-memory/documentador/ + MEMORY.md; source of truth: this PLAN + gsd log + impact map + test changes; follow GSD pre for your log; include pool phrase + handoff; no manual code edits."

9. **Self-check at F6 + item close (full in log + opt SUMMARY):** phases/DoD/gates/archivos/tests passed/reglas verificadas (GSD pre every, scope tight per PLAN, 3 crit + contracts protected via re-runs/greps, precedents copied al pie, UI 1:1, 0/0/0)/desviaciones (pre only, doc non-reg)/tests críticos (exact golds from impact)/"Item 1/34 closed. First of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch-enforcer re-scan (...) + test-guardian (...) + documentador (...) + gsd-executor siguiente del pool".

10. **Risks/mit (conservative, copy from impact):** Story advance atomic (mit: TestSession/file + explicit + re-query + story atomic gold re-run); archetype once-only (mit: copy immut setup + assert re-complete no overwrite); invalid no partial (mit: copy invalid trans gold); 1-line ports (mit: copy exact + comment; re-run golds); N806 (mit: tol + doc); detached post-commit (mit: TestSession as gold); fulfillment mocks (mit: patch external only; assert DB state); churn (mit: UI 1:1 + keep non-reality unit mocks); no prod change = safe revert (delete new tests). Safe points: delete new = clean.

11. **Output per phase:** Brief report in GSD (what + gates + safe point + DoD); full self-check + pool phrase at F6/item close. (opt) SUMMARY post mirroring 33/28/27.

---

## 5. Golds / Tests a re-ejecutar (exactos desde impact map; 0 regression)

```bash
# Story / narrativa golds (CRÍTICO #2)
pytest tests/unit/test_story_service.py -q --tb=line -p no:cov --override-ini="addopts="

# Cross atomicity (side effects claim/advance)
pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="

# Reaction/mission chains + mission E2E real
pytest tests/integration/test_reaction_full_chain.py tests/integration/test_reaction_mission_flow.py tests/integration/test_reaction_limit.py tests/integration/test_mission_e2e.py -q --tb=line -p no:cov --override-ini="addopts="

# Daily atomic
pytest tests/unit/test_daily_gift_service.py -q --tb=line -p no:cov --override-ini="addopts="

# VIP flows (canales-VIP + backpack resend / mission vip reward)
pytest tests/integration/test_vip_flow.py tests/integration/test_vip_flows.py tests/integration/test_vip_complete_cycle.py -q --tb=line -p no:cov --override-ini="addopts="

# Invariants
pytest tests/integration/test_invariants.py -q --tb=line -p no:cov --override-ini="addopts="

# Broader smoke
pytest -k "story or narrative or archetype or mission or backpack or fulfillment or reward or atomicity or reaction or daily or vip" -q --tb=line -p no:cov --override-ini="addopts=" 2>&1 | tail -20
```

Post ports + new int: also run the new *_integration.py + original unit handler tests for the modules.

---

## 6. Riesgos + Mitigación (copy de impact + pool33 precedent)

- DetachedInstance / post-commit visibility en advance/claim (mit: TestSession/file para paths atómicos como gold; re-query post; 1-line/guard).  
- Archetype once-only / immutabilidad (mit: copy TestStoryArchetypeImmutability setups + assert re-complete no overwrite).  
- Invalid branches partial debit (mit: copy TestStoryInvalidTransitions; assert balance/progress unchanged).  
- 1-line ports breaking on locals (mit: copy exact comment + pattern; re-run golds after).  
- N806 en TestSession (mit: tol + docstring como precedent).  
- Fulfillment/VIP mocks en backpack (mit: patch external only; assert DB state + UI).  
- Mission side effects best-effort (mit: seed optional; no hard assert unless golden).  
- Mock churn (mit: UI 1:1 pins + additive integration; non-reality unit tests untouched).  
- 0 impact on 3 crit golds (mit: re-runs protect; no writes in crit paths).  
Safe points: delete new test file = clean revert; ports are guards only (no beh chg).

---

## 7. Artefactos

- PLAN.md (this).  
- gsd-34-item1-user-flows-reality.log (GSD pre every + wc + self-checks + pool phrase).  
- New integration test files (3).  
- (opt) *-SUMMARY.md post (mirroring 33/28/27).  
- Arch-enforcer report (PASS / PASS WITH NOTES 0 critical).  
- Test-guardian report ("suite protege adecuadamente" + re-runs).  
- Documentador report + ROADMAP append + .grok/agent-memory/documentador/ + MEMORY (at pool close).  
- Handoff explicit after F6 self-check.

---

## 8. Self-check (planner, pre-handoff)

**Phases/DoD/gates/archivos/tests passed:** F1-F6 defined with safe points + DoD; files exact per scope; golds list + re-run cmds copied; precedents listed; 0/0/0 stated; pool phrase + "Item 1/34" in title/handoff.

**Reglas verificadas:** GSD pre every (planner entries + will be in executor); scope tight (only listed tests + log + PLAN; 3 files max new); 3 crit + contracts protected (re-runs + greps + 0 writes in crit paths); precedents copied al pie (gamif int + store int/E2E + story golds + 1-line/guard + GSD/self-check/pool/handoff); UI 1:1 required; get_service 1 call in prod unchanged; no prod change; logging standard in GSD; <50 if any helpers (unlikely in tests).

**Desviaciones:** Ninguna (pre-exist only, doc non-reg per precedent: N806 tol, daily flake, long guards, etc.).

**Tests críticos para futuro:** Exact golds list from impact + new integration files + original handler units.

**Pool note + handoff:** Item 1/34 closed. First of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch-enforcer re-scan (enfocado en story/backpack/mission handler integration tests + real svc + 1-line ports + 0 impact on 3 crit) + test-guardian (correr golds listados) + documentador (update ROADMAP + learnings + report) + gsd-executor del siguiente item del pool.

**Self-check PASSED.**  
**Handoff to gsd-executor ready.**

---

**Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.**
