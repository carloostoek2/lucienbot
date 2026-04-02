"""
Servicio VIP - Lucien Bot

Gestiona la lógica de tokens, tarifas y suscripciones VIP.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from contextlib import contextmanager
from sqlalchemy.orm import Session
from models.models import Tariff, Token, TokenStatus, Subscription, Channel, ChannelType, User
from models.database import SessionLocal


@contextmanager
def get_db_session():
    """Context manager para sesiones de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class VIPService:
    """Servicio para gestión VIP"""

    def __init__(self, db: Session = None):
        self.db = db
        self._owns_session = db is None

    def _get_db(self) -> Session:
        """Obtiene la sesión de base de datos activa."""
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def close(self):
        """Cierra la sesión de base de datos si fue creada por este servicio."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    # ==================== TARIFAS ====================

    def create_tariff(self, name: str, duration_days: int,
                      price: str, currency: str = "USD") -> Tariff:
        """Crea una nueva tarifa VIP"""
        db = self._get_db()
        tariff = Tariff(
            name=name,
            duration_days=duration_days,
            price=price,
            currency=currency
        )
        db.add(tariff)
        db.commit()
        db.refresh(tariff)
        return tariff

    def get_tariff(self, tariff_id: int) -> Optional[Tariff]:
        """Obtiene una tarifa por ID"""
        db = self._get_db()
        return db.query(Tariff).filter(Tariff.id == tariff_id).first()

    def get_all_tariffs(self, active_only: bool = True) -> List[Tariff]:
        """Obtiene todas las tarifas"""
        db = self._get_db()
        query = db.query(Tariff)
        if active_only:
            query = query.filter(Tariff.is_active == True)
        return query.all()

    def update_tariff(self, tariff_id: int, **kwargs) -> bool:
        """Actualiza una tarifa"""
        db = self._get_db()
        tariff = self.get_tariff(tariff_id)
        if tariff:
            for key, value in kwargs.items():
                if hasattr(tariff, key):
                    setattr(tariff, key, value)
            db.commit()
            return True
        return False

    def deactivate_tariff(self, tariff_id: int) -> bool:
        """Desactiva una tarifa"""
        return self.update_tariff(tariff_id, is_active=False)

    # ==================== TOKENS ====================

    def generate_token(self, tariff_id: int, expires_in_days: int = None) -> Token:
        """Genera un nuevo token para una tarifa"""
        db = self._get_db()
        tariff = self.get_tariff(tariff_id)
        if not tariff:
            raise ValueError("Tarifa no encontrada")

        token_code = Token.generate_token()

        token = Token(
            token_code=token_code,
            tariff_id=tariff_id
        )

        if expires_in_days:
            token.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        db.add(token)
        db.commit()
        db.refresh(token)
        return token

    def get_token_by_code(self, token_code: str) -> Optional[Token]:
        """Obtiene un token por su código"""
        db = self._get_db()
        return db.query(Token).filter(Token.token_code == token_code).first()

    def get_token(self, token_id: int) -> Optional[Token]:
        """Obtiene un token por ID"""
        db = self._get_db()
        return db.query(Token).filter(Token.id == token_id).first()

    def get_tokens_by_tariff(self, tariff_id: int) -> List[Token]:
        """Obtiene todos los tokens de una tarifa"""
        db = self._get_db()
        return db.query(Token).filter(Token.tariff_id == tariff_id).all()

    def get_all_tokens(self, status: TokenStatus = None) -> List[Token]:
        """Obtiene todos los tokens"""
        db = self._get_db()
        query = db.query(Token)
        if status:
            query = query.filter(Token.status == status)
        return query.order_by(Token.created_at.desc()).all()

    def validate_token(self, token_code: str) -> tuple:
        """
        Valida un token y retorna (token, mensaje_error)
        Si es válido, retorna (token, None)
        """
        db = self._get_db()
        token = self.get_token_by_code(token_code)

        if not token:
            return None, "invalid"

        if token.status == TokenStatus.USED:
            return None, "used"

        if token.status == TokenStatus.EXPIRED:
            return None, "expired"

        if token.expires_at and token.expires_at < datetime.utcnow():
            token.status = TokenStatus.EXPIRED
            db.commit()
            return None, "expired"

        return token, None

    def redeem_token(self, token_code: str, user_id: int) -> Optional[Subscription]:
        """
        Canjea un token y crea una suscripción.
        Usa SELECT FOR UPDATE para prevenir race conditions.
        Retorna la suscripción creada o None si falla
        """
        db = self._get_db()

        # Buscar token con bloqueo para prevenir race conditions
        token = db.query(Token).filter(
            Token.token_code == token_code
        ).with_for_update().first()

        if not token:
            return None

        # Validar estado del token
        if token.status == TokenStatus.USED:
            db.rollback()
            return None

        if token.status == TokenStatus.EXPIRED:
            db.rollback()
            return None

        if token.expires_at and token.expires_at < datetime.utcnow():
            token.status = TokenStatus.EXPIRED
            db.commit()
            return None

        # Marcar token como usado
        token.status = TokenStatus.USED
        token.redeemed_at = datetime.utcnow()
        token.redeemed_by_id = user_id

        # Crear suscripción
        tariff = token.tariff
        end_date = datetime.utcnow() + timedelta(days=tariff.duration_days)

        # Buscar canal VIP (asumimos el primero disponible o se especifica)
        vip_channel = db.query(Channel).filter(
            Channel.channel_type == ChannelType.VIP,
            Channel.is_active == True
        ).first()

        if not vip_channel:
            db.rollback()
            return None

        subscription = Subscription(
            user_id=user_id,
            channel_id=vip_channel.id,
            token_id=token.id,
            end_date=end_date
        )

        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        # Set VIP entry state for the 3-phase ritual
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.vip_entry_status = "pending_entry"
            user.vip_entry_stage = 1
            db.commit()

        return subscription

    def revoke_token(self, token_id: int) -> bool:
        """Revoca un token activo"""
        db = self._get_db()
        token = self.get_token(token_id)
        if token and token.status == TokenStatus.ACTIVE:
            token.status = TokenStatus.EXPIRED
            db.commit()
            return True
        return False

    # ==================== SUSCRIPCIONES ====================

    def get_subscription(self, subscription_id: int) -> Optional[Subscription]:
        """Obtiene una suscripción por ID"""
        db = self._get_db()
        return db.query(Subscription).filter(Subscription.id == subscription_id).first()

    def get_user_subscription(self, user_id: int, channel_id: int = None) -> Optional[Subscription]:
        """Obtiene la suscripción activa de un usuario"""
        db = self._get_db()
        query = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.is_active == True
        )
        if channel_id:
            query = query.filter(Subscription.channel_id == channel_id)
        return query.first()

    def get_active_subscriptions(self, channel_id: int = None) -> List[Subscription]:
        """Obtiene todas las suscripciones activas"""
        db = self._get_db()
        query = db.query(Subscription).filter(Subscription.is_active == True)
        if channel_id:
            query = query.filter(Subscription.channel_id == channel_id)
        return query.all()

    def get_expiring_subscriptions(self, hours: int = 24) -> List[Subscription]:
        """Obtiene suscripciones que vencen en las próximas X horas"""
        db = self._get_db()
        now = datetime.utcnow()
        threshold = now + timedelta(hours=hours)

        return db.query(Subscription).filter(
            Subscription.is_active == True,
            Subscription.reminder_sent == False,
            Subscription.end_date <= threshold,
            Subscription.end_date > now
        ).all()

    def get_expired_subscriptions(self) -> List[Subscription]:
        """Obtiene suscripciones que ya vencieron"""
        db = self._get_db()
        now = datetime.utcnow()
        return db.query(Subscription).filter(
            Subscription.is_active == True,
            Subscription.end_date < now
        ).all()

    def mark_reminder_sent(self, subscription_id: int) -> bool:
        """Marca que se envió el recordatorio de renovación"""
        db = self._get_db()
        subscription = self.get_subscription(subscription_id)
        if subscription:
            subscription.reminder_sent = True
            db.commit()
            return True
        return False

    def expire_subscription(self, subscription_id: int) -> bool:
        """Desactiva una suscripción vencida"""
        db = self._get_db()
        subscription = self.get_subscription(subscription_id)
        if subscription:
            subscription.is_active = False
            db.commit()
            return True
        return False

    def is_user_vip(self, user_id: int, channel_id: int = None) -> bool:
        """Verifica si un usuario tiene suscripción VIP activa"""
        subscription = self.get_user_subscription(user_id, channel_id)
        return subscription is not None

    def get_vip_channel(self) -> Optional[Channel]:
        """Obtiene el canal VIP activo"""
        db = self._get_db()
        return db.query(Channel).filter(
            Channel.channel_type == ChannelType.VIP,
            Channel.is_active == True
        ).first()

    # ==================== VIP ENTRY STATE MANAGEMENT (PHASE 10) ====================

    def get_vip_entry_state(self, user_id: int) -> tuple:
        """Returns (status, stage) for the user's VIP entry, or (None, None)."""
        db = self._get_db()
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            return user.vip_entry_status, user.vip_entry_stage
        return None, None

    def get_vip_entry_state_for_update(self, user_id: int) -> tuple:
        """
        Returns (status, stage) with SELECT FOR UPDATE to prevent race conditions.
        Use this before operations that modify state (e.g., advance_vip_entry_stage).
        """
        db = self._get_db()
        user = db.query(User).filter(
            User.telegram_id == user_id
        ).with_for_update().first()
        if user:
            return user.vip_entry_status, user.vip_entry_stage
        return None, None

    def advance_vip_entry_stage(self, user_id: int) -> int:
        """Advances vip_entry_stage by 1 (max 3). Returns new stage or None."""
        db = self._get_db()
        user = db.query(User).filter(
            User.telegram_id == user_id
        ).with_for_update().first()
        if not user or user.vip_entry_status != "pending_entry" or user.vip_entry_stage is None:
            return None
        new_stage = min(user.vip_entry_stage + 1, 3)
        user.vip_entry_stage = new_stage
        db.commit()
        return new_stage

    def clear_vip_entry_state(self, user_id: int) -> bool:
        """Clears vip_entry_status and vip_entry_stage."""
        db = self._get_db()
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.vip_entry_status = None
            user.vip_entry_stage = None
            db.commit()
            return True
        return False

    def get_active_subscription_for_entry(self, user_id: int) -> Optional[Subscription]:
        """Returns the active subscription for a pending_entry user, or None if expired/inactive."""
        db = self._get_db()
        now = datetime.utcnow()
        sub = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.is_active == True,
            Subscription.end_date > now
        ).first()
        return sub

    def complete_vip_entry(self, user_id: int) -> bool:
        """Marks VIP entry as active and clears stage. Returns True if state was pending_entry."""
        db = self._get_db()
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user and user.vip_entry_status == "pending_entry":
            user.vip_entry_status = "active"
            user.vip_entry_stage = None
            db.commit()
            return True
        return False
