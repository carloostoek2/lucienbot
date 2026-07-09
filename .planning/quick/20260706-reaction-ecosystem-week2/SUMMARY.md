# SUMMARY: Reaction Ecosystem Week 2

**Item:** `reaction-ecosystem-week2`  
**Date:** 2026-07-06  
**Scope:** Tests + docs + decisions only — **0 production code changes**, **0 behavior change**

---

## Completed Tasks

### Task 1 — Markup parity golden tests
- Added `_markup_structure()` helper and 4 parity tests to `tests/unit/test_broadcast_channel_markup.py`
- Locks send vs refresh structure (callbacks, row order, extra URL); text parity at zero counts; text differs only when N>0
- **Gate:** 15 passed

### Task 2 — `message_id=0` → `message_mismatch`
- Added `test_message_mismatch_when_broadcast_stuck_at_message_id_zero` in `TestCheckAndRegisterReaction`
- Documents `tracking_failed` persistence path; asserts no `BroadcastReaction` row created
- **Gate:** 3 message_mismatch tests passed; 28 total in reaction_flow

### Task 3 — Migrate `test_reaction_full_chain.py`
- Replaced manual `check_and_register_reaction` + `reactions_keyboard_with_counts` mirror with `process_channel_reaction`
- Both integration tests migrated (Option A); removed deprecated keyboard import
- **Gate:** 2 passed

### Task 4 — Rewrite `services/broadcast/CLAUDE.md`
- Documented production paths: `process_channel_reaction`, `check_and_register_reaction`
- Added return dict contract, validators, markup, message ID tracking, atomicity notes
- Marked `register_reaction` as DEPRECATED legacy sync

### Task 5 — `decisions.md` DEFER entry
- Appended `credit_besitos(commit=False)` deferral with atomicity gold blast-radius rationale

---

## Gold Test Results (mandated flags)

| Suite | Result |
|-------|--------|
| `test_broadcast_channel_markup.py` | 15 passed |
| `test_broadcast_service_reaction_flow.py` | 28 passed |
| `test_reaction_full_chain.py` | 2 passed |
| `test_cross_service_atomicity.py` | 10 passed |
| `test_invariants.py -k reaction` | 1 passed |
| `test_reaction_mission_flow.py` | 4 passed |
| `test_reaction_limit.py` | 3 passed |
| `test_gamification_user_handlers.py -k reaction` | 23 passed |
| `test_callbackdata_broadcast.py` | 31 passed |
| Broader smoke (`-k reaction or ...`) | 106 passed |

---

## Files Touched (Week 2 only)

| File | Action |
|------|--------|
| `tests/unit/test_broadcast_channel_markup.py` | EDIT (+4 parity tests) |
| `tests/unit/test_broadcast_service_reaction_flow.py` | EDIT (+1 test) |
| `tests/integration/test_reaction_full_chain.py` | EDIT (migrate to `process_channel_reaction`) |
| `services/broadcast/CLAUDE.md` | EDIT (rewrite reaction docs) |
| `decisions.md` | EDIT (DEFER entry) |
| `.planning/quick/gsd-reaction-ecosystem-week2.log` | LOG |

**Production paths NOT modified:** `broadcast_service.py`, `besito_service.py`, handlers, keyboards, validators.

---

## Handoff

Ready for **arch-enforcer** + **test-guardian**. GSD log: `SELF_CHECK PASSED`.