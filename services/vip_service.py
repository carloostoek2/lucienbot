"""
Servicio VIP - Lucien Bot

Gestiona la lógica de tokens, tarifas y suscripciones VIP.
"""

import logging
import math
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from models.database import SessionLocal
from models.models import Channel, ChannelType, Subscription, Tariff, Token, TokenStatus, User
from services.event_bus import EVENT_VIP_ACTIVATED, get_event_bus, schedule_emit
from utils.lucien_voice import LucienVoice

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
            existing_subscription.tariff_id = token.tariff_id  # direct tariff (new convention for internals + legacy compat)

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

            # Emit post-commit for nurture lifecycle etc (best-effort, non blocking)
            schedule_emit(
                get_event_bus().emit(
                    EVENT_VIP_ACTIVATED,
                    {"user_id": user_id, "subscription_id": existing_subscription.id},
                )
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
            user_id=user_id,
            channel_id=vip_channel.id,
            token_id=token.id,
            tariff_id=token.tariff_id,  # direct tariff association (enables relaxed rule for internal grants)
            end_date=end_date,
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

        # Emit post-commit for nurture / content lifecycle (best effort via schedule_emit)
        schedule_emit(
            get_event_bus().emit(
                EVENT_VIP_ACTIVATED, {"user_id": user_id, "subscription_id": subscription.id}
            )
        )

        return subscription

    async def redeem_token_with_missions(
        self, token_code: str, user_id: int, bot=None
    ) -> Subscription | None:
        """Canjea token VIP y procesa misiones VIP_ACTIVE con entrega automática."""
        subscription = self.redeem_token(token_code, user_id)
        if subscription:
            from services.mission_service import run_vip_mission_side_effects

            shared_db = self.db if not self._owns_session else None
            completed = await run_vip_mission_side_effects(
                user_id, bot=bot, db=shared_db
            )
            if completed:
                logger.info(
                    f"vip_service | vip_mission_side_effects | user_id={user_id} | "
                    f"completed={completed}"
                )
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
            .options(
                joinedload(Subscription.token).joinedload(Token.tariff),
                joinedload(Subscription.tariff),  # direct tariff (preferred for internal grants)
            )
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

    async def create_vip_invite_link(
        self, bot, user_id: int, *, allow_fallback: bool = False
    ) -> str | None:
        """Genera enlace de invitación de un solo uso al canal VIP."""
        vip_channel = self.get_vip_channel()
        if not vip_channel:
            return None
        try:
            invite_link_obj = await bot.create_chat_invite_link(
                chat_id=vip_channel.channel_id,
                name=f"VIP {user_id}",
                creates_join_request=False,
                member_limit=1,
                expire_date=datetime.now(UTC)
                + timedelta(days=self.INVITE_LINK_EXPIRATION_DAYS),
            )
            return invite_link_obj.invite_link
        except Exception as exc:
            logger.error(
                f"vip_service | create_vip_invite_link | user_id={user_id} | "
                f"channel_id={vip_channel.channel_id} | error={exc}"
            )
            if allow_fallback:
                return vip_channel.invite_link
            return None

    async def grant_vip_from_tariff(
        self, bot, user_id: int, tariff_id: int
    ) -> tuple[bool, str, dict]:
        """Genera token, canjea VIP y prepara mensaje de acceso directo."""
        tariff = self.get_tariff(tariff_id)
        if not tariff:
            return False, LucienVoice.reward_tariff_not_found(), {}

        token = self.generate_token(tariff_id)
        subscription = await self.redeem_token_with_missions(
            token.token_code, user_id, bot=bot
        )
        if not subscription:
            logger.error(
                f"vip_service | grant_vip_from_tariff | redeem_failed | "
                f"user_id={user_id} | tariff_id={tariff_id}"
            )
            return False, LucienVoice.reward_vip_activation_failed(), {}

        invite_link = await self.create_vip_invite_link(bot, user_id, allow_fallback=False)
        if not invite_link:
            logger.error(
                f"vip_service | grant_vip_from_tariff | invite_failed | "
                f"user_id={user_id} | tariff_id={tariff_id}"
            )
            partial_metadata = {
                "vip_activated": True,
                "subscription_id": subscription.id,
                "invite_link": None,
                "tariff_name": tariff.name,
                "token_id": token.id,
            }
            return False, LucienVoice.reward_vip_invite_failed(), partial_metadata

        metadata = {
            "vip_activated": True,
            "subscription_id": subscription.id,
            "invite_link": invite_link,
            "tariff_name": tariff.name,
            "token_id": token.id,
            "token_code": token.token_code,
        }
        return True, LucienVoice.vip_direct_access(invite_link), metadata

    async def grant_internal_vip_access(
        self, user_id: int, tariff_id: int
    ) -> tuple[bool, Subscription | None, dict]:
        """
        Otorga (o extiende) acceso VIP directamente asociado a una tarifa, sin requerir Token.
        Usar para grants internos/programáticos: misiones, tienda (VIP_GRANT), activación admin/forward, etc.

        Sigue el mismo contrato de atomicidad/extensión que redeem (pero sin token).
        Emite EVENT_VIP_ACTIVATED (best-effort).
        Retorna (ok, subscription_or_None, metadata).
        """
        tariff = self.get_tariff(tariff_id)
        if not tariff:
            return False, None, {"error": "tariff_not_found"}

        db = self._get_db()
        now = datetime.now(UTC)

        # Verificar si el usuario ya tiene una suscripción activa
        existing_subscription = self.get_user_subscription(user_id)
        sub_end_date = (
            _ensure_aware(existing_subscription.end_date)
            if existing_subscription and existing_subscription.end_date is not None
            else None
        )

        if existing_subscription and sub_end_date is not None and sub_end_date > now:
            # Extender existente
            existing_subscription.end_date = sub_end_date + timedelta(days=tariff.duration_days)
            existing_subscription.is_active = True
            # No tocamos token_id (puede ser None para grants internos)
            existing_subscription.tariff_id = tariff_id

            db.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.is_active,
                Subscription.id != existing_subscription.id,
            ).update({Subscription.is_active: False})

            db.commit()
            db.refresh(existing_subscription)

            user = db.query(User).filter(User.telegram_id == user_id).first()
            if user:
                user.vip_entry_status = None
                user.vip_entry_stage = None
                db.commit()

            logger.info(
                f"vip_service | grant_internal_vip_access | extended | user_id={user_id} | tariff_id={tariff_id}"
            )
            schedule_emit(
                get_event_bus().emit(
                    EVENT_VIP_ACTIVATED,
                    {"user_id": user_id, "subscription_id": existing_subscription.id},
                )
            )
            return True, existing_subscription, {"subscription_id": existing_subscription.id, "tariff_id": tariff_id}

        # Crear nueva
        end_date = now + timedelta(days=tariff.duration_days)

        db.query(Subscription).filter(
            Subscription.user_id == user_id, Subscription.is_active
        ).update({Subscription.is_active: False})

        vip_channel = (
            db.query(Channel)
            .filter(Channel.channel_type == ChannelType.VIP, Channel.is_active)
            .first()
        )
        if not vip_channel:
            db.rollback()
            return False, None, {"error": "no_vip_channel"}

        subscription = Subscription(
            user_id=user_id,
            channel_id=vip_channel.id,
            token_id=None,  # internal grant: no token required
            tariff_id=tariff_id,
            end_date=end_date,
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.vip_entry_status = None
            user.vip_entry_stage = None
            db.commit()

        logger.info(
            f"vip_service | grant_internal_vip_access | created | user_id={user_id} | tariff_id={tariff_id} | sub_id={subscription.id}"
        )
        schedule_emit(
            get_event_bus().emit(
                EVENT_VIP_ACTIVATED, {"user_id": user_id, "subscription_id": subscription.id}
            )
        )
        return True, subscription, {"subscription_id": subscription.id, "tariff_id": tariff_id}

    async def grant_internal_vip_access_for_subscription(
        self, subscription_id: int, tariff_id: int
    ) -> tuple[bool, Subscription | None, dict]:
        """
        Extiende una suscripción VIP específica por ID (admin perfil suscriptor).
        No usa get_user_subscription — apunta al subscription_id del perfil.
        """
        tariff = self.get_tariff(tariff_id)
        if not tariff:
            return False, None, {"error": "tariff_not_found"}
        if not tariff.is_active:
            logger.warning(
                f"vip_service | grant_internal_vip_access_for_subscription | "
                f"subscription_id={subscription_id} | tariff_id={tariff_id} | result=tariff_inactive"
            )
            return False, None, {"error": "tariff_inactive"}

        db = self._get_db()
        now = datetime.now(UTC)
        subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            return False, None, {"error": "subscription_not_found"}

        sub_end_date = _ensure_aware(subscription.end_date)
        if not subscription.is_active or sub_end_date is None or sub_end_date <= now:
            return False, None, {"error": "subscription_inactive"}

        subscription.end_date = sub_end_date + timedelta(days=tariff.duration_days)
        subscription.is_active = True
        subscription.tariff_id = tariff_id
        db.commit()
        db.refresh(subscription)

        user = db.query(User).filter(User.telegram_id == subscription.user_id).first()
        if user:
            user.vip_entry_status = None
            user.vip_entry_stage = None
            db.commit()

        logger.info(
            f"vip_service | grant_internal_vip_access_for_subscription | extended | "
            f"subscription_id={subscription_id} | tariff_id={tariff_id}"
        )
        schedule_emit(
            get_event_bus().emit(
                EVENT_VIP_ACTIVATED,
                {"user_id": subscription.user_id, "subscription_id": subscription.id},
            )
        )
        return True, subscription, {
            "subscription_id": subscription.id,
            "tariff_id": tariff_id,
        }

    async def resend_vip_invite_for_user(
        self, bot, user_id: int
    ) -> tuple[bool, str, str | None]:
        """Regenera enlace VIP si el usuario tiene suscripción activa."""
        if not self.is_user_vip(user_id):
            return False, LucienVoice.reward_vip_not_configured(), None
        invite_link = await self.create_vip_invite_link(bot, user_id, allow_fallback=False)
        if not invite_link:
            return False, LucienVoice.reward_vip_invite_failed(), None
        return True, LucienVoice.vip_direct_access(invite_link), invite_link

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

    def get_subscriber_list_page(
        self,
        channel_id: int | None = None,
        page: int = 0,
        page_size: int = 8,
    ) -> tuple[list[Subscription], int]:
        """Página de suscripciones activas ordenadas por end_date ASC + total."""
        db = self._get_db()
        now = datetime.now(UTC).replace(tzinfo=None)
        base = db.query(Subscription).filter(
            Subscription.is_active,
            Subscription.end_date > now,
        )
        if channel_id:
            base = base.filter(Subscription.channel_id == channel_id)
        total = base.count()
        total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
        clamped_page = max(0, min(page, total_pages - 1)) if total > 0 else 0
        subs = (
            base.options(
                joinedload(Subscription.user),
                joinedload(Subscription.tariff),
                joinedload(Subscription.token).joinedload(Token.tariff),
            )
            .order_by(Subscription.end_date.asc())
            .offset(clamped_page * page_size)
            .limit(page_size)
            .all()
        )
        logger.info(
            f"vip_service | get_subscriber_list_page | channel_id={channel_id or 0} | "
            f"page={page} | total={total} | result=ok"
        )
        return subs, total

    def get_subscriber_admin_snapshot(self, subscription_id: int) -> dict | None:
        """Snapshot read-only para perfil admin (besitos compuesto localmente)."""
        db = self._get_db()
        now = datetime.now(UTC)
        sub = (
            db.query(Subscription)
            .options(
                joinedload(Subscription.user),
                joinedload(Subscription.tariff),
                joinedload(Subscription.token).joinedload(Token.tariff),
                joinedload(Subscription.channel),
            )
            .filter(Subscription.id == subscription_id)
            .first()
        )
        if not sub or not sub.is_active:
            return None
        end_date = _ensure_aware(sub.end_date)
        if end_date is None or end_date <= now:
            return None

        from services.besito_service import BesitoService

        besito_svc = BesitoService(db=db)
        balance = besito_svc.get_balance(sub.user_id)

        if sub.tariff:
            tariff_name = sub.tariff.name
        elif sub.token and sub.token.tariff:
            tariff_name = sub.token.tariff.name
        else:
            tariff_name = "—"

        user = sub.user
        if user and user.username:
            display_name = f"@{user.username}"
        elif user and user.first_name:
            display_name = user.first_name
        else:
            display_name = f"ID:{sub.user_id}"

        days_remaining = max(0, (end_date - now).days)
        snapshot = {
            "subscription_id": sub.id,
            "user_id": sub.user_id,
            "display_name": display_name,
            "besitos_balance": balance,
            "tariff_name": tariff_name,
            "expiry_iso": end_date.strftime("%d/%m/%Y"),
            "days_remaining": days_remaining,
            "channel_db_id": sub.channel_id,
        }
        logger.info(
            f"vip_service | get_subscriber_admin_snapshot | subscription_id={subscription_id} | "
            f"user_id={sub.user_id} | result=ok"
        )
        return snapshot

    def get_subscriber_extend_context(
        self, subscription_id: int
    ) -> tuple[dict | None, list]:
        """Snapshot + tarifas activas para flujo extend (1 llamada de negocio compuesta)."""
        snapshot = self.get_subscriber_admin_snapshot(subscription_id)
        tariffs = self.get_all_tariffs(active_only=True)
        return snapshot, tariffs

    async def admin_revoke_subscription(
        self, bot, subscription_id: int, admin_id: int
    ) -> tuple[bool, str, dict]:
        """
        Revoca suscripción admin (kick).
        Contrato idéntico a scheduler _process_expired_subscriptions.
        """
        db = self._get_db()
        subscription = (
            db.query(Subscription)
            .options(joinedload(Subscription.channel))
            .filter(Subscription.id == subscription_id)
            .first()
        )
        if not subscription or not subscription.is_active:
            logger.warning(
                f"vip_service | admin_revoke_subscription | user_id={admin_id} | "
                f"subscription_id={subscription_id} | result=not_found"
            )
            return False, "not_found", {}

        channel = subscription.channel
        if not channel or not channel.is_active:
            subscription.is_active = False
            db.commit()
            logger.info(
                f"vip_service | admin_revoke_subscription | user_id={admin_id} | "
                f"subscription_id={subscription_id} | result=channel_inactive"
            )
            return True, "channel_inactive", {"subscription_id": subscription_id}

        other_active = self.has_other_active_subscription(
            subscription.user_id, subscription.id
        )
        if other_active:
            subscription.is_active = False
            db.commit()
            logger.info(
                f"vip_service | admin_revoke_subscription | user_id={admin_id} | "
                f"subscription_id={subscription_id} | result=deactivated_only"
            )
            return True, "deactivated_only", {"subscription_id": subscription_id}

        try:
            await bot.ban_chat_member(
                chat_id=channel.channel_id, user_id=subscription.user_id
            )
            await bot.unban_chat_member(
                chat_id=channel.channel_id, user_id=subscription.user_id
            )
            subscription.is_active = False
            user = db.query(User).filter(User.telegram_id == subscription.user_id).first()
            if user and user.vip_entry_status is not None:
                user.vip_entry_status = None
                user.vip_entry_stage = None
            db.commit()
            await bot.send_message(
                chat_id=subscription.user_id,
                text=LucienVoice.vip_expired(),
                parse_mode="HTML",
            )
            logger.info(
                f"vip_service | admin_revoke_subscription | user_id={admin_id} | "
                f"subscription_id={subscription_id} | target={subscription.user_id} | result=kicked"
            )
            return True, "kicked", {
                "subscription_id": subscription_id,
                "user_id": subscription.user_id,
            }
        except Exception as exc:
            db.rollback()
            logger.error(
                f"vip_service | admin_revoke_subscription | user_id={admin_id} | "
                f"subscription_id={subscription_id} | result=error | error={exc}"
            )
            return False, "error", {"error": str(exc)}
