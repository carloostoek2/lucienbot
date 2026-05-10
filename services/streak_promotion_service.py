"""
Streak Promotion Service - Lucien Bot

Gestiona promociones por racha de trivia: creacion, activacion, reclamo automatico
de codigos de descuento cuando un usuario alcanza una racha objetivo.
"""
import logging
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.models import (
    StreakPromotion,
    StreakPromotionLevel,
    StreakPromotionCode,
    StreakPromotionCodeStatus,
    StreakPromotionStatus,
    StreakPromotionRedemption,
)
from models.database import SessionLocal

logger = logging.getLogger(__name__)


class StreakPromotionService:
    """Servicio para gestion de promociones por racha de trivia."""

    def __init__(self, db: Session = None):
        self._owns_session = db is None
        self.db = db or SessionLocal()

    def _get_db(self) -> Session:
        """Obtiene la sesion de base de datos activa."""
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def close(self):
        """Cierra la sesion si fue creada por este servicio."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    def _generate_code(self, prefix: str = "SK") -> str:
        """Genera un codigo unico con prefijo y 12 caracteres hex aleatorios."""
        random_part = secrets.token_hex(6)
        return f"{prefix}-{random_part}"

    def _pre_generate_codes(self, level: StreakPromotionLevel, prefix: str = "SK"):
        """Genera todos los codigos para un nivel de promocion de forma anticipada."""
        count = level.codes_available
        db = self._get_db()
        generated = 0
        max_attempts = count * 3
        attempt = 0
        while generated < count and attempt < max_attempts:
            attempt = attempt + 1
            code_value = self._generate_code(prefix)
            code = StreakPromotionCode(
                level_id=level.id,
                code_value=code_value,
                status=StreakPromotionCodeStatus.AVAILABLE,
            )
            db.add(code)
            try:
                db.flush()
                generated = generated + 1
            except IntegrityError:
                db.rollback()
                logger.warning(
                    f"streak_promotion_service - _pre_generate_codes - "
                    f"level_id:{level.id} - code collision, retrying"
                )
        logger.info(
            f"streak_promotion_service - _pre_generate_codes - "
            f"level_id:{level.id} - count:{generated}"
        )

    def create_promotion(self, name: str, description: str, levels: list,
                         duration_mode: str, start_date=None, end_date=None,
                         duration_hours=None, category_id=None,
                         include_general=True, include_vip=False,
                         include_simple=True, created_by=None) -> StreakPromotion:
        """Crea una promocion por racha con niveles y codigos pre-generados."""
        db = self._get_db()
        promotion = StreakPromotion(
            name=name, description=description, duration_mode=duration_mode,
            start_date=start_date, end_date=end_date, duration_hours=duration_hours,
            category_id=category_id, include_general=include_general,
            include_vip=include_vip, include_simple=include_simple,
            created_by=created_by, status=StreakPromotionStatus.PENDING,
        )
        db.add(promotion)
        db.flush()
        for level_data in levels:
            level = StreakPromotionLevel(
                promotion_id=promotion.id,
                consecutive_required=level_data["consecutive_required"],
                discount_pct=level_data["discount_pct"],
                codes_available=level_data["codes_available"],
            )
            db.add(level)
            db.flush()
            self._pre_generate_codes(level)
        db.commit()
        db.refresh(promotion)
        logger.info(f"streak_promotion_service - create_promotion - name:{name} - levels:{len(levels)}")
        return promotion

    def get_promotion(self, promo_id: int) -> Optional[StreakPromotion]:
        """Obtiene una promocion por su ID."""
        db = self._get_db()
        return db.query(StreakPromotion).filter(StreakPromotion.id == promo_id).first()

    def get_all_promotions(self) -> list[StreakPromotion]:
        """Retorna todas las promociones ordenadas por creacion descendente."""
        db = self._get_db()
        return (
            db.query(StreakPromotion)
            .order_by(StreakPromotion.created_at.desc())
            .all()
        )

    def get_active_promotions(
        self, game_type: str = None, category_id: str = None
    ) -> list[StreakPromotion]:
        """Retorna promociones activas, opcionalmente filtradas por tipo y categoria."""
        db = self._get_db()
        query = db.query(StreakPromotion).filter(
            StreakPromotion.is_active == True,
            StreakPromotion.status == StreakPromotionStatus.ACTIVE,
        )
        if game_type:
            game_map = {
                "trivia": StreakPromotion.include_general,
                "trivia_vip": StreakPromotion.include_vip,
                "trivia_simple": StreakPromotion.include_simple,
            }
            column = game_map.get(game_type)
            if column is not None:
                query = query.filter(column == True)
        if category_id:
            query = query.filter(StreakPromotion.category_id == category_id)
        return query.all()

    def _has_claimed_level(self, user_id: int, level_id: int) -> bool:
        """Verifica si un usuario ya canjeo el nivel de promocion."""
        db = self._get_db()
        existing = (
            db.query(StreakPromotionRedemption)
            .filter(
                StreakPromotionRedemption.user_id == user_id,
                StreakPromotionRedemption.level_id == level_id,
            )
            .with_for_update()
            .first()
        )
        return existing is not None

    def _get_available_code(
        self, level_id: int
    ) -> Optional[StreakPromotionCode]:
        """Obtiene un codigo disponible para el nivel dado."""
        db = self._get_db()
        return (
            db.query(StreakPromotionCode)
            .filter(
                StreakPromotionCode.level_id == level_id,
                StreakPromotionCode.status == StreakPromotionCodeStatus.AVAILABLE,
            )
            .with_for_update()
            .first()
        )

    def claim_for_streak(self, user_id: int, game_type: str, streak: int,
                         category_id: str = None) -> Optional[dict]:
        """Reclama un codigo de descuento cuando el usuario alcanza una racha objetivo."""
        db = self._get_db()
        promotions = self.get_active_promotions(game_type, category_id)
        for promo in promotions:
            for level in promo.levels:
                if level.consecutive_required != streak:
                    continue
                if self._has_claimed_level(user_id, level.id):
                    continue
                code = self._get_available_code(level.id)
                if not code:
                    continue
                code.status = StreakPromotionCodeStatus.DELIVERED
                code.user_id = user_id
                code.delivered_at = datetime.utcnow()
                redemption = StreakPromotionRedemption(
                    user_id=user_id, level_id=level.id, code_id=code.id,
                    streak_achieved=streak,
                )
                db.add(redemption)
                db.commit()
                logger.info(f"streak_promotion_service - claim_for_streak - user:{user_id} - game_type:{game_type} - streak:{streak} - result:claimed")
                return {
                    "code": code.code_value,
                    "discount_pct": level.discount_pct,
                    "promotion_name": promo.name,
                }
        logger.info(f"streak_promotion_service - claim_for_streak - user:{user_id} - game_type:{game_type} - streak:{streak} - result:none")
        return None

    def activate(self, promo_id: int) -> bool:
        """Activa una promocion y su categoria asociada si existe."""
        db = self._get_db()
        promotion = (
            db.query(StreakPromotion)
            .filter(StreakPromotion.id == promo_id)
            .first()
        )
        if not promotion:
            logger.warning(
                f"streak_promotion_service - activate - "
                f"promo_id:{promo_id} - not_found"
            )
            return False

        promotion.is_active = True
        promotion.status = StreakPromotionStatus.ACTIVE

        if promotion.category_id:
            from services.trivia_service import TriviaCategoryService

            TriviaCategoryService(db).activate(
                category_id=promotion.category_id,
                display_name=promotion.name,
            )

        db.commit()
        logger.info(
            f"streak_promotion_service - activate - "
            f"promo_id:{promo_id} - activated"
        )
        return True

    def deactivate(self, promo_id: int) -> bool:
        """Desactiva una promocion y su categoria si no hay otras activas usandola."""
        db = self._get_db()
        promotion = (
            db.query(StreakPromotion)
            .filter(StreakPromotion.id == promo_id)
            .first()
        )
        if not promotion:
            logger.warning(
                f"streak_promotion_service - deactivate - "
                f"promo_id:{promo_id} - not_found"
            )
            return False

        promotion.is_active = False
        promotion.status = StreakPromotionStatus.EXPIRED

        if promotion.category_id:
            other_active = (
                db.query(StreakPromotion)
                .filter(
                    StreakPromotion.id != promo_id,
                    StreakPromotion.category_id == promotion.category_id,
                    StreakPromotion.is_active == True,
                    StreakPromotion.status == StreakPromotionStatus.ACTIVE,
                )
                .first()
            )
            if not other_active:
                from services.trivia_service import TriviaCategoryService

                TriviaCategoryService(db).deactivate(
                    category_id=promotion.category_id
                )

        db.commit()
        logger.info(
            f"streak_promotion_service - deactivate - "
            f"promo_id:{promo_id} - deactivated"
        )
        return True

    def delete_promotion(self, promo_id: int) -> bool:
        """Elimina una promocion permanentemente. Los niveles, codigos
        y redenciones se eliminan en cascada."""
        db = self._get_db()
        promotion = (
            db.query(StreakPromotion)
            .filter(StreakPromotion.id == promo_id)
            .first()
        )
        if not promotion:
            logger.warning(
                f"streak_promotion_service - delete_promotion - "
                f"promo_id:{promo_id} - not_found"
            )
            return False

        db.delete(promotion)
        db.commit()

        try:
            from services.scheduler_service import get_scheduler

            scheduler = get_scheduler()
            if scheduler:
                scheduler.remove_streak_promotion_jobs(promo_id)
        except Exception as e:
            logger.warning(
                f"streak_promotion_service - delete_promotion - "
                f"promo_id:{promo_id} - failed to remove jobs: {e}"
            )

        logger.info(
            f"streak_promotion_service - delete_promotion - "
            f"promo_id:{promo_id} - deleted"
        )
        return True

    def pause_promotion(self, promo_id: int) -> bool:
        """Pausa una promocion temporalmente."""
        db = self._get_db()
        promotion = (
            db.query(StreakPromotion)
            .filter(StreakPromotion.id == promo_id)
            .first()
        )
        if not promotion:
            logger.warning(
                f"streak_promotion_service - pause_promotion - "
                f"promo_id:{promo_id} - not_found"
            )
            return False

        promotion.status = StreakPromotionStatus.PAUSED
        promotion.is_active = False
        db.commit()
        logger.info(
            f"streak_promotion_service - pause_promotion - "
            f"promo_id:{promo_id} - paused"
        )
        return True

    def get_redemption_stats(self, promo_id: int) -> dict:
        """Retorna estadisticas de canje por nivel para una promocion."""
        db = self._get_db()
        promotion = (
            db.query(StreakPromotion)
            .filter(StreakPromotion.id == promo_id)
            .first()
        )
        if not promotion:
            return {}

        stats = []
        for level in promotion.levels:
            total_codes = len(level.codes)
            delivered = sum(
                1
                for c in level.codes
                if c.status == StreakPromotionCodeStatus.DELIVERED
            )
            redemptions = (
                db.query(StreakPromotionRedemption)
                .filter(StreakPromotionRedemption.level_id == level.id)
                .all()
            )
            stats.append(
                {
                    "level_id": level.id,
                    "consecutive_required": level.consecutive_required,
                    "discount_pct": level.discount_pct,
                    "total_codes": total_codes,
                    "delivered_count": delivered,
                    "remaining": total_codes - delivered,
                    "redemptions": [
                        {
                            "user_id": r.user_id,
                            "streak_achieved": r.streak_achieved,
                            "redeemed_at": r.redeemed_at.isoformat()
                            if r.redeemed_at
                            else None,
                        }
                        for r in redemptions
                    ],
                }
            )

        return {"promo_id": promo_id, "levels": stats}

    def get_user_redemptions(
        self, user_id: int, promo_id: int = None
    ) -> list[StreakPromotionRedemption]:
        """Retorna las redenciones de un usuario, opcionalmente filtradas por promocion."""
        db = self._get_db()
        query = db.query(StreakPromotionRedemption).filter(
            StreakPromotionRedemption.user_id == user_id
        )
        if promo_id:
            query = query.join(StreakPromotionLevel).filter(
                StreakPromotionLevel.promotion_id == promo_id
            )
        return query.order_by(StreakPromotionRedemption.redeemed_at.desc()).all()
