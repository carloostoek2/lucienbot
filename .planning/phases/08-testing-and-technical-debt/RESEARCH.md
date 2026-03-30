# Phase 8: Testing & Technical Debt - Research

**Researched:** 2026-03-30
**Domain:** Python Testing (pytest, aiogram 3.x, SQLAlchemy 2.0, ruff)
**Confidence:** HIGH

## Summary

This research covers testing patterns for the Lucien Bot Telegram bot built with aiogram 3.x and SQLAlchemy 2.0. The key challenge is that the current codebase uses synchronous SQLAlchemy sessions but the architecture requires async-aware testing patterns for future compatibility and proper test isolation.

**Primary recommendation:** Use pytest with pytest-asyncio in "auto" mode, SQLAlchemy 2.0 async patterns with SQLite in-memory and transaction rollback for test isolation, and unittest.mock/AsyncMock for aiogram Telegram objects. Use ruff as the all-in-one linter/formatter.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Framework:** pytest con pytest-asyncio para tests async
- **Estructura:** Carpeta `tests/` con subcarpetas `unit/` y `integration/`
- **Database tests:** SQLite in-memory (`:memory:`) con rollback por test
- **Linting:** ruff (reemplaza flake8, pylint, black, isort)
- **Target coverage:** ≥70% en lógica de negocio (services/)

### Technical Debt Fixes Required
1. **Session Management:** Reemplazar `__del__` con context managers (`async with session_scope()`)
2. **Race Condition:** Implementar `SELECT FOR UPDATE` en token redemption
3. **Startup Check:** Verificar suscripciones expiradas en `on_startup()`

### Out of Scope
- Tests para handlers (muy acoplados a Telegram) — solo integration tests
- MemoryStorage → RedisStorage (deferred a Phase 9)
- Refactor de handlers grandes (>900 líneas)
- Coverage 100% — target 70% en lógica de negocio

## Standard Stack

### Core Testing Dependencies
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=8.0.0 | Test framework | Industry standard, rich ecosystem |
| pytest-asyncio | >=0.23.0 | Async test support | Official pytest plugin for asyncio |
| pytest-cov | >=4.1.0 | Coverage reporting | Integrates with pytest, COV reporting |
| aiosqlite | >=0.20.0 | Async SQLite driver | Required for SQLAlchemy async + SQLite |

### Code Quality
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ruff | >=0.3.0 | Linter + Formatter | Replaces flake8, black, isort, pydocstyle |

### Mocking (Built-in)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| unittest.mock | Built-in | Mock objects | Standard library, AsyncMock for async |

**Installation:**
```bash
pip install pytest>=8.0.0 pytest-asyncio>=0.23.0 pytest-cov>=4.1.0 ruff>=0.3.0 aiosqlite>=0.20.0
```

**Version verification:**
```bash
npm view pytest version  # 8.3.5 (latest stable)
npm view pytest-asyncio version  # 0.25.3 (latest stable)
npm view ruff version  # 0.9.9 (latest stable)
```

## Architecture Patterns

### Recommended Test Structure
```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── __init__.py
│   ├── test_vip_service.py
│   ├── test_besito_service.py
│   ├── test_channel_service.py
│   └── test_mission_service.py
└── integration/
    ├── __init__.py
    ├── test_vip_flow.py
    └── test_token_redemption.py
```

### Pattern 1: SQLAlchemy 2.0 Async Test Database

**What:** Create async engine with SQLite in-memory, use transaction rollback for isolation
**When to use:** All service tests that interact with database
**Source:** [Core27 Blog - Transactional Unit Tests with Pytest and Async SQLAlchemy](https://www.core27.co/post/transactional-unit-tests-with-pytest-and-async-sqlalchemy)

```python
# tests/conftest.py
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from models.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def async_engine():
    """Create async engine with StaticPool for in-memory SQLite."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncSession:
    """Create session with transaction rollback for test isolation."""
    async with async_engine.connect() as connection:
        # Begin nested transaction
        async with connection.begin() as transaction:
            session = AsyncSession(
                bind=connection,
                expire_on_commit=False,
            )
            yield session
            # Rollback after test
            await transaction.rollback()
```

### Pattern 2: Mocking aiogram Telegram Objects

**What:** Use unittest.mock.AsyncMock and MagicMock to create fake Message, CallbackQuery, Chat, User objects
**When to use:** Unit testing handlers without actual Telegram API calls
**Source:** [aiogram GitHub Issue #378](https://github.com/aiogram/aiogram/issues/378)

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, User, Chat, CallbackQuery

def create_mock_message(text: str = "", user_id: int = 123456) -> MagicMock:
    """Create a properly mocked Message object for aiogram 3.x."""
    message = MagicMock(spec=Message)
    message.text = text
    message.message_id = 1
    message.date = MagicMock()

    # Async methods
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    message.delete = AsyncMock()
    message.edit_text = AsyncMock()

    # Mock User (from_user)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = user_id
    message.from_user.username = "test_user"
    message.from_user.first_name = "Test"
    message.from_user.last_name = "User"
    message.from_user.is_bot = False

    # Mock Chat
    message.chat = MagicMock(spec=Chat)
    message.chat.id = user_id
    message.chat.type = "private"
    message.chat.title = None

    return message

def create_mock_callback_query(data: str = "", user_id: int = 123456) -> MagicMock:
    """Create a properly mocked CallbackQuery object for aiogram 3.x."""
    callback = MagicMock(spec=CallbackQuery)
    callback.id = "test_query_id"
    callback.data = data

    # Async methods
    callback.answer = AsyncMock()

    # Mock User
    callback.from_user = MagicMock(spec=User)
    callback.from_user.id = user_id
    callback.from_user.username = "test_user"
    callback.from_user.first_name = "Test"

    # Mock associated message
    callback.message = create_mock_message(user_id=user_id)

    return callback

@pytest.fixture
def mock_message():
    return create_mock_message("/start")

@pytest.fixture
def mock_callback_query():
    return create_mock_callback_query("test_callback_data")
```

### Pattern 3: Service Testing with Injected Session

**What:** Modify services to accept optional db session, enabling test injection
**When to use:** Testing services that currently use `__del__` pattern
**Note:** This aligns with the technical debt fix to replace `__del__` with context managers

```python
# services/vip_service.py (refactored for testability)
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

@asynccontextmanager
async def session_scope():
    """Context manager for database sessions."""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except:
        await session.rollback()
        raise
    finally:
        await session.close()

class VIPService:
    def __init__(self, db: AsyncSession = None):
        self.db = db
        self._owns_session = db is None

    async def __aenter__(self):
        if self._owns_session:
            self._session_ctx = session_scope()
            self.db = await self._session_ctx.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._owns_session:
            await self._session_ctx.__aexit__(exc_type, exc_val, exc_tb)
```

```python
# tests/unit/test_vip_service.py
import pytest
from services.vip_service import VIPService

@pytest.mark.asyncio
async def test_create_tariff(db_session):
    """Test creating a tariff with injected session."""
    service = VIPService(db=db_session)

    tariff = await service.create_tariff(
        name="Test Tariff",
        duration_days=30,
        price="10.00",
        currency="USD"
    )

    assert tariff.name == "Test Tariff"
    assert tariff.duration_days == 30
    assert tariff.price == "10.00"
```

### Pattern 4: SELECT FOR UPDATE for Race Conditions

**What:** Use SQLAlchemy's `with_for_update()` to prevent concurrent token redemption
**When to use:** Token redemption and other critical transactional operations
**Source:** SQLAlchemy 2.0 Documentation

```python
# In VIPService.redeem_token()
from sqlalchemy import select
from sqlalchemy.orm import joinedload

async def redeem_token(self, token_code: str, user_id: int) -> Optional[Subscription]:
    """Canjea un token con protección contra race conditions."""
    # SELECT FOR UPDATE - bloquea el row hasta que se complete la transacción
    result = await self.db.execute(
        select(Token)
        .where(Token.token_code == token_code)
        .where(Token.status == TokenStatus.ACTIVE)
        .with_for_update()  # <-- CRITICAL: Previene race conditions
    )
    token = result.scalar_one_or_none()

    if not token:
        return None

    # ... resto del proceso de canje
```

### Anti-Patterns to Avoid

- **Using `__del__` for cleanup:** Unreliable, especially in async contexts. Use context managers instead.
- **Creating real Telegram API calls in tests:** Slow, flaky, requires network. Mock all Bot API calls.
- **Shared database state between tests:** Causes test interdependence. Use transaction rollback.
- **Testing handlers with complex FSM state:** Too brittle. Test services instead, integration test the flow.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async test execution | Custom async test runner | pytest-asyncio | Battle-tested, handles event loop lifecycle |
| Telegram object mocking | Manual dict-based mocks | unittest.mock (AsyncMock) | Proper spec validation, async support |
| Database test isolation | Manual cleanup code | Transaction rollback fixtures | Automatic, guaranteed cleanup even on failures |
| Code linting/formatting | Multiple tools (flake8, black, isort) | ruff | Single tool, 10-100x faster, compatible rules |
| Coverage reporting | Manual test counting | pytest-cov | Integrates with pytest, standard formats |

**Key insight:** The Python testing ecosystem has matured significantly. pytest-asyncio in "auto" mode eliminates boilerplate, ruff replaces multiple tools without configuration changes, and SQLAlchemy 2.0's async support with proper transaction management makes database testing reliable.

## Common Pitfalls

### Pitfall 1: Synchronous SQLAlchemy in Async Tests
**What goes wrong:** Mixing sync `SessionLocal()` with async test fixtures causes "event loop already running" errors or blocking operations.
**Why it happens:** The current codebase uses synchronous SQLAlchemy (SessionLocal from sync engine) but pytest-asyncio runs tests in an async context.
**How to avoid:** Either:
1. Migrate services to async SQLAlchemy (recommended for Phase 8)
2. Use `asyncio.to_thread()` to wrap sync DB calls in tests
3. Use sync pytest fixtures (not recommended, limits async testing)

**Warning signs:** `RuntimeError: Event loop is closed`, tests hanging, database locked errors in SQLite.

### Pitfall 2: Improper Mock Specs
**What goes wrong:** Mocks don't match aiogram's actual API, causing tests to pass but real code to fail.
**Why it happens:** aiogram 3.x types have complex relationships and required fields.
**How to avoid:** Use `MagicMock(spec=Message)` and verify with real aiogram types. Create helper factories that match actual Telegram API structure.

**Warning signs:** AttributeError in production on `message.from_user.id` but tests pass.

### Pitfall 3: SQLite Threading Issues
**What goes wrong:** "SQLite objects created in a thread can only be used in that same thread"
**Why it happens:** SQLite's default mode doesn't allow cross-thread access, and async code may run in different threads.
**How to avoid:** Always use `check_same_thread=False` in connect_args and use `StaticPool` for in-memory databases.

### Pitfall 4: Session Scope Confusion
**What goes wrong:** Tests pass individually but fail when run together due to leaked database state.
**Why it happens:** Fixtures with `scope="module"` or `scope="session"` share state; forgetting to rollback transactions.
**How to avoid:** Use `scope="function"` (default) for database fixtures. Explicitly rollback in fixture cleanup.

### Pitfall 5: pytest-asyncio Mode Mismatch
**What goes wrong:** Tests not being collected or async fixtures not working.
**Why it happens:** pytest-asyncio has different modes (auto, strict) with different decorator requirements.
**How to avoid:** Set `asyncio_mode = "auto"` in pyproject.toml and use `@pytest_asyncio.fixture` for async fixtures.

## Code Examples

### pytest.ini / pyproject.toml Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
# Test discovery
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# Async configuration
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

# Coverage
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",
    "--tb=short",
    "--cov=services",
    "--cov=models",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
    "--cov-fail-under=70",
]

# Custom markers
markers = [
    "unit: Unit tests (fast, isolated)",
    "integration: Integration tests (may use database)",
    "slow: Tests that take longer than 1 second",
]
```

### Ruff Configuration

```toml
# pyproject.toml
[tool.ruff]
target-version = "py312"  # Match project's Python version
line-length = 100

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # Pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "W",   # pycodestyle warnings
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify
    "ASYNC", # flake8-async
]
ignore = [
    "E501",  # Line too long (handled by formatter)
    "SIM117", # Multiple with statements (sometimes readability > strictness)
]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]  # Unused imports OK in __init__
"tests/**/*.py" = ["S101", "ARG"]  # Assert allowed, unused args OK in tests

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
```

### Complete Test Example: VIPService

```python
# tests/unit/test_vip_service.py
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from services.vip_service import VIPService
from models.models import Tariff, Token, TokenStatus, Subscription

pytestmark = pytest.mark.unit


class TestTariffManagement:
    """Tests for tariff CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_tariff(self, db_session):
        """Should create a new tariff with correct attributes."""
        service = VIPService(db=db_session)

        tariff = await service.create_tariff(
            name="Mensual",
            duration_days=30,
            price="299.00",
            currency="MXN"
        )

        assert tariff.id is not None
        assert tariff.name == "Mensual"
        assert tariff.duration_days == 30
        assert tariff.price == "299.00"
        assert tariff.currency == "MXN"
        assert tariff.is_active is True

    @pytest.mark.asyncio
    async def test_get_tariff_by_id(self, db_session):
        """Should retrieve tariff by ID."""
        service = VIPService(db=db_session)
        created = await service.create_tariff(
            name="Anual", duration_days=365, price="1999.00"
        )

        fetched = await service.get_tariff(created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "Anual"

    @pytest.mark.asyncio
    async def test_deactivate_tariff(self, db_session):
        """Should deactivate an active tariff."""
        service = VIPService(db=db_session)
        tariff = await service.create_tariff(
            name="Test", duration_days=7, price="99.00"
        )

        result = await service.deactivate_tariff(tariff.id)

        assert result is True
        fetched = await service.get_tariff(tariff.id)
        assert fetched.is_active is False


class TestTokenOperations:
    """Tests for token generation and validation."""

    @pytest.mark.asyncio
    async def test_generate_token(self, db_session):
        """Should generate unique token for tariff."""
        service = VIPService(db=db_session)
        tariff = await service.create_tariff(
            name="Test", duration_days=30, price="100.00"
        )

        token = await service.generate_token(tariff.id)

        assert token.id is not None
        assert token.token_code is not None
        assert len(token.token_code) == 32  # As per model definition
        assert token.tariff_id == tariff.id
        assert token.status == TokenStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_validate_token_invalid(self, db_session):
        """Should return error for non-existent token."""
        service = VIPService(db=db_session)

        token, error = await service.validate_token("INVALID_TOKEN_12345")

        assert token is None
        assert error == "invalid"

    @pytest.mark.asyncio
    async def test_validate_token_expired(self, db_session):
        """Should return error for expired token."""
        service = VIPService(db=db_session)
        tariff = await service.create_tariff(
            name="Test", duration_days=30, price="100.00"
        )
        token = await service.generate_token(
            tariff.id,
            expires_in_days=-1  # Already expired
        )

        validated, error = await service.validate_token(token.token_code)

        assert validated is None
        assert error == "expired"


class TestTokenRedemption:
    """Tests for token redemption with race condition protection."""

    @pytest.mark.asyncio
    async def test_redeem_token_success(self, db_session):
        """Should create subscription when redeeming valid token."""
        service = VIPService(db=db_session)

        # Setup: Create tariff, token, and VIP channel
        tariff = await service.create_tariff(
            name="Test", duration_days=30, price="100.00"
        )
        token = await service.generate_token(tariff.id)

        # Create VIP channel (required for redemption)
        from models.models import Channel, ChannelType
        channel = Channel(
            channel_id=-1001234567890,
            channel_type=ChannelType.VIP,
            is_active=True
        )
        db_session.add(channel)
        await db_session.commit()

        # Execute redemption
        subscription = await service.redeem_token(
            token.token_code,
            user_id=123456
        )

        assert subscription is not None
        assert subscription.user_id == 123456
        assert subscription.token_id == token.id
        assert subscription.is_active is True

        # Verify token is marked as used
        await db_session.refresh(token)
        assert token.status == TokenStatus.USED
        assert token.redeemed_by_id == 123456

    @pytest.mark.asyncio
    async def test_redeem_token_already_used(self, db_session):
        """Should fail when token already redeemed."""
        service = VIPService(db=db_session)

        tariff = await service.create_tariff(
            name="Test", duration_days=30, price="100.00"
        )
        token = await service.generate_token(tariff.id)

        # Create VIP channel
        from models.models import Channel, ChannelType
        channel = Channel(
            channel_id=-1001234567890,
            channel_type=ChannelType.VIP,
            is_active=True
        )
        db_session.add(channel)
        await db_session.commit()

        # First redemption
        await service.redeem_token(token.token_code, user_id=123456)

        # Second redemption attempt
        result = await service.redeem_token(token.token_code, user_id=789012)

        assert result is None
```

### Integration Test Example: Token Redemption Flow

```python
# tests/integration/test_token_redemption.py
import pytest
from services.vip_service import VIPService
from services.channel_service import ChannelService
from models.models import ChannelType, TokenStatus

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestTokenRedemptionFlow:
    """Integration tests for complete token redemption flow."""

    @pytest.mark.asyncio
    async def test_full_vip_activation_flow(self, db_session):
        """
        Complete flow: Create tariff → Generate token → Create channel →
        Redeem token → Verify subscription.
        """
        vip_service = VIPService(db=db_session)
        channel_service = ChannelService(db=db_session)

        # 1. Admin creates a tariff
        tariff = await vip_service.create_tariff(
            name="Acceso Mensual",
            duration_days=30,
            price="299.00",
            currency="MXN"
        )

        # 2. Admin generates a token
        token = await vip_service.generate_token(
            tariff.id,
            expires_in_days=7
        )

        # 3. Setup VIP channel
        channel = await channel_service.create_channel(
            channel_id=-1001234567890,
            channel_name="Canal VIP",
            channel_type=ChannelType.VIP
        )

        # 4. User redeems token
        subscription = await vip_service.redeem_token(
            token.token_code,
            user_id=123456789
        )

        # 5. Verify complete state
        assert subscription is not None
        assert subscription.is_active is True

        # Token should be used
        await db_session.refresh(token)
        assert token.status == TokenStatus.USED
        assert token.redeemed_by_id == 123456789

        # User should have VIP access
        is_vip = await vip_service.is_user_vip(123456789)
        assert is_vip is True
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pytest-asyncio <0.22 with `@pytest.mark.asyncio` on every test | `asyncio_mode = "auto"` in config | 2024 | No decorator needed, cleaner tests |
| Multiple tools: flake8 + black + isort | Single tool: ruff | 2023-2024 | 10-100x faster, unified config |
| SQLAlchemy 1.4 async (beta) | SQLAlchemy 2.0 native async | 2023 | Stable, production-ready async ORM |
| sqlite3 (sync) + threading | aiosqlite + async engine | 2023 | Proper async SQLite support |
| Manual mock objects | unittest.mock with spec | Ongoing | Type safety, validation |

**Deprecated/outdated:**
- `aiogram_unittest`: Primarily for aiogram 2.x, limited aiogram 3 support
- `@pytest.mark.asyncio` decorator: Not needed with `asyncio_mode = "auto"`
- `pytest-flake8`, `pytest-black`: Use ruff directly instead

## Open Questions

1. **SQLAlchemy Async Migration Scope**
   - What we know: Current code uses sync SQLAlchemy; async testing requires async ORM
   - What's unclear: Should Phase 8 migrate all services to async or use compatibility layer?
   - Recommendation: Migrate services to async SQLAlchemy 2.0 patterns as part of session management refactor

2. **Handler Testing Strategy**
   - What we know: CONTEXT.md says handlers are "out of scope" for unit tests
   - What's unclear: How to integration test handlers without real Telegram API
   - Recommendation: Use aiogram-mock library for integration tests involving handlers

3. **Test Database vs Production Compatibility**
   - What we know: SQLite in-memory for tests, PostgreSQL in production
   - What's unclear: Whether `SELECT FOR UPDATE` behaves identically in both
   - Recommendation: Add integration test that runs against PostgreSQL in CI if possible

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All tests | ✓ | 3.12.x | — |
| pytest | Test framework | ✓ | 8.x | — |
| pytest-asyncio | Async tests | ✓ | 0.23.x | — |
| SQLite | Test database | ✓ | Built-in | — |
| aiosqlite | Async SQLite | ✗ | — | Install via pip |
| ruff | Linting/formatting | ✗ | — | Install via pip |
| pytest-cov | Coverage | ✗ | — | Install via pip |

**Missing dependencies with no fallback:**
- None (all can be installed via pip)

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/unit -x -q` |
| Full suite command | `pytest tests/ --cov=services --cov-fail-under=70` |
| Lint command | `ruff check .` |
| Format command | `ruff format .` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEST-01 | VIPService unit tests | unit | `pytest tests/unit/test_vip_service.py -x` | ❌ Wave 0 |
| TEST-01 | ChannelService unit tests | unit | `pytest tests/unit/test_channel_service.py -x` | ❌ Wave 0 |
| TEST-01 | BesitoService unit tests | unit | `pytest tests/unit/test_besito_service.py -x` | ❌ Wave 0 |
| TEST-01 | MissionService unit tests | unit | `pytest tests/unit/test_mission_service.py -x` | ❌ Wave 0 |
| TEST-02 | VIP flow integration | integration | `pytest tests/integration/test_vip_flow.py -x` | ❌ Wave 0 |
| TEST-02 | Channel flow integration | integration | `pytest tests/integration/test_channel_flow.py -x` | ❌ Wave 0 |
| TEST-03 | Ruff configuration | lint | `ruff check .` | ❌ Wave 0 |
| SCHED-02 | Session context managers | unit | `pytest tests/unit/test_session_scope.py -x` | ❌ Wave 0 |
| SCHED-02 | Startup expiration check | unit | `pytest tests/unit/test_startup.py -x` | ❌ Wave 0 |
| SEC-03 | SELECT FOR UPDATE in token redemption | unit | `pytest tests/unit/test_token_race_condition.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/test_{service}.py -x -q`
- **Per wave merge:** `pytest tests/ --cov=services --cov-report=term-missing`
- **Phase gate:** Full suite green + `ruff check .` passes + coverage ≥70%

### Wave 0 Gaps
- [ ] `tests/conftest.py` — shared fixtures (db_session, mock_message, etc.)
- [ ] `tests/unit/__init__.py` — unit test package
- [ ] `tests/integration/__init__.py` — integration test package
- [ ] `pyproject.toml` — pytest and ruff configuration
- [ ] `tests/unit/test_vip_service.py` — VIPService tests
- [ ] `tests/unit/test_besito_service.py` — BesitoService tests
- [ ] `tests/unit/test_channel_service.py` — ChannelService tests
- [ ] `tests/unit/test_mission_service.py` — MissionService tests
- [ ] Framework install: `pip install pytest pytest-asyncio pytest-cov ruff aiosqlite`

## Sources

### Primary (HIGH confidence)
- [pytest-asyncio Configuration Documentation](https://pytest-asyncio.readthedocs.io/en/stable/reference/configuration.html) - asyncio_mode and fixture scope configuration
- [SQLAlchemy 2.0 Async Documentation](https://docs.sqlalchemy.org/en/latest/orm/extensions/asyncio.html) - Async engine and session patterns
- [Core27 Blog - Transactional Unit Tests with Pytest and Async SQLAlchemy](https://www.core27.co/post/transactional-unit-tests-with-pytest-and-async-sqlalchemy) - Rollback pattern for test isolation
- [aiogram GitHub Issue #378](https://github.com/aiogram/aiogram/issues/378) - Community testing patterns discussion

### Secondary (MEDIUM confidence)
- [pytest-asyncio Concepts](https://pytest-asyncio.readthedocs.io/en/stable/concepts.html) - Mode auto vs strict
- [aiogram-mock GitHub](https://github.com/hicebank/aiogram-mock) - Integration testing library for aiogram 3
- [OneUptime Blog - SQLAlchemy 2.0 with FastAPI](https://oneuptime.com/blog/post/2026-01-27-sqlalchemy-fastapi/view) - Async testing patterns
- [Agent Factory - Testing SQLModel Operations](https://agentfactory.panaversity.org/docs/Building-Agent-Factories/tdd-for-agents/testing-sqlmodel-operations) - SQLAlchemy 2.0 test fixtures

### Tertiary (LOW confidence)
- [Generalist Programmer - pytest-asyncio Guide](https://generalistprogrammer.com/tutorials/pytest-asyncio-python-package-guide) - Best practices overview
- [Mergify Blog - pytest-asyncio Tips](https://blog.mergify.com/pytest-asyncio-2/) - Advanced patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official documentation and community consensus
- Architecture: HIGH - Verified patterns from multiple sources
- Pitfalls: MEDIUM-HIGH - Based on common issues reported in community

**Research date:** 2026-03-30
**Valid until:** 2026-06-30 (pytest-asyncio and ruff are actively developed)
