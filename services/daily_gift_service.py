"""
Servicio de Regalo Diario - Lucien Bot

Gestiona el sistema de regalo diario de besitos.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.models import DailyGiftClaim, DailyGiftConfig, TransactionSource
from services.besito_service import BesitoService

logger = logging.getLogger(__name__)


class DailyGiftService:
    """Servicio para gestión del regalo diario"""

    def __init__(self, db: Session = None):
        self.db = db
        self._owns_session = db is None
        self._besito_service_instance = None

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

    @property
    def besito_service(self) -> BesitoService:
        """Obtiene BesitoService con la misma sesión de BD."""
        if self._besito_service_instance is None:
            self._besito_service_instance = BesitoService(self._get_db())
        return self._besito_service_instance

    # ==================== CONFIGURACIÓN ====================

    def get_config(self) -> DailyGiftConfig:
        """Obtiene la configuración del regalo diario"""
        db = self._get_db()
        config = db.query(DailyGiftConfig).first()
        if not config:
            config = DailyGiftConfig(besito_amount=10, is_active=True)
            db.add(config)
            db.commit()
            db.refresh(config)
            logger.info("Configuración de regalo diario creada con valores por defecto")
        return config

    def update_config(self, besito_amount: int, admin_id: int = None) -> DailyGiftConfig:
        """Actualiza la configuración del regalo diario"""
        config = self.get_config()
        config.besito_amount = besito_amount
        config.updated_by = admin_id
        config.updated_at = datetime.now(UTC)
        self._get_db().commit()
        logger.info(f"Configuración de regalo diario actualizada: {besito_amount} besitos")
        return config

    def is_active(self) -> bool:
        """Verifica si el regalo diario está activo"""
        config = self.get_config()
        return config.is_active

    def get_gift_amount(self) -> int:
        """Obtiene la cantidad de besitos del regalo diario"""
        config = self.get_config()
        return config.besito_amount if config.is_active else 0

    def toggle_daily_gift(self) -> bool:
        """
        Activa/desactiva el regalo diario.

        Returns:
            bool: El nuevo estado (True=activado, False=desactivado)
        """
        config = self.get_config()
        config.is_active = not config.is_active
        self._get_db().commit()
        logger.info(f"Daily gift toggled: is_active={config.is_active}")
        return config.is_active

    # ==================== RECLAMOS ====================

    def get_last_claim(self, user_id: int) -> DailyGiftClaim | None:
        """Obtiene el último reclamo de un usuario"""
        return (
            self._get_db()
            .query(DailyGiftClaim)
            .filter(DailyGiftClaim.user_id == user_id)
            .order_by(desc(DailyGiftClaim.claimed_at))
            .first()
        )

    def can_claim(self, user_id: int) -> tuple:
        """
        Verifica si un usuario puede reclamar el regalo diario.

        Returns:
            tuple: (puede_reclamar: bool, tiempo_restante: timedelta o None, mensaje: str)
        """
        config = self.get_config()

        # Verificar si está activo
        if not config.is_active:
            return False, None, "El regalo diario no está disponible en este momento."

        last_claim = self.get_last_claim(user_id)

        # Si nunca ha reclamado, puede reclamar
        if not last_claim:
            return True, None, "¡Puedes reclamar tu regalo diario!"

        # Calcular tiempo desde el último reclamo
        now = datetime.now(UTC)
        last_claim_at = last_claim.claimed_at
        if last_claim_at.tzinfo is None:
            last_claim_at = last_claim_at.replace(tzinfo=UTC)
        time_since_last = now - last_claim_at
        cooldown = timedelta(hours=24)

        # Verificar si han pasado 24 horas
        if time_since_last >= cooldown:
            return True, None, "¡Puedes reclamar tu regalo diario!"

        # Calcular tiempo restante
        time_remaining = cooldown - time_since_last
        hours = int(time_remaining.total_seconds() // 3600)
        minutes = int((time_remaining.total_seconds() % 3600) // 60)

        message = f"Debes esperar {hours}h {minutes}m para tu próximo regalo."
        return False, time_remaining, message

    def claim_gift(self, user_id: int) -> tuple:
        """
        Procesa el reclamo del regalo diario.

        Returns:
            tuple: (éxito: bool, cantidad: int o None, mensaje: str)
        """
        # Verificar si puede reclamar
        can_claim, time_remaining, message = self.can_claim(user_id)

        if not can_claim:
            return False, None, message

        config = self.get_config()
        amount = config.besito_amount
        db = self._get_db()
        besito_service = BesitoService(
            db=self._get_db()
        )  # local on-demand inside credit method only (Item 6); property kept for test guards/compat (hasattr daily precedent)

        try:
            # Registrar el reclamo
            claim = DailyGiftClaim(user_id=user_id, besitos_received=amount)
            db.add(claim)

            # Acreditar besitos
            success = besito_service.credit_besitos(
                user_id=user_id,
                amount=amount,
                source=TransactionSource.DAILY_GIFT,
                description="Regalo diario reclamado",
            )

            if not success:
                db.rollback()
                return False, None, "Hubo un error al procesar tu regalo. Intenta de nuevo."

            db.commit()

            # Obtener saldo actual
            balance = besito_service.get_balance(user_id)

            logger.info(f"Regalo diario reclamado: user={user_id}, amount={amount}")
            return (
                True,
                amount,
                f"¡Recibiste {amount} besitos! 💋\nTu saldo actual es: {balance} besitos.",
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error reclamando regalo: {e}")
            return False, None, "Hubo un error al procesar tu regalo. Intenta de nuevo más tarde."

    def get_claim_history(self, user_id: int, limit: int = 30) -> list:
        """Obtiene el historial de reclamos de un usuario"""
        return (
            self._get_db()
            .query(DailyGiftClaim)
            .filter(DailyGiftClaim.user_id == user_id)
            .order_by(desc(DailyGiftClaim.claimed_at))
            .limit(limit)
            .all()
        )

    def get_total_claims_today(self) -> int:
        """Obtiene el total de reclamos del día actual"""
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            self._get_db().query(DailyGiftClaim).filter(DailyGiftClaim.claimed_at >= today).count()
        )

    def get_total_besitos_given_today(self) -> int:
        """Obtiene el total de besitos entregados hoy"""
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        claims = (
            self._get_db().query(DailyGiftClaim).filter(DailyGiftClaim.claimed_at >= today).all()
        )
        return sum(claim.besitos_received for claim in claims)
