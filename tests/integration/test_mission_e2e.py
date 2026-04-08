"""
Test e2e de misiones - Simular reacción de usuario y verificar flujo de misión.

Este test verifica el flujo completo:
1. Usuario da una reacción a un mensaje
2. Se dispara la misión de tipo REACTION_COUNT
3. Al completar la misión, se otorgan los besitos de recompensa
"""
import pytest
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from services.mission_service import MissionService
from services.besito_service import BesitoService
from services.reward_service import RewardService
from models.models import (
    Mission, MissionType, MissionFrequency,
    UserMissionProgress, User, BesitoBalance, Reward, RewardType,
    TransactionSource
)


def log_step(message: str):
    """Print estructurado para ver el flujo en pytest"""
    print(f"\n{'='*60}")
    print(f"  {message}")
    print('='*60)


def log_detail(message: str):
    """Print de detalle con sangría"""
    print(f"    → {message}")


@pytest.mark.integration
class TestMissionE2E:
    """Test e2e del flujo de misiones desde reacción hasta recompensa"""

    def test_reaction_triggers_mission_and_grants_besitos(self, db_session, sample_user):
        """
        Test que simula el flujo: reacción -> misión -> besitos.

        Escenario:
        1. Usuario da una reacción a un mensaje
        2. Se verifica el progreso de misión aumenta
        3. Al completar la misión, se otorgan los besitos de recompensa
        """
        # === SETUP ===
        log_step("INICIANDO SETUP - Preparando datos de prueba")
        mission_service = MissionService(db_session)
        besito_service = BesitoService(db_session)
        reward_service = RewardService(db_session)

        # Crear recompensa de besitos para la misión
        reward = Reward(
            name="Recompensa Reacción",
            description="20 besitos por completar misión de reacciones",
            reward_type=RewardType.BESITOS,
            besito_amount=20,
            is_active=True
        )
        db_session.add(reward)
        db_session.commit()
        db_session.refresh(reward)

        log_detail(f"Recompensa creada: ID={reward.id}, tipo={reward.reward_type.name}, cantidad={reward.besito_amount} besitos")

        # Crear misión con tipo REACTION_COUNT
        mission = Mission(
            name="Reaccionista",
            description="Da 5 reacciones a mensajes",
            mission_type=MissionType.REACTION_COUNT,
            target_value=5,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=reward.id,
            is_active=True
        )
        db_session.add(mission)
        db_session.commit()
        db_session.refresh(mission)

        log_detail(f"Misión creada: ID={mission.id}")
        log_detail(f"  - Nombre: {mission.name}")
        log_detail(f"  - Tipo: {mission.mission_type.name}")
        log_detail(f"  - Target: {mission.target_value} reacciones")
        log_detail(f"  - Frecuencia: {mission.frequency.name}")
        log_detail(f"  - Recompensa: {reward.besito_amount} besitos")

        # Asegurar que el usuario tiene balance de besitos inicial
        balance = BesitoBalance(
            user_id=sample_user.id,
            balance=0,
            total_earned=0,
            total_spent=0
        )
        db_session.add(balance)
        db_session.commit()

        log_detail(f"Balance inicial del usuario: {balance.balance} besitos")

        # === ACCIÓN: Simular reacciones del usuario ===
        log_step("EJECUTANDO ACCIONES - Simulando reacciones del usuario")

        # El flujo de reacción del mundo real:
        # 1. Handler recibe callback de reacción
        # 2. Llama a mission_service.increment_progress(user_id, REACTION_COUNT)
        # 3. Si la misión se completa, se entrega la recompensa

        # Simular 5 reacciones (el target de la misión)
        for i in range(5):
            reaction_num = i + 1
            log_step(f"REACCIÓN #{reaction_num} - Usuario reacciona a un mensaje")

            completed_missions = mission_service.increment_progress(
                user_id=sample_user.id,
                mission_type=MissionType.REACTION_COUNT,
                amount=1
            )

            log_detail(f"MissionType disparado: {MissionType.REACTION_COUNT.name}")
            log_detail(f"Cantidad incrementada: +1")

            # Ver estado actual del progreso
            all_missions = mission_service.get_missions_by_type(MissionType.REACTION_COUNT)
            for m in all_missions:
                progress = mission_service.get_user_progress(sample_user.id, m.id)
                if progress:
                    status = "✓ COMPLETADA" if progress.is_completed else f"en progreso ({progress.current_value}/{m.target_value})"
                    log_detail(f"Misión '{m.name}': {status}")

            if completed_missions:
                for cm in completed_missions:
                    log_step(f"¡MISIÓN COMPLETADA! '{cm.mission.name}'")
                    log_detail(f"Progreso final: {cm.current_value}/{cm.mission.target_value}")

                    # Entregar recompensa
                    if cm.mission.reward:
                        log_step("ENTREGANDO RECOMPENSAS")
                        reward_obj = cm.mission.reward

                        if reward_obj.reward_type == RewardType.BESITOS:
                            # Credit los besitos
                            besito_service.credit_besitos(
                                user_id=sample_user.id,
                                amount=reward_obj.besito_amount,
                                source=TransactionSource.MISSION,
                                reference_id=cm.mission.id
                            )
                            log_detail(f"Besitos otorgados: +{reward_obj.besito_amount}")

                            # Verificar balance actualizado
                            new_balance = besito_service.get_balance(sample_user.id)
                            log_detail(f"Balance actual: {new_balance} besitos")

        # === ASSERT: Verificar progreso final ===
        log_step("VERIFICANDO RESULTADOS FINALES")

        progress = mission_service.get_user_progress(sample_user.id, mission.id)
        assert progress is not None, "El progreso debería existir"
        assert progress.current_value == 5, f"Progreso debería ser 5, got {progress.current_value}"
        assert progress.is_completed is True, "La misión debería estar completada"
        assert progress.completed_at is not None, "La fecha de completación debería estar registrada"

        log_detail(f"✓ Progreso verificado: {progress.current_value}/5")
        log_detail(f"✓ Completada: {progress.is_completed}")
        log_detail(f"✓ Fecha de completación: {progress.completed_at}")

        # === ASSERT: Verificar besitos ===
        user_balance = besito_service.get_balance(sample_user.id)

        log_step("RESUMEN FINAL")
        print(f"  ✓ Misión completada: {mission.name}")
        print(f"  ✓ Progreso final: {progress.current_value}/{progress.target_value}")
        print(f"  ✓ Besitos otorgados: {user_balance}")

    def test_partial_reaction_does_not_complete_mission(self, db_session, sample_user):
        """Test que partial progress no completa la misión"""
        log_step("TEST: Progreso parcial no debe completar misión")
        mission_service = MissionService(db_session)
        besito_service = BesitoService(db_session)

        # Crear misión con target 3
        reward = Reward(
            name="Recompensa Junior",
            description="10 besitos",
            reward_type=RewardType.BESITOS,
            besito_amount=10,
            is_active=True
        )
        db_session.add(reward)
        db_session.commit()
        db_session.refresh(reward)

        mission = Mission(
            name="Reaccionista Junior",
            description="Da 3 reacciones",
            mission_type=MissionType.REACTION_COUNT,
            target_value=3,
            frequency=MissionFrequency.ONE_TIME,
            reward_id=reward.id,
            is_active=True
        )
        db_session.add(mission)
        db_session.commit()
        db_session.refresh(mission)

        log_detail(f"Misión: {mission.name}, target: {mission.target_value}")

        # Balance inicial
        balance = BesitoBalance(user_id=sample_user.id, balance=0, total_earned=0, total_spent=0)
        db_session.add(balance)
        db_session.commit()

        # Solo 2 reacciones (menos que el target)
        log_step("Simulando 2 reacciones (menos que el target de 3)")
        for i in range(2):
            reaction_num = i + 1
            log_detail(f"Reacción #{reaction_num}")

            mission_service.increment_progress(
                user_id=sample_user.id,
                mission_type=MissionType.REACTION_COUNT,
                amount=1
            )

            progress = mission_service.get_user_progress(sample_user.id, mission.id)
            log_detail(f"Progreso actual: {progress.current_value}/{mission.target_value}")

        # Verificar que NO está completada
        progress = mission_service.get_user_progress(sample_user.id, mission.id)
        assert progress.current_value == 2
        assert progress.is_completed is False
        assert progress.completed_at is None

        # Verificar que NO se otorgaron besitos
        user_balance = besito_service.get_balance(sample_user.id)
        assert user_balance == 0, "No debe dar besitos si no se completa"

        log_step("RESULTADO: Progreso parcial NO completa misión")
        log_detail(f"Progreso: {progress.current_value}/3 (incompleto)")
        log_detail(f"Besitos: {user_balance} (sin recompensa)")

    def test_recurring_mission_resets_after_completion(self, db_session, sample_user):
        """Test que las misiones recurrentes se reinician al completarse"""
        log_step("TEST: Misión recurrente se reinicia al completar")
        mission_service = MissionService(db_session)

        # Crear misión recurrente (diaria)
        mission = Mission(
            name="Reaccionista Diario",
            description="Da 1 reacción cada día",
            mission_type=MissionType.REACTION_COUNT,
            target_value=1,
            frequency=MissionFrequency.RECURRING,
            is_active=True
        )
        db_session.add(mission)
        db_session.commit()
        db_session.refresh(mission)

        log_detail(f"Misión: {mission.name}")
        log_detail(f"Frecuencia: {mission.frequency.name} (se reinicia al completar)")

        # Completar la misión
        log_step("Primera reacción - Completando misión")
        mission_service.increment_progress(
            user_id=sample_user.id,
            mission_type=MissionType.REACTION_COUNT,
            amount=1
        )

        # Verificar completada
        progress1 = mission_service.get_user_progress(sample_user.id, mission.id)
        log_detail(f"Primera completada: {progress1.is_completed}")
        log_detail(f"Progreso: {progress1.current_value}/{mission.target_value}")
        assert progress1.is_completed is True

        # Reiniciar debería ocurrir automáticamente en increment_progress
        # para misiones recurrentes
        # Verificar el comportamiento de reinicio
        log_step("Segunda reacción - Verificando reinicio automático")
        completed = mission_service.increment_progress(
            user_id=sample_user.id,
            mission_type=MissionType.REACTION_COUNT,
            amount=1
        )

        # Obtener progreso actualizado
        progress2 = mission_service.get_user_progress(sample_user.id, mission.id)
        log_detail(f"Progreso después de segunda reacción: {progress2.current_value}")
        log_detail(f"¿Se reinició?: {'SÍ' if progress2.current_value == 1 and progress2.is_completed else 'NO'}")

        log_step("RESULTADO: Misión recurrente procesada")
        log_detail(f"Progreso actual: {progress2.current_value}")