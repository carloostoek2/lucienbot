# Free→VIP wiring status (post token_id nullable)

**Depends on:** PR #3 merged (`Subscription.token_id` nullable + `grant_internal_vip_access` tests).

## Order: ritual → grant → nurture → copy

| Step | Status | Notes |
|------|--------|-------|
| Ritual | Deferred / N/A for VIP | VIP 3-phase ritual removed; Free 30s ritual intact (`scheduler_service`). No new ritual hooks without Copywriter strings. |
| Grant | Cutover done (this PR) | `grant_internal_vip_access_with_invite` wraps internal grant + invite. Callers: `reward_service._deliver_vip_access` (missions), `confirm_forward_vip_activation` (admin forward). Admin subscriber extend already on `grant_internal_vip_access_for_subscription`. Sales/token redeem + fulfillment VIP_GRANT still on `grant_vip_from_tariff` (fulfillment out of scope). |
| Nurture | Done | `EVENT_VIP_ACTIVATED` → `on_vip_activated` + admin notify registered in `bot.py`. Covered by unit emit asserts. |
| Copy | Hooks only | Use existing `LucienVoice.vip_direct_access` / `vip_activated`. Do not invent strings. |

## Next concrete work
1. ~~Identify authorized internal entrypoints~~ → cut over missions/rewards + admin forward.
2. Invite/DM via existing LucienVoice — done in `grant_internal_vip_access_with_invite`.
3. Keep fulfillment D1–D5 / MXN / economy out of scope (optional later cutover of fulfillment VIP_GRANT).
4. Ritual hook only if product re-enables VIP entry — Copywriter owns strings.

## Blockers
- Production: `alembic upgrade head` on Railway DB — already at `20260917_subscription_token_id_nullable` (confirmed).
- Copywriter for any new Free→VIP ritual copy if product re-enables VIP entry ritual.
