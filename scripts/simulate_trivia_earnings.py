#!/usr/bin/env python3
"""
Simulación comparativa: sistema de trivia ANTES vs DESPUÉS del commit 93f7c04
([FEATURE] nuevos límites de ganador — 2026-06-17).

Reproduce la lógica de payout (base + bonus de racha) y caps nuevos.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.simulation.trivia_caps import (
    NEW,
    OLD,
    PlayResult,
    apply_cap,
    desired_payout,
    milestone_bonus,
    simulate_full_day,
    simulate_session,
    total_awarded,
)

# Re-export para compatibilidad
STREAK_MILESTONES = __import__(
    "scripts.simulation.constants", fromlist=["STREAK_MILESTONES"]
).STREAK_MILESTONES

__all__ = [
    "STREAK_MILESTONES",
    "OLD",
    "NEW",
    "PlayResult",
    "milestone_bonus",
    "desired_payout",
    "apply_cap",
    "simulate_session",
    "total_awarded",
    "simulate_full_day",
    "print_comparison_table",
]


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
        a = simulate_session(
            game="trivia",
            max_plays=10,
            is_vip=True,
            era="after",
            weekly_start=weekly_after,
        )
        daily = total_awarded(a)
        weekly_after += daily
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