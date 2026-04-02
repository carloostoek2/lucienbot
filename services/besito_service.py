"""
Servicio de Besitos - Lucien Bot

Gestiona la moneda virtual (besitos) del sistema de gamificación.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.models import (
    BesitoBalance, BesitoTransaction,
    TransactionType, TransactionSource
)
from models.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


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
        query = db.query(BesitoBalance).filter(
            BesitoBalance.user_id == user_id
        )

        if lock:
            query = query.with_for_update()

        balance = query.first()

        if not balance:
            balance = BesitoBalance(
                user_id=user_id,
                balance=0,
                total_earned=0,
                total_spent=0
            )
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
            'balance': balance.balance,
            'total_earned': balance.total_earned,
            'total_spent': balance.total_spent
        }

    # ==================== TRANSACCIONES ====================

    def credit_besitos(self, user_id: int, amount: int, source: TransactionSource,
                       description: str = None, reference_id: int = None) -> bool:
        """
        Acredita besitos a un usuario. Usa SELECT FOR UPDATE para prevenir race conditions.

        Args:
            user_id: ID del usuario
            amount: Cantidad a acreditar (debe ser positiva)
            source: Fuente de la transacción
            description: Descripción opcional
            reference_id: ID de referencia (misión, compra, etc.)

        Returns:
            True si se acreditó correctamente
        """
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
                reference_id=reference_id
            )
            db.add(transaction)
            db.commit()

            logger.info(f"Acreditados {amount} besitos a usuario {user_id} - {source.value}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error acreditando besitos: {e}")
            return False

    def debit_besitos(self, user_id: int, amount: int, source: TransactionSource,
                      description: str = None, reference_id: int = None,
                      commit: bool = True) -> bool:
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
                logger.warning(f"Saldo insuficiente para usuario {user_id}: {balance.balance} < {amount}")
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
                reference_id=reference_id
            )
            db.add(transaction)
            if commit:
                db.commit()

            logger.info(f"Debitados {amount} besitos de usuario {user_id} - {source.value}")
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

    def get_transaction_history(self, user_id: int, limit: int = 20) -> List[BesitoTransaction]:
        """Obtiene el historial de transacciones de un usuario"""
        db = self._get_db()
        return db.query(BesitoTransaction).filter(
            BesitoTransaction.user_id == user_id
        ).order_by(desc(BesitoTransaction.created_at)).limit(limit).all()

    def get_transactions_by_source(self, user_id: int, source: TransactionSource,
                                   limit: int = 20) -> List[BesitoTransaction]:
        """Obtiene transacciones filtradas por fuente"""
        db = self._get_db()
        return db.query(BesitoTransaction).filter(
            BesitoTransaction.user_id == user_id,
            BesitoTransaction.source == source
        ).order_by(desc(BesitoTransaction.created_at)).limit(limit).all()

    # ==================== ESTADÍSTICAS ====================

    def get_top_users(self, limit: int = 10) -> List[BesitoBalance]:
        """Obtiene los usuarios con más besitos"""
        db = self._get_db()
        return db.query(BesitoBalance).order_by(
            desc(BesitoBalance.balance)
        ).limit(limit).all()

    def get_total_besitos_in_circulation(self) -> int:
        """Obtiene el total de besitos en circulación"""
        db = self._get_db()
        result = db.query(BesitoBalance).all()
        return sum(b.balance for b in result)
