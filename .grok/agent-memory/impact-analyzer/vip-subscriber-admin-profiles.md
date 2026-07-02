# Impact Analysis: VIP Subscriber Admin Profiles (Etapa 1)

**Date:** 2026-07-02  
**Scope:** Paginated subscriber list + per-user admin profiles + extend / grant-debit besitos / kick.  
**Analysis only** — no implementation.

## Executive Summary

Replace flat `list_subscribers` (first 10, no pagination, no profile actions) with dedicated admin router, VIPService query/revoke methods, BesitoService admin debit mirror, CallbackData keyboards, LucienVoice copy. Fix dead `list_subscribers_{channel_id}`. Preserve forward-admin VIP|besitos in `vip_handlers.py`.

**Risk:** Medium-High (channels-VIP kick + besitos debit + 1-service/async bot).

## Consumers / Call Sites

### list_subscribers (TO REPLACE)
| Location | Usage |
|----------|-------|
| `handlers/vip_handlers.py:708-749` | `get_active_subscriptions()`, flat text, cap 10, `VIPService()`+close, **no is_admin** |
| `keyboards/inline_keyboards.py:411` | `callback_data="list_subscribers"` → vip_management_keyboard |
| `keyboards/inline_keyboards.py:229` | `list_subscribers_{channel_id}` → **NO HANDLER** (dead) |

### has_other_active_subscription (KICK CONTRACT)
| Consumer | Pattern |
|----------|---------|
| scheduler `_process_expired_subscriptions` | other_active → deactivate only; else ban/unban+notify |
| bot `check_expired_subscriptions_on_startup` | same |
| Tests | test_vip_service.py, test_vip_subscription_lifecycle.py |

### grant_internal_vip_access (EXTEND)
vip_service.py:534-634 — extend active sub; emit EVENT_VIP_ACTIVATED

### grant_manual_admin_besitos (GRANT MIRROR)
gamification_admin_handlers, vip_handlers forward, test_besito_service

### Forward flow (NO TOUCH)
vip_handlers.py L752-971

## Risks

### Critical
1. Kick without has_other_active check → wrongful expulsion
2. Besitos debit → negative balance or event on debit
3. Extend bypassing grant_internal_vip_access

### Medium
- list_subscribers missing is_admin
- Handler >50 LOC → pure helpers
- Snapshot: BesitoService local inside VIPService only

## Test Commands

```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "subscriber_admin or SubscriberList or debit_manual_admin or admin_revoke_subscription"
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "vip or TestVIPSubscriptionLifecycle or has_other_active"
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "cross_service_atomicity or grant_manual_admin_besitos"
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/handlers/test_vip_handlers.py
```

## Files Map

| File | Action |
|------|--------|
| handlers/vip_subscriber_admin_handlers.py | CREATE |
| services/vip_service.py, besito_service.py | EDIT |
| keyboards/callback_data.py, inline_keyboards.py | EDIT |
| utils/lucien_voice.py, handlers/__init__.py, bot.py | EDIT |
| handlers/vip_handlers.py | deprecate list_subscribers only |
| tests (handlers, unit, callbackdata) | CREATE/EDIT |

## Ready for gsd-planner

Tight PLAN: pagination PAGE_SIZE 8; FSM for extend/besitos/kick; 1 get_service per handler; admin_revoke async(bot); snapshot composes besitos inside VIPService.