# Config

Configuración global del bot.

## Archivos
- [settings.py](settings.py) - Configuración y variables de entorno

## Variables de Entorno

<!-- AUTO:ENV_VARS -->
```bash
# 
TOKEN=

# 
ADMIN_IDS=

# 
DATABASE_URL=

# 
TIMEZONE=

# 
CREATOR_USERNAME=

# 
WELCOME_FREE=

# 
ACCESS_APPROVED_FREE=

# 
WELCOME_VIP=

# 
VIP_ACTIVATED=

# 
RENEWAL_REMINDER=

# 
VIP_EXPIRED=

# 
TOKEN_INVALID=

# 
TOKEN_USED=

# 
TOKEN_EXPIRED=

# 
RATE_LIMIT_RATE=

# 
RATE_LIMIT_PERIOD=

# 
ADMIN_BYPASS=

```



## Acceso a Config
`from config.settings import settings

# Uso
bot_token = settings.BOT_TOKEN
admin_ids = settings.ADMIN_IDS`

## Reglas
- **NUNCA** hardcodear tokens o IDs
- Usar variables de entorno siempre
- No subir .env a git

## railway.toml
Configuración de despliegue en Railway.
