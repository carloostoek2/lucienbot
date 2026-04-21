---
phase: 16
plan: 16-05a
subsystem: engagement_layer
tech-stack: Python 3.12, Aiogram 3, SQLAlchemy 2.0
key-files:
  - services/besito_service.py
  - services/mission_service.py
  - tests/unit/test_besito_service.py
  - tests/unit/test_mission_service.py
---

# Plan 16-05a: Percentiles Anónimos

**Objective:** Implement anonymous percentile ranking for besitos and mission completions with soft bucket display.

## Tasks Completed

1. **Implement get_percentile in BesitoService** — Added method returning soft buckets (top 5%, 10%, 20%, 50%, 100%) based on balance ranking. Edge cases: empty DB, single user, user not found.

2. **Implement get_percentile in MissionService** — Added method counting completed missions per user, ranking by completion count, returning soft buckets.

3. **Add unit tests** — TestBesitoPercentile (4 tests), TestMissionPercentile (3 tests) covering edge cases.

## Commits

- `fc56f4a`: feat(besito): add anonymous percentile method get_percentile()
- `ecbb851`: feat(mission): add anonymous percentile method get_percentile()
- `d0ad7e6`: test: add unit tests for percentile logic

## Verification

- `pytest -xvs tests/unit/test_besito_service.py -k "TestBesitoPercentile"` — PASSED
- `pytest -xvs tests/unit/test_mission_service.py -k "TestMissionPercentile"` — PASSED

## Self-Check: PASSED