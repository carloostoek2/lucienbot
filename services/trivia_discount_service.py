"""
Trivia Discount Service - Sistema de Promociones por Racha de Trivia

Gestiona la configuración de promociones vinculadas a rachas de trivia
y la generación de códigos de descuento.
"""
import logging
import secrets
import string
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from models.models import (
    TriviaPromotionConfig,
    DiscountCode,
    DiscountCodeStatus,
    Promotion
)
from models.database import SessionLocal

logger = logging.getLogger(__name__)


def _generate_trivia_code() -> str:
    """Genera código único TRI-XXXXXX"""
    chars = string.ascii_uppercase.replace('O', '').replace('I', '') + string.digits.replace('0', '').replace('1', '')
    suffix = ''.join(secrets.choice(chars) for _ in range(6))
    return f"TRI-{suffix}"


class TriviaDiscountService:
    """Servicio para gestionar promociones por racha de trivia"""

    # ==================== CONFIGURACIÓN ====================

    def create_trivia_promotion_config(
        self,
        name: str,
        promotion_id: int,
        discount_percentage: int,
        required_streak: int = 5,
        max_codes: int = 5,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        created_by: Optional[int] = None
    ) -> Optional[TriviaPromotionConfig]:
        """Crea configuración de promoción por racha"""
        with SessionLocal() as session:
            try:
                config = TriviaPromotionConfig(
                    name=name,
                    promotion_id=promotion_id,
                    discount_percentage=discount_percentage,
                    required_streak=required_streak,
                    max_codes=max_codes,
                    start_date=start_date,
                    end_date=end_date,
                    created_by=created_by
                )
                session.add(config)
                session.commit()
                session.refresh(config)
                logger.info(f"trivia_discount_service - create_trivia_promotion_config - {created_by} - success: {config.id}")
                return config
            except Exception as e:
                session.rollback()
                logger.error(f"trivia_discount_service - create_trivia_promotion_config - {created_by} - error: {e}")
                return None

    def get_trivia_promotion_config(self, config_id: int) -> Optional[TriviaPromotionConfig]:
        """Obtiene configuración por ID"""
        with SessionLocal() as session:
            config = session.get(TriviaPromotionConfig, config_id)
            logger.info(f"trivia_discount_service - get_trivia_promotion_config - {config_id} - {'found' if config else 'not_found'}")
            return config

    def get_active_trivia_promotion_configs(self) -> list[TriviaPromotionConfig]:
        """Obtiene todas las configuraciones activas"""
        with SessionLocal() as session:
            configs = session.query(TriviaPromotionConfig).filter(
                TriviaPromotionConfig.is_active == True
            ).all()
            logger.info(f"trivia_discount_service - get_active_trivia_promotion_configs - count: {len(configs)}")
            return configs

    def update_trivia_promotion_config(self, config_id: int, **kwargs) -> bool:
        """Actualiza configuración"""
        with SessionLocal() as session:
            try:
                config = session.get(TriviaPromotionConfig, config_id)
                if not config:
                    return False
                for key, value in kwargs.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
                session.commit()
                logger.info(f"trivia_discount_service - update_trivia_promotion_config - {config_id} - success")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"trivia_discount_service - update_trivia_promotion_config - {config_id} - error: {e}")
                return False

    def delete_trivia_promotion_config(self, config_id: int) -> bool:
        """Elimina configuración"""
        with SessionLocal() as session:
            try:
                config = session.get(TriviaPromotionConfig, config_id)
                if not config:
                    return False
                session.delete(config)
                session.commit()
                logger.info(f"trivia_discount_service - delete_trivia_promotion_config - {config_id} - success")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"trivia_discount_service - delete_trivia_promotion_config - {config_id} - error: {e}")
                return False

    def pause_trivia_promotion_config(self, config_id: int) -> bool:
        """Pausa configuración"""
        return self.update_trivia_promotion_config(config_id, is_active=False)

    # ==================== CÓDIGOS ====================

    def generate_discount_code(
        self,
        user_id: int,
        config_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None
    ) -> Optional[DiscountCode]:
        """Genera código de descuento para usuario"""
        with SessionLocal() as session:
            try:
                # Verificar que la configuración existe y está activa
                config = session.get(TriviaPromotionConfig, config_id)
                if not config or not config.is_active:
                    logger.warning(f"trivia_discount_service - generate_discount_code - {user_id} - config not found or inactive")
                    return None

                # Verificar vigencia de fechas
                now = datetime.now(timezone.utc)
                if config.start_date and now < config.start_date:
                    logger.warning(f"trivia_discount_service - generate_discount_code - {user_id} - not started")
                    return None
                if config.end_date and now > config.end_date:
                    logger.warning(f"trivia_discount_service - generate_discount_code - {user_id} - expired")
                    return None

                # Verificar códigos disponibles (basado en reclamados, no emitidos)
                available = config.max_codes - config.codes_claimed
                if available <= 0:
                    logger.warning(f"trivia_discount_service - generate_discount_code - {user_id} - no codes available")
                    return None

                # Verificar que usuario no tenga ya código activo para esta configuración
                existing = session.query(DiscountCode).filter(
                    DiscountCode.user_id == user_id,
                    DiscountCode.config_id == config_id,
                    DiscountCode.status == DiscountCodeStatus.ACTIVE
                ).first()
                if existing:
                    logger.warning(f"trivia_discount_service - generate_discount_code - {user_id} - already has active code")
                    return None

                # Generar código único
                code = _generate_trivia_code()

                discount_code = DiscountCode(
                    config_id=config_id,
                    code=code,
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    promotion_id=config.promotion_id,
                    status=DiscountCodeStatus.ACTIVE
                )
                session.add(discount_code)
                session.commit()
                session.refresh(discount_code)
                logger.info(f"trivia_discount_service - generate_discount_code - {user_id} - success: {code}")
                return discount_code
            except Exception as e:
                session.rollback()
                logger.error(f"trivia_discount_service - generate_discount_code - {user_id} - error: {e}")
                return None

    def get_user_discount_code(self, user_id: int, config_id: int) -> Optional[DiscountCode]:
        """Obtiene código activo de usuario para una configuración"""
        with SessionLocal() as session:
            code = session.query(DiscountCode).filter(
                DiscountCode.user_id == user_id,
                DiscountCode.config_id == config_id,
                DiscountCode.status == DiscountCodeStatus.ACTIVE
            ).first()
            return code

    def get_codes_by_config(self, config_id: int) -> list[DiscountCode]:
        """Obtiene todos los códigos de una configuración"""
        with SessionLocal() as session:
            codes = session.query(DiscountCode).filter(
                DiscountCode.config_id == config_id
            ).all()
            return codes

    def use_discount_code(self, code_id: int) -> bool:
        """Marca código como usado e incrementa codes_claimed"""
        with SessionLocal() as session:
            try:
                code = session.get(DiscountCode, code_id)
                if not code or code.status != DiscountCodeStatus.ACTIVE:
                    return False

                # Marcar como usado
                code.status = DiscountCodeStatus.USED
                code.used_at = datetime.now(timezone.utc)

                # Incrementar contador de reclamados
                config = session.get(TriviaPromotionConfig, code.config_id)
                if config:
                    config.codes_claimed += 1

                session.commit()
                logger.info(f"trivia_discount_service - use_discount_code - {code_id} - success")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"trivia_discount_service - use_discount_code - {code_id} - error: {e}")
                return False

    def cancel_discount_code(self, code_id: int) -> bool:
        """Cancela código de descuento"""
        with SessionLocal() as session:
            try:
                code = session.get(DiscountCode, code_id)
                if not code:
                    return False
                code.status = DiscountCodeStatus.CANCELLED
                session.commit()
                logger.info(f"trivia_discount_service - cancel_discount_code - {code_id} - success")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"trivia_discount_service - cancel_discount_code - {code_id} - error: {e}")
                return False

    # ==================== VERIFICACIÓN ====================

    def get_config_by_promotion(self, promotion_id: int) -> Optional[TriviaPromotionConfig]:
        """Obtiene configuración por ID de promoción"""
        with SessionLocal() as session:
            config = session.query(TriviaPromotionConfig).filter(
                TriviaPromotionConfig.promotion_id == promotion_id
            ).first()
            return config

    def is_promotion_configured(self, promotion_id: int) -> bool:
        """Verifica si promoción tiene configuración de racha"""
        return self.get_config_by_promotion(promotion_id) is not None

    def get_available_codes_count(self, config_id: int) -> int:
        """Obtiene cantidad de códigos disponibles"""
        with SessionLocal() as session:
            config = session.get(TriviaPromotionConfig, config_id)
            if not config:
                return 0
            return max(0, config.max_codes - config.codes_claimed)

    # ==================== ESTADÍSTICAS ====================

    def get_discount_stats(self, config_id: int) -> dict:
        """Obtiene estadísticas de códigos de una configuración"""
        with SessionLocal() as session:
            config = session.get(TriviaPromotionConfig, config_id)
            if not config:
                return {}

            codes = session.query(DiscountCode).filter(
                DiscountCode.config_id == config_id
            ).all()

            total = len(codes)
            active = sum(1 for c in codes if c.status == DiscountCodeStatus.ACTIVE)
            used = sum(1 for c in codes if c.status == DiscountCodeStatus.USED)
            cancelled = sum(1 for c in codes if c.status == DiscountCodeStatus.CANCELLED)
            expired = sum(1 for c in codes if c.status == DiscountCodeStatus.EXPIRED)

            return {
                'total_codes': total,
                'available': config.max_codes - config.codes_claimed,
                'claimed': config.codes_claimed,
                'active': active,
                'used': used,
                'cancelled': cancelled,
                'expired': expired,
                'used_percentage': round((used / config.max_codes * 100), 1) if config.max_codes > 0 else 0
            }
