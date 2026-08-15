"""
Tests para el notificador de activación VIP a Custodios (Item 30).

Cubre:
- Emisión de EVENT_VIP_ACTIVATION_FAILED en los 6 puntos de fallo de redeem_token
  (patch get_event_bus + schedule_emit; assert emit payload y reason correctos).
- Listeners observationales (success reutiliza EVENT_VIP_ACTIVATED; failure DM a
  Custodios con razón). MUST-NOT-mutate: no tocan estado VIP, nunca re-entran a redeem.
- Helpers puros build_activation_* (None -> "N/A"; razón legible delegada a LucienVoice).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.models import Subscription, Token, TokenStatus
from services.event_bus import EVENT_VIP_ACTIVATION_FAILED
from services.vip_notifier import (
    _notify_admins,
    build_activation_failure_text,
    build_activation_success_text,
    on_vip_activation_failed_admin_notify,
    on_vip_activated_admin_notify,
)
from services.vip_service import VIPService


def _assert_emit_called_with(mock_bus, reason, token_code, user_id):
    """Assert the bus.emit was called once with the Item 30 failure payload."""
    mock_bus.emit.assert_called_once_with(
        EVENT_VIP_ACTIVATION_FAILED,
        {"user_id": user_id, "token_code": token_code, "reason": reason},
    )


def _patch_redeem_emits():
    """Contexto que aisla los emits de fallo de redeem_token (bus mock + schedule no-op)."""
    mock_bus = MagicMock()
    ctx = patch("services.vip_service.get_event_bus", return_value=mock_bus), patch(
        "services.vip_service.schedule_emit"
    )
    return mock_bus, ctx


@pytest.mark.unit
class TestVipActivationFailureEmits:
    """Los paths de fallo de redeem_token emiten EVENT_VIP_ACTIVATION_FAILED con razón."""

    def test_redeem_not_found_emits_failure(self, db_session):
        service = VIPService(db_session)
        mock_bus, ctx = _patch_redeem_emits()
        with ctx[0], ctx[1]:
            sub = service.redeem_token("NONEXISTENT", 999001)
        assert sub is None
        _assert_emit_called_with(mock_bus, "not_found", "NONEXISTENT", 999001)

    def test_redeem_used_emits_failure(self, db_session, sample_used_token, sample_user):
        token_code = sample_used_token.token_code  # snapshot plain values (rollback expires ORM obj)
        user_id = sample_user.telegram_id
        service = VIPService(db_session)
        mock_bus, ctx = _patch_redeem_emits()
        with ctx[0], ctx[1]:
            sub = service.redeem_token(token_code, user_id)
        assert sub is None
        _assert_emit_called_with(mock_bus, "used", token_code, user_id)

    def test_redeem_expired_status_emits_failure(
        self, db_session, sample_expired_token, sample_user
    ):
        """Token con status EXPIRED -> reason expired."""
        token_code = sample_expired_token.token_code  # snapshot plain values (rollback expires ORM obj)
        user_id = sample_user.telegram_id
        service = VIPService(db_session)
        mock_bus, ctx = _patch_redeem_emits()
        with ctx[0], ctx[1]:
            sub = service.redeem_token(token_code, user_id)
        assert sub is None
        _assert_emit_called_with(mock_bus, "expired", token_code, user_id)

    def test_redeem_expired_by_date_emits_failure(self, db_session, sample_tariff, sample_user):
        """Token ACTIVE pero expires_at en el pasado -> reason expired (path commit)."""
        token = Token(
            token_code="EXPIREDATE",
            tariff_id=sample_tariff.id,
            status=TokenStatus.ACTIVE,
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        db_session.add(token)
        db_session.commit()
        service = VIPService(db_session)
        mock_bus, ctx = _patch_redeem_emits()
        with ctx[0], ctx[1]:
            sub = service.redeem_token(token.token_code, sample_user.telegram_id)
        assert sub is None
        _assert_emit_called_with(mock_bus, "expired", token.token_code, sample_user.telegram_id)

    def test_redeem_missing_tariff_emits_failure(self, db_session, sample_user):
        """Token con tariff_id inexistente -> reason tariff_not_found."""
        token = Token(token_code="NOTARIFF", tariff_id=99999, status=TokenStatus.ACTIVE)
        db_session.add(token)
        db_session.commit()
        db_session.refresh(token)
        token_code = token.token_code  # snapshot plain values (rollback expires ORM obj)
        user_id = sample_user.telegram_id
        service = VIPService(db_session)
        mock_bus, ctx = _patch_redeem_emits()
        with ctx[0], ctx[1]:
            sub = service.redeem_token(token_code, user_id)
        assert sub is None
        _assert_emit_called_with(mock_bus, "tariff_not_found", token_code, user_id)

    def test_redeem_no_vip_channel_emits_failure(self, db_session, sample_token, sample_user):
        """Sin canal VIP activo -> reason no_vip_channel."""
        token_code = sample_token.token_code  # snapshot plain values (rollback expires ORM obj)
        user_id = sample_user.telegram_id
        service = VIPService(db_session)
        mock_bus, ctx = _patch_redeem_emits()
        with ctx[0], ctx[1]:
            sub = service.redeem_token(token_code, user_id)
        assert sub is None
        _assert_emit_called_with(mock_bus, "no_vip_channel", token_code, user_id)

    def test_redeem_success_returns_subscription_no_failure_emit(
        self, db_session, sample_user, sample_tariff, sample_vip_channel, sample_token
    ):
        """Regresión (FIX-7): éxito retorna Subscription y NO emite el evento de fallo."""
        token_code = sample_token.token_code  # snapshot plain values
        user_id = sample_user.telegram_id
        service = VIPService(db_session)
        mock_bus, ctx = _patch_redeem_emits()
        with ctx[0], ctx[1]:
            sub = service.redeem_token(token_code, user_id)
        assert sub is not None
        assert sub.user_id == user_id
        assert mock_bus.emit.call_count == 1  # solo el emit post-commit de éxito (VIP_ACTIVATED)
        failed_calls = [
            c
            for c in mock_bus.emit.call_args_list
            if c.args and c.args[0] == EVENT_VIP_ACTIVATION_FAILED
        ]
        assert failed_calls == []


def _ctx_for(db_session):
    """Context manager real para get_service(VIPService) enganchado a la sesión del test."""
    svc = VIPService(db_session)
    ctx = MagicMock()
    ctx.__enter__.return_value = svc
    ctx.__exit__.return_value = False
    return ctx


@pytest.mark.unit
class TestVipActivationListeners:
    """Listeners observationales: DM a Custodios, MUST-NOT-mutate, best-effort."""

    @pytest.mark.asyncio
    async def test_on_vip_activation_failed_sends_dm_to_admins(
        self, db_session, sample_user, mock_bot
    ):
        ctx = _ctx_for(db_session)
        payload = {
            "user_id": sample_user.telegram_id,
            "token_code": "USED123456",
            "reason": "used",
        }
        with patch("services.get_service", return_value=ctx), patch(
            "services.vip_notifier._get_bot", return_value=mock_bot
        ), patch("services.vip_notifier.bot_config") as mock_cfg:
            mock_cfg.ADMIN_IDS = [999001, 999002]
            await on_vip_activation_failed_admin_notify(payload)
        assert mock_bot.send_message.await_count == 2
        admin_chats = [c.kwargs["chat_id"] for c in mock_bot.send_message.await_args_list]
        assert set(admin_chats) == {999001, 999002}
        text = mock_bot.send_message.await_args_list[0].kwargs["text"]
        assert "utilizado" in text.lower()
        assert "Motivo" in text

    @pytest.mark.asyncio
    async def test_on_vip_activated_admin_notify_enriches_tariff_and_user(
        self, db_session, sample_user, sample_tariff, sample_vip_channel, sample_token, mock_bot
    ):
        sub = Subscription(
            user_id=sample_user.telegram_id,
            channel_id=sample_vip_channel.id,
            token_id=sample_token.id,
            tariff_id=sample_tariff.id,
            end_date=datetime.now(UTC) + timedelta(days=30),
            is_active=True,
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)
        ctx = _ctx_for(db_session)
        payload = {"user_id": sample_user.telegram_id, "subscription_id": sub.id}
        with patch("services.get_service", return_value=ctx), patch(
            "services.vip_notifier._get_bot", return_value=mock_bot
        ), patch("services.vip_notifier.bot_config") as mock_cfg:
            mock_cfg.ADMIN_IDS = [999001]
            await on_vip_activated_admin_notify(payload)
        assert mock_bot.send_message.await_count == 1
        text = mock_bot.send_message.await_args_list[0].kwargs["text"]
        assert sample_tariff.name in text
        assert str(sample_tariff.duration_days) in text
        assert "@testuser" in text
        assert "Test" in text

    @pytest.mark.asyncio
    async def test_notify_skips_when_no_admin_ids(self, db_session, sample_user, mock_bot):
        ctx = _ctx_for(db_session)
        payload = {
            "user_id": sample_user.telegram_id,
            "token_code": "ANY",
            "reason": "not_found",
        }
        with patch("services.get_service", return_value=ctx), patch(
            "services.vip_notifier._get_bot", return_value=mock_bot
        ), patch("services.vip_notifier.bot_config") as mock_cfg:
            mock_cfg.ADMIN_IDS = []
            await on_vip_activation_failed_admin_notify(payload)
        mock_bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_vip_activation_failed_unknown_user_renders_na(
        self, db_session, mock_bot
    ):
        """FIX-8a: user_id sin fila de User -> identidad 'N/A' y aun así intenta el DM."""
        ctx = _ctx_for(db_session)
        payload = {
            "user_id": 555666777,
            "token_code": "ANY123456",
            "reason": "used",
        }
        with patch("services.get_service", return_value=ctx), patch(
            "services.vip_notifier._get_bot", return_value=mock_bot
        ), patch("services.vip_notifier.bot_config") as mock_cfg:
            mock_cfg.ADMIN_IDS = [999001]
            await on_vip_activation_failed_admin_notify(payload)
        assert mock_bot.send_message.await_count == 1
        text = mock_bot.send_message.await_args_list[0].kwargs["text"]
        assert "N/A" in text

    @pytest.mark.asyncio
    async def test_on_vip_activated_subscription_not_found_no_raise(
        self, db_session, sample_user, mock_bot, caplog
    ):
        """FIX-8b: subscription_id no resuelve -> log not_found y NO propaga excepción."""
        ctx = _ctx_for(db_session)
        payload = {"user_id": sample_user.telegram_id, "subscription_id": 999999}
        with patch("services.get_service", return_value=ctx), patch(
            "services.vip_notifier._get_bot", return_value=mock_bot
        ), patch("services.vip_notifier.bot_config") as mock_cfg:
            mock_cfg.ADMIN_IDS = [999001]
            await on_vip_activated_admin_notify(payload)
        mock_bot.send_message.assert_not_called()
        assert "subscription_not_found" in caplog.text

    @pytest.mark.asyncio
    async def test_notify_admins_continues_after_admin_send_error(self, caplog):
        """FIX-9: si un admin falla en send_message, el resto sigue recibiendo el DM."""
        bot = AsyncMock()
        bot.send_message = AsyncMock(side_effect=[Exception("telegram down"), None])
        with patch("services.vip_notifier.bot_config") as mock_cfg:
            mock_cfg.ADMIN_IDS = [999001, 999002]
            await _notify_admins(bot, "text")
        assert bot.send_message.await_count == 2
        assert "notify_error" in caplog.text


@pytest.mark.unit
class TestVipActivationPureBuilders:
    """Helpers puros: None -> 'N/A'; razón legible delegada a LucienVoice."""

    def test_build_activation_success_text_defaults_to_na(self):
        text = build_activation_success_text(123, None, None, None, None)
        assert "N/A" in text
        assert "123" in text

    def test_build_activation_failure_text_maps_reason_and_token(self):
        text = build_activation_failure_text(123, "testuser", "Test", "used", "USED123456")
        assert "utilizado" in text.lower()
        assert "USED123456" in text

    def test_build_activation_failure_text_escapes_unknown_reason(self):
        """FIX-10: reason desconocido -> fallback HTML-escaped, no inyectado."""
        text = build_activation_failure_text(123, "testuser", "Test", "<unknown>", "TOK123")
        assert "&lt;unknown&gt;" in text
        assert "<unknown>" not in text
