"""
Tests LIVE contra Telegram Bot API (bot de prueba).

Requiere TELEGRAM_TEST_BOT_TOKEN. Opcionalmente:
- TELEGRAM_TEST_TARGET_USER_ID: usuario que ya hizo /start al bot de prueba
- TELEGRAM_TEST_USER_CHAT_ID: user_chat_id capturado de un ChatJoinRequest
- TELEGRAM_TEST_CHANNEL_ID: canal donde el bot es admin (TG chat id negativo)

Setup manual para join-request:
1. Agregar @IDcanalbot como admin del canal de prueba (can_invite_users).
2. Activar "solicitar unirse" en el canal.
3. Con otra cuenta, solicitar unión SIN /start al bot.
4. Ejecutar: TELEGRAM_TEST_BOT_TOKEN=... pytest tests/integration/test_telegram_dm_delivery_live.py -m telegram_live -q
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from utils.telegram_delivery import DmProbeResult, probe_send_message, resolve_private_chat_id

pytestmark = [pytest.mark.integration, pytest.mark.telegram_live]

_TOKEN_ENV = "TELEGRAM_TEST_BOT_TOKEN"
_TARGET_USER_ENV = "TELEGRAM_TEST_TARGET_USER_ID"
_USER_CHAT_ENV = "TELEGRAM_TEST_USER_CHAT_ID"
_CHANNEL_ENV = "TELEGRAM_TEST_CHANNEL_ID"


def _env_int(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    return int(raw)


def _require_token() -> str:
    token = os.getenv(_TOKEN_ENV, "").strip()
    if not token:
        pytest.skip(f"{_TOKEN_ENV} no configurado — omitiendo test live")
    return token


@pytest.fixture
async def live_bot():
    token = _require_token()
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    yield bot
    await bot.session.close()


JOIN_REQUEST_DM_WINDOW_MINUTES = 5


@dataclass(frozen=True)
class JoinRequestSnapshot:
    user_id: int
    user_chat_id: int
    channel_id: int
    age_minutes: float


def _join_request_age_minutes(jr) -> float:
    jr_dt = jr.date if jr.date.tzinfo else jr.date.replace(tzinfo=UTC)
    return (datetime.now(UTC) - jr_dt).total_seconds() / 60.0


async def _fetch_latest_join_request(
    bot: Bot, *, max_age_minutes: float | None = None
) -> JoinRequestSnapshot | None:
    updates = await bot.get_updates(limit=50, timeout=0)
    for update in reversed(updates):
        jr = update.chat_join_request
        if jr is None:
            continue
        age = _join_request_age_minutes(jr)
        if max_age_minutes is not None and age > max_age_minutes:
            continue
        return JoinRequestSnapshot(
            user_id=jr.from_user.id,
            user_chat_id=jr.user_chat_id,
            channel_id=jr.chat.id,
            age_minutes=age,
        )
    return None


@pytest.mark.asyncio
async def test_live_bot_identity(live_bot: Bot):
    me = await live_bot.get_me()
    assert me.id
    assert me.is_bot


@pytest.mark.asyncio
async def test_live_invalid_user_returns_permanent_or_error(live_bot: Bot):
    result = await probe_send_message(live_bot, 999999999, "probe invalid user")
    assert result.success is False
    assert result.error_text


@pytest.mark.asyncio
async def test_live_target_user_dm_if_configured(live_bot: Bot):
    target = _env_int(_TARGET_USER_ENV)
    if target is None:
        pytest.skip(f"{_TARGET_USER_ENV} no configurado")

    result = await probe_send_message(live_bot, target, "🧪 Lucien probe: usuario con /start")
    assert isinstance(result, DmProbeResult)
    if not result.success:
        pytest.fail(
            f"Usuario con /start debería recibir DM: {result.permanent_code} | {result.error_text}"
        )


@pytest.mark.asyncio
async def test_live_user_id_vs_user_chat_id_if_configured(live_bot: Bot):
    """Compara from.id vs user_chat_id cuando se proveen ambos (post join-request)."""
    user_id = _env_int(_TARGET_USER_ENV)
    user_chat_id = _env_int(_USER_CHAT_ENV)
    if user_id is None or user_chat_id is None:
        pytest.skip(f"Requiere {_TARGET_USER_ENV} y {_USER_CHAT_ENV}")

    via_user = await probe_send_message(live_bot, user_id, "🧪 probe via user.id")
    via_chat = await probe_send_message(
        live_bot, user_chat_id, "🧪 probe via user_chat_id"
    )

    # Al menos uno debe funcionar si el privilegio join-request sigue activo
    assert via_user.success or via_chat.success, (
        f"Ambos fallaron — user.id={via_user.permanent_code}/{via_user.error_text} | "
        f"user_chat_id={via_chat.permanent_code}/{via_chat.error_text}"
    )


@pytest.mark.asyncio
async def test_live_stale_join_request_dm_fails(live_bot: Bot):
    """Solicitudes viejas (>5 min) deben fallar: ventana user_chat_id expirada."""
    snap = await _fetch_latest_join_request(live_bot)
    if snap is None:
        pytest.skip("Sin chat_join_request en getUpdates")

    if snap.age_minutes <= JOIN_REQUEST_DM_WINDOW_MINUTES:
        pytest.skip("Solo hay join requests frescos — ver test_live_fresh_join_request_dm")

    via_user = await probe_send_message(live_bot, snap.user_id, "🧪 stale probe user.id")
    via_chat = await probe_send_message(
        live_bot, snap.user_chat_id, "🧪 stale probe user_chat_id"
    )

    assert not via_user.success and not via_chat.success
    assert via_user.permanent_code == "permanent:no_private_chat"
    assert via_chat.permanent_code == "permanent:no_private_chat"


@pytest.mark.asyncio
async def test_live_fresh_join_request_dm_if_present(live_bot: Bot):
    """Dentro de 5 min post-solicitud, al menos un ID debe permitir DM (API 5.5)."""
    snap = await _fetch_latest_join_request(
        live_bot, max_age_minutes=JOIN_REQUEST_DM_WINDOW_MINUTES
    )
    if snap is None:
        pytest.skip(
            "Sin join request fresca (<5 min). Envía solicitud al canal y re-ejecuta."
        )

    via_user = await probe_send_message(
        live_bot, snap.user_id, "🧪 fresh probe join-request via user.id"
    )
    via_chat = await probe_send_message(
        live_bot, snap.user_chat_id, "🧪 fresh probe via user_chat_id"
    )

    assert via_user.success or via_chat.success, (
        f"Join request fresca ({snap.age_minutes:.1f} min) "
        f"{snap.user_id}/{snap.user_chat_id} canal {snap.channel_id}: "
        f"user.id={via_user.error_text} | user_chat_id={via_chat.error_text}"
    )


@pytest.mark.asyncio
async def test_live_bot_admin_on_channel_if_configured(live_bot: Bot):
    channel_id = _env_int(_CHANNEL_ENV)
    if channel_id is None:
        pytest.skip(f"{_CHANNEL_ENV} no configurado")

    me = await live_bot.get_me()
    member = await live_bot.get_chat_member(chat_id=channel_id, user_id=me.id)
    assert member.status in {"administrator", "creator"}
    if member.status == "administrator":
        assert member.can_invite_users, "Bot necesita can_invite_users para join-request DM"


def test_resolve_private_chat_id_prefers_user_chat_id():
    assert resolve_private_chat_id(111, 222) == 222
    assert resolve_private_chat_id(111, None) == 111