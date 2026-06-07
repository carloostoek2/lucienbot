# Middleware Hardening Impact Analysis (RateLimiter + IdempotencyMiddleware)

**Date:** 2026-06-06 (analysis performed by impact-analyzer subagent)
**Task:** Pre-modification impact analysis of proposed middleware hardening (high priority per telegram-bot-hardener).
**Scope (as specified):** 
- Global register RateLimiterMiddleware (middlewares/rate_limiter.py) on DP for messages + callbacks.
- Promote IdempotencyCache (middlewares/idempotency.py) to real IdempotencyMiddleware (BaseMiddleware) for CallbackQuery: is_duplicate(callback.id) -> silent answer() + return (no handler).
- Register both *after* ErrorHandlerMiddleware (Error outer, then rate, then idemp per best practices).
- Resolve duplication: middlewares/rate_limiter.py vs legacy handlers/rate_limit_middleware.py (aiolimiter + ThrottlingMiddleware documented in handlers/CLAUDE.md + root CLAUDE.md). Decide official + document deprecation.
- Update middlewares/__init__.py as needed.
- Review + ensure clean migration/compat for manual `idempotency_cache` usages (gamification_user_handlers.py reactions; reward_user_handlers.py).
- Ensure Custodios (ADMIN_IDS) bypass for rate limiting (leverage existing pattern in config/settings.py + legacy mw).
**Non-goals:** Actual implementation of changes, GSD execution, or edits (analysis only; follow CLAUDE.md GSD enforcement for any future mods).
**Reference:** Project architecture (handlers/ only route + 1 service call, <=50 LOC funcs, no DB outside models, logging for important actions, middlewares/ for cross-cutting like ErrorHandler), Lucien voice, security (admin checks, balance, rate via Throttling historically), FSM (Redis/Memory).

## Executive Summary (Brutally Honest)
**Current state (pre-change):** 
- NO rate limiting or global idempotency active in production/dev. bot.py ONLY registers ErrorHandlerMiddleware on dp.message / dp.callback_query. 
- Legacy ThrottlingMiddleware (handlers/rate_limit_middleware.py, aiolimiter, per-user, ADMIN_BYPASS via rate_limit_config + bot_config.ADMIN_IDS, show_alert Lucien voice, cleanup) exists, has unit tests, is *documented as "global"* in handlers/CLAUDE.md + root CLAUDE.md, but is **dead/unwired code** (never imported/registered in bot.py or routers). 
- "New" RateLimiterMiddleware (middlewares/rate_limiter.py) is a minimal stub (in-mem monotonic 1s window, *only* Messages, no admin bypass, no config, no cleanup, no logging, no try/except on answer(), no cb support) — exported in middlewares/__init__.py but **zero consumers, zero dedicated tests**.
- Idempotency is *ad-hoc manual cache checks* (not middleware) in exactly 2 handlers for cbs only; cache class + global instance in middlewares/idempotency.py (TTL 60s in-mem); heavily patched in handler unit tests.
- This "hardening" is effectively *activating* long-planned but dormant protections + centralizing (good for arch: removes logic from handlers) + cleaning duplication/docs. **High blast radius** because it touches the *entire event pipeline* for all ~20 routers/domains.

**Key risks (non-exhaustive):**
- UX breakage: enabling rate (esp. if using 1s stub vs legacy 5req/10s) will throttle legitimate rapid clicks in interactive flows (narrative quiz choices, minigames/trivia/streak, store catalog->detail->buy, admin wizards, reactions, promotions "me interesa"). Users/admins perceive "broken".
- Admin lockout: new RateLimiter has *zero* bypass code. If not ported perfectly, Custodios blocked from panels (channel/VIP mgmt, approvals, etc.). High severity.
- Unhandled exceptions on throttle/dupe answer(): stub rate + proposed idemp do bare `await event.answer(...)` with no try. Failures (expired query_id, already-answered, network) bubble to outer ErrorHandler -> double-answer attempts + spurious "unhandled error" logs + wrong user messages. Legacy old mw + error mw already handle this defensively.
- Coverage gap: activating RateLimiterMiddleware (stub) with **no unit tests** for it. Handler dupe tests are brittle patches on internal handler logic.
- Distributed/prod: both rate + idemp are pure in-mem dicts (per-process). Redis is *only* for FSM (bot.py create_storage). Multi-instance (Railway scale?) or restarts = lost state, possible missed dups or uneven rate. Docstring in idemp already warns "Para producción con múltiples instancias, usar Redis."
- Arch/docs drift: handlers/rate_limit_middleware.py lives in handlers/ (violates "handlers solo enrutan, sin lógica"). Docs lie about "current" rate limiting. CLAUDE.md security section references non-active Throttling.
- Side effects: FSM state machines (wizards in store/promotion/story/mission/admin, streak, trivia, anonymous msgs, backpack), early answers in handlers (many cbs do answer() at end or early returns), minigame service limits + rate interaction, reaction business idemp (DB unique) + Telegram cb idemp (now centralized), error propagation, logging rules (50 LOC, verb+context+result, mandatory logs).
- Positive: Aligns with arch (move to middlewares/, handlers become pure routers), central dedup for *all* cbs prevents double-execution (rewards, interests, reactions, purchases, story advances), reuses config for bypass, per-user (better than misreported "global" in old security doc).

**Recommendation:** Do **not** implement direct. Use GSD (/gsd:debug or /gsd:execute-phase) for planned work. Prefer porting *mature logic* from legacy Throttling (aiolimiter, bypass, voice, cleanup) into middlewares/rate_limiter.py (make it the official RateLimiterMiddleware), deprecate (do not delete yet) the handlers/ version. Add missing tests *before* wiring. Phase the change. Update docs as part of scope.

## 1. Complete Impact Map

### 1.1 Files Modified Directly (per proposal + necessary for completeness)
- **bot.py**: 
  - Add imports: from middlewares.rate_limiter import RateLimiterMiddleware; from middlewares.idempotency import IdempotencyMiddleware (after promoting).
  - Register after Error (lines ~250-252): dp.message.middleware(Rate...()); dp.callback_query.middleware(Rate...()); dp.callback_query.middleware(Idemp...()).
  - (Possibly configure limits or pass config.)
- **middlewares/idempotency.py**: Promote IdempotencyCache to (or wrap in) IdempotencyMiddleware(BaseMiddleware). Implement __call__ for CallbackQuery only (per proposal): if isinstance(event, CallbackQuery) and cache.is_duplicate(event.id): try await event.answer(); return;  ... return await handler(event, data). Keep cache class/instance for now (compat + unit tests). Add robust try/except + logging.
- **middlewares/rate_limiter.py**: Likely *must* extend (even if "initial scope" claims register-as-is): add CallbackQuery support (isinstance + answer handling), integrate rate_limit_config + ADMIN_BYPASS + bot_config (from config.settings), add try/except around answer (like legacy), logging, perhaps cleanup/TTL or config-driven limit (1s stub is too naive vs legacy 5/10s). Current __call__ only handles Message and always passes non-Msg.
- **middlewares/__init__.py**: Update exports (__all__ + imports) to include "IdempotencyMiddleware". Possibly keep IdempotencyCache/idempotency_cache for transition/tests (or mark deprecated).
- **handlers/gamification_user_handlers.py**: Remove import of idempotency_cache + the if-dupe block (lines ~202-204) in handle_reaction (ReactionCallback). After mw, this becomes dead code / arch violation (logic in handler).
- **handlers/reward_user_handlers.py**: Remove import + if-dupe blocks (lines ~75-77 in show_available_rewards; ~109-111 in reward_detail). Also review _safe_answer / _safe_answer_alert (they catch answer fails; may become less necessary or still for normal path).
- **handlers/CLAUDE.md**: Update "Middleware" section: replace ThrottlingMiddleware doc with reference to middlewares/ (RateLimiterMiddleware + new IdempotencyMiddleware). Note deprecation.
- **CLAUDE.md** (root): Update "Seguridad" bullet on rate limiting (was "ThrottlingMiddleware con aiolimiter").
- **Documentation (ripple):**
  - docs/reporte_seguridad.md (Hallazgo #1 on rate limiter — note the report described a "global single limiter" which current legacy code does *not* have; it was per-user; update status as "addressed by per-user in middlewares + activation").
  - docs/SISTEMA_MOCHILA.md (rate limiting reuse note).
  - config/CLAUDE.md (rate config remains relevant).
  - Possibly AGENTS.md, decisions.md, rules.md if they reference.
- **handlers/rate_limit_middleware.py + its test**: Not deleted (high risk), but header comment + deprecation notice. May leave as-is for reference until full cutover.
- **No direct change (but consumers update):** config/settings.py (RateLimitConfig + ADMIN_BYPASS pattern stays authoritative), utils/admin.py (is_admin), services (no change — they already have business idemp like unique constraints on reactions/interests/progress).

**Indirect / touched by ripple (no direct edit unless doc):**
- All handler files with @router.callback_query or .message (20+ routers): now subject to global rate + (for cbs) idemp. No code change needed in most, but review for early answer() patterns or assumptions.
- models, services unchanged (good).
- Keyboards/callback_data: no impact (cbs still dispatched).

### 1.2 Consumers / Dependents of Middlewares or Cache
- **Rate limiting (current state):**
  - Legacy consumers: 0 in runtime (unregistered). Dependents: tests/unit/test_rate_limit_middleware.py (imports Throttling + hacks module globals for config bypass tests; ~8 test methods incl. admin_bypass, per-user, cleanup, none-user, limit-exceeded); handlers/CLAUDE.md + root CLAUDE.md + config/CLAUDE.md (docs); docs/reporte_seguridad.md + docs/SISTEMA_MOCHILA.md; fix_connection_leaks.py (lists the file); requirements.txt (aiolimiter dep, only used here).
  - New stub consumers: 0 runtime (only middlewares/__init__.py reexport). No tests.
- **IdempotencyCache / idempotency_cache:**
  - Runtime: handlers/gamification_user_handlers.py (import + use in handle_reaction only); handlers/reward_user_handlers.py (import + use in 2 cbs: rewards_list + reward_detail).
  - Tests: tests/unit/test_idempotency_cache.py (pure class tests on is_duplicate, TTL, mark_processed, empty id); tests/handlers/test_gamification_user_handlers.py (6 @patch("handlers.gamification_user_handlers.idempotency_cache") tests in TestHandleReaction: skip-dupe, registers, shows besitos, already-reacted alert, updates counts, closes service); tests/handlers/test_reward_user_handlers.py (~12-15 @patch("handlers.reward_user_handlers.idempotency_cache") across TestShowAvailableRewards + TestRewardDetail: every test sets return_value True/False for skip or proceed; asserts on answer calls + no edit on skip).
  - Init: middlewares/__init__.py.
  - No other handlers (confirmed via grep: only these 2 + tests).
- **ErrorHandlerMiddleware (outer reference):** bot.py (registers), tests/unit/test_error_handler_middleware.py (full coverage of success/exception/respond for msg+cb), middlewares/__init__.py. Will wrap the new ones.
- Cross: services (e.g. broadcast_service.check_and_register_reaction has its own DB-level dup guard via UniqueConstraint + atomic credit; reward/mission delivery idempotent per their CLAUDEs) — mw provides *Telegram retry* layer on top (good, defense in depth). No direct dep on mw.

### 1.3 Effect on Routers + All Domains (Focus Critical: channel_admin/VIP, gamification, narrative)
- **Routers:** All defined in handlers/*_handlers.py (router = Router(); @router.xxx decorators) + exported/ included in handlers/__init__.py + bot.py dp.include_router(...). Global dp-level mws apply *uniformly before* router dispatch/filters/FSM/handler. No per-router mws exist today (confirmed: zero .middleware calls in handlers/ sources). Adding global affects *every* message + cb path without touching router files (except the 2 for cleanup).
- **Gamification (critical):** 
  - Direct: gamification_user_router (reactions use manual idemp today; will be centralized + removed), daily_gift, balance, history, claim. game_user_router (minijuegos: dice, trivia simple/vip, streak protect/continue/retire — high spam surface, rate intended to protect per comments).
  - Services: BroadcastService (reactions), BesitoService, DailyGiftService, GameService. Business dups already guarded (e.g. unique on BroadcastReaction).
  - Tests heavily impacted (see below). Integration chains (reaction -> besitos + mission progress) will now have early global guard.
- **Narrative (critical):** story_user_router + story_admin_router. Callbacks: narrative, start/continue_story, ContinueStory/StoryChoice/QuizAnswer, discover_archetype, view archetype, achievements. Quiz is stateful (ArchetypeQuizStates); rate may interfere with rapid legitimate answers/choices. Idemp good for preventing double-advance on retry cb. VIP-gated nodes (story_service checks is_user_vip).
- **Channel admin / VIP (critical):** channel_router, vip_router, vip_user_router, free_channel_router, admin_router (some), anonymous_message_admin_router.
  - Channel: add/list/detail/config wait/invite, pending approve/cancel/approve_all/delete (many cbs with DB ids), join requests (free_channel_handlers — ChatJoinRequest events? rate may/may not apply depending on registration; proposal focuses msg+cb).
  - VIP: tariffs/tokens/subs management (admin cbs), user-side vip_area / map_of_desire / promo interests / anon msgs. High admin action volume; **bypass mandatory**.
  - Free entry, pending requests, VIP subs/rituals affected indirectly (cbs drive approvals).
  - Risk: admin cbs throttled = ops blocked; also broadcast (tied to gamif) uses channels.
- **Other domains (full blast):**
  - Store (store_user/admin): catalog, categories, product detail/preview/buy/confirm, history, search/filters, stock alerts, wizards. Many sequential cbs.
  - Promotions (promotion_user/admin): offers catalog, view/interest ("Me Interesa"), history, block, stats. Interests notified to *all* admins.
  - Missions/Rewards: mission_user (list/detail/claim), reward_user (already manual idemp), admin wizards. deliver_reward paths.
  - Trivia/streak (special promos): many admin + user cbs for config, play, protection.
  - Broadcast: send wizard (admin cbs), reactions (gamif overlap).
  - Backpack, package, category, analytics (stats/export are msg cmds), common (start/help/profile/back/cancel).
  - Effect: consistent protection, but potential for "feels slow" in browse-heavy UIs. FSM states (many *States dataclasses) processed after mw short-circuit or pass.
- **Positive uniformity:** One place for dedup/rate; easier future (e.g. per-action rates, distributed via Redis).
- **No effect:** Pure service/model layers, DB migrations, scheduler (background jobs), backups.

### 1.4 Risks (Order, Consume before other, answer() fail, side effects)
- **Middleware ordering/execution:**
  - aiogram v3: dp.xxx.middleware(M) calls wrap; first-registered = outermost (Error must stay first-registered to catch *everything* incl. exceptions from rate/idemp themselves or inner handlers). Proposal "registrar ... después de ErrorHandlerMiddleware" = correct (Error registered first, then rate, then idemp).
  - Chain example (cb): Error( try: Rate( if limit: answer+return; else: Idemp( if dupe: answer+return; else: handler ) ) except: log+respond )
  - Short-circuit good (no handler for dupe/throttle). But if rate short-circuits, idemp never sees the event (dupe protection after rate).
  - Filters (e.g. lambda cb: is_admin(...) in many admin @router) and FSM resolution happen *after* global mws? (aiogram processes mws around handler invocation). Admin filters won't prevent rate (bypass must be *inside* rate mw, before any handler/filter, using user from event or data["event_from_user"]).
- **answer() failures + robustness:**
  - Proposal idemp: bare `await callback.answer()` (silent) on dupe.
  - Current rate_limiter: bare answer on throttle for msgs (no show_alert).
  - If fails (Telegram: "query is too old and response timeout expired (400)", "callback query id is invalid", already answered by prior, bot blocked, etc.): exception propagates to ErrorHandler -> _respond_error tries *another* answer (may fail again) + logs as "Unhandled exception". User may see error msg instead of throttle/dupe ack. Legacy Throttling wraps its _on_limit_exceeded in try; error mw catches respond fails gracefully.
  - For cbs: answer() is *required* by Telegram (within ~48h, but practically immediate); failing to answer leaves "loading" on button. Silent dupe answer is correct per proposal.
  - Side: some handlers (reward) use _safe_answer that swallows answer exceptions (for normal path after edit). With mw, dups never reach; normal path still needs answer (or not, if mw could auto-ack but proposal doesn't).
- **Early answers / handler assumptions:**
  - Dozens of cbs do `await callback.answer()` (early in some error paths, at end after edit_text in most). Mw for dupe answers first + skips = prevents double-answer (Telegram forbids >1 answer per cb query_id).
  - Risk if handler assumes "I will always get to run and answer" (e.g. for side effects) — but per arch, handlers are thin.
  - Minigames/game_user: many answers + service calls with internal limits; rate + game limits may compound (intended?).
  - Story quiz: state transitions via FSM; if rate drops a choice cb, progress may appear stuck (user retries same cb.id = now deduped).
- **Rate bypass for admins:**
  - Must replicate legacy: if rate_limit_config.ADMIN_BYPASS and user_id in bot_config.ADMIN_IDS: pass through (before any limiter acquire or time check).
  - Extraction: prefer data.get("event_from_user") or event.from_user (both Message/Cb have .from_user; aiogram often populates data["event_from_user"]). Legacy uses data; new stub uses event. Inconsistent choice = risk of bypass fail for one event type.
  - Config load: bot_config.ADMIN_IDS populated in __post_init__ from env; tests hack module globals (fragile).
  - Risk of error: empty ADMIN_IDS or misparse -> all throttled (incl. Custodios). bot.py already warns if no ADMIN_IDS.
- **Side effects on FSM / states / minijuegos / other:**
  - FSM storage (Redis/Memory) independent. But rapid stateful flows (admin wizards 5-10 steps, story quiz, streak protection, store search, promo block user, package files, etc.) can be rate-limited mid-flow if user "too fast" (normal for humans on mobile?).
  - Minijuegos explicitly called out for protection (spam besitos/dice/trivia); good, but service already has per-user limits (see game_service tests).
  - Reactions: mw idemp at cb level + service atomic + DB unique = strong. But concurrent from same user (different emoji or race) handled in service.
  - No impact on scheduled jobs, startup expired subs check, on_startup notifications.
- **Memory / long-running / scale:**
  - Rate new: _last_call dict grows unbounded (no TTL like legacy _limiters + _cleanup_idle). One entry per user ever seen. For bot with thousands users over months: minor but real leak.
  - Idemp: _seen cleaned on every is_duplicate (TTL 60s); ok but in-mem only.
  - Multi-instance: as noted. If Railway runs >1 replica, or restarts, partial coverage. (Telegram likely delivers retries to same instance usually, but not guaranteed.)
- **Logging / rules compliance:**
  - Rate stub + proposed idemp have almost no logs. Per CLAUDE/rules: "Cada acción importante debe loguear: módulo, acción, user_id, resultado". Throttle hit, dupe dropped, admin bypass, cleanup = must log (use logger like error mw and legacy rate debug).
  - 50 LOC: current rate ~30 LOC; will exceed when adding cb/bypass/robustness/logging.
- **Other "could break this feature":**
  - DP init order: must before routers + polling (current code is; adding in same place safe). startup.register after mws ok.
  - aiogram version (3.24): middleware API stable (BaseMiddleware __call__(handler, event, data)).
  - Import cycles: none expected (config/settings has no mw deps).
  - Pycache / deployed: old handlers/rate pyc will linger; irrelevant.
  - Redis connect fail fallback: only affects FSM, not these mws (in-mem always).
  - Test isolation: unit handler tests patch at "handlers.xxx.idempotency_cache" (module attr); after removal of import in handler, patches will fail to find attr or have no effect. make_callback provides cb.id.
  - Security report + legacy bug: activating "fixed" per-user is good, but report's repro assumed single-limiter (which legacy never was in the source we read).
  - No rate on non-msg/cb events (e.g. ChatJoinRequest in free_channel, member updates, inline? ) — per proposal scope.
  - Voice: throttle msg in stub is plain Spanish; legacy uses elegant Lucien voice + <i>. Inconsistent post-activation.

## 2. Archivos Afectados (Summary List)
**Direct (code):**
bot.py, middlewares/idempotency.py, middlewares/rate_limiter.py, middlewares/__init__.py, handlers/gamification_user_handlers.py, handlers/reward_user_handlers.py, handlers/rate_limit_middleware.py (deprecate only).

**Docs:**
handlers/CLAUDE.md, CLAUDE.md, config/CLAUDE.md, docs/reporte_seguridad.md, docs/SISTEMA_MOCHILA.md (possibly AGENTS.md, decisions.md).

**Tests (will require update or new):**
tests/unit/test_rate_limit_middleware.py, tests/unit/test_idempotency_cache.py, tests/unit/test_error_handler_middleware.py, tests/handlers/test_gamification_user_handlers.py, tests/handlers/test_reward_user_handlers.py, tests/handlers/test_gamification_user_handlers_integration.py, multiple tests/integration/test_reaction_*.py + test_invariants.py + test_cross_service_atomicity.py (reaction paths), broader handler/integration suites.

**Other touched (no edit or doc-only):**
config/settings.py (config source of truth), all other handlers/*_handlers.py (implicit via global), services/broadcast_service.py etc. (complements), utils/admin.py, requirements.txt (aiolimiter stays), fix_connection_leaks.py, conftest.py (make_callback), run_critical_tests.py (indirect).

## 3. Tests Críticos (Explicit List to Run / Update Post-Change)
Must run **before** (baseline) + **after** any edit, plus targeted. Use `pytest -q --tb=line -k "..."` + full where possible. Mark xfail temporarily if needed during transition. Update patches/tests as part of the work.

1. **Unit middleware specific:**
   - pytest tests/unit/test_rate_limit_middleware.py (legacy; update imports/hacks if deprecate or keep parallel; verify admin bypass still works post-port).
   - pytest tests/unit/test_idempotency_cache.py (cache class; may adapt if mw internalizes).
   - pytest tests/unit/test_error_handler_middleware.py (ensure chaining with new inners doesn't break catch/respond for msg+cb).

2. **Handler units with direct idemp patches (will break on handler cleanup):**
   - pytest tests/handlers/test_gamification_user_handlers.py (esp. class TestHandleReaction: all 6+ dupe-related + reaction flows).
   - pytest tests/handlers/test_reward_user_handlers.py (all ~12-15 dupe skip + normal tests in ShowAvailableRewards + RewardDetail).

3. **Gamification / reaction integration (exercise real paths + dups at service + now mw):**
   - pytest tests/handlers/test_gamification_user_handlers_integration.py
   - pytest tests/integration/test_reaction_full_chain.py
   - pytest tests/integration/test_reaction_mission_flow.py
   - pytest tests/integration/test_reaction_mission_flow_real.py
   - pytest tests/integration/test_reaction_limit.py (docs no daily limit; still relevant)
   - pytest tests/integration/test_invariants.py (I6 reaction idempotent)
   - pytest tests/integration/test_cross_service_atomicity.py (reaction credit paths)
   - pytest tests/unit/test_broadcast_service_reaction_flow.py (service dup guards)

4. **Broader affected domains (critical + others) to catch side effects on cbs/rate:**
   - pytest tests/handlers/ -q (all: common, mission_*, store_*, story_*, promotion_*, vip_*, game, broadcast, etc.)
   - pytest tests/integration/ -k "vip or channel or story or store or promotion or mission or reward or trivia or streak or broadcast or backpack or game" --tb=line
   - Specific: test_vip_*.py (many flows), test_callbackdata_*.py (cb data validity post any change), test_free_entry_flow.py, test_mission_e2e.py, test_streak_*.py, test_trivia_*.py

5. **Full regression + critical runner:**
   - python run_critical_tests.py (or equivalent Makefile target)
   - pytest --tb=no (full suite) to confirm zero unexpected reg.
   - Targeted admin bypass: manual or new test — set ADMIN_IDS, rapid fire cbs/msgs as admin (should bypass) vs normal user (throttled).

6. **New tests required (do not ship without):**
   - Unit for (enhanced) RateLimiterMiddleware: per-user independence, admin bypass (True/False, multiple admins), msg throttle + answer, cb throttle + answer (show_alert?), cleanup if added, none-user pass, config integration, exception on answer handled.
   - Unit for IdempotencyMiddleware: first cb not dupe (calls handler), same cb.id within TTL (answers silent, no handler), different cbs independent, TTL expiry, empty id, non-cb pass-through (msgs), answer exceptions swallowed.
   - Perhaps integration: full dp with mws registered (like some e2e), simulate dupe cb.id, rapid clicks.

7. **Other:**
   - tests/unit/test_handler_service_leaks.py or similar (ensure mws don't leak services).
   - Any test that mocks bot_config or rate_limit_config.
   - Post: verify no more direct imports of legacy rate in runtime (only tests/docs).

**Note:** Many store/mission/story/promotion handler tests use make_callback but *do not* patch idemp (only reward/gamif did manual); they should continue to pass (mw transparent for non-dupes).

## 4. Riesgos y Recomendaciones de Orden/Scope
**Explicit list of handlers depending on manual idemp (will be affected / must clean):**
- gamification_user_handlers.py: handle_reaction (ReactionCallback.filter()).
- reward_user_handlers.py: show_available_rewards (F.data == "rewards_list"), reward_detail (RewardUserDetailCallback).
No others (grep confirmed). After mw, delete the 3 if-blocks + 2 imports. Do not leave "for safety" (violates "handlers solo 1 service, sin lógica").

**Risk of breaking legit cbs or rate-limiting admins erroneously:** 
- **HIGH for admins:** New rate_limiter lacks bypass entirely + uses different extraction/config. Port *exactly* (if rate_limit_config.ADMIN_BYPASS and uid in bot_config.ADMIN_IDS: return await handler). Test with real ADMIN_IDS list. Risk: Custodios can't use admin panel, approve channels, manage VIP, etc.
- **MEDIUM-HIGH for legit users:** 1s window (stub) too strict for normal use. Prefer legacy 5/10s semantics (configurable). Exempt? No per proposal. Narrative quizzes, store, streak, reactions, game plays most exposed.
- Dupe cbs dropped silently: correct for Telegram retries; if user double-taps intentionally, they get no feedback (but button "stuck" resolved by silent ack). Services still protect business rules.
- Other: rate on admin-gated cbs (the lambda is_admin filters run after?); cb.answer in mw before any state read.

**Other breakable pieces:**
- See "Risks" section above (multi-instance, memory growth, FSM interaction, answer robustness, logging/LOC violations, DP init order, aiolimiter dep, test patches at handler module, security report mismatch).
- If scale or Redis used: consider future Redis-backed rate/idemp (but out of initial scope).
- No impact on pure msg commands (/start etc.) from idemp, but rate will apply.

**Recomendaciones concretas de orden/scope (phased, safe):**
1. **Prep (doc + tests, low risk):** Update docs to reflect *current* (pre) state ("rate limiting not active; legacy unwired; manual idemp only in X/Y"). Add skeleton unit tests for RateLimiterMiddleware (as it exists today) + planned IdempotencyMiddleware. Run full baseline tests. Commit as "analysis + test prep".
2. **Enhance RateLimiterMiddleware first (in middlewares/):** Port/adapt legacy logic (aiolimiter for proper sliding, per-user + TTL cleanup, full ADMIN_BYPASS using config, support *both* Message and CallbackQuery, robust try: await answer(...) except: logger.warning, use Lucien voice for throttle msg like legacy, logging on hit/bypass). Decide semantics (keep 5/10s or proposal's 1s?). Make __init__ accept limit or read config. Keep <=50 LOC or split helpers. *This becomes the official.*
3. **Implement IdempotencyMiddleware:** Inherit BaseMiddleware. __call__ focused on cb (as proposal). Embed or delegate to IdempotencyCache. Silent answer + return on dupe. Try/except + log dupe drop. Export.
4. **Wire in bot.py:** Register Error first (already), *then* Rate on msg+cb, *then* Idemp on cb only. Use config for rate instance if needed. Update middlewares/__init__.
5. **Clean handlers:** Remove manual checks/imports in the 2 files. (Now pure: just call 1 service.)
6. **Deprecate legacy:** Add prominent comment at top of handlers/rate_limit_middleware.py + Throttling class: "# DEPRECATED since 2026-06: official is middlewares.rate_limiter.RateLimiterMiddleware (per-user aiolimiter + bypass). This file kept for tests/docs transition. Do not register or import in runtime." Do not delete (yet). Update its unit test imports if they stay.
7. **Docs sweep:** All listed md files + CLAs. Mark security finding addressed (per-user + now active + in correct dir).
8. **Test everything:** As listed in section 3. Add the new mw unit tests as part of change. Verify admin bypass explicitly (normal user throttled; admin passes even at limit). Run reaction full chains + story quiz + store buy + admin cbs flows.
9. **GSD enforcement:** Initiate via /gsd:quick (if tiny doc) or /gsd:debug (investigation + this analysis) or /gsd:execute-phase (the multi-step activation). No direct edits outside. Update this memory report post-approval.
10. **Future/scope creep to avoid:** Distributed rate/idemp (Redis), per-action rates, exempt lists, msg rate for cbs only or vice-versa. Keep initial tight.

**Decision on which rate is official:** 
- Recommend **middlewares/rate_limiter.py** (relocated + enhanced legacy logic) as the single source of truth. This eliminates duplication (one impl), follows dir structure (middlewares/ for mws, not handlers/), satisfies "decidir y documentar". Legacy file becomes archive/deprecated. aiolimiter dep justified. The stub was never complete.

**Final note on honesty vs arch:** This is the right direction (global mws after Error, centralize dedup out of handlers, admin bypass, clean 2 manual sites). But "high priority" does not mean "low risk" — global pipeline change + untested stub + dormant code + interactive UX features = treat as high-risk refactor. Validate with targeted tests + manual admin simulation before merge. Architecture (1-service handlers, logging, 50LOC) must be upheld in the middleware impls too.

---

**Handoff for next (if implementing):** Use this report + GSD. Start by enhancing + testing the rate mw in isolation. Persist updates to this file or new dated report in .claude/agent-memory/impact-analyzer/.

**References from exploration (key files read/grepped):**
- bot.py (DP creation, only Error registered, all routers, create_storage Redis/Mem, on_startup).
- middlewares/* (rate stub, idemp cache+instance, error mw, __init__ exports).
- handlers/rate_limit_middleware.py (full Throttling + aiolimiter + bypass + cleanup + voice).
- handlers/CLAUDE.md + root CLAUDE.md (outdated docs).
- config/settings.py + config/CLAUDE.md (RateLimitConfig, ADMIN_BYPASS, bot_config).
- handlers/gamification_user_handlers.py + reward_user_handlers.py (exact manual sites + _safe_answer).
- handlers/__init__.py + many *_handlers.py (routers, no per-router mws, admin lambdas, cb counts).
- tests/unit/test_*_middleware.py + test_idempotency_cache.py + handler tests (patches, make_callback cb.id).
- tests/integration/test_reaction_*.py + invariants + atomicity (business + service dups).
- conftest.py (make_callback), requirements.txt (aiolimiter), docs/*.md (security, mochila), utils/admin.py (is_admin), services/broadcast_service.py (DB guard), game_user_handlers.py (minigame cbs), story/vip/channel handlers (critical domain cbs).
- Greps for all "idempotency|duplicate|Throttling|RateLimiter|middleware" across py/md.

No implementation performed. Analysis complete via tools only.