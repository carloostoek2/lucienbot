"""
Bridge module — rompe el import circular entre scheduler_service y streak_promotion_service.

Este es el UNICO modulo que importa de ambos servicios (via lazy imports internos).
Tanto scheduler_service como streak_promotion_service importan desde aqui
con imports de nivel superior, eliminando el ciclo.
"""

import logging

from models.database import SessionLocal

logger = logging.getLogger(__name__)


async def activate_streak_promotion(promo_id: int):
    """Activa una promocion por racha en su fecha de inicio (DateTrigger job)."""
    from services.streak_promotion_service import StreakPromotionService

    db = SessionLocal()
    try:
        service = StreakPromotionService(db)
        service.activate(promo_id)
        logger.info(f"Bridge activated streak promotion: promo_id={promo_id}")
    except Exception as e:
        logger.error(f"Error activating streak promotion {promo_id}: {e}")
    finally:
        db.close()


async def deactivate_streak_promotion(promo_id: int):
    """Desactiva una promocion por racha en su fecha de expiracion (DateTrigger job)."""
    from services.streak_promotion_service import StreakPromotionService

    db = SessionLocal()
    try:
        service = StreakPromotionService(db)
        service.deactivate(promo_id)
        logger.info(f"Bridge deactivated streak promotion: promo_id={promo_id}")
    except Exception as e:
        logger.error(f"Error deactivating streak promotion {promo_id}: {e}")
    finally:
        db.close()


def remove_streak_promotion_jobs(promo_id: int):
    """Remueve jobs de activacion/desactivacion para una promocion por racha."""
    from services.scheduler_service import get_scheduler

    scheduler = get_scheduler()
    if scheduler:
        scheduler.remove_streak_promotion_jobs(promo_id)
