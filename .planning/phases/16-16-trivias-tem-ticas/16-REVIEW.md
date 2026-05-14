---
phase: 16-16-trivias-tem-ticas
reviewed: 2026-05-14T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - keyboards/callback_data.py
  - keyboards/inline_keyboards.py
  - handlers/trivia_admin_handlers.py
  - handlers/trivia_config_admin_handlers.py
  - handlers/trivia_streak_admin_handlers.py
  - handlers/game_user_handlers.py
  - handlers/gamification_admin_handlers.py
  - handlers/gamification_user_handlers.py
  - handlers/reward_admin_handlers.py
  - handlers/reward_user_handlers.py
findings:
  critical: 1
  warning: 5
  info: 0
  total: 6
status: issues_found
---
# Phase 16: Code Review Report

**Reviewed:** 2026-05-14T00:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed trivia-related handlers, keyboard configurations, and gamification code. Found one critical type mismatch bug that would cause a runtime error, plus several resource leaks and architectural inconsistencies.

## Critical Issues

### CR-01: Type mismatch in `streak_promo_toggle` callback

**File:** `handlers/trivia_streak_admin_handlers.py:727`
**Issue:** The function `streak_promo_view` expects a `TriviaStreakDetailCallback` object as second parameter, but line 727 passes a **packed string** instead.

```python
# Line 727 - BUG: passing string instead of CallbackData object
await streak_promo_view(callback, TriviaStreakDetailCallback(promo_id=promo_id).pack())

# Definition at line 652-668 shows it expects:
async def streak_promo_view(callback: CallbackQuery, callback_data: TriviaStreakDetailCallback):
    promo_id = callback_data.promo_id  # This would fail at runtime
```

**Fix:**
```python
# Should pass the callback object directly, not packed
await streak_promo_view(callback, TriviaStreakDetailCallback(promo_id=promo_id))
```

## Warnings

### WR-01: Resource leak - `BroadcastService` not closed in `config_besitos_menu`

**File:** `handlers/gamification_admin_handlers.py:97-101`
**Issue:** `config_besitos_menu` creates `BroadcastService()` but never calls `close()`. Other handlers in the same file use try/finally pattern correctly (see lines 367-371, 463-465).

```python
@router.callback_query(F.data == "config_besitos", lambda cb: is_admin(cb.from_user.id))
async def config_besitos_menu(callback: CallbackQuery):
    broadcast_service = BroadcastService()
    try:
        emojis = broadcast_service.get_all_emojis(active_only=False)
    finally:
        broadcast_service.close()  # Missing! Should follow pattern from other functions
```

**Fix:** Add try/finally or use context manager:
```python
async def config_besitos_menu(callback: CallbackQuery):
    broadcast_service = BroadcastService()
    try:
        emojis = broadcast_service.get_all_emojis(active_only=False)
    finally:
        broadcast_service.close()
```

### WR-02: Resource leak - `BroadcastService` not closed in FSM handlers

**File:** `handlers/gamification_admin_handlers.py:246-248, 293-294, 310-312, 343-345`
**Issue:** Multiple functions create `BroadcastService()` instances without closing them:
- `edit_emoji` (line 246-248)
- `toggle_emoji` (line 293-294)
- `change_emoji_value_start` (line 310-312)
- `process_emoji_value_edit` (line 343-345)

All four functions instantiate the service directly and use it without try/finally cleanup.

**Fix:** Either use context manager (`with get_service(BroadcastService) as ...`) or add proper try/finally cleanup.

### WR-03: Resource leak - `BesitoService` not closed in `gamification_stats`

**File:** `handlers/gamification_admin_handlers.py:466-467`
**Issue:** `gamification_stats` creates `BesitoService()` and `DailyGiftService()` without closing them.

```python
besito_service = BesitoService()
gift_service = DailyGiftService()
# ... uses services ...
# Missing close() calls
```

**Fix:** Use context manager pattern or add try/finally blocks.

### WR-04: Inconsistent service instantiation pattern

**File:** `handlers/gamification_admin_handlers.py`
**Issue:** Mixed patterns for service access:
- Some functions use context manager: `with get_service(TriviaCategoryService) as service:`
- Others use direct instantiation: `broadcast_service = BroadcastService()` then `broadcast_service.close()`

This inconsistency makes the code harder to maintain and increases risk of resource leaks.

**Fix:** Standardize on `get_service()` context manager pattern throughout.

### WR-05: Lambda filter repetition across handler files

**File:** `handlers/trivia_streak_admin_handlers.py`, `handlers/trivia_admin_handlers.py`, `handlers/trivia_config_admin_handlers.py`, `handlers/gamification_admin_handlers.py`, `handlers/reward_admin_handlers.py`
**Issue:** `is_admin` is defined as a local function in every handler file:
```python
def is_admin(user_id: int) -> bool:
    return user_id in bot_config.ADMIN_IDS
```

This duplication violates DRY principle and could lead to inconsistencies if `bot_config.ADMIN_IDS` access pattern changes.

**Fix:** Consider creating a shared utility module for common checks like `is_admin()`.

---

## Info

_No info-level findings._

---

_Reviewed: 2026-05-14T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_