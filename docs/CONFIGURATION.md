<!-- generated-by: gsd-doc-writer -->
# Configuration

## Environment variables

The application is configured exclusively via environment variables loaded from a `.env` file (using `python-dotenv`). Copy `.env.example` to `.env` and fill in values.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | **Required** | (none) | Telegram Bot API token obtained from [@BotFather](https://t.me/BotFather). If unset or empty, the bot fails to start with `sys.exit(1)`. |
| `ADMIN_IDS` | No | (empty list) | Comma-separated list of Custodio (admin) Telegram user IDs (e.g. `123,456`). If unset, admin commands are unavailable (warning logged only). Parsed into `list[int]` at startup. |
| `DATABASE_URL` | No | `sqlite:///lucien_bot.db` | SQLAlchemy connection string. Use `sqlite:///...` for local development; `postgresql://...` for production. |
| `TIMEZONE` | No | `America/Mexico_City` | IANA timezone name used for scheduled jobs, daily gifts, and date calculations. |
| `CREATOR_USERNAME` | No | (empty) | Telegram username of the content creator (Diana) without the leading `@`. Used to render contact buttons in promotions. |
| `LOG_LEVEL` | No | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Applied at process startup in `bot.py`. |
| `REDIS_URL` | No | (none) | Redis connection URL (e.g. `redis://host:6379/0`). When present, FSM conversation state uses persistent `RedisStorage`; otherwise falls back to in-memory `MemoryStorage` (state lost on restart). |
| `HEALTH_ENABLED` | No | (not set) | Set to `"1"` to start the optional lightweight HTTP health endpoint (`/health`) on a separate port. Requires the `aiohttp` package; gracefully skipped otherwise. |
| `HEALTH_PORT` | No | `8080` | TCP port for the health HTTP server (only used when `HEALTH_ENABLED=1`). |

**Additional variables documented in `.env.example` but not referenced via `os.getenv` (or equivalent) in current application Python source at runtime** (may be legacy, planned, or for external platform use):

- `VIP_CHANNEL_ID`
- `FREE_CHANNEL_ID`
- `DEBUG`
- `SECRET_KEY`
- `WEBHOOK_URL`
- `PORT`

**Script-only optional variables** (used exclusively by `scripts/seed_catalog.py` for placeholder linking during catalog seeding; not read by the main bot):

- `SEED_PLACEHOLDER_PACKAGE_ID`
- `SEED_PLACEHOLDER_STORY_NODE_ID`
- `SEED_PLACEHOLDER_TARIFF_ID`

## Config file format

Configuration beyond environment variables is provided by the following files (none are JSON/YAML application config; all are build, migration, or platform metadata).

### Primary runtime configuration (Python)
Environment variables are loaded once at import time:

```python
# config/settings.py
from dotenv import load_dotenv
load_dotenv()

@dataclass
class BotConfig:
    TOKEN: str = os.getenv("BOT_TOKEN", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///lucien_bot.db")
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Mexico_City")
    CREATOR_USERNAME: str = os.getenv("CREATOR_USERNAME", "")
    # ADMIN_IDS parsed from CSV in __post_init__
```

Access via:
```python
from config.settings import bot_config, messages_config, rate_limit_config
```

`MessagesConfig` and `RateLimitConfig` contain only hardcoded defaults (not driven by environment variables).

### Other configuration files

- `railway.toml` (TOML) — Railway deployment definition:
  ```toml
  [build]
  builder = "nixpacks"
  [build.env]
  NIXPACKS_PYTHON_VERSION = "3.12"

  [deploy]
  startCommand = "alembic upgrade head && python bot.py"
  restartPolicyType = "on_failure"
  restartPolicyMaxRetries = 3
  ```
- `alembic.ini` (INI) — Alembic migration engine configuration. The runtime `sqlalchemy.url` is overridden programmatically from `bot_config.DATABASE_URL` (see `alembic/env.py`).
- `pyproject.toml` — Project metadata:
  ```toml
  [project]
  requires-python = ">=3.12"
  ```
- `runtime.txt` — Simple version pin (used by some platforms): `python-3.11.8`
- `Procfile` — Process declaration for compatibility: `worker: python bot.py`

## Required vs optional settings

Startup validation occurs in `bot.py:main()` after `load_dotenv()` and `BotConfig` instantiation:

```python
if not bot_config.TOKEN:
    logger.error("BOT_TOKEN no configurado. Cree un archivo .env con BOT_TOKEN=your_token")
    sys.exit(1)

if not bot_config.ADMIN_IDS:
    logger.warning("ADMIN_IDS no configurado. El panel de administración no estará disponible.")
```

- **BOT_TOKEN**: Hard requirement. Missing/empty value terminates the process before any polling or router registration.
- All other variables: either provide explicit defaults inside `os.getenv(..., default)` or in dataclass fields, or are purely conditional (e.g. `REDIS_URL`, `HEALTH_ENABLED`). Absence produces degraded but non-fatal behavior (in-memory storage, disabled health endpoint, etc.).
- No schema validation libraries (e.g. Pydantic, environs) are used for environment variables.

## Defaults

Defaults are defined in two places:

| Variable | Default | Location |
|----------|---------|----------|
| `DATABASE_URL` | `sqlite:///lucien_bot.db` | `config/settings.py:16` |
| `TIMEZONE` | `America/Mexico_City` | `config/settings.py:17` |
| `CREATOR_USERNAME` | `""` | `config/settings.py:18` |
| `LOG_LEVEL` | `INFO` | `bot.py:94` (`os.getenv("LOG_LEVEL", "INFO")`) |
| `HEALTH_PORT` | `8080` | `bot.py:234` (`os.getenv("HEALTH_PORT", "8080")`) |

`ADMIN_IDS` defaults to `[]` when the env var is missing or empty. `REDIS_URL` and `HEALTH_ENABLED` have no defaults (presence/absence is the signal).

## Per-environment overrides

There are no environment-specific dotenv files (`.env.development`, `.env.production`) committed or loaded by the application.

- `.env.test` exists and supplies test-oriented values (e.g. in-memory DB, `LOG_LEVEL=ERROR`). Note that it references `TELEGRAM_BOT_TOKEN`, which is **not** read by the application (code always expects `BOT_TOKEN`).
- Runtime adaptation is driven by value inspection rather than `NODE_ENV`:
  - Database connection pool (models/database.py): if `"postgresql"` appears in `DATABASE_URL`, a production-sized pool (`pool_size=30`, `max_overflow=50`, etc.) is configured; SQLite uses `check_same_thread=False`.
  - FSM storage (bot.py:create_storage): Redis when `REDIS_URL` is truthy; MemoryStorage otherwise.
- Deployment platform configuration (Railway):
  - `railway.toml` sets `NIXPACKS_PYTHON_VERSION = "3.12"` during build.
  - The start command (`alembic upgrade head && python bot.py`) always runs migrations using the `DATABASE_URL` present at deploy time.
  - Production PostgreSQL `DATABASE_URL` values are injected by the platform (not present in source). <!-- VERIFY: exact production DATABASE_URL hostname, credentials, and connection parameters are managed by the deployment platform -->
- Alembic (`alembic/env.py`) explicitly loads the same `DATABASE_URL` via `bot_config` (after its own `load_dotenv()`).

Python version expectations (as declared vs pinned):
- `pyproject.toml`: `requires-python = ">=3.12"`
- `runtime.txt`: `python-3.11.8`
- Railway build: `3.12` (via nixpacks)

All environment variable reads are centralized through `os.getenv` (or `os.environ.get` for the seed script helper); there are no other config sources at runtime.
