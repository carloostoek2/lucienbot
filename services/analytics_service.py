"""
Analytics Service - Lucien Bot

Agregacion de metricas y exportacion de datos para Custodios.
"""
import csv
import tempfile
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.models import User, Subscription, BesitoTransaction, BesitoBalance
from models.database import SessionLocal
import logging

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
        active_vip = db.query(Subscription).filter(
            Subscription.is_active == True
        ).count()

        # Total besitos in circulation
        balances = db.query(BesitoBalance).all()
        total_besitos = sum(b.balance for b in balances)

        # Expiring soon (next 48h)
        now = datetime.utcnow()
        threshold = now + timedelta(hours=48)
        expiring_soon = db.query(Subscription).filter(
            Subscription.is_active == True,
            Subscription.end_date <= threshold,
            Subscription.end_date > now
        ).count()

        # New users today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        new_today = db.query(User).filter(
            User.created_at >= today_start
        ).count()

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

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        )
        try:
            writer = csv.DictWriter(
                tmp,
                fieldnames=[
                    "telegram_id", "username", "balance",
                    "vip_active", "is_active", "created_at"
                ]
            )
            writer.writeheader()

            for user in users:
                vip_active = (
                    db.query(Subscription)
                    .filter(
                        Subscription.user_id == user.telegram_id,
                        Subscription.is_active == True
                    )
                    .first() is not None
                )

                balance = db.query(BesitoBalance).filter(
                    BesitoBalance.user_id == user.telegram_id
                ).first()
                user_balance = balance.balance if balance else 0

                writer.writerow({
                    "telegram_id": user.telegram_id,
                    "username": user.username or "",
                    "balance": user_balance,
                    "vip_active": "Si" if vip_active else "No",
                    "is_active": "Si" if user.is_active else "No",
                    "created_at": (
                        user.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if user.created_at else ""
                    ),
                })

            tmp.close()
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

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        )
        try:
            writer = csv.DictWriter(
                tmp,
                fieldnames=[
                    "id", "user_id", "amount",
                    "type", "source", "created_at"
                ]
            )
            writer.writeheader()

            for tx in transactions:
                writer.writerow({
                    "id": tx.id,
                    "user_id": tx.user_id,
                    "amount": tx.amount,
                    "type": tx.type.value if hasattr(tx.type, 'value') else str(tx.type),
                    "source": tx.source.value if hasattr(tx.source, 'value') else str(tx.source),
                    "created_at": (
                        tx.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if tx.created_at else ""
                    ),
                })

            tmp.close()
            return tmp.name
        except Exception as e:
            logger.error(f"Activity CSV export error: {e}")
            return None
