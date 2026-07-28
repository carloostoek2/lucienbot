# Arch Audit: vip-admin-subscriber-list-sort-reduce

**Verdict:** PASS WITH NOTES  
**Critical violations:** 0  
**Date:** 2026-07-28  
**Item:** VIP admin subscriber list sort + reduce time (standalone quick)  
**Sources:** PLAN + SUMMARY + impact + production code + targeted tests

---

## Findings

### Critical (must fix before advance)

_None._

### Medium

_None attributable to this change._

### Observations

1. **Invalid re-prompt copy inline** — `process_reduce_input` uses hardcoded HTML for invalid days/date instead of `LucienVoice.*` helpers (success/confirm/mode prompts are in voice). Pattern already seen on other FSM free-text paths; not a layer violation.
2. **Auto-fix LOC split** — `_is_valid_reduce_args` + `_compute_reduced_end_candidate` + `_log_reduce_result` keep `admin_reduce_subscription_time` ≤50 (SUMMARY deviation, correct).
3. **Out of scope residual** — `search_active_subscribers` remains `end_date.asc` (PLAN non-goal). List page is `created_at.desc(), id.desc()` as required.
4. **Pre-existing env residual** — SUMMARY notes `test_real_with_get_service_usage_in_test` MissingGreenlet (broadcast); unrelated to this surface.

---

## Compliance Checklist

| Rule | Status | Evidence |
|------|--------|----------|
| Handlers call exactly 1 service | ✅ | Confirm: single `with get_service(VIPService)` → `admin_reduce_subscription_time`. Start: 1 snapshot read. Mode/input: 0 svc. No BesitoService on reduce path. |
| No DB access in handlers | ✅ | No `models` / SessionLocal / `db.query` in handler module for reduce; only `get_service`. |
| Funcs ≤50 LOC | ✅ | `admin_reduce_subscription_time` ~46; `confirm_subscriber_reduce` ~44; `process_reduce_input` ~38; `start_subscriber_reduce` ~32; `choose_subscriber_reduce_mode` ~28; pure helpers short. |
| Naming verb+context+result | ✅ | `admin_reduce_subscription_time`, `parse_reduce_days_input`, `parse_reduce_end_date_input`, `map_reduce_result_reason`, `build_reduce_confirm_summary`, `start/choose/process/confirm_subscriber_reduce`. |
| Logging standard | ✅ | Service: `vip_service \| admin_reduce_subscription_time \| user_id=… \| subscription_id=… \| resultado=…` (ok=info, fail=warning). Handler confirm: `vip_subscriber_admin_handlers \| confirmar_reduce \| …`. |
| `is_admin` on admin entrypoints | ✅ | Lambda filter + `_deny_non_admin_*` on reduce start/mode/input/confirm. |
| Reduce MUST NOT ban/revoke/is_active=False/EventBus | ✅ | Method mutates **only** `subscription.end_date`; no `is_active=False`, no `ban_chat_member`, no `schedule_emit`/`EVENT_VIP_ACTIVATED`. Docstring states contract. Kick remains on separate `admin_revoke_subscription` path only. |
| `would_expire` rejects with no mutation | ✅ | `_compute_reduced_end_candidate` → early return before commit; unit test asserts `end_date` unchanged + `is_active=True`. Same for `not_earlier` / `invalid_args`. |
| Pure helpers for parse | ✅ | `parse_reduce_days_input`, `parse_reduce_end_date_input` (+ map/summary) with `"Función pura (sin estado ni side-effects)."`; DD/MM/YYYY end-of-day UTC. |
| Capas handlers→services→models | ✅ | Domain mutation only in `VIPService`. |
| Scope PLAN respected | ✅ | Touches listed files only; no models/migration; no grant/redeem/scheduler body change. |
| 3 critical systems | ✅ | **Gamificación:** no credit/debit/reaction/daily. **Narrativa:** untouched. **Canales-VIP:** only earlier `end_date` on active sub; list order change only; no expire-kick side-effect on successful reduce. |
| EventBus contract | ✅ | Reduce path does not emit; listeners unchanged. |
| get_service context manager | ✅ | Confirm uses exactly one `with get_service(VIPService)`. |

---

## 3 systems impact (explicit)

| System | Impact |
|--------|--------|
| Gamificación | **None** — no BesitoService, no credit/debit, no reaction/daily. |
| Narrativa | **None** — no StoryService / FSM story / quiz. |
| Canales-VIP | **Controlled** — list sort newest-first; reduce shortens `end_date` only while `is_active=True` and `end_date > now`. No ban/revoke/deactivate. Scheduler expire remains the sole kick path for true expiry. |

---

## LOC snapshot (new/changed surface)

| Symbol | ~LOC | File |
|--------|------|------|
| `_is_valid_reduce_args` | ~7 | `services/vip_service.py` |
| `_compute_reduced_end_candidate` | ~18 | `services/vip_service.py` |
| `_log_reduce_result` | ~12 | `services/vip_service.py` |
| `admin_reduce_subscription_time` | ~46 | `services/vip_service.py` |
| `parse_reduce_days_input` | ~10 | handlers |
| `parse_reduce_end_date_input` | ~13 | handlers |
| `map_reduce_result_reason` | ~10 | handlers |
| `build_reduce_confirm_summary` | ~12 | handlers |
| `start_subscriber_reduce` | ~32 | handlers |
| `choose_subscriber_reduce_mode` | ~28 | handlers |
| `process_reduce_input` | ~38 | handlers |
| `confirm_subscriber_reduce` | ~44 | handlers |

All ≤50.

---

## Test evidence (arch relevance only; full suite → test-guardian)

- Unit: order `created_at.desc`; reduce by days/date; rejects would_expire/not_earlier/invalid_args with no mutation; never sets inactive.
- Handler: confirm calls `admin_reduce_subscription_time` once; never calls `admin_revoke_subscription`; FSM mismatch skips service.
- Pure helper unit tests for parse days/date.

---

## Gate

**PASS WITH NOTES** with **0 critical** → advance to **test-guardian**.

## Handoff

- Next: **test-guardian** (re-run targeted + VIP golds + atomicity/reaction/daily/invariants; assert suite protects reduce contracts).
- No executor rework required for architecture.
