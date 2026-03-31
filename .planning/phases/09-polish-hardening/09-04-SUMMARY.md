---
phase: 09-polish-hardening
plan: "04"
subsystem: scheduler
tags:
  - apscheduler
  - scheduler
  - persistence
  - cron
dependency_graph:
  requires:
    - 09-02
  provides:
    - SCHED-01
tech_stack:
  added:
    - APScheduler 3.10.4 (already present in requirements.txt)
  patterns:
    - AsyncIOScheduler with SQLAlchemyJobStore
    - CronTrigger for precise scheduling
    - JobDefaults with replace_existing=True
key_files:
  created: []
  modified:
    - services/scheduler_service.py
decisions:
  - id: backup-cron-schedule
    summary: Backup job migrated from 100-cycle counter to daily cron (03:00)
    rationale: APScheduler removed the cycle counter loop; backup now has its own cron trigger
    alternatives:
      - "Keep cycle counter (incompatible with APScheduler architecture)"
      - "Run backup on every job execution (too frequent)"
    selected: Daily cron at 03:00 (similar to original ~50min frequency)
---

# Phase 09 Plan 04: APScheduler Migration Summary

## One-liner

Replaced `asyncio.sleep(30)` polling loop with APScheduler AsyncIOScheduler + SQLAlchemyJobStore; jobs now persist across restarts and run on precise cron schedules.

## Tasks Completed

| # | Task | Name | Commit | Files |
|---|------|------|--------|-------|
| 1 | Task 1 | Refactor SchedulerService to use APScheduler | a63e5e6 | services/scheduler_service.py |
| 2 | Task 2 | Verify bot reference handling | (verification only, no changes) | services/scheduler_service.py |

## What Was Built

**Before:** Fixed 30-second `asyncio.sleep` polling loop in `_run_loop()` that ran all process methods every cycle, with backup every 100 cycles (~50 minutes). Jobs were lost on bot restart.

**After:** `AsyncIOScheduler` with `SQLAlchemyJobStore` using the existing `DATABASE_URL`. Four cron-triggered jobs registered with `replace_existing=True`:

| Job ID | Method | Schedule | Purpose |
|--------|--------|----------|---------|
| `approve_join_requests` | `_process_pending_requests` | Daily 09:00 | Auto-approve ready join requests |
| `expiry_reminders` | `_process_expiring_subscriptions` | Daily 08:00 | Send VIP expiry reminders (24h) |
| `expire_subscriptions` | `_process_expired_subscriptions` | Daily 00:05 | Process expired VIP subscriptions |
| `daily_backup` | `_run_backup_job` | Daily 03:00 | Database backup (migrated from cycle counter) |

## Key Implementation Details

- `JobDefaults(replace_existing=True)` at scheduler level ensures no duplicate jobs on restart
- `SQLAlchemyJobStore(url=bot_config.DATABASE_URL)` reuses existing DB connection
- `AsyncIOExecutor` handles async job callbacks correctly
- Bound methods (`self._process_pending_requests`) work directly with APScheduler AsyncIOExecutor -- `self` is preserved
- `self.bot` stored in `__init__` and accessible in all process methods (no change needed)
- `check_interval` parameter removed from constructor (no longer needed)

## Deviations from Plan

### Rule 2 - Auto-add: Backup job migration to cron
- **Found during:** Task 1 implementation
- **Issue:** Original backup ran every 100 cycles of the polling loop (~50 min). APScheduler removed the loop entirely, so the cycle counter was gone.
- **Fix:** Added backup as a separate cron job: `trigger="cron", hour=3, minute=0, id="daily_backup"` -- same ~daily frequency, cleaner architecture.
- **Files modified:** services/scheduler_service.py
- **Commit:** a63e5e6

## Acceptance Criteria Verification

| Criterion | Result |
|-----------|--------|
| File contains `from apscheduler.schedulers.asyncio import AsyncIOScheduler` | PASS |
| File contains `SQLAlchemyJobStore(url=bot_config.DATABASE_URL)` | PASS |
| File contains `trigger="cron"` (not "interval") | PASS (4 occurrences) |
| File contains `replace_existing=True` (at least 3 times) | PASS (5 occurrences) |
| File does NOT contain `asyncio.sleep` | PASS |
| File still contains `_process_pending_requests` method | PASS |
| File still contains `_process_expiring_subscriptions` method | PASS |
| File still contains `_process_expired_subscriptions` method | PASS |
| `python3 -c "from services.scheduler_service import SchedulerService"` succeeds | PASS |
| `self.bot = bot` stored in `__init__` | PASS (line 31) |
| Process methods reference `self.bot` | PASS |

## Self-Check: PASSED

- [x] Commit a63e5e6 exists and matches plan
- [x] services/scheduler_service.py updated correctly
- [x] All business logic methods unchanged
- [x] APScheduler correctly configured
- [x] No asyncio.sleep polling
