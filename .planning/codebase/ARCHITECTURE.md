# Architecture

**Analysis Date:** 2026-03-29

## Pattern Overview

**Overall:** Layered Architecture with Event-Driven Bot Pattern

**Key Characteristics:**
- Separation of concerns across handlers, services, and models
- Router-based message handling via aiogram 3.x
- Centralized scheduler for background tasks
- Service layer encapsulates business logic
- SQLAlchemy ORM for data persistence

## Layers

**Entry Point Layer:**
- Purpose: Bot initialization and event loop management
- Location: `bot.py`
- Contains: Bot/Dispatcher setup, router registration, startup/shutdown hooks
- Depends on: All handler routers, config, database init
- Used by: System entry point

**Handler Layer (aiogram Routers):**
- Purpose: Process Telegram updates (messages, callbacks, commands)
- Location: `handlers/`
- Contains: Route handlers, FSM state management, inline keyboard callbacks
- Depends on: Services, keyboards, utils
- Used by: aiogram Dispatcher

**Service Layer:**
- Purpose: Business logic and data operations
- Location: `services/`
- Contains: Domain services (VIP, channels, besitos, missions, etc.)
- Depends on: Models, database session
- Used by: Handlers

**Model Layer:**
- Purpose: Data persistence and ORM mappings
- Location: `models/`
- Contains: SQLAlchemy models, database configuration
- Depends on: SQLAlchemy
- Used by: Services

**Utility Layer:**
- Purpose: Shared helpers and personality/voice
- Location: `utils/`, `keyboards/`, `config/`
- Contains: LucienVoice messages, inline keyboards, settings
- Depends on: None (or minimal)
- Used by: Handlers, Services

## Data Flow

**User Command Flow:**

1. User sends message/command to Telegram bot
2. Telegram API delivers update to bot via polling
3. `bot.py` Dispatcher routes to appropriate handler in `handlers/`
4. Handler validates user (admin check if needed)
5. Handler calls service layer for business logic
6. Service queries/updates database via SQLAlchemy models
7. Service returns result to handler
8. Handler constructs response using `LucienVoice` for tone
9. Handler sends response via aiogram Bot

**VIP Subscription Flow:**

1. Admin creates tariff via `admin_handlers.py` → `VIPService.create_tariff()`
2. Admin generates token via `vip_handlers.py` → `VIPService.generate_token()`
3. User clicks token link (`?start=TOKEN_CODE`)
4. `vip_handlers.py` validates token via `VIPService.validate_token()`
5. Token redeemed, subscription created with expiry date
6. Scheduler checks expiring subscriptions every 30 seconds
7. 24h before expiry: reminder sent via `SchedulerService._process_expiring_subscriptions()`
8. At expiry: user removed from channel via `SchedulerService._process_expired_subscriptions()`

**Free Channel Approval Flow:**

1. User requests to join Free channel
2. `channel_handlers.py` intercepts join request
3. `ChannelService.create_pending_request()` schedules approval time
4. User notified of wait time
5. `SchedulerService._process_pending_requests()` runs every 30 seconds
6. When `scheduled_approval_at <= now`, bot approves request via Telegram API
7. User notified of approval

**State Management:**
- aiogram FSM (Finite State Machine) with memory storage
- States defined in handler files as `StatesGroup` classes
- State context stored in `MemoryStorage` (non-persistent)
- Example: `TariffStates` in `handlers/vip_handlers.py` for multi-step tariff creation

## Key Abstractions

**Router:**
- Purpose: aiogram v3 message routing mechanism
- Examples: `handlers/common_handlers.py`, `handlers/admin_handlers.py`
- Pattern: Each module exports `router = Router()` which is imported in `bot.py`

**Service:**
- Purpose: Encapsulate business logic for a domain
- Examples: `services/vip_service.py`, `services/channel_service.py`, `services/besito_service.py`
- Pattern: Class with CRUD methods, accepts optional `Session` for dependency injection

**Voice:**
- Purpose: Centralize bot personality and messaging tone
- Location: `utils/lucien_voice.py`
- Pattern: Static methods returning formatted HTML strings with consistent persona

**Inline Keyboard:**
- Purpose: Interactive button interfaces for conversations
- Location: `keyboards/inline_keyboards.py`
- Pattern: Functions return `InlineKeyboardMarkup` with callback data routing

## Entry Points

**Main Bot Entry:**
- Location: `bot.py`
- Triggers: Script execution (`python bot.py`)
- Responsibilities:
  - Load configuration from `.env`
  - Initialize database tables
  - Create aiogram Bot and Dispatcher
  - Register all routers
  - Start polling loop
  - Handle startup/shutdown events

**Startup Hook:**
- Location: `bot.py::on_startup()`
- Triggers: Dispatcher startup event
- Responsibilities:
  - Initialize database via `init_db()`
  - Start scheduler via `get_scheduler(bot).start()`
  - Notify admins of bot availability

**Shutdown Hook:**
- Location: `bot.py::on_shutdown()`
- Triggers: Dispatcher shutdown event
- Responsibilities:
  - Stop scheduler
  - Notify admins of bot shutdown

## Error Handling

**Strategy:** Try-except with logging and user-friendly messages

**Patterns:**
- Service methods return `None` or `(result, None)` / `(None, error_code)` tuples
- Handlers catch exceptions and display `LucienVoice.error_message()`
- Database rollbacks on service errors via explicit `db.rollback()`
- Scheduler continues loop on individual task failures

Example from `handlers/vip_handlers.py`:
```python
try:
    token = vip_service.generate_token(tariff_id)
    # ...
except Exception as e:
    logger.error(f"Error generando token: {e}")
    await callback.message.edit_text(
        LucienVoice.error_message("la generación del token"),
        ...
    )
```

## Cross-Cutting Concerns

**Logging:**
- Python stdlib `logging` module
- Configured in `bot.py` with file and console handlers
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Log file: `lucien_bot.log`

**Validation:**
- Admin validation via `is_admin()` helper checking `bot_config.ADMIN_IDS`
- Token validation in `VIPService.validate_token()`
- FSM states for multi-step forms

**Authentication:**
- Telegram user ID-based authentication
- Admin IDs loaded from `ADMIN_IDS` environment variable
- No session-based auth; relies on Telegram identity

**Configuration:**
- Environment variables via `python-dotenv`
- Dataclass-based config in `config/settings.py`
- Loaded once at startup

---

*Architecture analysis: 2026-03-29*
