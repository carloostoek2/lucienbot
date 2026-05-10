---
phase: 17-17-promos-de-trivias
plan: "17-03"
subsystem: gamification
tags: streak-promotion, admin-fsm, game-service-hook, promo-code, aiogram

# Dependency graph
requires:
  - phase: 17-02
    provides: StreakPromotionService, scheduler jobs for streak promotions
provides:
  - GameService hook calling claim_for_streak() after correct answers in all 3 trivia play methods
  - Promo code surfaced in trivia result messages (D-14)
  - Full FSM admin wizard for creating/managing streak promotions
  - Keyboard button and router registration for admin access
affects: [17-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Lazy import of StreakPromotionService inside GameService methods (avoids circular deps)
    - FSM wizard pattern with 12 states (matching BroadcastStates pattern)
    - `get_service()` context manager for automatic session handling in handlers

key-files:
  created:
    - handlers/trivia_streak_admin_handlers.py
  modified:
    - services/game_service.py
    - keyboards/inline_keyboards.py
    - handlers/__init__.py
    - bot.py

key-decisions:
  - "Lazy import of StreakPromotionService inside each play method to avoid circular dependency between GameService and StreakPromotionService"
  - "Refactored admin handlers to stay under 50 lines per function by extracting helpers (_build_promotions_list, _build_promotion_detail_text, _build_success_message, _build_game_type_selection_keyboard)"
  - "StreakPromotionService receives self.db (same session) from GameService for transactional consistency"

patterns-established:
  - "GameService -> StreakPromotionService: unidirectional call, no reverse coupling"
  - "Admin FSM wizards follow the same structure as BroadcastStates: callback entry -> states -> message collection -> confirmation -> service call"
  - "Promo code display format: ticket emoji + bold title + italic code block + Lucien registry note"

requirements-completed:
  - STREAK-PROMO-03

# Metrics
duration: 33 min
completed: 2026-05-10
---

# Phase 17 Plan 03: GameService Hook, Admin Handlers, and Registration

**StreakPromotionService.claim_for_streak() hooked into all 3 trivia play methods, promo code surfaced in user-facing messages, full FSM admin wizard with 12 states for promotion creation and management**

## Performance

- **Duration:** 33 min
- **Started:** 2026-05-10T02:19:05Z
- **Completed:** 2026-05-10T02:52:19Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added lazy import of StreakPromotionService inside play_trivia(), play_trivia_vip(), and play_trivia_simple() with claim_for_streak() call after correct answers
- Modified all 3 _build_*_message_parts() and _build_*_message() functions to accept and display promo_code_line when a code is awarded
- Created handlers/trivia_streak_admin_handlers.py with full FSM wizard (12 states) for creating streak promotions, plus view/pause/activate/delete/redemptions management
- Registered the new router in handlers/__init__.py, bot.py, and admin_menu_keyboard
- All admin functions conform to the 50-line project limit after refactor extraction

## Task Commits

Each task was committed atomically:

1. **Task 0: Register streak promotion admin router** - `650999b` (feat)
2. **Task 1: GameService hook with promo code display** - `bd43e2b` (feat)
3. **Task 2: Create admin handlers for streak promotion management** - `340e2fd` (feat)

## Files Created/Modified

- `handlers/trivia_streak_admin_handlers.py` - Created: FSM admin wizard (817 lines, 27 functions, all <= 50 lines)
- `services/game_service.py` - Modified: claim_for_streak() hook in 3 play methods + promo_code_line in 6 message functions
- `keyboards/inline_keyboards.py` - Modified: Added "🏆 Promos de Racha" button to admin_menu_keyboard()
- `handlers/__init__.py` - Modified: Imported trivia_streak_admin_router, added to __all__
- `bot.py` - Modified: Imported trivia_streak_admin_router, registered with dp.include_router()

## Decisions Made

- Used lazy import (inside method body) for StreakPromotionService in GameService to avoid circular imports -- StreakPromotionService already imports from services.__init__ which transitively imports GameService
- Refactored 4 over-length functions (57, 72, 52, 57 lines) into 50-line conformant versions by extracting helper functions (_build_promotions_list, _build_promotion_detail_text, etc.)
- StreakPromotionService receives self.db (shared session) from GameService for transactional consistency in claim_for_streak
- Admin FSM wizard follows the same structure as existing BroadcastStates pattern: callback entry -> sequential states -> confirmation -> service call -> state.clear()

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Over-length functions refactored**
- **Found during:** Task 2 (Admin handlers creation)
- **Issue:** 4 handler functions exceeded the 50-line project limit (max 72 lines)
- **Fix:** Extracted helper functions: _build_promotions_list, _build_promotion_detail_text, _build_success_message, _build_game_type_selection_keyboard
- **Files modified:** handlers/trivia_streak_admin_handlers.py
- **Verification:** AST scan confirmed all 27 functions <= 50 lines
- **Committed in:** 340e2fd (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor refactoring to comply with project standards. No scope creep.

## Issues Encountered

- None - all acceptance criteria passed on first try
- Final verification suite confirms keyboard button, router registration, GameService AST checks (3+ claim_for_streak calls, 9+ promo_code_line refs, no module-level import), and admin handler import all pass

## Next Phase Readiness

- Ready for plan 17-04 (remaining UI/handler work for streak promotions)
- GameService integration is complete -- all 3 trivia types can now award promo codes
- Admin can create, list, view, pause, activate, and delete streak promotions via the FSM wizard
- All wiring (keyboard, __init__.py, bot.py) is in place

---
*Phase: 17-17-promos-de-trivias*
*Completed: 2026-05-10*
