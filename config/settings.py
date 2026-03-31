"""
Configuración del Bot Lucien - Guardián de los Secretos de Diana
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BotConfig:
    """Configuración principal del bot"""
    TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: list = None
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///lucien_bot.db")
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Mexico_City")
    CREATOR_USERNAME: str = os.getenv("CREATOR_USERNAME", "")

    def __post_init__(self):
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        self.ADMIN_IDS = [int(id_str.strip()) for id_str in admin_ids_str.split(",") if id_str.strip()]


@dataclass
class MessagesConfig:
    """Mensajes configurables del sistema"""
    # Canal Free
    WELCOME_FREE: str = "Bienvenido al vestíbulo. Su solicitud ha sido registrada..."
    ACCESS_APPROVED_FREE: str = "Su acceso ha sido concedido. Diana lo espera."

    # Canal VIP
    WELCOME_VIP: str = "Bienvenido al círculo exclusivo."
    VIP_ACTIVATED: str = "Su membresía ha sido activada."
    RENEWAL_REMINDER: str = "Su acceso exclusivo vence mañana..."
    VIP_EXPIRED: str = "Su tiempo en el círculo íntimo ha concluido."

    # Errores
    TOKEN_INVALID: str = "El enlace proporcionado no es válido."
    TOKEN_USED: str = "Este enlace ya ha sido utilizado."
    TOKEN_EXPIRED: str = "Este enlace ha expirado."


@dataclass
class RateLimitConfig:
    """Configuración de rate limiting"""
    RATE_LIMIT_RATE: int = 5        # max requests per window
    RATE_LIMIT_PERIOD: float = 10.0 # seconds window
    ADMIN_BYPASS: bool = True       # skip throttling for Custodios


# Instancias globales
bot_config = BotConfig()
messages_config = MessagesConfig()
rate_limit_config = RateLimitConfig()
