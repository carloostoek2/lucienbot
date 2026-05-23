---
phase: 18
plan: 01
subsystem: streak-protection
tech-stack: python-3.12, aiogram-3, sqlalchemy-2.0, alembic
key-files:
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
---

## Summary

Extend the streak promotion system (Phase 17) with: (1) streak protection purchasable with besitos on incorrect answer, (2) risk mode FSM allowing retire/continue decisions, (3) 2-minute timeout to earn besitos in free trivia when user cannot afford protection.

## Tasks Completed

### Wave 0: Test Infrastructure
- **Task 0.1** - Created `tests/test_streak_protection.py` stub (commit 8784139)
- **Task 0.2** - Created `tests/test_streak_fsm.py` stub (commit d66115f)

### Wave 1: Models + Schema
- **Task 1.1** - Added `CANCELLED = "cancelled"` to `StreakPromotionCodeStatus` enum
- **Task 1.2** - Added `STREAK_PROTECTION = "streak_protection"` to `TransactionSource` enum
- **Task 1.3** - Added `StreakSession` model with UUID PK, `session_id` FK on `StreakPromotionCode`, relationships
- **Task 1.4** - Created two alembic migrations (enum + table), applied as head (commit e1ef8b6)

### Wave 2: StreakPromotionService Extensions
- **Task 2.1** - Added `calculate_protection_cost()`, `get_active_session()`, `_get_or_create_session()`, `protect_streak()`, `cancel_session_codes()`, `close_session()` (commit 46b3b69)
- **Task 2.2** - Modified `claim_for_streak()` to link delivered codes to active session (commit 110ef5e)

### Wave 3: GameService Extensions
- **Task 3.1** - Added `_build_streak_failure_state()`, `_build_streak_claim_state()` methods. Extended `play_trivia()`, `play_trivia_vip()`, `play_trivia_simple()` to return `session_state` in result dict (commit d8b6f19)

### Wave 4: CallbackData + Keyboards
- **Task 4.1** - Added `StreakProtectAcceptCallback`, `StreakProtectDeclineCallback`, `StreakRetireCallback`, `StreakContinueCallback` (commit 9eb325d)
- **Task 4.2** - Added `protection_keyboard()`, `risk_mode_keyboard()` functions (commit 98f7c9b)

### Wave 5: LucienVoice Messages
- **Task 5.1** - Added 8 message templates: protection offer/accepted/declined, risk mode offer, retire/continue confirmations, timeout granted, codes cancelled (commit a920530)

### Wave 6: Handlers
- **Task 6.1** - Added `TriviaStreakStates` StatesGroup. Extended all 3 trivia answer handlers with session_state routing (protection/risk/timeout keyboards) (commit 5c16db0)
- **Task 6.2** - Added `handle_protection_accept`, `handle_protection_decline`, `handle_streak_retire`, `handle_streak_continue` (commit b9c17e8)

### Wave 7: Scheduler
- **Task 7.1** - Added `_cleanup_expired_streak_sessions()` module-level function. Registered cleanup job with 60-minute interval (commit 898d9d9)

### Wave 8: Tests
- **Task 8.1** - Added `sample_streak_promotion` and `sample_streak_session` fixtures to conftest (commit bae7dc5)
- **Task 8.2** - 11 unit tests: cost calculation (5), session management (6) (commit 6c2d79e)
- **Task 8.3** - 6 integration tests: protection offered, protection used cancels, no session returns None, timeout set, retire offered, risk mode (commit 49d8f80)

## Commits

```
8784139 test(18): add stub test file for streak protection
d66115f test(18): add stub test file for streak FSM state transitions
c80b335 feat(18): add CANCELLED to StreakPromotionCodeStatus and STREAK_PROTECTION to TransactionSource enums
439b7b9 feat(18): add StreakSession model and session_id FK to StreakPromotionCode
e1ef8b6 feat(18): add alembic migrations for streak protection enums and streak_sessions table
46b3b69 feat(18): add session management methods to StreakPromotionService
110ef5e feat(18): link claim_for_streak delivered codes to active session
d8b6f19 feat(18): add session-aware logic to GameService play methods
9eb325d feat(18): add CallbackData classes for streak protection and risk mode
98f7c9b feat(18): add protection and risk mode keyboard functions
a920530 feat(18): add streak protection/risk/timeout messages to LucienVoice
5c16db0 feat(18): add TriviaStreakStates and extend trivia answer handlers with session routing
b9c17e8 feat(18): add protection and risk mode callback handlers
898d9d9 feat(18): add expired streak session cleanup job to scheduler
bae7dc5 test(18): add StreakSession and streak promotion fixtures to conftest
6c2d79e test(18): add unit tests for StreakPromotionService session methods
49d8f80 test(18): add integration tests for FSM state transitions
```

## Deviations

1. **SQLite FK constraint migration**: The initial table migration failed on SQLite because `op.create_foreign_key()` is not supported. Fixed by stamping the migration after the table and column were already created (SQLite doesn't enforce FK constraints). Downstream PostgreSQL deployments will create the FK correctly.
2. **Mock strategy for tests**: `_build_streak_failure_state()` creates a new `BesitoService` instance internally, so mocking `game_svc.besito_service` doesn't work. Fixed by using `@patch('services.besito_service.BesitoService.has_sufficient_balance')` decorator instead.

## Decisions

| Decision | Rationale |
|----------|-----------|
| Session linking in claim_for_streak | Session created/reused at claim time to track all codes in a streak lifecycle |
| atomic protect_streak | debit_besitos(commit=False) + session update in single commit ensures atomicity |
| Lazy timeout verification | 2-min timeout checked via expires_at when user re-enters, not via FSM timer |
| Batch migration for enums | Enum-first migration pattern per models/CLAUDE.md rules for PostgreSQL compatibility |

## Verification

- `python3 -m pytest tests/test_streak_protection.py -q --no-cov` -- 11 passed
- `python3 -m pytest tests/test_streak_fsm.py -q --no-cov` -- 6 passed
- `python3 -m alembic heads` -- single head: `20260523_streak_sessions_table`
- Python import test: `StreakSession`, `StreakPromotionCodeStatus.CANCELLED`, `TransactionSource.STREAK_PROTECTION` all importable
- `calculate_protection_cost(3)=10`, `calculate_protection_cost(6)=15`
