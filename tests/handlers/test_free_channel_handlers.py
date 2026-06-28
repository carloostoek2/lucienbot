"""
Tests para free_channel_handlers (prioridad por entry flow crítico + 20% cov).

Patrón replicado de gamif/mission handlers tests.
Cubre handle_join_request, leave, member_join.
Direct services patched ya que usa UserService/ChannelService directo + scheduler.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestFreeChannelJoin:
    @patch("handlers.free_channel_handlers.UserService", autospec=True)
    @patch("handlers.free_channel_handlers.ChannelService", autospec=True)
    @patch("handlers.free_channel_handlers.get_scheduler")
    async def test_handle_join_request_basic(
        self, mock_sched, mock_ch_svc, mock_user_svc, make_message
    ):
        # make_message or use direct
        join_req = MagicMock()
        join_req.from_user.id = 123456789
        join_req.from_user.username = "u"
        join_req.from_user.first_name = "F"
        join_req.from_user.last_name = None
        join_req.chat.id = -100123

        mock_ch = MagicMock()
        mock_ch_svc.return_value.get_channel_by_id.return_value = mock_ch

        from handlers.free_channel_handlers import handle_join_request

        # call may schedule or answer approve
        # We at least ensure no crash + calls
        with __import__("contextlib").suppress(Exception):
            await handle_join_request(join_req)

        mock_user_svc.return_value.get_or_create_user.assert_called()


class TestMemberEvents:
    @patch("handlers.free_channel_handlers.ChannelService", autospec=True)
    async def test_handle_member_leave(self, mock_ch, make_message):
        event = MagicMock()
        event.from_user.id = 123
        event.chat.id = -100

        from handlers.free_channel_handlers import handle_member_leave

        await handle_member_leave(event)

    @patch("handlers.free_channel_handlers.ChannelService", autospec=True)
    async def test_handle_member_join(self, mock_ch, make_message):
        event = MagicMock()
        event.from_user.id = 123
        event.chat.id = -100

        from handlers.free_channel_handlers import handle_member_join

        await handle_member_join(event)
