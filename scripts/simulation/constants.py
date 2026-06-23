"""Constantes de economía alineadas a GameService, TriviaConfigService y migración."""

from __future__ import annotations

from dataclasses import dataclass, field

# --- Regalo diario / reacciones (migración producción) ---
DEFAULT_DAILY_GIFT = 5
DEFAULT_REACTION_VALUE = 2

# --- Misiones (migrate_config_to_production.py) ---
MISSION_BASIC_REWARD = 5
MISSION_STREAK_REWARD = 15
MISSION_STREAK_TARGET = 3

# --- Dados (GameService) ---
DICE_WIN_BESITOS = 1
DICE_WIN_PROBABILITY = 12 / 36  # pares o dobles
DAILY_DICE_LIMIT_FREE = 10
DAILY_DICE_LIMIT_VIP = 20

# --- Trivia bases y caps (GameService / TriviaConfigService) ---
TRIVIA_WIN_BESITOS = 1
TRIVIA_VIP_WIN_BESITOS = 2
TRIVIA_SIMPLE_WIN_BESITOS = 1
TRIVIA_SIMPLE_VIP_WIN_BESITOS = 2

DAILY_TRIVIA_LIMIT_FREE = 5
DAILY_TRIVIA_LIMIT_VIP = 10
DAILY_TRIVIA_VIP_LIMIT = 5
DAILY_TRIVIA_SIMPLE_LIMIT_FREE = 5
DAILY_TRIVIA_SIMPLE_LIMIT_VIP = 10

TRIVIA_BESITOS_DAILY_FREE = 10
TRIVIA_BESITOS_DAILY_VIP = 15
TRIVIA_BESITOS_WEEKLY_FREE = 30
TRIVIA_BESITOS_WEEKLY_VIP = 40

STREAK_MILESTONES: dict[int, int] = {3: 2, 5: 5, 7: 10, 10: 20}

PLAY_LIMITS = {
    "trivia_free": DAILY_TRIVIA_LIMIT_FREE,
    "trivia_vip": DAILY_TRIVIA_LIMIT_VIP,
    "trivia_simple_free": DAILY_TRIVIA_SIMPLE_LIMIT_FREE,
    "trivia_vip_vip": DAILY_TRIVIA_VIP_LIMIT,
    "trivia_simple_vip": DAILY_TRIVIA_SIMPLE_LIMIT_VIP,
}

# Era "after" (post caps 2026-06-17) — compat con simulate_trivia_earnings
TRIVIA_ERA_AFTER = {
    "trivia_base": TRIVIA_WIN_BESITOS,
    "trivia_vip_base": TRIVIA_VIP_WIN_BESITOS,
    "trivia_simple_base_free": TRIVIA_SIMPLE_WIN_BESITOS,
    "trivia_simple_base_vip": TRIVIA_SIMPLE_VIP_WIN_BESITOS,
    "daily_cap_free": TRIVIA_BESITOS_DAILY_FREE,
    "daily_cap_vip": TRIVIA_BESITOS_DAILY_VIP,
    "weekly_cap_free": TRIVIA_BESITOS_WEEKLY_FREE,
    "weekly_cap_vip": TRIVIA_BESITOS_WEEKLY_VIP,
    "play_limits": PLAY_LIMITS,
}

TRIVIA_ERA_BEFORE = {
    "trivia_base": 1,
    "trivia_vip_base": 5,
    "trivia_simple_base_free": 2,
    "trivia_simple_base_vip": 4,
    "daily_cap": None,
    "weekly_cap": None,
    "play_limits": {
        **PLAY_LIMITS,
        "trivia_vip_only": True,
        "trivia_vip_free": 0,
        "trivia_free_vip": DAILY_TRIVIA_LIMIT_VIP,
    },
}


@dataclass
class EconomyConfig:
    """Parámetros configurables de la simulación."""

    daily_gift: int = DEFAULT_DAILY_GIFT
    reaction_value: int = DEFAULT_REACTION_VALUE
    posts_per_day: int = 1
    mission_basic_reward: int = MISSION_BASIC_REWARD
    mission_streak_reward: int = MISSION_STREAK_REWARD
    mission_streak_target: int = MISSION_STREAK_TARGET
    dice_win_besitos: int = DICE_WIN_BESITOS
    dice_limit_free: int = DAILY_DICE_LIMIT_FREE
    dice_limit_vip: int = DAILY_DICE_LIMIT_VIP
    trivia_accuracy: float = 0.6
    include_daily_missions: bool = False
    daily_mission_streak_reward: int = 0
    daily_mission_total_reward: int = 0
    play_limits: dict[str, int] = field(default_factory=lambda: dict(PLAY_LIMITS))
    trivia_caps: dict[str, int] = field(
        default_factory=lambda: {
            "daily_cap_free": TRIVIA_BESITOS_DAILY_FREE,
            "daily_cap_vip": TRIVIA_BESITOS_DAILY_VIP,
            "weekly_cap_free": TRIVIA_BESITOS_WEEKLY_FREE,
            "weekly_cap_vip": TRIVIA_BESITOS_WEEKLY_VIP,
        }
    )


PROFILE_NAMES = (
    "free_realistic",
    "free_max",
    "vip_realistic",
    "vip_max",
)