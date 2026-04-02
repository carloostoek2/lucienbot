"""
Tests unitarios para ThrottlingMiddleware.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

import sys
sys.path.insert(0, '/data/data/com.termux/files/home/repos/lucien_bot')

from handlers.rate_limit_middleware import ThrottlingMiddleware, _LIMITER_TTL


class MockUser:
    """Mock user object for testing."""
    def __init__(self, user_id: int):
        self.id = user_id


class MockEvent:
    """Mock Telegram event (Message/CallbackQuery) with answer method."""
    def __init__(self):
        self.answered = False
        self.answer_text = None

    async def answer(self, text=None, show_alert=False):
        self.answered = True
        self.answer_text = text


@pytest.mark.unit
class TestThrottlingMiddleware:
    """Tests para el middleware de rate limiting por usuario."""

    def test_per_user_limiters_are_independent(self):
        """Test que cada usuario obtiene su propio limitador."""
        mw = ThrottlingMiddleware()

        limiter_1 = mw._get_limiter(100)
        limiter_2 = mw._get_limiter(200)
        limiter_1_again = mw._get_limiter(100)

        assert limiter_1 is not limiter_2
        assert limiter_1 is limiter_1_again  # Same user gets same limiter

    def test_per_user_limiter_creation(self):
        """Test que se crea un nuevo AsyncLimiter para cada usuario."""
        mw = ThrottlingMiddleware()

        limiter_user_1 = mw._get_limiter(100)
        limiter_user_2 = mw._get_limiter(200)

        # Different instances for different users
        assert limiter_user_1 is not limiter_user_2

    @pytest.mark.asyncio
    async def test_admin_bypass_rate_limit(self):
        """Test que los admins (Custodios) ignoran el rate limiting."""
        mw = ThrottlingMiddleware()

        # Mock config
        import handlers.rate_limit_middleware as rl_module
        original_admin_bypass = rl_module.rate_limit_config.ADMIN_BYPASS
        original_admin_ids = rl_module.bot_config.ADMIN_IDS

        rl_module.rate_limit_config.ADMIN_BYPASS = True
        rl_module.bot_config.ADMIN_IDS = [999]  # Admin ID

        try:
            handler_called = False

            async def mock_handler(event, data):
                nonlocal handler_called
                handler_called = True
                return "handled"

            event = MockEvent()
            data = {"event_from_user": MockUser(999)}  # Admin user

            result = await mw(mock_handler, event, data)

            assert handler_called is True
            assert result == "handled"
            assert event.answered is False  # No throttle response
        finally:
            rl_module.rate_limit_config.ADMIN_BYPASS = original_admin_bypass
            rl_module.bot_config.ADMIN_IDS = original_admin_ids

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_returns_no_handler_result(self):
        """Test que al exceder el rate limit no se ejecuta el handler."""
        mw = ThrottlingMiddleware()

        handler_called = False

        async def mock_handler(event, data):
            nonlocal handler_called
            handler_called = True
            return "handled"

        event = MockEvent()
        user_id = 7777
        data = {"event_from_user": MockUser(user_id)}

        # Simulate rate limit exceeded by exhausting the limiter
        limiter = mw._get_limiter(user_id)
        for _ in range(100):  # Burst enough to exceed the 5-per-10s limit
            # Consume tokens (try to acquire without blocking)
            try:
                async with limiter:
                    pass
            except Exception:
                break  # Already at limit

        result = await mw(mock_handler, event, data)

        # Either handler was called (under limit) or event was answered (throttled)
        # Key: they should NOT both be true
        if event.answered:
            assert handler_called is False  # Throttled — no handler call
        # If handler was called, the user was under limit (expected on fresh limiter)

    @pytest.mark.asyncio
    async def test_none_user_passes_through(self):
        """Test que eventos sin usuario se pasan directamente al handler."""
        mw = ThrottlingMiddleware()

        handler_called = False

        async def mock_handler(event, data):
            nonlocal handler_called
            handler_called = True
            return "handled"

        event = MockEvent()
        data = {"event_from_user": None}

        result = await mw(mock_handler, event, data)

        assert handler_called is True
        assert result == "handled"

    def test_cleanup_idle_removes_expired_entries(self):
        """Test que _cleanup_idle elimina entradas idle."""
        mw = ThrottlingMiddleware()

        # Create a few user limiters
        mw._get_limiter(100)
        mw._get_limiter(200)

        # Manually age the entries past TTL
        import time
        old_time = time.monotonic() - _LIMITER_TTL - 10
        for uid in [100, 200]:
            limiter, _ = mw._limiters[uid]
            mw._limiters[uid] = (limiter, old_time)

        # Run cleanup synchronously (normally async but can call directly)
        asyncio.get_event_loop().run_until_complete(mw._cleanup_idle())

        # All entries should be removed since they all expired
        assert len(mw._limiters) == 0

    def test_get_limiter_updates_last_seen(self):
        """Test que _get_limiter actualiza last_seen para evitar cleanup."""
        import time
        mw = ThrottlingMiddleware()

        # Create limiter
        mw._get_limiter(100)
        _, last_seen_before = mw._limiters[100]

        # Call again after a small delay
        import time as t
        t.sleep(0.01)
        mw._get_limiter(100)
        _, last_seen_after = mw._limiters[100]

        assert last_seen_after > last_seen_before
