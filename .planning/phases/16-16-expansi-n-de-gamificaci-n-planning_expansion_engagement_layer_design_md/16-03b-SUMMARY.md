---
phase: 16
plan: 16-03b
subsystem: narrative
tech-stack: aiogram3, SQLAlchemy
key-files:
  - utils/lucien_voice.py
  - keyboards/inline_keyboards.py
  - handlers/engagement_user_handlers.py
  - handlers/engagement_admin_handlers.py
---

# Plan 16-03b Summary: Senderos del Espejo UI Wiring

## Tasks Completed

| Task | Files Modified | Commit |
|------|----------------|--------|
| Add LucienVoice messages for Senderos | `utils/lucien_voice.py` | `d77114c` |
| Update main menu keyboard with Senderos button | `keyboards/inline_keyboards.py` | `d77114c` |
| Add Senderos handlers to engagement_user_handlers | `handlers/engagement_user_handlers.py` | `d77114c` |
| Add admin handlers for StoryPath CRUD | `handlers/engagement_admin_handlers.py` | `d77114c` |

## Implementation Details

### 1. LucienVoice Messages (utils/lucien_voice.py)
Added 4 new methods:
- `senderos_menu(paths)` - Shows available paths or empty state
- `sendero_started(path_name)` - Confirmation when user starts a path
- `sendero_completed(path_name, reward_msg)` - Completion message with optional reward
- `sendero_locked(reason)` - Access denied message

### 2. Main Menu Keyboard (keyboards/inline_keyboards.py)
Added "Senderos del Espejo" button with callback_data `senderos_espejo` before "Fragmentos de la historia" row.

### 3. User Handlers (handlers/engagement_user_handlers.py)
Added 3 callback handlers:
- `senderos_menu` - Displays available paths for user based on VIP status
- `senderos_start` - Starts a path (start_path_{id})
- `senderos_advance` - Advances through path nodes (advance_path_{id}_{choice})

All handlers follow the architecture: call exactly 1 service method, no business logic.

### 4. Admin Handler (handlers/engagement_admin_handlers.py)
Added `admin_story_paths_list` callback handler that lists active story paths via StoryService.

## Requirements Mapped

- **ENG-02**: User sees "Senderos del Espejo" in main menu and can start available paths
- **ENG-07**: User receives Lucien-voice feedback when starting, advancing, or completing a path

## Deviations & Resolutions

None. All tasks executed as specified.

## Self-Check: PASSED

- [x] senderos_menu/senderos_started/senderos_completed/senderos_locked exist in lucien_voice.py
- [x] senderos_espejo button in main_menu_keyboard
- [x] User handlers import without errors
- [x] Admin handler imports without errors
- [x] All files committed individually
- [x] SUMMARY.md created