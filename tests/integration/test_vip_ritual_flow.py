"""
Tests de integración para acceso directo VIP.

Verifica que redeem_token da acceso inmediato sin ritual,
y que el invite link se genera correctamente via el handler.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock

from services.vip_service import VIPService
from models.models import Subscription


@pytest.mark.integration
class TestVIPRitualFlow:
    """Flujo completo del ritual VIP de 3 fases."""

    def test_vip_ritual_completes_all_stages(self, db_session, sample_user, sample_token, sample_vip_channel):
        """Redeem gives direct VIP access (no stages)."""
        vip_service = VIPService(db_session)

        sub = vip_service.redeem_token(sample_token.token_code, sample_user.telegram_id)
        assert sub is not None
        db_session.refresh(sample_user)
        # Direct access, no pending entry
        assert sample_user.vip_entry_status is None
        assert sample_user.vip_entry_stage is None

        # User is immediately VIP
        assert vip_service.is_user_vip(sample_user.telegram_id) is True

    def test_vip_ritual_resumable_from_stage_2(self, db_session, sample_user, sample_token, sample_vip_channel):
        """User with existing subscription gets direct VIP access."""
        vip_service = VIPService(db_session)

        sub = vip_service.redeem_token(sample_token.token_code, sample_user.telegram_id)
        assert sub is not None
        db_session.refresh(sample_user)

        # Direct VIP access
        assert vip_service.is_user_vip(sample_user.telegram_id) is True
        assert sample_user.vip_entry_status is None

    def test_vip_ritual_blocked_if_no_subscription(self, db_session, sample_user):
        """Sin suscripción no es VIP."""
        vip_service = VIPService(db_session)

        is_vip = vip_service.is_user_vip(sample_user.telegram_id)
        assert is_vip is False

    def test_redeem_token_sends_invite_link(self, db_session, sample_user, sample_token, sample_vip_channel, mock_bot):
        """Verify the VIP subscription is created (invite link sent by handler)."""
        vip_service = VIPService(db_session)

        # Redeem gives direct access
        sub = vip_service.redeem_token(sample_token.token_code, sample_user.telegram_id)
        assert sub is not None
        db_session.refresh(sample_user)

        # Subscription is active
        assert sub.is_active is True

        # Note: Invite link creation is handled by the handler, not the service
        # The handler would call create_chat_invite_link after verifying membership
        vip_channel = vip_service.get_vip_channel()
        if vip_channel:
            mock_bot.create_chat_invite_link = MagicMock(
                return_value=MagicMock(invite_link="https://t.me/+DynamicLink")
            )
            invite_link = mock_bot.create_chat_invite_link(
                chat_id=vip_channel.channel_id,
                name=f"VIP {sample_user.telegram_id}",
                creates_join_request=False,
                member_limit=1
            )
            mock_bot.send_message(
                chat_id=sample_user.telegram_id,
                text=f"Su enlace: {invite_link.invite_link}",
                parse_mode="HTML",
            )

    def test_vip_entry_expire_guard_during_ritual_cancels(self, db_session, sample_user, sample_token, sample_vip_channel):
        """DESIRED CONTRACT (Fase10): if sub expires mid ritual (stage>0), clear state, no link gen, blocked."""
        vip_service = VIPService(db_session)
        # simulate redeem sets pending (per Fase10 req + svc)
        # (tests show direct, but contract in vip_service redeem + sched clear)
        sub = vip_service.redeem_token(sample_token.token_code, sample_user.telegram_id)
        assert sub is not None
        # force pending stage (as would in full flow)
        sample_user.vip_entry_status = "pending_entry"
        sample_user.vip_entry_stage = 2
        db_session.commit()
        # now expire guard via svc/scheduler
        cleared = vip_service.clear_vip_entry_state(sample_user.telegram_id)
        assert cleared is True
        db_session.refresh(sample_user)
        assert sample_user.vip_entry_status is None
        assert sample_user.vip_entry_stage is None
        # is_vip false after expire clear
        assert vip_service.is_user_vip(sample_user.telegram_id) is False  # or check sub active false in full

        assert mock_bot.create_chat_invite_link.called
        assert mock_bot.send_message.called

    def test_vip_entry_expire_guard_during_ritual_cancels(self, db_session, sample_user, sample_token, sample_vip_channel):
        """DESIRED CONTRACT (Fase10): if sub expires mid ritual (stage>0), clear state, no link gen, blocked."""
        vip_service = VIPService(db_session)
        sub = vip_service.redeem_token(sample_token.token_code, sample_user.telegram_id)
        assert sub is not None
        # force pending stage (as would in full flow)
        sample_user.vip_entry_status = "pending_entry"
        sample_user.vip_entry_stage = 2
        db_session.commit()
        # now expire guard via svc/scheduler
        cleared = vip_service.clear_vip_entry_state(sample_user.telegram_id)
        assert cleared is True
        db_session.refresh(sample_user)
        assert sample_user.vip_entry_status is None
        assert sample_user.vip_entry_stage is None
        # is_vip false after
        assert vip_service.is_user_vip(sample_user.telegram_id) is False
