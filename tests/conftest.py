"""
Fixtures y configuración para tests de Lucien Bot.
"""

# Importar modelos
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.database import Base
from models.models import (
    Archetype,
    ArchetypeType,
    BesitoBalance,
    BroadcastMessage,
    CartItem,
    Category,
    Channel,
    ChannelType,
    DailyGiftConfig,
    Mission,
    MissionFrequency,
    MissionType,
    NodeType,
    NurtureAudience,
    NurtureSequence,
    NurtureStep,
    Order,
    OrderStatus,
    Package,
    PendingRequest,
    Promotion,
    PromotionStatus,
    ReactionEmoji,
    Reward,
    RewardType,
    StoreProduct,
    StoryChoice,
    StoryNode,
    Subscription,
    Tariff,
    Token,
    TokenStatus,
    User,
    UserMissionProgress,
    UserNurtureProgress,
    UserRole,
)

# ==================== DATABASE FIXTURES ====================


@pytest.fixture(scope="session")
def engine():
    """Crea un engine de SQLite en memoria para tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(engine):
    """Crea una sesión de base de datos limpia para cada test."""
    connection = engine.connect()
    transaction = connection.begin()
    # expire_on_commit=False evita que SQLAlchemy expire los objetos del identity map
    # después de cada commit() interno de los servicios (BroadcastService, MissionService,
    # RewardService, BesitoService, etc.). Esto previene DetachedInstanceError cuando
    # los tests acceden a fixtures como sample_user después de flujos con múltiples commits.
    session = sessionmaker(bind=connection, expire_on_commit=False)()

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
        role=UserRole.USER,
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
        role=UserRole.ADMIN,
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
        invite_link="https://t.me/+TestInviteLink",
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
        wait_time_minutes=3,
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    return channel


@pytest.fixture
def sample_tariff(db_session: Session):
    """Crea una tarifa de prueba."""
    tariff = Tariff(
        name="Test Tariff", duration_days=30, price="9.99", currency="USD", is_active=True
    )
    db_session.add(tariff)
    db_session.commit()
    db_session.refresh(tariff)
    return tariff


@pytest.fixture
def sample_token(db_session: Session, sample_tariff):
    """Crea un token activo de prueba."""
    token = Token(token_code="TEST123456", tariff_id=sample_tariff.id, status=TokenStatus.ACTIVE)
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
        redeemed_by_id=sample_user.telegram_id,
        redeemed_at=datetime.now(UTC),
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
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(token)
    db_session.commit()
    db_session.refresh(token)
    return token


@pytest.fixture
def sample_subscription(db_session: Session, sample_user, sample_vip_channel, sample_token):
    """Crea una suscripción activa de prueba. DESIRED CONTRACT: user_id stores TG BigInt (telegram_id) per model FK to users.telegram_id and real handler flows (user.id from TG); channel_id=DB PK; explicit aware datetimes."""
    subscription = Subscription(
        user_id=sample_user.telegram_id,
        channel_id=sample_vip_channel.id,
        token_id=sample_token.id,
        end_date=datetime.now(UTC) + timedelta(days=30),
        is_active=True,
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)
    return subscription


@pytest.fixture
def sample_expired_subscription(db_session: Session, sample_user, sample_vip_channel, sample_token):
    """Crea una suscripción expirada de prueba. DESIRED CONTRACT: user_id=telegram_id (TG value); active flag + past end for scheduler tests."""
    subscription = Subscription(
        user_id=sample_user.telegram_id,
        channel_id=sample_vip_channel.id,
        token_id=sample_token.id,
        end_date=datetime.now(UTC) - timedelta(days=1),
        is_active=True,  # Aún marcada como activa, debería ser corregida por el startup check
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)
    return subscription


@pytest.fixture
def sample_balance(db_session: Session, sample_user):
    """Crea un balance de besitos de prueba con valores específicos.
    DESIRED CONTRACT: user_id stores TG BigInt (telegram_id value) per models (BesitoBalance.user_id BigInteger, no FK to users.id/PK), real handler flows (from_user.id), besito_service credit/debit keys, and VIP/channel ID contract fixes. Matches sample_user.telegram_id; never the internal PK .id."""
    balance = BesitoBalance(
        user_id=sample_user.telegram_id, balance=1000, total_earned=1500, total_spent=500
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
        is_active=True,
    )
    db_session.add(mission)
    db_session.commit()
    db_session.refresh(mission)
    return mission


@pytest.fixture
def sample_mission_progress(db_session: Session, sample_user, sample_mission):
    """Crea un progreso de misión de prueba.
    DESIRED CONTRACT: user_id stores TG BigInt (telegram_id value) per models (UserMissionProgress.user_id BigInteger FK to users.telegram_id), real handler flows (from_user.id), MissionService calls, and prior ID contract fixes (VIP commit 00fd7e8, Fase4 gamif). Matches sample_user.telegram_id; never the internal PK .id. Used for dup guard, recurring, catch-up pilots."""
    progress = UserMissionProgress(
        user_id=sample_user.telegram_id,
        mission_id=sample_mission.id,
        target_value=sample_mission.target_value,
        current_value=5,
        is_completed=False,
    )
    db_session.add(progress)
    db_session.commit()
    db_session.refresh(progress)
    return progress


@pytest.fixture
def sample_pending_request(db_session: Session, sample_user, sample_free_channel):
    """Crea una solicitud pendiente de prueba."""
    request = PendingRequest(
        user_id=sample_user.telegram_id,
        channel_id=sample_free_channel.id,
        username="testuser",
        first_name="Test",
        scheduled_approval_at=datetime.now(UTC) + timedelta(minutes=3),
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
        is_active=True,
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
        is_active=True,
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
        status=PromotionStatus.ACTIVE,
    )
    db_session.add(promotion)
    db_session.commit()
    db_session.refresh(promotion)
    return promotion


@pytest.fixture
def sample_reaction_emoji(db_session: Session):
    """Crea un emoji de reacción de prueba."""
    emoji = ReactionEmoji(emoji="💋", name="besito", besito_value=1, is_active=True)
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
        has_reactions=True,
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
        is_starting_node=True,
    )
    db_session.add(node)
    db_session.commit()
    db_session.refresh(node)
    return node


@pytest.fixture
def sample_story_choice(db_session: Session, sample_story_node):
    """Crea una opción de historia de prueba."""
    choice = StoryChoice(
        node_id=sample_story_node.id, text="Go forward", next_node_id=None, archetype_points=0
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
        traits='["curiosidad","aventura"]',
    )
    db_session.add(archetype)
    db_session.commit()
    db_session.refresh(archetype)
    return archetype


@pytest.fixture
def sample_daily_gift_config(db_session: Session):
    """Crea una configuración de regalo diario de prueba."""
    config = DailyGiftConfig(besito_amount=10, is_active=True)
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)
    return config


@pytest.fixture
def sample_cart_item(db_session: Session, sample_user, sample_store_product):
    """Crea un item de carrito de prueba."""
    item = CartItem(user_id=sample_user.id, product_id=sample_store_product.id, quantity=1)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture
def sample_order(db_session: Session, sample_user):
    """Crea una orden de prueba."""
    order = Order(
        user_id=sample_user.id, total_items=1, total_price=100, status=OrderStatus.PENDING
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
        is_active=True,
    )
    db_session.add(reward)
    db_session.commit()
    db_session.refresh(reward)
    return reward


@pytest.fixture
def sample_category(db_session: Session):
    """Crea una categoría de prueba."""
    category = Category(
        name="Test Category", description="A test category", order_index=1, is_active=True
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


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
    bot.send_media_group = AsyncMock()
    bot.ban_chat_member = AsyncMock()
    bot.unban_chat_member = AsyncMock()
    bot.create_chat_invite_link = AsyncMock(
        return_value=MagicMock(invite_link="https://t.me/+NewInviteLink")
    )
    return bot


@pytest.fixture
def mock_dispatcher():
    """Crea un mock del dispatcher."""
    dp = MagicMock()
    return dp


def mock_service_ctx(mock_get_service, service_class, **methods):
    """Crea un service mock con create_autospec para handler tests.

    Valida que los métodos mockeados existan realmente en el service class.
    Cada kwarg es un `nombre_metodo=valor_retorno`.

    Uso::
        @patch("handlers.foo.get_service")
        async def test_foo(self, mock_get_service):
            svc = mock_service_ctx(mock_get_service, StoreService,
                get_all_products=[],
                get_product=product,
            )
            await handler(cb)
            svc.get_product.assert_called_once_with(1)
    """
    svc = create_autospec(service_class, spec_set=True, instance=True)
    for name, val in methods.items():
        method_mock = getattr(svc, name)
        method_mock.return_value = val
    ctx = MagicMock()
    ctx.__enter__.return_value = svc
    ctx.__exit__.return_value = False
    mock_get_service.return_value = ctx
    return svc


@pytest.fixture
def sample_streak_promotion(db_session):
    """Create a test streak promotion with one level and codes."""
    from models.models import (
        StreakPromotion,
        StreakPromotionCode,
        StreakPromotionCodeStatus,
        StreakPromotionLevel,
        StreakPromotionStatus,
    )

    promo = StreakPromotion(
        name="Test Promotion",
        description="Test",
        status=StreakPromotionStatus.ACTIVE,
        is_active=True,
        include_general=True,
        include_simple=True,
    )
    db_session.add(promo)
    db_session.flush()

    level = StreakPromotionLevel(
        promotion_id=promo.id,
        consecutive_required=5,
        discount_pct=50,
        codes_available=3,
    )
    db_session.add(level)
    db_session.flush()

    for i in range(3):
        code = StreakPromotionCode(
            level_id=level.id,
            code_value=f"TEST-CODE-{i}",
            status=StreakPromotionCodeStatus.AVAILABLE,
        )
        db_session.add(code)

    db_session.commit()
    return promo


@pytest.fixture
def sample_streak_session(db_session, sample_streak_promotion):
    """Create a test StreakSession."""
    from models.models import StreakSession

    session = StreakSession(
        user_id=12345,
        promotion_id=sample_streak_promotion.id,
        is_in_risk_mode=False,
        protection_used=False,
        codes_delivered="[]",
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


# ==================== NURTURE FIXTURES (for R3 gold alignment + shared tests) ====================


@pytest.fixture
def sample_nurture_sequence(db_session: Session):
    """Crea una secuencia nurture de prueba (VIP audience, like sample_package style)."""
    seq = NurtureSequence(
        name="Test Nurture Seq",
        description="A test nurture sequence",
        audience=NurtureAudience.VIP,
        is_active=True,
        created_by=None,
    )
    db_session.add(seq)
    db_session.commit()
    db_session.refresh(seq)
    return seq


@pytest.fixture
def sample_nurture_step(db_session: Session, sample_nurture_sequence, sample_package=None):
    """Crea un paso nurture de prueba (with pkg or fallback; telegram contract, aware ts, commit/refresh)."""
    step = NurtureStep(
        sequence_id=sample_nurture_sequence.id,
        step_order=1,
        delay_hours=0,
        package_id=sample_package.id if sample_package else None,
        fallback_text=None if sample_package else "Test fallback content for nurture",
        is_active=True,
    )
    db_session.add(step)
    db_session.commit()
    db_session.refresh(step)
    return step


@pytest.fixture
def sample_user_nurture_progress(db_session: Session, sample_user, sample_nurture_sequence):
    """Crea progreso nurture de prueba (telegram_id contract, aware, commit/refresh)."""
    prog = UserNurtureProgress(
        user_telegram_id=sample_user.telegram_id,
        sequence_id=sample_nurture_sequence.id,
        last_step_order_delivered=0,
        status="active",
    )
    db_session.add(prog)
    db_session.commit()
    db_session.refresh(prog)
    return prog


# ==================== TELEGRAM MOCK FACTORIES ====================

from aiogram.fsm.context import FSMContext  # noqa: E402
from aiogram.fsm.storage.base import StorageKey  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402
from aiogram.types import CallbackQuery, Message  # noqa: E402
from aiogram.types import User as AiogramUser  # noqa: E402


@pytest.fixture
def make_user():
    """Factory para crear usuarios mock de Telegram."""

    def _factory(
        user_id: int = 123456789,
        username: str = "testuser",
        first_name: str = "Test",
        is_bot: bool = False,
        is_premium: bool = False,
        last_name: str = None,
    ):
        user = MagicMock(spec=AiogramUser)
        user.id = user_id
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.full_name = first_name
        user.is_bot = is_bot
        user.is_premium = is_premium
        user.language_code = "es"
        return user

    return _factory


@pytest.fixture
def make_message(make_user):
    """Factory para crear mensajes mock de Telegram."""

    def _factory(
        text: str = "/start",
        user=None,
        chat_id: int = -1001,
        message_id: int = 42,
    ):
        user = user or make_user()
        msg = AsyncMock(spec=Message)
        msg.bot = AsyncMock()
        msg.bot.get_chat_member = AsyncMock()
        msg.bot.create_chat_invite_link = AsyncMock(
            return_value=MagicMock(invite_link="https://t.me/+TestLink")
        )
        msg.bot.send_message = AsyncMock()
        msg.bot.send_photo = AsyncMock()
        msg.bot.send_video = AsyncMock()
        msg.bot.send_document = AsyncMock()
        msg.bot.send_animation = AsyncMock()
        msg.from_user = user
        msg.chat = MagicMock()
        msg.chat.id = chat_id
        msg.chat.type = "private"
        msg.text = text
        msg.message_id = message_id
        msg.answer = AsyncMock()
        msg.reply = AsyncMock()
        msg.delete = AsyncMock()
        return msg

    return _factory


@pytest.fixture
def make_callback(make_user):
    """Factory para crear callbacks mock de Telegram."""

    def _factory(
        data: str = "action:test",
        user=None,
        message_text: str = "Previous message",
        callback_id: str = None,
    ):
        user = user or make_user()
        cb = AsyncMock(spec=CallbackQuery)
        cb.id = callback_id or f"cb_{data}_{id(data)}"
        cb.bot = AsyncMock()
        cb.bot.send_message = AsyncMock()
        cb.bot.send_photo = AsyncMock()
        cb.from_user = user
        cb.data = data
        cb.message = AsyncMock()
        cb.message.message_id = 100
        cb.message.chat = MagicMock()
        cb.message.chat.id = -1001
        cb.message.text = message_text
        cb.message.edit_text = AsyncMock()
        cb.message.edit_caption = AsyncMock()
        cb.message.edit_reply_markup = AsyncMock()
        cb.message.delete = AsyncMock()
        cb.message.answer = AsyncMock()
        cb.message.bot = cb.bot
        cb.answer = AsyncMock()
        return cb

    return _factory


@pytest.fixture
def make_fsm_context():
    """Factory para crear FSMContext real con MemoryStorage."""
    storage = MemoryStorage()

    async def _factory(
        user_id: int = 123456789,
        chat_id: int = 1001,
        bot_id: int = 123,
    ):
        key = StorageKey(bot_id=bot_id, chat_id=chat_id, user_id=user_id)
        return FSMContext(storage=storage, key=key)

    return _factory
