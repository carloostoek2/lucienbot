# Config

Configuración global del bot.

## Archivos
- `settings.py` — Tres dataclasses: `BotConfig`, `MessagesConfig`, `RateLimitConfig`

## BotConfig
```python
TOKEN: str                      # Bot token de @BotFather
ADMIN_IDS: list[int]            # IDs de Custodios (parseados de CSV env var)
DATABASE_URL: str               # sqlite:///... (dev) o postgresql://... (prod)
TIMEZONE: str                   # America/Mexico_City
CREATOR_USERNAME: str            # Username de Diana (sin @) para botón de contacto
```

## RateLimitConfig
```python
RATE_LIMIT_RATE: int = 5        # Requests por ventana
RATE_LIMIT_PERIOD: float = 10.0  # Ventana en segundos
ADMIN_BYPASS: bool = True      # Custodios ignoran rate limiting
```

## FSM Storage — Dev vs Prod

```python
# bot.py
if os.getenv("REDIS_URL"):
    storage = RedisStorage(Redis.from_url(os.getenv("REDIS_URL")),
                           key_builder=DefaultKeyBuilder(with_bot_id=True))
else:
    storage = MemoryStorage()
```

| Variable | Storage | Uso |
|----------|---------|-----|
| Sin `REDIS_URL` | `MemoryStorage` | Desarrollo local |
| Con `REDIS_URL` | `RedisStorage` | Producción (FSM persistente) |

## Acceso a Config
```python
from config.settings import bot_config, rate_limit_config, messages_config

bot_config.TOKEN
bot_config.ADMIN_IDS
rate_limit_config.RATE_LIMIT_RATE
messages_config.WELCOME_FREE
```

## Reglas
- **NUNCA** hardcodear tokens o IDs
- Usar variables de entorno siempre
- No subir `.env` a git
