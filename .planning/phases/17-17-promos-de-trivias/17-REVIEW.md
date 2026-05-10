---
phase: 17-17-promos-de-trivias
reviewed: 2026-05-10T06:30:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - bot.py
  - handlers/__init__.py
  - handlers/trivia_streak_admin_handlers.py
  - keyboards/inline_keyboards.py
  - services/game_service.py
  - tests/integration/test_streak_promotion_handler.py
  - tests/unit/test_streak_promotion_service.py
findings:
  critical: 0
  warning: 5
  info: 2
  total: 7
status: fixed
---

# Phase 17: Code Review Report

**Reviewed:** 2026-05-10T06:30:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Reviewed Phase 17 (Promociones por Racha de Trivia) implementation. CR-01 and CR-02 from the previous review have been successfully fixed -- `GameRecord` is now added before `claim_for_streak` so the shared session commit is atomic, and the null description crash is resolved. Five warnings and two informational items remain unaddressed.

## Critical Issues

None. Previously reported CR-01 (interleaved db.commit) and CR-02 (null description crash) have been resolved.

## Warnings

### WR-01: Race condition in claim_for_streak under concurrent requests

**File:** `services/streak_promotion_service.py:133-186`
**Issue:** The check-then-act pattern between `_has_claimed_level()` (read without row-level locking) and the redemption insert creates a race condition. Two concurrent requests for the same user on the same level can both pass the claim check. Both then acquire separate available codes via `_get_available_code` (uses `with_for_update()` lock on the code row), mark them DELIVERED, and attempt to insert `StreakPromotionRedemption` rows. The `UniqueConstraint` on `StreakPromotionRedemption` prevents duplicate data, but one request receives an `IntegrityError` instead of a graceful "already claimed" result, and one code is marked DELIVERED without a valid redemption record.

**Fix:** Use `with_for_update()` on the `_has_claimed_level` query, or restructure to a single atomic INSERT operation that handles the conflict gracefully.

---

### WR-02: Code collision in _pre_generate_codes is unhandled

**File:** `services/streak_promotion_service.py:45-64`
**Issue:** `_generate_code` uses `secrets.token_hex(6)` producing 12 hex characters (2^48 space). There is no retry or uniqueness verification before inserting. A collision raises an `IntegrityError` that is not caught in `_pre_generate_codes`, aborting the entire `create_promotion` transaction and losing all work done up to that point.

**Fix:** Catch `IntegrityError` in `_pre_generate_codes` and retry on collision, or add a pre-insert uniqueness query with retry loop.

---

### WR-03: Silent exception swallowing in delete_promotion

**File:** `services/streak_promotion_service.py:288-295`
**Issue:** The scheduler cleanup uses a bare `except Exception: pass` which swallows all error types (ImportError, AttributeError, operational failures) without logging. The promotion is already deleted from the DB when the exception is swallowed, leaving stale scheduler jobs.

**Fix:**
```python
except Exception as e:
    logger.warning(
        f"streak_promotion_service - delete_promotion - "
        f"promo_id:{promo_id} - failed to remove jobs: {e}"
    )
```

---

### WR-04: Silent exception swallowing in remove_streak_promotion_jobs

**File:** `services/scheduler_service.py:376-379`
**Issue:** Identical pattern to WR-03. `remove_streak_promotion_jobs` silently catches all exceptions when removing individual job IDs, with no logging. If only one of the two jobs (activate/deactivate) fails to be removed, the caller has no indication of partial failure.

**Fix:**
```python
except Exception as e:
    logger.warning(f"scheduler_service - remove_streak_promotion_jobs - job:{job_id} - error:{e}")
```

---

### WR-05: No validation that at least one game type is selected

**File:** `handlers/trivia_streak_admin_handlers.py:502-517`
**Issue:** In the game type selection step, a user can toggle all three game types to `False` by tapping each toggle button. The "Continuar" button proceeds regardless of the current selection state. The initial default is `{"general": True, "vip": False, "simple": True}`, but toggling general and simple off leaves `{"general": False, "vip": False, "simple": False}`. This creates a promotion where `get_active_promotions` will never match any `game_type`, so no user can ever receive codes from this promotion. The admin must delete and recreate to recover.

**Fix:** In the `if flag == "done":` branch, add validation:
```python
if not any(gt_flag.values()):
    await callback.answer("Seleccione al menos un tipo de juego.", show_alert=True)
    return
```

---

## Info

### IN-01: Duplicate local imports of StreakPromotionService in game_service.py

**File:** `services/game_service.py:762, 1052, 1356`
**Issue:** `StreakPromotionService` is imported locally in three different locations (within `play_trivia`, `play_trivia_vip`, and `play_trivia_simple`). While this avoids a circular dependency, it introduces copy-paste duplication and three separate import resolution points for the same module. The pattern is inconsistent with `from services.trivia_service import TriviaCategoryService` which is imported locally once at the module level (line 1454).

**Fix:** Move the import to the top of the file with the other local imports to match the existing pattern:
```python
from services.trivia_service import TriviaCategoryService  # already at line 1454
from services.streak_promotion_service import StreakPromotionService  # add this
```

---

### IN-02: Redundant session initialization pattern in StreakPromotionService

**File:** `services/streak_promotion_service.py:29-43`
**Issue:** The `_get_db` method checks `if self.db is None` and creates a new `SessionLocal()`, but `__init__` already initializes `self.db = db or SessionLocal()` on line 31. The only path where `self.db` becomes `None` is after `close()` is called. This lazy re-initialization pattern is inconsistently applied -- other services (`BesitoService`, `ChannelService`) do not use this pattern and instead guard `close()` to prevent reuse after close.

**Fix:** Remove `_get_db` indirection and use `self.db` directly, with a guard in `close()` that raises an error on reuse:
```python
def close(self):
    if self.db is None:
        raise RuntimeError("Session already closed")
    if self._owns_session:
        self.db.close()
    self.db = None
```

---

_Reviewed: 2026-05-10T06:30:00Z
_Reviewer: Claude (gsd-code-reviewer)
_Depth: standard_

## Fixes Applied

All warning-level issues have been resolved:

1. **WR-01 (Race condition):** Added `with_for_update()` row lock in `_has_claimed_level()` to prevent concurrent claim race conditions between the check and redemption insert.

2. **WR-02 (Code collision):** Added retry loop with `max_attempts` in `_pre_generate_codes()` to handle `IntegrityError` from duplicate code collisions gracefully instead of aborting the entire transaction.

3. **WR-03 (Silent exception):** Added logging for exceptions in `delete_promotion()` instead of silent `pass` to help diagnose scheduler cleanup issues.

4. **WR-04 (Silent exception):** Added logging for exceptions in `remove_streak_promotion_jobs()` instead of silent `pass`.

5. **WR-05 (Missing validation):** Added validation in game type selection step to ensure at least one game type is selected before allowing promotion creation.

**Commit:** `ea07231`
