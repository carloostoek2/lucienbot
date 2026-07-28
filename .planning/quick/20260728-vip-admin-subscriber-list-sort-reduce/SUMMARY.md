---
phase: quick
plan: vip-admin-subscriber-list-sort-reduce
subsystem: vip / channels-VIP admin
tech-stack: Python 3.12, Aiogram 3, SQLAlchemy 2, pytest
key-files:
  - services/vip_service.py
  - handlers/vip_subscriber_admin_handlers.py
  - keyboards/inline_keyboards.py
  - keyboards/callback_data.py
  - utils/lucien_voice.py
  - tests/unit/test_vip_service.py
  - tests/handlers/test_vip_subscriber_admin_handlers.py
  - tests/integration/test_callbackdata_vip.py
date: 2026-07-28
status: complete
---

# SUMMARY: VIP admin subscriber list sort + reduce time

## Objective

Custodios: newest-first VIP subscriber list; reduce remaining VIP time without kick/ban/deactivate.

## Tasks completed

| Task | Result | Commit |
|------|--------|--------|
| T1 Service sort + `admin_reduce_subscription_time` | GREEN | `a1d4be3` feat(vip): newest-first list + admin reduce time service |
| T2 UI surface + pure parse helpers | GREEN | `c463b4d` feat(vip): reduce-time UI surface and parse helpers |
| T3 Handler FSM reduce flow + tests + golds | GREEN | `ab630e7` feat(vip): admin FSM to reduce subscription time without kick |
| Fix Round 1 (review tests) | GREEN | `test(vip): cover reduce not_found/inactive and sort id tiebreak` |

## What shipped

1. **List order:** `get_subscriber_list_page` → `created_at.desc(), id.desc()`
2. **Reduce service:** mutates only `end_date` earlier; rejects `would_expire` / `not_earlier` / `invalid_args` with zero mutation; never ban / `is_active=False` / EventBus
3. **Admin FSM:** reduce → mode (days|date) → free text → confirm; confirm = exactly 1 `get_service(VIPService)`
4. **UI:** profile button «⏱ Reducir tiempo», mode keyboard, Lucien voice strings
5. **Pure helpers:** `parse_reduce_days_input`, `parse_reduce_end_date_input` (DD/MM/YYYY end-of-day UTC)

## Deviations

- Split `_is_valid_reduce_args` + `_compute_reduced_end_candidate` + `_log_reduce_result` so `admin_reduce_subscription_time` stays ≤50 LOC (auto-fix rule 2/3).
- No architectural change required.

## Verifications run

```bash
# Targeted
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  tests/unit/test_vip_service.py::TestSubscriberAdminVIPService \
  tests/handlers/test_vip_subscriber_admin_handlers.py \
  tests/integration/test_callbackdata_vip.py
# → 94 passed (post-impl); Fix Round 1 → 99 passed

# VIP golds
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "vip or TestVIPSubscriptionLifecycle or admin_revoke or grant_internal_vip_access_for_subscription"
# → 306 passed, 8 xfailed

# Atomicity / reaction / daily / invariants
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "cross_service_atomicity or reaction_ or daily_gift or invariants"
# → 94 passed, 1 failed (non-attributable env: asyncpg MissingGreenlet in broadcast get_service lifecycle)
```

## Self-check gates

- [x] `admin_reduce_subscription_time` present in service + confirm handler only
- [x] `admin_revoke_subscription` only on kick confirm path
- [x] No new EventBus emit in reduce path
- [x] Confirm reduce: 1 `with get_service(VIPService)`
- [x] New funcs ≤50 LOC
- [x] Logging on reduce success/fail

## Review Fix Round 1

Closed 4 open test suggestions/nits (no production code change):
1. Real-DB `not_found` + `inactive` reduce codes
2. Sort `id.desc` tiebreak when same `created_at`
3. Handler confirm date-mode kwargs (`days=None`, `new_end_date=…`) + no revoke
4. `not_earlier` boundary when `new_end == current`

Targeted re-run: **99 passed** (`env -u DATABASE_URL DATABASE_URL=sqlite:///lucien_bot.db`).

## Residuals

- **title:** `test_real_with_get_service_usage_in_test` fails with `sqlalchemy.exc.MissingGreenlet` (asyncpg)
- **clase_sugerida:** out-of-scope
- **por_qué:** Environment/DB URL async driver issue; unrelated to VIP reduce/sort; not in plan surface
- **archivos:** `tests/unit/test_broadcast_service_reaction_flow.py`

- **title:** `search_active_subscribers` still `end_date.asc`
- **clase_sugerida:** out-of-scope
- **por_qué:** Explicit non-goal in PLAN
- **archivos:** `services/vip_service.py`

## Self-Check: PASSED

- [x] Todas las tareas completadas
- [x] Tests del PLAN corridos
- [x] 0 regresiones atribuibles
- [x] Convenciones del proyecto respetadas

**ready_for_arch-enforcer: yes**
