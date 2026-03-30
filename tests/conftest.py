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
sys.path.insert(0, '/data/data/com.termux/files/home/repos/lucien_bot/.claude/worktrees/agent-a3b85150')

from models.database import Base
from models.models import (
    User, UserRole, Channel, ChannelType, Tariff, Token, TokenStatus,
    Subscription, BesitoBalance, Mission, MissionType, MissionFrequency,
    UserMissionProgress, PendingRequest
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
    """Crea un balance de besitos de prueba."""
    balance = BesitoBalance(
        user_id=sample_user.id,
        balance=1000,
        total_earned=1500,
        total_spent=500
    )
    db_session.add(balance)
    db_session.commit()
    db_session.refresh(balance)
    return balance


@pytest.fixture
def sample_mission(db_session: Session):
    """Crea una misión de prueba."""
    mission = Mission(
        name="Test Mission",
        description="A test mission",
        mission_type=MissionType.SEND_BESITOS,
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


# ==================== MOCK FIXTURES ====================

@pytest.fixture
def mock_bot():
    """Crea un mock del bot de Telegram."""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.ban_chat_member = AsyncMock()
    bot.unban_chat_member = AsyncMock()
    bot.create_chat_invite_link = AsyncMock(return_value=MagicMock(invite_link="https://t.me/+NewInviteLink"))
    return bot


@pytest.fixture
def mock_dispatcher():
    """Crea un mock del dispatcher."""
    dp = MagicMock()
    return dp
