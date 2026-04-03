---
phase: 11-cubrir-los-servicios-cr-ticos-en-los-tests-realizar-test-e2e
plan: 02
subsystem: testing
tags: [pytest, sqlalchemy, sqlite, with_for_update, StoreService]

# Dependency graph
requires:
  - phase: 11-cubrir-los-servicios-cr-ticos-en-los-tests-realizar-test-e2e
    provides: Testing infrastructure and conftest fixtures
provides:
  - StoreService.complete_order protected by SELECT FOR UPDATE
  - 19 passing unit tests for StoreService
  - Race condition test verifying locking pattern
affects:
  - services/store_service.py
  - tests/unit/test_store_service.py

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mock chain verification for with_for_update() race condition tests"
    - "Inline Package creation when NOT NULL constraints require it"

key-files:
  created:
    - tests/unit/test_store_service.py
  modified:
    - services/store_service.py

key-decisions:
  - "Used db.query(StoreProduct).filter(...).with_for_update().first() inside complete_order loop to prevent concurrent stock decrements"
  - "Captured real db_session.query before patching to avoid RecursionError in race condition mock test"

patterns-established:
  - "Race condition tests: patch db_session.query with a spy that routes StoreProduct to mock chain and other models to real query"

requirements-completed:
  - REQ-11-01
  - REQ-11-12

# Metrics
duration: 6min
completed: 2026-04-03
---

# Phase 11 Plan 02: StoreService Tests and Race Condition Fix Summary

**StoreService unit test coverage with 19 passing tests and a SELECT FOR UPDATE fix for the complete_order stock race condition**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-03T05:03:20Z
- **Completed:** 2026-04-03T05:09:49Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Fixed confirmed race condition in `StoreService.complete_order` by adding `with_for_update()` to the product query during stock decrement
- Created comprehensive `tests/unit/test_store_service.py` with 19 unit tests
- Added dedicated `TestRaceConditions` class with mock-chain verification proving the locking pattern is used

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix race condition in StoreService.complete_order** - `0bf6f6d` (fix)
2. **Task 2: Write StoreService unit tests** - `c8faa81` (test)

**Plan metadata:** `TBD` (docs: complete plan)

## Files Created/Modified

- `services/store_service.py` - Added `with_for_update()` locking in `complete_order` product stock query
- `tests/unit/test_store_service.py` - Full StoreService test suite (product CRUD, cart, orders, race condition verification)

## Decisions Made

- Used `db.query(StoreProduct).filter(StoreProduct.id == order_item.product_id).with_for_update().first()` instead of direct `order_item.product` access to prevent concurrent stock decrements
- In race condition tests, captured the real `db_session.query` before applying `patch.object` to avoid RecursionError when falling back to real queries for non-StoreProduct models

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_create_product IntegrityError**
- **Found during:** Task 2 (writing StoreService unit tests)
- **Issue:** `service.create_product(..., package_id=None)` failed with `NOT NULL constraint failed: store_products.package_id`
- **Fix:** Created an inline `Package` in the test setup before calling `create_product`
- **Files modified:** `tests/unit/test_store_service.py`
- **Verification:** `test_create_product` passes
- **Committed in:** `c8faa81` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed RecursionError in race condition mock test**
- **Found during:** Task 2 (writing StoreService unit tests)
- **Issue:** `spy_query` fallback `return db_session.query(model)` triggered infinite recursion because `db_session.query` was already patched
- **Fix:** Captured `real_query = db_session.query` before patching and used `return real_query(model)` in the spy fallback
- **Files modified:** `tests/unit/test_store_service.py`
- **Verification:** `test_complete_order_uses_select_for_update_on_product` passes
- **Committed in:** `c8faa81` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes were necessary for tests to pass. No scope creep.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- StoreService is fully tested and the race condition is fixed
- Ready to proceed to next critical service tests in Phase 11

## Self-Check: PASSED

- [x] `tests/unit/test_store_service.py` exists (206 lines)
- [x] `services/store_service.py` contains `with_for_update`
- [x] Commits `0bf6f6d` and `c8faa81` exist in git history

---
*Phase: 11-cubrir-los-servicios-cr-ticos-en-los-tests-realizar-test-e2e*
*Completed: 2026-04-03*
