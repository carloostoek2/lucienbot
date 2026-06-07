"""
Internal Event Bus - PoC for cross-domain notifications (Item 1: besitos_awarded).

Conservative, tight implementation per PLAN:
- Async fan-out with asyncio.gather(..., return_exceptions=True) following the
  proven pattern in tests/unit/test_broadcast_service_reaction_flow.py (concurrent reaction safety).
- Errors in listeners are logged per-listener and swallowed; never propagate to emitter.
- Support for scheduling from sync call sites (credit_besitos is a sync def) via schedule_emit.
- Singleton getter for minimal diff / no injection in PoC.
- Completely removable: delete this file + its unit test; nothing else references yet (Fase 1 isolated).

Logging follows project convention: "módulo | acción | user_id | resultado" (user_id included from payload when present).
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

# Event name constant to avoid typos across emitter, registrars, and tests.
EVENT_BESITOS_AWARDED: str = "besitos_awarded"

# Type alias for listeners: async callables receiving a payload dict.
Listener = Callable[[dict[str, Any]], Awaitable[None]]


class InternalEventBus:
    """
    Minimal async pub/sub bus for internal cross-domain notifications.

    DESIRED CONTRACT (verified by unit tests):
    - register(event: str, listener: async def(payload: dict)) -> None
    - emit(event: str, payload: dict) -> None  (async; never raises to caller)
    - Uses asyncio.gather( *listeners, return_exceptions=True )
    - One failing listener: others still execute; awaiter of emit sees no exception; error is logged.
    - Unknown event or zero listeners: no-op (debug log).
    - Payload forwarded verbatim (dict).
    - Best-effort scheduling helper allows emit from sync contexts without blocking caller.
    - Tests MUST use fresh instances (bus = InternalEventBus()) for isolation; do not rely on get_event_bus() singleton in bus unit tests.

    This is a PoC. No persistence, no retry policies, no topics beyond string keys.
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[Listener]] = {}

    def register(self, event: str, listener: Listener) -> None:
        """
        Register an async listener for the given event name.
        Duplicates are tolerated for PoC simplicity (callers/tests using fresh instances control their lists).
        """
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(listener)
        lis_name = getattr(listener, "__name__", repr(listener))
        logger.debug(f"event_bus | register | event={event} | listener={lis_name}")

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        """
        Fan-out the event to all registered listeners concurrently.
        Never raises. Listener exceptions are per-listener logged and do not affect siblings or the emitter.
        Includes user_id in logs when present in payload (project logging convention).
        """
        listeners = self._listeners.get(event, [])
        n = len(listeners)
        if n == 0:
            logger.debug(f"event_bus | emit | event={event} | listeners=0 | result=noop")
            return

        # Extract user_id for contextual logging (payload is dict by contract)
        uid = payload.get("user_id") if isinstance(payload, dict) else None
        uid_part = f"user_id={uid} | " if uid is not None else ""

        try:
            coros = [listener(payload) for listener in listeners]
            results = await asyncio.gather(*coros, return_exceptions=True)
        except Exception as gather_err:  # Should not happen, but defensive
            logger.warning(
                f"event_bus | emit | {uid_part}event={event} | listeners={n} | gather_error={gather_err}"
            )
            return

        error_count = 0
        for i, res in enumerate(results):
            lis = listeners[i]
            lis_name = getattr(lis, "__name__", repr(lis))
            if isinstance(res, Exception):
                error_count += 1
                logger.warning(
                    f"event_bus | listener_error | {uid_part}event={event} | listener={lis_name} | error={res}"
                )
            else:
                logger.debug(
                    f"event_bus | listener_ok | {uid_part}event={event} | listener={lis_name}"
                )

        logger.info(
            f"event_bus | emit | {uid_part}event={event} | listeners={n} | errors={error_count}"
        )


# --- Singleton / module-level access (PoC, no DI to minimize surface in credit_besitos) ---

_bus: InternalEventBus | None = None


def get_event_bus() -> InternalEventBus:
    """
    Return the process-wide singleton bus.
    Used by emitters (besito_service in Fase 2) and registrars (bot.py + story in Fase 3).
    Not used by the bus's own unit tests (they instantiate directly for isolation).
    """
    global _bus
    if _bus is None:
        _bus = InternalEventBus()
    return _bus


def schedule_emit(coro: Awaitable[None]) -> None:
    """
    Fire-and-forget scheduler for an awaitable (intended: bus.emit(...)) callable from synchronous code.

    Why needed: credit_besitos (the emitter site) is a regular def (sync) that does its own commit.
    We want post-commit best-effort notification without turning credit async or blocking the caller.

    Behavior:
    - If there is a running loop: schedule via create_task (non-blocking for the credit path).
    - If no running loop (RuntimeError): log at debug and skip. This is acceptable for PoC
      (rare pure-sync contexts like certain scheduler jobs; critical credit paths are exercised under
      the app loop or test loops). We deliberately avoid asyncio.run here to prevent nested-loop or
      heavy side effects in the caller's thread.

    The scheduled coroutine internally runs the gather+return_exceptions, so the caller of schedule_emit
    never awaits and never sees listener errors.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        # No running event loop in this context.
        logger.debug("event_bus | schedule_emit | no running loop; skipping (best effort)")


# --- Test helper (explicit, not part of public API surface) ---


def _reset_event_bus_for_tests() -> None:
    """
    Reset the module singleton. Intended ONLY for test fixtures that need a clean global bus
    between tests when exercising real registration + emit through the getter.
    Prefer fresh InternalEventBus() instances in pure bus unit tests.
    """
    global _bus
    _bus = None
