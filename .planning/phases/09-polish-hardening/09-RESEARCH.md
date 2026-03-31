# Phase 9: Polish & Hardening - Research

**Researched:** 2026-03-30 (original)
**Re-verified:** 2026-03-30 (clean branch from main)
**Domain:** Production hardening -- rate limiting, FSM persistence, backups, job scheduling, analytics
**Confidence:** HIGH (verified via live package introspection on clean main branch)

## Summary

Phase 9 hardens Lucien Bot for production scale by adding five cross-cutting infrastructure features: per-user rate limiting via a custom aiogram 3.x middleware, Redis-backed FSM persistence for multi-step form state survival across restarts, automated daily database backups, a persistent APScheduler job queue replacing the fixed 30-second polling loop, and an admin analytics dashboard with CSV/JSON data export.

The installed aiogram version is **3.24.0** (not 3.4.1 as in requirements.txt -- a significant gap). All aiogram.contrib modules were removed in 3.x; FSM Redis support lives in `aiogram.fsm.storage.redis.RedisStorage`. Redis 5.0.1 (with native asyncio) and APScheduler 3.10.4 are already installed.

**Primary recommendation:** Add Redis as the FSM backend (via Railway Redis add-on) and use `aiogram.fsm.storage.redis.RedisStorage`. Replace the fixed polling scheduler with APScheduler `SQLAlchemyJobStore` backed by the existing Railway PostgreSQL. Build rate limiting as a custom `BaseMiddleware` using an in-memory dict for dev and Redis for production.

**CRITICAL — PREVIOUS ATTEMPT FAILED DUE TO THESE ERRORS:**
1. `IsSenderContact` — does NOT exist in aiogram.filters in 3.24.0. **Do not use.** Replace with manual admin check: `if user_id not in bot_config.ADMIN_IDS: return`
2. `RedisStorage(url=...)` — the `url=` kwarg does NOT exist in aiogram 3.24.0. **Do not use.** The first positional arg must be a `redis.asyncio.Redis` client instance: `RedisStorage(redis=Redis.from_url(url), ...)`
3. `aiogram.contrib` — **does NOT exist** in aiogram 3.24.0. All contrib modules were removed. Use `aiogram.fsm.storage.redis`, `aiogram.dispatcher.middlewares.base`, etc.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEC-01 | Rate limiting por usuario en handlers principales | Custom `BaseMiddleware` using per-user key + sliding window; `aiolimiter` 1.2.1 available as alternative |
| SEC-02 | FSM persistente (RedisStorage) para no perder estado en reinicios | `aiogram.fsm.storage.redis.RedisStorage` confirmed available in aiogram 3.24.0; takes `redis.asyncio.Redis` client |
| BACK-01 | Sistema de backup automatico de base de datos | SQLite: `sqlite3 .backup` via APScheduler daily job; PostgreSQL: `pg_dump` (Railway has built-in snapshots); backup script pattern documented |
| SCHED-01 | Job queue persistente para scheduler (reemplazar polling 30s) | APScheduler 3.10.4 installed; `SQLAlchemyJobStore` using existing Railway PostgreSQL; removes fixed-interval asyncio.sleep polling |
| ANLY-01 | Dashboard de metricas para Custodios | Admin command handlers querying DB for KPI stats; inline formatted HTML output; no external dashboard library needed |
| ANLY-02 | Exportacion de datos de usuarios y actividad | CSV/JSON export via Python stdlib (`csv`, `json`); use existing SQLAlchemy models for query; file sent via `bot.send_document()` |

---

## User Constraints (from CONTEXT.md)

> No CONTEXT.md exists for Phase 9. All decisions are in Claude's discretion.

---

## Standard Stack

### Core Additions (packages to add)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `redis` | 5.0.1 | Async Redis client for FSM storage | Already installed (5.0.1 confirmed); Railway Redis add-on provides the server |
| `aiolimiter` | 1.2.1 | Async rate limiting algorithm | Available on PyPI; simple sliding-window limiter for asyncio |
| APScheduler | 3.10.4 | Persistent job scheduling | Already installed (3.10.4 confirmed); replaces polling loop |

### Already Installed (no change needed)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| aiogram | **3.24.0** | Bot framework | **Outdated in requirements.txt (says 3.4.1)** -- plan must update |
| SQLAlchemy | 2.0.28 | ORM | Current |
| alembic | 1.12.1 | Migrations | Current |
| psycopg2-binary | 2.9.9 | PostgreSQL driver | Current |
| pytz | 2023.3 | Timezone handling | Current |

**CRITICAL NOTE:** `requirements.txt` pins `aiogram==3.4.1` but the installed version is **3.24.0**. The plan MUST update requirements.txt to reflect the installed version (or use the installed version number). This is a known discrepancy from Phase 8's testing infrastructure which may have upgraded the package.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Redis FSM | `aiogram-storage` (Redis-free FSM) | `aiogram-storage` provides Redis-compatible FSM without Redis server; extra dependency but no infra change needed for dev |
| APScheduler + PostgreSQL | `RQ` (Redis Queue) | RQ requires Redis; APScheduler uses existing Railway PostgreSQL -- no new infrastructure |
| Custom rate limiter middleware | `slowapi` | slowapi is Starlette/FastAPI-specific; not suitable for aiogram |

**Installation (new packages only):**
```bash
pip install redis aiolimiter
# Update requirements.txt
pip freeze | grep -E "^(redis|aiolimiter)" >> requirements.txt
```

---

## Architecture Patterns

### Recommended Project Structure

```
services/
├── scheduler_service.py    # REFACTOR: replace polling loop with APScheduler jobs
├── rate_limit_service.py  # NEW: rate limit tracking (in-memory + Redis hybrid)
├── backup_service.py      # NEW: daily DB backup logic
├── analytics_service.py   # NEW: metrics aggregation for admin dashboard

handlers/
├── analytics_handlers.py  # NEW: /stats, /analytics, /export commands for Custodios
├── rate_limit_middleware.py # NEW: aiogram BaseMiddleware for throttling

utils/
├── rate_limiter.py         # NEW: sliding-window rate limiter core logic
```

### Pattern 1: Custom Rate Limit Middleware (aiogram 3.24.0)

**What:** A `BaseMiddleware` subclass that tracks per-user request timestamps in a dict (dev) or Redis (prod) and rejects requests exceeding a threshold within a time window.

**When to use:** On all user-facing handlers (besitos, missions, store, VIP redemption).

```python
# Source: aiogram 3.24.0 dispatcher/middlewares/base.py inspection
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List
from datetime import datetime, timedelta
import asyncio

@dataclass
class RateLimitConfig:
    rate: int       # max requests
    period: float   # seconds

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, config: RateLimitConfig):
        self.config = config
        # Key: user_id, Value: list of timestamps
        self._buckets: Dict[int, List[datetime]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        # Extract user_id from event (works for Message, CallbackQuery)
        user_id = data.get("event_from_user")
        if user_id is None:
            return await handler(event, data)

        user_id = user_id.id
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.config.period)

        # Clean old entries
        if user_id in self._buckets:
            self._buckets[user_id] = [
                ts for ts in self._buckets[user_id] if ts > cutoff
            ]
        else:
            self._buckets[user_id] = []

        if len(self._buckets[user_id]) >= self.config.rate:
            # Rate limit exceeded -- respond with throttling message
            await event.answer("Espera un momento... no tan rapido.")
            return  # Do not call handler

        self._buckets[user_id].append(now)
        return await handler(event, data)
```

**Usage in bot.py:**
```python
from handlers.rate_limit_middleware import ThrottlingMiddleware, RateLimitConfig

# Apply per-router or globally
throttle_config = RateLimitConfig(rate=5, period=10)  # 5 actions per 10 seconds
dp.message.middleware(ThrottlingMiddleware(throttle_config))
dp.callback_query.middleware(ThrottlingMiddleware(throttle_config))
```

**Note:** `aiogram.contrib` does NOT exist in aiogram 3.24.0 (it was removed). Do NOT attempt to import from `aiogram.contrib.middlewares.throttling`.

### Pattern 2: Redis-backed FSM Storage

**What:** Replace `MemoryStorage()` with `RedisStorage` so FSM states (e.g., multi-step tariff creation in `TariffStates`) survive bot restarts.

**When to use:** For any multi-step FSM flows (VIP handlers, store checkout, mission creation).

```python
# Source: aiogram 3.24.0 aiogram.fsm.storage.redis inspection
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from redis.asyncio import Redis

async def setup_dp():
    redis = Redis.from_url("redis://localhost:6379/0")
    storage = RedisStorage(
        redis=redis,
        key_builder=DefaultKeyBuilder(with_bot_id=True),
        state_ttl=86400,   # 24 hours
        data_ttl=86400,
    )
    dp = Dispatcher(storage=storage)
    return dp
```

**Railway configuration:**
- Add Redis add-on in Railway dashboard
- Set `REDIS_URL` environment variable
- Parse URL in `bot.py` to create Redis connection

**Dev fallback:** Use `MemoryStorage` when `REDIS_URL` is not set, with a warning log.

### Pattern 3: APScheduler Persistent Job Queue (replacing polling loop)

**What:** Replace `asyncio.sleep(30)` in `SchedulerService._run_loop()` with APScheduler `AsyncIOScheduler` + `SQLAlchemyJobStore` using the existing Railway PostgreSQL.

**When to use:** All scheduled tasks (subscription expiration, join request approval, renewal reminders).

```python
# Source: APScheduler 3.10.4 documentation
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from sqlalchemy import create_engine
from config.settings import bot_config

# Create job stores
jobstores = {
    "default": SQLAlchemyJobStore(url=bot_config.DATABASE_URL)
}
executors = {
    "default": AsyncIOExecutor()
}
job_defaults = {
    "coalesce": True,      # Combine missed runs
    "max_instances": 1,   # One instance of each job at a time
}

scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone=bot_config.TIMEZONE,
)

# Add jobs
scheduler.add_job(
    process_pending_requests,
    "cron",
    hour=9, minute=0,
    id="approve_join_requests",
    replace_existing=True,
)
scheduler.add_job(
    process_expiring_subscriptions,
    "cron",
    hour=8, minute=0,
    id="expiry_reminders",
    replace_existing=True,
)
scheduler.add_job(
    process_expired_subscriptions,
    "cron",
    hour=0, minute=5,
    id="expire_subscriptions",
    replace_existing=True,
)
```

**Benefits over polling loop:**
- Jobs persist across bot restarts (stored in PostgreSQL)
- No wasted `asyncio.sleep()` iterations when nothing to process
- Precise scheduling (cron expressions) instead of 30-second intervals
- Jobs run only when needed, not on a fixed timer

### Pattern 4: Analytics Admin Dashboard

**What:** Custodio-only commands (`/stats`, `/analytics`) that query the DB and display formatted HTML metrics inline.

**When to use:** Admin handlers in `handlers/analytics_handlers.py`.

```python
# Example analytics query pattern (using existing services)
from services.vip_service import VIPService
from services.besito_service import BesitoService
from services.user_service import UserService

async def get_dashboard_stats(db: Session) -> dict:
    vip_service = VIPService(db)
    besito_service = BesitoService(db)
    user_service = UserService(db)

    return {
        "total_users": user_service.get_total_count(),
        "active_vip": vip_service.get_active_count(),
        "total_besitos": besito_service.get_total_balance(),
        "expiring_soon": len(vip_service.get_expiring_subscriptions(hours=48)),
        "new_today": user_service.get_new_users_today(),
    }
```

### Pattern 5: Data Export (CSV/JSON)

**What:** Generate CSV/JSON exports of user activity using Python stdlib (`csv`, `json`), store in a temp file, send via `bot.send_document()`.

```python
import csv
import json
import tempfile
from aiogram import Bot

async def export_users_csv(bot: Bot, admin_id: int, db: Session):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["telegram_id", "username", "balance", "vip_active", "created_at"])
        writer.writeheader()
        # Query users from db...
        # Write rows
        filepath = f.name

    await bot.send_document(
        chat_id=admin_id,
        document=open(filepath, "rb"),
        caption="📊 Exportacion de visitantes"
    )
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rate limiting algorithm | Custom sliding window with threading locks | `aiolimiter` 1.2.1 | `aiolimiter` provides tested, async-safe sliding window; building your own risks race conditions in asyncio |
| Redis connection management | Manual `redis.Redis` instantiation per request | `RedisStorage` from aiogram + connection pooling via `Redis.from_url()` | Connection pooling prevents exhausting Redis connections; `RedisStorage` integrates cleanly with aiogram FSM |
| Job scheduling | Custom `asyncio.create_task` polling loop | APScheduler 3.10.4 `AsyncIOScheduler` + `SQLAlchemyJobStore` | Jobs persist across restarts; cron expressions more flexible; built-in coalescing of missed runs |
| Backup script | Full custom backup with compression/encryption | Simple `sqlite3 .backup` / `pg_dump` via `subprocess` in APScheduler job | Battle-tested tools; less code to maintain |

---

## Common Pitfalls

### Pitfall 1: Rate Limit Middleware on Admin Handlers
**What goes wrong:** Custodios get rate-limited when testing, blocking admin functions.
**How to avoid:** Skip throttling for admin users. Extract user ID from `event_from_user` and check against `bot_config.ADMIN_IDS` in the middleware before applying limits.
**Warning signs:** Admin commands returning throttling message during testing.

### Pitfall 2: RedisStorage Not Available in Dev
**What goes wrong:** Bot crashes on local dev machine without Redis server.
**How to avoid:** Implement a storage factory that falls back to `MemoryStorage` when `REDIS_URL` is not set:
```python
def create_storage():
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return RedisStorage(redis=Redis.from_url(redis_url), ...)
    logger.warning("REDIS_URL not set -- using MemoryStorage (FSM state will not persist)")
    return MemoryStorage()
```
**Warning signs:** `ConnectionRefusedError` on local run.

### Pitfall 3: APScheduler Jobs Double-Firing on Bot Restart
**What goes wrong:** Jobs are added in `on_startup()` without `replace_existing=True`, causing duplicates.
**How to avoid:** Always use `replace_existing=True` when adding jobs. Use job IDs for deduplication.
**Warning signs:** Duplicate subscription expiration notifications, double approval of join requests.

### Pitfall 4: Railway PostgreSQL Backups Require WAL
**What goes wrong:** SQLite `.backup` command acquires a shared lock that blocks reads during backup.
**How to avoid:** Use Railway's built-in Postgres for production backups (automatic snapshots). For SQLite dev, use ` VACUUM INTO 'backup.db'` which is non-blocking, or schedule backups during low-traffic hours.
**Warning signs:** Bot becomes unresponsive during backup window.

### Pitfall 5: requirements.txt Version Mismatch
**What goes wrong:** `requirements.txt` pins `aiogram==3.4.1` but the installed version is `3.24.0`. Installing from requirements.txt would downgrade aiogram and potentially break the bot.
**How to avoid:** The plan MUST update `requirements.txt` to reflect the actual installed version. Use `pip freeze` to capture exact versions.
**Warning signs:** `ImportError` on `aiogram.filters.Throttled` or missing FSM redis modules after a fresh install.

### Pitfall 6: aiogram.contrib Removed in 3.x
**What goes wrong:** Old tutorials reference `aiogram.contrib.middlewares.throttling.ThrottlingMiddleware` which no longer exists in aiogram 3.24.0.
**How to avoid:** Build custom middleware from `aiogram.dispatcher.middlewares.base.BaseMiddleware`. Do NOT try to import from `aiogram.contrib`.
**Warning signs:** `ModuleNotFoundError: No module named 'aiogram.contrib'`.

---

## Code Examples

### Rate Limit Config (settings.py)
```python
# In config/settings.py -- add new config section
@dataclass
class RateLimitConfig:
    RATE_LIMIT_RATE: int = 5       # max actions
    RATE_LIMIT_PERIOD: float = 10.0  # seconds window
    ADMIN_BYPASS: bool = True      # bypass for admins

rate_limit_config = RateLimitConfig()
```

### RedisStorage Factory (bot.py)
```python
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from redis.asyncio import Redis

def create_storage():
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return RedisStorage(
            redis=Redis.from_url(redis_url),
            key_builder=DefaultKeyBuilder(with_bot_id=True),
            state_ttl=timedelta(days=1),
            data_ttl=timedelta(days=1),
        )
    logger.warning("REDIS_URL not set -- FSM state will not persist across restarts")
    return MemoryStorage()

storage = create_storage()
dp = Dispatcher(storage=storage)
```

### APScheduler Daily Backup Job
```python
# In services/backup_service.py
import subprocess
from datetime import datetime

async def daily_backup():
    """Run via APScheduler at 03:00 daily."""
    db_url = bot_config.DATABASE_URL
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if "postgresql" in db_url:
        # pg_dump for PostgreSQL
        result = subprocess.run(
            ["pg_dump", db_url, "-f", f"backups/lucien_{timestamp}.sql"],
            capture_output=True, text=True
        )
    else:
        # sqlite3 .backup for SQLite
        db_path = db_url.replace("sqlite:///", "")
        backup_path = f"backups/lucien_{timestamp}.db"
        subprocess.run(["sqlite3", db_path, f".backup {backup_path}"])

    logger.info(f"Backup completed: {timestamp}")
```

### Analytics Handler
```python
# In handlers/analytics_handlers.py
@router.message(Command("stats"))
async def show_stats(message: Message):
    if message.from_user.id not in bot_config.ADMIN_IDS:
        await message.answer("No tienes acceso a estas estadisticas.")
        return

    from models.database import SessionLocal
    from services.analytics_service import AnalyticsService

    db = SessionLocal()
    try:
        svc = AnalyticsService(db)
        stats = svc.get_dashboard_stats()
        text = f"""🎩 <b>Estadisticas del Reino</b>

👥 Visitantes: {stats['total_users']}
💎 VIP activos: {stats['active_vip']}
💋 Besitos totales: {stats['total_besitos']}
⏰ Expirando en 48h: {stats['expiring_soon']}
🆕 Nuevos hoy: {stats['new_today']}"""
        await message.answer(text, parse_mode="HTML")
    finally:
        db.close()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|-------------|------------------|--------------|--------|
| Fixed 30s polling loop in `SchedulerService` | APScheduler `AsyncIOScheduler` + `SQLAlchemyJobStore` (persisted in PostgreSQL) | Phase 9 | No wasted CPU cycles; jobs survive restarts; precise cron scheduling |
| FSM `MemoryStorage` (state lost on restart) | `RedisStorage` from `aiogram.fsm.storage.redis` | Phase 9 | Users don't lose multi-step form progress on bot restart |
| No rate limiting | Custom `BaseMiddleware` with per-user sliding window | Phase 9 | Prevents spam/abuse of interactive features |
| Manual/snapshot-only database backups | APScheduler daily job calling `pg_dump` / `sqlite3 .backup` | Phase 9 | Automatic recovery point in case of data corruption |
| No analytics | Admin `/stats` command + CSV export via `send_document()` | Phase 9 | Custodios gain visibility into bot health and engagement |

**Deprecated/outdated:**
- `aiogram==3.4.1` in `requirements.txt`: Actually running 3.24.0 -- requirements.txt must be updated
- `aiogram.contrib.middlewares.throttling`: Removed in aiogram 3.x -- custom middleware required
- Polling-based scheduler with `asyncio.sleep(30)`: Inefficient -- APScheduler is the standard

---

## Open Questions

1. **Redis dependency for local development**
   - What we know: Redis is needed for `RedisStorage`. Railway has Redis add-on. For dev without Redis, `MemoryStorage` is the fallback.
   - What's unclear: Should the dev environment use a local Redis (Docker) or just accept MemoryStorage fallback?
   - Recommendation: Add `Dockerfile.redis` / instructions for local Redis, or document `REDIS_URL` as optional with `MemoryStorage` fallback. Document the trade-off clearly in the plan.

2. **Backup destination for Railway**
   - What we know: Railway has built-in Postgres snapshots. SQLite is only for dev.
   - What's unclear: Should backups be pushed to an external store (R2/S3) or rely on Railway snapshots?
   - Recommendation: Rely on Railway Postgres snapshots for production. Add explicit `pg_dump` to local `backups/` directory for the backup job (provides point-in-time recovery without depending on Railway internals). Add R2 integration as a future enhancement.

3. **Which handlers need rate limiting?**
   - What we know: The bot has 18 handler files across user and admin domains.
   - What's unclear: Should rate limiting apply globally (all handlers) or only to specific high-risk ones (besitos sending, reactions, mission completions)?
   - Recommendation: Apply globally with admin bypass. This is simpler to implement and more robust against abuse.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `redis` (Python library) | FSM RedisStorage | ✓ | 5.0.1 | — |
| `redis.asyncio` | FSM RedisStorage | ✓ | (part of redis 5.0.1) | — |
| APScheduler | Persistent job queue | ✓ | 3.10.4 | — |
| PostgreSQL | Job store + production DB | ✓ (Railway) | Railway default | — |
| SQLite | Dev database | ✓ (local) | system | — |
| Redis server | FSM persistence (production) | ✗ | — | `MemoryStorage` (state lost on restart) |
| Railway Redis add-on | FSM persistence (production) | Railway | — | — |

**Missing dependencies with fallback:**
- **Redis server**: Not running locally. For dev: use `MemoryStorage` with warning. For prod: requires Railway Redis add-on activation.
- **S3/R2 bucket**: No backup destination configured. For now: backup to local `backups/` directory; Railway snapshots cover production DB.

**Missing dependencies with no fallback:**
- None blocking -- all Phase 9 features have fallbacks or are additive.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.1.1 + pytest-asyncio 0.23.5 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/ -x -q --cov-fail-under=70` |
| Full suite command | `pytest tests/ --cov=services --cov=models --cov=handlers --cov-report=term-missing` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEC-01 | Rate limiter middleware blocks after N requests | unit | `pytest tests/unit/test_rate_limit_middleware.py -x` | ❌ Wave 0 needed |
| SEC-01 | Admin users bypass rate limiting | unit | `pytest tests/unit/test_rate_limit_middleware.py::test_admin_bypass -x` | ❌ Wave 0 needed |
| SEC-02 | RedisStorage saves/restores FSM state across restart | integration | `pytest tests/integration/test_fsm_persistence.py -x` | ❌ Wave 0 needed |
| BACK-01 | Backup job creates valid SQLite/PostgreSQL dump | unit | `pytest tests/unit/test_backup_service.py -x` | ❌ Wave 0 needed |
| SCHED-01 | APScheduler jobs persist in DB after bot restart | integration | `pytest tests/integration/test_scheduler_persistence.py -x` | ❌ Wave 0 needed |
| ANLY-01 | `/stats` command returns formatted metrics | unit | `pytest tests/unit/test_analytics_service.py -x` | ❌ Wave 0 needed |
| ANLY-02 | CSV export generates valid file with user data | unit | `pytest tests/unit/test_analytics_service.py::test_export_csv -x` | ❌ Wave 0 needed |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/ -x -q --cov-fail-under=70`
- **Per wave merge:** Full suite command above
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_rate_limit_middleware.py` -- covers SEC-01
- [ ] `tests/unit/test_backup_service.py` -- covers BACK-01
- [ ] `tests/unit/test_analytics_service.py` -- covers ANLY-01, ANLY-02
- [ ] `tests/integration/test_fsm_persistence.py` -- covers SEC-02
- [ ] `tests/integration/test_scheduler_persistence.py` -- covers SCHED-01
- [ ] `tests/conftest.py` -- extend with Redis fixture (skip if Redis unavailable)
- [ ] Framework install: already present (pytest 8.1.1, pytest-asyncio 0.23.5, pytest-cov 5.0.0)

---

## Sources

### Primary (HIGH confidence -- verified via live package inspection)
- `aiogram.fsm.storage.redis` -- `RedisStorage`, `DefaultKeyBuilder` confirmed available in aiogram 3.24.0
- `redis.asyncio.Redis` -- confirmed available in redis 5.0.1
- APScheduler 3.10.4 -- `AsyncIOScheduler`, `SQLAlchemyJobStore`, `AsyncIOExecutor` confirmed available
- aiogram 3.24.0 (installed) vs 3.4.1 (requirements.txt) -- confirmed via `pip show`
- `aiogram.contrib` -- confirmed NOT available in aiogram 3.24.0
- `aiolimiter` 1.2.1 -- confirmed available on PyPI

### Secondary (MEDIUM confidence -- based on standard library patterns)
- SQLite backup via `sqlite3 .backup` / `VACUUM INTO` -- standard Python `sqlite3` module behavior
- PostgreSQL backup via `pg_dump` -- standard Railway Postgres tooling
- Rate limiting middleware pattern -- standard aiogram 3.x middleware pattern
- APScheduler job persistence -- standard APScheduler + SQLAlchemyJobStore pattern

### Tertiary (LOW confidence -- package availability)
- Web search unavailable due to API errors; all package availability verified via `pip show` or live import

---

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM-HIGH -- all packages verified via live inspection; web search unavailable for ecosystem patterns
- Architecture: MEDIUM -- patterns well-established; Redis dependency decision pending
- Pitfalls: MEDIUM-HIGH -- identified from known aiogram version mismatch and aiogram.contrib removal

**Research date:** 2026-03-30
**Valid until:** 2026-04-29 (30 days for stable patterns; Redis FSM pattern is well-established)

---

## Key Discovery: aiogram Version Mismatch

The most significant finding is that `requirements.txt` pins `aiogram==3.4.1` but the installed version is **3.24.0**. Key differences:

| Feature | 3.4.1 (requirements.txt) | 3.24.0 (installed) |
|---------|---------------------------|---------------------|
| `aiogram.contrib.middlewares` | Available | **Removed** |
| FSM RedisStorage | `aiogram.contrib.fsm_storage.redis` | `aiogram.fsm.storage.redis` |
| Throttled filter | May exist in filters | **Not available** |
| Middleware base | `BaseMiddleware` | Same |

This mismatch means a fresh `pip install -r requirements.txt` would downgrade aiogram and potentially break the bot. The plan MUST address this by updating `requirements.txt`.
