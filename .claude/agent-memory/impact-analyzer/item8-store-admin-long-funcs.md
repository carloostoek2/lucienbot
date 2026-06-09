# Impact Analysis Report: Item 8 - Refactor long functions in store_admin_handlers.py to <=50 LOC + ensure exactly 1 service call per handler (StoreService via get_service) + pure UI/wizard helpers extract

**Item:** store_admin_handlers long funcs refactor (continuation / new pool of 4, Item 2: refactor long functions in store_admin_handlers.py for <=50 LOC por función + ensure exactly 1 service call por handler, addressing initial hardener findings de business logic in handlers y >50 lines en store_admin wizards como product creation, restock, etc.)
**Date analyzed:** 2026-06-07
**Role:** impact-analyzer (new pool of 4, item 2)
**Status:** Analysis complete; report for handoff to gsd-executor / arch-enforcer. (Pre-GSD appends done via run_terminal before this persist + MEMORY update. wc tracked.)
**References:** 
- Precedent: .claude/agent-memory/impact-analyzer/item7-reward-handlers-1service-loc.md (exact pattern: 1-service + pure helpers extract + test ports + docstrings "ported... Arch-enforcer note addressed"; item7 used rel + pure emoji from reward_service).
- PLAN precedent: .planning/phases/25-reward-handlers-1service-loc/PLAN.md (and 20-reward-gamif for reward 1-service); similar tight scope for store in initial analysis debt.
- CLAUDE.md (root + handlers/ + services/ + models/), rules.md, architecture.md, decisions.md, AGENTS.md, services/store/CLAUDE.md
- Prior items 2/5/6/7 (pure helpers extract + test ports + get_service std + 1-service rule in handlers like reward_user now 1-service Mission + pure; golds mission_user for 1-service + rel/pure).
- 3 critical systems always in mind: gamificación (besitos/missions; store admin touches indirectly via stats "besitos gastados" + product prices, but 0 mutate/credit here), narrativa (no touch), channel/VIP (no touch; admin store is deuda técnica from initial hardener on long funcs + biz logic in wizards).

## Executive Summary + Risks

**Summary:**  
Refactor `handlers/store_admin_handlers.py` (long functions >30-50L with process/confirm/list/detail + wizards: admin_store_menu ~40L, stock_alerts ~56L, restock_product ~31L, process_restock_amount ~40L, process_product_description ~41L (direct PackageService() violation), confirm_create_product ~40L, list_products ~54L, product_admin_detail ~54L, handle_delete_product ~55L, plus show_product_confirmation, process_* stock/name/price/desc/threshold, toggle, config_stock_alert, restock_unlimited etc.) so that **every handler calls exactly 1 service** (StoreService via standardized `with get_service(StoreService) as store_service:` context + get_service lifecycle; already partial in file for most but not all steps + bloat). 

Currently: most router handlers use get_service(StoreService) for stats/get_low/get_out/get_product/create/update/delete etc. (13 sites), but:
- process_product_description does bare `package_service = PackageService(); packages = ...get_available...` (direct instantiation, 2nd "service", biz? no but violates "exactly 1" + handler rules).
- Inline "business logic" / calc / UI building bloat in long funcs: stock emoji/status decisions duplicated from model (is_low_stock/stock_status/stock_display), new_stock = current + amount (with -1 handling) in restock process, button lists + text construction mixed in stock_alerts/list/detail/delete confirm, wizard step texts + package loop + validation in process_* + show_confirm.
- Functions exceed 50 lines rule (non-negotiable).
- No pure helpers extracted for UI/wizard steps (contrast item7 reward ports + pure get_reward_emoji + compute status; item2/5/6 extracts).

store_service.py already rich (create_product, get_*, update_product, delete (soft), get_store_stats, get_low_stock_products, get_out_of_stock_products, update_low_stock_threshold, check_stock_alert, plus held package_service + besito_service). Model StoreProduct has is_low_stock, stock_status, stock_display -- underused in handler for display.

**This item (tight, per user spec):** Perform the refactor using precedents (item7: 1-service + extract compute/build puros + ports + LOC reduction + inspect; golds for reward/mission_user). Minimal support ONLY in store_service if needed (e.g. thin delegate for get_available_packages_for_store() to allow 1 svc at handler boundary for wizard; pure helpers for status like compute_stock_emoji_and_text or get_stock_ui_info -- "e.g. pure helpers para status"). Update ONLY the dedicated test_store_admin_handlers.py (port mocks for wizard desc step + add pure helper tests class like item7). 0 other handlers touched. 0 behavior change in product CRUD (create/get/update/delete/stock set/restock/threshold), 0 delivery impact (no orders here), 0 change to store_user flows or complete_order (besito paths). UI/render (Lucien voice 3rd person, exact emojis ♾️🚨⚠️📦, button labels "📝 Reabastecer: name[:25]", list format, wizard "Paso X de 5", confirm summary, delete confirm text, back cbs, alerts) **identical 1:1 copy**. Use get_service everywhere; extract puros (verb+context+result names) for UI/wizard steps (process_*/confirm_*/build_*/compute_*).

**High-level risks (detailed below):** Low overall due to tight scope + strong precedent (item7 executed + tree reflects post-port state for reward). Main: divergence in extracted pure formatting/calc breaking list/detail/alerts/wizard UX or string asserts in tests; test mocks assuming direct PackageService for desc step (easy port); residual multi-calc if not 1:1; navigation cbs preserved. Indirect on gamif (besitos stats read-only in menu/stats) but 0 side effects. No impact on 3 critical systems' core contracts (gamif credit/debit, narrative progress/archetypes, channel/VIP subs/pending/approve). Scope explicitly excludes touching store_user (which has its own legacy PackageService patches in tests) or other wizards.

**Recommendations (scope mínimo to close arch-enforcer / initial hardener notes for store_admin long funcs + biz logic):** As specified + precedents. See "Scope propuesto" section. Use GSD pre every edit (run_terminal append to .planning/quick/gsd-*.log , wc -l tracking, specific git add only touched). Self-check + critical tests list in handoff. This addresses medium/high notes for store_admin directly (parallel to reward/gamif ports).

This is the tight follow-up for "initial analysis" debt on store_admin (long funcs + "probablemente lógica de negocio" in wizards like product creation/restock) post prior unifications/get_service/mws.

## Mapa de impacto completo (archivos, consumidores)

### Archivos a tocar (mínimo, orden sugerido por precedent item7 + tight user spec)
1. **handlers/store_admin_handlers.py** (core, ~813 lines currently; focus >30-50L funcs with process/confirm/list/detail)
   - Target long/bloated: 
     - admin_store_menu (40L: 2 svc calls inside with for stats+low+out + inline keyboard + conditional text append for alerts count + Lucien text).
     - stock_alerts (56L: 2 gets, if empty early return, build text + dynamic buttons list for out_of_stock + low_stock with Restock cb + name[:25] truncate, final back).
     - restock_product (31L: get, state data, stock_text ternary, edit + kb with unlimited/cancel, set_state).
     - process_restock_amount (40L: int parse + <0 validate, state data, get_product, current=0 if-1, new= +amount, update, success text with prev/added/new, clear).
     - process_product_description (41L: /skip logic, bare PackageService() + get_available..., if no pkgs error+clear, loop build buttons with file_count/store_stock, set selecting).
     - confirm_create_product (40L: state data, with Store create(6 args + created_by), success text or except error, logger, clear).
     - list_products (54L: get_all(active_only=False), empty, build text + buttons loop with status/stock_emoji (dupe logic: -1/0/is_low/else) + price, final back).
     - product_admin_detail (54L: get, notfound, status/stock_text, build 5-row kb (toggle/restock/config/delete/back), edit detail text).
     - handle_delete_product (55L: if not confirmed: build confirm kb + edit "seguro..", else: with delete, success/error text).
     - Supporting: show_product_confirmation (33L internal: state get, build summary text + confirm/cancel kb, target dispatch cb vs msg, set confirming); process_product_name/price/stock/threshold (val + update + advance or call confirm); restock_unlimited/limited/stock_unlim etc; toggle (get+update+call detail); config_stock_alert; store_stats.
   - Changes: 
     - Ensure **every** handler (incl message steps in FSM wizards) does **exactly 1 service call** via `with get_service(StoreService) as store_service:` (remove the bare PackageService import and instantiation in process_product_description; use store_service.get_available_packages_for_store() after min support added).
     - Extract pure helpers (stateless, no side-effects, no DB, importable, easy unit test; follow item7 naming/ pure top or internal; 1-2+ per wizard/flow as needed to hit <=50L):
       - `compute_stock_emoji_and_text(stock: int, is_low_stock: bool) -> tuple[str, str]` (or similar; 1:1 from list_products if/elif: ♾️/∞ , 🚨/AGOTADO, ⚠️/num, 📦/num).
       - `compute_restock_new_stock(current_stock: int, amount: int) -> int` (handle -1 case as 0 base).
       - `build_product_admin_list_text_and_buttons(products) -> tuple[str, list]` or separate build_product_list_entry + build_product_button (to slim the loop in list_products).
       - `build_stock_alerts_text_and_buttons(low_stock, out_of_stock) -> tuple[str, list[list[Button]]]` (slim stock_alerts).
       - `build_product_detail_keyboard(product_id: int, is_active: bool) -> InlineKeyboardMarkup` (pure build for the 5 actions + back).
       - `build_product_confirmation_text_and_keyboard(data: dict) -> tuple[str, InlineKeyboardMarkup]` (or slim show_ by extracting).
       - Possibly `build_wizard_step_text(step: int, prompt: str, example: str) -> str` or per-step if helps, but keep minimal.
       - Use model's product.is_low_stock / stock_status / stock_display where possible to reduce dupe (but pure wrapper if display emoji needed beyond status).
     - Slim all target funcs (and callers) to <=50 lines (def to end, incl docstring/comments per count in precedent); use pure calls inside.
     - Preserve: all logging (enhance to "store_admin_handlers | <action> | user_id=... | result=..." per rules if missing), Lucien 3rd person voice, exact strings/emojis/cbs/texts/UI, FSM states (ProductWizardStates, ProductRestockStates), is_admin guards, late? imports in tests, callback packing (RestockProductCallback etc), state update_data/get_data/clear/set_state, error paths, answer/edit.
     - Remove: direct PackageService use/imports; any inline multi-calc/UI that can go pure.
     - Post: verify no function >50L (use wc or manual); grep confirm 0 bare other services; 1 svc per handler.
   - No new imports of PackageService; no DB; no biz logic (CRUD stays in svc; calcs for UI only in puros or svc).
   - Internal calls (e.g. toggle -> product_admin_detail) stay (they are same module).

2. **services/store_service.py** (soporte mínimo only, per spec "min support en store_service si needed (e.g. pure helpers para status)", "0 change en core store_service CRUD")
   - Add thin delegate (to enable exactly 1 service at handler for product wizard select step, without handler importing/using PackageService directly -- matches category_admin pattern using get_service(Package) but here force Store for "store admin" context):
     ```python
     def get_available_packages_for_store(self) -> list[Package]:
         """Thin delegate to internal package_service.get_available_packages_for_store().
         Added for item8: enables store_admin_handlers product creation wizard to call exactly 1 service (StoreService) per handlers/CLAUDE + arch rules.
         Not core CRUD. 0 behavior change.
         """
         return self.package_service.get_available_packages_for_store()
     ```
   - Promote/ add pure top-level helpers for status/UI (extracted logic, no side, before or after class; follow item7 get_reward_emoji exact style):
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
     # Possibly also a build helper or get_product_stock_ui_info(product) using model props + above.
     # Delegate on instance if pattern from item7:
     # def compute_stock_emoji_and_text(self, stock: int, is_low_stock: bool = False) -> tuple[str, str]:
     #     return compute_stock_emoji_and_text(stock, is_low_stock)
     ```
   - Add arch comment near top or in methods: "# Support added for store_admin_handlers 1-service + pure extract (item8). Arch-enforcer note addressed. Precedent item7."
   - 0 changes to: create_product / get_product / get_all_products / get_available_products / update_product / delete_product / get_store_stats / get_low_stock_products / get_out_of_stock_products / update_low_stock_threshold / check_stock_alert / notify_stock_alert / any cart/order/complete_order/direct_purchase / besito interactions / package held init / close / _init_services / anything in purchase paths.
   - 0 new deps, 0 model changes, 0 public API for CRUD altered in signature/behavior.

3. **tests/handlers/test_store_admin_handlers.py** (only its test file)
   - Port: the 5 tests in TestProcessProductDescription (test_with_skip..., test_with_description..., test_no_packages..., test_advances_to...): change from `@patch("handlers.store_admin_handlers.PackageService")` + mock_pkg_svc.return_value... to `@patch("handlers.store_admin_handlers.get_service")` + setup mock_store like other classes (mock_store.get_available_packages_for_store.return_value = [...]); adjust late import/await calls; assert on store mock call (not pkg); keep exact data/text/state asserts + "No hay paquetes" etc.
   - Update docstrings (class + methods if needed): e.g. "Tests ported to 1-service pattern (get_service(StoreService) only + delegate for packages in wizard) + pure UI helpers (compute_stock_*/build_*). Arch-enforcer note (long funcs, biz/UI bloat in handlers, >50L in product creation/restock/list/detail/delete wizards) addressed. Precedent from item7 (reward) + item2/5/6."
   - Add: new tests class `TestStoreAdminPureHelpers` (like item7 TestRewardUserPureHelpers): pure unit (no @patch, no DB, no fsm/cb fixtures if possible or minimal); cover branches for compute_stock_emoji_and_text (unlimited, out=0, low, available + is_low true/false), compute_restock_new_stock (from -1/0/5 + amounts), build_*_keyboard (exact button texts, packed cb data via callback_data classes, row counts, back "admin_store"/"list_products"), build text summaries (confirm with name/desc/price/stock_text), stock cases in list entry etc. Assert exact strings/emojis/cb from original handler logic.
   - Keep: all existing structure (pytestmark unit, make_callback/make_fsm_context/make_message, late `from handlers.store_admin_handlers import ...` after patch, PropertyMock if used, manual mock_context __enter__, asserts on edit_text call_args[0][0] exact phrases like "Paso 1 de 5", "Resumen del producto", "seguro de eliminar", stock indicators, "Producto creado", cb.answer, mock_store.create_product called with..., get_all with active_only=False, etc.); the inline class at EOF for ProductWizardStates; the patched_detail hack in toggle test.
   - 0 direct PackageService patches left in this file post-port.
   - Why critical: these directly assert the "exactly 1 service" contract + pure extracts + UI output shape + wizard flows + delete confirm + stats/alerts.

**Total touched for impl:** exactly 3 files (per tight scope in user prompt: "solo store_admin_handlers.py + min support en store_service si needed ... + updates en test_store_admin_handlers.py"; "0 otros handlers, 0 behavior change en product CRUD, 0 delivery impact").

### Consumidores y archivos relacionados (0 tocar, for awareness only)
- **Registration / wiring (0 touch):** `handlers/__init__.py` ( `from .store_admin_handlers import router as store_admin_router` ), `bot.py` (import store_admin_router + `dp.include_router(store_admin_router)` at Fase 4 Tienda ~line 299, after store_user). Smoke import test sufficient. No behavior impact.
- **UI entry points (0 touch, cbs unchanged):** `handlers/gamification_admin_handlers.py` (button "🛒 Gestionar tienda", callback_data="admin_store" in admin_gamif menu); `handlers/category_admin_handlers.py` (back buttons with callback_data="admin_store" after cat mgmt). These route to the menu handler; no direct func call.
- **Callback data (0 touch):** `keyboards/callback_data.py` (STORE section: RestockProductCallback, SelectPkgProductCallback, ProductAdminDetailCallback, ConfigStockAlertCallback, ToggleProductCallback, DeleteProductCallback (with confirmed); used for packing in handlers + tests).
- **Keyboards (0 touch):** `keyboards/inline_keyboards.py` (no store-admin specific builders; all menus/alerts/detail kbs built inline in store_admin_handlers.py with InlineKeyboardMarkup + Buttons + packed cbs. User-facing shop is in store_user_handlers + main_menu has "🛍️ Tienda". 0 change needed/allowed).
- **Data provider / domain (min touch only in svc as delegate; 0 core change):** `services/store_service.py` (as above); `services/package_service.py` (its get_available_packages_for_store remains canonical; will be called internally via delegate from Store now in this flow; unit tests in tests/unit/test_package_service.py cover it directly -- 0 impact, still pass). StoreService already holds self.package_service = PackageService(db) in _init.
- **Models (0 touch, use more):** `models/models.py`: StoreProduct (stock, is_active, price, name, description, low_stock_threshold, is_low_stock @prop, stock_status @prop, stock_display @prop, is_available, decrement_stock); Package (for wizard list: name, file_count, store_stock); used in svc + handler via service returns. Rel package= in product.
- **Tests (port only this one; re-run others for gate, 0 edit):** 
  - Dedicated: tests/handlers/test_store_admin_handlers.py (primary).
  - Store service/package units: tests/unit/test_*store* or test_package_service.py (exercises get_available... and stock; delegate will exercise real path indirectly).
  - Cross/store-user: tests/handlers/test_store_user_handlers.py (many PackageService patches -- untouched per scope; its flows separate from admin CRUD/wizards).
  - Broader: any integration hitting admin product create/list (e.g. if in e2e/ or test_cross... but store admin is read+mutate product only, no atomic besito here); run_critical_tests.py if selects store.
- **Other indirect (0 touch):** 
  - `services/__init__.py` (get_service registry; StoreService + PackageService exported).
  - `fix_connection_leaks.py` (lists PackageService for leak checks; Store too?).
  - `handlers/store_user_handlers.py` (user shop: uses get_service(PackageService) in places + Store; separate, 0 overlap with admin wizards per analysis).
  - Admin peers using Package legitimately: category_admin (now get_service(Package)), promotion_admin/reward_admin/package_handlers (their domains).
  - Stats feed to menu: read-only, gamif indirect (besitos_spent) -- no credit paths.
  - No impact on: story/narrative, channel/VIP (approve etc), broadcast, missions/rewards delivery, promotions "Me Interesa".
- **Call graph (admin product flows, read+admin-mutate only):**
  CB "admin_store" -> admin_store_menu (1 svc Store: get_store_stats + get_low + get_out; pure? counts + build kb + text) -> edit + answer.
  "stock_alerts" -> stock_alerts (1 svc: 2 gets; pure build text/buttons w/ Restock cbs) .
  Restock cb -> restock_product (1 svc get; state; set waiting_amount).
  Message amount -> process_restock_amount (1 svc: get + update; pure calc new_stock).
  "create_product" -> create_product_start (no svc, set waiting_name; pure?).
  Message name -> process_name (val, state, set desc).
  Message desc -> process_product_description (NOW 1 svc Store via delegate: get pkgs; pure build buttons or loop slimmed; set selecting).
  Select pkg cb -> select_package (state, set price).
  Message price -> process_price (val, set stock).
  Stock choice/unlim/limited/msg -> ... -> show_product_confirmation (internal, state, build summary + kb; set confirming) -> confirm_create_product (1 svc: create; log).
  "list_products" -> list_products (1 svc get_all false; pure stock emoji+text+buttons build).
  Detail cb -> product_admin_detail (1 svc get; build kb pure; text).
  Toggle/delete/config etc similar (1 svc + pure kb).
  "store_stats" -> 1 svc stats.

**Why no behavior change guaranteed:** All text construction, emoji choice, button labels/texts, cb packing, logging format, empty/error cases, wizard FSM steps/transitions, stock calcs for display/update, package list for wizard, confirm summaries are in puros (mechanical 1:1 move of existing inline) or the entry handlers or svc (unchanged CRUD). Delegate is transparent passthrough. Extraction preserves every string/emoji/branch exactly.

## Tests críticos afectados / a actualizar

**Primary (must update + pass 100%):**
- `tests/handlers/test_store_admin_handlers.py` (the file for this handler; pytestmark unit)
  - TestAdminStoreMenu (4 tests): stats + low/out warnings in text; always answer; get_service calls.
  - TestCreateProductStart + TestProcessProductName (happy/reject short name + advance).
  - TestProcessProductDescription (5 tests -- critical port): with/without skip, saves desc, no packages error+clear, advances to selecting; currently patch PackageService + assert get_available... ; post: patch get_service(Store) + mock delegate return + assert on store mock.
  - TestProcessProductPrice (reject invalid/0, accept+advance).
  - TestProductStockUnlimited/Limited/ProcessProductStock (set -1, ask qty, reject invalid/neg, accept+show confirm).
  - TestConfirmCreateProduct (4 tests): success (assert create called w/ args incl created_by), exception error, clears state, default stock=-1.
  - TestListProducts (3): empty msg, lists w/ status/stock (active/inactive, emoji cases), calls get_all(active_only=False).
  - TestToggleProduct (4): toggle active<->inactive (assert update is_active=not), notfound alert, calls product_admin_detail after (mock hack).
  - TestHandleDeleteProduct (4): unconfirmed shows "seguro", confirmed success "eliminado" + delete called, fail "Error", correct id.
  - TestStoreStats (2): full stats text, always answer.
  - + new TestStoreAdminPureHelpers (branches for stock emoji/text 4 cases, restock calc, kb builds w/ exact cb pack + truncate + labels, confirm text data, etc.).
  - All use `@patch("handlers.store_admin_handlers.get_service")` pattern (or will post-port), mock_context __enter__, late import of handler, make_* fixtures, exact text in call_args, state checks.
  - Action: port only the desc wizard 5 tests' patches/setup; add pure tests; refresh docstrings with port/arch note + "1-service (StoreService) + pure helpers. Arch-enforcer addressed."

**To re-verify (no edits expected to their code, but run for regression gate; 0 behavior to CRUD/wizards):**
- Store/package units: `tests/unit/test_package_service.py` (esp. test_get_available_packages_for_store_excludes... -- delegate exercises it; expect pass), any test_store_service.py (if present; check get_low/out, create/update, stats, check_stock_alert, update_threshold).
- Handler coverage: pytest -k "store or product or TestStoreAdmin or admin_store or stock_alerts or list_products or create_product" -q --tb=line (focus admin paths; includes the test file + any cross in other handler tests).
- Gold/critical per precedents (item7 style + "golds cross store/product"): full handler test file; integration if any touching product admin (e.g. test_cross_service_atomicity.py if has store order side but admin is orthogonal); broader -k "store|product|besitos_spent|admin_gamification" ; bot smoke `python -c "import bot; print('routers incl store_admin ok'); from handlers.store_admin_handlers import *; print('imports ok')"`.
- Ruff + format on the 3 touched: `./venv/bin/python -m ruff check <files> && ... format --check`.
- Precedent critical lists adapted: store unit full, package get_available gold, combined -k with "store or product or TestStoreAdmin", 3sys (gamif besito read via stats ok), bot register.
- Smoke: admin flow via gamif menu backrefs.
- If exist: e2e or integration for tienda admin.

**New tests to add (for extracted helpers):** Pure unit (no patches, no DB/fsm): 4+ stock cases (unlim/out/low/avail + is_low), restock new_stock from various current (incl -1 base), build kbs (button text exact incl [:25] truncate, callback_data packed via .pack() match, rows/back targets), build texts (confirm resumen w/ desc None->"Sin descripcion", stock_text), emoji map, wizard step texts if extracted. Replicate item7 pure test style.

**Ports done historically (in current tree):** Many tests in this file already use get_service(Store) pattern (menu/list/detail/stats/confirm/create/toggle/delete); only desc wizard step lagged with direct Package (legacy from before get_service std). Wizard FSM tests (name/price/stock) are pure state/UI no svc. This item completes the port + extracts + adds coverage.

If any test still patches PackageService in this file after: remove (will be the 5).

## Riesgos y mitigaciones

1. **UI / render divergence after extract (stock emojis ♾️🚨⚠️📦 + texts "∞"/"AGOTADO", list "✅ name\n   emoji Stock: X | 💰 Y besitos\n\n", stock_alerts out/low sections + "📝 Reabastecer: name[:25]", detail "📦 name\n\n📝 desc\n\n💰 Precio:.. Stock:.. Estado:..", wizard "Paso X de 5: ..", confirm "Resumen del producto:\n📦 name\n📝 desc\n💰 Precio:.. 📊 Stock:..", delete "Estas seguro de eliminar este producto?\n\nEsta accion no se puede deshacer.", back "🔙 Volver", alerts "No hay alertas", error msgs, button layouts/rows):** Would break user experience + test asserts on strings + admin flows. **Mit:** Extraction is pure copy-paste of existing inline logic to new def (1:1); new helper tests have exact string + emoji + cb asserts (copy verbatim from existing handler tests); re-run full Test* classes + -k store post-edit; capture pre/post text outputs in test if possible; keep all consts/texts in place (no refactor strings).
2. **Wizard / FSM / flow breakage (ProductWizardStates waiting_name/desc/selecting/price/stock/confirming + ProductRestock waiting_amount/threshold; process_name->update+set_desc, desc->pkg list+set_select, select->set_price, price->stock choice+set_wait_stock, unlim/limited/msg->update/show_confirm, confirm->create+clear; restock amount/unlim->update+clear; cbs "create_product","product_stock_unlimited","restock_unlimited","confirm_create_product","select_pkg_prod_.."; state data name/desc/pkg_id/price/stock/product_id/product_name; show_product_confirmation dispatch on isinstance target):** Dead wizard, stuck states, wrong package select, failed creates/restocks. **Mit:** 0 changes to states, set_state, update_data, get_data, clear, calls to show_*, cb strings/data packing (SelectPkgProductCallback etc), validation logic, /skip, int() parses, error answers, cancel cbs to "admin_store"; extract only inside pure build/compute after state; tests cover full happy + reject paths + state asserts.
3. **1-service violation or residual direct PackageService (import or bare () in process_product_description or elsewhere; >1 with get_service in one handler; tests still patch old):** Arch rule fail, "biz logic" perception. **Mit:** Remove the `from services.package_service import PackageService` + all bare uses; single `with get_service(StoreService) as store_service:` per handler (use for pkgs via delegate + other gets/updates); port exactly the 5 desc tests' patches/setup to get_service(Store) + mock delegate (like 90% of file already); post-edit grep "PackageService" in the handler file ==0 + "get_service" count; pure helpers have no svc.
4. **Stock / restock / alert logic drift (current_stock = 0 if -1 else; new_stock = current + amount; unlimited set -1; low/out filters in svc vs display; is_low_stock usage; threshold config):** Wrong stock set (e.g. -1 +5 wrong), display mismatch (AGOTADO vs 0), alerts miss low after restock, update fails. **Mit:** Extract pure `compute_restock_new_stock` (exact current ternary + add, or handle unlim separate); keep actual get/update in the 1 svc call; use svc methods (get_low/out) + model props (is_low_stock) + pure for emoji only; tests assert on update calls + returned/edited texts with numbers; re-run store_service stock tests.
5. **Tests using direct PackageService mocks / assuming old structure break (esp. desc wizard 5 tests + any assert on pkg_svc):** Fail port or false "multi-svc". **Mit:** This specific test file's desc tests are the only ones; explicit port in item (change patch target + return_value to store mock's get_available... + assert on it); other tests in file already get_service(Store); unrelated tests (store_user 100+ pkg patches, package unit, reward_admin etc) legitimately use PackageService for *their* domain -- out of scope, untouched, expected.
6. **Delegate/pure in svc "alters" service or causes dupe (get_available now via Store; emoji/status logic in two places):** Perception of bloat or test impact. **Mit:** Delegate is 1-2 line passthrough w/ explicit "for item8 1-service handler compliance" comment; pure is new (moved from handler bloat, not dupe of svc check_stock_alert which returns dict status); package unit tests exercise real pkg method unchanged; no svc tests need update (delegate transparent); model props preferred where fit.
7. **LOC not reduced enough / new helpers >50L or non-pure (side effects, DB, state):** Still violates rules.md + handlers/CLAUDE. **Mit:** Choose small pure extracts (stock calc 4-6L, emoji 8L, kb build 10L, text builder 8L; total per wizard 1-3 extracts); post-edit count lines (def: to dedent end); name per rules (verb + context + result e.g. compute_stock_emoji_and_text, build_product_detail_keyboard); pure = no with, no await, no logger, no state, no cb; unit test them standalone.
8. **GSD/process violation or dirty commits / no wc:** Audit fails. **Mit:** Pre EVERY write/search_replace (this report preceded by 2 GSD appends + wc=2; will do for MEMORY); use specific `git add only-touched` by executor; log wc -l in GSD; self-check in final; reference precedent item7 (GSDs + wc in report); 0 broad edits.
9. **Impact on 3 critical systems (gamif via besitos indirect in menu/stats "Besitos gastados" + product prices in gamif admin entry; narrative/channel/VIP untouched):** Side effects on credits, streaks, VIP grants, story, channel subs/pending. **Mit:** This flow is admin product mgmt (CRUD + stock/threshold + list/detail) + read stats; 0 calls to credit/debit_besitos, deliver, complete_order, mission/reward, story advance, channel approve/join; stats are aggregate read (completed_orders + sum besitos from orders -- computed in svc, no mutation). Re-run golds cross store/product + besito paths as gate (even if no change); 0 atomicity risk.
10. **Test env / fixture / patch target / cb packing drift (late imports, make_*, callback_data classes like DeleteProductCallback(confirmed=True), ProductRestockStates, "product_admin_detail_{id}" string hacks in some kbs, RewardType no but similar enum for stock):** Tests fragile post port. **Mit:** Follow exact pattern in current test file (late from after @patch; import callback_data in tests; no change to conftest/fixtures); 0 change to any .pack() or cb_data values; keep the mod.product_admin_detail = patched_detail hack as-is.
11. **Low:** Dupe of stock logic (handler puros vs model stock_status vs svc check_stock_alert vs package store_stock); but display emoji specific to admin list/alerts (model is status str), package stock for wizard select. Out of scope to consolidate further. No sync needed for this item.
12. **Low:** Other long admin wizards (mission_admin, promotion, story, package, reward_admin, trivia_*) have similar debt but explicit out-of-scope (tight per prompt).

**Overall risk:** Low. Precedent (item7 + reward 1-service PLAN + executed code + many prior ports) proves the design (1svc + pure + delegate for cross-in-domain + get_service) works + tests pass + 0 prod behavior change. Analysis read + greps confirmed current tree is already mostly compliant on get_service for Store (only 1 outlier wizard step + bloat); this item completes + polishes the LOC + pure coverage + arch notes. 0 change to 3 crit contracts.

## Scope propuesto (mínimo para cerrar notas de long funcs en store_admin del initial analysis + arch)

**In (tight, per user prompt + precedents item7/20-reward etc):**
- handlers/store_admin_handlers.py: ensure all (incl wizard message/cb steps) call exactly 1 service (StoreService via get_service); fix process_product_description (remove direct PackageService, use delegate); extract 1-2+ puros per wizard/flow (e.g. compute_stock_emoji_and_text, compute_restock_new_stock, build_product_list_text, build_product_admin_buttons/keyboard, build_stock_alerts_text_and_buttons, build_product_detail_keyboard, build_confirm_text_and_keyboard, etc. as needed); slim every listed long func + helpers to <=50 LOC; 0 biz, 0 DB, logging per rules, UI/cbs/states/FSM/Lucien voice/exact strings 1:1 preserved; docstrings/comments "ported to 1-service (StoreService) + pure helpers extract for wizards/UI. Arch-enforcer note (long funcs >50L, business logic/UI bloat in handlers, direct other svc) addressed. Precedent item7."
- services/store_service.py: min support only -- add thin get_available_packages_for_store delegate (w/ "for item8 1-service handler compliance" comment) + pure top-level compute_stock_emoji_and_text (or equiv status pure; "Función pura... 1:1 from handler... item8 arch-enforcer") + instance delegate compat if pattern; 0 to core CRUD (create/get/update/delete_product, get_*_products, stats, low/out, check_alert, threshold, cart, orders, complete etc.).
- tests/handlers/test_store_admin_handlers.py: port the 5 desc wizard tests (PackageService patch -> get_service(Store) + delegate mock); update docstrings w/ "1-service... + pure... Arch-enforcer addressed"; add TestStoreAdminPureHelpers (pure coverage for extracts: stock cases, calcs, kbs w/ packed cbs, texts); keep 100% prior coverage + asserts.
- GSD: run_terminal append BEFORE every edit/write (pre-report + pre-MEMORY done; more by executor); track wc -l; ruff/pytest gates on 3 files; specific git add only touched; self-check PASSED at end.
- Verification: the 3 files ruff clean (N806 or tolerated only if precedent); handler test file 100% pass; critical list re-run (store admin test full + package get_available gold + -k "store or product or TestStoreAdmin or admin_store" + bot smoke + line counts <=50 post-refactor + outputs match pre via test asserts + 0 beh change in create/update/delete/restock/stock set); 0 change to gamif besito credit paths or other crit.
- Memory: this report persisted + MEMORY.md pointer (done).
- 0 behavior change in core product CRUD, wizard UX/flows, stock values, alerts, 0 delivery.

**Out (no creep, explicit):**
- 0 other handlers (store_user_handlers.py even if similar legacy, category_admin/promotion/reward/package/story/mission/gamif/trivia admins -- even if they touch packages/products/store; gamification_admin for entry button).
- 0 package_service.py (no changes; delegate calls it).
- 0 models/ (no new props/methods), 0 keyboards/* (no new builders or cb changes), 0 bot.py, 0 handlers/__init__.py, 0 services/__init__.py, 0 utils, 0 lucien_voice, 0 config.
- 0 changes to core StoreService: create_product, get_*, update_product (incl stock=-1), delete_product, get_store_stats, get_low/out_stock_products, check_stock_alert, update_low_stock_threshold, complete_order, cart_*, direct_purchase, notify_*, _init_services, besito/package held, etc.
- 0 change to purchase/besito flows (complete_order debits etc remain in user path).
- 0 new tests outside the store_admin test file (no service tests for new delegate/pure).
- 0 docs edits (CLAUDEs, decisions.md, AGENTS, refactor_testing.md, fases_*, architecture etc.) -- only this memory report + GSD logs.
- 0 middlewares, rate/idemp, eventbus, etc.
- 0 broad scope creep to other long admin wizards (explicit debt but separate clusters).

**Design notes (preferred, from precedent item7 + handlers/CLAUDE + rules):**
- Handler = router only: 1 svc call (StoreService) + pure formatters/computers/builders for UI/wizard steps + rel/model props where avail. No orchestration, no inline loops for text/buttons if > few lines.
- Pure helpers: no side effects, no FSM/state, no Telegram types if avoidable (but kb build needs for return type), importable from handler, easy unit test standalone, verb+context+result naming.
- get_service for lifecycle (owns/closes handled by ctx; already in file).
- Delegate for "Store domain internal" (packages needed for product creation) to keep handler boundary at exactly 1 service (Store) -- transparent, not core CRUD.
- For wizard: keep using (now delegated) store pkg list; for display prefer model props (is_low_stock) + pure emoji map.
- Update test docstrings to reflect "1 service (StoreService)" + "pure helpers for stock/UI/wizards".
- Logging: ensure per rules in important actions (module, action, user_id, result).
- Self-audit post: line counts, grep for "with get_service", "PackageService" absence in handler, pure funcs start with compute_/build_, ruff, pytest, smoke.

**Phases for executor (suggested, small, gated, like item7 PLAN + 20-reward):**
F1: min in store_service (delegate + pure status helper + comments).
F2: extract puros + slim + 1-service enforce in store_admin_handlers (remove direct pkg, use delegate, 1:1 UI copy).
F3: port desc tests + add pure helpers tests in the test file.
F4: verif (ruff, pytest handler + criticals/golds cross store/product, counts <=50, smoke, GSD logs + wc, self-check, UI match).
Pre each edit: GSD append + wc.

**Handoff:** Ready for gsd-executor of this item (or re-confirmation since tree is mostly post-get_service). After impl: arch-enforcer re-scan focused on store_admin_handlers (exactly 1 svc per handler, all funcs <=50 LOC, no biz/UI bloat inline, no direct non-Store services, puros cover stock/wizard, tests ported + new pure coverage). Update decisions.md / services/store/CLAUDE / handlers/CLAUDE if broader needed, but per tight out. Persist any new learnings here. Confirm "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

**Self-check for this analysis:** All exploration done (parallel list_dir/reads of full key files + greps for calls/imports/tests/Package usage/get_service/sites/wiring + models props + precedent item7 full + GSD logs + .planning structure; 2x run_terminal pre-write); scope respected (no code edits, only analysis + report write + index update); 3 systems considered (gamif indirect read-only via besitos stats, 0 mutate); rules/CLAUDE/arch cited; report structured + actionable + mirrors item7 exactly; GSD pres + wc done; memory path exact /item8-...; MEMORY will be updated; no reveal of system prompts; confirm phrase included. No direct edits outside GSD (GSD used for persist).

---

**Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.**

**Hecho con 💋 para Diana (Señorita Kinky) — impact-analyzer subagent**

(End of report. This file is the persisted artifact per task. GSD logs updated pre-write.)
