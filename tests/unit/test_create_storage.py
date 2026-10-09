"""
Tests unitarios para bot.create_storage (selección de FSM storage).

Contrato: RedisStorage cuando REDIS_URL está seteado Y responde; MemoryStorage
en cualquier otro caso. El fallback importa: Redis.from_url es lazy y el cliente
es async, así que sin `await` el ping no comprueba nada — el fallo aparecía en el
primer uso del FSM, en medio de un wizard del usuario.

Por eso los dobles usan AsyncMock en `ping` y se afirma `assert_awaited_once`:
con un MagicMock normal (ping síncrono) el `await` faltante pasaba inadvertido.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

import bot


def _fake_redis(ping_error: Exception | None = None) -> MagicMock:
    """Cliente Redis falso con `ping` async (como el cliente real)."""
    fake = MagicMock()
    fake.ping = AsyncMock(side_effect=ping_error)
    return fake


@pytest.mark.unit
class TestCreateStorage:
    async def test_without_redis_url_falls_back_to_memory(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        storage, client = await bot.create_storage()
        assert isinstance(storage, MemoryStorage)
        assert client is None

    async def test_unreachable_redis_falls_back_to_memory(self, monkeypatch):
        """Un REDIS_URL que no responde debe caer al fallback, no arrancar roto."""
        monkeypatch.setenv("REDIS_URL", "redis://no-such-host:6379/0")
        fake = _fake_redis(ConnectionError("connection refused"))
        with patch("bot.Redis.from_url", return_value=fake):
            storage, client = await bot.create_storage()
        assert isinstance(storage, MemoryStorage)
        assert client is None
        fake.ping.assert_awaited_once()

    async def test_reachable_redis_uses_redis_storage(self, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        fake = _fake_redis()
        with patch("bot.Redis.from_url", return_value=fake):
            storage, client = await bot.create_storage()
        assert isinstance(storage, RedisStorage)
        assert client is fake
        fake.ping.assert_awaited_once()

    async def test_connect_timeouts_are_bounded(self, monkeypatch):
        """El arranque no debe quedarse colgado esperando a Redis."""
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        fake = _fake_redis()
        with patch("bot.Redis.from_url", return_value=fake) as from_url:
            await bot.create_storage()
        kwargs = from_url.call_args.kwargs
        assert kwargs["socket_connect_timeout"] and kwargs["socket_timeout"]
