# PLAN: Refactor long functions in store_admin_handlers.py to <=50 LOC + ensure exactly 1 service call per handler (StoreService via get_service) (Item 8 / second of new pool of 4)

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-06-08  
**Focus:** Tight, conservative, phased refactor of `handlers/store_admin_handlers.py` (long functions >50L and inline biz/UI calc in stock_alerts~56L, list_products~54L, product_admin_detail~54L, handle_delete_product~55L + process_* / confirm_* / admin_store_menu~40L / restock~ etc; plus direct PackageService() instantiation in process_product_description wizard step violating "exactly 1 service"). Ensure **every handler entrypoint calls exactly 1 service** (StoreService via standardized `with get_service(StoreService) as store_service:` context + get_service lifecycle). Extract pure helpers (verb+context+result; stateless, no side-effects, importable, unit-testable) for stock/UI/wizard formatting and builders (e.g. `compute_stock_emoji_and_text`, `compute_restock_new_stock`, `build_*_text_and_buttons`, `build_product_detail_keyboard`, `build_product_confirmation_text_and_keyboard` etc.) to bring all functions <=50 LOC source. Minimal support ONLY in `services/store_service.py` (thin delegate `get_available_packages_for_store()` for wizard pkg select to keep handler boundary at exactly StoreService + pure top-level `compute_stock_emoji_and_text(stock, is_low_stock=False) -> tuple[str,str]` 1:1 from prior inline + arch comment + instance delegate compat if pattern). Update ONLY `tests/handlers/test_store_admin_handlers.py` (port the 5 TestProcessProductDescription tests from direct PackageService patch to get_service(Store) + mock delegate; update docstrings; add `TestStoreAdminPureHelpers` class with pure unit tests for extracts). **0 other handlers touched**. **0 behavior change in product CRUD/stock (create/get/update/delete, restock, threshold, set -1/0/positive)**. **0 delivery/gamif credit impact** (no complete_order, no besito debit, no orders here; admin product mgmt only; stats "besitos gastados" are read-only aggregates). UI/render identical 1:1 (Lucien 3rd person, exact emojis ♾️🚨⚠️📦, button labels "📝 Reabastecer: name[:25]", list format "✅ name\n   emoji Stock: X | 💰 Y besitos\n\n", wizard "Paso X de 5", confirm "Resumen del producto:\n📦 ...\n📝 ...\n💰 ...\n📊 ...", delete confirm "Estas seguro de eliminar este producto?\n\nEsta accion no se puede deshacer.", back cbs, alerts, empty cases, truncation). Use model's StoreProduct.is_low_stock / stock_status / stock_display where fit + puros for emoji display. 3 critical systems (gamif via besitos indirect read-only in menu/stats "besitos gastados", narrative, channel/VIP) always in mind (0 mutate/credit/deliver; read+admin-mutate product only). GSD pre-log discipline on `.planning/quick/gsd-store-admin-long-funcs.log` (cross-ref gsd-impact-analyzer-item8-store-admin-long-funcs.log) before every edit/gate/verif. Follow structure/patrones/snippets **al pie de la letra** from successful precedents (phase25 item7 reward-handlers-1service-loc PLAN + its gsd log for 1-service + pure helpers extract + ports + LOC inspect + self-check + BATCH/POOL note; 20-reward-gamif PLAN + gsd-reward-gamif-item2.log for reward 1-service + pure + delegate + port + helper tests; 23/24 for item phasing + BATCH close language "4 items completed in this tirón (Item 6 final of max 4)" + "Item X/24 closed. BATCH..."; item2/5/6 gsd for pure extract + test ports + "Arch-enforcer addressed"; golds mission_user_handlers.py + test for 1-service + get_service context + __enter__/__exit__ + rel patterns; item8 impact report as source of truth for map/risks/tests/scope/design "min support (delegate for pkgs + puros for status)" + exact code blocks for delegate/pure + port instructions + "segundo del nuevo pool de 4").

**Input principal (source of truth):** 
- Complete impact-analyzer report: `.claude/agent-memory/impact-analyzer/item8-store-admin-long-funcs.md` (executive summary, mapa de impacto with exact files: handlers/store_admin_handlers.py + min support en store_service + tests/handlers/test_store_admin_handlers.py; riesgos low due to precedents + tight scope; tests críticos (handler test full + package get_available gold + -k store/product/TestStoreAdmin + bot smoke + LOC verifiers); scope tight recomendado "solo store_admin_handlers.py + min support en store_service (e.g. pure helpers para stock/status, delegate para pkgs) + updates en test_store_admin_handlers.py"; "0 otros handlers, 0 behavior change en product CRUD/stock, 0 delivery/gamif credit impact"; design notes "1 service Store via get_service + delegate para wizard pkgs + puros para status/UI (compute_stock_emoji_and_text etc)"; precedentes de item7/25-reward-handlers-1service-loc + 20-reward-gamif PLAN + item2/5/6; "second of new pool of 4"; "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."; long funcs explicitly: stock_alerts~56L list_products~54L product_admin_detail~54L handle_delete_product~55L + process_* confirm_* admin_store_menu~40L restock~ etc with inline biz/UI calc + direct PackageService in wizard violating 1-svc; StoreProduct model props + store_service API + check_stock_alert etc; greps (get_service calls, PackageService usage only in 1 place in this handler + tests, wiring in handlers/__init__.py + bot.py); 3 crit systems in mind).
- Precedents + golds: `.planning/phases/25-reward-handlers-1service-loc/PLAN.md` + its gsd-reward-handlers-1service-loc.log (exact Item7 first-of-new-pool 1-service + pure helpers extract + ports + LOC inspect via inspect.getsourcelines + self-check PASSED structure + critical list + handoff + "first of new pool of 4" + "previous batch of 4 closed with tests passing per 24-SUMMARY BATCH note"); `.planning/phases/20-reward-gamif-rules-compliance/PLAN.md` + gsd-reward-gamif-item2.log (Item2 reward 1-service + pure emoji promotion + delegate + port of test to get_service + real pure via .xxx attrs + __exit__ closes + docstrings "Tests ported to 1-service pattern... Arch-enforcer note addressed" + new Test*PureHelpers class + re-runs + LOC inspect + self-check PASSED + critical tests list + handoff); 23/24 PLANs + SUMMARYs (BATCH close language "4 items completed in this tirón (Item 6 final of max 4)", "Item 6/24 closed. BATCH...", self-check structure, GSD style); gsd-testing-debt-item5.log / item6.log (ports of docstrings + asserts to "1 service" + pure formatting); gsd-getservice-unification.log + 21-PLAN (with/get_service context patterns + __enter__/__exit__ mocks in tests); handlers/mission_user_handlers.py + test_mission_user_handlers.py (1 service + get_service context + rel patterns); current source (store_admin_handlers.py has get_service(Store) in most but not all wizard steps + long funcs + direct PackageService in process_product_description; store_service holds package_service + has get_available_packages_for_store on it + stock methods + model props underused in handler; test_store_admin_handlers.py has most get_service ports but 5 desc tests still patch PackageService directly); impact report + MEMORY.md pointers; CLAUDE.md (root + handlers + services + models), rules.md (≤50 LOC, verb+context+result naming, logging "módulo | acción | user_id | resultado", exactly 1 service per handler entrypoint), architecture.md (handlers→services→models), decisions.md, AGENTS.md, services/store/CLAUDE.md (store domain, stock conventions -1/0/>0, delegate pattern awareness), models/CLAUDE.md (rels for access safe; no new models here), handlers/CLAUDE.md (1 service rule, no biz logic, no DB).

**GSD enforcement:** Executor MUST prefix **every** modification / pre-gate / verification / ruff / pytest / grep / smoke / self-check / summary with a GSD log append (timestamp | PHASE | description) to `.planning/quick/gsd-store-admin-long-funcs.log` (use the item8 impact one for cross-ref if needed). Use identical discipline, entry style, wc -l tracking, "pre-xxx <file> (F<N> <short motive>) - <desc + refs DoD + patrones copiados al pie de la letra>", and self-check structure as gsd-reward-handlers-1service-loc.log (item7, 40+ entries, phases complete + SAFE POINT + FINAL self-check PASSED + POOL/BATCH note) / gsd-reward-gamif-item2.log (46+ entries) / gsd-remaining-besito-compositions.log (BATCH note) / gsd-reward-besito-eventbus.log. No edits (even to PLAN/log beyond appends) without pre-log. Planner did INIT + pre-mkdir + pre-write (3 entries, wc tracked to 3).

---

## 1. Alcance preciso (In / Out explícito + archivos exactos)

### En esta entrega (scope "tight" per impact report + user spec + "no creep" + precedents item7/25 + item2/5/6):
- **handlers/store_admin_handlers.py** (core): Ensure/keep **exactly `with get_service(StoreService) as store_service:`** (1 call only per entrypoint/handler). Remove the bare `from services.package_service import PackageService` + direct `package_service = PackageService(); packages = package_service.get_available_packages_for_store()` in `process_product_description` (the wizard desc step); replace with `packages = store_service.get_available_packages_for_store()` inside its own `with get_service(StoreService) as store_service:` (or integrate if step already opens one; each message/cb entrypoint does exactly 1). Extract 1-2+ pure helpers per long flow to slim the listed funcs (stock_alerts, list_products, product_admin_detail, handle_delete_product, process_restock_amount, confirm_create_product, process_product_description, admin_store_menu, restock_product, show_product_confirmation, etc.) to <=50 lines source (def to end, incl docstring per inspect.getsourcelines precedent). Recommended extracts (copy logic 1:1 for identical render; verb+context+result; pure = no with, no await, no logger, no FSM/state, no DB):
  - `compute_stock_emoji_and_text(stock: int, is_low_stock: bool = False) -> tuple[str, str]`: the if/elif for ♾️/∞ , 🚨/AGOTADO , ⚠️/num , 📦/num (1:1 from list_products 537-548 and stock_alerts usage + model is_low_stock).
  - `compute_restock_new_stock(current_stock: int, amount: int) -> int`: the "0 if -1 else + amount" (from process_restock_amount 235-236).
  - `build_stock_alerts_text_and_buttons(low_stock, out_of_stock) -> tuple[str, list[list[InlineKeyboardButton]]]` (or equiv split) to slim the out/low sections + Restock cbs + name[:25] in stock_alerts.
  - `build_product_list_entry_and_button(product) -> tuple[str, list[InlineKeyboardButton]]` or `build_product_admin_list_text_and_buttons(products) -> tuple[str, list]` to slim the loop in list_products (status/stock_emoji dupe logic + price + ProductAdminDetailCallback).
  - `build_product_detail_keyboard(product_id: int, is_active: bool) -> InlineKeyboardMarkup`: the 5-row kb (toggle/restock/config/delete/back) from product_admin_detail.
  - `build_product_confirmation_text_and_keyboard(data: dict) -> tuple[str, InlineKeyboardMarkup]`: slim show_product_confirmation (or extract the text/kb build).
  - Possibly small `build_wizard_step_text(...)` or per-step if helps LOC, but tight/minimal: only as needed for the long ones.
  Keep all other _build_* / process_* validation as-is if already small (or slim inline if roza 50). Preserve: logs (enhance to "store_admin_handlers | <action> | user_id=... | result=..." inside withs post-success per rules if missing), is_admin guards, FSM states (ProductWizardStates, ProductRestockStates), state update_data/get_data/clear/set_state, late? imports in tests, callback packing (Restock/SelectPkg/ProductAdminDetail/ConfigStockAlert/Toggle/Delete with confirmed), /skip, int parses + validates, error paths/answers, cancel cbs to "admin_store", internal calls (e.g. toggle -> product_admin_detail same module), Lucien voice 3rd person, exact strings/emojis/cbs/texts/UI, truncation name[:25]/[:30], stock -1/0/positive handling in display vs update, empty cases, alerts. Post: verify no function >50 lines (inspect or wc on def-to-end); all entrypoints 1 svc Store via get_service; grep 0 "PackageService" active in handler. No new imports of PackageService; no DB; no biz logic (CRUD in svc; calcs/UI in puros or svc). Use model product.is_low_stock / stock_status / stock_display where fit to reduce dupe.
- **services/store_service.py** (soporte mínimo only): 
  - Add thin delegate (before or after class, or as method with comment):
    ```python
    def get_available_packages_for_store(self) -> list[Package]:
        """Thin delegate to internal package_service.get_available_packages_for_store().
        Added for item8: enables store_admin_handlers product creation wizard to call exactly 1 service (StoreService) per handlers/CLAUDE + arch rules.
        Not core CRUD. 0 behavior change.
        """
        return self.package_service.get_available_packages_for_store()
    ```
  - Promote/add pure top-level helper (module level, before class; follow item7 get_reward_emoji exact style + impact exact block):
    ```python
    def compute_stock_emoji_and_text(stock: int, is_low_stock: bool = False) -> tuple[str, str]:
        """Función pura (sin estado ni side-effects). Soporte para UI de admin store (list/alerts).
        1:1 de lógica previamente inline en store_admin_handlers (item8, arch-enforcer long-funcs note addressed).
        """
        if stock == -1:
            return "♾️", "∞"
        if stock == 0:
            return "🚨", "AGOTADO"
        if is_low_stock:
            return "⚠️", str(stock)
        return "📦", str(stock)
    ```
    (Optionally the 1-line instance delegate compat per item7 pattern, with comment "# Backward-compatible delegate added for Item 8 (arch-enforcer 1-service rule for store_admin handlers).")
  - Add arch comment near top or in the delegate/pure: "# Support added for store_admin_handlers 1-service + pure extract (item8). Arch-enforcer note (long funcs + direct PackageService in wizard + inline biz/UI calc) addressed. Precedent item7."
  - 0 changes to: create_product / get_product / get_all_products / get_available_products / update_product / delete_product / get_store_stats / get_low_stock_products / get_out_of_stock_products / update_low_stock_threshold / check_stock_alert / notify_stock_alert / any cart/order/complete_order/direct_purchase / besito interactions / package held init / close / _init_services / anything in purchase paths / atomicity contracts. (Already in current tree per analysis + store_service read; this item confirms/ensures + adds the min support only.)
- **tests/handlers/test_store_admin_handlers.py** (only its test file): Port/confirm: the 5 tests in TestProcessProductDescription (test_with_skip_sets_none, test_with_description_saves_it, test_no_packages_shows_error, test_advances_to_selecting_package, and the internal ones) change from `@patch("handlers.store_admin_handlers.PackageService")` + `mock_pkg_svc.return_value.get_available_packages_for_store.return_value = [mock_pkg]` (etc) to `@patch("handlers.store_admin_handlers.get_service")` + `mock_store = MagicMock(); mock_store.get_available_packages_for_store.return_value = [mock_pkg]; mock_context = MagicMock(); mock_context.__enter__.return_value = mock_store; mock_get_service.return_value = mock_context` (setup like other classes in file); adjust late import/await calls; assert on store mock call (not pkg); keep exact data/text/state asserts + "No hay paquetes" etc + state transitions. Update/refresh docstrings (keep/ensure "Tests ported to 1-service pattern (get_service(StoreService) only + delegate for packages in wizard) + pure UI helpers (compute_stock_emoji_and_text etc). Arch-enforcer note (long funcs >50L, business logic/UI bloat in handlers, direct other svc in wizard) addressed. Precedent from item7 (reward) + item2/5/6."). **Add**: new class `TestStoreAdminPureHelpers` (or equiv) at end (after last class; pattern item7 F5 / item2 F5): pure unit tests (import inside per file conv; no @patch, no DB, no fsm/cb fixtures or minimal; at least 5-8 cases: compute_stock_emoji_and_text for unlimited/-1, out/0, low + is_low=True/False, available/normal; compute_restock_new_stock from -1/0/5 + amounts; build_*_keyboard (len rows, exact button texts incl "📝 Reabastecer: name[:25]" or equiv, packed cb data via .pack() contains id, back targets like "stock_alerts"/"admin_store"/"list_products"); build text summaries (confirm "Resumen del producto" with name/desc None->"Sin descripcion"/price/stock_text); stock cases in list entry if a builder touches). Keep: all existing structure (pytestmark unit, make_callback/make_fsm_context/make_message, late `from handlers.store_admin_handlers import ...` after patch, PropertyMock if used, manual mock_context __enter__, asserts on edit_text call_args[0][0] exact phrases like "Paso 1 de 5", "Resumen del producto", "seguro de eliminar", stock indicators "♾️"/"🚨"/"⚠️"/"📦", "Producto creado", cb.answer, mock_store.create_product called with..., get_all with active_only=False, etc.); the inline class at EOF for ProductWizardStates; the patched_detail hack in toggle test. 0 direct PackageService patches left in this file post-port. 0 new tests outside this file.
- **GSD + artefacts**: run_terminal append BEFORE every edit/write/gate/verif (to .planning/quick/gsd-store-admin-long-funcs.log); track wc -l; specific git add only touched (if committing); ruff/pytest gates with exact flags `-p no:cov --override-ini="addopts="`; self-check PASSED at end with full structure (phases/DoD/gates/archivos/tests que pasaron/reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0 behavior chg in CRUD/delivery, 1svc Store via get_service + delegate for pkgs, LOC<=50 via inspect, logging, pure helpers tests, no prod chg)/desviaciones/tests críticos para futuro (store admin handler test full, package get_available_packages_for_store gold, cross -k "store or product or TestStoreAdmin or admin_store", bot smoke, ruff+greps+LOC verifiers)/"Item 8/26 closed. Second of new pool of 4. Previous batch of 4 (ending with Item 7/25 reward-handlers-1service-loc + Item 6/24 remaining-besito-compositions) closed with tests passing per 24-SUMMARY BATCH note + 25 self-check PASSED. Ready for arch-enforcer re-scan (enfocado en store_admin_handlers: exactly 1 service + <=50L + no direct PackageService + pure helpers for stock/UI/wizards) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4").
- **Verification**: the 3 files ruff clean; handler test file 100% pass (behavior identical); critical list re-run (store admin test full + package get_available gold + broader -k store|product|TestStoreAdmin|admin_store + bot smoke + line counts <=50 post via inspect + outputs match pre via test asserts on strings/emojis/cbs + 0 beh change in create/update/delete/restock/stock set/threshold); 0 change to gamif besito credit paths or other crit (re-runs of cross protect indirectly). Grep: 0 "PackageService" (active) in handler; all entrypoints have get_service(StoreService); delegate/pure present in svc with comments.
- Memory: cross-ref impact report + this PLAN + GSD log entries.

**Archivos que se modificarán (exactos, por orden de fases; prefer extend, minimal):**
1. `.planning/quick/gsd-store-admin-long-funcs.log` (all phases, pre only via echo; no "edit" of source beyond appends; wc tracked; planner INIT/pre-mkdir/pre-write 3 entries).
2. `services/store_service.py` (F2: min support -- thin delegate get_available_packages_for_store + pure top-level compute_stock_emoji_and_text (exact from impact) + arch comments + instance delegate if pattern; 0 core CRUD).
3. `handlers/store_admin_handlers.py` (F3: remove direct PackageService import + bare use in process_product_description (use delegate via store_service); extract 1-2+ pure helpers per long flow (compute_stock_emoji_and_text, compute_restock_new_stock, build_*_text_and_buttons / build_product_detail_keyboard / build_product_confirmation... etc); slim all listed long funcs + callers to <=50 LOC; ensure/keep exactly 1 with get_service(StoreService) per entrypoint; add/ensure logs standard; UI render 1:1).
4. `tests/handlers/test_store_admin_handlers.py` (F4: port the 5 desc wizard tests (PackageService patch -> get_service(Store) + delegate mock + assert on store); update/confirm docstrings "ported to 1-service... Arch-enforcer note addressed"; add TestStoreAdminPureHelpers class with pure unit tests (import inside); keep 100% prior coverage + asserts; behavior identical).
5. Re-runs/gates/verifs/smokes do not modify (except ruff auto-fixes if any on touched + log appends).

**Fuera explícitamente (nada de scope creep, per "tight" + impact "0 otros handlers" + "0 behavior change en product CRUD/stock" + "0 delivery/gamif credit impact" + "0 docs más allá de lo necesario para el item" + precedents):**
- **NO** otros handlers (store_user_handlers.py even if similar legacy, category_admin/promotion/reward/package/story/mission/gamif/trivia admins, gamification_admin_handlers for entry button, common, broadcast, etc. — even if they touch packages/products/store).
- **NO** package_service.py (no changes; delegate calls it; its get_available_packages_for_store remains canonical; unit tests in tests/unit/test_package_service.py cover it directly -- 0 impact, still pass).
- **NO** models (no new props/methods; use existing is_low_stock/stock_status/stock_display + Package for wizard), 0 keyboards/* (no new builders or cb changes; all built inline), 0 bot.py, 0 handlers/__init__.py, 0 services/__init__.py, 0 utils, 0 lucien_voice, 0 config, 0 middlewares.
- **NO** changes to core StoreService: create_product, get_*, update_product (incl stock=-1), delete_product, get_store_stats, get_low/out_stock_products, check_stock_alert, update_low_stock_threshold, complete_order, cart_*, direct_purchase, notify_*, _init_services, besito/package held, close, anything in purchase paths, atomicity contracts.
- **NO** change to purchase/besito flows (complete_order debits etc remain in user path; admin product mgmt is orthogonal).
- **NO** new tests outside the store_admin test file (no service tests for delegate/pure; no integration new files).
- **NO** edición de CLAUDEs (incl services/store/CLAUDE.md + handlers/CLAUDE.md), decisions.md, AGENTS, ROADMAP, fase_*, docs/, refactor_testing.md, o cualquier .md excepto este PLAN + el log GSD (impact report + MEMORY already done by analyzer).
- **NO** broad "fix all store wizards" or "touch store_user for parity" or "refactor package_service".
- **NO** behavior or contract changes (0 impact on product CRUD values, stock set/restock/threshold, wizard FSM transitions, UI strings/emojis/buttons/cbs, alerts, empty/error cases; delegate transparent passthrough; extracts pure 1:1 move of prior inline).
- 0 impact on 3 critical systems' core contracts (gamif credit/debit/missions/rewards delivery, narrative progress/archetypes/achievements, channel/VIP subs/pending/approve/auto-approve; this flow admin product mgmt + read stats "besitos gastados" aggregate only; re-runs of cross protect indirectly).

**Comportamiento observable idéntico + reglas:** All text construction, emoji choice (♾️/🚨/⚠️/📦), button labels/texts ("📝 Reabastecer: name[:25]"), cb packing (RestockProductCallback etc with confirmed), logging format, empty/error cases ("No hay productos", "No hay alertas", "Producto no encontrado", "Estas seguro...", "Error al..."), wizard FSM steps/transitions ("Paso X de 5", /skip, name>=3/price>0/stock>=0 validates, state data name/desc/package_id/price/stock/product_id/product_name, set waiting_* / confirming / clear), stock calcs for display/update (current=0 if-1, new=current+amount, set -1 unlimited), package list for wizard (name, file_count, store_stock ∞/-1/num), confirm summaries, list/detail/alerts formats, navigation (back to admin_store / list_products / stock_alerts / product_admin_detail_{id} string hacks), are in puros (mechanical 1:1 move of existing inline) or the entry handlers or svc (unchanged CRUD). Delegate is transparent passthrough. Extraction preserves every string/emoji/branch exactly. Handlers call exactly 1 service (StoreService); funciones <=50 LOC post-extract; logging en formato estándar "store_admin_handlers | <action> | user_id=... | result=..." para acciones importantes; get_service context manager; sin lógica de negocio en handlers; sin acceso DB fuera de models; pure helpers (no side effects, importable, fácil unit test, verb+context+result naming). 3 sistemas críticos protegidos (read+admin-mutate product only; 0 side effects en gamif credit / narrative / VIP-channel; stats read-only aggregates; re-runs protect).

**Artefactos:** Este PLAN.md + entradas GSD completas en el log dedicado (pre every) + (si procede en executor) SUMMARY.md posterior (seguir precedente 25/24/23/20). Memory/hand-off ya apunta desde impact report + MEMORY.md.

---

## 2. Fases ordenadas (5-6 fases pequeñas, secuenciales, con gates estrictos)

### Fase 1: Preparación (GSD log init/confirm, baseline, fixtures/patterns, patrones gold, LOC actual, confirm 1svc + PackageService direct sites, UI strings for pinning)

**Objective:** Establecer disciplina GSD para el Item (log touched by planner + executor first entries); confirmar baseline de archivos tocados (ruff clean + targeted pytest verde pre-cambios); mapear estado actual (most get_service(Store) already but process_product_description has bare PackageService() + long funcs >50L with inline stock/UI calc + button loops + wizard texts; inspect LOC on stock_alerts/list_products/product_admin_detail/handle_delete_product + key process_*/confirm_*/show_product_confirmation/admin_store_menu/restock_*; grep for PackageService direct + get_service(StoreService) sites + "with get_service" count; confirm fixtures (make_callback, make_fsm_context, make_message), patrones gold (get_service patch + __enter__/__exit__ from test_store_admin itself + item7/25 port + mission_user; real pure via attrs if any; mock_store.get_available... for delegate port); identificar los helpers a extraer (stock emoji/text, restock calc, build lists/alerts/detail/confirm kbs/texts) from impact recs + current inline; confirmar UI strings exactas para pinning en nuevos tests de helpers ( "♾️"/"🚨"/"⚠️"/"📦", "∞"/"AGOTADO", "Stock bajo", "Agotados", "Paso 1 de 5", "Resumen del producto", "seguro de eliminar", "Producto creado", "No hay productos", "No hay paquetes", button "📝 Reabastecer: name[:25]", "Ver productos", "Alertas de stock", etc.); GSD pre/post (varias); "F1 safe point - baseline verde + ready for F2; no source changed yet".

**DoD checklist (marcar al completar):**
- [ ] Log `.planning/quick/gsd-store-admin-long-funcs.log` exists with planner INIT/pre-mkdir/pre-write entries (wc >=3) + at least 1 pre-F1 of executor.
- [ ] Baseline: ruff clean on the 3 target files (`./venv/bin/python -m ruff check handlers/store_admin_handlers.py services/store_service.py tests/handlers/test_store_admin_handlers.py --fix && ./venv/bin/python -m ruff format --check ...`).
- [ ] Baseline targeted pytest verde (clean flags exact): `./venv/bin/python -m pytest tests/handlers/test_store_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` (all classes ~30+ tests; expect green as most already ported; only desc 5 use direct pkg).
- [ ] Confirm gold patterns via grep/lectura + python inspect: current long funcs LOC (stock_alerts~56, list_products~54, product_admin_detail~54, handle_delete_product~55, process_product_description~41, process_restock_amount~40, confirm_create_product~40, admin_store_menu~40, restock_product~31, show_product_confirmation~33 etc per impact); grep -n "get_service(StoreService)" + "from services import get_service" + "from services.store_service import StoreService" in handler (present in most); grep -n "PackageService" in handler (exactly 1 site: the bare in process_product_description + its import); "if not packages:" present in desc step; mock patterns in test (get_service patch + __enter__ in most classes, late imports, make_* fixtures, exact text asserts on edit_text/answer, state checks, mock_store.create_product / get_all_products(active_only=False) / get_low/out / get_store_stats etc); strings like "Paso 1 de 5", "Resumen del producto", "seguro de eliminar", "♾️"/"🚨"/"⚠️"/"📦", "Stock: ∞", "AGOTADO", "Stock bajo", "Agotados", "Producto creado", "No hay productos", "No hay paquetes", "Reabastecer: ", "admin_store", "stock_alerts", "list_products" for pinning.
- [ ] Read precedents (item7/25 PLAN + gsd log excerpts for ports + helper extract + self-check + BATCH/POOL; 20/item2 gsd for delegate + pure + 1-line + port of test + helper tests + LOC inspect; 24 SUMMARY for BATCH close language to cite in final self-check; mission_user for 1svc+get_service+__enter__/__exit__; impact for exact delegate/pure code blocks + port desc instructions + "second of new pool").
- [ ] GSD pre + post entries for baseline (multiple; wc tracked).
- [ ] Safe point F1.

**Archivos:** Log + (lectura/grep/ruff/pytest/inspect; 0 edits to prod/tests in F1 except hygiene ruff if auto).

**Cambios clave (bullets accionables):**
- Ejecutar comandos de baseline (ver "Instrucciones para el gsd-executor" + sección 5).
- Grep/lectura rápida + python -c inspect for LOC + patterns (copy from item7/25 F1/F3 gates: `python -c 'import inspect; from handlers.store_admin_handlers import stock_alerts, list_products, product_admin_detail, handle_delete_product, process_product_description, process_restock_amount, confirm_create_product; for name, fn in [("stock_alerts", stock_alerts), ...]: src=inspect.getsourcelines(fn)[0]; print(name, "LOC:", len(src))'`).
- Confirm import of Package in svc if needed for delegate type (from models); make_* fixtures from conftest.
- Actualizar log con "F1 baseline verde + patterns confirmed (most 1svc via Store get_service already; 1 outlier direct PackageService in process_product_description wizard + long funcs >50L with inline stock/UI calc + button loops + wizard texts; LOCs inspected; UI strings pinned; previous batch closed per 24/25 SUMMARY BATCH note; this is second of new pool of 4 per impact) + ready for F2".
- (No code changes in F1 logic.)

**Tests que deben pasar antes de avanzar (gates de F1):**
- Ruff on the 3 files (or 2 if hygiene only on test/handler).
- `pytest tests/handlers/test_store_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` (full; ~30+ or current count).
- Grep/inspect confirm + GSD entries + "F1 safe point".
- (Optional) spot broader `pytest -k "store or product or TestStoreAdmin or admin_store" -q --tb=line -p no:cov --override-ini="addopts="` for cross flows (no edit expected); package unit for get_available if want `pytest tests/unit/test_package_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "available_packages_for_store"`.

**Riesgos + mitigaciones:**
- Riesgo: baseline shows pre-existing unrelated fails (alembic, daily concurrent, cross daily !success, N806, SAWarnings, unraisable, RuntimeWarning AsyncMock in _safe_answer, MovedIn20Warning, Deprecation utcnow, InternalEventBus.emit not awaited, etc.) → Mit: document in log (precedent 25/24/23/22/20/19 "do not count as regression"); use targeted -k; focus "0 attributable to this Item".
- Riesgo: LOC count varies by comments/docstring (e.g. 54-56) → Mit: use inspect.getsourcelines (incl def) as in item7/25 F3/F5 + item2 F3; trim only if post-extract >50 (rare); mechanical extract of 5-15L per long flow (stock 4-8L, kb 8-12L, text 6-10L, calc 2-4L) will drop them.
- Bajo: time on baseline → Mit: targeted, parallel where safe but prefer sequential for log.

**Safe point:** Baseline verde + patterns confirmed (1svc Store mostly; 1 direct PackageService outlier in wizard desc; multiple long >50L with inline stock/UI + button loops + texts; UI strings pinned; previous batch closed per 24/25; this second of new pool) + "F1 safe point - ready for store_service min support (delegate + pure); no source changed yet". Reversible (nada editado en fuentes aún).

---

### Fase 2: Soporte mínimo en StoreService (thin delegate get_available_packages_for_store + pure top-level compute_stock_emoji_and_text + arch comments)

**Objective:** Add the thin delegate (passthrough to self.package_service) so the handler's product creation wizard desc step can call exactly 1 service (StoreService) without importing/using PackageService directly. Add the pure top-level `compute_stock_emoji_and_text` (exact logic 1:1 from prior inline in handler list/alerts; "Función pura (sin estado ni side-effects)"; follow item7 get_reward_emoji style + impact exact block). Add arch comments. This enables (and maintains) the handlers to comply with exactly 1 service at boundary. Ruff + smoke + grep (2 new defs or 1+delegate) + targeted store/package tests (non-blocking if only handler port pending). GSD pre. Safe point.

**DoD checklist:**
- [ ] Thin delegate `get_available_packages_for_store(self) -> list[Package]` added to `services/store_service.py` (passthrough; docstring exact "Thin delegate... Added for item8: enables store_admin_handlers product creation wizard to call exactly 1 service (StoreService) per handlers/CLAUDE + arch rules. Not core CRUD. 0 behavior change."; or close variant per impact).
- [ ] Pure top-level `compute_stock_emoji_and_text(stock: int, is_low_stock: bool = False) -> tuple[str, str]` defined at module level in store_service.py (before class; logic 1:1 from handler; docstring "Función pura (sin estado ni side-effects). Soporte para UI de admin store (list/alerts). 1:1 de lógica previamente inline en store_admin_handlers (item8, arch-enforcer long-funcs note addressed)."; branches for -1/0/low/normal exact).
- [ ] (If pattern followed) Instance delegate `def compute_stock_emoji_and_text(self, ...)` is 1-line calling the pure; comment "Backward-compatible delegate added for Item 8 (arch-enforcer 1-service rule for store_admin handlers)." present (or added).
- [ ] Arch comment present near delegate/pure or top: "# Support added for store_admin_handlers 1-service + pure extract (item8). Arch-enforcer note (long funcs + direct PackageService in wizard + inline biz/UI calc) addressed. Precedent item7."
- [ ] Imports necesarios ya presentes (Package from models.models for delegate return type if annotated; logging no requerido en pura).
- [ ] Sin cambios de comportamiento: for a stock + is_low given, the retorno (emoji, text) is idéntico (smoke 4 branches: -1/unlimited, 0/out, low + is_low=True, normal/positive + is_low=False); delegate for pkgs returns same list as direct (smoke via real or mock).
- [ ] Ruff limpio en el archivo.
- [ ] Smoke de import + llamada básica (pure 4 branches + delegate pkgs on real svc instance if possible + close) pasa.
- [ ] Grep confirma la pura + delegate: `grep -n "def get_available_packages_for_store\|def compute_stock_emoji_and_text" services/store_service.py` (muestra las defs + any delegate).
- [ ] GSD pre-edit + pre-gate entries en el log.
- [ ] Safe point.

**Archivos:** `services/store_service.py`

**Cambios clave (bullets accionables, orden sugerido):**
- Pre-log GSD "pre-edit services/store_service.py (F2 add min support delegate + pure compute_stock_emoji_and_text + comments) - refs DoD F2 + copy exact delegate/pure code blocks from item8 impact report + 1-line delegate + arch comment style from item7/25 PLAN F1/F2 + item2 gsd; read pre done; 0 change to core CRUD".
- Insert the pure (module level, after logger/imports, before `class StoreService:`) **exact per impact**:
  ```python
  def compute_stock_emoji_and_text(stock: int, is_low_stock: bool = False) -> tuple[str, str]:
      """Función pura (sin estado ni side-effects). Soporte para UI de admin store (list/alerts).
      1:1 de lógica previamente inline en store_admin_handlers (item8, arch-enforcer long-funcs note addressed).
      """
      if stock == -1:
          return "♾️", "∞"
      if stock == 0:
          return "🚨", "AGOTADO"
      if is_low_stock:
          return "⚠️", str(stock)
      return "📦", str(stock)
  ```
- Add the thin delegate (as method in class, or top-level if preferred for pure; but impact shows as instance method for the pkg one since it delegates to held service; place logically near other product methods or at end of products section; exact per impact):
  ```python
  def get_available_packages_for_store(self) -> list[Package]:
      """Thin delegate to internal package_service.get_available_packages_for_store().
      Added for item8: enables store_admin_handlers product creation wizard to call exactly 1 service (StoreService) per handlers/CLAUDE + arch rules.
      Not core CRUD. 0 behavior change.
      """
      return self.package_service.get_available_packages_for_store()
  ```
- (If following item7 1-line pure compat for the emoji one) Add 1-line instance delegate for compute_stock... with comment.
- Add arch comment (e.g. right above the delegate or pure).
- Post-edit: ruff check + format apply si necessary + smoke import+call (4 branches emoji + delegate pkgs + svc instance + close).
- Grep verificación (defs present).
- (Si ya estaba perfecto post-prior: el "cambio" puede ser solo el GSD + confirm; ruff/smoke/grep siguen siendo gates. But per analysis, needs the adds.)

**Tests que deben pasar antes de avanzar (gates de F2):**
- Ruff en el archivo: exit 0.
- Smoke: `./venv/bin/python -c "from services.store_service import StoreService, compute_stock_emoji_and_text; from models.models import Package; from unittest.mock import MagicMock; ..."` (exercise pure 4 branches + delegate pkgs on mock/real held + svc; expect identical returns for emoji; pkgs delegate returns what held returns; no errors; close ok).
- Grep: `grep -n "def get_available_packages_for_store\|def compute_stock_emoji_and_text" services/store_service.py` (shows defs + comments).
- Targeted: `pytest tests/unit/test_package_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "available_packages_for_store" | cat` (exercises real pkg method; delegate will be transparent); any test_store_service if exists for stock paths (non-blocking).
- GSD + "F2 safe point".

**Riesgos + mitigaciones:**
- Riesgo bajo: callers existentes of package_service.get_available... directly (other admins like category_admin, reward_admin, package_handlers) break or perceive dupe → Mitigación: delegate is internal to Store for this admin wizard flow only; other domains legitimately use PackageService directly per their CLAUDE/scope (explicit out); no signature change.
- Riesgo: duplicación accidental (emoji logic vs model stock_status vs svc check_stock_alert dict) → Mitigación: pure is new (moved from handler bloat for display emoji specific to admin list/alerts; model status str + svc alert dict are different contracts); visual + smoke; out of scope to consolidate further per impact "low" risk note.
- Riesgo: delegate "alters" service or causes test impact → Mitigación: passthrough 2 lines; package unit tests unchanged (they call pkg direct); no svc tests need update (delegate transparent); re-runs in F5 exercise via handler port.
- Ningún test directo del emoji sin mocks en svc units (los de handlers lo ejercitarán vía real pure post-port); el port en F4 + re-runs validan.

**Safe point:** Post-ruff + smoke verde + grep defs + GSD "F2 safe point - thin delegate get_available_packages_for_store + pure compute_stock_emoji_and_text added (exact from impact); arch comments; 0 behavior change in core CRUD or pkg method; only this file touched (reversible 1-2 lines if needed)". Handler baseline ready for extract + 1svc enforcement (remove direct pkg).

---

### Fase 3: Refactor handlers de store admin (asegurar exactly-1-service + extraer helpers puros para <=50 LOC; UI idéntica; logging; remove direct PackageService)

**Objective:** En `store_admin_handlers.py`, asegurar que todos los entrypoints (cb + message FSM steps) cumplan "exactly 1 service" (StoreService via get_service; already most, fix the outlier process_product_description by removing bare PackageService import + `package_service = PackageService()` + call, replace with `store_service.get_available_packages_for_store()` inside its with). Extraer 1-2+ helpers puros (compute_stock_emoji_and_text (or import from svc if promoted), compute_restock_new_stock, build_stock_alerts_text_and_buttons or equiv, build_product_list... , build_product_detail_keyboard, build_product_confirmation_text_and_keyboard, etc.) del cuerpo de las long funcs de forma que stock_alerts/list_products/product_admin_detail/handle_delete_product/process_restock_amount/confirm_create_product/process_product_description/admin_store_menu/restock_product/show_product_confirmation etc queden <=50 líneas fuente (ideal <50 estricto post). Preservar exactamente el mismo render (textos, emojis ♾️🚨⚠️📦, botones "📝 Reabastecer: name[:25]", callbacks packed, alerts, wizard steps "Paso X de 5", confirm resumen, delete "seguro...", list "✅ name\n   emoji Stock: X | 💰 Y\n\n", etc.). Añadir/estandarizar logging en formato "store_admin_handlers | <action> | user_id=... | result=..." dentro de los withs post data exitosa. Ruff + inspect LOC + grep 0 PackageService active + 1svc Store + new defs + GSD. Safe point.

**DoD checklist:**
- [ ] Imports: `from services import get_service`, `from services.store_service import StoreService`; **0** menciones a `PackageService` (grep -n "PackageService" ==0 active; import removed; only the one bare site fixed).
- [ ] All cb/message entrypoints that touch svc use `with get_service(StoreService) as store_service:` (most already; process_product_description now opens its with or uses one for the pkgs step; confirm_create_product etc keep theirs; no bare () or direct other svc).
- [ ] process_product_description uses `store_service.get_available_packages_for_store()` (via the delegate added F2) inside its with; the if no pkgs error+clear, loop build buttons with file_count/store_stock (or slimmed to pure builder), set selecting -- preserved 1:1.
- [ ] Helpers puros extraídos: at least `compute_stock_emoji_and_text(stock, is_low_stock=False) -> tuple[str,str]` (or import from svc pure if used that way), `compute_restock_new_stock(current, amount) -> int`, `build_stock_alerts_text_and_buttons(...)`, `build_product_admin_list_text_and_buttons(...)` or split entry/button, `build_product_detail_keyboard(product_id, is_active) -> InlineKeyboardMarkup`, `build_product_confirmation_text_and_keyboard(data) -> tuple[str, InlineKeyboardMarkup]` (or equiv names verb+context+result; lógica copiada 1:1 desde el cuerpo (sin side effects, sin DB, sin async, sin FSM)).
- [ ] Long funcs (stock_alerts, list_products, product_admin_detail, handle_delete_product, process_restock_amount, confirm_create_product, process_product_description, admin_store_menu, restock_product, show_product_confirmation, etc.) fuente <=50 líneas post-extract (verificado con `python -c 'import inspect; from handlers.store_admin_handlers import ...; ... print(len(inspect.getsourcelines(fn)[0]))'` <=50; prefer <50 estricto).
- [ ] Logging estándar presente para las acciones clave dentro de los with (después de obtener datos exitosos; e.g. "store_admin_handlers | list_products | user_id=... | count=..." ; "store_admin_handlers | confirm_create_product | user_id=... | product_id=... | name=...").
- [ ] Comportamiento idéntico: mismos textos/emojis/stock indicators en list/alerts/detail (usa pure o model), mismos botones (status + "📝 Reabastecer: name[:25]" + Restock cb packed, toggle/ restock/config/delete/back in detail), mismos callbacks packed, mismas alerts ("Producto no encontrado", "No hay alertas", "No hay productos", "No hay paquetes", "Error al..."), misma barra/leyenda en wizards, mismos strings "Paso X de 5", "Resumen del producto", "seguro de eliminar", "Producto creado exitosamente", "Reabastecido", "Umbral ... actualizado", truncation exact, back targets, empty cases.
- [ ] GSD pre + gates (ruff, inspect LOC <=50 on targets, grep 0 PackageService + 1svc Store + new defs, smoke import of handler + helpers + delegate, targeted test pre-F4) verdes.
- [ ] Safe point.

**Archivos:** `handlers/store_admin_handlers.py`

**Cambios clave (bullets accionables + snippets/patrón a copiar al pie de la letra de item7/25 PLAN + item8 impact report + current tree + mission precedent):**
- Pre-log GSD "pre-edit handlers/store_admin_handlers.py (F3 remove direct PackageService + extract pure helpers + ensure 1svc Store + slim long funcs) - refs DoD F3 + copy get_service+with from current (most sites) + item7/25 PLAN F2/F3 snippets (pure helper insert near section + body replace + inspect LOC post) + item8 impact (exact delegate usage in wizard, pure compute_stock_emoji_and_text + build_* recs + port desc instructions) + current lines for stock_alerts~92-152, list_products~512-567, product_admin_detail~570-625, handle_delete~728-784, process_product_description~300-342 (the bare PackageService site), process_restock_amount~211-252, confirm_create~466-507, show_product_confirmation~431-463, admin_store_menu~49-90, restock_product~155-187 etc; read pre done; 1:1 UI copy; 3 crit in mind (read stats only)".
- Remove the import: delete or comment `from services.package_service import PackageService` (grep confirm 0 active post).
- In process_product_description (around 306-308): replace the bare block with use of store_service delegate inside a with (pattern: open with for this message step since it needs pkgs; other steps like name/price/stock are pure state/UI no svc):
  ```python
  with get_service(StoreService) as store_service:
      packages = store_service.get_available_packages_for_store()
  # (then the if not packages: ... error+clear+return; the buttons loop using pkg.name/file_count/store_stock; set selecting)
  ```
  (If the step already had partial, consolidate to single with; each entrypoint exactly 1.)
- In the long funcs (e.g. list_products stock indicator block ~537-548; stock_alerts out/low ~119-145; similar in detail/alerts): replace inline if/elif for emoji/text with call to pure (or to svc pure if imported):
  ```python
  emoji, text = compute_stock_emoji_and_text(product.stock, product.is_low_stock)
  # or if promoted on svc: emoji, text = store_service.compute_stock_emoji_and_text(...) but prefer pure top import for "pure"
  ```
- Extract the puros (insert near other helpers or after imports/before routes; docstring "Función pura"; names verb+context+result; copy 1:1 logic):
  (Use the exact pure from F2 / impact if importing from svc; or duplicate minimal if internal only -- but per design prefer the promoted pure in svc and import it like get_reward_emoji in item7. For builds that return kb/text, they are local to handler module as pure builders.)
  Example for stock (if not importing the svc one, or to wrap):
  ```python
  def compute_stock_emoji_and_text(stock: int, is_low_stock: bool = False) -> tuple[str, str]:
      """Construye el emoji y texto de stock para UI de admin (list/alerts). Función pura."""
      if stock == -1:
          return "♾️", "∞"
      if stock == 0:
          return "🚨", "AGOTADO"
      if is_low_stock:
          return "⚠️", str(stock)
      return "📦", str(stock)
  ```
  Similar for compute_restock_new_stock (small):
  ```python
  def compute_restock_new_stock(current_stock: int, amount: int) -> int:
      """Calcula el nuevo stock tras reabastecimiento (maneja ilimitado como base 0). Función pura."""
      base = 0 if current_stock == -1 else current_stock
      return base + amount
  ```
  For builds (examples from impact recs + current; slim the loops):
  ```python
  def build_product_detail_keyboard(product_id: int, is_active: bool) -> InlineKeyboardMarkup:
      """Construye el teclado para detalle de producto admin (toggle/restock/config/delete/back)."""
      buttons = [
          [InlineKeyboardButton(text=f"{'Desactivar' if is_active else 'Activar'}", callback_data=ToggleProductCallback(product_id=product_id).pack())],
          [InlineKeyboardButton(text="📝 Reabastecer", callback_data=RestockProductCallback(product_id=product_id).pack())],
          [InlineKeyboardButton(text="⚙️ Configurar alerta", callback_data=ConfigStockAlertCallback(product_id=product_id).pack())],
          [InlineKeyboardButton(text="🗑️ Eliminar", callback_data=DeleteProductCallback(product_id=product_id).pack())],
          [InlineKeyboardButton(text="🔙 Volver", callback_data="list_products")],
      ]
      return InlineKeyboardMarkup(inline_keyboard=buttons)
  ```
  (Analogous for stock alerts builder, list entry/button, confirm text/kb -- copy the construction logic 1:1 from the bodies; keep truncation, cb packing, back targets exact.)
- In show_product_confirmation (or its callers): delegate the text + kb build to pure if it helps the 33L; dispatch on isinstance target stays.
- Añadir/asegurar logs estándar (dentro del with, post data exitosa; copiar formato de item7/25 F2/F3 + rules "módulo | acción | user_id=... | resultado"):
  e.g. inside list_products with: `logger.info(f"store_admin_handlers | list_products | user_id={callback.from_user.id} | count={len(products)}")`
  inside confirm_create after create: `logger.info(f"store_admin_handlers | confirm_create_product | user_id={callback.from_user.id} | product_id={product.id} | name={product.name}")`
  Similar for stock_alerts, restock success, delete, etc.
- Post-extract: ruff --fix + format --check (apply si dirty per precedent; hygiene 0 logic); inspect LOC of the target long funcs (deben <=50); grep -n "PackageService" ==0 (active); grep for the new def names + calls; grep get_service(StoreService) + withs; smoke import de las funcs + helpers + delegate usage.
- Confirmar que los helpers existentes (si any _build_*) y los nuevos son puros o utils pequeños; UI render 1:1 (los tests de F4 pin exact phrases + emojis + cb + math).
- (Si alguna queda en 50-51 por boilerplate, trim de docstring del helper o comentario "extracted for <=50 LOC rule (Item 8 / arch-enforcer)", precedente item7/25 F3 + item2 F3 "trim de docstring para encajar <=50").

**Tests que deben pasar antes de avanzar:**
- Ruff en el handler.
- Smoke: `./venv/bin/python -c "from handlers.store_admin_handlers import stock_alerts, list_products, product_admin_detail, handle_delete_product, process_product_description, compute_stock_emoji_and_text, build_product_detail_keyboard, ...; from services.store_service import StoreService, compute_stock_emoji_and_text; print('ok')"`
- Inspect LOC: `python -c 'import inspect; from handlers.store_admin_handlers import stock_alerts, list_products, product_admin_detail, handle_delete_product, process_product_description, process_restock_amount, confirm_create_product; for name, fn in [...]: src=inspect.getsourcelines(fn)[0]; print(name, "LOC:", len(src))'` → all <=50.
- Grep: `grep -n "PackageService" handlers/store_admin_handlers.py` → 0 (active); `grep -n "get_service(StoreService)" ...` presente en entrypoints; `grep -n "compute_stock_emoji_and_text\|build_product_detail_keyboard\|..." ...` presente.
- (Los tests funcionales del handler se gatean en F4; aquí basta que el módulo cargue, helpers sean callables, 1svc sites correctos, y LOC ok. Un test spot de refresh si aplica pero tight: no requerido.)
- GSD + "F3 safe point".

**Riesgos + mitigaciones:**
- Riesgo: UI / render divergence after extract (stock emojis/texts, list entry format, stock_alerts out/low sections + "📝 Reabastecer: name[:25]", detail kb 5 rows + labels, wizard "Paso X de 5", confirm resumen with desc None->"Sin descripcion", delete "seguro...", alerts, cb packing, back targets, truncation) → Mit: extraction is pure copy-paste of logic to new def; new helper tests in F4 have exact string/emoji/cb/math asserts (copy from existing handler tests + impact "cover ... for stock emoji 4 cases, ... button texts ... + truncation + packed cb data, ... confirm text with None descs"); re-run full Test* classes in F4; keep all consts/texts in place.
- Riesgo: LOC sigue =50-51 por docstring/boilerplate → Mit: trim docstring del helper (mantener contrato) + comentario "extracted for <=50 LOC rule (Item 8 / arch-enforcer)", precedente item7/25 F3 + item2 F3; usar inspect en gate.
- Riesgo: 1-service residual or direct PackageService left (import or bare in wizard or elsewhere; >1 with in one handler) → Mit: remove the import line; single with per entrypoint; port exactly the 5 desc tests' patches/setup in F4; post-edit grep "PackageService" in handler ==0 + "get_service" count + "with get_service(StoreService)" per entrypoint that needs svc.
- Riesgo: wizard / FSM / flow breakage (states, set_state, update_data, /skip, int validates, select pkg cb, price/stock choice, confirm dispatch, restock unlim/amount, cbs "create_product" / "product_stock_unlimited" / "restock_unlimited" / "confirm_create_product" / "select_pkg_prod_..", state data keys, show_product_confirmation isinstance target) → Mit: 0 changes to states/FSM/validates/state keys/cb strings/calls to show_*/set_state/clear/answer/edit; extract only inside pure build/compute after state or inside the with for data; tests cover full happy + reject + state asserts.
- Riesgo: logging nuevo introduce ruido or format drift → Mit: seguir exactamente el patrón de item7/25 / rules ("módulo | acción | user_id=... | resultado=..."); mismo logger; dentro del with post-success.
- Riesgo: rel / delegate / model prop drift (product.is_low_stock, package for wizard list) → Mit: use existing (model props already on mock in tests; package list via delegate transparent); tests F4 cover with real attrs on mocks.
- Riesgo: internal calls (toggle -> product_admin_detail) or same-module helpers break → Mit: no change to signatures/calls; they are same module, not cross-service.

**Safe point:** Post-ruff + LOC<=50 verificado via inspect on targets + grep 0 PackageService + 1svc Store + new defs + GSD "F3 safe point - long funcs (stock_alerts/list_products/product_admin_detail/handle_delete_product + process_*/confirm_*/show_*) <=50 via pure helpers (compute_stock_emoji_and_text, compute_restock_new_stock, build_*_text_and_buttons, build_product_detail_keyboard, build_product_confirmation...); 1 service only via StoreService get_service (direct PackageService removed from wizard; delegate used); UI render identical; logging compliant". El handler recompila; tests de F4 validarán el contrato observable. Reversible editando solo este archivo (o inlining los helpers + restoring bare pkg if needed, but not).

---

### Fase 4: Port/actualización de tests de store_admin_handlers + agregar tests para helpers puros extraídos

**Objective:** Actualizar/confirmar `test_store_admin_handlers.py` para que los tests reflejen (y protejan) el diseño "exactly 1 service" (StoreService) + delegate for pkgs + pure helpers. Port the 5 TestProcessProductDescription tests (PackageService patch -> get_service(Store) + mock delegate + assert on store mock). Añadir clase `TestStoreAdminPureHelpers` (o equivalente) con unit tests puros para los helpers extraídos (sin parches pesados; import inside per convención; cubrir branches de stock emoji 4 cases + is_low, restock calc incl -1, build kbs con packed cb + truncate + labels + row counts + back targets, build texts con None descs, etc.). Remover cualquier residual 2-svc language. Ruff + full suite del archivo verde (comportamiento idéntico). GSD pre. Safe point.

**DoD checklist:**
- [ ] 0 parches de `PackageService` en el archivo de tests (ni @patch ni referencias directas en setups/asserts para las funciones bajo test; the 5 desc tests ported; other tests in file already clean).
- [ ] Los 5 desc tests ahora usan `@patch("handlers.store_admin_handlers.get_service")` + `mock_get_service.return_value.__enter__.return_value = mock_instance` + `__exit__` asserts en closes (setup like other classes: mock_store.get_available_packages_for_store.return_value = [mock_pkg with id/name/file_count/store_stock]; assert on mock_store.get_available... call; keep exact data/text/state asserts + "No hay paquetes" + advances).
- [ ] Setups for detail/list/alerts etc configure mock_product with `.is_low_stock`, `.stock`, `.is_active`, `.name`, `.price`, `.description` etc so real pure (if used in _build) or model props execute; for wizard desc port: mock_store.get_available... returns list of MagicMock pkgs.
- [ ] Tests de close usan patrón de context (`__exit__` assert) per item7/25 + current file patterns.
- [ ] Docstrings de clases (esp. TestProcessProductDescription + others if touched) actualizadas/confirmadas: "Tests ported to 1-service pattern (get_service(StoreService) only + delegate for packages in wizard) + pure UI helpers (compute_stock_emoji_and_text etc). Arch-enforcer note (long funcs >50L, business logic/UI bloat in handlers, direct other svc in wizard) addressed. Precedent from item7 (reward) + item2/5/6."
- [ ] Nueva clase `TestStoreAdminPureHelpers` (or equiv) at end (después de la última clase; patrón de item7 F5 / item2 F5): tests unitarios puros para los helpers extraídos (al menos 5-8 casos: stock emoji unlimited/out/low/avail + is_low true/false; restock new_stock from -1/0/5 + amounts; build keyboard (len rows, texts exact incl "📝 Reabastecer: ...[:25]", '42' or id in cb via .pack(), back targets); build confirm text (name, desc None->"Sin descripcion", price, stock_text); list entry or stock cases if a builder; import inside test funcs per convención del archivo; no service mocks for the pure helpers themselves).
- [ ] Todos los asserts de texto, llamadas a edit_text/answer, state checks, y parámetros de servicio (user_id, product_id, create_product args incl created_by, get_all(active_only=False), etc.) se mantienen y pasan (comportamiento idéntico).
- [ ] Ruff limpio en el test.
- [ ] GSD pre + gate: la suite completa del archivo pasa verde.
- [ ] Safe point.

**Archivos:** `tests/handlers/test_store_admin_handlers.py`

**Cambios clave (bullets accionables, por clase; copiar al pie de la letra de item7/25 F4 port + item2/5/6 + current test_store_admin patterns + impact port instructions):**
- Pre-log GSD "pre-edit tests/handlers/test_store_admin_handlers.py (F4 port desc wizard 5 tests + add pure helper tests) - refs DoD F4 + copy from item7/25 PLAN F4 (get_service patch, __enter__/__exit__, mock_store setups for delegate, docstrings 'ported to 1-service... Arch-enforcer note addressed', closes to __exit__, NOTES cleaned) + item7/25 F5 Test*PureHelpers class (5+ tests, import inside) + impact 'port the 5 TestProcessProductDescription: change from @patch("...PackageService") + mock_pkg_svc.return_value... to @patch("...get_service") + setup mock_store.get_available_packages_for_store.return_value = [...] ; assert on store mock call (not pkg); keep exact data/text/state asserts'; read pre done (tail of file)".
- En TestProcessProductDescription (and its 4-5 methods): 
  - Change the 4 @patch("handlers.store_admin_handlers.PackageService") to `@patch("handlers.store_admin_handlers.get_service")`
  - Inside: `mock_store = MagicMock(); mock_pkg = MagicMock(); mock_pkg.id=1; mock_pkg.name="Test Pkg"; mock_pkg.file_count=5; mock_pkg.store_stock=-1; mock_store.get_available_packages_for_store.return_value = [mock_pkg]; mock_context = MagicMock(); mock_context.__enter__.return_value = mock_store; mock_get_service.return_value = mock_context`
  - For the no-packages test: `mock_store.get_available_packages_for_store.return_value = []`
  - Asserts: `mock_store.get_available_packages_for_store.assert_called_once()` (instead of pkg_svc.return_value...)
  - Keep all data/text/state asserts + "No hay paquetes" + advances + clear state.
  - Closes: `mock_get_service.return_value.__exit__.assert_called_once()` (add if not already in these methods).
- Añadir al final del archivo (después de la última clase + the EOF ProductWizardStates import; patrón de item7/25 F5 + item2 F5):
  ```python
  class TestStoreAdminPureHelpers:
      """Tests para los helpers puros extraídos de store_admin_handlers (Item 8 / arch-enforcer long-funcs + 1svc)."""

      def test_compute_stock_emoji_and_text_unlimited(self):
          from handlers.store_admin_handlers import compute_stock_emoji_and_text
          emoji, text = compute_stock_emoji_and_text(-1)
          assert emoji == "♾️"
          assert text == "∞"

      def test_compute_stock_emoji_and_text_out_of_stock(self):
          from handlers.store_admin_handlers import compute_stock_emoji_and_text
          emoji, text = compute_stock_emoji_and_text(0)
          assert emoji == "🚨"
          assert text == "AGOTADO"

      def test_compute_stock_emoji_and_text_low_stock(self):
          from handlers.store_admin_handlers import compute_stock_emoji_and_text
          emoji, text = compute_stock_emoji_and_text(3, is_low_stock=True)
          assert emoji == "⚠️"
          assert text == "3"

      def test_compute_stock_emoji_and_text_normal(self):
          from handlers.store_admin_handlers import compute_stock_emoji_and_text
          emoji, text = compute_stock_emoji_and_text(10, is_low_stock=False)
          assert emoji == "📦"
          assert text == "10"

      def test_compute_restock_new_stock_from_unlimited(self):
          from handlers.store_admin_handlers import compute_restock_new_stock
          assert compute_restock_new_stock(-1, 5) == 5

      def test_compute_restock_new_stock_normal(self):
          from handlers.store_admin_handlers import compute_restock_new_stock
          assert compute_restock_new_stock(10, 3) == 13

      def test_build_product_detail_keyboard(self):
          from handlers.store_admin_handlers import build_product_detail_keyboard
          from keyboards.callback_data import ToggleProductCallback, RestockProductCallback, ConfigStockAlertCallback, DeleteProductCallback
          kb = build_product_detail_keyboard(42, is_active=True)
          assert len(kb.inline_keyboard) == 5
          assert "Desactivar" in kb.inline_keyboard[0][0].text
          assert "42" in kb.inline_keyboard[0][0].callback_data  # packed contains id
          assert "Reabastecer" in kb.inline_keyboard[1][0].text
          assert "list_products" in kb.inline_keyboard[4][0].callback_data

      # + casos para build_stock_alerts_text_and_buttons (out/low sections, "📝 Reabastecer: name[:25]", Restock cb, back), build_product_list... (status + stock emoji + price + ProductAdminDetail cb + truncation), build_product_confirmation_text_and_keyboard ( "Resumen del producto", desc None->"Sin descripcion", stock_text, confirm/cancel cbs), etc. Replicate spirit of item7 pure tests + impact "cover ... stock emoji 4 cases, restock calc, button texts/status_emoji + truncation + packed cb data, confirm text with None descs".
  ```
- (Usar import inside test funcs para seguir el patrón del archivo, que hace `from handlers... import ...` dentro de cada test.)
- Post-add: ruff check + format (apply si dirty); full pytest del archivo; grep residual PackageService ==0 (active, unfiltered); asserts de textos/emojis/cbs/params idénticos.

**Tests que deben pasar antes de avanzar:**
- `./venv/bin/python -m pytest tests/handlers/test_store_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="` → todos verdes (comportamiento idéntico: mismos textos, emojis, stock indicators, calls, alerts, state, params on store only, __exit__; new pure tests cover the extracted + edges).
- Ruff en el test file.
- Grep: `grep -n "PackageService" tests/handlers/test_store_admin_handlers.py | grep -v "NOTE\|arch-enforcer\|pre-existing"` → preferiblemente 0; get_service patches + new helper tests presentes; the 5 desc now use get_service(Store).

**Riesgos + mitigaciones:**
- Riesgo: tests que confiaban en mocks de PackageService ahora ejecutan la real (via delegate) y fallan por attrs faltantes en mock_pkg → Mit: configurar explícitamente `.id`, `.name`, `.file_count`, `.store_stock` en cada setup for the desc port (ya hecho en tree for other mocks; impact specifies the attrs); 5-10 min por test pero precedentes existen (item7/25 port + item2).
- Riesgo: el test "no packages" falla porque MagicMock or delegate returns truthy → Mit: setear explícitamente `mock_store.get_available_packages_for_store.return_value = []` (documentado en impact + current test already does for pkg_svc).
- Riesgo: nuevos helper tests fallan por nombre/firma → Mit: nombres confirmados en F3 GSD1 + sección 4 del PLAN; ajustar en F4 primer GSD si difiere (mantener espíritu); use the pure from svc if imported in handler (import inside test the same name).
- Bajo: import inside + late from after patch → si choca, seguir exactamente el patrón del archivo (late import after the @patch in the test func).

**Safe point:** Suite de store_admin_handlers verde post-F4 (incl nuevos helper tests + ports) + ruff + GSD "F4 safe point - store admin handler tests confirmed ported to 1-service (StoreService) + delegate for pkgs in wizard + pure helpers; 5 desc tests now patch get_service(Store) + assert on delegate; new TestStoreAdminPureHelpers added + pass (stock 4 cases + restock + kbs + texts); arch-enforcer notes (long funcs >50L, biz/UI bloat, direct PackageService) addressed; behavior identical". Confirma que el render de list/alerts/detail/wizard/confirm/delete (y helpers) es idéntico. Reversible restaurando setups viejos (pero no necesario).

---

### Fase 5: Re-runs de golds + verificación final de reglas + self-check + handoff (segundo de nuevo pool de 4; batch anterior cerrado)

**Objective:** Re-ejecutar los golds que protegen el flujo de store admin (handler test full + cross flows store/product + package get_available gold que el delegate ejercita indirectamente). Verificar reglas (1 service Store via get_service, LOC<=50 via inspect, logging, pure helpers, 0 PackageService active en handler, delegate/pure in svc with comments). Completar GSD log con self-check PASSED explícito + lista de "tests críticos a re-correr en futuro". Confirmar en self-check/PLAN/output: "este es el segundo de un nuevo pool de 4, y que el batch anterior de 4 quedó cerrado con tests pasando" (citar 24-SUMMARY "BATCH: 4 items completed in this tirón (Item 6 final of max 4)" + "Item 6/24 closed..." + 25 self-check PASSED + "Item 7/25 closed. First of new pool..."). Handoff a arch-enforcer/test-guardian + gsd-executor del siguiente item del pool. Safe point final.

**DoD checklist:**
- [ ] Re-runs: full `pytest tests/handlers/test_store_admin_handlers.py ...` green; targeted cross `pytest -k "store or product or TestStoreAdmin or admin_store or TestStore or get_available_packages_for_store" -q --tb=line -p no:cov --override-ini="addopts="` (o más amplio filtrado; documentar pre-exist unrelated); package gold `pytest tests/unit/test_package_service.py ... -k "available_packages_for_store"`; bot smoke `python -c "import bot; print('bot import + routers (incl store_admin) ok')" ` or equivalent `python -c "from handlers.store_admin_handlers import *; print('imports ok')"`.
- [ ] Ruff limpio en los 3 archivos tocados.
- [ ] Verificación de reglas (grep/inspect manual + en log):
  - `grep -n "PackageService" handlers/store_admin_handlers.py` → 0 (active).
  - `python -c 'import inspect; from handlers.store_admin_handlers import stock_alerts, list_products, product_admin_detail, handle_delete_product, process_product_description, process_restock_amount, confirm_create_product, ...; for name, fn in [...]: print(name, "LOC:", len(inspect.getsourcelines(fn)[0]))'` → all <=50.
  - Logging formato "store_admin_handlers | ..." presente en las rutas principales (spot o grep inside withs).
  - get_service(StoreService) + with + delegate for pkgs in wizard + puros (compute_stock... etc) usados + tests added; 1 service rule + <=50 + logging + pure helpers + no biz logic en handler.
  - Delegate + pure in svc with arch comments + "item8" / "arch-enforcer" notes.
- [ ] GSD entries completas para F5 + log final con self-check PASSED + estructura completa (lista de fases/DoD/gates/archivos modificados/tests que pasaron/reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0 behavior chg in CRUD/delivery/gamif credit, 1svc Store via get_service + delegate for pkgs, LOC<=50 via inspect, logging, pure helpers tests, no prod chg)/desviaciones/tests críticos para futuro (store admin handler test full, package get_available gold, cross -k store|product|TestStoreAdmin|admin_store, bot smoke, ruff+greps+LOC verifiers)/"Item 8/26 closed. Second of new pool of 4. Previous batch of 4 (ending with Item 7/25 reward-handlers-1service-loc + Item 6/24 remaining-besito-compositions) closed with tests passing per 24-SUMMARY BATCH note + 25 self-check PASSED. Ready for arch-enforcer re-scan (enfocado en store_admin_handlers: exactly 1 service + <=50L + no direct PackageService + pure helpers for stock/UI/wizards) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4").
- [ ] Self-check explícito "Self-Check: PASSED".
- [ ] (Opcional pero recomendado) SUMMARY.md en el dir de la phase con executive + refs al log + comandos de re-verif (sigue estructura de 25/24/23/20).
- [ ] Safe point final + criterio de éxito del plan.

**Archivos:** Ninguno nuevo (solo log + opcional SUMMARY; los edits ya hechos en F2-F4).

**Cambios clave:** Solo ejecución de comandos (ver Instrucciones) + echo al log. Usar run_terminal para los gates finales + conteos + greps + self-check append.

**Tests gates (obligatorios):**
- Los re-runs targeted + full handler test + package gold.
- Ruff global en los 3.
- Greps + inspect LOC + smoke bot/handler imports.
- GSD pre cada + "F5 FINAL + self-check PASSED + BATCH/POOL note" + explicit "segundo del nuevo pool de 4" + "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

**Riesgos + mitigaciones:**
- Riesgo: re-runs muestran flakes preexistentes (no causados por este Item) → Mit: usar -p no:cov --override-ini; documentar si hay 1 unrelated fail (precedente 25/24/23/22/20/19 "do not count as regression"); enfocar "0 regressions atribuibles a los helpers, ports, o delegate".
- Riesgo de tiempo: chains de integración lentas → Mit: priorizar targeted del handler test primero, luego -k específicos de store/product + package get_available; el PLAN permite targeted combinados.
- Ninguno nuevo (verif final; scope tight).

**Safe point final + criterio de éxito:** Todos DoD de F5 + self-check PASSED en log con la nota explícita de "segundo de nuevo pool de 4" + "batch anterior de 4 cerrado con tests pasando per 24/25". El plan completo + log GSD son evidencia para el siguiente agente (gsd-executor next item o arch-enforcer/test-guardian). 0 breakage; UI idéntica; reglas cumplidas; 3 sistemas críticos (gamif read-only stats, narrative, channel/VIP) protegidos (0 side effects; re-runs protect).

---

## 3. Estrategia de tests general (port + nuevos + re-runs)

**Confirmación de ports en test_store_admin_handlers (F4):**
- Seguir exactamente el patrón de `tests/handlers/test_store_admin_handlers.py` itself (most classes already use @patch("handlers.store_admin_handlers.get_service") + mock_context __enter__ + __exit__ asserts + late import after patch + make_* fixtures + exact text asserts on edit_text/answer + state checks) + item7/25 F4 port (RewardType -> here the pkg attrs for delegate mock; get_service patch, mock_instance + __enter__, mock_store.get_available... = [mock_pkg], closes to __exit__, calls asserts on store only, docstrings "ported to 1-service... Arch-enforcer note addressed", NOTES cleaned).
- Configurar los mocks de product/pkg con los atributos que la pure / display / builder necesita (stock, is_low_stock, is_active, name, price, description, file_count, store_stock). Usar `mock_store.get_available_packages_for_store.return_value = [...]` para el acceso via delegate en los desc tests.
- Actualizar/confirmar docstrings de las clases afectadas (esp. TestProcessProductDescription) a "Tests ported to 1-service pattern (get_service(StoreService) only + delegate for packages in wizard) + pure UI helpers (compute_stock_emoji_and_text etc). Arch-enforcer note (long funcs >50L, business logic/UI bloat in handlers, direct other svc in wizard) addressed. Precedent from item7 (reward) + item2/5/6." (ya presentes en otras clases; refresh si residual 2-svc language).
- El "patched_detail hack" in toggle test stays as-is (internal same-module call mock; not related to service).

**Nuevos tests para pure helpers extraídos (F4):**
- Ubicación: `tests/handlers/test_store_admin_handlers.py` (mismo archivo; mantiene todo co-localizado y evita nuevos archivos per scope tight + precedent item7/25 F5 / item2 F5).
- Enfoque: unit tests puros del helper (datos de entrada falsos con MagicMock mínimos o simples objetos o ints/bools; no service mocks necesarios para los helpers mismos; import inside test funcs per convención del archivo).
- Casos mínimos (copiar espíritu de Test*PureHelpers en item7/25 F5 + impact "cover stock emoji 4 cases (unlimited/out/low/avail + is_low), restock calc (from -1/0/5 + amounts), build kbs (button texts exact incl [:25] truncate, callback_data packed via .pack() match, row counts, back targets), build texts (confirm resumen w/ desc None->'Sin descripcion', stock_text), list entry or stock cases if a builder touches"):
  - compute_stock_emoji_and_text(-1) → ("♾️", "∞")
  - compute_stock_emoji_and_text(0) → ("🚨", "AGOTADO")
  - compute_stock_emoji_and_text(3, is_low_stock=True) → ("⚠️", "3")
  - compute_stock_emoji_and_text(10, False) → ("📦", "10")
  - compute_restock_new_stock(-1, 5) → 5 ; compute_restock_new_stock(10, 3) → 13
  - build_product_detail_keyboard(42, True) → 5 rows, "Desactivar", "Reabastecer", "Configurar alerta", "Eliminar", "Volver", cbs contain "42" or packed id, back "list_products"
  - (si extract build_stock_alerts...) out/low sections contain "🚨 Productos agotados", "⚠️ Stock bajo", "📝 Reabastecer: name[:25]", Restock cb packed, back "admin_store"
  - build_product_confirmation... (or show_) → "Resumen del producto", name, "Sin descripcion" for None, price, stock_text "Ilimitado" or num, cbs "confirm_create_product" / "admin_store"
- Estos tests sirven como "test-guardian" para los helpers: cualquier refactor futuro del render de list/alerts/detail/wizard/confirm debe pasar estos.

**Re-runs de golds (F5, y spot en F1/F3/F4):**
- Handler level: `pytest tests/handlers/test_store_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="`
- Cross / store-product flows (gold paths que ejercitan admin product + wizard + list/detail + alerts + stats): `pytest -k "store or product or TestStoreAdmin or admin_store or TestStore or stock_alerts or list_products or create_product or restock" -q --tb=line -p no:cov --override-ini="addopts="` (filtrar; documentar pre-exist unrelated como daily concurrent o alembic per precedent 25/24/23).
- Package gold (exercises the real get_available... that the delegate calls; delegate transparent): `pytest tests/unit/test_package_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "available_packages_for_store"`
- Objetivo: confirmar que el código de render (ahora delegando a helpers puros) produce los mismos textos, emojis, botones, alerts, stock indicators, wizard steps, y que los calls a servicio siguen siendo solo StoreService via get_service (delegate for pkgs in one wizard step).
- (Nota: los tests de integración actuales pueden no asertar el contenido exacto del UI de admin store directamente; para "idéntico" el executor usa los asserts existentes del handler test + nuevos helper tests que pin strings/emojis/cbs/math; re-runs de chains protegen indirectamente via product/package paths + bot smoke.)

**Gates generales por fase / final:**
- Ruff: `./venv/bin/python -m ruff check <file> --fix` ; luego `./venv/bin/python -m ruff format --check <file>` (o apply en pre si se sigue el precedente de ruff pre-edit + hygiene como chore separado 0 logic).
- Pytest targeted limpio (sin cov para exit code estable): siempre con `-p no:cov --override-ini="addopts="` (precedente establecido en todos los golds 20/21/23/24/25 + item logs).
- Grep de reglas: 0 "PackageService" (activo) en store_admin_handlers.py; LOC de long funcs <=50 via inspect; imports de get_service(Store) + delegate/pure presentes; logging formato presente (spot); helpers puros usados + tests.
- (Opcional para executor) smoke de bot import o registro de routers si se quiere (`python -c "import bot; print('ok')" ` o `python -c "from handlers.store_admin_handlers import *; print('ok')"` o equivalent para store_admin router), pero mínimo es el handler test + cross targeted + package get_available gold.
- Cobertura de logging requirement: los tests no asertan logs usualmente (salvo en middleware tests); el gate es manual grep o inspección durante las ediciones + inclusión en el log de GSD.

---

## 4. Decisiones de diseño que el executor debe confirmar (o registrar desviación en el primer GSD entry de la fase relevante)

1. **Nombres de los helpers puros extraídos:** `compute_stock_emoji_and_text(stock: int, is_low_stock: bool = False) -> tuple[str, str]` (exact per impact + verb+context+result conv; cf. `compute_reward_status_text` / `calculate_emoji_counts_from_reactions` in item7/25/item2 / `calculate_user_besitos_from_reactions` in codebase). `compute_restock_new_stock(current_stock: int, amount: int) -> int`. `build_stock_alerts_text_and_buttons(...)`, `build_product_admin_list_text_and_buttons(...)` or split `build_product_list_entry` + `build_product_button`, `build_product_detail_keyboard(product_id: int, is_active: bool) -> InlineKeyboardMarkup`, `build_product_confirmation_text_and_keyboard(data: dict) -> tuple[str, InlineKeyboardMarkup]` (or close equivalents; keep minimal per tight). Confirmar o elegir alternativa equivalente en primer GSD de F3; documentar. Si se extrae un tercero/cuarto para wizard steps o list entry, nombre similar y cubrir en tests.
2. **Delegate backward-compatible / thin para get_available_packages_for_store:** Added as instance method on StoreService (passthrough to self.package_service); exact docstring + "Added for item8..." comment per impact. 1-2 lines; no core CRUD. If pure emoji also gets 1-line instance delegate (per item7 pattern), add with "Backward-compatible delegate added for Item 8 (arch-enforcer 1-service rule for store_admin handlers)." + arch comment.
3. **Logging en los handlers editados:** Agregar/confirmar logs en formato "módulo | acción | user_id=... | resultado=..." para acciones clave (list_products with count, confirm_create_product with product_id+name, stock_alerts, restock success, delete, etc.) dentro de los with post-success. Si los handlers actualmente delegan logging a middleware, mínimo es asegurar el log existente o añadir uno estándar. Confirmar formato con ejemplos de item7/25 F2/F3 + rules.
4. **Patrón de tests para pure helpers + delegate:** Ejecutar la real `compute_stock_emoji_and_text` (imported or local) en tests puros con ints/bools (preferred for "pure" semantics + simplicity; like item7 real get_reward_emoji via .reward_type attrs). Para los nuevos builders de kb/text: pure unit tests (import inside, MagicMock minimal or simple objs or dicts for data; no service mocks for the helpers themselves; no @patch on the helper in handler tests (the handler test covers full flow via real)). Para el port de desc: mock_store.get_available_packages_for_store.return_value = [mock_pkg with .id/.name/.file_count/.store_stock]; assert on the store mock call (not pkg). Follow item7/25 F4/F5 + impact port instructions exactly.
5. **Chequeo de delegate / pkgs en wizard:** En process_product_description: usar `store_service.get_available_packages_for_store()` (via delegate) dentro de su with get_service(Store); mantener `if not packages:` error+clear+return + loop build buttons (or slim to pure builder) + set selecting. No agregar chequeos de is_active en el handler para pkgs (scope tight; list ya filtra en service if needed). Tests F4 cubren empty pkgs path.
6. **Conteo estricto de <=50 LOC:** Usar `inspect.getsourcelines(func)[0]` (cuenta líneas de la def inclusive) o equivalente `sed -n 'X,Yp' | wc -l`. Si queda en 51 por docstring, aplicar trim de docstring del helper (mantener contrato) + comentario de "extracted for <=50 LOC rule (Item 8 / arch-enforcer)", precedente de item7/25 F3 + item2 F3 + credit_besitos/handle_reaction. No dejar >50. Verificar post-F3 y en F5 final. Targets: stock_alerts, list_products, product_admin_detail, handle_delete_product, process_restock_amount, confirm_create_product, process_product_description, admin_store_menu, restock_product, show_product_confirmation (y cualquier otro que roce).
7. **Actualización de docstrings de tests de store admin:** Confirmar/refresh las notas de "1-service (StoreService) + delegate for pkgs in wizard" y "Arch-enforcer note addressed" (long funcs, biz/UI bloat, direct PackageService) para la clase TestProcessProductDescription + cualquier otra tocada; las otras clases ya tienen patrones "ported...". Dejar comentario histórico breve si se desea ("pre-Item 8 this wizard step used direct PackageService; now 1-service Store via delegate per arch-enforcer remediation").
8. **Log file para GSD de Item 8:** Usar `.planning/quick/gsd-store-admin-long-funcs.log` (cross-ref gsd-impact-analyzer-item8-store-admin-long-funcs.log del analyzer). Cada pre-edit/pre-gate/pre-verif debe hacer `echo "=== $(date -Iseconds) | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie de la letra de item7/25 PLAN F4 + gsd-reward-handlers-1service-loc.log + item8 impact + 24/25 SUMMARY BATCH + current source lines>" >> <logfile>"` (o usar run_terminal_command con comando echo/printf). Al final del Item, el log debe tener entradas para cada acción significativa (como los 40+ de item7, 46+ de item2) + self-check PASSED + BATCH/POOL note + "segundo del nuevo pool de 4".
9. **Si se necesita un segundo (o tercer) helper para render en store admin:** Solo si el conteo de LOC de una long func no baja suficiente con los principales (stock emoji + 1 calc + 1-2 builds). El helper de button text o list entry (si se extrae) puede ser puro. Si no se extrae más, documentar por qué el LOC ya cumplía post los principales (tight scope prioriza mínimo).
10. **No exportar la pura o delegate en services/__init__.py:** Confirmado por scope (import directo del módulo es suficiente y usado en el codebase + item7/25; no editar __init__).
11. **Uso de model props vs pure:** Preferir product.is_low_stock / stock_status / stock_display (ya existen en StoreProduct per impact/models read) para reducir dupe en list/detail/alerts; usar el pure compute_stock_emoji_and_text solo para el mapping a emojis ♾️🚨⚠️📦 + display text específico de admin UI (model status es str diferente). No sincronizar más (out of scope per impact "low" risk note).
12. **Cualquier decisión que difiera:** Registrar en el GSD log + (si se permite fuera de scope estricto) en una nota breve al final del PLAN o en SUMMARY posterior. Elegir conservadoramente siguiendo precedentes (item7/25 ports + helper extract + LOC inspect + self-check, item2/5/6 pure + delegate comment, impact exact code blocks for delegate/pure + port desc, 24/25 BATCH/POOL language, get_service context + __enter__/__exit__ mocks, real pure via attrs, docstrings "ported...", 1-line/min support + delegate comment, inspect LOC, UI 1:1).

Cualquier decisión que difiera de lo anterior debe registrarse en el GSD log + nota breve al final del PLAN o en SUMMARY.

---

## 5. Criterios de verificación + gates finales + lista de comandos

**Criterios de éxito del Item (medibles, para self-check del executor):**
- Los handlers de store admin (todos los entrypoints cb + message FSM: admin_store_menu, stock_alerts, restock_*, process_restock_*, create_product_start, process_product_name/description/price/stock, product_stock_*, show_product_confirmation, confirm_create_product, list_products, product_admin_detail, config_stock_alert, process_stock_threshold, toggle_product, handle_delete_product, store_stats) no contienen ninguna referencia activa a PackageService (import o uso) — grep ==0 (active).
- Usan exclusivamente `get_service(StoreService)` vía context manager (with) + delegate `store_service.get_available_packages_for_store()` para el wizard pkg select step; exactamente 1 service por entrypoint.
- Todas las long funcs (stock_alerts, list_products, product_admin_detail, handle_delete_product, process_restock_amount, confirm_create_product, process_product_description, admin_store_menu, restock_product, show_product_confirmation, etc.) + helpers relevantes <=50 LOC fuente (inspect <=50; prefer <50); helpers puros extraídos (compute_stock_emoji_and_text, compute_restock_new_stock, build_*_text_and_buttons / build_product_detail_keyboard / build_product_confirmation... o equivalentes verb+context+result) y usados para el render/stock/UI/wizard.
- Todos los tests en `test_store_admin_handlers.py` pasan post-F4 (con get_service, delegate mock for pkgs, rel/model attrs if used, __exit__, nuevos helper tests; textos/emojis/cbs/stock indicators/alerts/params/state idénticos).
- Re-runs de golds (handler test + cross store/product flows + package get_available gold) pasan sin regressions atribuibles a la extracción, ports, o delegate.
- Ruff clean en los 3 archivos modificados.
- Verificaciones de reglas:
  - `grep -c "PackageService" handlers/store_admin_handlers.py` (activo) == 0
  - LOC de las long funcs <=50 via inspect
  - Logging formato "store_admin_handlers | <action> | user_id=... | ..." presente en las rutas principales (dentro de withs post-success)
  - 1 service (Store via get_service + delegate for pkgs) + pure helpers + get_service context + no biz logic en handler
  - Delegate + pure in svc with "item8" / "arch-enforcer" / "Added for item8" comments
  - GSD pre every (counts 5-10+/fase target; wc tracked)
- GSD log completo con pre-entries + self-check "PASSED" + lista explícita de "tests críticos a re-correr en el futuro para estos handlers/helpers" (el handler test full; package get_available_packages_for_store gold; cross -k store|product|TestStoreAdmin|admin_store; bot smoke; ruff + greps + LOC verifiers) + nota "Item 8/26 closed. Second of new pool of 4. Previous batch of 4 (ending with Item 7/25 reward-handlers-1service-loc + Item 6/24 remaining-besito-compositions) closed with tests passing per 24-SUMMARY BATCH note + 25 self-check PASSED. Ready for arch-enforcer re-scan (enfocado en store_admin_handlers: exactly 1 service + <=50L + no direct PackageService + pure helpers for stock/UI/wizards) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4".
- Comportamiento de usuario final idéntico (list/alerts/detail/wizard/confirm/delete muestran mismos emojis/stock indicators/textos/botones/alertas/navegación/FSM steps; helpers no cambian el contrato observable; stock values -1/0/positive, creates, updates, deletes, restocks, thresholds sin cambio).
- Safe point final documentado; item listo para guardians + siguiente del pool.

**Gates por fase (ver secciones de fases para detalles; siempre GSD pre antes):**
- Pre-edit / pre-gate / pre-verif / pre-ruff / pre-pytest / pre-grep / pre-smoke / pre-final: append al log.
- Post-edit: ruff + targeted pytest (cuando aplique) + smoke + grep/LOC checks + GSD entry de resultado.
- Avanzar solo si gate verde (o documentar desviación menor en log).
- F5: re-runs obligatorios de golds + broader smoke filtrado + package gold + self-check + BATCH/POOL note + explicit "segundo del nuevo pool de 4" + "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

**Comandos concretos sugeridos (copiar al pie de la letra en ejecución; usar run_terminal_command):**
```
# GSD (siempre pre)
echo "=== $(date -Iseconds) | PHASE N | GSD pre-... <file> (<motivo>) - <desc + refs DoD + patrones copiados al pie de la letra de item7/25 PLAN F4 + gsd-reward-handlers-1service-loc.log + item8 impact report (delegate/pure exact blocks + port desc instructions) + 24/25 SUMMARY BATCH + current source lines>" >> .planning/quick/gsd-store-admin-long-funcs.log
wc -l .planning/quick/gsd-store-admin-long-funcs.log

# Ruff (con --fix si hygiene)
./venv/bin/python -m ruff check handlers/store_admin_handlers.py services/store_service.py tests/handlers/test_store_admin_handlers.py --fix
./venv/bin/python -m ruff format --check handlers/store_admin_handlers.py services/store_service.py tests/handlers/test_store_admin_handlers.py

# Pytest targeted (siempre con estos flags para exit limpio; precedente todos los golds)
./venv/bin/python -m pytest tests/handlers/test_store_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -m pytest -k "store or product or TestStoreAdmin or admin_store or TestStore or stock_alerts or list_products or create_product or restock" -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -m pytest tests/unit/test_package_service.py -q --tb=line -p no:cov --override-ini="addopts=" -k "available_packages_for_store"

# Grep rules + 1svc + 0 PackageService
grep -n "PackageService" handlers/store_admin_handlers.py
grep -n "get_service(StoreService)\|from services import get_service\|from services.store_service import StoreService" handlers/store_admin_handlers.py
grep -n "compute_stock_emoji_and_text\|build_product_detail_keyboard\|build_stock_alerts\|build_product_admin_list\|build_product_confirmation" handlers/store_admin_handlers.py
grep -n "def get_available_packages_for_store\|def compute_stock_emoji_and_text" services/store_service.py

# LOC (inspect gold)
./venv/bin/python -c '
import inspect
from handlers.store_admin_handlers import stock_alerts, list_products, product_admin_detail, handle_delete_product, process_product_description, process_restock_amount, confirm_create_product, admin_store_menu, restock_product, show_product_confirmation
for name, fn in [("stock_alerts", stock_alerts), ("list_products", list_products), ("product_admin_detail", product_admin_detail), ("handle_delete_product", handle_delete_product), ("process_product_description", process_product_description), ("process_restock_amount", process_restock_amount), ("confirm_create_product", confirm_create_product), ("admin_store_menu", admin_store_menu), ("restock_product", restock_product), ("show_product_confirmation", show_product_confirmation)]:
    src = inspect.getsourcelines(fn)[0]
    print(f"{name} LOC: {len(src)}")
'

# Smoke import + pure + helpers + delegate
./venv/bin/python -c "
from handlers.store_admin_handlers import stock_alerts, list_products, product_admin_detail, handle_delete_product, process_product_description, compute_stock_emoji_and_text, build_product_detail_keyboard
from services.store_service import StoreService, compute_stock_emoji_and_text
print('imports + helpers ok')
from unittest.mock import MagicMock
from models.models import Package
print(compute_stock_emoji_and_text(-1))
print(compute_stock_emoji_and_text(0))
print(compute_stock_emoji_and_text(3, is_low_stock=True))
print(compute_stock_emoji_and_text(10))
print('pure ok')
svc = StoreService()
print('svc instance ok (delegate will be called via handler in tests)')
"

# Bot smoke (router registration)
./venv/bin/python -c "
import bot
print('bot import + routers (incl store_admin) ok')
"

# Combined critical re-run (F5)
./venv/bin/python -m pytest -k "store or product or TestStoreAdmin or admin_store or TestStore or stock_alerts or list_products or create_product or restock or get_available_packages_for_store" -q --tb=line -p no:cov --override-ini="addopts="
```

---

## Instrucciones para el gsd-executor

Este PLAN.md ES tu prompt de ejecución. Síguelo al pie de la letra, sin scope creep. El trabajo es para UNA persona (tú) + disciplina GSD total. El flujo debe continuar automáticamente con gsd-executor para este item (y luego los siguientes 2 del pool de 4). 

**CONFIRMACIÓN OBLIGATORIA (incluir en tu output final y en el self-check del log):** Este es el segundo de un nuevo pool de 4 (Item 8 / 26-store-admin-long-funcs, post item7 reward 1svc+LOC). El batch anterior de 4 quedó cerrado con tests pasando: ver .planning/phases/24-remaining-besito-compositions/24-remaining-besito-compositions-SUMMARY.md ("**BATCH:** 4 items completed in this tirón (Item 6 final of max 4). ... Item 6/24 closed. BATCH: 4 items completed in this tirón (final of max 4). **Status:** COMPLETE - Self-Check: PASSED") + su gsd-remaining-besito-compositions.log (self-check PASSED + BATCH COMPLETE NOTE al final) + .planning/phases/25-reward-handlers-1service-loc/SUMMARY.md ("Item 7/25 closed. First of new pool of 4. Previous batch of 4 ... closed with tests passing per 24-SUMMARY BATCH note + self-check PASSED") + su gsd-reward-handlers-1service-loc.log (self-check PASSED + POOL note) + re-runs verdes en F5 de esos items. "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

1. **GSD discipline (non-negotiable, como en todas las phases exitosas 20/21/23/24/25 + item2/5/6/7 logs):**
   - ANTES de **cualquier** modificación (search_replace/write/edit en fuentes o log o SUMMARY), antes de ruff, pytest, grep de verif, smoke, o resumen: append al log.
   - Log: `.planning/quick/gsd-store-admin-long-funcs.log` (cross-ref gsd-impact-analyzer-item8-store-admin-long-funcs.log del analyzer si útil).
   - Crea/append al archivo si necesario (planner ya hizo INIT + pre-mkdir + pre-write con 3 entries; wc tracked; primer entry de executor puede confirmar + wc).
   - Formato de entry (copia estilo **al pie de la letra** de gsd-reward-handlers-1service-loc.log / gsd-reward-gamif-item2.log / gsd-remaining-besito-compositions.log / gsd-reward-besito-eventbus.log / gsd-getservice-unification.log):
     ```
     === 2026-06-08Txx:xx:xx+00:00 | PHASE 3 | GSD pre-edit handlers/store_admin_handlers.py (F3 remove direct PackageService + extract pure helpers + ensure 1svc Store) - Agregar compute_stock_emoji_and_text + compute_restock_new_stock + build_stock_alerts_text_and_buttons + build_product_detail_keyboard + build_product_confirmation_text_and_keyboard (puros, verb+context+result); slim stock_alerts/list_products/product_admin_detail/handle_delete_product/process_* etc de >50L a <=50; remover import + bare PackageService() en process_product_description; usar store_service.get_available_packages_for_store() via delegate dentro de with get_service(StoreService); refs DoD F3 + copy snippets from item7/25 PLAN F2/F3 (with+log+rel/pure helper insert + body replace + inspect LOC) + item8 impact report (exact delegate/pure code blocks + port desc instructions + long funcs list) + current handler lines ~92-152 (stock_alerts), ~512-567 (list), ~570-625 (detail), ~728-784 (delete), ~300-342 (desc wizard bare pkg), ~211-252 (restock amount), ~466-507 (confirm), ~431-463 (show confirm), ~49-90 (menu), ~155-187 (restock); read pre done; patrones de item7/25 + item2/5/6 + impact.
     ```
     Luego ejecuta el comando de edit/tool.
   - También pre-gate (pre-pytest, pre-ruff, pre-grep "PackageService|get_service", pre-inspect LOC, pre-final-self-check, pre-SUMMARY si produces).
   - Cuenta las entradas; apunta a varias por fase (5-10+ totales por fase como precedentes item7 40+, item2 46+, 24 55+). Al final del Item el log debe tener el self-check completo + BATCH/POOL note + "segundo del nuevo pool de 4".
   - Usa `run_terminal_command` con `echo "=== $(date -Iseconds) | PHASE N | ..." >> .planning/quick/gsd-store-admin-long-funcs.log` (o printf). Nunca edites sin pre-log. wc -l después de appends clave.

2. **Orden estricto:** Ejecuta Fase 1 → gates → Fase 2 → gates → Fase 3 → gates → Fase 4 → gates → Fase 5 (re-runs + verif final + self-check + POOL/BATCH confirm). **No saltes fases ni hagas "todo de una".** Marca DoD mentalmente o en el log al completar cada checklist. Al final de cada fase documenta "F<N> safe point" + "F<N> COMPLETE" en log (como item7/25 / item2 log).

3. **Herramientas y comandos concretos (usa run_terminal_command para estos; copia los de sección 5 + precedents):**
   - GSD logs + wc: `echo "..." >> log; wc -l log`
   - Mkdir (si planner no lo hizo completamente): `mkdir -p .planning/phases/26-store-admin-long-funcs`
   - Ruff: `./venv/bin/python -m ruff check <file> --fix` ; `./venv/bin/python -m ruff format --check <file>` (apply si "would reformat" como chore 0 logic per precedent 25/24/23).
   - Pytest targeted (siempre con estos flags para exit limpio): `./venv/bin/python -m pytest <path or -k "expr"> -q --tb=line -p no:cov --override-ini="addopts="`
     - Ejemplos exactos en sección 5 arriba + item7/25 F4/F5 / 24 F5 / item2.
   - Grep de reglas: `grep -n "PackageService" handlers/store_admin_handlers.py` (0 active); `grep -n "get_service(StoreService)\|from services import get_service\|from services.store_service import StoreService" ...`; `grep -n "compute_stock_emoji_and_text\|build_product_detail_keyboard\|..." ...`; `grep -n "def get_available_packages_for_store\|def compute_stock_emoji_and_text" services/store_service.py`
   - LOC (siempre inspect): `./venv/bin/python -c 'import inspect; from handlers.store_admin_handlers import stock_alerts, list_products, ...; for name, fn in [...]: src=inspect.getsourcelines(fn)[0]; print(name, "LOC:", len(src))'`
   - Smokes: `./venv/bin/python -c "from handlers... import ...; from services.store_service import StoreService, compute_stock_emoji_and_text; ..."` (4 branches pure + delegate pkgs + helpers); bot `python -c "import bot; print('ok')"` or `python -c "from handlers.store_admin_handlers import *; print('ok')"`
   - Evita sleeps; usa comandos directos. Si tool soporta background para integ lentas, úsalo pero log secuencial prefer.
   - Al final: re-ejecuta los combinados + broader smoke filtrado por store/product + package get_available gold + self-check en log + (opt) write de SUMMARY.

4. **Patrones a copiar (no reinventar; **al pie de la letra** de golds):**
   - Patrón get_service + with + mock en tests + closes __exit__: copia de `tests/handlers/test_store_admin_handlers.py` itself (most classes) + item7/25 F4 port (get_service patch, mock_instance + __enter__, mock_store setups for delegate get_available...= , closes to __exit__, calls asserts on store only, docstrings "ported to 1-service... Arch-enforcer note addressed", NOTES cleaned) + mission_user_handlers.py + its test.
   - Extracción de helper puro para LOC + UI idéntica: copia espíritu + snippets de F3 de item7/25 (insert pure compute_... near section; replace inline with call; docstring "Construye... Función pura."; inspect LOC post; test refresh path green; 1-3 helpers por long flow if suficiente; trim docstring si 51 por boilerplate + comentario "extracted for LOC rule (Item X / arch-enforcer)").
   - 1-line / min support + delegate comment: de item7/25 F1/F2 + item2 F1 (pura + delegate 1-line + "Backward-compatible delegate added for Item X (arch-enforcer...)"; thin delegate for cross-in-domain with "Added for item8: enables ... exactly 1 service (StoreService)..." exact per impact).
   - Logging: "módulo | acción | user_id=... | resultado=..." (copiar de item7/25 F2 logs + F3 for handle_reaction + rules).
   - GSD entries detalladas: "pre-xxx <file> (F<N> <motivo>) - <desc + refs DoD + patrones copiados al pie de la letra de item7/25 PLAN F4 + gsd-reward-handlers-1service-loc.log + item8 impact report (exact delegate/pure blocks + port desc + long funcs list) + 24/25 SUMMARY BATCH>"; wc; style de item7 (40+), item2 (46+), 24 (55+).
   - Safe points + self-check al final del log: estructura de item7/25 (lista fases/DoD/gates/archivos/tests que pasaron/reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0, 1svc Store + delegate for pkgs, LOC<=50 via inspect, logging, pure helpers tests, no prod chg)/desviaciones/tests críticos/"Item closed. Ready for ... + arch-enforcer + test-guardian + siguiente item del pool") + 24/25 BATCH/POOL note + explicit "segundo del nuevo pool de 4" + "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."
   - Precedentes PLAN/GSD + handoff + pool/batch: .planning/phases/25-reward-handlers-1service-loc/PLAN.md + its gsd log (Item7 first-of-new-pool 1svc+LOC gold), 20-reward-gamif PLAN + gsd-reward-gamif-item2.log (Item2 reward 1svc gold + delegate + pure + ports + helper tests + LOC + self-check), 23/24 PLANs + SUMMARYs (BATCH "4 items completed in this tirón (Item 6 final of max 4)", "Item 6/24 closed. BATCH...", self-check), item8 impact report .md (source of truth for scope/map/risks/tests/"second of new pool of 4" + exact code blocks for delegate/pure + port desc instructions + "Pool anterior de 4 cerrado...").
   - VOZ/estilo: handlers hablan vía textos ya existentes (Lucien voice preservado idéntico); no cambiar mensajes de usuario.
   - 3 sistemas críticos: siempre en mente (gamif/missions/rewards como dominio principal en mente de hardening; narrativa cross via events; channel/VIP; este item es admin product mgmt + read stats "besitos gastados" aggregate only; 0 tx/credit/deliver/claim; re-runs de cross protegen).
   - Commands: exact from PLAN sec5 + "Instrucciones" ( -p no:cov --override-ini="addopts=", ./venv/bin/python -m for ruff/pytest, python -c for smokes with venv fallback, greps for rules/1svc/0-PackageService, python -c for LOC inspect, bot smoke, combined critical re-run in F5, package get_available gold).
   - Test class for pure helpers: exact pattern from item7/25 F5 (class Test*PureHelpers with 5+ tests; import inside test funcs per file convention; no service mocks for pure; placed after last class).
   - Port of desc wizard 5 tests: exact per item8 impact "change from @patch("handlers.store_admin_handlers.PackageService") + mock_pkg_svc.return_value.get_available... = [mock_pkg] to @patch("handlers.store_admin_handlers.get_service") + setup mock_store.get_available_packages_for_store.return_value = [mock_pkg with .id/.name/.file_count/.store_stock]; ... assert on store mock call (not pkg); keep exact data/text/state asserts + 'No hay paquetes' etc".
   - 0 export pure/delegate in __init__: confirmed (import direct sufficient + used).
   - Any differing: none; registered in GSD + self-check (none).

5. **Decisiones (sección 4 del PLAN):** Al inicio de la fase relevante (primer GSD entry de la fase), registra qué decidiste para "nombre de helper", si trimmaste docstring para LOC, cómo manejaste logging, si usaste el pure desde svc o local, etc. Si difieres del "preferido" (impact recs + item7/25 patterns), explica brevemente (mantén espíritu tight + gold + 0 behavior + UI idéntica).

6. **Gates y re-runs:** 
   - Corre los targeted pytest con los flags exactos de sección 5 ( -p no:cov --override-ini="addopts=" ).
   - Si un unrelated fail preexistente aparece (ej. alembic_heads, daily concurrent UNIQUE, cross daily !success pre patch en priors, N806, SAWarnings, RuntimeWarning AsyncMock in _safe_answer, MovedIn20Warning, Deprecation utcnow, InternalEventBus.emit not awaited, unraisable), documéntalo en log pero **no lo cuentes como regression del Item** (precedente 25/24/23/22/20/19 "Riesgo: baseline shows pre-existing unrelated fails ... document; do not count as regression" + "0 attributable to this Item").
   - Re-run de handler test full + cross store/product flows + package get_available gold es obligatorio en F5 (y spot en F1/F3/F4).
   - Siempre GSD pre- antes del pytest/ruff/grep grande.
   - Al final F5: re-ejecuta los combinados + broader smoke filtrado por store/product + package gold + self-check + POOL/BATCH confirm + explicit "segundo del nuevo pool de 4" + "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

7. **Alcance (recuerda siempre):** Solo edita los archivos listados en "Archivos que se modificarán" + el log GSD + (este PLAN ya está) + opcional SUMMARY.md al final. Si sientes la tentación de "limpiar más handlers", "tocar store_user para parity", "agregar tests fuera del store_admin test file", "editar CLAUDEs o decisions o services/store/CLAUDE.md", "cambiar behavior de CRUD/stock/delivery", "broad fix other long wizards (mission_admin etc)", detente: scope tight para esta entrega (recomendado por impact + "second of new pool of 4" + "0 otros handlers" + "0 behavior change en product CRUD/stock" + "0 delivery/gamif credit impact" + "0 docs más allá"). El analyzer + user prompt + precedents recomiendan empezar tight aquí. El siguiente item del pool (o arch-enforcer) puede expandir si user quiere.

8. **Al final del Item (F5):**
   - Completa el self-check en el log (lista de fases, DoD cumplidos, archivos modificados, tests que pasaron, reglas verificadas (GSD pre every, scope tight 3 files + log + 0/0/0/0, 1svc Store + delegate for pkgs, LOC<=50 via inspect, logging, pure helpers tests, no prod chg), desviaciones (si las hubo; ej. ruff hygiene como chore 0 logic per 25/24), tests críticos para futuro (lista explícita), "Item 8/26 closed. Second of new pool of 4. Previous batch of 4 (ending with Item 7/25 + Item 6/24 ...) closed with tests passing per 24-SUMMARY BATCH note + 25 self-check PASSED. Ready for arch-enforcer re-scan (enfocado en store_admin_handlers: exactly 1 service + <=50L + no direct PackageService + pure helpers for stock/UI/wizards) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4").
   - (Opcional pero recomendado) Produce `.planning/phases/26-store-admin-long-funcs/SUMMARY.md` con executive + refs al log + comandos de re-verificación (sigue estructura de 25/24/23/20).
   - Confirma en log: "Self-Check: PASSED".
   - El siguiente agente (gsd-executor next item o arch-enforcer/test-guardian) usará el log + este PLAN + los cambios como fuente de verdad.

9. **Si algo no está claro o difiere del "reporte del impact-analyzer" o user prompt:** El prompt del usuario + este PLAN (basado en discovery completa + el reporte completo en .claude/.../item8-...md + handoff de 25-SUMMARY + 24 BATCH + gsd logs de item7/25 + item2/5/6 + código actual + precedents PLAN 20/21/23/25) es la fuente de verdad. Pregunta solo si un gate bloquea por ambigüedad real de nombre/firma/contrato (e.g. nombre exacto del helper); de lo contrario, elige conservadoramente siguiendo precedentes (item7/25 ports + helper extract + LOC inspect + self-check, impact exact code blocks for delegate/pure + port desc instructions, item2/5/6 pure + delegate comment, 24/25 BATCH/POOL language, get_service context + __enter__/__exit__ mocks, real pure via attrs, docstrings "ported...", 1-line/min support + delegate comment, inspect LOC, UI 1:1) y registra la elección en GSD.

**¡Ejecuta con disciplina total. Cierra el Item de forma limpia, segura, medible y con trazabilidad GSD completa. La refactor de los store_admin handlers (1 service Store-only via get_service + delegate for pkgs in wizard + pure helpers for <=50L + tests) queda hecha sin impacto en los 3 sistemas críticos ni en los contratos de CRUD/stock/delivery/partial failure. UI idéntica. Listo para arch-enforcer + test-guardian + siguiente item del pool de 4 (flujo continúa automáticamente).**

---

**Fin del PLAN para 26-store-admin-long-funcs (Item 8, second of new pool of 4).**

Referencias rápidas para el executor (actualizar con líneas reales durante ejecución si cambian):
- Impact report (source of truth): .claude/agent-memory/impact-analyzer/item8-store-admin-long-funcs.md (mapa, risks, scope 3 files, "second of new pool of 4", helper examples compute_stock_emoji_and_text / build_*_text_and_buttons / build_product_detail_keyboard / build_product_confirmation..., tests port 5 desc + add TestStoreAdminPureHelpers, 0 behavior/0 other handlers/0 package_svc/0 CRUD/delivery chg, design "StoreService vía get_service + delegate para wizard pkgs + puros para status/UI", exact delegate/pure code blocks, port instructions, "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters...").
- Gold precedent for 1svc + pure helpers + ports + helper tests + LOC + self-check (first of new pool): .planning/phases/25-reward-handlers-1service-loc/PLAN.md + .planning/quick/gsd-reward-handlers-1service-loc.log (F1 pure+delegate confirm, F2 handler 1svc+rel+pure+log, F4 port test to get_service+rel+pure attrs+__exit__+docstrings "ported...", F5 new Test*PureHelpers class + re-runs + rules verif + self-check PASSED + critical list + handoff + "first of new pool" + "previous batch closed per 24-SUMMARY").
- Item2/5/6 golds for pure extract + delegate comment + 1-line + test ports + helper tests + LOC inspect + "Arch-enforcer addressed": gsd-reward-gamif-item2.log + gsd-testing-debt-item5.log / item6.log + 20-reward-gamif PLAN.
- BATCH close precedent (cite in F5 self-check): .planning/phases/24-remaining-besito-compositions/24-remaining-besito-compositions-SUMMARY.md ("BATCH: 4 items completed in this tirón (Item 6 final of max 4)", "Item 6/24 closed. BATCH...", self-check PASSED) + its gsd log (BATCH COMPLETE NOTE) + 25 SUMMARY/gsd (first of new pool + previous batch closed).
- GSD log para este Item: .planning/quick/gsd-store-admin-long-funcs.log (planner INIT + pre-mkdir + pre-write 3 entries; executor append pre every).
- Reglas + contexto: CLAUDE.md (root + handlers + services + models), rules.md, architecture.md, decisions.md, AGENTS.md, services/store/CLAUDE.md (stock conventions -1/0/>0, delegate awareness), models/CLAUDE.md (rels safe), handlers/CLAUDE.md (1 service rule).
- Comandos + patrones: sección 5 + "Instrucciones" arriba + item7/25 log entries exactas + item8 impact exact blocks.

Listo para gsd-executor. Ejecuta F1 → ... → F5 con GSD pre en cada paso + self-check PASSED + POOL/BATCH confirm al final + explicit "segundo del nuevo pool de 4" + "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool." Handoff explícito.

**Hecho con 💋 para Diana (Señorita Kinky) — gsd-planner subagent (continuación del hardening post-unificación de Besito + item7 reward 1svc+LOC; second of new pool of 4).**
