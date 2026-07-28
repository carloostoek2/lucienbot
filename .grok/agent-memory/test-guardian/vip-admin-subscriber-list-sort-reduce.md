# Test-Guardian: VIP admin subscriber list sort + reduce time

**Item:** vip-admin-subscriber-list-sort-reduce  
**Date:** 2026-07-28  
**Verdict:** **suite protege adecuadamente**  
**status:** PASS  
**ready_for_pytest_gate:** yes  

**PLAN:** `.planning/quick/20260728-vip-admin-subscriber-list-sort-reduce/PLAN.md`  
**SUMMARY:** `.planning/quick/20260728-vip-admin-subscriber-list-sort-reduce/SUMMARY.md`  
**Arch:** PASS WITH NOTES 0 critical — `.grok/agent-memory/arch-enforcer/vip-admin-subscriber-list-sort-reduce.md`  
**Impact:** `.grok/agent-memory/impact-analyzer/vip-admin-subscriber-list-sort-reduce.md`  

---

## 1. Scope audited

| Area | Files |
|------|-------|
| Service | `services/vip_service.py` — sort + `admin_reduce_subscription_time` |
| Handlers | `handlers/vip_subscriber_admin_handlers.py` — FSM reduce + pure parsers |
| UI/callback | `keyboards/*`, `utils/lucien_voice.py` |
| Tests | `tests/unit/test_vip_service.py` (`TestSubscriberAdminVIPService`) · `tests/handlers/test_vip_subscriber_admin_handlers.py` · `tests/integration/test_callbackdata_vip.py` |

---

## 2. Coverage matrix (PLAN truths)

| # | Criterion | Test evidence | Status |
|---|-----------|---------------|--------|
| 1 | List orders by `created_at` desc (+ id desc) | `test_get_subscriber_list_page_orders_by_created_at_desc` — real `VIPService` + 3 subs with explicit `created_at` | ✅ |
| 2 | Reduce by days keeps active | `test_admin_reduce_subscription_time_by_days_keeps_active` — end_date −N, `is_active=True` | ✅ |
| 3 | Reduce by date | `test_admin_reduce_subscription_time_by_new_end_date` | ✅ |
| 4 | `would_expire` reject, zero mutate | `test_admin_reduce_subscription_time_rejects_would_expire` | ✅ |
| 5 | `not_earlier` reject, zero mutate | `test_admin_reduce_subscription_time_rejects_not_earlier` | ✅ |
| 6 | `invalid_args` (none / both / 0 / −1) | `test_admin_reduce_subscription_time_rejects_invalid_args` | ✅ |
| 7 | Never inactive / still in list+snapshot | `test_admin_reduce_subscription_time_never_sets_inactive` | ✅ |
| 8 | Pure parse days/date | `TestPureHelpers::test_parse_reduce_days_input` / `test_parse_reduce_end_date_input` (import-inside) | ✅ |
| 9 | Callback pack reduce / reduce_days / reduce_date / confirm reduce | `test_subscriber_action_callback_pack_reduce` (+ days/date) + `test_subscriber_confirm_callback_pack_reduce` | ✅ |
| 10 | Start reduce: snapshot once | `test_start_subscriber_reduce_calls_snapshot_once` | ✅ |
| 11 | Confirm: 1× `admin_reduce_subscription_time` + kwargs | `test_confirm_subscriber_reduce_calls_service_once` | ✅ |
| 12 | Confirm never calls revoke | `assert_not_called` on `admin_revoke_subscription` in confirm ok + would_expire tests | ✅ |
| 13 | FSM mismatch: no get_service | `test_confirm_subscriber_reduce_rejects_fsm_mismatch` | ✅ |

**Business-critical invariants** (would_expire / keeps active / never ban / sort) live in **unit service tests with real DB** — not mocked.

---

## 3. Mock Audit (mandatory)

### Decision tree applied

| Path | Mock? | Verdict | Confidence |
|------|-------|---------|------------|
| `VIPService.admin_reduce_subscription_time` / sort | **No** — real service + `db_session` SQLite | PERMITIDO (real) | **Alta** |
| Pure helpers parse_reduce_* | **No** — direct import-inside | PERMITIDO | **Alta** |
| Callback pack/unpack | **No** | PERMITIDO | **Alta** |
| Handler confirm/start wiring | `_mock_vip_ctx` = `create_autospec(VIPService)` + `patch get_service` + `patch is_admin` | **PERMITIDO** — PLAN Mock policy: "Handler tests: mock get_service + autospec VIPService (existing `_mock_vip_ctx`)." Wiring only (call count / kwargs / no revoke). Business rules covered by unit real DB. | **Media** (wiring) + **Alta** (rules via unit) |
| Telegram fixtures | `make_callback`, `make_fsm_context` | PERMITIDO (borde externo) | — |

### Table — mocks in scope test files

| File | Mock / patch | Target | Allowed? | Why |
|------|--------------|--------|----------|-----|
| `test_vip_service.py` reduce/sort tests | none on VIP reduce/sort | N/A | ✅ | Real `VIPService(db_session)` |
| `test_vip_subscriber_admin_handlers.py` | `_mock_vip_ctx` / `get_service` / `is_admin` | handler wiring | ✅ | PLAN explicit; autospec; asserts call-once + no revoke |
| `test_vip_subscriber_admin_handlers.py` | `MagicMock` subs in pure list-text builders | display helpers (pre-existing) | ✅ | Pure UI text builders; not reduce business logic |
| `test_callbackdata_vip.py` | none | pack/unpack | ✅ | Real CallbackData |

### Prohibited patterns search

| Pattern | In scope new/reduce tests? |
|---------|----------------------------|
| `_mock_*` stubbing business under unit service test | **0** |
| Mock `db_session.query` for reduce | **0** |
| Mock `admin_reduce` in unit tests | **0** |
| Assert UI only from mock.return_value without unit DB | Handler confirm uses mock return for success copy only — **OK**: real mutation covered in unit; handler asserts service contract (once / no revoke) |

**0 mocks prohibidos en paths del scope.**  
Handler `_mock_vip_ctx` is **PLAN-authorized** thin-admin pattern (mirror debit/kick); critical channels-VIP rules protected at service unit with real DB.

---

## 4. Gaps

| Gap | Severity | Action |
|-----|----------|--------|
| No handler test for `process_reduce_input` / `reduce_date` confirm path | BAJA / optional | Pure parse + service `new_end_date` cover risk; not required by PLAN Task 3 list |
| No full integration handler→real VIPService→DB for reduce | BAJA | PLAN allows unit real + handler wiring mock; not economic/store atomic path |
| `search_active_subscribers` still end_date.asc | Out of scope | PLAN non-goal |

**Blocking gaps: 0**

---

## 5. Tests results (re-run test-guardian)

Flags: `-q --tb=line -p no:cov --override-ini="addopts="`  
Env: project `venv/` (`/home/ubuntu/repos/lucienbot/venv`).

### Targeted
```
tests/unit/test_vip_service.py::TestSubscriberAdminVIPService
tests/handlers/test_vip_subscriber_admin_handlers.py
tests/integration/test_callbackdata_vip.py
→ 94 passed
```

### VIP golds / smoke
```
-k "vip or TestVIPSubscriptionLifecycle or admin_revoke or grant_internal_vip_access_for_subscription"
→ 306 passed, 8 xfailed, 0 failed
```

### Atomicity / reaction / daily / invariants
```
-k "cross_service_atomicity or reaction_ or daily_gift or invariants"
→ 94 passed, 1 failed
```

**Known residual (non-attributable, document — do not fail gate):**
- `tests/unit/test_broadcast_service_reaction_flow.py::TestServiceLifecycleOrGetServiceContext::test_real_with_get_service_usage_in_test`
- `sqlalchemy.exc.MissingGreenlet` (asyncpg / env driver)
- Out of VIP sort/reduce surface; matches SUMMARY residual; PLAN note accepted.

**0 regressions attributable to this item.**

---

## 6. 3 critical systems

| System | Impact of item | Gold re-run |
|--------|----------------|-------------|
| Gamificación | 0 (orthogonal) | reaction_ / daily_gift / invariants green (minus known broadcast flake) |
| Narrativa | 0 | not touched |
| Canales-VIP | sort + reduce end_date only; never ban/revoke/is_active=False | VIP golds 306p + unit reduce suite |

Contracts: no EventBus on reduce (arch); get_service 1× on confirm (handler test); atomicity golds unaffected.

---

## 7. Verdict

**suite protege adecuadamente**

- Cobertura del ítem OK (sort + all reduce result codes + never inactive + handler 1-svc + no revoke + pure helpers + callback pack)
- **0 mocks prohibidos** (handler autospec PLAN-authorized; business logic real DB)
- Golds re-run green except known out-of-scope MissingGreenlet
- ready_for_pytest_gate: **yes**

Log: `.planning/quick/gsd-test-guardian-vip-admin-subscriber-list-sort-reduce.log`
