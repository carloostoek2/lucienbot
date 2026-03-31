---
phase: 10-flujos-de-entrada-docs-req-fase10-md
plan: 03
subsystem: VIP
milestone: Ritualized VIP Entry Flow
tags: [vip, entry-flow, ritual, callbacks]
dependency_graph:
  requires: [10-01]
  provides: [vip-entry-ritual-complete]
  affects: [handlers/common_handlers.py, handlers/vip_handlers.py, services/vip_service.py]
tech_stack:
  added: []
  patterns: [3-phase ritual, state persistence, expiration guard]
key_files:
  created: []
  modified:
    - services/vip_service.py
    - handlers/common_handlers.py
    - handlers/vip_handlers.py
decisions:
  - VIP entry state stored in User model (vip_entry_status, vip_entry_stage)
  - Invite link generated ONLY in Phase 3 (vip_entry_ready callback)
  - Expired subscriptions clear state and show expiration message
  - Repeat clicks guarded by checking pending_entry status
  - member_limit=1 for one-time invite links
metrics:
  duration: "45 minutes"
  completed_at: "2026-03-31"
  tasks_completed: 3
  files_modified: 3
  lines_added: ~180
---

# Phase 10 Plan 03: Ritualized VIP Entry Flow Summary

**One-liner:** Implemented 3-phase ritualized VIP entry flow with state persistence, stage advancement callbacks, and expiration guards.

## What Was Built

### 1. VIPService Entry State Management (services/vip_service.py)

Extended VIPService with 6 new methods to manage the ritualized entry flow:

- **`redeem_token()`** - Now sets `vip_entry_status="pending_entry"` and `vip_entry_stage=1` after successful token redemption
- **`get_vip_entry_state(user_id)`** - Returns `(status, stage)` tuple for resuming interrupted flows
- **`advance_vip_entry_stage(user_id)`** - Increments stage (max 3), returns new stage or None
- **`clear_vip_entry_state(user_id)`** - Resets both fields when subscription expires or ritual completes
- **`get_active_subscription_for_entry(user_id)`** - Returns active subscription or None (expiration guard)
- **`complete_vip_entry(user_id)`** - Sets status="active", clears stage after successful entry

### 2. /start Resumption Guard (handlers/common_handlers.py)

Modified `cmd_start()` to:

1. **Check for pending_entry BEFORE token processing** - Users resuming the ritual are handled first
2. **Resume from appropriate stage:**
   - Stage 1: Sends `vip_entry_stage_1()` with `vip_entry_continue_keyboard()`
   - Stage 2: Sends `vip_entry_stage_2()` with `vip_entry_ready_keyboard()`
   - Stage 3: Sends `vip_entry_stage_3()`, generates invite link, calls `complete_vip_entry()`
3. **Handle expired subscriptions** - Clears state and shows `free_entry_expired()` message
4. **Start ritual on token redemption** - Instead of immediate link delivery, sends Stage 1 ritual

### 3. VIP Entry Callbacks (handlers/vip_handlers.py)

Added two callback handlers:

**`vip_entry_continue` (Phase 1→2):**
- Guards against repeat clicks (checks `pending_entry` status)
- Guards against expired subscriptions
- Advances to stage 2
- Sends `vip_entry_stage_2()` with `vip_entry_ready_keyboard()`

**`vip_entry_ready` (Phase 2→3):**
- Guards against repeat clicks
- Guards against expired subscriptions
- Advances to stage 3
- Sends `vip_entry_stage_3()`
- Generates invite link with `member_limit=1`
- Calls `complete_vip_entry()` to finalize

## Verification Results

- **Import smoke test:** PASSED - No circular imports
- **Unit tests:** 28/28 passed in `test_vip_service.py`
- **Acceptance criteria:** All met

## Deviations from Plan

None - plan executed exactly as written.

## Key Implementation Details

### Expiration Guard Pattern
Both callbacks and `/start` resumption check subscription validity:
```python
subscription = vip_service.get_active_subscription_for_entry(user.id)
if not subscription:
    vip_service.clear_vip_entry_state(user.id)
    # Show expiration message
    return
```

### Repeat Click Guard Pattern
All entry points check status first:
```python
status, _ = vip_service.get_vip_entry_state(user.id)
if status != "pending_entry":
    await callback.answer("El ritual ya ha sido completado.")
    return
```

### Invite Link Security
- Generated ONLY in Phase 3 (never during token redemption)
- Uses `member_limit=1` for one-time use
- Falls back to stored channel invite_link if generation fails

## Commits

1. `e3374f8` - feat(phase-10-03): add VIP entry state management methods
2. `089cdea` - feat(phase-10-03): modify cmd_start to detect and resume VIP entry ritual
3. `4389368` - feat(phase-10-03): add VIP entry ritual callbacks

## Self-Check: PASSED

- [x] services/vip_service.py contains all 6 new methods
- [x] handlers/common_handlers.py checks pending_entry before token processing
- [x] handlers/vip_handlers.py contains both callback handlers
- [x] All imports resolve correctly
- [x] No circular imports
- [x] All existing tests pass
