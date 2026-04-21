---
phase: 16
plan: 16-03a
subsystem: narrative
tech-stack: Python, SQLAlchemy, Aiogram 3, Alembic
key-files:
  - models/models.py (StoryNode, StoryPath, UserStoryPathProgress)
  - services/story_service.py (path CRUD, unlock logic)
  - alembic/versions/20250415_*.py (migrations)
  - tests/unit/test_story_service.py (unit tests)
---

# Plan 16-03a Summary: Senderos Narrativos - Models, Migrations, and StoryService Methods

## Tasks Completed

### 1. Extend StoryNode and add StoryPath models (models/models.py)
- Added `unlock_required_streak` and `unlock_required_besitos_total` columns to StoryNode
- Added StoryPath model with: name, description, node_sequence (JSON), reward_id, is_vip_exclusive, max_attempts, valid_from, valid_until, is_active
- Added UserStoryPathProgress model with: user_id, path_id, current_node_index, attempts_used, is_completed, started_at, completed_at

### 2. Create Alembic migrations
- 20250415_add_story_node_unlock_columns.py: adds unlock_required_streak and unlock_required_besitos_total to story_nodes
- 20250415_add_story_paths_table.py: creates story_paths table
- 20250415_add_user_story_path_progress_table.py: creates user_story_path_progress with unique constraint

### 3. Extend StoryService with path CRUD and unlock logic (services/story_service.py)
- Added imports for StoryPath, UserStoryPathProgress, DailyGiftStreak, BesitoBalance
- Extended create_node() with unlock_required_streak and unlock_required_besitos_total parameters
- Added StoryPath methods: create_story_path, get_story_path, list_active_story_paths, list_available_paths
- Added progression methods: start_path, advance_path
- Added unlock checks in can_access_node() for streak and besitos total requirements

### 4. Add unit tests (tests/unit/test_story_service.py)
- TestStoryPathCRUD: test create_story_path, list_available_paths filters VIP, respects attempts
- TestStoryNodeUnlock: test blocking by streak, allowing when streak met
- TestStoryPathProgress: test start_path creates progress

## Requirements Mapped
- ENG-02: Unlock story nodes by daily streak days
- ENG-06: Unlock story nodes by total earned besitos

## Deviations and Resolutions
- Database migration error due to SQLite unique constraint issue resolved manually
- Added unlock parameters to create_node() as they were missing from the service method

## Commits
- 29ab1b1: feat(narrative): add StoryPath and unlock columns to StoryNode (Phase 16)
- 2563ae8: feat(migrations): add alembic migrations for StoryPath tables
- 448856e: feat(narrative): extend StoryService with path CRUD and unlock logic
- 4779e6c: test(narrative): add unit tests for StoryPath and unlock functionality

## Self-Check: PASSED