"""
Minimal health HTTP endpoint for Lucien Bot (Item 11).

/health JSON for Railway/curl/monitoring. Lightweight, best-effort.
Uses aiohttp if available and HEALTH_ENABLED=1 (separate port to not conflict aiogram polling).
Graceful skip (log warning) if no aiohttp or flag off; 0 breakage to bot loop.

Handler reuses HealthService via get_service exactly (1 svc inside).
Non-blocking start via asyncio.create_task in bot.py on_startup (after scheduler/listeners).

See PLAN F3 + impact design for /health shape + wiring.
"""

import logging
import os

logger = logging.getLogger(__name__)

# Lazy import to avoid hard dep at bot startup
_web = None
_runner = None  # for optional shutdown


async def _get_web():
    global _web
    if _web is None:
        try:
            from aiohttp import web as aio_web  # type: ignore

            _web = aio_web
        except Exception:
            _web = False  # sentinel: unavailable
    return _web if _web is not False else None


async def health_handler(request):
    """Return overall health JSON. Best-effort, uses get_service(HealthService)."""
    from services import HealthService, get_service  # late import, after bot/services ready

    with get_service(HealthService) as svc:
        data = svc.get_overall_status()
    # web is guaranteed non-None here (checked in starter)
    return _web.json_response(data)


async def start_health_http_server(port: int = 8080) -> None:
    """
    Start /health on separate port (non-blocking). Call via asyncio.create_task.
    Skips gracefully if aiohttp missing or HEALTH_ENABLED != "1".
    """
    if os.getenv("HEALTH_ENABLED") != "1":
        logger.info("health_service | startup_endpoint | user_id=0 | result=disabled_flag")
        return

    web = await _get_web()
    if web is None:
        logger.warning("health_service | startup_endpoint | user_id=0 | result=disabled_no_aiohttp")
        return

    global _runner
    app = web.Application()
    app.router.add_get("/health", health_handler)
    _runner = web.AppRunner(app)
    await _runner.setup()
    site = web.TCPSite(_runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"health_service | startup_endpoint | user_id=0 | result=started port={port}")


async def stop_health_http_server() -> None:
    """Optional stop (call from on_shutdown if runner exists)."""
    global _runner
    if _runner:
        await _runner.cleanup()
        _runner = None
        logger.info("health_service | shutdown_endpoint | user_id=0 | result=stopped")


# =============================================================================
# Item 11 / observability health / arch-enforcer
# Endpoint is optional (HEALTH_ENABLED=1 + aiohttp present). Separate port.
# Handler uses exactly get_service(HealthService) + returns JSON (no secrets).
# Started fire-and-forget after scheduler/listeners in bot.py (F3 wiring).
# 0 impact on polling or critical flows.
# =============================================================================
