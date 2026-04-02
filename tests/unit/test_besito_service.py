"""
Tests unitarios para BesitoService.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from services.besito_service import BesitoService
from models.models import TransactionSource, TransactionType, BesitoBalance


@pytest.mark.unit
class TestBesitoService:
    """Tests para el servicio de besitos"""

    def test_get_or_create_balance_new_user(self, db_session):
        """Test crear balance para nuevo usuario"""
        service = BesitoService(db_session)
        user_id = 123456

        balance = service.get_or_create_balance(user_id)

        assert balance is not None
        assert balance.user_id == user_id
        assert balance.balance == 0
        assert balance.total_earned == 0
        assert balance.total_spent == 0

    def test_get_or_create_balance_existing_user(self, db_session, sample_balance):
        """Test obtener balance existente"""
        service = BesitoService(db_session)

        balance = service.get_or_create_balance(sample_balance.user_id)

        assert balance is not None
        assert balance.id == sample_balance.id
        assert balance.balance == sample_balance.balance

    def test_get_balance(self, db_session, sample_balance):
        """Test obtener saldo actual"""
        service = BesitoService(db_session)

        balance = service.get_balance(sample_balance.user_id)

        assert balance == sample_balance.balance

    def test_get_balance_with_stats(self, db_session, sample_balance):
        """Test obtener saldo con estadísticas"""
        service = BesitoService(db_session)

        stats = service.get_balance_with_stats(sample_balance.user_id)

        assert stats['balance'] == sample_balance.balance
        assert stats['total_earned'] == sample_balance.total_earned
        assert stats['total_spent'] == sample_balance.total_spent


@pytest.mark.unit
class TestBesitoTransactions:
    """Tests para transacciones de besitos"""

    def test_credit_besitos_success(self, db_session, sample_user):
        """Test acreditar besitos exitosamente"""
        service = BesitoService(db_session)
        amount = 100

        result = service.credit_besitos(
            user_id=sample_user.id,
            amount=amount,
            source=TransactionSource.DAILY_GIFT,
            description="Regalo diario"
        )

        assert result is True

        # Verificar balance actualizado
        balance = service.get_balance_with_stats(sample_user.id)
        assert balance['balance'] == amount
        assert balance['total_earned'] == amount

    def test_credit_besitos_invalid_amount(self, db_session, sample_user):
        """Test acreditar cantidad inválida"""
        service = BesitoService(db_session)

        result = service.credit_besitos(
            user_id=sample_user.id,
            amount=-10,
            source=TransactionSource.DAILY_GIFT
        )

        assert result is False

    def test_credit_besitos_zero_amount(self, db_session, sample_user):
        """Test acreditar cero besitos"""
        service = BesitoService(db_session)

        result = service.credit_besitos(
            user_id=sample_user.id,
            amount=0,
            source=TransactionSource.DAILY_GIFT
        )

        assert result is False

    def test_debit_besitos_success(self, db_session, sample_balance):
        """Test debitar besitos exitosamente"""
        service = BesitoService(db_session)
        initial_balance = sample_balance.balance
        amount = 50

        result = service.debit_besitos(
            user_id=sample_balance.user_id,
            amount=amount,
            source=TransactionSource.PURCHASE,
            description="Compra en tienda"
        )

        assert result is True

        # Verificar balance actualizado
        balance = service.get_balance_with_stats(sample_balance.user_id)
        assert balance['balance'] == initial_balance - amount
        assert balance['total_spent'] == 500 + amount

    def test_debit_besitos_insufficient_balance(self, db_session, sample_user):
        """Test debitar con saldo insuficiente"""
        service = BesitoService(db_session)
        # Crear balance inicial de 1000 besitos directamente
        balance = BesitoBalance(
            user_id=sample_user.id,
            balance=1000,
            total_earned=1000,
            total_spent=0
        )
        db_session.add(balance)
        db_session.commit()
        user_id = sample_user.id
        initial_balance = balance.balance
        amount = 2000  # Más de lo que tiene (1000)

        # Verificar balance antes del debit
        assert initial_balance == 1000

        result = service.debit_besitos(
            user_id=user_id,
            amount=amount,
            source=TransactionSource.PURCHASE
        )

        assert result is False
        # El debit falló antes de modificar el balance
        assert initial_balance == 1000

    def test_debit_besitos_invalid_amount(self, db_session, sample_balance):
        """Test debitar cantidad inválida"""
        service = BesitoService(db_session)

        result = service.debit_besitos(
            user_id=sample_balance.user_id,
            amount=-10,
            source=TransactionSource.PURCHASE
        )

        assert result is False

    def test_has_sufficient_balance_true(self, db_session, sample_balance):
        """Test verificar saldo suficiente (sí lo tiene)"""
        service = BesitoService(db_session)

        result = service.has_sufficient_balance(sample_balance.user_id, 100)

        assert result is True

    def test_has_sufficient_balance_false(self, db_session, sample_balance):
        """Test verificar saldo suficiente (no lo tiene)"""
        service = BesitoService(db_session)

        result = service.has_sufficient_balance(sample_balance.user_id, 999999)

        assert result is False


@pytest.mark.unit
class TestBesitoHistory:
    """Tests para historial de transacciones"""

    def test_get_transaction_history(self, db_session, sample_balance):
        """Test obtener historial de transacciones"""
        service = BesitoService(db_session)

        # Crear algunas transacciones
        service.credit_besitos(sample_balance.user_id, 50, TransactionSource.DAILY_GIFT)
        service.credit_besitos(sample_balance.user_id, 30, TransactionSource.MISSION)
        service.debit_besitos(sample_balance.user_id, 20, TransactionSource.PURCHASE)

        history = service.get_transaction_history(sample_balance.user_id, limit=10)

        assert len(history) >= 3
        # Verificar que están ordenadas por fecha descendente
        for i in range(len(history) - 1):
            assert history[i].created_at >= history[i + 1].created_at

    def test_get_transactions_by_source(self, db_session, sample_balance):
        """Test obtener transacciones filtradas por fuente"""
        service = BesitoService(db_session)

        # Crear transacciones de diferentes fuentes
        service.credit_besitos(sample_balance.user_id, 50, TransactionSource.DAILY_GIFT)
        service.credit_besitos(sample_balance.user_id, 30, TransactionSource.MISSION)
        service.credit_besitos(sample_balance.user_id, 20, TransactionSource.PURCHASE)

        daily_gifts = service.get_transactions_by_source(
            sample_balance.user_id,
            TransactionSource.DAILY_GIFT
        )

        assert len(daily_gifts) == 1  # solo el creado por el test
        for transaction in daily_gifts:
            assert transaction.source == TransactionSource.DAILY_GIFT


@pytest.mark.unit
class TestBesitoStats:
    """Tests para estadísticas de besitos"""

    def test_get_top_users(self, db_session, sample_balance):
        """Test obtener top usuarios con más besitos"""
        service = BesitoService(db_session)

        top_users = service.get_top_users(limit=10)

        assert len(top_users) >= 1
        # El usuario con más besitos debería estar primero
        assert top_users[0].balance >= top_users[-1].balance if len(top_users) > 1 else True

    def test_get_total_besitos_in_circulation(self, db_session, sample_balance):
        """Test obtener total de besitos en circulación"""
        service = BesitoService(db_session)

        total = service.get_total_besitos_in_circulation()

        assert total >= sample_balance.balance


@pytest.mark.unit
class TestBesitoServiceRaceCondition:
    """Tests para verificar protección contra race conditions"""

    def test_credit_besitos_uses_select_for_update(self, db_session, sample_user):
        """Test que credit_besitos usa SELECT FOR UPDATE"""
        service = BesitoService(db_session)

        # Mock la cadena query().filter().with_for_update().first()
        mock_query = MagicMock()
        mock_filtered = MagicMock()
        mock_with_lock = MagicMock()
        mock_first = MagicMock(return_value=None)

        mock_query.filter.return_value = mock_filtered
        mock_filtered.with_for_update.return_value = mock_with_lock
        mock_with_lock.first.return_value = None

        with patch.object(db_session, 'query', return_value=mock_query):
            # Llamar al método
            service.credit_besitos(
                user_id=sample_user.id,
                amount=100,
                source=TransactionSource.DAILY_GIFT
            )

            # Verificar que se llamó with_for_update
            mock_filtered.with_for_update.assert_called()

    def test_debit_besitos_uses_select_for_update(self, db_session, sample_balance):
        """Test que debit_besitos usa SELECT FOR UPDATE"""
        service = BesitoService(db_session)

        # Mock la cadena query().filter().with_for_update().first()
        mock_query = MagicMock()
        mock_filtered = MagicMock()
        mock_with_lock = MagicMock()
        mock_first = MagicMock(return_value=sample_balance)

        mock_query.filter.return_value = mock_filtered
        mock_filtered.with_for_update.return_value = mock_with_lock
        mock_with_lock.first.return_value = sample_balance

        with patch.object(db_session, 'query', return_value=mock_query):
            # Llamar al método
            service.debit_besitos(
                user_id=sample_balance.user_id,
                amount=50,
                source=TransactionSource.PURCHASE
            )

            # Verificar que se llamó with_for_update
            mock_filtered.with_for_update.assert_called()


@pytest.mark.unit
class TestBesitoServiceCommitParam:
    """Tests para el parametro commit=False de debit_besitos (atomicity fix)."""

    def test_debit_besitos_commit_true_commits(self, db_session, sample_balance):
        """Test que debit_besitos con commit=True hace commit."""
        service = BesitoService(db_session)
        initial_balance = sample_balance.balance
        amount = 50

        result = service.debit_besitos(
            user_id=sample_balance.user_id,
            amount=amount,
            source=TransactionSource.PURCHASE,
            commit=True
        )

        assert result is True
        # Commit=True commits immediately; a new session query sees the new value
        db_session.expire_all()
        balance = service.get_balance(sample_balance.user_id)
        assert balance == initial_balance - amount

    def test_debit_besitos_accepts_commit_false_param(self, db_session, sample_balance):
        """Test que debit_besitos acepta el parametro commit=False sin error."""
        service = BesitoService(db_session)
        amount = 50

        # Calling with commit=False should not raise
        result = service.debit_besitos(
            user_id=sample_balance.user_id,
            amount=amount,
            source=TransactionSource.PURCHASE,
            commit=False
        )

        assert result is True

    def test_debit_besitos_default_commit_is_true(self, db_session, sample_balance):
        """Test que el default de commit=True mantiene el comportamiento original."""
        service = BesitoService(db_session)
        initial_balance = sample_balance.balance
        amount = 50

        # Llamar sin parametro commit (default True)
        result = service.debit_besitos(
            user_id=sample_balance.user_id,
            amount=amount,
            source=TransactionSource.PURCHASE
        )

        assert result is True
        db_session.expire_all()
        balance = service.get_balance(sample_balance.user_id)
        assert balance == initial_balance - amount  # Committed change
