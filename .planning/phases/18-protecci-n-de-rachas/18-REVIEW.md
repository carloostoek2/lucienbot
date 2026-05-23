---
phase: 18-protecci-n-de-rachas
reviewed: 2026-05-23T14:30:00Z
depth: standard
files_reviewed: 13
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
  - tests/conftest.py
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 18: Code Review Report — Proteccion de Rachas

**Reviewed:** 2026-05-23T14:30:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

The streak protection implementation introduces new models (StreakSession, StreakPromotion), a new service (StreakPromotionService), and integrates with existing game flow (GameService) and handlers. The architecture is sound overall, but there are two critical bugs that break core functionality of the timeout mechanism and transaction integrity during code pre-generation. Several migration/model inconsistencies and quality issues are also present.

---

## Critical Issues

### CR-01: `get_active_session` filter breaks timeout mechanism entirely

**File:** `services/streak_promotion_service.py:240-258`
**Issue:** `get_active_session()` filters for `StreakSession.expires_at == None` at line 248. However, when `_build_streak_failure_state` (game_service.py:848-849) sets `session.expires_at` to `now + 2 minutes` to grant a timeout, the session becomes invisible to `get_active_session()` on subsequent calls. This means:

- `_get_or_create_session` (line 260) calls `get_active_session`, finds nothing, and creates a **brand new session**, completely bypassing the timeout.
- The `if session.expires_at and now > session.expires_at` check at line 254 is **dead code** — it can never be true because the query already filtered `expires_at == None`.
- The timed-out session is orphaned, and its codes are only cleaned up later by the 60-minute scheduler job (`_cleanup_expired_streak_sessions`).

**Impact:** Any user who receives a 2-minute timeout can immediately continue playing with a fresh session. The timeout mechanism is entirely ineffective.

**Fix:** Remove the `expires_at == None` filter from `get_active_session`. The method should find ANY active session for the user (including those with a future `expires_at`), then check the expiration:

```python
def get_active_session(self, user_id: int) -> Optional[StreakSession]:
    db = self._get_db()
    now = datetime.now(timezone.utc)
    session = (
        db.query(StreakSession)
        .filter(
            StreakSession.user_id == user_id,
        )
        .order_by(StreakSession.started_at.desc())
        .first()
    )
    if not session:
        return None
    if session.expires_at and now > session.expires_at:
        self.cancel_session_codes(session.id)
        self.close_session(user_id, retire=False)
        return None
    return session
```

There is a design question: should there be only one active session per user? If so, enforce uniqueness at the application level or add a unique constraint (which may require a new boolean column like `is_active`). Currently, without the filter, all old sessions will be returned. The `order_by(...started_at.desc()).first()` pattern above picks the most recent session, which is the simplest fix. A more robust approach would add an `is_active` boolean column.

### CR-02: `_pre_generate_codes` rollback destroys parent transaction

**File:** `services/streak_promotion_service.py:54-82`

**Issue:** When `_pre_generate_codes` encounters a code collision (IntegrityError on the `code_value` unique constraint), it calls `db.rollback()` at line 74. This rolls back the **entire** current transaction, which includes:
- The `promotion` insert (flushed at line 99 in `create_promotion`)
- The `level` insert (flushed at line 108 in `create_promotion`)
- Any successfully inserted codes from earlier iterations

After the rollback, the `level` object is in a detached state (its DB identity was rolled back), but `level.id` still holds the old value. Subsequent retries create `StreakPromotionCode` objects referencing that now-nonexistent `level_id`, which will fail with a foreign key violation.

**Impact:** If a code collision occurs (extremely rare but possible with `secrets.token_hex(6)`), the entire promotion creation fails and the database is left in an inconsistent state. The `create_promotion` method at line 110 then calls `db.commit()`, which may commit garbage or nothing at all depending on the session state.

**Fix:** Use a savepoint (nested transaction) instead of a full rollback:

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
        code = StreakPromotionCode(
            level_id=level.id,
            code_value=code_value,
            status=StreakPromotionCodeStatus.AVAILABLE,
        )
        db.add(code)
        try:
            db.flush()
            generated += 1
        except IntegrityError:
            db.rollback()  # <-- PROBLEM: rolls back entire transaction
```

Replace with a savepoint:

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
        code = StreakPromotionCode(
            level_id=level.id,
            code_value=code_value,
            status=StreakPromotionCodeStatus.AVAILABLE,
        )
        db.add(code)
        try:
            with db.begin_nested():
                db.flush()
            generated += 1
        except IntegrityError:
            logger.warning(...)
```

Alternatively, since collisions are extremely rare with 12 random hex chars, simply generate a new code and retry the flush without a rollback — the broken code object is local and can be replaced:

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
            logger.warning(...)
```

---

## Warnings

### WR-01: Missing ForeignKey constraint on `streak_sessions.promotion_id` in migration

**File:** `alembic/versions/20260523_streak_sessions_table.py:19-37`
**File:** `models/models.py:1238`

**Issue:** The `StreakSession` model at models.py:1238 declares `promotion_id = Column(Integer, ForeignKey("streak_promotions.id"), nullable=False)`, but the migration at `20260523_streak_sessions_table.py` creates the column without the foreign key:

```python
sa.Column('promotion_id', sa.Integer(), nullable=False),
```

Compare how the `session_id` FK on `streak_promotion_codes` IS properly added via `batch_op.create_foreign_key` (lines 33-36). The `promotion_id` FK is entirely missing from the migration.

**Impact:** In production PostgreSQL, no referential integrity is enforced for `streak_sessions.promotion_id` -> `streak_promotions.id`. Orphaned session rows can exist if a promotion is deleted.

**Fix:** Add the foreign key to the migration:

```python
with op.batch_alter_table('streak_sessions', schema=None) as batch_op:
    batch_op.create_foreign_key(
        'fk_streak_sessions_promotion',
        'streak_promotions',
        ['promotion_id'], ['id']
    )
```

### WR-02: Dead `question_idx` field in streak protection callbacks

**Files:**
- `keyboards/callback_data.py:620-629` (both `StreakProtectAcceptCallback` and `StreakProtectDeclineCallback`)
- `keyboards/inline_keyboards.py:543-554` (`protection_keyboard`)
- `handlers/game_user_handlers.py:486-528` (both `handle_protection_accept` and `handle_protection_decline`)

**Issue:** `StreakProtectAcceptCallback` and `StreakProtectDeclineCallback` both define a `question_idx: int` field, and `protection_keyboard` passes it in the callback data. However, none of the handlers that receive these callbacks ever read `question_idx`. The field is serialized into the callback payload for no benefit, bloating the callback data string unnecessarily.

**Fix:** Remove `question_idx` from both callback classes and from `protection_keyboard`:

```python
class StreakProtectAcceptCallback(CallbackData, prefix="streak_protect_accept"):
    streak: int

class StreakProtectDeclineCallback(CallbackData, prefix="streak_protect_decline"):
    streak: int
```

And update `protection_keyboard` to not pass `question_idx`.

### WR-03: Hardcoded path in conftest.py prevents portability

**File:** `tests/conftest.py:13`

**Issue:** The sys.path insertion at line 13 uses a hardcoded path:
```python
sys.path.insert(0, '/data/data/com.termux/files/home/repos/lucien_bot')
```

This path is specific to a Termux environment on a single developer's device. This will prevent tests from running on any other machine, CI server, or developer workstation. The test file's imports rely on this path to find the project modules.

**Fix:** Use a relative path derived from the test file location:

```python
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
```

### WR-04: Duplicate fixture definitions override each other silently

**File:** `tests/conftest.py`
- `sample_package`: lines 276-289 AND lines 479-492 (different `store_stock` defaults: 10 vs -1)
- `sample_promotion`: lines 309-323 AND lines 495-509
- `sample_reaction_emoji`: lines 327-338 AND lines 513-524 (different `besito_value`: 1 vs 5)
- `sample_broadcast_message`: lines 341-354 AND lines 527-540

**Issue:** pytest does not allow duplicate fixture names. The second definition silently overrides the first. Any test that depends on `sample_package` with `store_stock=10` will unexpectedly get `store_stock=-1` because the second definition (line 479) wins. This changes the behavior of tests that rely on stock decrement logic.

**Impact:** Subtle test failures or false passes. A test expecting limited stock behavior will get unlimited stock behavior.

**Fix:** Remove the duplicate fixture definitions. Keep only the version that reflects the most common test scenario, or better, make separate fixtures with distinct names (e.g., `sample_package_limited_stock`, `sample_package_unlimited_stock`).

### WR-05: Direct `db.commit()` called from handler code

**File:** `handlers/game_user_handlers.py:559-559`

**Issue:** In `handle_streak_continue`, the handler calls `promo_svc.db.commit()` directly:
```python
with get_service(StreakPromotionService) as promo_svc:
    session = promo_svc.get_active_session(user_id)
    if session:
        session.is_in_risk_mode = True
        promo_svc.db.commit()  # <-- direct commit from handler
```

Per the architecture rules (`handlers/CLAUDE.md`): handlers must **not** access the database. While this goes through a service attribute, it still performs a write operation from the handler layer. The commit should be handled by the service itself via a dedicated method.

**Fix:** Add a `set_risk_mode` method to `StreakPromotionService`:

```python
def set_risk_mode(self, user_id: int) -> bool:
    session = self.get_active_session(user_id)
    if not session:
        return False
    session.is_in_risk_mode = True
    self.db.commit()
    return True
```

Then the handler simply calls `promo_svc.set_risk_mode(user_id)`.

---

## Info

### IN-01: TriviaStreakStates FSM states defined but never used

**File:** `handlers/game_user_handlers.py:41-43`

**Issue:** The `TriviaStreakStates` class defines `waiting_protection_choice` and `waiting_retire_choice` states, but no handler ever sets or checks FSM states. The entire protection flow operates via direct session updates without FSM state management, leaving the FSM states as dead code.

**Fix:** Either implement FSM state transitions (set state before showing protection/risk-mode keyboard, check/clear state when handling responses) or remove the unused FSM states.

### IN-02: `streak_codes_cancelled(0)` hardcoded in all handler calls

**Files:**
- `handlers/game_user_handlers.py:209`
- `handlers/game_user_handlers.py:319`
- `handlers/game_user_handlers.py:465`

**Issue:** All handler invocations of `LucienVoice.streak_codes_cancelled()` pass a hardcoded `0` for the `code_count` parameter. The resulting message says "Los 0 codigo(s)..." regardless of how many codes were actually cancelled. This is misleading to the user.

**Fix:** Return the count of cancelled codes from `cancel_session_codes` and pass it to the voice method:

```python
def cancel_session_codes(self, session_id: uuid.UUID) -> int:
    """Returns number of codes cancelled."""
    ...
    return cancelled
```

### IN-03: `claimed_in_risk` session_state action not handled explicitly in handlers

**Files:**
- `handlers/game_user_handlers.py:176-213` (trivia_answer)
- `handlers/game_user_handlers.py:285-323` (trivia_vip_answer)
- `handlers/game_user_handlers.py:431-469` (trivia_simple_answer)

**Issue:** The `_build_streak_claim_state` service method can return `{"action": "claimed_in_risk"}` (when the user is already in risk mode and claims another code). None of the three handler methods have a branch for this action, so it falls through to the default message display. While the promo code line IS still shown in the default message (because `_build_trivia_message_parts` renders it from the `promo_code` dict), the session_state branching infrastructure implies an intent to handle it specially. The mismatch can confuse future maintainers.

**Fix:** Either add an explicit handler branch for `claimed_in_risk` (even if it just shows the normal result) or document in the service method that `claimed_in_risk` is intentionally consumed by the normal message flow.

---

_Reviewed: 2026-05-23T14:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
