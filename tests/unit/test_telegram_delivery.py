"""Unit tests para utils/telegram_delivery.py"""

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from utils.telegram_delivery import (
    classify_bad_request_error,
    classify_forbidden_error,
    resolve_private_chat_id,
)

pytestmark = [pytest.mark.unit]


def test_resolve_private_chat_id_prefers_join_request_chat():
    assert resolve_private_chat_id(100, 200) == 200
    assert resolve_private_chat_id(100, None) == 100


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Forbidden: bot was blocked by the user", "permanent:bot_blocked"),
        ("Forbidden: bot can't initiate conversation with a user", "permanent:no_private_chat"),
        ("Forbidden: user is deactivated", "permanent:user_deactivated"),
    ],
)
def test_classify_forbidden_error_known_cases(message, expected):
    exc = TelegramForbiddenError(method="sendMessage", message=message)
    is_perm, code = classify_forbidden_error(exc)
    assert is_perm is True
    assert code == expected


def test_classify_forbidden_error_unknown():
    exc = TelegramForbiddenError(method="sendMessage", message="Forbidden: bot is not an admin")
    is_perm, code = classify_forbidden_error(exc)
    assert is_perm is False
    assert code is None


def test_classify_bad_request_chat_not_found():
    exc = TelegramBadRequest(method="sendMessage", message="Bad Request: chat not found")
    is_perm, code = classify_bad_request_error(exc)
    assert is_perm is True
    assert code == "permanent:chat_not_found"