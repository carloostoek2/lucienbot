"""Tests unitarios para LinkNotifier (Fase 6 link - emisor [LINK] hacia Diana)."""
import json
import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import BusinessConnection as TgBusinessConnection
from aiogram.types import User as TgUser

from handlers import business_connection_handlers as bch
from handlers.business_connection_handlers import handle_business_connection
from models.models import BusinessConnection
from services import link_notifier
from services.link_notifier import LinkNotifier


@contextmanager
def _session_ctx(session):
    """Espejo de get_db_session sobre una sesión real (commit/rollback en exit)."""
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise


def _add_bc(db_session, bc_id, is_enabled, user_id=1):
    """Añade una fila business_connections habilitada/disabled en la sesión de test."""
    db_session.add(
        BusinessConnection(business_connection_id=bc_id, user_id=user_id, is_enabled=is_enabled)
    )
    db_session.commit()


def _get_db_session_raises():
    """Helper: get_db_session que siempre falla (simula DB caída / migración no aplicada)."""
    raise RuntimeError("db down")


@pytest.mark.unit
async def test_notify_vip_kicked_disabled_does_not_send(mock_bot):
    """Flag OFF (enabled=False) → no envía nada (comportamiento idéntico)."""
    notifier = LinkNotifier(bot=mock_bot, chat_id=-100, enabled=False)
    await notifier.notify_vip_kicked(
        {"user_id": 1, "username": "testuser", "channel_id": 2, "reason": "admin_revoke", "ts": 123}
    )
    mock_bot.send_message.assert_not_awaited()


@pytest.mark.unit
async def test_notify_vip_kicked_chat_id_none_does_not_send(mock_bot):
    """LINK_CHAT_ID None (off) → no envía, aun con la feature enabled."""
    notifier = LinkNotifier(bot=mock_bot, chat_id=None, enabled=True)
    await notifier.notify_vip_kicked(
        {"user_id": 1, "username": "testuser", "channel_id": 2, "reason": "admin_revoke", "ts": 123}
    )
    mock_bot.send_message.assert_not_awaited()


@pytest.mark.unit
async def test_notify_vip_kicked_no_enabled_row_does_not_send(mock_bot, db_session, monkeypatch):
    """Sin fila habilitada en business_connections → no send (result=no_business_connection)."""
    monkeypatch.setattr(link_notifier, "SessionLocal", lambda: db_session)
    notifier = LinkNotifier(bot=mock_bot, chat_id=-100, enabled=True)
    await notifier.notify_vip_kicked(
        {"user_id": 1, "username": "testuser", "channel_id": 2, "reason": "admin_revoke", "ts": 123}
    )
    mock_bot.send_message.assert_not_awaited()


@pytest.mark.unit
async def test_notify_vip_kicked_disabled_row_does_not_send(mock_bot, db_session, monkeypatch):
    """Fila disabled (is_enabled=False) → el helper la filtra → no send."""
    _add_bc(db_session, "bc_disabled", is_enabled=False)
    monkeypatch.setattr(link_notifier, "SessionLocal", lambda: db_session)
    notifier = LinkNotifier(bot=mock_bot, chat_id=-100, enabled=True)
    await notifier.notify_vip_kicked(
        {"user_id": 1, "username": "testuser", "channel_id": 2, "reason": "admin_revoke", "ts": 123}
    )
    mock_bot.send_message.assert_not_awaited()


@pytest.mark.unit
async def test_notify_vip_kicked_enabled_sends_exact_link_payload(mock_bot, db_session, monkeypatch):
    """Flag ON + fila habilitada → payload [LINK] one-line JSON exacto con username '@'."""
    _add_bc(db_session, "bc_test", is_enabled=True)
    monkeypatch.setattr(link_notifier, "SessionLocal", lambda: db_session)
    notifier = LinkNotifier(bot=mock_bot, chat_id=-100, enabled=True)
    await notifier.notify_vip_kicked(
        {
            "user_id": 1,
            "username": "testuser",
            "channel_id": 2,
            "channel_name": "El Divan",
            "reason": "admin_revoke",
            "ts": 123,
        }
    )
    mock_bot.send_message.assert_awaited_once()
    kwargs = mock_bot.send_message.await_args.kwargs
    assert kwargs["chat_id"] == -100
    assert kwargs["business_connection_id"] == "bc_test"
    text = kwargs["text"]
    assert text.startswith("[LINK] ")
    body = json.loads(text[7:])
    assert body["v"] == 1
    assert body["event"] == "vip_kicked"
    assert body["username"] == "@testuser"
    assert body["channel_id"] == 2
    assert body["channel_name"] == "El Divan"
    assert body["reason"] == "admin_revoke"
    assert body["ts"] == 123
    assert body["user_id"] == 1


@pytest.mark.unit
async def test_notify_vip_kicked_nullable_wire_fields(mock_bot, db_session, monkeypatch):
    """username=None y channel_name=None → el payload los serializa como null."""
    _add_bc(db_session, "bc_nullable", is_enabled=True)
    monkeypatch.setattr(link_notifier, "SessionLocal", lambda: db_session)
    notifier = LinkNotifier(bot=mock_bot, chat_id=-100, enabled=True)
    await notifier.notify_vip_kicked(
        {
            "user_id": 1,
            "username": None,
            "channel_id": 2,
            "channel_name": None,
            "reason": "expired",
            "ts": 123,
        }
    )
    mock_bot.send_message.assert_awaited_once()
    body = json.loads(mock_bot.send_message.await_args.kwargs["text"][7:])
    assert body["username"] is None
    assert body["channel_name"] is None
    assert body["user_id"] == 1


@pytest.mark.unit
async def test_notify_vip_kicked_send_error_is_swallowed(mock_bot, db_session, monkeypatch):
    """send_message lanza → la excepción se traga; no rompe el flujo de expulsión."""
    _add_bc(db_session, "bc_swallow", is_enabled=True)
    monkeypatch.setattr(link_notifier, "SessionLocal", lambda: db_session)
    mock_bot.send_message = AsyncMock(side_effect=Exception("boom"))
    notifier = LinkNotifier(bot=mock_bot, chat_id=-100, enabled=True)
    await notifier.notify_vip_kicked(
        {"user_id": 1, "username": "testuser", "channel_id": 2, "reason": "admin_revoke", "ts": 123}
    )
    mock_bot.send_message.assert_awaited_once()


@pytest.mark.unit
async def test_notify_vip_kicked_event_id_fresh_per_event(mock_bot, db_session, monkeypatch):
    """Cada envío genera un event_id uuid4 distinto y válido."""
    _add_bc(db_session, "bc_fresh", is_enabled=True)
    monkeypatch.setattr(link_notifier, "SessionLocal", lambda: db_session)
    notifier = LinkNotifier(bot=mock_bot, chat_id=-100, enabled=True)
    payload = {
        "user_id": 1,
        "username": "testuser",
        "channel_id": 2,
        "channel_name": "El Divan",
        "reason": "expired",
        "ts": 123,
    }
    await notifier.notify_vip_kicked(payload)
    first_id = json.loads(mock_bot.send_message.await_args.kwargs["text"][7:])["event_id"]
    await notifier.notify_vip_kicked(payload)
    second_id = json.loads(mock_bot.send_message.await_args.kwargs["text"][7:])["event_id"]
    assert first_id != second_id
    uuid.UUID(first_id)
    uuid.UUID(second_id)


@pytest.mark.unit
def test_fetch_enabled_business_connection_id_returns_most_recent_enabled(db_session):
    """Con una fila habilitada → devuelve su business_connection_id."""
    _add_bc(db_session, "bc_row", is_enabled=True)
    assert link_notifier._fetch_enabled_business_connection_id(db_session) == "bc_row"


@pytest.mark.unit
def test_fetch_enabled_business_connection_id_picks_enabled_over_disabled(db_session):
    """Con 2 filas (una disabled, una enabled) → devuelve la enabled."""
    _add_bc(db_session, "bc_disabled", is_enabled=False)
    _add_bc(db_session, "bc_enabled", is_enabled=True)
    assert link_notifier._fetch_enabled_business_connection_id(db_session) == "bc_enabled"


@pytest.mark.unit
def test_fetch_enabled_business_connection_id_returns_none_when_empty(db_session):
    """Sin filas → None."""
    assert link_notifier._fetch_enabled_business_connection_id(db_session) is None


@pytest.mark.unit
def test_build_vip_kicked_payload_builds_contract_dict():
    """Helper puro: keys exactas + ts int unix; username/channel_name pasan raw (el '@' se agrega en notify)."""
    payload = link_notifier.build_vip_kicked_payload(
        user_id=7, username="testuser", channel_id=99, channel_name="El Divan", reason="expired"
    )
    assert set(payload) == {"user_id", "username", "channel_id", "channel_name", "reason", "ts"}
    assert payload["user_id"] == 7
    assert payload["username"] == "testuser"
    assert payload["channel_id"] == 99
    assert payload["channel_name"] == "El Divan"
    assert payload["reason"] == "expired"
    assert isinstance(payload["ts"], int)


@pytest.mark.unit
async def test_business_connection_handler_disabled_is_noop(monkeypatch):
    """FEATURE_LINK_ENABLED OFF → el handler retorna sin tocar el service (comportamiento idéntico)."""
    monkeypatch.setattr(bch.bot_config, "FEATURE_LINK_ENABLED", False)
    upsert = MagicMock()
    monkeypatch.setattr(bch.LinkNotifier, "upsert_business_connection", upsert)
    await handle_business_connection(
        TgBusinessConnection(
            id="bc_off",
            user=TgUser(id=1, is_bot=False, first_name="Duenia"),
            user_chat_id=1,
            date=1700000000,
            is_enabled=True,
        )
    )
    upsert.assert_not_called()


@pytest.mark.unit
async def test_business_connection_handler_enabled_persists_row(db_session, monkeypatch):
    """FEATURE_LINK_ENABLED ON + owner → el handler delega a 1 service y la fila se persiste."""
    monkeypatch.setattr(bch.bot_config, "FEATURE_LINK_ENABLED", True)
    monkeypatch.setattr(bch.bot_config, "ADMIN_IDS", [1])
    monkeypatch.setattr(link_notifier, "get_db_session", lambda: _session_ctx(db_session))
    await handle_business_connection(
        TgBusinessConnection(
            id="bc_on",
            user=TgUser(id=1, is_bot=False, first_name="Duenia"),
            user_chat_id=123,
            date=1700000000,
            is_enabled=True,
        )
    )
    row = db_session.query(BusinessConnection).filter_by(business_connection_id="bc_on").first()
    assert row is not None
    assert row.user_id == 1
    assert row.user_chat_id == 123
    assert row.is_enabled is True


@pytest.mark.unit
async def test_business_connection_handler_enabled_ignores_non_owner(db_session, monkeypatch):
    """bc de cuenta ajena (no ADMIN_IDS) → no se persiste (result=ignored_non_owner)."""
    monkeypatch.setattr(bch.bot_config, "FEATURE_LINK_ENABLED", True)
    monkeypatch.setattr(bch.bot_config, "ADMIN_IDS", [1])
    monkeypatch.setattr(link_notifier, "get_db_session", lambda: _session_ctx(db_session))
    await handle_business_connection(
        TgBusinessConnection(
            id="bc_ajena",
            user=TgUser(id=999, is_bot=False, first_name="Otra"),
            user_chat_id=999,
            date=1700000000,
            is_enabled=True,
        )
    )
    row = db_session.query(BusinessConnection).filter_by(business_connection_id="bc_ajena").first()
    assert row is None


@pytest.mark.unit
def test_upsert_business_connection_inserts_then_updates(db_session, monkeypatch):
    """Upsert idempotente por PK: inserta y luego actualiza la misma fila (no duplica)."""
    monkeypatch.setattr(link_notifier, "get_db_session", lambda: _session_ctx(db_session))
    monkeypatch.setattr(link_notifier.bot_config, "ADMIN_IDS", [1])

    def _bc(user_chat_id, enabled):
        return TgBusinessConnection(
            id="bc_idem",
            user=TgUser(id=1, is_bot=False, first_name="Duenia"),
            user_chat_id=user_chat_id,
            date=1700000000,
            is_enabled=enabled,
        )

    LinkNotifier.upsert_business_connection(_bc(123, True))
    LinkNotifier.upsert_business_connection(_bc(456, False))
    rows = db_session.query(BusinessConnection).filter_by(business_connection_id="bc_idem").all()
    assert len(rows) == 1
    assert rows[0].user_chat_id == 456
    assert rows[0].is_enabled is False


@pytest.mark.unit
def test_upsert_business_connection_non_owner_not_persisted(db_session, monkeypatch):
    """bc de cuenta ajena (no ADMIN_IDS) → no se persiste (owner scoping)."""
    monkeypatch.setattr(link_notifier, "get_db_session", lambda: _session_ctx(db_session))
    monkeypatch.setattr(link_notifier.bot_config, "ADMIN_IDS", [1])
    LinkNotifier.upsert_business_connection(
        TgBusinessConnection(
            id="bc_ajena",
            user=TgUser(id=999, is_bot=False, first_name="Otra"),
            user_chat_id=999,
            date=1700000000,
            is_enabled=True,
        )
    )
    rows = db_session.query(BusinessConnection).filter_by(business_connection_id="bc_ajena").all()
    assert len(rows) == 0


@pytest.mark.unit
def test_upsert_business_connection_error_is_swallowed(monkeypatch):
    """Error de DB en el upsert → se traga y loguea result=upsert_error (best-effort)."""
    monkeypatch.setattr(link_notifier.bot_config, "ADMIN_IDS", [1])
    monkeypatch.setattr(link_notifier, "get_db_session", _get_db_session_raises)
    # No debe propagar la excepción (best-effort: nunca rompe el flujo del handler).
    LinkNotifier.upsert_business_connection(
        TgBusinessConnection(
            id="bc_err",
            user=TgUser(id=1, is_bot=False, first_name="Duenia"),
            user_chat_id=1,
            date=1700000000,
            is_enabled=True,
        )
    )
