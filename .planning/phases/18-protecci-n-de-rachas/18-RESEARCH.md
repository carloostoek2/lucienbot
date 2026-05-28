# Phase 18: Proteccion De Rachas - Research

**Researched:** 2026-05-23
**Domain:** Streak protection & risk mode for trivia promotions (Phase 17 extension)
**Confidence:** HIGH

## Summary

Phase 18 extends the Phase 17 streak promotion system (`StreakPromotionService` + `StreakPromotionCode`) with three new capabilities: (1) streak protection purchased with besitos when a user fails a question, (2) a risk-mode FSM flow where users choose to retire and keep codes or continue for bigger codes, and (3) a 2-minute timeout mechanism when a user fails without enough besitos to pay.

The existing `play_trivia`/`play_trivia_vip`/`play_trivia_simple` methods in `GameService` already call `claim_for_streak()` after every correct answer and return `promo_code` in the result dict. The current handlers (`trivia_answer`, `trivia_vip_answer`, `trivia_simple_answer`) wrap this result into a pre-built `message` string and display it with a generic keyboard -- they do NOT inspect `promo_code` for logic decisions. Phase 18 needs to modify this to: (a) intercept failed answers to offer protection, (b) intercept tier-reached moments to offer retire/continue choices via FSM, and (c) cancel all session codes on failure in risk mode.

**Primary recommendation:** Add `StreakSession` model for lifecycle tracking, extend `StreakPromotionCode` with `session_id` FK, add `CANCELLED` to `StreakPromotionCodeStatus` enum, modify `claim_for_streak()` to link codes to the active session, and layer FSM states (`TriviaStreakStates`) into the three existing trivia answer handlers. Use lazy timeout verification (check `expires_at` on next interaction) rather than scheduled jobs -- simpler, no DB-vs-scheduler coupling, matches existing patterns. For cleanup of stale sessions, add an optional daily cron job.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Agregar `CANCELLED` al enum `StreakPromotionCodeStatus`. Valor: `"cancelled"`. Los codigos CANCELLED son aquellos que el usuario perdio tras fallar en modo arriesgo o timeout.
- **D-02:** Los codigos NUNCA se marcan como USED al entregarse. Solo el admin los marca USED manualmente. Esto ya existe en Phase 17 y se mantiene.
- **D-03:** Nuevo modelo `StreakSession` con campos: id (UUID PK), user_id (int), promotion_id (int FK), is_in_risk_mode (bool), protection_used (bool), codes_delivered (JSON list de code_ids), started_at (datetime), expires_at (datetime para timeout de 2 min).
- **D-04:** Relacion 1:N: un `StreakSession` puede tener multiples `StreakPromotionCode` (via `session_id` FK en `StreakPromotionCode`).
- **D-05:** Costo de proteccion: formula `5 + (streak // 3) * 5` besitos. Ej: streak 0-2 => 5, streak 3-5 => 10, streak 6-8 => 15.
- **D-06:** Proteccion disponible desde la primera pregunta. Se ofrece al fallar una respuesta.
- **D-07:** Si el usuario tiene proteccion disponible y besitos suficientes, puede comprarla. Se debitan los besitos, `protection_used = True`, y el streak continua.
- **D-08:** Si ya uso la proteccion (`protection_used = True`) y vuelve a fallar: pierde el streak a 0, TODOS los codigos DELIVERED de esa sesion se marcan CANCELLED.
- **D-09:** Si falla y no tiene besitos suficientes para proteger: se le ofrece ir a trivia libre para ganar besitos. Timeout de 2 minutos.
- **D-10:** Cuando el usuario alcanza un tier (`claim_for_streak` entrega un codigo), se activa FSM state con dos opciones: "Continuar por X%" (siguiente nivel) o "Retirarse con Y%" (conservar codigos actuales).
- **D-11:** Si elige retirarse: los codigos quedan en DELIVERED, la sesion se cierra, el admin los ve en el panel.
- **D-12:** Si elige continuar: entra en modo arriesgo (`is_in_risk_mode = True`). Si falla una pregunta en este modo, TODOS los codigos de la sesion se marcan CANCELLED.
- **D-13:** Si el usuario falla, no tiene besitos para proteger, y no tiene proteccion disponible, se le da timeout de 2 minutos para ganar besitos en trivia libre y volver.
- **D-14:** Si no regresa en 2 minutos: streak y codigos se pierden (CANCELLED).
- **D-15:** El timeout se implementa con `expires_at` en `StreakSession` y se verifica al reingresar.
- **D-16:** Se necesitan 6 handlers/callbacks nuevos: game_trivia_promo (entry point), trivia_promo_answer (procesa respuestas con logica de proteccion), waiting_retire_choice (FSM state para retirarse/continuar), trivia_promo_accept_protection, trivia_promo_decline_protection, trivia_promo_timeout.
- **D-17:** Estos handlers extienden el flujo de trivia existente, no lo reemplazan. El entry point normal de trivia sigue funcionando igual.

### Claude's Discretion
- Diseno exacto de los mensajes de Lucien para ofrecer proteccion, retirarse/continuar, timeout
- Formato de teclados inline para las opciones (proteger/no proteger, continuar/retirarse)
- Estrategia de limpieza de sesiones expiradas (scheduler job o lazy cleanup)
- Si la trivia libre durante el timeout debe tener algun limite especial
- Implementacion exacta del timeout (job programado vs verificacion lazy en cada interaccion)

### Deferred Ideas (OUT OF SCOPE)
None -- PRD covers complete phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TBD | Requirements not yet assigned IDs in REQUIREMENTS.md | This phase extends Phase 17 trivia promo flows. Requirements derived from CONTEXT.md D-01 through D-17 |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| StreakSession lifecycle | API / Backend | Database | Session is a DB entity managed by StreakPromotionService |
| Protection payment (besito debit) | API / Backend | -- | BesitoService handles balances; new TransactionSource required |
| claim_for_streak() modification | API / Backend | -- | StreakPromotionService owns code delivery logic |
| FSM risk-mode flow | Browser / Client (Telegram) | API / Backend | aiogram FSM states in handlers; service validates state transitions |
| Timeout enforcement | API / Backend | -- | Lazy verification: check expires_at on each interaction. No scheduled job per session. |
| Timeout cleanup (stale sessions) | API / Backend | -- | Optional daily cron in SchedulerService or lazy-on-next-interaction |
| Inline keyboard for protection/risk | Browser / Client (Telegram) | -- | New keyboard functions in inline_keyboards.py |
| CANCELLED enum migration | Database | -- | Enum-first Alembic migration per models/CLAUDE.md rules |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy (via models.py) | 2.x (project dep) | ORM for StreakSession, code status updates | [VERIFIED: codebase grep] Standard ORM for the project |
| aiogram | 3.x (project dep) | FSM states, callback data, inline keyboards | [VERIFIED: codebase grep] Current handler pattern uses `Router` + `CallbackData.filter()` |
| Alembic | 1.18.4 | Migration for new table + enum value + FK | [VERIFIED: Bash `pip show alembic`] Same migration toolchain |
| APScheduler | 3.x (project dep) | Optional cleanup job for expired sessions | [VERIFIED: codebase grep] Already used via `SchedulerService` with `DateTrigger` |
| uuid (stdlib) | built-in | UUID primary keys for StreakSession | [VERIFIED: Python stdlib] No external dep needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | built-in | Serialize `codes_delivered` list in StreakSession | Always (for JSON column) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| UUID PK for StreakSession | Integer auto-increment PK | UUID avoids collision in distributed context (future-proof); int is simpler. D-03 locked UUID. |
| Lazy timeout check | Scheduled APScheduler job per session | Scheduler jobs are one-shot (DateTrigger) but require bot reference. Lazy check avoids coupling; simpler. I recommend lazy. |
| New StreakPromotionService methods | Extend existing methods | Extending is preferred -- same service owns the domain |

**Installation:** No new packages required. All deps already in project.

## Architecture Patterns

### System Architecture Diagram

```
User answers trivia question
         │
         ▼
[trivia_answer handler] ──calls──▶ [GameService.play_trivia()]
         │                                    │
         │                              ┌─────┴──────┐
         │                         correct?       incorrect?
         │                              │              │
         │                    claim_for_streak()    ▼
         │                    [code delivered?]   [check session]
         │                              │              │
         │                         ┌────┴────┐    protection_used?
         │                      yes          no   │         │
         │                        │          │   yes        no
         │                   FSM state     normal │         │
         │                   retire/cont   message │    has besitos?
         │                        │                │     │       │
         │              ┌────────┴────────┐       all   yes      no
         │           retire            continue   codes  │        │
         │              │                 │       CANCELLED  debit +  timeout 2min
         │         session.close()  is_in_risk=  streak=0   protect   (free trivia)
         │         codes stay        True        │          streak     │
         │         DELIVERED         │          ─┘        continues   ─┘
         │                           ▼                               │
         │                     next question                  lazy verify
         ▼                           │                      expires_at on
    [return to user]                 ▼                      next interaction
         │                    [normal flow]
         ▼
    result['message'] + keyboard
```

### Recommended Project Structure
```
models/
├── models.py                    # ADD: StreakSession model, ADD: CANCELLED to enum, ADD: session_id FK

services/
├── streak_promotion_service.py  # EXTEND: start_session(), close_session(), get_active_session(),
│                                  # cancel_session_codes(), calculate_protection_cost()
├── game_service.py              # EXTEND: check_streak_session() in play_trivia/VIP/simple,
│                                  # add check_timeout() pattern
├── besito_service.py            # USE: has_sufficient_balance(), debit_besitos() - already exists

handlers/
├── game_user_handlers.py        # EXTEND: add FSM states, modify trivia_answer for protection logic,
│                                  # add retire/continue callbacks, add timeout handling

keyboards/
├── callback_data.py             # ADD: StreakProtectCallback, StreakRetireCallback, etc.
├── inline_keyboards.py          # ADD: protection_keyboard(), risk_mode_keyboard(), timeout_keyboard()

alembic/versions/
├── XXXX_add_streak_session.py   # NEW: StreakSession table + CANCELLED enum + session_id FK
```

### Pattern 1: FSM State Extension (without breaking existing flow)
**What:** Add `TriviaStreakStates` StatesGroup to `game_user_handlers.py`. Existing handlers remain unchanged; new callbacks intercept specific states.
**When to use:** For the retire/continue risk-mode flow (D-10 through D-12).
**Example:**
```python
# Source: [VERIFIED: codebase - game_user_handlers.py current pattern]
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

class TriviaStreakStates(StatesGroup):
    waiting_retire_choice = State()  # "Retirarse con Y%" vs "Continuar por X%"
    waiting_protection_choice = State()  # "Proteger (-X besitos)" vs "No proteger"
    in_timeout = State()  # Timeout de 2 minutos: trivia libre

# Handler pattern - filter on FSM state:
@router.callback_query(F.data == "streak_retire", TriviaStreakStates.waiting_retire_choice)
async def handle_streak_retire(callback: CallbackQuery, state: FSMContext):
    """Usuario elige retirarse y conservar codigos."""
    user_id = callback.from_user.id
    with get_service(StreakPromotionService) as service:
        service.close_session(user_id, retire=True)  # codes stay DELIVERED
    await state.clear()
    ...
```

### Pattern 2: Lazy Timeout Verification
**What:** Store `expires_at` in `StreakSession`. On every interaction (answer, protection decision), check if `now > expires_at`. If expired, cancel session codes and clear FSM.
**When to use:** For the 2-minute timeout (D-13, D-14, D-15). Avoids per-session scheduled jobs.
**Example:**
```python
# Source: [ASSUMED pattern - derived from scheduler_service.py DateTrigger pattern]
def _check_session_timeout(self, user_id: int) -> bool:
    """Check if user's active session has expired. Returns True if still valid."""
    session = self.get_active_session(user_id)
    if not session:
        return True  # No session = no timeout
    if session.expires_at and datetime.now(timezone.utc) > session.expires_at:
        self.cancel_session_codes(session.id)
        return False
    return True
```

### Pattern 3: claim_for_streak() Extension
**What:** Modify `claim_for_streak()` to: (1) check for an active `StreakSession`, (2) create or reuse session, (3) append `code.id` to session's `codes_delivered` JSON, (4) set `code.session_id`. Existing logic (status=DELIVERED, redemption record) unchanged.
**When to use:** Every correct answer triggers `claim_for_streak`. The session tracking is layered on top.
**Example:**
```python
# Source: [VERIFIED: codebase - streak_promotion_service.py:192-222]
def claim_for_streak(self, user_id: int, game_type: str, streak: int,
                     category_id: str = None) -> Optional[dict]:
    db = self._get_db()
    # ... existing logic to find promotion/level/code ...
    # NEW: Link code to active session
    session = self._get_or_create_session(user_id, code.level.promotion_id)
    code.session_id = session.id
    codes = json.loads(session.codes_delivered or '[]')
    codes.append(code.id)
    session.codes_delivered = json.dumps(codes)
    # ... existing: set status=DELIVERED, create redemption, commit ...
```

### Anti-Patterns to Avoid
- **FSM state logic in GameService:** Keep FSM transitions in handlers. GameService checks `StreakSession` state (is_in_risk_mode, protection_used) but never sets FSM states.
- **Direct DB access in handlers:** All session queries go through `StreakPromotionService`. Handlers only call service methods.
- **Modifying play_trivia return structure:** The current return dict is consumed by handlers. Extend it with a `session_state` key rather than changing existing keys.
- **Scheduled job per session for timeout:** Creates coupling between scheduler and user interaction. Use lazy verification instead.
- **Duplicate session checking across three trivia types:** Factor session-check logic into a single `_check_and_update_session()` private method in `GameService`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session timeout tracking | Custom timer/thread per session | `expires_at` datetime + lazy check on next interaction | Simpler, no concurrency issues, no bot reference needed in timer |
| UUID generation | Random string generation | `uuid.uuid4()` from Python stdlib | Standard, collision-safe, already imported in many places |
| JSON serialization for codes_delivered | Custom serialization | `json.dumps()`/`json.loads()` | Used throughout project (e.g., `TriviaPromotionConfig.discount_tiers`) |
| Balance checking before protection payment | Custom balance query | `BesitoService.has_sufficient_balance()` + `debit_besitos(commit=False)` | Already exists, race-condition-safe via SELECT FOR UPDATE |
| Enum value migration | SQLAlchemy autogenerate in same migration | Dedicated enum-first migration per models/CLAUDE.md | PostgreSQL cannot DROP enum values; dedicated migration is idempotent |

**Key insight:** The protection payment must be atomic with the session state update. Use `debit_besitos(commit=False)` to defer commit, then commit both the debit transaction and session update in one DB transaction to avoid inconsistent state where besitos are debited but protection isn't applied.

## Runtime State Inventory

> This is a greenfield extension phase (no rename/refactor/migration of existing strings). The new model `StreakSession` and enum value `CANCELLED` are additive, not replacements.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None -- new `StreakSession` table created, existing `streak_promotion_codes` gets nullable `session_id` FK | Code edit (add column + FK in migration) |
| Live service config | None -- no external services reference streak promo data | None |
| OS-registered state | None -- no OS-level registrations for this domain | None |
| Secrets/env vars | None -- no new env vars or secrets needed | None |
| Build artifacts | None -- no installed packages or build artifacts affected | None |

## Common Pitfalls

### Pitfall 1: Not checking session timeout before every interaction
**What goes wrong:** User enters risk mode, closes Telegram, comes back 10 minutes later -- if timeout is only checked on the "next question" callback but they use a different callback (menu, back), they bypass timeout enforcement.
**Why it happens:** Timeout check is only added to the specific answer/protection handlers, not to a generalized middleware or entry-point check.
**How to avoid:** Add `_check_session_timeout()` call at the start of every handler that touches trivia promo state. Alternatively, add session timeout check as a callback filter or in `GameService` entry methods like `get_trivia_entry_data()`.
**Warning signs:** Users accumulating session codes that should have expired.

### Pitfall 2: Session creation on wrong event
**What goes wrong:** Creating a `StreakSession` on every `get_trivia_entry_data()` or menu view, generating empty sessions. Sessions should only be created when a user actually begins a trivia round where promotions apply.
**Why it happens:** The session creation hook is placed too early in the flow.
**How to avoid:** Create session lazily in `claim_for_streak()` when the first code is about to be delivered, or in `play_trivia()` at the first answer. Do NOT create sessions in entry/view methods.
**Warning signs:** Database filling with empty sessions (codes_delivered=[]).

### Pitfall 3: Inconsistent session state across trivia types
**What goes wrong:** Protection is applied in `trivia` (general) but risk mode only works in `trivia_simple`. Or session state changes in one trivia type but isn't visible in another.
**Why it happens:** Three separate play methods (`play_trivia`, `play_trivia_vip`, `play_trivia_simple`) each contain copy-pasted `claim_for_streak` blocks. Session logic must be duplicated or factored out.
**How to avoid:** Factor session-related logic into a shared private method `_handle_streak_session()` called by all three play methods, or add session handling inside `claim_for_streak()` itself.
**Warning signs:** Protection/risk mode works in general trivia but not VIP trivia.

### Pitfall 4: JSON column mutation without re-serialization
**What goes wrong:** `codes_delivered` JSON list is loaded, code ID appended, but not re-assigned to `session.codes_delivered` before commit. SQLAlchemy only detects changes to scalar columns and mutable JSON objects may be missed.
**Why it happens:** SQLAlchemy's change tracking doesn't detect in-place mutations of mutable Python objects (lists, dicts) stored in JSON columns.
**How to avoid:** Always re-assign: `session.codes_delivered = json.dumps(codes)` after mutating the list. Never do `codes.append(...)` without the re-assignment.
**Warning signs:** Codes silently not persisted in session; user reports "missing" codes.

### Pitfall 5: Reference branch `resp_trivia_multiniveles` traps
**What went wrong in reference branch:**
- Used a completely different model structure (`TriviaPromotionConfig`/`DiscountCode`) that doesn't match the current `StreakPromotion*` models on main [VERIFIED: git diff main...resp_trivia_multiniveles]
- `get_all_promotions` had bugs (referenced in CONTEXT.md but specific diff not available)
- Handler callbacks were broken (likely due to callback_data mismatch between old and new callback types)
- `max_codes` validation failed (validation logic in different model hierarchy)
- The FSM patterns in the reference branch (`TriviaStreakStates.waiting_streak_choice`, `streak_continue`) were conceptually sound but implemented against the wrong models
**How to avoid:** Do NOT reuse code from the reference branch. Study the FSM pattern but implement against current `StreakPromotion*` models.

## Code Examples

### Convencion de naming para enum
```python
# Source: [VERIFIED: models/models.py:679-683 - OrderStatus pattern]
class StreakPromotionCodeStatus(str, enum.Enum):
    AVAILABLE = "available"
    DELIVERED = "delivered"
    USED = "used"
    CANCELLED = "cancelled"  # NEW: matches OrderStatus.CANCELLED convention
```

### BesitoService debit with atomic commit
```python
# Source: [VERIFIED: services/besito_service.py:131-187]
# Pattern for protection payment - atomic with session update:
besito_service = BesitoService(db)
# Use commit=False to defer commit
if not besito_service.debit_besitos(
    user_id=user_id,
    amount=cost,
    source=TransactionSource.STREAK_PROTECTION,  # NEW enum value needed
    description=f"Proteccion de racha streak={streak}",
    commit=False  # Defer commit for atomicity with session update
):
    return False  # Insufficient balance
# Then update session and commit both:
session.protection_used = True
db.commit()
```

### FSM state transition pattern
```python
# Source: [VERIFIED: handlers/game_user_handlers.py:100-165 - current trivia flow]
# Pattern for adding FSM to existing trivia answer handler:
@router.callback_query(TriviaAnswerCallback.filter())
async def trivia_answer(callback: CallbackQuery, callback_data: TriviaAnswerCallback,
                        state: FSMContext):
    user_id = callback.from_user.id
    # ... existing play_trivia call ...
    if not result['correct']:
        # NEW: Check for active promo session and protection
        with get_service(StreakPromotionService) as promo_svc:
            session = promo_svc.get_active_session(user_id)
            if session:
                if not session.protection_used:
                    await state.set_state(TriviaStreakStates.waiting_protection_choice)
                    await state.update_data(question_idx=question_idx, streak=result['previous_streak'])
                    # Show protection keyboard
                    return
                else:
                    # Already used protection - cancel all codes
                    promo_svc.cancel_session_codes(session.id)
                    promo_svc.close_session(user_id, retire=False)
    # ... existing message display ...
```

### Alembic migration pattern (enum-first)
```python
# Source: [VERIFIED: models/CLAUDE.md + alembic/versions/36c345796281_add_streak_promotions_tables.py]
# Step 1: Enum migration (separate revision)
def upgrade():
    op.execute(
        "ALTER TYPE streakpromotioncodestatus ADD VALUE IF NOT EXISTS 'CANCELLED'"
    )

def downgrade():
    # PostgreSQL cannot DROP enum values; document this
    pass
```

### Inline keyboard pattern for protection
```python
# Source: [VERIFIED: keyboards/inline_keyboards.py:475-487 - trivia_keyboard pattern]
def protection_keyboard(protection_cost: int) -> InlineKeyboardMarkup:
    """Teclado para decision de proteccion de racha."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"Proteger (-{protection_cost} besitos)",
            callback_data="streak_protect_accept"
        )],
        [InlineKeyboardButton(
            text="No proteger",
            callback_data="streak_protect_decline"
        )]
    ])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| StreakPromotionCodeStatus: AVAILABLE, DELIVERED, USED | + CANCELLED | Phase 18 | Four states cover full lifecycle |
| No session tracking for codes | StreakSession with codes_delivered JSON | Phase 18 | Enables bulk cancel on risk-mode failure |
| Trivia handlers: stateless callbacks | + FSM states for retire/continue/protection | Phase 18 | New flow layered on existing without breaking |
| TransactionSource: existing 8 values | + STREAK_PROTECTION | Phase 18 | New transaction type for protection payment |

**Deprecated/outdated:**
- `resp_trivia_multiniveles` branch: Uses old `TriviaPromotionConfig`/`DiscountCode` models not in main. Do not reference for implementation.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Timeout enforcement via lazy check (expires_at) is preferred over scheduled jobs | Architecture Patterns | If interactive timeout requirements change, may need to refactor to scheduled job pattern |
| A2 | `TransactionSource.STREAK_PROTECTION` is appropriate name for the new enum value | Code Examples | If user prefers different name, enum migration + code references need update |
| A3 | StreakSession UUID PK is acceptable (not int) | Common Pitfalls | UUID overhead is negligible vs int; D-03 already locked this |
| A4 | Trivia_simple flow also needs protection/risk-mode (all three trivia types treated equally) | Common Pitfalls | If only general trivia should have protection, scope is narrower |
| A5 | `claim_for_streak()` is the right place to create/link sessions, not play_trivia | Architecture Patterns | If session needs to exist before first correct answer, creation point must move |
| A6 | Lazy timeout verification is the right approach (Claude's discretion per D-06) | Standard Stack | If user wants scheduled-job approach, implementation changes significantly |

## Open Questions (RESOLVED)

1. **Trivia promo entry point (D-16 mentions `game_trivia_promo` handler)**
   - What we know: D-16 lists 6 new handlers including `game_trivia_promo` as an entry point
   - What's unclear: Whether this entry point is user-visible (a new menu button) or internal (redirected from normal trivia when promotions are active). Current game menu has one "El examen de Diana" button for normal trivia.
   - Recommendation: Two possible implementations: (A) Redirect from normal trivia if active promotions exist, or (B) add new menu button "Las promociones de Diana" visible only when promotions are active. Plan both options and let discuss-phase decide.
   - **RESOLVED (Phase 18 Plan):** Protection/risk flows integrate into the existing 3 `trivia_answer` handlers (general/VIP/simple) rather than adding a separate entry point. When active promotions exist and a user starts trivia, the session is created lazily on first code delivery in `claim_for_streak()`. No new menu button needed; the existing trivia entry points (`/trivia`, `/trivia_vip`, `/trivia_simple`) cover this transparently. The 2-minute timeout state is handled via lazy verification (checking `expires_at` on next interaction) within these same handlers, avoiding the need for a dedicated `in_timeout` FSM state.

2. **Timeout trivia_free interaction (D-09, D-13)**
   - What we know: User plays "trivia libre" to earn besitos during timeout
   - What's unclear: Whether the free trivia during timeout should be limited (fewer questions? same limits?) or treat it as normal trivia. Whether earning enough besitos auto-clears the timeout state.
   - Recommendation: Free trivia uses normal limit. On each correct answer in free trivia mode, re-check `has_sufficient_balance()`. If now sufficient, auto-offer protection. The timeout check on next interaction handles expiration.
   - **RESOLVED (Phase 18 Plan):** Free trivia during timeout uses normal limits and question count. On each correct answer, the `_build_streak_failure_state()` method re-checks `has_sufficient_balance()`. If balance is now sufficient, the method returns `offer_protection` action so the handler shows the protection keyboard. Timeout enforcement is lazy: `get_active_session()` checks `expires_at` on every session access and cancels if expired. A 60-minute SchedulerService cleanup job handles stale sessions for users who never return.

3. **Session cleanup strategy (Claude's discretion)**
   - What we know: Sessions with expires_at in the past are "expired" but may remain in DB
   - What's unclear: Whether to add a scheduled cleanup job or rely on lazy expiration
   - Recommendation: Lazy + optional cron. Check `expires_at` on every session access; if expired, cancel and close. Add a daily cleanup cron via SchedulerService to remove truly stale sessions (>24h past expiration) as a safety net. This avoids scheduled-per-session complexity while preventing DB bloat.
   - **RESOLVED (Phase 18 Plan):** Hybrid approach: lazy verification + scheduled cleanup. Every `get_active_session()` call checks `expires_at` and cancels expired sessions on access. A 60-minute interval job in SchedulerService (`cleanup_streak_sessions`) handles sessions where the user never returns after timeout, preventing DB bloat. This avoids per-session scheduled jobs while maintaining data hygiene.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All code | Yes | 3.14.4 | -- |
| Alembic | Migration | Yes | 1.18.4 | -- |
| PostgreSQL (production) | Enum ALTER TYPE | Yes | Railway-hosted | -- |
| SQLite (local dev) | Enum ALTER TYPE fails on SQLite | Yes | Test migration on PostgreSQL | SQLite dev: manually add enum value to code definition |

**Missing dependencies with no fallback:** None. All deps available.
**Missing dependencies with fallback:** None.

### SQLite Caveat
PostgreSQL `ALTER TYPE ... ADD VALUE IF NOT EXISTS` does NOT work on SQLite. The enum-first migration pattern is PostgreSQL-specific. For local dev with SQLite, the migration must be manually skipped or the SQLAlchemy enum definition must include CANCELLED before running the migration. This is a known pattern in the project -- the production DB is PostgreSQL and CI verifies against it.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project standard) |
| Config file | tests/conftest.py |
| Quick run command | `python -m pytest tests/ -x -k "streak_session"` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-TBD-01 | CANCELLED enum value present | unit | `python -m pytest tests/ -x -k "test_streak_code_status_enum"` | No - Wave 0 |
| REQ-TBD-02 | StreakSession created on first code delivery | unit | `python -m pytest tests/ -x -k "test_streak_session_creation"` | No - Wave 0 |
| REQ-TBD-03 | Protection payment debits correct besito amount | unit | `python -m pytest tests/ -x -k "test_protection_cost"` | No - Wave 0 |
| REQ-TBD-04 | Protection unavailable after use (protection_used=True) | unit | `python -m pytest tests/ -x -k "test_protection_single_use"` | No - Wave 0 |
| REQ-TBD-05 | Risk mode failure cancels all session codes | unit | `python -m pytest tests/ -x -k "test_risk_mode_cancel_all"` | No - Wave 0 |
| REQ-TBD-06 | Retire preserves codes in DELIVERED state | unit | `python -m pytest tests/ -x -k "test_retire_preserves_codes"` | No - Wave 0 |
| REQ-TBD-07 | Timeout cancels codes when expires_at passed | unit | `python -m pytest tests/ -x -k "test_timeout_cancels_codes"` | No - Wave 0 |
| REQ-TBD-08 | FSM state transitions: retire, continue, protect, decline | integration | `python -m pytest tests/ -x -k "test_fsm_streak_states"` | No - Wave 0 |
| REQ-TBD-09 | Existing trivia flow unchanged when no session active | integration | `python -m pytest tests/ -x -k "test_trivia_no_session_unchanged"` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -k "streak_session or streak_promotion"` 
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_streak_protection.py` -- covers all REQ-TBD-XX unit tests
- [ ] `tests/test_streak_fsm.py` -- covers FSM state transition integration tests
- [ ] `tests/conftest.py` -- add StreakSession and promotion fixtures

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | No | -- |
| V3 Session Management | Yes (FSM) | aiogram FSM with RedisStorage -- state validates user ownership |
| V4 Access Control | Yes | Verify user_id matches session owner on every interaction |
| V5 Input Validation | Yes | Callback data validated via aiogram CallbackData filter -- no raw string parsing |
| V6 Cryptography | No | -- |

### Known Threat Patterns for aiogram + SQLAlchemy trivia promo

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| User manipulating callback data to trigger protection they didn't pay for | Tampering | Callback data is serialized by aiogram -- harder to forge. But always re-verify balance + session state server-side before applying protection. |
| Race condition: user buys protection while timeout fires | Tampering / DoS | Use `SELECT FOR UPDATE` on session row (already pattern in BesitoService). Protection purchase checks `expires_at` under lock. |
| Cross-user session manipulation (user A triggers B's retire) | Spoofing | Every handler verifies `callback.from_user.id == session.user_id` before any state mutation. |
| Besito debit without protection application | Repudiation | Atomic transaction: debit `commit=False`, update session, single `db.commit()`. |
| Expired session codes being used by admin | Information Disclosure | `CANCELLED` state prevents admin from accidentally using cancelled codes. Filter CANCELLED out of admin code display. |

## Sources

### Primary (HIGH confidence)
- `models/models.py:1130-1223` -- Verifie: StreakPromotionCodeStatus, StreakPromotionCode, StreakPromotionRedemption [VERIFIED: codebase read]
- `services/streak_promotion_service.py:1-290` -- Verifie: claim_for_streak (L192-222), get_active_promotions, _pre_generate_codes [VERIFIED: codebase read]
- `services/game_service.py:692-814, 987-1107, 1299-1410` -- Verifie: play_trivia/play_trivia_vip/play_trivia_simple integration with claim_for_streak [VERIFIED: codebase read]
- `services/besito_service.py:131-189` -- Verifie: debit_besitos with commit=False, has_sufficient_balance [VERIFIED: codebase read]
- `models/CLAUDE.md` -- Verifie: Enum-First migration pattern, alembic chain [VERIFIED: codebase read]
- `alembic/versions/36c345796281_add_streak_promotions_tables.py` -- Verifie: Current migration structure and naming conventions [VERIFIED: codebase read]
- `handlers/game_user_handlers.py:1-345` -- Verifie: Current trivia handlers, no FSM, callback_data pattern [VERIFIED: codebase read]
- `models/models.py:167-176` -- Verifie: TransactionSource enum values [VERIFIED: codebase read]
- `models/models.py:679-683` -- Verifie: CANCELLED naming convention (OrderStatus) [VERIFIED: codebase read]

### Secondary (MEDIUM confidence)
- `handlers/CLAUDE.md` -- Handler rules: 1 service, no DB, no logic [VERIFIED: codebase read]
- `keyboards/callback_data.py:602-615` -- TriviaAnswerCallback pattern [VERIFIED: codebase read]
- `keyboards/inline_keyboards.py:475-535` -- Trivia keyboard patterns [VERIFIED: codebase read]
- `services/scheduler_service.py:311-394` -- Scheduler job patterns (IntervalTrigger, DateTrigger) [VERIFIED: codebase read]

### Tertiary (LOW confidence)
- `resp_trivia_multiniveles` reference branch diffs -- FSM state patterns (TriviaStreakStates) [VERIFIED: git diff main...resp_trivia_multiniveles]
- Reference branch issues: get_all_promotions broken, handler callbacks broken, max_codes validation [CITED: CONTEXT.md]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all dependencies verified via codebase reads and Bash checks
- Architecture: HIGH -- current handler/service/model patterns verified; FSM integration points identified
- Pitfalls: HIGH -- reference branch studied; conventions verified across multiple files; SQLAlchemy JSON mutation trap documented
- Reference branch: MEDIUM -- exact bugs in get_all_promotions not reproducible (old model structure); FSM patterns verified

**Research date:** 2026-05-23
**Valid until:** 2026-06-22 (30 days -- stable domain, no external API changes)
