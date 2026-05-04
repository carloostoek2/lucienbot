"""
Servicio de Configuración de Trivia - Lucien Bot

Gestiona la configuración editable de límites de intentos de trivia.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from models.models import TriviaConfig
from models.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class TriviaConfigService:
    """Servicio para gestión de configuración de trivia"""

    def __init__(self, db: Session = None):
        self.db = db
        self._owns_session = db is None

    def _get_db(self) -> Session:
        """Obtiene la sesión de base de datos activa, inicializando lazily si es necesario."""
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def close(self):
        """Cierra la sesión de base de datos si fue creada por este servicio."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    def __del__(self):
        """Cierra la sesión de base de datos"""
        self.close()

    def get_config(self) -> TriviaConfig:
        """Obtiene la configuración de trivia (singleton). Crea con defaults si no existe."""
        db = self._get_db()
        config = db.query(TriviaConfig).first()
        if not config:
            config = TriviaConfig(
                daily_trivia_limit_free=7,
                daily_trivia_limit_vip=15,
                daily_trivia_vip_limit=5,
                is_active=True
            )
            db.add(config)
            db.commit()
            db.refresh(config)
            logger.info("trivia_config_service - get_config - created default config")
        return config

    def update_config(
        self,
        daily_trivia_limit_free: int,
        daily_trivia_limit_vip: int,
        daily_trivia_vip_limit: int,
        admin_id: int = None
    ) -> TriviaConfig:
        """Actualiza la configuración de trivia"""
        config = self.get_config()
        config.daily_trivia_limit_free = daily_trivia_limit_free
        config.daily_trivia_limit_vip = daily_trivia_limit_vip
        config.daily_trivia_vip_limit = daily_trivia_vip_limit
        config.updated_by = admin_id
        config.updated_at = datetime.utcnow()
        self._get_db().commit()
        logger.info(
            f"trivia_config_service/update_config - admin={admin_id} - "
            f"free={daily_trivia_limit_free}, vip={daily_trivia_limit_vip}, "
            f"vip_exclusive={daily_trivia_vip_limit}"
        )
        return config

    def get_limits_for_user(self, is_vip: bool) -> dict:
        """Retorna límites según tipo de usuario"""
        config = self.get_config()
        return {
            'trivia_limit': config.daily_trivia_limit_vip if is_vip else config.daily_trivia_limit_free,
            'trivia_vip_limit': config.daily_trivia_vip_limit
        }
