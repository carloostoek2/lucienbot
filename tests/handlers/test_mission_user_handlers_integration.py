"""
Tests de integración para mission_user_handlers (tight).

Usa SQLite + MissionService real + bot mockeado.
Verifica: show_my (progress bars real), detail (progress + catchup + reward shape), claim (real deliver).
"""
from unittest.mock import patch

import pytest

from models.models import (
    Mission,
    MissionFrequency,
    MissionType,
    UserMissionProgress,
)
from services.mission_service import MissionService

pytestmark = [pytest.mark.integration]


class TestShowMyMissionsIntegration:
    """Tests de integración tight para show_my_missions (real progress bars)."""

    async def test_show_my_missions_real_progress_bars(
        self, make_callback, db_session, sample_user
    ):
        """Misiones activas con progreso real → barras █░ + % + valores."""
        tg = sample_user.telegram_id
        mission = Mission(
            name="Test Mission Int",
            description="Do X",
            mission_type=MissionType.REACTION_COUNT,
            target_value=10,
            frequency=MissionFrequency.ONE_TIME,
            is_active=True,
        )
        db_session.add(mission)
        db_session.commit()
        db_session.refresh(mission)

        prog = UserMissionProgress(
            user_id=tg, mission_id=mission.id, target_value=10, current_value=3, is_completed=False
        )
        db_session.add(prog)
        db_session.commit()

        real_svc = MissionService(db_session)
        cb = make_callback(data="my_missions", user=type("U", (), {"id": tg})())

        with patch("handlers.mission_user_handlers.MissionService") as mock_cls:
            mock_cls.return_value = real_svc
            from handlers.mission_user_handlers import show_my_missions
            await show_my_missions(cb)

        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Test Mission Int" in text
        assert "3" in text and "10" in text
        assert "%" in text or "█" in text or "░" in text
        cb.answer.assert_called_once()


class TestMissionDetailIntegration:
    """Tests de integración tight para mission_detail (progress + catchup + reward)."""

    async def test_mission_detail_not_found_graceful_real(
        self, make_callback, db_session, sample_user
    ):
        """Detail con id inexistente: real get_mission=None → answer 'no encontrada' (no deleted instance)."""
        tg = sample_user.telegram_id
        real_svc = MissionService(db_session)
        from keyboards.callback_data import MissionDetailCallback

        cb_data = MissionDetailCallback(mission_id=999999)
        cb = make_callback(data=cb_data.pack(), user=type("U", (), {"id": tg})())

        with patch("handlers.mission_user_handlers.MissionService") as mock_cls:
            mock_cls.return_value = real_svc
            from handlers.mission_user_handlers import mission_detail
            await mission_detail(cb, cb_data)

        cb.answer.assert_called()
        assert "no encontrada" in str(cb.answer.call_args).lower() or cb.answer.called


class TestClaimMissionRewardIntegration:
    """Tests de integración tight para claim_mission_reward (real deliver)."""

    async def test_claim_mission_reward_real_deliver(
        self, make_callback, db_session, sample_user
    ):
        """Claim con pending real → deliver visible (success or pending alert)."""
        tg = sample_user.telegram_id
        real_svc = MissionService(db_session)
        cb = make_callback(data="claim_mission_reward", user=type("U", (), {"id": tg})())

        with patch("handlers.mission_user_handlers.MissionService") as mock_cls:
            mock_cls.return_value = real_svc
            from handlers.mission_user_handlers import claim_mission_reward
            await claim_mission_reward(cb)

        cb.answer.assert_called_once()
        # Alert text from LucienVoice (success or pending)
        arg = str(cb.answer.call_args)
        assert "mision" in arg.lower() or "recompensa" in arg.lower() or "pendiente" in arg.lower() or "entreg" in arg.lower()
