"""
Tests de integración para common_handlers.

Verifica interacciones reales con BD:
- cmd_start: creación de usuarios, manejo de deep links, tokens
- back_to_main: menú contextual según estado VIP
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

pytestmark = [pytest.mark.integration]


class TestCmdStartIntegration:
    """Integración de cmd_start con BD real."""

    @pytest.fixture(autouse=True)
    def _mock_mission_catchup(self):
        with patch("handlers.common_handlers.get_service") as mock_gs:
            mock_ms = MagicMock()
            mock_ms.deliver_pending_rewards = AsyncMock(return_value=0)
            mock_gs.return_value.__enter__.return_value = mock_ms
            mock_gs.return_value.__exit__.return_value = False
            yield mock_gs

    @patch("handlers.common_handlers.VIPService")
    @patch("handlers.common_handlers.UserService")
    async def test_new_user_created_in_db(
        self, mock_user_svc, mock_vip_svc, db_session, make_message, make_user
    ):
        """Usuario nuevo sin args: se crea en BD."""
        user = make_user()
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        mock_vip_svc.return_value.is_user_vip.return_value = False
        msg = make_message(text="/start", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        mock_user_svc.return_value.get_or_create_user.assert_called_once()
        msg.answer.assert_called_once()

    @patch("utils.admin.bot_config")
    @patch("handlers.common_handlers.VIPService")
    @patch("handlers.common_handlers.UserService")
    async def test_admin_id_detected(
        self, mock_user_svc, mock_vip_svc, mock_config, db_session, make_message, make_user
    ):
        """Usuario en ADMIN_IDS recibe admin_greeting."""
        user = make_user(user_id=999)
        mock_config.ADMIN_IDS = [999]
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        msg = make_message(text="/start", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        mock_user_svc.return_value.get_or_create_user.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "custodio" in text.lower() or "admin" in text.lower()

    @patch("handlers.common_handlers.VIPService")
    @patch("handlers.common_handlers.UserService")
    async def test_token_flow_redeem_called(
        self, mock_user_svc, mock_vip_svc, db_session, make_message, make_user
    ):
        """Con token: redeem_token es llamado."""
        user = make_user()
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        mock_vip_svc.return_value.get_vip_channel.return_value = MagicMock(
            channel_id=-100123, invite_link="https://t.me/+vip"
        )
        mock_vip_svc.return_value.redeem_token_with_missions = AsyncMock(
            return_value=MagicMock(id=1)
        )
        mock_vip_svc.return_value.create_vip_invite_link = AsyncMock(
            return_value="https://t.me/+custom"
        )
        msg = make_message(text="/start ABC123", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        mock_vip_svc.return_value.redeem_token_with_missions.assert_awaited_once_with(
            "ABC123", user.id, bot=msg.bot
        )
        mock_vip_svc.return_value.create_vip_invite_link.assert_awaited_once_with(
            msg.bot, user.id, allow_fallback=True
        )

    @patch("handlers.common_handlers.VIPService")
    @patch("handlers.common_handlers.UserService")
    async def test_free_deep_link_creates_user(
        self, mock_user_svc, mock_vip_svc, db_session, make_message, make_user
    ):
        """Deep link free, usuario nuevo: se llama create_user."""
        user = make_user()
        mock_vip_svc.return_value.get_vip_channel.return_value = MagicMock(
            channel_id=-100123
        )
        mock_user_svc.return_value.get_user.return_value = None
        msg = make_message(text="/start free", user=user)
        msg.bot.get_chat_member.return_value = MagicMock(status="left")

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        mock_user_svc.return_value.create_user.assert_called_once()
        mock_user_svc.return_value.get_or_create_user.assert_not_called()

    @patch("handlers.common_handlers.VIPService")
    @patch("handlers.common_handlers.UserService")
    async def test_free_deep_link_existing_user(
        self, mock_user_svc, mock_vip_svc, db_session, make_message, make_user
    ):
        """Deep link free, usuario existente: fluye a /start normal."""
        user = make_user()
        mock_vip_svc.return_value.get_vip_channel.return_value = MagicMock(
            channel_id=-100123
        )
        mock_user_svc.return_value.get_user.return_value = MagicMock(id=1)
        msg = make_message(text="/start free", user=user)
        msg.bot.get_chat_member.return_value = MagicMock(status="left")

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        mock_user_svc.return_value.create_user.assert_not_called()
        mock_user_svc.return_value.get_or_create_user.assert_called_once()


class TestBackToMainIntegration:
    """Integración de back_to_main."""

    @patch("handlers.common_handlers.VIPService")
    async def test_vip_user_receives_vip_menu(
        self, mock_vip_svc, db_session, make_callback, make_user
    ):
        """VIP user: muestra menú con opciones VIP."""
        user = make_user()
        mock_vip_svc.return_value.is_user_vip.return_value = True
        cb = make_callback(data="back_to_main", user=user)

        from handlers.common_handlers import back_to_main
        await back_to_main(cb)

        mock_vip_svc.return_value.is_user_vip.assert_called_once()
        cb.message.edit_text.assert_called_once()

    @patch("handlers.common_handlers.VIPService")
    async def test_non_vip_user_receives_standard_menu(
        self, mock_vip_svc, db_session, make_callback, make_user
    ):
        """Non-VIP user: menú estándar."""
        user = make_user()
        mock_vip_svc.return_value.is_user_vip.return_value = False
        cb = make_callback(data="back_to_main", user=user)

        from handlers.common_handlers import back_to_main
        await back_to_main(cb)

        mock_vip_svc.return_value.is_user_vip.assert_called_once()
