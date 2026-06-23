#!/usr/bin/env python3
"""
Simulación integral de economía de besitos — límites actuales + catálogo Kinky.

Modela ingresos por: regalo diario, reacciones, misiones, dados y trivia (con caps
diarios/semanales). Calcula días para comprar cada producto del catálogo (50–5,000 💋).

Uso:
    python scripts/simulate_gamification_economy.py
    python scripts/simulate_gamification_economy.py --csv /tmp/economy.csv
    python scripts/simulate_gamification_economy.py --from-db
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.simulation.catalog import (
    TIER_LABELS,
    TIER_ORDER,
    get_catalog_products,
    load_products_from_db,
)
from scripts.simulation.constants import (
    DICE_WIN_PROBABILITY,
    PROFILE_NAMES,
    EconomyConfig,
)
from scripts.simulation.db_loader import load_economy_config_from_db
from scripts.simulation.income import resolve_profile
from scripts.simulation.store_affordability import run_sanity_checks, simulate_affordability
from scripts.simulation.trivia_caps import simulate_full_day


def print_header(title: str) -> None:
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_gaps_and_assumptions(config: EconomyConfig) -> None:
    print("\n--- Notas y gaps (conf_gam.md vs código) ---")
    notes = [
        "Límite 2 reacciones/día en conf_gam.md NO está en BroadcastService; "
        f"se simula {config.posts_per_day} post(s)/día = {config.posts_per_day} reacción(es).",
        "Caps semanales trivia son rolling 7 días — el loop día-a-día es obligatorio.",
        "Catálogo: 22 productos seed_catalog (no packs legacy 80/150/300).",
        "Fuentes excluidas: ADMIN, anon VIP, narrativa, streak protection.",
        "Misiones DAILY_GIFT_* solo si --include-daily-missions.",
    ]
    for note in notes:
        print(f"  • {note}")


def print_constants(config: EconomyConfig) -> None:
    print("\n--- Constantes de simulación ---")
    caps = config.trivia_caps
    print(f"  Regalo diario:        {config.daily_gift} 💋/día")
    print(f"  Reacción:             {config.reaction_value} 💋 × {config.posts_per_day} post/día")
    print(f"  Misión básica:        +{config.mission_basic_reward} 💋 por reacción")
    print(
        f"  Misión racha:         +{config.mission_streak_reward} 💋 "
        f"cada {config.mission_streak_target} posts"
    )
    print(f"  Dados:                {config.dice_limit_free}/{config.dice_limit_vip} jugadas "
          f"(FREE/VIP), P(win)≈{DICE_WIN_PROBABILITY:.1%}, +{config.dice_win_besitos} 💋")
    print(
        f"  Trivia caps:          {caps['daily_cap_free']}/{caps['daily_cap_vip']} diario, "
        f"{caps['weekly_cap_free']}/{caps['weekly_cap_vip']} semanal (FREE/VIP)"
    )
    print(f"  Trivia accuracy (realista): {config.trivia_accuracy:.0%}")


def print_trivia_validation() -> None:
    print("\n--- Validación caps trivia (máximo esfuerzo, día 1) ---")
    for is_vip, label in ((False, "FREE"), (True, "VIP")):
        after = simulate_full_day(is_vip, era="after", all_correct=True)
        cap = 15 if is_vip else 10
        print(f"  {label}: {after['total']} 💋 (cap diario {cap})")


def print_income_table(results: dict) -> None:
    print("\n--- Ingreso diario promedio (primeros 7 días, con rolling semanal) ---")
    headers = ["Perfil", "Daily", "React", "Misión", "Dados", "Trivia", "TOTAL"]
    print("  " + " | ".join(f"{h:>8}" for h in headers))
    print("  " + "-" * 72)
    for name, sim in results.items():
        avg = sim.avg_income
        print(
            f"  {name:18} | {avg.daily_gift:8} | {avg.reaction:7} | "
            f"{avg.missions:7} | {avg.dice:7} | {avg.trivia:7} | {avg.total:8}"
        )
        if avg.total:
            pct = lambda v: 100 * v / avg.total
            print(
                f"  {'':18}   "
                f"({pct(avg.daily_gift):.0f}% / {pct(avg.reaction):.0f}% / "
                f"{pct(avg.missions):.0f}% / {pct(avg.dice):.0f}% / {pct(avg.trivia):.0f}%)"
            )


def print_affordability_matrix(results: dict, products: list) -> None:
    print("\n--- Días para alcanzar cada producto (por precio ascendente) ---")
    profile_names = list(results.keys())
    header = f"  {'Producto':<28} {'Tier':<10} {'Precio':>6}"
    for pn in profile_names:
        header += f" {pn:>16}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    by_tier: dict[str, list] = {t: [] for t in TIER_ORDER}
    for p in sorted(products, key=lambda x: x.price):
        by_tier.setdefault(p.tier_slug, []).append(p)

    for tier in TIER_ORDER:
        tier_products = by_tier.get(tier, [])
        if not tier_products:
            continue
        print(f"\n  {TIER_LABELS.get(tier, tier)}")
        for product in tier_products:
            row = f"  {product.name:<28} {product.tier_slug:<10} {product.price:>6}"
            for pn in profile_names:
                aff = next(
                    a for a in results[pn].affordability if a.product.name == product.name
                )
                if aff.days_to_afford is None:
                    cell = ">horizon"
                else:
                    weeks = aff.days_to_afford / 7
                    cell = f"{aff.days_to_afford}d (~{weeks:.1f}sem)"
                row += f" {cell:>16}"
            print(row)


def print_insights(results: dict, products: list) -> None:
    print("\n--- Insights ---")
    cheapest = min(products, key=lambda p: p.price)
    priciest = max(products, key=lambda p: p.price)
    for name, sim in results.items():
        aff = {a.product.name: a.days_to_afford for a in sim.affordability}
        d_cheap = aff.get(cheapest.name)
        d_pricey = aff.get(priciest.name)
        cheap_txt = f"{d_cheap} días" if d_cheap else "no alcanza en horizon"
        pricey_txt = f"{d_pricey} días (~{d_pricey / 30:.1f} meses)" if d_pricey else "no alcanza en horizon"
        print(
            f"  {name}: ~{sim.avg_income.total} 💋/día promedio (sem 1) → "
            f"{cheapest.name} ({cheapest.price}) en {cheap_txt}; "
            f"{priciest.name} ({priciest.price}) en {pricey_txt}"
        )


def write_csv(path: str, results: dict, products: list) -> None:
    profile_names = list(results.keys())
    fieldnames = ["product", "tier", "price"] + profile_names
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for product in sorted(products, key=lambda x: x.price):
            row = {
                "product": product.name,
                "tier": product.tier_slug,
                "price": product.price,
            }
            for pn in profile_names:
                aff = next(
                    a for a in results[pn].affordability if a.product.name == product.name
                )
                row[pn] = aff.days_to_afford if aff.days_to_afford is not None else ""
            writer.writerow(row)
    print(f"\nCSV escrito: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulación de economía de besitos")
    parser.add_argument(
        "--profiles",
        default=",".join(PROFILE_NAMES),
        help=f"Perfiles separados por coma (default: todos). Opciones: {PROFILE_NAMES}",
    )
    parser.add_argument("--posts-per-day", type=int, default=1)
    parser.add_argument("--reaction-value", type=int, default=None)
    parser.add_argument("--daily-gift", type=int, default=None)
    parser.add_argument("--trivia-accuracy", type=float, default=0.6)
    parser.add_argument("--include-daily-missions", action="store_true")
    parser.add_argument("--horizon-days", type=int, default=365)
    parser.add_argument("--from-db", action="store_true", help="Leer config y catálogo de BD")
    parser.add_argument("--csv", metavar="PATH", help="Exportar matriz días-a-comprar a CSV")
    parser.add_argument("--seed", type=int, default=42, help="Semilla RNG para perfil realista")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    import random

    random.seed(args.seed)

    config = load_economy_config_from_db() if args.from_db else EconomyConfig()
    if args.posts_per_day:
        config.posts_per_day = args.posts_per_day
    if args.reaction_value is not None:
        config.reaction_value = args.reaction_value
    if args.daily_gift is not None:
        config.daily_gift = args.daily_gift
    config.trivia_accuracy = args.trivia_accuracy
    config.include_daily_missions = args.include_daily_missions

    products = load_products_from_db() if args.from_db else get_catalog_products()
    profile_list = [p.strip() for p in args.profiles.split(",") if p.strip()]

    print_header("SIMULACIÓN ECONOMÍA BESITOS — Catálogo Kinky + límites actuales")
    source = "BD (--from-db)" if args.from_db else "constantes + seed_catalog"
    print(f"  Fuente config/catálogo: {source}")
    print(f"  Perfiles: {', '.join(profile_list)}")
    print(f"  Horizonte: {args.horizon_days} días")

    print_gaps_and_assumptions(config)
    print_constants(config)
    print_trivia_validation()

    results = {}
    for pname in profile_list:
        profile = resolve_profile(pname)
        results[pname] = simulate_affordability(
            config, profile, products, horizon_days=args.horizon_days
        )

    print_income_table(results)
    print_affordability_matrix(results, products)
    print_insights(results, products)

    failures = run_sanity_checks(results, products)
    if failures:
        print("\n--- Sanity checks: ADVERTENCIAS ---")
        for f in failures:
            print(f"  ⚠ {f}")
    else:
        print("\n--- Sanity checks: OK ---")

    if args.csv:
        write_csv(args.csv, results, products)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())