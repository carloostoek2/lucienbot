# Phase 14: Minijuegos - Research

**Researched:** 2026-04-06
**Domain:** Telegram Mini-games (Dice & Trivia) integration with gamification system
**Confidence:** HIGH

## Summary

Phase 14 implements a mini-games system in Lucien Bot for generating besitos income. Two games: **Dados** (dice) and **Trivia** (questions from `docs/preguntas.json`). The system follows existing patterns from BesitoService and DailyGiftService, crediting wins via `TransactionSource` enum. Found existing 175-question trivia dataset with 3 options each, indexed answers.

**Primary recommendation:** Create `GameService` and `TriviaService` following DailyGiftService pattern, extend `TransactionSource` enum with GAME and TRIVIA, add keyboard functions to `inline_keyboards.py`, and register handlers in `bot.py`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiogram 3.x | 3.4+ | Telegram bot framework | Project uses aiogram for all handlers |
| SQLAlchemy | 2.x | ORM for game records | Same as existing models.py |

### Existing Services (to leverage)
| Service | Purpose | Integration |
|---------|--------|-------------|
| `BesitoService` | Credit/debit besitos | Use `credit_besitos(user_id, amount, source)` |
| `TransactionSource` | Track transaction origin | Extend with GAME, TRIVIA |
| `daily_gift_service.py` | Reference pattern | Same service-with-service pattern |

**Installation:**
```bash
# No new packages needed - all existing
```

## Architecture Patterns

### Recommended Project Structure
```
services/
├── game_service.py       # NEW - dice logic + trivia core
├── trivia_service.py     # NEW - trivia game logic (optional, can be in game_service)
handlers/
├── game_user_handlers.py # NEW - user interactions
├── game_admin_handlers.py # NEW - admin config
keyboards/
├── inline_keyboards.py   # MODIFY - add game keyboards
models/
├── models.py            # MODIFY - add GameRecord, TriviaSession
```

### Pattern 1: Service-with-Service (Reference: DailyGiftService)
```python
# services/daily_gift_service.py - embedding BesitoService
class DailyGiftService:
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.besito_service = BesitoService(self.db)  # Embed service

    def claim_gift(self, user_id: int) -> tuple:
        # ... logic ...
        success = self.besito_service.credit_besitos(
            user_id=user_id,
            amount=amount,
            source=TransactionSource.DAILY_GIFT,
            description="Regalo diario reclamanado"
        )
```

**When to use:** Games need to credit besitos, so embed BesitoService like DailyGiftService does.

### Pattern 2: Handler Flow (Reference: gamification_user_handlers.py)
```python
# handlers/gamification_user_handlers.py pattern
@router.callback_query(F.data == "my_balance")
async def show_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    besito_service = BesitoService()
    stats = besito_service.get_balance_with_stats(user_id)
    # ... build text with stats ...
    await callback.message.edit_text(text, reply_markup=back_keyboard("back_to_main"))
    await callback.answer()
```

**When to use:** Each callback is one function, calls exactly one service, returns inline keyboard.

### Pattern 3: Keyboard Pattern (Reference: inline_keyboards.py)
```python
def main_menu_keyboard(is_vip: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="💋 Mi saldo", callback_data="my_balance")],
        # ...
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_keyboard(back_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Regresar", callback_data=back_callback)]
    ])
```

**When to use:** All keyboards return InlineKeyboardMarkup, use callback_data for routing.

### Pattern 4: TransactionSource Usage
```python
# models/models.py - TransactionSource enum
class TransactionSource(str, enum.Enum):
    REACTION = "reaction"
    DAILY_GIFT = "daily_gift"
    MISSION = "mission"
    PURCHASE = "purchase"
    ADMIN = "admin"
    ANONYMOUS_MESSAGE = "anonymous_message"
    # ADD: GAME = "game"
    # ADD: TRIVIA = "trivia"
```

**When to use:** Need to add new sources to enum for game tracking.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Besitos credit | Custom DB insert | BesitoService.credit_besitos() | Has SELECT FOR UPDATE to prevent race conditions |
| Question storage | New table for trivia | docs/preguntas.json (already exists) | 175 questions already loaded, JSON is fine for read-only |
| Keyboard routing | Custom parsing | callback_data pattern | aiogram handles callback routing automatically |

**Key insight:** The codebase already has a working besitos system with proper concurrency handling. Games should use BesitoService to credit wins, not write custom DB code.

## Common Pitfalls

### Pitfall 1: Missing TransactionSource enum values
**What goes wrong:** Game transactions show as empty/unknown source
**Why it happens:** GAME and TRIVIA not added to enum yet
**How to avoid:** Add to TransactionSource enum before implementing services
**Warning signs:** Logs show source.value as empty string

### Pitfall 2: Handler doing business logic
**What goes wrong:** Code quality violations, hard to test
**Why it happens:** Trying to do too much in handler
**How to avoid:** Handlers only call services, services do all logic
**Warning signs:** Handler imports models directly or has complex if/else

### Pitfall 3: Forgetting back keyboard
**What goes wrong:** Users stuck in game flow, can't navigate
**Why it happens:** Game messages don't include back button
**How to avoid:** Use back_keyboard() on all game messages
**Warning signs:** Users ask "how do I go back?"

## Code Examples

### Dice Win Check (from DESIGN.md)
```python
# services/game_service.py - check win condition
def check_win(dice1: int, dice2: int) -> bool:
    """
    Victoria: pares (ambos pares) o dobles (iguales)
    """
    both_even = dice1 % 2 == 0 and dice2 % 2 == 0
    doubles = dice1 == dice2
    return both_even or doubles
```

### Trivia Question Format (from docs/preguntas.json)
```json
[
  { "q": "¿Cuál es la capital de Francia?", "opts": ["Madrid", "París", "Roma"], "answer": 1 }
]
```

**Format:** 3 options, `answer` is index of correct (0=A, 1=B, 2=C)

### Credit Besitos Pattern (reference: daily_gift_service.py)
```python
# Inside service method
success = self.besito_service.credit_besitos(
    user_id=user_id,
    amount=amount,
    source=TransactionSource.GAME,  # NEW enum value
    description="Victoria en dados"
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Besitos only from reactions/gifts | Add games as income source | Phase 14 | New engagement mechanic |

**Deprecated/outdated:**
- None relevant to this phase

## Open Questions

1. **Should TriviaSession track per-user progress (avoid repeats)?**
   - What we know: preguntas.json has 175 questions, users could repeat
   - What's unclear: Whether to track which questions user answered
   - Recommendation: Skip for MVP - just pick random question each time

2. **Should GameRecord be created for every game play?**
   - What we know: DESIGN.md shows GameRecord model with bet_amount, result, payout
   - What's unclear: Is tracking history required for MVP?
   - Recommendation: Add model for future analytics, but don't require extensive logging yet

3. **How to handle "Me Interesa" vs free users?**
   - What we know: minijuegos need to generate besitos income
   - What's unclear: Should premium users get more/better games?
   - Recommendation: Keep simple for MVP - same games for all, besitos are virtual currency

## Environment Availability

Step 2.6: SKIPPED (no external dependencies - all project code/config)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pytest.ini (if exists) |
| Quick run command | `pytest tests/unit/ -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GAME-01 | Dados: victory check (pares/dobles) | unit | `pytest tests/unit/test_game_service.py::test_check_win -x` | ❌ New |
| GAME-02 | Trivia: random question selection | unit | `pytest tests/unit/test_game_service.py::test_random_trivia -x` | ❌ New |
| GAME-03 | Credit besitos on win | unit | `pytest tests/unit/test_game_service.py::test_credit_on_win -x` | ❌ New |

### Wave 0 Gaps
- [ ] `tests/unit/test_game_service.py` - covers GAME-01, GAME-02, GAME-03
- [ ] Framework install: pytest - already in requirements.txt

## Sources

### Primary (HIGH confidence)
- `services/besito_service.py` - BesitoService.credit_besitos() usage pattern
- `services/daily_gift_service.py` - Service-with-service pattern, TransactionSource usage
- `models/models.py` - TransactionSource enum, existing model structure
- `handlers/gamification_user_handlers.py` - Handler callback pattern
- `keyboards/inline_keyboards.py` - Keyboard function pattern
- `docs/preguntas.json` - 175 trivia questions with format

### Secondary (MEDIUM confidence)
- DESIGN.md (this phase) - Game requirements and architecture

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - using existing aiogram/SQLAlchemy, no new packages
- Architecture: HIGH - follows existing patterns (DailyGiftService, gamification handlers)
- Pitfalls: HIGH - clear what to avoid (handler business logic, missing enum)

**Research date:** 2026-04-06
**Valid until:** 30 days (stable tech stack)