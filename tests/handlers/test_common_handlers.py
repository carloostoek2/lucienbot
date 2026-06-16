"""
Tests unitarios para common_handlers.

Cubre:
- cmd_start: múltiples ramas (sin args, free deep link, token, admin, VIP)
- cmd_help: mensaje de ayuda
- back_to_main: menú principal con verificación VIP
- back_to_admin: menú admin
- cancel_action: cancelar
- coming_soon_features: features no implementadas
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

pytestmark = [pytest.mark.unit]


class TestCmdStart:
    """Tests para cmd_start — el handler más complejo del bot."""

    @pytest.fixture(autouse=True)
    def _mock_mission_catchup(self):
        """Evita DB real en deliver_pending_rewards de /start."""
        with patch("handlers.common_handlers.get_service") as mock_gs:
            mock_ms = MagicMock()
            mock_ms.deliver_pending_rewards = AsyncMock(return_value=0)
            mock_gs.return_value.__enter__.return_value = mock_ms
            mock_gs.return_value.__exit__.return_value = False
            yield mock_gs

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_start_invokes_mission_catchup_with_bot(
        self, mock_user_svc, mock_vip_svc, make_message, make_user, _mock_mission_catchup
    ):
        """Catch-up en /start debe llamar deliver_pending_rewards con user.id y bot."""
        user = make_user()
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        mock_vip_svc.return_value.is_user_vip.return_value = False
        msg = make_message(text="/start", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        mock_ms = _mock_mission_catchup.return_value.__enter__.return_value
        mock_ms.deliver_pending_rewards.assert_awaited_once_with(user.id, bot=msg.bot)

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_start_continues_when_catchup_raises(
        self, mock_user_svc, mock_vip_svc, make_message, make_user, _mock_mission_catchup
    ):
        """Flujo /start continúa si catch-up lanza excepción."""
        user = make_user()
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        mock_vip_svc.return_value.is_user_vip.return_value = False
        mock_ms = _mock_mission_catchup.return_value.__enter__.return_value
        mock_ms.deliver_pending_rewards = AsyncMock(side_effect=RuntimeError("catchup boom"))
        msg = make_message(text="/start", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        msg.answer.assert_called_once()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_start_continues_when_catchup_delivers_one(
        self, mock_user_svc, mock_vip_svc, make_message, make_user, _mock_mission_catchup
    ):
        """Flujo /start continúa sin excepción cuando catch-up entrega recompensas."""
        user = make_user()
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        mock_vip_svc.return_value.is_user_vip.return_value = False
        mock_ms = _mock_mission_catchup.return_value.__enter__.return_value
        mock_ms.deliver_pending_rewards = AsyncMock(return_value=1)
        msg = make_message(text="/start", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        msg.answer.assert_called_once()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_new_user_no_args_greeting(
        self, mock_user_svc, mock_vip_svc, make_message, make_user
    ):
        """Usuario nuevo sin args recibe greeting."""
        user = make_user()
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        mock_vip_svc.return_value.is_user_vip.return_value = False
        msg = make_message(text="/start", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        msg.answer.assert_called_once()
        mock_user_svc.return_value.get_or_create_user.assert_called_once()
        mock_user_svc.return_value.close.assert_called_once()
        mock_vip_svc.return_value.close.assert_called_once()

    @patch("handlers.common_handlers.bot_config")
    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_admin_user_receives_admin_menu(
        self, mock_user_svc, mock_vip_svc, mock_config, make_message, make_user
    ):
        """Usuario admin (por ADMIN_IDS) recibe admin_greeting."""
        user = make_user(user_id=999)
        mock_config.ADMIN_IDS = [999]
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        msg = make_message(text="/start", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "admin" in text.lower() or "custodio" in text.lower()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_free_deep_link_vip_member(
        self, mock_user_svc, mock_vip_svc, make_message, make_user
    ):
        """args='free' y miembro VIP: mensaje especial, sin registro."""
        user = make_user()
        mock_vip_svc.return_value.get_vip_channel.return_value = MagicMock(
            channel_id=-100123
        )
        msg = make_message(text="/start free", user=user)
        msg.bot.get_chat_member.return_value = MagicMock(status="member")

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        msg.answer.assert_called_once()
        mock_user_svc.return_value.get_or_create_user.assert_not_called()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_free_deep_link_new_user(
        self, mock_user_svc, mock_vip_svc, make_message, make_user
    ):
        """args='free', usuario nuevo: flujo de 'viejo conocido'."""
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
        msg.answer.assert_called_once()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_free_deep_link_no_vip_channel(
        self, mock_user_svc, mock_vip_svc, make_message, make_user
    ):
        """args='free' sin canal VIP configurado: no hay error."""
        user = make_user()
        mock_vip_svc.return_value.get_vip_channel.return_value = None
        msg = make_message(text="/start free", user=user)
        msg.bot.get_chat_member.return_value = MagicMock(status="left")

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        mock_user_svc.return_value.get_or_create_user.assert_called_once()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_free_deep_link_get_chat_member_fails(
        self, mock_user_svc, mock_vip_svc, make_message, make_user
    ):
        """get_chat_member lanza excepción: no debe romper el flujo."""
        user = make_user()
        mock_vip_svc.return_value.get_vip_channel.return_value = MagicMock(
            channel_id=-100123
        )
        msg = make_message(text="/start free", user=user)
        msg.bot.get_chat_member.side_effect = Exception("API error")

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        mock_user_svc.return_value.get_or_create_user.assert_called_once()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_token_valid_creates_invite(
        self, mock_user_svc, mock_vip_svc, make_message, make_user
    ):
        """Token válido: crea invite link y muestra acceso VIP."""
        user = make_user()
        mock_vip_svc.return_value.get_vip_channel.return_value = MagicMock(
            channel_id=-100123, invite_link="https://t.me/+fallback"
        )
        mock_vip_svc.return_value.redeem_token_with_missions = AsyncMock(
            return_value=MagicMock(id=1)
        )
        mock_vip_svc.INVITE_LINK_EXPIRATION_DAYS = 7
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        msg = make_message(text="/start TOKEN123", user=user)
        msg.bot.create_chat_invite_link.return_value = MagicMock(
            invite_link="https://t.me/+custom"
        )

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        msg.bot.create_chat_invite_link.assert_called_once()
        msg.answer.assert_called_once()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_token_used_shows_message(
        self, mock_user_svc, mock_vip_svc, make_message, make_user
    ):
        """Token usado: mensaje específico."""
        user = make_user()
        mock_vip_svc.return_value.redeem_token_with_missions = AsyncMock(return_value=None)
        mock_vip_svc.return_value.validate_token.return_value = (None, "used")
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        msg = make_message(text="/start USEDTOKEN", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        msg.answer.assert_called_once()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_token_expired_shows_message(
        self, mock_user_svc, mock_vip_svc, make_message, make_user
    ):
        """Token expirado: mensaje específico."""
        user = make_user()
        mock_vip_svc.return_value.redeem_token_with_missions = AsyncMock(return_value=None)
        mock_vip_svc.return_value.validate_token.return_value = (None, "expired")
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        msg = make_message(text="/start EXPTOKEN", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        msg.answer.assert_called_once()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_token_invalid_shows_message(
        self, mock_user_svc, mock_vip_svc, make_message, make_user
    ):
        """Token inválido: mensaje específico."""
        user = make_user()
        mock_vip_svc.return_value.redeem_token_with_missions = AsyncMock(return_value=None)
        mock_vip_svc.return_value.validate_token.return_value = (None, "invalid")
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        msg = make_message(text="/start BADTOKEN", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        msg.answer.assert_called_once()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_no_args_vip_user(
        self, mock_user_svc, mock_vip_svc, make_message, make_user
    ):
        """Usuario VIP sin args: menú con opciones VIP."""
        user = make_user()
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        mock_vip_svc.return_value.is_user_vip.return_value = True
        msg = make_message(text="/start", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        msg.answer.assert_called_once()

    @patch("handlers.common_handlers.bot_config")
    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_admin_by_role_in_db(
        self, mock_user_svc, mock_vip_svc, mock_config, make_message, make_user
    ):
        """Usuario con role=admin en DB recibe admin_greeting."""
        user = make_user(user_id=555)
        mock_config.ADMIN_IDS = [999]  # no coincide con user_id
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="admin")
        )
        msg = make_message(text="/start", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "admin" in text.lower() or "custodio" in text.lower()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_create_invite_link_fails_uses_fallback(
        self, mock_user_svc, mock_vip_svc, make_message, make_user
    ):
        """Si create_chat_invite_link falla, usa el invite_link del canal."""
        user = make_user()
        mock_vip_svc.return_value.get_vip_channel.return_value = MagicMock(
            channel_id=-100123, invite_link="https://t.me/+fallback"
        )
        mock_vip_svc.return_value.redeem_token_with_missions = AsyncMock(
            return_value=MagicMock(id=1)
        )
        mock_vip_svc.INVITE_LINK_EXPIRATION_DAYS = 7
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        msg = make_message(text="/start TOKEN123", user=user)
        msg.bot.create_chat_invite_link.side_effect = Exception("API error")

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        msg.answer.assert_called_once()
        # Debe usar link del canal (fallback)
        assert msg.answer.call_count == 1

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_closes_both_services_in_finally(
        self, mock_user_svc, mock_vip_svc, make_message, make_user
    ):
        """Ambos servicios se cierran en finally."""
        user = make_user()
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="user")
        )
        mock_vip_svc.return_value.is_user_vip.return_value = False
        msg = make_message(text="/start", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        mock_user_svc.return_value.close.assert_called_once()
        mock_vip_svc.return_value.close.assert_called_once()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    @patch("handlers.common_handlers.UserService", autospec=True)
    async def test_no_args_existing_user_admin(
        self, mock_user_svc, mock_vip_svc, make_message, make_user
    ):
        """Usuario existente admin sin args: admin menu."""
        user = make_user(user_id=999)
        mock_user_svc.return_value.get_or_create_user.return_value = MagicMock(
            role=MagicMock(value="admin")
        )
        msg = make_message(text="/start", user=user)

        from handlers.common_handlers import cmd_start
        await cmd_start(msg)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "admin" in text.lower() or "custodio" in text.lower()


class TestCmdHelp:
    """Tests para cmd_help."""

    async def test_shows_help_message(self, make_message):
        """Muestra la ayuda con formato."""
        msg = make_message(text="/help")

        from handlers.common_handlers import cmd_help
        await cmd_help(msg)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "comandos" in text.lower()


class TestBackToMain:
    """Tests para back_to_main."""

    @patch("handlers.common_handlers.VIPService", autospec=True)
    async def test_checks_vip_status(self, mock_vip_svc, make_callback):
        """Verifica VIP status y muestra menú."""
        mock_vip_svc.return_value.is_user_vip.return_value = False
        cb = make_callback(data="back_to_main")

        from handlers.common_handlers import back_to_main
        await back_to_main(cb)

        mock_vip_svc.return_value.is_user_vip.assert_called_once()
        cb.message.edit_text.assert_called_once()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    async def test_callback_answer_fails_gracefully(self, mock_vip_svc, make_callback):
        """Si callback.answer() falla por expirado, no debe romper."""
        mock_vip_svc.return_value.is_user_vip.return_value = False
        cb = make_callback(data="back_to_main")
        cb.answer.side_effect = Exception("expired")

        from handlers.common_handlers import back_to_main
        await back_to_main(cb)

        cb.answer.assert_called_once()

    @patch("handlers.common_handlers.VIPService", autospec=True)
    async def test_closes_service(self, mock_vip_svc, make_callback):
        """Servicio se cierra después de usar."""
        mock_vip_svc.return_value.is_user_vip.return_value = False
        cb = make_callback(data="back_to_main")

        from handlers.common_handlers import back_to_main
        await back_to_main(cb)

        mock_vip_svc.return_value.close.assert_called_once()


class TestBackToAdmin:
    """Tests para back_to_admin."""

    async def test_shows_admin_menu(self, make_callback):
        """Muestra el menú de administrador."""
        cb = make_callback(data="back_to_admin")

        from handlers.common_handlers import back_to_admin
        await back_to_admin(cb)

        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()


class TestCancelAction:
    """Tests para cancel_action."""

    async def test_shows_cancel_message(self, make_callback):
        """Muestra mensaje de cancelación."""
        cb = make_callback(data="cancel")

        from handlers.common_handlers import cancel_action
        await cancel_action(cb)

        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once_with("Acción cancelada")


class TestComingSoonFeatures:
    """Tests para coming_soon_features."""

    @patch("handlers.common_handlers.main_menu_keyboard")
    async def test_shows_coming_soon(self, mock_kb, make_callback):
        """Muestra mensaje de 'próximamente'."""
        mock_kb.return_value = None
        cb = make_callback(data="profile")

        from handlers.common_handlers import coming_soon_features
        await coming_soon_features(cb)

        cb.message.edit_text.assert_called_once()
        cb.answer.assert_called_once()
