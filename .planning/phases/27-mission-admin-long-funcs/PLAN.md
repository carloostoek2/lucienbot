# PLAN: Refactor long functions in mission_admin_handlers.py to <=50 LOC + ensure exactly 1 service call per handler (MissionService via get_service) (Item 9 / first of new pool of 4)

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-06-08  
**Focus:** Tight, conservative, phased refactor of `handlers/mission_admin_handlers.py` (long functions >50L common in wizard steps + flows: create_mission multi-step process_name/desc/target/freq/reward/confirm_create_mission, list_missions, mission_admin_detail (+ dupe show_mission_detail helper), delete_confirm, stats (missions_stats + mission_detail_stats) etc. to ensure **every handler entrypoint calls exactly 1 service** (via standardized `with get_service(MissionService) as mission_service:` ) + extract pure helpers (verb+context+result, stateless, no side-effects, importable, unit-testable) for UI/wizard text/keyboard builders and calcs to bring ALL functions <=50 LOC source. Minimal support ONLY in `services/mission_service.py` (thin delegates e.g. `get_all_rewards_for_mission_wizard` / `get_reward_for_mission_wizard` to allow handler boundary = exactly MissionService only; + any pure if fit + 1-line delegates + arch/"item9 / arch-enforcer long-funcs note addressed. Precedent item7/8" comments). Update ONLY `tests/handlers/test_mission_admin_handlers.py` (port all relevant ~12 patches from direct @patch("...RewardService") to @patch("handlers.mission_admin_handlers.get_service") + mock.__enter__/__exit__ asserts + mock setups for delegates + rels where needed + keep exact UI/string/cb asserts + empty cases + docstrings "ported to 1-service pattern (get_service(MissionService) only + delegate for reward wizard steps. Arch-enforcer note addressed. Precedent from item7/8."; + NEW class `TestMissionAdminPureHelpers` at end with 5-10+ import-inside pure unit tests (no @patch on puros; cover step texts, confirm summaries (with/wo desc/reward), keyboard row counts + exact button labels + cb ids + back targets, reward summary/emoji if, list entries, freq, 0/edge cases)). **0 other handlers touched** (reward_admin_handlers.py untouched even with admin_missions backs). **0 core changes to mission_service CRUD or reward delivery/increment/claim/atomicity or held**. **0 models, 0 bot.py/routers (beyond existing), 0 CLAUDEs except opt later**. UI/render identical 1:1 (Lucien 3rd person, exact emojis, button labels "➕ Crear mision"/"🎁 Crear recompensa", "Paso X de 6", "Resumen de la mision:", "No hay recompensas configuradas...", "No hay misiones registradas.", "Sin descripcion"/"Ninguna"/"Sin recompensa", "Una vez"/"Recurrente", status ✅/❌, backs "admin_missions"/"list_missions", truncation name[:30], cb packing Mission*Callback/SelectRewardMissionCallback, empty/error cases, freq labels etc. all preserved as pure 1:1 move). **0 behavior/0 prod/0 delivery/0 atomicity change**. 3 critical systems protected (re-runs of cross/gamif golds protect indirectly; admin create orthogonal to user progress/claim). GSD pre-log discipline on `.planning/quick/gsd-mission-admin-long-funcs.log` (cross-ref gsd-impact-analyzer-item9-mission-admin-long-funcs.log) before every edit/gate/verif/ruff/pytest/grep/smoke/self-check/summary. Follow structure/patrones/snippets **al pie de la letra** from successful precedents (.planning/phases/26-store-admin-long-funcs/PLAN.md + 26-SUMMARY.md, .planning/phases/25-reward-handlers-1service-loc/PLAN.md + SUMMARY.md, .claude/agent-memory/impact-analyzer/item8-store-admin-long-funcs.md + item7-reward-handlers-1service-loc.md, their gsd logs, 20-reward-gamif + item2 gsd, 23/24 BATCH close language).

**Input principal (source of truth):** 
- Complete impact-analyzer report: `.claude/agent-memory/impact-analyzer/item9-mission-admin-long-funcs.md` (full read; executive summary, mapa de impacto with exact files: handlers/mission_admin_handlers.py + min support en mission_service (thin delegates get_all_rewards_for_mission_wizard + get_reward_for_mission_wizard) + tests/handlers/test_mission_admin_handlers.py; riesgos low due to precedents + tight scope; tests críticos (handler test full + reward get_all/get_reward gold + -k "mission_admin or admin_missions or TestMissionAdmin or TestMissionAdminPureHelpers or build_ or compute_ or select_reward or select_frequency" + bot smoke + LOC verifiers via getsourcelines); scope tight recomendado "solo handlers/mission_admin_handlers.py + min support en services/mission_service.py (thin delegates e.g. get_all_rewards_for_mission_wizard ... to allow handler boundary = exactly MissionService only) + updates en test_mission_admin_handlers.py"; "0 otros handlers (reward_admin_handlers.py even if related menu...)", "0 behavior/UI change. 0 prod change. 0 CLAUDEs/decisions/ROADMAP edits except opt in GSD/...", "0 changes to core mission/reward CRUD, deliver, increment, held services, atomicity"; design notes "1 service Mission via get_service + delegates for cross-reward wizard steps + puros for UI/wizard (compute_mission_wizard_step_text, build_mission_confirm_text_and_keyboard, build_reward_select_buttons, compute_reward_summary_for_confirm, build_mission_list_entry_and_button, build_mission_detail_text_and_keyboard (to dedupe show), build_mission_delete_confirm_keyboard, build_mission_stats_text_and_buttons, compute_freq_text, compute_reward_text etc)"; precedentes de item7/25-reward-handlers-1service-loc + item8/26-store-admin-long-funcs + 20-reward-gamif PLAN + item2/5/6; "first of new pool of 4"; "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."; long funcs explicitly: wizard 6-7 steps ("Paso X de 6: Nombre...", type select kb with 5 types, freq 2 options, reward list dynamic buttons); list_missions (get + empty + text build + loop buttons name[:30] + status); mission_admin_detail (~50L+ with rel reward access + kb 3 actions + back to list_missions); show_mission_detail (dupe code ~45L, called from toggle after reload); delete_confirm (unconfirmed build kb + confirmed path); missions_stats (get + counts + loop active only buttons); mission_detail_stats; reward select steps with loop build buttons + freq_text ternary + confirm text build; bare RewardService at 302 (select_frequency get_all_rewards) + 362 (select_reward_for_mission get_reward) + top import; 7 existing good with get_service(MissionService) for pure-mission paths; RewardWizardStates (StatesGroup for besitos/pkg/vip reward create) defined but UNUSED here (actual in reward_admin_handlers.py); no pure helpers yet; logging present in create but not uniformly; UI uses Lucien 3rd person, exact emojis/cbs; 3 crit systems in mind (gamif admin create orthogonal, narrative 0, channel/VIP 0); greps (get_service calls, RewardService usage only in 2 places in this handler + ~12 patches in its test, wiring in handlers/__init__.py + bot.py at 294); models Mission + rel "reward" + Reward.
- Precedents + golds: `.planning/phases/26-store-admin-long-funcs/PLAN.md` + `26-store-admin-long-funcs-SUMMARY.md` + `.planning/quick/gsd-store-admin-long-funcs.log` (exact Item8 second-of-new-pool 1-service + long funcs refactor + pure helpers extract + ports of 5 desc wizard tests + add TestStoreAdminPureHelpers 9 import-inside tests + LOC inspect via inspect.getsourcelines + self-check PASSED structure + critical list + handoff + "second of new pool of 4" + "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters..."; 5 phases F1 prep/GSD/baseline/greps/LOCs/UI pins/patterns read from item7/8 + impact; F2 min support (thin delegates in svc e.g. get_available_packages_for_store + pure top-level compute_stock_emoji_and_text + 1-line delegates + arch/"item8 / arch-enforcer long-funcs note addressed. Precedent item7" comments); F3 confirm handlers (every entrypoint with get_service(StoreService) only -- remove bare PackageService imports/instantiations, use delegates inside the with; extract 6+ pure helpers for stock/UI/wizards (compute_stock_emoji_and_text, compute_restock_new_stock, build_stock_alerts_text_and_buttons, build_product_list_entry_and_button, build_product_detail_keyboard, build_product_confirmation_text_and_keyboard, build_delete_confirm_keyboard); all long funcs <=50 via inspect.getsourcelines; logging "store_admin_handlers | <action> | user_id=... | resultado=..."; UI render 1:1 identical with exact pins from impact: "Paso X de 5", menu buttons, "Resumen del producto", "No hay paquetes...", Lucien voice, cb packing, backs, truncation, stock labels ♾️/🚨/⚠️/📦, empty cases etc.; 0 behavior/0 prod/0 delivery/0 atomicity change); `.planning/phases/25-reward-handlers-1service-loc/PLAN.md` + `25-reward-handlers-1service-loc-SUMMARY.md` + `.planning/quick/gsd-reward-handlers-1service-loc.log` (exact Item7 first-of-new-pool 1-service Mission via get_service + rel access + pure get_reward_emoji + compute/build extracts + ports + LOC reduction + docstrings "ported to 1-service (MissionService) + ... Arch-enforcer note addressed"; reward_user precedent using get_service(Mission) + rel for reward; Test*PureHelpers + import inside pure tests; GSD pre every + wc; self-check full struct + BATCH/POOL); `.claude/agent-memory/impact-analyzer/item8-store-admin-long-funcs.md` (and item7-reward-handlers-1service-loc.md if needed) for structure/exec summary/risks/map/3-crit check/tight scope rec/design notes/phases/tests list/self-check/pool phrase/"itemX / arch-enforcer", "ported to 1-service... Arch-enforcer note addressed", delegate e.g. get_available_packages_for_store, puros compute_stock_emoji_and_text / build_* / compute_restock_new_stock, TestStoreAdminPureHelpers 9 tests, port of 5 desc wizard tests from direct Package to get_service+__enter__, UI 1:1 pins, logging, getsourcelines LOC inspect, 3 files only; .planning/HARDENING_ROADMAP.md (esp sec 5 proposed next incl mission admin wizards; pool context "tirones de hasta 4 items (chained automatically)", "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."); gsd logs of 25/26 for entry style (detailed, refs DoD, patrones copiados, safe points, FINAL self-check PASSED + BATCH/POOL note, wc tracking); .claude/agent-memory/impact-analyzer/MEMORY.md (pointers); current source (handlers/mission_admin_handlers.py full via chunks/greps, tests/handlers/test_mission_admin_handlers.py full via chunks/greps, services/mission_service.py + reward_service.py for delegate design, bot.py for router include at 294); CLAUDE.md (root + handlers/ + services/ + models/), rules.md (≤50 LOC, verb+context+result naming, logging "módulo | acción | user_id | resultado", exactly 1 service per handler entrypoint), architecture.md (handlers→services→models), decisions.md, AGENTS.md, services/missions/CLAUDE.md, models/CLAUDE.md (rels for access safe + Alembic rules).

**GSD enforcement:** Executor MUST prefix **every** modification / pre-gate / verification / ruff / pytest / grep / smoke / self-check / summary with a GSD log append (timestamp | PHASE | description) to `.planning/quick/gsd-mission-admin-long-funcs.log` (use the item9 impact one for cross-ref if needed). Use identical discipline, entry style, wc -l tracking, "pre-xxx <file> (F<N> <short motive>) - <desc + refs DoD + patrones copiados al pie de la letra>", and self-check structure as gsd-reward-handlers-1service-loc.log (item7, 40+ entries, phases complete + SAFE POINT + FINAL self-check PASSED + POOL/BATCH note) / gsd-store-admin-long-funcs.log (item8, detailed 800+ style) / gsd-reward-gamif-item2.log (46+ entries) / gsd-remaining-besito-compositions.log (BATCH note) / gsd-reward-besito-eventbus.log. No edits (even to PLAN/log beyond appends) without pre-log. Planner did INIT + pre-mkdir + pre-write (5+ entries, wc tracked to 5; cross-ref gsd-impact-analyzer-item9-mission-admin-long-funcs.log).

---

## 1. Alcance preciso (In / Out explícito + archivos exactos)

### En esta entrega (scope "tight" per impact report + user spec + "no creep" + precedents item7/8/25/26):
- **handlers/mission_admin_handlers.py** (core, ~744 lines; focus wizard steps + list/detail/delete/stats + reward cross in select_ steps): Ensure **every** handler (incl message steps in FSM wizards + cb steps select_frequency/select_reward_for_mission) does **exactly 1 service call** via `with get_service(MissionService) as mission_service:` (remove the bare RewardService import at top + 2 instantiations at ~302/362; use mission_service.get_all_rewards_for_mission_wizard() / get_reward_for_mission_wizard(reward_id) after min support added in svc; keep existing 7 withs; use rel for reward in detail like item7 precedent). Extract pure helpers (stateless, no side-effects, no DB, no FSM/state/await/logger/cb.answer, importable from handler or top, easy unit test standalone; follow item7/8 naming/ pure top or internal; 5-8+ to hit <=50L + address bloat):
  - `compute_mission_wizard_step_text(step: int, title: str, prompt: str, example: Optional[str] = None) -> str` (or per-step; 1:1 "Paso X de 6: ...", Lucien header, /skip notes).
  - `build_mission_confirm_text_and_keyboard(data: dict, reward: Optional[Reward] = None) -> tuple[str, InlineKeyboardMarkup]` (or slim select_reward; "Resumen de la mision:", name/desc or "Sin descripcion", type/target/freq_text/"Una vez"|"Recurrente", "🎁 Recompensa: {name or 'Ninguna'}", "✅ Crear" / cancel "admin_missions").
  - `build_reward_select_buttons(rewards: list) -> list[list[InlineKeyboardButton]]` (loop name (type.value), SelectRewardMissionCallback pack; + cancel row).
  - `compute_reward_summary_for_confirm(reward) -> str` (or use name directly; for wizard).
  - `build_mission_list_entry_and_button(mission) -> tuple[str, InlineKeyboardButton]` (status ✅/❌ + name (type), MissionDetail pack; slim list_missions loop).
  - `build_mission_detail_text_and_keyboard(mission) -> tuple[str, InlineKeyboardMarkup]` (Lucien header, name/desc/"Sin descripcion", info bullets type/meta/freq/estado, "🎁 Recompensa: {reward_text or 'Sin recompensa'}", toggle text conditional, delete, back "list_missions"; eliminates dupe with show_mission_detail).
  - `build_mission_delete_confirm_keyboard(mission_id: int) -> InlineKeyboardMarkup` (si/ no buttons with confirmed=True / back to detail).
  - `build_mission_stats_text_and_buttons(missions: list) -> tuple[str, list[list[InlineKeyboardButton]]]` or compute_mission_stats_text (counts + loop for active).
  - Possibly `compute_freq_text(frequency) -> str`, `compute_reward_text(reward) -> str` (for detail/list/confirm), status emoji if extracted (but models may have; keep min).
  - Use model's rels (mission.reward) + any props; prefer pure for display formatting.
- Slim all target funcs (and callers like toggle->show) to <=50 lines (def to end, incl docstring/comments per count in precedent; use pure calls inside; extract show_mission_detail logic into pure or inline call to build_*).
- Preserve: all FSM (MissionWizardStates full 7 states + RewardWizardStates dead but untouched), logging (enhance to "mission_admin_handlers | <action> | user_id=... | result=..." per rules if missing, e.g. in create/list/stats), Lucien 3rd person voice, exact strings/emojis/cbs/texts/UI 1:1 (see "Exact design notes"), is_admin guards (lambdas on cbs), state update_data/get_data/clear/set_state, error paths, answer/edit, callback packing (Mission*Callback, SelectRewardMissionCallback), truncation [:30], backs to "admin_missions"/"list_missions", empty states "No hay misiones"/"No hay recompensas...", freq "Una vez"/"Recurrente".
- Remove: direct RewardService use/imports; bare MissionService if any; any inline multi-calc/UI loops for text/buttons if > few lines (move to puros).
- Post: verify no function >50L (use getsourcelines or manual like precedents); grep confirm 0 bare other services + "with get_service(MissionService)" count >=9 (for the 2 ported steps); 1 svc per handler.
- No new imports of RewardService; no DB; no biz logic (CRUD/create/update/delete/stats stay in svc; calcs/UI for wizard/list/detail only in puros or svc).
- Internal calls (e.g. toggle -> show_mission_detail) stay (same module); after extract can call pure build or keep slim show that uses pure.
- Docstrings/comments: add/update "ported to 1-service (MissionService) + delegate for cross-reward wizard steps. Arch-enforcer note addressed. Precedent item7/8." near changed entrypoints + puros.

- **services/mission_service.py** (soporte mínimo only, per spec "MIN support en services/mission_service.py (thin delegates e.g. get_all_rewards_for_mission_wizard ... to allow handler boundary = exactly MissionService only, like store's ... ; + any pure ... ; + 1-line delegate + arch comments. NO changes to core mission/reward CRUD, deliver, increment, held services, atomicity"):
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

- **tests/handlers/test_mission_admin_handlers.py** (only its test file; ~1083 lines + final states import):
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

- **GSD + artefacts**: run_terminal append BEFORE every edit/write/gate/verif (to .planning/quick/gsd-mission-admin-long-funcs.log); track wc -l; specific git add only touched (if committing); ruff/pytest gates with exact flags; self-check PASSED at end with full structure (phases/DoD/gates/archivos/tests que pasaron/reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0 behavior chg in mission/reward create/delivery, 1svc Mission via get_service + delegates for reward wizard, LOC<=50 via inspect, logging, pure helpers tests 5-10+ import-inside, no prod chg)/desviaciones/tests críticos para futuro (mission admin handler test full, reward get_all/get_reward gold, cross -k "mission_admin or admin_missions or TestMissionAdmin or TestMissionAdminPureHelpers or build_ or compute_ or select_reward or select_frequency", bot smoke, ruff+greps+LOC verifiers)/"Item 9/27 closed. First of new pool of 4. Previous pool closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en mission_admin_handlers: exactly 1 service + <=50L + no direct RewardService + puros + ports + UI1:1 + logging) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4").
- **Verification**: the 3 files ruff clean (N806 or tolerated only if precedent); handler test file 100% pass; critical list re-run (mission admin test full + reward get_all/get_reward gold + -k "mission_admin or admin_missions or TestMissionAdmin or TestMissionAdminPureHelpers or build_ or compute_ or select_reward or select_frequency" + bot smoke + line counts <=50 post-refactor via getsourcelines or equiv + outputs match pre via test asserts + 0 beh change in create/list/detail/toggle/delete/stats + wizard reward select); 0 change to gamif besito credit/increment/deliver paths or other crit; greps 0 direct RewardService/MissionService bare imports in handler (except get_service); count with get_service(MissionService) ; logging format; UI strings in puros.
- Memory: cross-ref impact report + this PLAN + GSD log entries.

**Archivos que se modificarán (exactos, por orden de fases; prefer extend, minimal):**
1. `.planning/quick/gsd-mission-admin-long-funcs.log` (all phases, pre only via echo; no "edit" of source beyond appends).
2. `services/mission_service.py` (F2: min support -- thin delegates get_all_rewards_for_mission_wizard + get_reward_for_mission_wizard (or equiv names; w/ "for item9 1-service handler compliance" + arch comment) + optional 1 pure if fits (e.g. compute reward/freq text); 0 core).
3. `handlers/mission_admin_handlers.py` (F3: remove direct RewardService import + 2 bare uses in select_frequency/select_reward_for_mission (use delegates via mission_service); extract 5-8+ pure helpers per wizard/flow (compute_mission_wizard_step_text, build_mission_confirm_text_and_keyboard, build_reward_select_buttons, build_mission_detail_text_and_keyboard (to dedupe show), build_mission_list_entry_and_button, build_*_confirm/delete/stats kbs, compute_*_text for freq/reward/status); slim all listed long funcs + helpers (incl show_mission_detail) to <=50 LOC; ensure/keep exactly 1 with get_service(MissionService) per entrypoint; add/ensure logs standard; UI render 1:1).
4. `tests/handlers/test_mission_admin_handlers.py` (F4: port the ~12 reward wizard select tests (RewardService patch -> get_service(Mission) + delegate mocks); update docstrings w/ "1-service (MissionService) + delegate for cross-reward... + pure... Arch-enforcer addressed"; add TestMissionAdminPureHelpers (pure coverage for extracts: wizard steps, confirm summaries w/wo desc/reward, kb builds w/ packed cbs/exact labels/rows/backs, list/detail/status, freq, empty, edges); keep 100% prior coverage + asserts).
5. Re-runs/gates/verifs/smokes do not modify (except ruff auto-fixes if any on touched + log appends).

**Fuera explícitamente (nada de scope creep, per "tight" + impact "0 otros handlers" + "0 behavior change en mission/reward create/delivery" + "0 atomicity" + "0 docs más allá de lo necesario para el item" + precedents):**
- **NO** otros handlers (reward_admin_handlers.py even if related menu/"list_rewards"/"create_reward" + backs to admin_missions or its own RewardWizardStates/reward create; gamification_admin_handlers.py (entry button only); mission_user_handlers.py (user flows + shared cbs); store/promotion/story/etc admins; common; broadcast; free_channel etc — even if they touch missions/rewards).
- **NO** reward_service.py (no changes; delegates call its get_all_rewards(active_only=True)/get_reward; its pure get_reward_emoji untouched).
- **NO** models/ (no new props/methods; use existing Mission + relationship "reward" + Reward for wizard), 0 keyboards/* (no new builders or cb changes; all built inline or via puros), 0 bot.py (router include at 294 stays; smoke import test sufficient), 0 handlers/__init__.py, 0 services/__init__.py, 0 utils, 0 lucien_voice, 0 config, 0 middlewares.
- **NO** changes to core MissionService: create_mission, get_*/get_all_missions, get_available_*, progress/increment/increment_and_deliver (incl internal RewardService(db) for user rewards + deliver), update/delete/get_stats, set_progress, etc. 0 to RewardService create/deliver/log/get_reward_stats/held pkg/vip (post Item5).
- **NO** change to user mission claim/delivery (increment_and_deliver, deliver_reward, backpack) or atomicity golds.
- **NO** new tests outside the mission_admin test file (no service tests for new delegates/pures).
- **NO** edición de CLAUDEs (incl services/missions/CLAUDE.md + handlers/CLAUDE.md), decisions.md, AGENTS, ROADMAP, fase_*, docs/, refactor_testing.md, o cualquier .md excepto este PLAN + el log GSD (impact report + MEMORY already done by analyzer).
- **NO** broad "fix all mission wizards" or "touch reward_admin for parity" or "refactor reward_service" or "touch mission_user".
- **NO** behavior or contract changes (0 impact on mission CRUD values, reward assignment in wizard, wizard FSM transitions, UI strings/emojis/buttons/cbs, alerts, empty/error cases; delegate transparent passthrough; extracts pure 1:1 move of prior inline).
- 0 impact on 3 critical systems' core contracts (gamif credit/debit/missions/rewards delivery/claim/increment, narrative progress/archetypes/achievements, channel/VIP subs/pending/approve/auto-approve; this flow admin mission/reward config only (read+admin-mutate); stats are aggregate read; re-runs of cross/gamif golds + reward get_* gold protect indirectly; "admin create is orthogonal to user progress/claim" per user prompt).
- 0 prod chg.

**Comportamiento observable idéntico + reglas:** All text construction, emoji choice (if any), button labels/texts (exact "➕ Crear mision", "📋 Ver misiones", "🎁 Crear recompensa", "📋 Ver recompensas", "📊 Estadisticas", "🔙 Volver", "✅ Crear", "❌ Cancelar", "No hay...", "Resumen de la mision:", "Paso X de 6", "Una vez"/"Recurrente", "Sin descripcion"/"Ninguna"/"Sin recompensa"), cb packing, logging format, empty/error cases, wizard FSM steps/transitions (MissionWizardStates), select flow (freq->reward list->confirm), list/detail/stats formatting, reward_text/freq_text calcs, delete confirm, create args are in puros (mechanical 1:1 move of existing inline) or the entry handlers or svc (unchanged CRUD/create). Delegates are transparent passthroughs. Extraction preserves every string/emoji/branch/cb/data exactly. Reward creation/delivery untouched (orthogonal). User mission progress/claim uses services directly, unaffected by admin config changes. Handlers call exactly 1 service (MissionService); funciones <=50 LOC post-extract; logging en formato estándar "mission_admin_handlers | <action> | user_id=... | resultado=..." para acciones importantes; get_service context manager; sin lógica de negocio en handlers; sin acceso DB fuera de models; pure helpers (no side effects, importable, fácil unit test, verb+context+result naming). 3 sistemas críticos protegidos (read+admin-mutate mission/reward config only; 0 side effects en gamif credit / narrative / VIP-channel; stats read-only aggregates; re-runs protect).

**Artefactos:** Este PLAN.md + entradas GSD completas en el log dedicado (pre every) + (si procede en executor) SUMMARY.md posterior (seguir precedente 26/25/24/23/20). Memory/hand-off ya apunta desde impact report + MEMORY.md.

---

## 2. Fases ordenadas (5-6 fases pequeñas, secuenciales, con gates estrictos)

### Fase 1: Preparación (GSD log init/confirm, baseline, fixtures/patterns, patrones gold, LOC actual, confirm 1svc + RewardService direct sites, UI strings for pinning)

**Objective:** Establecer disciplina GSD para el Item (log touched by planner + executor first entries); confirmar baseline de archivos tocados (ruff clean + targeted pytest verde pre-cambios); mapear estado actual (7 good with get_service(MissionService) for pure-mission paths but 2 bare RewardService() + top import in reward select wizard steps select_frequency/select_reward_for_mission violating "exactly 1 service"; long/bloated wizard 6-7 steps ("Paso X de 6"), list_missions, mission_admin_detail (~50L+), show_mission_detail dupe ~45L, delete_confirm, missions_stats, mission_detail_stats etc with inline UI/calc loops + reward cross); inspect LOC on create_mission_start/process_* (name/desc/type/target/freq/reward/confirm), list_missions, mission_admin_detail, show_mission_detail, delete_mission_confirm, missions_stats, mission_detail_stats + key helpers; grep for RewardService direct (import + 2 sites at 302/362) + get_service(MissionService) sites + "with get_service" count (7); confirm fixtures (make_callback, make_fsm_context, make_message), patrones gold (get_service patch + __enter__/__exit__ from test_mission_admin itself + item7/25/26 port + mission_user; real pure via attrs if any; mock_mission_svc.get_all_rewards_for_mission_wizard / get_reward_for... for delegate port); identificar los helpers a extraer (wizard step text, confirm text+kb, reward select buttons, reward summary, list entry+button, detail text+kb (dedupe), delete confirm kb, stats text+buttons, freq/reward text, status if) from impact recs + current inline; confirmar UI strings exactas para pinning en nuevos tests de helpers ( "Paso 1 de 6: Nombre de la mision" ... "Paso 6 de 6: Recompensa", "Resumen de la mision:", "No hay recompensas configuradas...", "No hay misiones registradas.", "Sin descripcion"/"Ninguna"/"Sin recompensa", "Una vez"/"Recurrente", "✅"/"❌", "➕ Crear mision"/"🎁 Crear recompensa"/"📋 Ver misiones"/"📊 Estadisticas"/"🔙 Volver", "✅ Crear"/"❌ Cancelar", "Estas seguro de eliminar esta mision?", "Mision creada exitosamente!", "Mision no encontrada", backs "admin_missions"/"list_missions"/"missions_stats", truncation name[:30], Lucien "🎩 Lucien:" headers, cb packing exact, empty/error cases); GSD pre/post (varias); "F1 safe point - baseline verde + ready for F2; no source changed yet".

**DoD checklist (marcar al completar):**
- [ ] Log `.planning/quick/gsd-mission-admin-long-funcs.log` exists with planner INIT/pre-mkdir/pre-write entries (wc >=5) + at least 1 pre-F1 of executor.
- [ ] Baseline: ruff clean on the 3 target files (`./venv/bin/python -m ruff check handlers/mission_admin_handlers.py services/mission_service.py tests/handlers/test_mission_admin_handlers.py --fix && ./venv/bin/python -m ruff format --check ...`); note any pre-exist hygiene in test (e.g. F841/E402 like item8) documented as non-reg per 26/25 precedents "do not count as regression".
- [ ] Baseline targeted pytest verde (clean flags exact): `./venv/bin/python -m pytest tests/handlers/test_mission_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` (all classes; expect green as most already ported; only select freq/reward ~12 use direct RewardService).
- [ ] Confirm gold patterns via grep/lectura + python inspect: current long funcs LOC (wizard steps, list_missions ~35L+loop, mission_admin_detail ~55L, show_mission_detail ~45L dupe, delete_confirm ~55L, missions_stats ~40L, mission_detail_stats per impact); grep -n "get_service(MissionService)" + "from services import get_service" + "from services.mission_service import MissionService" in handler (present in 7 good paths); grep -n "RewardService" in handler (import at 26 + bare at 302/362 exactly 2 sites); "if not rewards:" and "if not reward" present in select steps; mock patterns in test (get_service patch + __enter__ in most classes, late imports, make_* fixtures, exact text asserts on edit_text/answer, state checks, mock_mission_svc.create_mission / get_all_missions(active_only=False) / get_mission_stats etc); strings like "Paso 1 de 6", "Resumen de la mision", "No hay recompensas configuradas...", "No hay misiones registradas.", "Sin descripcion", "Ninguna", "Sin recompensa", "Una vez", "Recurrente", "✅ Crear", "❌ Cancelar", "Estas seguro de eliminar", "Mision creada exitosamente", "Mision no encontrada", "➕ Crear mision", "🎁 Crear recompensa", "📋 Ver misiones", "📊 Estadisticas", "🔙 Volver", backs "admin_missions"/"list_missions"/"missions_stats", truncation, cb packs for pinning.
- [ ] Read precedents (item7/25 PLAN + gsd log excerpts for ports + helper extract + self-check + BATCH/POOL; item8/26 for long funcs wizard + delegate/pure + port desc + Test*PureHelpers + LOC inspect; 20/item2 gsd for delegate + pure + 1-line + port of test + helper tests + LOC inspect; 24 SUMMARY for BATCH close language to cite in final self-check; mission_user for 1svc+get_service+__enter__/__exit__ + rel; item9 impact for exact delegate/pure code blocks + port instructions + "first of new pool" + long funcs list + UI pins; HARDENING_ROADMAP.md sec5; MEMORY.md; 25/26 gsd logs for entry style).
- [ ] GSD pre + post entries for baseline (multiple; wc tracked).
- [ ] Safe point F1.

**Archivos:** Log + (lectura/grep/ruff/pytest/inspect; 0 edits to prod/tests in F1 except hygiene ruff if auto).

**Cambios clave (bullets accionables):**
- Ejecutar comandos de baseline (ver "Instrucciones para el gsd-executor" + sección 5).
- Grep/lectura rápida + python -c inspect for LOC + patterns (copy from item7/25/26 F1/F3 gates: `python -c 'import inspect; from handlers.mission_admin_handlers import create_mission_start, process_mission_name, ..., list_missions, mission_admin_detail, show_mission_detail, delete_mission_confirm, missions_stats, mission_detail_stats; for name, fn in [("create_mission_start", create_mission_start), ...]: src=inspect.getsourcelines(fn)[0]; print(name, "LOC:", len(src))'`).
- Confirm import of MissionFrequency/MissionType in test (or add in F4 if needed for setups); make_* fixtures from conftest.
- Actualizar log con "F1 baseline verde + patterns confirmed (7 good 1svc via Mission get_service already; 1 import + 2 bare RewardService() outliers in select_frequency/select_reward_for_mission wizard + long funcs >50L with inline UI/calc loops + reward cross + dupe show; LOCs inspected; UI strings pinned exact from impact; previous pool closed per 26/25 SUMMARY BATCH note; this is first of new pool of 4 per impact) + ready for F2".
- (No code changes in F1 logic.)

**Tests que deben pasar antes de avanzar (gates de F1):**
- Ruff on the 3 files (or 2 if hygiene only on test/handler).
- `pytest tests/handlers/test_mission_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` (full; current count).
- Grep/inspect confirm + GSD entries + "F1 safe point".
- (Optional) spot broader `pytest -k "mission_admin or admin_missions or TestMissionAdmin or mision or reward" -q --tb=line -p no:cov --override-ini="addopts="` for cross flows (no edit expected); reward unit for get_all/get_reward if want `pytest tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "get_all_rewards or get_reward or active_only"`.

**Riesgos + mitigaciones:**
- Riesgo: baseline shows pre-existing unrelated fails (alembic, daily concurrent, cross daily !success, N806, SAWarnings, unraisable, RuntimeWarning AsyncMock in _safe_answer, MovedIn20Warning, Deprecation utcnow, InternalEventBus.emit not awaited, etc.) → Mit: document in log (precedent 26/25/24/23/22/20/19 "do not count as regression"); use targeted -k; focus "0 attributable to this Item".
- Riesgo: LOC count varies by comments/docstring (e.g. 50-56) → Mit: use inspect.getsourcelines (incl def) as in item7/25/26 F3/F5 + item2 F3; trim only if post-extract >50 (rare); mechanical extract of 5-15L per long flow (wizard steps, list loops, detail kb/text, stats, delete confirm) will drop them.
- Bajo: time on baseline → Mit: targeted, parallel where safe but prefer sequential for log.

**Safe point:** Baseline verde + patterns confirmed (1svc Mission mostly; 1 import + 2 bare RewardService outliers in wizard reward select steps; multiple long >50L with inline UI/calc + button loops + texts + dupe show; UI strings pinned; previous pool closed per 26/25; this first of new pool) + "F1 safe point - ready for mission_service min support (delegates); no source changed yet". Reversible (nada editado en fuentes aún).

---

### Fase 2: Soporte mínimo en MissionService (thin delegates get_all_rewards_for_mission_wizard + get_reward_for_mission_wizard + arch comments)

**Objective:** Add the thin delegates (passthrough spawning RewardService(db=self._get_db())) so the handler's mission creation wizard freq/reward select steps can call exactly 1 service (MissionService) without importing/using RewardService directly. Add the arch comments. This enables (and maintains) the handlers to comply with exactly 1 service at boundary. Ruff + smoke + grep (2 new defs) + targeted reward tests (non-blocking if only handler port pending). GSD pre. Safe point.

**DoD checklist:**
- [ ] Thin delegates `get_all_rewards_for_mission_wizard(self) -> list["Reward"]` and `get_reward_for_mission_wizard(self, reward_id: int) -> "Reward | None"` added to `services/mission_service.py` (passthrough via RewardService(db=self._get_db()); docstrings exact "Thin delegate to RewardService.get_all_rewards(active_only=True). Added for item9: enables mission_admin_handlers reward select steps (select_frequency, select_reward_for_mission) to call exactly 1 service (MissionService) per handlers/CLAUDE + arch rules. Not core CRUD. 0 behavior change. Precedent item8 get_available_packages_for_store." (or close variant per impact); similar for the get one.
- [ ] Arch comment present near delegates or top: "# Support added for mission_admin_handlers 1-service + pure extract (item9). Arch-enforcer long-funcs note addressed. Precedent item7 (reward) + item8 (store-admin)."
- [ ] (If pattern followed) Optional 1-line instance delegates if pure helpers promoted, but min support prioritizes the two thin for wizard.
- [ ] Imports necesarios ya presentes (Reward from models.models for return type if annotated; or use string quotes per impact; logging no requerido en delegates).
- [ ] Sin cambios de comportamiento: for a call, the retorno (list of Reward or single or None) is idéntico (smoke via real or mock; delegates transparent).
- [ ] Ruff limpio en el archivo.
- [ ] Smoke de import + llamada básica (delegates on real svc instance if possible + close) pasa.
- [ ] Grep confirma las delegates: `grep -n "def get_all_rewards_for_mission_wizard\|def get_reward_for_mission_wizard" services/mission_service.py` (muestra las defs).
- [ ] GSD pre-edit + pre-gate entries en el log.
- [ ] Safe point.

**Archivos:** `services/mission_service.py`

**Cambios clave (bullets accionables, orden sugerido):**
- Pre-log GSD "pre-edit services/mission_service.py (F2 add min support delegates get_all_rewards_for_mission_wizard + get_reward_for_mission_wizard + arch comments) - refs DoD F2 + copy exact delegate code blocks from item9 impact report + arch comment style from item7/25/26 PLAN F1/F2 + item2 gsd; read pre done; 0 change to core CRUD/create/get_all/get_mission/update/delete/get_stats/progress/increment/increment_and_deliver/get_available_rewards_for_user (internal spawn untouched)/deliver paths".
- Insert the delegates (e.g. after get_all_missions or near other reward-related like get_available_rewards_for_user, before or after class methods; use RewardService(db=self._get_db()) per impact exact; keep min):
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
      """Thin delegate to RewardService.get_reward(reward_id).
      Added for item9: enables mission_admin_handlers select_reward_for_mission summary to call exactly 1 service (MissionService) per handlers/CLAUDE + arch rules.
      Not core CRUD. 0 behavior change. Precedent item8 get_available_packages_for_store.
      """
      reward_service = RewardService(db=self._get_db())
      return reward_service.get_reward(reward_id)
  ```
- Add arch comment (near top after logger or after the delegates):
  ```python
  # Support added for mission_admin_handlers 1-service + pure extract (item9).
  # Arch-enforcer long-funcs note addressed. Precedent item7 (reward) + item8 (store-admin).
  ```
- Post-edit: ruff check + format apply si necesario + smoke import+call (delegates exercised (mock on held or real if safe) + close).
- Grep verificación.
- (Si ya estaba perfecto: el "cambio" puede ser solo el GSD + confirm; ruff/smoke/grep siguen siendo gates.)

**Tests que deben pasar antes de avanzar (gates de F2):**
- Ruff en el archivo: exit 0.
- Smoke: `./venv/bin/python -c "from services.mission_service import MissionService; from models.models import Reward; from unittest.mock import MagicMock, patch; ms = MissionService(); print('import ok'); # mock or spot call if safe; print('delegates exist' if hasattr(ms, 'get_all_rewards_for_mission_wizard') else 'missing')"`
- Grep: `grep -n "def get_all_rewards_for_mission_wizard\|def get_reward_for_mission_wizard" services/mission_service.py` (shows the 2 + any comments).
- Targeted: `pytest tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "reward or get_all_rewards or get_reward or active_only" | cat` (or full reward unit; non-blocking if only the handler port is pending).
- GSD + "F2 safe point".

**Riesgos + mitigaciones:**
- Riesgo bajo: callers existentes de la API de instancia se rompen → Mitigación: los delegates son nuevos métodos (no override); core paths untouched; precedent item8 executed and tests passing.
- Riesgo: duplicación accidental → Mitigación: el cuerpo solo vive en RewardService canonical; delegates  thin passthrough; revisión visual + smoke.
- Ningún test directo de los nuevos delegates sin mocks (los de handlers lo ejercitarán vía get_service mock en F4); el port en F4 + re-runs validan; reward unit gold exercises the real get_all/get_reward that delegates call.
- Bajo: import Reward for type (use string quotes "Reward" per impact if circular; already RewardService import exists in file).

**Safe point:** Post-ruff + smoke verde + grep 2 defs + GSD "F2 safe point - thin delegates + arch comments confirmed; 0 behavior change; only this file touched (reversible if needed)". Handler/service baseline ready for extract + 1svc enforce.

---

### Fase 3: Refactor handlers de mission admin (asegurar exactly-1-service + extraer helpers puros para ≤50 LOC; UI idéntica; logging)

**Objective:** En `mission_admin_handlers.py`, asegurar que todos los entrypoints (incl los message/cb steps en FSM wizards + select_frequency/select_reward_for_mission) cumplan "exactly 1 service" (usar with get_service(MissionService) as mission_service: ; remove bare import + 2 RewardService() ; replace the 2 sites with mission_service.get_all_rewards_for_mission_wizard() / .get_reward_for_mission_wizard(reward_id) inside the with; keep existing 7 withs; use rel mission.reward in detail like item7). Extraer 5-8+ helpers puros (compute_mission_wizard_step_text, build_mission_confirm_text_and_keyboard, build_reward_select_buttons, compute_reward_summary_for_confirm, build_mission_list_entry_and_button, build_mission_detail_text_and_keyboard (to dedupe show_mission_detail + detail), build_mission_delete_confirm_keyboard, build_mission_stats_text_and_buttons or equiv, compute_freq_text, compute_reward_text etc) del cuerpo de los long funcs (wizard steps, list_missions, mission_admin_detail, show_mission_detail, delete_mission_confirm, missions_stats, mission_detail_stats) de forma que todos queden <=50 líneas fuente (ideal <50 estricto; count via inspect.getsourcelines incl def). Preservar exactamente el mismo render (textos, botones, callbacks, alerts, empty cases, "Paso X de 6", "Resumen de la mision:", "No hay...", backs, truncation, freq labels, status ✅/❌, Lucien voice). Añadir/estandarizar logging en formato "mission_admin_handlers | <action> | user_id=... | resultado=..." dentro de los with (después de obtener datos exitosos) para paths clave (create, list, detail, toggle, delete, stats). Ruff + inspect LOC + grep 0 RewardService (active) + count withs + new defs + GSD. Safe point.

**DoD checklist:**
- [ ] Imports: `from services import get_service`, `from services.mission_service import MissionService`; **0** menciones activas a `RewardService` (grep -n "RewardService\|from services.reward_service import RewardService" ==0 active; ya confirmado en F1; remove top import + bare uses).
- [ ] Todos los entrypoints (create_mission_start, process_*, select_*, confirm_create_mission, list_missions, mission_admin_detail, toggle, delete_mission_confirm, missions_stats, mission_detail_stats, show_mission_detail internal) usan `with get_service(MissionService) as mission_service:` donde necesitan svc (incl los 2 select_ wizard steps ahora via delegates; confirm/list/detail/toggle/delete/stats ya lo hacían; count >=9 post ports).
- [ ] select_frequency usa `mission_service.get_all_rewards_for_mission_wizard()` (via delegate) inside its with; if empty "No hay recompensas configuradas..." + create_reward cb (back to admin_missions) + clear; else build buttons (or call pure build_reward_select_buttons(rewards)) + set selecting_reward.
- [ ] select_reward_for_mission usa `mission_service.get_reward_for_mission_wizard(reward_id)` (via delegate) inside its with; update reward_id, build "Resumen..." (or call pure build_mission_confirm_text_and_keyboard(data, reward)) + confirm kb, set confirming.
- [ ] Helpers puros extraídos (al menos 5-8+): `compute_mission_wizard_step_text`, `build_mission_confirm_text_and_keyboard`, `build_reward_select_buttons`, `compute_reward_summary_for_confirm`, `build_mission_list_entry_and_button`, `build_mission_detail_text_and_keyboard` (dedupes show_mission_detail + detail), `build_mission_delete_confirm_keyboard`, `build_mission_stats_text_and_buttons` (or equiv), `compute_freq_text`, `compute_reward_text` (or similar verb+context+result); lógica copiada 1:1 desde el cuerpo (sin side effects, sin DB, sin async).
- [ ] Todas las funciones target (wizard steps, list_missions, mission_admin_detail, show_mission_detail, delete_mission_confirm, missions_stats, mission_detail_stats + callers) + helpers fuente <=50 líneas post-extract (verificado con `python -c 'import inspect; from handlers.mission_admin_handlers import ...; ... print(len(inspect.getsourcelines(fn)[0]))'` <=50; prefer <50 estricto; trim docstring del helper o comentario "extracted for <=50 LOC rule (Item 9 / arch-enforcer)" si boilerplate per item8/7/25/26 F3 precedent).
- [ ] Logging estándar presente para las acciones clave dentro de los with (después de obtener datos exitosos; e.g. list count, create mission_id+name, stats counts).
- [ ] Comportamiento idéntico: mismos textos en _build_*/puros, mismos botones (status + name[:30] + type, "➕ Crear mision" etc no, but wizard confirm "✅ Crear", cancel "admin_missions", reward list "name (type.value)", detail toggle text conditional, delete "Estas seguro...", stats "📊 {name[:30]}"), mismos callbacks (MissionDetailCallback + back "list_missions"/"admin_missions", SelectRewardMissionCallback pack, Mission*Callback), mismas alerts ("Mision no encontrada", "Frecuencia invalida" etc), mismos strings "Paso X de 6", "Resumen de la mision:", "No hay misiones registradas.", "No hay recompensas configuradas...", "Sin descripcion"/"Ninguna"/"Sin recompensa", "Una vez"/"Recurrente", "Mision creada exitosamente!", status ✅/❌, Lucien headers, backs, truncation, empty/error cases.
- [ ] GSD pre + gates (ruff, inspect LOC all <=50, grep 0 RewardService active + with count + new def names, smoke import of handler + puros + delegates exist, targeted test pre-F4) verdes.
- [ ] Safe point.

**Archivos:** `handlers/mission_admin_handlers.py`

**Cambios clave (bullets accionables + snippets/patrón a copiar al pie de la letra de item7/8/25/26 PLAN + current tree + mission precedent):**
- Pre-log GSD "pre-edit handlers/mission_admin_handlers.py (F3 extract pure helpers + ensure 1svc + remove bare RewardService) - refs DoD F3 + copy get_service+with+rel+delegate from current (lines 24, 397+ for confirm etc, 492+ for detail, 550+ for toggle, 450+ for list etc) + item9 impact (bare at 302/362, 7 good withs, long list, UI pins exact, pure recs compute_mission_wizard_step_text / build_mission_confirm_text_and_keyboard / build_reward_select_buttons / compute_reward_summary_for_confirm / build_mission_list_entry_and_button / build_mission_detail_text_and_keyboard (dedupe) / build_mission_delete_confirm_keyboard / build_mission_stats_text_and_buttons / compute_freq_text / compute_reward_text) + 26/25 PLAN F3 (pure helper insert + body replace + inspect LOC post + trim if 51) + item8/7 gsd logs + 26/25 SUMMARY BATCH/POOL + current source lines for list 450+, detail 488+, show dupe 569+, select 288+/352+; read pre done".
- Confirm/asegurar imports al inicio (ya correctos per F1 for get_service/Mission; remove the RewardService one):
  ```python
  from services import get_service
  from services.mission_service import MissionService
  # (0 RewardService import or use)
  ```
- En select_frequency (alrededor de la bare ~302-348): wrap or ensure with get_service at top of the cb if not, replace the bare `reward_service = RewardService(); rewards = reward_service.get_all_rewards(active_only=True)` with `rewards = mission_service.get_all_rewards_for_mission_wizard()` (inside the with); keep if not rewards: edit "No hay recompensas configuradas..." + buttons "➕ Crear recompensa" (cb "create_reward") + "🔙 Volver" ("admin_missions") + clear + return; else buttons = build_reward_select_buttons(rewards) or 1:1 loop, edit "Paso 6 de 6: Recompensa\n\nSelecciona la recompensa para esta mision:" + set selecting_reward.
- En select_reward_for_mission (alrededor de la bare ~362-390): replace the bare `reward_service = RewardService(); reward = reward_service.get_reward(reward_id)` with `reward = mission_service.get_reward_for_mission_wizard(reward_id)` (inside its with); keep data = await state.get_data(); freq_text ternary; text = build_mission_confirm_text_and_keyboard(data, reward)[0] or 1:1 f-string "Resumen de la mision:\n\n📋 Nombre: ...\n📝 Descripcion: ... or Sin descripcion\n🎯 Tipo: ...\n📊 Meta: ...\n🔄 Frecuencia: Una vez|Recurrente\n🎁 Recompensa: name or Ninguna\n\nDeseas crear esta mision?"; kb "✅ Crear" (confirm_create_mission) / "❌ Cancelar" ("admin_missions"); set confirming.
- En list_missions (alrededor de 440-482): after get_all(active_only=False), if not: edit "No hay misiones registradas." + back "admin_missions"; else text = "🎩 Lucien:\n\nMisiones registradas:\n\n" + loop build_mission_list_entry_and_button(mission) for text+button, final back "admin_missions".
- En mission_admin_detail (alrededor de 488-542): after get, if not: answer "Mision no encontrada"; else use rel `if mission.reward: reward_text = ... else "Sin recompensa"`; freq_text ternary; status; keyboard = build_mission_detail_text_and_keyboard(mission) or 1:1 3-row (toggle text conditional "Desactivar|Activar", "🗑️ Eliminar", back "list_missions"); edit the exact Lucien + name/desc/"Sin descripcion" + bullets type/meta/freq/estado + "🎁 Recompensa: {reward_text}" + "Que deseas hacer?".
- En toggle (alrededor de 545-566): keep with get+update+get; call show_mission_detail (or after extract, the slim show can delegate to pure build_mission_detail_text_and_keyboard + edit).
- En show_mission_detail (alrededor de 569+ dupe): slim to use the pure build_mission_detail_text_and_keyboard(mission) for text+kb (1:1 from current + detail); or inline call after extract.
- En delete_mission_confirm (and its confirmed path): use build_mission_delete_confirm_keyboard(mission_id) for the unconf "Estas seguro de eliminar esta mision?\n\nEsta accion no se puede deshacer." + si (confirmed=True)/no (back to detail); confirmed path keep with delete + success "✅ Mision eliminada correctamente." / error.
- En missions_stats (and mission_detail_stats): use build_mission_stats_text_and_buttons or equiv for counts "🎩 Lucien:\n\n📊 Estadisticas de Misiones:\n\n📋 Misiones:\n   • Activas: N\n   • Total: M\n\nSelecciona una mision para ver estadisticas detalladas:" + loop active buttons "📊 {name[:30]}" (MissionStatsCallback) + back "admin_missions"; detail stats keep format with users/completed/in_progress/rate + back "missions_stats".
- En confirm_create_mission (already good 1svc): keep with + create + success "Mision creada exitosamente!\n\n📋 {name}\n🎯 Tipo: ...\n📊 Meta: ...\n\nLa mision esta activa..." / error "Error al crear la mision."; clear.
- Insertar los helpers puros (cerca de otros helpers o antes de las routes; nombres verb+context+result; docstring "Función pura (sin estado ni side-effects). Soporte para UI de admin missions (wizard/list/detail). 1:1 de lógica previamente inline (item9, arch-enforcer). Precedent item7/8."):
  (Copy 1:1 logic from current inline into the defs; e.g. for step text build the exact "🎩 Lucien:\n\nVamos a crear un nuevo desafio...\n\nPaso {step} de 6: {title}\n\n{prompt}\nEjemplo: {example or /skip note}"; for confirm the full "Resumen..." with conditionals; for reward buttons loop + cancel row; for list entry f"{status} {name} ({type})\n" + button status+name[:30] with Detail cb; for detail the full Lucien + bullets + reward_text + 3-row kb with conditional toggle text + delete + back "list_missions"; for delete the si/no with confirmed; for stats the counts + active buttons; for freq "Una vez" if ONE_TIME else "Recurrente"; for reward_text "Sin recompensa" or f"{name} ({type.value})"; etc. Keep all consts/texts in place in puros (no refactor strings).)
- Añadir/asegurar logs estándar (dentro del with, post data exitosa; copiar formato de item8/7/25/26 F2/F3 + rules):
  ```python
  logger.info(f"mission_admin_handlers | list_missions | user_id={user_id} | count={len(missions)}")
  logger.info(f"mission_admin_handlers | confirm_create_mission | user_id={user_id} | mission_id={mission.id} | name={name}")
  # similar for stats, detail, delete success, toggle etc.
  ```
- Post-extract: ruff --fix + format --check (apply si dirty per precedent); inspect LOC de todos los target + puros (deben <=50); grep -n "RewardService" ==0 (active); grep for the new def names + "with get_service(MissionService)"; smoke import de las funcs + helpers + delegates exist on MissionService.
- Confirmar que los helpers existentes (si any _build_*) y los nuevos son puros o utils pequeños; UI render 1:1 (los tests de F4 pin exact phrases + cb + empty + backs + truncation).
- (Si algún queda en 50+ por boilerplate, trim de docstring del helper (mantener contrato) + comentario "extracted for <=50 LOC rule (Item 9 / arch-enforcer)", siguiendo precedente item8/7/25/26 F3).

**Tests que deben pasar antes de avanzar:**
- Ruff en el handler.
- Smoke: `./venv/bin/python -c "from handlers.mission_admin_handlers import admin_missions_menu, create_mission_start, process_mission_name, ..., select_frequency, select_reward_for_mission, confirm_create_mission, list_missions, mission_admin_detail, show_mission_detail, delete_mission_confirm, missions_stats, mission_detail_stats, toggle_mission, compute_mission_wizard_step_text, build_mission_confirm_text_and_keyboard, build_reward_select_buttons, compute_reward_summary_for_confirm, build_mission_list_entry_and_button, build_mission_detail_text_and_keyboard, build_mission_delete_confirm_keyboard, build_mission_stats_text_and_buttons, compute_freq_text, compute_reward_text; from services.mission_service import MissionService; print('ok'); print(hasattr(MissionService, 'get_all_rewards_for_mission_wizard'))"`
- Inspect LOC: `python -c 'import inspect; from handlers.mission_admin_handlers import ... list all ... ; for name, fn in [...]: src=inspect.getsourcelines(fn)[0]; print(name, "LOC:", len(src)); assert len(src) <= 50'` → all <=50.
- Grep: `grep -n "RewardService\|from services.reward_service import RewardService" handlers/mission_admin_handlers.py` → 0 (active); `grep -n "with get_service(MissionService)" ...` (count >=9 post); `grep -n "def compute_mission_wizard_step_text\|def build_mission_confirm...\|def build_reward_select...\|def build_mission_detail...\|def build_mission_list...\|def build_mission_delete...\|def build_mission_stats...\|def compute_freq_text\|def compute_reward..." ...` presente.
- (Los tests funcionales del handler se gatean en F4; aquí basta que el módulo cargue, helpers sean callables, delegates exist, LOC ok, greps pass, UI strings in puros via spot if added. Un test spot de refresh si aplica pero tight: no requerido.)

**Riesgos + mitigaciones:**
- Riesgo: UI / render divergence after extract (step texts, confirm summaries, reward buttons, list entries, detail text/kb, delete confirm, stats, "Paso X de 6", "Resumen de la mision:", "No hay...", backs, cb data, truncation, freq, status, "Sin descripcion"/"Ninguna") → Mit: extraction is pure copy-paste of logic to new def; new helper tests in F4 have exact string/math/cb/row/label/back asserts (copy from existing handler tests + impact "cover ... for wizard step texts, confirm summaries (with/wo desc/reward), keyboard row counts + exact button labels + cb ids + back targets, ... list entries, freq, 0/edge cases"); re-run full Test* classes in F4; keep all consts.
- Riesgo: LOC sigue =50+ por docstring/boilerplate → Mit: trim docstring del helper (mantener contrato) + comentario "extracted for <=50 LOC rule (Item 9 / arch-enforcer)", precedente item8/7/25/26 F3; usar inspect en gate.
- Riesgo: logging nuevo introduce ruido → Mit: seguir exactamente el patrón de item8/7/25/26 / otros handlers ("módulo | acción | user_id= | resultado"); mismo logger.
- Riesgo: rel access None cases or delegate empty → Mit: guard "if not rewards" / "if not reward" / "if mission.reward" ya presente + tests F4 cubren los paths (precedent item7/8 + impact).
- Riesgo: wizard FSM / state transitions break (Paso X, set waiting_*/selecting_*/confirming, clear) → Mit: puros no tocan state/FSM; solo text/kb; the with/delegate calls stay in entrypoints; tests F4 pin state + text.

**Safe point:** Post-ruff + LOC<=50 verificado via inspect + grep 0 RewardService (active) + count withs >=9 + new puros defs + GSD "F3 safe point - all long funcs + helpers <=50 via pure helpers (compute_mission_wizard_step_text + build_mission_* + compute_*); 1 service only via MissionService get_service + delegates for reward wizard steps (select_frequency/select_reward_for_mission); rel used in detail; UI render identical; logging compliant". El handler recompila; tests de F4 validarán el contrato observable + ports. Reversible editando solo este archivo (o inlining los helpers).

---

### Fase 4: Port/actualización de tests de mission_admin_handlers + agregar tests para helpers puros extraídos

**Objective:** Actualizar/confirmar `test_mission_admin_handlers.py` para que los tests reflejen (y protejan) el diseño "exactly 1 service" + delegates for reward wizard + pure helpers. Port the ~12 RewardService patches in TestSelectFrequency + TestSelectRewardForMission (and any residual) to get_service(MissionService) + delegate mocks + __enter__/__exit__ + asserts on mission_svc; update/refresh docstrings. Añadir clase `TestMissionAdminPureHelpers` (o equivalente) con unit tests puros para los helpers extraídos (sin parches pesados; import inside per convención de archivos de test; cubrir branches de step texts, confirm summaries w/wo desc/reward, kb builds w/ exact labels/rows/cbs/backs, list entries, detail (rel/None), freq, reward summary, 0/edge/empty). Remover cualquier residual 2-svc language. Ruff + full suite del archivo verde (comportamiento idéntico). GSD pre. Safe point.

**DoD checklist:**
- [ ] 0 parches de `RewardService` en el archivo de tests (ni @patch ni referencias directas en setups/asserts para las funciones bajo test; post-port grep count 0 active, even unfiltered; residual NOTE/historical ok if commented "pre-Item9 / direct RewardService in wizard").
- [ ] Todos los tests (incl los ported select freq/reward + confirm/list/etc) usan `@patch("handlers.mission_admin_handlers.get_service")` + `mock_get_service.return_value.__enter__.return_value = mock_mission_svc` + `__exit__` asserts en closes (use mock_context.__enter__.return_value pattern already in file for other classes).
- [ ] Setups para ported tests configuran `mock_mission_svc.get_all_rewards_for_mission_wizard.return_value = []` or `[mock_reward with .id/.name/.reward_type]` (etc) + `mock_mission_svc.get_reward_for_mission_wizard.return_value = mock_reward or None`; para paths de detail/list si puros usan rel: `mock_mission.reward = mock_reward` (with .name/.reward_type etc) or `.reward = None`; no reward_svc.
- [ ] Tests de close usan patrón de context (`__exit__` assert) per mission precedent + item7/8/25/26 F4.
- [ ] Docstrings de clases actualizadas/confirmadas: "Tests ported to 1-service pattern (get_service(MissionService) only + delegate for reward wizard steps. Arch-enforcer note addressed. Precedent from item7/8." (module + TestSelectFrequency + TestSelectRewardForMission + others if needed; keep/refresh existing "ported..." for consistency).
- [ ] Nueva clase `TestMissionAdminPureHelpers` (or Test*PureHelpers): tests unitarios para los helpers extraídos (al menos 5-10+ casos: wizard step texts Paso 1-6 exact + w/wo example + Lucien headers; confirm summaries with/without desc/reward ("Resumen de la mision:", "Sin descripcion", "Ninguna", freq "Una vez"/"Recurrente", full data); keyboard builds (row counts e.g. rewards+1 cancel, exact button texts "✅ Crear"/"❌ Cancelar"/"🔙 Volver", back targets "admin_missions"/"list_missions", cb packing e.g. SelectRewardMissionCallback(reward_id=xx).pack() contains "select_reward_mission:xx" or ==, MissionDetailCallback etc); list entry (status ✅/❌ + name (type), button text status+name[:30] + Detail cb); detail text+kb (with rel reward or None "Sin recompensa", 3 rows toggle/delete/back "list_missions"); delete confirm kb (2 buttons si/no with confirmed + back); stats text+buttons (counts + active "📊 name[:30]" + back "admin_missions"); freq/reward text if extracted; 0/50/100 edges, empty cases ("No hay..."), truncation; import inside test funcs per convención del archivo).
- [ ] Todos los asserts de texto, llamadas a edit_text/answer, y parámetros de servicio (user_id, mission_id, calls to create_mission/get_all_missions(active_only=False)/get_mission_stats/get_mission etc + the new delegate calls in ported tests) se mantienen y pasan (comportamiento idéntico).
- [ ] Ruff limpio en el test.
- [ ] GSD pre + gate: la suite completa del archivo pasa verde.
- [ ] Safe point.

**Archivos:** `tests/handlers/test_mission_admin_handlers.py`

**Cambios clave (bullets accionables, por clase; copiar al pie de la letra de item8/7/25 F4 port + test_mission_user / test_store_admin precedent):**
- Pre-log GSD "pre-edit tests/handlers/test_mission_admin_handlers.py (F4 add pure helper tests + confirm ports) - refs DoD F4 + copy from item8/7/25/26 PLAN F4 (get_service patch, __enter__/__exit__, mock_mission_svc.get_all_rewards_for_mission_wizard.return_value = [mock with .id/.name/.reward_type], .get_reward_for_mission_wizard.return_value = ..., assert on mission_svc not reward_svc, docstrings 'ported to 1-service (MissionService) only + delegate for reward wizard steps. Arch-enforcer note addressed. Precedent from item7/8.', closes to __exit__, NOTES cleaned, RewardType? if needed for puros but use MagicMock attrs) + item8/7 F5 Test*PureHelpers class (5-10+ tests, import inside); read pre done".
- Añadir/confirmar al top si needed (from models.models import ... but for puros use MagicMock or simple; the file already imports MissionFrequency/MissionType).
- En TestSelectFrequency y TestSelectRewardForMission (y cualquier otra con RewardService patch): 
  - Cada test: `@patch("handlers.mission_admin_handlers.get_service")` (reemplaza el RewardService patch)
  - `mock_mission_svc = MagicMock(); mock_context = MagicMock(); mock_context.__enter__.return_value = mock_mission_svc; mock_get_service.return_value = mock_context`
  - Para freq (no_rewards/with_rewards): `mock_mission_svc.get_all_rewards_for_mission_wizard.return_value = []` or `[mock_reward]`
  - Para reward select (shows_summary/una_vez/recurrente/missing_desc/missing_reward): `mock_mission_svc.get_reward_for_mission_wizard.return_value = mock_reward` or None
  - Closes: `mock_get_service.return_value.__exit__.assert_called_once()`
  - Asserts on mission methods only (get_all_rewards_for_mission_wizard(active_only=True) or without if sig, get_reward_for_mission_wizard(reward_id), create_mission etc); no reward_svc; keep exact data/text/state asserts + "No hay recompensas" / "Resumen de la mision:" / "Una vez" / "Ninguna" / "Sin descripcion" / "Recurrente" / "Paso 6 de 6" etc.
- En otras clases (TestAdminMissionsMenu, TestCreate..., TestProcess..., TestConfirmCreate..., TestListMissions, TestMissionAdminDetail, TestToggle, TestDelete, TestMissionsStats, TestMissionDetailStats): confirmar/refresh que ya usan get_service(Mission) + __enter__/__exit__ + mock_mission_svc setups for get_mission/get_all_missions(active_only=False)/create_mission/get_mission_stats etc; si algún hack o NOTE historical, dejar o limpiar como en precedents.
- Añadir al final del archivo (después de la última clase o inline MissionWizardStates class; patrón de item8/7/25 F5):
  ```python
  class TestMissionAdminPureHelpers:
      """Tests para los helpers puros extraídos de mission_admin_handlers (Item 9 / arch-enforcer LOC)."""

      def test_compute_mission_wizard_step_text_paso1(self):
          from handlers.mission_admin_handlers import compute_mission_wizard_step_text
          text = compute_mission_wizard_step_text(1, "Nombre de la mision", "Indica un nombre descriptivo:")
          assert "Paso 1 de 6: Nombre de la mision" in text
          assert "Indica un nombre descriptivo" in text
          assert "🎩 Lucien" in text

      def test_compute_mission_wizard_step_text_with_example(self):
          from handlers.mission_admin_handlers import compute_mission_wizard_step_text
          text = compute_mission_wizard_step_text(4, "Valor objetivo", "Indica un numero:", "Ejemplo: 10")
          assert "Paso 4 de 6" in text
          assert "Ejemplo: 10" in text

      def test_build_mission_confirm_text_and_keyboard_full(self):
          from handlers.mission_admin_handlers import build_mission_confirm_text_and_keyboard
          from models.models import MissionFrequency, MissionType
          data = {"name": "Test Mision", "description": "Desc", "mission_type": MagicMock(value="reaccion"), "target_value": 10, "frequency": MissionFrequency.ONE_TIME}
          reward = MagicMock(name="Recompensa X", reward_type=MagicMock(value="besitos"))
          text, kb = build_mission_confirm_text_and_keyboard(data, reward)
          assert "Resumen de la mision:" in text
          assert "📋 Nombre: Test Mision" in text
          assert "📝 Descripcion: Desc" in text
          assert "🎁 Recompensa: Recompensa X (besitos)" in text
          assert "✅ Crear" in kb.inline_keyboard[0][0].text
          assert "admin_missions" in kb.inline_keyboard[1][0].callback_data

      def test_build_mission_confirm_text_and_keyboard_no_desc_no_reward(self):
          from handlers.mission_admin_handlers import build_mission_confirm_text_and_keyboard
          data = {"name": "Test", "description": None, "mission_type": MagicMock(value="reaccion"), "target_value": 5, "frequency": MissionFrequency.RECURRING}
          text, kb = build_mission_confirm_text_and_keyboard(data, None)
          assert "Sin descripcion" in text
          assert "Ninguna" in text
          assert "Recurrente" in text

      def test_build_reward_select_buttons(self):
          from handlers.mission_admin_handlers import build_reward_select_buttons
          from keyboards.callback_data import SelectRewardMissionCallback
          r1 = MagicMock(id=1, name="R1", reward_type=MagicMock(value="besitos"))
          r2 = MagicMock(id=2, name="R2", reward_type=MagicMock(value="paquete"))
          buttons = build_reward_select_buttons([r1, r2])
          assert len(buttons) == 3  # 2 rewards + cancel
          assert "R1 (besitos)" in buttons[0][0].text
          assert "R2 (paquete)" in buttons[1][0].text
          assert "select_reward_mission:1" in buttons[0][0].callback_data
          assert "admin_missions" in buttons[2][0].callback_data

      def test_build_mission_list_entry_and_button(self):
          from handlers.mission_admin_handlers import build_mission_list_entry_and_button
          from keyboards.callback_data import MissionDetailCallback
          m = MagicMock(id=42, name="Mi Mision Larga Nombre Para Truncar", mission_type=MagicMock(value="reaccion"), is_active=True)
          text, button = build_mission_list_entry_and_button(m)
          assert "✅" in text
          assert "Mi Mision Larga Nombre Para Truncar (reaccion)" in text
          assert "✅ Mi Mision Larga Nombre Para Truncar"[:33] in button.text or "✅ Mi Mision Larga Nombre Para Truncar"[:30] in button.text  # truncation
          assert "42" in button.callback_data

      def test_build_mission_detail_text_and_keyboard_with_reward(self):
          from handlers.mission_admin_handlers import build_mission_detail_text_and_keyboard
          from keyboards.callback_data import MissionToggleCallback, MissionDeleteCallback
          m = MagicMock(id=7, name="Detail M", description="D", mission_type=MagicMock(value="reaccion"), target_value=10, frequency=MagicMock(value="one_time"), is_active=True)
          m.reward = MagicMock(name="Rew", reward_type=MagicMock(value="besitos"))
          text, kb = build_mission_detail_text_and_keyboard(m)
          assert "📋 Detail M" in text
          assert "Sin descripcion" not in text
          assert "🎁 Recompensa: Rew (besitos)" in text
          assert "Desactivar" in kb.inline_keyboard[0][0].text
          assert "list_missions" in kb.inline_keyboard[2][0].callback_data

      def test_build_mission_detail_text_and_keyboard_no_reward(self):
          from handlers.mission_admin_handlers import build_mission_detail_text_and_keyboard
          m = MagicMock(id=8, name="NoRew", description=None, mission_type=MagicMock(value="reaccion"), target_value=5, frequency=MagicMock(value="recurring"), is_active=False)
          m.reward = None
          text, kb = build_mission_detail_text_and_keyboard(m)
          assert "Sin descripcion" in text
          assert "Sin recompensa" in text
          assert "Activar" in kb.inline_keyboard[0][0].text

      def test_build_mission_delete_confirm_keyboard(self):
          from handlers.mission_admin_handlers import build_mission_delete_confirm_keyboard
          from keyboards.callback_data import MissionDeleteCallback
          kb = build_mission_delete_confirm_keyboard(99)
          assert len(kb.inline_keyboard) == 2
          assert "si" in kb.inline_keyboard[0][0].text.lower() or "✅" in kb.inline_keyboard[0][0].text  # or exact "Sí"
          assert "99" in kb.inline_keyboard[0][0].callback_data  # confirmed=True path
          assert "list_missions" in kb.inline_keyboard[1][0].callback_data or "detail" in kb.inline_keyboard[1][0].callback_data.lower()

      def test_compute_freq_text(self):
          from handlers.mission_admin_handlers import compute_freq_text
          from models.models import MissionFrequency
          assert compute_freq_text(MissionFrequency.ONE_TIME) == "Una vez"
          assert compute_freq_text(MissionFrequency.RECURRING) == "Recurrente"

      # + casos para build_mission_stats_text_and_buttons (counts + active buttons + back), compute_reward_text if extracted, edges 0/empty, truncation exact, cb pack exact match or contains
  ```
- (Usar import inside test funcs para seguir el patrón del archivo, que hace `from handlers.mission_admin_handlers import ...` dentro de cada test.)
- Post-add: ruff check + format (apply si dirty); full pytest del archivo; grep residual RewardService ==0 (active); asserts de textos idénticos + delegate calls in ported tests.

**Tests que deben pasar antes de avanzar:**
- `./venv/bin/python -m pytest tests/handlers/test_mission_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` → todos verdes (comportamiento idéntico: mismos textos, calls to mission_svc only incl delegates in ported, alerts, params, __exit__).
- Ruff en el test file.
- Grep: `grep -n "RewardService" tests/handlers/test_mission_admin_handlers.py | grep -v "NOTE\|arch-enforcer\|pre-existing"` → preferiblemente 0; get_service patches + new helper tests presentes.

**Riesgos + mitigaciones:**
- Riesgo: tests que confiaban en mocks de RewardService ahora ejecutan delegates via get_service mock y fallan por attrs faltantes o call sig → Mit: configurar explícitamente `mock_mission_svc.get_all_rewards_for_mission_wizard.return_value = [...]` con mocks que tengan .id .name .reward_type (ya hecho en tree patterns + item8/7 F4); 5-10 min por test pero precedentes existen.
- Riesgo: el test "without reward" or empty falla porque MagicMock.reward is truthy → Mit: setear explícitamente `.reward = None` (documentado en item7/8 + impact).
- Riesgo: nuevos helper tests fallan por nombre/firma o UI string drift → Mit: nombres confirmados en F3 GSD1 + sección 4 del PLAN; UI pins exact from impact + current asserts copied to pure tests; ajustar en F4 primer GSD si difiere (mantener espíritu).
- Bajo: import inside for puros (per file conv; already used for handler funcs in tests).

**Safe point:** Suite de mission_admin_handlers verde post-F4 (incl nuevos pure tests + ports) + ruff + GSD "F4 safe point - mission admin handler tests confirmed ported to 1-service + delegates for reward wizard + new TestMissionAdminPureHelpers added + pass; arch-enforcer notes addressed; behavior identical". Confirma que el render de wizard/list/detail/stats/delete/confirm (y helpers) + reward select cross es idéntico. Reversible restaurando setups viejos (pero no necesario).

---

### Fase 5: Re-runs de golds + verificación final de reglas + self-check + handoff (primero de nuevo pool de 4; pool anterior cerrado)

**Objective:** Re-ejecutar los golds que protegen el flujo de misiones admin + reward wizard cross (handler test full + cross flows mission/reward + reward get_all/get_reward gold que ejercita los reales que los delegates llaman + bot smoke). Verificar reglas (1 service Mission only via get_service + delegates for reward wizard, LOC<=50 via inspect, logging, pure helpers, 0 RewardService active in handler). Completar GSD log con self-check PASSED explícito + lista de "tests críticos a re-correr en futuro". Confirmar en self-check/PLAN: "este es el primero de un nuevo pool de 4, y que el pool anterior de 4 quedó cerrado con tests pasando" (citar 26/25 SUMMARY "Item 8/26 closed. Second of new pool..." + "Item 7/25 closed. First of new pool..." + their self-check PASSED + BATCH/POOL notes + re-runs verdes). Handoff a arch-enforcer/test-guardian + gsd-executor del siguiente item del pool. Safe point final.

**DoD checklist:**
- [ ] Re-runs: full `pytest tests/handlers/test_mission_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` green; targeted cross `pytest -k "mission_admin or admin_missions or TestMissionAdmin or TestMissionAdminPureHelpers or build_ or compute_ or select_reward or select_frequency or mision or reward" -q --tb=line -p no:cov --override-ini="addopts="` (o más amplio filtrado; documentar pre-exist unrelated); reward unit gold `pytest tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "get_all_rewards or get_reward or active_only"`; bot smoke `python -c "from handlers.mission_admin_handlers import *; print('imports ok')"` (or equiv with venv fallback per 25/26 precedent) PASS "imports ok" + "bot import + routers (incl mission_admin) equivalent smoke PASS".
- [ ] Ruff limpio en los 3 archivos tocados.
- [ ] Verificación de reglas (grep/inspect manual + en log):
  - `grep -n "RewardService\|from services.reward_service import RewardService" handlers/mission_admin_handlers.py` → 0 (active).
  - `python -c 'import inspect; from handlers.mission_admin_handlers import ... list long + puros ...; for name, fn in [...]: print(name, "LOC:", len(inspect.getsourcelines(fn)[0]))'` → all <=50.
  - Logging formato "mission_admin_handlers | ..." presente en key withs (spot o grep; e.g. list/confirm/stats/create).
  - get_service(MissionService) + with + delegates (get_all_rewards_for_mission_wizard / get_reward_for_mission_wizard) + puros en handler; helpers puros usados + tests added (5-10+ in TestMissionAdminPureHelpers); with count >=9.
  - 1 service rule + <=50 + logging + pure helpers + no biz logic en handler.
- [ ] GSD entries completas para F5 + log final con self-check PASSED + estructura completa (lista de fases/DoD/gates/archivos modificados/tests que pasaron/reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0 behavior chg in mission/reward create/delivery/atomic/held, 1svc Mission via get_service + delegates for reward wizard, LOC<=50 via inspect, logging, pure helpers tests 5-10+ import-inside, no prod chg)/desviaciones (ruff pre-exist hygiene in test only documented not regression per 26/25 precedents "do not count as regression", pre-exist pytest warns/xfails not attributable)/tests críticos para futuro (mission admin handler test full, reward get_all/get_reward gold, -k "mission_admin or admin_missions or TestMissionAdmin or TestMissionAdminPureHelpers or build_ or compute_ or select_reward or select_frequency", ruff+LOC/grep verifiers (0 RewardService handler, inspect entrypoints+helpers <=50, logging format, helpers, get_service count, delegate/pure comments svc), bot smoke "from handlers.mission_admin_handlers import *", combined critical)/"Item 9/27 closed. First of new pool of 4. Previous pool closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en mission_admin_handlers: exactly 1 service + <=50L + no direct RewardService + puros + ports + UI1:1 + logging) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4.").
- [ ] Self-check explícito "Self-Check: PASSED".
- [ ] (Opcional pero recomendado) SUMMARY.md en el dir de la phase con executive + refs al log + comandos de re-verif (sigue estructura de 26/25/24/23/20/19).
- [ ] Safe point final + criterio de éxito del plan.

**Archivos:** Ninguno nuevo (solo log + opcional SUMMARY; los edits ya hechos en F2-F4).

**Cambios clave:** Solo ejecución de comandos (ver Instrucciones) + echo al log. Usar run_terminal para los gates finales + conteos + greps + self-check append.

**Tests gates (obligatorios):**
- Los re-runs targeted + full handler test.
- Ruff global en los 3.
- Greps + inspect LOC + smoke bot.
- GSD pre cada + "F5 FINAL + self-check PASSED + BATCH/POOL note".

**Riesgos + mitigaciones:**
- Riesgo: re-runs muestran flakes preexistentes (no causados por este Item) → Mit: usar -p no:cov --override-ini; documentar si hay 1 unrelated fail (precedente 26/25/24/23/22); enfocar "0 regressions atribuibles a los helpers o ports".
- Riesgo de tiempo: chains de integración lentas → Mit: priorizar targeted del handler test primero, luego -k específicos de mission/reward; el PLAN permite targeted combinados.
- Ninguno nuevo (verif final; scope tight).

**Safe point final + criterio de éxito:** Todos DoD de F5 + self-check PASSED en log con la nota explícita de "primero de nuevo pool de 4" + "pool anterior de 4 cerrado con tests pasando". El plan completo + log GSD son evidencia para el siguiente agente (gsd-executor next item o arch-enforcer/test-guardian). 0 breakage; UI idéntica; reglas cumplidas; 3 sistemas críticos (gamif/missions/rewards etc.) protegidos (read-only config + orthogonal admin create; re-runs protect).

---

## 3. Estrategia de tests general (port + nuevos + re-runs)

**Confirmación de ports en test_mission_admin_handlers (F4, ya en tree patterns pero refresh):**
- Seguir exactamente el patrón de `tests/handlers/test_store_admin_handlers.py` (post item8) + item7/25 F4 port (get_service patch, mock_get_service.return_value.__enter__.return_value = mock_instance, asserts en __exit__.assert_called (o en el mock_context), remoción de parches a RewardService (0 post), mantener todos los asserts de UI (edit_text, answer, textos producidos como "Paso 1 de 6"/"Resumen de la mision"/"No hay recompensas configuradas..."/"No hay misiones registradas."/"Sin descripcion"/"Ninguna"/"Sin recompensa"/"Una vez"/"Recurrente"/"Mision creada exitosamente", botones/callbacks) idénticos.
- Configurar los mocks de mission_svc con los delegates: `mock_mission_svc.get_all_rewards_for_mission_wizard.return_value = [mock_reward]` (mock_reward with .id/.name/.reward_type=RewardType.XXX or MagicMock(value=...)); `mock_mission_svc.get_reward_for_mission_wizard.return_value = mock_reward or None`.
- Para paths de detail/list si puros tocan rel: `mock_mission.reward = mock_reward` (with .name/.reward_type etc) or `.reward = None` explícitamente (precedent item7/8 + impact).
- Actualizar/confirmar docstrings de clases a "Tests ported to 1-service pattern (get_service(MissionService) only + delegate for reward wizard steps. Arch-enforcer note addressed. Precedent from item7/8." (ya patterns en tree post priors; asegurar que residual "2-svc" o "closes_both" language está limpia). Dejar comentario histórico breve si se desea ("pre-Item 9 this had direct RewardService() in select_frequency/select_reward_for_mission wizard steps; now 1-service per arch-enforcer remediation").

**Nuevos tests para pure helpers extraídos (F4):**
- Ubicación: `tests/handlers/test_mission_admin_handlers.py` (mismo archivo; mantiene todo co-localizado y evita nuevos archivos per scope tight + precedent item8/7 F5).
- Enfoque: unit tests puros del helper (datos de entrada falsos con MagicMock mínimos o simples objetos/dicts/ints; no service mocks necesarios para los helpers mismos; import inside test funcs per convención del archivo).
- Casos mínimos (copiar espíritu de TestStoreAdminPureHelpers 9 tests + TestRewardUserPureHelpers 5+ + item2 F5 TestCalculate... + impact "cover wizard step texts, confirm summaries (with/wo desc/reward), keyboard row counts + exact button labels + cb ids + back targets, reward summary/emoji if, list entries, freq, 0/edge cases"):
  - compute_mission_wizard_step_text paso1-6 exact match incl "Paso X de 6: Nombre...", "Paso X de 6: Frecuencia", Lucien header, /skip notes, with/wo example.
  - build_mission_confirm_text_and_keyboard full data + None desc -> "Sin descripcion", reward=None -> "Ninguna", freq ONE_TIME/RECURRING -> "Una vez"/"Recurrente", "Resumen de la mision:" present, kb row 2 ("✅ Crear" / "❌ Cancelar" with "admin_missions").
  - build_reward_select_buttons([r1,r2]) -> len(rows)==3 (rewards+1 cancel), exact text f"{name} ({type.value})", cb data contains "select_reward_mission:xx", back "admin_missions".
  - build_mission_list_entry_and_button(m) -> text has "✅"/"❌" + name + (type), button text status+name[:30], cb MissionDetail pack contains id, back "admin_missions".
  - build_mission_detail_text_and_keyboard(with reward rel) -> "📋 name", "📝 desc or Sin descripcion", bullets with type/target/freq/estado ✅/❌, "🎁 Recompensa: name (type) or Sin recompensa", kb 3 rows (toggle "Desactivar|Activar", "🗑️ Eliminar", back "list_missions").
  - build_mission_detail_text_and_keyboard(no reward) -> "Sin recompensa".
  - build_mission_delete_confirm_keyboard(id) -> 2 buttons (si/no with confirmed=True/False + back to detail or list_missions).
  - build_mission_stats_text_and_buttons or equiv (counts active/total, buttons for active "📊 name[:30]" + back "admin_missions").
  - compute_freq_text(ONE_TIME) == "Una vez", RECURRING == "Recurrente".
  - compute_reward_text or summary (with/None).
  - 0/edge/empty ("No hay misiones registradas.", "No hay recompensas configuradas..."), truncation name[:30] exact.
  - (si un helper render toca emoji/status) real via mock attrs or direct call.
- Estos tests sirven como "test-guardian" para los helpers: cualquier refactor futuro del render/wizard de missions/reward select debe pasar estos + UI asserts en handler tests.

**Re-runs de golds (F5, y spot en F1/F3/F4):**
- Handler level: `pytest tests/handlers/test_mission_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="`
- Cross / mission-reward flows (gold paths que ejercitan list/detail/confirm/wizard reward select + reward data): `pytest -k "mission_admin or admin_missions or TestMissionAdmin or TestMissionAdminPureHelpers or build_ or compute_ or select_reward or select_frequency or mision or reward" -q --tb=line -p no:cov --override-ini="addopts="` (filtrar; documentar pre-exist unrelated como daily concurrent o alembic per precedent 26/25/24/23).
- Reward get_* gold: `pytest tests/unit/test_reward_service.py ... -k "get_all_rewards or get_reward or active_only"` (exercises the real that delegates passthrough to; 0 impact).
- Objetivo: confirmar que el código de render (ahora delegando a puros) + wizard reward select (via delegates) produce los mismos textos, botones, alerts, cbs, empty cases, y que los calls a servicio siguen siendo solo MissionService via get_service + delegates for the cross reward wizard steps.
- (Nota: los tests de integración actuales pueden no asertar el contenido exacto del UI de missions/reward wizard directamente; para "idéntico" el executor usa los asserts existentes del handler test + nuevos pure tests que pin strings/math/cbs/rows/labels/backs + re-runs de chains protegen indirectamente via mission/reward data paths.)

**Gates generales por fase / final:**
- Ruff: `./venv/bin/python -m ruff check <file> --fix` ; luego `./venv/bin/python -m ruff format --check <file>` (o apply en pre si se sigue el precedente de ruff pre-edit + hygiene como chore separado 0 logic).
- Pytest targeted limpio (sin cov para exit code estable): siempre con `-p no:cov --override-ini="addopts="` (precedente establecido en todos los golds 20/21/23/24/25/26 + item logs).
- Grep de reglas: 0 "RewardService" (active import/use) en mission_admin_handlers.py; LOC de todos los target + puros <=50 via inspect; imports de get_service + delegates + puros presentes; logging formato presente (spot); helpers puros usados + tests.
- (Opcional para executor) smoke de bot import o registro de routers si se quiere (`python -c "import bot; from handlers.mission_admin_handlers import *; print('ok')"` o equivalente para mission_admin router), pero mínimo es el handler test + cross targeted + reward get_* gold.
- Cobertura de logging requirement: los tests no asertan logs usualmente (salvo en middleware tests); el gate es manual grep o inspección durante las ediciones + inclusión en el log de GSD.
- Pre-exist in broader: 1 warning (pre), deselected many (pre); tolerated + doc per PLAN + precedent. Documented; 0 counted as regression of this Item.
- 0 attributable to this Item: all pre-exist (ruff hygiene in patched hack per PLAN explicit stay if any, bottom import per file conv, MovedIn20, other warns from priors).

---

## 4. Decisiones de diseño que el executor debe confirmar (o registrar desviación en el primer GSD entry de la fase relevante)

1. **Nombres de los helpers puros extraídos:** `compute_mission_wizard_step_text(step: int, title: str, prompt: str, example: Optional[str] = None) -> str`, `build_mission_confirm_text_and_keyboard(data: dict, reward: Optional[Reward] = None) -> Tuple[str, InlineKeyboardMarkup]`, `build_reward_select_buttons(rewards: list[Reward]) -> list[list[InlineKeyboardButton]]`, `compute_reward_summary_for_confirm(reward: Optional[Reward]) -> str` (or inline name), `build_mission_list_entry_and_button(mission: Mission) -> Tuple[str, InlineKeyboardButton]`, `build_mission_detail_text_and_keyboard(mission: Mission) -> Tuple[str, InlineKeyboardMarkup]` (dedupes show + detail), `build_mission_delete_confirm_keyboard(mission_id: int) -> InlineKeyboardMarkup`, `build_mission_stats_text_and_buttons(missions: list[Mission]) -> Tuple[str, list[list[InlineKeyboardButton]]]`, `compute_freq_text(frequency: MissionFrequency) -> str`, `compute_reward_text(reward: Optional[Reward]) -> str` (exact per PLAN rec + impact + verb+context+result conv; cf. compute_stock_emoji_and_text / build_* in item8, compute_reward_status_text / build_reward_detail_keyboard in item7, calculate_... in item2 / codebase). Confirmar o elegir alternativa equivalente en primer GSD de F3; documentar. Si se extrae un tercero (e.g. para button text en list o status emoji), nombre similar y cubrir en tests.
2. **Delegate backward-compatible for get_all_rewards_for_mission_wizard / get_reward_for_mission_wizard:** Added in F2 with exact docstrings + arch comments per impact; 1-line/min support if pattern; delegates at module or in class; "Thin delegate... Added for item9: enables mission_admin_handlers ... exactly 1 service (MissionService)..." exact per impact; arch "# Support added for mission_admin_handlers 1-service + pure extract (item9). Arch-enforcer long-funcs note addressed. Precedent item7 (reward) + item8 (store-admin)."; transparent passthrough using RewardService(db=self._get_db()) (mission_svc already imports RewardService for other paths; keep pattern).
3. **Logging en los handlers editados:** Agregar/confirmar logs en formato "módulo | acción | user_id=... | resultado=..." para list_missions (con count), confirm_create_mission (con mission_id + name), missions_stats (con counts), mission_admin_detail/toggle/delete (con mission_id + resultado), y otros paths clave dentro del with post-data. Si los handlers actualmente delegan logging a middleware, mínimo es asegurar el log existente dentro del with post-data. Confirmar formato con ejemplos de item8/7/25/26 / otros (e.g. "mission_admin_handlers | list_missions | user_id=123 | count=5").
4. **Patrón de tests para puros + delegates port:** Ejecutar real puros (import inside) con MagicMock o dicts/ints para inputs (preferred for "pure" semantics + simplicity; like item8 real compute_stock with ints/bools, item7 real get_reward_emoji via .reward_type attrs); for builders: pure unit tests (import inside, MagicMock minimal or simple objs; no service mocks for the helpers themselves; no @patch on the helper in handler tests (handler test covers full flow via real)). For port of select: mock_mission_svc.get_all_rewards_for_mission_wizard.return_value = [mock_reward with .id/.name/.reward_type]; .get_reward_for_mission_wizard.return_value = mock_reward or None; assert on the mission mock call (not reward_svc). Followed item8/7/25 F4/F5 + impact port instructions exactly. 5-10+ tests >5 min.
5. **Chequeo de relationship en mission detail puros:** Mantener `if mission.reward:` (or equiv in build_mission_detail_text_and_keyboard) (consistente con current + item7 precedent in reward_user + mission_user_handlers.py); mensaje "Sin recompensa"; no agregar chequeos de is_active en el handler (scope tight; list filters in service).
6. **Conteo estricto de ≤50 LOC:** Usar `inspect.getsourcelines(func)[0]` (cuenta líneas de la def inclusive) per PLAN + item8/7/25 F3/F5 + item2 F3; post-extract max <=50 (target < for wizard/list/detail etc; if boilerplate 51 aplicar trim de docstring del helper (mantener contrato) + comentario de "extracted for LOC rule (Item 9 / arch-enforcer)", precedente de item8/7/25/26 F3 + credit_besitos en Item1 + handle_reaction en item2). No dejar >50. Verificar post-F3 y en F5 final.
7. **Actualización de docstrings de mission admin tests:** Confirmar/refresh (ya "ported to 1-service..." patterns post-priors; asegurar que residual "2-svc" o "closes_both" language está limpia). Actualizar TestSelectFrequency/TestSelectRewardForMission + module a "Tests ported to 1-service pattern (get_service(MissionService) only + delegate for reward wizard steps. Arch-enforcer note (long funcs >50L, business logic/UI bloat in handlers, direct other svc in reward select wizard steps) addressed. Precedent from item7 (reward) + item8 (store_admin)."; dejar comentario histórico breve si se desea ("pre-Item 9 this orchestrated RewardService directly in select_frequency/select_reward_for_mission; now 1-service per arch-enforcer remediation").
8. **Log file para GSD de Item 9:** Usar `.planning/quick/gsd-mission-admin-long-funcs.log` (o el item9 completo si el analyzer usó gsd-impact-analyzer-item9-mission-admin-long-funcs.log; cross-ref ambos). Cada pre-edit/pre-gate/pre-verif debe hacer `echo "=== $(date -Iseconds) | PHASE N | GSD pre-... - <descripción corta refs DoD + patrones copiados>" >> <logfile>"` (o usar run_terminal_command con comando echo/printf). Al final del Item, el log debe tener entradas para cada acción significativa (como los 40+ de Item 7, many de Item 8) + self-check PASSED + BATCH/POOL note.
9. **Si se necesita un segundo (o tercer) helper para render en missions:** Min 5-8+ como listados en impact/PLAN (wizard step/confirm/reward buttons/list entry/detail (dedupe)/delete kb/stats/freq/reward text); si más needed para hit <=50 (e.g. additional for show_mission_detail dupe elim), extract; tight scope prioriza mínimo pero suficiente para la regla. Documented (no more extracted if not needed).
10. **No exportar la pura/delegate en services/__init__.py:** Confirmado por scope (import directo del módulo es suficiente y usado en el codebase + item7/8/25; no editar __init__).
11. **Uso de model rels vs pure:** Confirmado use of mission.reward in detail puros/build (precedent item7/8 + current code at 503/575); puros for formatting/text/kb only (model status str + svc stats are different contracts); visual + smoke + tests pin; out of scope to consolidate further per impact "low" risk note.
12. **Cualquier decisión que difiera:** Registrar en el GSD log + (si se permite fuera de scope estricto) en una nota breve al final del PLAN o en SUMMARY posterior. Elegir conservadoramente siguiendo precedentes (item8/7/25 ports + helper extract + LOC inspect + self-check + BATCH/POOL, item2/5/6 pure + delegate comment + 1-line + port desc tests + Test*PureHelpers, impact exact code blocks for delegate/pure + port instructions + "first of new pool", 26/25 BATCH language, get_service context + __enter__/__exit__ mocks, real pure via attrs or direct ints, docstrings "ported...", 1-line/min support + delegate comment exact, inspect LOC, UI 1:1 strings pinned, commands exact -p no:cov..., 3 crit in mind, scope tight 0/0/0/0). Registrada en GSD entry of the phase + note in self-check.

Cualquier decisión que difiera de lo anterior debe registrarse en el GSD log + nota breve al final del PLAN o en SUMMARY.

---

## 5. Criterios de verificación + gates finales + lista de comandos

**Criterios de éxito del Item (medibles, para self-check del executor):**
- Los handlers de mission admin (todos los entrypoints incl message/cb steps in FSM wizards) no contienen ninguna referencia activa a RewardService (import o uso) — grep ==0 active.
- Usan exclusivamente `get_service(MissionService)` vía context manager (with) + delegates for reward wizard steps (get_all_rewards_for_mission_wizard / get_reward_for_mission_wizard) + rel for reward in display; exactamente 1 service por entrypoint.
- Todas las funciones largas + helpers <=50 LOC fuente (inspect <=50; prefer <50); helpers puros extraídos (compute_mission_wizard_step_text, build_mission_confirm_text_and_keyboard, build_reward_select_buttons, compute_reward_summary_for_confirm, build_mission_list_entry_and_button, build_mission_detail_text_and_keyboard, build_mission_delete_confirm_keyboard, build_mission_stats_text_and_buttons, compute_freq_text, compute_reward_text etc) y usados para el render/wizard/list/detail/stats.
- Todos los tests en `test_mission_admin_handlers.py` pasan post-F4 (con get_service, delegates, rel, puros real, __exit__, nuevos pure tests; textos/calls/alerts/params/cbs idénticos + empty cases "No hay...").
- Re-runs de golds (handler test + cross mission/reward flows + reward get_all/get_reward gold + bot smoke) pasan sin regressions atribuibles a la extracción o ports.
- Ruff clean en los 3 archivos modificados.
- Verificaciones de reglas:
  - `grep -c "RewardService\|from services.reward_service import RewardService" handlers/mission_admin_handlers.py` (activo) == 0
  - LOCs (all target entrypoints + helpers) <=50 via inspect
  - Logging formato "mission_admin_handlers | <action> | user_id=... | ..." presente en las rutas principales dentro de withs
  - get_service(MissionService) + with + delegates for reward wizard + puros usados + tests added
  - 1 service rule + <=50 + logging + pure helpers + no biz logic en handler
- GSD pre every (counts 5-10+/fase target; wc tracked)
- GSD log completo con pre-entries + self-check "PASSED" + lista explícita de "tests críticos a re-correr en el futuro para estos handlers/helpers" (el handler test full; cross -k mission_admin|admin_missions|TestMissionAdmin|TestMissionAdminPureHelpers|build_|compute_|select_reward|select_frequency; reward get_all/get_reward gold; bot smoke; ruff + greps + LOC verifiers (0 RewardService handler, inspect <=50, logging, helpers, get_service count, delegate/pure comments svc)) + nota "Item 9/27 closed. First of new pool of 4. Previous pool closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en mission_admin_handlers: exactly 1 service + <=50L + no direct RewardService + puros + ports + UI1:1 + logging) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4." + pool phrase verbatim "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."
- Comportamiento de usuario final idéntico (wizard 6 pasos "Paso X de 6: Nombre..."/"Descripcion (opcional /skip)"/"Tipo de mision" (5 buttons 💋/🎁/🛒/👑)/"Valor objetivo" (examples per type)/"Frecuencia" ("Una vez"/"Recurrente")/"Recompensa" (list or empty "No hay recompensas configuradas..." + "➕ Crear recompensa" back "admin_missions"), confirm "Resumen de la mision:" with exact fields + "Sin descripcion"/"Ninguna", create success, list with status ✅/❌ name (type) + name[:30] buttons + back "admin_missions", detail with rel reward or "Sin recompensa" + 3 action kb (toggle conditional, delete, back "list_missions"), toggle reload show, delete confirm "Estas seguro..." / success "✅ Mision eliminada correctamente.", stats counts + active buttons + detail stats, all cbs, empty cases, backs, truncation, Lucien voice, freq labels all preserved 1:1 - puros mechanical 1:1 move of prior inline + delegates transparent).
- Safe point final documentado; item listo para guardians + siguiente del pool.

**Gates por fase (ver secciones de fases para detalles; siempre GSD pre antes):**
- Pre-edit / pre-gate / pre-verif / pre-ruff / pre-pytest / pre-grep / pre-smoke / pre-final: append al log.
- Post-edit: ruff + targeted pytest (cuando aplique) + smoke + grep/LOC checks + GSD entry de resultado.
- Avanzar solo si gate verde (o documentar desviación menor en log).
- F5: re-runs obligatorios de golds + broader smoke filtrado + self-check + BATCH/POOL note.

**Comandos concretos sugeridos (copiar al pie de la letra en ejecución; usar run_terminal_command):**
```
# GSD (siempre pre)
echo "=== $(date -Iseconds) | PHASE N | GSD pre-... <file> (<motivo>) - <desc + refs DoD + patrones copiados al pie de la letra de 26/25 PLAN F4 + gsd-reward-handlers-1service-loc.log + gsd-store-admin-long-funcs.log + item9 impact report (exact delegate/pure blocks + port instructions + long funcs list + UI pins 'Paso X de 6' ... 'No hay recompensas...' 'Resumen de la mision:' backs 'admin_missions' etc) + 25/26 SUMMARY BATCH/POOL + current source lines>" >> .planning/quick/gsd-mission-admin-long-funcs.log
wc -l .planning/quick/gsd-mission-admin-long-funcs.log

# Ruff (con --fix si hygiene)
./venv/bin/python -m ruff check handlers/mission_admin_handlers.py services/mission_service.py tests/handlers/test_mission_admin_handlers.py --fix
./venv/bin/python -m ruff format --check handlers/mission_admin_handlers.py services/mission_service.py tests/handlers/test_mission_admin_handlers.py

# Pytest targeted (siempre con estos flags para exit limpio; precedente todos los golds)
./venv/bin/python -m pytest tests/handlers/test_mission_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -m pytest -k "mission_admin or admin_missions or TestMissionAdmin or TestMissionAdminPureHelpers or build_ or compute_ or select_reward or select_frequency or mision" -q --tb=line -p no:cov --override-ini="addopts="

# Reward gold for get_all / get_reward (exercises the real that delegates call)
./venv/bin/python -m pytest tests/unit/test_reward_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "get_all_rewards or get_reward or active_only"

# Grep rules + 1svc + 0 bare Reward + puros + logging
grep -n "RewardService\|from services.reward_service import RewardService" handlers/mission_admin_handlers.py
grep -n "with get_service(MissionService)" handlers/mission_admin_handlers.py | wc -l
grep -n "def compute_mission_wizard_step_text\|def build_mission_confirm_text_and_keyboard\|def build_reward_select_buttons\|def compute_reward_summary_for_confirm\|def build_mission_list_entry_and_button\|def build_mission_detail_text_and_keyboard\|def build_mission_delete_confirm_keyboard\|def build_mission_stats_text_and_buttons\|def compute_freq_text\|def compute_reward_text" handlers/mission_admin_handlers.py
grep -n "mission_admin_handlers | " handlers/mission_admin_handlers.py
grep -n "def get_all_rewards_for_mission_wizard\|def get_reward_for_mission_wizard" services/mission_service.py

# LOC (inspect gold)
./venv/bin/python -c '
import inspect
from handlers.mission_admin_handlers import (
    create_mission_start, process_mission_name, process_mission_description, select_mission_type, process_mission_target,
    select_frequency, select_reward_for_mission, confirm_create_mission,
    list_missions, mission_admin_detail, show_mission_detail, delete_mission_confirm, toggle_mission,
    missions_stats, mission_detail_stats,
    compute_mission_wizard_step_text, build_mission_confirm_text_and_keyboard, build_reward_select_buttons,
    compute_reward_summary_for_confirm, build_mission_list_entry_and_button, build_mission_detail_text_and_keyboard,
    build_mission_delete_confirm_keyboard, build_mission_stats_text_and_buttons, compute_freq_text, compute_reward_text
)
for name, fn in [
    ("create_mission_start", create_mission_start), ("process_mission_name", process_mission_name),
    ("process_mission_description", process_mission_description), ("select_mission_type", select_mission_type),
    ("process_mission_target", process_mission_target), ("select_frequency", select_frequency),
    ("select_reward_for_mission", select_reward_for_mission), ("confirm_create_mission", confirm_create_mission),
    ("list_missions", list_missions), ("mission_admin_detail", mission_admin_detail),
    ("show_mission_detail", show_mission_detail), ("delete_mission_confirm", delete_mission_confirm),
    ("toggle_mission", toggle_mission), ("missions_stats", missions_stats), ("mission_detail_stats", mission_detail_stats),
    ("compute_mission_wizard_step_text", compute_mission_wizard_step_text),
    ("build_mission_confirm_text_and_keyboard", build_mission_confirm_text_and_keyboard),
    ("build_reward_select_buttons", build_reward_select_buttons),
    ("compute_reward_summary_for_confirm", compute_reward_summary_for_confirm),
    ("build_mission_list_entry_and_button", build_mission_list_entry_and_button),
    ("build_mission_detail_text_and_keyboard", build_mission_detail_text_and_keyboard),
    ("build_mission_delete_confirm_keyboard", build_mission_delete_confirm_keyboard),
    ("build_mission_stats_text_and_buttons", build_mission_stats_text_and_buttons),
    ("compute_freq_text", compute_freq_text), ("compute_reward_text", compute_reward_text),
]:
    src = inspect.getsourcelines(fn)[0]
    print(f"{name} LOC: {len(src)}")
    if len(src) > 50: print("OVER 50!")
'

# Smoke import + puros + delegates + bot
./venv/bin/python -c "
from handlers.mission_admin_handlers import (
    admin_missions_menu, create_mission_start, process_mission_name, process_mission_description,
    select_mission_type, process_mission_target, select_frequency, select_reward_for_mission,
    confirm_create_mission, list_missions, mission_admin_detail, show_mission_detail,
    delete_mission_confirm, toggle_mission, missions_stats, mission_detail_stats,
    compute_mission_wizard_step_text, build_mission_confirm_text_and_keyboard, build_reward_select_buttons,
    compute_reward_summary_for_confirm, build_mission_list_entry_and_button, build_mission_detail_text_and_keyboard,
    build_mission_delete_confirm_keyboard, build_mission_stats_text_and_buttons, compute_freq_text, compute_reward_text
)
from services.mission_service import MissionService
print('imports + helpers ok')
from unittest.mock import MagicMock
from models.models import MissionFrequency, MissionType, RewardType
# smoke puros
print(compute_mission_wizard_step_text(1, 'Nombre de la mision', 'Indica un nombre descriptivo:'))
data = {'name':'T', 'description':None, 'mission_type':MagicMock(value='reaccion'), 'target_value':5, 'frequency':MissionFrequency.ONE_TIME}
t, k = build_mission_confirm_text_and_keyboard(data, None)
print('confirm has Resumen and Ninguna:', 'Resumen de la mision' in t and 'Ninguna' in t)
print('pure ok')
ms = MissionService()
print('delegates exist:', hasattr(ms, 'get_all_rewards_for_mission_wizard') and hasattr(ms, 'get_reward_for_mission_wizard'))
"
# Bot smoke (router registration)
./venv/bin/python -c "
import bot
from handlers.mission_admin_handlers import *
print('bot import + routers (incl mission_admin) + handler import ok')
"

# Combined critical re-run (F5)
./venv/bin/python -m pytest -k "mission_admin or admin_missions or TestMissionAdmin or TestMissionAdminPureHelpers or build_ or compute_ or select_reward or select_frequency or mision or reward get_all or get_reward" -q --tb=line -p no:cov --override-ini="addopts="
```

---

## Instrucciones para el gsd-executor

Este PLAN.md ES tu prompt de ejecución. Síguelo al pie de la letra, sin scope creep. El trabajo es para UNA persona (tú) + disciplina GSD total. El flujo debe continuar automáticamente con gsd-executor para este item (y luego los siguientes 3 del pool de 4). 

**CONFIRMACIÓN OBLIGATORIA (incluir en tu output final y en el self-check del log):** Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. (Este es el primero de un nuevo pool de 4 (Item 9 / 27-mission-admin-long-funcs, post Item8 store-admin + Item7 reward-handlers-1service-loc + priors). El batch/pool anterior de 4 quedó cerrado con tests pasando: ver .planning/phases/26-store-admin-long-funcs/26-store-admin-long-funcs-SUMMARY.md + .planning/phases/25-reward-handlers-1service-loc/25-reward-handlers-1service-loc-SUMMARY.md (self-check PASSED + BATCH/POOL note) + their gsd logs (self-check PASSED + BATCH COMPLETE NOTE al final) + re-runs verdes en F5 de esos items.)

1. **GSD discipline (non-negotiable, como en todas las phases exitosas 26/25 + item7/8 logs + item2/24 etc):**
   - ANTES de **cualquier** modificación (search_replace/write/edit en fuentes o log o SUMMARY), antes de ruff, pytest, grep de verif, smoke, o resumen: append al log.
   - Log: `.planning/quick/gsd-mission-admin-long-funcs.log` (cross-ref gsd-impact-analyzer-item9-mission-admin-long-funcs.log del analyzer si útil).
   - Crea/append al archivo si necesario (planner ya hizo INIT + pre-mkdir + pre-write con 5+ entries; wc tracked; primer entry de executor puede confirmar + wc).
   - Formato de entry (copia estilo **al pie de la letra** de gsd-reward-handlers-1service-loc.log / gsd-store-admin-long-funcs.log / gsd-reward-gamif-item2.log / gsd-remaining-besito-compositions.log / gsd-reward-besito-eventbus.log / gsd-getservice-unification.log / gsd-critical-tests.log):
     ```
     === 2026-06-08Txx:xx:xx+00:00 | PHASE 3 | GSD pre-edit handlers/mission_admin_handlers.py (F3 extract pure helpers + ensure 1svc + remove bare Reward) - Agregar compute_mission_wizard_step_text + build_mission_confirm_text_and_keyboard + build_reward_select_buttons + compute_reward_summary_for_confirm + build_mission_list_entry_and_button + build_mission_detail_text_and_keyboard (dedupe show) + build_mission_delete_confirm_keyboard + build_mission_stats_text_and_buttons + compute_freq_text + compute_reward_text (puros, verb+context+result); slim all long (wizard steps create_mission_*/process_*/select_*, list_missions, mission_admin_detail + dedupe show_mission_detail via build_detail, delete_mission_confirm, missions_stats, mission_detail_stats) de >50 a <=50; mantener with get_service(MissionService) para TODOS entrypoints incl select_frequency/select_reward_for_mission; usar delegates get_all_rewards_for_mission_wizard / get_reward_for_mission_wizard dentro de los with; remove import + 2 bare RewardService() at 302/362; add uniform logging 'mission_admin_handlers | <action> | user_id=... | resultado=...' inside withs post-success; UI idéntica 1:1 con pins exact de impact ('Paso X de 6' ... 'Resumen de la mision:' 'No hay recompensas configuradas...' 'No hay misiones registradas.' backs 'admin_missions'/'list_missions' truncation [:30] freq 'Una vez'/'Recurrente' status ✅/❌ 'Sin descripcion'/'Ninguna'/'Sin recompensa' Lucien headers cb packs); refs DoD F3 + copy snippets from 26/25 PLAN F3 (pure helper insert + body replace + inspect LOC post) + item9 impact report (exact delegate/pure blocks + port instructions + long funcs list + all UI pins) + 25/26 gsd logs + SUMMARY BATCH/POOL + current source lines 26(import),302(bare),362(bare),450+(list),488+(detail),569+(show dupe); read pre done; patrones de item7/8/25/26.
     ```
     Luego ejecuta el comando de edit/tool.
   - También pre-gate (pre-pytest, pre-ruff, pre-grep "RewardService|get_service|def compute_|def build_mission_", pre-inspect LOC, pre-final-self-check, pre-SUMMARY si produces).
   - Cuenta las entradas; apunta a varias por fase (5-10+ totales por fase como precedentes item7 40+, item8 many, 24 55+, item2 46+). Al final del Item el log debe tener el self-check completo + BATCH/POOL note.
   - Usa `run_terminal_command` con `echo "=== $(date -Iseconds) | PHASE N | ..." >> .planning/quick/gsd-mission-admin-long-funcs.log` (o printf). Nunca edites sin pre-log. wc -l después de appends clave.

2. **Orden estricto:** Ejecuta Fase 1 → gates → Fase 2 → gates → Fase 3 → gates → Fase 4 → gates → Fase 5 (re-runs + verif final + self-check + POOL/BATCH confirm). **No saltes fases ni hagas "todo de una".** Marca DoD mentalmente o en el log al completar cada checklist. Al final de cada fase documenta "F<N> safe point" + "F<N> COMPLETE" en log (como item7/8 logs).

3. **Herramientas y comandos concretos (usa run_terminal_command para estos; copia los de sección 5 + precedents):**
   - GSD logs + wc: `echo "..." >> log; wc -l log`
   - Mkdir (si planner no lo hizo completamente): `mkdir -p .planning/phases/27-mission-admin-long-funcs`
   - Ruff: `./venv/bin/python -m ruff check <file> --fix` ; `./venv/bin/python -m ruff format --check <file>` (apply si "would reformat" como chore 0 logic per precedent 26/25/24/23).
   - Pytest targeted (siempre con estos flags para exit limpio): `./venv/bin/python -m pytest <path or -k "expr"> -q --tb=line -p no:cov --override-ini="addopts="`
     - Ejemplos exactos en sección 5 arriba + item8/7/25 F4/F5 / 24 F5.
   - Grep de reglas: `grep -n "RewardService\|from services.reward_service import RewardService" handlers/mission_admin_handlers.py` (0); `grep -n "with get_service(MissionService)\|from services import get_service" ...`; `grep -n "def compute_mission_wizard_step_text\|def build_mission_confirm_text_and_keyboard\|..." ...`; `grep -n "mission_admin_handlers | " ...`; `grep -n "def get_all_rewards_for_mission_wizard\|def get_reward_for_mission_wizard" services/mission_service.py`
   - LOC (siempre inspect): `./venv/bin/python -c 'import inspect; from handlers.mission_admin_handlers import ... list all long + puros ...; for name, fn in [...]: src=inspect.getsourcelines(fn)[0]; print(name, "LOC:", len(src))'`
   - Smokes: `./venv/bin/python -c "from handlers... import ...; from services.mission_service import MissionService; ..."` (puros calls with mocks for confirm/list etc, delegates hasattr or call if safe, bot `python -c "import bot; from handlers.mission_admin_handlers import *; print('ok')"` )
   - Evita sleeps; usa comandos directos. Si tool soporta background para integ lentas, úsalo pero log secuencial prefer.
   - Al final: re-ejecuta los combinados + broader smoke filtrado por mission/reward + self-check en log + (opt) write de SUMMARY.

4. **Patrones a copiar (no reinventar; **al pie de la letra** de golds):**
   - Patrón get_service + with + mock en tests + closes __exit__: copia de `tests/handlers/test_store_admin_handlers.py` (post item8) + item7/25 F4 port (get_service patch, mock_instance + __enter__, mock_mission_svc.get_all_rewards_for_mission_wizard.return_value = [mock with .id/.name/.reward_type], .get_reward_for_mission_wizard.return_value = mock or None, assert on mission_svc only (not reward_svc), closes to __exit__, calls asserts on main svc, docstrings "ported to 1-service (MissionService) only + delegate for reward wizard steps. Arch-enforcer note addressed. Precedent from item7/8.", NOTES cleaned).
   - Extracción de helper puro para LOC + UI idéntica: copia espíritu + snippets de F3 de item8/7/25 (insert pure compute_... / build_... near section or before routes; replace inline with call; docstring "Construye... Función pura (sin estado ni side-effects). Soporte para UI de admin missions (wizard/list/detail). 1:1 de lógica previamente inline (item9, arch-enforcer). Precedent item7/8."; inspect LOC post; test refresh path green; 5-8+ helpers for the flows; trim docstring si 51 por boilerplate + comentario "extracted for LOC rule (Item 9 / arch-enforcer)").
   - Logging: "módulo | acción | user_id=... | resultado=..." (copiar de item8/7/25/26 F2/F3 logs para list/confirm/create/stats + rules; inside with post data).
   - 1-line / min support + delegate comment: de item8/7/25 F1/F2 (pura + delegate + "Thin delegate... Added for item9: enables mission_admin_handlers ... exactly 1 service (MissionService)..." exact per impact; arch comment "# Support added for mission_admin_handlers 1-service + pure extract (item9). Arch-enforcer long-funcs note addressed. Precedent item7 (reward) + item8 (store-admin).").
   - GSD entries detalladas: "pre-xxx <file> (F<N> <motivo>) - <desc + refs DoD + patrones copiados al pie de la letra de 26/25 PLAN F4 + gsd-*-logs + item9 impact report (exact delegate/pure blocks + port instructions + long funcs list + UI pins) + 25/26 SUMMARY BATCH + current source lines>"; wc; style de item7 (40+), item8 (detailed), 24/25 (55+), item2 (46+).
   - Safe points + self-check al final del log: estructura de item7/8/25 (lista fases/DoD/gates/archivos/tests que pasaron/reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0, 1svc Mission + delegates for reward wizard, LOC<=50 via inspect, logging, pure helpers tests 5-10+ import-inside, no prod chg)/desviaciones/tests críticos/"Item 9/27 closed. First of new pool of 4. Previous pool... closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en mission_admin_handlers: exactly 1 service + <=50L + no direct RewardService + puros + ports + UI1:1 + logging) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4") + 25/26 BATCH/POOL note + explicit "first of new pool of 4" + "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."
   - Precedentes PLAN/GSD + handoff + pool/batch: .planning/phases/26-store-admin-long-funcs/PLAN.md + 26-SUMMARY + gsd-store-admin-long-funcs.log (Item8 second-of-new-pool long funcs 1svc+LOC gold), .planning/phases/25-reward-handlers-1service-loc/PLAN.md + 25-SUMMARY + gsd-reward-handlers-1service-loc.log (Item7 first-of-new-pool 1svc+LOC gold), 20-reward-gamif PLAN + gsd-reward-gamif-item2.log (Item2 reward 1svc gold + delegate + pure + ports + helper tests + LOC inspect + self-check PASSED + critical tests list + handoff), 23/24 PLANs + SUMMARYs (BATCH "4 items completed in this tirón (Item 6 final of max 4)", "Item 6/24 closed. BATCH...", self-check), item9 impact report .md (source of truth for scope/map/risks/tests/"first of new pool of 4" + exact code blocks for delegate/pure + port instructions + "Pool anterior de 4 cerrado..."), item8/item7 impacts, HARDENING_ROADMAP.md (sec5 pool + "tirones de hasta 4 items (chained automatically)"), .claude/agent-memory/impact-analyzer/MEMORY.md .
   - VOZ/estilo: handlers speak via existing texts (Lucien voice preserved identical); no change to user messages.
   - 3 sistemas críticos: always in mind (gamif/missions/rewards as domain in mind of hardening; this item admin mission/reward config only (read+admin-mutate); "admin create is orthogonal to user progress/claim" per user prompt; narrative cross 0; channel/VIP 0; re-runs of cross/gamif golds + reward get_* gold protect indirectly).
   - Commands: exact from PLAN sec5 + "Instrucciones" ( -p no:cov --override-ini="addopts=", ./venv/bin/python -m for ruff/pytest, python -c for smokes with venv fallback per 25/26 precedent, greps for rules/1svc/0-RewardService/puros/logging, python -c for LOC inspect with getsourcelines, bot smoke "from handlers.mission_admin_handlers import *", combined critical re-run in F5, reward get_* gold).
   - Test class for pure helpers: exact pattern from item8/7/25 F5 (class Test*PureHelpers with 5-10+ tests; import inside test funcs per file convention; no service mocks for pure; placed after last class).
   - Port of reward select ~12 tests: exact per item9 impact "change from @patch("handlers.mission_admin_handlers.RewardService") + mock_reward_svc.return_value.get_all... / .get_reward = ... to @patch("handlers.mission_admin_handlers.get_service") + setup mock_mission_svc.get_all_rewards_for_mission_wizard.return_value = [...]; .get_reward_for_mission_wizard.return_value = ...; ... assert on mission mock call (not reward_svc); keep exact data/text/state asserts + 'No hay recompensas' etc".
   - 0 export pure/delegate in __init__: confirmed (import direct sufficient + used).
   - Any differing: none; registered in GSD + self-check (none).

5. **Decisiones (sección 4 del PLAN):** Al inicio de la fase relevante (primer GSD entry de la fase), registra qué decidiste para "nombre de helper", si trimmaste docstring para LOC, cómo manejaste logging, delegate impl details (e.g. RewardService(db=...) vs other), etc. Si difieres del "preferido", explica brevemente (mantén espíritu tight + gold + 0 behavior + UI idéntica).

6. **Gates y re-runs:** 
   - Corre los targeted pytest con los flags exactos de sección 5 ( -p no:cov --override-ini="addopts=" ).
   - Si un unrelated fail preexistente aparece (ej. alembic_heads, daily concurrent UNIQUE, cross daily !success pre patch en priors, N806, SAWarnings, MovedIn20, Runtime AsyncMock, deprec utcnow, InternalEventBus, unraisable etc), documéntalo en log pero **no lo cuentes como regression del Item** (precedente 26/25/24/23/22/20/19 "Riesgo: baseline shows pre-existing unrelated fails ... document; do not count as regression" + "pre-exist pytest warns/xfails not attributable").
   - Re-run de handler test full + cross mission/reward flows + reward get_* gold + bot smoke es obligatorio en F5 (y spot en F1/F3/F4).
   - Siempre GSD pre- antes del pytest/ruff/grep grande.
   - Al final F5: re-ejecuta los combinados + broader smoke filtrado + self-check + POOL/BATCH confirm.

7. **Alcance (recuerda siempre):** Solo edita los archivos listados en "Archivos que se modificarán" + el log GSD + (este PLAN ya está) + opcional SUMMARY.md al final. Si sientes la tentación de "limpiar más handlers", "tocar reward_admin aunque backs a admin_missions", "tocar mission_service core CRUD o get_available_rewards_for_user internal o increment_and_deliver o deliver paths", "agregar tests fuera del mission_admin test file", "editar CLAUDEs o decisions o ROADMAP", "cambiar behavior de create_mission / reward delivery / user claim / atomicity", detente: scope tight para esta entrega (recomendado por impact + "first of new pool of 4" + "0 otros handlers" + "0 changes in mission/reward create/delivery/atomicity" + "0 bot.py/routers" + "0 CLAUDEs" + "3 crit protected"). El analyzer + user prompt + precedents recomiendan empezar tight aquí. "0 behavior/0 prod/0 delivery/0 atomicity change".

8. **Al final del Item (F5):**
   - Completa el self-check en el log (lista de fases, DoD cumplidos, archivos modificados, tests que pasaron, reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0 behavior chg in mission/reward create/delivery/atomic/held, 1svc Mission via get_service + delegates for reward wizard, LOC<=50 via inspect, logging, pure helpers tests 5-10+ import-inside, no prod chg), desviaciones (si las hubo; ej. ruff hygiene como chore 0 logic per 26/25 precedents "do not count as regression"), tests críticos para futuro (lista explícita), "Item 9/27 closed. First of new pool of 4. Previous pool closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en mission_admin_handlers: exactly 1 service + <=50L + no direct RewardService + puros + ports + UI1:1 + logging) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4." + pool phrase "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.").
   - (Opcional pero recomendado) Produce `.planning/phases/27-mission-admin-long-funcs/SUMMARY.md` con executive + refs al log + comandos de re-verificación (sigue estructura de 26/25/24/23/20/19).
   - Confirma en log: "Self-Check: PASSED".
   - El siguiente agente (gsd-executor next item o arch-enforcer/test-guardian) usará el log + este PLAN + los cambios como fuente de verdad.

9. **Si algo no está claro o difiere del "reporte del impact-analyzer" o user prompt:** El prompt del usuario + este PLAN (basado en discovery completa + el reporte completo en .claude/.../item9-...md + handoff de 26/25 SUMMARY + gsd logs de 26/25/item7/8 + código actual + precedents PLAN 26/25/20/21/23/24) es la fuente de verdad. Pregunta solo si un gate bloquea por ambigüedad real de nombre/firma/contrato (e.g. nombre exacto del helper); de lo contrario, elige conservadoramente siguiendo precedentes (item8/7 ports + helper extract + LOC inspect + self-check, item2/5/6 pure + delegate, impact examples for wizard step/confirm/list/detail/kb/reward select, 25/26 BATCH language) y registra la elección en GSD.

**¡Ejecuta con disciplina total. Cierra el Item de forma limpia, segura, medible y con trazabilidad GSD completa. La refactor de los mission_admin_handlers (1 service Mission-only + delegates for reward wizard + pure helpers para <=50L + ports + UI 1:1 + logging) queda hecha sin impacto en los 3 sistemas críticos ni en los contratos de create_mission / reward delivery / user claim / atomicity / increment. UI idéntica. Listo para arch-enforcer + test-guardian + siguiente item del pool de 4 (flujo continúa automáticamente).**

---

**Fin del PLAN para 27-mission-admin-long-funcs (Item 9, first of new pool of 4).**

Referencias rápidas para el executor (actualizar con líneas reales durante ejecución si cambian):
- Impact report (source of truth): .claude/agent-memory/impact-analyzer/item9-mission-admin-long-funcs.md (mapa, risks, scope 3 files, "first of new pool of 4", helper examples compute_mission_wizard_step_text / build_mission_* , tests port ~12 + add TestMissionAdminPureHelpers 5-10+, 0 behavior/0 other handlers/0 reward_svc/0 mission core CRUD or delivery chg, design "MissionService vía get_service + delegates para reward wizard steps + puros para UI/wizard/list/detail", exact delegate/pure code blocks, port instructions, "Pool anterior de 4 cerrado...").
- Gold precedent for store-admin 1svc + long funcs + puros + ports + helper tests + LOC + self-check + pool: .planning/phases/26-store-admin-long-funcs/PLAN.md + 26-SUMMARY + gsd-store-admin-long-funcs.log (F1 prep GSD baseline ruff pytest greps LOC UI pins patterns read, F2 min delegate/pure in svc, F3 1svc + puros + logging + LOC<=50 + UI1:1, F4 port + Test*PureHelpers, F5 re-runs + rules + self-check PASSED + critical + handoff + "second of new pool" + pool phrase).
- Precedent for reward 1svc + LOC + ports + pure + pool: .planning/phases/25-reward-handlers-1service-loc/PLAN.md + SUMMARY + gsd-reward-handlers-1service-loc.log (Item7 first-of-new-pool 1svc+LOC gold, docstrings, pure tests import inside, BATCH cite).
- Item8/7 impacts for exact blocks/port desc instructions + "first/second of new pool".
- 20-reward-gamif PLAN + gsd-reward-gamif-item2.log (Item2 reward 1svc gold + delegate + pure + ports + helper tests + LOC inspect + self-check PASSED + critical tests list + handoff).
- 23/24 PLANs + SUMMARYs (BATCH "4 items completed in this tirón (Item 6 final of max 4)", "Item 6/24 closed. BATCH...", self-check structure, GSD style).
- HARDENING_ROADMAP.md (sec 5 proposed + pool language "tirones de hasta 4 items (chained automatically)", "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.").
- .claude/agent-memory/impact-analyzer/MEMORY.md (pointers to item9 + item8 + item7).
- Current state (pre): handlers/mission_admin_handlers.py (7 good with get_service(MissionService) for confirm/list/detail/toggle/delete/stats/detail_stats; bare RewardService import at 26 + 2 instantiations at 302 (select_frequency get_all) + 362 (select_reward_for_mission get_reward) violating 1svc + long wizard steps "Paso X de 6" + list~ + detail~ + show dupe + delete~ + stats~ ; RewardWizardStates dead but untouched; UI exact pins as above); services/mission_service.py (already imports RewardService for get_available_rewards_for_user + increment_and_deliver paths; core CRUD intact; place delegates min support); tests/handlers/test_mission_admin_handlers.py (docstrings, ~12 RewardService patches in select freq/reward tests, get_service patterns in other classes with __enter__/__exit__, late imports, make_* , exact UI asserts + empty cases); bot.py (include at 294, 0 touch).
- GSD log para este Item: .planning/quick/gsd-mission-admin-long-funcs.log (planner INIT/pre-mkdir/pre-write 5+ entries; executor append pre every).
- Reglas + contexto: CLAUDE.md (root + handlers + services + models), rules.md (≤50 LOC, verb+context+result naming, logging "módulo | acción | user_id | resultado", exactly 1 service per handler entrypoint), architecture.md (handlers→services→models), decisions.md, AGENTS.md, services/missions/CLAUDE.md, models/CLAUDE.md (rels safe), handlers/CLAUDE.md (1 service rule).
- Comandos + patrones: sección 5 + "Instrucciones" arriba + item8/7/25/26 gsd log entries exactas + impact.

Listo para gsd-executor. Ejecuta F1 → ... → F5 con GSD pre en cada paso + self-check PASSED + POOL/BATCH confirm al final + handoff explícito para arch-enforcer (enfocado mission_admin_handlers: exactly 1 service + <=50L + no direct RewardService + puros + ports + UI1:1 + logging) + test-guardian (correr tests críticos) + gsd-executor del siguiente del pool de 4.

**Hecho con 💋 para Diana (Señorita Kinky) — gsd-planner subagent (continuación del hardening post-unificación de Besito + mw + getservice + pools; first of new pool of 4).**
