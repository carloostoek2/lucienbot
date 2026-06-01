"""
Servicio VIP - Lucien Bot

Gestiona la lógica de tokens, tarifas y suscripciones VIP.
"""

import logging
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from models.database import SessionLocal
from models.models import Channel, ChannelType, Subscription, Tariff, Token, TokenStatus, User

logger = logging.getLogger(__name__)


def _ensure_aware(dt):
    """Normaliza un datetime a timezone-aware UTC.

    SQLite no preserva tzinfo en columnas DateTime(timezone=True), por lo que
    los datetimes recuperados de BD pueden ser naive aunque se hayan guardado
    como aware. Esta función permite comparaciones seguras sin TypeError.
    """
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


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

    # Constant for VIP invite link expiration (7 days)
    INVITE_LINK_EXPIRATION_DAYS = 7

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

    def create_tariff(
        self, name: str, duration_days: int, price: str, currency: str = "USD"
    ) -> Tariff:
        """Crea una nueva tarifa VIP"""
        db = self._get_db()
        tariff = Tariff(name=name, duration_days=duration_days, price=price, currency=currency)
        db.add(tariff)
        db.commit()
        db.refresh(tariff)
        return tariff

    def get_tariff(self, tariff_id: int) -> Tariff | None:
        """Obtiene una tarifa por ID"""
        db = self._get_db()
        return db.query(Tariff).filter(Tariff.id == tariff_id).first()

    def get_all_tariffs(self, active_only: bool = True) -> list[Tariff]:
        """Obtiene todas las tarifas"""
        db = self._get_db()
        query = db.query(Tariff)
        if active_only:
            query = query.filter(Tariff.is_active)
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

        token = Token(token_code=token_code, tariff_id=tariff_id)

        if expires_in_days:
            token.expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        db.add(token)
        db.commit()
        db.refresh(token)
        return token

    def get_token_by_code(self, token_code: str) -> Token | None:
        """Obtiene un token por su código"""
        db = self._get_db()
        return db.query(Token).filter(Token.token_code == token_code).first()

    def get_token(self, token_id: int) -> Token | None:
        """Obtiene un token por ID"""
        db = self._get_db()
        return db.query(Token).filter(Token.id == token_id).first()

    def get_tokens_by_tariff(self, tariff_id: int) -> list[Token]:
        """Obtiene todos los tokens de una tarifa"""
        db = self._get_db()
        return db.query(Token).filter(Token.tariff_id == tariff_id).all()

    def get_all_tokens(self, status: TokenStatus = None) -> list[Token]:
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

        if token.expires_at and _ensure_aware(token.expires_at) < datetime.now(UTC):
            token.status = TokenStatus.EXPIRED
            db.commit()
            return None, "expired"

        return token, None

    def redeem_token(self, token_code: str, user_id: int) -> Subscription | None:
        """
        Canjea un token y crea una suscripción.
        Usa SELECT FOR UPDATE para prevenir race conditions.
        Retorna la suscripción creada o None si falla
        """
        db = self._get_db()

        # Buscar token con bloqueo para prevenir race conditions
        token = db.query(Token).filter(Token.token_code == token_code).with_for_update().first()

        if not token:
            return None

        # Validar estado del token
        if token.status == TokenStatus.USED:
            db.rollback()
            return None

        if token.status == TokenStatus.EXPIRED:
            db.rollback()
            return None

        if token.expires_at and _ensure_aware(token.expires_at) < datetime.now(UTC):
            token.status = TokenStatus.EXPIRED
            db.commit()
            return None

        # Marcar token como usado
        token.status = TokenStatus.USED
        token.redeemed_at = datetime.now(UTC)
        token.redeemed_by_id = user_id

        # Obtener la tarifa asociada al token
        tariff = self.get_tariff(token.tariff_id)
        if not tariff:
            db.rollback()
            return None

        # Verificar si el usuario ya tiene una suscripción activa
        existing_subscription = self.get_user_subscription(user_id)
        now = datetime.now(UTC)

        # Normalizar a timezone-aware: SQLite no preserva tzinfo en DateTime(timezone=True)
        sub_end_date = (
            _ensure_aware(existing_subscription.end_date)
            if existing_subscription and existing_subscription.end_date is not None
            else None
        )

        if existing_subscription and sub_end_date is not None and sub_end_date > now:
            # Usuario activo: extender la suscripción existente
            existing_subscription.end_date = sub_end_date + timedelta(days=tariff.duration_days)
            existing_subscription.is_active = True  # Defensive: ensure active after extension
            # Mantener la nueva referencia del token aunque sea extensión
            existing_subscription.token_id = token.id

            # Desactivar cualquier otra suscripción activa del usuario (duplicados por bug anterior)
            db.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.is_active,
                Subscription.id != existing_subscription.id,
            ).update({Subscription.is_active: False})

            db.commit()
            db.refresh(existing_subscription)

            # Limpiar estado VIP previo y mantener como activo
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if user:
                user.vip_entry_status = None
                user.vip_entry_stage = None
                db.commit()

            logger.info(
                f"VIP subscription extended: user_id={user_id}, new_end_date={existing_subscription.end_date}"
            )
            return existing_subscription

        # Crear nueva suscripción
        end_date = now + timedelta(days=tariff.duration_days)

        # Desactivar suscripciones previas (expiradas o duplicadas)
        db.query(Subscription).filter(
            Subscription.user_id == user_id, Subscription.is_active
        ).update({Subscription.is_active: False})

        # Buscar canal VIP (asumimos el primero disponible o se especifica)
        vip_channel = (
            db.query(Channel)
            .filter(Channel.channel_type == ChannelType.VIP, Channel.is_active)
            .first()
        )

        if not vip_channel:
            db.rollback()
            return None

        subscription = Subscription(
            user_id=user_id, channel_id=vip_channel.id, token_id=token.id, end_date=end_date
        )

        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        # Clear any previous VIP entry state (no ritual anymore)
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.vip_entry_status = None
            user.vip_entry_stage = None
            db.commit()

        return subscription

    def set_gift_status(self, token_id: int, is_gift: bool) -> bool:
        """Marca/desmarca un token como regalo"""
        db = self._get_db()
        token = self.get_token(token_id)
        if token:
            token.is_gift = is_gift
            db.commit()
            logger.info(f"VIP token gift status: token_id={token_id}, is_gift={is_gift}")
            return True
        return False

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

    def get_subscription(self, subscription_id: int) -> Subscription | None:
        """Obtiene una suscripción por ID"""
        db = self._get_db()
        return db.query(Subscription).filter(Subscription.id == subscription_id).first()

    def get_user_subscription(self, user_id: int, channel_id: int = None) -> Subscription | None:
        """Obtiene la suscripción activa de un usuario (no expirada)"""
        db = self._get_db()
        now = datetime.now(UTC)
        query = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.is_active,
            Subscription.end_date > now,
        )
        if channel_id:
            query = query.filter(Subscription.channel_id == channel_id)
        return query.first()

    def get_active_subscriptions(self, channel_id: int = None) -> list[Subscription]:
        """Obtiene todas las suscripciones activas (no expiradas)"""
        db = self._get_db()
        now = datetime.now(UTC).replace(tzinfo=None)
        query = (
            db.query(Subscription)
            .options(joinedload(Subscription.token).joinedload(Token.tariff))
            .filter(
                Subscription.is_active,
                Subscription.end_date > now,
            )
        )
        if channel_id:
            query = query.filter(Subscription.channel_id == channel_id)
        return query.all()

    def get_expiring_subscriptions(self, hours: int = 24) -> list[Subscription]:
        """Obtiene suscripciones que vencen en las próximas X horas"""
        db = self._get_db()
        now = datetime.now(UTC).replace(tzinfo=None)
        threshold = now + timedelta(hours=hours)

        return (
            db.query(Subscription)
            .filter(
                Subscription.is_active,
                Subscription.reminder_sent == False,  # noqa: E712
                Subscription.end_date <= threshold,
                Subscription.end_date > now,
            )
            .all()
        )

    def get_expired_subscriptions(self) -> list[Subscription]:
        """Obtiene suscripciones activas que ya vencieron"""
        db = self._get_db()
        now = datetime.now(UTC).replace(tzinfo=None)
        return (
            db.query(Subscription).filter(Subscription.is_active, Subscription.end_date < now).all()
        )

    def has_other_active_subscription(self, user_id: int, exclude_subscription_id: int) -> bool:
        """Verifica si un usuario tiene otra suscripcion activa a futuro ademas de la dada."""
        db = self._get_db()
        now = datetime.now(UTC).replace(tzinfo=None)
        other = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.is_active,
                Subscription.end_date > now,
                Subscription.id != exclude_subscription_id,
            )
            .first()
        )
        return other is not None

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

    def get_vip_channel(self) -> Channel | None:
        """Obtiene el canal VIP activo"""
        db = self._get_db()
        return (
            db.query(Channel)
            .filter(Channel.channel_type == ChannelType.VIP, Channel.is_active)
            .first()
        )

    # ==================== VIP ENTRY STATE (legacy cleanup) ====================

    def get_vip_entry_state(self, user_id: int) -> tuple:
        """Returns (status, stage) for the user's VIP entry, or (None, None)."""
        db = self._get_db()
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            return user.vip_entry_status, user.vip_entry_stage
        return None, None

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
