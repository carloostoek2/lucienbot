"""
Servicio de Canales - Lucien Bot

Gestiona la lógica de canales Free y VIP.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.models import Channel, ChannelType, PendingRequest
from services.channel_grant import (
    ApproveAllResult,
    GrantResult,
    grant_pending_request,
    is_valid_telegram_invite_link,
    reject_pending_request,
)

logger = logging.getLogger(__name__)


class ChannelService:
    """Servicio para gestión de canales"""

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

    # ==================== CANALES ====================

    def create_channel(
        self, channel_id: int, channel_name: str, channel_type: ChannelType, wait_time: int = 3
    ) -> Channel:
        """Crea un nuevo canal"""
        db = self._get_db()
        channel = Channel(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_type=channel_type,
            wait_time_minutes=wait_time if channel_type == ChannelType.FREE else 0,
        )
        db.add(channel)
        db.commit()
        db.refresh(channel)
        return channel

    def get_channel_by_id(self, channel_id: int) -> Channel | None:
        """Obtiene un canal por su ID de Telegram"""
        db = self._get_db()
        return db.query(Channel).filter(Channel.channel_id == channel_id).first()

    def get_channel_by_db_id(self, db_id: int) -> Channel | None:
        """Obtiene un canal por su ID de base de datos"""
        db = self._get_db()
        return db.query(Channel).filter(Channel.id == db_id).first()

    def get_all_channels(self) -> list[Channel]:
        """Obtiene todos los canales"""
        db = self._get_db()
        return db.query(Channel).filter(Channel.is_active).all()

    def get_free_channels(self) -> list[Channel]:
        """Obtiene todos los canales Free"""
        db = self._get_db()
        return (
            db.query(Channel)
            .filter(Channel.channel_type == ChannelType.FREE, Channel.is_active)
            .all()
        )

    def get_vip_channels(self) -> list[Channel]:
        """Obtiene todos los canales VIP"""
        db = self._get_db()
        return (
            db.query(Channel)
            .filter(Channel.channel_type == ChannelType.VIP, Channel.is_active)
            .all()
        )

    def delete_channel(self, channel_id: int) -> bool:
        """Elimina un canal de la base de datos"""
        db = self._get_db()
        channel = self.get_channel_by_db_id(channel_id)
        if not channel:
            logger.warning(f"Canal {channel_id} no encontrado para eliminar")
            return False

        db.delete(channel)
        db.commit()
        logger.info(f"Canal {channel_id} eliminado permanentemente")
        return True

    def update_wait_time(self, channel_id: int, minutes: int) -> bool:
        """Actualiza el tiempo de espera de un canal Free"""
        db = self._get_db()
        channel = self.get_channel_by_db_id(channel_id)
        if channel and channel.channel_type == ChannelType.FREE:
            channel.wait_time_minutes = minutes
            db.commit()
            return True
        return False

    def update_invite_link(self, channel_id: int, invite_link: str | None) -> bool:
        """Actualiza el enlace de invitación de un canal Free."""
        if invite_link is not None and not is_valid_telegram_invite_link(invite_link):
            logger.warning(f"Invalid invite_link rejected for channel {channel_id}")
            return False
        db = self._get_db()
        channel = self.get_channel_by_db_id(channel_id)
        if channel:
            channel.invite_link = invite_link
            db.commit()
            return True
        return False

    def update_approval_message(self, channel_db_id: int, text: str | None) -> bool:
        """Actualiza mensaje ritual (approval_message). channel_db_id = DB PK."""
        db = self._get_db()
        channel = self.get_channel_by_db_id(channel_db_id)
        if channel and channel.channel_type == ChannelType.FREE:
            channel.approval_message = text
            db.commit()
            return True
        return False

    def update_welcome_message(self, channel_db_id: int, text: str | None) -> bool:
        """Actualiza mensaje de bienvenida. channel_db_id = DB PK."""
        db = self._get_db()
        channel = self.get_channel_by_db_id(channel_db_id)
        if channel and channel.channel_type == ChannelType.FREE:
            channel.welcome_message = text
            db.commit()
            return True
        return False

    def clear_custom_messages(self, channel_db_id: int, msg_type: str) -> bool:
        """Restaura mensajes custom a default Lucien (None en BD). msg_type: approval|welcome|all."""
        db = self._get_db()
        channel = self.get_channel_by_db_id(channel_db_id)
        if not channel or channel.channel_type != ChannelType.FREE:
            return False
        if msg_type in ("approval", "all"):
            channel.approval_message = None
        if msg_type in ("welcome", "all"):
            channel.welcome_message = None
        db.commit()
        return True

    # ==================== SOLICITUDES PENDIENTES ====================

    def create_pending_request(
        self,
        user_id: int,
        channel_id: int,
        username: str = None,
        first_name: str = None,
        user_chat_id: int | None = None,
    ) -> PendingRequest:
        """Crea una solicitud pendiente de acceso"""
        db = self._get_db()
        channel = self.get_channel_by_db_id(channel_id)
        if not channel:
            raise ValueError("Canal no encontrado")

        scheduled_time = datetime.now(UTC) + timedelta(minutes=channel.wait_time_minutes)

        request = PendingRequest(
            user_id=user_id,
            user_chat_id=user_chat_id,
            channel_id=channel_id,
            username=username,
            first_name=first_name,
            scheduled_approval_at=scheduled_time,
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        return request

    def get_request_by_id(self, request_id: int) -> PendingRequest | None:
        """Obtiene una solicitud por su ID de BD."""
        db = self._get_db()
        return db.query(PendingRequest).filter(PendingRequest.id == request_id).first()

    def get_pending_request(self, user_id: int, channel_id: int) -> PendingRequest | None:
        """Obtiene una solicitud pendiente específica"""
        db = self._get_db()
        return (
            db.query(PendingRequest)
            .filter(
                PendingRequest.user_id == user_id,
                PendingRequest.channel_id == channel_id,
                PendingRequest.status == "pending",
            )
            .first()
        )

    def get_pending_requests_by_channel(self, channel_id: int) -> list[PendingRequest]:
        """Obtiene todas las solicitudes pendientes de un canal (orden estable)."""
        db = self._get_db()
        return (
            db.query(PendingRequest)
            .filter(PendingRequest.channel_id == channel_id, PendingRequest.status == "pending")
            .order_by(PendingRequest.scheduled_approval_at, PendingRequest.id)
            .all()
        )

    def get_valid_pending_request(
        self, request_id: int, expected_channel_db_id: int
    ) -> PendingRequest | None:
        """Valida request pendiente y pertenencia al canal (DB PK)."""
        request = self.get_request_by_id(request_id)
        if not request or request.status != "pending":
            return None
        if request.channel_id != expected_channel_db_id:
            logger.warning(
                f"channel_service | channel_mismatch | request_id={request_id} | "
                f"expected={expected_channel_db_id} | actual={request.channel_id}"
            )
            return None
        return request

    def get_all_pending_requests(self) -> list[PendingRequest]:
        """Obtiene todas las solicitudes pendientes"""
        db = self._get_db()
        return db.query(PendingRequest).filter(PendingRequest.status == "pending").all()

    def get_ready_to_approve(self) -> list[PendingRequest]:
        """Obtiene solicitudes listas para aprobar (tiempo vencido)"""
        db = self._get_db()
        now = datetime.now(UTC)
        return (
            db.query(PendingRequest)
            .filter(PendingRequest.status == "pending", PendingRequest.scheduled_approval_at <= now)
            .all()
        )

    def approve_request(self, request_id: int) -> bool:
        """Aprueba una solicitud específica"""
        db = self._get_db()
        request = db.query(PendingRequest).filter(PendingRequest.id == request_id).first()
        if request:
            request.status = "approved"
            request.approved_at = datetime.now(UTC)
            db.commit()
            return True
        return False

    def cancel_request(self, user_id: int, channel_id: int) -> bool:
        """Cancela una solicitud pendiente"""
        db = self._get_db()
        request = self.get_pending_request(user_id, channel_id)
        if request:
            request.status = "cancelled"
            db.commit()
            return True
        return False

    def approve_all_pending(self, channel_id: int = None) -> int:
        """Aprueba todas las solicitudes pendientes (solo BD — uso interno/tests legacy)."""
        db = self._get_db()
        query = db.query(PendingRequest).filter(PendingRequest.status == "pending")
        if channel_id:
            query = query.filter(PendingRequest.channel_id == channel_id)

        requests = query.all()
        count = 0
        for req in requests:
            req.status = "approved"
            req.approved_at = datetime.now(UTC)
            count += 1

        db.commit()
        return count

    async def approve_request_now(
        self, request_id: int, expected_channel_db_id: int, bot
    ) -> GrantResult:
        """Aprueba una solicitud con grant real. Valida channel_id (DB PK)."""
        db = self._get_db()
        request = self.get_valid_pending_request(request_id, expected_channel_db_id)
        if not request:
            return GrantResult(
                success=False,
                request_id=request_id,
                error="not found, not pending, or channel mismatch",
            )
        return await grant_pending_request(db, request, bot)

    async def approve_all_pending_now(self, channel_db_id: int, bot) -> ApproveAllResult:
        """Aprueba todas las pendientes de un canal con grant real. channel_db_id = DB PK."""
        db = self._get_db()
        result = ApproveAllResult()
        request_ids = [r.id for r in self.get_pending_requests_by_channel(channel_db_id)]
        for request_id in request_ids:
            request = self.get_request_by_id(request_id)
            if not request or request.status != "pending":
                continue
            grant_result = await grant_pending_request(db, request, bot)
            if grant_result.success:
                result.approved += 1
            else:
                result.failed += 1
                if grant_result.error:
                    result.errors.append(f"req {request_id}: {grant_result.error}")
        return result

    async def reject_request_now(self, request_id: int, expected_channel_db_id: int, bot) -> bool:
        """Rechaza una solicitud en Telegram. Valida channel_id (DB PK)."""
        db = self._get_db()
        request = self.get_valid_pending_request(request_id, expected_channel_db_id)
        if not request:
            return False
        return await reject_pending_request(db, request, bot)

    def count_pending_requests(self, channel_id: int = None) -> int:
        """Cuenta solicitudes pendientes"""
        db = self._get_db()
        query = db.query(PendingRequest).filter(PendingRequest.status == "pending")
        if channel_id:
            query = query.filter(PendingRequest.channel_id == channel_id)
        return query.count()
