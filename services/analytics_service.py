"""
Analytics Service - Lucien Bot

Agregacion de metricas y exportacion de datos para Custodios.
"""

import csv
import logging
import tempfile
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.models import BesitoBalance, BesitoTransaction, Subscription, TransactionType, User

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Servicio de analiticas y metricas."""

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self._owns_session = db is None

    def _get_db(self) -> Session:
        """Obtiene la sesion de base de datos activa."""
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def close(self):
        """Cierra la sesion de base de datos si fue creada por este servicio."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    def get_dashboard_stats(self) -> dict:
        """Obtiene metricas generales del bot."""
        db = self._get_db()

        # Total users
        total_users = db.query(User).count()

        # Active VIP subscriptions
        active_vip = db.query(Subscription).filter(Subscription.is_active).count()

        # Total besitos in circulation
        balances = db.query(BesitoBalance).all()
        total_besitos = sum(b.balance for b in balances)

        # Expiring soon (next 48h)
        now = datetime.now(UTC)
        threshold = now + timedelta(hours=48)
        expiring_soon = (
            db.query(Subscription)
            .filter(
                Subscription.is_active,
                Subscription.end_date <= threshold,
                Subscription.end_date > now,
            )
            .count()
        )

        # New users today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        new_today = db.query(User).filter(User.created_at >= today_start).count()

        return {
            "total_users": total_users,
            "active_vip": active_vip,
            "total_besitos": total_besitos,
            "expiring_soon": expiring_soon,
            "new_today": new_today,
        }

    def export_users_csv(self) -> str | None:
        """
        Genera un archivo CSV con datos de usuarios.

        Returns:
            Ruta del archivo CSV, o None si no hay usuarios.
        """
        db = self._get_db()
        users = db.query(User).all()

        if not users:
            return None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False, newline=""
            ) as tmp:
                writer = csv.DictWriter(
                    tmp,
                    fieldnames=[
                        "telegram_id",
                        "username",
                        "balance",
                        "vip_active",
                        "is_active",
                        "created_at",
                    ],
                )
                writer.writeheader()

                for user in users:
                    vip_active = (
                        db.query(Subscription)
                        .filter(Subscription.user_id == user.telegram_id, Subscription.is_active)
                        .first()
                        is not None
                    )

                    balance = (
                        db.query(BesitoBalance)
                        .filter(BesitoBalance.user_id == user.telegram_id)
                        .first()
                    )
                    user_balance = balance.balance if balance else 0

                    writer.writerow(
                        {
                            "telegram_id": user.telegram_id,
                            "username": user.username or "",
                            "balance": user_balance,
                            "vip_active": "Si" if vip_active else "No",
                            "is_active": "Si" if user.is_active else "No",
                            "created_at": (
                                user.created_at.strftime("%Y-%m-%d %H:%M:%S")
                                if user.created_at
                                else ""
                            ),
                        }
                    )

                return tmp.name
        except Exception as e:
            logger.error(f"CSV export error: {e}")
            return None

    def export_activity_csv(self) -> str | None:
        """
        Genera un archivo CSV con historial de actividad (besitos).

        Returns:
            Ruta del archivo CSV, o None si no hay actividad.
        """
        db = self._get_db()
        transactions = (
            db.query(BesitoTransaction)
            .order_by(BesitoTransaction.created_at.desc())
            .limit(1000)
            .all()
        )

        if not transactions:
            return None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False, newline=""
            ) as tmp:
                writer = csv.DictWriter(
                    tmp, fieldnames=["id", "user_id", "amount", "type", "source", "created_at"]
                )
                writer.writeheader()

                for tx in transactions:
                    writer.writerow(
                        {
                            "id": tx.id,
                            "user_id": tx.user_id,
                            "amount": tx.amount,
                            "type": tx.type.value if hasattr(tx.type, "value") else str(tx.type),
                            "source": tx.source.value
                            if hasattr(tx.source, "value")
                            else str(tx.source),
                            "created_at": (
                                tx.created_at.strftime("%Y-%m-%d %H:%M:%S") if tx.created_at else ""
                            ),
                        }
                    )

                return tmp.name
        except Exception as e:
            logger.error(f"Activity CSV export error: {e}")
            return None

    # ==================== ECONOMÍA (Slice 1) ====================
    # Slice 1 of approved economy stats expansion.
    # Pure read-only best-effort reporting on *existing* data:
    # - BesitoBalance.total_earned / total_spent (monotonic counters from credits/debits)
    # - BesitoTransaction (source, type=CREDIT/DEBIT, amount signed, created_at, ref)
    # Windows default 30d for bounded/perf queries (None = full history).
    # Follows AnalyticsService + HealthService patterns *al pie de la letra*
    # (lifecycle, best-effort try/except/degraded, structured logging
    # "analytics_service | verb_context_result | ...", verb+context+result names,
    # <=50 LOC public, no mutation).
    # 0 impact on 3 critical systems (gamif/narrative/channel-VIP),
    # atomicity/EventBus/get_service contracts, or gold invariants (I2 balance=earned-spent,
    # I3 monotonic; "credit survives deliver False").
    # See impact-analyzer report (LOW risk) + approved PLAN.md.
    # Custodios only (via future get_service + is_admin in handlers).

    def _get_since(self, window_days: int | None) -> datetime | None:
        """Helper puro para ventana temporal (best-effort)."""
        if not window_days:
            return None
        return datetime.now(UTC) - timedelta(days=int(window_days))

    def get_economy_overview(self, window_days: int | None = 30) -> dict:
        """Overview de economía (ingresos/spends/circulación/velocity). Best-effort."""
        try:
            db = self._get_db()
            # Lifetime counters from Balance (authoritative, monotonic)
            earned = db.query(func.sum(BesitoBalance.total_earned)).scalar() or 0
            spent = db.query(func.sum(BesitoBalance.total_spent)).scalar() or 0
            circulation = db.query(func.sum(BesitoBalance.balance)).scalar() or 0
            net = earned - spent
            burn_rate = (spent / earned * 100) if earned > 0 else 0.0

            logger.info(
                f"analytics_service | get_economy_overview | window_days={window_days} | earned={earned} spent={spent} circulation={circulation} net={net}"
            )
            return {
                "total_ever_earned": int(earned),
                "total_ever_spent": int(spent),
                "circulation": int(circulation),
                "net_flow": int(net),
                "burn_rate_pct": round(burn_rate, 1),
                "window_days": window_days,
                "status": "ok",
            }
        except Exception as e:
            logger.warning(f"analytics_service | get_economy_overview | error={str(e)[:80]}")
            return {"status": "degraded", "error": str(e)[:80], "window_days": window_days}

    def get_source_attribution(self, window_days: int | None = 30) -> dict:
        """Fuentes de ingresos (solo CREDITs): total, count, % por TransactionSource."""
        try:
            db = self._get_db()
            since = self._get_since(window_days)
            q = db.query(
                BesitoTransaction.source,
                func.sum(BesitoTransaction.amount).label("total"),
                func.count(BesitoTransaction.id).label("count"),
            ).filter(BesitoTransaction.type == TransactionType.CREDIT)
            if since:
                q = q.filter(BesitoTransaction.created_at >= since)
            rows = q.group_by(BesitoTransaction.source).all()

            total_all = sum((r.total or 0) for r in rows)
            items = []
            for r in rows:
                pct = ((r.total or 0) / total_all * 100) if total_all > 0 else 0.0
                src_val = r.source.value if hasattr(r.source, "value") else str(r.source)
                items.append(
                    {
                        "source": src_val,
                        "total": int(r.total or 0),
                        "count": int(r.count or 0),
                        "pct": round(pct, 1),
                    }
                )
            items.sort(key=lambda x: x["total"], reverse=True)

            logger.info(
                f"analytics_service | get_source_attribution | window={window_days} | sources={len(items)} total={total_all}"
            )
            return {
                "sources": items,
                "total_credits": int(total_all),
                "window_days": window_days,
                "status": "ok",
            }
        except Exception as e:
            logger.warning(f"analytics_service | get_source_attribution | error={str(e)[:80]}")
            return {"status": "degraded", "error": str(e)[:80]}

    def get_top_earners(self, limit: int = 20) -> list[dict]:
        """Top usuarios por total_earned histórico (los que más se han explotado)."""
        try:
            db = self._get_db()
            rows = (
                db.query(BesitoBalance)
                .order_by(desc(BesitoBalance.total_earned))
                .limit(int(limit))
                .all()
            )
            result = []
            for b in rows:
                username = ""
                try:
                    u = db.query(User.username).filter(User.telegram_id == b.user_id).first()
                    if u and u.username:
                        username = u.username
                except Exception:
                    pass  # best-effort, como en export_users_csv

                net = (b.total_earned or 0) - (b.total_spent or 0)
                result.append(
                    {
                        "user_id": b.user_id,
                        "username": username,
                        "total_earned": int(b.total_earned or 0),
                        "total_spent": int(b.total_spent or 0),
                        "net": int(net),
                        "current_balance": int(b.balance or 0),
                    }
                )

            logger.info(
                f"analytics_service | get_top_earners | limit={limit} | returned={len(result)}"
            )
            return result
        except Exception as e:
            logger.warning(f"analytics_service | get_top_earners | error={str(e)[:80]}")
            return []
