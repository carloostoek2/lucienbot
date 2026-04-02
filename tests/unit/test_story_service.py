"""
Tests unitarios para StoryService (atomicity fix para advance_to_node).
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, '/data/data/com.termux/files/home/repos/lucien_bot')

from services.story_service import StoryService
from models.models import (
    StoryNode, StoryChoice, UserStoryProgress, ArchetypeType,
    NodeType, TransactionSource
)


@pytest.mark.unit
class TestStoryServiceAtomicity:
    """Tests para verificar atomicidad de advance_to_node (Finding #2)."""

    def test_advance_to_node_calls_debit_besitos_with_commit_false(self, db_session, sample_user):
        """Test que advance_to_node pasa commit=False a debit_besitos."""
        # Setup: crear nodo con costo en besitos
        node = StoryNode(
            title="Test Node",
            content="Test content",
            node_type=NodeType.NARRATIVE,
            cost_besitos=10,
            chapter=1,
            is_active=True,
        )
        db_session.add(node)
        db_session.commit()

        # Setup: usuario con saldo suficiente y progreso inicial
        from models.models import BesitoBalance
        balance = BesitoBalance(
            user_id=sample_user.id,
            balance=100,
            total_earned=100,
            total_spent=0
        )
        db_session.add(balance)
        db_session.commit()

        service = StoryService(db_session)

        # Mock debit_besitos para verificar que se llama con commit=False
        original_debit = service.besito_service.debit_besitos
        debit_call_args = {}

        def mock_debit(user_id, amount, source, description=None, reference_id=None, commit=True):
            debit_call_args['commit'] = commit
            return original_debit(user_id, amount, source, description, reference_id, commit)

        with patch.object(service.besito_service, 'debit_besitos', mock_debit):
            service.advance_to_node(sample_user.id, node.id)

        # Verificar que debit_besitos fue llamado con commit=False
        assert 'commit' in debit_call_args
        assert debit_call_args['commit'] is False, (
            "advance_to_node debe llamar a debit_besitos con commit=False "
            "para mantener atomicidad (besitos + progreso en una transaccion)"
        )

    def test_advance_to_node_atomic_on_success_commits_both(self, db_session, sample_user):
        """Test que advance_to_node exitoso persiste besitos + progreso en una sola transaccion.

        Verifica que cuando advance_to_node tiene exito, tanto el debit de besitos
        como el progreso del usuario se persisten en la BD.
        """
        # Setup: crear nodo con costo
        node = StoryNode(
            title="Test Node",
            content="Test content",
            node_type=NodeType.NARRATIVE,
            cost_besitos=5,
            chapter=1,
            is_active=True,
        )
        db_session.add(node)
        db_session.commit()

        from models.models import BesitoBalance
        balance = BesitoBalance(
            user_id=sample_user.id,
            balance=100,
            total_earned=100,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()

        service = StoryService(db_session)

        # Ejecutar advance_to_node exitosamente
        success, _, progress = service.advance_to_node(sample_user.id, node.id)

        assert success is True
        assert progress is not None

        # Both besitos and progress are persisted atomically
        db_session.expire_all()
        from models.models import BesitoBalance as BB
        db_balance = db_session.query(BB).filter(BB.user_id == sample_user.id).first()
        assert db_balance.balance == 95, "Besitos deben estar debitados en la BD"

        db_session.expire(progress)
        updated_progress = db_session.query(UserStoryProgress).filter(
            UserStoryProgress.user_id == sample_user.id
        ).first()
        assert updated_progress.current_node_id == node.id, "Progreso debe estar guardado"

    def test_advance_to_node_removes_intermediate_commit(self, db_session, sample_user):
        """Test que advance_to_node NO tiene commits intermedios que rompan atomicidad.

        Verifica que debit_besitos se llama con commit=False para que el llamador
        controle el commit atomico al final.
        """
        node = StoryNode(
            title="Test Node",
            content="Test content",
            node_type=NodeType.NARRATIVE,
            cost_besitos=5,
            chapter=1,
            is_active=True,
        )
        db_session.add(node)
        db_session.commit()

        from models.models import BesitoBalance
        balance = BesitoBalance(
            user_id=sample_user.id,
            balance=100,
            total_earned=100,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()

        service = StoryService(db_session)

        # Spy on debit_besitos to verify commit=False is passed
        original_debit = service.besito_service.debit_besitos
        commit_values = []

        def spy_debit(*args, **kwargs):
            commit_values.append(kwargs.get('commit', True))
            return original_debit(*args, **kwargs)

        with patch.object(service.besito_service, 'debit_besitos', spy_debit):
            service.advance_to_node(sample_user.id, node.id)

        # debit_besitos debe ser llamado con commit=False
        assert any(v is False for v in commit_values), (
            "advance_to_node debe llamar a debit_besitos con commit=False "
            "para que el commit atomico se haga al final de advance_to_node"
        )


@pytest.mark.unit
class TestBigIntegerOverflow:
    """Tests para verificar que los campos de besitos usan BigInteger (Finding #5)."""

    def test_besito_balance_uses_biginteger(self):
        """Test que BesitoBalance.balance, total_earned, total_spent son BigInteger."""
        from models.models import BesitoBalance
        from sqlalchemy import BigInteger

        # Verificar que las columnas son BigInteger
        assert isinstance(BesitoBalance.balance.type, BigInteger)
        assert isinstance(BesitoBalance.total_earned.type, BigInteger)
        assert isinstance(BesitoBalance.total_spent.type, BigInteger)

    def test_besito_transaction_amount_uses_biginteger(self):
        """Test que BesitoTransaction.amount es BigInteger."""
        from models.models import BesitoTransaction
        from sqlalchemy import BigInteger

        assert isinstance(BesitoTransaction.amount.type, BigInteger)

    def test_broadcast_reaction_besitos_awarded_uses_biginteger(self):
        """Test que BroadcastReaction.besitos_awarded es BigInteger."""
        from models.models import BroadcastReaction
        from sqlalchemy import BigInteger

        assert isinstance(BroadcastReaction.besitos_awarded.type, BigInteger)
