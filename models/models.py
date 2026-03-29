"""
Modelos de datos - Lucien Bot
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, BigInteger, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base
import enum
import secrets
import string


class ChannelType(str, enum.Enum):
    """Tipos de canal"""
    FREE = "free"
    VIP = "vip"


class TokenStatus(str, enum.Enum):
    """Estados de un token"""
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"


class UserRole(str, enum.Enum):
    """Roles de usuario"""
    ADMIN = "admin"
    USER = "user"


class User(Base):
    """Modelo de usuario"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    tokens_redeemed = relationship("Token", back_populates="redeemed_by")


class Channel(Base):
    """Modelo de canal"""
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(BigInteger, unique=True, index=True, nullable=False)
    channel_name = Column(String(200), nullable=True)
    channel_type = Column(Enum(ChannelType), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Configuración específica para canal Free
    wait_time_minutes = Column(Integer, default=3)  # Tiempo de espera en minutos
    welcome_message = Column(Text, nullable=True)
    approval_message = Column(Text, nullable=True)
    
    # Relaciones
    subscriptions = relationship("Subscription", back_populates="channel")
    pending_requests = relationship("PendingRequest", back_populates="channel", cascade="all, delete-orphan")


class Tariff(Base):
    """Modelo de tarifa VIP"""
    __tablename__ = "tariffs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    duration_days = Column(Integer, nullable=False)
    price = Column(String(50), nullable=False)
    currency = Column(String(10), default="USD")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    tokens = relationship("Token", back_populates="tariff", cascade="all, delete-orphan")


class Token(Base):
    """Modelo de token de acceso VIP"""
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token_code = Column(String(64), unique=True, index=True, nullable=False)
    tariff_id = Column(Integer, ForeignKey("tariffs.id"), nullable=False)
    status = Column(Enum(TokenStatus), default=TokenStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    redeemed_at = Column(DateTime(timezone=True), nullable=True)
    redeemed_by_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=True)
    
    # Relaciones
    tariff = relationship("Tariff", back_populates="tokens")
    redeemed_by = relationship("User", back_populates="tokens_redeemed")
    subscriptions = relationship("Subscription", back_populates="token")
    
    @staticmethod
    def generate_token():
        """Genera un token único de 32 caracteres"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))


class Subscription(Base):
    """Modelo de suscripción VIP"""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    user = relationship("User", back_populates="subscriptions")
    channel = relationship("Channel", back_populates="subscriptions")
    token = relationship("Token", back_populates="subscriptions")


class PendingRequest(Base):
    """Modelo de solicitud pendiente de acceso al canal Free"""
    __tablename__ = "pending_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    status = Column(String(20), default="pending")  # pending, approved, cancelled
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    scheduled_approval_at = Column(DateTime(timezone=True), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relaciones
    channel = relationship("Channel", back_populates="pending_requests")


# ============================================================
# FASE 1: GAMIFICACIÓN - BESITOS, BROADCASTING, REGALO DIARIO
# ============================================================

class TransactionType(str, enum.Enum):
    """Tipos de transacción de besitos"""
    CREDIT = "credit"      # Entrada de besitos
    DEBIT = "debit"        # Salida de besitos


class TransactionSource(str, enum.Enum):
    """Fuentes de transacción de besitos"""
    REACTION = "reaction"          # Reacción a mensaje
    DAILY_GIFT = "daily_gift"      # Regalo diario
    MISSION = "mission"            # Recompensa por misión
    PURCHASE = "purchase"          # Compra en tienda
    ADMIN = "admin"                # Ajuste manual por admin


class BesitoBalance(Base):
    """Saldo de besitos por usuario"""
    __tablename__ = "besito_balances"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    balance = Column(Integer, default=0, nullable=False)
    total_earned = Column(Integer, default=0, nullable=False)  # Total acumulado histórico
    total_spent = Column(Integer, default=0, nullable=False)   # Total gastado histórico
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    transactions = relationship("BesitoTransaction", back_populates="balance", cascade="all, delete-orphan")


class BesitoTransaction(Base):
    """Historial de transacciones de besitos"""
    __tablename__ = "besito_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("besito_balances.user_id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # Positivo para crédito, negativo para débito
    type = Column(Enum(TransactionType), nullable=False)
    source = Column(Enum(TransactionSource), nullable=False)
    description = Column(String(255), nullable=True)  # Descripción del movimiento
    reference_id = Column(Integer, nullable=True)  # ID de referencia (misión, compra, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    balance = relationship("BesitoBalance", back_populates="transactions")


class ReactionEmoji(Base):
    """Configuración de emojis de reacción y sus valores"""
    __tablename__ = "reaction_emojis"
    
    id = Column(Integer, primary_key=True, index=True)
    emoji = Column(String(10), unique=True, nullable=False)  # El emoji mismo (💋, ❤️, etc.)
    name = Column(String(50), nullable=True)  # Nombre descriptivo
    besito_value = Column(Integer, default=1, nullable=False)  # Cuántos besitos otorga
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    broadcast_reactions = relationship("BroadcastReaction", back_populates="reaction_emoji")


class BroadcastMessage(Base):
    """Mensajes de broadcasting con reacciones"""
    __tablename__ = "broadcast_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(BigInteger, nullable=False, index=True)  # ID del mensaje en Telegram
    channel_id = Column(BigInteger, ForeignKey("channels.channel_id"), nullable=False)
    admin_id = Column(BigInteger, nullable=False)  # Quién envió el mensaje
    text = Column(Text, nullable=True)  # Texto del mensaje
    has_attachment = Column(Boolean, default=False)  # Si tiene foto/archivo adjunto
    attachment_type = Column(String(50), nullable=True)  # photo, video, document, etc.
    attachment_file_id = Column(String(500), nullable=True)  # ID del archivo en Telegram
    has_reactions = Column(Boolean, default=False)  # Si tiene botones de reacción
    is_protected = Column(Boolean, default=False)  # Protección contra copia/reenvío
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    reactions = relationship("BroadcastReaction", back_populates="broadcast", cascade="all, delete-orphan")


class BroadcastReaction(Base):
    """Reacciones de usuarios a mensajes de broadcast"""
    __tablename__ = "broadcast_reactions"
    
    id = Column(Integer, primary_key=True, index=True)
    broadcast_id = Column(Integer, ForeignKey("broadcast_messages.id"), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    reaction_emoji_id = Column(Integer, ForeignKey("reaction_emojis.id"), nullable=False)
    besitos_awarded = Column(Integer, nullable=False)  # Cuántos besitos se otorgaron
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    broadcast = relationship("BroadcastMessage", back_populates="reactions")
    reaction_emoji = relationship("ReactionEmoji", back_populates="broadcast_reactions")
    
    # Constraint único: un usuario solo puede reaccionar una vez por mensaje
    __table_args__ = (
        # No se puede usar UniqueConstraint directamente con SQLAlchemy 1.4/2.0 de esta forma
        # Se manejará a nivel de aplicación
    )


class DailyGiftConfig(Base):
    """Configuración del regalo diario"""
    __tablename__ = "daily_gift_config"
    
    id = Column(Integer, primary_key=True, index=True)
    besito_amount = Column(Integer, default=10, nullable=False)  # Cantidad de besitos
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(BigInteger, nullable=True)  # Admin que actualizó


class DailyGiftClaim(Base):
    """Registros de reclamos de regalo diario"""
    __tablename__ = "daily_gift_claims"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    besitos_received = Column(Integer, nullable=False)
    claimed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Para facilitar consultas de "último reclamo"
    __table_args__ = (
        # Índice compuesto para consultas eficientes
    )


# ============================================================
# FASE 2: PAQUETES (COMPONENTE COMPARTIDO)
# ============================================================

class Package(Base):
    """Paquetes de contenido (fotos/archivos) para tienda o recompensas"""
    __tablename__ = "packages"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Stock independiente para tienda y recompensas
    # -2 = no disponible, -1 = ilimitado, 0+ = stock limitado
    store_stock = Column(Integer, default=-1)
    reward_stock = Column(Integer, default=-1)
    
    is_active = Column(Boolean, default=True)
    created_by = Column(BigInteger, nullable=True)  # Admin que creó el paquete
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    files = relationship("PackageFile", back_populates="package", cascade="all, delete-orphan")
    
    @property
    def is_available_in_store(self) -> bool:
        """Verifica si está disponible en tienda"""
        if not self.is_active:
            return False
        if self.store_stock == -2:  # No disponible
            return False
        return self.store_stock == -1 or self.store_stock > 0
    
    @property
    def is_available_for_reward(self) -> bool:
        """Verifica si está disponible para recompensas"""
        if not self.is_active:
            return False
        if self.reward_stock == -2:  # No disponible
            return False
        return self.reward_stock == -1 or self.reward_stock > 0
    
    @property
    def store_stock_display(self) -> str:
        """Retorna texto legible del stock de tienda"""
        if self.store_stock == -2:
            return "No disponible"
        elif self.store_stock == -1:
            return "Ilimitado"
        else:
            return str(self.store_stock)
    
    @property
    def reward_stock_display(self) -> str:
        """Retorna texto legible del stock de recompensas"""
        if self.reward_stock == -2:
            return "No disponible"
        elif self.reward_stock == -1:
            return "Ilimitado"
        else:
            return str(self.reward_stock)
    
    @property
    def file_count(self) -> int:
        """Retorna la cantidad de archivos en el paquete"""
        return len(self.files) if self.files else 0
    
    def decrement_store_stock(self) -> bool:
        """Decrementa el stock de tienda. Retorna True si tuvo éxito."""
        if self.store_stock == -2:  # No disponible
            return False
        if self.store_stock == -1:  # Ilimitado
            return True
        if self.store_stock > 0:
            self.store_stock -= 1
            return True
        return False
    
    def decrement_reward_stock(self) -> bool:
        """Decrementa el stock de recompensas. Retorna True si tuvo éxito."""
        if self.reward_stock == -2:  # No disponible
            return False
        if self.reward_stock == -1:  # Ilimitado
            return True
        if self.reward_stock > 0:
            self.reward_stock -= 1
            return True
        return False


class PackageFile(Base):
    """Archivos individuales dentro de un paquete"""
    __tablename__ = "package_files"
    
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False, index=True)
    
    # Información del archivo en Telegram
    file_id = Column(String(500), nullable=False)  # ID del archivo en Telegram
    file_type = Column(String(50), nullable=False)  # photo, video, document, animation
    file_name = Column(String(255), nullable=True)  # Nombre original del archivo
    file_size = Column(Integer, nullable=True)  # Tamaño en bytes
    
    # Orden para mantener secuencia
    order_index = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    package = relationship("Package", back_populates="files")


# ============================================================
# FASE 3: MISIONES Y RECOMPENSAS
# ============================================================

class MissionType(str, enum.Enum):
    """Tipos de misiones soportados"""
    REACTION_COUNT = "reaction_count"           # Reaccionar N veces
    DAILY_GIFT_STREAK = "daily_gift_streak"     # Reclamar regalo N dias (consecutivos)
    DAILY_GIFT_TOTAL = "daily_gift_total"       # Reclamar regalo N dias (acumulados)
    STORE_PURCHASE = "store_purchase"           # Comprar en tienda
    VIP_ACTIVE = "vip_active"                   # Tener suscripcion VIP activa


class MissionFrequency(str, enum.Enum):
    """Frecuencia de la mision"""
    ONE_TIME = "one_time"       # Se completa una sola vez
    RECURRING = "recurring"     # Se reinicia al completarse


class Mission(Base):
    """Misiones configuradas por el administrador"""
    __tablename__ = "missions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Tipo y configuracion
    mission_type = Column(Enum(MissionType), nullable=False)
    target_value = Column(Integer, default=1, nullable=False)  # Meta numerica
    
    # Frecuencia y vigencia
    frequency = Column(Enum(MissionFrequency), default=MissionFrequency.ONE_TIME)
    start_date = Column(DateTime(timezone=True), nullable=True)  # None = sin fecha inicio
    end_date = Column(DateTime(timezone=True), nullable=True)    # None = sin fecha fin
    
    # Estado
    is_active = Column(Boolean, default=True)
    created_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Recompensa asociada
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=True)
    
    # Relaciones
    reward = relationship("Reward", back_populates="missions")
    user_progress = relationship("UserMissionProgress", back_populates="mission", cascade="all, delete-orphan")
    
    @property
    def is_available(self) -> bool:
        """Verifica si la mision esta disponible actualmente"""
        if not self.is_active:
            return False
        
        from datetime import datetime
        now = datetime.utcnow()
        
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        
        return True


class UserMissionProgress(Base):
    """Progreso de cada usuario en las misiones"""
    __tablename__ = "user_mission_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False, index=True)
    
    # Progreso
    current_value = Column(Integer, default=0, nullable=False)
    target_value = Column(Integer, nullable=False)
    is_completed = Column(Boolean, default=False)
    
    # Fechas
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    mission = relationship("Mission", back_populates="user_progress")


class RewardType(str, enum.Enum):
    """Tipos de recompensas"""
    BESITOS = "besitos"         # Cantidad de besitos
    PACKAGE = "package"         # Paquete de contenido
    VIP_ACCESS = "vip_access"   # Acceso VIP


class Reward(Base):
    """Recompensas configuradas por el administrador"""
    __tablename__ = "rewards"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Tipo y contenido
    reward_type = Column(Enum(RewardType), nullable=False)
    
    # Configuracion segun tipo
    besito_amount = Column(Integer, nullable=True)      # Para tipo BESITOS
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=True)  # Para tipo PACKAGE
    tariff_id = Column(Integer, ForeignKey("tariffs.id"), nullable=True)    # Para tipo VIP_ACCESS
    
    # Estado
    is_active = Column(Boolean, default=True)
    created_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    missions = relationship("Mission", back_populates="reward")
    package = relationship("Package")
    tariff = relationship("Tariff")


class UserRewardHistory(Base):
    """Historial de recompensas entregadas a usuarios"""
    __tablename__ = "user_reward_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=False)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=True)  # None si fue de tienda
    
    # Detalles de la entrega
    delivered_at = Column(DateTime(timezone=True), server_default=func.now())
    details = Column(Text, nullable=True)  # JSON con detalles de la entrega


# ============================================================
# FASE 4: TIENDA
# ============================================================

class StoreProduct(Base):
    """Productos disponibles en la tienda"""
    __tablename__ = "store_products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Relacion con paquete
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False)
    
    # Precio en besitos
    price = Column(Integer, nullable=False)
    
    # Stock (-1 = ilimitado, 0+ = stock limitado)
    stock = Column(Integer, default=-1)
    
    # Estado
    is_active = Column(Boolean, default=True)
    created_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    package = relationship("Package")
    cart_items = relationship("CartItem", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")
    
    @property
    def is_available(self) -> bool:
        """Verifica si el producto esta disponible"""
        if not self.is_active:
            return False
        if self.stock == 0:
            return False
        return True
    
    @property
    def stock_display(self) -> str:
        """Retorna texto legible del stock"""
        if self.stock == -1:
            return "Ilimitado"
        return str(self.stock)
    
    def decrement_stock(self, amount: int = 1) -> bool:
        """Decrementa el stock. Retorna True si tuvo exito."""
        if self.stock == -1:  # Ilimitado
            return True
        if self.stock >= amount:
            self.stock -= amount
            return True
        return False


class CartItem(Base):
    """Items en el carrito de compras de un usuario"""
    __tablename__ = "cart_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("store_products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    product = relationship("StoreProduct", back_populates="cart_items")


class OrderStatus(str, enum.Enum):
    """Estados de una orden"""
    PENDING = "pending"      # Pendiente de pago/confirmacion
    COMPLETED = "completed"  # Completada y entregada
    CANCELLED = "cancelled"  # Cancelada


class Order(Base):
    """Ordenes de compra en la tienda"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    
    # Totales
    total_items = Column(Integer, default=0)
    total_price = Column(Integer, default=0)
    
    # Estado
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    
    # Fechas
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relaciones
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """Items dentro de una orden"""
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("store_products.id"), nullable=False)
    
    # Detalles al momento de la compra
    product_name = Column(String(200), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Integer, nullable=False)
    total_price = Column(Integer, nullable=False)
    
    # Relaciones
    order = relationship("Order", back_populates="items")
    product = relationship("StoreProduct", back_populates="order_items")
