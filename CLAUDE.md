# Lucien Bot

Telegram bot gamificado para la comunidad de Señorita Kinky (Diana Hernández).

## Quick Commands
```bash
python bot.py                    # Iniciar bot
```

## Arquitectura
```
handlers/ → services/ → models/ → database
```
- **handlers/**: Solo enrutan eventos, SIN lógica de negocio
- **services/**: Lógica de negocio por dominio (un service = un dominio)
- **models/**: Entidades y acceso a DB

## Dominios
Cada dominio tiene su propio CLAUDE.md con contexto específico:

| Dominio | Service | Carpeta |
|---------|---------|---------|
| Gamificación | besito_service.py, daily_gift_service.py | [@services/besito_service.py] |
| Missions | mission_service.py, reward_service.py | [@services/mission_service.py] |
| Store | store_service.py, package_service.py | [@services/store_service.py] |
| Promotions | promotion_service.py | [@services/promotion_service.py] |
| VIP | vip_service.py | [@services/vip_service.py] |
| Narrative | story_service.py | [@services/story_service.py] |
| Users | user_service.py | [@services/user_service.py] |
| Channels | channel_service.py | [@services/channel_service.py] |
| Broadcast | broadcast_service.py | [@handlers/broadcast_handlers.py] |

## Documentos de Referencia
- [@architecture.md] - Reglas de arquitectura (CAPAS PROHIBIDAS)
- [@rules.md] - Reglas del sistema (50 líneas máx, sin lógica en handlers)
- [@decisions.md] - Decisiones técnicas
- [@AGENTS.md] - Documentación técnica completa

## Reglas Críticas
1. **PROHIBIDO** lógica en handlers
2. **PROHIBIDO** acceso a DB fuera de models
3. **PROHIBIDO** duplicación entre services
4. Funciones máximo 50 líneas
5. Nombrar: verbo + contexto + resultado

## Voz de Lucien
- Habla en 3ra persona ("Lucien gestiona...")
- Elegante, misterioso, nunca vulgar
- "Diana" como figura central
- "Visitantes" no "usuarios"
- "Custodios" no "admins"

## Seguridad
- Validar IDs de callback
- Verificar permisos admin
- Verificar saldos antes de transacciones
- Usar transacciones en BD

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Lucien Bot**

Telegram bot gamificado para la comunidad de Señorita Kinky (Diana Hernández). Gestiona suscripciones VIP, canales de contenido, un sistema de gamificación con besitos, misiones, tienda virtual, promociones y narrativa interactiva con arquetipos de personajes.

**Core Value:** Crear una experiencia premium y gamificada que incentiva el compromiso de la comunidad con Diana a través de un sistema de recompensas, acceso exclusivo VIP y narrativa inmersiva.

### Constraints

- **Tech stack**: Python 3.12+, aiogram 3.x, SQLAlchemy 2.0 — no cambiar sin razón
- **Arquitectura**: Capas handlers/services/models estrictas — sin lógica de negocio en handlers
- **Voz de Lucien**: Siempre en 3ra persona, elegante y misterioso, "Diana" como figura central
- **DB**: SQLite local / PostgreSQL en Railway — compatible SQLAlchemy
- **Sin tests**: Prioridad alta pero no bloqueante para features
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12+ - All application code
- SQL (via SQLAlchemy) - Database queries
## Runtime
- Python 3.12 (detected from venv)
- pip
- Lockfile: `requirements.txt` present (no `requirements.lock` or `pyproject.toml`)
## Frameworks
- aiogram 3.4.1 - Telegram Bot API framework (async-first)
- SQLAlchemy 2.0.28 - ORM and database abstraction
- python-dotenv 1.0.1 - Environment variable loading from `.env`
- pytz 2024.1 - Timezone handling
- Not detected (no test framework in requirements.txt)
- Not detected (no build tools configured)
## Key Dependencies
- aiogram 3.4.1 - Core bot framework, provides Router, Dispatcher, FSM, Bot classes
- SQLAlchemy 2.0.28 - Data persistence layer, all models use SQLAlchemy ORM
- python-dotenv 1.0.1 - Configuration management via `.env` files
- pytz 2024.1 - Timezone-aware datetime handling for scheduling
- asyncio - Async runtime (built-in)
- logging - Logging framework (built-in)
- dataclasses - Configuration dataclasses (built-in)
- secrets, string - Token generation (built-in)
- enum - Enumerations for types (built-in)
## Configuration
- `.env` file loaded via `python-dotenv`
- Required variables:
- No build configuration detected
- Direct Python execution: `python bot.py`
## Platform Requirements
- Python 3.9+ (README states 3.9+, venv uses 3.12)
- Virtual environment recommended
- `.env` file with valid bot token
- Deployment target: Self-hosted (no cloud platform detected)
- Process manager: Not configured (would need systemd/supervisor for production)
- Database: SQLite by default (`lucien_bot.db`), PostgreSQL-compatible via SQLAlchemy
## Database
- SQLite (default) - `sqlite:///lucien_bot.db`
- Configurable via `DATABASE_URL` environment variable
- SQLAlchemy 2.0.28 with declarative base
- Session-per-request pattern in services
- Manual session management (no async SQLAlchemy)
## External APIs
- aiogram 3.4.1 as client
- Long polling method (no webhook configured)
- Features used:
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Separation of concerns across handlers, services, and models
- Router-based message handling via aiogram 3.x
- Centralized scheduler for background tasks
- Service layer encapsulates business logic
- SQLAlchemy ORM for data persistence
## Layers
- Purpose: Bot initialization and event loop management
- Location: `bot.py`
- Contains: Bot/Dispatcher setup, router registration, startup/shutdown hooks
- Depends on: All handler routers, config, database init
- Used by: System entry point
- Purpose: Process Telegram updates (messages, callbacks, commands)
- Location: `handlers/`
- Contains: Route handlers, FSM state management, inline keyboard callbacks
- Depends on: Services, keyboards, utils
- Used by: aiogram Dispatcher
- Purpose: Business logic and data operations
- Location: `services/`
- Contains: Domain services (VIP, channels, besitos, missions, etc.)
- Depends on: Models, database session
- Used by: Handlers
- Purpose: Data persistence and ORM mappings
- Location: `models/`
- Contains: SQLAlchemy models, database configuration
- Depends on: SQLAlchemy
- Used by: Services
- Purpose: Shared helpers and personality/voice
- Location: `utils/`, `keyboards/`, `config/`
- Contains: LucienVoice messages, inline keyboards, settings
- Depends on: None (or minimal)
- Used by: Handlers, Services
## Data Flow
- aiogram FSM (Finite State Machine) with memory storage
- States defined in handler files as `StatesGroup` classes
- State context stored in `MemoryStorage` (non-persistent)
- Example: `TariffStates` in `handlers/vip_handlers.py` for multi-step tariff creation
## Key Abstractions
- Purpose: aiogram v3 message routing mechanism
- Examples: `handlers/common_handlers.py`, `handlers/admin_handlers.py`
- Pattern: Each module exports `router = Router()` which is imported in `bot.py`
- Purpose: Encapsulate business logic for a domain
- Examples: `services/vip_service.py`, `services/channel_service.py`, `services/besito_service.py`
- Pattern: Class with CRUD methods, accepts optional `Session` for dependency injection
- Purpose: Centralize bot personality and messaging tone
- Location: `utils/lucien_voice.py`
- Pattern: Static methods returning formatted HTML strings with consistent persona
- Purpose: Interactive button interfaces for conversations
- Location: `keyboards/inline_keyboards.py`
- Pattern: Functions return `InlineKeyboardMarkup` with callback data routing
## Entry Points
- Location: `bot.py`
- Triggers: Script execution (`python bot.py`)
- Responsibilities:
- Location: `bot.py::on_startup()`
- Triggers: Dispatcher startup event
- Responsibilities:
- Location: `bot.py::on_shutdown()`
- Triggers: Dispatcher shutdown event
- Responsibilities:
## Error Handling
- Service methods return `None` or `(result, None)` / `(None, error_code)` tuples
- Handlers catch exceptions and display `LucienVoice.error_message()`
- Database rollbacks on service errors via explicit `db.rollback()`
- Scheduler continues loop on individual task failures
```python
```
## Cross-Cutting Concerns
- Python stdlib `logging` module
- Configured in `bot.py` with file and console handlers
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Log file: `lucien_bot.log`
- Admin validation via `is_admin()` helper checking `bot_config.ADMIN_IDS`
- Token validation in `VIPService.validate_token()`
- FSM states for multi-step forms
- Telegram user ID-based authentication
- Admin IDs loaded from `ADMIN_IDS` environment variable
- No session-based auth; relies on Telegram identity
- Environment variables via `python-dotenv`
- Dataclass-based config in `config/settings.py`
- Loaded once at startup
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
