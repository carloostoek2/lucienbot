"""Tests unitarios para LinkNotifier (Fase 6 link - emisor [LINK] hacia Diana)."""
import json
import uuid
from unittest.mock import AsyncMock

import pytest

from models.models import BusinessConnection
from services import link_notifier
from services.link_notifier import LinkNotifier


@pytest.mark.unit
async def test_notify_vip_kicked_disabled_does_not_send(mock_bot):
    """Flag OFF (enabled=False) → no envía nada (comportamiento idéntico)."""
    notifier = LinkNotifier(bot=mock_bot, chat_id=-100, enabled=False)
    await notifier.notify_vip_kicked(
        {"user_id": 1, "username": "testuser", "channel_id": 2, "reason": "admin_revoke", "ts": 123}
    )
    mock_bot.send_message.assert_not_awaited()


@pytest.mark.unit
async def test_notify_vip_kicked_enabled_sends_exact_link_payload(mock_bot, monkeypatch):
    """Flag ON → payload [LINK] one-line JSON exacto con username prefijado con '@'."""
    monkeypatch.setattr(link_notifier, "_fetch_enabled_business_connection_id", lambda db: "bc_test")
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
async def test_notify_vip_kicked_send_error_is_swallowed(mock_bot, monkeypatch):
    """send_message lanza → la excepción se traga; no rompe el flujo de expulsión."""
    monkeypatch.setattr(link_notifier, "_fetch_enabled_business_connection_id", lambda db: "bc_test")
    mock_bot.send_message = AsyncMock(side_effect=Exception("boom"))
    notifier = LinkNotifier(bot=mock_bot, chat_id=-100, enabled=True)
    await notifier.notify_vip_kicked(
        {"user_id": 1, "username": "testuser", "channel_id": 2, "reason": "admin_revoke", "ts": 123}
    )
    mock_bot.send_message.assert_awaited_once()


@pytest.mark.unit
async def test_notify_vip_kicked_event_id_fresh_per_event(mock_bot, monkeypatch):
    """Cada envío genera un event_id uuid4 distinto y válido."""
    monkeypatch.setattr(link_notifier, "_fetch_enabled_business_connection_id", lambda db: "bc_test")
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
    db_session.add(
        BusinessConnection(business_connection_id="bc_row", user_id=1, is_enabled=True)
    )
    db_session.commit()
    assert link_notifier._fetch_enabled_business_connection_id(db_session) == "bc_row"


@pytest.mark.unit
def test_fetch_enabled_business_connection_id_returns_none_when_empty(db_session):
    """Sin filas → None."""
    assert link_notifier._fetch_enabled_business_connection_id(db_session) is None
