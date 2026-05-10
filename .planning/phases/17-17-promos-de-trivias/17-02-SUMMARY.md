---
phase: 17
plan: "17-02"
status: complete
subsystem: Promociones por Racha
tech-stack: Python 3.12, SQLAlchemy 2.0, APScheduler 3.10
key-files:
  - services/streak_promotion_service.py (CREATED, 386 lines)
  - services/scheduler_service.py (MODIFIED, +67 lines)
  - services/__init__.py (MODIFIED, +4 lines)
---

## Summary: Service Layer and Scheduler Integration

Created `StreakPromotionService` with full CRUD for promotions, upfront code generation, streak-based claim logic, and category management. Added APScheduler job handlers and scheduling methods to `SchedulerService` for automatic promotion activation/deactivation.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 0 | Register `StreakPromotionService` in `services/__init__.py` (import + `__all__`) | 84e33fc |
| 1 | Create `services/streak_promotion_service.py` with 16 methods including `create_promotion`, `claim_for_streak`, `activate`, `deactivate`, `get_redemption_stats` | 55b7bbc |
| 2 | Add scheduler job handlers `_activate_streak_promotion`, `_deactivate_streak_promotion` and methods `schedule_streak_promotion`, `remove_streak_promotion_jobs` to `SchedulerService` | 3c9849f |

## Service Methods Implemented

### StreakPromotionService (12 public + 4 private methods)

- `create_promotion()` -- promotion with levels, upfront code generation via `_pre_generate_codes()`
- `get_promotion()` -- single promotion lookup by ID
- `get_all_promotions()` -- all promotions ordered by `created_at DESC`
- `get_active_promotions()` -- filtered by `game_type` maps (`trivia`->`include_general`, `trivia_vip`->`include_vip`, `trivia_simple`->`include_simple`) and optional `category_id`
- `claim_for_streak()` -- core logic: checks active promos, matches streak level, prevents duplicate claims (D-15), marks code as DELIVERED, creates `StreakPromotionRedemption`
- `activate()` -- sets `is_active=True`, `status=ACTIVE`, activates associated `TriviaCategory` (D-08)
- `deactivate()` -- sets `is_active=False`, `status=EXPIRED`, deactivates category only if no other active promo uses same category (D-09)
- `pause_promotion()` -- sets `status=PAUSED`, `is_active=False`
- `delete_promotion()` -- cascade delete, attempts scheduler job cleanup
- `get_redemption_stats()` -- per-level stats with total/delivered/remaining/redemption list
- `get_user_redemptions()` -- user redemption history, optionally filtered by promo
- `_generate_code()` -- `secrets.token_hex(6)` with `SK-` prefix (D-11)
- `_pre_generate_codes()` -- batch creates `StreakPromotionCode` records per level (D-10)
- `_has_claimed_level()` -- checks `StreakPromotionRedemption` table (D-15)
- `_get_available_code()` -- finds `AVAILABLE` code with `with_for_update()` locking

### SchedulerService additions

- `_activate_streak_promotion()` -- module-level async job handler, opens session, calls `service.activate()`
- `_deactivate_streak_promotion()` -- module-level async job handler, opens session, calls `service.deactivate()`
- `schedule_streak_promotion()` -- schedules `DateTrigger` jobs for start/end dates using `streak_promo_activate_`/`streak_promo_deactivate_` job ID prefixes
- `remove_streak_promotion_jobs()` -- removes both jobs with exception handling

## Deviations

None. All methods adhere to the 50-line limit (verified via AST). The service follows existing patterns from `PromotionService` (CRUD pattern), `TriviaCategoryService` (category activation), and `SchedulerService` (module-level job handlers with `SessionLocal()`).

## Design Decisions

1. **Lazy import of `TriviaCategoryService` inside `activate`/`deactivate` methods** -- avoids circular imports between `services/__init__.py`, `streak_promotion_service.py`, and `trivia_service.py`
2. **`with_for_update()` on `_get_available_code`** -- prevents race conditions when multiple users claim codes simultaneously for the same level
3. **Scheduler job cleanup in `delete_promotion` is guarded by try/except** -- the scheduler may not be running (e.g., during tests), and the `remove_streak_promotion_jobs` method was added in Task 2 (applied after Task 1)
4. **`deactivate` sets `status=EXPIRED`** -- consistent with `PromotionStatus.EXPIRED` pattern; paused promotions use `PAUSED`

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `services/__init__.py` | MODIFIED | +4 |
| `services/streak_promotion_service.py` | CREATED | 386 |
| `services/scheduler_service.py` | MODIFIED | +67 |

## Verification

- Python import: `from services import StreakPromotionService` passes
- Methods introspection: all 16 expected methods present
- Scheduler handlers import: `from services.scheduler_service import _activate_streak_promotion, _deactivate_streak_promotion` passes
- All functions <= 50 lines (verified via AST)
- Stub test passes: `pytest tests/unit/test_streak_promotion_service.py -v -q --no-cov`
