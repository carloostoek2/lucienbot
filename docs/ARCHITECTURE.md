<!-- generated-by: gsd-doc-writer -->
# Architecture

## System overview

Lucien Bot is a Telegram bot that automates management of free and VIP subscription channels, gamification with virtual currency ("besitos"), a virtual store, recurring missions and rewards, promotions, and interactive narrative for the Señorita Kinky (Diana Hernández) community. It presents an elegant, mysterious persona ("Lucien") as a virtual butler. The primary inputs are Telegram messages, callback queries, deep-link tokens (for VIP access), scheduled jobs, and admin actions; outputs include channel membership grants/revocations, messages and keyboards to visitors and custodians, balance mutations, reward deliveries, purchases, and story progress. The architecture is strictly layered and event-driven: aiogram handles Telegram polling and routing, thin handlers delegate to exactly one domain service, services contain all business logic and interact with SQLAlchemy models for persistence, and an internal best-effort EventBus decouples cross-domain effects (e.g., besitos awards notifying narrative, rewards, store, and broadcast domains).

## Component diagram

```mermaid
graph TD
    TG[Telegram API] -->|Updates / Callbacks| DP[aiogram Dispatcher<br/>bot.py]
    DP --> MW[Middlewares<br/>ErrorHandler, Idempotency, Throttling]
    DP --> HR[Domain Routers<br/>handlers/__init__.py]
    HR --> H[Thin Handlers<br/>exactly one service call]
    H -->|with get_service(Svc) as svc:| S[Domain Services<br/>e.g. BesitoService, VIPService, StoreService]
    S --> EB[InternalEventBus<br/>best-effort, gather return_exceptions]
    S --> DB[(SQLAlchemy Models<br/>models/models.py)]
    DB --> P[(PostgreSQL / SQLite)]
    SCH[SchedulerService<br/>APScheduler + SQLAJobStore] --> S
    HS[HealthService / AnalyticsService] -. read-only .-> DB
    H --> KV[LucienVoice + Keyboards<br/>utils/ + keyboards/]
```

## Data flow

A typical user or admin interaction follows this path:

1. Telegram delivers an Update (Message or CallbackQuery) to the long-polling loop started by `dp.start_polling(bot)` in `bot.py`.
2. Registered outer/middle middlewares run in order: `ErrorHandlerMiddleware` (outer), `IdempotencyMiddleware` (callbacks), `ThrottlingMiddleware` (both).
3. The `Dispatcher` matches the update to one of the registered routers (e.g. `gamification_user_router`, `store_user_router`) and invokes the matching handler function.
4. The handler performs routing, validation, and permission checks, then calls a service (typically via the `get_service()` context manager; direct instantiation used in some handlers). Direct model or DB access from handlers is prohibited.
5. The service executes business logic. It obtains a DB session (via its own `SessionLocal` or passed `get_db_session()`), performs queries/mutations on SQLAlchemy models, and may emit an event after a successful commit (e.g. `schedule_emit(EVENT_BESITOS_AWARDED, payload)`).
6. The `InternalEventBus` fans out the event asynchronously to registered observers using `asyncio.gather(..., return_exceptions=True)`. Each observer logs context and may trigger best-effort side effects in its own domain; observers must not mutate critical balances or atomic state.
7. The service returns a result (balance, subscription, order, etc.). The handler uses `LucienVoice.*()` for message text and keyboard builders from `keyboards/inline_keyboards.py` to craft the response and calls `message.answer(...)` / `callback.message.edit_text(...)`.
8. For background work, `SchedulerService` (started in `on_startup`) triggers jobs that call services directly (no handler involved). The optional `health_server` (aiohttp on separate port when `HEALTH_ENABLED=1`) exposes read-only checks via `HealthService`.

VIP token redemption, subscription expiration checks on startup, and daily gift / mission delivery follow similar paths with additional bot API calls for member management.

## Key abstractions

- **`get_service(service_class, db=None)`** (`services/__init__.py`): Context manager that instantiates a service (passing an optional existing session), yields it, and calls `service.close()` on exit. Enforces the "exactly one service per handler" rule and automatic resource cleanup.
- **`InternalEventBus`** (`services/event_bus.py`): Minimal async pub/sub. `register(event, listener)` and `emit(event, payload)` (never raises to emitter; uses `gather(return_exceptions=True)`). Events: `EVENT_BESITOS_AWARDED`, `EVENT_VIP_ACTIVATED`. Listeners are best-effort and observational for cross-domain notification.
- **`LucienVoice`** (`utils/lucien_voice.py`): Static methods returning HTML-formatted strings. User-facing text in the Lucien voice originates here (some inline in handlers) (3rd person, elegant/mysterious tone, references to "Diana", "visitantes", "custodios").
- **Domain Services** (e.g. `BesitoService`, `VIPService`, `StoreService`, `MissionService`, `ChannelService`, `StoryService`, `RewardService`, `PromotionService`, `AnalyticsService`, `HealthService` in `services/*.py` and subpackages): Encapsulate all business rules, balance arithmetic, token redemption, order processing, archetype calculation, etc. Each owns its DB session unless one is injected.
- **`SchedulerService`** (`services/scheduler_service.py`): Wraps APScheduler with `SQLAlchemyJobStore` so jobs survive restarts; started centrally in `on_startup`.
- **`HealthService`** (`services/health_service.py`): Read-only, best-effort health and sanity checks (DB latency, bot uptime, channel states, scheduler jobs, EventBus listeners, critical invariants, backup age). Follows the same `get_service` + `is_admin` pattern as `AnalyticsService`; never mutates state.
- **SQLAlchemy Models + `get_db_session`** (`models/models.py`, `models/database.py`): Declarative `Base` entities (User, BesitoBalance/Transaction, Channel, Tariff, Token, Subscription, Package, StoreProduct, Mission, Reward, Order, StoryNode, etc.) and context manager that yields a session with automatic commit/rollback.
- **Aiogram Routers** (`handlers/__init__.py` and per-file `router = Router()`): One router per functional area (common, admin, gamification, store, narrative, etc.). Exported and included in the top-level `Dispatcher`.
- **Middlewares** (`middlewares/rate_limiter.py`, `middlewares/idempotency.py`, `middlewares/error_handler.py`): Aiogram middleware stack providing rate limiting (with admin bypass), callback deduplication, and centralized exception handling/logging.
- **`BotConfig`** (`config/settings.py`): Dataclass loaded from environment (BOT_TOKEN, ADMIN_IDS, DATABASE_URL, TIMEZONE, etc.).

## Directory structure rationale

The project uses a flat layout at the repository root (no `src/` package) chosen for simplicity in a single-process Telegram bot while enforcing strong architectural boundaries through naming and import conventions.

- `bot.py`: Single entry point. Wires the aiogram `Dispatcher`, registers all routers and middlewares, performs startup (DB init is a no-op; Alembic runs in deploy, scheduler start, EventBus listener registration, optional health server), and runs `dp.start_polling`.
- `handlers/`: All aiogram handlers and routers. Contains routing/validation logic (no direct DB access). Handler actions delegate to services (typically one via `get_service`; direct calls in some handlers). Organized by user vs. admin and by domain (gamification, store, narrative, etc.). Subdirectory `handlers/states/` holds FSM state classes.
- `services/`: All business logic, organized by domain. Services are the only place that may read/write models and coordinate via the EventBus. Several domains have their own `CLAUDE.md` for additional rules. Cross-cutting services live here too (event_bus, scheduler, health, analytics, fulfillment).
- `models/`: SQLAlchemy declarative models (`models.py`) and engine/session configuration + Alembic-aware `database.py`. No business logic lives in models. Schema evolution is exclusively via Alembic migrations under `alembic/versions/`.
- `middlewares/`: Aiogram-specific cross-cutting concerns (rate limiting, idempotency for callback retries, error handling). Registered in strict order in `bot.py`.
- `keyboards/`: Pure functions that build `InlineKeyboardMarkup` objects. Separated so UI structure can be reviewed independently of handlers.
- `utils/`: Shared utilities. `lucien_voice.py` is the canonical source of all user-facing text. Other helpers (admin checks, bot runtime clock) live here.
- `config/`: Environment-driven settings loaded once at import time. No secrets in code.
- `alembic/` + `alembic.ini`: Database schema migrations. `init_db()` in `models/database.py` is intentionally a no-op; all production schema work goes through `alembic upgrade head`.
- `tests/`: Unit, integration, handler, and e2e tests (pytest). Tests for services mock at the `get_service` boundary or use real `TestSession` patterns for atomicity contracts.
- `scripts/`: Operational and data scripts (health checks, seeding, simulations, migrations). Not part of the runtime bot.
- `docs/`: Project documentation (user guides, style guide, specs). The generated `ARCHITECTURE.md` lives here.

This structure directly supports the project's core rules: handlers are thin, services own behavior, models own data, and the EventBus + `get_service` context manager provide controlled extension points without violating layering or the 50-line function limit.

## Deployment notes

The production start command (see `railway.toml`) is `alembic upgrade head && python bot.py`. An optional separate HTTP health endpoint can be enabled via `HEALTH_ENABLED=1` and `HEALTH_PORT` (defaults to 8080) without interfering with aiogram polling. FSM storage is `RedisStorage` when `REDIS_URL` is present, otherwise `MemoryStorage`. Database is PostgreSQL in production (pool settings in `models/database.py`) and SQLite for local development. <!-- VERIFY: exact Railway project identifiers, health endpoint public URL if exposed, and production Redis cluster details -->
