"""Calculadores de ingreso diario por fuente de besitos."""

from __future__ import annotations

from dataclasses import dataclass, field

from scripts.simulation.constants import (
    DICE_WIN_PROBABILITY,
    EconomyConfig,
    PROFILE_NAMES,
)
from scripts.simulation.trivia_caps import (
    rolling_weekly_start,
    simulate_full_day,
)


@dataclass
class DailyIncome:
    daily_gift: int = 0
    reaction: int = 0
    mission_basic: int = 0
    mission_streak: int = 0
    mission_daily_extra: int = 0
    dice: int = 0
    trivia: int = 0

    @property
    def missions(self) -> int:
        return self.mission_basic + self.mission_streak + self.mission_daily_extra

    @property
    def total(self) -> int:
        return (
            self.daily_gift
            + self.reaction
            + self.missions
            + self.dice
            + self.trivia
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "daily_gift": self.daily_gift,
            "reaction": self.reaction,
            "mission_basic": self.mission_basic,
            "mission_streak": self.mission_streak,
            "mission_daily_extra": self.mission_daily_extra,
            "dice": self.dice,
            "trivia": self.trivia,
            "total": self.total,
        }


@dataclass
class ProfileSpec:
    name: str
    is_vip: bool
    max_effort: bool


def resolve_profile(name: str) -> ProfileSpec:
    if name not in PROFILE_NAMES:
        raise ValueError(f"Perfil desconocido: {name}. Opciones: {PROFILE_NAMES}")
    return ProfileSpec(
        name=name,
        is_vip=name.startswith("vip"),
        max_effort=name.endswith("_max"),
    )


def compute_mission_income(
    config: EconomyConfig,
    *,
    day_index: int,
    posts_today: int,
) -> tuple[int, int, int]:
    """Retorna (basic, streak, daily_extra) para el día day_index (1-based)."""
    basic = config.mission_basic_reward * posts_today if posts_today else 0
    streak = 0
    if posts_today and (day_index % config.mission_streak_target == 0):
        streak = config.mission_streak_reward
    daily_extra = 0
    if config.include_daily_missions:
        # Placeholder: recompensas one-shot al completar (simplificado)
        if config.daily_mission_streak_reward and day_index == 7:
            daily_extra += config.daily_mission_streak_reward
        if config.daily_mission_total_reward and day_index == 5:
            daily_extra += config.daily_mission_total_reward
    return basic, streak, daily_extra


def compute_dice_income(config: EconomyConfig, *, is_vip: bool, max_effort: bool) -> int:
    limit = config.dice_limit_vip if is_vip else config.dice_limit_free
    if max_effort:
        return limit * config.dice_win_besitos
    return int(round(limit * config.dice_win_besitos * DICE_WIN_PROBABILITY))


def build_trivia_cfg_override(config: EconomyConfig) -> dict:
    caps = config.trivia_caps
    return {
        "trivia_base": 1,
        "trivia_vip_base": 2,
        "trivia_simple_base_free": 1,
        "trivia_simple_base_vip": 2,
        "daily_cap_free": caps["daily_cap_free"],
        "daily_cap_vip": caps["daily_cap_vip"],
        "weekly_cap_free": caps["weekly_cap_free"],
        "weekly_cap_vip": caps["weekly_cap_vip"],
        "play_limits": config.play_limits,
    }


def compute_trivia_income(
    config: EconomyConfig,
    *,
    is_vip: bool,
    max_effort: bool,
    trivia_history: list[int],
) -> int:
    weekly_start = rolling_weekly_start(trivia_history)
    result = simulate_full_day(
        is_vip,
        era="after",
        all_correct=max_effort,
        accuracy=1.0 if max_effort else config.trivia_accuracy,
        weekly_start=weekly_start,
        play_limits=config.play_limits,
        cfg_override=build_trivia_cfg_override(config),
    )
    return result["total"]


def simulate_day_income(
    config: EconomyConfig,
    profile: ProfileSpec,
    *,
    day_index: int,
    trivia_history: list[int],
) -> DailyIncome:
    posts = config.posts_per_day
    basic, streak, daily_extra = compute_mission_income(
        config, day_index=day_index, posts_today=posts
    )
    return DailyIncome(
        daily_gift=config.daily_gift,
        reaction=config.reaction_value * posts,
        mission_basic=basic,
        mission_streak=streak,
        mission_daily_extra=daily_extra,
        dice=compute_dice_income(config, is_vip=profile.is_vip, max_effort=profile.max_effort),
        trivia=compute_trivia_income(
            config,
            is_vip=profile.is_vip,
            max_effort=profile.max_effort,
            trivia_history=trivia_history,
        ),
    )


@dataclass
class IncomeAccumulator:
    """Acumula ingresos y trivia history para simulación multi-día."""

    trivia_history: list[int] = field(default_factory=list)
    cumulative_by_source: dict[str, int] = field(default_factory=dict)
    balance: int = 0

    def record_day(self, income: DailyIncome) -> None:
        self.balance += income.total
        self.trivia_history.append(income.trivia)
        for key, val in income.as_dict().items():
            if key == "total":
                continue
            self.cumulative_by_source[key] = self.cumulative_by_source.get(key, 0) + val


def average_daily_income(samples: list[DailyIncome]) -> DailyIncome:
    if not samples:
        return DailyIncome()
    n = len(samples)
    return DailyIncome(
        daily_gift=sum(s.daily_gift for s in samples) // n,
        reaction=sum(s.reaction for s in samples) // n,
        mission_basic=sum(s.mission_basic for s in samples) // n,
        mission_streak=sum(s.mission_streak for s in samples) // n,
        mission_daily_extra=sum(s.mission_daily_extra for s in samples) // n,
        dice=sum(s.dice for s in samples) // n,
        trivia=sum(s.trivia for s in samples) // n,
    )