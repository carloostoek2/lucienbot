---
phase: 11-critical-services-tests
plan: "03"
subsystem: "Promotions + Broadcast"
tags: ["tests", "race-condition", "select-for-update", "promotion", "broadcast"]
dependency_graph:
  requires: ["11-01"]
  provides: ["11-04", "11-05", "11-06", "11-07"]
  affects: ["services/promotion_service.py", "services/broadcast_service.py"]
tech-stack:
  added: []
  patterns: ["pytest", "unittest.mock.patch", "SELECT FOR UPDATE"]
key-files:
  created:
    - tests/unit/test_promotion_service.py
    - tests/unit/test_broadcast_service.py
  modified:
    - services/promotion_service.py
    - services/broadcast_service.py
    - tests/conftest.py
decisions: []
metrics:
  duration: "~18m"
  completed_date: "2026-04-03"
---

# Phase 11 Plan 03: PromotionService + BroadcastService Tests and Race Condition Fixes Summary

**One-liner:** Fixed duplicate-interest and double-reaction race conditions with SELECT FOR UPDATE and delivered 31 passing unit tests with dedicated race-condition verification classes.

## What Was Done

- Replaced unprotected `has_user_expressed_interest` call in `PromotionService.express_interest` with an inline `PromotionInterest` query locked via `with_for_update()`.
- Replaced unprotected `has_user_reacted` call in `BroadcastService.register_reaction` with an inline `BroadcastReaction` query locked via `with_for_update()`.
- Created `tests/unit/test_promotion_service.py` (280 lines) with 17 tests covering promotion CRUD, interest lifecycle, user blocking, stats, and a `TestPromotionServiceRaceCondition` class that mocks the query chain to assert `with_for_update()` is invoked.
- Created `tests/unit/test_broadcast_service.py` (281 lines) with 14 tests covering emoji management, broadcast messages, reaction registration, duplicate-prevention, stats, and a `TestBroadcastServiceRaceCondition` class that verifies `with_for_update()` on the `BroadcastReaction` query inside `register_reaction`.
- Added reusable fixtures to `tests/conftest.py`: `sample_package`, `sample_promotion`, `sample_reaction_emoji`, `sample_broadcast_message`.

## Commits

- `084dcbd` fix(phase-11-03): add SELECT FOR UPDATE to PromotionService.express_interest
- `d14cf40` fix(phase-11-03): add SELECT FOR UPDATE to BroadcastService.register_reaction
- `ead2f2b` test(phase-11-03): add PromotionService unit tests with race condition verification
- `50ad430` test(phase-11-03): add BroadcastService unit tests with race condition verification

## Test Results

```
python -m pytest tests/unit/test_promotion_service.py tests/unit/test_broadcast_service.py -v
31 passed
```

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. Data sources are fully wired to the in-memory SQLite test database.

## Self-Check: PASSED

- [x] `tests/unit/test_promotion_service.py` exists (280 lines, 17 tests)
- [x] `tests/unit/test_broadcast_service.py` exists (281 lines, 14 tests)
- [x] `services/promotion_service.py` contains `with_for_update()` inside `express_interest`
- [x] `services/broadcast_service.py` contains `with_for_update()` inside `register_reaction`
- [x] All 31 tests pass
