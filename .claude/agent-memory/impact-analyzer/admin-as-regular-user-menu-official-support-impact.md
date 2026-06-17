# Impact Analysis: Make Official that Custodios Can Access/Use Normal User Menu & User-Facing Functionality

**Change proposed:** "Make it OFFICIAL that administrators (Custodios) can access and use the normal user menu and user-facing functionality (gamification, store, missions, rewards, narrative, etc.). Currently /start forces admin_menu for admins. We want to support admins switching to / acting as regular users for testing new implementations live, without breaking anything."

**Date:** 2026-06-17
**Agent:** impact-analyzer (per hardener 6-step + GSD pre protocol)
**GSD pre:** .planning/quick/gsd-impact-analyzer-admin-user-menu-official.md.log (14 lines; pre-log + discoveries + pool phrase before any file write/mod)
**Scope:** Analysis ONLY. No code changes, no proposals for edits. Exhaustive read/grep via tools before conclusion.

---

## Executive Summary

**Safe at code level for the decision (0 behavior change for non-admins):** Yes. User paths (handlers + services) have **ZERO** admin/role checks by design. All critical functions (credit/debit, deliver_reward, advance_to_node, complete_order, express_interest, claim etc.) are pure `user_id`-keyed with no "if admin" branching. Allowing admins to reach user menu will "just work" for existing flows.

**Risks: MEDIUM overall (data pollution + shared identity, LOW for breakage/atomicity/contracts):** 
- **HIGH gotcha area:** Single `User` record per `telegram_id` (role + besitos balance/tx + narrative progress/archetype/achievements + orders + pending requests + subscriptions + mission progress all live on same row). "Admin acting as visitor" == polluting the Custodio's own visitor data. No persona separation exists.
- **3 Critical Systems:** All affected for the *admin's own record* (not other visitors):
  - Gamification: own balance drained/credited via daily, games, reactions (if applicable), missions, story costs, store buys, achievements.
  - Narrative: progress, visited nodes, archetype points, endings, achievements locked to admin id.
  - Channels-VIP: pending requests, subs, VIP grants/tokens on admin id possible.
- Atomicity/EventBus: **unaffected** (per-user locks in besito ops; listeners are best-effort "MUST NOT mutate" for *any* uid).
- Other: self-purchase notifications (store), analytics/health aggregates polluted, role never mutated by user flows.

**Recommendation from analysis (no action taken):** The change is **technically feasible without breaking non-admin behavior or contracts**. To make "official" requires:
- Explicit UI switch (admin-only "👤 Ver como visitante" button in admin_menu).
- Safe navigation back (detect admin in back_to_main flows to offer return without leaking admin cbs).
- Logging "acting_as_user" on switch.
- Document "shared id = shared data; use dedicated test visitors for clean data".
- Add/ensure tests exercising admin ids through user golds.
- Consider guarding `back_to_admin` (current unguarded handler).

0 breakage expected for visitors. Data side-effects are the real "cost" of live testing on prod-like admin accounts.

---

## Detailed Impact Map (files, functions, data flows touched by the *decision*)

**Entry / decision points (current state, no change yet):**
- `handlers/common_handlers.py:151`: `is_admin = user.id in bot_config.ADMIN_IDS or db_user.role.value == "admin"` → forces `admin_menu_keyboard()` ONLY for admins on /start. (Dual check intentional per comment; differs from utils.is_admin which is ADMIN_IDS only.)
- `handlers/common_handlers.py:200` (`back_to_main`): always renders `main_menu_keyboard(is_vip)` (vip check only). NO role exclusion.
- `handlers/common_handlers.py:224` (`back_to_admin`): **NO guard** — always `admin_menu_keyboard()`. Relies on never exposing cb to non-admins.
- `handlers/common_handlers.py:247` (coming_soon): uses `main_menu_keyboard()` (no is_vip).
- `keyboards/inline_keyboards.py:32` (main_menu), `78` (admin_menu): separate; admin has no "switch to user" entry. User menu items: my_balance, daily_gift, shop, my_missions, rewards_list, narrative, offers, game_menu, backpack, vip_area (if vip).

**User flows — ALL telegram_id driven, ZERO admin exclusion (confirmed):**
- Handlers (user*): `gamification_user_handlers.py`, `store_user_handlers.py`, `mission_user_handlers.py`, `reward_user_handlers.py`, `story_user_handlers.py`, `promotion_user_handlers.py`, `game_user_handlers.py`, `backpack_handler.py`, `free_channel_handlers.py`, `vip_user_handlers.py`, `trivia_*_user_handlers.py`, `broadcast_handlers.py` (reactions side).
  - All: `user_id = callback.from_user.id` or `message.from_user.id` → pass to `with get_service(XService) as svc: svc.xxx(user_id, ...)` (exactly 1 service per handler per rules).
- Services (pure by id, no role):
  - `services/besito_service.py`: `get_balance(user_id)`, `credit_besitos(user_id, ...)`, `debit_besitos(user_id, ...)`, `has_sufficient...`, tx history. Locks + tx rows + post-credit `_schedule_besitos_awarded_event`.
  - `services/reward_service.py:231` (`deliver_reward`): branches to `_deliver_besitos` (local Besito + credit MISSION), `_deliver_package`, `_deliver_vip_access`. Idempotency via claims.
  - `services/mission_service.py:647` (`_execute_mission...`): `deliver_reward` + side effects.
  - `services/store_service.py:532` (`complete_order`): recheck balance, `debit_besitos(PURCHASE)`, stock--, deliver_package, order COMPLETE, best-effort `_notify_admins_of_purchase` (ADMIN_IDS), `run_mission_side_effects_isolated(STORE_PURCHASE)`.
  - `services/story_service.py:288` (`advance_to_node`): `can_access_node` (vip/archetype/cost balance), optional `debit_besitos(PURCHASE, commit=False)`, archetype points, progress update (current_node, visited, chapter, completed, archetype), `_check_achievements` (may `credit_besitos` for rewards), commit atomic.
  - `services/daily_gift_service.py:149` (`claim_gift`): local Besito `credit_besitos(DAILY_GIFT)`.
  - `services/broadcast_service.py:258/356`: local credit REACTION.
  - `services/game_service.py`: multiple credit (win, streak, trivia) + locals.
  - `services/promotion_service.py:241` (`express_interest`): block check, duplicate, insert `PromotionInterest(user_id)`.
  - `services/channel_service.py`: `create_pending_request(user_id, ...)`, `get_pending...`.
  - `services/vip_service.py`: redeem, is_user_vip, subs (by telegram_id/user_id).
- Models (shared):
  - `models/models.py:52` (`User`): `telegram_id` (unique), `role=ADMIN/USER`, `vip_entry_*`. Relationships: subscriptions, tokens_redeemed.
  - BesitoBalance/BesitoTransaction (user_id), Order (user_id), UserMissionProgress, UserStoryProgress (user_id), PromotionInterest (user_id), PendingRequest (user_id), Subscription (user_id), StoryAchievement etc. **All keyed to same id.**
- Event flows: `bot.py:216-222`: central reg of `EVENT_BESITOS_AWARDED` → 5 observers + `EVENT_VIP_ACTIVATED`.
- Notif consumers: `store_service.py:780` (`_notify_admins_of_purchase` using `bot_config.ADMIN_IDS`), promotion notify in handlers (ADMIN_IDS).

**Admin checks (only at admin boundaries; none inside user paths):**
- `utils/admin.py:9`: `is_admin(user_id)` == `user_id in ADMIN_IDS` (env list only).
- `services/user_service.py:79`: `is_admin(telegram_id)` == DB role == ADMIN. `set_admin`/`remove_admin` mutate role only.
- Call sites: ONLY admin_* handlers (decorators `lambda cb: is_admin(cb.from_user.id)`), analytics_handlers (for /health + admin cmds), rate_limiter tests, promotion tests, common_handlers tests. NO appearance in gamif_user/store_user/mission_user/story_user etc.
- Dual in /start only (intentional).
- `back_to_admin` and some admin kbs use `back_to_admin` cb (unguarded handler).

**Consumers of critical functions (exact):**
- credit_besitos: reward (MISSION), broadcast (REACTION x2), game (win/streak/trivia x~6), daily (DAILY_GIFT), story (_grant_achievement + some?), besito internal.
- debit_besitos: story (node cost PURCHASE, commit=False), store (complete_order PURCHASE), streak_promotion.
- deliver_reward: mission claim paths.
- complete_order: store_user purchase flows.
- advance_to_node: story_user narrative.
- express_interest: promotion_user + vip_user?
- claim daily/gift: gamif + daily.
- Side effects post: mission side (store purchase), achievements, notifs (ADMIN_IDS), health/analytics counts.

**Other flows:** Analytics (aggregates all users/balances/tx), Health (sanity counts neg_besito, UserStoryProgress, achievements, VIP subs — all include admin records).

---

## Risks & Mitigations (HIGH/MED/LOW; focus 3 crit + contracts)

**Role integrity: LOW risk**
- User flows never call set/remove_admin or touch role. /start dual remains.
- No demotion when "acting as user". Role stays "admin".
- Mitigation: none needed for this; if adding switch, keep dual check.

**3 Critical Systems:**
- **Gamification (MED/HIGH for data, LOW for contract breakage):**
  - Admin id will accumulate tx (DAILY_GIFT, REACTION if reacts on broadcasts sent to them?, GAME, MISSION rewards, PURCHASE debits for story/store, achievement credits).
  - Balance can go neg if over-test spend (no guard).
  - Health sanity will report neg if happens; analytics total_besitos polluted.
  - Atomicity preserved (besito ops use per-user_id FOR UPDATE; same id serializes own actions).
  - Event emissions from admin credits will fan to listeners — fine.
  - Gotcha: "testing live" on own account means real balance impact (no separate "test persona").
- **Narrative (MED/HIGH data pollution):**
  - `advance_to_node`, `_check_achievements`, `_grant_achievement` (credit), archetype points, visited_nodes, completed_at all mutate UserStoryProgress + UserStoryAchievement for the id.
  - If admin plays narrative for testing, their real archetype/achievements/progress polluted.
  - No exclusion.
  - Listeners (on_besitos) purely observational (log only).
- **Channels-VIP (LOW-MED):**
  - Free channel join → `create_pending_request(admin_id)`.
  - VIP redeem token (in /start or vip flows) → subs/tokens on admin id.
  - Health "active/expiring" + pending counts will include.
  - Admin can become VIP on own record (separate from role).
  - Approval flows, bans etc keyed by id — self-affecting.
  - Low because Custodios rarely request access, but for testing possible.

**Atomicity + tx integrity (LOW):**
- All high-value paths use shared-db locals inside debit/credit sites (Item 5/6/10 precedent) or get_service.
- Cross (mission claim + deliver + besito; store complete + debit + mission side) use explicit tx patterns + golds.
- Same-id admin+user actions: locks protect; no cross-id races new.
- No change to "credit survives deliver False", "post best effort".

**EventBus (LOW):**
- 5 listeners (story_service:678 `on_besitos_awarded_from_gamification`, reward:649, broadcast:528, game:1903, store:853) — all copy "MUST NOT credit/debit/mutate", best-effort, log only. "DESIRED CONTRACT" holds for any uid.
- Central reg in bot.py. schedule_emit + gather(return_exceptions=True).
- Admin credits just cause extra log lines + any future listener logic (still safe).

**Data pollution / shared telegram_id (HIGH gotcha, fundamental):**
- One User row = admin role + visitor data (balance, narrative, store orders, missions, interests, pending, vip subs).
- No "impersonate" flag or test-user separation.
- When admin tests as user: their personal visitor stats/progress/orders polluted.
- Exports (analytics CSV) will include admin rows with "visitor" activity.
- Analytics dashboard aggregates (total_besitos, new_today? no but circulation, user counts) affected.
- VIP entry state etc. mixed.

**Notifications / self-notif (MED):**
- Store purchase by admin id → `_notify_admins_of_purchase` sends to EVERY ADMIN_IDS (incl self).
- Promotion "Me interesa" → notifies ADMIN_IDS.
- Self-notification possible.

**Analytics / Health / Ops (LOW-MED):**
- `analytics_service.get_dashboard_stats`: total_users, total_besitos (sums balances), new_today (creates), active_vip.
- Exports: users + activity include admin activity as "visitor".
- `health_service.check_critical_services_sanity`: neg_besito count (global), UserStoryProgress count, achievements count, VIP active/expiring. Degraded if admin overdraws.
- No per-id filtering; admin-as-user counts as real.

**Other assumptions violated:**
- "user flows only for non-admins" — implicit only (via menu routing), not enforced in code. Decision makes it explicit/official.
- back_to_admin unguarded: current latent (any cb fire shows admin menu). Adding user↔admin nav must not leak admin cbs to visitors.
- Rate limiting / idempotency / throttling: apply to admin ids too (already do, via middlewares on all).

**Mitigations (high level, for future impl):**
- Explicit admin-only entry point + "acting as visitor" logging (e.g. "admin | acting_as_user | user_id=...").
- Document in CLAUDEs/AGENTS: "Custodios share visitor record; use dedicated test visitors for clean data".
- Optional: in back_to_main, if dual-is-admin, render main + "🔙 Volver al panel Custodio".
- Consider adding guard to back_to_admin (with graceful user message).
- For tests: use ADMIN_IDS ids in gold paths where relevant.

---

## Test Inventory Needed / Recommended (golds + extension)

**Existing golds to (re)run (0 attributable regressions):**
- `tests/integration/test_cross_service_atomicity.py` (credit survives deliver False, post-credit best effort misiones+listeners, reaction_mission, daily atomic, invariants, N806 tol, TestSession/file, 777 ids, gather return_exceptions, patch schedule_emit).
- Reaction full chain + limit tests.
- Daily gift flows.
- Story progress / narrative tests (advance, archetype, achievements, costs).
- Store purchase (complete_order debit + stock + deliver + side effects).
- Mission claim + deliver_reward (besitos + package + VIP).
- Broadcast/game reaction award + credit paths.
- Promotion interest + notify.
- Channel pending + approve flows.
- `tests/integration/test_invariants.py`, unit for each service, handler tests for user routers.

**New / extended for this decision:**
- Unit/integration exercising admin-id (from ADMIN_IDS fixture + role=admin) through:
  - daily claim, game win, reaction credit, mission reward, story advance (debit + progress + ach), store buy (debit + notif), express_interest.
  - Verify: success, correct tx source/ref, balance delta, progress rows created on that id, events emitted (but best-effort), no role change.
- Assert no admin checks leak into user services (grep or import tests).
- Back_to_main / menu navigation tests: admin dual → shows main (or enhanced), non-admin unaffected.
- Self-notif case: admin purchase triggers _notify for that id (capture).
- Health/analytics: admin activity contributes to aggregates (or explicit test that it does).
- Unguarded back_to_admin: test or note (non-admin cb fires → admin menu visible — current latent risk).
- Cross: same id interleaving (rare, admin action + user action) — ensure no deadlock on locks.
- Re-run broader smoke + bot startup (listener regs).

**Coverage note:** User services already tested with arbitrary ids (incl potential admin fixtures in tests). Extend rather than new suite.

---

## Navigation / UI Implications

**Current:**
- Admins land in admin_menu on /start (dual).
- Can reach user menu **only** indirectly if a flow renders main_menu_keyboard (back_to_main, coming_soon) or they manually trigger user cbs.
- No button from admin_menu → user view.
- User flows' backs use "back_to_main".
- Admin subs use "back_to_admin".
- coming_soon always forces main_menu (even if admin triggered?).

**To support official switch (analysis only):**
- Add to `admin_menu_keyboard()` (or after analytics/health): button "👤 Ver como visitante" (or "Probar flujos de visitantes") → new cb e.g. "switch_to_user_view" or directly "back_to_main" (but better dedicated to log).
- In `back_to_main`: after vip check, compute dual is_admin; if yes, render greeting + main_menu + extra row `["🔙 Volver al panel de Custodio", "back_to_admin"]`.
- Or provide two paths: user menu for pure visitors; enhanced for admins-acting (without changing main_menu_keyboard signature if possible).
- Keep /start behavior (admin first) — switch is opt-in for testing.
- Ensure when showing admin return button, only admins see that cb data.
- back_to_admin remains; consider future guard.
- Lucien voice: keep consistent (no "acting as" in strings unless added).

**Risk if naive:** Leaking "back_to_admin" cb data into visitor-visible keyboards → non-admins could trigger admin menu.

---

## Other Non-Obvious Discoveries

1. **Dual detection inconsistency:** /start uses `ADMIN_IDS or role=="admin"`; utils.is_admin = only ADMIN_IDS; UserService.is_admin = only role; notify paths = only ADMIN_IDS. Role in DB is "shadow" (rarely mutated in prod per grep).
2. **No prod callers of set/remove_admin:** Only tests. Admins are effectively ADMIN_IDS-driven; role column mostly vestigial for dual in /start.
3. **back_to_admin unguarded latent security:** Any TG user who can fire callback "back_to_admin" (old message, forward, crafted) sees full admin panel. Not new, but relevant when adding cross-nav.
4. **EventBus + best-effort already "admin ready":** Listeners were designed for any uid post-hardener Items 1/5/6/10. Admin credits will just exercise them more.
5. **Store notif + mission side always fire for admin purchases:** `_notify...` + `run_mission_side_effects` post complete_order. Self + others notified; store purchase missions may progress on admin id.
6. **VIP and role orthogonal:** Admin can be non-VIP or VIP independently. User menu shows "El Divan" only on is_vip (separate check).
7. **Health/observability already sees everything:** Item 11 HealthService aggregates will reflect admin visitor activity (progress counts, neg if any). Best-effort read-only.
8. **Pure helpers / 1-service contracts untouched:** No impact on hardener patterns (handlers 1 svc, puros, locals inside credit/debit only).
9. **Test fixtures use ADMIN_IDS:** Many tests patch `mock_config.ADMIN_IDS = [999]`; can leverage for new coverage exercising user paths with "admin" ids.
10. **Shared id is by design (not bug):** Telegram identity = single record. Live testing as admin-visitor is inherently "using your real visitor persona".

**Sources cited (exact paths/lines from reads/greps):**
- common_handlers.py:148-165 (/start), 200-216 (back_to_main), 224-230 (back_to_admin).
- utils/admin.py:9-11; user_service.py:79-82,84-100 (is/set/remove).
- besito_service.py:107-150 (credit),152-216 (debit).
- reward_service.py:231-290 (deliver), 649-666 (observer).
- store_service.py:532-634 (complete), 780-839 (_notify), 853-868 (observer).
- story_service.py:288-350 (advance), 363-422 (ach), 678-693 (listener).
- daily_gift:149-199 (claim); broadcast:258+ (credit),528 (obs); game:707+ (credits),1903 (obs).
- models/models.py:52-76 (User + role).
- keyboards/inline_keyboards.py:32-75 (main),78-114 (admin).
- bot.py:216-225 (regs).
- promotion_service:241+ (express); channel_service + free_channel_handlers:60-89 (pending).
- health_service:202-245 (sanity); analytics:40-77 (dash),79+ (exports).
- Multiple handlers user* + admin* for guard sites (grep confirmed zero in user files).
- Prior impact patterns + CLAUDE rules (1 svc, <=50L, logging, 3 crit, atomicity golds).

**GSD log + self-check PASSED** (pre-writes done; 0 edits to src; analysis complete).

---

**End of report. Ready for planner / next if approved. Pool phrase observed throughout.**
