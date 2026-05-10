---
phase: 17-17-promos-de-trivias
reviewed: 2026-05-10T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - models/models.py
  - alembic/versions/36c345796281_add_streak_promotions_tables.py
  - services/streak_promotion_service.py
  - services/scheduler_service.py
  - services/__init__.py
  - services/game_service.py
  - handlers/trivia_streak_admin_handlers.py
  - handlers/__init__.py
  - bot.py
  - keyboards/inline_keyboards.py
  - tests/unit/test_streak_promotion_service.py
  - tests/integration/test_streak_promotion_handler.py
findings:
  critical: 2
  warning: 5
  info: 4
  total: 11
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-05-10
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the Phase 17 (Promociones por Racha de Trivia) implementation across 12 files. The new `StreakPromotionService`, admin handlers, and model definitions are well-structured and follow the project's architectural pattern (handlers route, services contain logic, models define schema). The alembic migration is clean with proper downgrade support.

Two blocking issues were found: (1) the `claim_for_streak` method commits a shared database session prematurely in `GameService`, creating a window where besito credits are persisted without the corresponding `GameRecord`, which corrupts streak calculations and daily play counts; (2) a null reference crash in the admin handlers when a promotion has a null description. Five warnings cover a race condition in concurrent claims, missing exception handling, absent code uniqueness verification, missing game type validation, and silent exception swallowing. Four informational items cover code consistency and style.

## Critical Issues

### CR-01: Interleaved db.commit() in shared session causing partial data persistence

**File:** `services/game_service.py:731-773`, `services/game_service.py:1022-1064`, `services/game_service.py:1328-1368`
**Issue:** In all three trivia play methods (`play_trivia`, `play_trivia_vip`, `play_trivia_simple`), `StreakPromotionService.claim_for_streak()` is called with `GameService`'s session (line 754, 1045, 1350). `claim_for_streak` internally calls `db.commit()` at `services/streak_promotion_service.py:183`, which commits ALL uncommitted state in the shared session -- including the `credit_besitos` calls on lines 731-748 (1022-1039, 1328-1344). The `GameRecord` is then added to the session AFTER this commit (lines 766-772, 1057-1063, 1361-1367) and committed separately (line 773, 1064, 1368).

If the second `self.db.commit()` fails, the `GameRecord` is lost while besito credits, promo code delivery, and redemption records are already permanently persisted. This corrupts streak calculation (`_get_trivia_streak` depends on `GameRecord` order), daily play limits, and the historical record.

**Fix:**
In `services/game_service.py`, add the `GameRecord` to the session BEFORE calling `claim_for_streak`, and remove the redundant second commit. Example for `play_trivia`:

```python
# Move GameRecord creation BEFORE claim_for_streak
record = GameRecord(
    user_id=user_id,
    game_type='trivia',
    result=f"question_{question_idx}",
    payout=besitos + streak_bonus
)
self.db.add(record)

# Phase 17: Streak Promotion check (commits everything including GameRecord)
promo_code_info = None
if is_correct:
    from services.streak_promotion_service import StreakPromotionService
    promo_service = StreakPromotionService(self.db)
    try:
        promo_code_info = promo_service.claim_for_streak(
            user_id=user_id,
            game_type='trivia',
            streak=new_streak,
            category_id=None,
        )
    finally:
        promo_service.close()

# Remove: self.db.add(record)  -- already done above
# Remove: self.db.commit()     -- claim_for_streak already committed
```

Apply the same pattern to `play_trivia_vip` and `play_trivia_simple`.

---

### CR-02: Null pointer crash when promotion.description is None

**File:** `handlers/trivia_streak_admin_handlers.py:88-91`
**Issue:** The `_build_promotions_list` function accesses `promo.description[:50]` and `len(promo.description)` without a null check:

```python
desc_short = promo.description[:50]     # line 89: TypeError if description is None
if len(promo.description) > 50:         # line 90: TypeError if description is None
    desc_short += "..."
```

The `StreakPromotion.description` column is defined as `Column(Text, nullable=True)` in `models/models.py:1135`. When a promotion is created without a description (which the admin wizard allows -- `waiting_description` state requires non-empty text via handler validation at line 181, but data could be created programmatically or via direct DB operations), this crashes the admin promotions menu with an unhandled `TypeError`, preventing the admin from viewing any promotions.

**Fix:**
```python
desc_short = (promo.description or "")[:50]
if promo.description and len(promo.description) > 50:
    desc_short += "..."
```

---

## Warnings

### WR-01: Race condition in claim_for_streak under concurrent requests

**File:** `services/streak_promotion_service.py:133-186`
**Issue:** The check-then-act pattern between `_has_claimed_level()` (line 170, a read without row-level locking) and the redemption insert (line 178) creates a race condition. Two concurrent requests for the same user on the same level can both pass `_has_claimed_level` (no redemption exists yet). Both then acquire separate available codes via `_get_available_code` (uses `with_for_update()` lock on the code row), mark them DELIVERED, and attempt to insert `StreakPromotionRedemption` rows with the same `(user_id, level_id)`. The `UniqueConstraint` on `StreakPromotionRedemption` prevents duplicate data, but one request will receive an `IntegrityError` instead of a graceful "already claimed" result, and one code will be marked DELIVERED without a valid redemption record.

**Fix:** Use `with_for_update()` (or `SELECT ... FOR UPDATE`) on the `StreakPromotionRedemption` query inside `_has_claimed_level`, or restructure the claim logic to use a single atomic operation (e.g., `INSERT ... ON CONFLICT DO NOTHING` or a DB-level function).

---

### WR-02: Code collision in _pre_generate_codes is unhandled

**File:** `services/streak_promotion_service.py:45-64`
**Issue:** `_generate_code` uses `secrets.token_hex(6)` to produce 12 hex characters. While the collision probability is very low (2^48 space), there is no retry or uniqueness verification before inserting. The DB has a unique constraint on `code_value`, so a collision would raise an `IntegrityError` that is not caught in `_pre_generate_codes`, aborting the entire `create_promotion` transaction and losing all work done up to that point. In a promotion with many levels and codes, a single collision anywhere in the loop destroys the entire creation.

**Fix:** Either check uniqueness before inserting (query + retry loop), or catch `IntegrityError` in `_pre_generate_codes` and retry the specific code generation on collision.

---

### WR-03: Silent exception swallowing in delete_promotion

**File:** `services/streak_promotion_service.py:288-295`
**Issue:** The scheduler cleanup in `delete_promotion` uses a bare `except Exception: pass`:

```python
try:
    from services.scheduler_service import get_scheduler
    scheduler = get_scheduler()
    if scheduler:
        scheduler.remove_streak_promotion_jobs(promo_id)
except Exception:
    pass
```

This swallows all error types including `ImportError` (if `scheduler_service` is renamed/removed), `AttributeError` (if the method is renamed), and operational failures. The promotion is already deleted from the DB by this point, but stale scheduler jobs remain without any logging.

**Fix:** At minimum, log the exception:
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
**Issue:** Identical pattern to WR-03. `remove_streak_promotion_jobs` catches all exceptions silently when removing individual job IDs:

```python
for job_id in (f"streak_promo_activate_{promo_id}", f"streak_promo_deactivate_{promo_id}"):
    try:
        self._scheduler.remove_job(job_id)
    except Exception:
        pass
```

If only one of the two jobs fails, the other is removed, but the caller has no indication of partial failure.

**Fix:** Log each failure and consider collecting errors for the caller:
```python
except Exception as e:
    logger.warning(f"scheduler_service - remove_streak_promotion_jobs - job:{job_id} - error:{e}")
```

---

### WR-05: No validation that at least one game type is selected

**File:** `handlers/trivia_streak_admin_handlers.py:496-532`
**Issue:** In the game type selection step, a user can toggle all three game types (general, simple, VIP) to `False` by tapping each toggle button. The "Continuar" button (line 502) proceeds regardless of the current selection state. The default initial state is `{"general": True, "vip": False, "simple": True}`, but toggling general and simple off leaves `{"general": False, "vip": False, "simple": False}`. This creates a promotion where `get_active_promotions` will never match any `game_type`, so no one can ever receive codes from this promotion. The admin would need to delete and recreate to fix it.

**Fix:** In the `if flag == "done":` branch (line 502), add a validation check:
```python
if flag == "done":
    if not any(gt_flag.values()):
        await callback.answer("Seleccione al menos un tipo de juego.", show_alert=True)
        return
    ...
```

---

## Info

### IN-01: category_admin_handlers not listed in handlers/__init__.py

**File:** `bot.py:54`, `handlers/__init__.py`
**Issue:** `bot.py` imports `category_admin_handlers` from the `handlers` package, and uses `dp.include_router(category_admin_handlers.router)` at line 267. While the import works (Python resolves `handlers/category_admin_handlers.py` as a submodule), it is not listed in `handlers/__init__.py`'s imports or `__all__`, unlike every other router in the codebase. This inconsistency makes the import graph harder to understand and could cause confusion during refactoring.

**Fix:** Add the import to `handlers/__init__.py`:
```python
from .category_admin_handlers import router as category_admin_router
```
And add `'category_admin_router'` to `__all__`. Then update `bot.py` to use the imported name.

---

### IN-02: Redundant session initialization in _get_db

**File:** `services/streak_promotion_service.py:33-37`
**Issue:** The `_get_db` method checks `if self.db is None` and creates a new `SessionLocal()`, but `__init__` (line 31) already initializes `self.db = db or SessionLocal()`. The only path where `self.db` becomes `None` is after `close()` is called (line 43). This lazy re-initialization pattern is inconsistently applied -- `BesitoService`, `ChannelService`, and other services in the project do not use this pattern.

**Fix:** Either consistently apply this pattern across all services, or remove the `_get_db` indirection and use `self.db` directly with a guard in `close()` that prevents reuse after close.

---

### IN-03: Magic number in _generate_code

**File:** `services/streak_promotion_service.py:47`
**Issue:** `secrets.token_hex(6)` uses a hardcoded `6` with no documented rationale. This generates 12 hex characters of randomness (2^48 space). While adequate for most use cases, the size choice is arbitrary and undocumented.

**Fix:** Extract to a named constant with a comment explaining the tradeoff:
```python
CODE_RANDOM_BYTES = 6  # 12 hex chars, ~2.8e14 possible values -- sufficient for <1M codes
```

---

### IN-04: Unnecessary re-fetch in streak_promo_toggle

**File:** `handlers/trivia_streak_admin_handlers.py:700-716`
**Issue:** In `streak_promo_toggle`, the handler fetches the promotion with `service.get_promotion(promo_id)`, toggles its state via `service.pause_promotion()` or `service.activate()`, then calls `await streak_promo_view(callback)` which re-fetches the same promotion from the database. This doubles the database queries for no benefit.

**Fix:** Pass the already-loaded promotion object to `streak_promo_view` or inline the view logic to avoid the second query.

---

_Reviewed: 2026-05-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
