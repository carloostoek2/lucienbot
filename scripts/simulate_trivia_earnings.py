#!/usr/bin/env python3
"""
Simulación comparativa: sistema de trivia ANTES vs DESPUÉS del commit 93f7c04
([FEATURE] nuevos límites de ganador — 2026-06-17).

Reproduce la lógica de payout (base + bonus de racha) y caps nuevos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

STREAK_MILESTONES = {3: 2, 5: 5, 7: 10, 10: 20}

# --- Constantes ANTES (pre-93f7c04) ---
OLD = {
    "trivia_base": 1,
    "trivia_vip_base": 5,
    "trivia_simple_base_free": 2,
    "trivia_simple_base_vip": 4,
    "daily_cap": None,
    "weekly_cap": None,
    "play_limits": {
        "trivia_free": 5,
        "trivia_vip": 5,
        "trivia_simple_free": 5,
        "trivia_vip_only": True,
        "trivia_vip_free": 0,
        "trivia_vip_vip": 5,
        "trivia_free_vip": 10,
        "trivia_simple_vip": 10,
    },
}

# --- Constantes DESPUÉS (actual) ---
NEW = {
    "trivia_base": 1,
    "trivia_vip_base": 2,
    "trivia_simple_base_free": 1,
    "trivia_simple_base_vip": 2,
    "daily_cap_free": 10,
    "daily_cap_vip": 15,
    "weekly_cap_free": 30,
    "weekly_cap_vip": 40,
    "play_limits": OLD["play_limits"].copy(),
}


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
    game: str, streak: int, is_vip: bool, era: str
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


def simulate_session(
    *,
    game: str,
    max_plays: int,
    is_vip: bool,
    era: str,
    all_correct: bool = True,
    weekly_start: int = 0,
) -> list[PlayResult]:
    cfg = OLD if era == "before" else NEW
    daily_cap = None
    weekly_cap = None
    if era == "after":
        daily_cap = cfg["daily_cap_vip"] if is_vip else cfg["daily_cap_free"]
        weekly_cap = cfg["weekly_cap_vip"] if is_vip else cfg["weekly_cap_free"]

    results: list[PlayResult] = []
    streak = 0
    earned_daily = 0
    earned_weekly = weekly_start

    for play in range(1, max_plays + 1):
        if all_correct:
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


def simulate_full_day(is_vip: bool, era: str) -> dict:
    """Suma las 3 variantes de trivia en un día (caps compartidos en era 'after')."""
    limits = OLD["play_limits"] if era == "before" else NEW["play_limits"]
    games_plays = []
    if is_vip:
        games_plays = [
            ("trivia", limits["trivia_free_vip"]),
            ("trivia_vip", limits["trivia_vip_vip"]),
            ("trivia_simple", limits["trivia_simple_vip"]),
        ]
    else:
        games_plays = [
            ("trivia", limits["trivia_free"]),
            ("trivia_simple", limits["trivia_simple_free"]),
        ]

    cfg = OLD if era == "before" else NEW
    daily_cap = None
    weekly_cap = None
    if era == "after":
        daily_cap = cfg["daily_cap_vip"] if is_vip else cfg["daily_cap_free"]
        weekly_cap = cfg["weekly_cap_vip"] if is_vip else cfg["weekly_cap_free"]

    all_results: dict[str, list[PlayResult]] = {}
    earned_daily = 0
    earned_weekly = 0
    streaks: dict[str, int] = {g: 0 for g, _ in games_plays}

    for game, max_plays in games_plays:
        game_results: list[PlayResult] = []
        for play in range(1, max_plays + 1):
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
        all_results[game] = game_results

    return {
        "games": all_results,
        "total": earned_daily,
        "capped_plays": sum(
            1 for gr in all_results.values() for r in gr if r.capped or r.awarded == 0
        ),
        "zero_payout_correct": sum(
            1 for gr in all_results.values() for r in gr if r.awarded == 0 and r.streak > 0
        ),
    }


def print_comparison_table():
    print("=" * 72)
    print("SIMULACIÓN TRIVIA: ANTES vs DESPUÉS (commit 93f7c04, 2026-06-17)")
    print("=" * 72)

    print("\n--- Cambios estructurales en el commit ---")
    changes = [
        ("TRIVIA_VIP_WIN_BESITOS", "5 → 2", "-60% base por victoria VIP"),
        ("TRIVIA_SIMPLE_WIN (free)", "2 → 1", "-50% base"),
        ("TRIVIA_SIMPLE_WIN (VIP)", "4 → 2", "-50% base"),
        ("TRIVIA_WIN_BESITOS", "1 → 1", "sin cambio"),
        ("Caps diarios besitos trivia", "∞ → 10 free / 15 VIP", "NUEVO"),
        ("Caps semanales besitos trivia", "∞ → 30 free / 40 VIP", "NUEVO"),
        ("Límites de jugadas/día", "sin cambio", "5/10 free/VIP + 5 VIP-excl"),
    ]
    for name, delta, note in changes:
        print(f"  {name:32} {delta:22} {note}")

    print("\n--- Escenario A: Trivia general, 10 respuestas correctas seguidas (VIP) ---")
    for era in ("before", "after"):
        res = simulate_session(game="trivia", max_plays=10, is_vip=True, era=era)
        print(f"\n  [{era.upper()}] total={total_awarded(res)} besitos")
        for r in res:
            flag = " ⚠️ CAP" if r.capped else ""
            print(
                f"    jugada {r.play:2d} | racha {r.streak:2d} | "
                f"deseado {r.desired:3d} | otorgado {r.awarded:3d}{flag}"
            )

    print("\n--- Escenario B: Día completo VIP (todas las trivias, todo correcto) ---")
    before = simulate_full_day(is_vip=True, era="before")
    after = simulate_full_day(is_vip=True, era="after")
    print(f"  ANTES:  {before['total']} besitos (sin tope)")
    print(f"  DESPUÉS: {after['total']} besitos (cap diario 15)")
    print(
        f"  Reducción: {before['total'] - after['total']} besitos "
        f"({100 * (1 - after['total'] / before['total']):.1f}%)"
    )
    print(f"  Jugadas con payout 0 bajo cap: {after['zero_payout_correct']}")

    print("\n--- Escenario C: Día completo FREE (trivia + simple, todo correcto) ---")
    before_f = simulate_full_day(is_vip=False, era="before")
    after_f = simulate_full_day(is_vip=False, era="after")
    print(f"  ANTES:  {before_f['total']} besitos")
    print(f"  DESPUÉS: {after_f['total']} besitos (cap diario 10)")
    print(
        f"  Reducción: {before_f['total'] - after_f['total']} besitos "
        f"({100 * (1 - after_f['total'] / before_f['total']):.1f}%)"
    )

    print("\n--- Escenario D: Solo Trivia VIP, 5 correctas (VIP) ---")
    for era in ("before", "after"):
        res = simulate_session(game="trivia_vip", max_plays=5, is_vip=True, era=era)
        print(f"  [{era.upper()}] total={total_awarded(res)} (bases: 5→2 en commit)")

    print("\n--- Escenario E: Racha 10 en trivia general (1 sola sesión) ---")
    for era, vip in (("before", True), ("after", True), ("before", False), ("after", False)):
        res = simulate_session(game="trivia", max_plays=10, is_vip=vip, era=era)
        print(f"  [{era.upper()} VIP={vip}] total 10 jugadas = {total_awarded(res)} besitos")

    print("\n--- Escenario F: Semana rolling (VIP, 7 días idénticos trivia general x10) ---")
    weekly_before = 0
    weekly_after = 0
    for day in range(7):
        b = simulate_session(game="trivia", max_plays=10, is_vip=True, era="before")
        weekly_before += total_awarded(b)
        # weekly cap compartido: acumular earned_weekly entre días
        a = simulate_session(
            game="trivia",
            max_plays=10,
            is_vip=True,
            era="after",
            weekly_start=weekly_after,
        )
        daily = total_awarded(a)
        weekly_after += daily
        # cap semanal 40: después del día que lo llena, siguientes días = 0
    print(f"  ANTES (7×10 correctas): {weekly_before} besitos/semana (sin tope)")
    print(f"  DESPUÉS (7×10 correctas): {weekly_after} besitos/semana (tope 40)")

    print("\n--- Desglose por juego (día VIP completo) ---")
    for era, data in (("ANTES", before), ("DESPUÉS", after)):
        print(f"  {era}:")
        for game, results in data["games"].items():
            t = total_awarded(results)
            print(f"    {game:14} → {t:3d} besitos ({len(results)} jugadas)")


if __name__ == "__main__":
    print_comparison_table()