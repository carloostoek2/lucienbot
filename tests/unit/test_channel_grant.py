"""
Tests unitarios para services/channel_grant.py
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.exceptions import TelegramBadRequest

from services.channel_grant import (
    GrantResult,
    append_invite_link,
    build_welcome_payload,
    grant_pending_request,
    is_valid_telegram_invite_link,
    reject_pending_request,
    resolve_channel_message,
)
from utils.lucien_voice import LucienVoice

pytestmark = [pytest.mark.unit]


class TestResolveChannelMessage:
    def test_custom_message_used_when_set(self):
        channel = MagicMock()
        channel.approval_message = "Custom ritual text"
        result = resolve_channel_message(
            channel, "approval_message", LucienVoice.free_entry_ritual, "Test Channel"
        )
        assert result == "Custom ritual text"

    def test_default_when_empty(self):
        channel = MagicMock()
        channel.approval_message = ""
        result = resolve_channel_message(
            channel, "approval_message", LucienVoice.free_entry_ritual, "Test Channel"
        )
        assert "Test Channel" in result

    def test_default_when_whitespace_only(self):
        channel = MagicMock()
        channel.welcome_message = "   "
        result = resolve_channel_message(
            channel, "welcome_message", LucienVoice.free_entry_welcome, "Chan"
        )
        assert "Chan" in result


class TestIsValidTelegramInviteLink:
    def test_valid_and_invalid(self):
        assert is_valid_telegram_invite_link("https://t.me/+Invite123")
        assert not is_valid_telegram_invite_link("javascript:alert(1)")


class TestAppendInviteLink:
    def test_valid_link_appended(self):
        result = append_invite_link("Welcome", "https://t.me/+Invite123")
        assert "https://t.me/+Invite123" in result

    def test_invalid_link_skipped(self):
        result = append_invite_link("Welcome", "javascript:alert(1)")
        assert result == "Welcome"


class TestBuildWelcomePayload:
    def test_with_invite_link(self):
        channel = MagicMock()
        channel.channel_name = "Free Chan"
        channel.welcome_message = None
        channel.invite_link = "https://t.me/+Invite123"
        payload = build_welcome_payload(channel)
        assert "https://t.me/+Invite123" in payload

    def test_without_invite_link(self):
        channel = MagicMock()
        channel.channel_name = "Free Chan"
        channel.welcome_message = "Welcome custom"
        channel.invite_link = None
        payload = build_welcome_payload(channel)
        assert payload == "Welcome custom"


class TestGrantPendingRequest:
    @pytest.mark.asyncio
    async def test_happy_path(self, db_session, sample_user, sample_free_channel):
        from models.models import PendingRequest

        req = PendingRequest(
            user_id=sample_user.telegram_id,
            channel_id=sample_free_channel.id,
            status="pending",
            scheduled_approval_at=datetime.now(UTC),
        )
        db_session.add(req)
        db_session.commit()
        db_session.refresh(req)

        bot = AsyncMock()
        result = await grant_pending_request(db_session, req, bot)

        assert isinstance(result, GrantResult)
        assert result.success is True
        assert req.status == "approved"
        assert req.approved_at is not None
        bot.approve_chat_join_request.assert_called_once_with(
            chat_id=sample_free_channel.channel_id, user_id=sample_user.telegram_id
        )
        bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_already_participant(self, db_session, sample_user, sample_free_channel):
        from models.models import PendingRequest

        req = PendingRequest(
            user_id=sample_user.telegram_id,
            channel_id=sample_free_channel.id,
            status="pending",
            scheduled_approval_at=datetime.now(UTC),
        )
        db_session.add(req)
        db_session.commit()
        db_session.refresh(req)

        bot = AsyncMock()
        bot.approve_chat_join_request.side_effect = TelegramBadRequest(
            method="approve", message="USER_ALREADY_PARTICIPANT"
        )

        result = await grant_pending_request(db_session, req, bot)

        assert result.success is True
        assert req.status == "approved"
        bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_user_channels_too_much_marks_rejected_terminal(
        self, db_session, sample_user, sample_free_channel
    ):
        from models.models import PendingRequest

        req = PendingRequest(
            user_id=sample_user.telegram_id,
            channel_id=sample_free_channel.id,
            status="pending",
            scheduled_approval_at=datetime.now(UTC),
        )
        db_session.add(req)
        db_session.commit()
        db_session.refresh(req)

        bot = AsyncMock()
        bot.approve_chat_join_request.side_effect = TelegramBadRequest(
            method="approve", message="USER_CHANNELS_TOO_MUCH"
        )

        result = await grant_pending_request(db_session, req, bot)

        assert result.success is False
        assert req.status == "rejected"
        assert req.approved_at is None
        bot.decline_chat_join_request.assert_called_once_with(
            chat_id=sample_free_channel.channel_id, user_id=sample_user.telegram_id
        )
        bot.send_message.assert_not_called()


class TestRejectPendingRequest:
    @pytest.mark.asyncio
    async def test_reject_sets_status_rejected(self, db_session, sample_user, sample_free_channel):
        from models.models import PendingRequest

        req = PendingRequest(
            user_id=sample_user.telegram_id,
            channel_id=sample_free_channel.id,
            status="pending",
            scheduled_approval_at=datetime.now(UTC),
        )
        db_session.add(req)
        db_session.commit()
        db_session.refresh(req)

        bot = AsyncMock()
        ok = await reject_pending_request(db_session, req, bot)

        assert ok is True
        assert req.status == "rejected"
        bot.decline_chat_join_request.assert_called_once_with(
            chat_id=sample_free_channel.channel_id, user_id=sample_user.telegram_id
        )
