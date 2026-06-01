"""
Utilidades de administración — Lucien Bot

Función centralizada is_admin() para verificar si un usuario es Custodio.
"""
from config.settings import bot_config


def is_admin(user_id: int) -> bool:
    """Verifica si un usuario es administrador (Custodio)"""
    return user_id in bot_config.ADMIN_IDS
