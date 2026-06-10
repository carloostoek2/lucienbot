"""
Health Service - Lucien Bot (Item 11 / observability health)

Read-only best-effort system health checks for Custodios/ops/platform.
Follows AnalyticsService pattern al pie de la letra:
    __init__(db=None), self._owns_session = db is None, _get_db, close,
    direct model counts for speed, no mutation.
All checks <=50 LOC, verb+context+result naming, mandatory structured logging
"health_service | <action> | user_id=0 | status=... latency=...".
Best-effort + try/except + short budgets; never blocks main loop or tx.
3 critical systems explicitly protected: pure reads only; 0 writes/mutation/side
effects on gamif credits/reactions/daily/missions, narrative progress/archetypes/FSM,
channel pending/approve/expire/bans/subs, VIP grant/revoke.
Arch-enforcer focus: health checks + endpoint + admin views + no impact on 3 crit.

See: impact-analyzer item11, .planning/phases/29-observability-health/PLAN.md,
precedents 28/27/26/25/24/23 (GSD pre every, self-check, pool phrase, copy al pie).
"""

import logging
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.models import BesitoBalance, BesitoTransaction, UserStoryAchievement, UserStoryProgress
from services.channel_service import ChannelService
from services.event_bus import EVENT_BESITOS_AWARDED, get_event_bus
from services.scheduler_service import get_scheduler
from services.vip_service import VIPService

logger = logging.getLogger(__name__)


class HealthService:
    """Servicio de observabilidad y salud del reino (Item 11)."""

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self._owns_session = db is None

    def _get_db(self) -> Session:
        """Obtiene la sesion de base de datos activa (crea si necesario)."""
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def close(self):
        """Cierra la sesion si fue creada por este servicio."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    # -------------------------------------------------------------------------
    # Checks (read-only, best-effort, <=50 LOC, verb+context+result, logging)
    # -------------------------------------------------------------------------

    def check_db_connectivity(self) -> dict:
        """Check DB connectivity and basic ping latency. Best-effort."""
        start = time.time()
        try:
            db = self._get_db()
            db.execute(text("SELECT 1")).scalar()
            latency = int((time.time() - start) * 1000)
            logger.info(
                f"health_service | check_db_connectivity | user_id=0 | status=ok latency_ms={latency}"
            )
            # pool_pre_ping is configured in models/database for postgres
            pool = (
                "pre_ping"
                if "postgresql" in str(SessionLocal.kw.get("bind", ""))
                or "pool_pre_ping" in str(SessionLocal.kw)
                else "sqlite"
            )
            return {"status": "ok", "latency_ms": latency, "pool": pool}
        except Exception as e:
            logger.warning(
                f"health_service | check_db_connectivity | user_id=0 | status=fail error={str(e)[:120]}"
            )
            return {"status": "fail", "error": str(e)[:120]}

    def check_bot_runtime(self) -> dict:
        """Check bot runtime/uptime (best-effort; wired in F3 on_startup)."""
        try:
            # Wired in bot.py __main__ entrypoint (Item 11 observability-health).
            from bot import _BOT_START_TIME  # type: ignore[attr-defined]

            if _BOT_START_TIME is None:
                raise RuntimeError("start time not recorded yet")
            now = datetime.now(UTC)
            uptime = int((now - _BOT_START_TIME).total_seconds())
            logger.info(
                f"health_service | check_bot_runtime | user_id=0 | status=ok uptime_s={uptime}"
            )
            return {
                "status": "ok",
                "uptime_seconds": uptime,
                "start_time": _BOT_START_TIME.isoformat(),
            }
        except Exception as e:
            logger.warning(
                f"health_service | check_bot_runtime | user_id=0 | status=degraded error={str(e)[:80]}"
            )
            return {
                "status": "degraded",
                "uptime_seconds": 0,
                "start_time": None,
                "note": "bot start time not tracked (see bot.py on_startup Item 11 wiring)",
            }

    def check_channels_status(self) -> dict:
        """Check channels (free/VIP counts, pending, ready). Best-effort via publics."""
        ch = None
        try:
            ch = ChannelService()
            free = len(ch.get_free_channels())
            vip = len(ch.get_vip_channels())
            pending = ch.count_pending_requests()
            ready = len(ch.get_ready_to_approve())
            status = "ok" if pending < 50 else ("degraded" if pending < 100 else "unhealthy")
            logger.info(
                f"health_service | check_channels_status | user_id=0 | pending={pending} ready={ready} status={status}"
            )
            return {
                "status": status,
                "free_channels": free,
                "vip_channels": vip,
                "pending_requests": pending,
                "ready_to_approve": ready,
            }
        except Exception as e:
            logger.warning(
                f"health_service | check_channels_status | user_id=0 | status=fail error={str(e)[:80]}"
            )
            return {"status": "fail", "error": str(e)[:80]}
        finally:
            if ch and hasattr(ch, "close"):
                ch.close()

    def check_scheduler_jobs(self) -> dict:
        """Check APScheduler jobs (count + next run for key ones). Best-effort."""
        try:
            scheduler = get_scheduler()
            if not scheduler or not hasattr(scheduler, "_scheduler"):
                return {"status": "fail", "error": "no scheduler or _scheduler"}
            jobs = (
                scheduler._scheduler.get_jobs() if hasattr(scheduler._scheduler, "get_jobs") else []
            )
            job_list = [
                {
                    "id": j.id,
                    "name": getattr(j, "name", j.id),
                    "next_run_time": str(j.next_run_time) if j.next_run_time else None,
                    "trigger": str(j.trigger),
                }
                for j in jobs
            ]
            status = "ok" if jobs else "degraded"
            next_approve = None
            for j in job_list:
                if (
                    "approve" in (j.get("name") or "").lower()
                    or "pending" in (j.get("id") or "").lower()
                ):
                    next_approve = j.get("next_run_time")
                    break
            logger.info(
                f"health_service | check_scheduler_jobs | user_id=0 | jobs={len(jobs)} next_approve={next_approve}"
            )
            return {"status": status, "jobs_count": len(jobs), "jobs": job_list}
        except Exception as e:
            logger.warning(
                f"health_service | check_scheduler_jobs | user_id=0 | status=fail error={str(e)[:80]}"
            )
            return {"status": "fail", "error": str(e)[:80]}

    def check_event_bus_listeners(self) -> dict:
        """Check EventBus registered listeners (counts, besitos_awarded focus). Best-effort."""
        try:
            bus = get_event_bus()
            counts = {e: len(ls) for e, ls in getattr(bus, "_listeners", {}).items()}
            total = sum(counts.values())
            besitos_listeners = counts.get(EVENT_BESITOS_AWARDED, 0)
            logger.info(
                f"health_service | check_event_bus_listeners | user_id=0 | total={total} besitos_listeners={besitos_listeners}"
            )
            return {
                "status": "ok",
                "total_listeners": total,
                "by_event": counts,
                "besitos_awarded_listeners": besitos_listeners,
            }
        except Exception as e:
            logger.warning(
                f"health_service | check_event_bus_listeners | user_id=0 | status=fail error={str(e)[:80]}"
            )
            return {"status": "fail", "error": str(e)[:80]}

    def check_critical_services_sanity(self) -> dict:
        """Check sanity of critical domains (besitos neg, vip active, narrative counts). Best-effort."""
        try:
            db = self._get_db()
            neg = db.query(BesitoBalance).filter(BesitoBalance.balance < 0).count()
            now = datetime.now(UTC)
            recent_tx = (
                db.query(BesitoTransaction)
                .filter(BesitoTransaction.created_at >= now - timedelta(hours=1))
                .count()
            )
            v = VIPService()
            try:
                active = len(v.get_active_subscriptions())
                expiring = len(v.get_expiring_subscriptions(24))
            finally:
                if hasattr(v, "close"):
                    v.close()
            progress = db.query(UserStoryProgress).count()
            achievements = db.query(UserStoryAchievement).count()
            besito_status = "ok" if neg == 0 else "degraded"
            overall = "ok" if neg == 0 else "degraded"
            logger.info(
                f"health_service | check_critical_services_sanity | user_id=0 | neg_besito={neg} active_vip={active} progress={progress}"
            )
            return {
                "besitos": {
                    "neg_balances": neg,
                    "recent_tx_vol": recent_tx,
                    "status": besito_status,
                },
                "vip": {"active_subscriptions": active, "expiring_24h": expiring, "status": "ok"},
                "narrative": {
                    "progress_count": progress,
                    "achievements_count": achievements,
                    "status": "ok",
                },
                "overall_sanity": overall,
            }
        except Exception as e:
            logger.warning(
                f"health_service | check_critical_services_sanity | user_id=0 | status=fail error={str(e)[:80]}"
            )
            return {"status": "fail", "error": str(e)[:80]}

    def check_backup_status(self) -> dict:
        """Check last backup age (backups/ dir mtime). Best-effort, ops only."""
        try:
            backups_dir = Path("backups")
            if not backups_dir.exists():
                return {"status": "unknown", "error": "no backups dir"}
            backups = sorted(backups_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
            latest = backups[0] if backups else None
            if not latest:
                return {"status": "unknown", "error": "no backups found"}
            age_h = (time.time() - latest.stat().st_mtime) / 3600.0
            status = "ok" if age_h < 25 else ("degraded" if age_h < 48 else "fail")
            logger.info(
                f"health_service | check_backup_status | user_id=0 | status={status} age_h={round(age_h, 1)}"
            )
            return {
                "status": status,
                "last_backup": latest.name,
                "age_hours": round(age_h, 1),
            }
        except Exception as e:
            logger.warning(
                f"health_service | check_backup_status | user_id=0 | status=unknown error={str(e)[:80]}"
            )
            return {"status": "unknown", "error": str(e)[:80]}

    def get_overall_status(self) -> dict:
        """Aggregate all checks into overall status. Best-effort, never raises."""
        checks = {}
        for key, meth in (
            ("db", self.check_db_connectivity),
            ("bot", self.check_bot_runtime),
            ("channels", self.check_channels_status),
            ("scheduler", self.check_scheduler_jobs),
            ("event_bus", self.check_event_bus_listeners),
            ("critical_sanity", self.check_critical_services_sanity),
            ("backup", self.check_backup_status),
        ):
            try:
                checks[key] = meth()
            except Exception as e:
                checks[key] = {"status": "fail", "error": str(e)[:80]}
        has_fail = any(c.get("status") == "fail" for c in checks.values())
        has_deg = any(c.get("status") in ("degraded", "unhealthy") for c in checks.values())
        cs = checks.get("critical_sanity", {})
        if has_fail or (
            cs.get("overall_sanity") == "degraded"
            and cs.get("besitos", {}).get("neg_balances", 0) > 0
        ):
            overall = "unhealthy"
        elif has_deg:
            overall = "degraded"
        else:
            overall = "healthy"
        result = {
            "status": overall,
            "checks": checks,
            "timestamp": datetime.now(UTC).isoformat(),
            "version": "1.0-observability-spike",
            "uptime_s": checks.get("bot", {}).get("uptime_seconds", 0),
        }
        logger.info(f"health_service | get_overall_status | user_id=0 | overall={overall} checks=7")
        return result


# =============================================================================
# Item 11 / observability health / arch-enforcer
# HealthService is observational only (read-only/best-effort). MUST NOT mutate
# any critical flows. All checks are on-demand from admin/terminal/endpoint.
# Wiring in bot.py (F3), admin view via exactly 1 get_service(HealthService) +
# is_admin (F4), terminal script (F5), tests (F6), docs via documentador.
# =============================================================================
