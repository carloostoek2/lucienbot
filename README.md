<!-- generated-by: gsd-doc-writer -->
# Lucien Bot

A gamified Telegram bot for the Señorita Kinky community that manages VIP subscriptions, content channels, besitos-based points, missions, virtual store, promotions, and interactive narrative.

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.24.0-green.svg)](https://docs.aiogram.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.28-orange.svg)](https://www.sqlalchemy.org/)
[![CI](https://github.com/carloostoek2/lucienbot/actions/workflows/ci.yml/badge.svg)](https://github.com/carloostoek2/lucienbot/actions/workflows/ci.yml)

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

1. Clone the repository and create a virtual environment:
   ```bash
   git clone https://github.com/carloostoek2/lucienbot.git
   cd lucienbot
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with BOT_TOKEN, ADMIN_IDS, and other required values
   ```

4. Run the bot:
   ```bash
   python bot.py
   ```

## Usage Examples

### Start the bot and view the main menu

Send `/start` to Lucien. The bot greets you and presents the main menu with options for balance, daily gift, store, missions, offers, and narrative fragments.

### Check your besitos balance

From the main menu, tap **💋 Mi saldo de besitos**. Lucien replies with your current balance, total earned, and total spent.

Example response:
```
🎩 Lucien:

Permíteme consultar los fragmentos de atención que ha acumulado...

💋 Tu saldo de besitos: 245

📊 Estadísticas:
   • Total acumulado: 1250
   • Total gastado: 1005

Diana aprecia cada momento de su atención...
```

### Claim the daily gift

Tap **🎁 Regalo diario** from the main menu. If eligible, you receive a random amount of besitos and any associated mission progress is recorded.

## Project Structure

```
lucienbot/
├── bot.py                 # Application entry point
├── config/
│   └── settings.py        # Environment-driven configuration
├── handlers/              # Event routers (no business logic)
├── services/              # Domain business logic
├── models/                # SQLAlchemy models and DB session
├── keyboards/             # Inline keyboard builders
├── middlewares/           # Rate limiting, idempotency, error handling
├── utils/                 # Helpers and Lucien voice templates
├── scripts/               # Operational scripts (health_check, seed, etc.)
├── tests/                 # Unit, integration, and e2e tests
├── pyproject.toml
├── requirements.txt
└── Makefile
```

## Key Features

- **Canales Free y VIP**: Automatic approval with wait time for free channels; token-based one-time access for VIP
- **Gamificación con besitos**: Credit/debit with atomic transactions, daily gifts, and reaction rewards
- **Misiones y Recompensas**: Recurring and one-time missions delivering besitos, packages, or VIP grants
- **Tienda Virtual**: Categorized catalog with stock management and direct purchase flows
- **Promociones**: "Me interesa" interest capture with admin notifications; streak-based promotions
- **Narrativa Interactiva**: Story nodes, choices, archetype quiz, and achievement tracking
- **Minijuegos**: Dice rolls and trivia with streak mechanics
- **Panel de Administración**: Full conversational admin UI for all domains
- **Observabilidad**: Health service and `/health` endpoint for runtime checks

## Requirements

- Python >= 3.12
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- Admin rights in channels to manage (for channel features)
- Optional: Redis for FSM persistence, PostgreSQL for production

## Configuration

Required environment variables (see `.env.example`):

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token |
| `ADMIN_IDS` | Comma-separated Telegram user IDs for custodians |
| `DATABASE_URL` | `sqlite:///lucien_bot.db` or `postgresql://...` |
| `TIMEZONE` | IANA timezone (default: `America/Mexico_City`) |
| `CREATOR_USERNAME` | Diana's username (without @) for contact buttons |

See `config/settings.py` and `DEPLOY.md` for additional options.

## Development

```bash
# Install dev dependencies and pre-commit
make install

# Run tests
make test

# Lint and format
make lint
make format

# Run locally
make run
```

## Deployment

The project includes configuration for Railway (see `railway.toml` and `Procfile`). On deploy, migrations run automatically:

```
alembic upgrade head && python bot.py
```

## Architecture Notes

Handlers contain only routing and call exactly one service method. All business logic lives in services under `services/`. Database access is confined to models. See `CLAUDE.md` and `architecture.md` for detailed rules and diagrams.

## Testing

Tests live under `tests/` with markers: `unit`, `integration`, `e2e`, `slow`. Coverage is enforced via pytest-cov (see `pyproject.toml` for thresholds and sources).

```bash
pytest tests/ -m "unit or integration"
```

## License

<!-- VERIFY: license type and LICENSE file location cannot be confirmed from repository contents -->
