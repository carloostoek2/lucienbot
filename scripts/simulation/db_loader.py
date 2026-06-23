"""Carga configuración real desde BD (modo --from-db)."""

from __future__ import annotations

from scripts.simulation.constants import (
    DEFAULT_DAILY_GIFT,
    DEFAULT_REACTION_VALUE,
    EconomyConfig,
    MISSION_BASIC_REWARD,
    MISSION_STREAK_REWARD,
    MISSION_STREAK_TARGET,
    PLAY_LIMITS,
)


def load_economy_config_from_db() -> EconomyConfig:
    from models.database import SessionLocal
    from models.models import DailyGiftConfig, Mission, ReactionEmoji, Reward

    db = SessionLocal()
    try:
        daily_gift = DEFAULT_DAILY_GIFT
        cfg = db.query(DailyGiftConfig).first()
        if cfg and cfg.is_active:
            daily_gift = cfg.besito_amount

        reaction_value = DEFAULT_REACTION_VALUE
        emoji = (
            db.query(ReactionEmoji)
            .filter(ReactionEmoji.is_active.is_(True))
            .order_by(ReactionEmoji.besito_value.desc())
            .first()
        )
        if emoji:
            reaction_value = emoji.besito_value

        mission_basic = MISSION_BASIC_REWARD
        mission_streak = MISSION_STREAK_REWARD
        streak_target = MISSION_STREAK_TARGET
        for mission in db.query(Mission).filter(Mission.is_active.is_(True)).all():
            if mission.name == "Reacciona y Gana" and mission.reward_id:
                reward = db.query(Reward).filter(Reward.id == mission.reward_id).first()
                if reward and reward.besito_amount:
                    mission_basic = reward.besito_amount
            if mission.name == "Racha de 3 Posts" and mission.reward_id:
                reward = db.query(Reward).filter(Reward.id == mission.reward_id).first()
                if reward and reward.besito_amount:
                    mission_streak = reward.besito_amount
                streak_target = mission.target_value or MISSION_STREAK_TARGET

        from services.trivia_config_service import TriviaConfigService

        trivia_svc = TriviaConfigService(db)
        tcfg = trivia_svc.get_config()

        play_limits = {
            "trivia_free": tcfg["trivia_limit_free"],
            "trivia_vip": tcfg["trivia_limit_vip"],
            "trivia_simple_free": tcfg["trivia_simple_limit_free"],
            "trivia_vip_vip": tcfg["trivia_vip_limit"],
            "trivia_simple_vip": tcfg["trivia_simple_limit_vip"],
        }
        trivia_caps = {
            "daily_cap_free": tcfg["trivia_besitos_daily_free"],
            "daily_cap_vip": tcfg["trivia_besitos_daily_vip"],
            "weekly_cap_free": tcfg["trivia_besitos_weekly_free"],
            "weekly_cap_vip": tcfg["trivia_besitos_weekly_vip"],
        }

        return EconomyConfig(
            daily_gift=daily_gift,
            reaction_value=reaction_value,
            mission_basic_reward=mission_basic,
            mission_streak_reward=mission_streak,
            mission_streak_target=streak_target,
            dice_limit_free=tcfg["dice_limit_free"],
            dice_limit_vip=tcfg["dice_limit_vip"],
            play_limits=play_limits,
            trivia_caps=trivia_caps,
        )
    finally:
        db.close()