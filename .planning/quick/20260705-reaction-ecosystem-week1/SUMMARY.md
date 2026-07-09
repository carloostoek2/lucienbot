# SUMMARY: Reaction Ecosystem Week 1 Hardening

**Item:** `reaction-ecosystem-week1`  
**Date:** 2026-07-05  
**Status:** COMPLETE — all gold gates green

---

## Objectives Achieved

| # | Objective | Result |
|---|-----------|--------|
| 1 | **Unify markup** | `keyboards/broadcast_channel_markup.py` — single `build_channel_reaction_markup` covers send + refresh + extra URL |
| 2 | **Extract validators** | `services/broadcast/reaction_validators.py` — 4 pure validators (≤13 LOC each) |
| 3 | **Move refresh to service** | `BroadcastService.process_channel_reaction` — register + refresh post-commit |
| 4 | **Slim handler** | `handle_reaction`: exactly `1× get_service` + `1× process_channel_reaction` |
| 5 | **Deprecate shims** | `reactions_keyboard_with_counts` → thin wrapper; `register_reaction` → `DeprecationWarning` |
| 6 | **Migrate tests** | 5 unit tests migrated to async `check_and_register_reaction`; legacy kept for SELECT FOR UPDATE |

---

## Files Created

- `keyboards/broadcast_channel_markup.py`
- `services/broadcast/reaction_validators.py`
- `tests/unit/test_broadcast_channel_markup.py`

## Files Edited

- `handlers/broadcast_handlers.py` — removed duplicate markup helpers; import unified builder
- `handlers/gamification_user_handlers.py` — slim handler; removed refresh helpers
- `services/broadcast_service.py` — `process_channel_reaction`, validator refactor, `register_reaction` deprecation
- `keyboards/inline_keyboards.py` — deprecated `reactions_keyboard_with_counts` wrapper
- `keyboards/CLAUDE.md` — documented unified module
- `tests/integration/test_callbackdata_broadcast.py` — imports updated
- `tests/handlers/test_gamification_user_handlers.py` — `process_channel_reaction` mocks
- `tests/unit/test_broadcast_service.py` — async migration (except SELECT FOR UPDATE)
- `tests/integration/test_reaction_mission_flow.py` — `test_reaction_besitos_value_mapping` migrated
- `tests/integration/test_reaction_limit.py` — `filterwarnings` for legacy path

---

## Test Results (full gold gate)

| Suite | Result |
|-------|--------|
| `test_broadcast_service_reaction_flow.py` | 23 passed |
| `test_cross_service_atomicity.py` | 10 passed |
| `test_invariants.py -k reaction` | 1 passed |
| `test_reaction_full_chain.py` | 2 passed |
| `test_reaction_mission_flow.py` | 4 passed |
| `test_reaction_limit.py` | 3 passed |
| `test_gamification_user_handlers.py -k reaction` | 24 passed |
| `test_callbackdata_broadcast.py` | 31 passed |
| `test_broadcast_service.py` | 22 passed |
| `test_broadcast_channel_markup.py` | 11 passed |
| **Primary gate** (`-k "reaction or broadcast_channel_markup or TestBroadcastPureHelpers or TestHandleReaction"`) | **97 passed** |

**Total failures:** 0

---

## Constraints Verified

- [x] 0 user-visible behavior change (markup golden tests pass)
- [x] 0 atomicity change (cross_service_atomicity + invariants green)
- [x] `handle_reaction`: `1× get_service` + `1× process_channel_reaction`
- [x] Validators ≤50 LOC each; validation orchestration ≤50 LOC
- [x] `register_reaction` deprecated with `warnings.warn`; not deleted
- [x] EventBus observer untouched
- [x] Ruff clean on all touched files

---

## Deviations

1. **`check_and_register_reaction` total LOC (~149)** — validation block extracted to pure validators (~27 LOC orchestration); transaction body (INSERT/credit/commit/missions/IntegrityError) intentionally unchanged per plan; exceeds 50 LOC as pre-existing transaction scope (same as original 156 LOC monolith minus validator extraction).
2. **`test_complete_reaction_mission_flow_with_real_data`** — kept on legacy `register_reaction` (sync mission flow semantics; comment explicitly avoided async).
3. **`test_no_daily_reaction_limit_exists`** — kept on legacy `register_reaction` with `filterwarnings` (documents sync multi-emoji loop semantics).

---

## Handoff

Ready for `arch-enforcer` → `test-guardian`.