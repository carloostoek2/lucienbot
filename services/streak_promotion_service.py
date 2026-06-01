"""
Streak Promotion Service - Lucien Bot

Gestiona promociones por racha de trivia: creacion, activacion, reclamo automatico
de codigos de descuento cuando un usuario alcanza una racha objetivo.
"""

import json
import logging
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from models.database import SessionLocal
from models.models import (
    StreakPromotion,
    StreakPromotionCode,
    StreakPromotionCodeStatus,
    StreakPromotionLevel,
    StreakPromotionRedemption,
    StreakPromotionStatus,
    StreakSession,
)
from services.streak_scheduler_bridge import remove_streak_promotion_jobs

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
                db.expunge(code)
                logger.warning(
                    f"streak_promotion_service - _pre_generate_codes - "
                    f"level_id:{level.id} - code collision, retrying"
                )
        logger.info(
            f"streak_promotion_service - _pre_generate_codes - "
            f"level_id:{level.id} - count:{generated}"
        )

    def create_promotion(
        self,
        name: str,
        description: str,
        levels: list,
        duration_mode: str,
        start_date=None,
        end_date=None,
        duration_hours=None,
        category_id=None,
        include_general=True,
        include_vip=False,
        include_simple=True,
        created_by=None,
    ) -> StreakPromotion:
        """Crea una promocion por racha con niveles y codigos pre-generados."""
        db = self._get_db()
        promotion = StreakPromotion(
            name=name,
            description=description,
            duration_mode=duration_mode,
            start_date=start_date,
            end_date=end_date,
            duration_hours=duration_hours,
            category_id=category_id,
            include_general=include_general,
            include_vip=include_vip,
            include_simple=include_simple,
            created_by=created_by,
            status=StreakPromotionStatus.PENDING,
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
        logger.info(
            f"streak_promotion_service - create_promotion - name:{name} - levels:{len(levels)}"
        )
        return promotion

    def get_promotion(self, promo_id: int) -> StreakPromotion | None:
        """Obtiene una promocion por su ID."""
        db = self._get_db()
        return (
            db.query(StreakPromotion)
            .options(joinedload(StreakPromotion.levels).joinedload(StreakPromotionLevel.codes))
            .filter(StreakPromotion.id == promo_id)
            .first()
        )

    def get_all_promotions(self) -> list[StreakPromotion]:
        """Retorna todas las promociones ordenadas por creacion descendente."""
        db = self._get_db()
        return (
            db.query(StreakPromotion)
            .options(joinedload(StreakPromotion.levels).joinedload(StreakPromotionLevel.codes))
            .order_by(StreakPromotion.created_at.desc())
            .all()
        )

    def get_active_promotions(
        self, game_type: str = None, category_id: str = None
    ) -> list[StreakPromotion]:
        """Retorna promociones activas, opcionalmente filtradas por tipo y categoria."""
        db = self._get_db()
        query = (
            db.query(StreakPromotion)
            .options(joinedload(StreakPromotion.levels).joinedload(StreakPromotionLevel.codes))
            .filter(
                StreakPromotion.is_active,
                StreakPromotion.status == StreakPromotionStatus.ACTIVE,
            )
        )
        if game_type:
            game_map = {
                "trivia": StreakPromotion.include_general,
                "trivia_vip": StreakPromotion.include_vip,
                "trivia_simple": StreakPromotion.include_simple,
            }
            column = game_map.get(game_type)
            if column is not None:
                query = query.filter(column)
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

    def _get_available_code(self, level_id: int) -> StreakPromotionCode | None:
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

    def claim_for_streak(
        self, user_id: int, game_type: str, streak: int, category_id: str = None
    ) -> dict | None:
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
                code.delivered_at = datetime.now(UTC)
                # Phase 18: Link code to active session
                session = self._get_or_create_session(user_id, promo.id)
                code.session_id = session.id
                codes_list = json.loads(session.codes_delivered or "[]")
                codes_list.append(code.id)
                session.codes_delivered = json.dumps(codes_list)
                redemption = StreakPromotionRedemption(
                    user_id=user_id,
                    level_id=level.id,
                    code_id=code.id,
                    streak_achieved=streak,
                )
                db.add(redemption)
                db.commit()
                logger.info(
                    f"streak_promotion_service - claim_for_streak - user:{user_id} - game_type:{game_type} - streak:{streak} - result:claimed"
                )
                return {
                    "code": code.code_value,
                    "discount_pct": level.discount_pct,
                    "promotion_name": promo.name,
                }
        logger.info(
            f"streak_promotion_service - claim_for_streak - user:{user_id} - game_type:{game_type} - streak:{streak} - result:none"
        )
        return None

    def calculate_protection_cost(self, streak: int) -> int:
        """Calcula el costo en besitos para proteger una racha.
        Formula: 5 + (streak // 3) * 5
        Ej: streak 0-2 -> 5, streak 3-5 -> 10, streak 6-8 -> 15
        """
        return 5 + (streak // 3) * 5

    def get_active_session(self, user_id: int) -> StreakSession | None:
        """Retorna la sesion activa de promociones del usuario, o None.
        NO filtra por expires_at=None para que las sesiones con timeout
        (expires_at futuro) sigan siendo visibles y se pueda verificar
        la expiracion en la logica posterior.
        """
        db = self._get_db()
        now = datetime.now(UTC).replace(tzinfo=None)
        session = (
            db.query(StreakSession)
            .filter(
                StreakSession.user_id == user_id,
            )
            .order_by(StreakSession.started_at.desc())
            .first()
        )
        if not session:
            return None
        if session.expires_at and now > session.expires_at:
            self.cancel_session_codes(session.id)
            # Inline expire set (was close_session) to prevent recursion:
            # close_session calls get_active_session which can re-trigger this
            # expired branch on boundary (now ~ expires_at set to 'now' in close).
            # This is defensive minimal fix for discovered cycle (get<->close).
            # close_session also logs; we log here for the auto-expire case.
            session.expires_at = datetime.now(UTC).replace(tzinfo=None)
            db.flush()
            db.commit()  # ensure side-effects (CANCELLED codes + expires) persist beyond current session (addresses flush-only visibility gap in auto-expire)
            logger.info(
                f"streak_promotion_service - get_active_session - "
                f"user:{user_id} - auto-closed expired session:{session.id}"
            )
            return None
        return session

    def _get_or_create_session(self, user_id: int, promotion_id: int) -> StreakSession:
        """Obtiene la sesion activa o crea una nueva."""
        db = self._get_db()
        session = self.get_active_session(user_id)
        if session:
            return session
        session = StreakSession(
            id=uuid.uuid4(),
            user_id=user_id,
            promotion_id=promotion_id,
            is_in_risk_mode=False,
            protection_used=False,
            codes_delivered="[]",
        )
        db.add(session)
        db.flush()
        logger.info(
            f"streak_promotion_service - _get_or_create_session - "
            f"user:{user_id} - promotion:{promotion_id} - created"
        )
        return session

    def protect_streak(self, user_id: int, streak: int) -> bool:
        """Protege una racha debitando besitos y marcando protection_used.
        Encapsula BesitoService debit + session update en un solo metodo atomico
        para que los handlers llamen exactamente 1 service.
        Retorna True si la proteccion fue aplicada, False si saldo insuficiente.
        """
        db = self._get_db()
        session = self.get_active_session(user_id)
        if not session:
            logger.warning(
                f"streak_promotion_service - protect_streak - user:{user_id} - no_active_session"
            )
            return False
        cost = self.calculate_protection_cost(streak)
        from models.models import TransactionSource
        from services.besito_service import BesitoService

        besito_service = BesitoService(db)
        if not besito_service.debit_besitos(
            user_id=user_id,
            amount=cost,
            source=TransactionSource.STREAK_PROTECTION,
            description=f"Proteccion de racha streak={streak}",
            commit=False,
        ):
            logger.info(
                f"streak_promotion_service - protect_streak - "
                f"user:{user_id} - insufficient_balance - cost:{cost}"
            )
            return False
        session.protection_used = True
        db.commit()
        logger.info(
            f"streak_promotion_service - protect_streak - "
            f"user:{user_id} - cost:{cost} - streak:{streak}"
        )
        return True

    def cancel_session_codes(self, session_id: uuid.UUID) -> int:
        """Marca todos los codigos DELIVERED de la sesion como CANCELLED.
        Retorna la cantidad de codigos cancelados.
        """
        db = self._get_db()
        session = db.query(StreakSession).filter(StreakSession.id == session_id).first()
        if not session:
            return 0
        code_ids = json.loads(session.codes_delivered or "[]")
        cancelled = 0
        for code_id in code_ids:
            code = db.query(StreakPromotionCode).filter(StreakPromotionCode.id == code_id).first()
            if code and code.status == StreakPromotionCodeStatus.DELIVERED:
                code.status = StreakPromotionCodeStatus.CANCELLED
                cancelled += 1
                logger.info(
                    f"streak_promotion_service - cancel_session_codes - "
                    f"session:{session_id} - code:{code.id} - cancelled"
                )
        db.flush()
        return cancelled

    def close_session(self, user_id: int, retire: bool = True):
        """Cierra la sesion activa del usuario.
        retire=True: conserva codigos DELIVERED, limpia expires_at.
        retire=False: cancela todos los codigos de la sesion.
        """
        db = self._get_db()
        session = self.get_active_session(user_id)
        if not session:
            return
        if not retire:
            self.cancel_session_codes(session.id)
        session.expires_at = datetime.now(UTC).replace(tzinfo=None)
        db.flush()
        logger.info(
            f"streak_promotion_service - close_session - "
            f"user:{user_id} - session:{session.id} - retire:{retire}"
        )

    def set_risk_mode(self, user_id: int) -> bool:
        """Activa el modo arriesgo en la sesion activa del usuario.
        Los handlers delegan en este metodo en vez de llamar db.commit().
        Retorna True si se activo, False si no hay sesion activa.
        """
        db = self._get_db()
        session = self.get_active_session(user_id)
        if not session:
            return False
        session.is_in_risk_mode = True
        db.commit()
        logger.info(
            f"streak_promotion_service - set_risk_mode - user:{user_id} - session:{session.id}"
        )
        return True

    def activate(self, promo_id: int) -> bool:
        """Activa una promocion y su categoria asociada si existe."""
        db = self._get_db()
        promotion = db.query(StreakPromotion).filter(StreakPromotion.id == promo_id).first()
        if not promotion:
            logger.warning(f"streak_promotion_service - activate - promo_id:{promo_id} - not_found")
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
        logger.info(f"streak_promotion_service - activate - promo_id:{promo_id} - activated")
        return True

    def deactivate(self, promo_id: int) -> bool:
        """Desactiva una promocion y su categoria si no hay otras activas usandola."""
        db = self._get_db()
        promotion = db.query(StreakPromotion).filter(StreakPromotion.id == promo_id).first()
        if not promotion:
            logger.warning(
                f"streak_promotion_service - deactivate - promo_id:{promo_id} - not_found"
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
                    StreakPromotion.is_active,
                    StreakPromotion.status == StreakPromotionStatus.ACTIVE,
                )
                .first()
            )
            if not other_active:
                from services.trivia_service import TriviaCategoryService

                TriviaCategoryService(db).deactivate(category_id=promotion.category_id)

        db.commit()
        logger.info(f"streak_promotion_service - deactivate - promo_id:{promo_id} - deactivated")
        return True

    def delete_promotion(self, promo_id: int) -> bool:
        """Elimina una promocion permanentemente. Los niveles, codigos
        y redenciones se eliminan en cascada."""
        db = self._get_db()
        promotion = db.query(StreakPromotion).filter(StreakPromotion.id == promo_id).first()
        if not promotion:
            logger.warning(
                f"streak_promotion_service - delete_promotion - promo_id:{promo_id} - not_found"
            )
            return False

        db.delete(promotion)
        db.commit()

        try:
            remove_streak_promotion_jobs(promo_id)
        except Exception as e:
            logger.warning(
                f"streak_promotion_service - delete_promotion - "
                f"promo_id:{promo_id} - failed to remove jobs: {e}"
            )

        logger.info(f"streak_promotion_service - delete_promotion - promo_id:{promo_id} - deleted")
        return True

    def pause_promotion(self, promo_id: int) -> bool:
        """Pausa una promocion temporalmente."""
        db = self._get_db()
        promotion = db.query(StreakPromotion).filter(StreakPromotion.id == promo_id).first()
        if not promotion:
            logger.warning(
                f"streak_promotion_service - pause_promotion - promo_id:{promo_id} - not_found"
            )
            return False

        promotion.status = StreakPromotionStatus.PAUSED
        promotion.is_active = False
        db.commit()
        logger.info(f"streak_promotion_service - pause_promotion - promo_id:{promo_id} - paused")
        return True

    def get_redemption_stats(self, promo_id: int) -> dict:
        """Retorna estadisticas de canje por nivel para una promocion."""
        db = self._get_db()
        promotion = (
            db.query(StreakPromotion)
            .options(joinedload(StreakPromotion.levels).joinedload(StreakPromotionLevel.codes))
            .filter(StreakPromotion.id == promo_id)
            .first()
        )
        if not promotion:
            return {}

        stats = []
        for level in promotion.levels:
            total_codes = len(level.codes)
            delivered = sum(
                1 for c in level.codes if c.status == StreakPromotionCodeStatus.DELIVERED
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
                            "redeemed_at": r.redeemed_at.isoformat() if r.redeemed_at else None,
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
