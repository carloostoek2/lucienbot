"""
DEPRECATED SHIM - DO NOT USE FOR NEW CODE.

This module previously contained the ThrottlingMiddleware implementation.
The canonical, maintained implementation now lives in:

    middlewares.rate_limiter.ThrottlingMiddleware

This shim exists only for transitional backward-compatibility during
gsd-mw-hardening (phase 2). It will be removed in a future cleanup phase.

Any direct import from handlers.rate_limit_middleware will emit
DeprecationWarning.

gsd-mw-hardening: phase 2 - legacy rate_limit_middleware.py converted to shim.
Refer to middlewares/rate_limiter.py for the authoritative source.

Rate limiting config, Lucien voice message, aiolimiter, admin (Custodios) bypass,
per-user limiters + idle cleanup, and CQ support are all in the new location.
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
