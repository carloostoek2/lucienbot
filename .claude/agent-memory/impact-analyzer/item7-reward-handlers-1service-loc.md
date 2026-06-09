# Impact Analysis Report: Item 7 - Consolidate reward_user_handlers to exactly 1 service + extract pure helpers for ≤50 LOC

**Item:** reward handlers 1-service compliance + pure helpers extraction (continuation / new pool item, post Besito unification + mw hardening tirón)
**Date analyzed:** 2026-06-07
**Role:** impact-analyzer (new pool of 4, first item)
**Status:** Analysis complete; report for handoff to gsd-executor / arch-enforcer. (Pre-GSD append done via run_terminal before this persist + MEMORY update.)
**References:** 
- Precedent PLAN: .planning/phases/20-reward-gamif-rules-compliance/PLAN.md (Item 2, which references "Impact-analyzer report for Item 2" as source of truth; describes exact same tight scope)
- CLAUDE.md (root + handlers + services + models), rules.md, architecture.md, decisions.md, AGENTS.md
- Prior items 5/6 (RewardService desacoplado held Besito; get_service std; ports in tests for 1svc; pure emoji precedent "como en item 6")
- 3 critical systems always in mind: gamificación (besitos/missions), narrativa, channel/VIP (rewards feed into backpack/VIP but read-only here; 0 mutate)

## Executive Summary + Risks

**Summary:**  
Consolidate `handlers/reward_user_handlers.py` (specifically `show_available_rewards` and `reward_detail`, plus supporting `_build_rewards_buttons` and any long helpers) so they invoke **exactly 1 service** (MissionService via the standardized `with get_service(MissionService) as ...` context + `get_service` lifecycle). Currently, the handlers already achieve this post-prior work (only MissionService; no RewardService instantiation or direct calls in handler code), using:
- ORM relationship access (`mission.reward`) for reward details (precedent from mission_user_handlers).
- Pure top-level `get_reward_emoji(reward)` imported from `services.reward_service` (promoted for UI formatting; stateless, no side-effects, no DB).

The remaining arch-enforcer medium notes (from post-middleware + unification) are:
- Functions exceeding 50 lines (reward_detail ~49-56 LOC depending on count incl. comments/docstring; violates "Funciones máximo 50 líneas").
- Perception of orchestration (via enriched data dicts from `mission_service.get_available_rewards_for_user`, which internally does `RewardService(db)` just for `.get_reward`; plus helpers; even if handler itself is clean).

**This item (tight, first of new pool of 4):** Perform minimal extraction of 1-2 pure helpers inside the reward_user_handlers module to bring all functions ≤50 LOC. Minimal support in services (promote/ensure `get_reward_emoji` pure top-level + delegate compat, as done in Item 2 precedent). Update only the dedicated test file. 0 other handlers touched. 0 behavior change in claim/delivery (deliver_reward, log_reward_delivery, auto-deliver in mission increment paths, backpack earned rewards, etc. remain untouched). UI render (emoji, progress bar █░, status texts, button labels, truncation, callback data) must be **identical**.

**High-level risks (detailed below):** Low overall due to tight scope + precedent execution already in tree (code reflects "after" state of prior Item 2). Main: divergence in extracted pure formatting logic breaking list/detail UX or tests; residual test mocks assuming 2 services (already cleaned in this test file); indirect coupling via mission_service's internal RewardService spawn (out of scope, per explicit "NO tocar mission_service"). No impact on 3 critical systems' core (gamif credit, narrative progress, VIP/channel access) because this is read-only user-facing rewards list/detail (no tx, no deliver).

**Recommendations (scope mínimo to close arch-enforcer notes for reward):** As specified + PLAN precedent. See "Scope propuesto" section. Use GSD pre every edit (run_terminal append to .planning/quick/gsd-*.log , wc -l tracking, specific git add only touched). Self-check + critical tests list in handoff.

This addresses medium notes for reward handlers directly (parallel to prior work on gamif_user, broadcast etc.).

## Mapa de impacto completo (archivos, consumidores)

### Archivos a tocar (mínimo, orden sugerido por precedent PLAN)
1. **handlers/reward_user_handlers.py** (core)
   - Target: `show_available_rewards`, `reward_detail` (the ~56L one), `_build_rewards_buttons`.
   - Changes: Ensure/keep exactly `with get_service(MissionService) as mission_service:` (1 call only). Use rel `mission.reward` (already in detail). Use pure `get_reward_emoji` (already imported top-level). Extract 1-2 pure helpers to slim reward_detail (and show if needed) e.g.:
     - `_compute_reward_status_text(progress, mission) -> str` (the ternary + bar logic).
     - `_build_reward_detail_keyboard(mission_id: int) -> InlineKeyboardMarkup` (the buttons list).
     - Or internal for button item in list.
   - Keep all _build_*_text , _build_progress_bar, _safe_* (already small/pure or util).
   - Preserve: logs ("reward_user_handlers | ... | user_id=... | ..."), _EMPTY_REWARDS_TEXT, idempotency comments (gsd-mw-hardening phase 5), Lucien voice, exact strings/emoji/progress.
   - No new imports of RewardService; no DB; no biz logic (progress calc stays in service or pure format).
   - Post: verify no function >50 lines (count def-to-end).

2. **services/reward_service.py** (soporte mínimo only)
   - Ensure `get_reward_emoji(reward: Reward) -> tuple[str, str]` remains/ is module-level pure top (before class; docstring: "Función pura (sin estado ni side-effects)."; logic for BESITOS/PACKAGE/VIP_ACCESS/default identical).
   - Keep the instance delegate (added for Item 2):
     ```python
     # Backward-compatible delegate added for Item 2 (arch-enforcer 1-service rule for reward handlers).
     def get_reward_emoji(self, reward: Reward) -> tuple[str, str]:
         return get_reward_emoji(reward)
     ```
   - 0 changes to: deliver_reward / _deliver_* / log_reward_delivery / close / create_* / get_* / held subs (package/vip) / observer / anything in claim/delivery paths.
   - (Already in current tree per analysis; this item confirms.)

3. **tests/handlers/test_reward_user_handlers.py** (only its test file)
   - Port/confirm: all tests patch `"handlers.reward_user_handlers.get_service"` (not RewardService). Mock context `__enter__`/`__exit__`. Setup mock_reward with `.reward_type`, `.besito_amount`, `.name` etc so real pure `get_reward_emoji` executes in _build (for list) and detail.
   - Use `mock_mission.reward = mock_reward` for rel in detail tests.
   - Update docstrings (already say "Tests ported to 1-service pattern (get_service + MissionService only) + pure formatting via get_reward_emoji. Arch-enforcer note addressed." and note removals of skip-dupe/idempotency tests per mw phase5).
   - Add: new tests for extracted pure helpers (e.g. class `TestRewardUserPureHelpers`; cover empty/completed/progress for status, different RewardType for emoji+ gives, button texts/status_emoji + truncation + packed cb data, _build_progress_bar math).
   - Keep: make_callback fixture usage, assertions on edit_text content (exact phrases like "Recompensas Disponibles", "completada", "Progreso", "3 / 10"), calls to get_mission/get_or_create_progress/get_available..., close via context.
   - 0 direct RewardService mocks left in this file.

**Total touched for impl:** exactly 3 files (per tight scope in user spec + PLAN: "solo reward_user_handlers + soporte mínimo en services ... + updates en su test file").

### Consumidores y archivos relacionados (0 tocar, for awareness)
- **Registration / wiring:** `handlers/__init__.py` ( `from .reward_user_handlers import router as reward_user_router` ), `bot.py` (import + `dp.include_router(reward_user_router)` at ~line 296). Smoke import test sufficient.
- **UI entry:** `keyboards/inline_keyboards.py` (main menu: button "🎁 Recompensas" with `callback_data="rewards_list"`; shares row with Misiones).
- **Callback data:** `keyboards/callback_data.py` ( `class RewardUserDetailCallback(CallbackData, prefix="reward_user_detail"): mission_id: int` ; also MissionDetailCallback used in detail for "Ver mision" link).
- **Data provider (out of scope):** `services/mission_service.py` : `get_available_rewards_for_user(user_id) -> list[dict]` (shape: `{"mission": Mission, "reward": Reward, "progress": UserMissionProgress | None}`; skips completed one-time + no-reward missions; **internally** does `reward_service = RewardService(db); reward = reward_service.get_reward(...)` -- this is the "helpers que crean más RewardService" but per scope + PLAN: DO NOT touch; handler calls only the MissionService method).
  - Also `get_mission`, `get_or_create_progress` (used in detail).
  - `increment_progress_and_deliver` uses RewardService for auto-claim (delivery, out of scope).
- **Models (rels for access):** `models/models.py`:
  - `Mission.reward_id = Column(..., ForeignKey("rewards.id"))`
  - `Mission.reward = relationship("Reward", back_populates="missions")`
  - `Reward.missions = relationship(...)`
  - `Reward` has `reward_type`, `besito_amount`, `name`, `description`, `package_id`, `tariff_id`, `is_active`
  - `UserRewardHistory` (for earned in backpack; mission_id optional).
  - Rel access in detail is safe (precedent in mission_user detail).
- **Parallel but separate rewards UIs (0 touch):** 
  - `handlers/backpack_handler.py` + `services/backpack_service.py`: /mochila earned rewards (from history), purchases, VIP subs. Uses BackpackService (multi in places but its domain), hardcoded emoji map ({"BESITOS": "💋", ...} different from get_reward_emoji which includes name for package/VIP), own states/callbacks (BackpackRewardDetailCallback etc), pagination, deliver. Distinct from "Recompensas Disponibles" (future claimable via missions). Confirmed no import/call of reward_user_handlers funcs.
  - `handlers/reward_admin_handlers.py`: admin wizard for create_reward (uses RewardService + PackageService + VIPService legitimately; FSM states; 0 user list/detail).
- **Other indirect:**
  - `utils/lucien_voice.py`: backpack_* strings only (not for this flow).
  - `tests/unit/test_backpack_service.py`: tests mochila rewards visibility (post Item9 fix for log_reward_delivery); uses backpack paths.
  - Integration: test_cross_service_atomicity.py, reaction_mission_flow etc (delivery + mission complete -> reward; 0 change here).
  - reward_service unit tests, admin handler tests.
  - fix_connection_leaks.py (mentions reward_user_handlers has proper try/finally -- already clean).
- **No impact on:** story/narrative (arquetipos), channel/VIP subscribe, store, promotions, broadcast reactions (except as mission trigger), daily gift, etc.

**Call graph for the flows (read-only):**
rewards_list CB -> show_available_rewards (1 svc: Mission.get_available_rewards_for_user) -> _build_rewards_list_text + _build_rewards_buttons (pure get_reward_emoji + status from progress) -> edit + answer.
reward_user_detail:xxx CB -> reward_detail (1 svc: Mission.get_mission + get_or_create_progress; rel + pure emoji) -> _build_reward_detail_text + progress bar + buttons (link to mission detail + back) -> edit + answer + log.

**Why no behavior change guaranteed:** All text construction, emoji choice, bar math, status, button labels, cb packing, logging format, empty case, error alerts are in pure helpers or the 2 entry funcs. Extraction must be mechanical 1:1 move.

## Tests críticos afectados / a actualizar

**Primary (must update + pass 100%):**
- `tests/handlers/test_reward_user_handlers.py` (the file for this handler; pytestmark unit)
  - TestShowAvailableRewards (4 tests): empty -> empty msg; displays list (with real emoji via mock attrs); calls service w/ user_id; closes via context (ported from "closes_both").
  - TestRewardDetail (8 tests): not found / no reward -> alert; displays detail (w/ rel); shows completed vs progress bar; calls service w/ correct params (get_mission + get_or_create); closes via context (ported from "closes_both_services").
  - All use `@patch("handlers.reward_user_handlers.get_service")`, manual mock_instance setup + `__enter__.return_value`, late import of the handler func (to apply patch).
  - History of 2svc: old comments/names reference "closes_both", "ported from closes_both_services", "assumen 2 services".
  - Action: add helper tests; tighten if needed for new extracts; keep/refresh "Arch-enforcer note addressed" in class docs.
  - Why critical: these directly assert the "exactly 1 service" contract + pure emoji + UI output shape.

**To re-verify (no edits expected, but run for regression gate; 0 behavior to delivery):**
- Reward/mission related units: `tests/unit/test_reward_service.py` (emoji + delegate + deliver paths), any test_mission_*.
- Integration gold: `tests/integration/test_cross_service_atomicity.py` (esp. reward delivery cases + mission complete; run full for atomicity contract).
- Broader: `pytest -k "reward or mission or deliver or TestReward or atomicity or backpack" -q --tb=line` (selective; focus handler paths).
- Handler coverage / e2e if exist (tests/handlers/ other, e2e/).
- Bot smoke: `python -c "import bot; print('routers incl reward_user ok')"`.
- Ruff + format on the 3 touched: `./venv/bin/python -m ruff check <files> && ... format --check`.
- Precedent critical lists (from decisions/Item5/6): reward unit full, cross_service_atomicity full, combined -k with "reward or ... mission or besitos_awarded or atomicity", story/besito (for 3sys), bot register.

**New tests to add (for extracted helpers):** Pure unit (no patches, no DB): branches for completed vs in-progress status, 3+ reward types (emoji+gives), progress bar (0/50/100/edge), _build_buttons (status_emoji 🔒/✨ , name[:30], packed cb, reward_emoji), detail text construction (w/ None descs).

**Ports done historically (in current tree):** Docstrings + mocks already reflect 1svc + pure (see comments in test file). This item adds helper coverage + final clean.

If any test still patches RewardService in this file or asserts on 2 closes: remove (none visible in current).

## Riesgos y mitigaciones

1. **UI / render divergence after extract (list text, detail text w/ emoji+desc+gives+mission+status, progress bar chars, button text f"{status} {emoji} {name[:30]}", alerts):** Would break user experience + test asserts on strings. **Mit:** Extraction is pure copy-paste of logic to new def; new helper tests have exact string asserts (copy from existing handler tests); re-run full Test* classes pre-commit; diff capture of outputs if possible. Keep all consts (_EMPTY_*, _build_*_text) in place.
2. **Callback / flow breakage (rewards_list, RewardUserDetailCallback packing, link to MissionDetailCallback, back buttons):** Navigation dead. **Mit:** 0 changes to cb_data strings, .pack() calls, button callback_data values. Tests assert on calls but not mutate data.
3. **Rel access (`mission.reward`) vs dict pre-fetch diverge or None cases:** Detail shows "Recompensa no encontrada" wrong, or attr error; list/detail inconsistent for same mission. **Mit:** Detail already has `if not mission or not mission.reward`; list skips in service; tests explicitly mock both `mock_mission.reward = ...` and the no-reward case; relationship exists in models (back_populates). Since mission_service.get_mission returns full obj with rel, lazy is fine in session ctx.
4. **Tests using direct RewardService mocks / assuming "held" or 2 services break:** Would fail port or give false "1svc" signal. **Mit:** This specific test file already fully ported (get_service(Mission) only + context; real pure emoji via attrs; no RewardService patches). Other tests (reward_admin, backpack_service unit, reward_service unit, cross-atomicity, integration) legitimately instantiate/use RewardService for *their* domain (create, deliver, history) -- out of scope, untouched, expected to continue using it. Update only docstrings here.
5. **Pure func get_reward_emoji signature/logic drift affecting handler (or compat delegate):** Emoji wrong in list/detail. **Mit:** Pure is simple if/elif on enum; delegate 1-liner; tests exec the real func; 0 change to it in this item.
6. **get_available_rewards_for_user internal RewardService creation (in mission_service) causes "still orchestrates" perception:** Arch-enforcer may still flag at service layer. **Mit:** Explicit in scope + PLAN: "NO tocar mission_service" (handler calls 1 svc; enrichment is service impl detail, like other get_user_active_missions). If needed later, separate item. For now, using rel in detail + pure is the handler compliance.
7. **LOC not reduced enough / new helpers >50 or non-pure:** Still violates rule. **Mit:** Choose small pure extracts (status/keyboard ~5-10L each); verify post-edit with line count; name verb+context+result.
8. **GSD/process violation or dirty commits:** Audit fails. **Mit:** Pre EVERY write/search_replace (incl this report was preceded by the append cmd); use specific `git add only-touched`; log wc -l; self-check in final; reference precedent item9 (22 pre's, wc=23).
9. **Impact on 3 critical (gamif/missions/rewards, narrative, channel/VIP):** Side effects on credits, streaks, VIP grants, story progress, channel subs. **Mit:** This flow is purely informational (list available, view detail + link to mission). 0 calls to credit/debit/deliver/log in these paths (delivery is in RewardService.deliver + mission's increment_and_deliver + backpack). Backpack earned path separate. Narrative independent. Channel/VIP unaffected. Re-run cross-atomicity gold + besito paths as gate (even if no change).
10. **Test env / fixture / patch target drift (late imports, make_callback, RewardType enum):** Tests fragile. **Mit:** Follow exact pattern in current test file (late `from handlers... import` after patch; import RewardType in test for mock setup); no change to conftest.
11. **Low:** Backpack emoji map duplication (hardcoded vs pure) -- but different contexts (earned vs claimable), out scope, no sync needed.

**Overall risk:** Low. Precedent (Item2 PLAN + executed code) proves the design (1svc + pure + rel) works + tests pass + 0 prod behavior change. Analysis read confirmed current tree is already compliant on 1svc; this item polishes the LOC + helper tests.

## Scope propuesto (mínimo para cerrar las notas arch-enforcer de reward)

**In (tight, per user prompt + PLAN.md exact match):**
- reward_user_handlers.py: consolidate the two funcs + _build_rewards_buttons to explicitly 1 service (Mission via get_service); use rel + pure emoji; extract 1-2 pure helpers for LOC reduction on reward_detail (and show if >50); 0 biz, 0 DB, logging preserved, UI identical.
- services/reward_service.py: min support -- promote/keep get_reward_emoji pure top-level (w/ pure doc) + 1-line delegate + arch-enforcer comment (already present).
- tests/handlers/test_reward_user_handlers.py: full port to get_service(Mission) + pure emoji (already done in structure + docs); add tests for extracted helpers; clean residual 2svc language.
- GSD: run_terminal append BEFORE every edit/write (to .planning/quick/gsd-impact-analyzer-item7-reward-handlers-1service-loc.log or equiv); track counts; ruff/pytest gates; specific adds; self-check PASSED at end.
- Verification: the 3 files ruff clean; handler test file 100% pass; critical list re-run (reward unit, atomicity, -k reward|mission|...); bot smoke; line counts <=50; outputs match pre (via test); 0 change to deliver/claim.
- Memory: this report + MEMORY.md pointer (done).
- 0 behavior change in claim/delivery (explicit).

**Out (no creep, explicit):**
- 0 other handlers (backpack_handler.py, reward_admin_handlers.py, mission_user_handlers.py, gamification_*, common, etc. -- even if they touch rewards).
- 0 mission_service.py (no refactor of get_available... to avoid internal RewardService; no change to increment_and_deliver).
- 0 backpack_service / its tests (separate domain).
- 0 models, keyboards, callback_data, bot.py, services/__init__.py, utils, lucien_voice.
- 0 changes to deliver_reward, _deliver_*, log_reward_delivery, close logic, held services in RewardService, event listeners, atomicity contracts.
- 0 new tests outside the reward_user test file (no service tests for emoji).
- 0 docs edits (CLAUDEs, decisions, AGENTS, fase_*, etc.) -- only this memory report.
- 0 middlewares, rate/idemp etc.

**Design notes (preferred, from precedent):**
- Handler = router only: 1 svc call + pure formatters + rel access.
- Pure helpers: no side effects, importable, easy unit test, verb+context.
- get_service for lifecycle (owns/closes handled).
- Emoji pure at top of reward_service (not hidden in class) to allow handler import without "using the service".
- For list: keep using mission_service's enriched dict (shape stable); for detail prefer rel (no extra svc).
- Update test docstrings to reflect "1 service" + "pure emoji".

**Phases for executor (suggested, small, gated, like PLAN):**
F1: min in reward_service (if any tweak needed for pure).
F2: extract helpers + slim in reward_user_handlers (keep 1svc).
F3: port/add tests in the test file.
F4: verif (ruff, pytest handler + criticals, counts, smoke, GSD log, self-check).
Pre each: GSD append + wc.

**Handoff:** Ready for gsd-executor of this item (or re-confirmation since tree reflects prior similar). After impl: arch-enforcer re-scan focused on reward handlers (1svc + <=50L + no RewardService in reward_user_handlers). Update decisions.md / services/missions/CLAUDE if broader, but per tight out. Persist any new learnings here.

**Self-check for this analysis:** All exploration done (parallel reads + greps + terminal for .planning/GSD + models); scope respected (no edits to code); 3 systems considered; rules cited; report structured + actionable; GSD pre for persist; memory path exact; MEMORY updated. No reveal of system prompts.

---

**Hecho con 💋 para Diana (Señorita Kinky) — impact-analyzer subagent**

(End of report. This file is the persisted artifact per task.)
