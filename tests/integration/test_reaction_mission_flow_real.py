"""
Test E2E de Reacciones y Misiones - DATOS REALES DE PRODUCCIÓN

Este test se conecta a la base de datos REAL del proyecto para mostrar
el flujo completo con los datos actuales del sistema.

ADVERTENCIA: Este test modifica datos en la base de datos real.
Usa con precaución en entornos de producción.
"""
import pytest
import os
import sys

# Agregar el path del proyecto
sys.path.insert(0, '/data/data/com.termux/files/home/repos/lucien_bot')

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Usar la base de datos real del proyecto
from config.settings import bot_config
from models.models import (
    User, Mission, MissionType, MissionFrequency, Reward, RewardType,
    BroadcastMessage, BroadcastReaction, ReactionEmoji, BesitoBalance,
    BesitoTransaction, TransactionSource, Channel
)
from services.broadcast_service import BroadcastService
from services.mission_service import MissionService
from services.besito_service import BesitoService


# Crear engine con la URL real
print(f"\n🔌 Conectando a base de datos: {bot_config.DATABASE_URL[:50]}...")
real_engine = create_engine(
    bot_config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in bot_config.DATABASE_URL else {}
)
RealSession = sessionmaker(autocommit=False, autoflush=False, bind=real_engine)


@pytest.mark.integration
class TestReactionMissionFlowRealData:
    """Test E2E con datos reales de la base de datos"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup que usa la sesión real"""
        self.db = RealSession()
        yield
        self.db.close()

    def test_e2e_with_real_missions_from_production_db(self):
        """
        Test que extrae las misiones REALES de la base de datos
        y muestra el flujo completo paso a paso.
        """
        print("\n" + "="*70)
        print("🎯 TEST E2E: FLUJO REACCIÓN → MISIONES → BESITOS")
        print("   (DATOS REALES DE LA BASE DE DATOS)")
        print("="*70)

        mission_service = MissionService(self.db)
        broadcast_service = BroadcastService(self.db)
        besito_service = BesitoService(self.db)

        # ========================================
        # PASS 1: CONSULTAR MISIONES REALES
        # ========================================
        print("\n📋 PASS 1: CONSULTANDO MISIONES REALES DE LA BASE DE DATOS")
        print("-" * 50)

        all_missions = mission_service.get_available_missions()

        print(f"🎯 Total de misiones activas en el sistema: {len(all_missions)}")

        # Agrupar por tipo
        missions_by_type = {}
        for m in all_missions:
            t = m.mission_type.value if m.mission_type else 'unknown'
            if t not in missions_by_type:
                missions_by_type[t] = []
            missions_by_type[t].append(m)

        # Mostrar todas las misiones
        for mission_type, missions in missions_by_type.items():
            print(f"\n  📌 Tipo: {mission_type} ({len(missions)} misión(es))")
            for m in missions:
                # Obtener info de recompensa
                reward_info = ""
                if m.reward_id:
                    reward = self.db.query(Reward).filter(Reward.id == m.reward_id).first()
                    if reward:
                        if reward.reward_type == RewardType.BESITOS:
                            reward_info = f" → Recompensa: {reward.besito_amount} besitos"
                        elif reward.reward_type == RewardType.PACKAGE:
                            reward_info = f" → Recompensa: Paquete #{reward.package_id}"
                        elif reward.reward_type == RewardType.VIP_ACCESS_ACCESS:
                            reward_info = f" → Recompensa: VIP_ACCESS {reward.vip_days if hasattr(reward, 'vip_days') else '?'} días"

                print(f"     • {m.name}")
                print(f"       Meta: {m.target_value} | Frecuencia: {m.frequency.value if m.frequency else 'N/A'}{reward_info}")

        # Obtener misiones REACTION_COUNT específicamente
        # Extraer solo los IDs para evitar problemas de sesión
        mission_ids = [m.id for m in mission_service.get_missions_by_type(MissionType.REACTION_COUNT)]

        print(f"\n  🎯 Misiones de REACCIONES: {len(mission_ids)}")

        if not mission_ids:
            print("  ⚠️  ATENCIÓN: No hay misiones de tipo REACTION_COUNT configuradas")
            print("     Las reacciones otorgarán besitos pero NO dispararán misiones")

        # ========================================
        # PASS 2: CONSULTAR EMOJIS DE REACCIÓN
        # ========================================
        print("\n📋 PASS 2: EMOJIS DE REACCIÓN CONFIGURADOS")
        print("-" * 50)

        emojis = broadcast_service.get_all_emojis(active_only=True)
        print(f"  Emojis activos: {len(emojis)}")

        emoji_value_map = {}
        for e in emojis:
            print(f"    {e.emoji} → {e.besito_value} besitos (ID: {e.id})")
            emoji_value_map[e.emoji] = e

        # ========================================
        # PASS 3: PREPARAR ESCENARIO DE TEST
        # ========================================
        print("\n📋 PASS 3: PREPARANDO ESCENARIO DE TEST")
        print("-" * 50)

        # Usar un usuario de test (crear uno nuevo o usar existente)
        test_user_telegram_id = 999999999  # ID de test
        user = self.db.query(User).filter(User.telegram_id == test_user_telegram_id).first()

        if not user:
            user = User(
                telegram_id=test_user_telegram_id,
                username="test_e2e_user",
                first_name="Test",
                last_name="E2E"
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            print(f"  ✅ Usuario de test creado: ID={user.id}, Telegram={user.telegram_id}")
        else:
            # Refrescar para asegurar que está en la sesión actual
            self.db.refresh(user)
            print(f"  ✅ Usuario de test encontrado: ID={user.id}, Telegram={user.telegram_id}")

        # Guardar el user_id para evitar problemas de sesión
        user_id = user.id

        # Asegurar que tenga balance
        balance = besito_service.get_or_create_balance(user_id)
        initial_balance = balance.balance if balance else 0
        print(f"  💰 Balance inicial del usuario: {initial_balance} besitos")

        # Crear un mensaje de broadcast de test
        test_channel = self.db.query(Channel).first()
        if not test_channel:
            print("  ⚠️  No hay canales en la base de datos")
            return

        # Crear mensaje de broadcast
        broadcast_msg = BroadcastMessage(
            message_id=999999999,
            channel_id=test_channel.channel_id,
            admin_id=987654321,
            text="Test E2E - Reacción y Misiones (DATOS REALES)",
            has_reactions=True
        )
        self.db.add(broadcast_msg)
        self.db.commit()
        self.db.refresh(broadcast_msg)
        broadcast_msg_id = broadcast_msg.id
        print(f"  📝 Mensaje de broadcast creado: ID={broadcast_msg_id}")

        # ========================================
        # PASS 4: REGISTRAR REACCIÓN
        # ========================================
        print("\n📋 PASS 4: REGISTRANDO REACCIÓN")
        print("-" * 50)

        # Usar el primer emoji disponible
        if not emojis:
            # Crear uno si no existe
            emoji = broadcast_service.create_reaction_emoji(
                emoji="💋",
                name="besito_test",
                besito_value=1
            )
            emojis = [emoji]

        emoji = emojis[0]
        # Guardar solo los datos necesarios para evitar DetachedInstanceError
        emoji_id = emoji.id
        emoji_str = emoji.emoji
        emoji_value = emoji.besito_value

        print(f"  🎭 Emoji a usar: {emoji_str} (valor: {emoji_value} besitos)")

        # Registrar reacción
        reaction = broadcast_service.register_reaction(
            broadcast_id=broadcast_msg_id,
            user_id=user_id,
            emoji_id=emoji_id,
            username=user.username
        )

        if reaction:
            print(f"  ✅ Reacción registrada: ID={reaction.id}")
            print(f"     Besitos otorgados por reacción: +{reaction.besitos_awarded}")
            besitos_from_reaction = reaction.besitos_awarded
            reaction_id = reaction.id
        else:
            print("  ℹ️  El usuario ya había reaccionado a este mensaje")
            besitos_from_reaction = 0
            reaction_id = None

        # ========================================
        # PASS 5: PROCESAR MISIONES
        # ========================================
        print("\n📋 PASS 5: MISIONES DISPARADAS POR LA REACCIÓN")
        print("-" * 50)

        # Importar el event loop para ejecutar el método async
        import asyncio

        # Crear un mock del bot para la entrega de recompensas
        # El mock necesita tener session para que RewardService pueda usar besito_service
        class MockBot:
            def __init__(self, db_session):
                self.session = db_session

        mock_bot = MockBot(self.db)

        # Incrementar progreso Y entregar recompensas automáticamente
        completed_missions = asyncio.run(
            mission_service.increment_progress_and_deliver(
                user_id=user_id,
                mission_type=MissionType.REACTION_COUNT,
                amount=1,
                bot=mock_bot,
                reference_id=broadcast_msg_id
            )
        )

        print(f"  🚀 Misiones REACTION_COUNT procesadas: {len(mission_ids)}")
        print(f"  ✅ Misiones completadas en esta interacción: {len(completed_missions)}")

        # Mostrar progreso de cada misión
        print("\n  📊 Progreso en misiones de REACCIÓN:")
        for mid in mission_ids:
            mission = self.db.query(Mission).filter(Mission.id == mid).first()
            progress = mission_service.get_user_progress(user_id, mid)
            if progress and mission:
                pct = int((progress.current_value / mission.target_value) * 100) if mission.target_value > 0 else 0
                status = "✅ COMPLETADA" if progress.is_completed else f"{progress.current_value}/{mission.target_value} ({pct}%)"
                print(f"     • {mission.name}: {status}")
            elif mission:
                print(f"     • {mission.name}: 0/{mission.target_value} (0%)")

        # Calcular besitos de recompensas desde las misiones completadas
        besitos_from_missions = 0
        for mid in mission_ids:
            mission = self.db.query(Mission).filter(Mission.id == mid).first()
            progress = mission_service.get_user_progress(user_id, mid)
            if progress and progress.is_completed and mission and mission.reward_id:
                reward = self.db.query(Reward).filter(Reward.id == mission.reward_id).first()
                if reward and reward.reward_type == RewardType.BESITOS:
                    besitos_from_missions += reward.besito_amount

        # ========================================
        # PASS 6: BALANCE FINAL
        # ========================================
        print("\n📋 PASS 6: BALANCE FINAL DE BESITOS")
        print("-" * 50)

        final_balance = besito_service.get_balance(user_id)
        total_gained = final_balance - initial_balance

        print(f"  💰 Balance inicial: {initial_balance} besitos")
        print(f"  + Besitos por reacción directa: +{besitos_from_reaction}")
        print(f"  + Besitos por recompensas: +{besitos_from_missions}")
        print(f"  ─────────────────────────────────────")
        print(f"  📈 TOTAL BESITOS GANADOS: {total_gained} besitos")
        print(f"  💰 Balance final: {final_balance} besitos")

        # ========================================
        # RESUMEN FINAL
        # ========================================
        print("\n" + "="*70)
        print("📊 RESUMEN DEL FLUJO E2E (DATOS REALES)")
        print("="*70)
        print(f"""
  ┌────────────────────────────────────────────────────────────────┐
  │ 1. Reacción registrada: {emoji_str} en mensaje #{broadcast_msg_id}
  ├────────────────────────────────────────────────────────────────┤
  │ 2. Misiones REACTION_COUNT activas: {len(mission_ids)}
  ├────────────────────────────────────────────────────────────────┤
  │ 3. Misiones completadas ahora: {len(completed_missions)}
  ├────────────────────────────────────────────────────────────────┤
  │ 4. Besitos de reacción directa: +{besitos_from_reaction}
  ├────────────────────────────────────────────────────────────────┤
  │ 5. Besitos de recompensas: +{besitos_from_missions}
  ├────────────────────────────────────────────────────────────────┤
  │ 6. TOTAL BESITOS OBTENIDOS: {total_gained} besitos
  └────────────────────────────────────────────────────────────────┘
        """)

        # Mostrar detalle de cada misión
        print("\n📋 DETALLE DE MISIONES REACTION_COUNT:")
        print("-" * 50)
        for mid in mission_ids:
            mission = self.db.query(Mission).filter(Mission.id == mid).first()
            progress = mission_service.get_user_progress(user_id, mid)
            if progress and mission:
                pct = int((progress.current_value / mission.target_value) * 100) if mission.target_value > 0 else 0
                reward_details = ""
                if mission.reward_id:
                    reward = self.db.query(Reward).filter(Reward.id == mission.reward_id).first()
                    if reward:
                        if reward.reward_type == RewardType.BESITOS:
                            reward_details = f" | Recompensa: {reward.besito_amount} besitos al completar"
                        elif reward.reward_type == RewardType.VIP_ACCESS:
                            reward_details = f" | Recompensa: VIP_ACCESS {reward.vip_days} días"

                print(f"  🎯 {mission.name}")
                print(f"     Progreso: {progress.current_value}/{mission.target_value} ({pct}%){reward_details}")
                if progress.is_completed:
                    print(f"     Estado: ✅ COMPLETADA el {progress.completed_at}")

        print("\n✅ TEST E2E CON DATOS REALES COMPLETADO")

    def test_list_all_active_missions_real_db(self):
        """
        Lista todas las misiones activas en la base de datos real.
        """
        print("\n" + "="*70)
        print("📋 TODAS LAS MISIONES ACTIVAS EN EL SISTEMA")
        print("="*70)

        mission_service = MissionService(self.db)

        all_missions = mission_service.get_available_missions()

        if not all_missions:
            print("\n  ⚠️  No hay misiones activas configuradas")
        else:
            print(f"\n  Total de misiones activas: {len(all_missions)}\n")

            for m in all_missions:
                print(f"  📌 {m.name}")
                print(f"     Tipo: {m.mission_type.value if m.mission_type else 'N/A'}")
                print(f"     Meta: {m.target_value}")
                print(f"     Frecuencia: {m.frequency.value if m.frequency else 'N/A'}")
                print(f"     Descripción: {m.description or 'Sin descripción'}")

                if m.reward_id:
                    reward = self.db.query(Reward).filter(Reward.id == m.reward_id).first()
                    if reward:
                        print(f"     Recompensa: {reward.reward_type.value if reward.reward_type else 'N/A'}")
                        if reward.reward_type == RewardType.BESITOS:
                            print(f"       → {reward.besito_amount} besitos")
                        elif reward.reward_type == RewardType.VIP_ACCESS:
                            print(f"       → {reward.vip_days} días VIP_ACCESS")

                print()

        # Agrupar por tipo
        print("\n📊 RESUMEN POR TIPO:")
        print("-" * 50)
        by_type = {}
        for m in all_missions:
            t = m.mission_type.value if m.mission_type else 'unknown'
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(m.name)

        for t, names in by_type.items():
            print(f"  {t}: {len(names)} misión(es)")
            for n in names:
                print(f"    • {n}")


# Tests que pueden ejecutarse independientemente
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])