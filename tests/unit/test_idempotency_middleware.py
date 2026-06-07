"""
Unit tests for IdempotencyMiddleware (gsd-mw-hardening phase 3).

Covers:
- duplicate callback skip + answer() + no handler call
- first-seen callback pass-through + handler call
- Message (and non-CB) always pass-through
- robustness: answer() failure on skip does not propagate / does not call handler
- logging of skip (optional, via caplog if needed)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.types import CallbackQuery, Message

from middlewares.idempotency import IdempotencyMiddleware


pytestmark = [pytest.mark.unit]


class TestIdempotencyMiddleware:
    """Tests for the IdempotencyMiddleware using the shared cache."""

    @pytest.mark.asyncio
    async def test_skips_duplicate_callback_and_answers(self):
        """If cache.is_duplicate returns True for a CB, mw answers and skips handler (dupe skip + answer)."""
        with patch("middlewares.idempotency.idempotency_cache") as mock_cache:
            mock_cache.is_duplicate.return_value = True

            mw = IdempotencyMiddleware()

            cb = MagicMock(spec=CallbackQuery)
            cb.id = "callback-dupe-123"
            cb.from_user = MagicMock()
            cb.from_user.id = 424242
            cb.answer = AsyncMock()

            handler = AsyncMock(return_value="should-not-run")

            result = await mw(handler, cb, {})

            mock_cache.is_duplicate.assert_called_once_with("callback-dupe-123")
            cb.answer.assert_called_once()
            handler.assert_not_called()
            assert result is None  # early return, no value from handler

    @pytest.mark.asyncio
    async def test_passes_through_first_seen_callback(self):
        """Non-duplicate CB is passed to handler (cache.is_duplicate returned False and marked it)."""
        with patch("middlewares.idempotency.idempotency_cache") as mock_cache:
            mock_cache.is_duplicate.return_value = False

            mw = IdempotencyMiddleware()

            cb = MagicMock(spec=CallbackQuery)
            cb.id = "callback-first-456"
            cb.from_user = MagicMock()
            cb.from_user.id = 424242
            # answer should NOT be called by mw on first
            cb.answer = AsyncMock()

            handler = AsyncMock(return_value="processed")

            result = await mw(handler, cb, {})

            mock_cache.is_duplicate.assert_called_once_with("callback-first-456")
            cb.answer.assert_not_called()
            handler.assert_called_once()
            assert result == "processed"

    @pytest.mark.asyncio
    async def test_messages_and_non_callbacks_always_pass_through(self):
        """Any non-CallbackQuery event (e.g. Message) is always passed to handler, no cache check."""
        with patch("middlewares.idempotency.idempotency_cache") as mock_cache:
            mw = IdempotencyMiddleware()

            msg = MagicMock(spec=Message)
            msg.from_user = MagicMock()
            msg.from_user.id = 111

            handler = AsyncMock(return_value="msg-ok")

            result = await mw(handler, msg, {})

            # cache should never be consulted for non-CB
            mock_cache.is_duplicate.assert_not_called()
            handler.assert_called_once()
            assert result == "msg-ok"

    @pytest.mark.asyncio
    async def test_robustness_answer_failure_on_dupe_does_not_crash_and_skips_handler(self):
        """If event.answer() raises on dupe skip, mw still does not call handler and does not propagate."""
        with patch("middlewares.idempotency.idempotency_cache") as mock_cache:
            mock_cache.is_duplicate.return_value = True

            mw = IdempotencyMiddleware()

            cb = MagicMock(spec=CallbackQuery)
            cb.id = "callback-robust-789"
            cb.from_user = MagicMock()
            cb.from_user.id = 424242

            async def failing_answer(*a, **k):
                raise RuntimeError("simulated TG answer failure on dupe ack")

            cb.answer = AsyncMock(side_effect=failing_answer)

            handler = AsyncMock()

            # Should not raise
            result = await mw(handler, cb, {})

            cb.answer.assert_called_once()
            handler.assert_not_called()
            assert result is None

    @pytest.mark.asyncio
    async def test_different_callbacks_are_independent_via_cache(self):
        """Two different CB ids are treated separately (cache behavior exercised via the mw)."""
        with patch("middlewares.idempotency.idempotency_cache") as mock_cache:
            # Simulate cache: first A False, then A True; B always independent False then True
            mock_cache.is_duplicate.side_effect = [False, True, False, True]

            mw = IdempotencyMiddleware()

            def make_cb(cid):
                cb = MagicMock(spec=CallbackQuery)
                cb.id = cid
                cb.from_user = MagicMock()
                cb.from_user.id = 999
                cb.answer = AsyncMock()
                return cb

            h1 = AsyncMock(return_value="h1")
            h2 = AsyncMock(return_value="h2")

            # First A -> pass
            await mw(h1, make_cb("cbA"), {})
            # Second A -> skip
            await mw(h1, make_cb("cbA"), {})
            # First B -> pass
            await mw(h2, make_cb("cbB"), {})
            # Second B -> skip
            await mw(h2, make_cb("cbB"), {})

            # We called is_duplicate 4 times with the ids in order
            calls = [c.args[0] for c in mock_cache.is_duplicate.call_args_list]
            assert calls == ["cbA", "cbA", "cbB", "cbB"]

    @pytest.mark.asyncio
    async def test_callback_without_id_passes_through_without_cache_check(self):
        """Edge: callback with no .id (falsy) skips the dupe guard entirely (if cb_id and ...).
        Passes to handler; no answer from mw; cache never consulted. Covers 'callback sin id' case."""
        with patch("middlewares.idempotency.idempotency_cache") as mock_cache:
            mw = IdempotencyMiddleware()

            cb = MagicMock(spec=CallbackQuery)
            cb.id = None  # or ""
            cb.from_user = MagicMock()
            cb.from_user.id = 424242
            cb.answer = AsyncMock()

            handler = AsyncMock(return_value="ok-no-id")

            result = await mw(handler, cb, {})

            mock_cache.is_duplicate.assert_not_called()
            cb.answer.assert_not_called()
            handler.assert_called_once()
            assert result == "ok-no-id"
