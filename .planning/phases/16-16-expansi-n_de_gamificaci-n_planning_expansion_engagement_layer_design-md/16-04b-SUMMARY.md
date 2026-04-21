---
phase: 16
plan: 16-04b
subsystem: engagement-layer-susurros
tech-stack: python-aiogram-sqlalchemy
key-files:
  - utils/lucien_voice.py
  - keyboards/inline_keyboards.py
  - handlers/engagement_user_handlers.py
  - handlers/engagement_admin_handlers.py
---

# Plan 16-04b Summary: Susurros de Diana — Handlers, Keyboards, Voice, Admin UI

## Tasks Completed

| Task | Commit | Status |
|------|--------|--------|
| Add LucienVoice messages for Susurros | 68e0af6 | ✅ |
| Update main menu keyboard with Susurros button | 903c9f4 | ✅ |
| Add Susurros handlers to engagement_user_handlers | a21b981 | ✅ |
| Add admin handler for whisper pools | 0288e27 | ✅ |

## Implementation Details

### LucienVoice (utils/lucien_voice.py)
Added three new methods:
- `susurros_menu(can_claim)` — Shows claim eligibility with status badges
- `susurro_claimed(reward_name, message)` — Success message with Lucien voice
- `susurro_limit_reached()` — Daily limit feedback

### Main Menu Keyboard (keyboards/inline_keyboards.py)
Updated row from 2 buttons to 3:
- Ritmo Diario | Susurros | Regalo diario

### User Handlers (handlers/engagement_user_handlers.py)
Added three callback handlers:
- `susurros_menu` — Shows eligibility and claim buttons
- `susurros_claim_free` — Claims free daily whisper
- `susurros_claim_vip` — Claims VIP daily whisper

All handlers follow architecture rules: call exactly one service (RewardService), no DB access, Lucien voice messages.

### Admin Handler (handlers/engagement_admin_handlers.py)
Added:
- `admin_whisper_pools_list` — View configured whisper pools with status

## Verification

- Import check: handlers/engagement_user_handlers ✅
- Import check: handlers/engagement_admin_handlers ✅
- LucienVoice method count: 3 methods present ✅
- Keyboard button: susurros_diana present ✅

## Deviation Notes
- Fixed typo "reclamaciones" → "reclamo" in voice messages