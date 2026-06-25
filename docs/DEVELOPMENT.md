<!-- generated-by: gsd-doc-writer -->
# Development

## Local setup

1. Clone the repository and create a virtual environment:

   ```bash
   git clone https://github.com/carloostoek2/lucienbot.git
   cd lucienbot
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies (runtime + dev tools + pre-commit hooks):

   ```bash
   make install
   ```

   Or manually:

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   pre-commit install
   ```

3. Configure environment variables:

   ```bash
   cp .env.example .env
   # Edit .env with at minimum BOT_TOKEN and ADMIN_IDS
   ```

4. Verify the environment:

   ```bash
   make verify
   ```

Python version: the project declares `requires-python = ">=3.12"` in `pyproject.toml`. The `runtime.txt` file pins `python-3.11.8` (may be stale for some platforms). CI runs on Python 3.12.

## Build commands

All development tasks are defined as Makefile targets:

| Command | Description |
|---------|-------------|
| `make install` | Install runtime and dev dependencies, then run `pre-commit install`. |
| `make run` | Start the bot (`python bot.py`). |
| `make test` | Run the full test suite verbosely (`pytest tests/ -v`). |
| `make test-cov` | Run tests with coverage and open the HTML report (if `xdg-open` available). |
| `make test-parallel` | Run tests in parallel with `pytest-xdist` (`-n auto`). |
| `make lint` | Run `ruff check` and `ruff format --check` on source directories. |
| `make format` | Auto-fix with `ruff check --fix` and format with `ruff format`. |
| `make typecheck` | Run `mypy` on source directories. |
| `make security` | Run `bandit -r` and `safety check`. |
| `make ci` | Composite: `lint`, `security`, `typecheck`, `test`. |
| `make check-db` | Quick DB connectivity probe using SQLAlchemy. |
| `make verify` | Run `scripts/verify_env.py` to check required dev packages are importable. |
| `make clean` | Remove coverage artifacts and `__pycache__` / `.pyc` files. |

Note: Makefile targets reference `bot/` directories for lint/format/typecheck/security, but the actual entry point is `bot.py` (no `bot/` package directory). CI runs tools directly against `bot.py` and the package directories.

## Code style

### Linting and formatting — Ruff

Ruff is configured in `pyproject.toml` under `[tool.ruff]`, `[tool.ruff.lint]`, and `[tool.ruff.format]`:

- Target Python: 3.12
- Line length: 100
- Quote style: double
- Indent: 4 spaces
- Enabled rule sets: E (errors), W (warnings), F (Pyflakes), I (isort), N (pep8-naming), UP (pyupgrade), B (bugbear), C4 (comprehensions), SIM (simplify)
- Ignored: E501 (line length, handled by formatter), B008 (function calls in defaults)
- Docstring convention: Google style (`[tool.ruff.lint.pydocstyle]`)

Run via:

```bash
make lint     # check only
make format   # auto-fix + format
```

Pre-commit runs `ruff` (with `--fix`) and `ruff-format` on commit.

### Type checking — mypy

Configuration lives in `mypy.ini`:

- `python_version = 3.12`
- `warn_return_any = True`
- `warn_unused_configs = True`
- `check_untyped_defs = True`
- Missing imports ignored for: `aiogram.*`, `sqlalchemy.*`, `pytz.*`, `redis.*`

Run via:

```bash
make typecheck
```

Pre-commit runs mypy on commit (with `types-python-dateutil` extra).

### Pre-commit hooks

`.pre-commit-config.yaml` registers:

- Standard hooks: trailing whitespace, end-of-file fixer, YAML check, large files, merge conflict check
- `ruff-pre-commit` (v0.6.0): ruff + ruff-format
- `mirrors-mypy` (v1.10.0): mypy with `types-python-dateutil`

Install once with `make install` (or `pre-commit install`). Hooks run automatically on `git commit`.

## Branch conventions

No formal branch naming convention is documented in `CONTRIBUTING.md`, `.github/PULL_REQUEST_TEMPLATE.md`, or other project documentation.

Observed patterns in the repository history include:

- `main` — default branch
- `feature/*` (e.g., `feature/trivias-tematicas`)
- Phase / work identifiers (e.g., `fase18`, `fase18_1`, `vip_fix`, `reset_trivia`)
- Remote PR / dependabot branches (e.g., `dependabot/pip/aiogram-3.27.0`)

Use descriptive names that communicate scope. When in doubt, prefix with `feature/`, `fix/`, or `chore/` for clarity.

## PR process

No formal PR process is documented. There is no `.github/PULL_REQUEST_TEMPLATE.md` or `CONTRIBUTING.md` in the repository.

Observed CI behavior:

- CI workflow (`.github/workflows/ci.yml`) triggers on push and pull requests to `main`.
- The workflow installs via `uv`, then runs lint, format check, type check, security (bandit), and tests (with some integration/e2e exclusions and targeted deselections).
- Coverage is collected but the threshold in CI is currently lowered to 30% (`--cov-fail-under=30`) for the executed subset.

For contributions:

1. Create a branch from `main`.
2. Make changes following the project's architecture rules (handlers call exactly one service; no direct DB access outside models; functions ≤ 50 lines; verb+context+result naming; logging with module|action|user_id|result).
3. Ensure `make lint`, `make typecheck`, and `make test` (or the subsets relevant to your change) pass locally.
4. Open a pull request targeting `main`.
5. Address review feedback and keep CI green.

Admins / custodians merging to `main` should ensure Alembic migrations (if any) are forward-compatible and that critical invariants (gamification balances, narrative progress, VIP/channel state) remain protected.
