# Test-Guardian Report: 33-item1 (pool 33-test-reality-user-flows-store)

**Item:** 1 / first of new pool of 4  
**Verdict:** suite protege adecuadamente  
**Date:** 2026-06-26  
**Guardian:** test-guardian (following hardener-agile + PLAN al pie)  
**Scope:** Audit new integration test `tests/handlers/test_store_user_handlers_integration.py` (8 tests) + verify golds + coverage reality + no regression on 3 crit.

---

## Exact Commands Run + Output Summary

All runs used project flags: `-q --tb=line -p no:cov --override-ini="addopts="`

Using `./venv/bin/python -m pytest` per PLAN.

### 1. New integration test (baseline)
```bash
./venv/bin/python -m pytest tests/handlers/test_store_user_handlers_integration.py -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 8 passed, 1 warning (MovedIn20, pre-exist)

### 2. Store atomic gold
```bash
./venv/bin/python -m pytest tests/unit/test_store_service.py -k "TestStorePurchaseAtomicGold or complete_order" -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 25 passed, 30 deselected, 1 warning

### 3. Cross service atomicity (full)
```bash
./venv/bin/python -m pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 10 passed, 1 warning

### 4. Invariants (I8 + others)
```bash
./venv/bin/python -m pytest tests/integration/test_invariants.py -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 11 passed, 6 warnings (pre-exist RuntimeWarning + SAWarning)

### 5. Reaction chains
```bash
./venv/bin/python -m pytest tests/integration/test_reaction_full_chain.py tests/integration/test_reaction_mission_flow.py tests/integration/test_reaction_limit.py -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 9 passed, 4 warnings

### 6. Daily atomic
```bash
./venv/bin/python -m pytest tests/unit/test_daily_gift_service.py -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 19 passed, 2 warnings

### 7. VIP flows
```bash
./venv/bin/python -m pytest tests/integration/test_vip_flow.py tests/integration/test_vip_flows.py tests/integration/test_vip_complete_cycle.py -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 37 passed, 26 warnings (pre-exist; includes PytestReturnNotNoneWarning on vip_complete_cycle which is pre-existing)

### 8. Broader smoke (exact from PLAN/mapeo)
```bash
./venv/bin/python -m pytest -k "store or atomicity or mission or reaction or daily or vip" -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 778 passed, 930 deselected, 8 xfailed, 57 warnings

**All xfailed/warnings documented as pre-existing (non-attributable to Item 1) per SUMMARY F5.**

---

## Coverage Added (Purchase Paths Now Real vs Previous Isolation)

### Previous State (per impact mapeo)
- `test_store_user_handlers.py`: 1873 LOC, 252 get_service patches, ~380 total mocks
- `_mock_store_ctx` helper that returns MagicMock for ALL service methods
- Pure isolation: product, balance, effective_price, tier gates, monthly_cap — ALL mocked
- Bug in `get_product_detail_context`, `_apply_discount`, `complete_order` debit, or fulfillment dispatch would NOT be detected

### New State (Item 1 additive integration tests)
New file: `tests/handlers/test_store_user_handlers_integration.py` (8 tests)

| Test | Path Exercised | Real vs Mock | DB State Verified |
|------|----------------|--------------|-------------------|
| `test_direct_buy_sufficient_balance_shows_confirm` | direct_buy → get_product, get_shop_balance_display, get_effective_price → UI confirm | Real StoreService(db_session) | N/A (pre-purchase) |
| `test_direct_buy_insufficient_balance_alerts` | direct_buy → balance < effective → alert | Real StoreService | N/A |
| `test_confirm_direct_buy_success_persists_complete_and_purchase_tx` | confirm → purchase_and_complete → direct_purchase + complete_order (atomic: debit commit=False, stock, COMPLETE, db.commit) → post-commit best-effort | Real StoreService + TestSession/file + expire_on_commit=False | ✅ Order COMPLETE, ✅ tx PURCHASE amount=-150, ✅ balance delta via 1-line/guard |
| `test_confirm_direct_buy_insufficient_after_effective_discount` | confirm → effective after 50% discount > balance → error, NO order | Real StoreService + privilege seed chain | ✅ No order created |
| `test_product_detail_shows_effective_price_with_active_discount` | product_detail → get_product_detail_context (via real service) with 25% discount | Real StoreService + privilege chain | N/A (read path) |
| `test_store_user_purchase_success_integration` | confirm → purchase_and_complete → COMPLETE + PURCHASE tx + delta (77 besitos) | Real StoreService + TestSession/file | ✅ Order COMPLETE, ✅ tx PURCHASE -77, ✅ balance 200→123 via 1-line/guard |
| `test_store_user_purchase_insufficient_after_effective_discount` | confirm → effective 50% > balance → error | Real StoreService + privilege | ✅ No order |
| `test_purchase_history_shows_real_orders` | purchase_history → get_user_orders (real) → UI shows header/item | Real StoreService | Pre-seeded real order in DB |

### Key Real Paths Now Covered (Previously Pure Mock)
1. **direct_buy**: `get_product`, `_check_monthly_cap_for_product`, `check_tier_purchase_gate`, `get_shop_balance_display`, `get_effective_price` — all real
2. **confirm_direct_buy → purchase_and_complete**: `direct_purchase` (tier gate, cap, stock, balance check, order create) + `complete_order` (debit local Besito commit=False, stock decrement, COMPLETE, commit) + post side effects (patched external only)
3. **product_detail**: `get_product_detail_context` with active discount privilege → effective price computation
4. **purchase_history**: `get_user_orders` returning real Order rows

### 1-Line/Guard Ports + TestSession Pattern Confirmed
- Exact comment: `# 1-line/guard port post Item10 (copy daily precedent in cross; arch-enforcer)`
- Pattern: `BesitoService(db=db).get_balance(tg) if not hasattr(real_svc, "besito_service") else real_svc.besito_service.get_balance(tg)`
- TestSession/file + `N806` tol + `expire_on_commit=False` for complete_order visibility (copy atomic gold)
- Patch ONLY external: `patch("services.fulfillment_service.PackageService")` for deliver (fire-and-forget)

---

## Golds Status (List + Pass/Fail Counts)

| Gold | Command | Result | Notes |
|------|---------|--------|-------|
| Store atomic gold (TestStorePurchaseAtomicGold + complete_order) | `-k "TestStorePurchaseAtomicGold or complete_order"` on test_store_service.py | ✅ 25 passed | DESIRED CONTRACT protected; "credit survives deliver False"; "post-credit best effort" |
| Cross service atomicity (full) | test_cross_service_atomicity.py | ✅ 10 passed | Includes store purchase side-effect path (mission) + 1-line/guard for local besito |
| Invariants (I8) | test_invariants.py | ✅ 11 passed | Order status COMPLETE irreversible |
| Reaction full chain | test_reaction_full_chain.py | ✅ (part of 9) | Gamif crit #1 |
| Reaction mission flow | test_reaction_mission_flow.py | ✅ (part of 9) | Side effects exercised |
| Reaction limit | test_reaction_limit.py | ✅ (part of 9) | |
| Daily atomic | test_daily_gift_service.py | ✅ 19 passed | Gamif crit #1 |
| VIP flows (test_vip_flow + test_vip_flows + test_vip_complete_cycle) | 3 vip files | ✅ 37 passed | Canales-VIP crit #3 |
| Broader smoke | `-k "store or atomicity or mission or reaction or daily or vip"` | ✅ 778 passed, 8 xfailed | 8 xfailed pre-existing (non-attributable) |

**Total attributable regressions to Item 1: 0**

---

## Risks to Contracts

**None.**

- Atomicity contract: protected by gold re-runs (TestStorePurchaseAtomicGold + cross + "credit survives deliver False" + "post-credit best effort" + TestSession + N806 + 777 + try/finally patterns untouched)
- EventBus contract: best-effort, fire-and-forget; no mutation in new tests; schedule_emit patch in cross gold preserved
- get_service contract: prod handlers unchanged (1 get_service(StoreService) per entrypoint); tests patch class to inject real (per gamif precedent + PLAN)
- 3 crit systems: gamif (golds green), narrativa (not touched; not in scope), canales-VIP (golds green)
- No writes to crit paths (gamif/narr/channel); only additive test file + hygiene in store unit (1-line ports already in gold)

---

## Positive: New Tests Protect User Purchase Reality

1. **Debit is real**: `complete_order` calls local `BesitoService(db=...).debit_besitos(..., commit=False)` → tx PURCHASE created → balance delta verified
2. **COMPLETE is real**: `order.status == OrderStatus.COMPLETED` + `completed_at` set in same atomic commit
3. **Discounts are real**: `get_effective_price` + `_apply_discount_to_order_total` exercised with seeded StorePrivilege (25%/50%); effective price gates purchase
4. **Insufficient after effective is real**: balance exactly at effective-1 → error, NO order created, NO tx
5. **History is real**: `get_user_orders` returns real Order rows → UI shows id/price/status
6. **Direct buy pre-purchase is real**: tier gate, cap, stock, effective price all computed from DB rows
7. **Post-commit is best-effort**: PackageService.deliver patched (external only); DB state (COMPLETE + tx + balance) asserted regardless of delivery

This directly addresses the user's concern (per mapeo): "en los flujos del usuario por ejemplo en la tienda es muy importante y el hecho de que haya tanto mock me parece una mala práctica"

---

## Precedent Verification: Follows Gamif Exactly

| Aspect | Gamif Precedent | New Integration Test | Match |
|--------|-----------------|----------------------|-------|
| pytestmark | `[pytest.mark.integration]` | `[pytest.mark.integration]` | ✅ |
| Real service | `real_service = BesitoService(db_session)` | `real_svc = StoreService(db_session)` or `db=` | ✅ |
| Class patch | `patch("handlers.gamification_user_handlers.BesitoService")` | `patch("handlers.store_user_handlers.StoreService")` | ✅ |
| Inject pattern | `mock.return_value = real_service` | `mock_store_cls.return_value = real_svc` | ✅ |
| Call handler | `await show_balance(cb)` | `await direct_buy(cb, callback_data=...)` | ✅ |
| UI 1:1 | `edit_text.assert_called_once(); "1000" in text` | `edit_text.assert_called(); price in text or "confirma" in ...` | ✅ |
| DB verify | `db_session.query(DailyGiftClaim)...` | `db.query(Order).filter(...COMPLETE).first()` | ✅ |
| 1-line/guard | (cross/daily have) | Exact comment + pattern for balance post | ✅ |
| TestSession | (cross/atomic have) | For complete_order paths, N806 + expire_on_commit=False | ✅ |
| Patch external only | N/A (no external) | PackageService.deliver only | ✅ |

**Structure matches gamif al pie de la letra** (docstring, imports, class organization, fixture usage, make_callback/make_user, UI 1:1, real DB state).

---

## GSD Discipline Verified

- GSD log: `.planning/quick/gsd-33-test-reality-user-flows-store.log`
- Entries: **60** (wc -l)
- Pre before every: read, edit, gate (ruff/pytest/grep), self-check, SUMMARY
- Safe points + DoD marked per phase (F1-F6)
- Pool phrase verbatim in SUMMARY + gsd log + handoff

---

## Scope Verification

- ✅ Only Item 1 files: new integration test + log/PLAN/SUMMARY
- ✅ 0 prod changes (confirmed: `git diff --quiet HEAD -- handlers/store_user_handlers.py services/store_service.py`)
- ✅ 0 behavior / 0 atomicity / 0 impact on 3 crit
- ✅ No writes to gamif/narr/channel paths
- ✅ Golds re-run only (not modified)
- ✅ UI 1:1 (LucienVoice strings preserved in asserts)

---

## Recommendation

**Proceed to review loop (effort=4).**

The suite protects adecuadamente:
- 8 new integration tests exercise real StoreService purchase paths (direct_buy, confirm, product_detail, history) that were previously 100% MagicMock
- Real DB state verified for atomic contract (COMPLETE + PURCHASE tx + balance delta)
- 1-line/guard ports + TestSession patterns copied al pie from precedents
- All listed golds green; 0 attributable regressions
- 0 risks to contracts (atomicity, EventBus, get_service, 3 crit)
- Follows gamif precedent exactly (structure, injection, UI 1:1)
- GSD discipline (60 entries), self-check PASSED, pool phrase, handoff explicit

**No gaps requiring action within Item 1 scope.** The additive integration tests close the highest-value gap identified in mapeo (tienda user purchase flows with economic atomicity).

After review loop: documentador for ROADMAP + learnings + agent-memory report.

---

**Report path:** `.grok/agent-memory/test-guardian/33-item1-test-guardian-report.md`

**Veredict:** suite protege adecuadamente ✅

**Pool phrase (verbatim):** "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

---
*Source of truth: PLAN.md + SUMMARY + gsd-log (60) + impact mapeo + new test file + gold runs + git (0 prod) + precedent verification.*  
*Handoff ready for documentador + Item 2 executor.* 🎩
