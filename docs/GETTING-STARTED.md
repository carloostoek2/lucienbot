<!-- generated-by: gsd-doc-writer -->
# Getting Started

This guide walks you through setting up Lucien Bot locally so you can run the Telegram bot for the Señorita Kinky community.

## Prerequisites

- **Python** >= 3.12 (enforced by `pyproject.toml` `requires-python`; CI matrix and Railway build pin 3.12)
- **pip** and **venv** (included with Python 3)
- **git** (to clone the repository)
- A Telegram account and access to [@BotFather](https://t.me/BotFather) to obtain a bot token
- (Optional) Make (for `make run`, `make install`, etc.)

No other system dependencies are required for local development with the default SQLite database.

## Installation steps

1. Clone the repository:
   ```bash
   git clone https://github.com/carloostoek2/lucienbot.git
   cd lucienbot
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   For full development tooling (tests, lint, typecheck, pre-commit):
   ```bash
   pip install -r requirements-dev.txt
   pre-commit install
   ```
   Or use the convenience target:
   ```bash
   make install
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your values (see below)
   ```

## First run

After configuration, initialize the database schema and start the bot:

```bash
alembic upgrade head
python bot.py
```

Or using Make (after venv activation and config):
```bash
make run
```

The bot will:
- Load configuration from `.env`
- Connect to the database (SQLite by default)
- Register all handlers and middlewares
- Begin polling for Telegram updates

You should see log output like:
```
Iniciando Lucien Bot...
Base de datos inicializada
Scheduler iniciado
```

Send `/start` to your bot in Telegram to verify it is running.

## Common setup issues

- **Missing `BOT_TOKEN`**
  - Error: `BOT_TOKEN no configurado. Cree un archivo .env con BOT_TOKEN=your_token` followed by `sys.exit(1)`
  - Fix: Set `BOT_TOKEN=...` (from @BotFather) in `.env` and restart.

- **Database tables missing (fresh clone)**
  - Error: `OperationalError: no such table: users` (or similar) on first interaction
  - Fix: Run `alembic upgrade head` before (or after) the first `python bot.py`. The production start command in `railway.toml` always does this.

- **Virtual environment not activated**
  - Error: `ModuleNotFoundError: No module named 'aiogram'` or `alembic: command not found`
  - Fix: `source venv/bin/activate` (or equivalent on Windows) before running pip, alembic, or python.

- **`ADMIN_IDS` not set**
  - Warning: `ADMIN_IDS no configurado. El panel de administración no estará disponible.`
  - Admin features (and Custodio commands) will be unavailable until you add comma-separated Telegram user IDs.

- **Python version mismatch**
  - `pyproject.toml` and CI require Python 3.12+. Older runtimes may fail import or lint checks. Use `python --version` to verify.

- **`.env` file not created or incomplete**
  - Run `python scripts/verify_env.py` (after dev requirements) or simply start the bot; the startup validation in `bot.py` will catch the critical missing values.

## Next steps

- See [CONFIGURATION.md](CONFIGURATION.md) for the complete list of environment variables and their meanings.
- See [ARCHITECTURE.md](ARCHITECTURE.md) for system overview, component diagram, and directory rationale.
- See [DEVELOPMENT.md](DEVELOPMENT.md) for local development workflows, linting, and contribution process.
- See [TESTING.md](TESTING.md) (when available) for running the test suite and writing tests.
- Explore the `Makefile` targets (`make test`, `make lint`, `make verify`) for common tasks.
