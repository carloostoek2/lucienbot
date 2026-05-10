---
phase: "16"
slug: trivias-tematicas
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-09
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest -x tests/ --ignore=tests/e2e -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest -x tests/unit/test_trivia_service.py tests/unit/test_game_service.py -q`
- **After every plan wave:** Run `pytest -x tests/ --ignore=tests/e2e -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | — | T-16-01 | Admin `is_admin()` check on all category handlers | unit | `pytest tests/unit/test_trivia_service.py -x -q` | ✅ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | — | T-16-02 | Category state writes use DB transactions | unit | `pytest tests/unit/test_trivia_service.py::test_category_state_transaction -x -q` | ✅ W0 | ⬜ pending |
| 16-02-01 | 02 | 1 | — | — | Draw-without-repetition logic | unit | `pytest tests/unit/test_game_service.py::test_draw_without_repetition -x -q` | ❌ | ⬜ pending |
| 16-02-02 | 02 | 1 | — | — | Streak milestone bonus calculation | unit | `pytest tests/unit/test_game_service.py::test_streak_milestone_bonus -x -q` | ❌ | ⬜ pending |
| 16-02-03 | 02 | 1 | — | — | Streak bonus does not stack | unit | `pytest tests/unit/test_game_service.py::test_streak_no_stacking -x -q` | ❌ | ⬜ pending |
| 16-03-01 | 03 | 2 | — | T-16-01 | Category file not found handling | unit | `pytest tests/unit/test_trivia_service.py::test_category_file_not_found -x -q` | ✅ W0 | ⬜ pending |
| 16-03-02 | 03 | 2 | — | — | Thematic trivia has independent limits | unit | `pytest tests/unit/test_trivia_service.py::test_independent_limits -x -q` | ✅ W0 | ⬜ pending |
| 16-03-03 | 03 | 2 | — | — | Thematic button appears in game menu | integration | `pytest tests/integration/test_trivia_handler.py -x -q` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/unit/test_trivia_service.py` — stubs for TriviaCategoryService tests
- [x] `tests/integration/test_trivia_handler.py` — stubs for thematic trivia handler tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Category JSON file creation (Halloween, Navidad) | D-01, D-15 | Files are produced externally by Diana/team | Verify `docs/preguntas_halloween.json` and `docs/preguntas_navidena.json` exist with valid question format |
| Admin inline button flow for category management | D-14 | Requires actual Telegram UI interaction | /admin → "🎯 Mazos de Trivia" → activate/deactivate/schedule/view |
| Scheduling UI (programar por fecha) | D-14 | Deferred to future task — activates/deactivates are manual-only for Phase 16 scope | Schedule via SchedulerService DateTrigger in follow-up task |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
