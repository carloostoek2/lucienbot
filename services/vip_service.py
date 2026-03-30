"""
Servicio VIP - Lucien Bot

Gestiona la lógica de tokens, tarifas y suscripciones VIP.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from models.models import Tariff, Token, TokenStatus, Subscription, Channel, ChannelType, User
from models.database import SessionLocal


class VIPService:
    """Servicio para gestión VIP"""
    
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
    
    # ==================== TARIFAS ====================
    
    def create_tariff(self, name: str, duration_days: int, 
                      price: str, currency: str = "USD") -> Tariff:
        """Crea una nueva tarifa VIP"""
        tariff = Tariff(
            name=name,
            duration_days=duration_days,
            price=price,
            currency=currency
        )
        self.db.add(tariff)
        self.db.commit()
        self.db.refresh(tariff)
        return tariff
    
    def get_tariff(self, tariff_id: int) -> Optional[Tariff]:
        """Obtiene una tarifa por ID"""
        return self.db.query(Tariff).filter(Tariff.id == tariff_id).first()
    
    def get_all_tariffs(self, active_only: bool = True) -> List[Tariff]:
        """Obtiene todas las tarifas"""
        query = self.db.query(Tariff)
        if active_only:
            query = query.filter(Tariff.is_active == True)
        return query.all()
    
    def update_tariff(self, tariff_id: int, **kwargs) -> bool:
        """Actualiza una tarifa"""
        tariff = self.get_tariff(tariff_id)
        if tariff:
            for key, value in kwargs.items():
                if hasattr(tariff, key):
                    setattr(tariff, key, value)
            self.db.commit()
            return True
        return False
    
    def deactivate_tariff(self, tariff_id: int) -> bool:
        """Desactiva una tarifa"""
        return self.update_tariff(tariff_id, is_active=False)
    
    # ==================== TOKENS ====================
    
    def generate_token(self, tariff_id: int, expires_in_days: int = None) -> Token:
        """Genera un nuevo token para una tarifa"""
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
        
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token
    
    def get_token_by_code(self, token_code: str) -> Optional[Token]:
        """Obtiene un token por su código"""
        return self.db.query(Token).filter(Token.token_code == token_code).first()
    
    def get_token(self, token_id: int) -> Optional[Token]:
        """Obtiene un token por ID"""
        return self.db.query(Token).filter(Token.id == token_id).first()
    
    def get_tokens_by_tariff(self, tariff_id: int) -> List[Token]:
        """Obtiene todos los tokens de una tarifa"""
        return self.db.query(Token).filter(Token.tariff_id == tariff_id).all()
    
    def get_all_tokens(self, status: TokenStatus = None) -> List[Token]:
        """Obtiene todos los tokens"""
        query = self.db.query(Token)
        if status:
            query = query.filter(Token.status == status)
        return query.order_by(Token.created_at.desc()).all()
    
    def validate_token(self, token_code: str) -> tuple:
        """
        Valida un token y retorna (token, mensaje_error)
        Si es válido, retorna (token, None)
        """
        token = self.get_token_by_code(token_code)
        
        if not token:
            return None, "invalid"
        
        if token.status == TokenStatus.USED:
            return None, "used"
        
        if token.status == TokenStatus.EXPIRED:
            return None, "expired"
        
        if token.expires_at and token.expires_at < datetime.utcnow():
            token.status = TokenStatus.EXPIRED
            self.db.commit()
            return None, "expired"
        
        return token, None
    
    def redeem_token(self, token_code: str, user_id: int) -> Optional[Subscription]:
        """
        Canjea un token y crea una suscripción
        Retorna la suscripción creada o None si falla
        """
        token, error = self.validate_token(token_code)
        if error:
            return None
        
        # Marcar token como usado
        token.status = TokenStatus.USED
        token.redeemed_at = datetime.utcnow()
        token.redeemed_by_id = user_id
        
        # Crear suscripción
        tariff = token.tariff
        end_date = datetime.utcnow() + timedelta(days=tariff.duration_days)
        
        # Buscar canal VIP (asumimos el primero disponible o se especifica)
        vip_channel = self.db.query(Channel).filter(
            Channel.channel_type == ChannelType.VIP,
            Channel.is_active == True
        ).first()
        
        if not vip_channel:
            self.db.rollback()
            return None
        
        subscription = Subscription(
            user_id=user_id,
            channel_id=vip_channel.id,
            token_id=token.id,
            end_date=end_date
        )
        
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription
    
    def revoke_token(self, token_id: int) -> bool:
        """Revoca un token activo"""
        token = self.get_token(token_id)
        if token and token.status == TokenStatus.ACTIVE:
            token.status = TokenStatus.EXPIRED
            self.db.commit()
            return True
        return False
    
    # ==================== SUSCRIPCIONES ====================
    
    def get_subscription(self, subscription_id: int) -> Optional[Subscription]:
        """Obtiene una suscripción por ID"""
        return self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
    
    def get_user_subscription(self, user_id: int, channel_id: int = None) -> Optional[Subscription]:
        """Obtiene la suscripción activa de un usuario"""
        query = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.is_active == True
        )
        if channel_id:
            query = query.filter(Subscription.channel_id == channel_id)
        return query.first()
    
    def get_active_subscriptions(self, channel_id: int = None) -> List[Subscription]:
        """Obtiene todas las suscripciones activas"""
        query = self.db.query(Subscription).filter(Subscription.is_active == True)
        if channel_id:
            query = query.filter(Subscription.channel_id == channel_id)
        return query.all()
    
    def get_expiring_subscriptions(self, hours: int = 24) -> List[Subscription]:
        """Obtiene suscripciones que vencen en las próximas X horas"""
        now = datetime.utcnow()
        threshold = now + timedelta(hours=hours)
        
        return self.db.query(Subscription).filter(
            Subscription.is_active == True,
            Subscription.reminder_sent == False,
            Subscription.end_date <= threshold,
            Subscription.end_date > now
        ).all()
    
    def get_expired_subscriptions(self) -> List[Subscription]:
        """Obtiene suscripciones que ya vencieron"""
        now = datetime.utcnow()
        return self.db.query(Subscription).filter(
            Subscription.is_active == True,
            Subscription.end_date < now
        ).all()
    
    def mark_reminder_sent(self, subscription_id: int) -> bool:
        """Marca que se envió el recordatorio de renovación"""
        subscription = self.get_subscription(subscription_id)
        if subscription:
            subscription.reminder_sent = True
            self.db.commit()
            return True
        return False
    
    def expire_subscription(self, subscription_id: int) -> bool:
        """Desactiva una suscripción vencida"""
        subscription = self.get_subscription(subscription_id)
        if subscription:
            subscription.is_active = False
            self.db.commit()
            return True
        return False
    
    def is_user_vip(self, user_id: int, channel_id: int = None) -> bool:
        """Verifica si un usuario tiene suscripción VIP activa"""
        subscription = self.get_user_subscription(user_id, channel_id)
        return subscription is not None

    def get_vip_channel(self) -> Optional[Channel]:
        """Obtiene el canal VIP activo"""
        return self.db.query(Channel).filter(
            Channel.channel_type == ChannelType.VIP,
            Channel.is_active == True
        ).first()
    
    def __del__(self):
        """Cierra la sesión de base de datos"""
        if hasattr(self, 'db'):
            self.db.close()
