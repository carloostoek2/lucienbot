"""
Servicio de Regalo Diario - Lucien Bot

Gestiona el sistema de regalo diario de besitos.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.models import DailyGiftConfig, DailyGiftClaim
from models.database import SessionLocal
from services.besito_service import BesitoService
from models.models import TransactionSource
import logging

logger = logging.getLogger(__name__)


class DailyGiftService:
    """Servicio para gestión del regalo diario"""

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

    def _get_besito_service(self) -> BesitoService:
        """Obtiene BesitoService con la misma sesión de BD."""
        return BesitoService(self._get_db())
    
    # ==================== CONFIGURACIÓN ====================
    
    def get_config(self) -> DailyGiftConfig:
        """Obtiene la configuración del regalo diario"""
        db = self._get_db()
        config = db.query(DailyGiftConfig).first()
        if not config:
            config = DailyGiftConfig(
                besito_amount=10,
                is_active=True
            )
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
        config.updated_at = datetime.utcnow()
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
    
    # ==================== RECLAMOS ====================
    
    def get_last_claim(self, user_id: int) -> Optional[DailyGiftClaim]:
        """Obtiene el último reclamo de un usuario"""
        return self._get_db().query(DailyGiftClaim).filter(
            DailyGiftClaim.user_id == user_id
        ).order_by(desc(DailyGiftClaim.claimed_at)).first()
    
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
        now = datetime.now(timezone.utc)
        time_since_last = now - last_claim.claimed_at
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
        besito_service = self._get_besito_service()

        try:
            # Registrar el reclamo
            claim = DailyGiftClaim(
                user_id=user_id,
                besitos_received=amount
            )
            db.add(claim)

            # Acreditar besitos
            success = besito_service.credit_besitos(
                user_id=user_id,
                amount=amount,
                source=TransactionSource.DAILY_GIFT,
                description="Regalo diario reclamado"
            )

            if not success:
                db.rollback()
                return False, None, "Hubo un error al procesar tu regalo. Intenta de nuevo."

            db.commit()

            # Obtener saldo actual
            balance = besito_service.get_balance(user_id)

            logger.info(f"Regalo diario reclamado: user={user_id}, amount={amount}")
            return True, amount, f"¡Recibiste {amount} besitos! 💋\nTu saldo actual es: {balance} besitos."

        except Exception as e:
            db.rollback()
            logger.error(f"Error reclamando regalo: {e}")
            return False, None, "Hubo un error al procesar tu regalo. Intenta de nuevo más tarde."
    
    def get_claim_history(self, user_id: int, limit: int = 30) -> list:
        """Obtiene el historial de reclamos de un usuario"""
        return self._get_db().query(DailyGiftClaim).filter(
            DailyGiftClaim.user_id == user_id
        ).order_by(desc(DailyGiftClaim.claimed_at)).limit(limit).all()

    def get_total_claims_today(self) -> int:
        """Obtiene el total de reclamos del día actual"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return self._get_db().query(DailyGiftClaim).filter(
            DailyGiftClaim.claimed_at >= today
        ).count()

    def get_total_besitos_given_today(self) -> int:
        """Obtiene el total de besitos entregados hoy"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        claims = self._get_db().query(DailyGiftClaim).filter(
            DailyGiftClaim.claimed_at >= today
        ).all()
        return sum(claim.besitos_received for claim in claims)

