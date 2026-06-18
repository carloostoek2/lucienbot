"""
Servicio de Mensajes Anónimos - Lucien Bot

Gestiona el envío y recepción de mensajes anónimos de suscriptores VIP a Diana.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.models import AnonymousMessage, AnonymousMessageStatus, TransactionSource, User
from services.besito_service import BesitoService
from services.vip_service import VIPService

logger = logging.getLogger(__name__)

ANONYMOUS_MESSAGE_COST = 50
ANONYMOUS_MESSAGE_MIN_LENGTH = 3
ANONYMOUS_MESSAGE_MAX_LENGTH = 4000


class AnonymousMessageService:
    """Servicio para gestión de mensajes anónimos VIP"""

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

    def send_message(self, sender_id: int, content: str) -> AnonymousMessage:
        """Envía un mensaje anónimo desde un suscriptor VIP."""
        db = self._get_db()
        message = AnonymousMessage(
            sender_id=sender_id, content=content, status=AnonymousMessageStatus.UNREAD
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    def send_paid_anonymous_message(
        self, user_id: int, content: str, cost: int = ANONYMOUS_MESSAGE_COST
    ) -> tuple[bool, str, AnonymousMessage | None]:
        """Debita besitos y persiste mensaje anónimo en una sola transacción."""
        content = (content or "").strip()
        if len(content) < ANONYMOUS_MESSAGE_MIN_LENGTH or len(content) > ANONYMOUS_MESSAGE_MAX_LENGTH:
            logger.info(
                f"anonymous_message_service | send_paid | user_id={user_id} | result=invalid_content"
            )
            return False, "invalid_content", None

        db = self._get_db()
        vip_service = VIPService(db=db)
        if not vip_service.is_user_vip(user_id):
            logger.info(
                f"anonymous_message_service | send_paid | user_id={user_id} | result=not_vip"
            )
            return False, "not_vip", None

        besito_service = BesitoService(db=db)
        if not besito_service.has_sufficient_balance(user_id, cost):
            logger.info(
                f"anonymous_message_service | send_paid | user_id={user_id} | "
                f"result=insufficient_balance"
            )
            return False, "insufficient_balance", None

        try:
            if not besito_service.debit_besitos(
                user_id=user_id,
                amount=cost,
                source=TransactionSource.ANONYMOUS_MESSAGE,
                description="Envío de mensaje anónimo a Diana",
                commit=False,
            ):
                # debit_besitos already rollbacks on real failure; no full rollback here
                logger.info(
                    f"anonymous_message_service | send_paid | user_id={user_id} | result=debit_failed"
                )
                return False, "debit_failed", None

            message = AnonymousMessage(
                sender_id=user_id, content=content, status=AnonymousMessageStatus.UNREAD
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            logger.info(
                f"anonymous_message_service | send_paid | user_id={user_id} | "
                f"result=ok | message_id={message.id}"
            )
            return True, "ok", message
        except Exception as e:
            db.rollback()
            logger.error(
                f"anonymous_message_service | send_paid | user_id={user_id} | "
                f"result=internal_error | error={e}"
            )
            return False, "internal_error", None

    def get_message(self, message_id: int) -> AnonymousMessage | None:
        """Obtiene un mensaje por ID."""
        db = self._get_db()
        return db.query(AnonymousMessage).filter(AnonymousMessage.id == message_id).first()

    def get_all_messages(
        self, status: AnonymousMessageStatus = None, limit: int = 50
    ) -> list[AnonymousMessage]:
        """Obtiene todos los mensajes, opcionalmente filtrados por estado."""
        db = self._get_db()
        query = db.query(AnonymousMessage)
        if status:
            query = query.filter(AnonymousMessage.status == status)
        return query.order_by(AnonymousMessage.created_at.desc()).limit(limit).all()

    def get_unread_messages(self) -> list[AnonymousMessage]:
        """Obtiene mensajes no leídos."""
        return self.get_all_messages(status=AnonymousMessageStatus.UNREAD)

    def mark_as_read(self, message_id: int, admin_id: int) -> bool:
        """Marca un mensaje como leído."""
        db = self._get_db()
        message = self.get_message(message_id)
        if message:
            message.status = AnonymousMessageStatus.READ
            message.read_at = datetime.now(UTC)
            message.read_by = admin_id
            db.commit()
            return True
        return False

    def reply_to_message(self, message_id: int, admin_id: int, reply: str) -> bool:
        """Agrega una respuesta de Diana a un mensaje."""
        db = self._get_db()
        message = self.get_message(message_id)
        if message:
            message.status = AnonymousMessageStatus.REPLIED
            message.admin_reply = reply
            message.replied_at = datetime.now(UTC)
            if not message.read_at:
                message.read_at = datetime.now(UTC)
                message.read_by = admin_id
            db.commit()
            return True
        return False

    def get_sender_info(self, message_id: int) -> User | None:
        """
        Obtiene información del remitente (solo para casos delicados).
        Esto debe usarse con precaución y solo cuando sea necesario.
        """
        self._get_db()
        message = self.get_message(message_id)
        if message and message.sender:
            return message.sender
        return None

    def get_message_count_by_status(self) -> dict:
        """Retorna conteo de mensajes por estado."""
        db = self._get_db()
        counts = {}
        for status in AnonymousMessageStatus:
            count = db.query(AnonymousMessage).filter(AnonymousMessage.status == status).count()
            counts[status.value] = count
        return counts

    def delete_message(self, message_id: int) -> bool:
        """Elimina un mensaje (solo para casos especiales)."""
        db = self._get_db()
        message = self.get_message(message_id)
        if message:
            db.delete(message)
            db.commit()
            return True
        return False
