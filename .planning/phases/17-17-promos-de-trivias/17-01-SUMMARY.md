# Plan 17-01 Summary: Models, Migration, and Wave 0 Stubs

**Phase:** 17 (17-promos-de-trivias)
**Plan:** 17-01
**Subsystem:** Streak Promotion - Foundation
**Tech Stack:** Python 3.12, SQLAlchemy 2.0, Alembic 1.12, Aiogram 3
**Status:** Complete

## Tasks Completed

### Task 0: Wave 0 test stubs
- **Files created:** `tests/unit/test_streak_promotion_service.py`, `tests/integration/test_streak_promotion_handler.py`
- **Commit:** `f58e19c` - test(17): add Wave 0 test stubs for streak promotion service and handlers
- **Details:** Created placeholder stub files so downstream verify blocks in plans 17-02 and 17-04 can reference existing file paths without errors. Unit test stub adjusted to not import the non-existent service module (created in a later phase). Integration test stub imports and validates `admin_menu_keyboard()` existence.

### Task 1: Add 4 streak promotion models
- **File modified:** `models/models.py` (+97 lines)
- **Commit:** `fdaeb10` - feat(17): add 4 streak promotion models to models/models.py
- **Models added:**
  - `StreakPromotionStatus` enum (PENDING, ACTIVE, EXPIRED, PAUSED)
  - `StreakPromotionCodeStatus` enum (AVAILABLE, DELIVERED, USED)
  - `StreakPromotion` (promotions table with duration modes, category linking, boolean flags for trivia types)
  - `StreakPromotionLevel` (levels with consecutive_required, discount_pct, cascade all delete-orphan)
  - `StreakPromotionCode` (codes with unique code_value, enum status tracking, delivered_at/used_at timestamps)
  - `StreakPromotionRedemption` (redemptions with UniqueConstraint on user_id+level_id for D-15 duplicate prevention)
- **Patterns followed:** Enum-first, server_default=func.now(), relationship with back_populates, cascade delete-orphan, ForeignKey with proper references

### Task 2: Create Alembic migration
- **File created:** `alembic/versions/36c345796281_add_streak_promotions_tables.py`
- **Commit:** `e5c4a0f` - feat(17): add Alembic migration for streak promotion tables
- **Migration:** `20260509_add_trivia_categories` -> `36c345796281`
- **Tables created:** streak_promotions, streak_promotion_levels, streak_promotion_codes, streak_promotion_redemptions
- **Verification:** `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` all succeed
- **Note:** Autogenerate detected unrelated schema drift from existing tables; migration was manually cleaned to only include the 4 new streak promotion tables.

## Deviations

1. **Unit test stub import failure:** The plan template's unit test stub attempted to import `StreakPromotionService` which doesn't exist yet (created in a later phase). Applied **Deviation Rule 2 (auto-add missing critical functionality)** by changing the stub to a simple `assert True` placeholder, matching the pattern used by other Wave 0 stubs in the codebase (e.g., Phase 16 test stubs).

2. **Autogenerate noise:** `alembic revision --autogenerate` detected schema drift in 7 existing tables (besito_balances, besito_transactions, broadcast_reactions, categories, packages, store_products, trivia_categories). Applied **Deviation Rule 2** by manually rewriting the migration to include ONLY the 4 new streak promotion tables.

## Key Decisions

1. **Migration placement after `20260509_add_trivia_categories`:** The existing migration chain ends with `20260509_add_trivia_categories` from Phase 16. Our migration `36c345796281` points `down_revision` to that migration.

2. **Double-quote vs single-quote for UniqueConstraint:** The model uses double quotes `("user_id", "level_id")` for the UniqueConstraint on StreakPromotionRedemption, which is a stylistic difference from the existing codebase's single-quote convention but functionally identical.

3. **Stub simplification:** Rather than importing non-existent services, stubs use `assert True` placeholders to ensure they pass without depending on future work.

## Success Criteria Checklist

- [x] 4 new models in models/models.py -- verified via Python import
- [x] Alembic migration creates tables and is idempotent -- verified via upgrade/downgrade/upgrade
- [x] Wave 0 test stubs exist and pass -- verified via pytest (2 passed)
- [x] No modifications to Promotion model or PromotionService -- verified via git diff

## Key File Paths

- `/home/ubuntu/repos/lucienbot/models/models.py` (lines 1113-1212)
- `/home/ubuntu/repos/lucienbot/alembic/versions/36c345796281_add_streak_promotions_tables.py`
- `/home/ubuntu/repos/lucienbot/tests/unit/test_streak_promotion_service.py`
- `/home/ubuntu/repos/lucienbot/tests/integration/test_streak_promotion_handler.py`
