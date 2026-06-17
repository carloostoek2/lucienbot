"""
Utilidades de administración — Lucien Bot

Función centralizada is_admin() para verificar si un usuario es Custodio.
"""
import logging

from config.settings import bot_config

logger = logging.getLogger(__name__)


def _is_admin_in_db(user_id: int) -> bool:
    """Verifica role=admin en base de datos (respaldo de ADMIN_IDS)."""
    from services.user_service import UserService

    user_service = UserService()
    try:
        return user_service.is_admin(user_id)
    except Exception as exc:
        logger.warning(
            "admin | is_admin_db_check | user_id=%s | result=error %s",
            user_id,
            exc,
        )
        return False
    finally:
        user_service.close()


def is_admin(user_id: int) -> bool:
    """Verifica si un usuario es administrador (Custodio).

    Fuente de verdad dual:
    1. ADMIN_IDS (variables de entorno) — principal
    2. role=admin en base de datos — respaldo
    """
    if not isinstance(user_id, int):
        return False
    if user_id in bot_config.ADMIN_IDS:
        return True
    return _is_admin_in_db(user_id)