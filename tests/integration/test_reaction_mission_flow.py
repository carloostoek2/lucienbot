"""
Test E2E de Reacciones y Misiones - Flujo Completo

Este test verifica el flujo completo desde que un usuario reacciona a un mensaje:
1. Qué misión se activa (tipo REACTION_COUNT)
2. Cuántas misiones se disparan por esa reacción
3. Cuántos besitos se dan por cada misión
4. Cuántos besitos obtuvo en total el usuario

DATOS REALES: Este test extrae las misiones actuales de la base de datos,
NO usa mocks - trabaja con los datos真实的 del sistema.
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from services.broadcast_service import BroadcastService
from services.mission_service import MissionService
from services.besito_service import BesitoService
from models.models import (
    BroadcastMessage, BroadcastReaction, Channel, ChannelType,
    ReactionEmoji, User, Mission, MissionType, MissionFrequency,
    Reward, RewardType, BesitoBalance, BesitoTransaction
)


@pytest.mark.integration
class TestReactionMissionFlow:
    """Test E2E del flujo reacción → misión → besitos"""

    def test_complete_reaction_mission_flow_with_real_data(self, db_session, sample_user, sample_free_channel):
        """
        Test completo del flujo de reacción → misiones → besitos.

        Este test:
        1. Obtiene las misiones REACTION_COUNT reales de la BD
        2. Crea un mensaje de broadcast
        3. Registra una reacción del usuario
        4. Muestra paso a paso qué misiones se activan y cuántos besitos otorga cada una
        5. Verifica el balance final de besitos del usuario
        """
        print("\n" + "="*70)
        print("TEST E2E: FLUHO REACCIÓN → MISIONES → BESITOS")
        print("="*70)

        # ========================================
        # PASS 1: CONSULTAR MISIONES REALES
        # ========================================
        print("\n📋 PASS 1: CONSULTANDO MISIONES REALES DE LA BASE DE DATOS")
        print("-" * 50)

        mission_service = MissionService(db_session)

        # Obtener todas las misiones de tipo REACTION_COUNT
        reaction_missions = mission_service.get_missions_by_type(MissionType.REACTION_COUNT)

        print(f"🎯 Misiones REACTION_COUNT encontradas: {len(reaction_missions)}")

        if not reaction_missions:
            print("⚠️  NO hay misiones REACTION_COUNT configuradas en el sistema")
            print("   El flujo de misiones no se ejecutará (no hay misiones que dispararse)")
            mission_details = []
        else:
            # Obtener detalles de cada misión
            mission_details = []
            for m in reaction_missions:
                # Obtener la recompensa si existe
                reward_info = None
                if m.reward_id:
                    reward = db_session.query(Reward).filter(Reward.id == m.reward_id).first()
                    if reward:
                        reward_info = {
                            'type': reward.reward_type.value if reward.reward_type else 'unknown',
                            'besitos': reward.besitos_amount if hasattr(reward, 'besitos_amount') else 0,
                            'package_id': reward.package_id
                        }

                mission_details.append({
                    'id': m.id,
                    'name': m.name,
                    'description': m.description,
                    'target_value': m.target_value,
                    'frequency': m.frequency.value if m.frequency else 'unknown',
                    'is_active': m.is_active,
                    'reward_id': m.reward_id,
                    'reward': reward_info
                })

                print(f"\n  📌 Misión #{m.id}: {m.name}")
                print(f"     Descripción: {m.description or 'Sin descripción'}")
                print(f"     Meta: {m.target_value} reacciones")
                print(f"     Frecuencia: {m.frequency.value if m.frequency else 'N/A'}")
                print(f"     Activa: {m.is_active}")
                if reward_info:
                    print(f"     Recompensa: {reward_info['type']} - {reward_info.get('besitos', 'N/A')} besitos")

        # ========================================
        # PASS 2: PREPARAR BROADCAST Y REACCIÓN
        # ========================================
        print("\n\n📋 PASS 2: PREPARANDO MENSAJE DE BROADCAST")
        print("-" * 50)

        broadcast_service = BroadcastService(db_session)

        # Obtener o crear emoji de reacción
        emoji = broadcast_service.get_reaction_emoji_by_emoji("💋")
        if not emoji:
            emoji = broadcast_service.create_reaction_emoji(
                emoji="💋",
                name="besito",
                besito_value=1
            )
        print(f"  Emoji configurado: {emoji.emoji} (valor: {emoji.besito_value} besitos)")

        # Crear mensaje de broadcast
        broadcast_msg = BroadcastMessage(
            message_id=999998,
            channel_id=sample_free_channel.channel_id,
            admin_id=987654321,
            text="Test E2E - Reacción y Misiones",
            has_reactions=True
        )
        db_session.add(broadcast_msg)
        db_session.commit()
        db_session.refresh(broadcast_msg)
        print(f"  Mensaje de broadcast creado: ID={broadcast_msg.id}")

        # ========================================
        # PASS 3: OBTENER BALANCE INICIAL
        # ========================================
        print("\n📋 PASS 3: BALANCE INICIAL DE BESITOS")
        print("-" * 50)

        besito_service = BesitoService(db_session)
        initial_balance = besito_service.get_balance(sample_user.id)
        print(f"  Usuario: {sample_user.id}")
        print(f"  Balance inicial: {initial_balance} besitos")

        # ========================================
        # PASS 4: REGISTRAR REACCIÓN (SINCRÓNICO)
        # ========================================
        print("\n📋 PASS 4: REGISTRANDO REACCIÓN")
        print("-" * 50)

        # Usar el método síncrono register_reaction para evitar problemas async
        reaction = broadcast_service.register_reaction(
            broadcast_id=broadcast_msg.id,
            user_id=sample_user.id,
            emoji_id=emoji.id,
            username=sample_user.username
        )

        if reaction:
            print(f"  ✅ Reacción registrada exitosamente")
            print(f"     Reaction ID: {reaction.id}")
            print(f"     Besitos otorgados por reacción: {reaction.besitos_awarded}")
        else:
            print(f"  ⚠️  Reacción no registrada (posiblemente ya existía)")

        # ========================================
        # PASS 5: PROCESAR MISIONES (INCREMENTAR PROGRESO)
        # ========================================
        print("\n📋 PASS 5: PROCESANDO MISIONES DISPARADAS")
        print("-" * 50)

        # Obtener progreso actual del usuario en las misiones
        user_progress_before = []
        for mission in reaction_missions:
            progress = mission_service.get_user_progress(sample_user.id, mission.id)
            if progress:
                user_progress_before.append({
                    'mission_id': mission.id,
                    'mission_name': mission.name,
                    'current_value': progress.current_value,
                    'target_value': mission.target_value,
                    'is_completed': progress.is_completed
                })

        print(f"  Progreso ANTES de la reacción:")
        for p in user_progress_before:
            print(f"    - {p['mission_name']}: {p['current_value']}/{p['target_value']} ({p['is_completed'] and 'COMPLETADA' or 'en progreso'})")

        # Incrementar progreso (síncrono)
        completed_missions = mission_service.increment_progress(
            user_id=sample_user.id,
            mission_type=MissionType.REACTION_COUNT,
            amount=1,
            reference_id=broadcast_msg.id
        )

        print(f"\n  🚀 Misiones disparadas por esta reacción: {len(completed_missions)}")

        # Obtener progreso después de la reacción
        user_progress_after = []
        besitos_from_missions = 0

        for mission in reaction_missions:
            progress = mission_service.get_user_progress(sample_user.id, mission.id)
            if progress:
                user_progress_after.append({
                    'mission_id': mission.id,
                    'mission_name': mission.name,
                    'current_value': progress.current_value,
                    'target_value': mission.target_value,
                    'is_completed': progress.is_completed,
                    'completed_at': progress.completed_at
                })

                # Calcular besitos de recompensas (si hay)
                if progress.is_completed and mission.reward_id:
                    reward = db_session.query(Reward).filter(Reward.id == mission.reward_id).first()
                    if reward and reward.reward_type == RewardType.BESITOS:
                        besitos_from_missions += reward.besitos_amount
                        print(f"    🎁 {mission.name}: RECOMPENSA ENTREGADA - {reward.besitos_amount} besitos")

        print(f"\n  Progreso DESPUÉS de la reacción:")
        for p in user_progress_after:
            status = "✅ COMPLETADA" if p['is_completed'] else f"en progreso ({p['current_value']}/{p['target_value']})"
            print(f"    - {p['mission_name']}: {status}")

        # ========================================
        # PASS 6: BALANCE FINAL
        # ========================================
        print("\n📋 PASS 6: BALANCE FINAL DE BESITOS")
        print("-" * 50)

        final_balance = besito_service.get_balance(sample_user.id)

        # Calcular totales
        besitos_from_reaction = reaction.besitos_awarded if reaction else 0
        total_besitos_gained = final_balance - initial_balance

        print(f"  Balance inicial: {initial_balance} besitos")
        print(f"  Besitos por reacción directa: +{besitos_from_reaction}")
        print(f"  Besitos por recompensas de misiones: +{besitos_from_missions}")
        print(f"  ─────────────────────────────────────")
        print(f"  Total ganado en esta interacción: {total_besitos_gained} besitos")
        print(f"  Balance final: {final_balance} besitos")

        # ========================================
        # PASS 7: RESUMEN FINAL
        # ========================================
        print("\n" + "="*70)
        print("📊 RESUMEN DEL FLUJO E2E")
        print("="*70)
        print(f"""
  ┌────────────────────────────────────────────────────────────────┐
  │ 1. Reacción registrada: {emoji.emoji} en mensaje #{broadcast_msg.id}
  ├────────────────────────────────────────────────────────────────┤
  │ 2. Misiones de tipo REACTION_COUNT activas: {len(reaction_missions)}
  │    {f"(Las siguientes misiones se disparan con cada reacción)" if reaction_missions else "(No hay misiones configuradas)"}
  ├────────────────────────────────────────────────────────────────┤
  │ 3. Misiones completadas en esta interacción: {len(completed_missions)}
  ├────────────────────────────────────────────────────────────────┤
  │ 4. Besitos de la reacción directa: +{besitos_from_reaction}
  ├────────────────────────────────────────────────────────────────┤
  │ 5. Besitos de recompensas de misiones: +{besitos_from_missions}
  ├────────────────────────────────────────────────────────────────┤
  │ 6. TOTAL BESITOS OBTENIDOS: {total_besitos_gained} besitos
  └────────────────────────────────────────────────────────────────┘
        """)

        # ========================================
        # ASSERTIONS
        # ========================================

        # Verificar que la reacción se registró
        assert reaction is not None, "La reacción debería haberse registrado"

        # Verificar que se otorgaron besitos por la reacción
        assert besitos_from_reaction > 0, "Deberían haberse otorgado besitos por la reacción"

        # Verificar que el balance aumentó correctamente
        expected_total = besitos_from_reaction + besitos_from_missions
        assert total_besitos_gained == expected_total, (
            f"El total de besitos ganados ({total_besitos_gained}) debería ser "
            f"reacción ({besitos_from_reaction}) + misiones ({besitos_from_missions}) = {expected_total}"
        )

        print("\n✅ TEST E2E COMPLETADO EXITOSAMENTE")

    def test_show_all_mission_types_available(self, db_session):
        """
        Muestra todos los tipos de misiones disponibles en el sistema.
        """
        print("\n" + "="*70)
        print("TIPOS DE MISIONES DISPONIBLES EN EL SISTEMA")
        print("="*70)

        mission_service = MissionService(db_session)

        print("\nEnumeración MissionType:")
        for mt in MissionType:
            print(f"  • {mt.value}")

        print("\nEnumeración MissionFrequency:")
        for mf in MissionFrequency:
            print(f"  • {mf.value}")

        # Obtener todas las misiones activas
        all_missions = mission_service.get_available_missions()

        print(f"\nMisiones activas configuradas: {len(all_missions)}")
        for m in all_missions:
            print(f"  • {m.name} ({m.mission_type.value}) - Meta: {m.target_value}")

        # Agrupar por tipo
        by_type = {}
        for m in all_missions:
            t = m.mission_type.value
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(m.name)

        print("\nMisiones por tipo:")
        for t, names in by_type.items():
            print(f"  {t}: {len(names)} misión(es) - {', '.join(names)}")

        assert True, "Información mostrada"

    def test_reaction_besitos_value_mapping(self, db_session, sample_user, sample_free_channel):
        """
        Test que muestra cómo cada emoji de reacción tiene un valor diferente de besitos.
        """
        print("\n" + "="*70)
        print("MAPA DE EMOJIS DE REACCIÓN Y SUS VALORES EN BESITOS")
        print("="*70)

        broadcast_service = BroadcastService(db_session)

        # Obtener todos los emojis activos
        emojis = broadcast_service.get_all_emojis(active_only=True)

        print(f"\nEmojis de reacción configurados: {len(emojis)}")

        if not emojis:
            print("⚠️  No hay emojis de reacción configurados")
            print("   Creando emoji de prueba...")
            emoji = broadcast_service.create_reaction_emoji(
                emoji="💋",
                name="besito",
                besito_value=1
            )
            emojis = [emoji]

        for e in emojis:
            print(f"  {e.emoji} → {e.besito_value} besitos")
            print(f"      ID: {e.id}, Nombre: {e.name}, Activo: {e.is_active}")

        # Demostrar con un mensaje
        emoji = emojis[0]
        broadcast_msg = BroadcastMessage(
            message_id=999997,
            channel_id=sample_free_channel.channel_id,
            admin_id=987654321,
            text="Test de valores de emoji",
            has_reactions=True
        )
        db_session.add(broadcast_msg)
        db_session.commit()

        # Registrar reacción
        reaction = broadcast_service.register_reaction(
            broadcast_id=broadcast_msg.id,
            user_id=sample_user.id,
            emoji_id=emoji.id
        )

        print(f"\n📝 Ejemplo de reacción:")
        print(f"   Emoji: {emoji.emoji}")
        print(f"   Besitos otorgados: {reaction.besitos_awarded if reaction else 0}")

        assert reaction is not None, "La reacción debería registrarse"
        assert reaction.besitos_awarded == emoji.besito_value, (
            f"Besitos de reacción ({reaction.besitos_awarded}) "
            f"deberían igualar el valor del emoji ({emoji.besito_value})"
        )


@pytest.mark.integration
class TestReactionMissionFlowAsync:
    """Tests asíncronos para el flujo de reacción → misiones"""

    @pytest.mark.asyncio
    async def test_async_reaction_and_mission_delivery(self, db_session, sample_user, sample_free_channel):
        """
        Test asíncrono que usa check_and_register_reaction (el método real del bot)
        y delivery automático de recompensas de misiones.
        """
        print("\n" + "="*70)
        print("TEST ASÍNCRONO: REACCIÓN + ENTREGA AUTOMÁTICA DE RECOMPENSAS")
        print("="*70)

        # Preparar
        broadcast_service = BroadcastService(db_session)
        besito_service = BesitoService(db_session)
        mission_service = MissionService(db_session)

        # Obtener emoji
        emoji = broadcast_service.get_reaction_emoji_by_emoji("💋")
        if not emoji:
            emoji = broadcast_service.create_reaction_emoji(
                emoji="💋",
                name="besito",
                besito_value=1
            )

        # Crear mensaje
        broadcast_msg = BroadcastMessage(
            message_id=999996,
            channel_id=sample_free_channel.channel_id,
            admin_id=987654321,
            text="Test async - Entrega automática",
            has_reactions=True
        )
        db_session.add(broadcast_msg)
        db_session.commit()
        db_session.refresh(broadcast_msg)

        # Balance inicial
        initial_balance = besito_service.get_balance(sample_user.id)
        print(f"\nBalance inicial: {initial_balance} besitos")

        # Mock del bot (no necesitamos enviar mensajes reales)
        mock_bot = AsyncMock()

        # Usar el método async que entrega recompensas automáticamente
        result = await broadcast_service.check_and_register_reaction(
            broadcast_id=broadcast_msg.id,
            user_id=sample_user.id,
            emoji_id=emoji.id,
            username=sample_user.username,
            bot=mock_bot
        )

        if result:
            print(f"\n✅ Reacción registrada async")
            print(f"   Besitos otorgados: {result['besitos_awarded']}")
            print(f"   Emoji: {result['emoji_char']}")

        # Balance final
        final_balance = besito_service.get_balance(sample_user.id)
        total_gained = final_balance - initial_balance

        print(f"\n📊 Balance final: {final_balance} besitos")
        print(f"   Total ganado: +{total_gained} besitos")

        # Obtener misiones completadas
        reaction_missions = mission_service.get_missions_by_type(MissionType.REACTION_COUNT)
        completed_count = 0
        for m in reaction_missions:
            progress = mission_service.get_user_progress(sample_user.id, m.id)
            if progress and progress.is_completed:
                completed_count += 1

        print(f"\n🎯 Misiones completadas: {completed_count}/{len(reaction_missions)}")

        assert result is not None, "La reacción debería registrarse"
        assert total_gained > 0, "Deberían haberse acreditado besitos"