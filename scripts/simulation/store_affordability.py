"""Simulación día-a-día: cuántos días para alcanzar cada producto."""

from __future__ import annotations

from dataclasses import dataclass

from scripts.simulation.catalog import StoreProductSim
from scripts.simulation.constants import EconomyConfig
from scripts.simulation.income import (
    IncomeAccumulator,
    ProfileSpec,
    average_daily_income,
    simulate_day_income,
)


@dataclass
class AffordabilityResult:
    product: StoreProductSim
    days_to_afford: int | None
    balance_at_day: int | None


@dataclass
class ProfileSimulation:
    profile: ProfileSpec
    affordability: list[AffordabilityResult]
    sample_days: list
    avg_income: object
    final_balance: int
    days_simulated: int


def simulate_affordability(
    config: EconomyConfig,
    profile: ProfileSpec,
    products: list[StoreProductSim],
    *,
    horizon_days: int = 365,
) -> ProfileSimulation:
    acc = IncomeAccumulator()
    remaining = {p.name: p.price for p in products}
    affordability: dict[str, AffordabilityResult] = {
        p.name: AffordabilityResult(product=p, days_to_afford=None, balance_at_day=None)
        for p in products
    }
    sample_days = []

    for day in range(1, horizon_days + 1):
        income = simulate_day_income(config, profile, day_index=day, trivia_history=acc.trivia_history)
        acc.record_day(income)
        if day <= 14 or day % 7 == 0:
            sample_days.append((day, income))

        for name, price in list(remaining.items()):
            if acc.balance >= price:
                affordability[name] = AffordabilityResult(
                    product=next(p for p in products if p.name == name),
                    days_to_afford=day,
                    balance_at_day=acc.balance,
                )
                del remaining[name]

        if not remaining:
            break

    avg = average_daily_income(
        [simulate_day_income(config, profile, day_index=d, trivia_history=[]) for d in range(1, 8)]
    )
    # Recompute avg with proper rolling for first 7 days
    acc_avg = IncomeAccumulator()
    week_samples = []
    for day in range(1, 8):
        inc = simulate_day_income(
            config, profile, day_index=day, trivia_history=acc_avg.trivia_history
        )
        acc_avg.record_day(inc)
        week_samples.append(inc)
    avg = average_daily_income(week_samples)

    return ProfileSimulation(
        profile=profile,
        affordability=[affordability[p.name] for p in sorted(products, key=lambda x: x.price)],
        sample_days=sample_days,
        avg_income=avg,
        final_balance=acc.balance,
        days_simulated=horizon_days if remaining else day,
    )


def run_sanity_checks(results: dict[str, ProfileSimulation], products: list[StoreProductSim]) -> list[str]:
    """Validaciones rápidas; retorna lista de fallos (vacía = OK)."""
    failures: list[str] = []
    cheapest = min(p.price for p in products)
    priciest = max(p.price for p in products)

    for name, sim in results.items():
        avg = sim.avg_income
        if name.endswith("_max"):
            cap = 15 if sim.profile.is_vip else 10
            if avg.trivia > cap:
                failures.append(f"{name}: trivia promedio {avg.trivia} > cap {cap}")

        aff_map = {a.product.name: a.days_to_afford for a in sim.affordability}
        cheap_days = aff_map.get(
            next(p.name for p in products if p.price == cheapest)
        )
        if name.endswith("_max") and cheap_days is not None and cheap_days >= 7:
            failures.append(f"{name}: producto {cheapest} tarda {cheap_days}d (esperado <7)")

        if "realistic" in name:
            pricey_name = next(p.name for p in products if p.price == priciest)
            days = aff_map.get(pricey_name)
            if days is not None and days < 90:
                failures.append(
                    f"{name}: {pricey_name} en {days}d (realista esperado >90 o no alcanzable en horizon)"
                )

    return failures