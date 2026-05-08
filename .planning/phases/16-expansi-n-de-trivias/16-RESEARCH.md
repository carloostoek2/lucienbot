# Phase 16: Expansión de Trivias - Research

**Researched:** 2026-05-08
**Domain:** Trivia Question Management (CRUD operations, categorization, admin interface)
**Confidence:** HIGH

## Summary

Phase 16 implements administrative management of trivia questions for Lucien Bot. Currently, trivia questions are stored in a static JSON file (`docs/preguntas.json`) with 675+ questions across general knowledge categories. A parallel worktree (`trivia-timeout`) has already implemented a `QuestionSet` model and service pattern for themed question sets stored in the database, but the main codebase still lacks full CRUD operations for individual questions. This research identifies what exists, what's missing, and recommends a path forward for Custodios to manage trivia questions directly.

**Primary recommendation:** Adopt the `QuestionSet` pattern from the `trivia-timeout` worktree for database-backed question storage, create a `TriviaQuestion` model with category and difficulty fields, implement a `TriviaQuestionService` with full CRUD, and build an admin management interface following the existing wizard patterns (e.g., `store_admin_handlers.py` product wizard).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Question storage | Database | — | `QuestionSet` model stores file_path reference; actual questions in JSON |
| Question loading | API/Backend | — | `GameService.load_trivia_questions()` reads JSON file at runtime |
| Admin management UI | API/Backend | — | Handlers route events, Services contain business logic |
| Question CRUD | API/Backend | — | Service layer creates/reads/updates/deletes via ORM |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiogram 3.x | 3.4+ | Telegram bot framework | Project uses aiogram for all handlers |
| SQLAlchemy | 2.x | ORM for database models | Same as existing models.py |
| Alembic | — | Database migrations | Existing migration infrastructure |

### Existing Patterns (to leverage)
| Pattern | Source | Usage |
|---------|--------|-------|
| Wizard FSM pattern | `store_admin_handlers.py` ProductWizard | Multi-step question creation |
| Service-with-service | `daily_gift_service.py` | Embed BesitoService for related features |
| Config singleton pattern | `TriviaConfigService` (worktree) | Single-row config for settings |
| QuestionSet pattern | `question_set_service.py` (worktree) | Themed question group management |

**Installation:**
```bash
# No new packages needed - all existing
```

## Architecture Patterns

### Recommended Project Structure
```
services/
├── trivia_question_service.py  # NEW - CRUD for individual questions
models/
├── models.py                   # MODIFY - add TriviaQuestion model
handlers/
├── trivia_question_admin_handlers.py  # NEW - admin management UI
keyboards/
├── inline_keyboards.py          # MODIFY - add trivia admin keyboards
```

### Pattern 1: QuestionSet Service (Reference: trivia-timeout worktree)
```python
# services/question_set_service.py - database-backed question groups
class QuestionSetService:
    def get_all_sets(self) -> list[QuestionSet]:
        with SessionLocal() as session:
            return session.query(QuestionSet).order_by(...).all()

    def create_set(self, name: str, file_path: str, description: Optional[str]) -> Optional[QuestionSet]:
        # Creates a reference to a JSON file containing questions
```

**When to use:** Custodio creates a themed set by providing path to JSON file.

### Pattern 2: Wizard FSM for Multi-step Creation (Reference: store_admin_handlers.py)
```python
class ProductWizardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_price = State()
    # ...

async def create_product_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await message.answer("Next question...")
    await state.set_state(ProductWizardStates.waiting_description)
```

**When to use:** Multi-step question creation with validation at each step.

### Pattern 3: Inline Editing with Confirmation (Reference: category_admin_handlers.py)
```python
@router.callback_query(F.data.startswith("edit_category_"))
async def edit_category(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.replace("edit_category_", ""))
    # Show current values with edit buttons
    # On edit, set FSM state and prompt for new value
```

**When to use:** When editing existing questions, show current value and allow partial edits.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Question storage | JSON file editing by hand | Database with `TriviaQuestion` model | Easier admin UI, relationships to categories |
| Configuration | Hardcoded constants | `TriviaConfig` singleton model | Allows runtime changes without code deploy |
| Admin interface | Custom parsing | aiogram FSM with wizard pattern | Existing patterns are well-tested |
| Question loading | Custom file readers | JSON in DB or referenced JSON files | Consistency with QuestionSet approach |

**Key insight:** The trivia-timeout worktree has already solved the database storage problem with `QuestionSet`. The main codebase should adopt this pattern rather than inventing a new one.

## Common Pitfalls

### Pitfall 1: Questions Loaded at Runtime from Static File
**What goes wrong:** Changes to questions require bot restart; no admin UI possible
**Why it happens:** `GameService.load_trivia_questions()` reads `docs/preguntas.json` once and caches
**How to avoid:** Move questions to database with `TriviaQuestion` model, implement cache invalidation
**Warning signs:** "I edited the JSON but the bot still asks the old question"

### Pitfall 2: No Category/Difficulty Metadata
**What goes wrong:** All questions treated equally; can't filter by topic or difficulty
**Why it happens:** JSON format is flat: `{"q": "...", "opts": [...], "answer": N}`
**How to avoid:** Add `category` and `difficulty` fields to `TriviaQuestion` model
**Warning signs:** "How do I add only easy questions to the VIP trivia?"

### Pitfall 3: Question IDs Not Stable Across Edits
**What goes wrong:** Deleting a question shifts indices, breaking streak tracking
**Why it happens:** Questions identified by array index in JSON
**How to avoid:** Use auto-increment primary key IDs, never expose raw array indices
**Warning signs:** "User's streak reset because I deleted a question"

### Pitfall 4: Admin Handler Doing Business Logic
**What goes wrong:** Violates architecture rules, hard to test
**Why it happens:** Trying to do too much in handler callbacks
**How to avoid:** Handlers only call services, services do all ORM operations
**Warning signs:** Handler imports models directly

## Code Examples

### Current Question Format (docs/preguntas.json)
```json
[
  { "q": "¿Cuál es la capital de Francia?", "opts": ["Madrid", "París", "Roma"], "answer": 1 }
]
```
**Format:** 3 options, `answer` is index of correct option (0=A, 1=B, 2=C)

### Themed Question Set Format (docs/question_sets/primero_de_mayo.json)
```json
[
  {
    "q": "¿En qué fecha se celebra el Día Internacional del Trabajo...?",
    "opts": ["1 de Mayo", "1 de Abril", "1 de Junio", "5 de Mayo"],
    "answer": 0
  }
]
```
**Format:** Same as general questions, but stored in themed files.

### QuestionSet Model (trivia-timeout worktree - verified)
```python
class QuestionSet(Base):
    """Sets temáticos de preguntas de trivia"""
    __tablename__ = "question_sets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    file_path = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)
    is_override = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### TriviaConfig Singleton (trivia-timeout worktree - verified)
```python
class TriviaConfig(Base):
    """Configuración de límites de intentos de trivia"""
    __tablename__ = "trivia_config"

    id = Column(Integer, primary_key=True)
    daily_trivia_limit_free = Column(Integer, default=7, nullable=False)
    daily_trivia_limit_vip = Column(Integer, default=15, nullable=False)
    daily_trivia_vip_limit = Column(Integer, default=5, nullable=False)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(BigInteger, nullable=True)
```

### Admin Handler with Wizard FSM (reference: store_admin_handlers.py)
```python
class ProductWizardStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    selecting_package = State()
    waiting_price = State()
    waiting_stock = State()
    confirming = State()

@router.callback_query(F.data == "create_product", lambda cb: is_admin(cb.from_user.id))
async def create_product_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Nombre del producto:", ...)
    await state.set_state(ProductWizardStates.waiting_name)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static JSON file for questions | Database with `QuestionSet` references | trivia-timeout worktree | Enables runtime admin management |
| No question categorization | `category` field on QuestionSet | This phase | Enables filtering and themed trivias |
| Hardcoded trivia limits | `TriviaConfig` singleton in DB | trivia-timeout worktree | Runtime configurable limits |

**Deprecated/outdated:**
- None relevant to this phase

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The trivia-timeout worktree's models are compatible with main branch | Standard Stack | May need migration adaptation |

## Open Questions

1. **Should individual questions be stored in DB or referenced JSON files?**
   - What we know: `QuestionSet` stores `file_path` reference, loads questions from JSON at play time
   - What's unclear: Whether to migrate all questions to `TriviaQuestion` rows in DB
   - Recommendation: Start with referenced JSON files (QuestionSet pattern), migrate to DB rows later if admin UI needs it

2. **Should question editing support inline edits or require full replacement?**
   - What we know: Current JSON format is flat with no ID field
   - What's unclear: Whether Custodios prefer inline Telegram editing vs. uploading new JSON
   - Recommendation: Support both — inline edit individual questions AND bulk JSON upload

3. **Should categories be free-form strings or enum/relationship?**
   - What we know: Questions span topics: geography, video games, anime, science, culture
   - What's unclear: Whether to create `TriviaCategory` model or use string tags
   - Recommendation: Use string tags initially, create model if categorization grows complex

## Environment Availability

Step 2.6: SKIPPED (no external dependencies - all project code/config)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pytest.ini |
| Quick run command | `pytest tests/unit/ -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRIVIA-ADMIN-01 | Create question via wizard | unit | `pytest tests/unit/test_trivia_question_service.py::test_create_question -x` | NO |
| TRIVIA-ADMIN-02 | Edit existing question | unit | `pytest tests/unit/test_trivia_question_service.py::test_update_question -x` | NO |
| TRIVIA-ADMIN-03 | Delete question | unit | `pytest tests/unit/test_trivia_question_service.py::test_delete_question -x` | NO |
| TRIVIA-ADMIN-04 | List questions by category | unit | `pytest tests/unit/test_trivia_question_service.py::test_list_by_category -x` | NO |
| TRIVIA-ADMIN-05 | Admin menu navigation | integration | `pytest tests/integration/test_trivia_admin_handlers.py -x` | NO |

### Wave 0 Gaps
- [ ] `tests/unit/test_trivia_question_service.py` - covers TRIVIA-ADMIN-01 through 04
- [ ] `tests/integration/test_trivia_admin_handlers.py` - covers TRIVIA-ADMIN-05
- [ ] Framework install: pytest - already in requirements.txt

## Sources

### Primary (HIGH confidence)
- `services/game_service.py` - Current trivia loading from JSON, question format
- `docs/preguntas.json` - 675+ trivia questions with current format
- `docs/preguntas_vip.json` - VIP trivia questions with same format
- `.claude/worktrees/trivia-timeout/services/question_set_service.py` - QuestionSet service pattern
- `.claude/worktrees/trivia-timeout/handlers/question_set_admin_handlers.py` - Admin management pattern
- `.claude/worktrees/trivia-timeout/models/models.py` - QuestionSet, TriviaConfig models

### Secondary (MEDIUM confidence)
- `handlers/store_admin_handlers.py` - Wizard FSM pattern for admin creation flows
- `.planning/phases/14-minijuegos/14-RESEARCH.md` - Previous research on trivia baseline

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - using existing aiogram/SQLAlchemy, adopting proven worktree patterns
- Architecture: HIGH - follows existing patterns (wizard FSM, service-with-service, singleton config)
- Pitfalls: HIGH - clear what to avoid (handler business logic, static JSON limitations)

**Research date:** 2026-05-08
**Valid until:** 30 days (stable tech stack, active development on trivia system)
