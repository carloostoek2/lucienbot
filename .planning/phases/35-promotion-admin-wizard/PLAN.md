# PLAN: Refactor long functions in promotion_admin_handlers.py to <=50 LOC + ensure exactly 1 service call per handler (PromotionService via get_service) (Item 2/35, second of new pool of 4)

**Type:** gsd-planner output (for gsd-executor + hardener seq: arch-enforcer + test-guardian + documentador at pool close)  
**Date:** 2026-06-26  
**Focus:** Tight, conservative, phased refactor of `handlers/promotion_admin_handlers.py` (wizard steps with direct PackageService usage in select_package_source + inline build logic in show_promotion_confirmation + other wizard process/show flows; currently 1+ direct cross via get_service(PackageService) and top import; most other entrypoints already use get_service(PromotionService) but consolidate all + extract puros). Ensure **every handler entrypoint calls exactly 1 service** (PromotionService via standardized `with get_service(PromotionService) as promotion_service:` context + get_service lifecycle). Extract pure helpers (verb+context+result; stateless, no side-effects, importable, unit-testable; "Función pura...") for UI/wizard formatting and builders (e.g. `build_promotion_confirm_text_and_keyboard`, `build_*_text_and_buttons`, `compute_*_text`) to bring all functions <=50 LOC source. Minimal support ONLY in `services/promotion_service.py` (thin delegates for cross Package: `get_available_packages_for_promo_wizard` etc so handler boundary = exactly PromotionService only; + 1-line delegates + arch/"item 2/35 ... precedent item 8/9/34" comments). Update ONLY `tests/handlers/test_promotion_admin_handlers.py` (port direct PackageService patches to get_service(PromotionService) + delegate mocks + assert on promotion_svc; add `TestPromotionAdminPureHelpers` class with 10+ import-inside pure unit tests). **0 other handlers touched**. **0 behavior change in promotion create/list/toggle/interests/block flows**. **0 atomicity/EventBus/get_service contracts impact**. "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

**Input principal (source of truth):** 
- Complete impact-analyzer report just returned for pool35 item2 (promotion admin wizard) (full read via mandatory; executive summary + mapa: exact files handlers/promotion_admin_handlers.py + min support en promotion_service.py (thin delegates) + tests/handlers/test_promotion_admin_handlers.py; riesgos low due to precedents + tight scope; tests críticos (handler test full + promotion service + broader -k "promotion or promo or admin_promo or TestPromotionAdmin or TestPromotionAdminPureHelpers or build_promotion or select_package or show_promotion_confirmation" + bot smoke + LOC verifiers via getsourcelines); scope tight recomendado "solo handlers/promotion_admin_handlers.py + min support en services/promotion_service.py (thin delegates e.g. get_available_packages_for_promo_wizard ... to allow handler boundary = exactly PromotionService only) + updates en test_promotion_admin_handlers.py"; "0 otros handlers", "0 behavior/UI change. 0 prod change. 0 CLAUDEs/decisions/ROADMAP edits except opt in GSD/..."; "0 changes to core promotion CRUD, interests, block, notify, atomicity"; design notes "1 service Promotion via get_service + delegates for cross-package wizard steps + puros for UI/wizard (build_promotion_confirm_text_and_keyboard, build_*, compute_* etc)"; precedentes de item8/26-store-admin-long-funcs + item9/27-mission-admin-long-funcs + item7/25 + 34-reward-admin-wizard; "second of new pool of 4"; "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."; long funcs/wizard focus explicitly: select_package_source (direct Package), show_promotion_confirmation (inline text+kb build), process_* steps, list/detail with inline loops; direct Package import at top + get_all_packages call; get_service uses already in menu/confirm/list/detail etc but ensure uniform).
- `.planning/HARDENING_ROADMAP.md` (pool34 close + phrase + proposed "Additional wizard modernization (promotion?)" + item2 context; pool phrase verbatim x many; 3 crit; hardener standard).
- Precedents + golds: `.planning/phases/34-reward-admin-wizard/PLAN.md` (at least first 120 lines + phases section; exact structure, DoD, GSD pre, self-check, UI 1:1 pins, "Paso X de 5", copy al pie, handoff, pool phrase) and `.planning/phases/27-mission-admin-long-funcs/PLAN.md` (structure/sections/DoD/GSD/self-check/phrase); `.planning/phases/35-full-redis-rate-idemp-middleware/PLAN.md` (pool35 header style "Item 1/35, first of new pool of 4" + phrase); 26/28/29 precedents for puros/delegates/ports/LOC inspect/Test*PureHelpers/import-inside; current source (promotion_admin_handlers.py with wizard 5 pasos + direct Package + show_confirm + get_service(Promotion) in most; promotion_service.py; tests/handlers/test_promotion_admin_handlers.py header + Test* + PackageService patch in select); CLAUDE.md (root + handlers + services + hardener section 1svc/get_service/puros/pattern from Items 7-11 + pool phrase + 3 crit); rules.md, architecture.md, decisions.md, AGENTS.md, services/promotions/CLAUDE.md, handlers/CLAUDE.md (1svc + puros pattern from Items 7-9).
- Current files briefly (mandatory read): handlers/promotion_admin_handlers.py (focus on wizard steps + direct Package import + get_service uses), services/promotion_service.py (to see where thin delegates go), tests/handlers/test_promotion_admin_handlers.py (header + test classes).

**GSD enforcement:** Executor MUST prefix **every** modification / pre-gate / verification / ruff / pytest / grep / smoke / self-check / summary with a GSD log append (timestamp | PHASE | description) to `.planning/quick/gsd-35-promotion-admin-wizard.log` (cross-ref impact if present). Use identical discipline, entry style, wc -l tracking, "pre-xxx <file> (F<N> <short motive>) - <desc + refs DoD + patrones copiados al pie de la letra>", and self-check structure as gsd-reward-admin-wizard.log / gsd-mission-admin-long-funcs.log / gsd-35-full-redis... (phases + SAFE POINT + FINAL self-check PASSED + POOL/BATCH note). No edits (even to PLAN/log beyond appends) without pre-log. Planner did INIT + pre-mkdir + pre-write (3+ entries, wc tracked; cross-ref gsd logs + impact context).

---

## 1. Alcance preciso (In / Out explícito + archivos exactos)

### En esta entrega (scope "tight" per impact report + precedents + "no creep" + 0/0/0):
- **handlers/promotion_admin_handlers.py** (core): Ensure/keep **exactly `with get_service(PromotionService) as promotion_service:`** (1 call only per entrypoint/handler, including all message FSM steps and cb steps for promotion wizard 5 pasos + confirm + list/detail/toggle/delete/interests/block/stats). Remove direct `from services.package_service import PackageService` (or keep only if type annotation absolutely required, no instantiation/use); replace the get_all_packages call site (select_package_source) with promotion_service delegate. Extract 10+ pure helpers to slim long wizard flows (show_promotion_confirmation, select_package_source, process steps, confirm flows). Recommended extracts (copy logic 1:1 for identical render; verb+context+result; pure = no with, no await, no logger, no FSM/state, no DB; from impact tentative):
  - `build_promotion_confirm_text_and_keyboard(data: dict, package=None) -> tuple[str, InlineKeyboardMarkup]`
  - `build_promotion_step_text(step: int, title: str, prompt: str, example: str = None) -> str`
  - `compute_file_text_for_confirm(manual_file_count: int | None, package_id: int | None) -> str`
  - `build_promotion_list_entry_and_button(promo) -> tuple[str, list[InlineKeyboardButton]]`
  - `build_promotion_detail_text_and_keyboard(promo) -> tuple[str, InlineKeyboardMarkup]`
  - `build_promotion_delete_confirm_keyboard(promo_id: int) -> InlineKeyboardMarkup`
  - `compute_promo_price_display(price_mxn: int) -> str`
  - `compute_dates_text(start_date, end_date) -> str`
  - `build_interest_list_text_and_buttons(pending: list) -> tuple[str, list[list[InlineKeyboardButton]]]`
  - `build_blocked_user_text_and_keyboard(blocked) -> tuple[str, InlineKeyboardMarkup]`
  - Possibly small compute for status/available/file_count display.
  Keep all other process_* validation (name len, int parses, /skip, date parse, file_count) as-is if already small or slim inline. Preserve: is_admin guards (lambdas), FSM states (PromotionWizardStates  + BlockUserStates), state update_data/get_data/clear/set_state, late imports in tests, callback packing (Promo*Callback, SelectPkgPromoCallback, Interest* etc), /skip, error paths/answers, cancel cbs to "admin_promotions", internal calls (toggle -> detail), Lucien voice 3rd person ("forjar experiencias", "Gabinete de Oportunidades"), exact strings/emojis ("Paso X de 5", "🎩 <b>Lucien:</b>", "✨", "💰", "📅", "🔔", "🚫", confirm "✅ Forjar experiencia", "Resumen", empty "El Gabinete esta vacio...", "No hay...", backs, truncation), price in cents logic, dates optional, package vs manual, interests/block flows. Post: verify no function >50 lines (inspect.getsourcelines); all entrypoints 1 svc Promotion via get_service; grep 0 "PackageService" active in handler. No new direct imports of PackageService; no DB; no biz logic (CRUD in svc; calcs/UI in puros or svc). Use delegates for packages in wizard.
- **services/promotion_service.py** (soporte mínimo only):
  - Add thin delegates (passthrough; place near admin helpers; exact style from item8/9/34 + arch comments):
    ```python
    def get_available_packages_for_promo_wizard(self) -> list["Package"]:
        """Thin delegate to PackageService.get_all_packages().
        Added for item 2/35: enables promotion_admin_handlers package selection in promo wizard to call exactly 1 service (PromotionService) per handlers/CLAUDE + arch rules.
        Not core CRUD. 0 behavior change. Precedent item 8/9/34.
        """
        from services.package_service import PackageService
        return PackageService(db=self._get_db()).get_all_packages()
    ```
  - (If needed for confirm) thin passthroughs or 1-line for package fetch if used in confirm path, with comment "# Backward-compatible delegate added for Item 2/35 (arch-enforcer 1-service rule for promotion_admin handlers)."
  - Arch comment near delegates: "# Support added for promotion_admin_handlers 1-service + pure extract (item 2/35). Arch-enforcer long-funcs + multi-service note addressed. Precedent item 8/9/34."
  - 0 changes to: create_promotion / get_promotion / get_all_promotions / get_active_promotions / update_promotion / delete_promotion / express_interest / get_pending_interests / get_interests_for_promotion / mark_interest_attended / block_user / get_blocked_users / get_blocked_user_info / get_promotion_stats / close / _get_db / __init__ / anything in user "me interesa" / notify / block paths.
- **tests/handlers/test_promotion_admin_handlers.py** (only its test file):
  - Port: any direct PackageService patches (e.g. in TestSelectPackageSource ~ test_no_packages... and related) from @patch("handlers.promotion_admin_handlers.PackageService") to @patch("handlers.promotion_admin_handlers.get_service") + setup mock_promo_svc.get_available_packages_for_promo_wizard.return_value = [...] ; adjust late import/await calls; assert on promotion mock call (not pkg_svc); keep exact data/text/state asserts + "Paso X de 5" / "No hay colecciones..." / UI strings / cbs. Use mock_context.__enter__.return_value = mock_promo_svc pattern.
  - Update docstrings (module + class + methods if needed): "Tests ported to 1-service pattern (get_service(PromotionService) only + delegate for packages in wizard) + pure UI helpers (build_promotion_* / compute_*). Arch-enforcer note addressed. Precedent item 8/9/34."
  - Add: new tests class `TestPromotionAdminPureHelpers` (like item 34 TestRewardAdminPureHelpers / item9 TestMission... / item8): pure unit (no @patch on puros; import inside test); 10+ cases covering:
    - confirm texts with/wo package/manual/desc/dates (exact "✨ name", "Sin descripcion", price "$X.00 MXN", "📁 Archivos: N (definido manualmente)", "Contenido: De coleccion existente", dates).
    - step texts ("Paso X de 5: ...", Lucien headers, examples).
    - file compute branches (manual vs package_id vs none).
    - list entry/status + buttons (✅/❌ name, price).
    - detail text/keyboard (status, available, interests counts, content file_count, Lucien, buttons).
    - delete confirm kb.
    - empty/edge (no packages, no interests, None desc, truncation, 0 price).
    - "Paso X de 5" pins, Lucien strings, back cbs, empty cases.
  - Keep: all existing structure (pytestmark unit, make_* fixtures, late `from handlers...` after patch, PropertyMock/MagicMock, manual mock_context, asserts on edit_text/answer exact phrases like "Paso X de 5", "Forjar esta experiencia", "El Gabinete esta vacio", cb.answer, state checks); all current Test* classes 100% coverage preserved.
  - 0 direct PackageService patches left in this file post-port.
- **GSD + artefacts**: run_terminal append BEFORE every edit/write/gate/verif (to .planning/quick/gsd-35-promotion-admin-wizard.log); track wc -l; specific git add only touched (if committing); ruff/pytest gates with exact flags `-q --tb=line -p no:cov --override-ini="addopts="`; self-check PASSED at end with full structure (phases/DoD/gates/archivos/tests que pasaron/reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0 behavior chg in promotion CRUD/interests/block, 1svc Promotion via get_service + delegates for package, LOC<=50 via inspect, logging, pure helpers tests 10+ import-inside, no prod chg)/desviaciones/tests críticos para futuro (promotion admin handler test full + pure class, promotion unit if delegates, cross -k "promotion or promo or admin or TestPromotionAdmin or TestPromotionAdminPureHelpers or build_promotion or select_package", bot smoke, ruff+greps+LOC verifiers)/"Item 2/35 closed. Second of new pool of 4. Previous pool of 4 closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en promotion_admin_handlers: exactly 1 service + <=50L + no direct PackageService + puros + ports + UI1:1 + logging) + test-guardian (correr los tests críticos listados) + documentador (ROADMAP + learnings + agent-memory) + gsd-executor del siguiente item del pool de 4").
- **Verification**: the 3 files ruff clean; handler test/pure class 100% pass (behavior identical); critical list re-run (promotion admin test full + promotion service + broader -k promotion/promo/admin + bot smoke + line counts <=50 post via inspect + outputs match pre via test asserts on strings/emojis/cbs + 0 beh change in create/list/detail/toggle/interests/block + wizard package/manual flows); 0 change to gamif or narrative or channel/VIP contracts (re-runs of cross/gamif golds protect indirectly); "admin create is orthogonal to user interests" per precedent. Greps: 0 "PackageService" active in handler (except comments); count with get_service(PromotionService); delegates present in svc with comments; logging format; UI strings in puros.
- Memory: cross-ref this PLAN + GSD log + HARDENING_ROADMAP + precedents + impact report.

**Archivos que se modificarán (exactos, por orden de fases; prefer extend, minimal):**
1. `.planning/quick/gsd-35-promotion-admin-wizard.log` (all phases, pre only via echo; no "edit" of source beyond appends; wc tracked).
2. `services/promotion_service.py` (F3: min support -- thin delegate get_available_packages_for_promo_wizard + arch comments + 1-line if pattern; 0 core CRUD).
3. `handlers/promotion_admin_handlers.py` (F4: remove direct PackageService import/use; all entrypoints use with get_service(PromotionService) only; use delegates for packages; extract 10+ pure helpers per wizard/flow; slim long show_confirm + select + process steps + callers to <=50 LOC; ensure/keep exactly 1 svc per entrypoint; add/ensure logs standard; UI render 1:1).
4. `tests/handlers/test_promotion_admin_handlers.py` (F5: port the PackageService wizard select tests (direct patch -> get_service(Promotion) + delegate mocks); update docstrings w/ "1-service (PromotionService) + delegate for cross-package... + pure... Arch-enforcer addressed"; add TestPromotionAdminPureHelpers (pure coverage for extracts: confirm, steps, file compute, list/detail/status, empty, edges, "Paso X de 5"/Lucien pins); keep 100% prior coverage + asserts).
5. Re-runs/gates/verifs/smokes do not modify (except ruff auto-fixes if any on touched + log appends).

**Fuera explícitamente (nada de scope creep, per "tight" + impact "0 otros handlers" + "0 behavior change en promotion CRUD/interests/block" + "0 atomicity" + "0 docs más allá de lo necesario" + 3 crit protected):**
- **NO** otros handlers (promotion_user_handlers.py, reward_admin, mission_admin, store_admin, gamification_*, story_*, channel, vip, common, broadcast, free_channel, analytics etc. — even if related cbs or "Gabinete").
- **NO** package_service.py or other (no changes; delegate calls it; its methods remain canonical; unit tests unchanged).
- **NO** models (no new props), 0 keyboards/* (no new builders or cb changes; packages_for_promotion_keyboard etc remain; puros return raw or InlineKeyboardMarkup from existing), 0 bot.py, 0 handlers/__init__.py, 0 services/__init__.py, 0 utils, 0 lucien_voice, 0 config, 0 middlewares.
- **NO** changes to core PromotionService: create_promotion / get_* / update / delete / express_interest / get_pending / mark / block / unblock / get_blocked / get_stats / notify paths / close / _get_db / anything in user interests or atomic (if any).
- **NO** change to user promotion flows or "Me Interesa" or notify_admins.
- **NO** new tests outside the promotion_admin test file (no service tests for delegates/pures beyond the pure class).
- **NO** edición de CLAUDEs (incl services/promotions/CLAUDE.md, handlers/CLAUDE.md), decisions.md, AGENTS, ROADMAP, fase_*, docs/, o cualquier .md excepto este PLAN + el log GSD (impact if present + MEMORY by documentador at close).
- **NO** broad "fix all promotion flows" or "touch promotion_user for parity" or "refactor package".
- **NO** behavior or contract changes (0 impact on promotion create values, wizard FSM transitions, package/manual semantics, UI strings/emojis/buttons/cbs, alerts, empty/error cases; delegates transparent; extracts pure 1:1 move of prior inline).
- 0 impact on 3 critical systems' core contracts (gamificación (besitos/reactions/daily/missions), narrativa, canales-VIP; this flow admin promotion config only (read+admin-mutate); orthogonal to user interests/notify; re-runs protect indirectly).
- 0 prod chg.

**Comportamiento observable idéntico + reglas:** All text construction, emoji choice, button labels/texts (exact wizard steps "Paso X de 5", "🎩 <b>Lucien:</b>", "✨ name", "💰 Inversion: $X.00 MXN", "📁 Archivos: N (definido manualmente)" / "Contenido: De coleccion existente", "📅 Disponibilidad", "✅ Forjar experiencia", list "✅/❌ name", "💰 price", detail status/available/interests counts/file_count, interests "🔔 Expresiones pendientes", block "🚫", backs, truncation, "El Gabinete esta vacio...", "No hay expresiones...", price cents, dates parse, package vs manual, empty cases), cb packing, logging format, error paths, wizard FSM steps/transitions (PromotionWizardStates full, BlockUserStates, /skip, name>=3, price>0, date format, state data name/desc/package_id/manual_file_count/price_mxn/start/end, set waiting_*/selecting_*/confirming / clear), confirm summaries, list/detail formats, interests/block flows (pending lists, status emojis, block reason, unblock), navigation (back to admin_promotions), are in puros (mechanical 1:1 move of existing inline) or the entry handlers or svc (unchanged CRUD/interests). Delegates are transparent passthroughs. Extraction preserves every string/emoji/branch/cb/data exactly. Handlers call exactly 1 service (PromotionService); funciones <=50 LOC post-extract; logging en formato estándar "promotion_admin_handlers | <action> | user_id=... | resultado=..." para acciones importantes; get_service context manager; sin lógica de negocio en handlers; sin acceso DB fuera de models; pure helpers (no side effects, importable, fácil unit test, verb+context+result naming). 3 sistemas críticos protegidos (admin config orthogonal; 0 side effects en gamif credit / narrative / VIP-channel; re-runs protect).

**Artefactos:** Este PLAN.md + entradas GSD completas en el log dedicado (pre every) + (si procede en executor) SUMMARY.md posterior (seguir precedente 34/27/26/25). Memory/hand-off apunta desde PLAN + GSD + documentador at close (ROADMAP + agent-memory + MEMORY pointer).

---

## 2. Fases ordenadas (7 fases pequeñas, secuenciales, con gates estrictos)

### Fase 1: Preparación (GSD log init/confirm, baseline, fixtures/patterns, patrones gold, LOC actual, confirm 1svc + direct cross sites, UI strings for pinning)

**Objective:** Establecer disciplina GSD para el Item (log touched); confirmar baseline (ruff clean + targeted pytest verde pre-cambios); mapear estado actual (get_service(Promotion) uses + 1 direct Package via get_service(PackageService) in wizard + show_promotion_confirmation inline + other list/detail loops; long confirm ~60L); inspect LOC on key long funcs (show_promotion_confirmation, select_package_source, process_*, list_promotions, show_pending_interests etc); grep for PackageService + get_service(PromotionService) sites + "with get_service" count; confirm fixtures (make_callback, make_fsm_context, make_message); patrones gold (get_service patch + __enter__/__exit__ from item 34/9/8/7 ports + Test*PureHelpers; real pure via attrs if any; mock_promo_svc delegates for packages); identificar los helpers a extraer (confirm text+kb, step text, file_text, list entry, detail text+kb, delete kb, price/dates computes, interests buttons) from current inline + precedents; confirmar UI strings exactas para pinning ("Paso X de 5", "🎩 <b>Lucien:</b>", "✨ <b>name</b>", "📝 desc", "💰 <b>Inversion:</b> $X.00 MXN", "📁 <b>Archivos:</b> N (definido manualmente)", "Contenido: De coleccion existente", "📅 <b>Disponibilidad:</b>", "✅ Forjar experiencia", "El Gabinete esta vacio...", "No hay colecciones...", "No hay expresiones de interes pendientes...", "Paso 1 de 5: El nombre...", "Paso 3 de 5: Definir el contenido", "Paso 4 de 5: La inversion", "Paso 5 de 5: Periodo...", list status ✅/❌ + price, detail "Estado:", "📦 Archivos: {file_count}", interests counts, block "🚫", empty, truncation name[:20]/[:15]/[:25], Lucien headers, backs); GSD pre/post (varias); "F1 safe point - baseline verde + ready for F2; no source changed yet".

**DoD checklist (marcar al completar):**
- [ ] Log `.planning/quick/gsd-35-promotion-admin-wizard.log` exists with planner INIT/pre-write entries (wc >=3) + at least 1 pre-F1 of executor.
- [ ] Baseline: ruff clean on the target files (handler + promotion_service + test).
- [ ] Baseline targeted pytest verde (clean flags exact): `python -m pytest tests/handlers/test_promotion_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` + broader -k "promotion or promo" smoke if present; expect green.
- [ ] Confirm gold patterns via grep/lectura + python inspect: current long flows LOC (show_promotion_confirmation, select_package_source, process_promotion_* , list_promotions, promotion_admin_detail, show_pending_interests, show_promotion_interests etc.); grep -n "get_service(PromotionService)" + "PackageService" + "with get_service" in handler (map sites); mock patterns in precedent tests (get_service patch + __enter__ + __exit__ asserts, delegate mocks, exact text asserts, state checks); strings for pinning listed above. "Paso X de 5" / Lucien / empty cases pinned.
- [ ] GSD pre logged for F1 (wc tracked).

**Exact files changed:** only log appends (no source yet). Safe point after.

**GSD pre-log instruction:** "GSD pre-edit/phase F1 <log> (baseline/greps/LOC/UI pins) - copy patterns al pie from 34-reward PLAN F1 + 27-mission + item9 impact; read current get_service/Package sites + long confirm; no source touched."

### Fase 2: Consolidate to exactly 1 service (PromotionService via get_service in all entrypoints incl wizard)

**Objective:** Uniformly wrap every handler entrypoint (wizard starts/process/cb, list, detail, toggle, delete_confirm, interests, block flows, stats) with `with get_service(PromotionService) as promotion_service:` (1 call); replace the PackageService usage in select_package_source with future delegate call (will wire in F3); ensure no bare instantiations remain. Add/ensure standard logging inside withs ("promotion_admin_handlers | <action> | user_id=... | result=..."). No behavior change.

**DoD:**
- [ ] All ~15+ entrypoints (incl create wizard 5 pasos + confirm + select_package_source + list + detail + toggle + delete + pending/show interests + block flows + stats) use exactly 1 with get_service(PromotionService).
- [ ] Grep confirms 0 active PackageService import/use (except future comment) + count of "with get_service(PromotionService)" >= prior + wizard sites.
- [ ] Logging added where missing per rules (inside withs on important actions like create/list/confirm/interests).
- [ ] F2 safe point (tests still pass on baseline mocks, no delegate yet).
- [ ] GSD pre + post.

**Exact files changed:** handlers/promotion_admin_handlers.py (F2 edits), log.

**GSD pre-log instruction:** "GSD pre-edit F2 <handler> (consolidate 1svc) - copy al pie item34 F2 / item9 F2 / 34-reward: use get_service(Promotion) in every entrypoint incl all wizard cb/message steps; replace Package get_all; no other svc."

### Fase 3: Add thin delegates in promotion_service.py (min support for Package cross in wizard)

**Objective:** Add 1-2 thin delegates in promotion_service.py so handler can use only PromotionService (e.g. get_available_packages_for_promo_wizard passthrough to PackageService.get_all_packages(); import-inside; exact arch comments "Added for item 2/35: enables promotion_admin_handlers package selection in promo wizard... Precedent item 8/9/34"; place near other admin helpers; 0 core change).

**DoD:**
- [ ] Thin delegate(s) present with verbatim comments + import inside + "Not core CRUD. 0 behavior change."
- [ ] Arch comment present.
- [ ] No change to existing PromotionService methods/contracts.
- [ ] GSD pre + post (before/after appends).
- [ ] F3 safe point.

**Exact files changed:** services/promotion_service.py , log.

**GSD pre-log instruction:** "GSD pre-edit F3 <svc> (thin delegates) - copy al pie item34 reward_service delegates + item9 mission + item8 store: get_available_packages_for_promo_wizard (or equiv name from impact); import-inside; arch comments exact; precedent item 8/9/34; 0 core."

### Fase 4: Extract pure helpers (10+ , slim long wizard flows to <=50 LOC)

**Objective:** Extract 10+ pure helpers (tentative list from impact: build_promotion_confirm_text_and_keyboard, build_promotion_step_text, compute_file_text_for_confirm, build_promotion_list_entry_and_button, build_promotion_detail_text_and_keyboard, build_promotion_delete_confirm_keyboard, compute_promotion_price_display, compute_dates_text, build_interest_list_text_and_buttons, build_blocked_user_text_and_keyboard, + compute_status_emoji or similar; verb+context+result; "Función pura (sin estado ni side-effects). Soporte para UI de admin promotions (wizard/list/detail). 1:1 de lógica previamente inline (item 2/35, arch-enforcer). Precedent item 8/9/34."; call them from handler; slim show_promotion_confirmation + select + process_* + list/detail loops etc to <=50 via inspect post; keep UI 1:1 exact (all strings/emojis/cbs/builder logic identical); add logging only in withs (not puros).

**DoD:**
- [ ] 10+ puros extracted with exact docstrings + naming.
- [ ] All target long funcs (show_promotion_confirmation, select_package_source, list_promotions, show_pending_interests etc) + callers <=50 LOC (inspect.getsourcelines post-edit).
- [ ] UI render 1:1 (tests will pin; strings match pre-extract).
- [ ] No side effects in puros (pure by construction).
- [ ] GSD pre + post; F4 safe point (baseline tests would pass if run now).
- [ ] Grep for pure docstrings + names.

**Exact files changed:** handlers/promotion_admin_handlers.py (F4), log.

**GSD pre-log instruction:** "GSD pre-edit F4 <handler> (extract puros) - copy al pie item34 F3 / item9 F3 / 26/27: 10+ build/compute_ puros with 'Función pura...' + verb+context+result; move confirm/list/detail/interest inline 1:1; slim to <=50 via inspect; UI1:1 exact 'Paso X de 5' / Lucien / price / file texts / empty; precedent item 8/9/34."

### Fase 5: Port tests + add TestPromotionAdminPureHelpers (import-inside, 10+ cases)

**Objective:** Port PackageService patches in test_promotion_admin_handlers.py (esp TestSelectPackageSource and wizard select paths) to get_service(PromotionService) + mock_promo_svc.get_available_packages_for_promo_wizard + __enter__/__exit__ asserts + delegate style + docstrings "ported to 1-service... Arch-enforcer note addressed. Precedent item 8/9/34."; add TestPromotionAdminPureHelpers at end with import inside (after patch), 10+ tests exercising real puros (no @patch on helpers; use attrs/returns for data; cover all branches/UI pins "Paso X de 5", confirm texts, file compute, list/detail, empty, edges, cbs, Lucien); keep 100% existing coverage.

**DoD:**
- [ ] 0 direct PackageService patches remain (only get_service on PromotionService).
- [ ] TestPromotionAdminPureHelpers with 10+ cases (import-inside per conv; exact UI pins from F1 + impact).
- [ ] Docstrings updated with port note + precedent.
- [ ] All tests pass on the pure + ported (real puros exec via setup).
- [ ] GSD pre + post.
- [ ] F5 safe point.

**Exact files changed:** tests/handlers/test_promotion_admin_handlers.py , log.

**GSD pre-log instruction:** "GSD pre-edit F5 <test> (port + pure class) - copy al pie item34 F4 / item9 F4 / item8 Test*PureHelpers: import inside after get_service patch; port Package -> promo delegate mocks + assert on promotion_svc; 10+ cases for build_promotion_confirm / compute_file / step texts / list entry / detail / edges / 'Paso X de 5' / empty / Lucien; no @patch on puros; docstrings 'ported... Arch-enforcer'."

### Fase 6: Ruff + gold cmds + smoke (targeted + broader)

**Objective:** Run ruff on touched files (clean or pre-tol non-reg); run exact gold pytest cmds with flags; broader smoke -k promotion/promo/admin + cross; bot import smoke; verify LOC <=50 via terminal inspect; greps for rules (1svc count, 0 Package active, delegates comments, pure docstrings, logs, UI pins).

**DoD:**
- [ ] ruff clean (or documented pre-exist tol).
- [ ] Golds: `python -m pytest tests/handlers/test_promotion_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` + -k "TestPromotionAdminPureHelpers or build_promotion or compute_ or promo" + broader -k "promotion or promo or admin_promo or TestPromotionAdmin" + cross smoke (e.g. -k "admin or promotion") green (0 attributable reg).
- [ ] Bot smoke: python -c "import bot; print('bot ok')".
- [ ] Inspect LOC + greps pass (1svc >=N, 0 bare Package, puros present, UI strings match).
- [ ] GSD pre logged for each gate/ruff/pytest/grep.

**Exact files changed:** only log + possible ruff auto on touched.

**GSD pre-log instruction:** "GSD pre-ruff F6 + GSD pre-pytest F6 <files> (gold cmds) - exact flags from PLAN + precedents 34/27/ item9 testg; re-runs golds protect; copy al pie."

### Fase 7: Self-check PASSED + handoff + pool phrase

**Objective:** Full self-check PASSED matching precedents (phases/DoD/gates/archivos/tests passed; reglas: GSD pre every, scope tight 3 files + log + 0/0/0/0 beh in promotion CRUD/interests, 1svc Promotion via get_service + delegates for package, LOC<=50 via inspect, logging, pure helpers tests 10+ import-inside, no prod chg); verify 3 crit protected (promo admin orthogonal to gamif/narr/chan; re-runs protect); UI 1:1; arch/testg readiness. Append final to log + handoff "Item 2/35 closed. Second of new pool of 4. ... Ready for arch-enforcer + test-guardian + documentador + next".

**DoD:**
- [ ] Self-check PASSED full template in log (copy structure from 34-reward self-check + 27-mission).
- [ ] Pool phrase verbatim present multiple times + "Item 2/35 closed. Second of new pool of 4."
- [ ] Handoff explicit.
- [ ] GSD pre for self-check.
- [ ] All prior DoDs green.

**Exact files changed:** log only (self-check entry).

**GSD pre-log instruction:** "GSD pre self-check F7 <log> (final) - full verif phases/DoD/0/0/0/1svc/puros/LOC/UI1:1/3crit/GSD/phrase; copy al pie 34/27 precedents; handoff to arch-enforcer + test-guardian."

---

## 3. Golds / Critical tests to protect (exact cmds from impact + precedents)

- `python -m pytest tests/handlers/test_promotion_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` (full handler + pure class post)
- `-k "TestPromotionAdminPureHelpers or build_promotion_confirm_text_and_keyboard or compute_file_text_for_confirm or build_promotion or select_package or show_promotion_confirmation or Paso X de 5"` (pure + wizard UI)
- Broader: `-k "promotion or promo or admin_promo or TestPromotionAdmin or promotion_admin"` (156p+ precedent style from pool33)
- Cross smoke: `-k "admin or promotion or promo" + atomic/cross/reaction/daily/vip if relevant (orthogonal)`
- Bot smoke + delegate smoke (has get_available_packages_for_promo_wizard True)
- Re-runs protect "suite protege adecuadamente" + 0 attributable reg (per test-guardian precedent).
- Precedents golds re-runs as needed for pool (no touch to atomic/reaction golds).

## 4. Verification gates

- Arch-enforcer: PASS / PASS WITH NOTES 0 critical target (scope tight 3 files; 1svc via get_service confirmed; 0 PackageService active; 10+ puros + LOC<=50 via inspect; delegates + comments exact; UI 1:1 + Lucien preserved; logging; 3 crit protected orthogonal (promo admin config read+create orthogonal to user "me interesa"/interests atomic if any + gamif credit; re-runs protect); GSD pre + self + phrase; no new long/0 creep/0 beh/0 atomic/0 prod).
- Test-guardian: "suite protege adecuadamente" (re-runs exact per PLAN F6 + handler 100% + 10+ pure + broader green; ports faithful; pure direct real exec import-inside; 0 attr reg; coverage on puros/ports/delegates; pre-exist only non-attrib).
- Self-check PASSED (full in F7 log; matches 34-reward/27-mission template verbatim structure).
- Pool phrase repeated in PLAN/SUMMARY/gsd/self/hand off/ROADMAP (by docu).

## 5. Instrucciones para gsd-executor

Copy patterns **al pie de la letra** from 34-reward-admin-wizard + 27-mission-admin-long-funcs (get_service in every entrypoint incl all wizard message/cb steps, thin delegates with exact comment + import-inside + arch "Added for item 2/35 ... precedent item 8/9/34", puros with "Función pura..." docstring + verb+context+result + 1:1 move, Test*PureHelpers import-inside + @patch only on svc not puros, inspect for LOC post F3/F5, UI 1:1 pin in tests "Paso X de 5" / Lucien / price / file texts / empty / backs / cbs, logging inside withs, no behavior change). GSD pre every edit/gate/ruff/pytest/grep/smoke/self-check (append to .planning/quick/gsd-35-promotion-admin-wizard.log + wc -l). 3 crit (promo admin orthogonal; gamif/narr/channel 0 direct mutation; re-runs of cross + atomic protect indirectly). Use optional imports inside delegates/tests. No prod/0 beh/0 atomic/0 other handlers/0 package core/0 promotion user flows change. Self-check PASSED at end with exact structure + phrase + handoff. "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

**Tentative list of puros (from impact + precedent patterns):** build_promotion_confirm_text_and_keyboard, build_promotion_step_text, compute_file_text_for_confirm, build_promotion_list_entry_and_button, build_promotion_detail_text_and_keyboard, build_promotion_delete_confirm_keyboard, compute_promotion_price_display, compute_dates_text, build_interest_list_text_and_buttons, build_blocked_user_text_and_keyboard (and 1-2 small computes for status/available).

**Safe points:** After F1 (baseline), F2 (1svc uniform no delegate yet), F3 (delegates only), F4 (puros + slim), F5 (ports + pure tests), F6 (gates).

Handoff: "Ready for gsd-executor (copy 34-reward + 27-mission al pie + GSD pre + self-check) + arch-enforcer + test-guardian. Item 2/35 second of new pool of 4."

"Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."
