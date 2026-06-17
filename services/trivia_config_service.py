"""
Servicio de Configuracion de Trivia - Lucien Bot

Gestiona la configuracion de limites diarios de minijuegos (dados, trivia).
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.models import TriviaConfig

logger = logging.getLogger(__name__)

# Valores por defecto (fallback si no hay row en BD)
DEFAULTS = {
    "dice_limit_free": 10,
    "dice_limit_vip": 20,
    "trivia_limit_free": 5,
    "trivia_limit_vip": 10,
    "trivia_vip_limit": 5,
    "trivia_simple_limit_free": 5,
    "trivia_simple_limit_vip": 10,
    # Límites de besitos ganados por trivia (diario y semanal)
    "trivia_besitos_daily_free": 10,
    "trivia_besitos_daily_vip": 15,
    "trivia_besitos_weekly_free": 30,
    "trivia_besitos_weekly_vip": 40,
}


class TriviaConfigService:
    """Servicio para gestion de configuracion de limites de trivia"""

    def __init__(self, db: Session = None):
        self.db = db
        self._owns_session = db is None

    def _get_db(self) -> Session:
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def close(self):
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    def get_config(self) -> dict:
        """Obtiene la configuracion actual de limites, creandola con defaults si no existe."""
        db = self._get_db()
        config = db.query(TriviaConfig).first()
        if not config:
            config = TriviaConfig(**DEFAULTS)
            db.add(config)
            db.commit()
            db.refresh(config)
            logger.info("TriviaConfig creada con valores por defecto")
        return {
            "dice_limit_free": config.dice_limit_free,
            "dice_limit_vip": config.dice_limit_vip,
            "trivia_limit_free": config.trivia_limit_free,
            "trivia_limit_vip": config.trivia_limit_vip,
            "trivia_vip_limit": config.trivia_vip_limit,
            "trivia_simple_limit_free": config.trivia_simple_limit_free,
            "trivia_simple_limit_vip": config.trivia_simple_limit_vip,
            "trivia_besitos_daily_free": config.trivia_besitos_daily_free,
            "trivia_besitos_daily_vip": config.trivia_besitos_daily_vip,
            "trivia_besitos_weekly_free": config.trivia_besitos_weekly_free,
            "trivia_besitos_weekly_vip": config.trivia_besitos_weekly_vip,
        }

    def update_config(self, admin_id: int, **kwargs) -> dict:
        """Actualiza los limites especificados. Solo actualiza los campos provistos."""
        db = self._get_db()
        config = db.query(TriviaConfig).first()
        if not config:
            config = TriviaConfig(**DEFAULTS)
            db.add(config)

        valid_fields = set(DEFAULTS.keys())
        for key, value in kwargs.items():
            if key in valid_fields and isinstance(value, int) and value >= 0:
                setattr(config, key, value)

        config.updated_by = admin_id
        config.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(config)
        logger.info(f"TriviaConfig actualizada por admin {admin_id}: {kwargs}")
        return self.get_config()
