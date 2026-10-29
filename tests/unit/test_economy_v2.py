"""PR B (economía v2): topes, VIP corto, nurture ≥7 días y premio de racha en besitos."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.economy_limits import LIMITS, EconomyLimitError, clamp, validate
from models.database import Base
from models.models import (
    BesitoBalance,
    BesitoTransaction,
    StreakSession,
    Subscription,
    Tariff,
    TransactionSource,
    User,
    UserRole,
)
from services.streak_promotion_service import StreakPromotionService
from services.vip_service import VIPService, vip_activated_payload
from utils.lucien_voice import LucienVoice

# ==================== 4) Topes ====================

PROD_VALUES = {
    "daily_gift_amount": 10,
    "dice_limit_free": 5,
    "dice_limit_vip": 10,
    "trivia_limit_free": 5,
    "trivia_limit_vip": 8,
    "trivia_simple_limit_free": 5,
    "trivia_simple_limit_vip": 8,
    "trivia_vip_limit": 5,
    "trivia_besitos_daily_free": 10,
    "trivia_besitos_daily_vip": 15,
    "trivia_besitos_weekly_free": 50,
    "trivia_besitos_weekly_vip": 70,
    "reaction_besito_value": 5,
    "mission_reward_besitos": 30,
    "streak_retire_besitos": 15,
    "streak_complete_besitos": 30,
}


@pytest.mark.parametrize(("key", "value"), sorted(PROD_VALUES.items()))
def test_prod_values_are_within_caps(key, value):
    assert validate(key, value) == value


def test_every_cap_has_headroom_over_prod():
    for key, value in PROD_VALUES.items():
        assert LIMITS[key].max >= 2 * value or LIMITS[key].max >= value + 10, key


def test_validate_rejects_out_of_range_with_readable_message():
    with pytest.raises(EconomyLimitError) as exc:
        validate("daily_gift_amount", 500)
    assert "500" in str(exc.value)
    assert "1–30" in str(exc.value)


def test_clamp_reads_never_exceed_cap():
    assert clamp("reaction_besito_value", 999) == LIMITS["reaction_besito_value"].max
    assert clamp("daily_gift_amount", None) == LIMITS["daily_gift_amount"].min


def test_daily_gift_amount_clamped_on_read(db_session):
    from models.models import DailyGiftConfig
    from services.daily_gift_service import DailyGiftService

    db_session.add(DailyGiftConfig(besito_amount=999, is_active=True))
    db_session.commit()
    assert DailyGiftService(db_session).get_gift_amount() == LIMITS["daily_gift_amount"].max


def test_daily_gift_update_rejects_over_cap(db_session):
    from services.daily_gift_service import DailyGiftService

    with pytest.raises(EconomyLimitError):
        DailyGiftService(db_session).update_config(besito_amount=31)


def test_mission_reward_besitos_clamped(db_session):
    from services.reward_service import effective_reward_besitos

    class _R:
        besito_amount = 5000

    assert effective_reward_besitos(_R()) == LIMITS["mission_reward_besitos"].max


# ==================== 1) VIP corto ====================


def _tariff(db, days):
    t = Tariff(name=f"{days} días", duration_days=days, price="1", currency="USD", is_active=True)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def test_invite_expiry_matches_short_access(db_session):
    svc = VIPService(db_session)
    end = datetime.now(UTC) + timedelta(days=1)
    expire, is_short = svc.invite_link_expiry(1, access_end=end)
    assert is_short is True
    assert expire == end


def test_invite_expiry_caps_at_seven_days_for_long_access(db_session):
    svc = VIPService(db_session)
    expire, is_short = svc.invite_link_expiry(1, access_end=datetime.now(UTC) + timedelta(days=30))
    assert is_short is False
    assert expire - datetime.now(UTC) <= timedelta(days=7, seconds=5)


def test_invite_expiry_none_when_access_already_over(db_session):
    svc = VIPService(db_session)
    expire, _ = svc.invite_link_expiry(1, access_end=datetime.now(UTC) + timedelta(minutes=1))
    assert expire is None


async def test_create_invite_link_short_access_member_limit_and_expiry(
    db_session, sample_vip_channel, mock_bot
):
    svc = VIPService(db_session)
    end = datetime.now(UTC) + timedelta(days=3)
    await svc.create_vip_invite_link(mock_bot, 42, access_end=end)
    kwargs = mock_bot.create_chat_invite_link.await_args.kwargs
    assert kwargs["member_limit"] == 1
    assert kwargs["expire_date"] == end


async def test_create_invite_link_no_permanent_fallback_for_short_access(
    db_session, sample_vip_channel, mock_bot
):
    mock_bot.create_chat_invite_link = AsyncMock(side_effect=RuntimeError("tg down"))
    svc = VIPService(db_session)
    link = await svc.create_vip_invite_link(
        mock_bot, 42, allow_fallback=True, access_end=datetime.now(UTC) + timedelta(days=1)
    )
    assert link is None  # el enlace permanente no vence: no se entrega en un VIP corto


async def test_internal_grant_unbans_only_if_banned_before_link(
    db_session, sample_user, sample_vip_channel, mock_bot
):
    tariff = _tariff(db_session, 1)
    svc = VIPService(db_session)
    with patch("services.vip_service.schedule_emit"):
        ok, msg, _meta = await svc.grant_internal_vip_access_with_invite(
            mock_bot, sample_user.telegram_id, tariff.id
        )
    assert ok is True
    mock_bot.unban_chat_member.assert_awaited_once_with(
        chat_id=sample_vip_channel.channel_id,
        user_id=sample_user.telegram_id,
        only_if_banned=True,
    )
    assert "vence junto con su acceso" in msg
    assert "expira en 7 días" not in msg


def test_vip_activated_payload_carries_granted_days():
    class _T:
        id = 15
        duration_days = 1

    payload = vip_activated_payload(7, 99, _T(), is_extension=False)
    assert payload == {
        "user_id": 7,
        "subscription_id": 99,
        "tariff_id": 15,
        "granted_days": 1,
        "is_extension": False,
    }


def test_one_day_vip_skips_24h_reminder(db_session, sample_user, sample_vip_channel):
    one_day = _tariff(db_session, 1)
    now = datetime.now(UTC)
    sub = Subscription(
        user_id=sample_user.telegram_id,
        channel_id=sample_vip_channel.id,
        tariff_id=one_day.id,
        start_date=now - timedelta(hours=4),
        end_date=now + timedelta(hours=20),
        is_active=True,
    )
    db_session.add(sub)
    db_session.commit()
    assert sub not in VIPService(db_session).get_expiring_subscriptions(hours=24)


def test_vip_direct_access_copy_by_duration():
    end = datetime.now(UTC) + timedelta(days=1)
    short = LucienVoice.vip_direct_access(
        "https://t.me/+x", "1 día", end, 1, granted_days=1, link_expires_with_access=True
    )
    assert "Entre hoy" in short
    assert "vence junto con su acceso" in short
    long_ = LucienVoice.vip_direct_access("https://t.me/+x", "Mes", end, 30, granted_days=30)
    assert "expira en 7 días" in long_
    assert "Entre hoy" not in long_


# ==================== 3) Nurture solo ≥7 días ====================


@contextmanager
def _ctx(obj):
    yield obj


@pytest.mark.parametrize(("days", "enrolls"), [(1, False), (3, False), (7, True), (30, True)])
async def test_nurture_only_for_grants_of_seven_days_or_more(db_session, days, enrolls):
    from services.nurture_service import NurtureService, on_vip_activated

    ns = NurtureService(db_session)
    with (
        patch("services.get_service", return_value=_ctx(ns)),
        patch.object(ns, "start_sequences_for_user", return_value=1) as start,
    ):
        await on_vip_activated({"user_id": 5, "granted_days": days})
    assert start.called is enrolls


def test_nurture_granted_days_falls_back_to_subscription_tariff(
    db_session, sample_user, sample_vip_channel
):
    from services.nurture_service import NurtureService

    tariff = _tariff(db_session, 3)
    sub = Subscription(
        user_id=sample_user.telegram_id,
        channel_id=sample_vip_channel.id,
        tariff_id=tariff.id,
        end_date=datetime.now(UTC) + timedelta(days=3),
        is_active=True,
    )
    db_session.add(sub)
    db_session.commit()
    assert NurtureService(db_session).resolve_granted_days({"subscription_id": sub.id}) == 3


def test_expire_sweep_runs_every_ten_minutes():
    from services import scheduler_service

    src = Path(scheduler_service.__file__).read_text(encoding="utf-8")
    block = src[src.index("_process_expired_subscriptions,\n") :][:200]
    assert 'minute="*/10"' in block


# ==================== 2) Premio de racha ====================


@pytest.fixture
def streak_db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'streak.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    db.add(User(telegram_id=880001, username="s", first_name="S", role=UserRole.USER))
    db.add(BesitoBalance(user_id=880001, balance=0, total_earned=0, total_spent=0))
    db.commit()
    svc = StreakPromotionService(db)
    promo = svc.create_promotion(
        name="Promo racha",
        description="t",
        levels=[
            {"consecutive_required": 2, "discount_pct": 10, "codes_available": 2},
            {"consecutive_required": 4, "discount_pct": 20, "codes_available": 2},
        ],
        duration_mode="dates",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=7),
    )
    session = svc._get_or_create_session(880001, promo.id)
    db.commit()
    yield db, svc, session
    db.close()
    engine.dispose()


def _streak_credits(db):
    return (
        db.query(BesitoTransaction)
        .filter(
            BesitoTransaction.user_id == 880001,
            BesitoTransaction.source == TransactionSource.STREAK_REWARD,
        )
        .all()
    )


def test_retire_pays_once_and_commits(streak_db):
    db, svc, session = streak_db
    first = svc.retire_with_payout(880001, session.id.hex)
    second = svc.retire_with_payout(880001, session.id.hex)
    assert first["status"] == "paid" and first["besitos"] == 15
    assert second["status"] == "already_paid"
    db.expire_all()
    assert [t.amount for t in _streak_credits(db)] == [15]
    row = db.query(StreakSession).filter(StreakSession.id == session.id).one()
    assert row.retired_at is not None and row.payout_paid_at is not None
    assert row.payout_besitos == 15
    assert svc.get_active_session(880001) is None


def test_retire_rejects_other_users_session_and_risk_mode(streak_db):
    db, svc, session = streak_db
    assert svc.retire_with_payout(999, session.id.hex)["status"] == "unavailable"
    assert svc.set_risk_mode(880001, session.id.hex) is True
    assert svc.retire_with_payout(880001, session.id.hex)["status"] == "unavailable"
    assert _streak_credits(db) == []


def test_continue_with_stale_button_is_rejected(streak_db):
    _db, svc, _session = streak_db
    assert svc.set_risk_mode(880001, "0" * 32) is False


def test_complete_pays_at_final_level_only_in_risk_mode(streak_db):
    db, svc, session = streak_db
    assert svc.complete_with_payout(880001, 4) is None  # sin modo arriesgo no hay "completa"
    svc.set_risk_mode(880001, session.id.hex)
    assert svc.complete_with_payout(880001, 3) is None  # aún no llega al último nivel
    assert svc.complete_with_payout(880001, 4) == {"besitos": 30}
    assert svc.complete_with_payout(880001, 5) is None  # una sola vez por sesión
    db.expire_all()
    assert [t.amount for t in _streak_credits(db)] == [30]


def test_streak_amounts_come_from_trivia_config(streak_db):
    from services.trivia_config_service import TriviaConfigService

    db, svc, session = streak_db
    TriviaConfigService(db).update_config(admin_id=1, streak_retire_besitos=20)
    assert svc.retire_with_payout(880001, session.id.hex)["besitos"] == 20


def test_streak_copy_is_verbatim():
    assert LucienVoice.streak_risk_mode_offer("C", 10, "P", 15, 30).endswith(
        "Lleva una buena racha. Puede retirarse ahora con 15 💋, o seguir y llevarse 30 💋 "
        "si la completa. Usted decide."
    )
    assert LucienVoice.streak_retire_confirmed(15).startswith(
        "Sabia decisión. 15 💋 ya están en su cuenta."
    )
    assert LucienVoice.streak_completed(30) == (
        "Racha completa. Diana toma nota de su constancia: 30 💋 a su cuenta."
    )
    assert LucienVoice.streak_risk_failed() == (
        "Esta vez la racha se cortó. Mañana Diana vuelve a preguntar."
    )
