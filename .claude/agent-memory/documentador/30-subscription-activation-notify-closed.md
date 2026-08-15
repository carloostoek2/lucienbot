---
name: 30-subscription-activation-notify-closed
description: Feature pool close (2026-08-15): VIP activation DM notify to Custodios — success (reuse EVENT_VIP_ACTIVATED) + failure (new EVENT_VIP_ACTIVATION_FAILED, 6 emits). All gates green, review 0 open, residuals W-1..W-4 classified.
type: project
---

# Documentador — Pool 30-subscription-activation-notify

**Date:** 2026-08-15
**Source:** user dev spec + `.planning/quick/30-subscription-activation-notify-CLARIFY.md` + PLAN.md (4 tasks) + arch/testg reports + review loop.
**Type:** Feature pool (NOT hardening — no HARDENING_ROADMAP update, no pool phrase).

## Outcome

Cada Custodio (`bot_config.ADMIN_IDS`) recibe DM (voz de Lucien, HTML) al activar un token VIP: éxito (reutiliza `EVENT_VIP_ACTIVATED`, internal grants incluidos) y fallo (nuevo `EVENT_VIP_ACTIVATION_FAILED`, cubre TODOS los fallos). Observacional + best-effort: nunca muta estado VIP, nunca re-entra `redeem_token`.

## Items

1. **Item 1 — Success listener** `on_vip_activated_admin_notify` reutilizando `EVENT_VIP_ACTIVATED`.
2. **Item 2 — Failure listener** `on_vip_activation_failed_admin_notify` + 6 emits en `redeem_token` (not_found / used / expired x2 / tariff_not_found / no_vip_channel), post-rollback/commit.

## Blocked decisions (CLARIFY, locked — no re-abrir)

1. Failure scope = TODOS los fallos.
2. DM a cada `bot_config.ADMIN_IDS`.
3. Identidad user = user_id + @username + first_name.
4. Success scope = TODAS las activaciones VIP (reuse `EVENT_VIP_ACTIVATED`).

## Review stats (effort 5)

- 6 reviewers, 2 rounds.
- Round 1 → 10 fixes + 7 wontfix.
- Round 2 → all fixes verified + all wontfix accepted, **0 open issues**.

## Test evidence

- targeted 110 passed / 3 xfailed + golds 34 passed + integration smoke 61 passed / 6 xfailed, 0 attributable regressions.
- test-guardian "suite protege adecuadamente", 0 prohibited mocks. arch-enforcer PASS WITH NOTES, 0 critical.

## Learnings / patterns

- **Reuse over new events:** success path reused existing `EVENT_VIP_ACTIVATED`; only the genuinely new signal (failure) got a new constant. Minimizes event surface.
- **Observational listeners as the safe default for cross-domain notifications:** mirror nurture/listener pattern (lazy `get_service`, try/except, log handled/swallowed_best_effort), DM loop per store `_notify_admins_of_purchase`, lazy bot per `link_notifier._get_bot`. 0 mutation on VIP state.
- **Text in LucienVoice, not in service:** user-facing DM copy delegated to `LucienVoice.vip_activation_admin_success/_failure` + `_VIP_FAILURE_REASONS` map, with `html.escape` on all user-derived fields (XSS-safe in HTML parse_mode).
- **`token_code[:64]` truncation** before DB query — column is `String(64)`; prevents inflated payloads.
- **Security reviewer surfaced brute-force amplification** on failure DMs (all admins, no per-user debounce) — accepted, mitigations: locked scope + `/start` throttling.

## Residuals (all out-of-scope — do NOT create new pool items)

- **W-1 (surface to user for awareness):** failed redeem DM a todos los admins sin per-user debounce → admin-noise / brute-force amplification. Future optional: dedupe identical consecutive failures.
- **W-2:** listeners tocan `VIPService._get_db()` privado + ORM raw → future thin public read method on VIPService.
- **W-3:** `_notify_admins` duplica `store_service._notify_admins_of_purchase` send-loop → future shared util.
- **W-4:** `_get_bot()` duplica `link_notifier._get_bot()` → future consolidation.
- **W-7:** EventBus test singleton teardown ya existe (`_reset_event_bus_for_tests`) — non-issue.

## Files changed

- `services/event_bus.py` — +`EVENT_VIP_ACTIVATION_FAILED`, +`coro.close()` en `schedule_emit` (rama sin loop).
- `services/__init__.py` — re-export.
- `services/vip_notifier.py` (NUEVO) — 6 funciones descritas arriba.
- `services/vip_service.py` — 6 failure emits + `db.rollback()` en not_found + `token_code[:64]`.
- `bot.py` — registra ambos listeners en `on_startup`.
- `utils/lucien_voice.py` — 2 static methods + `_VIP_FAILURE_REASONS` + html.escape.
- `tests/unit/test_vip_notifier.py` (NUEVO, 16 tests), `tests/unit/test_vip_service.py` (patches schedule_emit).

## Handoff

Feature completa y revisada a 0 issues. Cambios en working tree (sin commit) — el orquestador hará commit tras autorización del usuario. No tocar HARDENING_ROADMAP (feature, no hardening).
