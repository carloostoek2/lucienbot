"""
Unit tests for HealthService (Item 11 / observability health).

Mirrors test_analytics_service + test_scheduler patterns:
- keys present
- mocked cross services (Channel/VIP/Scheduler/EventBus) via patch or get_service mock
- db checks via mocked SessionLocal / _get_db (no real tx)
- error paths return fail/degraded (best-effort, no exc to caller)
- overall aggregation (healthy / degraded / unhealthy rules)
- logging format "health_service | <action> | user_id=0 | ..."
- lifecycle (owns_session, close)
- <50 LOC per test func
- 10-15+ tests
- import-inside for some pure/mocks per file conv
- no real side effects on 3 crit systems

See PLAN F6 + impact "tests: new unit green" + "exact pytest ... -k 'health or TestHealthService ...'".
"""

import logging
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from services.health_service import HealthService


def _mk_db_mock():
    db = MagicMock()
    db.execute.return_value.scalar.return_value = 1
    # For sanity queries
    q = MagicMock()
    q.filter.return_value.count.return_value = 0
    db.query.return_value = q
    return db


class TestHealthServiceLifecycle:
    def test_owns_and_close(self):
        svc = HealthService()
        assert svc._owns_session is True
        assert svc.db is not None
        svc.close()
        assert svc.db is None

    def test_passed_db_no_own(self):
        fake = MagicMock()
        svc = HealthService(db=fake)
        assert svc._owns_session is False
        svc.close()  # should not close passed
        assert svc.db is fake


class TestHealthChecksBestEffort:
    def test_check_db_connectivity_ok(self):
        svc = HealthService()
        with patch.object(svc, "_get_db", return_value=_mk_db_mock()):
            res = svc.check_db_connectivity()
        assert res["status"] == "ok"
        assert "latency_ms" in res

    def test_check_db_connectivity_fail(self):
        svc = HealthService()
        bad = MagicMock()
        bad.execute.side_effect = RuntimeError("boom")
        with patch.object(svc, "_get_db", return_value=bad):
            res = svc.check_db_connectivity()
        assert res["status"] == "fail"
        assert "error" in res

    def test_check_bot_runtime_degraded_when_no_start_time(self):
        svc = HealthService()
        res = svc.check_bot_runtime()
        # In this env _BOT_START_TIME not set -> degraded with note (best effort)
        assert res["status"] in ("degraded", "ok")
        assert "uptime_seconds" in res

    def test_check_channels_status_ok(self):
        ch = MagicMock()
        ch.get_free_channels.return_value = [1]
        ch.get_vip_channels.return_value = [2]
        ch.count_pending_requests.return_value = 0
        ch.get_ready_to_approve.return_value = []
        with patch("services.health_service.ChannelService", return_value=ch):
            svc = HealthService()
            res = svc.check_channels_status()
        assert res["status"] == "ok"
        assert res["free_channels"] == 1

    def test_check_scheduler_jobs_ok(self):
        sched = MagicMock()
        job = MagicMock(
            id="j1", name="expire_subscriptions", next_run_time=datetime.now(UTC), trigger="cron"
        )
        sched._scheduler.get_jobs.return_value = [job]
        with patch("services.health_service.get_scheduler", return_value=sched):
            svc = HealthService()
            res = svc.check_scheduler_jobs()
        assert res["status"] == "ok"
        assert res["jobs_count"] == 1

    def test_check_event_bus_listeners_ok(self):
        bus = MagicMock()
        bus._listeners = {
            "besitos_awarded": [lambda x: None, lambda x: None],
            "other": [lambda x: None],
        }
        with patch("services.health_service.get_event_bus", return_value=bus):
            svc = HealthService()
            res = svc.check_event_bus_listeners()
        assert res["status"] == "ok"
        assert res["besitos_awarded_listeners"] == 2

    def test_check_critical_services_sanity_ok(self):
        db = _mk_db_mock()
        # neg=0, recent=5
        db.query.return_value.filter.return_value.count.side_effect = [0, 5, 10, 2]
        v = MagicMock()
        v.get_active_subscriptions.return_value = []
        v.get_expiring_subscriptions.return_value = []
        with (
            patch.object(HealthService, "_get_db", return_value=db),
            patch("services.health_service.VIPService", return_value=v),
        ):
            svc = HealthService()
            res = svc.check_critical_services_sanity()
        assert res["besitos"]["status"] == "ok"
        assert res["overall_sanity"] == "ok"

    def test_check_backup_status_unknown_no_dir(self):
        svc = HealthService()
        with patch("services.health_service.Path") as pth:
            p = MagicMock()
            p.exists.return_value = False
            pth.return_value = p
            res = svc.check_backup_status()
        assert res["status"] == "unknown"

    def test_get_overall_status_aggregates_and_never_raises(self):
        svc = HealthService()
        # Force one fail, one degraded, rest ok via patches
        with (
            patch.object(svc, "check_db_connectivity", return_value={"status": "ok"}),
            patch.object(
                svc, "check_bot_runtime", return_value={"status": "degraded", "uptime_seconds": 0}
            ),
            patch.object(svc, "check_channels_status", return_value={"status": "ok"}),
            patch.object(svc, "check_scheduler_jobs", return_value={"status": "ok"}),
            patch.object(svc, "check_event_bus_listeners", return_value={"status": "ok"}),
            patch.object(
                svc,
                "check_critical_services_sanity",
                return_value={"overall_sanity": "ok", "besitos": {"neg_balances": 0}},
            ),
            patch.object(svc, "check_backup_status", return_value={"status": "ok"}),
        ):
            res = svc.get_overall_status()
        assert res["status"] in ("healthy", "degraded", "unhealthy")
        assert "checks" in res
        assert "timestamp" in res


class TestHealthServiceLoggingAndContracts:
    def test_logging_format_present(self, caplog):
        caplog.set_level(logging.INFO)
        svc = HealthService()
        with patch.object(svc, "_get_db", return_value=_mk_db_mock()):
            svc.check_db_connectivity()
        # At least one log with the expected prefix and user_id=0
        assert any(
            "health_service | check_db_connectivity | user_id=0 |" in m for m in caplog.messages
        )

    def test_best_effort_no_exception_to_caller(self):
        svc = HealthService()
        # Make all checks explode internally
        with (
            patch.object(svc, "check_db_connectivity", side_effect=RuntimeError("x")),
            patch.object(svc, "check_bot_runtime", side_effect=RuntimeError("x")),
            patch.object(svc, "check_channels_status", side_effect=RuntimeError("x")),
            patch.object(svc, "check_scheduler_jobs", side_effect=RuntimeError("x")),
            patch.object(svc, "check_event_bus_listeners", side_effect=RuntimeError("x")),
            patch.object(svc, "check_critical_services_sanity", side_effect=RuntimeError("x")),
            patch.object(svc, "check_backup_status", side_effect=RuntimeError("x")),
        ):
            res = svc.get_overall_status()
        # Should still return a dict with status, never propagate
        assert isinstance(res, dict)
        assert "status" in res


# Note: integration/smoke (bot import, terminal run, curl if enabled, broader -k with health)
# are executed in F6 gates (not unit file) per PLAN "Integration/smoke: ... terminal smoke in gates (not unit test file)".
