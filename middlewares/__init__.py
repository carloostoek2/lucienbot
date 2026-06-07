"""Middlewares de Telegram para Lucien Bot."""
from middlewares.error_handler import ErrorHandlerMiddleware
from middlewares.rate_limiter import ThrottlingMiddleware, RateLimiterMiddleware
from middlewares.idempotency import (
    IdempotencyCache,
    IdempotencyMiddleware,  # gsd-mw-hardening phase 3
    idempotency_cache,
)

__all__ = [
    "ErrorHandlerMiddleware",
    "ThrottlingMiddleware",      # canonical name (gsd-mw-hardening phase 2+)
    "RateLimiterMiddleware",     # alias for transitional compatibility
    "IdempotencyCache",
    "IdempotencyMiddleware",     # gsd-mw-hardening phase 3 (uses the cache for cb dedup)
    "idempotency_cache",
]
