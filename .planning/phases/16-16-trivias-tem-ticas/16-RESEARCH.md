# Phase 16: Trivias Temáticas - Research

**Researched:** 2026-05-09
**Domain:** Trivia thematic categories, streak bonuses, admin category management
**Confidence:** HIGH

## Summary

Phase 16 extends the existing trivia system (Phase 14) to support thematic question categories managed as separate JSON files, a per-user draw-without-repetition deck that resets daily, streak milestone bonuses (3/5/7/10 correct answers), and an admin interface for category activation/deactivation. The implementation reuses the existing `GameService` pattern, `GameRecord` model, and `game_type` string field (which does NOT require a migration for new values).

**Key architectural insight:** `GameRecord.game_type` is `String(20)` -- NOT an enum. New game_type `'trivia_tematica'` can be used immediately without any DB migration. Similarly, `TransactionSource.TRIVIA` already exists and can be reused for thematic trivia besitos. The streak system exists for display only -- no bonus besitos are currently awarded for streaks; this phase introduces that logic.

**Primary recommendation:** Extend `GameService` with thematic trivia methods (mirroring the existing VIP trivia pattern), introduce a `TriviaCategoryService` for JSON file discovery and admin state, and add a new admin handler file for the category management interface.

## User Constraints (from CONTEXT.md)

<user_constraints>
### Locked Decisions

#### Modelo de Categorías
- **D-01:** Las categorías son archivos JSON separados, ej: `preguntas_halloween.json`, `preguntas_navidena.json`. El nombre del archivo es el identificador de la categoría.
- **D-02:** Las categorías son **invisibles para los usuarios** -- son herramientas internas de administración para dinámicas y eventos especiales.
- **D-03:** `docs/preguntas.json` se mantiene intacto como el mazo "general" por defecto.

#### Sistema de Mazo
- **D-04:** Draw sin repetición: cada usuario tiene su propio registro de preguntas respondidas por día. Una pregunta ya respondida no se vuelve a mostrar hasta el reinicio diario.
- **D-05:** El mazo se reinicia cada 24h (sigue el patrón de límites diarios existente).
- **D-06:** Cuando una categoría temática está activa, **reemplaza completamente** al mazo general (no se combinan). Solo una categoría activa a la vez.
- **D-07:** Por defecto (sin categoría activa), siempre se usa el mazo general de `preguntas.json`.
- **D-08:** El mazo es independiente de los límites diarios -- solo controla que no se repitan preguntas dentro de la sesión diaria.

#### Recompensas por Racha
- **D-09:** Besitos bonus al alcanzar hitos de racha (además del besito base por respuesta correcta):
  - Racha de 3: +2 besitos (normal) / +4 (VIP)
  - Racha de 5: +5 besitos (normal) / +10 (VIP)
  - Racha de 7: +10 besitos (normal) / +20 (VIP)
  - Racha de 10: +20 besitos (normal) / +40 (VIP)
- **D-10:** Los hitos son los mismos para trivia normal y VIP. VIP recibe el doble de bonus.
- **D-11:** La racha se reinicia al fallar una respuesta (mismo comportamiento actual).

#### Integración con Trivia Existente
- **D-12:** Durante una dinámica temática, aparece un **botón especial visible** en el menú de juegos (ej: "🎃 Trivia de Halloween") con nombre personalizado. No reemplaza el botón de trivia general.
- **D-13:** La trivia temática tiene **límites diarios independientes** de la general. No consume los intentos de la trivia normal.
- **D-14:** El admin gestiona categorías desde el panel de administración existente con interfaz visual de botones inline. Opciones: activar categoría, desactivar, programar por fecha, ver estado actual.
- **D-15:** Las preguntas las prepara Diana/equipo externamente como archivos JSON. El admin no crea preguntas desde el bot.

### Claude's Discretion
- Los montos exactos de bonus de racha pueden ajustarse por balance si se considera necesario durante implementación/pruebas.
- El formato específico del botón temático en el menú de juegos (nombre, ícono) queda a discreción de implementación.

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Category state (active/inactive) | Database / Storage | -- | Admin-set category state must persist across bot restarts; a simple DB model or config file stores it |
| Question file management | Database / Storage | -- | JSON files in `docs/` are the source of truth (D-01, D-15); admin only activates/deactivates, does not edit |
| Draw-without-repetition (deck) | API / Backend | -- | Tracks per-user, per-day answered questions in `GameRecord` with `game_type='trivia_tematica'` |
| Streak calculation | API / Backend | -- | Uses same pattern as `_get_trivia_streak()` -- query today's GameRecords in DESC order |
| Streak bonus awarding | API / Backend | -- | `BesitoService.credit_besitos()` is called when streak milestone is reached |
| Thematic button in game menu | Browser / Client | API / Backend | `game_menu_keyboard()` is modified to accept optional category name; handler queries active category from service |
| Daily limit tracking | API / Backend | Database / Storage | Uses `get_today_play_count(user_id, 'trivia_tematica')` with new limit constants |
| Admin category management | Browser / Client | API / Backend | New admin handler file + inline keyboard buttons; reads/writes category state via service |
| Scheduled activation | API / Backend | -- | Reuses `SchedulerService` with APScheduler `DateTrigger` for one-shot timed category activation |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiogram | 3.x | Telegram bot framework | Already the project's bot framework |
| SQLAlchemy | 2.x | ORM for persistence | Already the project's ORM |
| APScheduler | 3.x | Job scheduling for timed activation | Already used by `SchedulerService` with `SQLAlchemyJobStore` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | -- | JSON file loading for questions | Already used in `GameService.load_trivia_questions()` |
| pathlib.Path | -- | File discovery for category JSONs | Already used to locate `docs/preguntas.json` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| String(20) `game_type` | ENUM in PostgreSQL | String(20) is already the existing pattern (`game_records` table). No migration needed. |
| DB model for category state | JSON state file | DB model survives resets and is queryable. JSON file is simpler but less robust. |
| New `TriviaCategoryService` | Extend `GameService` | A separate service follows project domain pattern (one service per domain). `GameService` is already large; thematic trivia is a distinct subdomain. |

**Installation:**
```bash
# No new dependencies needed. Everything uses existing stack.
```

## Architecture Patterns

### System Architecture Diagram

```
[Admin] --activates category--> [admin_handler category_menu] --writes--> [TriviaCategory state in DB]
                                                                                |
                                                                                v
[Daily Reset at UTC 00:00]                                              [Category is active?]
                                                                              /       \
                                                                           YES         NO
                                                                            |            |
                                                                            v            v
[Preguntas file path] = docs/preguntas_{cat}.json           [Preguntas file path] = docs/preguntas.json
                                                                            |
                                                                            v
                                                              [GameService method]
                                                              load_questions(file_path)
                                                                            |
                                                                            v
[User opens game_menu] -----> [game_menu_keyboard() checks active category]
                                    |           |
                                    |           +-- no active cat: show normal 3-button menu
                                    |
                                    +-- active cat: add thematic button + label text
                                         |
                                         v
[User taps thematic button] --> [game_trivia_tematica callback]
                                    |
                                    v
                         [draw_without_repetition]
                         query GameRecord WHERE
                         user_id=X AND game_type='trivia_tematica'
                         AND played_at >= TODAY
                                    |
                                    +-- all answered today? --> reset message (wait till tomorrow)
                                    |
                                    +-- answered IDs exclude from candidate pool
                                    |       |
                                    |       v
                                    |  [pick random from remaining]
                                    |       |
                                    |       v
                                    |  [show question with trivia_keyboard]
                                    |
                                    +-- [check answer]
                                         |
                                         +-- correct? credit besitos, check streak, award milestone bonus
                                         |
                                         +-- incorrect? reset streak, show correct answer

[Streak milestone check]
    new_streak in (3, 5, 7, 10)?
        |       |
        YES     NO
        |       |
        v       v
  credit bonus  nothing
  besitos       else
```

### Recommended Project Structure

```
services/
├── game_service.py              # EXTEND: add thematic trivia methods (+ deck tracking)
├── trivia_service.py            # NEW: category state management (activate/deactivate/list)
├── __init__.py                  # ADD: TriviaService to imports and __all__

handlers/
├── game_user_handlers.py        # EXTEND: add game_trivia_tematica handler
├── trivia_admin_handlers.py     # NEW: category management admin handlers

keyboards/
├── inline_keyboards.py          # EXTEND: add game_menu_keyboard_tematica variant or parameter

models/
├── models.py                    # NEW: TriviaCategory model (optional -- could use JSON config)
├── __init__.py                  # ADD: TriviaCategory if new model created

docs/
├── preguntas.json               # UNCHANGED: default general deck
├── preguntas_vip.json           # UNCHANGED: VIP deck
├── preguntas_halloween.json     # NEW: example thematic category
├── preguntas_navidena.json      # NEW: example thematic category
```

### Pattern 1: Extend GameService with Thematic Trivia (mirror VIP pattern)

**What:** The existing VIP trivia (`trivia_vip`) provides a complete template for how to add a new game_type. Every method has a VIP counterpart: `load_trivia_vip_questions()`, `get_random_vip_question()`, `play_trivia_vip()`, `_get_vip_trivia_streak()`, etc. Thematic trivia follows the same pattern.

**When to use:** When adding a new game_type that has the same lifecycle (load questions, pick random, check answer, track streak, record play).

**Pattern to follow:**
- New methods follow naming: `load_trivia_tematica_questions(category_id)`, `get_random_tematica_question()`, `play_trivia_tematica()`, `_get_tematica_trivia_streak()`
- Draw-without-repetition filtering happens between picking and showing; filter out question indices already answered today (query `GameRecord where user_id and game_type='trivia_tematica' and played_at >= today`)

### Pattern 2: Streak Milestone Bonuses

**What:** Currently, `_get_trivia_streak()` counts streak for display only. No bonus besitos are awarded. Phase 16 introduces bonus awards at milestones 3, 5, 7, 10.

**Implementation approach:**
```python
STREAK_MILESTONES = {3: 2, 5: 5, 7: 10, 10: 20}  # base bonus amounts

def _check_streak_milestone(self, new_streak: int, is_vip: bool = False) -> Optional[int]:
    """Returns bonus besitos if streak milestone reached, else None."""
    bonus = STREAK_MILESTONES.get(new_streak)
    if bonus is not None:
        return bonus * 2 if is_vip else bonus
    return None
```

This runs AFTER `credit_besitos` for the correct answer, granting the bonus as a SECOND `credit_besitos` call with a distinct `TransactionSource` and a description like "Bonus por racha de {streak}".

### Pattern 3: Category State Management

**Options for storing active category:**

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| `TriviaCategory` DB model | Persistent, queryable, supports scheduled activation fields | Requires Alembic migration | RECOMMENDED for full implementation |
| Simple JSON state file (`docs/trivia_categories_state.json`) | No migration needed, simple to implement | Race conditions on concurrent writes, less robust | Acceptable fallback |
| Single env var | Too simple | Cannot list available categories, no scheduling | Not recommended |

**Recommended model (or equivalent JSON state):**
```
active_category: str | None  # filename stem: "halloween", None = use default
active_category_display: str | None  # "🎃 Trivia de Halloween"
scheduled_activation: datetime | None
scheduled_deactivation: datetime | None
```

### Anti-Patterns to Avoid
- **Duplicate streak logic:** The streak calculation logic exists in `_get_trivia_streak()` and `_get_vip_trivia_streak()` -- extract to a shared method that accepts game_type parameter instead of creating a third copy.
- **Loading all questions into memory at startup:** The existing pattern loads and caches questions lazily (`_questions = None` pattern). Keep this -- thematic questions should be loaded on demand when the category is active.
- **Mixing deck and limit logic:** D-08 explicitly separates deck (avoids repetition) from daily limits (max plays). Keep them as two independent checks.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Job scheduling | Custom timer loops | `SchedulerService` with APScheduler `DateTrigger` | Already exists with SQLAlchemyJobStore for persistence; `schedule_free_welcome()` shows the one-shot job pattern |
| FSM state management | Custom state tracking | aiogram FSM (`StatesGroup`) | Already the project standard for multi-step wizards |
| Admin permission checks | Custom admin middleware | `lambda cb: is_admin(cb.from_user.id)` filter | Existing pattern used across all admin handlers |
| Question persistence | DB storage for questions | JSON files in `docs/` | D-01 and D-15 mandate this; Diana's team produces JSON files externally |
| Besitos transactions | BesitoService calls with `TransactionSource.TRIVIA` | Reuse existing TransactionSource | `TransactionSource.TRIVIA` already exists and covers any trivia-related earning; no enum migration needed |

**Key insight:** The existing trivia system (especially VIP trivia) provides a complete, battle-tested template for thematic trivia. The three primary innovations are: (1) draw-without-repetition filtering, (2) streak milestone bonuses, and (3) admin category toggling. Everything else follows established patterns.

## Common Pitfalls

### Pitfall 1: Deck Reset vs. Daily Limit Confusion
**What goes wrong:** Developers conflate "deck resets every 24h" with "daily limit resets every 24h" and try to merge the logic.
**Why it happens:** Both use date-based time windows; both filter GameRecords by `played_at >= today`.
**How to avoid:** D-08 states they are independent. The deck check answers "are there any unanswered questions remaining?" The limit check answers "has the user played too many times today?". Always check both, but never conflate their logic.
**Warning signs:** A single function returning both "no questions left" AND "limit reached" messages.

### Pitfall 2: Stacking Streak Bonuses
**What goes wrong:** When a user has a streak of 10, milestones 3, 5, 7, and 10 all trigger, awarding 2+5+10+20 = 37 bonus besitos.
**Why it happens:** The check fires on every correct answer and sees `new_streak` is in the milestones dict.
**How to avoid:** Only award the milestone for the EXACT value. Track the LAST awarded milestone per user per day, or only fire when `new_streak` equals the milestone value (checking previous streak ensures it wasn't already awarded). A better approach: only check milestones at the exact threshold -- streak=3 awards +2, streak=5 awards +5, etc. No stacking.
**Warning signs:** Total bonus besitos for a single answer exceed the intended amount.

### Pitfall 3: Overlapping Active Categories
**What goes wrong:** Multiple categories become active simultaneously (race condition on state writes, or scheduler activates a second before first deactivates).
**Why it happens:** D-06 says only one active at a time, but concurrent operations could violate this.
**How to avoid:** Implement state transitions atomically: when activating category B, deactivate category A in the same write operation. Serialize scheduler jobs with `max_instances=1` (already the default).
**Warning signs:** The trivia menu shows multiple thematic buttons.

### Pitfall 4: Forgetting That `game_record.game_type` Uses Free-Form String
**What goes wrong:** A developer tries to add `'trivia_tematica'` to a Python enum or runs `ALTER TYPE` in PostgreSQL.
**Why it happens:** Game developers expect enum-like type safety. The field is `String(20)` specifically to avoid enum migration overhead.
**How to avoid:** Just use `game_type='trivia_tematica'` directly. No migration, no enum changes.
**Warning signs:** Any code that attempts to validate `game_type` against a whitelist.

### Pitfall 5: Cache Invalidation for Category Switching
**What goes wrong:** Admin activates a new category, but `GameService` still has old questions cached in `self._questions`.
**Why it happens:** `load_trivia_questions()` caches with `if self._questions is not None: return self._questions`.
**How to avoid:** `load_trivia_questions()` for thematic categories should NOT cache aggressively, or should accept an optional `category_id` parameter that busts the cache when category changes. The thematic loading method should either: (a) accept no caching, or (b) cache by category file path so switching categories loads the new file.
**Warning signs:** Questions from the old category still appear after admin switches to a new category.

## Code Examples

### File Structure for a Thematic Question JSON
```json
[
  { "q": "¿Qué tradición de Halloween involucra tallar calabazas?", "opts": ["Trick or treat", "Jack-o'-lantern", "Dulce o truco"], "answer": 1 },
  { "q": "¿De qué color es típicamente la flor de Nochebuena?", "opts": ["Blanca", "Roja", "Dorada"], "answer": 1 }
]
```
**Format note:** Same structure as `preguntas.json` -- array of objects with `q`, `opts` (array of strings), `answer` (0-indexed integer).

### Existing Pattern: Loading Questions by Path
```python
# From game_service.py lines 575-593
def load_trivia_questions(self) -> list:
    """Carga preguntas de docs/preguntas.json"""
    if self._questions is not None:
        return self._questions

    questions_path = Path("docs/preguntas.json")
    if not questions_path.exists():
        logger.warning("Questions file not found: docs/preguntas.json")
        return []

    try:
        with open(questions_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self._questions = data if isinstance(data, list) else data.get('questions', [])
    except Exception as e:
        logger.error(f"Error loading trivia questions: {e}")
        self._questions = []

    return self._questions
```

### Existing Pattern: Draw-Without-Repetition Filtering

The existing `get_random_question()` picks from ALL questions. For thematic trivia, filter out already-answered question indices:

```python
def _get_answered_today(self, user_id: int, game_type: str) -> set:
    """Returns set of question indices already answered today."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    records = self.db.query(GameRecord).filter(
        GameRecord.user_id == user_id,
        GameRecord.game_type == game_type,
        GameRecord.played_at >= today
    ).all()
    answered = set()
    for r in records:
        # result format: "question_{idx}" for trivia
        if r.result.startswith("question_"):
            answered.add(int(r.result.split("_")[1]))
    return answered
```

### Existing Pattern: Streak Calculation
```python
# From game_service.py lines 263-272
def _get_trivia_streak(self, user_id: int) -> int:
    """Calcula racha actual de victorias en trivia (solo hoy)"""
    records = self._get_today_trivia_records(user_id)
    streak = 0
    for record in records:
        if record.payout > 0:
            streak += 1
        else:
            break
    return streak
```
(Query returns records ordered by `played_at DESC`, so streak counts consecutive wins from most recent backwards.)

### Existing Pattern: Admin Menu Button Addition
```python
# In admin_menu_keyboard() - add a new button to the existing list
[InlineKeyboardButton(
    text="🎯 Mazos de Trivia",
    callback_data="admin_trivia_categories"
)]
```

### Existing Pattern: Admin Section Handler
```python
# New file: handlers/trivia_admin_handlers.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config.settings import bot_config
import logging

logger = logging.getLogger(__name__)
router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in bot_config.ADMIN_IDS

@router.callback_query(F.data == "admin_trivia_categories", lambda cb: is_admin(cb.from_user.id))
async def admin_trivia_categories(callback: CallbackQuery):
    """Admin menu for managing trivia categories"""
    # List categories, show active, provide activate/deactivate/schedule buttons
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Random question from pool (with replacement) | Draw-without-repetition per user per day | Phase 16 | Users see fresh questions until pool exhausted for the day |
| Streak display only (no bonus besitos) | Streak milestone bonuses (3/5/7/10) | Phase 16 | New engagement mechanic rewards sustained correct answers |
| Single trivia game_type | Multiple game_type values: 'trivia', 'trivia_vip', 'trivia_tematica' | Phase 14-16 | Independent daily limits, separate tracking |
| Static game menu | Dynamic game menu with optional thematic button | Phase 16 | Menu adapts to active category without replacing general trivia |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `GameRecord.game_type = 'trivia_tematica'` requires no DB migration because the column is `String(20)` | Standard Stack | If column is actually an enum type on PostgreSQL -- but migration `c32861733e54` shows `sa.String(length=20)` [VERIFIED: codebase grep] |
| A2 | `TransactionSource.TRIVIA` is appropriate for thematic trivia besitos | Don't Hand-Roll | If Diana wants separate tracking of thematic vs. general trivia earnings in besito_transactions -- but this is an analytics concern, not a functional one |
| A3 | Existing `game_menu_keyboard(is_vip=False)` can be modified to accept category info | Architecture | If the keyboard function signature changes break existing callers -- verify all call sites are updated |
| A4 | Date-based deck reset at UTC midnight is sufficient | Architecture | If the bot uses a different timezone for "daily" -- but `get_today_play_count` uses `datetime.utcnow().replace(hour=0, minute=0, ...)` [VERIFIED: codebase] |

## Open Questions (RESOLVED)

1. **(RESOLVED)** **Category state storage: DB model vs. JSON file**
   - What we know: D-01/D-14 say admin manages categories. No decision on WHERE the active/inactive state lives.
   - What's unclear: Whether a lightweight JSON state file is sufficient, or a DB model is needed for scheduled activation queries.
   - Recommendation: Start with `TriviaCategory` DB model with columns: `id`, `file_name`, `display_name`, `is_active`, `scheduled_at`, `scheduled_end`. This supports all D-14 requirements (activate, deactivate, schedule, view status) and persists across restarts. Requires one Alembic migration.

2. **(RESOLVED)** **Streak bonus for general trivia vs. only thematic?**
   - What we know: D-10 says "Los hitos son los mismos para trivia normal y VIP."
   - What's unclear: Should general trivia also award streak bonuses, or only in this phase?
   - Recommendation: Implement bonuses in a shared _award_streak_bonus() method. Decide at implementation whether to backport bonuses to general trivia or only apply to thematic. Given D-10 mentions "normal" trivia, the bonuses should apply uniformly to all trivia types.

3. **(RESOLVED)** **How does daily deck reset interact with active answered state?**
   - What we know: Deck resets every 24h (D-05). Draw-without-repetition only applies within daily session (D-08).
   - What's unclear: Should the reset happen at UTC midnight (existing limit pattern) or at a custom hour?
   - Recommendation: Follow existing pattern -- `played_at >= today` with UTC midnight. This aligns with daily limits.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | (project configured) | -- |
| PostgreSQL | Production | ✓ | (Railway) | SQLite for local dev |
| APScheduler | Timed activation | ✓ | (in SchedulerService) | Manual activation only |
| Json (stdlib) | Question loading | ✓ | -- | -- |

**Missing dependencies with no fallback:** None -- everything uses existing project stack.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pytest.ini` |
| Quick run command | `pytest -x tests/ --ignore=tests/e2e -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

No formal requirement IDs exist for Phase 16. The following behaviors need tests:

| Behavior | Test Type | Automated Command | Notes |
|----------|-----------|-------------------|-------|
| Category activation state persistence | unit | `pytest tests/unit/test_trivia_service.py -x -q` | Wave 0 -- new file |
| Draw-without-repetition logic | unit | `pytest tests/unit/test_game_service.py::test_draw_without_repetition -x -q` | Add to existing test file |
| Streak milestone bonus calculation | unit | `pytest tests/unit/test_game_service.py::test_streak_milestone_bonus -x -q` | Add to existing test file |
| Streak bonus does not stack | unit | `pytest tests/unit/test_game_service.py::test_streak_no_stacking -x -q` | Edge case test |
| Thematic trivia has independent limits | integration | `pytest tests/integration/test_trivia_handler.py -x -q` | Wave 0 -- new file |
| Thematic button appears in game menu | integration | See above | -- |
| Category file not found handling | unit | `pytest tests/unit/test_trivia_service.py::test_category_file_not_found -x -q` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest -x tests/unit/test_trivia_service.py tests/unit/test_game_service.py -q`
- **Per wave merge:** `pytest -x tests/ --ignore=tests/e2e -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps (RESOLVED)
- [x] `tests/unit/test_trivia_service.py` -- created as Wave 0 stub
- [x] `tests/integration/test_trivia_handler.py` -- created as Wave 0 stub
- [ ] `tests/unit/test_game_service.py` -- extend with streak bonus tests (needs game_service.py file; no existing test file for this service)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | All users authenticated via Telegram |
| V3 Session Management | no | Stateless handlers |
| V4 Access Control | yes | `is_admin(user_id)` check on all admin category handlers |
| V5 Input Validation | yes | Validate callback data parsing; validate question_idx and answer_idx bounds |
| V6 Cryptography | no | No cryptographic operations |

### Known Threat Patterns for aiogram + SQLAlchemy

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Callback data tampering | Tampering | Validate all parsed callback data: `answer_idx` must be 0-3, `question_idx` must be valid index |
| Admin privilege escalation | Elevation of Privilege | `is_admin()` check on every admin handler. Already the project standard. |
| Concurrent category state writes | Tampering | Use DB transaction for state changes; or use SERIALIZABLE isolation if PostgreSQL |

## Sources

### Primary (HIGH confidence)
- [CITED: codebase] `services/game_service.py` -- Full trivia lifecycle (loading, playing, streak, limits)
- [CITED: codebase] `handlers/game_user_handlers.py` -- Trivia callback handlers (game_trivia, trivia_answer, game_trivia_vip, trivia_vip_answer)
- [CITED: codebase] `models/models.py:1089-1098` -- GameRecord model definition (game_type as String(20))
- [CITED: codebase] `models/models.py:167-177` -- TransactionSource enum (TRIVIA value exists)
- [CITED: codebase] `keyboards/inline_keyboards.py:424-431` -- game_menu_keyboard function
- [CITED: codebase] `handlers/admin_handlers.py:79-118` -- Admin menu keyboard and section pattern
- [CITED: codebase] `alembic/versions/c32861733e54_add_game_records_table_for_minijuegos.py` -- game_type declared as String(20)
- [CITED: codebase] `alembic/versions/20250406_add_trivia_to_transaction_source_enum.py` -- Pattern for adding enum values
- [CITED: codebase] `services/scheduler_service.py` -- Scheduler with DateTrigger for one-shot jobs
- [CITED: codebase] `docs/preguntas.json` -- Question JSON format (array of {q, opts, answer})

### Secondary (MEDIUM confidence)
- [CITED: codebase] `CONTEXT.md` decisions D-01 through D-15 -- All locked decisions verified in source

### Tertiary (LOW confidence)
None -- all claims verified against the codebase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries and patterns verified in existing codebase
- Architecture: HIGH -- VIP trivia provides a complete template; migration, enum, and model details verified
- Pitfalls: HIGH -- identified from codebase patterns and D decision analysis

**Research date:** 2026-05-09
**Valid until:** 2026-06-09 (stable stack -- all existing, no new versions)
