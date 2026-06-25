<!-- generated-by: gsd-doc-writer -->
# Testing

## Test framework and setup

The project uses [pytest](https://pytest.org/) (>=8.2.0) as the testing framework. Supporting plugins from `requirements-dev.txt` enable async testing, coverage reporting, parallel execution, and time control:

- `pytest-asyncio>=0.23.0` — automatic async test support (`asyncio_mode = "auto"`).
- `pytest-cov>=5.0.0` — coverage collection and reporting.
- `pytest-xdist>=3.6.0` — parallel test runner (`-n auto`).
- `pytest-emoji>=0.2.0` — emoji output in reports.
- `freezegun>=1.5.0` — mocking of `datetime` for time-sensitive tests.

All pytest configuration lives in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--verbose",
    "--cov=services",
    "--cov=models",
    "--cov=handlers",
    "--cov-report=term-missing",
    "--cov-report=html:.coverage_html",
    "--cov-fail-under=70"
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow tests",
    "e2e: E2E tests"
]
```

Coverage source and reporting configuration is also in `pyproject.toml` under `[tool.coverage.*]`.

Before running tests for the first time, install dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

The shared test infrastructure is defined in `tests/conftest.py`:

- `engine` / `db_session` — in-memory SQLite database with per-test transactional rollback (prevents state leakage between tests).
- Dozens of `sample_*` fixtures (e.g. `sample_user`, `sample_admin`, `sample_mission`, `sample_balance`, `sample_subscription`, `sample_package`, etc.) that create realistic model instances.
- `mock_bot`, `mock_dispatcher` — AsyncMock/MagicMock Telegram objects.
- Factory fixtures: `make_user`, `make_message`, `make_callback`, `make_fsm_context` for building aiogram test doubles on demand.
- Additional domain-specific fixtures (streak promotions, nurture sequences, etc.).

## Running tests

The canonical entry points are the Makefile targets (recommended) or direct `pytest` invocations. Pyproject `addopts` are applied automatically unless overridden on the command line.

```bash
# Full verbose suite (applies coverage from pyproject.toml)
make test
# equivalent to:
pytest tests/ -v
```

```bash
# Coverage report (opens HTML if xdg-open available)
make test-cov
```

```bash
# Parallel execution
make test-parallel
# or
pytest tests/ -n auto
```

```bash
# Subset examples
pytest tests/ -m "unit or integration"           # only unit + integration
pytest tests/unit/                               # services and utilities
pytest tests/integration/test_cross_service_atomicity.py
pytest tests/handlers/test_gamification_user_handlers.py -k "besito"
```

E2E tests live under `tests/e2e/` and are excluded from the default CI run (see CI section).

## Writing new tests

- **Location and naming** (enforced by `pyproject.toml`):
  - Files: `test_*.py` or `*_test.py`
  - Classes: `Test*`
  - Functions: `test_*`
  - Unit tests → `tests/unit/`
  - Integration / cross-service flows → `tests/integration/`
  - End-to-end → `tests/e2e/`
  - Handler tests → `tests/handlers/`

- **Markers** — always decorate the test or class:

  ```python
  import pytest

  @pytest.mark.unit
  def test_credit_increases_balance(db_session, sample_user):
      ...
  ```

- **Use the fixtures**:

  ```python
  @pytest.mark.integration
  def test_vip_grant_flow(db_session, sample_user, sample_tariff, sample_vip_channel, make_callback):
      ...
  ```

- **Handler test pattern** (typical):

  ```python
  @pytest.mark.unit
  async def test_start_creates_user(make_message, make_fsm_context):
      msg = make_message("/start")
      # call handler
      # assert service called once, reply sent, etc.
  ```

- Keep tests focused. Unit tests should not hit real external services. Integration tests use the real `db_session` but still mock Telegram I/O via the factories.
- Prefer the `sample_*` and `make_*` fixtures over ad-hoc object creation so that contract changes (telegram_id vs internal id, aware datetimes, etc.) are caught centrally.

## Coverage requirements

Coverage is collected for `services/`, `models/`, and `handlers/`.

| Type                  | Threshold |
|-----------------------|-----------|
| Overall (fail-under)  | 70%       |

Configured in `pyproject.toml`:

- `--cov-fail-under=70`
- Reports: `term-missing` + HTML in `.coverage_html/`

**Note**: The CI job currently executes with `--cov-fail-under=30` together with a set of ignores and deselections for stability during refactors. The 70% threshold in `pyproject.toml` remains the project standard for local and future CI tightening.

## CI integration

Tests are executed in the GitHub Actions workflow `.github/workflows/ci.yml`.

- **Name**: CI
- **Triggers**: `push` and `pull_request` to the `main` branch
- **Environment**: Ubuntu latest, Python 3.12 (via `uv`)
- **Test step** (excerpt):

  ```yaml
  - name: Test (pytest + coverage)
    run: >
      pytest tests/
      --ignore=tests/e2e
      --ignore=tests/integration/test_alembic_heads.py
      --deselect tests/integration/test_free_entry_flow.py::...
      ... (additional deselections for known-flaky or refactored tests)
      --cov=services --cov=models --cov=handlers --cov-fail-under=30
    env:
      CI: true
  ```

Other jobs in the same workflow run lint (ruff), format check, mypy (some non-blocking), and bandit security scan.

To reproduce the exact CI test command locally:

```bash
pytest tests/ \
  --ignore=tests/e2e \
  --ignore=tests/integration/test_alembic_heads.py \
  --deselect tests/integration/test_free_entry_flow.py::TestFreeEntryFlow::test_impatience_message_on_repeated_request \
  # ... (see .github/workflows/ci.yml for current list) \
  --cov=services --cov=models --cov=handlers --cov-fail-under=30
```

---

**Related**:
- `Makefile` — convenience targets
- `tests/conftest.py` — shared fixtures and factories
- `pyproject.toml` — pytest and coverage configuration
- `README.md` — quick pointer to running subsets
