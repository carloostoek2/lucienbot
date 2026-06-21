"""
Tests unitarios para StoryService (atomicity fix para advance_to_node).
"""

from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError

from models.models import (
    ArchetypeType,
    NodeType,
    StoryChoice,
    StoryNode,
    TransactionSource,
    UserStoryProgress,
)
from services.story_service import StoryService


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
            user_id=sample_user.id, balance=100, total_earned=100, total_spent=0
        )
        db_session.add(balance)
        db_session.commit()

        service = StoryService(db_session)

        # Mock debit_besitos para verificar que se llama con commit=False
        original_debit = service.besito_service.debit_besitos
        debit_call_args = {}

        def mock_debit(user_id, amount, source, description=None, reference_id=None, commit=True):
            debit_call_args["commit"] = commit
            return original_debit(user_id, amount, source, description, reference_id, commit)

        with patch.object(service.besito_service, "debit_besitos", mock_debit):
            service.advance_to_node(sample_user.id, node.id)

        # Verificar que debit_besitos fue llamado con commit=False
        assert "commit" in debit_call_args
        assert debit_call_args["commit"] is False, (
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
        from models.models import BesitoBalance

        db_balance = (
            db_session.query(BesitoBalance).filter(BesitoBalance.user_id == sample_user.id).first()
        )
        assert db_balance.balance == 95, "Besitos deben estar debitados en la BD"

        db_session.expire(progress)
        updated_progress = (
            db_session.query(UserStoryProgress)
            .filter(UserStoryProgress.user_id == sample_user.id)
            .first()
        )
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
            commit_values.append(kwargs.get("commit", True))
            return original_debit(*args, **kwargs)

        with patch.object(service.besito_service, "debit_besitos", spy_debit):
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
        from sqlalchemy import BigInteger

        from models.models import BesitoBalance

        # Verificar que las columnas son BigInteger
        assert isinstance(BesitoBalance.balance.type, BigInteger)
        assert isinstance(BesitoBalance.total_earned.type, BigInteger)
        assert isinstance(BesitoBalance.total_spent.type, BigInteger)

    def test_besito_transaction_amount_uses_biginteger(self):
        """Test que BesitoTransaction.amount es BigInteger."""
        from sqlalchemy import BigInteger

        from models.models import BesitoTransaction

        assert isinstance(BesitoTransaction.amount.type, BigInteger)

    def test_broadcast_reaction_besitos_awarded_uses_biginteger(self):
        """Test que BroadcastReaction.besitos_awarded es BigInteger."""
        from sqlalchemy import BigInteger

        from models.models import BroadcastReaction

        assert isinstance(BroadcastReaction.besitos_awarded.type, BigInteger)


@pytest.mark.unit
class TestStoryServiceCRUD:
    def test_create_node(self, db_session, sample_admin):
        service = StoryService(db_session)
        node = service.create_node(
            title="Node A",
            content="Content A",
            node_type=NodeType.NARRATIVE,
            chapter=1,
            created_by=sample_admin.telegram_id,
        )
        assert node.title == "Node A"
        assert node.node_type == NodeType.NARRATIVE

    def test_add_choice_to_node(self, db_session, sample_story_node):
        service = StoryService(db_session)
        choice = service.add_choice_to_node(
            sample_story_node.id, text="Choice 1", next_node_id=None, archetype_points=5
        )
        assert choice.node_id == sample_story_node.id
        assert choice.text == "Choice 1"
        assert choice.archetype_points == 5

    def test_get_node_choices(self, db_session, sample_story_node, sample_story_choice):
        service = StoryService(db_session)
        choices = service.get_node_choices(sample_story_node.id)
        assert any(c.id == sample_story_choice.id for c in choices)


@pytest.mark.unit
class TestStoryServiceArchetype:
    def test_calculate_archetype(self, db_session, sample_user):
        service = StoryService(db_session)
        progress = service.get_or_create_progress(sample_user.id)
        progress.explorador_points = 10
        progress.seductor_points = 5
        db_session.commit()
        archetype = service.calculate_archetype(progress)
        assert archetype == ArchetypeType.EXPLORADOR

    def test_get_user_archetype(self, db_session, sample_user):
        service = StoryService(db_session)
        progress = service.get_or_create_progress(sample_user.id)
        progress.archetype = ArchetypeType.MISTERIOSO
        db_session.commit()
        assert service.get_user_archetype(sample_user.id) == ArchetypeType.MISTERIOSO


@pytest.mark.unit
class TestStoryServiceBranching:
    def test_advance_to_node_with_choice_updates_archetype_points(self, db_session, sample_user):
        service = StoryService(db_session)
        from models.models import BesitoBalance

        bb = BesitoBalance(user_id=sample_user.id, balance=100, total_earned=100, total_spent=0)
        db_session.add(bb)
        db_session.commit()

        node_a = service.create_node("Decision", "Choose", NodeType.DECISION, chapter=1)
        node_b = service.create_node("Outcome B", "You chose B", NodeType.NARRATIVE, chapter=1)
        choice = service.add_choice_to_node(
            node_a.id,
            "Go to B",
            node_b.id,
            choice_archetype=ArchetypeType.EXPLORADOR,
            archetype_points=7,
        )

        service.advance_to_node(sample_user.id, node_a.id)
        success, msg, progress = service.advance_to_node(
            sample_user.id, node_b.id, choice_id=choice.id
        )
        assert success is True
        db_session.refresh(progress)
        assert progress.current_node_id == node_b.id
        assert progress.explorador_points == 7

    def test_advance_to_node_deducts_besitos(self, db_session, sample_user):
        service = StoryService(db_session)
        from models.models import BesitoBalance

        bb = BesitoBalance(user_id=sample_user.id, balance=100, total_earned=100, total_spent=0)
        db_session.add(bb)
        db_session.commit()

        node = service.create_node(
            "Costly", "Costs 10", NodeType.NARRATIVE, chapter=1, cost_besitos=10
        )
        success, msg, progress = service.advance_to_node(sample_user.id, node.id)
        assert success is True
        db_session.refresh(progress)
        assert progress.current_node_id == node.id
        assert service.besito_service.get_balance(sample_user.id) == 90


@pytest.mark.unit
class TestStoryServiceStats:
    def test_get_story_stats(self, db_session, sample_user):
        service = StoryService(db_session)
        service.get_or_create_progress(sample_user.id)
        stats = service.get_story_stats()
        assert "total_nodes" in stats
        assert "total_chapters" in stats
        assert "total_users" in stats
        assert "completed_users" in stats
        assert "archetype_distribution" in stats
        assert "total_achievements" in stats


@pytest.mark.unit
class TestStoryArchetypeImmutability:
    """
    DESIRED CONTRACT (Item 4 / F3 narrative): arquetipo se asigna una sola vez y no cambia (once-only on ending or quiz/assign; never overwritten on re-advance/assign).
    + assign_archetype_to_user idempotent no override.
    Copia setups de TestStoryServiceArchetype / Branching (node, progress, balance TG explícito, advance, refresh, assert) pero con fresh TG + DESIRED comment (evitar sample_user.id skew en balance.user_id per Fase4 ID contract).
    """

    def test_archetype_assigned_once_on_ending_never_overwritten(self, db_session, sample_user):
        service = StoryService(db_session)
        tg = 77720001
        from models.models import BesitoBalance

        bal = BesitoBalance(user_id=tg, balance=100, total_earned=100, total_spent=0)
        db_session.add(bal)
        db_session.commit()
        progress = service.get_or_create_progress(tg)
        progress.archetype = ArchetypeType.EXPLORADOR
        db_session.commit()
        node2 = service.create_node("End2", "content", NodeType.ENDING, chapter=1)
        success, msg, prog = service.advance_to_node(tg, node2.id)
        assert success
        db_session.refresh(prog)
        assert prog.archetype == ArchetypeType.EXPLORADOR  # never overwritten

    def test_assign_archetype_idempotent_no_override(self, db_session, sample_user):
        service = StoryService(db_session)
        tg = 77720002
        from models.models import BesitoBalance

        bal = BesitoBalance(user_id=tg, balance=100, total_earned=100, total_spent=0)
        db_session.add(bal)
        db_session.commit()
        progress = service.get_or_create_progress(tg)
        progress.archetype = ArchetypeType.MISTERIOSO
        db_session.commit()
        # re "assign" via advance to another ending (the once-only guard in advance/calc should not overwrite)
        node3 = service.create_node("End3", "content", NodeType.ENDING, chapter=1)
        service.advance_to_node(tg, node3.id)
        db_session.refresh(progress)
        assert progress.archetype == ArchetypeType.MISTERIOSO  # no override (idempotent/once-only)


@pytest.mark.unit
class TestStoryInvalidTransitions:
    """
    DESIRED CONTRACT (Item 4 / F3): rama inválida no rompe flujo, retorna anterior/graceful (bad choice_id -> success False or prog unchanged, no points added, visited not polluted).
    Trans inválidas (cost high or required_vip) rechazadas no partial (False + msg contains besitos or VIP or Lucien voice, no debit, no progress update).
    """

    def test_invalid_branch_choice_graceful_no_corrupt_progress(self, db_session, sample_user):
        service = StoryService(db_session)
        tg = 77720003
        from models.models import BesitoBalance

        bal = BesitoBalance(user_id=tg, balance=100, total_earned=100, total_spent=0)
        db_session.add(bal)
        db_session.commit()
        node = service.create_node("Dec", "choose", NodeType.DECISION, chapter=1)
        service.advance_to_node(tg, node.id)
        progress_before = service.get_user_progress(tg)
        visited_before = progress_before.visited_nodes
        current_before = progress_before.current_node_id

        bad_choice = 999999
        success, msg, prog = service.advance_to_node(tg, node.id, choice_id=bad_choice)
        assert success is False
        assert msg is not None

        progress_after = service.get_user_progress(tg)
        assert progress_after.current_node_id == current_before
        assert progress_after.visited_nodes == visited_before
        assert service.besito_service.get_balance(tg) == 100

    def test_invalid_transition_cost_or_vip_rejected_no_partial(self, db_session, sample_user):
        service = StoryService(db_session)
        tg = 77720004
        from models.models import BesitoBalance

        bal = BesitoBalance(user_id=tg, balance=5, total_earned=5, total_spent=0)
        db_session.add(bal)
        db_session.commit()
        node = service.create_node(
            "CostlyVIP",
            "needs 100 or VIP",
            NodeType.NARRATIVE,
            chapter=1,
            cost_besitos=100,
            required_vip=True,
        )
        success, msg, prog = service.advance_to_node(tg, node.id)
        assert success is False
        assert msg is not None
        msg_lower = str(msg).lower()
        assert "besito" in msg_lower or "diván" in msg_lower or "divan" in msg_lower
        assert prog is None or prog.current_node_id != node.id
        assert service.besito_service.get_balance(tg) == 5  # no debit/partial


@pytest.mark.unit
class TestStoryFSMEventBus:
    """
    DESIRED CONTRACT (Item 4 / F3): FSM state restores after simulated restart (make_fsm_context MemoryStorage sim; real progress persists in DB independent via advance_to_node, tested in atomic).
    EventBus listener on_besitos_awarded receives best effort (patch schedule_emit; assert called/logged; no mutation to besitos per contract; use get_service(StoryService) wiring if).
    """

    async def test_story_fsm_state_restores_after_simulated_restart(self, make_fsm_context):
        from handlers.story_user_handlers import ArchetypeQuizStates

        tg = 77720005
        ctx1 = await make_fsm_context(user_id=tg)
        await ctx1.set_state(ArchetypeQuizStates.answering)
        await ctx1.update_data({"quiz_answers": [1, 3, 2], "current_question": 3})
        ctx2 = await make_fsm_context(user_id=tg)
        state = await ctx2.get_state()
        data = await ctx2.get_data()
        assert state == ArchetypeQuizStates.answering.state
        assert data.get("quiz_answers") == [1, 3, 2]
        assert data.get("current_question") == 3
        # note: Memory sim; real durable contract is DB progress via advance (atomic tested separately)

    @pytest.mark.asyncio
    async def test_on_besitos_awarded_listener_does_not_mutate_besitos(
        self, db_session, sample_user
    ):
        """El listener narrativo MUST NOT credit/debit besitos."""
        from services.event_bus import EVENT_BESITOS_AWARDED, InternalEventBus
        from services.story_service import on_besitos_awarded_from_gamification

        tg = 77720006
        from models.models import BesitoBalance

        bal = BesitoBalance(user_id=tg, balance=10, total_earned=10, total_spent=0)
        db_session.add(bal)
        db_session.commit()

        bus = InternalEventBus()
        bus.register(EVENT_BESITOS_AWARDED, on_besitos_awarded_from_gamification)

        service = StoryService(db_session)
        balance_before = service.besito_service.get_balance(tg)

        with patch("services.besito_service.BesitoService.credit_besitos") as credit_mock, patch(
            "services.besito_service.BesitoService.debit_besitos"
        ) as debit_mock:
            payload = {
                "user_id": tg,
                "amount": 5,
                "source": "mission",
                "reference_id": 1,
            }
            await bus.emit(EVENT_BESITOS_AWARDED, payload)

        credit_mock.assert_not_called()
        debit_mock.assert_not_called()
        assert service.besito_service.get_balance(tg) == balance_before


@pytest.mark.unit
class TestArchetypeQuizPhase6:
    """Tests para el cuestionario de arquetipos (hardcodeado en StoryService - Fase 6 narrativa)."""

    def test_calculate_archetype_from_quiz_seductor_dominant(self):
        """Respuestas seductor-heavy dan SEDUCTOR (UAT fase 6: historias con arquetipos)."""
        # No db needed; quiz is pure
        service = StoryService(db=None)
        # All first options heavily weight seductor
        answers = [0, 0, 0]
        result = service.calculate_archetype_from_quiz(answers)
        assert result == ArchetypeType.SEDUCTOR

    def test_calculate_archetype_from_quiz_observer_dominant(self):
        """Opciones observer dan OBSERVER."""
        service = StoryService(db=None)
        # Second option on Q1 (observer), Q2 observer, Q3 observer
        answers = [1, 1, 1]
        result = service.calculate_archetype_from_quiz(answers)
        assert result == ArchetypeType.OBSERVER

    def test_calculate_archetype_from_quiz_invalid_answers_fallback_to_max(self):
        """Indices fuera de rango no rompen; usa max disponible."""
        service = StoryService(db=None)
        # Too many answers, bad indices
        answers = [99, 99, 99, 0]
        result = service.calculate_archetype_from_quiz(answers)
        # Should still return a valid ArchetypeType (the one with highest from partial)
        assert isinstance(result, ArchetypeType)


@pytest.mark.unit
class TestStoryAccessGatesPhase6:
    """Tests de can_access_node gates (VIP, arquetipo, costo) - UAT fase 6 narrativa."""

    def test_can_access_node_vip_required_denies_non_vip(self, db_session, sample_user):
        node = StoryNode(
            title="VIP Only",
            content="...",
            node_type=NodeType.NARRATIVE,
            required_vip=True,
            is_active=True,
        )
        db_session.add(node)
        db_session.commit()

        service = StoryService(db_session)
        can, reason = service.can_access_node(sample_user.id, node.id, is_vip=False)
        assert can is False
        assert (
            "diván" in (reason or "").lower()
            or "requiere acceso" in (reason or "").lower()
            or "el diván" in (reason or "").lower()
        )

    def test_can_access_node_archetype_required_denies_mismatch(self, db_session, sample_user):
        node = StoryNode(
            title="Devoto Only",
            content="...",
            node_type=NodeType.NARRATIVE,
            required_archetype=ArchetypeType.DEVOTO,
            is_active=True,
        )
        db_session.add(node)
        db_session.commit()
        # Progress without the archetype
        progress = UserStoryProgress(user_id=sample_user.id, current_node_id=1)
        db_session.add(progress)
        db_session.commit()

        service = StoryService(db_session)
        can, reason = service.can_access_node(sample_user.id, node.id, is_vip=False)
        assert can is False
        assert "arquetipo" in (reason or "").lower() or "archetype" in (reason or "").lower()

    def test_can_access_node_story_unlock_bypasses_vip_gate(self, db_session, sample_user):
        from models.models import (
            DeliveryMode,
            FulfillmentKind,
            FulfillmentStatus,
            Order,
            OrderFulfillment,
            OrderItem,
            OrderStatus,
            Package,
            StoreProduct,
        )

        node = StoryNode(
            title="Purchased VIP Node",
            content="...",
            node_type=NodeType.NARRATIVE,
            required_vip=True,
            is_active=True,
        )
        db_session.add(node)
        db_session.commit()
        pkg = Package(name="story pkg", is_active=True)
        db_session.add(pkg)
        db_session.commit()
        product = StoreProduct(
            name="Unlock",
            price=10,
            stock=-1,
            package_id=pkg.id,
            delivery_mode=DeliveryMode.AUTO,
            fulfillment_kind=FulfillmentKind.STORY_UNLOCK,
            story_node_id=node.id,
            is_active=True,
        )
        db_session.add(product)
        db_session.commit()
        order = Order(
            user_id=sample_user.id,
            total_items=1,
            total_price=10,
            status=OrderStatus.COMPLETED,
        )
        db_session.add(order)
        db_session.flush()
        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=1,
            unit_price=10,
            total_price=10,
        )
        db_session.add(item)
        db_session.flush()
        row = OrderFulfillment(
            order_item_id=item.id,
            user_id=sample_user.id,
            product_id=product.id,
            fulfillment_kind=FulfillmentKind.STORY_UNLOCK,
            status=FulfillmentStatus.FULFILLED,
            auto_result=f'{{"node_id": {node.id}}}',
        )
        db_session.add(row)
        db_session.commit()

        service = StoryService(db_session)
        can, reason = service.can_access_node(sample_user.id, node.id, is_vip=False)
        assert can is True
        assert reason is None

    def test_can_access_node_cost_besitos_insufficient_denies(self, db_session, sample_user):
        node = StoryNode(
            title="Paid Fragment",
            content="...",
            node_type=NodeType.NARRATIVE,
            cost_besitos=50,
            is_active=True,
        )
        db_session.add(node)
        db_session.commit()
        # Low balance
        from models.models import BesitoBalance

        bal = BesitoBalance(user_id=sample_user.id, balance=10, total_earned=10, total_spent=0)
        db_session.add(bal)
        db_session.commit()

        service = StoryService(db_session)
        can, reason = service.can_access_node(sample_user.id, node.id, is_vip=False)
        assert can is False
        assert (
            "besito" in (reason or "").lower()
            or "costo" in (reason or "").lower()
            or "50" in (reason or "")
        )


# GOLD PILOT Fase6 NARR #4 (extend existing): advance + archetype contract
# DESIRED CONTRACT: advance_to_node debits with commit=False (atomic with progress), archetype calc from points, achievements.
# Uses db_session + explicit .telegram_id (TG BigInt) + cost>0 + choice_id for archetype. Full SQLite+TestSession + saved_tg verbatim gold is used in pilots with internal besito commits (store atomic, cross); here commit=False + unit scope makes db_session + explicit sufficient and lower risk. See store gold for verbatim file+TS example.
# Pre-existing legacy (sys.path, some .id) untouched.
@pytest.mark.unit
class TestStoryNarrativeGoldFase6:
    """Pilots contrato deseado narrativa (Fase 6)."""

    def test_advance_and_archetype_contract_gold(self, db_session, sample_user):
        """DESIRED CONTRACT: advance persists debit+progress atomic; calc archetype from choices points. Cost>0 + choice_id exercised; strict TG ID and re-query."""
        from models.models import BesitoBalance

        node1 = StoryNode(
            title="Start",
            content="..",
            node_type=NodeType.NARRATIVE,
            is_starting_node=True,
            is_active=True,
            cost_besitos=10,  # >0 to exercise debit path in gold pilot
        )
        db_session.add(node1)
        db_session.commit()
        db_session.refresh(node1)

        choice = StoryChoice(
            node_id=node1.id,
            text="Go Devoto",
            choice_archetype=ArchetypeType.DEVOTO,
            archetype_points=5,
        )
        db_session.add(choice)
        db_session.commit()

        bal = BesitoBalance(
            user_id=sample_user.telegram_id, balance=100, total_earned=100, total_spent=0
        )
        db_session.add(bal)
        db_session.commit()

        service = StoryService(db_session)
        service.advance_to_node(sample_user.telegram_id, node1.id)
        result = service.advance_to_node(sample_user.telegram_id, node1.id, choice_id=choice.id)
        assert result and result[0] is True, "advance returns (True, msg, progress) per contract"

        progress = service.get_user_progress(sample_user.telegram_id)
        assert progress is not None
        assert progress.current_node_id == node1.id

        # archetype calc (exact per dominant points from choice)
        arch = service.calculate_archetype(progress)
        assert arch == ArchetypeType.DEVOTO

        # re-query strict post
        re_prog = (
            db_session.query(UserStoryProgress).filter_by(user_id=sample_user.telegram_id).first()
        )
        assert re_prog is not None
        assert re_prog.current_node_id == node1.id  # strict contract verification

        # debit side-effect assert (cost=10 exercised)
        re_bal = db_session.query(BesitoBalance).filter_by(user_id=sample_user.telegram_id).first()
        assert re_bal.balance == 90
        assert re_bal.total_spent == 10


@pytest.mark.unit
class TestStoryAchievementAtomicity:
    """Achievement + besitos reward must commit atomically via single credit_besitos commit."""

    def test_grant_achievement_with_besitos_atomic(self, db_session, sample_user):
        from models.models import BesitoBalance, StoryAchievement, UserStoryAchievement

        balance = BesitoBalance(
            user_id=sample_user.telegram_id,
            balance=100,
            total_earned=100,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()

        achievement = StoryAchievement(
            name="Primer Fragmento",
            description="Desbloquea el inicio",
            reward_besitos=25,
            is_active=True,
        )
        db_session.add(achievement)
        db_session.commit()
        db_session.refresh(achievement)

        service = StoryService(db_session)
        service._grant_achievement(sample_user.telegram_id, achievement)

        user_ach = (
            db_session.query(UserStoryAchievement)
            .filter_by(user_id=sample_user.telegram_id, achievement_id=achievement.id)
            .first()
        )
        assert user_ach is not None
        assert user_ach.reward_delivered is True
        assert user_ach.reward_delivered_at is not None

        re_bal = db_session.query(BesitoBalance).filter_by(user_id=sample_user.telegram_id).first()
        assert re_bal.balance == 125
        assert re_bal.total_earned == 125

        from models.models import BesitoTransaction

        tx = (
            db_session.query(BesitoTransaction)
            .filter_by(user_id=sample_user.telegram_id, source=TransactionSource.MISSION)
            .first()
        )
        assert tx is not None
        assert tx.amount == 25
        assert tx.reference_id == achievement.id

    def test_grant_achievement_credit_failure_rolls_back(self, db_session, sample_user):
        from models.models import BesitoBalance, StoryAchievement, UserStoryAchievement

        balance = BesitoBalance(
            user_id=sample_user.telegram_id,
            balance=100,
            total_earned=100,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()

        achievement = StoryAchievement(
            name="Fallo Credito",
            description="Test rollback",
            reward_besitos=25,
            is_active=True,
        )
        db_session.add(achievement)
        db_session.commit()
        db_session.refresh(achievement)

        saved_tg = sample_user.telegram_id
        saved_ach_id = achievement.id
        service = StoryService(db_session)
        with patch.object(service.besito_service, "credit_besitos", return_value=False):
            service._grant_achievement(saved_tg, achievement)

        assert (
            db_session.query(UserStoryAchievement)
            .filter_by(user_id=saved_tg, achievement_id=saved_ach_id)
            .count()
            == 0
        )
        re_bal = db_session.query(BesitoBalance).filter_by(user_id=saved_tg).first()
        assert re_bal.balance == 100

    def test_grant_achievement_without_besitos_commits_only_achievement(
        self, db_session, sample_user
    ):
        from models.models import (
            BesitoBalance,
            BesitoTransaction,
            StoryAchievement,
            UserStoryAchievement,
        )

        balance = BesitoBalance(
            user_id=sample_user.telegram_id,
            balance=100,
            total_earned=100,
            total_spent=0,
        )
        db_session.add(balance)
        db_session.commit()

        achievement = StoryAchievement(
            name="Sin Recompensa",
            description="Solo logro",
            reward_besitos=0,
            is_active=True,
        )
        db_session.add(achievement)
        db_session.commit()
        db_session.refresh(achievement)

        service = StoryService(db_session)
        service._grant_achievement(sample_user.telegram_id, achievement)

        user_ach = (
            db_session.query(UserStoryAchievement)
            .filter_by(user_id=sample_user.telegram_id, achievement_id=achievement.id)
            .first()
        )
        assert user_ach is not None
        assert user_ach.reward_delivered is False
        assert user_ach.reward_delivered_at is None

        re_bal = db_session.query(BesitoBalance).filter_by(user_id=sample_user.telegram_id).first()
        assert re_bal.balance == 100
        assert re_bal.total_earned == 100
        assert db_session.query(BesitoTransaction).filter_by(user_id=sample_user.telegram_id).count() == 0


@pytest.mark.unit
class TestAdvanceToNodeDebitFailure:
    """Rollback cuando debit_besitos retorna False tras checks de acceso."""

    def test_debit_failure_rolls_back_progress(self, db_session, sample_user):
        from models.models import BesitoBalance, UserStoryProgress

        tg = 77730001
        node = StoryNode(
            title="Paid",
            content="content",
            node_type=NodeType.NARRATIVE,
            cost_besitos=50,
            chapter=1,
            is_active=True,
        )
        db_session.add(node)
        balance = BesitoBalance(user_id=tg, balance=100, total_earned=100, total_spent=0)
        db_session.add(balance)
        db_session.commit()
        db_session.refresh(node)

        service = StoryService(db_session)
        with patch.object(service.besito_service, "debit_besitos", return_value=False):
            success, msg, prog = service.advance_to_node(tg, node.id)

        assert success is False
        assert prog is None
        assert service.besito_service.get_balance(tg) == 100
        assert (
            db_session.query(UserStoryProgress).filter(UserStoryProgress.user_id == tg).count()
            == 0
        )


@pytest.mark.unit
class TestAdditionalCostDebit:
    """additional_cost en elecciones se debita junto al costo del nodo."""

    def test_choice_additional_cost_debited_atomically(self, db_session, sample_user):
        from models.models import BesitoBalance, StoryChoice

        node_a = StoryNode(
            title="A",
            content="a",
            node_type=NodeType.DECISION,
            cost_besitos=10,
            chapter=1,
            is_active=True,
        )
        node_b = StoryNode(
            title="B",
            content="b",
            node_type=NodeType.NARRATIVE,
            cost_besitos=0,
            chapter=1,
            is_active=True,
        )
        db_session.add_all([node_a, node_b])
        db_session.commit()

        choice = StoryChoice(
            node_id=node_a.id,
            text="Go B",
            next_node_id=node_b.id,
            additional_cost=15,
        )
        db_session.add(choice)
        balance = BesitoBalance(
            user_id=sample_user.id, balance=100, total_earned=100, total_spent=0
        )
        db_session.add(balance)
        db_session.commit()

        service = StoryService(db_session)
        service.advance_to_node(sample_user.id, node_a.id)
        success, _, _ = service.advance_to_node(
            sample_user.id, node_b.id, choice_id=choice.id
        )

        assert success is True
        assert service.besito_service.get_balance(sample_user.id) == 75

    def test_convergent_path_additional_cost_on_revisit(self, db_session, sample_user):
        """additional_cost se cobra aunque el destino ya fue visitado."""
        from models.models import BesitoBalance, StoryChoice

        node_a = StoryNode(
            title="Fork",
            content="a",
            node_type=NodeType.DECISION,
            cost_besitos=0,
            chapter=1,
            is_active=True,
        )
        node_b = StoryNode(
            title="Hub",
            content="b",
            node_type=NodeType.NARRATIVE,
            cost_besitos=20,
            chapter=1,
            is_active=True,
        )
        db_session.add_all([node_a, node_b])
        db_session.commit()

        cheap = StoryChoice(
            node_id=node_a.id, text="Free route", next_node_id=node_b.id, additional_cost=0
        )
        premium = StoryChoice(
            node_id=node_a.id, text="Premium", next_node_id=node_b.id, additional_cost=25
        )
        db_session.add_all([cheap, premium])
        balance = BesitoBalance(
            user_id=sample_user.id, balance=100, total_earned=100, total_spent=0
        )
        db_session.add(balance)
        db_session.commit()

        service = StoryService(db_session)
        service.advance_to_node(sample_user.id, node_a.id)
        service.advance_to_node(sample_user.id, node_b.id, choice_id=cheap.id)
        assert service.besito_service.get_balance(sample_user.id) == 80

        service.advance_to_node(sample_user.id, node_a.id)
        success, _, _ = service.advance_to_node(
            sample_user.id, node_b.id, choice_id=premium.id
        )
        assert success is True
        assert service.besito_service.get_balance(sample_user.id) == 55


@pytest.mark.unit
class TestValidateContinueTransition:
    """validate_continue_transition bloquea saltos arbitrarios."""

    def test_rejects_non_successor_node(self, db_session, sample_user):
        service = StoryService(db_session)
        node_a = service.create_node("A", "a", chapter=1, order_in_chapter=0)
        node_b = service.create_node("B", "b", chapter=1, order_in_chapter=1)
        node_c = service.create_node("C", "c", chapter=1, order_in_chapter=2)

        from models.models import BesitoBalance

        db_session.add(
            BesitoBalance(user_id=sample_user.id, balance=50, total_earned=50, total_spent=0)
        )
        db_session.commit()

        service.advance_to_node(sample_user.id, node_a.id)

        valid, reason = service.validate_continue_transition(sample_user.id, node_c.id)
        assert valid is False
        assert reason is not None


@pytest.mark.unit
class TestChoiceIdor:
    """_validate_choice_transition bloquea choice de otro nodo."""

    def test_choice_from_wrong_node_rejected(self, db_session, sample_user):
        from models.models import BesitoBalance, StoryChoice

        service = StoryService(db_session)
        node_a = service.create_node("A", "a", NodeType.DECISION, chapter=1)
        node_b = service.create_node("B", "b", NodeType.DECISION, chapter=1)
        choice_on_b = StoryChoice(
            node_id=node_b.id, text="On B", next_node_id=node_b.id, additional_cost=0
        )
        db_session.add(choice_on_b)
        db_session.add(
            BesitoBalance(user_id=sample_user.id, balance=100, total_earned=100, total_spent=0)
        )
        db_session.commit()

        service.advance_to_node(sample_user.id, node_a.id)
        progress_before = service.get_user_progress(sample_user.id)

        success, msg, prog = service.advance_to_node(
            sample_user.id, node_b.id, choice_id=choice_on_b.id
        )
        assert success is False
        assert prog is None

        progress_after = service.get_user_progress(sample_user.id)
        assert progress_after.current_node_id == progress_before.current_node_id

    def test_terminal_choice_wrong_target_rejected(self, db_session, sample_user):
        from models.models import BesitoBalance, StoryChoice

        service = StoryService(db_session)
        node_a = service.create_node("A", "a", NodeType.DECISION, chapter=1)
        node_b = service.create_node("B", "b", NodeType.NARRATIVE, chapter=1)
        terminal = StoryChoice(node_id=node_a.id, text="End", next_node_id=None)
        db_session.add(terminal)
        db_session.add(
            BesitoBalance(user_id=sample_user.id, balance=100, total_earned=100, total_spent=0)
        )
        db_session.commit()

        service.advance_to_node(sample_user.id, node_a.id)
        success, _, _ = service.advance_to_node(
            sample_user.id, node_b.id, choice_id=terminal.id
        )
        assert success is False


@pytest.mark.unit
class TestCanAccessVisitedNode:
    """Nodos visitados no requieren balance para re-display."""

    def test_visited_node_accessible_with_zero_balance(self, db_session, sample_user):
        from models.models import BesitoBalance

        node = StoryNode(
            title="Paid",
            content="c",
            node_type=NodeType.NARRATIVE,
            cost_besitos=50,
            chapter=1,
            is_active=True,
        )
        db_session.add(node)
        balance = BesitoBalance(
            user_id=sample_user.id, balance=100, total_earned=100, total_spent=0
        )
        db_session.add(balance)
        db_session.commit()

        service = StoryService(db_session)
        service.advance_to_node(sample_user.id, node.id)
        balance.balance = 0
        db_session.commit()

        can, reason = service.can_access_node(sample_user.id, node.id)
        assert can is True
        assert reason is None


@pytest.mark.unit
class TestDeleteNodeWithProgress:
    """delete_node reasigna progreso antes de eliminar."""

    def test_delete_reassigns_current_node(self, db_session, sample_user):
        service = StoryService(db_session)
        start = service.create_node(
            "Start", "s", is_starting_node=True, chapter=1, order_in_chapter=0
        )
        doomed = service.create_node("Doomed", "d", chapter=1, order_in_chapter=1)

        from models.models import BesitoBalance

        db_session.add(
            BesitoBalance(user_id=sample_user.id, balance=10, total_earned=10, total_spent=0)
        )
        db_session.commit()

        service.advance_to_node(sample_user.id, doomed.id)
        assert service.delete_node(doomed.id) is True

        progress = service.get_user_progress(sample_user.id)
        assert progress.current_node_id == start.id


@pytest.mark.unit
class TestCheckAchievements:
    """_check_achievements desbloquea con semantica AND."""

    def test_achievement_unlocks_on_required_node(self, db_session, sample_user):
        from models.models import BesitoBalance, StoryAchievement, UserStoryAchievement

        node = StoryNode(
            title="Unlock",
            content="c",
            node_type=NodeType.NARRATIVE,
            chapter=1,
            is_active=True,
        )
        db_session.add(node)
        db_session.commit()
        db_session.refresh(node)

        achievement = StoryAchievement(
            name="Paso Uno",
            description="Visita nodo",
            required_node_id=node.id,
            is_active=True,
        )
        db_session.add(achievement)
        db_session.commit()

        balance = BesitoBalance(
            user_id=sample_user.id, balance=0, total_earned=0, total_spent=0
        )
        db_session.add(balance)
        db_session.commit()

        service = StoryService(db_session)
        service.advance_to_node(sample_user.id, node.id)

        unlocked = (
            db_session.query(UserStoryAchievement)
            .filter_by(user_id=sample_user.id, achievement_id=achievement.id)
            .count()
        )
        assert unlocked == 1

    def test_compound_requirements_need_all_conditions(self, db_session, sample_user):
        from models.models import BesitoBalance, StoryAchievement, UserStoryAchievement

        node = StoryNode(
            title="N",
            content="c",
            node_type=NodeType.NARRATIVE,
            chapter=2,
            is_active=True,
        )
        db_session.add(node)
        db_session.commit()
        db_session.refresh(node)

        achievement = StoryAchievement(
            name="Combo",
            description="Nodo + arquetipo",
            required_node_id=node.id,
            required_archetype=ArchetypeType.DEVOTO,
            is_active=True,
        )
        db_session.add(achievement)
        balance = BesitoBalance(
            user_id=sample_user.id, balance=0, total_earned=0, total_spent=0
        )
        db_session.add(balance)
        db_session.commit()

        service = StoryService(db_session)
        progress = service.create_user_progress(sample_user.id)
        progress.archetype = ArchetypeType.DEVOTO
        db_session.commit()

        service.advance_to_node(sample_user.id, node.id)

        count = (
            db_session.query(UserStoryAchievement)
            .filter_by(user_id=sample_user.id, achievement_id=achievement.id)
            .count()
        )
        assert count == 1


@pytest.mark.unit
class TestConcurrentProgressUnique:
    """UniqueConstraint en user_id evita filas duplicadas de progreso."""

    def test_create_user_progress_rejects_duplicate_user_id(self, db_session, sample_user):
        service = StoryService(db_session)
        service.create_user_progress(sample_user.id)
        with pytest.raises(IntegrityError):
            service.create_user_progress(sample_user.id)

    def test_advance_to_node_retries_after_concurrent_first_insert(
        self, db_session, sample_user
    ):
        """Simula carrera: retry tras IntegrityError encuentra progreso del ganador."""
        from models.models import BesitoBalance

        node = StoryNode(
            title="Start",
            content="content",
            node_type=NodeType.NARRATIVE,
            cost_besitos=5,
            chapter=1,
            is_active=True,
        )
        db_session.add(node)
        db_session.add(
            BesitoBalance(
                user_id=sample_user.id, balance=100, total_earned=100, total_spent=0
            )
        )
        db_session.commit()
        db_session.refresh(node)

        service = StoryService(db_session)
        winner_progress = service.create_user_progress(sample_user.id, commit=True)

        with (
            patch.object(
                service,
                "_lock_user_progress",
                side_effect=[None, winner_progress],
            ),
            patch.object(
                service,
                "create_user_progress",
                side_effect=IntegrityError("stmt", {}, Exception("duplicate")),
            ),
        ):
            success, _, progress = service.advance_to_node(sample_user.id, node.id)

        assert success is True
        assert progress is not None
        assert progress.current_node_id == node.id
        assert (
            db_session.query(UserStoryProgress)
            .filter(UserStoryProgress.user_id == sample_user.id)
            .count()
            == 1
        )
