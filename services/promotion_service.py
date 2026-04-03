"""
Servicio de Promociones - Lucien Bot

Gestiona promociones comerciales con precio en dinero real (MXN)
y el sistema de "Me Interesa" para notificar a administradores.
"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from models.models import (
    Promotion, PromotionStatus, PromotionInterest, InterestStatus,
    BlockedPromotionUser, Package
)
from models.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class PromotionService:
    """Servicio para gestion de promociones y sistema 'Me Interesa'"""

    def __init__(self, db: Session = None):
        self._owns_session = db is None
        self.db = db or SessionLocal()

    def _get_db(self) -> Session:
        """Obtiene la sesión de base de datos activa."""
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def close(self):
        """Cierra la sesion si fue creada por este servicio"""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    # ==================== PROMOCIONES ====================

    def create_promotion(self, name: str, description: str, package_id: int,
                         price_mxn: int, created_by: int = None,
                         start_date: datetime = None, end_date: datetime = None) -> Promotion:
        """
        Crea una nueva promocion comercial.

        Args:
            name: Nombre de la promocion
            description: Descripcion de la promocion
            package_id: ID del paquete asociado
            price_mxn: Precio en centavos de peso mexicano (ej: 99900 = $999.00 MXN)
            created_by: ID del admin que crea la promocion
            start_date: Fecha de inicio (None = inmediato)
            end_date: Fecha de expiracion (None = sin expiracion)
        """
        db = self._get_db()
        promotion = Promotion(
            name=name,
            description=description,
            package_id=package_id,
            price_mxn=price_mxn,
            created_by=created_by,
            start_date=start_date,
            end_date=end_date,
            status=PromotionStatus.ACTIVE,
            is_active=True
        )
        db.add(promotion)
        db.commit()
        db.refresh(promotion)
        logger.info(f"Promocion creada: {name} (ID: {promotion.id}) - Precio: {promotion.price_display}")
        return promotion

    def get_promotion(self, promotion_id: int) -> Optional[Promotion]:
        """Obtiene una promocion por ID"""
        db = self._get_db()
        return db.query(Promotion).filter(Promotion.id == promotion_id).first()

    def get_all_promotions(self, active_only: bool = False) -> List[Promotion]:
        """Obtiene todas las promociones"""
        db = self._get_db()
        query = db.query(Promotion)
        if active_only:
            query = query.filter(Promotion.is_active == True)
        return query.order_by(desc(Promotion.created_at)).all()

    def get_available_promotions(self) -> List[Promotion]:
        """Obtiene promociones disponibles para los usuarios"""
        db = self._get_db()
        now = datetime.now(timezone.utc)
        return db.query(Promotion).filter(
            Promotion.is_active == True,
            Promotion.status == PromotionStatus.ACTIVE,
            and_(
                Promotion.start_date.is_(None) | (Promotion.start_date <= now)
            ),
            and_(
                Promotion.end_date.is_(None) | (Promotion.end_date >= now)
            )
        ).order_by(desc(Promotion.created_at)).all()

    def update_promotion(self, promotion_id: int, **kwargs) -> bool:
        """Actualiza una promocion"""
        db = self._get_db()
        promotion = self.get_promotion(promotion_id)
        if not promotion:
            return False

        allowed_fields = ['name', 'description', 'price_mxn', 'status',
                         'start_date', 'end_date', 'is_active']
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(promotion, field):
                setattr(promotion, field, value)

        db.commit()
        logger.info(f"Promocion {promotion_id} actualizada")
        return True

    def delete_promotion(self, promotion_id: int) -> bool:
        """Elimina (desactiva) una promocion"""
        return self.update_promotion(promotion_id, is_active=False)

    def pause_promotion(self, promotion_id: int) -> bool:
        """Pausa una promocion temporalmente"""
        return self.update_promotion(promotion_id, status=PromotionStatus.PAUSED)

    def resume_promotion(self, promotion_id: int) -> bool:
        """Reactiva una promocion pausada"""
        return self.update_promotion(promotion_id, status=PromotionStatus.ACTIVE)

    # ==================== SISTEMA "ME INTERESA" ====================

    def is_user_blocked(self, user_id: int) -> bool:
        """Verifica si un usuario esta bloqueado del sistema de promociones"""
        db = self._get_db()
        blocked = db.query(BlockedPromotionUser).filter(
            BlockedPromotionUser.user_id == user_id
        ).first()

        if not blocked:
            return False

        # Si no es permanente, verificar si expiro el bloqueo
        if not blocked.is_permanent and blocked.expires_at:
            if datetime.now(timezone.utc) > blocked.expires_at:
                # Desbloquear automaticamente
                db.delete(blocked)
                db.commit()
                return False

        return True

    def get_blocked_user_info(self, user_id: int) -> Optional[BlockedPromotionUser]:
        """Obtiene informacion de un usuario bloqueado"""
        db = self._get_db()
        return db.query(BlockedPromotionUser).filter(
            BlockedPromotionUser.user_id == user_id
        ).first()

    def has_user_expressed_interest(self, user_id: int, promotion_id: int) -> bool:
        """Verifica si un usuario ya expreso interes en una promocion"""
        db = self._get_db()
        existing = db.query(PromotionInterest).filter(
            PromotionInterest.user_id == user_id,
            PromotionInterest.promotion_id == promotion_id
        ).first()
        return existing is not None

    def get_user_interest(self, user_id: int, promotion_id: int) -> Optional[PromotionInterest]:
        """Obtiene el registro de interes de un usuario en una promocion"""
        db = self._get_db()
        return db.query(PromotionInterest).filter(
            PromotionInterest.user_id == user_id,
            PromotionInterest.promotion_id == promotion_id
        ).first()

    def express_interest(self, user_id: int, promotion_id: int,
                         username: str = None, first_name: str = None,
                         last_name: str = None) -> tuple:
        """
        Registra el interes de un usuario en una promocion.

        Retorna: (exito: bool, mensaje: str, interest: PromotionInterest)
        """
        db = self._get_db()
        # Verificar si el usuario esta bloqueado
        if self.is_user_blocked(user_id):
            blocked_info = self.get_blocked_user_info(user_id)
            reason = blocked_info.reason if blocked_info else "Razon no especificada"
            return False, f"No puedes expresar interes. Razon: {reason}", None

        # Verificar si la promocion existe y esta disponible
        promotion = self.get_promotion(promotion_id)
        if not promotion:
            return False, "Promocion no encontrada", None

        if not promotion.is_available:
            return False, "Esta promocion no esta disponible actualmente", None

        # Verificar si ya expreso interes (con lock para evitar race conditions)
        existing = db.query(PromotionInterest).filter(
            PromotionInterest.user_id == user_id,
            PromotionInterest.promotion_id == promotion_id
        ).with_for_update().first()
        if existing:
            return False, "Ya has expresado interes en esta promocion", None

        # Crear el registro de interes
        interest = PromotionInterest(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            promotion_id=promotion_id,
            status=InterestStatus.PENDING
        )
        db.add(interest)
        db.commit()
        db.refresh(interest)

        logger.info(f"Usuario {user_id} expreso interes en promocion {promotion_id}")
        return True, "Interes registrado correctamente", interest

    def get_interest(self, interest_id: int) -> Optional[PromotionInterest]:
        """Obtiene un registro de interes por ID"""
        db = self._get_db()
        return db.query(PromotionInterest).filter(
            PromotionInterest.id == interest_id
        ).first()

    def get_pending_interests(self, promotion_id: int = None) -> List[PromotionInterest]:
        """Obtiene intereses pendientes, opcionalmente filtrados por promocion"""
        db = self._get_db()
        query = db.query(PromotionInterest).filter(
            PromotionInterest.status == InterestStatus.PENDING
        )
        if promotion_id:
            query = query.filter(PromotionInterest.promotion_id == promotion_id)
        return query.order_by(desc(PromotionInterest.created_at)).all()

    def get_all_interests(self, user_id: int = None, status: InterestStatus = None) -> List[PromotionInterest]:
        """Obtiene todos los intereses con filtros opcionales"""
        db = self._get_db()
        query = db.query(PromotionInterest)
        if user_id:
            query = query.filter(PromotionInterest.user_id == user_id)
        if status:
            query = query.filter(PromotionInterest.status == status)
        return query.order_by(desc(PromotionInterest.created_at)).all()

    def mark_interest_attended(self, interest_id: int, admin_id: int) -> bool:
        """Marca un interes como atendido"""
        db = self._get_db()
        interest = self.get_interest(interest_id)
        if not interest:
            return False

        interest.status = InterestStatus.ATTENDED
        interest.attended_at = datetime.now(timezone.utc)
        interest.attended_by = admin_id
        db.commit()

        logger.info(f"Interes {interest_id} marcado como atendido por admin {admin_id}")
        return True

    # ==================== BLOQUEO DE USUARIOS ====================

    def block_user(self, user_id: int, blocked_by: int = None,
                   reason: str = None, is_permanent: bool = True,
                   expires_at: datetime = None,
                   username: str = None, first_name: str = None,
                   last_name: str = None) -> BlockedPromotionUser:
        """
        Bloquea a un usuario del sistema de promociones.

        Args:
            user_id: ID del usuario a bloquear
            blocked_by: ID del admin que bloquea
            reason: Razon del bloqueo
            is_permanent: Si el bloqueo es permanente
            expires_at: Fecha de expiracion del bloqueo (si no es permanente)
        """
        db = self._get_db()
        # Verificar si ya esta bloqueado
        existing = db.query(BlockedPromotionUser).filter(
            BlockedPromotionUser.user_id == user_id
        ).first()

        if existing:
            # Actualizar bloqueo existente
            existing.reason = reason
            existing.is_permanent = is_permanent
            existing.expires_at = expires_at
            existing.blocked_by = blocked_by
            existing.blocked_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Bloqueo actualizado para usuario {user_id}")
            return existing

        # Crear nuevo bloqueo
        blocked = BlockedPromotionUser(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            blocked_by=blocked_by,
            reason=reason,
            is_permanent=is_permanent,
            expires_at=expires_at
        )
        db.add(blocked)

        # Tambien actualizar intereses pendientes del usuario a bloqueados
        pending_interests = db.query(PromotionInterest).filter(
            PromotionInterest.user_id == user_id,
            PromotionInterest.status == InterestStatus.PENDING
        ).all()

        for interest in pending_interests:
            interest.status = InterestStatus.BLOCKED

        db.commit()
        logger.info(f"Usuario {user_id} bloqueado del sistema de promociones")
        return blocked

    def unblock_user(self, user_id: int) -> bool:
        """Desbloquea a un usuario"""
        db = self._get_db()
        blocked = db.query(BlockedPromotionUser).filter(
            BlockedPromotionUser.user_id == user_id
        ).first()

        if blocked:
            db.delete(blocked)
            db.commit()
            logger.info(f"Usuario {user_id} desbloqueado")
            return True
        return False

    def get_blocked_users(self) -> List[BlockedPromotionUser]:
        """Obtiene todos los usuarios bloqueados"""
        db = self._get_db()
        return db.query(BlockedPromotionUser).order_by(
            desc(BlockedPromotionUser.blocked_at)
        ).all()

    # ==================== ESTADISTICAS ====================

    def get_promotion_stats(self, promotion_id: int = None) -> dict:
        """Obtiene estadisticas de promociones"""
        db = self._get_db()
        # Estadisticas generales
        total_promotions = db.query(Promotion).filter(
            Promotion.is_active == True
        ).count()

        active_promotions = len(self.get_available_promotions())

        # Estadisticas de intereses
        query_interests = db.query(PromotionInterest)
        if promotion_id:
            query_interests = query_interests.filter(
                PromotionInterest.promotion_id == promotion_id
            )

        total_interests = query_interests.count()
        pending_interests = query_interests.filter(
            PromotionInterest.status == InterestStatus.PENDING
        ).count()
        attended_interests = query_interests.filter(
            PromotionInterest.status == InterestStatus.ATTENDED
        ).count()

        # Usuarios bloqueados
        blocked_count = db.query(BlockedPromotionUser).count()

        return {
            'total_promotions': total_promotions,
            'active_promotions': active_promotions,
            'total_interests': total_interests,
            'pending_interests': pending_interests,
            'attended_interests': attended_interests,
            'blocked_users': blocked_count
        }

    def get_user_interest_history(self, user_id: int) -> List[PromotionInterest]:
        """Obtiene el historial de intereses de un usuario"""
        db = self._get_db()
        return db.query(PromotionInterest).filter(
            PromotionInterest.user_id == user_id
        ).order_by(desc(PromotionInterest.created_at)).all()
