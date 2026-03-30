# Config

Configuración global del bot.

## Archivos
- [settings.py](settings.py) - Configuración y variables de entorno

## Variables de Entorno

```bash
# Token del Bot de Telegram
BOT_TOKEN=your_bot_token_here

# IDs de administradores (separados por comas)
ADMIN_IDS=123456789,987654321

# Base de datos
DATABASE_URL=sqlite:///lucien_bot.db
# PostgreSQL para producción:
# DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Zona horaria
TIMEZONE=America/Mexico_City

# Username de la creadora
CREATOR_USERNAME=dianita

# Canales
VIP_CHANNEL_ID=@divan_de_diana
FREE_CHANNEL_ID=@senorita_kinky_free
```

## Acceso a Config
```python
from config.settings import settings

# Uso
bot_token = settings.BOT_TOKEN
admin_ids = settings.ADMIN_IDS
```

## Reglas
- **NUNCA** hardcodear tokens o IDs
- Usar variables de entorno siempre
- No subir .env a git

## railway.toml
Configuración de despliegue en Railway.
