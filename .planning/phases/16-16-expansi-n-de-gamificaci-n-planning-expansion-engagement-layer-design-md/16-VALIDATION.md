---
phase: 16
slug: 16-expansi-n-de-gamificaci-n-planning-expansion-engagement-layer-design-md
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-15
updated: 2026-04-15
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pytest.ini` (existing) |
| **Quick run command** | `pytest -xvs tests/unit/test_daily_gift_service.py tests/unit/test_story_service.py tests/unit/test_reward_service.py tests/unit/test_mission_service.py tests/unit/test_besito_service.py` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest -xvs tests/unit/test_<affected_service>.py`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | enum-first migrations | migration | `alembic upgrade head && alembic downgrade -1` | W0 | pending |
| 16-01-02 | 01 | 1 | DailyGiftStreak model + table migration | migration | `alembic upgrade head && alembic downgrade -1` | W0 | pending |
| 16-01-03 | 01 | 1 | Ritmo logic in DailyGiftService | unit | `pytest -xvs tests/unit/test_daily_gift_service.py` | yes | pending |
| 16-01-04 | 01 | 1 | Engagement handlers (Ritmo) | integration | `python -c "from handlers.engagement_user_handlers import router; print('ok')"` | no | pending |
| 16-01-05 | 01 | 1 | LucienVoice + keyboard updates | integration | `grep "ritmo_diario" keyboards/inline_keyboards.py` | yes | pending |
| 16-02-01 | 02 | 2 | MissionTemplate model + migration | migration | `alembic upgrade head && alembic downgrade -1` | W0 | pending |
| 16-02-02 | 02 | 2 | MissionTemplate CRUD + daily generation | unit | `pytest -xvs tests/unit/test_mission_service.py` | yes | pending |
| 16-02-03 | 02 | 2 | Scheduler job for daily missions | integration | `grep "generate_daily_missions" services/scheduler_service.py` | yes | pending |
| 16-03-01 | 03 | 3 | StoryPath + UserStoryPathProgress models + migrations | migration | `alembic upgrade head && alembic downgrade -1` | W0 | pending |
| 16-03-02 | 03 | 3 | StoryNode unlock columns migration | migration | `alembic upgrade head && alembic downgrade -1` | W0 | pending |
| 16-03-03 | 03 | 3 | StoryService path methods | unit | `pytest -xvs tests/unit/test_story_service.py` | yes | pending |
| 16-03-04 | 03 | 3 | Senderos user handlers | integration | `python -c "from handlers.engagement_user_handlers import router; print('ok')"` | no | pending |
| 16-04-01 | 04 | 4 | WhisperRewardPool + items + claims models + migrations | migration | `alembic upgrade head && alembic downgrade -1` | W0 | pending |
| 16-04-02 | 04 | 4 | RewardService whisper methods | unit | `pytest -xvs tests/unit/test_reward_service.py` | yes | pending |
| 16-04-03 | 04 | 4 | Susurros user handlers | integration | `python -c "from handlers.engagement_user_handlers import router; print('ok')"` | no | pending |
| 16-05-01 | 05 | 5 | Percentile queries (BesitoService + MissionService) | unit | `pytest -xvs tests/unit/test_besito_service.py tests/unit/test_mission_service.py` | yes | pending |
| 16-05-02 | 05 | 5 | Mi Percentil handler + keyboard | integration | `grep "mi_percentil" keyboards/inline_keyboards.py` | yes | pending |
| 16-05-03 | 05 | 5 | Full suite green | full | `pytest tests/ -x` | yes | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [x] Enum-first migration stubs identified (TransactionSource + MissionType)
- [x] `tests/unit/test_daily_gift_service.py` — extend with streak tests
- [x] `tests/unit/test_story_service.py` — extend with path/progress tests
- [x] `tests/unit/test_reward_service.py` — extend with whisper tests
- [x] `tests/unit/test_mission_service.py` — extend with template tests
- [x] `tests/unit/test_besito_service.py` — extend with percentile tests

*Existing infrastructure covers framework and conftest; service test files exist and need extension.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Telegram inline keyboard flow | UX | Requires live bot UI interaction | Run `/ritmo_diario` and verify message + keyboard update |
| VIP vs Free differentiation | Business logic | Requires VIP state | Create VIP user, verify caps/multipliers differ from Free |
| Daily mission generation at 00:01 | Scheduler | Requires waiting for cron or manual job trigger | Trigger `_generate_daily_missions_job` manually and verify `[Daily]` missions created |

*All core behaviors have automated verification via unit tests or grep/import checks.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved for execution
