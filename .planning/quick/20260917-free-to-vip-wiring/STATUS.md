# Free→VIP wiring status (post token_id nullable)

**Depends on:** PR #3 merged (`Subscription.token_id` nullable + `grant_internal_vip_access` tests).

## Order: ritual → grant → nurture → copy

| Step | Status | Notes |
|------|--------|-------|
| Ritual | Deferred / N/A for VIP | VIP 3-phase ritual removed; Free 30s ritual intact (`scheduler_service`). No new ritual hooks without Copywriter strings. |
| Grant | Schema+API ready | `grant_internal_vip_access` create/extend with `token_id=None`. Callers still mostly `grant_vip_from_tariff` (synthetic token). Cutover = this PR scope (not fulfillment D1–D5). |
| Nurture | Done | `EVENT_VIP_ACTIVATED` → `on_vip_activated` + admin notify registered in `bot.py`. Covered by unit emit asserts. |
| Copy | Hooks only | Use existing `LucienVoice.vip_direct_access` / `vip_activated`. Do not invent strings. |

## Next concrete work
1. Identify authorized internal entrypoints (missions/rewards/admin forward) to call `grant_internal_vip_access`.
2. After grant: invite link + DM via existing LucienVoice (same pattern as `grant_vip_from_tariff` return path).
3. Keep fulfillment D1–D5 / MXN / economy out of scope.

## Blockers
- Production: `alembic upgrade head` on Railway DB after PR #3.
- Copywriter for any new Free→VIP ritual copy if product re-enables VIP entry ritual.
