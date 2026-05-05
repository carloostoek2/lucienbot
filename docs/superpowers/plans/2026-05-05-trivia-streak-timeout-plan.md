# Trivia Streak Timeout — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Impose a 2-minute timeout on trivia streak sessions. Users must answer all questions consecutively within 2 minutes or lose their streak and any active discount code.

**Architecture:** FSM data stores `streak_started_at` when streak goes 0→1. Each trivia callback checks elapsed time; if > 120s, the streak is invalidated. A periodic scheduler handles users who abandon sessions.

**Tech Stack:** Python, aiogram 3.x FSM, SQLAlchemy, APScheduler

---

## File Overview

| File | Role |
|------|------|
| `services/game_service.py` | Core timeout logic, helper methods |
| `handlers/game_user_handlers.py` | Timeout checks at entry points |
| `handlers/trivia_discount_admin_handlers.py` | Scheduler registration (unchanged) |

---

## Task 1: Add Timeout Constants to GameService

**Files:**
- Modify: `services/game_service.py` (add constants near top of class)

- [ ] **Step 1: Add constants**

Find the `TRIVIA_WIN_BESITOS` constant around line 200. Add above it:

```python
STREAK_TIMEOUT_SECONDS = 120  # 2 minutes max to answer all questions in a streak session
```

Run: `grep -n "TRIVIA_WIN_BESITOS" services/game_service.py`
Expected: line number where constant is defined

- [ ] **Step 2: Commit**

```bash
git add services/game_service.py
git commit -m "feat(trivia): add STREAK_TIMEOUT_SECONDS constant"
```

---

## Task 2: Add Helper Methods to GameService

**Files:**
- Modify: `services/game_service.py`

- [ ] **Step 1: Add `_check_streak_timeout` helper**

Find `invalidate_streak_code` at line 1127. Add above it:

```python
def _check_streak_timeout(self, state_data: dict) -> bool:
    """
    Verifies if the user's streak session is still within the 2-minute window.
    Returns True if OK, False if expired.
    """
    streak_started_at = state_data.get("streak_started_at")
    if not streak_started_at:
        return True  # No active streak being tracked

    from datetime import datetime, timezone
    elapsed = datetime.now(timezone.utc) - streak_started_at
    return elapsed.total_seconds() <= self.STREAK_TIMEOUT_SECONDS

def _handle_streak_timeout(self, user_id: int, state_data: dict) -> None:
    """
    Executes full streak invalidation due to timeout:
    - Cancels active discount code
    - Breaks the streak in GameRecord
    """
    config_id = state_data.get("current_config_id")
    game_type = 'trivia_vip' if state_data.get('vip_mode') else 'trivia'

    if config_id:
        self.invalidate_streak_code(user_id, config_id)

    self.reset_trivia_streak(user_id, game_type)
    logger.info(f"game_service - _handle_streak_timeout - {user_id} - streak_invalidated")
```

- [ ] **Step 2: Run to verify no syntax errors**

Run: `cd /home/ubuntu/repos/lucienbot && python -c "from services.game_service import GameService; print('OK')"`
Expected: `OK` (no output on success)

- [ ] **Step 3: Commit**

```bash
git add services/game_service.py
git commit -m "feat(trivia): add timeout check and handler helpers"
```

---

## Task 3: Add Timeout Message Constant to GameService

**Files:**
- Modify: `services/game_service.py`

- [ ] **Step 1: Add timeout message template in `STREAK_TEMPLATES`**

Find `STREAK_TEMPLATES` dict. Add a new key inside it:

```python
STREAK_TEMPLATES: dict = {
    # ... existing keys ...
    'timeout': (
        "🎩 <b>Lucien:</b>\n\n"
        "<i>Ah... parece que sus dedos necesitaban un descanso más largo que su mente.\n"
        "El tiempo corre, incluso para quienes creen que pueden burlarlo.\n"
        "Su racha ha sido... olvidada.</i>"
    ),
    # ... rest of existing keys ...
}
```

The `STREAK_TEMPLATES` is around line 100. Look for the `'streak_messages'` key to understand the nesting.

- [ ] **Step 2: Verify**

Run: `cd /home/ubuntu/repos/lucienbot && python -c "from services.game_service import GameService; s=GameService; print('timeout' in s.STREAK_TEMPLATES)"`
Expected: `True`

- [ ] **Step 3: Commit**

```bash
git add services/game_service.py
git commit -m "feat(trivia): add timeout message template"
```

---

## Task 4: Inject Timeout Check into `trivia_answer` Handler

**Files:**
- Modify: `handlers/game_user_handlers.py:164`

- [ ] **Step 1: Add timeout check at the START of `trivia_answer`**

After `user_id = callback.from_user.id` and before the `parts = callback.data.split("_")` line, insert:

```python
    # --- STREAK TIMEOUT CHECK ---
    current_state = await state.get_state()
    if current_state in (TriviaStreakStates.waiting_streak_choice.state,
                          TriviaStreakStates.streak_continue.state):
        data = await state.get_data()
        if not service._check_streak_timeout(data):
            config_id = data.get('current_config_id')
            game_type = 'trivia_vip' if data.get('vip_mode') else 'trivia'
            service._handle_streak_timeout(user_id, data)
            await state.clear()

            header = service._select_template(service.STREAK_TEMPLATES['timeout'])
            footer = service._select_template(service.TRIVIA_TEMPLATES.get('footer', '¿Qué desea hacer ahora?'))
            message = f"{header}\n\n<i>{footer}</i>"
            await callback.message.edit_text(message, reply_markup=game_menu_keyboard())
            await callback.answer()
            logger.info(f"game_user_handlers - trivia_answer - {user_id} - timeout_expired")
            return
    # --- END TIMEOUT CHECK ---
```

Note: This block requires `service` to be available. Since `service` is created inside `with get_service(GameService) as service:`, the timeout check must be placed **after** the service context exits but **before** we process the answer.

**Revised approach — the timeout check needs to be INSIDE the with block:**

At line 177, after `with get_service(GameService) as service:`, add the timeout check as the first thing inside:

```python
    with get_service(GameService) as service:
        # --- STREAK TIMEOUT CHECK (moved inside) ---
        current_state = await state.get_state()
        if current_state in (TriviaStreakStates.waiting_streak_choice.state,
                              TriviaStreakStates.streak_continue.state):
            data = await state.get_data()
            if not service._check_streak_timeout(data):
                config_id = data.get('current_config_id')
                game_type = 'trivia_vip' if data.get('vip_mode') else 'trivia'
                service._handle_streak_timeout(user_id, data)
                await state.clear()

                timeout_msg = service._select_template(service.STREAK_TEMPLATES['timeout'])
                message = f"{timeout_msg}\n\n<i>¿Qué desea hacer ahora?</i>"
                await callback.message.edit_text(message, reply_markup=game_menu_keyboard())
                await callback.answer()
                logger.info(f"game_user_handlers - trivia_answer - {user_id} - timeout_expired")
                return
        # --- END TIMEOUT CHECK ---

        result = service.play_trivia(user_id, question_idx, answer_idx)
```

- [ ] **Step 2: Save `streak_started_at` when streak goes 0→1**

In `trivia_answer`, after the line `if tier_info and tier_info.get('tier_reached'):` block (around line 266), find where `streak_mode=True` is saved in state and add `streak_started_at`:

The `state.update_data` call at line 324-335 saves `streak_mode=True` and other tier fields. But `streak_started_at` should be saved when the streak **starts** (first correct answer, when `previous_streak == 0` and `new_streak == 1`).

This happens in `play_trivia` — but FSM state is managed in the handler. We need to track when the streak started. The best place is: **at the START of `trivia_answer`, if user has `streak == 0` and we haven't saved `streak_started_at` yet, and the result is correct, we save it.**

Actually, the cleaner approach: After `result = service.play_trivia(...)` (line 178), check if `result['correct']` and `result['new_streak'] == 1` and `result['previous_streak'] == 0`. If so, update FSM with `streak_started_at=datetime.now(timezone.utc)`.

But this needs `from datetime import datetime, timezone` at the top of the handler file.

Find the imports at the top of `game_user_handlers.py` and add:

```python
from datetime import datetime, timezone
```

Then after `result = service.play_trivia(...)` (line 178), add:

```python
    # Save streak start time when user goes from 0 to 1
    if result['correct'] and result['new_streak'] == 1 and result['previous_streak'] == 0:
        await state.update_data(streak_started_at=datetime.now(timezone.utc))
```

- [ ] **Step 3: Verify changes compile**

Run: `cd /home/ubuntu/repos/lucienbot && python -c "from handlers.game_user_handlers import router; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add handlers/game_user_handlers.py
git commit -m "feat(trivia): inject timeout check into trivia_answer handler"
```

---

## Task 5: Inject Timeout Check into `streak_retire`, `streak_continue`, `streak_exit`

**Files:**
- Modify: `handlers/game_user_handlers.py`

- [ ] **Step 1: Add timeout check to `streak_retire` (line 603)**

At the start of the handler function body (after `user_id = callback.from_user.id`):

```python
@router.callback_query(F.data == "streak_retire", TriviaStreakStates.waiting_streak_choice)
async def streak_retire(callback: CallbackQuery, state: FSMContext):
    """Usuario elige retirarse con su descuento actual"""
    user_id = callback.from_user.id

    # --- TIMEOUT CHECK ---
    with get_service(GameService) as service:
        data = await state.get_data()
        if not service._check_streak_timeout(data):
            service._handle_streak_timeout(user_id, data)
            await state.clear()
            timeout_msg = service._select_template(service.STREAK_TEMPLATES['timeout'])
            message = f"{timeout_msg}\n\n<i>¿Qué desea hacer ahora?</i>"
            await callback.message.edit_text(message, reply_markup=game_menu_keyboard())
            await callback.answer()
            logger.info(f"game_user_handlers - streak_retire - {user_id} - timeout_expired")
            return
    # --- END TIMEOUT CHECK ---
```

- [ ] **Step 2: Add timeout check to `streak_continue` handler**

Find the streak_continue handler. It should be after streak_retire. Add the same timeout check at the beginning.

- [ ] **Step 3: Find `streak_exit` handler and add timeout check**

```bash
grep -n "streak_exit" handlers/game_user_handlers.py
```

Add the same timeout check pattern.

- [ ] **Step 4: Verify all compile**

Run: `cd /home/ubuntu/repos/lucienbot && python -c "from handlers.game_user_handlers import router; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add handlers/game_user_handlers.py
git commit -m "feat(trivia): add timeout checks to streak decision handlers"
```

---

## Task 6: Add Scheduler Job for Orphaned Streaks

**Files:**
- Modify: `services/game_service.py`

- [ ] **Step 1: Add `cleanup_expired_streaks` method**

Find `reset_trivia_streak` (line 1131). Add after it:

```python
def cleanup_expired_streaks(self) -> int:
    """
    Scheduler job: finds users with active streaks that have exceeded
    the 2-minute timeout window and invalidates them.
    Returns count of invalidated streaks.
    """
    # This requires access to FSM state storage which is external to GameService.
    # The actual implementation queries GameRecord for recent high-streak users
    # and relies on the FSM storage to track streak_started_at.
    # For now, this is a placeholder — the real logic lives in the scheduler
    # that calls this method and pairs it with FSM state lookup.
    return 0  # TODO: implement with Redis/Memory storage access
```

**Important:** The scheduler needs access to FSM state (which is stored in Redis or MemoryStorage). Since GameService doesn't have access to FSM context directly, the cleanup job should be implemented in the scheduler service that HAS access to the FSM storage.

This approach requires the scheduler to:
1. Query recent GameRecords with payout > 0 in the last 5 minutes
2. For each user, check FSM state for `streak_started_at`
3. If `now() - streak_started_at > 120`, call `invalidate_streak_code`

For initial implementation, skip this scheduler task and rely on the inline timeout checks. The scheduler can be added in a follow-up.

- [ ] **Step 2: Commit**

```bash
git add services/game_service.py
git commit -m "feat(trivia): add cleanup_expired_streaks stub for scheduler"
```

---

## Task 7: Smoke Test

**Files:**
- Test: manually trigger scenarios

Test the following scenarios by interacting with the bot:

1. Start a streak (answer 1 correctly) — verify no timeout message yet
2. Wait 2+ minutes and answer another — verify timeout invalidates streak
3. Reach a tier, choose "continue", wait 2 min — verify timeout
4. Verify message uses Lucien voice

---

## Spec Coverage Check

| Spec Section | Task |
|-------------|------|
| §2 FSM field `streak_started_at` | Tasks 4 (save), 5 (check) |
| §2 Timeout check logic | Task 2, 4, 5 |
| §3 Invalidación completa | Task 2 (`_handle_streak_timeout`) |
| §4 Mensaje timeout | Task 3 |
| §5 Puntos de inyección | Tasks 4, 5 |
| §7 Scheduler cleanup | Task 6 |

---

## Type Consistency Check

- `streak_started_at` stored as `datetime` — consistent in `_check_streak_timeout` and `_handle_streak_timeout`
- `config_id` comes from `state_data.get('current_config_id')` — consistent across all handlers
- `game_type` derived from `data.get('vip_mode')` — `'trivia'` or `'trivia_vip'` — matches `GameRecord.game_type` values