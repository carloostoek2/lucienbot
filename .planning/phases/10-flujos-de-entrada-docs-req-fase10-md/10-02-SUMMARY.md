, "---
phase: 10-flujos-de-entrada-docs-req-fase10-md
plan: 02
type: execute
subsystem: free-channel-entry
tags: [scheduler, apscheduler, free-channel, ritual-entry, delay-message]
dependency_graph:
  requires: [10-01]
  provides: [free-entry-flow-complete]
  affects: [handlers/free_channel_handlers.py, services/scheduler_service.py]
tech_stack:
  added: []
  patterns: [APScheduler DateTrigger for delayed messages, IntervalTrigger for real-time approvals]
key_files:
  created: []
  modified:
    - handlers/free_channel_handlers.py
    - services/scheduler_service.py
decisions:
  - Used DateTrigger with 30-second delay for ritual welcome message instead of immediate response
  - Implemented impatience message for repeated requests while pending
  - IntervalTrigger(seconds=30) replaces daily cron for real-time approval processing
metrics:
  duration_minutes: 15
  tasks_completed: 2
  files_modified: 2
  commits: 2
  lines_added: 95
  lines_removed: 14
completed_date: 2026-03-31
---

# Phase 10 Plan 02: Ritualized Free Channel Entry Flow

## Summary

Implemented the ritualized Free channel entry flow with a 30-second delayed welcome message, immediate impatience message on repeated requests, and a corrected real-time approval loop using IntervalTrigger.

## One-Liner

Free channel entry flow with 30s delayed ritual message, impatience handling for repeated requests, and real-time 30-second approval loop via APScheduler.

## What Was Built

### Services/Scheduler (Task 1 - Already Completed)

- Changed `_process_pending_requests` trigger from `cron(hour=9, minute=0)` to `IntervalTrigger(seconds=30)` for real-time approvals
- Added `_send_free_welcome_job()` module-level async function for delayed welcome messages
- Added `schedule_free_welcome(user_id, channel_id)` method using `DateTrigger(run_date=datetime.utcnow() + timedelta(seconds=30))`
- Updated `_process_pending_requests` to send `LucienVoice.free_entry_welcome()` followed by invite link

### Handlers/Free Channel (Task 2 - Completed)

- Added import for `get_scheduler` from `services.scheduler_service`
- Modified `handle_join_request()`:
  - Sends `LucienVoice.free_entry_impatient()` when existing pending request found
  - Calls `scheduler.schedule_free_welcome()` after creating pending request
  - Removed immediate `free_request_received` message
- Completed `handle_member_join()`:
  - Sends `LucienVoice.free_entry_welcome(channel.channel_name)`
  - Sends `channel.invite_link` in separate message if available

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `IntervalTrigger(seconds=30)` for approvals | ✅ | services/scheduler_service.py:259 |
| `_send_free_welcome_job` module function | ✅ | services/scheduler_service.py:66 |
| `schedule_free_welcome` method | ✅ | services/scheduler_service.py:293 |
| `free_entry_impatient()` on repeated request | ✅ | handlers/free_channel_handlers.py:58 |
| `schedule_free_welcome()` after create | ✅ | handlers/free_channel_handlers.py:75 |
| `free_entry_welcome()` + invite link on join | ✅ | handlers/free_channel_handlers.py:147-156 |
| No `free_request_received` immediate message | ✅ | Removed from handlers/free_channel_handlers.py |

## Commits

| Hash | Message | Files |
|------|---------|-------|
| d82e88d | feat(phase-10-02): update free channel handlers for ritualized entry flow | handlers/free_channel_handlers.py |
| 72f99a6 | feat(phase-10-02): implement 30s delay mechanism for Free channel entry | services/scheduler_service.py |

## Deviations from Plan

None - plan executed exactly as written. The scheduler_service.py was already completed per the user's instructions.

## Verification Results

```bash
# Automated verification passed:
grep -n "IntervalTrigger" services/scheduler_service.py
# 16:from apscheduler.triggers.interval import IntervalTrigger
# 259:            trigger=IntervalTrigger(seconds=30),

grep -n "free_entry_impatient\|schedule_free_welcome\|free_entry_welcome" handlers/free_channel_handlers.py
# 58:            text=LucienVoice.free_entry_impatient(),
# 75:            scheduler.schedule_free_welcome(user.id, channel.id)
# 147:                text=LucienVoice.free_entry_welcome(channel.channel_name),
```

## Self-Check: PASSED

- [x] handlers/free_channel_handlers.py exists and contains required changes
- [x] services/scheduler_service.py contains required components
- [x] Commit d82e88d exists in git log
- [x] All acceptance criteria met

## Next Steps

The ritualized Free channel entry flow is complete. The system now:
1. Schedules a 30-second delayed ritual welcome message with social links
2. Sends an impatience message immediately if user requests again while pending
3. Approves pending requests every 30 seconds via IntervalTrigger
4. Sends the ritual welcome message with invite link upon approval
