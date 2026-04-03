"""
Fixtures y configuración para tests de Lucien Bot.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from unittest.mock import MagicMock, AsyncMock

# Importar modelos
import sys
sys.path.insert(0, '/data/data/com.termux/files/home/repos/lucien_bot')

from models.database import Base
from models.models import (
    User, UserRole, Channel, ChannelType, Tariff, Token, TokenStatus,
    Subscription, BesitoBalance, Mission, MissionType, MissionFrequency,
    UserMissionProgress, PendingRequest,
    StoreProduct, Package, Promotion, PromotionStatus, ReactionEmoji,
    BroadcastMessage, StoryNode, StoryChoice, NodeType, Archetype,
    ArchetypeType, DailyGiftConfig, DailyGiftClaim, CartItem, Order,
    OrderStatus, Reward, RewardType
)


# ==================== DATABASE FIXTURES ====================

@pytest.fixture(scope="session")
def engine():
    """Crea un engine de SQLite en memoria para tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(engine):
    """Crea una sesión de base de datos limpia para cada test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ==================== MODEL FIXTURES ====================

@pytest.fixture
def sample_user(db_session: Session):
    """Crea un usuario de prueba."""
    user = User(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        role=UserRole.USER
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_admin(db_session: Session):
    """Crea un usuario admin de prueba."""
    user = User(
        telegram_id=987654321,
        username="adminuser",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_vip_channel(db_session: Session):
    """Crea un canal VIP de prueba."""
    channel = Channel(
        channel_id=-1001234567890,
        channel_name="Canal VIP Test",
        channel_type=ChannelType.VIP,
        is_active=True,
        invite_link="https://t.me/+TestInviteLink"
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    return channel


@pytest.fixture
def sample_free_channel(db_session: Session):
    """Crea un canal Free de prueba."""
    channel = Channel(
        channel_id=-1000987654321,
        channel_name="Canal Free Test",
        channel_type=ChannelType.FREE,
        is_active=True,
        wait_time_minutes=3
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    return channel


@pytest.fixture
def sample_tariff(db_session: Session):
    """Crea una tarifa de prueba."""
    tariff = Tariff(
        name="Test Tariff",
        duration_days=30,
        price="9.99",
        currency="USD",
        is_active=True
    )
    db_session.add(tariff)
    db_session.commit()
    db_session.refresh(tariff)
    return tariff


@pytest.fixture
def sample_token(db_session: Session, sample_tariff):
    """Crea un token activo de prueba."""
    token = Token(
        token_code="TEST123456",
        tariff_id=sample_tariff.id,
        status=TokenStatus.ACTIVE
    )
    db_session.add(token)
    db_session.commit()
    db_session.refresh(token)
    return token


@pytest.fixture
def sample_used_token(db_session: Session, sample_tariff, sample_user):
    """Crea un token usado de prueba."""
    token = Token(
        token_code="USED123456",
        tariff_id=sample_tariff.id,
        status=TokenStatus.USED,
        redeemed_by_id=sample_user.id,
        redeemed_at=datetime.utcnow()
    )
    db_session.add(token)
    db_session.commit()
    db_session.refresh(token)
    return token


@pytest.fixture
def sample_expired_token(db_session: Session, sample_tariff):
    """Crea un token expirado de prueba."""
    token = Token(
        token_code="EXPIRED123",
        tariff_id=sample_tariff.id,
        status=TokenStatus.EXPIRED,
        expires_at=datetime.utcnow() - timedelta(days=1)
    )
    db_session.add(token)
    db_session.commit()
    db_session.refresh(token)
    return token


@pytest.fixture
def sample_subscription(db_session: Session, sample_user, sample_vip_channel, sample_token):
    """Crea una suscripción activa de prueba."""
    subscription = Subscription(
        user_id=sample_user.id,
        channel_id=sample_vip_channel.id,
        token_id=sample_token.id,
        end_date=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)
    return subscription


@pytest.fixture
def sample_expired_subscription(db_session: Session, sample_user, sample_vip_channel, sample_token):
    """Crea una suscripción expirada de prueba."""
    subscription = Subscription(
        user_id=sample_user.id,
        channel_id=sample_vip_channel.id,
        token_id=sample_token.id,
        end_date=datetime.utcnow() - timedelta(days=1),
        is_active=True  # Aún marcada como activa, debería ser corregida por el startup check
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)
    return subscription


@pytest.fixture
def sample_balance(db_session: Session, sample_user):
    """Crea un balance de besitos de prueba con valores específicos."""
    balance = BesitoBalance(
        user_id=sample_user.id,
        balance=1000,
        total_earned=1500,
        total_spent=500
    )
    db_session.add(balance)
    db_session.commit()
    return balance


@pytest.fixture
def sample_mission(db_session: Session):
    """Crea una misión de prueba."""
    mission = Mission(
        name="Test Mission",
        description="A test mission",
        mission_type=MissionType.REACTION_COUNT,
        target_value=10,
        frequency=MissionFrequency.ONE_TIME,
        is_active=True
    )
    db_session.add(mission)
    db_session.commit()
    db_session.refresh(mission)
    return mission


@pytest.fixture
def sample_mission_progress(db_session: Session, sample_user, sample_mission):
    """Crea un progreso de misión de prueba."""
    progress = UserMissionProgress(
        user_id=sample_user.id,
        mission_id=sample_mission.id,
        target_value=sample_mission.target_value,
        current_value=5,
        is_completed=False
    )
    db_session.add(progress)
    db_session.commit()
    db_session.refresh(progress)
    return progress


@pytest.fixture
def sample_pending_request(db_session: Session, sample_user, sample_free_channel):
    """Crea una solicitud pendiente de prueba."""
    request = PendingRequest(
        user_id=sample_user.id,
        channel_id=sample_free_channel.id,
        username="testuser",
        first_name="Test",
        scheduled_approval_at=datetime.utcnow() + timedelta(minutes=3)
    )
    db_session.add(request)
    db_session.commit()
    db_session.refresh(request)
    return request


@pytest.fixture
def sample_package(db_session: Session):
    """Crea un paquete de prueba."""
    package = Package(
        name="Test Package",
        description="A test package",
        store_stock=10,
        reward_stock=5,
        is_active=True
    )
    db_session.add(package)
    db_session.commit()
    db_session.refresh(package)
    return package


@pytest.fixture
def sample_store_product(db_session: Session, sample_package):
    """Crea un producto de tienda de prueba."""
    product = StoreProduct(
        name="Test Product",
        description="A product",
        package_id=sample_package.id,
        price=100,
        stock=10,
        is_active=True
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture
def sample_promotion(db_session: Session, sample_package):
    """Crea una promoción de prueba."""
    promotion = Promotion(
        name="Test Promo",
        description="A promo",
        package_id=sample_package.id,
        price_mxn=99900,
        is_active=True,
        status=PromotionStatus.ACTIVE
    )
    db_session.add(promotion)
    db_session.commit()
    db_session.refresh(promotion)
    return promotion


@pytest.fixture
def sample_reaction_emoji(db_session: Session):
    """Crea un emoji de reacción de prueba."""
    emoji = ReactionEmoji(
        emoji="💋",
        name="besito",
        besito_value=1,
        is_active=True
    )
    db_session.add(emoji)
    db_session.commit()
    db_session.refresh(emoji)
    return emoji


@pytest.fixture
def sample_broadcast_message(db_session: Session, sample_free_channel, sample_admin):
    """Crea un mensaje de broadcast de prueba."""
    message = BroadcastMessage(
        message_id=1001,
        channel_id=sample_free_channel.channel_id,
        admin_id=sample_admin.telegram_id,
        text="Test broadcast",
        has_reactions=True
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    return message


@pytest.fixture
def sample_story_node(db_session: Session):
    """Crea un nodo de historia de prueba."""
    node = StoryNode(
        title="Test Node",
        content="Test content",
        node_type=NodeType.NARRATIVE,
        chapter=1,
        is_active=True,
        is_starting_node=True
    )
    db_session.add(node)
    db_session.commit()
    db_session.refresh(node)
    return node


@pytest.fixture
def sample_story_choice(db_session: Session, sample_story_node):
    """Crea una opción de historia de prueba."""
    choice = StoryChoice(
        node_id=sample_story_node.id,
        text="Go forward",
        next_node_id=None,
        archetype_points=0
    )
    db_session.add(choice)
    db_session.commit()
    db_session.refresh(choice)
    return choice


@pytest.fixture
def sample_archetype(db_session: Session):
    """Crea un arquetipo de prueba."""
    archetype = Archetype(
        archetype_type=ArchetypeType.EXPLORADOR,
        name="El Explorador",
        description="Curioso y aventurero",
        traits='["curiosidad","aventura"]'
    )
    db_session.add(archetype)
    db_session.commit()
    db_session.refresh(archetype)
    return archetype


@pytest.fixture
def sample_daily_gift_config(db_session: Session):
    """Crea una configuración de regalo diario de prueba."""
    config = DailyGiftConfig(
        besito_amount=10,
        is_active=True
    )
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)
    return config


@pytest.fixture
def sample_cart_item(db_session: Session, sample_user, sample_store_product):
    """Crea un item de carrito de prueba."""
    item = CartItem(
        user_id=sample_user.id,
        product_id=sample_store_product.id,
        quantity=1
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture
def sample_order(db_session: Session, sample_user):
    """Crea una orden de prueba."""
    order = Order(
        user_id=sample_user.id,
        total_items=1,
        total_price=100,
        status=OrderStatus.PENDING
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.fixture
def sample_reward_besitos(db_session: Session):
    """Crea una recompensa de besitos de prueba."""
    reward = Reward(
        name="Test Reward",
        description="A reward",
        reward_type=RewardType.BESITOS,
        besito_amount=50,
        is_active=True
    )
    db_session.add(reward)
    db_session.commit()
    db_session.refresh(reward)
    return reward




@pytest.fixture
def sample_package(db_session: Session):
    """Crea un paquete de prueba."""
    package = Package(
        name="Test Package",
        description="A test package",
        store_stock=-1,
        reward_stock=-1,
        is_active=True
    )
    db_session.add(package)
    db_session.commit()
    db_session.refresh(package)
    return package


@pytest.fixture
def sample_promotion(db_session: Session, sample_package):
    """Crea una promocion de prueba."""
    promotion = Promotion(
        name="Test Promotion",
        description="A test promotion",
        package_id=sample_package.id,
        price_mxn=99900,
        status=PromotionStatus.ACTIVE,
        is_active=True
    )
    db_session.add(promotion)
    db_session.commit()
    db_session.refresh(promotion)
    return promotion


@pytest.fixture
def sample_reaction_emoji(db_session: Session):
    """Crea un emoji de reaccion de prueba."""
    emoji = ReactionEmoji(
        emoji="\U0001f48b",
        name="beso",
        besito_value=5,
        is_active=True
    )
    db_session.add(emoji)
    db_session.commit()
    db_session.refresh(emoji)
    return emoji


@pytest.fixture
def sample_broadcast_message(db_session: Session, sample_free_channel):
    """Crea un mensaje de broadcast de prueba."""
    broadcast = BroadcastMessage(
        message_id=12345,
        channel_id=sample_free_channel.channel_id,
        admin_id=987654321,
        text="Test broadcast",
        has_reactions=True
    )
    db_session.add(broadcast)
    db_session.commit()
    db_session.refresh(broadcast)
    return broadcast

# ==================== MOCK FIXTURES ====================

@pytest.fixture
def mock_bot():
    """Crea un mock del bot de Telegram."""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.send_video = AsyncMock()
    bot.send_animation = AsyncMock()
    bot.send_document = AsyncMock()
    bot.ban_chat_member = AsyncMock()
    bot.unban_chat_member = AsyncMock()
    bot.create_chat_invite_link = AsyncMock(return_value=MagicMock(invite_link="https://t.me/+NewInviteLink"))
    return bot


@pytest.fixture
def mock_dispatcher():
    """Crea un mock del dispatcher."""
    dp = MagicMock()
    return dp
