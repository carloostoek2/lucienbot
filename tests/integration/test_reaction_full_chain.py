"""
Integration test: Full reaction flow (production path) - Patrón SQLite en archivo

Covers the complete real-world chain when a user reacts to a broadcast:

1. Reaction registration + besitos credit (check_and_register_reaction)
2. Automatic mission progress + reward delivery (increment_progress_and_deliver + deliver_reward)
3. Post-reaction UI update: rebuilding reaction keyboard with live counts

Este archivo establece el **patrón recomendado** para tests de integración complejos
que cruzan múltiples servicios con commits internos (BroadcastService, MissionService,
RewardService, BesitoService, etc.).

Patrón: SQLite en archivo temporal + TestSession independiente (ver también
test_vip_subscription_lifecycle.py).
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from keyboards.inline_keyboards import reactions_keyboard_with_counts
from models.database import Base
from models.models import (
    BesitoBalance,
    BroadcastMessage,
    BroadcastReaction,
    Channel,
    ChannelType,
    Mission,
    MissionFrequency,
    MissionType,
    ReactionEmoji,
    Reward,
    RewardType,
    User,
    UserRole,
)
from services.besito_service import BesitoService
from services.broadcast_service import BroadcastService
from services.mission_service import MissionService


@pytest.mark.integration
class TestFullReactionChainWithMissionAndKeyboardUpdate:
    """
    Test del flujo completo usando el patrón de SQLite en archivo.

    Este es el patrón preferido para flujos pesados con muchos commits internos
    de servicios. Evita por completo los problemas de DetachedInstanceError
    que aparecen con el fixture db_session global.
    """

    def _create_engine_and_session(self, tmp_path):
        """Crea engine + sessionmaker sobre archivo SQLite temporal.

        Usamos archivo (no :memory:) porque los servicios crean sus propias
        SessionLocal() internamente en algunos caminos, y necesitamos que
        todas las conexiones vean los mismos datos de forma confiable.
        """
        db_path = tmp_path / "test_reaction_full_chain.db"
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return engine, TestSession

    @pytest.mark.asyncio
    async def test_reaction_advances_mission_and_updates_keyboard_counts(self, tmp_path):
        """
        Flujo completo usando el patrón de SQLite en archivo:
        reacción → besitos → misión completada → recompensa entregada → conteos de teclado actualizados.
        """
        engine, TestSession = self._create_engine_and_session(tmp_path)
        db = TestSession()

        try:
            # Usuario de prueba
            user = User(
                telegram_id=111111,
                username="testuser",
                first_name="Test",
                role=UserRole.USER,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Canal
            channel = Channel(
                channel_id=-100111222333,
                channel_name="Test Broadcast Channel",
                channel_type=ChannelType.FREE,
                is_active=True,
            )
            db.add(channel)
            db.commit()

            # Emojis
            emoji1 = ReactionEmoji(emoji="💋", name="beso", besito_value=2, is_active=True)
            emoji2 = ReactionEmoji(emoji="❤️", name="corazon", besito_value=1, is_active=True)
            db.add_all([emoji1, emoji2])
            db.commit()
            db.refresh(emoji1)
            db.refresh(emoji2)
            emoji1_id = emoji1.id
            emoji2_id = emoji2.id

            # Broadcast con reacciones
            selected_ids_str = f"{emoji1_id},{emoji2_id}"
            broadcast = BroadcastMessage(
                message_id=999001,
                channel_id=channel.channel_id,
                admin_id=987654321,
                text="Mensaje de prueba con reacciones",
                has_reactions=True,
                selected_emoji_ids=selected_ids_str,
            )
            db.add(broadcast)
            db.commit()
            db.refresh(broadcast)

            broadcast_db_id = broadcast.id
            broadcast_telegram_id = broadcast.message_id
            broadcast_channel_id = broadcast.channel_id

            # Recompensa + Misión
            reward = Reward(
                name="Recompensa por reaccionar",
                description="5 besitos por completar la misión de reacciones",
                reward_type=RewardType.BESITOS,
                besito_amount=5,
                is_active=True,
            )
            db.add(reward)
            db.commit()
            db.refresh(reward)

            mission = Mission(
                name="Reaccionista Veloz",
                description="Reacciona 1 vez",
                mission_type=MissionType.REACTION_COUNT,
                target_value=1,
                frequency=MissionFrequency.ONE_TIME,
                reward_id=reward.id,
                is_active=True,
            )
            db.add(mission)
            db.commit()

            mission_id = mission.id

            # Balance
            # DESIRED CONTRACT: besito balance user_id = TG BigInt (user.telegram_id value here 111111), not PK .id
            balance = BesitoBalance(
                user_id=user.telegram_id, balance=0, total_earned=0, total_spent=0
            )
            db.add(balance)
            db.commit()

            # Cerramos la sesión de setup y abrimos una fresca para la ejecución.
            # Patrón recomendado para flujos con muchos commits internos de servicios.
            user_id = user.telegram_id  # besito key = TG id (contract)
            db.close()
            db = TestSession()

            mock_bot = AsyncMock()
            mock_bot.get_me.return_value = type("obj", (object,), {"username": "testlucienbot"})()

            # ==========================================
            # EJECUCIÓN DEL FLUJO REAL
            # ==========================================
            broadcast_service = BroadcastService(db)
            besito_service = BesitoService(db)

            reaction_result = await broadcast_service.check_and_register_reaction(
                broadcast_id=broadcast_db_id,
                user_id=user_id,
                emoji_id=emoji1_id,
                username="testuser",
                bot=mock_bot,
            )

            assert reaction_result["success"] is True
            assert reaction_result["besitos_awarded"] == 2

            # Lógica exacta de actualización de teclado del handler
            selected_emoji_ids = broadcast_service.get_selected_emoji_ids(broadcast_db_id)
            reactions = broadcast_service.get_reactions_by_broadcast(broadcast_db_id)

            emoji_counts = {}
            for r in reactions:
                if r.reaction_emoji:
                    eid = r.reaction_emoji.id
                    emoji_counts[eid] = emoji_counts.get(eid, 0) + 1

            emojis_for_keyboard = []
            for eid in selected_emoji_ids:
                emoji_obj = broadcast_service.get_reaction_emoji(eid)
                if emoji_obj:
                    emojis_for_keyboard.append((eid, emoji_obj.emoji))

            new_markup = reactions_keyboard_with_counts(
                broadcast_db_id, emojis_for_keyboard, emoji_counts
            )

            await broadcast_service.update_reaction_message(
                bot=mock_bot,
                channel_id=broadcast_channel_id,
                message_id=broadcast_telegram_id,
                new_markup=new_markup,
            )

            # ==========================================
            # ASSERTS DEL FLUJO COMPLETO
            # ==========================================
            reaction_in_db = (
                db.query(BroadcastReaction)
                .filter(
                    BroadcastReaction.broadcast_id == broadcast_db_id,
                    BroadcastReaction.user_id == user_id,
                )
                .first()
            )
            assert reaction_in_db is not None
            assert reaction_in_db.besitos_awarded == 2

            mission_service = MissionService(db)
            progress = mission_service.get_user_progress(user_id, mission_id)
            assert progress is not None
            assert progress.is_completed is True
            assert progress.current_value == 1
            assert progress.last_reference_id == broadcast_db_id

            final_balance = besito_service.get_balance(user_id)
            assert final_balance == 7  # 2 (reacción) + 5 (recompensa de misión)

            assert emoji_counts.get(emoji1_id) == 1
            assert emoji_counts.get(emoji2_id, 0) == 0

            mock_bot.edit_message_reply_markup.assert_awaited()

            call_args = mock_bot.edit_message_reply_markup.await_args
            assert call_args.kwargs["chat_id"] == broadcast_channel_id
            assert call_args.kwargs["message_id"] == broadcast_telegram_id

        finally:
            db.close()
            engine.dispose()

    @pytest.mark.asyncio
    async def test_multiple_reactions_update_counts_correctly(self, tmp_path):
        """
        Variante con dos usuarios. Valida que los conteos en el teclado se acumulan
        correctamente (parte que históricamente ha tenido comportamientos raros).
        """
        engine, TestSession = self._create_engine_and_session(tmp_path)
        db = TestSession()

        try:
            user1 = User(telegram_id=111111, username="u1", first_name="U1", role=UserRole.USER)
            user2 = User(telegram_id=222222, username="u2", first_name="U2", role=UserRole.USER)
            db.add_all([user1, user2])
            db.commit()

            channel = Channel(
                channel_id=-100444555666,
                channel_name="Multi Reaction Test",
                channel_type=ChannelType.FREE,
                is_active=True,
            )
            db.add(channel)
            db.commit()

            emoji = ReactionEmoji(emoji="🔥", name="fuego", besito_value=1, is_active=True)
            db.add(emoji)
            db.commit()

            broadcast = BroadcastMessage(
                message_id=999002,
                channel_id=channel.channel_id,
                admin_id=1,
                text="Test multi reacción",
                has_reactions=True,
                selected_emoji_ids=str(emoji.id),
            )
            db.add(broadcast)
            db.commit()
            db.refresh(broadcast)

            for uid in [user1.telegram_id, user2.telegram_id]:
                db.add(BesitoBalance(user_id=uid, balance=0, total_earned=0, total_spent=0))
            db.commit()

            mock_bot = AsyncMock()

            broadcast_service = BroadcastService(db)

            await broadcast_service.check_and_register_reaction(
                broadcast_id=broadcast.id,
                user_id=user1.telegram_id,
                emoji_id=emoji.id,
                bot=mock_bot,
            )
            await broadcast_service.check_and_register_reaction(
                broadcast_id=broadcast.id,
                user_id=user2.telegram_id,
                emoji_id=emoji.id,
                bot=mock_bot,
            )

            reactions = broadcast_service.get_reactions_by_broadcast(broadcast.id)
            emoji_counts = {}
            for r in reactions:
                if r.reaction_emoji:
                    eid = r.reaction_emoji.id
                    emoji_counts[eid] = emoji_counts.get(eid, 0) + 1

            assert emoji_counts.get(emoji.id) == 2

            emojis = [(emoji.id, emoji.emoji)]
            _markup = reactions_keyboard_with_counts(broadcast.id, emojis, emoji_counts)

            assert emoji_counts[emoji.id] == 2

        finally:
            db.close()
            engine.dispose()
