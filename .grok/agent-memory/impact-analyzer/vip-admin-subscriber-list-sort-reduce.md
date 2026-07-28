# Impact Analysis: VIP admin subscriber list sort + reduce time

**Date:** 2026-07-28  
**Change:** Sort admin VIP list by newest subscription first; add reduce-time admin action (no kick)  
**Analysis only** — no implementation  
**Risk:** CRITICAL (channels-VIP / end_date surface; mitigable)

## Executive Summary

Admin VIP subscriber list currently orders by `Subscription.end_date.asc()` (who expires soonest first). Product wants **most recently subscribed first** → `created_at.desc(), id.desc()`.

Reduce subscription time does not exist. Mirror extend/besitos patterns: new `VIPService.admin_reduce_subscription_time` that **only** moves `end_date` earlier while keeping `is_active=True`, never ban/revoke. Reject if result would be ≤ now (scheduler would kick). Admin UI: mode (days | date) → free text → confirm.

Touches channels-VIP. Do not touch gamification, narrative, EventBus, grant/revoke/expire semantics, or models (no migration).

## Consumers / Call Sites Map

| Area | Path | Notes |
|------|------|-------|
| List page | `VIPService.get_subscriber_list_page` | Change order_by |
| Render list | `handlers/vip_subscriber_admin_handlers.py` `_render_subscriber_list` | Contract unchanged |
| Profile keyboard | `keyboards/inline_keyboards.py` `subscriber_profile_keyboard` | Add reduce button |
| Callback | `SubscriberActionCallback.action` | Add `"reduce"` |
| Snapshot | `get_subscriber_admin_snapshot` | Reads end_date after reduce |
| Scheduler | `get_expired_subscriptions` / `get_expiring_subscriptions` | Indirect — reduce must leave end_date > now |
| Revoke | `admin_revoke_subscription` | **NO TOUCH** |
| Extend | `grant_internal_vip_access_for_subscription` | Pattern reference only |

## Subscription fields (models)

- `start_date`, `created_at` — set on create; **not** updated on extend
- `end_date` — expiry clock (extend/reduce target)
- `is_active`, `reminder_sent`

Sort key: **`created_at.desc(), id.desc()`** (tiebreaker for same-second creates). Not `end_date`.

## Design recommended

### Sort
```python
.order_by(Subscription.created_at.desc(), Subscription.id.desc())
```

### Service
```python
def admin_reduce_subscription_time(
    self,
    subscription_id: int,
    admin_id: int,
    *,
    days: int | None = None,
    new_end_date: datetime | None = None,
) -> tuple[bool, str, dict]:
```
Rules: exactly one of days/new_end_date; active sub; days > 0; new_end > now and < current_end; would_expire reject no mutate; no ban; no EventBus; log standard.

### FSM (mirror besitos)
States: reduce_choosing_mode → reduce_waiting_input → reduce_confirming  
Confirm: exactly 1 `get_service(VIPService)` call. Pure helpers for parse days/date (`%d/%m/%Y`).

## Files Map

**Edit:**
- `services/vip_service.py`
- `handlers/vip_subscriber_admin_handlers.py`
- `keyboards/callback_data.py`
- `keyboards/inline_keyboards.py`
- `utils/lucien_voice.py`
- `tests/unit/test_vip_service.py`
- `tests/handlers/test_vip_subscriber_admin_handlers.py`
- `tests/integration/test_callbackdata_vip.py`

**No touch:**
- `admin_revoke_subscription` / `expire_subscription` semantics
- grant/redeem paths
- `scheduler_service` expire job
- models (no migration)
- besitos / narrative / EventBus

## Risks

| Level | Risk | Mitigation |
|-------|------|------------|
| Critical | reduce end_date ≤ now → scheduler ban | reject `would_expire` |
| Critical | accidental reuse of revoke in reduce | separate method + button |
| Medium | created_at vs start_date vs last-extend | document: created_at = first subscribe |
| Medium | pagination tests order assumptions | update asserts |
| Low | search_active_subscribers still end_date.asc | out of scope |

## Exact tests

```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  tests/unit/test_vip_service.py::TestSubscriberAdminVIPService \
  tests/handlers/test_vip_subscriber_admin_handlers.py \
  tests/integration/test_callbackdata_vip.py

python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "vip or TestVIPSubscriptionLifecycle or admin_revoke or grant_internal_vip_access_for_subscription"

python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "cross_service_atomicity or reaction_ or daily_gift or invariants"
```

## Missing tests to add

- order by created_at desc
- reduce by days keeps active
- reduce by new_end_date
- reject would_expire
- reject new_end after current / invalid
- reduce never bans
- handler confirm exactly 1 svc
- callback pack action=reduce

## Ready for chain

**ready_for_planner: yes**
