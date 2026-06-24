# Impact Analysis: VIP Forward Activation (new/renew by admin forward)

**Date:** 2026-06-24
**Change:** VIP forward activation flow for admin to activate/renew VIP by forwarding a candidate user's message to the bot. Bot extracts original user ID (via forward), confirms with tariff selection, activates via existing grant path, sends direct welcome + native 1-use TG invite link; fallback notify admin on send failure (blocked etc). Manual token flow 100% preserved.
**Analysis only** — no implementación

## Executive Summary
Analysis based exclusively on reads of intake, root CLAUDE.md, AGENTS.md, architecture.md, rules.md, handlers/CLAUDE.md, services/CLAUDE.md, services/vip/CLAUDE.md, full key files (vip_service.py, vip_handlers.py, common_handlers.py, channel_grant.py, reward_service.py, lucien_voice.py, models/models.py), keyboards/inline_keyboards.py + callback_data.py, bot.py, grep discoveries for call sites/forward patterns/sends, fd/rg for test files, and channel forward precedent.

**Core recommendation (reuse):** New admin-forwarded message handler in vip_handlers.py (exactly 1 service call: prefer grant_vip_from_tariff which already does generate+redeem_with_missions+create_invite), FSM for tariff select + confirm (reuse TokenStates/select pattern + tariffs_keyboard + confirmation_keyboard + SelectTariffCallback), direct bot.send to candidate, catch blocked (precedent in channel_grant.py: "bot was blocked by the user"), on fail notify the forwarding admin with manual token deep-link. No service change needed (grant_vip_from_tariff returns the Lucien vip_direct_access string + metadata). Handler <=50 LOC by extracting pure helpers if needed per hardener precedent. Preserve redeem atomicity (always via grant -> redeem_token FOR UPDATE + post-commit EVENT_VIP_ACTIVATED best-effort). Channels-VIP critical protected (Subscription via token only). 

**Risk level:** Medium-High (touches channels-VIP critical #3 + redeem atomicity + send failure paths + admin auth). 0 behavior change to existing manual flows. Evidence shows grant paths already handle partial (vip_activated=True + invite=None) + send failures without rollback of sub.

## Consumers / Call Sites Map
**Evidence:** Multiple rg/grep runs + full reads.

**VIP grant paths (prefer this):**
- services/reward_service.py:465 (in _deliver_vip_access): `await self.vip_service.grant_vip_from_tariff(bot, user_id, reward.tariff_id)`; then _send; handles prior_grant via resend_vip_invite_for_user; marks _CLAIM_TOKEN / _CLAIM_SENT for idemp; catches send exc -> _mark_vip_partial_grant
- services/fulfillment_service.py:369 (in _dispatch_vip_grant for store VIP products): `await vip_svc.grant_vip_from_tariff(bot, row.user_id, product.tariff_id)`; similar partial AUTO_IN_PROGRESS + _commit after send; resend path
- services/vip_service.py:491 (internal to grant_vip_from_tariff): calls redeem_token_with_missions + create_vip_invite_link(allow_fallback=False)

**Redeem (atomic core):**
- services/vip_service.py:309 (redeem_token_with_missions), 175 (redeem_token: SELECT FOR UPDATE on token, mark USED, extend if active sub or new sub + deact dups, clear vip_entry_*, post-commit schedule_emit EVENT_VIP_ACTIVATED)
- handlers/common_handlers.py:116 (`await vip_service.redeem_token_with_missions(args, user.id, bot=...)`); on success `await vip_service.create_vip_invite_link(..., allow_fallback=True)` + answer(vip_direct_access)
- reward/fulfillment call indirectly via grant
- Tests: unit/test_vip_service.py (many: test_redeem_*, TestVIPServiceInviteLinks test_grant_*), integration/test_vip_flow*.py, test_vip_subscription_lifecycle.py, test_vip_ritual_flow.py, test_invariants.py (I4 token single-use, I5 VIP expired), test_cross_service_atomicity (indirect), test_reward_service.py, test_fulfillment_service.py, test_common_handlers*.py

**Invite creation:**
- vip_service:456 (create_vip_invite_link: bot.create_chat_invite_link member_limit=1, expire 7d; allow_fallback returns static channel.invite_link only if flag)
- grant/resend use allow_fallback=False (strict)
- common_handlers start path: allow_fallback=True (manual fallback)
- resend_vip_invite_for_user:532

**Resend:**
- reward:451 (prior grant cases)
- fulfillment:336,791
- vip_service:526 (if already VIP)

**is_user_vip / get_user_subscription (broad fanout):**
- story_service, game_service, anonymous_message_service (guards), scheduler_service (audience), fulfillment, health (read), handlers (common, vip_user), many tests/invariants.

**Event emission (critical for nurture):**
- ONLY inside vip_service.redeem_token (lines 254-259 new sub, 296-301 extend): `schedule_emit( get_event_bus().emit(EVENT_VIP_ACTIVATED, {"user_id":..., "subscription_id":...}) )` — post-commit, best-effort, non-mutating.
- bot.py:223: `get_event_bus().register(EVENT_VIP_ACTIVATED, on_vip_activated)` (nurture_service)

**Admin paths / UI:**
- handlers/vip_handlers.py: direct VIPService() + finally close (manage tariffs/tokens/subs; tariffs_keyboard(for_selection=True), SelectTariffCallback, confirmation_keyboard, TokenStates); is_admin guards; no message forward yet. Uses logging "módulo | acción | user_id | ..."
- handlers/admin_handlers.py:55 delegates "admin_vip" -> vip_management_keyboard
- handlers/common_handlers.py + back_to_main: multi-svc (User+VIP direct); noted as debt in docs
- keyboards: tariffs_keyboard, confirmation_keyboard, vip_access_keyboard; SelectTariffCallback

**Other sends to user for VIP:**
- reward _send_vip_access_message (send + vip_access_keyboard)
- fulfillment _send_vip_access_dm
- common start: answer + vip_access_keyboard
- grant returns msg for caller

**Forward patterns (precedent only in channels):**
- handlers/channel_handlers.py:345 `@router.message(..., F.forward_from_chat)`; `forwarded_chat = message.forward_from_chat`; extracts id/title for channel reg + confirm.
- No user-forward handling anywhere. Docs mention forward for channels.
- Aiogram note (per task): for forwarded *user* messages use `message.forward_from` (legacy) or `message.forward_origin` (MessageOriginUser in v3+). Use `F.forward_from | F.forward_origin` filter + guard.

**Bot registration:**
- bot.py:318 common_router, 321 vip_router (from handlers/__init__.py:54 `from .vip_handlers import router as vip_router`)
- No change needed for new handler.

**get_service usage:**
- Promoted (services/__init__.py:82 example for VIPService; handlers/CLAUDE: "exactly 1 service" via `with get_service(XXXService) as svc:`)
- Current VIP handlers/common use direct `VIPService()` + close (precedent but hardener pushes get_service + 1 call)
- Handlers tests mock get_service or direct per file.

## Risks
(critical/medium/low + mitigation; evidence from code)

**Critical (channels-VIP + redeem atomicity):**
- **Redeem atomicity (FOR UPDATE, extension, EVENT):** redeem_token uses `with_for_update()`, tx for token USED + sub create/extend + deact other actives + user clear entry + commit then schedule_emit EVENT. grant_vip_from_tariff wraps it. New flow **MUST** call grant_vip_from_tariff (or equivalent that hits redeem) to preserve "siempre vía token" + single active + post-emit. Risk if bypass: dupe sub, token not marked, EVENT missed (nurture broken), ID duality (TG BigInt). Mitigation: reuse grant exactly; tests cover extend/new + emit (vip_service unit 455+, invariants I4/I5, cross atomicity).
- **Invite 1-use + creation fail:** create_chat_invite_link( member_limit=1, expire 7d). grant uses allow_fallback=False (errors -> partial metadata vip_activated=True, invite=None, return False + "invite failed"). common allows fallback. Fallback path in scope for blocked. Evidence: vip_service 501, tests test_grant_partial..., test_create..._fallback.
- **Send failure (blocked):** Direct send to candidate can fail (blocked, etc). Precedents: channel_grant 112 (`if "bot was blocked by the user" in str(e): warning log` no rollback), package Forbidden -> permanent, reward/fulfillment catch any -> partial mark + error return. Scope requires: if send fails notify *admin forwarder* to provide manual deep link (/start=token). Risk: admin not notified, user stuck. Mitigation: wrap send in try like reward; on except notify admin (use original forwarded msg or id).
- **Tariff selection / confirm:** Must reuse existing (tariffs_keyboard for_selection, SelectTariff, confirmation_keyboard, FSM TokenStates or new). Risk wrong tariff or no confirm -> wrong duration. Evidence in vip_handlers 211, 248+.
- **Auth / spam:** is_admin must guard message handler + all CB (current pattern lambda or explicit). Forwarded msg from non-candidate? Validate forward_from exists and not admin self? No hardcode IDs. Evidence: all vip/admin handlers use is_admin.

**Medium:**
- FSM state pollution: reuse/extend TokenStates.selecting_tariff or new states in vip_handlers (existing pattern).
- Handler rule violation: MUST be exactly 1 service call + no biz logic (e.g. `with get_service(VIPService) as svc: ok, msg, meta = await svc.grant... ; then TG send/notify`). Current common/vip mix direct + multi; hardener precedent extracts puros for <=50LOC. Intake specifies prefer grant + wrap send+notify.
- Direct vs get_service: new code should follow get_service + handlers/CLAUDE 1-service rule for testability (ports in tests).
- Logging: must use f"{__name__} | accion | user_id=... | resultado=..." (vip_handlers already does on key paths).
- Voice: new messages? reuse vip_direct_access, add if needed (e.g. confirm "forwarded user X -> activate Y tariff?").
- Extension/renew: grant already handles via redeem (extend logic); forward can be used for renewal too per scope.
- Nurture/EventBus: activation will emit as side of redeem; observer is best-effort ("MUST NOT mutate").
- Scheduler/expire: no impact (uses subs).

**Low:**
- Multi VIP channels: redeem takes first active VIP ch (internal); has_other etc support but rare.
- TZ: _ensure_aware used in redeem; tests use aware.
- ID duality: sub.user_id / redeemed_by_id = TG BigInt (from TG .id); channel_id = DB PK. Forwarded provides TG id. Handlers pass from_user.id or forward id correctly.
- Rate/Idemp: covered by global middlewares (Idempotency on CB, Throttle).

**No impact areas (evidence):** gamification atomic (credits separate), narrative progress, free channels pending, besito tx, store non-VIP.

## Affected Tests
**Must re-run and stay green (0 attributable regression):**
- Exact gold flags from root CLAUDE.md + phases/decisions.md + intake: `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "vip or TestVIP or redeem or grant_vip or subscription or TestVIPServiceInviteLinks or TestVIPServiceExpirationSupport or TestVIPSubscriptionLifecycle or TestVIPRitual or invariants"`
- Re-runs of cross atomicity (protects partials around VIP grants): `... -k "cross_service_atomicity or atomicity"`
- Reaction/daily/invariants broader: `... -k "reaction or daily or invariants or TestCrossServiceAtomicity"`
- Specific VIP test files (read via discovery):
  - tests/unit/test_vip_service.py (redeem success/used/expired/FOR UPDATE/emit on new+extend/extend date/clear entry/grant partial+success/invite member_limit=1/fallback)
  - tests/integration/test_vip_flow.py, test_vip_flows.py, test_vip_complete_cycle.py, test_vip_ritual_flow.py, test_vip_subscription_lifecycle.py
  - tests/unit/test_reward_service.py (VIP deliver paths, spies on grant/resend, partials, sent markers)
  - tests/unit/test_fulfillment_service.py (store VIP grants, send fail keeps in progress)
  - tests/handlers/test_common_handlers*.py (start token redeem + invite fallback)
  - tests/integration/test_invariants.py (I4 single-use token, I5 expired no VIP)
  - tests/unit/test_mission_side_effects.py (redeem_with_missions)
  - Also handlers tests, story/game/anon that call is_user_vip
- Broader smoke: bot import, full suite with -k filters if needed. Use TestSession/file SQLite for atomic paths.

**Coverage expectation:** Add integration for forward flow + unit for new pure helpers; no breakage to existing golds. Arch-enforcer will verify 0 crit on handler (1 svc), LOC, logging, no dupe logic.

## Files Map
- **Edit:** handlers/vip_handlers.py (new message handler for forwarded candidate msg + is_admin guard + FSM for tariff select/confirm + CB handlers for approval; use 1 svc call to grant; TG sends + blocked handling + admin notify on fail; reuse existing keyboards/voice/states where possible; logging)
- **Edit (likely):** utils/lucien_voice.py (new strings for forward confirm/activation success/fail notify to admin if no reuse covers; e.g. confirm prompt with user/tariff)
- **Edit (possible minimal):** keyboards/inline_keyboards.py (if new specific confirm keyboard for forward VIP needed; otherwise reuse confirmation_keyboard/tariffs_keyboard)
- **No/minimal service change:** services/vip_service.py (reuse grant_vip_from_tariff + create_invite + resend; only if pure helper needed for forward-specific, but prefer not)
- **Create:** tests/handlers/test_vip_handlers_forward.py or extend existing (targeted for new flow); unit for any new puros
- **No touch (preserve):** models/models.py, bot.py (router already there), services/reward/fulfillment (they use grant), common_handlers (manual flow intact), channel_grant.py (precedent only), event_bus/nurture (side effect ok), keyboards/callback_data.py (reuse SelectTariff etc), most tests (only extend)
- **Possibly touch for pattern:** services/__init__.py? no. Add to handlers/CLAUDE if new pattern.

**Ready for chain:** Handoff a gsd-planner...

## Ready for chain
Handoff a gsd-planner...

**Evidence summary (selected lines/files):**
- Redeem atomic + emit: services/vip_service.py:184 (with_for_update), 204 (USED), 225-238 (extend), 253 (schedule_emit EVENT), 296 (new), grant:491
- Send blocked precedent: services/channel_grant.py:112
- Forward precedent: handlers/channel_handlers.py:345 (F.forward_from_chat)
- Grant consumers: services/reward_service.py:465, fulfillment:369
- Start redeem: handlers/common_handlers.py:116-129
- UI reuse: handlers/vip_handlers.py:202 (tariffs_keyboard), 211 (SelectTariff), 141 (confirmation), keyboards/inline:248, callback:68
- Handler rule: root CLAUDE:68 ("llamar exactamente 1 service"), handlers/CLAUDE:53
- get_service: services/__init__.py:89
- Voice: utils/lucien_voice.py:190 (vip_direct_access), 205 (vip_activated)
- Tests gold: decisions.md + fases (exact pytest flags + -k vip/atomicity/invariants)
- Intake + scope: .planning/quick/2026-06-24-vip-forward-activation-intake.md (all constraints)

All facts traced to tool output (read/grep/rg/fd/eza/terminal logs). No assumptions beyond code. 
