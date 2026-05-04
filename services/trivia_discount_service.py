"""
Trivia Discount Service - Sistema de Promociones por Racha de Trivia

Gestiona la configuración de promociones vinculadas a rachas de trivia
y la generación de códigos de descuento.
"""
import json
import logging
import secrets
import string
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session, joinedload
from models.models import (
    TriviaPromotionConfig,
    DiscountCode,
    DiscountCodeStatus,
    Promotion,
    QuestionSet
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

    def close(self):
        """Cierra el servicio (no hay recursos externos)"""
        pass

    # ==================== CONFIGURACIÓN ====================

    def create_trivia_promotion_config(
        self,
        name: str,
        promotion_id: Optional[int],
        discount_percentage: int,
        required_streak: int = 5,
        max_codes: int = 5,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        created_by: Optional[int] = None,
        custom_description: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        auto_reset_enabled: bool = False,
        max_reset_cycles: Optional[int] = None,
        question_set_id: Optional[int] = None,
        discount_tiers: Optional[List[dict]] = None
    ) -> Optional[TriviaPromotionConfig]:
        """Crea configuración de promoción por racha"""
        # Validar tiers si se proporcionan
        if discount_tiers:
            is_valid, error_msg = self.validate_discount_tiers(discount_tiers)
            if not is_valid:
                logger.warning(f"trivia_discount_service - create_trivia_promotion_config - {created_by} - invalid tiers: {error_msg}")
                return None

        with SessionLocal() as session:
            try:
                # Convertir tiers a JSON si se proporcionan
                tiers_json = json.dumps(discount_tiers) if discount_tiers else None

                config = TriviaPromotionConfig(
                    name=name,
                    promotion_id=promotion_id,
                    custom_description=custom_description,
                    discount_percentage=discount_percentage,
                    required_streak=required_streak,
                    max_codes=max_codes,
                    start_date=start_date,
                    end_date=end_date,
                    duration_minutes=duration_minutes,
                    auto_reset_enabled=auto_reset_enabled,
                    max_reset_cycles=max_reset_cycles,
                    created_by=created_by,
                    question_set_id=question_set_id,
                    discount_tiers=tiers_json
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
            config = session.query(TriviaPromotionConfig).options(
                joinedload(TriviaPromotionConfig.promotion),
                joinedload(TriviaPromotionConfig.question_set)
            ).filter(TriviaPromotionConfig.id == config_id).first()
            logger.info(f"trivia_discount_service - get_trivia_promotion_config - {config_id} - {'found' if config else 'not_found'}")
            return config

    def get_active_trivia_promotion_configs(self) -> list[TriviaPromotionConfig]:
        """Obtiene todas las configuraciones activas"""
        with SessionLocal() as session:
            configs = session.query(TriviaPromotionConfig).options(
                joinedload(TriviaPromotionConfig.promotion),
                joinedload(TriviaPromotionConfig.question_set)
            ).filter(
                TriviaPromotionConfig.status == 'active'
            ).all()
            logger.info(f"trivia_discount_service - get_active_trivia_promotion_configs - count: {len(configs)}")
            return configs

    def get_all_trivia_promotion_configs(self) -> list[TriviaPromotionConfig]:
        """Obtiene todas las configuraciones (activas e inactivas)"""
        with SessionLocal() as session:
            configs = session.query(TriviaPromotionConfig).options(
                joinedload(TriviaPromotionConfig.promotion),
                joinedload(TriviaPromotionConfig.question_set)
            ).order_by(TriviaPromotionConfig.created_at.desc()).all()
            logger.info(f"trivia_discount_service - get_all_trivia_promotion_configs - count: {len(configs)}")
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
        """Pausa configuración (marca como paused)"""
        return self.update_trivia_promotion_config(config_id, status='paused', is_active=False)

    def resume_trivia_promotion_config(self, config_id: int) -> bool:
        """Reanuda configuración pausada o terminada"""
        return self.update_trivia_promotion_config(config_id, status='active', is_active=True)

    # ==================== DURACIÓN RELATIVA ====================

    def is_duration_based(self, config: TriviaPromotionConfig) -> bool:
        """Verifica si la configuración usa duración relativa"""
        return config.duration_minutes is not None and config.duration_minutes > 0

    def start_trivia_promotion(self, config_id: int) -> bool:
        """Inicia el contador de la promoción"""
        with SessionLocal() as session:
            try:
                config = session.get(TriviaPromotionConfig, config_id)
                if not config:
                    return False
                if not self.is_duration_based(config):
                    logger.warning(f"trivia_discount_service - start_trivia_promotion - {config_id} - not duration based")
                    return False
                # Usar datetime sin timezone para consistencia
                config.started_at = datetime.utcnow()
                session.commit()
                logger.info(f"trivia_discount_service - start_trivia_promotion - {config_id} - started")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"trivia_discount_service - start_trivia_promotion - {config_id} - error: {e}")
                return False

    def get_time_remaining(self, config_id: int) -> int:
        """Obtiene minutos restantes de la promoción (0 si expiró o no es por duración).
        Si está habilitado el reinicio automático, lo ejecuta cuando expire."""
        with SessionLocal() as session:
            try:
                config = session.get(TriviaPromotionConfig, config_id)
                if not config or not self.is_duration_based(config):
                    return 0
                if not config.started_at:
                    # Si no se ha iniciado, devolver la duración completa
                    return config.duration_minutes

                # Normalizar: convertir started_at a naive datetime para comparar
                now = datetime.utcnow()
                started = config.started_at

                # Si started tiene timezone (PostgreSQL), convertir a naive UTC
                if started.tzinfo:
                    started = started.replace(tzinfo=None)

                elapsed_minutes = (now - started).total_seconds() / 60
                remaining = max(0, int(config.duration_minutes - elapsed_minutes))

                # Verificar si necesita reinicio automático
                if remaining <= 0 and config.auto_reset_enabled and config.is_active:
                    # Verificar si hay ciclos disponibles
                    can_reset = config.max_reset_cycles is None or config.reset_count < config.max_reset_cycles
                    if can_reset:
                        # Ejecutar reinicio
                        reset_duration = int(config.duration_minutes * 0.25)  # 25% del tiempo original
                        config.started_at = datetime.utcnow()
                        config.duration_minutes = reset_duration
                        config.reset_count += 1
                        session.commit()
                        logger.info(f"trivia_discount_service - get_time_remaining - {config_id} - auto reset to {reset_duration} min, cycle {config.reset_count}")
                        return reset_duration
                    else:
                        # Ya no hay ciclos disponibles - marcar como expirada
                        config.status = 'expired'
                        config.is_active = False
                        session.commit()
                        logger.info(f"trivia_discount_service - get_time_remaining - {config_id} - no cycles left, expired")
                        return 0

                # Si tiempo expiró y no tiene reinicio automático, marcar expirada
                if remaining <= 0 and not config.auto_reset_enabled and config.status == 'active':
                    config.status = 'expired'
                    config.is_active = False
                    session.commit()
                    logger.info(f"trivia_discount_service - get_time_remaining - {config_id} - duration expired, expired")
                    return 0

                return remaining
            except Exception as e:
                logger.error(f"trivia_discount_service - get_time_remaining - {config_id} - error: {e}")
                return 0

    def get_time_remaining_formatted(self, config_id: int) -> str:
        """Obtiene tiempo restante formateado para mostrar"""
        remaining = self.get_time_remaining(config_id)
        if remaining <= 0:
            return "Expirada"
        if remaining < 60:
            return f"{remaining} min"
        hours = remaining // 60
        mins = remaining % 60
        if remaining < 1440:  # menos de 24 horas
            if mins > 0:
                return f"{hours}h {mins}min"
            return f"{hours}h"
        days = remaining // 1440
        hours = (remaining % 1440) // 60
        if hours > 0:
            return f"{days}d {hours}h"
        return f"{days}d"

    def extend_duration(self, config_id: int, additional_minutes: int) -> bool:
        """Extiende la duración de la promoción"""
        with SessionLocal() as session:
            try:
                config = session.get(TriviaPromotionConfig, config_id)
                if not config or not self.is_duration_based(config):
                    return False
                # Extender la duración total (no agregar al tiempo restante)
                if config.duration_minutes:
                    config.duration_minutes += additional_minutes
                else:
                    config.duration_minutes = additional_minutes
                session.commit()
                logger.info(f"trivia_discount_service - extend_duration - {config_id} - extended by {additional_minutes} min")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"trivia_discount_service - extend_duration - {config_id} - error: {e}")
                return False

    def get_active_promotion_with_time(self) -> Optional[dict]:
        """Obtiene la promoción activa con tiempo restante formateado (para menú principal)"""
        with SessionLocal() as session:
            try:
                configs = session.query(TriviaPromotionConfig).options(
                    joinedload(TriviaPromotionConfig.promotion)
                ).filter(
                    TriviaPromotionConfig.status == 'active'
                ).all()

                for config in configs:
                    remaining = self.get_time_remaining(config.id)
                    if remaining > 0:
                        promo_name = config.promotion.name if config.promotion else config.custom_description or config.name
                        return {
                            'id': config.id,
                            'name': promo_name,
                            'remaining': remaining,
                            'remaining_formatted': self.get_time_remaining_formatted(config.id),
                            'discount_percentage': config.discount_percentage,
                            'required_streak': config.required_streak
                        }
                return None
            except Exception as e:
                logger.error(f"trivia_discount_service - get_active_promotion_with_time - error: {e}")
                return None

    # ==================== CÓDIGOS ====================

    def generate_discount_code(
        self,
        user_id: int,
        config_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None
    ) -> Optional[dict]:
        """Genera código de descuento para usuario (devuelve dict para evitar detached instance)"""
        with SessionLocal() as session:
            try:
                # Verificar que la configuración existe y está activa
                config = session.get(TriviaPromotionConfig, config_id)
                if not config or config.status != 'active':
                    logger.warning(f"trivia_discount_service - generate_discount_code - {user_id} - config not found or not active")
                    return None

                # Verificar vigencia de fechas
                now = datetime.utcnow()
                if config.start_date and now < config.start_date:
                    logger.warning(f"trivia_discount_service - generate_discount_code - {user_id} - not started")
                    return None
                if config.end_date and now > config.end_date:
                    logger.warning(f"trivia_discount_service - generate_discount_code - {user_id} - expired")
                    return None

                # Verificar vigencia por duración relativa
                # Usar get_time_remaining para aprovechar el reinicio automático si está habilitado
                if config.duration_minutes and config.started_at:
                    remaining = self.get_time_remaining(config_id)
                    if remaining <= 0:
                        logger.warning(f"trivia_discount_service - generate_discount_code - {user_id} - expired by duration")
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

                # Devolver diccionario en lugar del objeto para evitar detached instance
                result = {
                    'code': discount_code.code,
                    'promotion_name': config.promotion.name if config.promotion else config.custom_description,
                    'discount_percentage': config.discount_percentage
                }
                logger.info(f"trivia_discount_service - generate_discount_code - {user_id} - success: {code}")
                return result
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
                code.used_at = datetime.utcnow()

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

    def invalidate_user_code(self, user_id: int, config_id: int) -> bool:
        """Invalida el código activo de un usuario para una configuración (por fallo en racha)"""
        with SessionLocal() as session:
            try:
                code = session.query(DiscountCode).filter(
                    DiscountCode.user_id == user_id,
                    DiscountCode.config_id == config_id,
                    DiscountCode.status == DiscountCodeStatus.ACTIVE
                ).first()
                if not code:
                    logger.info(f"trivia_discount_service - invalidate_user_code - {user_id}/{config_id} - no_active_code")
                    return False
                code.status = DiscountCodeStatus.CANCELLED
                session.commit()
                logger.info(f"trivia_discount_service - invalidate_user_code - {user_id}/{config_id} - invalidated:{code.code}")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"trivia_discount_service - invalidate_user_code - {user_id}/{config_id} - error: {e}")
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

    def validate_discount_tiers(self, tiers: List[dict]) -> tuple[bool, str]:
        """Valida estructura de tiers. Retorna (es_valido, mensaje_error)"""
        if not tiers:
            return False, "La lista de tiers no puede estar vacía"

        if len(tiers) > 5:
            return False, "Máximo 5 tiers permitidos"

        if len(tiers) < 1:
            return False, "Al menos 1 tier requerido"

        prev_streak = 0
        prev_discount = 0

        for i, tier in enumerate(tiers):
            if 'streak' not in tier or 'discount' not in tier:
                return False, f"Tier {i+1} debe tener 'streak' y 'discount'"

            streak = tier['streak']
            discount = tier['discount']

            if not isinstance(streak, int) or streak < 1:
                return False, f"Tier {i+1}: streak debe ser entero positivo"

            if not isinstance(discount, int) or discount < 0 or discount > 100:
                return False, f"Tier {i+1}: discount debe ser 0-100"

            if streak <= prev_streak:
                return False, f"Tier {i+1}: streak debe ser mayor que el anterior ({prev_streak})"

            if discount <= prev_discount and discount != 100:
                return False, f"Tier {i+1}: discount debe ser mayor que el anterior ({prev_discount}) o 100%"

            prev_streak = streak
            prev_discount = discount

        # El último tier debe ser 100%
        if tiers[-1]['discount'] != 100:
            return False, "El último tier debe ser 100% (descuento completo)"

        return True, ""

    # ==================== TIERS DE DESCUENTO ====================

    def parse_discount_tiers(self, config: TriviaPromotionConfig) -> List[dict]:
        """Parse discount_tiers JSON y retorna lista de tiers ordenados por streak"""
        if not config.discount_tiers:
            # Fallback al método antiguo si no hay tiers
            return [{'streak': config.required_streak, 'discount': config.discount_percentage}]
        try:
            tiers = json.loads(config.discount_tiers)
            return sorted(tiers, key=lambda x: x['streak'])
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"trivia_discount_service - parse_discount_tiers - config {config.id} - invalid tiers format")
            return [{'streak': config.required_streak, 'discount': config.discount_percentage}]

    def get_tier_for_streak(self, config: TriviaPromotionConfig, streak: int) -> Optional[dict]:
        """Obtiene el tier correspondiente a una racha dada"""
        tiers = self.parse_discount_tiers(config)
        # Buscar el tier más alto que corresponde a esta racha
        for tier in reversed(tiers):
            if streak >= tier['streak']:
                return tier
        return None

    def get_next_tier(self, config: TriviaPromotionConfig, current_streak: int) -> Optional[dict]:
        """Obtiene el siguiente tier después del streak actual"""
        tiers = self.parse_discount_tiers(config)
        for tier in tiers:
            if tier['streak'] > current_streak:
                return tier
        return None

    def generate_tiered_discount_code(
        self,
        user_id: int,
        config_id: int,
        discount_percentage: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None
    ) -> Optional[dict]:
        """Genera código de descuento con un porcentaje específico (para tiers)"""
        with SessionLocal() as session:
            try:
                config = session.get(TriviaPromotionConfig, config_id)
                if not config or config.status != 'active':
                    logger.warning(f"trivia_discount_service - generate_tiered_discount_code - {user_id} - config not found or not active")
                    return None

                # Verificar vigencia
                now = datetime.utcnow()
                if config.start_date and now < config.start_date:
                    logger.warning(f"trivia_discount_service - generate_tiered_discount_code - {user_id} - not started")
                    return None
                if config.end_date and now > config.end_date:
                    logger.warning(f"trivia_discount_service - generate_tiered_discount_code - {user_id} - expired")
                    return None

                # Verificar duración relativa
                if config.duration_minutes and config.started_at:
                    remaining = self.get_time_remaining(config_id)
                    if remaining <= 0:
                        logger.warning(f"trivia_discount_service - generate_tiered_discount_code - {user_id} - expired by duration")
                        return None

                # Verificar códigos disponibles
                available = config.max_codes - config.codes_claimed
                if available <= 0:
                    logger.warning(f"trivia_discount_service - generate_tiered_discount_code - {user_id} - no codes available")
                    return None

                # Verificar que usuario no tenga ya código activo para esta configuración
                existing = session.query(DiscountCode).filter(
                    DiscountCode.user_id == user_id,
                    DiscountCode.config_id == config_id,
                    DiscountCode.status == DiscountCodeStatus.ACTIVE
                ).first()
                if existing:
                    logger.warning(f"trivia_discount_service - generate_tiered_discount_code - {user_id} - already has active code")
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

                result = {
                    'code': discount_code.code,
                    'promotion_name': config.promotion.name if config.promotion else config.custom_description,
                    'discount_percentage': discount_percentage
                }
                logger.info(f"trivia_discount_service - generate_tiered_discount_code - {user_id} - success: {code} at {discount_percentage}%")
                return result
            except Exception as e:
                session.rollback()
                logger.error(f"trivia_discount_service - generate_tiered_discount_code - {user_id} - error: {e}")
                return None

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
