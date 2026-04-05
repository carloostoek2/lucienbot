"""
Servicio de Mensajes Anónimos - Lucien Bot

Gestiona el envío y recepción de mensajes anónimos de suscriptores VIP a Diana.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from models.models import AnonymousMessage, AnonymousMessageStatus, User
from models.database import SessionLocal


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
            sender_id=sender_id,
            content=content,
            status=AnonymousMessageStatus.UNREAD
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    def get_message(self, message_id: int) -> Optional[AnonymousMessage]:
        """Obtiene un mensaje por ID."""
        db = self._get_db()
        return db.query(AnonymousMessage).filter(AnonymousMessage.id == message_id).first()

    def get_all_messages(self, status: AnonymousMessageStatus = None, limit: int = 50) -> List[AnonymousMessage]:
        """Obtiene todos los mensajes, opcionalmente filtrados por estado."""
        db = self._get_db()
        query = db.query(AnonymousMessage)
        if status:
            query = query.filter(AnonymousMessage.status == status)
        return query.order_by(AnonymousMessage.created_at.desc()).limit(limit).all()

    def get_unread_messages(self) -> List[AnonymousMessage]:
        """Obtiene mensajes no leídos."""
        return self.get_all_messages(status=AnonymousMessageStatus.UNREAD)

    def mark_as_read(self, message_id: int, admin_id: int) -> bool:
        """Marca un mensaje como leído."""
        db = self._get_db()
        message = self.get_message(message_id)
        if message:
            message.status = AnonymousMessageStatus.READ
            message.read_at = datetime.utcnow()
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
            message.replied_at = datetime.utcnow()
            if not message.read_at:
                message.read_at = datetime.utcnow()
                message.read_by = admin_id
            db.commit()
            return True
        return False

    def get_sender_info(self, message_id: int) -> Optional[User]:
        """
        Obtiene información del remitente (solo para casos delicados).
        Esto debe usarse con precaución y solo cuando sea necesario.
        """
        db = self._get_db()
        message = self.get_message(message_id)
        if message and message.sender:
            return message.sender
        return None

    def get_message_count_by_status(self) -> dict:
        """Retorna conteo de mensajes por estado."""
        db = self._get_db()
        counts = {}
        for status in AnonymousMessageStatus:
            count = db.query(AnonymousMessage).filter(
                AnonymousMessage.status == status
            ).count()
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
