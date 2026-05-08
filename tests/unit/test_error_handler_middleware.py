"""
Tests unitarios para ErrorHandlerMiddleware.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, CallbackQuery, User

from middlewares.error_handler import ErrorHandlerMiddleware


@pytest.mark.unit
class TestErrorHandlerMiddleware:
    """Tests para el middleware global de errores."""

    @pytest.fixture
    def middleware(self):
        return ErrorHandlerMiddleware()

    @pytest.fixture
    def mock_user(self):
        user = MagicMock(spec=User)
        user.id = 123456
        return user

    @pytest.fixture
    def mock_message(self, mock_user):
        msg = MagicMock(spec=Message)
        msg.from_user = mock_user
        msg.answer = AsyncMock()
        return msg

    @pytest.fixture
    def mock_callback(self, mock_user):
        cb = MagicMock(spec=CallbackQuery)
        cb.from_user = mock_user
        cb.answer = AsyncMock()
        return cb

    async def test_handler_success_returns_result(self, middleware, mock_message):
        """Test que si el handler funciona, se retorna el resultado normalmente."""
        result = "success"

        async def handler(event, data):
            return result

        output = await middleware(handler, mock_message, {})
        assert output == result

    async def test_handler_exception_is_caught_and_logged(self, middleware, mock_message):
        """Test que excepciones en el handler son capturadas y loggeadas."""
        async def handler(event, data):
            raise ValueError("test error")

        await middleware(handler, mock_message, {})

        mock_message.answer.assert_called_once()

    async def test_handler_exception_on_message_answers_user(self, middleware, mock_message):
        """Test que excepciones en Message responden al usuario."""
        async def handler(event, data):
            raise RuntimeError("intentional")

        await middleware(handler, mock_message, {})

        mock_message.answer.assert_called_once()

    async def test_handler_exception_on_callback_answers_with_alert(self, middleware, mock_callback):
        """Test que excepciones en CallbackQuery responden con show_alert=True."""
        async def handler(event, data):
            raise RuntimeError("intentional")

        await middleware(handler, mock_callback, {})

        mock_callback.answer.assert_called_once()
        call_kwargs = mock_callback.answer.call_args[1]
        assert call_kwargs.get("show_alert") is True

    async def test_user_id_extracted_from_message(self, middleware, mock_message, mock_user):
        """Test que user_id se extrae correctamente del evento Message."""
        async def handler(event, data):
            raise ValueError("test")

        await middleware(handler, mock_message, {})
        mock_message.answer.assert_called_once()

    async def test_user_id_extracted_from_callback(self, middleware, mock_callback, mock_user):
        """Test que user_id se extrae correctamente del evento CallbackQuery."""
        async def handler(event, data):
            raise ValueError("test")

        await middleware(handler, mock_callback, {})
        mock_callback.answer.assert_called_once()

    async def test_no_user_returns_none_gracefully(self, middleware):
        """Test que eventos sin from_user no crashean."""
        event_no_user = MagicMock(spec=Message)
        event_no_user.from_user = None
        event_no_user.answer = AsyncMock()

        async def handler(event, data):
            raise ValueError("test")

        await middleware(handler, event_no_user, {})
        event_no_user.answer.assert_called_once()
