"""Lógica de payout y caps de trivia (extraída de simulate_trivia_earnings.py)."""

from __future__ import annotations

import random
from dataclasses import dataclass

from scripts.simulation.constants import STREAK_MILESTONES, TRIVIA_ERA_AFTER, TRIVIA_ERA_BEFORE

# Re-export para compatibilidad con simulate_trivia_earnings
OLD = TRIVIA_ERA_BEFORE
NEW = TRIVIA_ERA_AFTER


@dataclass
class PlayResult:
    play: int
    streak: int
    desired: int
    awarded: int
    daily_earned: int
    weekly_earned: int
    capped: bool


def milestone_bonus(streak: int, is_vip: bool) -> int:
    if streak not in STREAK_MILESTONES:
        return 0
    base = STREAK_MILESTONES[streak]
    return base * 2 if is_vip else base


def desired_payout(
    game: str, streak: int, is_vip: bool, era: str = "after"
) -> tuple[int, int]:
    cfg = OLD if era == "before" else NEW
    if game == "trivia":
        base = cfg["trivia_base"]
    elif game == "trivia_vip":
        base = cfg["trivia_vip_base"]
    elif game == "trivia_simple":
        base = (
            cfg["trivia_simple_base_vip"]
            if is_vip
            else cfg["trivia_simple_base_free"]
        )
    else:
        raise ValueError(game)
    bonus = milestone_bonus(streak, is_vip)
    return base, bonus


def apply_cap(
    desired_base: int,
    desired_bonus: int,
    earned_daily: int,
    earned_weekly: int,
    daily_cap: int | None,
    weekly_cap: int | None,
) -> tuple[int, int]:
    if daily_cap is None or weekly_cap is None:
        return desired_base, desired_bonus
    total = desired_base + desired_bonus
    allowed = min(
        total,
        max(0, daily_cap - earned_daily),
        max(0, weekly_cap - earned_weekly),
    )
    awarded_base = min(desired_base, allowed)
    awarded_bonus = min(desired_bonus, max(0, allowed - awarded_base))
    return awarded_base, awarded_bonus


def _resolve_caps(is_vip: bool, era: str, cfg_override: dict | None) -> tuple[int | None, int | None]:
    cfg = OLD if era == "before" else (cfg_override or NEW)
    if era == "before":
        return None, None
    if cfg_override:
        daily = cfg["daily_cap_vip"] if is_vip else cfg["daily_cap_free"]
        weekly = cfg["weekly_cap_vip"] if is_vip else cfg["weekly_cap_free"]
        return daily, weekly
    daily = cfg["daily_cap_vip"] if is_vip else cfg["daily_cap_free"]
    weekly = cfg["weekly_cap_vip"] if is_vip else cfg["weekly_cap_free"]
    return daily, weekly


def _play_correct(*, accuracy: float, max_effort: bool) -> bool:
    if max_effort:
        return True
    if accuracy >= 1.0:
        return True
    return random.random() < accuracy


def simulate_session(
    *,
    game: str,
    max_plays: int,
    is_vip: bool,
    era: str = "after",
    all_correct: bool = True,
    accuracy: float = 1.0,
    weekly_start: int = 0,
    cfg_override: dict | None = None,
) -> list[PlayResult]:
    daily_cap, weekly_cap = _resolve_caps(is_vip, era, cfg_override)
    results: list[PlayResult] = []
    streak = 0
    earned_daily = 0
    earned_weekly = weekly_start

    for play in range(1, max_plays + 1):
        correct = _play_correct(accuracy=accuracy, max_effort=all_correct)
        if correct:
            streak += 1
            d_base, d_bonus = desired_payout(game, streak, is_vip, era)
            a_base, a_bonus = apply_cap(
                d_base, d_bonus, earned_daily, earned_weekly, daily_cap, weekly_cap
            )
            awarded = a_base + a_bonus
            earned_daily += awarded
            earned_weekly += awarded
            results.append(
                PlayResult(
                    play=play,
                    streak=streak,
                    desired=d_base + d_bonus,
                    awarded=awarded,
                    daily_earned=earned_daily,
                    weekly_earned=earned_weekly,
                    capped=awarded < d_base + d_bonus,
                )
            )
        else:
            streak = 0
            results.append(
                PlayResult(
                    play=play,
                    streak=0,
                    desired=0,
                    awarded=0,
                    daily_earned=earned_daily,
                    weekly_earned=earned_weekly,
                    capped=False,
                )
            )
    return results


def total_awarded(results: list[PlayResult]) -> int:
    return sum(r.awarded for r in results)


def simulate_full_day(
    is_vip: bool,
    era: str = "after",
    *,
    all_correct: bool = True,
    accuracy: float = 1.0,
    weekly_start: int = 0,
    play_limits: dict[str, int] | None = None,
    cfg_override: dict | None = None,
) -> dict:
    """Suma variantes de trivia en un día (caps compartidos en era 'after')."""
    limits = play_limits or (OLD["play_limits"] if era == "before" else NEW["play_limits"])
    games_plays: list[tuple[str, int]] = []
    if is_vip:
        games_plays = [
            ("trivia", limits["trivia_vip"]),
            ("trivia_vip", limits["trivia_vip_vip"]),
            ("trivia_simple", limits["trivia_simple_vip"]),
        ]
    else:
        games_plays = [
            ("trivia", limits["trivia_free"]),
            ("trivia_simple", limits["trivia_simple_free"]),
        ]

    daily_cap, weekly_cap = _resolve_caps(is_vip, era, cfg_override)
    all_results: dict[str, list[PlayResult]] = {}
    earned_daily = 0
    earned_weekly = weekly_start
    streaks: dict[str, int] = {g: 0 for g, _ in games_plays}

    for game, max_plays in games_plays:
        game_results: list[PlayResult] = []
        for play in range(1, max_plays + 1):
            correct = _play_correct(accuracy=accuracy, max_effort=all_correct)
            if correct:
                streaks[game] += 1
                d_base, d_bonus = desired_payout(game, streaks[game], is_vip, era)
                a_base, a_bonus = apply_cap(
                    d_base, d_bonus, earned_daily, earned_weekly, daily_cap, weekly_cap
                )
                awarded = a_base + a_bonus
                earned_daily += awarded
                earned_weekly += awarded
                game_results.append(
                    PlayResult(
                        play=play,
                        streak=streaks[game],
                        desired=d_base + d_bonus,
                        awarded=awarded,
                        daily_earned=earned_daily,
                        weekly_earned=earned_weekly,
                        capped=awarded < d_base + d_bonus,
                    )
                )
            else:
                streaks[game] = 0
                game_results.append(
                    PlayResult(
                        play=play,
                        streak=0,
                        desired=0,
                        awarded=0,
                        daily_earned=earned_daily,
                        weekly_earned=earned_weekly,
                        capped=False,
                    )
                )
        all_results[game] = game_results

    return {
        "games": all_results,
        "total": earned_daily,
        "capped_plays": sum(
            1 for gr in all_results.values() for r in gr if r.capped or r.awarded == 0
        ),
        "zero_payout_correct": sum(
            1
            for gr in all_results.values()
            for r in gr
            if r.awarded == 0 and r.streak > 0
        ),
    }


def rolling_weekly_start(trivia_daily_history: list[int]) -> int:
    """Besitos trivia en ventana rolling 7 días (días anteriores, sin hoy)."""
    return sum(trivia_daily_history[-7:])