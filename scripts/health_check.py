#!/usr/bin/env python
"""
Standalone health check CLI for Lucien Bot ops/monitoring (Item 11).

Reuses HealthService (read-only/best-effort checks) via get_service context
or direct instantiation for ops flexibility.

Usage:
    python -m scripts.health_check
    python -m scripts.health_check --json
    python -m scripts.health_check --verbose
    python -m scripts.health_check --json --verbose

Exit codes:
    0 if overall status is "healthy"
    1 otherwise (degraded/unhealthy/unknown)

Logs inside HealthService use user_id=0 (terminal/startup convention).

No new dependencies. Follows scripts/verify_env.py pattern for structure.
"""

import argparse
import json
import sys
from datetime import UTC, datetime

from services import HealthService, get_service
from utils.lucien_voice import LucienVoice


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lucien Bot health check (Item 11). Reuses HealthService."
    )
    parser.add_argument("--json", action="store_true", help="Output JSON only (machine readable)")
    parser.add_argument(
        "--verbose", action="store_true", help="Human/Lucien sections even in JSON mode (combined)"
    )
    args = parser.parse_args()

    # Direct for ops (no context lifecycle if caller manages); or use get_service for symmetry with bot.
    # Use get_service to exercise the same path as bot admin view.
    with get_service(HealthService) as svc:
        health = svc.get_overall_status()

    overall = health.get("status", "unknown")
    exit_code = 0 if overall == "healthy" else 1

    if args.json:
        if args.verbose:
            # Combined: JSON + Lucien human on stderr or as extra field
            print(json.dumps(health, indent=2, ensure_ascii=False))
            print(LucienVoice.system_health(health), file=sys.stderr)
        else:
            print(json.dumps(health, indent=2, ensure_ascii=False))
    else:
        # Human/Lucien output (default)
        try:
            print(LucienVoice.system_health(health))
        except Exception:
            # Fallback human if voice not available or error
            ts = health.get("timestamp", datetime.now(UTC).isoformat())
            print(f"Overall: {overall}")
            print(f"Timestamp: {ts}")
            for k, v in health.get("checks", {}).items():
                print(f"  {k}: {v}")

    # Log for traceability (user_id=0 for terminal)
    import logging

    logging.getLogger("health_check").info(
        f"health_check | cli | user_id=0 | status={overall} exit={exit_code}"
    )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())


# =============================================================================
# Item 11 / observability health / arch-enforcer
# Standalone, reuses HealthService exactly as bot/endpoint do.
# --json for platform/monitoring (exit code reflects overall).
# --verbose for combined human + machine when needed.
# Logs "health_check | cli | user_id=0 | ...".
# No new deps. chmod +x for direct ./scripts/health_check.py if preferred.
# =============================================================================
