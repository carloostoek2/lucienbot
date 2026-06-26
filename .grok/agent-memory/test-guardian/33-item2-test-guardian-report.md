# Test-Guardian Report: 33-item2 (pool 33-test-reality-user-flows-store)

**Item:** 2 / second of new pool of 4  
**Verdict:** suite protege adecuadamente  
**Date:** 2026-06-26  
**Guardian:** test-guardian (following hardener-agile + PLAN al pie + arch PASS WITH NOTES)  
**Scope:** Audit mock reduction in non-gold purchase paths of `tests/unit/test_store_service.py` (TestRaceConditions + 1-line/guard ports); confirm `TestStorePurchaseAtomicGold` verbatim untouched; re-run atomic gold full + cross_service_atomicity + invariants I8 + reactions + daily + vip + broader store/atomicity; 0 regressions; mocks now use real db_session.

---

## Quick Reads Performed (as instructed)
- Item 2 executor SUMMARY/gold status: from gsd log (F1-F4, self-check PASSED, golds 25p atomic identical etc) + SUMMARY.md (Item 2 note: F1-F4 + "atomic gold verbatim (kept 100%)" + "1-line/guard exact now at 2 sites" + "reduced (no spy... only in gold)")
- Arch audit: `.grok/agent-memory/arch-enforcer/33-item2-arch-audit.md` → **PASS WITH NOTES (0 critical)**
- PLAN Item 2: `.planning/phases/33-test-reality-user-flows-store/PLAN.md` (Item2: "Reduce spies/mocks internos en tests/unit/test_store_service.py para purchase paths"; keep gold 100%; re-runs atomic+cross+invariants; 1-line/guard exact; real db_session/fixtures prefer)
- Edited: `tests/unit/test_store_service.py` (TestRaceConditions updated for real path + ports; gold class 831+ untouched)
- Atomic gold class: full `TestStorePurchaseAtomicGold` (DESIRED CONTRACT, TestSession/file, 777, try/finally, "credit survives deliver False", "post-credit best effort", external patch only, N806 tol) — verbatim

---

## Exact Commands Run + Output Summary

All runs used project flags: `-q --tb=line -p no:cov --override-ini="addopts="`

Using `./venv/bin/python -m pytest` per PLAN / precedents.

### 1. Store atomic gold full (critical: must be identical)
```bash
./venv/bin/python -m pytest tests/unit/test_store_service.py -k "TestStorePurchaseAtomicGold or complete_order" -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 25 passed, 30 deselected, 1 warning (MovedIn20 pre-exist)

### 2. Cross service atomicity (full)
```bash
./venv/bin/python -m pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 10 passed, 1 warning (Runtime pre-exist)

### 3. Invariants I8
```bash
./venv/bin/python -m pytest tests/integration/test_invariants.py -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 11 passed, warnings pre-exist (SA + Runtime never awaited)

### 4. Reaction chains
```bash
./venv/bin/python -m pytest tests/integration/test_reaction_full_chain.py tests/integration/test_reaction_mission_flow.py tests/integration/test_reaction_limit.py -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 9 passed, 4 warnings (pre-exist)

### 5. Daily atomic
```bash
./venv/bin/python -m pytest tests/unit/test_daily_gift_service.py -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 19 passed, 2 warnings (pre-exist)

### 6. VIP flows
```bash
./venv/bin/python -m pytest tests/integration/test_vip_flow.py tests/integration/test_vip_flows.py tests/integration/test_vip_complete_cycle.py -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 37 passed, warnings pre-exist (PytestReturnNotNone etc)

### 7. Broader smoke (store or atomicity or ...)
```bash
./venv/bin/python -m pytest -k "store or atomicity or mission or reaction or daily or vip" -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 780 passed, 930 deselected, 8 xfailed, 57 warnings

**All xfailed/warnings documented as pre-existing (non-attributable) per executor SUMMARY / arch.**

### Targeted for edit
```bash
./venv/bin/python -m pytest tests/unit/test_store_service.py::TestRaceConditions -q --tb=line -p no:cov --override-ini="addopts="
```
**Result:** 1 passed

---

## Audit: Mocks Reduced + Gold Untouched + Ports Exact + 0 Regressions

### Mocks in non-gold purchase (TestRaceConditions)
- **Before (per F1 baseline/greps):** MagicMock query chain + spy_query + fs_inst / heavy Fulfillment patch in `test_complete_order_uses_select_for_update_on_product`
- **After (Item 2 edit):** Real `db_session` + real query path + **external-only** `patch("services.fulfillment_service.PackageService")` (exact gold precedent for deliver/TG-side)
- Docstring updated: "Reducido mock query chain / spy_query / heavy fs_inst (Item2 reality hardening, non-gold purchase path). Solo parche externo/TG-side deliver (PackageService, como gold precedent). Prefer real db_session/fixtures."
- rg confirm (post-edit): remaining MagicMock/spy_query/fs_inst usages are **only inside gold class** (lines ~1113+ for spy_query internal to TestStorePurchaseAtomicGold) + import + comments. Race test now real.

### Atomic gold verbatim untouched
- Class `TestStorePurchaseAtomicGold` (831+) + all 7 tests + DESIRED CONTRACT docstring + `_create_engine_and_session` (N806 tol) + 7770xxx TG ids + explicit models + try/finally + re-query + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + external patch only (PackageService.deliver) — **100% identical**
- Gold-internal spy remains (expected, per PLAN: "keep TestStorePurchaseAtomicGold verbatim")
- rg / reads / test counts confirm 0 logic change to gold

### 1-line/guard ports exact
- Exact comment present (2 sites):
  - `... )  # 1-line/guard port post Item10 local (copy daily precedent in cross; arch-enforcer); was service.besito_service`
  - `# 1-line/guard port post Item10 local (copy daily precedent in cross; arch-enforcer); was service.besito_service`
- Pattern: `BesitoService(db=db_session).get_balance(...) if not hasattr(service, "besito_service") else service.besito_service.get_balance(...)`
- One pre-existing (complete_order_success ~217), one added in race (~812) per PLAN

### 0 regressions
- Atomic gold: 25p **identical** (gold contract protected)
- Cross: 10p
- Invariants I8: 11p (order COMPLETE irreversible)
- Reactions: 9p
- Daily: 19p
- VIP: 37p
- Broader: 780p + 8xf (xf pre-exist, same order of magnitude as prior)
- Targeted race: 1p
- Attributable to Item 2 edit: **0**

---

## Golds Status (List + Pass/Fail Counts)

| Gold | Command | Result | Notes |
|------|---------|--------|-------|
| Store atomic gold (TestStorePurchaseAtomicGold + complete_order) | `-k "TestStorePurchaseAtomicGold or complete_order"` on test_store_service.py | ✅ 25 passed (identical) | DESIRED CONTRACT protected; "credit survives deliver False"; "post-credit best effort"; TestSession + 777 + try/finally; external patch only |
| Cross service atomicity (full) | test_cross_service_atomicity.py | ✅ 10 passed | Store side effects + 1-line/guard for locals |
| Invariants (I8) | test_invariants.py | ✅ 11 passed | Order COMPLETE irreversible |
| Reaction full chain + mission + limit | 3 reaction files | ✅ 9 passed | Gamif crit #1 protected |
| Daily atomic | test_daily_gift_service.py | ✅ 19 passed | Gamif crit #1 |
| VIP flows (test_vip_flow + test_vip_flows + test_vip_complete_cycle) | 3 vip files | ✅ 37 passed | Canales-VIP crit #3 |
| Broader smoke | `-k "store or atomicity or mission or reaction or daily or vip"` | ✅ 780 passed, 8 xfailed | Pre-exist xf/warns non-attrib |

**Total attributable regressions to Item 2: 0**

---

## Coverage Note
- Runs used `-p no:cov` (per exact flags in PLAN + all prior hardener runs)
- No coverage delta measured here. Reality increase is structural: non-gold purchase path (race) now exercises real db query + complete_order debit path (previously spied). Gold atomic coverage unchanged (untouched).
- New reality in TestRace: complete_order with_for_update path + balance via real/local Besito now under real DB (was mock).

---

## Risks to Contracts

**None.**

- Atomicity contract: protected (gold 25p identical + cross + DESIRED + survives + post-credit + TestSession + external-only patch; race now real but does not alter contract)
- EventBus contract: best-effort preserved; no mutation in unit tests
- get_service contract: prod unchanged (locals post-Item10); tests use direct/real or external patch
- 3 crit systems: gamif (reactions/daily/atomic/cross green), narrativa (untouched), canales-VIP (vip green)
- No writes to crit paths; only non-gold unit test edit + hygiene
- Gold contract verbatim

---

## Precedent + Arch Verification
- Follows PLAN Item2 al pie: reduce in non-gold only; gold untouched; real db_session; external patch only; 1-line/guard exact; re-runs listed
- Arch: **PASS WITH NOTES (0 critical)** (mocks reduced, gold 100% untouched, ports exact, GSD, scope tight, 0 prod/0 beh/0 atomicity/0 impact 3crit)
- GSD discipline: 20+ entries for Item2 in gsd-33-*.log (pre every edit/gate); wc tracked; safe points + DoD; self-check PASSED in log + SUMMARY
- Pool phrase verbatim in executor SUMMARY + handoff

---

## Scope Verification
- ✅ Only Item 2: non-gold purchase mock reduction (TestRaceConditions) in tests/unit/test_store_service.py + log/PLAN/SUMMARY
- ✅ Gold untouched (confirmed)
- ✅ 0 prod changes (git diff 0 on services/store_service.py handlers/store*.py)
- ✅ 0 behavior / 0 atomicity / 0 impact on 3 crit + contracts
- ✅ 1-line/guard exact
- ✅ Prefer real db/fixtures in race

---

## Recommendation
**Proceed (pool continues to Item 3 or documentador if last).**

**suite protege adecuadamente** ✅

- Mocks reduced in non-gold purchase (TestRace now real db_session + external-only patch; no MagicMock/spy/fs_inst in race)
- Atomic gold verbatim untouched + contract fully protected (25p identical)
- 1-line/guard exact x2 with comment
- All listed golds green (atomic/cross/invariants/reactions/daily/vip/broader); 0 attributable regressions
- 0 risks to atomicity/EventBus/get_service/3 crit
- Follows PLAN + precedents (gold patterns, 1-line/guard, real prefer, GSD, pool phrase) al pie
- Arch PASS WITH NOTES (0 crit)

**No gaps requiring action within Item 2 scope.** The mock reduction in TestRace + gold protection directly increases reality for the race purchase path while locking the atomic gold.

After next (or pool close): documentador for ROADMAP + learnings + agent-memory report.

---

**Report path:** `.grok/agent-memory/test-guardian/33-item2-test-guardian-report.md`

**Veredict:** suite protege adecuadamente ✅

**Pool phrase (verbatim):** "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

---

*Source of truth: PLAN.md (Item2) + SUMMARY (Item2 note) + gsd-33-*.log (F1-F4 + self-check) + arch-audit + edited test_store_service.py (race only) + gold runs (all green) + rg confirms (mocks/gold/ports) + precedent verification.*  
*Handoff ready for documentador + Item 3 (per handoff).* 🎩
