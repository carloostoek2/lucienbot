"""
Unit tests for InternalEventBus (PoC Item 1).

Isolation rule (per PLAN): all tests instantiate `bus = InternalEventBus()` directly.
They do NOT use or pollute the get_event_bus() singleton.

Covers DoD:
- register multiple listeners for same event
- emit calls all registered for that event (others untouched)
- one listener raises: others still execute, emit await does not propagate, error logged
- payload forwarded intact
- unknown event is no-op
- zero listeners is no-op

Uses the exact gather+return_exceptions contract demonstrated in
tests/unit/test_broadcast_service_reaction_flow.py (concurrent safety).
"""

import logging
from unittest.mock import AsyncMock

import pytest

from services.event_bus import (
    EVENT_BESITOS_AWARDED,
    InternalEventBus,
    _reset_event_bus_for_tests,
    get_event_bus,
)


@pytest.mark.asyncio
async def test_register_multiple_and_emit_calls_all():
    """Register two listeners for the event; both are called with payload; unrelated event listener is not."""
    bus = InternalEventBus()
    listener1 = AsyncMock()
    listener2 = AsyncMock()
    unrelated = AsyncMock()

    bus.register(EVENT_BESITOS_AWARDED, listener1)
    bus.register(EVENT_BESITOS_AWARDED, listener2)
    bus.register("some_other_event", unrelated)

    payload = {"user_id": 777, "amount": 5, "source": "reaction"}
    await bus.emit(EVENT_BESITOS_AWARDED, payload)

    listener1.assert_awaited_once_with(payload)
    listener2.assert_awaited_once_with(payload)
    unrelated.assert_not_awaited()


@pytest.mark.asyncio
async def test_one_listener_fails_others_execute_no_exception_propagated(caplog):
    """
    One listener raises. The emit must:
    - still await the others to completion
    - NOT raise to the caller of emit
    - log the error for the failing listener (project wants per-listener logging)
    """
    bus = InternalEventBus()
    good = AsyncMock()
    bad = AsyncMock(side_effect=RuntimeError("listener boom"))

    bus.register(EVENT_BESITOS_AWARDED, good)
    bus.register(EVENT_BESITOS_AWARDED, bad)

    payload = {"user_id": 42, "amount": 10}

    # Must not raise
    await bus.emit(EVENT_BESITOS_AWARDED, payload)

    good.assert_awaited_once_with(payload)
    bad.assert_awaited_once_with(payload)

    # Error should have been logged (warning level per impl)
    assert any(
        "listener_error" in rec.message and "listener boom" in rec.message for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_payload_is_forwarded_intact():
    """Payload dict must arrive exactly as emitted (no mutation, no wrapping)."""
    bus = InternalEventBus()
    received = {}

    async def spy(p):
        received.update(p)

    bus.register(EVENT_BESITOS_AWARDED, spy)

    payload = {
        "user_id": 1234567890123,
        "amount": 42,
        "source": "daily_gift",
        "reference_id": 99,
        "description": "test",
        "timestamp": "2026-06-07T20:15:35+00:00",
    }
    await bus.emit(EVENT_BESITOS_AWARDED, payload)

    assert received == payload


@pytest.mark.asyncio
async def test_unknown_event_is_noop():
    """Emitting an event with no registrations must be a silent no-op (no listeners called)."""
    bus = InternalEventBus()
    listener = AsyncMock()
    bus.register(EVENT_BESITOS_AWARDED, listener)

    await bus.emit("definitely_not_registered", {"user_id": 1})

    listener.assert_not_awaited()


@pytest.mark.asyncio
async def test_emit_with_zero_listeners_is_noop():
    """Fresh bus with nothing registered: emit does not explode."""
    bus = InternalEventBus()
    # Should just debug-log and return
    await bus.emit(EVENT_BESITOS_AWARDED, {"user_id": 999})


@pytest.mark.asyncio
async def test_get_event_bus_singleton_is_separate_from_fresh_instances():
    """
    Sanity: the getter returns the module singleton.
    Unit tests for bus behavior use fresh instances; this just documents the boundary.
    We reset to keep test hermetic.
    """
    _reset_event_bus_for_tests()
    b1 = get_event_bus()
    b2 = get_event_bus()
    assert b1 is b2

    # A fresh one is a different object
    fresh = InternalEventBus()
    assert fresh is not b1

    _reset_event_bus_for_tests()


@pytest.mark.asyncio
async def test_narrative_listener_is_invoked_and_logs(caplog):
    """
    F3 verification: the real listener defined in the narrative domain
    (story_service.on_besitos_awarded_from_gamification) can be registered
    and is called when the event is emitted. We assert the expected log line
    (the contract for "narrative | besitos_awarded_received").
    This proves the wiring shape works (the same registration bot.py does).
    """
    from services.story_service import on_besitos_awarded_from_gamification

    bus = InternalEventBus()
    bus.register(EVENT_BESITOS_AWARDED, on_besitos_awarded_from_gamification)

    payload = {
        "user_id": 424242,
        "amount": 7,
        "source": "daily_gift",
        "reference_id": 123,
        "description": "test award",
        "timestamp": "2026-06-07T20:30:00+00:00",
    }

    with caplog.at_level(logging.INFO):
        await bus.emit(EVENT_BESITOS_AWARDED, payload)

    # The listener must have logged the exact project-format line
    found = any(
        "narrative | besitos_awarded_received" in rec.message
        and "user_id=424242" in rec.message
        and "amount=7" in rec.message
        and "source=daily_gift" in rec.message
        for rec in caplog.records
    )
    assert found, "narrative listener was not invoked or did not log as specified"


@pytest.mark.asyncio
async def test_broadcast_and_game_listeners_are_invoked_and_log_per_item6(caplog):
    """
    Item 6: explicit coverage for the new observational listeners (broadcast reaction award + game award)
    registered in bot.py (now 4 total). Mirrors narrative test exactly (fresh InternalEventBus + register +
    emit + caplog for domain log lines). Proves wiring shape + "MUST NOT credit" contract observability
    (no mutation asserted in credit-path golds + story precedent). Best effort, errors swallowed.
    """
    from services.broadcast_service import on_besitos_awarded_broadcast_reaction_observer
    from services.game_service import on_besitos_awarded_game_award_observer

    bus = InternalEventBus()
    bus.register(EVENT_BESITOS_AWARDED, on_besitos_awarded_broadcast_reaction_observer)
    bus.register(EVENT_BESITOS_AWARDED, on_besitos_awarded_game_award_observer)

    payload = {
        "user_id": 424243,
        "amount": 2,
        "source": "reaction",
        "reference_id": 99,
        "description": "test broadcast/game award",
        "timestamp": "2026-06-07T20:31:00+00:00",
    }

    with caplog.at_level(logging.INFO):
        await bus.emit(EVENT_BESITOS_AWARDED, payload)

    found_broadcast = any(
        "broadcast | besitos_awarded_received" in rec.message and "user_id=424243" in rec.message
        for rec in caplog.records
    )
    found_game = any(
        "game | besitos_awarded_received" in rec.message and "user_id=424243" in rec.message
        for rec in caplog.records
    )
    assert found_broadcast, "broadcast reaction observer (Item 6) not invoked or did not log"
    assert found_game, "game award observer (Item 6) not invoked or did not log"
    # contract: these are best-effort obs only (credit paths + atomicity golds assert no impact)


@pytest.mark.asyncio
async def test_vip_activated_listener_is_invoked_and_logs(caplog):
    """R3 gold extension: nurture on_vip_activated (vip_activated + exact caplog, best-effort swallow).
    Mirrors narrative/broadcast/game listener tests exactly (fresh bus, register, emit, caplog for "nurture_service | on_vip_activated").
    """
    from services.nurture_service import on_vip_activated
    from services.event_bus import EVENT_VIP_ACTIVATED

    _reset_event_bus_for_tests()
    bus = InternalEventBus()
    bus.register(EVENT_VIP_ACTIVATED, on_vip_activated)

    payload = {"user_id": 424244, "subscription_id": 99}

    with caplog.at_level(logging.INFO):
        await bus.emit(EVENT_VIP_ACTIVATED, payload)

    found = any(
        "nurture_service | on_vip_activated" in rec.message and "user_id=424244" in rec.message
        for rec in caplog.records
    )
    assert found, "nurture vip_activated listener was not invoked or did not log as specified (R3)"
    # best-effort: errors swallowed (no exception to caller, logged per listener) -- covered by gold pattern


@pytest.mark.asyncio
async def test_streak_promotion_listener_is_invoked_and_logs_per_item3_35(caplog):
    """
    Item 3/35: explicit coverage for new streak promotion observational listener (added F2).
    Mirrors narrative/broadcast/game listener tests exactly (fresh InternalEventBus + register +
    emit + caplog for domain log "streak | besitos_awarded_received"). Proves wiring + "MUST NOT credit"
    contract observability (no mutation asserted in credit golds). Best effort, errors swallowed.
    Port hygiene: import inside per conv.
    """
    from services.streak_promotion_service import on_besitos_awarded_streak_promotion_observer
    from services.event_bus import EVENT_BESITOS_AWARDED, InternalEventBus

    bus = InternalEventBus()
    bus.register(EVENT_BESITOS_AWARDED, on_besitos_awarded_streak_promotion_observer)

    payload = {
        "user_id": 424245,
        "amount": 3,
        "source": "trivia",
        "reference_id": 77,
        "description": "test streak promo award",
        "timestamp": "2026-06-26T12:00:00+00:00",
    }

    with caplog.at_level(logging.INFO):
        await bus.emit(EVENT_BESITOS_AWARDED, payload)

    found = any(
        "streak | besitos_awarded_received" in rec.message and "user_id=424245" in rec.message
        and "amount=3" in rec.message and "source=trivia" in rec.message
        for rec in caplog.records
    )
    assert found, "streak promotion observer (Item 3/35) not invoked or did not log per contract"
    # contract: obs only (0 impact on gamif credits/atomicity golds/protection debits)
