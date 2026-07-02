# SUMMARY: VIP Subscriber Admin Profiles (Etapa 1) — Phase 36

**Date:** 2026-07-02  
**Executor:** gsd-executor  
**Status:** COMPLETE

## Objetivo cumplido

Reemplazado `list_subscribers` plano (cap 10, sin paginación, sin `is_admin`, sin acciones) por router dedicado `vip_subscriber_admin_handlers` con:

- Lista paginada 8/página (gold channel_handlers)
- Perfiles clicables con snapshot (besitos compuesto en VIPService)
- Acciones FSM: extender / otorgar besitos / debitar besitos / expulsar
- Dead callback `list_subscribers_{channel_id}` cableado vía `SubscriberListCallback`
- Forward flow `vip_handlers.py` L707+ intacto

## Archivos tocados

| Archivo | Acción |
|---------|--------|
| `handlers/vip_subscriber_admin_handlers.py` | **CREATE** — router, FSM, puros, 4 acciones |
| `services/vip_service.py` | +`get_subscriber_list_page`, `get_subscriber_admin_snapshot`, `get_subscriber_extend_context`, `admin_revoke_subscription` |
| `services/besito_service.py` | +`debit_manual_admin_besitos` |
| `keyboards/callback_data.py` | +5 clases Subscriber* |
| `keyboards/inline_keyboards.py` | +4 keyboards + wire callbacks |
| `utils/lucien_voice.py` | +12 métodos admin suscriptores |
| `handlers/vip_handlers.py` | Eliminado `list_subscribers` handler |
| `handlers/__init__.py` | Export `vip_subscriber_admin_router` |
| `bot.py` | `include_router(vip_subscriber_admin_router)` |
| `tests/handlers/test_vip_subscriber_admin_handlers.py` | **CREATE** |
| `tests/unit/test_vip_service.py` | +5 tests subscriber admin |
| `tests/unit/test_besito_service.py` | +2 tests debit_manual_admin |
| `tests/integration/test_callbackdata_vip.py` | +Subscriber* pack tests |
| `tests/handlers/test_vip_handlers.py` | +regression forward intacto |
| `decisions.md` | Item 36 append |

## Gates pytest

| Gate | Comando | Resultado |
|------|---------|-----------|
| 1 — feature | `-k "subscriber_admin or SubscriberList or debit_manual_admin or admin_revoke_subscription"` | **16 passed** |
| 2 — VIP lifecycle | `-k "vip or TestVIPSubscriptionLifecycle or has_other_active"` | **257 passed, 1 failed** (pre-existing: `test_confirm_direct_buy_vip_activated_shows_purchase_completed` — store copy "discernimiento", no atribuible a phase 36) |
| 3 — atomicity | `-k "cross_service_atomicity or grant_manual_admin_besitos"` | **13 passed** |
| 4 — forward regression | `tests/handlers/test_vip_handlers.py` | **14 passed** |
| 5 — smoke | `-k "reaction_ or daily_gift or invariants" tests/` | **83 passed** |

## Contratos verificados

- `admin_revoke_subscription`: `has_other_active` → deactivate only, sin ban (test PASS)
- `debit_manual_admin_besitos`: `has_sufficient_balance` antes de debit, sin EventBus (test PASS)
- Extend confirm: solo `grant_internal_vip_access` (test PASS)
- Handlers confirm: 1 `get_service` por entrypoint confirm
- `is_admin` en 100% entrypoints + `_deny_non_admin_*` para tests directos
- 0 `VIPService()` bare en nuevo handler
- 0 `has_other_active` en handler (solo service)
- `SUBSCRIBER_PAGE_SIZE = 8`

## Self-check

```
SELF-CHECK: PASSED
```

## Hardener review fixes (2026-07-02)

| # | Fix |
|---|-----|
| P0-1 | `state.clear()` en `open_subscriber_profile` (cancel → perfil) |
| P0-2 | Escape HTML solo en `LucienVoice.admin_subscriber_list_line` |
| P0-3 | Clamp página antes de `offset` en `get_subscriber_list_page` |
| P0-4 | Guard `SubscriberAdminStates.extend_confirming` en confirm extend |
| P0-5 | `grant_internal_vip_access_for_subscription(subscription_id, tariff_id)` |
| P0-6 | `validate_fsm_subscription_id` en todos los confirm handlers |
| P0-7 | Extend success sin 2º `get_service` — `admin_subscriber_extend_success` |
| P0-8 | `start_subscriber_extend` ≤50 LOC + `build_tariff_map` puro |
| P1-9 | `channel_inactive` → `admin_subscriber_kick_channel_inactive` |
| P1-10 | `select_extend_tariff` rechaza `tariff_id` fuera de `tariff_map` |
| P1-11 | +8 tests (FSM clear, mismatch, debit fail, kick deactivated, extend by sub, clamp, invalid debit) |
| P1-12 | `admin_subscriber_debit_success` LucienVoice |
| P2-16 | Imports top-level `InlineKeyboardButton/Markup` en kick confirm |

**Post-fix gates:** 24 passed (subscriber_admin/revoke/debit) + 14 passed (forward regression)

## R2 final fixes (2026-07-02)

| # | Fix |
|---|-----|
| R2-1 | `await state.clear()` at start of all `start_subscriber_*` (extend, grant, debit, kick) |
| R2-2 | `grant_internal_vip_access_for_subscription` rejects `not tariff.is_active` |
| R2-3 | `test_select_extend_tariff_rejects_invalid_tariff` |
| R2-4 | `test_confirm_extend_fail_shows_error` |
| R2-5 | `test_admin_revoke_channel_inactive` + `test_confirm_kick_channel_inactive_messaging` |
| R2-6 | `test_open_subscriber_profile_not_found` |
| R2-7 | `test_get_subscriber_extend_context` + `test_grant_internal_vip_access_for_subscription_rejects_inactive_tariff` |

**R2 gate:** **29 passed** (`subscriber_admin or admin_revoke or debit_manual_admin`)

**Status:** ALL REVIEW ISSUES CLOSED (hardener r1 + r2)

## Handoff arch-enforcer

- Revisar LOC handlers (todos ≤50 tras extracción puros)
- Gate 2 failure pre-existente en store — no bloqueante para Item 36
- `get_subscriber_extend_context` compuesto interno (2 queries) expuesto como 1 svc al handler