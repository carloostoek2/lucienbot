"""Recordatorio a Free inactivos (#6): selección, ventana horaria, claim y bloqueo."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from middlewares.activity import classify
from models.database import Base
from models.models import (
    Channel,
    ChannelType,
    DailyGiftConfig,
    FeatureActivation,
    Subscription,
    User,
    UserRole,
)
from services import inactivity_reminder_service as svc

CDMX = ZoneInfo("America/Mexico_City")
# Día de activación del flag: jueves 5 nov 2026, 10:30 CDMX.
T0 = datetime(2026, 11, 5, 10, 30, tzinfo=CDMX).astimezone(UTC)
DAY = timedelta(days=1)


@pytest.fixture
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'inactivity.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    session.add(DailyGiftConfig(besito_amount=10, is_active=True))
    session.commit()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture(autouse=True)
def flag_on():
    with (
        patch.object(svc.bot_config, "FEATURE_FREE_INACTIVITY_REMINDER", True, create=True),
        patch.object(svc.bot_config, "ADMIN_IDS", [], create=True),
    ):
        yield


def _user(db, tg, *, started=True, last_activity=None, role=UserRole.USER):
    user = User(
        telegram_id=tg,
        first_name=f"u{tg}",
        role=role,
        bot_started_at=(T0 - 200 * DAY) if started else None,
        last_activity_at=last_activity,
    )
    db.add(user)
    db.commit()
    return user


async def _run(db, now):
    bot = AsyncMock()
    stats = await svc.run_inactivity_reminders(db, bot, now, pause_seconds=0, clock=lambda: now)
    return bot, stats


def _sent_to(bot):
    return [c.kwargs["chat_id"] for c in bot.send_message.await_args_list]


# ---- 1) inactivos históricos: NUNCA reciben nada, ningún día ----
async def test_historical_inactive_users_never_get_reminder(db):
    _user(db, 1, last_activity=T0 - 120 * DAY)  # última actividad antes de la activación
    _user(db, 101, last_activity=T0 - timedelta(seconds=1))
    _user(db, 102, last_activity=None)  # hizo /start pero sin actividad registrada
    for day in range(31):
        for hour in (10, 15, 20):
            local = (T0 + day * DAY).astimezone(CDMX).replace(hour=hour, minute=30)
            bot, _ = await _run(db, local.astimezone(UTC))
            assert _sent_to(bot) == [], (day, hour)
    assert db.get(FeatureActivation, svc.FEATURE_KEY) is not None


async def test_activity_at_activation_counts_and_sends_at_three_days(db):
    _user(db, 103, last_activity=T0)
    for offset in (timedelta(0), DAY, 2 * DAY, 3 * DAY - timedelta(hours=1)):
        bot, _ = await _run(db, T0 + offset)
        assert _sent_to(bot) == [], offset
    bot, _ = await _run(db, T0 + 3 * DAY)
    assert _sent_to(bot) == [103]


async def test_activation_is_stored_once_and_never_recalculated(db):
    await _run(db, T0)
    await _run(db, T0 + 5 * DAY)
    row = db.get(FeatureActivation, svc.FEATURE_KEY)
    assert svc._utc(row.activated_at) == T0


# ---- 2) inactivo después de la activación: uno solo a los 3 días ----
async def test_inactive_after_activation_gets_exactly_one_at_three_days(db):
    _user(db, 2, last_activity=T0 + DAY)
    await _run(db, T0)  # activa el flag
    bot, _ = await _run(db, T0 + 3 * DAY + timedelta(hours=1))
    assert _sent_to(bot) == []  # solo 2 días desde su última actividad
    bot, _ = await _run(db, T0 + 4 * DAY)
    assert _sent_to(bot) == [2]
    text = bot.send_message.await_args.kwargs["text"]
    assert text == (
        "Hace unos días que no pasa por aquí. Su regalo diario sigue esperándole: "
        "10 💋 cuando quiera reclamarlo."
    )
    for later in (4 * DAY + timedelta(hours=2), 5 * DAY, 12 * DAY, 30 * DAY):
        bot, _ = await _run(db, T0 + later)
        assert _sent_to(bot) == [], later  # no vuelve a llegar sin que regrese


# ---- 3) vuelve y se vuelve a ir: uno nuevo (respetando 1 por semana) ----
async def test_returning_user_gets_new_reminder_after_new_inactivity(db):
    user = _user(db, 3, last_activity=T0)
    await _run(db, T0)
    bot, _ = await _run(db, T0 + 3 * DAY)
    assert _sent_to(bot) == [3]
    reminded_at = T0 + 3 * DAY
    # Vuelve al día siguiente del recordatorio.
    svc.touch_activity(db, user.telegram_id, now=reminded_at + DAY)
    bot, _ = await _run(db, reminded_at + 4 * DAY)  # 3 días inactivo, pero <7 desde el último
    assert _sent_to(bot) == []
    bot, _ = await _run(db, reminded_at + 7 * DAY)
    assert _sent_to(bot) == [3]
    assert bot.send_message.await_args.kwargs["text"] == (
        "Lucien le guarda el lugar. Cuando tenga un momento, la trivia y su regalo "
        "del día siguen esperándole."
    )


# ---- 4) VIP nunca ----
async def test_vip_never_gets_reminder(db):
    _user(db, 4, last_activity=T0)
    channel = Channel(channel_id=-100, channel_type=ChannelType.VIP, is_active=True)
    db.add(channel)
    db.commit()
    db.add(Subscription(user_id=4, channel_id=channel.id, end_date=T0 + 60 * DAY, is_active=True))
    db.commit()
    await _run(db, T0)
    for offset in (3 * DAY, 10 * DAY, 40 * DAY):
        bot, _ = await _run(db, T0 + offset)
        assert _sent_to(bot) == []


# ---- 5) fuera de horario: nada ----
@pytest.mark.parametrize(
    ("hour", "minute", "sends"),
    [(9, 59, False), (10, 0, True), (20, 59, True), (21, 0, False), (2, 0, False)],
)
async def test_send_window_cdmx(db, hour, minute, sends):
    _user(db, 5, last_activity=T0)
    await _run(db, T0)
    day4 = (T0 + 4 * DAY).astimezone(CDMX)
    now = day4.replace(hour=hour, minute=minute).astimezone(UTC)
    bot, _ = await _run(db, now)
    assert bool(_sent_to(bot)) is sends


async def test_window_closing_mid_batch_stops_sending(db):
    _user(db, 51, last_activity=T0)
    _user(db, 52, last_activity=T0)
    await _run(db, T0)
    start = (T0 + 4 * DAY).astimezone(CDMX).replace(hour=20, minute=59).astimezone(UTC)
    times = iter([start, start + timedelta(minutes=2)])
    bot = AsyncMock()
    await svc.run_inactivity_reminders(db, bot, start, pause_seconds=0, clock=lambda: next(times))
    assert _sent_to(bot) == [51]


# ---- Otros filtros ----
async def test_join_request_only_user_never_gets_reminder(db):
    _user(db, 6, started=False, last_activity=None)
    await _run(db, T0)
    bot, _ = await _run(db, T0 + 10 * DAY)
    assert _sent_to(bot) == []


async def test_admin_excluded(db):
    _user(db, 7, last_activity=T0, role=UserRole.ADMIN)
    _user(db, 8, last_activity=T0)
    await _run(db, T0)
    with patch.object(svc.bot_config, "ADMIN_IDS", [8], create=True):
        bot, _ = await _run(db, T0 + 4 * DAY)
    assert _sent_to(bot) == []


async def test_flag_off_does_nothing_and_does_not_activate(db):
    _user(db, 9, last_activity=T0)
    with patch.object(svc.bot_config, "FEATURE_FREE_INACTIVITY_REMINDER", False):
        bot, stats = await _run(db, T0 + 10 * DAY)
    assert stats["reason"] == "disabled"
    assert _sent_to(bot) == []
    assert db.get(FeatureActivation, svc.FEATURE_KEY) is None


async def test_blocked_user_is_marked_and_never_retried(db):
    _user(db, 10, last_activity=T0)
    await _run(db, T0)
    bot = AsyncMock()
    bot.send_message.side_effect = TelegramForbiddenError(
        method=SendMessage(chat_id=10, text="x"), message="Forbidden: bot was blocked by the user"
    )
    now = T0 + 4 * DAY
    stats = await svc.run_inactivity_reminders(db, bot, now, pause_seconds=0, clock=lambda: now)
    assert stats["blocked"] == 1
    db.expire_all()
    assert db.query(User).filter_by(telegram_id=10).one().bot_blocked_at is not None
    bot2, _ = await _run(db, T0 + 30 * DAY)
    assert _sent_to(bot2) == []
    # /start posterior: desbloqueó al bot.
    svc.mark_started(db, 10, now=T0 + 31 * DAY)
    db.expire_all()
    assert db.query(User).filter_by(telegram_id=10).one().bot_blocked_at is None


async def test_claim_is_per_row_two_runs_send_once(db):
    _user(db, 11, last_activity=T0)
    await _run(db, T0)
    now = T0 + 4 * DAY
    candidates = svc.find_candidates(db, now, T0, 10)
    assert [u.telegram_id for u in candidates] == [11]
    user_id = candidates[0].id
    # Dos instancias leyeron el mismo candidato (previous=None) y compiten.
    assert svc.claim(db, user_id, None, now) is True
    assert svc.claim(db, user_id, None, now) is False


def test_touch_activity_is_throttled(db):
    _user(db, 12, last_activity=T0)
    assert svc.touch_activity(db, 12, now=T0 + timedelta(minutes=5)) is False
    assert svc.touch_activity(db, 12, now=T0 + timedelta(minutes=16)) is True


def test_mark_started_never_overwrites_first_start(db):
    user = _user(db, 13, started=False)
    svc.mark_started(db, 13, now=T0)
    svc.mark_started(db, 13, now=T0 + 5 * DAY)
    db.expire_all()
    assert svc._utc(db.get(User, user.id).bot_started_at) == T0


# ---- Middleware: qué cuenta como actividad ----
def _cb(chat_type):
    from aiogram.types import CallbackQuery, Chat, Message
    from aiogram.types import User as TgUser

    tg_user = TgUser(id=1, is_bot=False, first_name="a")
    msg = Message(
        message_id=1, date=datetime.now(UTC), chat=Chat(id=1, type=chat_type), from_user=tg_user
    )
    return CallbackQuery(id="1", from_user=tg_user, chat_instance="x", message=msg, data="d")


def _fn(module, name):
    return SimpleNamespace(__module__=module, __name__=name)


def test_channel_reaction_is_not_activity():
    from handlers.gamification_user_handlers import handle_reaction

    assert classify(_cb("channel"), handle_reaction) is None
    assert classify(_cb("private"), handle_reaction) is None


def test_private_game_gift_store_menu_count_as_activity():
    from handlers.common_handlers import back_to_main, cmd_start
    from handlers.game_user_handlers import trivia_answer
    from handlers.gamification_user_handlers import claim_daily_gift

    assert classify(_cb("private"), claim_daily_gift) == "activity"
    assert classify(_cb("private"), trivia_answer) == "activity"
    assert classify(_cb("private"), back_to_main) == "activity"
    assert classify(_cb("private"), cmd_start) == "start"
    assert classify(_cb("private"), _fn("handlers.store_user_handlers", "shop_menu")) == "activity"
    assert classify(_cb("private"), _fn("handlers.mission_user_handlers", "x")) is None
    assert classify(_cb("group"), claim_daily_gift) is None


# ---- Flag: apagado por defecto ----
def _flag_in_fresh_interpreter(env_value):
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    env = {k: v for k, v in os.environ.items() if k != "FEATURE_FREE_INACTIVITY_REMINDER"}
    env.setdefault("BOT_TOKEN", "x")
    if env_value is not None:
        env["FEATURE_FREE_INACTIVITY_REMINDER"] = env_value
    code = (
        "import json\n"
        "from config.settings import bot_config, BotConfig\n"
        "from services.inactivity_reminder_service import is_enabled\n"
        "print(json.dumps([BotConfig.FEATURE_FREE_INACTIVITY_REMINDER,"
        " bot_config.FEATURE_FREE_INACTIVITY_REMINDER, is_enabled()]))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [(None, False), ("", False), ("0", False), ("true", False), ("1", True)],
)
def test_flag_defaults_off_and_only_1_enables(env_value, expected):
    assert _flag_in_fresh_interpreter(env_value) == [expected, expected, expected]
