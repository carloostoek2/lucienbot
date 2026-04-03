---
phase: 11-critical-services-tests
plan: "05"
subsystem: tests
 tags:
  - testing
  - unit-tests
  - user-service
  - analytics-service
  - story-service
dependency_graph:
  requires:
    - 11-01
  provides:
    - REQ-11-03
    - REQ-11-04
    - REQ-11-05
  affects:
    - tests/unit/test_user_service.py
    - tests/unit/test_analytics_service.py
    - tests/unit/test_story_service.py
    - services/story_service.py
tech_stack:
  added: []
  patterns:
    - pytest unit tests with db_session fixture
    - TDD: RED / GREEN / commit per task
key_files:
  created:
    - tests/unit/test_user_service.py
    - tests/unit/test_analytics_service.py
  modified:
    - tests/unit/test_story_service.py
    - services/story_service.py
decisions:
  - Added missing StoryService.calculate_archetype as wrapper over progress.get_dominant_archetype
  - Added missing StoryService.get_or_create_progress to support test expectations
  - Added StoryService.add_choice_to_node as alias of create_choice
  - Fixed plan test for advance_to_node to pass target node_id (node_b) instead of decision node (node_a)
metrics:
  duration: ~15
  completed_date: "2026-04-02"
---

# Phase 11 Plan 05: Critical Services Unit Tests Summary

Complete unit test coverage for UserService, AnalyticsService, and StoryService (CRUD, archetypes, branching). StoryService tests were appended to the existing file without removing atomicity tests.

## Tasks Completed

| # | Task | Commit | Result |
|---|------|--------|--------|
| 1 | UserService unit tests | `e13119a` | 13/13 tests passing |
| 2 | AnalyticsService unit tests | `2a2d730` | 8/8 tests passing |
| 3 | StoryService CRUD/archetype/branching tests | `9c76de8` | 14/14 tests passing |

## Overall Verification

`python -m pytest tests/unit/test_user_service.py tests/unit/test_analytics_service.py tests/unit/test_story_service.py -v --no-cov`

**Result: 35 passed**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing StoryService methods needed by tests**
- **Found during:** Task 3
- **Issue:** `get_or_create_progress`, `calculate_archetype`, and `add_choice_to_node` did not exist in `StoryService`, causing the planned tests to fail at import or execution time.
- **Fix:** Added the three methods as thin wrappers:
  - `get_or_create_progress(user_id)` → delegates to `get_user_progress` / `create_user_progress`
  - `calculate_archetype(progress)` → delegates to `progress.get_dominant_archetype()`
  - `add_choice_to_node(...)` → aliases `create_choice(...)`
- **Files modified:** `services/story_service.py`
- **Commit:** `9c76de8`

**2. [Rule 1 - Bug] Test expected advance_to_node to auto-redirect via choice.next_node_id**
- **Found during:** Task 3
- **Issue:** `test_advance_to_node_with_choice_updates_archetype_points` passed `node_a.id` to `advance_to_node` but asserted `progress.current_node_id == node_b.id`. The service sets `current_node_id = node_id` (the explicit target), not the choice's `next_node_id`.
- **Fix:** Changed the test to call `advance_to_node(sample_user.id, node_b.id, choice_id=choice.id)` so the target node matches the assertion.
- **Files modified:** `tests/unit/test_story_service.py`
- **Commit:** `9c76de8`

### Minor plan corrections

**3. Missing `UserRole` import in AnalyticsService test draft**
- **Found during:** Task 2
- **Fix:** Added `from models.models import ..., UserRole` to `test_analytics_service.py`.
- **Commit:** `2a2d730`

**4. Incorrect `user_id` comparison in AnalyticsService CSV test draft**
- **Found during:** Task 2
- **Issue:** `export_activity_csv` writes the internal `BesitoTransaction.user_id` (== `sample_user.id`), not `telegram_id`.
- **Fix:** Changed assertion from `str(sample_user.telegram_id)` to `str(sample_user.id)`.
- **Commit:** `2a2d730`

## Known Stubs

None — all tests are fully wired and passing.

## Self-Check: PASSED

- [x] `tests/unit/test_user_service.py` exists and has 79 lines
- [x] `tests/unit/test_analytics_service.py` exists and has 95 lines
- [x] `tests/unit/test_story_service.py` exists and has 286 lines
- [x] Existing `TestStoryServiceAtomicity` and `TestBigIntegerOverflow` classes remain
- [x] Commits `e13119a`, `2a2d730`, `9c76de8` are present in git history
