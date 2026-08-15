# SUMMARY — 30-subscription-activation-notify

**Pool:** Notificar por DM a Custodios el estado de activación de tokens de suscripción VIP (éxito + fallo).
**Type:** Feature pool (NOT hardening — no ROADMAP update).
**Date:** 2026-08-15
**Source:** user dev spec + `--clarify` (`.planning/quick/30-subscription-activation-notify-CLARIFY.md`) + PLAN.md.

## Outcome
Cada Custodio (`bot_config.ADMIN_IDS`) recibe un DM (voz de Lucien, HTML) al activar un token VIP: éxito (reutiliza `EVENT_VIP_ACTIVATED`, internal grants incluidos) y fallo (nuevo `EVENT_VIP_ACTIVATION_FAILED`, cubre TODOS los fallos). Observacional y best-effort: nunca muta estado VIP ni re-entra `redeem_token`.

## Items
1. **Item 1 — Success listener** reutilizando `EVENT_VIP_ACTIVATED` (`on_vip_activated_admin_notify`).
2. **Item 2 — Failure listener** nuevo `EVENT_VIP_ACTIVATION_FAILED` + 6 emits en `redeem_token` + listener (`on_vip_activation_failed_admin_notify`).

## Blocked decisions (CLARIFY — no re-abrir)
1. Failure scope = TODOS los fallos (not_found / used / expired / tariff_not_found / no_vip_channel).
2. DM a cada `bot_config.ADMIN_IDS`.
3. Identidad user = user_id + @username + first_name.
4. Success scope = TODAS las activaciones VIP (reuse `EVENT_VIP_ACTIVATED`).

## Pipeline results (all gates green)
| Gate | Result |
|------|--------|
| impact-analyzer | Riesgo MEDIO-ALTO; arquitectura → nuevo módulo `services/vip_notifier.py` (no un nuevo service) |
| gsd-planner | PLAN.md (4 tasks) |
| gsd-executor | Implementado (sin commit), self-check PASSED |
| arch-enforcer | **PASS WITH NOTES, 0 critical** (notas: `_notify_admins` dup, `_get_db()` raw — out-of-scope) |
| test-guardian | **"suite protege adecuadamente"**, 0 prohibited mocks |
| Tests | targeted 110 passed / 3 xfailed + golds 34 passed + integration smoke 61 passed / 6 xfailed, 0 attributable regressions |

## Review stats
- Effort 5, 6 reviewers, 2 rounds. Round 1 → 10 fixes + 7 wontfix. Round 2 → all fixes verified + all wontfix accepted, **0 open issues**.

## Files changed
- `services/event_bus.py` — +`EVENT_VIP_ACTIVATION_FAILED`, +`coro.close()` en `schedule_emit` (rama sin loop).
- `services/__init__.py` — re-export.
- `services/vip_notifier.py` (NUEVO) — `_get_bot`, `_notify_admins`, `build_activation_success_text`, `build_activation_failure_text`, `on_vip_activated_admin_notify`, `on_vip_activation_failed_admin_notify`.
- `services/vip_service.py` — 6 failure emits (post-rollback/commit), +`db.rollback()` en not_found, +`token_code[:64]`.
- `bot.py` — registra ambos listeners en `on_startup`.
- `utils/lucien_voice.py` — 2 static methods + `_VIP_FAILURE_REASONS`, `html.escape` en campos user-derived.
- `tests/unit/test_vip_notifier.py` (NUEVO, 16 tests), `tests/unit/test_vip_service.py` (patches schedule_emit).

## Residuals (out-of-scope — do NOT create new pool items)
- **W-1 (surface to user):** failure DMs a todos los admins sin per-user debounce → admin-noise / brute-force amplification. Mitigado por locked decision #1 + `/start` throttling. Futuro opcional: dedupe fallos consecutivos idénticos.
- **W-2:** listeners tocan `VIPService._get_db()` privado + ORM raw → futuro thin public read method.
- **W-3:** `_notify_admins` duplica `store_service._notify_admins_of_purchase` → futuro shared util.
- **W-4:** `_get_bot()` duplica `link_notifier._get_bot()` → futura consolidación.
- **W-7:** EventBus test singleton teardown ya existe (`_reset_event_bus_for_tests`) — non-issue.
