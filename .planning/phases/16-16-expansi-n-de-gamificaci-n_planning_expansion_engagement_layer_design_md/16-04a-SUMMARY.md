---
phase: 16
plan: 16-04a
subsystem: whisper-reward-system
tech-stack: Python 3.12, SQLAlchemy 2.0, Aiogram 3, Alembic
key-files:
  - models/models.py
  - services/reward_service.py
  - alembic/versions/20250415_add_whisper_reward_pools.py
  - alembic/versions/20250415_add_whisper_reward_items.py
  - alembic/versions/20250415_add_whisper_claims.py
  - tests/unit/test_reward_service.py
---

## Tasks Completed

### Task 1: Add Whisper models to models.py
- Added `Date` to sqlalchemy imports
- Added `WhisperRewardPool`, `WhisperRewardItem`, and `WhisperClaim` classes after `UserRewardHistory`
- Verified models load correctly

### Task 2: Create Alembic migrations for whisper tables
- Created `20250415_add_whisper_reward_pools.py` - creates whisper_reward_pools table
- Created `20250415_add_whisper_reward_items.py` - creates whisper_reward_items table
- Created `20250415_add_whisper_claims.py` - creates whisper_claims table with unique constraint
- Verified migrations run successfully on SQLite

### Task 3: Extend RewardService with whisper pool CRUD and claim logic
- Added imports: `date`, `WhisperRewardPool`, `WhisperRewardItem`, `WhisperClaim`, `random`
- Added methods:
  - `create_whisper_pool(name, code)` - create new pool
  - `get_whisper_pool_by_code(code)` - get active pool by code
  - `add_item_to_whisper_pool(pool_id, reward_id, weight)` - add reward to pool
  - `remove_item_from_whisper_pool(item_id)` - remove item
  - `list_whisper_pools()` - list all pools
  - `can_claim_whisper(user_id, is_vip)` - check eligibility
  - `claim_whisper(user_id, pool_code, bot)` - claim daily whisper with race condition protection

### Task 4: Add unit tests for whisper pools, limits, and claims
- Added `TestWhisperPoolCRUD` class with 3 tests
- Added `TestWhisperClaim` class with 5 tests
- Tests pass successfully

## Deviations Found and Resolved

1. **Missing `sample_reward` fixture**: Tests referenced non-existent fixture `sample_reward`. Fixed by using existing `sample_reward_besitos` fixture instead.

2. **SQLite unique constraint limitation**: Alembic downgrades fail on SQLite when dropping unique constraints. Resolved by wrapping constraint operations in try/except blocks.

3. **Missing Date import**: Had to add `Date` to sqlalchemy imports for `WhisperClaim.claim_date`.

## Decisions Taken

1. **Pool codes**: Using "free_daily" and "vip_daily" as standard pool codes
2. **Race condition protection**: Using existing BesitoService lock mechanism (get_or_create_balance with lock=True) before checking/creating WhisperClaim
3. **Weighted random selection**: Using Python's random.choices with weights parameter

## Verification Results

- Models import correctly: `python -c "from models.models import WhisperRewardPool, WhisperRewardItem, WhisperClaim; print('OK')"` → OK
- Migrations run: `alembic upgrade head` → 20250415_whisper_claims (head)
- Tests pass: `pytest -xvs tests/unit/test_reward_service.py -k "TestWhisper"` → 8 passed
- All 8 whisper tests pass

## Commits

- `1cb89ed`: feat(whisper): add WhisperRewardPool, WhisperRewardItem, WhisperClaim models

## Self-Check: PASSED