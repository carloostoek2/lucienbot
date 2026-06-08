# get_service Context Manager Unification Impact Analysis

**Date:** 2026-06-07 (analysis performed by impact-analyzer subagent)
**Task:** Pre-modification impact analysis for "Unificación de manejo de sesiones / recursos con `get_service` context manager" (high-value robustness + tech debt item, first of new batch up to 4).
**Scope (as specified):** 
- Explore current state: `services/__init__.py` (get_service + _ServiceContext), grep get_service vs legacy manual `Service() + close()` (try/finally, bare, or partial), key handlers (reward_user, gamification_user, mission_user, store_user, broadcast, story_user, channel, vip, admin, common, free, backpack, etc.), services that compose/create others internally (RewardService, StoryService, MissionService, StoreService, DailyGift, Scheduler, etc.), tests (conftest, handler units/integrations, service units, atomicity tests).
- Complete impact map: count/ classify manual sites by criticality (volume, leak risk, user-facing handlers of 3 critical systems: Gamificación/Besitos/Broadcast/Daily + Misiones/Rewards + related like Store/VIP/Channels), files to modify (handlers + services + tests), effects on atomic transactions (shared db=), risks to close() behavior / explicit db passing, test impact (mocks of close/__enter__/__exit__).
- List: critical tests to run/update; prioritization (which first); specific risks (async ctx, exc during close, etc.); massive vs phased (e.g. handlers-only first).
- Recommendations for first iteration scope (manageable: max 3-4 handlers + related services).
**Non-goals:** Actual code edits, GSD execution (analysis only; any future source mods must go via /gsd:quick or /gsd:execute-phase per root CLAUDE.md), full codebase audit beyond specified.
**References:** root CLAUDE.md (arch: handlers 1-service, <=50LOC, logging; security; get_service in services), AGENTS.md (structure), models/CLAUDE.md (migrations), services/*/CLAUDE.md + handlers/CLAUDE.md (some outdated session examples), previous impact reports (middleware-hardening, channels), fix_connection_leaks.py (historical), scripts/migrate_services.py (prior partial conversion tool), test_cross_service_atomicity.py + reaction flows.

## Executive Summary (Brutally Honest)

**Current state (pre-unification):**
- Excellent modern primitive exists and is partially rolled out: `from services import get_service`; `with get_service(SomeService) as svc:` (or `db=session` for sharing). Implemented in `services/__init__.py` via `_ServiceContext` which does `svc = ServiceClass(db); ... ; svc.close() if has` in `__exit__`. Supports shared sessions for atomicity. Exported in `__all__`.
- Adoption is **incomplete/hybrid**: Many handlers (mission_user, reward_user, promotion_*, story_* main, game_user, category_admin, trivia_*, some reward_admin flows) already converted to `with get_service` (tests updated to patch `get_service` + assert `__enter__`/`__exit__`). 
- **Legacy manual dominant in critical paths**: `svc = XXXService(); try: ... finally: svc.close()` (or bare `= Service(); use(); svc.close()` without try, or no close at all). This is exactly the pattern that motivated historical `fix_connection_leaks.py` (scans for leaks, lists "ALREADY_FIXED" with try/finally including broadcast/gamif/vip/channel/store_user/common etc. -- but even those "fixed" ones are still legacy today).
- Services themselves heavily compose: e.g. RewardService/StoreService/StoryService/DailyGift always create sub-services (Besito/Package/VIP) in `__init__` passing `self.db`; MissionService creates temp `RewardService(db)` inside methods (never .close() on temps); Scheduler/StreakBridge do direct `Service(db)` + manual db.close().
- `get_service(..., db=)` support is **completely unexercised** in real code (only in __init__.py docstring). All current `with get_service` are plain (no db).
- Close() behavior is **inconsistent across services** (root cause of past leaks + future risk): 
  - Good (respect passed db, noop close if not owner via `_owns_session = db is None`): BesitoService, StoreService, StoryService, MissionService, ChannelService, VIPService, AnonymousMessageService, DailyGiftService, PromotionService, Analytics, Backpack, StreakPromotion, Trivia*, User? mixed.
  - Bad (dumb always-close, no owns check, will clobber shared db): RewardService (unconditional `db.close()` + force sub.close()), BroadcastService (`hasattr db close`), PackageService (same), GameService, some others like old User/Package paths.
- Result: ongoing leak risk (esp. in store_user product_detail with 3 bare Services no close visible; nested VIPService() inside story with get(Story) with zero close; backpack many manual closes; admin wizards), inconsistency, maintenance burden (migrate script exists but incomplete/fragile indent handling), despite middlewares + EventBus recent hardening.

**Why now (post-middleware/EventBus):** Perfect time to standardize resource mgmt, reduce historical debt (fix_connection_leaks references, multiple CLAUDE mentions of patterns), before more domains (trivia/streaks/backpack) add more sites. Aligns with "handlers solo enrutan + 1 service call".

**Key risks (non-exhaustive, brutally):**
- **Atomic tx breakage:** If any conversion or internal starts using `get_service(RewardService, db=shared)` (or Package/Broadcast), Reward's close() will `db.close()` the caller's shared session (no owns guard). Same for other dumb-closers. Current internal `RewardService(db)` in mission_service never calls close on temp -- safe by omission. Switching them to `with get_service(RewardService, db=...)` would introduce forced closes on outer sessions. Cross-service atomicity tests (reaction->besito credit->mission progress->deliver_reward) + daily gift claim paths rely on explicit shared db + controlled commits/rollbacks; pattern must not change.
- **Close() / owns inconsistency surfaces:** Converting "dumb" services without first normalizing their close() will make `with get_service(PackageService)` etc. unsafe for future db= sharing (even if current handler conversions use no-db form). Sub-closes in Reward (always) vs Story/Store (never call sub.close()) are divergent.
- **Test explosion + brittleness:** Dozens of handler unit tests patch direct `handlers.xxx.XXXService` and assert `.close()`. Converted handlers use `get_service` patch + `mock_get_service.return_value.__enter__.return_value=...` + `__exit__.assert_called`. Switching requires test rewrites (see 50+ patches in test_store_user_handlers.py alone). Service unit tests + integrations (cross_atomicity, reaction_mission_flow, mission_e2e, gamif integration) create services directly with db_session/TestSession + explicit try/finally svc.close() + db.close() -- mostly unaffected but sensitive to close side-effects. No dedicated current test for get_service(db=) behavior.
- **Nested / multi-service handlers:** Story user, reward_admin, store_user, vip_user, backpack create secondary services (VIP/Package/Besito) inside or alongside main. Conversion must wrap them too or leave leaks. Using nested `with get_service(VIPService) as v:` (separate session) vs `with get_service(VIPService, db=outer.db)` (share, noop on inner close) -- latter better for consistency but requires db= (unexercised) + all involved services must respect owns.
- **Async / exception / lifecycle:** Handlers async but services sync; `with` (sync ctx) around awaits is fine (current pattern in gamif reaction handler). __exit__ close exc replaces block exc (same as legacy finally). __del__ in some services (Reward, DailyGift, Package, User) + double-close risk (mostly idempotent via None/db=None). Background (scheduler) + EventBus listeners use direct; must not touch or risk jobs.
- **Partial conversion debt:** Some "converted" handlers (story_user) still have bare VIPService() inside with get(Story) -- no close = leak. reward_admin/mission_admin/store_admin have bare Package/Reward in wizard helpers. migrate_services.py only targeted specific list, not comprehensive.
- **Volume + blast:** ~15-18 handler files still have manual, ~80-120+ individual Service() sites (rough count from greps: broadcast~7, channel~12, vip_handlers~12, gamif_admin~10, gamif_user~5, store_user~15+, vip_user~10, backpack~12, admin/common/free~8, reward_admin~5 Package/VIP, mission_admin~2 Reward, story nested~3+, promotion/store_admin~3). Plus service internals. Changing touches user paths (balance, gift, reactions, buys, VIP, backpack, missions/rewards) + admin panels. High user-visible if breaks.
- **Arch/docs:** handlers/CLAUDE.md shows outdated `with get_session() as session: service=BesitoService(session)` example (vs canonical get_service). Some service docs recommend get_service for fresh. No widespread db= yet.

**Benefits if done right:** Eliminates entire class of leaks (historical pain point), uniform resource mgmt, easier future shared-tx in handlers (e.g. atomic buy flows), aligns with "1 service call" rule + middleware centralization, reduces try/finally boilerplate (50LOC funcs), better testability via context.

**Verdict:** High value, medium-high risk if scope too broad or Reward/Package/Broadcast closes not normalized first. **Phased mandatory** (handlers first, no db= initially; fix dumb closers in parallel or pre; services internals later). Do not massive-sweep all 15+ files.

## Mapa de Impacto Completo

### Manual vs Modern Sites (from broad grep + targeted reads on handlers/services 2026-06-07)
- **Modern `with get_service` (adopted, good):** 
  - Handlers: reward_user_handlers.py (MissionService, full), mission_user_handlers.py (full), game_user_handlers.py (GameService + StreakPromotionService, many), category_admin_handlers.py (Package, 9+), promotion_admin_handlers.py (Promotion, ~15 incl nested), promotion_user_handlers.py (Promotion, 5), story_user_handlers.py (StoryService, 9+), story_admin_handlers.py (many), reward_admin_handlers.py (RewardService, 5+ in wizard), store_admin_handlers.py (Store, many), mission_admin_handlers.py (Mission, many), trivia_* (TriviaCategory + Streak), broadcast? no.
  - Services: zero (they use direct or compose in __init__).
  - Tests: heavily updated for the above (patch get_service + __enter__/__exit__ in test_mission_*, test_store_admin, test_story_*, test_promotion_*, test_reward?).
- **Legacy manual (still present, target):**
  - **Bare or partial/no-close (worst leaks):** store_user_handlers.py (many: Besito bare in shop_menu, Store/Package/Besito triples in product_detail + direct_buy flows + search/filters with no close in several paths; some try/finally in catalog but incomplete), story_user_handlers.py (VIPService() bare inside 2x `with get(Story)` -- zero close on VIP), reward_admin_handlers.py (PackageService bare in show_package_selection + helpers; VIP bare in tariff select), mission_admin_handlers.py (RewardService bare x2 in freq/reward select), promotion_admin_handlers.py (Package bare in package select), store_admin_handlers.py (Package bare), backpack_handler.py (many bare Backpack + explicit .close() not in try in all paths; VIP bare + close in one).
  - **try/finally close (legacy "good" but to unify):** broadcast_handlers.py (Channel x2 + Broadcast x4-5 incl reactions), channel_handlers.py (~12 Channel), vip_handlers.py (~12 VIP), gamification_admin_handlers.py (Broadcast ~6 + DailyGift ~4 + Besito), gamification_user_handlers.py (Besito x2 + Daily x2 + Broadcast 1), vip_user_handlers.py (~8-10: VIP x4 + Promotion x3 + Anon + Besito), admin_handlers.py (User + Channel/VIP), common_handlers.py (User + VIP, closes in finally but some ifs), free_channel_handlers.py (User + Channel, conditional closes), store_user_handlers.py (remaining try/finally for some), gamif_user remaining.
  - Approx total manual creation sites in handlers: 80-120+ (concentrated; rough: gamif_user 5, store_user 15+, broadcast 7, channel 12, vip_handlers 12, gamif_admin 10, vip_user 10, backpack 12, reward_admin 5+, mission_admin 2+, story nested 3+, others 10-15).
  - Services internal manual (should mostly stay, or targeted): scheduler_service.py (many Channel/VIP/Backup + db.close()), mission_service.py (RewardService(db) x2 inside get_available... no close on temp), streak_scheduler_bridge.py (Streak(db) + db.close()), daily_gift (lazy besito), store/reward/story (compose in __init__), backpack_service? listed in files, game etc.
- **Criticality classification (volume of use + leak risk + 3 systems):**
  - **Tier 1 (highest, attack first):** Gamificación paths (besitos + broadcast reactions + daily gift) -- gamification_user_handlers.py (user-facing balance/history/gift/reaction -- core "3 systems" gamif), broadcast_handlers.py (reactions + admin send, used by gamif), gamification_admin_handlers.py. High call volume, user clicks, past reaction atomic bugs.
  - **Tier 1 econ:** store_user_handlers.py (shop, catalog, direct buy, purchase_history -- touches Besito + Store + Package; partial fixes noted historically; purchase = money-equivalent, stock, atomic debit risk). 
  - **Tier 2 rewards/missions:** reward_admin_handlers.py + mission_admin_handlers.py (wizards create missions/rewards using Package/Reward/VIP bare), reward_user (already modern but related), mission_user (modern).
  - **Tier 2 VIP/Channels/user entry:** vip_user_handlers.py (VIP checks + promo + anon msg + besito), vip_handlers.py, channel_handlers.py, common_handlers.py + free_channel_handlers.py (start flows, user/vip create -- entry point leaks bad).
  - **Tier 3/new:** backpack_handler.py (mochila, many user queries + deliver + VIP; recent, high manual close sites), story_user (narrative, already main modern but nested leak), admin/store_admin/promotion_admin (wizards, secondary).
  - Services: Reward/Store/Story (composers for rewards/store/narrative critical), Mission (internal Reward for reward delivery in missions), Broadcast/Besito/Daily (gamif), Scheduler (system, leave mostly).

### Files That Would Be Modified
- **Handlers (~8-12 for first + full):** gamification_user_handlers.py, store_user_handlers.py, broadcast_handlers.py, reward_admin_handlers.py, mission_admin_handlers.py, backpack_handler.py, vip_user_handlers.py, channel_handlers.py, vip_handlers.py, common_handlers.py, free_channel_handlers.py, story_user_handlers.py (for nested), store_admin/promotion_admin (secondary Package), gamification_admin. (Add `from services import get_service`; replace `= FooService()` blocks + remove closes with `with get_service(FooService) as foo:` ; handle multi-service in one func with sequential/nested with; fix imports from direct to include get_service).
- **Services (related, for safety/consistency):** RewardService.py (normalize close to use _owns_session like peers -- critical pre-req if touching reward_admin or mission internals), PackageService.py (add owns, to support future), BroadcastService.py (add owns), GameService.py, UserService.py (dumb closers); optionally clean MissionService temps or Store/Reward compose closes for consistency; no change to good ones (Besito etc.); scheduler/streak_bridge leave or minimal.
- **Tests (high volume):** 
  - Handler units: test_gamification_user_handlers.py (switch ~10-15 patches from direct Besito/Daily/Broadcast to get_service + __enter__ mocks; also integration version), test_store_user_handlers.py (50+ patches for Besito/Store/Package -- biggest), test_reward_user_handlers.py / test_mission_* (if scope touches, already get_service style), test_story_user_handlers.py etc.
  - Others: test_common_handlers*.py, test_backpack? (if exists direct), promotion/store_admin handler tests (some already get_service).
  - Service units + integration: test_reward_service.py, test_broadcast_service*.py, test_package_service.py, test_store_service.py, test_mission_service.py, test_cross_service_atomicity.py (direct db= creations + explicit closes; verify no regression on atomic), test_reaction_mission_flow*.py, test_mission_e2e.py, test_gamification_user_handlers_integration.py, possibly test_backpack_service.py, test_vip_service etc. Conftest db_session fixture unchanged (real session, expire_on_commit=False for multi-commit flows).
  - No change or minimal: pure service units that never hit handlers, e2e, callbackdata tests.
- **Other:** Possibly handlers/CLAUDE.md (update example to canonical get_service, not get_session+ctor), services/ docs if mention, scripts/migrate_services.py (deprecate or improve), run_critical_tests.py / Makefile if specific, root decisions.md. No models changes. bot.py/middlewares untouched (services not registered there).

### Effect on Atomic Transactions (shared db)
- Current get_service supports `db=` (passes to ctor; context only closes if the service _owns). Ideal for handler-level atomic like "debit besitos + create order + deliver" in one session.
- **Zero current usage** of db= form in with get_service (all plain). Atomicity today achieved via: (a) internal service composition (Store creates Besito(db) sharing), (b) explicit `FooService(db=shared)` in tests/scheduler/mission internals, (c) get_db_session() raw for some.
- Conversion of plain handlers (no db passed) has **no effect** on existing atomics (new owned session per with, like legacy).
- **Risk only on db= adoption or touching Reward/Package/Broadcast:** e.g. if mission internals converted to with get(Reward, db=mission_db), Reward.close forces close. Cross atomic test explicitly re-creates TestSession after setup commits because "credit_besitos + broadcast commit + mission increment + deliver credits" + "SessionLocal() in RewardService etc." -- any change to close ownership breaks the "re-query post-commit" + partial failure invariants.
- Recommendation in design: for first phase use only no-db `with` (safe); add db= support later with tests; normalize all closes first.

### Risks to close() Behavior / Explicit db Passing
- Inconsistent owns: converting a handler that does `with get_service(RewardService) as r:` (no db) works today (Reward creates own, its close closes it). But makes Reward "owning" behavior different from Store/Story (Reward closes subs unconditionally; others don't call sub.close()).
- Passing db to dumb closer = clobber (see above).
- Explicit db in services (e.g. `RewardService(db)` in mission) + no .close() = current "safe" for shared; wrapping changes contract.
- __exit__ always calls close if hasattr (even on error); same as finally.
- Some services set db=None in close; others not. __del__ can fire after.

### Impact on Tests
- High: handler tests for legacy files are written against direct patch + .close() assert (gamif_user, store_user -- 60+ patches total). Must rewrite to get_service style (see mission_user tests as template: mock_get_service.return_value.__enter__.return_value = mock_instance; ... ; mock_get_service.return_value.__exit__.assert_called_once()).
- Medium: integration/atomic tests use real db + direct Service(db=TestSession) + manual close in try/finally -- keep as-is (they test service internals + cross commits, not handler resource mgmt). Adding get_service(db=) tests would be new.
- Service units: direct ctors + .close() calls in fixtures/tests; normalizing owns in dumb services won't change no-db behavior (close still happens).
- Potential new tests needed: test get_service itself (in services? or unit), db= sharing case, close on exception, nested withs.
- Conftest unchanged.
- Risk: test updates introduce bugs if mock setup wrong (e.g. __exit__ not called on early return).

## Tests Críticos (Must Run / Update)

**Handler unit (must update mocks + re-verify behavior/close):**
- tests/handlers/test_gamification_user_handlers.py (and _integration.py) -- direct Besito/Daily/Broadcast patches + close asserts.
- tests/handlers/test_store_user_handlers.py -- 50+ Besito/Store/Package patches; covers buy flows critical.
- tests/handlers/test_reward_user_handlers.py , test_mission_user_handlers.py , test_story_user_handlers.py , test_promotion_user_handlers.py (style reference + any scope overlap).
- tests/handlers/test_common_handlers.py + integration, test_backpack if direct.

**Admin/handler units for secondary:**
- test_mission_admin_handlers.py , test_reward? (already some get_service), test_store_admin_handlers.py , test_promotion_admin_handlers.py , test_story_admin_handlers.py.

**Integration + atomic + flows (run to verify no regression on tx/closes/commits; update only if direct handler calls change):**
- tests/integration/test_cross_service_atomicity.py (core for besito/mission/reward/broadcast; explicit db= + closes + partial failure).
- tests/integration/test_reaction_mission_flow*.py , test_reaction_full_chain.py , test_mission_e2e.py , test_reaction_limit.py.
- tests/handlers/test_gamification_user_handlers_integration.py.
- tests/integration/test_vip_*.py , test_free_entry_flow.py (entry + vip), test_callbackdata_* for affected.
- tests/integration/test_store? (indirect via flows).

**Service units (run full; update if we normalize close in Reward/Package/Broadcast/Game):**
- tests/unit/test_reward_service.py , test_broadcast_service*.py (incl reaction_flow), test_package_service.py , test_store_service.py , test_mission_service.py , test_besito_service.py , test_daily_gift_service.py , test_backpack_service.py , test_story_service.py , test_user_service.py , test_game_service.py , test_analytics_service.py etc.
- tests/unit/test_handler_service_leaks.py (if source exists; pyc present historically -- search showed none, perhaps removed post-prior fixes).

**Other / full runs:**
- pytest -k "gamification or store or broadcast or reward or mission or backpack or atomic or leak or cross_service" -q --tb=line
- Use run_critical_tests.py
- Service-specific: pytest tests/unit/test_*_service.py -q
- Full relevant: pytest tests/handlers/ tests/integration/ -k "not trivia" (to focus) or targeted.
- Verify with real DB? (but sqlite in mem/file per tests).
- Post-change: any e2e/test_lucien_voice etc. if flow hits.
- Manual: check no double-close, db closed only for owners, no leaks under exception paths (use the old fix script idea or add monitoring).

Run before (baseline) + after each phase. Update only the handler tests for converted files; leave service tests creating direct (they are valid for internal + test db sharing).

## Recomendaciones de Diseño y Scope Propuesto para Primera Entrega

**Design principles / gotchas to enforce:**
1. **All handler top-level creations go through `with get_service(XXXService) as` (no bare, no manual try/finally).** One service per logical block. Remove .close() calls.
2. **Prefer sequential/nested `with` for multi-service in one handler func** (e.g. product_detail: with Store, with Package, with Besito -- or better refactor to single Store which already composes Besito/Package internally, then delegate).
3. **For nested in already-converted (e.g. story_user VIP inside Story):** convert to `with get_service(VIPService) as vip:` (separate session for read is fine, or later `db=story_service.db` once safe). Never leave bare.
4. **Normalize dumb closers as pre-work or in-scope:** Add `_owns_session = db is None; self.db = db or SessionLocal()` to RewardService, BroadcastService, PackageService, GameService, UserService (and update their close to `if self._owns_session and self.db: ...; self.db=None`). For Reward, keep sub-closes (or make conditional); this makes db= future-proof without changing no-db semantics.
5. **Do not introduce db= in first phase handlers** (keep plain `with get_service`); document the pattern for later (e.g. atomic buy in store). Add test for get_service(db=) sharing + owns.
6. **Inside services:** leave most composition as-is (passing db is the "internal get" equivalent). For mission's temp Reward(db): either leave (no close needed), or wrap locally with with get_service(RewardService, db=db) **after** Reward normalized. Same for scheduler.
7. **Imports:** `from services import get_service` (plus the Service if needed for type? but not usually). Update __all__ already has it.
8. **Logging:** Keep existing "module | action | user_id= | result" per CLAUDE rules.
9. **Voice:** No change.
10. **Edge:** Idempotency mw already central; with will run inside. Early returns / exceptions: context guarantees close. For FSM wizards spanning (reward_admin etc.): the withs are per-step, fine (state in FSM).
11. **If using db= later:** only with services that respect owns; prefer top-level service that composes (Store over separate Besito+Package).
12. **Deprecate legacy:** after, remove manual patterns; update fix_connection_leaks.py or delete; improve migrate script or remove.

**Phased vs massive:** **Phased strongly recommended.** Massive across 15+ handlers + tests + services = high churn, high chance of missing a nested leak or test mock, regression in atomic flows, long review. Handlers first (as migrate script intended), services close-normalization in parallel or pre (small, high leverage), internals/scheduler last (low user risk). "Handlers user-facing + 3 critical systems" per spec.

**Proposed first iteration scope (manageable, ~3-4 handlers + related):**
- **Primary handlers (user-facing + gamif/besito/broadcast/store critical):**
  1. handlers/gamification_user_handlers.py (BesitoService, DailyGiftService, BroadcastService) -- user balance, tx history, daily gift claim, reaction handling. High volume, touches core gamif system.
  2. handlers/store_user_handlers.py (Besito + Store + Package) -- shop menu, catalog, categories, product detail/buy, history, search/filters. Economy-critical, had partial fixes + current bare multi-service leaks.
  3. handlers/broadcast_handlers.py (ChannelService + BroadcastService) -- start, reactions flow (shared with gamif_user), emoji mgmt. Complements 1.
- **4th (rewards/mission critical or to round):** handlers/reward_admin_handlers.py (keep its Reward with get; convert Package/VIP bare in selection flows) or handlers/backpack_handler.py (many sites, mochila user data). Or mission_admin for symmetry. Limit to avoid >4.
- **Related services (must include for safety):**
  - Normalize close() + owns in: RewardService.py (pre-req if including reward_admin or future mission), BroadcastService.py (used in scope), PackageService.py (used in store/reward).
  - Optional light: audit/fix any bare in story_user if story in scope; leave scheduler.
- **Tests to update in scope:** The unit + integration for the 3-4 handlers (gamif_user full, store_user full -- biggest effort here). Run all listed critical above.
- **Out of scope for iter 1:** vip_*/channel/common/free (entry but lower gamif priority), full backpack/story nested unless chosen as 4th, admin panels beyond reward, all service internals beyond the 3 closers, db= usage, scheduler, raw get_db_session sites, docs updates (can be follow-up).
- **Size estimate:** 3 handlers (~20-40 sites converted), 3 service close normalizations (small targeted edits), 2-3 test files major rewrite (store/gamif), plus run/update others. Fits "max 3-4 handlers + related". Verifiable with targeted pytest.
- **Order in phase:** 1. Normalize the 3 dumb closers + add basic get_service test if missing. 2. Convert gamification_user (test it). 3. Store_user (test). 4. Broadcast. 5. Verify atomics + full relevant suite + any leak scan.
- **Validation:** Before/after diff on close calls; run atomicity tests; perhaps add a temp "leak detector" in test (count sessions or use patch on SessionLocal). Post: update CLAUDE if needed.

**Next batch items (suggestions for up to 4 total):** Phase 2: remaining user/admin (vip_user, backpack, channel, story nested, gamif_admin, mission_admin); Phase 3: service internals + db= adoption + shared tx examples in store/reward flows + test coverage for get_service(db=); Phase 4: cleanup (migrate script, old fix script, docs, deprecate direct ctors in handlers).

This unifies the excellent pattern, kills debt, without overreach. Analysis complete; ready for GSD if proceeding.

**Persisted for future batches:** See MEMORY.md index + this file. References prior middleware/channels reports for context on debt items.
