# Arch-Enforcer Audit Report: Item 32 — Store Admin Wizard UX (Fase 2: inline tariff/story selection + edit VIP/STORY_UNLOCK)

**Date:** 2026-06-21  
**Auditor:** arch-enforcer  
**Task:** Audit Fase 2 Store Admin Wizard UX implementation per PLAN `.planning/phases/32-store-admin-wizard-ux/PLAN.md` + SUMMARY `.planning/phases/32-store-admin-wizard-ux/32-store-admin-wizard-ux-SUMMARY.md`.  
**Scope (5 files):** `keyboards/callback_data.py`, `utils/lucien_voice.py`, `services/store_service.py`, `handlers/store_admin_handlers.py`, `tests/handlers/test_store_admin_handlers.py` (tests reviewed via green gates; handler/svc/callback/voice primary).

**Reference rules:** CLAUDE.md (root + handlers/), architecture.md, rules.md, handlers/CLAUDE.md hardener pattern (item8/26 gold), PLAN §3 contracts + self-check §6.

---

## Methodology

- Read PLAN + SUMMARY + changed source files (full handler scan; svc delegates; callback_data; lucien_voice wizard section).
- Grep: `VIPService|StoryService` in handler (expect 0); `waiting_tariff_id|wizard_process_tariff_id` (expect 0); 4 CallbackData prefixes; 4 delegates in store_service.
- LOC: `inspect.getsourcelines` on new/modified funcs in handler + delegates.
- Pytest gates from PLAN §7:
  - `tests/handlers/test_store_admin_handlers.py` → **72 passed**
  - Gold: `complete_order or atomic` (19), `test_cross_service_atomicity` (10), `fulfillment vip_grant|story_unlock` (6), `test_vip_flow` (8) → **43 passed**
- Verify `complete_order` / `create_product` / `update_product` contracts unchanged (read-only audit of bodies; delegates appended only).

---

## Findings (Classified)

### Critical (Architecture-breaking) — **0 found**

| Rule | Result |
|------|--------|
| Handlers: exactly 1× `get_service(StoreService)` per entrypoint | ✅ New entrypoints (`wizard_select_tariff`, `wizard_select_story_node`, `process_edit_product_tariff`, `process_edit_product_story_node`, `_wizard_prompt_tariff_selection`, `_wizard_prompt_story_node_selection`, `edit_product_field_start`) each have **one** `with get_service(StoreService)` block |
| No `VIPService` / `StoryService` direct in handlers | ✅ `grep VIPService\|StoryService handlers/store_admin_handlers.py` → **0 matches** |
| No DB in handlers | ✅ No `SessionLocal`, `db.query`, or `models.database` imports |
| Funcs ≤50 LOC (new/changed) | ⚠️ See Medium #1 — one modified entrypoint exceeds 50 LOC; **not** layer-breaking |
| Logging format on important actions | ⚠️ See Medium #2 — new paths lack logs; existing `confirm_create_product` / `list_products` retain standard format |
| 0 impact on 3 critical systems | ✅ Admin UX + read-only delegates only; purchase/fulfillment/VIP activation paths untouched |

**Layer compliance:** Handlers route FSM + inline keyboards → `StoreService` thin delegates → on-demand `VIPService`/`StoryService` **inside service only** (mirror `get_packages_for_product_edit` gold). No business logic in handlers beyond FSM routing and pure UI builders. No duplication across domains at handler layer.

**Contracts preserved:**
- `create_product` / `update_product` validation for `tariff_id` / `story_node_id` by kind — unchanged
- `complete_order` (lines 986–1061) — **no edits** in this phase
- `fulfillment_service.py`, `store_user_handlers.py`, `vip_handlers.py` — out of scope, untouched per PLAN

---

### Medium (Maintenance / Pre-existing / Non-blocking) — **4 findings**

1. **`edit_product_field_start` = 71 LOC (>50 rule)**  
   - Fase 2 added `tariff` / `story_node` branches (~24 lines) to an existing multi-field router without extracting (e.g. `_route_edit_field_tariff(...)` pure/helper).  
   - Pre-Fase-2 estimate ~47 LOC (71 − tariff/story block). Regression introduced by **this** item, but orthogonal to layers/atomicity.  
   - **Recommendation:** Future quick — extract tariff/story branches to helper(s) to restore ≤50 (item8/9 precedent).

2. **Logging on new wizard/edit callbacks**  
   - `wizard_select_tariff`, `wizard_select_story_node`, `process_edit_product_tariff`, `process_edit_product_story_node` have **no** `logger.info("store_admin_handlers | ...")`.  
   - Matches item9 precedent (min logging on main paths only). Not a layer violation.

3. **Redundant read in `wizard_select_tariff` / `wizard_select_story_node`**  
   - Callback handlers re-call `get_tariffs_for_product_wizard()` / `get_story_nodes_for_product_wizard()` to resolve display names. PLAN allowed storing name from button label; still **1× get_service per entrypoint** (arch OK, minor inefficiency).

4. **Pre-existing handler string debt (not introduced by Fase 2)**  
   - Examples: `"No hay paquetes disponibles"` (L1389), `_finish_product_edit` hardcoded Lucien lines, package-create wizard HTML block.  
   - Fase 2 **new** user-facing strings correctly use LucienVoice (`select_tariff`, `no_tariffs`, `no_story_nodes`, confirmation summary).  
   - Removed deprecated `invalid_tariff_id` / `invalid_story_node_id` — grep **0 references**.

---

### Observations (Good adherence)

- **4 CallbackData** with exact prefixes: `wiz_store_tariff`, `wiz_store_story`, `sel_tariff_edit`, `sel_story_edit`; `EditProductFieldCallback.field` doc extended with `tariff | story_node`.
- **4 StoreService delegates** (7–17 LOC each): on-demand `VIPService(self._get_db())` / `StoryService(self._get_db())`; edit delegates prepend inactive current entity (mirror packages gold).
- **FSM:** `selecting_tariff` / `selecting_story_node` in wizard + edit; removed `waiting_tariff_id` / `waiting_story_node_id` and text handlers — grep **0**.
- **Pure helpers** (all ≤32 LOC): `build_wizard_tariff_keyboard`, `build_wizard_story_node_keyboard`, `build_edit_tariff_buttons`, `build_edit_story_node_buttons`; extended `build_product_edit_menu_*`, `build_product_confirmation_text_and_keyboard`.
- **LucienVoice:** `fulfillment_admin_wizard_select_tariff` / `_select_story_node`, empty states, confirmation `tariff_name` / `story_node_title` kwargs.
- **Tests:** 72 handler tests green; 43 gold regression tests green (SUMMARY aligned).
- **Gold pattern fidelity:** `_wizard_prompt_tariff_selection` copies `_wizard_prompt_package_selection` structure (empty → LucienVoice + back + `state.clear()` on empty tariffs).

**Minor PLAN deviation (info):** Story button label uses `node.title` only; PLAN suggested `internal_name` fallback if title empty — low risk if titles always set in admin data.

---

## Impact on 3 Critical Systems

| System | Impact |
|--------|--------|
| **Gamification (besitos — credit/debit/atomicity)** | **0.** No changes to `complete_order`, `BesitoService` debit sites, reactions, daily gift, or mission rewards. Admin product CRUD only. Gold atomicity 19+10 tests green. |
| **Narrative (story visitor FSM / progress / quiz)** | **0.** `StoryService` used read-only via `StoreService` delegates for admin lists only. No `story_user_handlers` / progress mutation. |
| **Channels / VIP (activation, tokens, pending requests)** | **0.** `VIPService` read-only for tariff lists; no token generation, subscription activation, or channel grant paths. `test_vip_flow` 8 passed. |

Fulfillment post-commit (`fulfillment_service` VIP_GRANT / STORY_UNLOCK) — **unchanged**; product wizard only sets `tariff_id` / `story_node_id` on `StoreProduct` (same contract as before).

---

## Compliance Checklist

| Criterion | Status |
|-----------|--------|
| handlers → services → models | ✅ |
| 1× `get_service(StoreService)` per new entrypoint | ✅ |
| 0 VIP/Story in handlers | ✅ |
| 0 DB in handlers | ✅ |
| Thin delegates in StoreService | ✅ |
| CallbackData namespaced (no collision with `select_tariff`) | ✅ |
| User-facing strings in LucienVoice (Fase 2 additions) | ✅ |
| `complete_order` / purchase atomicity untouched | ✅ |
| Handler tests + gold regression | ✅ 72 + 43 |
| All **new** functions ≤50 LOC | ✅ (puros + prompts + edit callbacks) |
| All **modified** entrypoints ≤50 LOC | ❌ `edit_product_field_start` 71 |

---

## Verdict

### **PASS WITH NOTES**

**Critical violations: 0** (target met).

**Summary:** Fase 2 correctly implements admin-only inline tariff/story UX following item8 gold (package selection + edit delegates + pure keyboards). Architecture boundaries are respected: handlers never import VIP/Story; read-only cross-domain access is encapsulated in `StoreService`; purchase/fulfillment/VIP activation critical paths show no regression in gold suites.

**Notes (non-blocking):**
1. Extract tariff/story branches from `edit_product_field_start` to restore ≤50 LOC.
2. Optional: log wizard/edit tariff selections; avoid redundant list fetch for name resolution.
3. Pre-existing hardcoded strings in handler remain out of scope for this item.

**Handoff:** Ready for **test-guardian** (confirm "suite protege adecuadamente" + re-run golds). Item 32 Fase 2 arch gate **PASSED**.

---

**References:**  
- `.planning/phases/32-store-admin-wizard-ux/PLAN.md`  
- `.planning/phases/32-store-admin-wizard-ux/32-store-admin-wizard-ux-SUMMARY.md`  
- `.planning/quick/gsd-store-admin-wizard-ux.log` (executor self-check PASSED)  
- Precedent: item8/26 store-admin-long-funcs, item9-arch-audit (PASS WITH NOTES + 0 critical template)

**End of audit.**