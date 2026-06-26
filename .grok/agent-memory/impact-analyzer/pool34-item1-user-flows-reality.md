# 📊 Análisis de Impacto: Remaining User Flows Test Reality Hardening (Story / Backpack / Mission User)

**Agent:** impact-analyzer (hardener-agile, Item 1 of new pool of 4 after pool 33)  
**Date:** 2026-06-26  
**Scope:** Tests-only hardening. 0 behavior change, 0 atomicity change, 0 prod code change (except 1-line/guard ports precedent if balance inspection required in new tests). Protect 3 critical systems (gamificación/besitos/reacciones/daily, narrativa, canales-VIP) + atomicity/EventBus/get_service contracts.

---

## Cambio Propuesto (from ROADMAP + mapeo 33)

Per HARDENING_ROADMAP.md section 5 "Proposed Next #1" and pool 33 close:
"Remaining user flows test reality hardening (per 33 mapeo clusters left: story_user quiz/archetype real, backpack fulfillment real, mission_user claim/progress/list real integration style)"

After pool 33 (store + promo reality hardened, tests-only, 4 items, arch PASS WITH NOTES 0 crit, test-guardian "suite protege adecuadamente", golds 0 attributable regressions):
- Source of truth: .grok/agent-memory/impact-analyzer/33-test-reality-user-flows-mapeo.md (tables + "remaining" summary + explicit recs for story/backpack/mission_user).
- "Quedan ~2-4 clusters del análisis inicial después de este pool."
- "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado."

High reality value: narrativa (CRÍTICO #2) + post-purchase (backpack) + mission claim/progress.

Apply proven patterns from pool 33 + prior:
- gamification_user_handlers_integration.py style: pytestmark=integration, real_svc = XXXService(db_session), patch("handlers.*.XXXService") return real, handler → real svc → DB → UI 1:1 (Lucien strings, emojis, buttons, cbs, empty states preserved exactly).
- TestSession/file + N806 tol + docstring DESIRED CONTRACT + 777 tg + explicit models + try/finally reopen/re-query + external patch ONLY for delivery/notify + 1-line/guard for Besito balance (if inspecting post-debit/credit).
- UI 1:1, logging standard, 0/0/0, get_service 1 call unchanged in prod.
- No touch golds of 3 crit (only re-run).

---

## Riesgo Total: ALTO (narrativa es CRÍTICO #2; MEDIO para backpack/mission)

**Por qué ALTO:**
- StoryUser flows (quiz/archetype calc+assign+once-only, advance_to_node with cost_besitos + commit=False atomicity (besitos + UserStoryProgress), invalid branches, FSM restore, achievements, VIP-gated nodes) directly exercise CRÍTICO #2 (narrativa). See unit/test_story_service.py: TestStoryArchetypeImmutability, TestStoryInvalidTransitions, TestStoryServiceAtomicity (debit commit=False), TestStoryFSMEventBus, TestStoryAchievementAtomicity, TestStoryNarrativeGoldFase6.
- StoryService holds direct BesitoService (self.besito_service = BesitoService(self.db)) + does debit/credit in advance/_grant_achievement. advance_to_node is atomic boundary (besitos + progress in one tx).
- Backpack touches post-purchase fulfillment (retry, read chapter → story node, VIP resend) + besito balance in summary. Delegates to FulfillmentService (locals), Package, Story, VIP.
- MissionUser claim/progress/list touches Reward delivery (besitos/package/VIP rewards) → gamif credit paths (Reward now uses locals per Item5). Uses real integration golds already (test_reaction_mission_flow, test_mission_e2e) but handler layer is pure isolation.
- From 33 mapeo table (source):
  - story: 84-95 get_service / 186 total mocks → "CRÍTICO #2 (narrativa). No tocar sin gold re-runs de story + archetype."
  - mission user: 47/95
  - backpack: 35/58

**3 crit protegidos:** Golds (cross_service_atomicity, reaction_mission_flow, reaction_* , daily atomic, invariants, vip_*, story unit golds, atomic story) NO deben romperse. New handler integration tests must re-run them after. 0 mutation on gamif credits, narrative progress/archetypes/FSM/quiz, channel pending/approve/VIP grant.

---

## Mapa de Impacto Directo (User Flows + Tests)

### Story User (NARRATIVA — CRÍTICO #2, MÁXIMA PRIORIDAD)

| Flujo de Usuario | Archivos de Test | Mock Count / Tipos | Nivel de Realidad Actual | Riesgo de Realidad | Recomendación |
|------------------|------------------|--------------------|---------------------------|--------------------|---------------|
| narrative_menu (not started / started / with/without archetype / progress chapter) | test_story_user_handlers.py (TestNarrativeMenu) | Heavy MagicMock on has_started_story, get_user_archetype, get_user_progress | Isolation | Alto: UI texts ("Fragmentos...", "Bienvenido de vuelta", "Capitulo X", archetype name) + buttons depend on mock returns. | Alta: integration style real StoryService + real UserStoryProgress + archetype rows. |
| start_story (already / no starting node / with node → advance + show) | TestStartStory | Mocks get_starting_node, create_user_progress, advance_to_node + internal patch continue/show_node | Isolation | Alto: advance path (cost, atomic) mocked; no real progress persistence or besitos debit visible. | Muy alta (crit #2). |
| continue_story / go_to_node (progress node, no progress, invalid) | TestContinueStory, TestGoToNode | Mocks get_user_progress + patch show_node/start | Isolation | Alto: real advance_to_node + visited + chapter not exercised from handler. | Alta. |
| make_choice (not found, success advance, end of story, advance failure) | TestMakeChoice | Mocks advance + patch show_node | Isolation | Alto: choices, additional_cost, ending → archetype button. | Alta. |
| Archetype quiz: start, process_answer (accumulate), complete (calc + assign + clear FSM) | TestStartArchetypeQuiz, TestProcessQuizAnswer, TestQuizCompletion | Mocks start/calc/assign + FSM state mocks | Isolation (FSM + service) | CRÍTICO: calculate_archetype_from_quiz (hardcoded in service), assign_archetype_to_user (once-only), clear. No real archetype persistence or immutability test from handler. | MÁXIMA (narrativa core). |
| show_node (not found, VIP deny, ending, decision, quiz node) + render builders | TestShowNode | Mocks get_node, get_choices, resolve_next + VIP check | Isolation | Alto: cost display, VIP gate, choice buttons with extra cost, Lucien voice. | Alta. |
| view_my_archetype, my_story_achievements (with/without) | TestViewMyArchetype, TestMyStoryAchievements | Mocks get_user_archetype, get_user_achievements | Isolation | Medio-alto: real achievements from _grant_achievement (credit possible) not visible. | Media-alta. |
| Admin deny filter (router lambda is_admin) | TestAdminDeny | patch is_admin | Thin | Bajo. | Baja. |

**Total @patch get_service in story test (grep):** 28 (plus 186 total pattern occurrences of get/patch/Mock; 33 mapeo cited 84-95/186).

**Consumers directos de StoryService (trazado 1-2 niveles):**
- handlers/story_user_handlers.py (all via `with get_service(StoryService) as ...` — 1 service rule; ~10+ entrypoints: narrative, start/continue, go_to/make_choice, quiz start/process, view archetype/achievements).
- handlers/backpack_handler.py (callback_read_chapter delegates to story_user_handlers.show_node after getting node_id from fulfillment).
- services/store_service.py (thin delegates: get_all_nodes, get_node for story-unlock products).
- services/fulfillment_service.py (StoryService for chapter read?).
- services/story_service.py itself (internal + held Besito/Package/VIP).
- tests/unit/test_story_service.py (real db + atomic golds).
- tests/handlers/test_story_admin_handlers.py (admin CRUD, separate).
- integration/test_callbackdata_story_user.py (packing only, no behavior).

**Dependencias internas de StoryService (trazado):**
- Held: BesitoService (debit in advance_to_node with commit=False for atomicity with progress; credit in _grant_achievement for some rewards).
- PackageService, VIPService (for access gates?).
- EventBus listener on_besitos_awarded (obs only, "MUST NOT credit/debit"; best-effort).
- Models: StoryNode, StoryChoice, UserStoryProgress, StoryAchievement, UserArchetype? , BesitoTransaction (for costs).

**Impacto indirecto:**
- Real integration test exercising advance_to_node with cost_besitos >0 → touches besitos atomic tx → re-run unit/test_story_service.py (TestStoryServiceAtomicity + AchievementAtomicity), cross_service_atomicity (if side), invariants if any story-related.
- Quiz complete → archetype assign once-only → must protect TestStoryArchetypeImmutability.
- Invalid branches → TestStoryInvalidTransitions.
- FSM quiz + restart sim → TestStoryFSMEventBus.
- Achievements list → may reflect prior grants/credits.
- If new test hits paid node → 1-line/guard for balance inspect or class patch BesitoService.

### Backpack Fulfillment (Post-Purchase — Alta Prioridad UX)

| Flujo | Test File | Mocks | Realidad | Riesgo | Rec |
|-------|-----------|-------|----------|--------|-----|
| fulfillment_retry (success, html strip in toast) | TestBackpackFulfillmentCallbacks | _mock_backpack_ctx + AsyncMock retry_fulfillment_delivery | Isolation | Medio: real FulfillmentService retry + status not exercised from handler. | Media-alta. |
| resend_vip_invite (activate shows link) | same | resend_vip_invite_for_fulfillment | Isolation | Alto (toca VIP crítico): real VIP resend + token not visible. | Alta (canales-VIP). |
| read_chapter (requires node, delegates to story show_node) | ... + patch story_user_handlers.show_node | get_fulfillment_detail + cross patch | Isolation + cross | Alto: links post-purchase to narrative (crit #2); node_id roundtrip. | Alta. |
| submit_input_start / process (FSM, validation, submit) | TestBackpackInputFSM | get_input_prompt, submit_fulfillment_input | Isolation + FSM | Medio: real prompt/submit via Fulfillment. | Media. |
| view_waitlist, deliver_package, purchase/reward detail, lists/pagination, balance | various + pure kb tests | get_detail, deliver_package_content (direct MockBackpack), build_* pure | Mix (puros good) | Medio: lists from real orders/rewards/vip + balance. | Media (puros already extracted). |
| cmd_mochila / menus | ... | summary via svc | Isolation | Medio. | Media. |

**Counts (from 33 mapeo + grep):** 35 get_service / 58 total; 11 @patch get_service (grep).

**Consumers:**
- handlers/backpack_handler.py (many cbs + /mochila; uses get_service(BackpackService); one direct patch BackpackService in test_deliver; cross to story show_node).
- Possibly fulfillment_admin_handlers (not in scope).
- services/backpack_service.py (thin delegates to FulfillmentService locals for retry/get_prompt/submit/resend_vip; Besito for summary; Package; Story? via fulfillment).
- Cross: test_cross_service_atomicity, unit/test_fulfillment_service, unit/test_backpack_service, test_store_* (orders).

**Deps:** FulfillmentService (heavy), BesitoService (balance), PackageService, StoryService (indirect via chapter node), VIP for resend.

### Mission User (Claim/Progress/List)

| Flujo | Test | Mocks | Realidad | Riesgo | Rec |
|-------|------|-------|----------|--------|-----|
| show_my_missions (empty, with progress bars, calls with user_id, closes ctx) | TestShowMyMissions | get_user_active_missions returning list of dicts {mission, progress, percentage} | Isolation | Medio: real progress + bar calc + bot= not visible. | Media-alta. |
| mission_detail (not found, no reward, besitos/pkg/vip reward, catchup before render, escapes, calls, closes) | TestMissionDetail | get_mission, get_or_create_progress, deliver_pending... | Isolation | Medio-alto: catchup (deliver_pending) + reward shape in UI. Touches gamif via reward delivery. | Alta. |
| claim_mission_reward (success deliver, no pending) | TestClaimMissionReward | deliver_pending_rewards_for_mission | Isolation | Alto (recompensa): real deliver path (may credit besitos/pkg/vip). | Alta (gamif side). |

**Counts:** 47 get_service / 95 total; 15 @patch get_service.

**Consumers:**
- handlers/mission_user_handlers.py (3 entrypoints via get_service(MissionService) — 1svc).
- handlers/reward_user? , admin (separate), broadcast/scheduler/vip/daily for side effects (run_mission_side_effects_isolated).
- services/mission_service.py (delegates RewardService for deliver/get_all/get; local Besito in places; thin delegates added in Item9 for admin wizard).
- tests/integration/test_reaction_mission_flow.py + test_mission_e2e.py (real service E2E, gold style, NO handler mocks — "DATOS REALES", no mocks for missions).
- unit/test_mission_service.py, test_mission_side_effects, test_reward_service, cross atomicity (side effects), invariants.

**Deps:** RewardService (core for claim), Besito (in some paths), models progress/reward.

---

## Mapa de Impacto Indirecto (Cadenas)

| Archivo Afectado | Cadena de Dependencia |
|------------------|-----------------------|
| tests/handlers/test_story_user_handlers.py (new integration) | handler test → real StoryService(db) → BesitoService held (debit commit=False in advance or credit in achievement) → DB (UserStoryProgress + BesitoTransaction atomic) → UI; also EventBus listener (obs). Re-run story atomic golds + archetype immut + invalid + FSM + achievement atomic. |
| tests/handlers/test_mission_user_handlers.py (claim integration) | handler → real MissionService → RewardService.deliver → (local Besito credit or package/vip) → post best-effort side effects. Re-run cross_service_atomicity + reaction_mission_flow + mission_e2e + reward gold. 1-line/guard if balance inspected post-claim. |
| tests/handlers/test_backpack_handler.py (fulfillment/vip/story link) | handler → real Backpack → Fulfillment (retry/resend) or Story show_node (chapter) or VIP. Re-run vip flows + story unit golds if chapter real. |
| tests/unit/test_story_service.py (golds) | If new handler int exercises advance/quiz/achievement with costs or assigns → re-run full TestStory*Atomicity/Immutability/Invalid/FSM/Achievement/NarrativeGold. |
| tests/integration/test_cross_service_atomicity.py + test_reaction_mission_flow.py + test_mission_e2e.py | Side effects from claim or (indirect) purchase history in backpack. Re-run full. |
| tests/integration/test_vip_flow*.py + test_invariants.py | VIP resend or VIP reward from mission claim. Re-run. |
| services/* (thin delegates) | store_service thin to Story (nodes for unlock products) — if fixtures change, but tests-only no prod. |
| bot.py (listener reg) | 0 new; story listener already; if achievement emits, already covered. |

---

## Tests que DEBES Correr Antes (y Después)

**Golds obligatorios (0 regression; copy from 33 mapeo + story specifics):**
```bash
# Story / narrativa golds (CRÍTICO #2)
pytest tests/unit/test_story_service.py -q --tb=line -p no:cov --override-ini="addopts="

# Cross atomicity (side effects claim/purchase)
pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="

# Reaction/mission chains (gamif + mission deliver)
pytest tests/integration/test_reaction_full_chain.py tests/integration/test_reaction_mission_flow.py tests/integration/test_reaction_limit.py -q --tb=line -p no:cov --override-ini="addopts="

# Mission E2E real
pytest tests/integration/test_mission_e2e.py -q --tb=line -p no:cov --override-ini="addopts="

# Daily atomic
pytest tests/unit/test_daily_gift_service.py -q --tb=line -p no:cov --override-ini="addopts="

# VIP flows (canales-VIP + backpack resend / mission vip reward)
pytest tests/integration/test_vip_flow.py tests/integration/test_vip_flows.py tests/integration/test_vip_complete_cycle.py -q --tb=line -p no:cov --override-ini="addopts="

# Invariants (any order/mission status)
pytest tests/integration/test_invariants.py -q --tb=line -p no:cov --override-ini="addopts="

# Broader smoke
pytest -k "story or narrative or archetype or mission or backpack or fulfillment or reward or atomicity or reaction or daily or vip" -q --tb=line -p no:cov --override-ini="addopts=" 2>&1 | tail -20
```

**Specific after ports / new integration:**
```bash
pytest tests/handlers/test_story_user_handlers.py -q --tb=line ...
pytest tests/handlers/test_mission_user_handlers.py ...
pytest tests/handlers/test_backpack_handler.py ...
# Plus any new *_integration.py created
```

**Precedents to re-run / copy exactly:**
- tests/handlers/test_gamification_user_handlers_integration.py (full style)
- tests/handlers/test_store_user_handlers_integration.py (pool33 Item1)
- tests/integration/test_store_purchase_integration.py (TestSession E2E pattern, 1-line/guard, external patch only, N806 doc, 777, try/finally)
- unit/test_story_service.py atomic + immut + invalid + FSM + achievement (DESIRED comments, fresh 777 tg, explicit balance, strict asserts)

---

## Tests que FALTAN (Riesgo No Cubierto — Confianza de Realidad Baja)

Per 33 mapeo + current scan:
- [ ] test_story_user_quiz_real_archetype_calc — no existe (handler mocks calc/assign; service unit covers but not via handler FSM + UI)
- [ ] test_story_user_advance_real_cost_debit_and_progress_persist — isolation; atomic gold only in service unit
- [ ] test_story_user_invalid_branch_graceful_from_handler — no real service path
- [ ] test_story_user_achievements_real_from_grants — mocks
- [ ] test_story_user_fsm_quiz_restore — mocked
- [ ] test_backpack_fulfillment_retry_real_delivery — isolation (58 mocks total)
- [ ] test_backpack_resend_vip_real_token_link — isolation (VIP crit)
- [ ] test_backpack_read_chapter_real_node_link — cross mock
- [ ] test_mission_user_claim_real_progress_persist_and_reward — isolation (service + reaction golds exist but handler claim path not real)
- [ ] test_mission_user_list_and_detail_real_db — isolation
- [ ] No dedicated handler integration for story/backpack/mission_user (only gamif + common + now store/promo from pool33)

**Patrón faltante:** Solo gamif + common + (post33) store/promo use real service handler integration. Story (crit#2) + post-purchase + mission claim are high reality gaps.

---

## Precauciones Específicas (copy precedents al pie)

1. **Story advance atomic (besitos + progress):** If new integration hits paid nodes (cost_besitos>0), use TestSession/file + explicit balance + re-query post like test_store_purchase_integration + story unit atomic gold. Re-run TestStoryServiceAtomicity. "credit/debit survives" style not directly but "besitos tx + progress in same tx" contract.
2. **1-line/guard for Besito (Item10 precedent):** In any test inspecting balance after story advance or mission claim or backpack summary:
   ```python
   bal = (BesitoService(db=db_session).get_balance(tg)
          if not hasattr(svc, "besito_service") else svc.besito_service.get_balance(tg))
   ```
   See cross atomicity 726/762, store unit ~210/420, daily guards.
3. **External patch ONLY for delivery/notify:** In E2E style, patch PackageService.deliver or VIP resend or notify — never core logic. See store E2E + atomic gold.
4. **Archetype once-only / immutability:** New quiz completion test MUST assert archetype not overwritten on re-complete. Copy TestStoryArchetypeImmutability setups (fresh 777 tg, explicit balance, DESIRED comment).
5. **Invalid transitions:** Test must verify no partial debit, progress unchanged, balance same. Copy TestStoryInvalidTransitions.
6. **FSM quiz:** Use real state or MemoryStorage sim; test clear on complete + archetype assign. See TestStoryFSMEventBus for restart sim.
7. **get_service class patch (not ctx):** Like gamif/store int:
   ```python
   real_svc = StoryService(db_session)
   with patch("handlers.story_user_handlers.StoryService") as MockS:
       MockS.return_value = real_svc
       ...
   ```
8. **UI 1:1 + Lucien:** Pin exact strings from current tests/handlers (e.g. "Fragmentos de la Historia", "Bienvenido de vuelta", "Capitulo X", "descubrira que arquetipo", "Sin recompensa", progress bars "█░", "50 besitos", "Paquete: ...", toasts without HTML, etc.).
9. **No touch 3 crit golds:** Only re-run. If port causes fail in cross/reaction/story atomic/vip/daily/invariants → revert, it broke contract.
10. **Arch-enforcer gate:** 1-service already in these handlers (get_service); puros for build_* if touched; <=50 if long funcs edited in tests (unlikely); logging; 3 crit protected orthogonal.
11. **CallbackData tests:** test_callbackdata_story_user.py is packing only — do not "real-ify"; correct as-is (unit serial).

---

## Recomendación de Tight Scope para Este Ítem (1 of new pool of 4)

**Pool phrase (al cerrar item / pool):** "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

**Tight scope (tests-only, high reality value, follow pool33 exactly):**

**Primary (narrativa crit #2 first):**
- Create tests/handlers/test_story_user_handlers_integration.py (or extend)
  - pytestmark=integration
  - Real flows: narrative_menu (started/not + archetype), start/continue/advance paths (real progress, chapter), make_choice (success + end), quiz start/process/complete (real calc + assign + once-only + clear + UI), view_archetype, achievements list (if seed grants), invalid branch graceful.
  - Use real StoryService(db_session) via class patch.
  - For cost paths or achievement credits: TestSession or 1-line/guard; explicit seeds (nodes with/without cost, choices, balance 777 tg, progress, achievements).
  - UI 1:1 exact (copy strings from current unit tests + handler).
  - Re-runs: story unit full + cross + reaction_mission + vip + broader.
- If E2E atomic visible (paid advance or achievement credit): add or extend integration with TestSession/file pattern copy store E2E + story atomic gold verbatim (N806 doc, 777, explicit models, try/finally, external patch if any, re-query).

**Secondary (backpack post-purchase + mission claim):**
- tests/handlers/test_backpack_handler_integration.py (tight): fulfillment_retry, resend_vip (real or external patch VIP), read_chapter (real node link + delegate to show_node), lists from real data (orders/rewards/vip via fixtures).
- tests/handlers/test_mission_user_handlers_integration.py (tight): show_my_missions real, mission_detail (progress + catchup), claim (real deliver_pending → reward visible; may need 1-line if balance).
- Or combine if tight; prioritize 1-2 key per to keep item small.
- Use gamif int + store int + store E2E patterns al pie.

**In / Out (per 33 precedent):**
- In: the 3 handler test files (add integration or convert key classes), new integration files, 1-line/guard ports in new tests or if touching cross/unit non-golds, GSD pre, self-check, arch, testg, re-runs, report.
- Out: 0 prod code (handlers/*.py, services/*.py), 0 change to golds (story atomic, cross, reactions, daily, vip, invariants — only re-run), 0 new listeners/reg, 0 get_service change, 0 other handlers, 0 models/mig, 0 admin flows, no callbackdata change, no pure kb change unless 1:1.

**Entregables (hardener):**
- GSD pre-log before every edit/gate (in .planning/quick/gsd-*.log).
- self-check PASSED in executor.
- arch-enforcer: PASS / PASS WITH NOTES (0 critical).
- test-guardian: "suite protege adecuadamente" + re-runs golds + veredicto.
- This impact map persisted.
- Explicit handoff to gsd-planner with this + precedents.

**No scope creep:** Nothing outside listed user flows for story/backpack/mission_user. Story quiz/archetype/advance/achievements highest value.

---

## Resumen Ejecutivo + Recomendación para gsd-planner

**Estado actual (evidence from reads):**
- 3 crit: gamif well protected by real-service golds (cross, reaction chains, daily, invariants); narrativa (crit#2) protected in service unit (atomicity, archetype once-only, invalid trans, FSM restore, achievement atomic, narrative gold) but handler layer 100% isolation (186 mock patterns, 28 get_service patches); backpack/mission_user similar (58/95 mocks, handler claims/lists/details fully mocked while service+cross golds exist).
- Pool 33 proved the pattern works for store (critical money flow) + promo: converted to real svc integration + E2E TestSession, 1-line/guard, UI 1:1, 0 attributable reg on golds, arch PASS WITH NOTES 0 crit, testg "protege adecuadamente".
- Story has the richest gold unit coverage among the three (multiple DESIRED CONTRACT tests with fresh 777, explicit balance, strict post-state); but no handler integration exercising the real quiz → assign → once-only, advance cost atomic, invalid graceful, achievements from real grants, FSM from handler.
- Backpack has pure helpers already (build_* keyboards) — good; handler cbs still isolated.
- Mission has excellent real E2E at service level (reaction_mission, mission_e2e — "NO usa mocks"); handler claim/list/detail is the gap.
- Consumers tree traced 2+ levels: handlers (1svc each) → services → (Besito direct in story, Reward in mission, Fulfillment+Besito+Story/VIP in backpack) → cross effects (side effects best-effort, atomic tx in story advance).
- Risks to 3 crit + contracts identified with exact gold files to re-run. Mitigations: class patch get_service pattern, external-only patches, 1-line/guard, TestSession for visibility, re-runs, no prod changes.

**Recomendación para gsd-planner:**
- Proceed with tight item scoped to the 3 areas, prioritizing narrativa (quiz/advance/achievements/once-only/invalid/FSM) first, then backpack fulfillment + VIP link + chapter, then mission claim/list/detail.
- Copy al pie de la letra:
  - gamif integration structure + docstring.
  - store integration (pool33) + store E2E TestSession (N806, 777, explicit, try/finally, external patch, 1-line/guard, DESIRED, re-query).
  - story unit golds setups (archetype immut, invalid trans, atomic advance, FSM).
  - 1-line/guard from cross/daily/Item10.
- PLAN with 4-6 small phases (prep/GSD/baseline/greps; story int; backpack int or key cbs; mission int; 1-lines + re-runs golds exact list; self-check + arch handoff).
- List exact files touched, DoD per phase (UI 1:1 asserts, counts of patches reduced, golds green, no prod diff), risks+mit, safe points.
- Include full gold re-run commands from this report.
- After PLAN: handoff to executor with "copy precedents al pie", GSD pre every, self-check PASSED required.
- Keep pool phrase in all artifacts.
- 0/0/0 + 3 crit + contracts front of mind.

**Evidence citations (no assumptions):**
- 33 mapeo tables + recs + precautions (Item10 guards, TestSession, external only, UI1:1, golds list).
- ROADMAP pool33 entry + section5 Proposed Next #1 + metrics (0 crit, 0 attr reg, GSD, pool phrase).
- Handler tests: 186/95/58 pattern counts, class/test counts from grep, _mock_* helpers, MagicMock returns for all key methods.
- Handlers source: get_service(Story/Mission/Backpack), router cbs listed, 1svc already, pure build_* in backpack/story.
- Services grep: story holds Besito + debit(commit=False) + credit in grant + listener MUST NOT; mission delegates Reward + locals Besito; backpack delegates Fulfillment locals + Besito summary + Story/VIP.
- Unit story: atomic, immut (DESIRED + 777 + balance), invalid (no partial), FSMEventBus, achievement atomic, narrative gold.
- Integrations: reaction_mission + mission_e2e (real, no mocks, "DATOS REALES"); cross (TestSession + side effects + 1-line + DESIRED + patch schedule_emit); store E2E (full pattern); callbackdata story (packing only).
- Consumers: grep showed handlers + thin in store/fulfillment + side effects in scheduler/broadcast/vip/daily + backpack.
- CLAUDEs: 1-service via get_service, hardener pattern (1svc + puros + ports + UI1:1 + arch/testg + pool phrase), 3 crit always.

This map is actionable: gsd-planner can open exactly the listed test files + precedents, know which flows to convert first, what golds to re-run, what ports/guards, and what "suite protege" looks like.

**Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.**

*Fin del reporte (impact-analyzer Item 1 pool34).*
