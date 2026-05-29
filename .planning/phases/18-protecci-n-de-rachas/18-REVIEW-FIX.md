---
phase: 18-protecci-n-de-rachas
fixed_at: 2026-05-27T00:00:00Z
review_path: .planning/phases/18-protecci-n-de-rachas/18-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 18: Code Review Fix Report

**Fixed at:** 2026-05-27T00:00:00Z
**Source review:** `.planning/phases/18-protecci-n-de-rachas/18-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 6
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: `_pre_generate_codes` rollback destroys parent transaction

**Files modified:** `services/streak_promotion_service.py`
**Commit:** `ae79b6d`
**Applied fix:** Replaced `db.rollback()` with `db.expunge(code)` inside the IntegrityError except block in `_pre_generate_codes`. Instead of rolling back the entire transaction (which also rolls back the parent `promotion` and `level` inserts), the failed `StreakPromotionCode` object is simply expunged from the session, allowing the loop to retry without collateral damage.

### WR-01: Missing ForeignKey constraint on `streak_sessions.promotion_id`

**Files modified:** `alembic/versions/20260523_streak_sessions_table.py`
**Commit:** `f5dae8e`
**Applied fix:** Added `create_foreign_key` for `streak_sessions.promotion_id -> streak_promotions.id` in the migration `upgrade()` function, following the existing pattern used for the `session_id` FK on `streak_promotion_codes`. Added corresponding `drop_constraint` in `downgrade()`.

### WR-02: Timezone inconsistency in `_cleanup_expired_streak_sessions`

**Files modified:** `services/scheduler_service.py`
**Commit:** `9fd2f68`
**Applied fix:** Changed `datetime.now(timezone.utc)` to `datetime.now(timezone.utc).replace(tzinfo=None)` in the cleanup job to match the timezone-naive convention used everywhere else in the codebase for SQLite compatibility.

### IN-01: Duplicate fixture definitions in conftest.py

**Files modified:** `tests/conftest.py`
**Commit:** `6782a28`
**Applied fix:** Removed the duplicate fixture block (4 fixtures: `sample_package`, `sample_promotion`, `sample_reaction_emoji`, `sample_broadcast_message`) that redefined fixtures already defined earlier in the same file. The duplicate definitions had different default parameter values (e.g., `store_stock=-1` vs `store_stock=10`, `besito_value=5` vs `besito_value=1`), and pytest used the last definition, silently changing test behavior.

### IN-02: Dead unreachable code in `game_trivia_simple` handler

**Files modified:** `handlers/game_user_handlers.py`
**Commit:** `ea5c051`
**Applied fix:** Removed two unreachable lines (`await callback.answer()` and `return`) that appeared after a `return` statement in the `question is None` branch of `game_trivia_simple`, which were a copy-paste artifact.

### IN-03: TriviaStreakStates FSM states remain unused

**Files modified:** `handlers/game_user_handlers.py`
**Commit:** `43f37c4`
**Applied fix:** Removed the unused `TriviaStreakStates` class (StatesGroup with `waiting_protection_choice` and `waiting_retire_choice`) since no handler uses FSM state transitions for the protection flow. Also removed the now-unused imports (`FSMContext`, `State`, `StatesGroup`).

---

_Fixed: 2026-05-27T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
