# PLAN: Reaction Ecosystem Week 3 — Opción A (tight)

**Item:** `reaction-ecosystem-week3-tight`  
**Date:** 2026-07-06  
**Source:** impact report `reaction-ecosystem-week3-benefit-risk.md` — Opción A  
**Scope:** 0 prod code, 0 atomicity change

## Objective

Close admin→reaction E2E gap: test `tracking_failed` path in broadcast wizard.

## Tasks

### Task 1: Handler test `tracking_failed`
**Files:** `tests/handlers/test_broadcast_handlers.py`

Add `test_tracking_failed_shows_alert_without_success_notify`:
- `update_broadcast_message_id` returns `False`
- `send_message` succeeds with `message_id=888`
- Assert alert: "registrar el ID" / "reacciones podrían fallar"
- Assert `notify_broadcast_send_success` NOT invoked (no edit_text "exitosamente")
- Assert `state.clear()` called

### Task 2: Pure helper test `publish_broadcast_to_channel`
**Files:** `tests/handlers/test_broadcast_handlers.py`

Add `test_publish_returns_tracking_failed_when_message_id_update_fails`:
- Import `publish_broadcast_to_channel` directly
- Mock send success + `update_broadcast_message_id` False
- Assert `("tracking_failed", sent_id)`

## NOT in scope
- 3B refactor check_and_register_reaction (deferred)
- 3D atomicity
- 3E prod fix

## Test gate
```bash
python -m pytest tests/handlers/test_broadcast_handlers.py -q --tb=line -p no:cov --override-ini="addopts="
python -m pytest -k "reaction or TestConfirmAndSendBroadcast or TestPublishBroadcast" -q --tb=line -p no:cov --override-ini="addopts="
```

## GSD log
`.planning/quick/gsd-reaction-ecosystem-week3-tight.log`