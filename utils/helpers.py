"""
Helpers - Lucien Bot

Funciones auxiliares para el bot.
"""
from datetime import datetime
from typing import Optional
import pytz
from config.settings import bot_config


def get_current_time() -> datetime:
    """Obtiene la hora actual en la zona horaria configurada"""
    tz = pytz.timezone(bot_config.TIMEZONE)
    return datetime.now(tz)


def format_datetime(dt: datetime, format_str: str = "%d/%m/%Y %H:%M") -> str:
    """Formatea una fecha/hora"""
    if dt is None:
        return "N/A"
    return dt.strftime(format_str)


def escape_markdown(text: str) -> str:
    """Escapa caracteres especiales de Markdown"""
    chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in chars:
        text = text.replace(char, f'\\{char}')
    return text


def truncate_text(text: str, max_length: int = 4000) -> str:
    """Trunca texto si excede el límite"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def generate_invite_link(bot_username: str, token: str) -> str:
    """Genera enlace de invitación con token"""
    return f"https://t.me/{bot_username}?start={token}"


def is_admin(user_id: int) -> bool:
    """Verifica si un usuario es administrador"""
    return user_id in bot_config.ADMIN_IDS


def parse_duration(text: str) -> Optional[int]:
    """
    Parsea una duración en texto a días.
    Soporta: '30 dias', '1 mes', '1 año', etc.
    """
    text = text.lower().strip()
    
    try:
        # Intentar extraer número directo
        return int(text)
    except ValueError:
        pass
    
    # Mapeo de palabras clave
    if any(word in text for word in ['mes', 'month']):
        return 30
    if any(word in text for word in ['trimestre', 'quarter']):
        return 90
    if any(word in text for word in ['semestre', 'semester']):
        return 180
    if any(word in text for word in ['año', 'year', 'anual', 'annual']):
        return 365
    if any(word in text for word in ['semana', 'week']):
        return 7
    if any(word in text for word in ['dia', 'day']):
        # Extraer número antes de "dia"
        import re
        match = re.search(r'(\d+)\s*d', text)
        if match:
            return int(match.group(1))
    
    return None
