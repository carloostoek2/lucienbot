---
name: lucien-bot-patterns
description: Coding patterns extracted from lucien_bot Telegram bot repository
version: 1.0.0
source: local-git-analysis
analyzed_commits: 200
---

# Lucien Bot Patterns

## Commit Conventions

This project uses **Conventional Commits** consistently:

- `feat(scope):` - New features (most common)
- `fix(scope):` - Bug fixes
- `docs(scope):` - Documentation and planning updates
- `test(scope):` - Test additions and updates
- `chore:` - Maintenance tasks, tooling, imports
- `refactor(scope):` - Code restructuring without behavior changes
- `todo:` - Capture pending work items

**Scope conventions:**
- Domain scopes: `(store)`, `(vip)`, `(game)`, `(trivia)`, `(admin)`, `(models)`, `(handlers)`
- Phase scopes: `(phase-14)`, `(12-04)`, `(09-01)` — tied to `.planning/phases/`
- Sub-scope format: `(phase-11-02)` for phase + task number

**Language:** Commit messages mix English and Spanish freely (Spanish for domain-specific features).

## Code Architecture

```
handlers/           # Telegram bot handlers
├── {domain}_user_handlers.py    # User-facing commands
├── {domain}_admin_handlers.py   # Admin/Custodio commands
├── {domain}_handlers.py         # Mixed or entry handlers
└── __init__.py      # Router registration + imports

services/           # Business logic
├── {domain}_service.py          # Top-level domain services
├── {domain}/                    # Nested domain services
│   └── {sub}_service.py
└── CLAUDE.md        # Domain-specific context

models/             # Data layer
├── models.py        # All SQLAlchemy entities
└── database.py      # Connection + session management

keyboards/          # UI layer
└── inline_keyboards.py
    └── {action}_keyboard() helpers

middlewares/        # Bot middleware
├── rate_limit_middleware.py
└── ...

utils/              # Shared utilities
└── lucien_voice.py  # Copy/voice helpers

tests/              # Test suite
├── unit/test_{service}.py
├── integration/test_{feature}.py
├── e2e/test_{feature}_e2e.py
└── conftest.py      # Pytest fixtures

alembic/versions/   # Database migrations
└── {YYYYMMDD}_{description}.py

.planning/          # GSD workflow artifacts
├── phases/{phase}/
├── STATE.md
├── ROADMAP.md
└── notes/
```

## Workflows

### Adding a New Domain Feature
Typical file touch sequence (from git co-change patterns):
1. `models/models.py` — add SQLAlchemy entities/enums
2. `alembic/versions/` — create migration
3. `services/{domain}_service.py` — implement business logic
4. `handlers/{domain}_*_handlers.py` — wire Telegram commands
5. `keyboards/inline_keyboards.py` — add UI keyboards
6. `handlers/__init__.py` + `bot.py` — register routers
7. `tests/unit/test_{domain}_service.py` — add coverage

### Database Migration Workflow
1. Modify `models/models.py`
2. Generate Alembic migration in `alembic/versions/`
3. Update enum values in migrations if adding new `TransactionSource`

### Menu/UI Changes
1. Update keyboard helper in `keyboards/inline_keyboards.py`
2. Update handler messages in relevant `handlers/*_handlers.py`
3. Register any new callbacks in `handlers/__init__.py` if needed

### Phase Completion Workflow
1. Execute code changes across handlers/services/models
2. Add/update tests
3. Write phase summary in `.planning/phases/{phase}/`
4. Update `.planning/STATE.md` and `.planning/ROADMAP.md`
5. Commit with `docs(phase-xx):` prefix

## Testing Patterns

- **Unit tests:** `tests/unit/test_{service_name}.py` — service logic, edge cases
- **Integration tests:** `tests/integration/test_{feature}.py` — handler + service flows
- **E2E tests:** `tests/e2e/test_{feature}_e2e.py` — full Telegram bot simulation
- **Fixtures:** `tests/conftest.py` for shared setup, mock bot, test database
- **Coverage:** `.coverage` tracked; commits often include coverage updates

## Naming Conventions

- **Services:** `{domain}_service.py` with class `{Domain}Service`
- **Handlers:** `{domain}_{role}_handlers.py` where role is `user`, `admin`, or omitted
- **Functions:** verb + context + result (e.g., `add_product_to_cart`, `complete_order_for_user`)
- **Keyboard builders:** `{purpose}_keyboard()` in `inline_keyboards.py`
- **Tests:** `test_{domain}_{scenario}.py` or `test_{domain}_service.py`
- **Migrations:** `{YYYYMMDD}_{description}.py`

## Critical Rules (from CLAUDE.md enforcement)

- **NO business logic in handlers** — handlers route to exactly 1 service call
- **NO database access outside `models/`**
- **NO duplication between services**
- Function max 50 lines
- Every significant action logs: module, action, user_id, result
- Admin checks via `is_admin()` before any custodio action
- Callback ID validation mandatory

## Language & Voice

- Python 3.12 + aiogram 3
- SQLAlchemy for ORM, Alembic for migrations
- APScheduler with SQLAlchemyJobStore
- Spanish copy in UI, English in code identifiers
- "Lucien" persona: 3rd person, elegant, "Visitantes" not "users", "Custodios" not "admins"
