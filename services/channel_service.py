"""
Servicio de Canales - Lucien Bot

Gestiona la lógica de canales Free y VIP.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from models.models import Channel, ChannelType, PendingRequest, User
from models.database import SessionLocal


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

    def create_channel(self, channel_id: int, channel_name: str,
                       channel_type: ChannelType, wait_time: int = 3) -> Channel:
        """Crea un nuevo canal"""
        db = self._get_db()
        channel = Channel(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_type=channel_type,
            wait_time_minutes=wait_time if channel_type == ChannelType.FREE else 0
        )
        db.add(channel)
        db.commit()
        db.refresh(channel)
        return channel

    def get_channel_by_id(self, channel_id: int) -> Optional[Channel]:
        """Obtiene un canal por su ID de Telegram"""
        db = self._get_db()
        return db.query(Channel).filter(
            Channel.channel_id == channel_id
        ).first()

    def get_channel_by_db_id(self, db_id: int) -> Optional[Channel]:
        """Obtiene un canal por su ID de base de datos"""
        db = self._get_db()
        return db.query(Channel).filter(Channel.id == db_id).first()

    def get_all_channels(self) -> List[Channel]:
        """Obtiene todos los canales"""
        db = self._get_db()
        return db.query(Channel).filter(Channel.is_active == True).all()

    def get_free_channels(self) -> List[Channel]:
        """Obtiene todos los canales Free"""
        db = self._get_db()
        return db.query(Channel).filter(
            Channel.channel_type == ChannelType.FREE,
            Channel.is_active == True
        ).all()

    def get_vip_channels(self) -> List[Channel]:
        """Obtiene todos los canales VIP"""
        db = self._get_db()
        return db.query(Channel).filter(
            Channel.channel_type == ChannelType.VIP,
            Channel.is_active == True
        ).all()

    def delete_channel(self, channel_id: int) -> bool:
        """Elimina (desactiva) un canal"""
        db = self._get_db()
        channel = self.get_channel_by_db_id(channel_id)
        if channel:
            channel.is_active = False
            db.commit()
            return True
        return False

    def update_wait_time(self, channel_id: int, minutes: int) -> bool:
        """Actualiza el tiempo de espera de un canal Free"""
        db = self._get_db()
        channel = self.get_channel_by_db_id(channel_id)
        if channel and channel.channel_type == ChannelType.FREE:
            channel.wait_time_minutes = minutes
            db.commit()
            return True
        return False

    # ==================== SOLICITUDES PENDIENTES ====================

    def create_pending_request(self, user_id: int, channel_id: int,
                               username: str = None, first_name: str = None) -> PendingRequest:
        """Crea una solicitud pendiente de acceso"""
        db = self._get_db()
        channel = self.get_channel_by_db_id(channel_id)
        if not channel:
            raise ValueError("Canal no encontrado")

        scheduled_time = datetime.utcnow() + timedelta(minutes=channel.wait_time_minutes)

        request = PendingRequest(
            user_id=user_id,
            channel_id=channel_id,
            username=username,
            first_name=first_name,
            scheduled_approval_at=scheduled_time
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        return request

    def get_pending_request(self, user_id: int, channel_id: int) -> Optional[PendingRequest]:
        """Obtiene una solicitud pendiente específica"""
        db = self._get_db()
        return db.query(PendingRequest).filter(
            PendingRequest.user_id == user_id,
            PendingRequest.channel_id == channel_id,
            PendingRequest.status == "pending"
        ).first()

    def get_pending_requests_by_channel(self, channel_id: int) -> List[PendingRequest]:
        """Obtiene todas las solicitudes pendientes de un canal"""
        db = self._get_db()
        return db.query(PendingRequest).filter(
            PendingRequest.channel_id == channel_id,
            PendingRequest.status == "pending"
        ).all()

    def get_all_pending_requests(self) -> List[PendingRequest]:
        """Obtiene todas las solicitudes pendientes"""
        db = self._get_db()
        return db.query(PendingRequest).filter(
            PendingRequest.status == "pending"
        ).all()

    def get_ready_to_approve(self) -> List[PendingRequest]:
        """Obtiene solicitudes listas para aprobar (tiempo vencido)"""
        db = self._get_db()
        now = datetime.utcnow()
        return db.query(PendingRequest).filter(
            PendingRequest.status == "pending",
            PendingRequest.scheduled_approval_at <= now
        ).all()

    def approve_request(self, request_id: int) -> bool:
        """Aprueba una solicitud específica"""
        db = self._get_db()
        request = db.query(PendingRequest).filter(
            PendingRequest.id == request_id
        ).first()
        if request:
            request.status = "approved"
            request.approved_at = datetime.utcnow()
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
        """Aprueba todas las solicitudes pendientes"""
        db = self._get_db()
        query = db.query(PendingRequest).filter(PendingRequest.status == "pending")
        if channel_id:
            query = query.filter(PendingRequest.channel_id == channel_id)

        requests = query.all()
        count = 0
        for req in requests:
            req.status = "approved"
            req.approved_at = datetime.utcnow()
            count += 1

        db.commit()
        return count

    def count_pending_requests(self, channel_id: int = None) -> int:
        """Cuenta solicitudes pendientes"""
        db = self._get_db()
        query = db.query(PendingRequest).filter(PendingRequest.status == "pending")
        if channel_id:
            query = query.filter(PendingRequest.channel_id == channel_id)
        return query.count()
