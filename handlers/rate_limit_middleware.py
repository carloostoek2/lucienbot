"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
DEPRECATED SHIM - DO NOT IMPORT OR USE IN NEW CODE OR TESTS (except transitional).
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

This module previously contained the ThrottlingMiddleware implementation.
THE CANONICAL, MAINTAINED, TESTED IMPLEMENTATION NOW LIVES IN:

    from middlewares.rate_limiter import ThrottlingMiddleware  # canonical
    # (also exports RateLimiterMiddleware as alias during transition)

This shim exists **only** for transitional backward-compatibility during
gsd-mw-hardening (phases 2-6). It **will be removed** in a future cleanup.

IMPORTING THIS MODULE EMITS DeprecationWarning AT IMPORT TIME.

gsd-mw-hardening: phase 2 - converted to shim + strong header.
Phase 6 - docs + final verification completed.

Refer to:
- middlewares/rate_limiter.py (full mature logic + tests)
- middlewares/idempotency.py (IdempotencyMiddleware + cache)
- bot.py (wiring order)
- handlers/CLAUDE.md and decisions.md (updated)

Everything (config, Lucien voice exact string, aiolimiter, Custodios bypass using
real rate_limit_config + bot_config.ADMIN_IDS, cleanup, logging, CQ support via
event_from_user, robustness) is in the middlewares/ canonical files.

DO NOT ADD NEW LOGIC HERE. DO NOT RELY ON THIS PATH.
"""
import warnings

# Re-export the canonical implementation (and the alias)
from middlewares.rate_limiter import (
    ThrottlingMiddleware,
    RateLimiterMiddleware,
    _LIMITER_TTL,
)

warnings.warn(
    "handlers.rate_limit_middleware is DEPRECATED. "
    "Import 'ThrottlingMiddleware' (canonical) from 'middlewares.rate_limiter' instead. "
    "This shim will be removed after gsd-mw-hardening cleanup.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ThrottlingMiddleware", "RateLimiterMiddleware", "_LIMITER_TTL"]
