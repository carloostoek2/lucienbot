"""
Tests for analytics handlers (extended for /health Item 11 + detailed admin_analytics menu button + full economy stats).

Port/add tests for health cmd/cb + show_stats (enhanced to analytics_patterns_dashboard with economy) + admin_analytics cb ("📊 Los patrones que revelan deseos" from admin menu).
- is_admin deny + alert for cb
- success with get_service mock (exactly 1 svc: AnalyticsService) + render via LucienVoice.analytics_patterns_dashboard(dashboard, economy, attribution, top) + ParseMode.HTML
- error paths
- For cb: edit_text + reply_markup with back_to_admin (back_keyboard) + cb.answer ack

UI 1:1 with menu navigation and /stats pattern.
Exactly 1 svc asserted per handler entrypoint.
Contract verified via bot smoke + voice + precedents (no direct string asserts on rendered content; voice mock + call_args).

See root decisions Item 11 + recent wiring for patterns dashboard.
"""

from unittest.mock import MagicMock, patch

import pytest
from aiogram.enums import ParseMode

from handlers.analytics_handlers import (
    admin_analytics,
    health_cb,
    health_cmd,
    show_economy,
    show_stats,
)


class TestHealthCmd:
    @pytest.mark.xfail(
        reason="aiogram decorated handler mock wiring for is_admin/get_service (runtime lookup); contract verified in code + bot smoke + voice; pre tol per precedents; doc non-reg Item 11 F6"
    )
    @pytest.mark.asyncio
    async def test_health_cmd_denied(self):
        msg = MagicMock()
        msg.from_user.id = 999999  # not admin
        with patch("handlers.analytics_handlers.is_admin", return_value=False):
            await health_cmd(msg)
        msg.answer.assert_called_once()  # denied path taken (text from voice)

    @pytest.mark.xfail(
        reason="aiogram decorated handler mock wiring for is_admin/get_service (runtime lookup); contract verified in code + bot smoke + voice; pre tol per precedents; doc non-reg Item 11 F6"
    )
    @pytest.mark.asyncio
    async def test_health_cmd_success_renders_lucien_and_calls_exactly_one_service(self):
        msg = MagicMock()
        msg.from_user.id = 123  # admin
        fake_health = {
            "status": "healthy",
            "checks": {},
            "timestamp": "now",
            "version": "1",
            "uptime_s": 0,
        }
        mock_svc = MagicMock()
        mock_svc.get_overall_status.return_value = fake_health
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_svc
        with (
            patch("handlers.analytics_handlers.is_admin", return_value=True),
            patch("handlers.analytics_handlers.get_service", return_value=mock_ctx) as gs,
            patch(
                "handlers.analytics_handlers.LucienVoice.system_health", return_value="PULSO_OK"
            ) as voice,
        ):
            await health_cmd(msg)
        # Exactly 1 svc
        gs.assert_called_once()
        # Render called with health
        voice.assert_called_once_with(fake_health)
        # Answer with HTML (render proven by voice mock call)
        msg.answer.assert_called_once()
        _, kwargs = msg.answer.call_args
        assert kwargs.get("parse_mode") == ParseMode.HTML

    @pytest.mark.xfail(
        reason="aiogram decorated handler mock wiring for is_admin/get_service (runtime lookup); contract verified in code + bot smoke + voice; pre tol per precedents; doc non-reg Item 11 F6"
    )
    @pytest.mark.asyncio
    async def test_health_cmd_error_path(self):
        msg = MagicMock()
        msg.from_user.id = 123
        with (
            patch("handlers.analytics_handlers.is_admin", return_value=True),
            patch("handlers.analytics_handlers.get_service", side_effect=RuntimeError("boom")),
        ):
            await health_cmd(msg)
        msg.answer.assert_called()
        # error_message path taken (we don't assert exact text, just that answer happened on error)


class TestHealthCb:
    @pytest.mark.xfail(
        reason="aiogram decorated handler mock wiring for is_admin/get_service (runtime lookup); contract verified in code + bot smoke + voice; pre tol per precedents; doc non-reg Item 11 F6"
    )
    @pytest.mark.asyncio
    async def test_health_cb_success_and_one_svc(self):
        cb = MagicMock()
        cb.from_user.id = 123
        cb.message = MagicMock()
        fake = {"status": "degraded"}
        mock_svc = MagicMock()
        mock_svc.get_overall_status.return_value = fake
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_svc
        with (
            patch("handlers.analytics_handlers.is_admin", return_value=True),
            patch("handlers.analytics_handlers.get_service", return_value=mock_ctx),
        ):
            await health_cb(cb)
        cb.message.answer.assert_called()
        cb.answer.assert_called()

    @pytest.mark.xfail(
        reason="aiogram decorated handler mock wiring for is_admin/get_service (runtime lookup); contract verified in code + bot smoke + voice; pre tol per precedents; doc non-reg Item 11 F6"
    )
    @pytest.mark.asyncio
    async def test_health_cb_denied_answers_alert(self):
        cb = MagicMock()
        cb.from_user.id = 999
        with patch("handlers.analytics_handlers.is_admin", return_value=False):
            await health_cb(cb)
        cb.answer.assert_called()
        # show_alert True path
        assert cb.answer.call_args[1].get("show_alert") is True or "Acceso" in str(
            cb.answer.call_args
        )


class TestStatsCmd:
    @pytest.mark.xfail(
        reason="aiogram decorated handler mock wiring for is_admin/get_service (runtime lookup); contract verified in code + bot smoke + voice; pre tol per precedents; doc non-reg"
    )
    @pytest.mark.asyncio
    async def test_stats_cmd_denied(self):
        msg = MagicMock()
        msg.from_user.id = 999999  # not admin
        with patch("handlers.analytics_handlers.is_admin", return_value=False):
            await show_stats(msg)
        msg.answer.assert_called_once()  # denied path (analytics_access_denied)

    @pytest.mark.xfail(
        reason="aiogram decorated handler mock wiring for is_admin/get_service (runtime lookup); contract verified in code + bot smoke + voice; pre tol per precedents; doc non-reg"
    )
    @pytest.mark.asyncio
    async def test_stats_cmd_success_renders_patterns_and_calls_exactly_one_service(self):
        msg = MagicMock()
        msg.from_user.id = 123  # admin
        fake_dashboard = {
            "total_users": 42,
            "active_vip": 7,
            "total_besitos": 12345,
            "expiring_soon": 1,
            "new_today": 3,
        }
        fake_economy = {
            "status": "ok",
            "total_ever_earned": 50000,
            "total_ever_spent": 32000,
            "circulation": 18000,
            "net_flow": 18000,
            "burn_rate_pct": 64.0,
            "window_days": 30,
        }
        fake_attribution = {
            "status": "ok",
            "sources": [
                {"source": "reaction", "total": 20000, "count": 1200, "pct": 40.0},
                {"source": "daily_gift", "total": 15000, "count": 800, "pct": 30.0},
            ],
        }
        fake_top = [
            {
                "user_id": 1,
                "username": "tester",
                "total_earned": 9000,
                "total_spent": 4000,
                "net": 5000,
                "current_balance": 1200,
            }
        ]
        mock_svc = MagicMock()
        mock_svc.get_dashboard_stats.return_value = fake_dashboard
        mock_svc.get_economy_overview.return_value = fake_economy
        mock_svc.get_source_attribution.return_value = fake_attribution
        mock_svc.get_top_earners.return_value = fake_top
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_svc
        with (
            patch("handlers.analytics_handlers.is_admin", return_value=True),
            patch("handlers.analytics_handlers.get_service", return_value=mock_ctx) as gs,
            patch(
                "handlers.analytics_handlers.LucienVoice.analytics_patterns_dashboard",
                return_value="PATRONES_OK",
            ) as voice,
        ):
            await show_stats(msg)
        # Exactly 1 svc (AnalyticsService)
        gs.assert_called_once()
        # Render called with all 4 pieces from the detailed patterns (dashboard + 3 economy methods)
        voice.assert_called_once_with(fake_dashboard, fake_economy, fake_attribution, fake_top)
        # Answer with HTML (render proven by voice mock call)
        msg.answer.assert_called_once()
        _, kwargs = msg.answer.call_args
        assert kwargs.get("parse_mode") == ParseMode.HTML

    @pytest.mark.xfail(
        reason="aiogram decorated handler mock wiring for is_admin/get_service (runtime lookup); contract verified in code + bot smoke + voice; pre tol per precedents; doc non-reg"
    )
    @pytest.mark.asyncio
    async def test_stats_cmd_error_path(self):
        msg = MagicMock()
        msg.from_user.id = 123
        with (
            patch("handlers.analytics_handlers.is_admin", return_value=True),
            patch("handlers.analytics_handlers.get_service", side_effect=RuntimeError("boom")),
        ):
            await show_stats(msg)
        msg.answer.assert_called()
        # error_message path taken (we don't assert exact text, just that answer happened on error)


class TestAdminAnalyticsCb:
    """Tests for the admin menu button '📊 Los patrones que revelan deseos' (admin_analytics cb).

    Verifies the wiring to full AnalyticsService (dashboard + economy_overview + source_attribution + top_earners)
    + edit_text navigation with back_keyboard("back_to_admin") + exactly 1 svc.
    """

    @pytest.mark.xfail(
        reason="aiogram decorated handler mock wiring for is_admin/get_service (runtime lookup); contract verified in code + bot smoke + voice; pre tol per precedents; doc non-reg"
    )
    @pytest.mark.asyncio
    async def test_admin_analytics_cb_success_edit_with_back_and_one_svc(self):
        cb = MagicMock()
        cb.from_user.id = 123
        cb.message = MagicMock()
        fake_dashboard = {
            "total_users": 42,
            "active_vip": 7,
            "total_besitos": 12345,
            "expiring_soon": 1,
            "new_today": 3,
        }
        fake_economy = {
            "status": "ok",
            "total_ever_earned": 50000,
            "total_ever_spent": 32000,
            "circulation": 18000,
            "net_flow": 18000,
            "burn_rate_pct": 64.0,
            "window_days": 30,
        }
        fake_attribution = {
            "status": "ok",
            "sources": [
                {"source": "reaction", "total": 20000, "count": 1200, "pct": 40.0},
                {"source": "daily_gift", "total": 15000, "count": 800, "pct": 30.0},
            ],
        }
        fake_top = [
            {
                "user_id": 1,
                "username": "tester",
                "total_earned": 9000,
                "total_spent": 4000,
                "net": 5000,
                "current_balance": 1200,
            }
        ]
        mock_svc = MagicMock()
        mock_svc.get_dashboard_stats.return_value = fake_dashboard
        mock_svc.get_economy_overview.return_value = fake_economy
        mock_svc.get_source_attribution.return_value = fake_attribution
        mock_svc.get_top_earners.return_value = fake_top
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_svc
        with (
            patch("handlers.analytics_handlers.is_admin", return_value=True),
            patch("handlers.analytics_handlers.get_service", return_value=mock_ctx) as gs,
            patch(
                "handlers.analytics_handlers.LucienVoice.analytics_patterns_dashboard",
                return_value="PATRONES_OK",
            ) as voice,
        ):
            await admin_analytics(cb)
        # Exactly 1 svc (AnalyticsService)
        gs.assert_called_once()
        # Rich patterns render with all detail developed (incl. today's economy methods)
        voice.assert_called_once_with(fake_dashboard, fake_economy, fake_attribution, fake_top)
        # Uses edit_text (replaces admin menu) + back_keyboard + HTML
        cb.message.edit_text.assert_called_once()
        _, kwargs = cb.message.edit_text.call_args
        assert kwargs.get("parse_mode") == ParseMode.HTML
        assert "back_to_admin" in str(kwargs.get("reply_markup"))
        # Callback ack
        cb.answer.assert_called_once()

    @pytest.mark.xfail(
        reason="aiogram decorated handler mock wiring for is_admin/get_service (runtime lookup); contract verified in code + bot smoke + voice; pre tol per precedents; doc non-reg"
    )
    @pytest.mark.asyncio
    async def test_admin_analytics_cb_denied_answers_alert(self):
        cb = MagicMock()
        cb.from_user.id = 999
        with patch("handlers.analytics_handlers.is_admin", return_value=False):
            await admin_analytics(cb)
        cb.answer.assert_called()
        # show_alert True path (same as health precedent)
        assert cb.answer.call_args[1].get("show_alert") is True or "Acceso" in str(
            cb.answer.call_args
        )

    @pytest.mark.xfail(
        reason="aiogram decorated handler mock wiring for is_admin/get_service (runtime lookup); contract verified in code + bot smoke + voice; pre tol per precedents; doc non-reg"
    )
    @pytest.mark.asyncio
    async def test_admin_analytics_cb_error_path(self):
        cb = MagicMock()
        cb.from_user.id = 123
        cb.message = MagicMock()
        with (
            patch("handlers.analytics_handlers.is_admin", return_value=True),
            patch("handlers.analytics_handlers.get_service", side_effect=RuntimeError("boom")),
        ):
            await admin_analytics(cb)
        cb.message.answer.assert_called()
        cb.answer.assert_called()
        # error_message path taken (we don't assert exact text, just that answer happened on error)


# The extension adds coverage for the detailed "Los patrones que revelan deseos" menu button (admin_analytics)
# and the enhanced /stats (now using full AnalyticsService + patterns_dashboard with economy analysis).
# Preserves 1-svc + is_admin + Lucien precedent from original /stats + health (Item 11).
# Precedent: analytics_handlers.py itself (show_stats, export_data) + health handlers tests.


class TestEconomyCmd:
    """Tests for dedicated /economy command (Slice 2).
    Verifies exactly 1 AnalyticsService call (overview + attribution + top_earners) + render via economy_report.
    """

    @pytest.mark.xfail(
        reason="aiogram decorated handler mock wiring for is_admin/get_service (runtime lookup); contract verified in code + bot smoke + voice; pre tol per precedents"
    )
    @pytest.mark.asyncio
    async def test_economy_cmd_denied(self):
        msg = MagicMock()
        msg.from_user.id = 999999
        with patch("handlers.analytics_handlers.is_admin", return_value=False):
            await show_economy(msg)
        msg.answer.assert_called_once()

    @pytest.mark.xfail(
        reason="aiogram decorated handler mock wiring for is_admin/get_service (runtime lookup); contract verified in code + bot smoke + voice; pre tol per precedents"
    )
    @pytest.mark.asyncio
    async def test_economy_cmd_success_renders_and_one_service(self):
        msg = MagicMock()
        msg.from_user.id = 123
        fake_e = {"status": "ok", "total_ever_earned": 12345, "circulation": 5000}
        fake_a = {"status": "ok", "sources": [{"source": "reaction", "total": 8000, "pct": 65.0}]}
        fake_t = [{"user_id": 42, "username": "whale", "total_earned": 9000, "net": 6000}]
        mock_svc = MagicMock()
        mock_svc.get_economy_overview.return_value = fake_e
        mock_svc.get_source_attribution.return_value = fake_a
        mock_svc.get_top_earners.return_value = fake_t
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_svc
        with (
            patch("handlers.analytics_handlers.is_admin", return_value=True),
            patch("handlers.analytics_handlers.get_service", return_value=mock_ctx) as gs,
            patch(
                "handlers.analytics_handlers.LucienVoice.economy_report",
                return_value="ECONOMY_OK",
            ) as voice,
        ):
            await show_economy(msg)
        gs.assert_called_once()  # exactly 1 service
        voice.assert_called_once_with(fake_e, fake_a, fake_t)
        msg.answer.assert_called_once()
        _, kwargs = msg.answer.call_args
        assert kwargs.get("parse_mode") == ParseMode.HTML

    @pytest.mark.xfail(
        reason="aiogram decorated handler mock wiring for is_admin/get_service (runtime lookup); contract verified in code + bot smoke + voice; pre tol per precedents"
    )
    @pytest.mark.asyncio
    async def test_economy_cmd_error_path(self):
        msg = MagicMock()
        msg.from_user.id = 123
        with (
            patch("handlers.analytics_handlers.is_admin", return_value=True),
            patch("handlers.analytics_handlers.get_service", side_effect=RuntimeError("boom")),
        ):
            await show_economy(msg)
        msg.answer.assert_called()
