"""
Servicio de Besitos - Lucien Bot

Gestiona la moneda virtual (besitos) del sistema de gamificación.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.models import BesitoBalance, BesitoTransaction, TransactionSource, TransactionType

logger = logging.getLogger(__name__)

MAX_ADMIN_BESITO_GRANT = 10_000


class BesitoService:
    """Servicio para gestión de besitos (moneda virtual)"""

    def __init__(self, db: Session = None):
        self.db = db
        self._owns_session = db is None

    def _get_db(self) -> Session:
        """Obtiene la sesión de base de datos activa."""
        if self.db is None:
            self.db = SessionLocal()
        return self.db

    def close(self):
        """Cierra la sesión de base de datos si fue creada por este servicio."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None

    # ==================== GESTIÓN DE SALDO ====================

    def get_or_create_balance(self, user_id: int, lock: bool = False) -> BesitoBalance:
        """Obtiene o crea el saldo de un usuario. Usa lock=True para operaciones de escritura."""
        db = self._get_db()
        query = db.query(BesitoBalance).filter(BesitoBalance.user_id == user_id)

        if lock:
            query = query.with_for_update()

        balance = query.first()

        if not balance:
            balance = BesitoBalance(user_id=user_id, balance=0, total_earned=0, total_spent=0)
            db.add(balance)
            db.commit()
            db.refresh(balance)
            logger.info(f"Nuevo saldo creado para usuario {user_id}")

        return balance

    def get_balance(self, user_id: int) -> int:
        """Obtiene el saldo actual de un usuario"""
        balance = self.get_or_create_balance(user_id)
        return balance.balance

    def get_balance_with_stats(self, user_id: int) -> dict:
        """Obtiene el saldo con estadísticas"""
        balance = self.get_or_create_balance(user_id)
        return {
            "balance": balance.balance,
            "total_earned": balance.total_earned,
            "total_spent": balance.total_spent,
        }

    # ==================== TRANSACCIONES ====================

    def _schedule_besitos_awarded_event(
        self,
        user_id: int,
        amount: int,
        source: TransactionSource,
        reference_id: int | None,
        description: str | None,
    ) -> None:
        """
        Best-effort emit of 'besitos_awarded' event after a successful credit commit.
        Extracted to keep credit_besitos() under the 50-line project limit.
        Never raises; any failure is logged at warning and swallowed (observational only).
        """
        try:
            # Lazy to keep import surface minimal for this module.
            from .event_bus import EVENT_BESITOS_AWARDED, get_event_bus, schedule_emit

            bus = get_event_bus()
            payload = {
                "user_id": user_id,
                "amount": amount,
                "source": source.value if hasattr(source, "value") else str(source),
                "reference_id": reference_id,
                "description": description,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            schedule_emit(bus.emit(EVENT_BESITOS_AWARDED, payload))
        except Exception as emit_err:
            logger.warning(
                f"besito_service | schedule_besitos_awarded_event | user_id={user_id} | result=emit_failed error={emit_err}"
            )

    def credit_besitos(
        self,
        user_id: int,
        amount: int,
        source: TransactionSource,
        description: str = None,
        reference_id: int = None,
    ) -> bool:
        """Acredita besitos (post-commit emite besitos_awarded best-effort via bus)."""
        if amount <= 0:
            logger.error(f"Cantidad inválida para crédito: {amount}")
            return False

        db = self._get_db()
        try:
            # Usar lock para prevenir race conditions
            balance = self.get_or_create_balance(user_id, lock=True)

            # Actualizar saldo
            balance.balance += amount
            balance.total_earned += amount

            # Crear transacción
            transaction = BesitoTransaction(
                user_id=user_id,
                amount=amount,
                type=TransactionType.CREDIT,
                source=source,
                description=description,
                reference_id=reference_id,
            )
            db.add(transaction)
            db.commit()

            # Post-commit best-effort event (observational; never affects return/rollback).
            # Item 3/35 logging hygiene + EventBus expansion: structured format "besito_service | ... | user_id=... | ... result=..." (copy health_service + pool34 al pie)
            self._schedule_besitos_awarded_event(user_id, amount, source, reference_id, description)

            logger.info(f"besito_service | credit_besitos | user_id={user_id} | amount={amount} source={source.value} result=credited")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error acreditando besitos: {e}")
            return False

    def debit_besitos(
        self,
        user_id: int,
        amount: int,
        source: TransactionSource,
        description: str = None,
        reference_id: int = None,
        commit: bool = True,
    ) -> bool:
        """
        Debita besitos de un usuario. Usa SELECT FOR UPDATE para prevenir race conditions.

        Args:
            user_id: ID del usuario
            amount: Cantidad a debitar (debe ser positiva)
            source: Fuente de la transacción
            description: Descripción opcional
            reference_id: ID de referencia
            commit: Si True, hace commit al final. Si False, deja la transacción
                   pendiente para que el llamador haga commit atómico con otras operaciones.

        Returns:
            True si se debitó correctamente
        """
        if amount <= 0:
            logger.error(f"Cantidad inválida para débito: {amount}")
            return False

        db = self._get_db()
        try:
            # Usar lock para prevenir race conditions
            balance = self.get_or_create_balance(user_id, lock=True)

            # Verificar saldo suficiente
            if balance.balance < amount:
                logger.warning(
                    f"Saldo insuficiente para usuario {user_id}: {balance.balance} < {amount}"
                )
                db.rollback()  # Liberar el lock
                return False

            # Actualizar saldo
            balance.balance -= amount
            balance.total_spent += amount

            # Crear transacción (cantidad negativa para débitos)
            transaction = BesitoTransaction(
                user_id=user_id,
                amount=-amount,
                type=TransactionType.DEBIT,
                source=source,
                description=description,
                reference_id=reference_id,
            )
            db.add(transaction)
            if commit:
                db.commit()

            logger.info(f"besito_service | debit_besitos | user_id={user_id} | amount={amount} source={source.value} result=debited")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error debitando besitos: {e}")
            return False

    def has_sufficient_balance(self, user_id: int, amount: int) -> bool:
        """Verifica si un usuario tiene saldo suficiente"""
        balance = self.get_balance(user_id)
        return balance >= amount

    # ==================== HISTORIAL ====================

    def get_transaction_history(self, user_id: int, limit: int = 20) -> list[BesitoTransaction]:
        """Obtiene el historial de transacciones de un usuario"""
        db = self._get_db()
        return (
            db.query(BesitoTransaction)
            .filter(BesitoTransaction.user_id == user_id)
            .order_by(desc(BesitoTransaction.created_at))
            .limit(limit)
            .all()
        )

    def get_transactions_by_source(
        self, user_id: int, source: TransactionSource, limit: int = 20
    ) -> list[BesitoTransaction]:
        """Obtiene transacciones filtradas por fuente"""
        db = self._get_db()
        return (
            db.query(BesitoTransaction)
            .filter(BesitoTransaction.user_id == user_id, BesitoTransaction.source == source)
            .order_by(desc(BesitoTransaction.created_at))
            .limit(limit)
            .all()
        )

    def grant_manual_admin_besitos(
        self, target_user_id: int, amount: int, admin_id: int
    ) -> tuple[bool, int]:
        """Otorga besitos por ajuste manual de Custodio. Returns (success, new_balance)."""
        if amount <= 0 or amount > MAX_ADMIN_BESITO_GRANT:
            logger.warning(
                f"besito_service | grant_manual_admin_besitos | user_id={admin_id} | "
                f"target={target_user_id} | amount={amount} | result=invalid_amount"
            )
            return False, 0
        desc = f"Otorgamiento manual por Custodio (admin_id={admin_id})"
        # reference_id queda None: admin_id es Telegram BigInt y reference_id en BD es Integer.
        ok = self.credit_besitos(
            target_user_id,
            amount,
            TransactionSource.ADMIN,
            description=desc,
            reference_id=None,
        )
        balance = self.get_balance(target_user_id) if ok else 0
        logger.info(
            f"besito_service | grant_manual_admin_besitos | user_id={admin_id} | "
            f"target={target_user_id} | amount={amount} | result={'credited' if ok else 'failed'}"
        )
        return ok, balance

    def debit_manual_admin_besitos(
        self, target_user_id: int, amount: int, admin_id: int
    ) -> tuple[bool, int]:
        """Debita besitos por ajuste manual de Custodio. Returns (success, new_balance)."""
        if amount <= 0 or amount > MAX_ADMIN_BESITO_GRANT:
            logger.warning(
                f"besito_service | debit_manual_admin_besitos | user_id={admin_id} | "
                f"target={target_user_id} | amount={amount} | result=invalid_amount"
            )
            return False, 0
        if not self.has_sufficient_balance(target_user_id, amount):
            logger.warning(
                f"besito_service | debit_manual_admin_besitos | user_id={admin_id} | "
                f"target={target_user_id} | amount={amount} | result=insufficient_balance"
            )
            return False, 0
        desc = f"Débito manual por Custodio (admin_id={admin_id})"
        ok = self.debit_besitos(
            target_user_id,
            amount,
            TransactionSource.ADMIN,
            description=desc,
            reference_id=None,
        )
        balance = self.get_balance(target_user_id) if ok else 0
        logger.info(
            f"besito_service | debit_manual_admin_besitos | user_id={admin_id} | "
            f"target={target_user_id} | amount={amount} | result={'debited' if ok else 'failed'}"
        )
        return ok, balance

    # ==================== ESTADÍSTICAS ====================

    def get_top_users(self, limit: int = 10) -> list[BesitoBalance]:
        """Obtiene los usuarios con más besitos"""
        db = self._get_db()
        return db.query(BesitoBalance).order_by(desc(BesitoBalance.balance)).limit(limit).all()

    def get_total_besitos_in_circulation(self) -> int:
        """Obtiene el total de besitos en circulación"""
        db = self._get_db()
        result = db.query(BesitoBalance).all()
        return sum(b.balance for b in result)
