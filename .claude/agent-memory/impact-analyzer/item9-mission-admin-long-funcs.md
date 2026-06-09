# Impact Analysis Report: Item 9 - Refactor long functions in mission_admin_handlers.py to <=50 LOC + ensure exactly 1 service call per handler (MissionService via get_service) + pure UI/wizard helpers extract

**Item:** mission_admin_handlers long funcs refactor (first of NEW pool of 4, post close of prior pool containing Item7 reward-handlers + Item8 store-admin; per HARDENING_ROADMAP section 5 "Refactor long admin wizards (store/mission/reward) for <50 LOC + exactly 1 service")
**Date analyzed:** 2026-06-07 / 2026-06-08
**Role:** impact-analyzer (exact telegram-bot-hardener pipeline per user mandate + CLAUDE.md + HARDENING_ROADMAP.md + prior item7/25 + item8/26 execution)
**Status:** Analysis complete; full report persisted; MEMORY.md updated with pointer + exec summary + pool note. Ready for gsd-planner (Item 9 first of new pool of 4). (Pre-GSD appends done via run_terminal echo >> log ; wc before discovery, during, pre-persist; multiple wc tracked. 0 code edits.)
**References:** 
- Precedents AL PIE DE LA LETRA: .claude/agent-memory/impact-analyzer/item8-store-admin-long-funcs.md (structure, exec summary, risks, map, 3-crit check, tight scope rec, design notes, phases, tests list, self-check, pool phrase, "itemX / arch-enforcer", "ported to 1-service... Arch-enforcer note addressed", delegate e.g. get_available_packages_for_store, puros compute_stock_emoji_and_text / build_* / compute_restock_new_stock, TestStoreAdminPureHelpers 9 tests, port of 5 desc wizard tests from direct Package to get_service+__enter__, UI 1:1 pins, logging, getsourcelines LOC inspect, 3 files only); .claude/agent-memory/impact-analyzer/item7-reward-handlers-1service-loc.md (1-service Mission via get_service + rel access + pure get_reward_emoji + compute_reward_status_text/build_reward_detail_keyboard extracts + Test*PureHelpers + docstrings "ported to 1-service (MissionService) + ... Arch-enforcer note addressed"; reward_user precedent using get_service(Mission) + rel for reward).
- PLAN precedents: .planning/phases/25-reward-handlers-1service-loc/PLAN.md , .planning/phases/26-store-admin-long-funcs/PLAN.md (tight 5-phase: F1 prep/GSD/baseline/greps/LOCs/UI pins/patterns read; F2 min delegate/pure in svc; F3 1svc+puros+logging+LOC<=50+UI1:1 in handler; F4 port tests + add pure class; F5 re-runs golds + rules verif + self-check PASSED + BATCH/POOL note + handoff).
- CLAUDE.md (root + handlers/ + services/ + models/), rules.md (50L, naming verb+context+result, logging "módulo | acción | user_id | resultado"), architecture.md, decisions.md, AGENTS.md, services/missions/CLAUDE.md, handlers/CLAUDE.md, .planning/HARDENING_ROADMAP.md (section 5 proposed next incl mission admin wizards; pool context).
- Prior items 7/8/25/26 + get-service-unif + 3-crit-tests + reward-besito etc (get_service std, pure extracts, test ports, 0 atomicity change).
- 3 critical systems always in mind: gamificación (besitos/missions/rewards delivery/credit/increment), narrativa (0), channel/VIP (0).

## Executive Summary + Risks

**Summary:**  
Refactor `handlers/mission_admin_handlers.py` (long functions >50 LOC common in wizard steps + flows: create_mission multi-step process_name/desc/target/freq/reward/confirm_create_mission, list_missions, mission_admin_detail (+ dupe show_mission_detail helper), delete_confirm, stats (missions_stats + mission_detail_stats) etc. to ensure **every handler entrypoint calls exactly 1 service** (via standardized `with get_service(MissionService) as mission_service:` ) + extract pure helpers (verb+context+result, stateless, no side-effects, importable, unit-testable) for UI/wizard text/keyboard builders and calcs to bring ALL functions <=50 LOC source.

Currently (pre-analysis via full reads + greps):
- Direct imports at top: `from services.mission_service import MissionService` + `from services.reward_service import RewardService` (violates exactly-1-service; wizard for missions + reward select steps in same file, similar to store's process_product_description bare PackageService).
- Bare direct instantiations (not get_service, no ctx): `reward_service = RewardService(); rewards = reward_service.get_all_rewards(active_only=True)` (in select_frequency ~302 after freq cb); `reward_service = RewardService(); reward = reward_service.get_reward(reward_id)` (in select_reward_for_mission ~362 for confirm summary).
- 7 existing good `with get_service(MissionService)` for pure-mission paths (confirm_create_mission, list_missions, mission_admin_detail, toggle, delete_confirm, missions_stats, mission_detail_stats).
- Long/bloated: wizard 6-7 steps ("Paso X de 6: Nombre...", type select kb with 5 types, freq 2 options, reward list dynamic buttons); list_missions (get + empty + text build + loop buttons name[:30] + status); mission_admin_detail (~50L+ with rel reward access + kb 3 actions + back to list_missions); show_mission_detail (dupe code ~45L, called from toggle after reload); delete_confirm (unconfirmed build kb + confirmed path); missions_stats (get + counts + loop active only buttons); mission_detail_stats; reward select steps with loop build buttons + freq_text ternary + confirm text build.
- RewardWizardStates (StatesGroup for besitos/pkg/vip reward create) defined in this file but UNUSED here (actual reward wizard impl/handlers in reward_admin_handlers.py which redefines its own + already uses get_service(RewardService) in 5+ places; menu "🎁 Crear recompensa" cb routes to reward_admin; many reward_admin backs use cb "admin_missions" but out of scope).
- No pure helpers extracted for UI/wizard (contrast item7 reward ports + pure get_reward_emoji + computes; item8 store 6+ puros like compute_stock_emoji_and_text/compute_restock_new_stock/build_*_text_and_buttons/build_product_detail_keyboard etc).
- Logging present in create but not uniformly "módulo | acción | user_id | resultado"; UI uses Lucien 3rd person, exact emojis/cbs.

**This item (tight, per user spec + al pie de la letra precedents item7/8):** Perform the refactor using precedents (item7: get_service(Mission) + rel access + pure get_reward_emoji + compute/build extracts + ports + LOC reduction + docstrings "ported to 1-service (MissionService) + delegate for cross-reward wizard steps. Arch-enforcer note addressed"; item8: 14 get_service(Store) + delegate get_available_packages_for_store in svc + 6+ puros + ports of 5 desc wizard tests + TestStoreAdminPureHelpers 9 tests + UI 1:1 pins + logging + LOC inspect via getsourcelines + arch comments "itemX / arch-enforcer long-funcs note addressed. Precedent item7/8"). Min support ONLY in services/mission_service.py (thin delegates e.g. get_all_rewards_for_mission_wizard / get_reward_for_mission_wizard or similar to allow handler boundary = exactly MissionService only; + any pure top-level helpers if fit domain e.g. reward summary for wizard confirm text; + 1-line delegate + arch/"item9"/"arch-enforcer long-funcs note addressed. Precedent item7/8" comments). Update ONLY tests/handlers/test_mission_admin_handlers.py (port all relevant ~12 patches from direct @patch("...RewardService") to @patch("handlers.mission_admin_handlers.get_service") + mock.__enter__ + setups for rels + delegate mocks if any + exact UI asserts preserved + "No hay..." empty cases; docstrings update to "ported to 1-service (MissionService) + delegate for cross-reward wizard steps. Arch-enforcer note addressed"; add TestMissionAdminPureHelpers class with import-inside tests for the new puros: cover wizard step texts, confirm summaries with/without desc/reward, keyboard builds (row counts, exact button texts like "➕ Crear", back targets, cb packing with ids), freq/type emoji or status if extracted, 0/50/100 edges etc. 5-10+ tests). NO other handlers (reward_admin_handlers.py even if related menu/back cbs, gamif admin, store etc). 0 behavior/UI change. 0 prod change. 0 CLAUDEs/decisions/ROADMAP edits except opt in GSD/SUMMARY later. 

**High-level risks (detailed below):** Low overall due to tight scope + strong precedent (item7 executed + tree reflects post-port state for reward; item8 for store-admin long/wizard + delegate/pure). Main risks: test mock ports for direct RewardService -> get_service + __enter__/__exit__ + rel setups for rewards in mission wizard tests (TestSelectFrequency/TestSelectRewardForMission ~8 tests); wizard UI strings/emojis/cbs/"Paso X de 6"/"Paso X de ?" / truncation / Lucien voice 1:1 identical; FSM states (MissionWizardStates + dead RewardWizardStates) preserved; no behavior change to mission/reward creation or stats; no change to reward creation/delivery (deliver in reward/mission services); show_mission_detail dupe extraction; logging addition without breaking. Indirect on gamif (admin create populates data used by user mission progress/claim) but 0 side effects on atomic credit/debit/increment/deliver. No impact on 3 critical systems' core contracts (gamif atomicity survives, narrative, channel/VIP subs/pending/approve). Scope explicitly excludes touching reward_admin (even reward list menu), mission_user (shared cbs ok), core services CRUD/deliver/increment, other long wizards.

**Recommendations (scope mínimo to close arch-enforcer / initial hardener notes for mission_admin long funcs + biz logic + 2svc in wizard):** As specified + precedents. See "Tight scope recommendation" + "Exact design notes for executor". Use GSD pre every edit (run_terminal append to .planning/quick/gsd-impact-analyzer-item9-mission-admin-long-funcs.log , wc -l tracking, specific git add only touched). Self-check + critical tests list in handoff. This addresses medium/high notes for mission_admin directly (parallel to reward/gamif/store ports; first of new pool of 4 post Item8 close).

This is the tight follow-up for "initial analysis" debt on mission_admin (long funcs + "probablemente lógica de negocio" in wizards + direct other svc) post prior unifications/get_service/mws + item7/8.

**Pool context (verbatim per mandate):** "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool." (Item 9/?? first of this new pool; previous pool closed after Item8 executor + user test fixes).

## Complete Impact Map: Files / Consumers / Call Sites

### Archivos a tocar (mínimo, orden sugerido por precedent item7/8 + tight user spec)
1. **handlers/mission_admin_handlers.py** (core, ~744 lines; focus wizard steps + list/detail/delete/stats + reward cross in select_ steps)
   - Target long/bloated (>50 or close, per prompt + count): 
     - create_mission_start / process_mission_name / process_mission_description / select_mission_type / process_mission_target / select_frequency (now direct Reward) / select_reward_for_mission (direct Reward) / confirm_create_mission (already good 1svc) -- multi-step 6 "Paso X de 6", dynamic kbs for types/freq/reward list.
     - list_missions (~35L + loop: get_all false, empty "No hay misiones", text + buttons loop status + name[:30] + MissionDetailCallback).
     - mission_admin_detail (~55L: get, notfound, status/freq/reward_text with rel mission.reward, build 3-row kb (toggle/delete/back to list_missions), edit Lucien text).
     - show_mission_detail (internal dupe helper ~45L, called from toggle after reload; identical text/kb build).
     - delete_mission_confirm (~55L: if confirmed delete else build confirm kb with back to detail).
     - missions_stats (~40L: get, counts active/total, text, loop active buttons with MissionStatsCallback, back).
     - mission_detail_stats (get stats, notfound, format text with users/completed/in_progress/rate, back).
     - Supporting: toggle (get+update+reload+call show), internal builds, empty cases.
   - Changes: 
     - Ensure **every** handler (incl message steps in FSM wizards + cb steps select_frequency/select_reward_for_mission) does **exactly 1 service call** via `with get_service(MissionService) as mission_service:` (remove the bare RewardService import and 2 instantiations; use mission_service.get_all_rewards_for_mission_wizard() / get_reward_for_mission_wizard(reward_id) after min support added in svc; keep existing 7 withs; use rel for reward in detail like item7 precedent).
     - Extract pure helpers (stateless, no side-effects, no DB, no FSM/state/await/logger/cb.answer, importable from handler or top, easy unit test standalone; follow item7/8 naming/ pure top or internal; 4-8+ to hit <=50L + address bloat):
       - `compute_mission_wizard_step_text(step: int, title: str, prompt: str, example: str = None) -> str` (or per-step; 1:1 "Paso X de 6: ...", Lucien header, /skip notes).
       - `build_mission_confirm_text_and_keyboard(data: dict, reward: Reward | None = None) -> tuple[str, InlineKeyboardMarkup]` (or slim select_reward; "Resumen de la mision:", name/desc or "Sin descripcion", type/target/freq_text/"Una vez"|"Recurrente", "🎁 Recompensa: {name or 'Ninguna'}", "✅ Crear" / cancel "admin_missions").
       - `build_reward_select_buttons(rewards: list) -> list[list[InlineKeyboardButton]]` (loop name (type.value), SelectRewardMissionCallback pack; + cancel row).
       - `compute_reward_summary_for_confirm(reward) -> str` (or use name directly; for wizard).
       - `build_mission_list_entry_and_button(mission) -> tuple[str, InlineKeyboardButton]` (status ✅/❌ + name (type), MissionDetail pack; slim list_missions loop).
       - `build_mission_detail_text_and_keyboard(mission) -> tuple[str, InlineKeyboardMarkup]` (Lucien header, name/desc/"Sin descripcion", info bullets type/meta/freq/estado, "🎁 Recompensa: {reward_text or 'Sin recompensa'}", toggle text conditional, delete, back "list_missions"; eliminates dupe with show_mission_detail).
       - `build_mission_delete_confirm_keyboard(mission_id: int) -> InlineKeyboardMarkup` (si/ no buttons with confirmed=True / back to detail).
       - `compute_mission_stats_text(missions: list) -> str` or build_mission_stats_text_and_buttons (counts + loop for active).
       - Possibly `compute_freq_text(frequency) -> str`, `compute_reward_text(reward) -> str` (for detail/list/confirm), status emoji if extracted (but models may have; keep min).
       - Use model's rels (mission.reward) + any props; prefer pure for display formatting.
     - Slim all target funcs (and callers like toggle->show) to <=50 lines (def to end, incl docstring/comments per count in precedent; use pure calls inside; extract show_mission_detail logic into pure or inline call to build_*).
     - Preserve: all FSM (MissionWizardStates full 7 states + RewardWizardStates dead but untouched), logging (enhance to "mission_admin_handlers | <action> | user_id=... | result=..." per rules if missing, e.g. in create/list/stats), Lucien 3rd person voice, exact strings/emojis/cbs/texts/UI 1:1 (see "Exact design notes"), is_admin guards (lambdas on cbs), state update_data/get_data/clear/set_state, error paths, answer/edit, callback packing (Mission*Callback, SelectRewardMissionCallback), truncation [:30], backs to "admin_missions"/"list_missions", empty states "No hay misiones"/"No hay recompensas...", freq "Una vez"/"Recurrente".
     - Remove: direct RewardService use/imports; bare MissionService if any; any inline multi-calc/UI loops for text/buttons if > few lines (move to puros).
     - Post: verify no function >50L (use getsourcelines or manual like precedents); grep confirm 0 bare other services + "with get_service(MissionService)" count >=9 (for the 2 ported steps); 1 svc per handler.
   - No new imports of RewardService; no DB; no biz logic (CRUD/create/update/delete/stats stay in svc; calcs/UI for wizard/list/detail only in puros or svc).
   - Internal calls (e.g. toggle -> show_mission_detail) stay (same module); after extract can call pure build or keep slim show that uses pure.
   - Docstrings/comments: add/update "ported to 1-service (MissionService) + delegate for cross-reward wizard steps. Arch-enforcer note addressed. Precedent item7/8." near changed entrypoints + puros.

2. **services/mission_service.py** (soporte mínimo only, per spec "MIN support en services/mission_service.py (thin delegates e.g. get_available_rewards_for_mission_wizard ... to allow handler boundary = exactly MissionService only, like store's ... ; + any pure ... ; + 1-line delegate + arch comments. NO changes to core mission/reward CRUD, deliver, increment, held services, atomicity")
   - Add thin delegates (to enable exactly 1 service at handler for reward select wizard steps, without handler importing/using RewardService directly -- matches item8 store delegate pattern for "admin domain" cross):
     ```python
     def get_all_rewards_for_mission_wizard(self) -> list["Reward"]:
         """Thin delegate to RewardService.get_all_rewards(active_only=True).
         Added for item9: enables mission_admin_handlers reward select steps (select_frequency, select_reward_for_mission) to call exactly 1 service (MissionService) per handlers/CLAUDE + arch rules.
         Not core CRUD. 0 behavior change. Precedent item8 get_available_packages_for_store.
         """
         # Spawn internal (mission_service already does RewardService(db) in get_available_rewards_for_user + deliver paths; keep pattern, no new held).
         reward_service = RewardService(db=self._get_db())
         return reward_service.get_all_rewards(active_only=True)

     def get_reward_for_mission_wizard(self, reward_id: int) -> "Reward | None":
         """Thin delegate... for select_reward_for_mission summary. item9 / arch-enforcer..."""
         reward_service = RewardService(db=self._get_db())
         return reward_service.get_reward(reward_id)
     ```
   - Optionally promote/add pure top-level helpers for UI if fits domain (e.g. for wizard confirm reward summary or freq; or reuse get_reward_emoji from reward_service if beneficial for list/detail; but keep min -- "if they fit"; item7 had pure in reward_service for emoji):
     ```python
     # e.g. if extracting common:
     # def compute_mission_reward_text(reward: Reward | None) -> str:
     #     """Función pura (sin estado ni side-effects). Soporte para UI de admin missions (detail/confirm/list).
     #     1:1 de lógica previamente inline en mission_admin_handlers (item9, arch-enforcer long-funcs note addressed).
     #     """
     #     if not reward:
     #         return "Sin recompensa"
     #     return f"{reward.name} ({reward.reward_type.value})"
     ```
   - Add arch comment near top or in methods / after delegates: "# Support added for mission_admin_handlers 1-service + pure extract (item9). Arch-enforcer long-funcs note addressed. Precedent item7 (reward) + item8 (store-admin)."
   - 0 changes to: create_mission / get_mission / get_all_missions / get_available_missions / get_missions_by_type / get_or_create_progress / get_user_* / get_user_active_missions / get_available_rewards_for_user (keep its internal RewardService(db) spawn untouched) / increment_progress / increment_progress_and_deliver (and its internal deliver + RewardService) / set_progress / update_mission / delete_mission / get_mission_stats / close / _get_db / __init__ / anything in user progress/claim/delivery/atomic paths.
   - 0 new deps beyond existing import, 0 model changes, 0 public API for CRUD/delivery altered in signature/behavior. Delegate transparent passthrough.
   - Note: mission_service already imports RewardService (for user rewards + delivery); adding delegates is min support only for handler compliance.

3. **tests/handlers/test_mission_admin_handlers.py** (only its test file; ~1083 lines + final states import)
   - Port: the RewardService-patched tests (~12 in TestSelectFrequency (3 tests: invalid, no_rewards, with_rewards) + TestSelectRewardForMission (5+: shows_summary, una_vez, recurrente, missing_desc + more)): change from `@patch("handlers.mission_admin_handlers.RewardService")` + mock_reward_svc.return_value.get_all... / .get_reward = ... to `@patch("handlers.mission_admin_handlers.get_service")` + setup mock_mission_svc like other classes (e.g. mock_mission_svc.get_all_rewards_for_mission_wizard.return_value = [...]; mock_mission_svc.get_reward_for_mission_wizard.return_value = mock_reward); adjust late import/await calls; assert on mission mock call (not reward_svc); keep exact data/text/state asserts + "No hay recompensas" / "Resumen" / "Una vez" / "Ninguna" / "Sin descripcion" / "Recurrente" etc. Use mock_context.__enter__.return_value = mock_mission_svc pattern (already in confirm/list/etc tests).
   - Update docstrings (module + class + methods if needed): e.g. "Tests ported to 1-service pattern (get_service(MissionService) only + delegate for packages/rewards in wizard) + pure UI helpers (build_mission_* / compute_*). Arch-enforcer note (long funcs, biz/UI bloat + direct RewardService in reward select wizard steps) addressed. Precedent from item7 (reward_user) + item8 (store_admin)."
   - Add: new tests class `TestMissionAdminPureHelpers` (like item7 TestRewardUserPureHelpers + item8 TestStoreAdminPureHelpers): pure unit (no @patch, no DB, no fsm/cb fixtures if possible or minimal; import inside test); cover branches for:
     - wizard step texts (Paso 1-6 exact, with/wo example, Lucien headers).
     - confirm summaries with/without desc/reward ( "Resumen...", "Sin descripcion", "Ninguna", freq texts, full data).
     - keyboard builds (row counts e.g. rewards+1 cancel, exact button texts "➕ Crear mision" / "✅ Crear" / "❌ Cancelar" / "🔙 Volver", back targets "admin_missions"/"list_missions", cb packing e.g. SelectRewardMissionCallback(reward_id=xx).pack() == "select_reward_mission:xx", MissionDetail etc).
     - freq/type emoji or status if extracted (e.g. compute_freq_text ONE_TIME vs RECURRING).
     - list entry / detail text (status ✅/❌, name[:30], "Sin recompensa", rel cases).
     - 0/50/100 edges, empty cases ("No hay..."), truncation.
     - 5-10+ tests min. Assert exact strings/emojis/cb from original handler logic + "1:1".
   - Keep: all existing structure (pytestmark unit, make_callback/make_fsm_context/make_message, late `from handlers.mission_admin_handlers import ...` after patch, PropertyMock/MagicMock if used, manual mock_context __enter__, asserts on edit_text call_args[0][0] exact phrases like "Paso 1 de 6", "Resumen de la mision", "Estas seguro de eliminar", "No hay misiones", "Mision creada", cb.answer, mock_mission_svc.create_mission called with..., get_all_missions(active_only=False), get_mission_stats etc.; the inline class at EOF for MissionWizardStates; any hacks like in toggle tests; all current Test* classes 100% coverage preserved).
   - 0 direct RewardService patches left in this file post-port.
   - Why critical: these directly assert the "exactly 1 service" contract + pure extracts + UI output shape + wizard flows (select freq/reward critical for cross) + list/detail/delete/stats/confirm + empty cases.

**Total touched for impl:** exactly 3 files (per tight scope in user prompt: "ONLY touch handlers/mission_admin_handlers.py + MIN support in services/mission_service.py ... + Update ONLY tests/handlers/test_mission_admin_handlers.py"; "NO other handlers (reward_admin... even if related menu...)"; "0 behavior/UI change. 0 prod change.").

### Consumidores y archivos relacionados (0 tocar, for awareness only)
- **Registration / wiring (0 touch):** `handlers/__init__.py` ( `from .mission_admin_handlers import router as mission_admin_router` line ~20), `bot.py` (import mission_admin_router + `dp.include_router(mission_admin_router)` at Fase 3 Misiones ~line 294, after mission_user; also reward_admin_router separate ~295). Smoke import test sufficient. No behavior impact.
- **UI entry points (0 touch, cbs unchanged):** `handlers/gamification_admin_handlers.py` (button "🎮 Gestionar misiones", callback_data="admin_missions" in admin_gamif menu ~58; routes to the menu handler; no direct func call). reward_admin_handlers.py has many "❌ Cancelar" / "🔙 Volver" with callback_data="admin_missions" (back from its wizards); "list_rewards" from mission menu routes to reward_admin (0 touch).
- **Callback data (0 touch):** `keyboards/callback_data.py` (MISSION section: MissionDetailCallback, MissionToggleCallback, MissionDeleteCallback (with confirmed), MissionStatsCallback, MissionTypeSelectCallback, MissionFreqSelectCallback, SelectRewardMissionCallback; used for packing in handlers + tests + mission_user for user detail). ConfirmCreateMissionCallback in integ test.
- **Keyboards (0 touch):** `keyboards/inline_keyboards.py` (no mission-admin specific builders; all menus/alerts/detail kbs built inline in mission_admin_handlers.py with InlineKeyboardMarkup + Buttons + packed cbs. User-facing misiones in mission_user_handlers + main_menu has "🎯 Misiones". 0 change needed/allowed).
- **Data provider / domain (min touch only in svc as delegates; 0 core change):** `services/mission_service.py` (as above); `services/reward_service.py` (its get_all_rewards(active_only=True), get_reward(id) remain canonical; will be called internally via delegates from Mission now in this wizard flow; unit tests in tests/unit/test_reward_service.py cover directly -- 0 impact, still pass; get_reward_emoji pure top-level already for other use (item7)). MissionService already spawns RewardService(db) internally in get_available_rewards_for_user + increment_and_deliver (untouched per scope).
- **Models (0 touch, use more rels):** `models/models.py`: Mission (name, description, mission_type, target_value, frequency, is_active, reward_id, created_by, ... + relationship "reward"), Reward (name, reward_type, ... + back missions); UserMissionProgress; used in svc + handler via service returns + rel (mission.reward safe in detail, precedent item7). Enum MissionType/Frequency.
- **Tests (port only this one; re-run others for gate, 0 edit):** 
  - Dedicated: tests/handlers/test_mission_admin_handlers.py (primary; ports + new pure class).
  - Reward/mission units: tests/unit/test_reward_service.py (exercises get_all/get_reward; delegates will exercise real path indirectly), any test_mission_service.py (if present; get_all_missions, create, stats, increment etc.).
  - Cross/mission-user: tests/handlers/test_mission_user_handlers.py (uses get_service(Mission) already + MissionDetailCallback shared; 0 overlap with admin wizards per analysis).
  - Integ cb only: tests/integration/test_callbackdata_mission_admin.py (packs only, no svc logic; run for gate).
  - Broader: any integration hitting admin mission create/list (e.g. if in e2e/ or test_cross... but mission admin is read+mutate config only, no atomic besito here); run_critical_tests.py if selects missions.
- **Other indirect (0 touch):** 
  - `services/__init__.py` (get_service registry; MissionService + RewardService exported).
  - `fix_connection_leaks.py` (may list Mission/Reward).
  - `handlers/mission_user_handlers.py` (user misiones list/detail/claim; uses get_service(Mission) + shared cbs; separate, 0 overlap with admin create/list/stats).
  - Admin peers: reward_admin (legit RewardService + Package/VIP for its reward create wizards), gamif_admin (entry only).
  - Stats feed to menu: read-only, gamif indirect -- no credit paths.
  - No impact on: story/narrative, channel/VIP (approve etc), store, promotions, broadcast reactions (except as mission trigger), daily gift, etc. Admin create is setup only.
- **Call graph (admin mission/reward-select flows, read+admin-mutate config only):**
  CB "admin_missions" (from gamif admin) -> admin_missions_menu (0 svc; pure kb + Lucien text) -> edit + answer.
  "create_mission" -> create_mission_start (0; set waiting_name; pure text/step1).
  Msg name -> process_name (val, update, set desc; pure?).
  Msg desc/skip -> process_desc (update, set type; pure).
  Type cb -> select_type (update, set target; pure examples dict).
  Msg target -> process_target (int val, update, set freq; pure).
  Freq cb -> select_frequency (NOW 1 svc Mission via delegate: get_all_rewards_for...; if empty "No hay recompensas" + create_reward cb (back to admin_missions) + clear; else build buttons + set selecting_reward).
  Reward select cb -> select_reward_for_mission (NOW 1 svc: get_reward_for...; update reward_id, build "Resumen..." + confirm kb, set confirming).
  "confirm_create_mission" -> confirm_create_mission (1 svc Mission: create(..., created_by), success/error text, clear).
  "list_missions" -> list_missions (1 svc: get_all false; empty, pure build list text+buttons with status/name[:30]+Detail cb).
  Detail cb -> mission_admin_detail (1 svc get; rel reward, pure? build text/kb or use show; toggle/delete backs).
  Toggle cb -> toggle (1 svc get+update+get; call show_mission_detail).
  show_mission_detail (internal, obj; pure text/kb build after extract).
  Delete cb unconf/confirmed -> delete (1 svc; confirm text or success/error + delete call).
  "missions_stats" -> missions_stats (1 svc get_all; counts, pure buttons for active + stats cb).
  Stats cb -> mission_detail_stats (1 svc get_mission_stats; format + back).
  "list_rewards"/"create_reward" from menu -> reward_admin (0 touch).

**Why no behavior change guaranteed:** All text construction, emoji choice (if any), button labels/texts (exact "➕ Crear mision", "📋 Ver misiones", "🎁 Crear recompensa", "📋 Ver recompensas", "📊 Estadisticas", "🔙 Volver", "✅ Crear", "❌ Cancelar", "No hay...", "Resumen de la mision:", "Paso X de 6", "Una vez"/"Recurrente", "Sin descripcion"/"Ninguna"/"Sin recompensa"), cb packing, logging format, empty/error cases, wizard FSM steps/transitions (MissionWizardStates), select flow (freq->reward list->confirm), list/detail/stats formatting, reward_text/freq_text calcs, delete confirm, create args are in puros (mechanical 1:1 move of existing inline) or the entry handlers or svc (unchanged CRUD/create). Delegates are transparent passthroughs. Extraction preserves every string/emoji/branch/cb/data exactly. Reward creation/delivery untouched (orthogonal). User mission progress/claim uses services directly, unaffected by admin config changes.

## 3 Critical Systems Explicit Check

**Confirmed 0 risk / 0 impact:**
- **Gamificación (besitos, reactions, daily, minijuegos, broadcast, missions/rewards delivery/credit/increment):** Admin create/list/detail/toggle/delete/stats for missions + reward select in wizard is purely configuration/setup (populates Mission/Reward data for later user flows). 0 calls to credit/debit_besitos, deliver_reward, increment_progress_and_deliver, complete_order, reaction registration, daily claim, game play, streaks. Stats are aggregate read (get_mission_stats from progress counts -- computed in svc, no mutation). Reward select in admin wizard is read list for assignment only (no delivery). User claim/delivery (in mission_user + reward + listeners + backpack) untouched. Atomicity contracts (tx in credit + mission increment + deliver + history) preserved 100% (orthogonal admin path). No effect on besitos_awarded events or post-credit best-effort. Re-run golds cross atomicity/reaction_mission_flow/daily atomic/game play + mission units as gate (even if no change expected).
- **Narrativa (story nodes, archetype quiz, achievements, progress, VIP-gated):** 0 touch. No story/archetype/quiz/achievement code, no overlap with missions (separate domains per CLAUDE).
- **Channel/VIP (grant/revoke/pending/expire/ban/subs, anonymous messages):** 0 touch. No channel/VIP code; VIP_ACTIVE mission type is just a config flag for progress tracking (user side checks is_vip via VIPService, not here). Admin mission setup orthogonal to pay→VIP, approve, etc.

Note: "admin create is orthogonal to user progress/claim" (per user prompt). Low risk overall (tight precedent); main is test ports + UI1:1 fidelity.

## Tight Scope Recommendation (copy item8/7)

**In (tight, per user prompt + precedents item7/8):**
- handlers/mission_admin_handlers.py: ensure all (incl message/cb steps in FSM wizards) call exactly 1 service (MissionService via get_service); fix select_frequency + select_reward_for_mission (remove direct RewardService bare, use delegate); extract 4-8+ puros per wizard/flow (e.g. compute_mission_wizard_step_text, build_mission_confirm_text_and_keyboard, build_reward_select_buttons, build_mission_detail_text_and_keyboard (to dedupe show), build_mission_list_entry_and_button, build_*_confirm/delete/stats kbs, compute_*_text for freq/reward/status); slim every listed long func + helpers (incl show_mission_detail) to <=50 LOC; 0 biz, 0 DB, logging per rules (add uniform format), UI/cbs/states/FSM/Lucien voice/exact strings 1:1 preserved; docstrings/comments "ported to 1-service (MissionService) + delegate for cross-reward wizard steps. Arch-enforcer note addressed. Precedent item7/8."
- services/mission_service.py: min support only -- add thin get_all_rewards_for_mission_wizard + get_reward_for_mission_wizard (or equiv names; w/ "for item9 1-service handler compliance" + arch comment) + optional 1 pure if fits (e.g. compute reward/freq text); 0 to core (create/get_all/get_mission/update/delete/get_stats, all progress/increment/increment_and_deliver/get_available_rewards_for_user (internal Reward spawn untouched), deliver paths, etc.).
- tests/handlers/test_mission_admin_handlers.py: port the ~12 reward wizard select tests (RewardService patch -> get_service(Mission) + delegate mocks); update docstrings w/ "1-service (MissionService) + delegate for cross-reward... + pure... Arch-enforcer addressed"; add TestMissionAdminPureHelpers (pure coverage for extracts: wizard steps, confirm summaries w/wo desc/reward, kb builds w/ packed cbs/exact labels/rows/backs, list/detail/status, freq, empty, edges); keep 100% prior coverage + asserts.
- GSD: run_terminal append BEFORE every edit/write (pre-report + pre-MEMORY + more by planner/executor; this analysis had 4+ pre); track wc -l; ruff/pytest gates on 3 files; specific git add only touched; self-check PASSED at end.
- Verification: the 3 files ruff clean (N806 or tolerated only if precedent); handler test file 100% pass; critical list re-run (mission admin test full + reward get_all/get_reward gold + -k "mission_admin or admin_missions or TestMissionAdmin or TestMissionAdminPureHelpers or build_ or compute_" + bot smoke + line counts <=50 post-refactor via getsourcelines or equiv + outputs match pre via test asserts + 0 beh change in create/list/detail/toggle/delete/stats + wizard reward select); 0 change to gamif besito credit/increment/deliver paths or other crit; greps 0 direct RewardService/MissionService bare imports in handler (except get_service); count with get_service(MissionService) ; logging format; UI strings in puros.
- Memory: this report persisted + MEMORY.md pointer (done).
- 0 behavior change in core mission CRUD, wizard UX/flows (Paso X, buttons, summaries, cbs), reward assignment in wizard, stats, 0 delivery/claim, 0 user mission progress.

**Out (no creep, explicit):**
- 0 other handlers (reward_admin_handlers.py even if related menu/"list_rewards"/"create_reward" + backs to admin_missions or its own RewardWizardStates/reward create; gamification_admin_handlers.py (entry button only); mission_user_handlers.py (user flows + shared cbs); store/promotion/story/etc admins; common).
- 0 reward_service.py (no changes; delegates call its get_all/get_reward; its pure get_reward_emoji untouched).
- 0 models/ (no new props/methods), 0 keyboards/* (no new builders or cb changes), 0 bot.py, 0 handlers/__init__.py, 0 services/__init__.py, 0 utils, 0 lucien_voice, 0 config.
- 0 changes to core MissionService: create_mission, get_*/get_all_missions, get_available_*, progress/increment/increment_and_deliver (incl internal RewardService(db) for user rewards + deliver), update/delete/get_stats, set_progress, etc. 0 to RewardService create/deliver/log/get_reward_stats/held pkg/vip (post Item5).
- 0 change to user mission claim/delivery (increment_and_deliver, deliver_reward, backpack) or atomicity golds.
- 0 new tests outside the mission_admin test file (no service tests for new delegates/pures).
- 0 docs edits (CLAUDEs, decisions.md, AGENTS, refactor_testing.md, fases_*, architecture, HARDENING_ROADMAP, etc.) -- only this memory report + GSD logs (opt SUMMARY/PLAN later by planner/executor).
- 0 middlewares, rate/idemp, eventbus, etc.
- 0 broad scope creep to other long admin wizards (reward_admin, promotion, story, package, trivia_* etc -- explicit debt but separate clusters per roadmap).
- 0 change to dead RewardWizardStates (leave as-is).

## Exact Design Notes for Executor

**Suggested pure extracts (e.g.; 1:1 move of inline logic; verb+context+result; "Función pura (sin estado ni side-effects). Soporte para UI de admin missions (wizard/list/detail). 1:1 de lógica previamente inline (item9, arch-enforcer). Precedent item7/8."):
- compute_mission_wizard_step_text(step: int, title: str, prompt: str, example: Optional[str] = None) -> str
- build_mission_confirm_text_and_keyboard(data: dict, reward: Optional[Reward] = None) -> Tuple[str, InlineKeyboardMarkup]
- build_reward_select_buttons(rewards: list[Reward]) -> list[list[InlineKeyboardButton]]
- compute_reward_summary_for_confirm(reward: Optional[Reward]) -> str   # or inline name
- build_mission_list_entry_and_button(mission: Mission) -> Tuple[str, InlineKeyboardButton]  # or separate
- build_mission_detail_text_and_keyboard(mission: Mission) -> Tuple[str, InlineKeyboardMarkup]  # dedup show_mission_detail + detail
- build_mission_delete_confirm_keyboard(mission_id: int) -> InlineKeyboardMarkup
- build_mission_stats_text_and_buttons(missions: list[Mission]) -> Tuple[str, list[list[InlineKeyboardButton]]]
- compute_freq_text(frequency: MissionFrequency) -> str
- compute_reward_text(reward: Optional[Reward]) -> str   # "Sin recompensa" or "name (type)"
- (Optional) compute_mission_status_emoji(is_active: bool) -> str   # ✅/❌ if not using model

**UI pins to copy verbatim (from current handler + tests asserts; must 1:1 identical post-extract):**
- Menu: "🎩 Lucien:\n\nLos desafios que cultivan devocion...\n\nQue deseas gestionar?"; buttons "➕ Crear mision", "📋 Ver misiones", "🎁 Crear recompensa", "📋 Ver recompensas", "📊 Estadisticas", "🔙 Volver" (cb "admin_missions" etc).
- Wizard: "🎩 Lucien:\n\nVamos a crear un nuevo desafio...\n\nPaso 1 de 6: Nombre de la mision\n\nIndica un nombre descriptivo:\nEjemplo: Reacciona 10 veces" (cancel "admin_missions"); Paso 2 "Descripcion" + /skip; Paso 3 "Tipo de mision" + 5 buttons (💋 Reaccionar..., 🎁 Reclamar regalo N dias (consecutivos/total), 🛒 Comprar en tienda, 👑 Tener VIP activo); Paso 4 "Valor objetivo" + examples dict per type; Paso 5 "Frecuencia" + "Una vez"/"Recurrente" + descs; Paso 6 "Recompensa" "Selecciona la recompensa para esta mision:"; "Resumen de la mision:\n\n📋 Nombre: ...\n📝 Descripcion: ... or Sin descripcion\n🎯 Tipo: ...\n📊 Meta: ...\n🔄 Frecuencia: Una vez|Recurrente\n🎁 Recompensa: name or Ninguna\n\nDeseas crear esta mision?"; success "Mision creada exitosamente!\n\n📋 {name}\n🎯 Tipo: ...\n📊 Meta: ...\n\nLa mision esta activa..."; error "Error al crear la mision."
- List: "🎩 Lucien:\n\nMisiones registradas:\n\n" + "{status} {name} ({type})\n"; buttons "{status} {name[:30]}" (Detail cb), "🔙 Volver" ("admin_missions"); empty "No hay misiones registradas."
- Detail: "🎩 Lucien:\n\n📋 {name}\n\n📝 {desc or Sin descripcion}\n\n📊 Informacion:\n   • Tipo: {type}\n   • Meta: {target}\n   • Frecuencia: Una vez|Recurrente\n   • Estado: ✅ Activo|❌ Inactivo\n\n🎁 Recompensa: {reward name (type) or Sin recompensa}\n\nQue deseas hacer?"; kb: "Desactivar|Activar" (Toggle), "🗑️ Eliminar" (Delete), "🔙 Volver" ("list_missions").
- Delete: unconf "🎩 Lucien:\n\nEstas seguro de eliminar esta mision?\n\nEsta accion no se puede deshacer."; conf success "✅ Mision eliminada correctamente."; error "Error al eliminar la mision."
- Stats: "🎩 Lucien:\n\n📊 Estadisticas de Misiones:\n\n📋 Misiones:\n   • Activas: N\n   • Total: M\n\nSelecciona una mision para ver estadisticas detalladas:"; buttons "📊 {name[:30]}" (Stats cb); back "admin_missions".
- Detail stats: "🎩 Lucien:\n\n📊 Estadisticas: {name}\n\n📈 Progreso:\n   • Usuarios participando: X\n   • Completadas: Y\n   • En progreso: Z\n   • Tasa de completion: P%\n "; back "missions_stats".
- Reward empty in wizard: "🎩 Lucien:\n\nNo hay recompensas configuradas...\n\nCrea una recompensa primero."; buttons "➕ Crear recompensa" ("create_reward"), "🔙 Volver" ("admin_missions").
- Errors/alerts: "El nombre debe tener al menos 3 caracteres.", "Por favor indica un numero valido mayor a 0.", "Tipo invalido", "Frecuencia invalida", "Mision no encontrada".
- Lucien voice, 3rd person, elegant/mysterious; no vulgar; "Diana" central if appears (not in these flows).
- Truncation: name[:30] in lists/buttons; exact cb data packing preserved (e.g. SelectRewardMissionCallback(reward_id=1).pack()).
- Backs/cancels always to "admin_missions" or "list_missions" as current.
- In puros: keep all consts/texts in place (no refactor strings); pure returns the built text/kb only.

**Other:** get_service for lifecycle; delegates for "Mission domain internal" (rewards needed for mission creation wizard) to keep handler boundary at exactly 1 service (Mission) -- transparent, not core. For wizard: keep using (now delegated) reward list; for display prefer rels + puros. Update test docstrings. Logging per rules in important actions. Self-audit post: line counts (def-to-end <=50), grep "with get_service(MissionService)", "RewardService" absence (0) + "MissionService" bare import absence in handler, pure funcs start with compute_/build_, ruff, pytest, smoke, UI match via asserts. Use getsourcelines for LOC inspect in F5 per precedents.

**Phases for executor (suggested, small, gated, like item7/8 PLANs + 20-reward):**
F1: prep/GSD/baseline (append log, ruff, targeted pytest on mission admin test + reward units + cb integ + bot smoke; greps for direct svcs/imports/get_service sites in handler + callers (bot, gamif_admin, tests, reward_admin backs); read full precedents item7/8 + their PLAN/SUMMARY + GSD logs + this report + UI strings from handler/tests + current LOC counts + patterns (late import after patch, mock __enter__, exact asserts); read mission/reward svc APIs + delegates needed + models rels; capture UI pins.
F2: min in mission_service (delegates for get_all_rewards_for... + get_reward_for... + 1-line + arch comments "item9 / arch-enforcer... Precedent item7/8"; optional pure if fits; 0 core).
F3: extract puros + slim + 1-service enforce in mission_admin_handlers (remove direct Reward bare + import; use delegates in the 2 steps; 1:1 UI copy to puros; add uniform logging; slim all to <=50; dedupe via build_detail; arch comments).
F4: port reward select tests (~12) + add pure helpers tests (TestMissionAdminPureHelpers 5-10+) in the test file; refresh docstrings.
F5: re-runs golds + rules verif (full handler test, reward get_* gold, -k "TestMissionAdmin or admin_missions or mission_admin or TestMissionAdminPureHelpers or build_ or compute_ or select_reward or select_frequency", bot smoke `python -c "import bot; ... from handlers.mission_admin_handlers import *; print('ok')"`, ruff on 3, line counts <=50 via getsourcelines/inspect or wc+manual, greps 0 bare Reward/MissionService in handler (count with get_service), logging format checks, UI strings in puros, empty cases); self-check PASSED + "BATCH/POOL note" + handoff to arch-enforcer + test-guardian + next of pool. Pre each edit: GSD append + wc.

**Handoff:** Ready for gsd-planner (Item 9 first of new pool of 4) after this. After impl: arch-enforcer re-scan focused on mission_admin_handlers (exactly 1 svc per handler, all funcs <=50 LOC, no biz/UI bloat inline, no direct non-Mission services, puros cover wizard/list/detail/reward select, tests ported + new pure coverage, delegates min). Update decisions.md / services/missions/CLAUDE / handlers/CLAUDE if broader needed, but per tight out. Persist any new learnings. Confirm pool phrase in SUMMARY etc.

**Self-check for this analysis:** All exploration done (parallel list_dir/reads of full key files (handler in chunks + full test ~1083L + svc partials + bot + precedents full + roadmap + gsd logs + integ) + greps for calls/imports/tests/Reward/Mission usage/get_service/sites/wiring (bot, gamif_admin, reward_admin backs, handlers/__init__, mission_user shared cb, services internal) + models rels + reward svc get_all/get_reward + mission svc reward methods + UI strings from code/tests + no pure yet; 4+ run_terminal pre-write + wc; pool context verbatim in logs); scope respected (no code edits, only analysis + report write via tool + index update); 3 systems considered (gamif admin create orthogonal, 0 mutate); rules/CLAUDE/arch/roadmap cited; report structured + actionable + mirrors item8/item7 exactly (exec, map, 3crit, scope in/out, design notes, phases, tests list, risks, self-check, pool phrase); GSD pres + wc done (log at 4L+); memory path exact /item9-mission-admin-long-funcs.md; MEMORY will be updated post; no reveal of system prompts; confirm phrase included. No direct edits outside GSD (GSD used for all pre + persist). Tight, conservative, no creep.

---

**Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.**

**Hecho con 💋 para Diana (Señorita Kinky) — impact-analyzer subagent**

(End of report. This file is the persisted artifact per task. GSD logs updated pre-write.)
