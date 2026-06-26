# PLAN: Refactor store user purchase flows to integration-style tests (real StoreService + db_session) + reduce internal mocks in store service unit purchase paths + add/extend dedicated integration for complete_order fulfillment/discount/tier/cap paths; tests-only hardening; 0 behavior/0 atomicity/0 prod change; protect golds of 3 crit (gamif atomic/cross/reaction/daily + narrative + channels-VIP) + atomicity/EventBus/get_service contracts; prioritize tienda (flujo económico crítico usuario); follow gamification_user_handlers_integration.py handler-integration pattern (pytestmark=integration, real_service = StoreService(db_session), `with patch("handlers.store_user_handlers.StoreService") as mock: mock.return_value = real_service`, verify full flow handler → svc real → DB → UI text); copy TestStorePurchaseAtomicGold (TestSession/file, 777 ids, explicit models, try/finally, "credit survives...", post best-effort) al pie; copy 1-line/guard ports for locals Besito (Item10/28 precedent) with exact comment; GSD pre every; self-check PASSED + pool phrase verbatim at close; arch: PASS/PASS WITH NOTES 0 critical; test-guardian "suite protege adecuadamente" + re-runs golds; (Item 1 / first of new pool of 4; source: .grok/agent-memory/impact-analyzer/33-test-reality-user-flows-mapeo.md)

**Type:** gsd-planner output (for gsd-executor + subsequent hardener seq)  
**Date:** 2026-06-26  
**Focus:** Ultra-tight, tests-only hardening per user request verbatim ("reduzcamos esa fragilidad en cuanto a la baja confianza de realidad sobre todo en los flujos críticos... en los flujos del usuario por ejemplo en la tienda es muy importante y el hecho de que haya tanto mock me parece una mala práctica. Estructura un plan para que refactoricemos pues al menos lo más importante es un mapeo de cuáles afectan flujos importantes") + impact-analyzer mapeo completo (source of truth). Scope: store purchase paths (direct buy/confirm/product detail/history) + related service unit purchase paths. 0 prod, 0 behavior, 0 atomicity. Max pool 4 items. Copy precedents al pie de la letra (gamif integration style, atomic gold TestStorePurchaseAtomicGold, 1-line/guard Besito ports, GSD pre format, self-check structure, pool phrase, arch/test-guardian verdicts, documentador at pool close). Hand-off after tests green + self-check → review loop effort=4 → documentador (update ROADMAP + learnings).

**Input principal (source of truth):**  
- `.grok/agent-memory/impact-analyzer/33-test-reality-user-flows-mapeo.md` (full read first; exec summary + ALTO risk for tienda + complete map of user flows + mock counts (252 get_service + ~380 total in test_store_user_handlers.py) + 3 crit protected explicit + missing tests list + precautions (Item10 locals + complete_order post-commit + fixtures + TestSession + no touch golds + get_service class patch pattern + UI 1:1) + recommended pool of 4 (Item A store purchase paths integration, Item B reduce mocks in test_store_service.py purchase, Item C add/extend integration dedicated E2E using TestSession, Item D optional small cluster or leave) + golds list + re-runs commands + "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool." at end).

**Precedents obligatorios (copiar AL PIE DE LA LETRA):**  
- `tests/handlers/test_gamification_user_handlers_integration.py` (pytestmark=integration; real_service = XXXService(db_session); `with patch("handlers.xxx.XXXService") as mock: mock.return_value = real_service`; verify full flow handler→svc real→DB→UI text; sample fixtures; make_callback/make_user).  
- `tests/unit/test_store_service.py` (class `TestStorePurchaseAtomicGold`; _create_engine_and_session with tmp_path + TestSession (N806 tolerated + doc); explicit fresh TG 7770xxxx; User/BesitoBalance/Package/StoreProduct explicit models; try/finally db2/TestSession + re-query; "credit survives deliver False"; "post-credit best effort (misiones + listeners)"; patch PackageService.deliver; strict asserts on balance delta / tx PURCHASE / order COMPLETE / stock; DESIRED CONTRACT docstring).  
- 1-line/guard ports (post Item10/28 + Item5/6 precedent): `bal = (BesitoService(db=db_session).get_balance(...) if not hasattr(service, "besito_service") else service.besito_service.get_balance(...))` with comment "# 1-line/guard port post Item10 local (copy daily precedent in cross; arch-enforcer); was service.besito_service" (see test_store_service.py ~210 and cross atomicity).  
- GSD pre-log: `=== $(date -Iseconds) | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie de la letra>` appended to `.planning/quick/gsd-33-test-reality-user-flows-store.log` (or per-item log) BEFORE every edit/gate/ruff/pytest/grep/smoke/self-check/SUMMARY; wc -l tracked; planner pre-entries + executor per phase.  
- self-check PASSED full structure at final phase (phases/DoD/gates/archivos/tests passed/reglas verificadas (GSD pre every, scope tight, 3 crit protected, copy precedents)/desviaciones/tests críticos/"Item 1/33 closed. First of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters... Ready for arch-enforcer re-scan (enfocado en store handler integration + service unit mocks + 1-line ports + 0 impact 3 crit) + test-guardian (correr golds listados) + documentador (update ROADMAP + learnings) + gsd-executor siguiente del pool").  
- Arch: PASS or PASS WITH NOTES (0 critical). Test-guardian: "suite protege adecuadamente" + re-runs golds exactos. Pool phrase verbatim at every close.

**GSD enforcement (non-negotiable):**  
Executor MUST prefix **every** modification, gate, verification, ruff, pytest, grep, smoke, self-check, or summary step with GSD log append (timestamp | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie de la letra from gamif integration + atomic gold + 1-line ports + Item10 + impact mapeo>) to `.planning/quick/gsd-33-test-reality-user-flows-store.log`. Use python -c for long/quoted safety. wc -l after. No edits (even to PLAN or log beyond appends) without pre-log. "Planner did INIT + pre-mkdir + pre-write."

---

## 1. Alcance preciso (In / Out explícito; ultra tight per mapeo + 0/0/0)

### En esta entrega (pool de <=4 items; tests-only; 0 prod/0 behavior/0 atomicity; protect golds 3 crit + contracts; source = impact mapeo):
- **Item 1 (core, highest value for "confianza de realidad del usuario"):** Store user purchase paths → handler-integration style.
  - New file: `tests/handlers/test_store_user_handlers_integration.py` (or targeted addition to existing if minimal; prefer new mirroring gamif _integration.py exactly).
  - Scope (from mapeo table + "Store user purchase paths"): TestDirectBuy (sufficient/insufficient + effective/discount paths; cap/tier exercised in pass paths), TestConfirmDirectBuy (purchase_and_complete success/error), TestProductDetail (context with effective_price/discount/tier/cap), TestPurchaseHistory (display orders). Full error branches for cap/tier protected in unit gold + atomic.
  - Pattern: `pytestmark = [pytest.mark.integration]`; `real_svc = StoreService(db_session)`; `with patch("handlers.store_user_handlers.StoreService") as MockStore: MockStore.return_value = real_svc`; call handler (direct_buy, confirm_direct_buy, product_detail, purchase_history); assert UI text 1:1 (Lucien strings preserved), DB side effects where purchase reaches complete (order COMPLETE, tx PURCHASE, balance delta via local Besito or guard).
  - Add 1-2 new tests: e.g. `test_store_user_purchase_success_integration` (real flow to complete_order → COMPLETE + PURCHASE tx), `test_store_user_purchase_insufficient_after_effective_discount` (effective price computed real, insufficient shows exact).
  - Reuse/extend fixtures from gold (sample_store_product + packages + categories + tiers + privileges + BesitoBalance with telegram_id = user.telegram_id).
  - 1-line/guard ports in any new integration test that inspects balance post-purchase (exact comment style).
  - UI 1:1: texts, emojis, buttons, callbacks unchanged (verify in asserts).
  - Re-runs golds post ports/edits.
  - 0 prod change.

- **Item 2:** Reduce spies/mocks internos en `tests/unit/test_store_service.py` para purchase paths.
  - Scope: In TestStoreService / TestStorePrivilegeDiscount / complete_order / direct_purchase related tests, where MagicMock of query or heavy patches of Fulfillment/Package exist for paths that can use real DB + fixtures, prefer real (sample products, real privileges, real tier gates via DB rows).
  - Keep the atomic gold `TestStorePurchaseAtomicGold` 100% intact (no logic change; only 1-line/guard ports if any access to .besito_service).
  - Document "external only" for patches that must remain (deliver_package_to_user is TG side, fire-and-forget best-effort).
  - Re-runs: atomic gold + cross + invariants.
  - 0 change to gold contract or DESIRED.

- **Item 3:** Agregar / extender tests de integración dedicados para complete_order / fulfillment paths + discount/tier/cap.
  - Basado en gold existente (TestSession/file, 777 ids, explicit models, try/finally, DESIRED CONTRACT docstring).
  - Cubrir: success (debit + stock + COMPLETE + side effects best-effort), insufficient (after effective), cap agotado (monthly_stock_cap), tier locked (REQUIRED_PREV_TIER_PURCHASES), descuento aplicado una sola vez (StorePrivilege consume).
  - If TestSession used: N806 tol + docstring; patch only external (PackageService.deliver) as gold does; verify post-commit best-effort via asserts on DB state (order COMPLETE, tx, balance) even if delivery mocked.
  - Seed optional STORE_PURCHASE mission for side-effect realism (best-effort, no assert on mission unless golden path).
  - Do not duplicate gold; extend or reference.
  - Re-runs cross_service_atomicity + invariants I8 + reaction_mission_flow (side effects).

- **Item 4 (opcional tight, or defer):** Small cluster for another high-impact user flow (e.g. promotion_user "me interesa" or backpack fulfillment callbacks) applying same pattern (reduce mocks, add 1 integration test). Or explicitly "dejar para próximo pool" if Items 1-3 close clean. Maintain ultra tight: only if 1-3 clean + user confirms. Do not expand scope mid-pool.

**Archivos que se modificarán / crearán (exactos; por orden de items/fases; 0 other):**
- `.planning/quick/gsd-33-test-reality-user-flows-store.log` (all GSD pre + wc + self-check + pool phrase).
- `tests/handlers/test_store_user_handlers_integration.py` (new; Item 1; integration tests for purchase paths using real StoreService + db_session + class patch + UI 1:1 + 1-line guards if balance inspect).
- `tests/unit/test_store_service.py` (Item 2; ports 1-line/guard where .besito_service accessed in purchase tests; reduce MagicMock for real fixtures in non-gold purchase tests; keep TestStorePurchaseAtomicGold verbatim).
- `tests/integration/test_store_purchase_integration.py` (new or extend existing; Item 3; dedicated E2E using TestSession/file for complete_order paths + discount/tier/cap; copy gold pattern + DESIRED + try/finally).
- (If Item 4 activated) one additional handler test file for chosen flow (minimal).
- `.planning/phases/33-test-reality-user-flows-store/` (PLAN.md + opt SUMMARY post + reports from arch/test-guardian/documentador).
- (Docs minimal if needed: decisions.md append for pool decision + tests reality hardening; services/CLAUDE.md note under store if cross impact; done at pool close via documentador, not manual mid-item).

**Fuera explícitamente (no scope creep):**
- **NO** prod code (handlers/store_user_handlers.py, services/store_service.py, fulfillment_service.py, etc. untouched except 0-line comments if any for clarity; 0 behavior).
- **NO** change to golds of 3 crit (cross_service_atomicity.py, reaction_*.py, test_invariants.py I1-I9, vip_*.py, daily atomic, story paths). Only re-run.
- **NO** other handler flows (promotion, story, mission user, backpack, gamif) unless Item 4 explicitly activated and tight.
- **NO** change to get_service impl, EventBus, atomicity contracts, locals pattern in prod (already done Item10; tests only port guards).
- **NO** new models / alembic.
- **NO** broad "refactor all mocks in store"; only purchase paths identified in mapeo.
- **NO** editing CLAUDEs/decisions/ROADMAP except targeted appends at end via documentador.
- **NO** touching callbackdata tests (packing only; correct as-is).
- **NO** mutation of contracts (1 service via get_service in prod handlers remains; tests patch the class to inject real instance).

**Comportamiento observable (tests only):** Existing prod flows identical. New/ported tests exercise real service paths for purchase (handler → real StoreService → local Besito(db=) on debit sites → DB commit for COMPLETE/PURCHASE tx → UI text reflects real state). Gold atomic protected. 0 user-visible change. 3 crit untouched.

---

## 2. Fases (strict order per item; gated; DoD + GSD pre every; copy precedents)

**Pool structure (max 4 items, sequential or batched per effort=4):**
- Item 1 (this PLAN primary): Store handler purchase paths to integration style.
- Item 2: Reduce mocks in test_store_service.py purchase paths.
- Item 3: Add/extend dedicated integration for complete_order/fulfillment + discount/tier/cap.
- Item 4: Optional small cluster or defer.

**Per-item phases (F1-Fx; 4-6 small; safe points; handoff after each item to arch-enforcer + test-guardian + (if last) documentador).**

### Item 1: Store handler purchase integration (F1-F6)

**F1 prep/GSD/baseline (Item 1)** (GSD pre; mkdir phase dir if needed; read this PLAN full + impact mapeo full + gamification_user_handlers_integration.py full + TestStorePurchaseAtomicGold full + 1-line examples in test_store_service.py + cross atomicity + store_user_handlers.py (TestDirectBuy/TestConfirmDirectBuy/TestProductDetail/TestPurchaseHistory) + store_service.py purchase methods (direct_purchase/create_order/complete_order/purchase_and_complete) + fixtures (sample_store_product, db_session, make_callback, make_user); baseline ruff on new integration test target + store unit; baseline targeted pytest with exact flags (-q --tb=line -p no:cov --override-ini="addopts="): gamif integration (model), store unit (atomic gold spot + complete_order + discount), cross atomicity spot, invariants I8 spot, broader -k "store or atomicity or mission or reaction"; greps for current mocks in store handlers (expect 252+ get_service), _mock_store_ctx helper, direct_buy/confirm paths; confirm fixtures (sample products with package + tiers + privileges + BesitoBalance telegram_id match); read precedents (28/27/26/25/24/23 PLANs + gsd + SUMMARIES for GSD style + self-check + pool + "Copia al pie" + "Instrucciones..."); confirm 3 crit golds list from mapeo; "F1 safe point". DoD marked. 0 edits to prod.

**F2 create integration test skeleton + port first path (direct_buy sufficient/insufficient) (Item 1)** (GSD pre each edit; create tests/handlers/test_store_user_handlers_integration.py with pytestmark + docstring mirroring gamif; import real StoreService + patch + models for fixtures; add class TestDirectBuyIntegration with 2-3 tests using real_svc = StoreService(db_session); patch class; call direct_buy; assert UI 1:1 + answer calls; use real product + balance fixtures; add 1-line guard if inspecting balance post; ruff; targeted pytest on new file + spot store unit; grep for patch("handlers.store_user_handlers.StoreService") + real service usage; "F2 safe point". DoD marked. UI 1:1 verified.

**F3 port confirm_direct_buy + product_detail paths (Item 1)** (GSD pre; extend integration test with TestConfirmDirectBuyIntegration (success path reaching purchase_and_complete → COMPLETE + tx PURCHASE verifiable via DB re-query or guard balance) + TestProductDetailIntegration (real get_product_detail_context or via handler with effective_price/discount/tier/cap using real rows); 1-2 new tests per mapeo "test_store_user_purchase_success_integration" and "insufficient after effective"; use TestSession/file pattern if complete_order commit visibility requires (N806 + doc); patch only external if needed (PackageService.deliver as gold); ruff; pytest new + re-run atomic gold + cross spot; grep ports + no prod touch; "F3 safe point". DoD marked.

**F4 port purchase_history + 1-line guards + full file hygiene (Item 1)** (GSD pre; add TestPurchaseHistoryIntegration (real orders in DB → real service → UI shows id/price/status 1:1); ensure any balance inspect uses exact 1-line/guard with comment; ruff + format; full pytest on integration file; re-runs golds per mapeo (cross full, atomic gold, invariants, reaction_mission, daily, vip); broader -k "store or atomicity"; greps (patch class, real service, 1-line comments, UI strings preserved); "F4 safe point". DoD marked.

**F5 gates + re-runs + rules verif (Item 1)** (GSD pre every; ruff on touched (new integration + any ports in unit); re-execute exact golds list from mapeo + PLAN; bot smoke (import handlers); grep 0 prod changes (handlers/store_user_handlers.py untouched); LOC if any helpers extracted (unlikely; tests); rules verif (GSD pre every + wc, scope tight per Item 1 files + log + PLAN, 3 crit protected via re-runs, UI 1:1, 1 service via get_service in prod unchanged, integration follows precedent gamif exactly, 1-line ports present with comment); "F5 safe point". DoD marked.

**F6 self-check PASSED + handoff (Item 1)** (GSD pre; append full self-check structure to log + opt SUMMARY.md mirroring 28/27; include verbatim "Item 1/33 closed. First of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. ... Ready for arch-enforcer re-scan (enfocado en store handler integration tests + 1-line ports + 0 impact on 3 crit) + test-guardian (correr golds listados) + documentador (update ROADMAP + learnings) + gsd-executor del siguiente item del pool (Item 2)"; launch arch-enforcer + test-guardian per hardener seq if orchestrated; explicit next: Item 2 PLAN or continue in same pool). Self-check PASSED. Pool phrase.

### Item 2 phases (F1-F4 tight; after Item 1 closed + guardians)
(Brief: F1 prep read mapeo + gold + ports precedent; F2 reduce MagicMock in non-gold purchase tests + add 1-line guards if needed; F3 ruff/pytest atomic gold + cross + invariants; F4 self-check + handoff to Item 3 or documentador if pool ends.)

### Item 3 phases (F1-F4)
(Brief: F1 prep gold atomic + cross; F2 add/extend test_store_purchase_integration.py with TestSession E2E for complete_order paths + tier/discount/cap; F3 re-runs full golds + side effect chains; F4 self-check + pool close if last.)

### Item 4 (if activated)
Tight 2-3 phases; defer otherwise with explicit note in F6 Item 3.

---

## 3. Copia patrones **al pie de la letra**

- **Handler integration style (gamif precedent):** pytestmark=integration; real service instance injected via class patch on the handler module's StoreService; full flow handler → real svc → DB → edit_text/answer with exact UI text; no MagicMock returns for product/balance/effective_price; fixtures real (products + packages + balance with telegram_id match).
- **Atomic gold (TestStorePurchaseAtomicGold):** TestSession/file + N806 tol + doc; 777 TG ids; explicit User/Balance/Package/Product models; try/finally reopen/re-query; "credit survives deliver False"; "post-credit best effort (misiones + listeners)"; patch PackageService.deliver only (external); DESIRED CONTRACT in docstring; strict asserts on tx PURCHASE / balance delta / order COMPLETE / stock.
- **1-line/guard ports (Item10/28 + daily/cross):** exact pattern `if not hasattr(svc, "besito_service") else svc.besito_service...` or `BesitoService(db=...) if not hasattr...`; comment "# 1-line/guard port post Item10 local (copy daily precedent in cross; arch-enforcer); was service.besito_service"; applied in tests that would otherwise break on local removal (already in prod via Item10).
- **GSD pre + wc + detailed entry:** timestamp | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie de la letra (gamif integration + atomic gold + 1-line + mapeo + pool phrase)>; pre every; wc after; planner pre + executor.
- **Self-check structure + pool phrase + handoff:** full at final phase per section 6 + precedents; verbatim pool phrase; "Nth of new pool of 4"; explicit arch-enforcer re-scan (focus) + test-guardian (golds) + documentador (ROADMAP/learnings) + next executor.
- **Arch + test-guardian verdicts:** arch "PASS" or "PASS WITH NOTES (0 critical)"; test-guardian "suite protege adecuadamente" + re-runs of listed golds.
- **Documentador at pool close:** after last item's tests green + self-check; updates HARDENING_ROADMAP + extracts learnings + persists report; GSD pre for its log; source of truth = PLAN + gsd + impact + SUMMARYs + test changes.
- **UI 1:1 + Lucien voice:** in integration tests, assert exact strings from prod (e.g. "adquisición", "Moneda especial insuficiente", cap/tier messages) preserved; no change to voice.
- **3 crit + contracts + logging + GSD in every section:** explicit.

---

## 4. Instrucciones para gsd-executor

1. **Read first (MANDATORY, before any edit/gate):** This PLAN.md (full) + `.grok/agent-memory/impact-analyzer/33-test-reality-user-flows-mapeo.md` (full) + precedents: `tests/handlers/test_gamification_user_handlers_integration.py` (full), `tests/unit/test_store_service.py` (TestStorePurchaseAtomicGold + 1-line ports around 210/420 + discount tests), `tests/integration/test_cross_service_atomicity.py` (1-line ports + DESIRED + TestSession + patch schedule_emit + "credit survives" + "post-credit best effort"), gamif integration + store unit + cross + invariants + reaction_mission + daily + vip golds, recent PLANs (29/28/27/26) + their gsd logs + SUMMARIES for GSD style/self-check/pool/handoff/"Copia al pie"/"Instrucciones...", HARDENING_ROADMAP (recent), decisions.md tail, services/CLAUDE.md store section, handlers/store_user_handlers.py (purchase paths), store_service.py (direct_purchase/create_order/complete_order/purchase_and_complete + local Besito sites post Item10), fixtures conftest, current test_store_user_handlers.py (mock counts + classes). Confirm 0 prod intent. Confirm golds list matches mapeo.

2. **GSD pre-log discipline (total):** BEFORE every modification (write/search_replace on test files/PLAN/log/SUMMARY), gate (ruff/pytest/grep/smoke/LOC/self-check), verif: append "=== $(date -Iseconds) | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie de la letra (gamif integration + atomic gold + 1-line ports + Item10 + mapeo + 3 crit protected)>" >> `.planning/quick/gsd-33-test-reality-user-flows-store.log` (python -c for safety on long); wc -l after. Track 5-10+ per phase. No exceptions. "No edits without pre-log."

3. **Tight scope (0 creep):** Only files listed in "Archivos que se modificarán" for the active Item (Item 1 primary: new integration test + ports in unit if any + log + PLAN + opt SUMMARY). 0 prod code. 0 golds of 3 crit (re-run only). If Item 4 activated, add 1 minimal file only after 1-3 clean. Re-verify 3 crit via golds re-runs + greps (0 new writes in gamif/narr/channel paths).

4. **Copy al pie de la letra (every phase):** Gamif integration pattern (class patch return real, full flow verify, pytestmark); atomic gold (TestSession, 777, try/finally, DESIRED, survives, post-credit, patch external only); 1-line/guard with exact comment; GSD pre + wc + detailed; self-check + pool phrase + handoff; UI 1:1 asserts; 3 crit + contracts cited.

5. **Phases strict (per item, gated, safe points, DoD before advance):** Follow F1-F6 (Item 1) order; mark DoD in GSD at end of each (e.g. "F2 gates complete + safe point: ruff limpio; grep patch class + real service; pytest spot green; UI 1:1; 1-line guard present; F2 safe point - direct_buy paths integration; ready for F3. DoD all marked."). "F<N> safe point" log. Revertable (delete new test file = clean; ports are additive guards only).

6. **Re-verify 3 crit + contracts + rules (every item end):** Re-run golds (cross_service_atomicity full w/ patch+DESIRED+TestSession+strict+"credit survives deliver False"+"post-credit best effort (misiones + listeners)"+N806+777+gather+try/finally; free_entry; scheduler/event_bus/channel/vip/daily/story units; reaction_*; invariants I8; broader -k "store or atomicity or mission or reaction or daily or vip"; store handler unit + admin; new integration; atomic gold full). Greps: 0 writes in crit paths from our test files; patch class present; real service usage; 1-line comments; UI strings 1:1; "Item 1/33" refs. Ruff clean. Rules: GSD pre every (wc), scope tight, 3 crit protected (re-runs + greps), get_service 1 call in prod unchanged (grep confirm), integration follows precedent, no prod change.

7. **Gates/commands (exact):** `./venv/bin/python -m ruff check ... --fix && ./venv/bin/python -m ruff format --check ...`; `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "..."` (exact lists from mapeo + PLAN); bot smoke `python -c "import handlers.store_user_handlers; print('import ok')" ` (or venv); greps `-n -c -A`; GSD pre before each. Re-runs after any port/edit.

8. **Documentador at pool close (after last item):** spawn_subagent or explicit launch with rich prompt: "For pool 33-test-reality-user-flows-store close (Item N/33): update HARDENING_ROADMAP.md (append completed work + metrics + pool/BATCH notes + verbatim pool phrase); persist tirón report in .grok/agent-memory/documentador/ + MEMORY.md; source of truth: this PLAN + gsd log + impact mapeo + test changes + (opt) SUMMARIES; follow GSD pre for your log; include pool phrase + handoff; no manual code edits outside report."

9. **Self-check at each item close + pool close (full in log + opt SUMMARY):** phases/DoD/gates/archivos/tests passed/reglas verificadas (GSD pre every, scope tight per PLAN, 3 crit + contracts protected via re-runs/greps, precedents copied al pie, UI 1:1, 0 prod/0 behavior/0 atomicity)/desviaciones (pre only, doc non-reg)/tests críticos para futuro (exact golds list from mapeo)/"Item 1/33 closed. First of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. ... Ready for arch-enforcer re-scan (enfocado en store handler integration + service unit mocks + 1-line ports + 0 impact on 3 crit) + test-guardian (correr golds listados) + documentador (update ROADMAP + learnings) + gsd-executor del siguiente item del pool."

10. **Risks/mit (conservative, from mapeo):** DetachedInstance post-commit (mit: use TestSession/file for paths exercising complete_order as gold does); fulfillment mocks (mit: patch external only as gold; assert DB state only); mission side effects (mit: best-effort, seed optional, no hard assert unless golden); churn in mocks (mit: UI 1:1 + keep unit mocks as-is for non-purchase; new integration additive); 1-line ports (mit: copy exact + comment; re-run golds after); N806 (mit: tol + doc as precedent). Safe points: delete new test = clean; revert guards (no behavior change in prod).

11. **Output per phase:** Brief report in GSD (what + gates + safe point + DoD); full self-check + pool phrase at item/pool close. (opt) SUMMARY post mirroring 28/27.

12. **0 prod intent / verification:** Hardening/tests-only. All verif via re-runs/greps/smokes/self-check. Handoff explicit.

---

## 5. Riesgos / Mitigaciones + Safe Points + DoD

**Riesgos + Mitigaciones (per mapeo):**
- DetachedInstance / visibility post complete_order commit (mit: TestSession/file pattern from gold; close/reopen before re-query).
- Fulfillment (PackageService.deliver) may fail or require real TG in real run (mit: patch external only as gold; verify DB atomic phase only).
- Mission side effects (STORE_PURCHASE) best-effort (mit: seed mission for realism if needed; swallow errors; no hard assert on side unless golden path).
- Churn / large diff in test_store_user_handlers.py (mit: do not edit the unit file for Item 1; create additive integration; UI 1:1 asserts; arch will see 0 prod).
- 1-line ports needed in multiple sites (mit: copy exact pattern + comment; re-run golds post each).
- N806 in TestSession (mit: precedent tol + docstring "N806 tolerated per atomic gold / reaction patterns").
- Pre-exist flakes in broader (mit: document non-attributable; focus 0 attributable to our changes).
- Handler test mock wiring (aiogram decorators) (mit: if integration uses make_callback fixtures, they are already used in gamif integration; verify contract in smoke).

**Safe points (revertable 0 residual):**
- Delete new integration test file(s) = clean (no prod impact).
- Revert any 1-line guard in unit tests (no prod change; guards are test-only).
- Item 4 not activated = no extra scope.

**DoD (per item + final; copy 28/27 style):**
- All phases GSD pre-logs (counts 5-10+/fase + wc), self-check "PASSED" with full structure + critical tests list + pool phrase + "0 behavior/0 atomicity/0 risk to 3 systems" + "Item 1/33 closed. First of new pool..." + handoff.
- Integration tests exist for key purchase paths (direct_buy, confirm, product_detail, history); use real StoreService + db_session + class patch; full flow verified (handler → real svc → DB → UI 1:1).
- 1-line/guard ports present where balance inspected post-purchase; exact comment.
- Atomic gold untouched (or only guard ports); all listed golds re-run green 0 attributable.
- Ruff limpio on touched; greps confirm patch class, real service, UI strings, 0 prod changes.
- Rules: GSD pre every, scope tight (listed files + log + PLAN + opt SUMMARY + 0 other), 3 crit + contracts protected, get_service 1 call in prod unchanged, integration follows gamif precedent, UI 1:1, documentador used at pool close.
- Handoff: explicit to arch-enforcer (focus on integration style + ports + 0 impact) + test-guardian (golds) + documentador + next item executor.

---

## 6. Self-check (planner, after all exploration + reads + GSD pre + write)

**PASSED**

- All exploration + reads done (impact mapeo full via read_file; gamif integration full; TestStorePurchaseAtomicGold + 1-line ports + discount tests in store_service unit; cross atomicity ports + DESIRED + TestSession; store_user_handlers purchase classes; store_service purchase methods; recent PLANs 29/28/27 + gsd + SUMMARIES; golds list from mapeo; GSD pre logged before this write + prior).
- Scope respected (tight In/Out explicit; 0 prod/0 behavior/0 atomicity/0 other critical flows; 3 crit + contracts + GSD + pool phrase + documentador integration cited in every relevant section: Alcance, Fases, Copia, Instrucciones, Risks, Self-check).
- PLAN complete/actionable + mirrors precedents exactly (title with Item 1/33 + "first of new pool of 4" + pool phrase; Input principal = mapeo; GSD enforcement; Alcance with exact files + patterns from impact + In/Out; Archivos/Fuera; phases F1-F6 per item with gates/DoD/safe/copy al pie; Copia patrones (gamif integration + atomic gold + 1-line + GSD + self-check + pool + handoff + documentador + UI 1:1 + 3 crit); Instrucciones para gsd-executor (read first + GSD pre every + tight + copy al pie + phases strict + re-verify 3 crit + gates exact + documentador + self-check full + risks); Risks + safe + DoD; Self-check + handoff with verbatim pool + "Item 1/33 closed. First... Ready for arch-enforcer re-scan (enfocado en store handler integration + service unit mocks + 1-line ports + 0 impact on 3 crit) + test-guardian (correr golds listados) + documentador (update ROADMAP + learnings) + gsd-executor del siguiente item del pool"; commands with exact flags; 3 crit + contracts protected).
- Verbatim pool language repeated: "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."
- Golds list (from mapeo, to re-run in every item): store atomic gold (TestStorePurchaseAtomicGold + complete_order), cross_service_atomicity, invariants I8, reaction_full_chain + reaction_mission_flow + reaction_limit, daily atomic, vip flows (test_vip_flow + test_vip_flows + test_vip_complete_cycle), broader -k "store or atomicity or mission or reaction or daily or vip".
- 0 scope creep. Follows user desire (mapear flujos importantes → tienda prioridad → reducir mocks → integration style). Strict: no edits outside GSD (planner pre-log before write); documentador for docs at close.

**Pool phrase (verbatim, repeated in PLAN + will be in self-check/F6 log/SUMMARY):** "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

**Item 1/33 closed (in F6 handoff after executor + arch + testg + documentador if pool item).** PLAN ready for gsd-executor (store test reality hardening, first of new pool of 4).

Self-check (planner): PASSED (all exploration + reads done, scope respected, 3 systems + rules + GSD + pool phrase + documentador integration cited in every relevant section; PLAN complete/actionable + mirrors precedents exactly).

---

**End of PLAN.** (GSD pre-write logged; wc tracked; ready for gsd-executor. Source: impact mapeo 100%.)