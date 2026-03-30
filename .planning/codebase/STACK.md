# Technology Stack

**Analysis Date:** 2026-03-29

## Languages

**Primary:**
- Python 3.12+ - All application code

**Secondary:**
- SQL (via SQLAlchemy) - Database queries

## Runtime

**Environment:**
- Python 3.12 (detected from venv)

**Package Manager:**
- pip
- Lockfile: `requirements.txt` present (no `requirements.lock` or `pyproject.toml`)

## Frameworks

**Core:**
- aiogram 3.4.1 - Telegram Bot API framework (async-first)

**Database:**
- SQLAlchemy 2.0.28 - ORM and database abstraction

**Utilities:**
- python-dotenv 1.0.1 - Environment variable loading from `.env`
- pytz 2024.1 - Timezone handling

**Testing:**
- Not detected (no test framework in requirements.txt)

**Build/Dev:**
- Not detected (no build tools configured)

## Key Dependencies

**Critical:**
- aiogram 3.4.1 - Core bot framework, provides Router, Dispatcher, FSM, Bot classes
- SQLAlchemy 2.0.28 - Data persistence layer, all models use SQLAlchemy ORM

**Infrastructure:**
- python-dotenv 1.0.1 - Configuration management via `.env` files
- pytz 2024.1 - Timezone-aware datetime handling for scheduling

**Standard Library:**
- asyncio - Async runtime (built-in)
- logging - Logging framework (built-in)
- dataclasses - Configuration dataclasses (built-in)
- secrets, string - Token generation (built-in)
- enum - Enumerations for types (built-in)

## Configuration

**Environment:**
- `.env` file loaded via `python-dotenv`
- Required variables:
  - `BOT_TOKEN` - Telegram bot API token
  - `ADMIN_IDS` - Comma-separated Telegram user IDs
  - `DATABASE_URL` - SQLAlchemy connection string
  - `TIMEZONE` - IANA timezone name
  - `CREATOR_USERNAME` - Content creator username (for promotions)

**Build:**
- No build configuration detected
- Direct Python execution: `python bot.py`

## Platform Requirements

**Development:**
- Python 3.9+ (README states 3.9+, venv uses 3.12)
- Virtual environment recommended
- `.env` file with valid bot token

**Production:**
- Deployment target: Self-hosted (no cloud platform detected)
- Process manager: Not configured (would need systemd/supervisor for production)
- Database: SQLite by default (`lucien_bot.db`), PostgreSQL-compatible via SQLAlchemy

## Database

**Engine:**
- SQLite (default) - `sqlite:///lucien_bot.db`
- Configurable via `DATABASE_URL` environment variable

**ORM:**
- SQLAlchemy 2.0.28 with declarative base
- Session-per-request pattern in services
- Manual session management (no async SQLAlchemy)

## External APIs

**Telegram Bot API:**
- aiogram 3.4.1 as client
- Long polling method (no webhook configured)
- Features used:
  - Message handling (text, commands)
  - Callback query handling (inline keyboards)
  - Chat join request management
  - Chat member management (ban/unban for VIP expiry)
  - File handling (package content delivery)

---

*Stack analysis: 2026-03-29*
