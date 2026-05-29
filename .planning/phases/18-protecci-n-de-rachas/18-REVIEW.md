---
phase: 18-protecci-n-de-rachas
reviewed: 2026-05-27T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - models/models.py
  - services/streak_promotion_service.py
  - services/game_service.py
  - services/scheduler_service.py
  - handlers/game_user_handlers.py
  - keyboards/callback_data.py
  - keyboards/inline_keyboards.py
  - utils/lucien_voice.py
  - alembic/versions/20260523_streak_protection_enums.py
  - alembic/versions/20260523_streak_sessions_table.py
  - tests/test_streak_protection.py
  - tests/test_streak_fsm.py
findings:
  critical: 1
  warning: 2
  info: 3
  total: 6
status: issues_found
---

# Phase 18: Code Review Report -- RE-review

**Reviewed:** 2026-05-27T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

This is a RE-review following commits dabe16b, e02ecaa, cc2e344, 1d1ac61, and 93bdb42 that addressed issues from the original review on 2026-05-23.

**Of the 10 previously-identified issues, 4 are fixed and 6 remain unresolved:**

Fixed: CR-01 (timeout filter), WR-02 (dead question_idx), WR-05 (direct db.commit in handler), IN-02 (hardcoded code_count=0).

Not fixed: CR-02 (rollback in _pre_generate_codes), WR-01 (missing FK in migration), WR-03 (hardcoded path in conftest.py), WR-04 (duplicate fixtures), IN-01 (unused FSM states), IN-03 (claimed_in_risk not handled).

One new Warning was introduced (timezone inconsistency in cleanup) and one new Info finding (dead code after return).

---

## Critical Issues

### CR-01: `_pre_generate_codes` rollback destroys parent transaction (REOPENED -- NOT FIXED)

**File:** `services/streak_promotion_service.py:74`
**Issue:** When `_pre_generate_codes` encounters an `IntegrityError` on the `code_value` unique constraint, it calls `db.rollback()` at line 74. This rolls back the **entire** current transaction, which includes:

- The `promotion` insert (flushed at line 99 in `create_promotion`)
- The `level` insert (flushed at line 108 in `create_promotion`)
- Any successfully inserted codes from earlier iterations

After the rollback, the `level` object is in a detached state (its DB identity was rolled back), but `level.id` still holds the old value. Subsequent retries create `StreakPromotionCode` objects referencing that now-nonexistent `level_id`, which will fail with a foreign key violation.

NOTE: The fix suggested in the original review on 2026-05-23 was **not applied**. The `db.rollback()` is still present at line 74.

**Impact:** If a code collision occurs (extremely rare but possible with `secrets.token_hex(6)`), the entire promotion creation fails and the database is left in an inconsistent state.

**Fix:** Use a savepoint (nested transaction) or expunge the failed object instead of a full rollback:

```python
def _pre_generate_codes(self, level: StreakPromotionLevel, prefix: str = "SK"):
    count = level.codes_available
    db = self._get_db()
    generated = 0
    max_attempts = count * 3
    attempt = 0
    while generated < count and attempt < max_attempts:
        attempt += 1
        code_value = self._generate_code(prefix)
        try:
            code = StreakPromotionCode(
                level_id=level.id,
                code_value=code_value,
                status=StreakPromotionCodeStatus.AVAILABLE,
            )
            db.add(code)
            db.flush()
            generated += 1
        except IntegrityError:
            db.expunge(code)  # remove failed object from session
            logger.warning(
                f"streak_promotion_service - _pre_generate_codes - "
                f"level_id:{level.id} - code collision, retrying"
            )
    logger.info(
        f"streak_promotion_service - _pre_generate_codes - "
        f"level_id:{level.id} - count:{generated}"
    )
```

---

## Warnings

### WR-01: Missing ForeignKey constraint on `streak_sessions.promotion_id` in migration (REOPENED -- NOT FIXED)

**File:** `alembic/versions/20260523_streak_sessions_table.py:24`
**File:** `models/models.py:1238`

**Issue:** The `StreakSession` model declares `promotion_id = Column(Integer, ForeignKey("streak_promotions.id"), nullable=False)`, but the migration creates the column without the foreign key constraint:

```python
sa.Column('promotion_id', sa.Integer(), nullable=False),
```

No `create_foreign_key` call exists for this column, unlike the `session_id` FK on `streak_promotion_codes` which IS properly created at lines 33-36 of the same migration.

**Impact:** In production PostgreSQL, no referential integrity is enforced. Orphaned `StreakSession` rows can exist if a `StreakPromotion` is deleted.

**Fix:** Add the foreign key to the migration:

```python
with op.batch_alter_table('streak_sessions', schema=None) as batch_op:
    batch_op.create_foreign_key(
        'fk_streak_sessions_promotion',
        'streak_promotions',
        ['promotion_id'], ['id']
    )
```

### WR-02: Timezone inconsistency in `_cleanup_expired_streak_sessions` (NEW)

**File:** `services/scheduler_service.py:281`
**File:** `services/streak_promotion_service.py:247, 359, 849`

**Issue:** The cleanup job `_cleanup_expired_streak_sessions` constructs `now` as a timezone-aware datetime:

```python
now = datetime.now(timezone.utc)
```

However, every location that sets `expires_at` strips timezone info:

```python
# streak_promotion_service.py:247 (get_active_session)
now = datetime.now(timezone.utc).replace(tzinfo=None)

# streak_promotion_service.py:359 (close_session)
session.expires_at = datetime.now(timezone.utc).replace(tzinfo=None)

# game_service.py:849 (_build_streak_failure_state)
session.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=2)
```

This means the stored `expires_at` values are naive datetimes but the query uses a timezone-aware `now`. The comparison `StreakSession.expires_at < now` may behave differently depending on database backend:

- **PostgreSQL with TIMESTAMPTZ**: naive timestamps are interpreted as UTC by the driver, so the comparison works correctly.
- **SQLite**: the comparison depends on string representation and may silently fail to match expired sessions.

Commit dabe16b explicitly adopted timezone-naive datetimes for SQLite compatibility. The cleanup job should use the same convention.

**Fix:** Make the cleanup job consistent with the storage convention:

```python
now = datetime.now(timezone.utc).replace(tzinfo=None)
```

---

## Info

### IN-01: Duplicate fixture definitions in conftest.py (REOPENED -- NOT FIXED)

**File:** `tests/conftest.py`

**Issue:** pytest silently uses the last definition when duplicate fixture names exist. Four fixture pairs have different default parameter values:

| Fixture | Line 1 | Line 2 | Value Diff |
|---------|--------|--------|------------|
| `sample_package` | 277 | 480 | `store_stock`: 10 vs -1 |
| `sample_promotion` | 310 | 496 | identical except `price_mxn` format |
| `sample_reaction_emoji` | 327 | 513 | `besito_value`: 1 vs 5 |
| `sample_broadcast_message` | 342 | 528 | second uses `AsyncMock` admin, first uses sample_admin |

The second definition (lines 480-540) always wins. Any test depending on `sample_package` with `store_stock=10` unexpectedly gets `store_stock=-1` (unlimited stock). This changes the behavior of stock decrement logic tests.

**Fix:** Remove the duplicate block (lines 478-540) or rename the second set with distinct fixture names.

### IN-02: Dead unreachable code in `game_trivia_simple` handler (NEW)

**File:** `handlers/game_user_handlers.py:383-384`

**Issue:** Lines 383-384 are unreachable dead code after the `return` statement on line 382:

```python
        if question is None:
            await callback.message.edit_text(
                "Los pergaminos especiales estan en el taller de Lucien.",
                reply_markup=game_menu_keyboard()
            )
            await callback.answer()
            return              # <-- line 382
            await callback.answer()   # <-- DEAD CODE, unreachable
            return                     # <-- DEAD CODE, unreachable
```

This appears to be a copy-paste artifact or unfinished edit. While not a functional bug (the code never executes), it indicates a lack of cleanup and could confuse future maintainers.

**Fix:** Remove lines 383-384.

### IN-03: TriviaStreakStates FSM states remain unused (REOPENED -- NOT FIXED)

**File:** `handlers/game_user_handlers.py:41-43`

**Issue:** The `TriviaStreakStates` class defines `waiting_protection_choice` and `waiting_retire_choice` states, but no handler ever sets or checks FSM state transitions. The protection/retire/continue flow operates entirely through `session_state` dict values from the service layer, bypassing the FSM.

**Fix:** Either implement FSM state management for the protection flow or remove the unused `TriviaStreakStates` class.

---

## Previously Fixed Issues (Verified)

The following issues from the 2026-05-23 review have been successfully resolved:

| Issue | Fix | Verification |
|-------|-----|--------------|
| **CR-01** timeout filter | Removed `expires_at == None` from `get_active_session` filter | Confirmed at `streak_promotion_service.py:250` -- only filters by `user_id`, checks expiration in application logic |
| **WR-02** dead `question_idx` | Removed from callback classes and keyboard | `StreakProtectAcceptCallback` and `StreakProtectDeclineCallback` now only have `streak: int, game_type: str` |
| **WR-05** `db.commit()` in handler | Moved to `StreakPromotionService.set_risk_mode()` | Handler at line 566 calls `promo_svc.set_risk_mode(user_id)`; service method properly encapsulates the commit |
| **IN-02** hardcoded `code_count=0` | Returns actual count from `cancel_session_codes()` | `cancel_session_codes` returns `cancelled` count; handlers use `session_state.get('codes_cancelled', 0)` |

---

_Reviewed: 2026-05-27T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
