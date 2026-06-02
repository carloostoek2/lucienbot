# Pre-GSD Canales: Approval Flows Impact Report (ChannelService + Scheduler + Handlers + ID Duality)

**Agent:** impact-analyzer  
**Date:** 2026-06-01 (analysis run)  
**Task:** Analyze impact of potential changes/new tests for foundational Canales (Pre-GSD) approval flows. Target areas as specified. Pre any test writing or design for contract pilots. Thorough on ID duality + cross effects.  
**Inputs:** Full codebase exploration via list_dir/grep/read_file/run_terminal (DB schema), prior agent memory (channels-*.md), docs (CLAUDEs, AGENTS, fases_refactor_testing.md, refactor_testing.md, architecture.md), tests, models, etc. GSD log prepended before writes.  
**Scope:** Call sites, existing tests, risks ("changed A broke B"), mandatory tests to run/update, arch violations/bypasses, "today's code vs desired contract".  
**No changes to prod code**; analysis + memory persistence only.  

---

## Summary of Key Components and Their Consumers

### 1. Models: PendingRequest + Channel (ID Duality Core)
- **Channel** (models/models.py:78-102):
  - `id`: Integer PK (surrogate, internal).
  - `channel_id`: BigInteger unique (Telegram chat ID, e.g. -1001..., used for all bot API: approve_chat_join_request, ban, send_message to chat, invite links).
  - Other: channel_type (FREE/VIP), wait_time_minutes (FREE only), welcome/approval_message, invite_link, is_active.
  - Relations: subscriptions (via DB id), pending_requests (via DB id).
- **PendingRequest** (models/models.py:169-185):
  - `id`: PK.
  - `user_id`: BigInteger (stores Telegram user ID value; **no FK** declared to users.telegram_id or users.id).
  - `channel_id`: Integer FK("channels.id") = **DB PK** (not TG).
  - status: "pending"/"approved"/"cancelled".
  - scheduled_approval_at, approved_at, requested_at, username/first_name.
  - Relation: channel (back).
- **ID Duality Facts** (confirmed via code + runtime DB inspect):
  - Pending/Subscription.channel_id FK targets channels.id (PK).
  - BroadcastMessage.channel_id FK targets channels.channel_id (TG) -- **inconsistent design**.
  - User duality parallel: User.id (PK small) vs telegram_id (bigint); Pending.user_id always uses telegram value in real paths.
  - Service methods blur: `get_channel_by_id(channel_id)` = TG lookup; `get_channel_by_db_id(db_id)` = PK; but `create_pending_request(..., channel_id)` and all pending_* take/ use **DB PK** (internal get_by_db_id + filter on Pending.channel_id).
  - Callers must convert: free handlers do `get_by_id(TG=chat.id)` then `channel.id` (PK) for pending ops + pass `chat.id` (TG) explicitly to schedule_free_welcome.
  - Callbacks: Channel* (detail, pending, approve_all, etc.) carry **DB PK**; BroadcastChannelCallback carries **TG**.
  - DB inspect (local SQLite via engine): pending_requests cols lack 'approval_attempts' (stub mig 73702d0a06be claims "applied in prod" only); channels.channel_id has no enforced unique in this DB (model declares it).
  - Cross effect: VIP subs, bot ban/expire, common_handlers invites, broadcast sends all rely on correct .channel_id (TG) from Channel obj.

Consumers of models directly (bypass service):
- services/channel_service.py (PendingRequest() ctor, queries).
- scheduler_service.py (via returned objs from service.get_ready + direct attr set).
- Tests only (conftest, unit_channel, integ_free_entry).
- No other services import PendingRequest.

### 2. ChannelService (services/channel_service.py:123-228 for pending; full 1-228)
Key methods targeted:
- `create_pending_request(user_id, channel_id: DB_PK, username, first_name) -> PendingRequest`: Validates via get_by_db_id, computes scheduled = now + wait, stores DB channel_id. (Lines 123-144)
- `get_pending_request(user_id, channel_id: DB_PK) -> Pending | None`: Filters pending status + exact user/channel DB. (146-157)
- `get_pending_requests_by_channel(channel_id: DB_PK)` (159)
- `get_all_pending_requests()` (168)
- `get_ready_to_approve() -> list`: pending + scheduled_approval_at <= now. **DB only, no TG**. (173-181)
- `approve_request(request_id) -> bool`: direct mutate status+approved_at + commit on the row. **DB only**. (183-192)
- `cancel_request(user_id, channel_id: DB_PK) -> bool` (194)
- `approve_all_pending(channel_id: DB_PK|None) -> int`: bulk query + loop direct mutate status+at + single commit. **DB only, no TG approve, no welcome**. (204-219)
- `count_pending_requests(channel_id=None)` (221)
- Supporting: get_channel_by_* , create_channel (takes TG as 'channel_id' param!), etc. Uses manual SessionLocal + close pattern (legacy, not get_session).

**Note:** approve_* / get_ready never touch TG bot API or send messages. Pure state flip.

### 3. Scheduler Job: _process_pending_requests (services/scheduler_service.py:99-150)
- Registered in SchedulerService.start() (bot.py:189 calls get_scheduler; scheduler:324) as IntervalTrigger(seconds=30), id="approve_join_requests".
- Impl:
  - db=SessionLocal(); svc=ChannelService(db); ready=svc.get_ready_to_approve()
  - for each: channel = request.channel (rel load); if not active continue
  - bot.approve_chat_join_request(chat_id=channel.channel_id (TG), user_id=request.user_id)
  - **DIRECT:** request.status="approved"; approved_at=now; db.commit()
  - Then: send free_entry_welcome + optional invite_link via bot.send_message (with social keyboard). (Comment 122-124: "handle_member_join NO se dispara cuando bot aprueba via API")
  - On err per-req: rollback; outer finally close.
- Also owns: _send_free_welcome_job (68-96: ritual msg 30s after join_request; uses get_by_id(TG); scheduled via schedule_free_welcome which stores TG in job kwargs).
- schedule_free_welcome called **only** from free_channel_handlers:84 (with TG).
- Other jobs (expire subs) use VIP paths + TG ids.
- **Bypass:** Does not call svc.approve_request(); mutates directly (and uses raw SessionLocal, not injected consistently).
- Relies on objects from svc query staying bound to the session.

### 4. free_channel_handlers (handlers/free_channel_handlers.py:23-178)
- `handle_join_request` (chat_join_request router):
  - UserService.get_or_create (TG ids).
  - ChannelService(): get_by_id(chat.id = TG); if not or inactive return.
  - get_pending(user.id, channel.id=DB); if exists -> send impatient msg.
  - create_pending(..., channel_id=channel.id=DB)
  - scheduler = get_scheduler(); schedule_free_welcome(user.id, chat.id=TG)  << explicit comment 80-81 on duality handoff.
  - finally close both services.
- `handle_member_leave` (LEAVE_TRANSITION): get_by_id(TG); cancel(user, channel.id=DB); send cancel msg.
- `handle_member_join` (JOIN_TRANSITION): get_by_id(TG); get_pending(user, DB id); if pending: svc.approve_request(pending.id); send welcome + invite.
- **Arch note:** Calls 2 services + direct get_scheduler(); has biz logic (dup check, inactive, msgs); >50 lines for join_request. (Per handlers/CLAUDE + root rules: "exactly 1 service", "no biz logic". channels/CLAUDE notes as "only handler with direct commit" -- now outdated, commits are in svc; scheduler does the direct mutate.)
- Only entry for free join requests. Member join fires for *non-bot* approvals (e.g. manual TG client approve by custodian?).

### 5. channel_handlers.py (admin panel for "approve all" etc.)
- Uses ChannelService() + closes.
- approve_all_requests(cb): calls approve_all_pending( channel_id from ApproveAllCallback = DB PK from list using ch.id )
- view_pending: get_by_channel(DB)
- count in detail + admin_analytics (admin_handlers.py:103 no-arg count)
- All channel mgmt cbs carry DB id; create_channel receives TG from forwarded chat.

### 6. Call Sites / Consumers (exhaustive from greps; no other services bypass for approve paths)
**Service methods (pending/approve):**
- free_channel_handlers.py: get_pending(2x), create_pending, cancel, approve_request(1x via member_join).
- channel_handlers.py: count(1), get_by_channel(1), approve_all(1).
- admin_handlers.py: count(1).
- scheduler_service.py: get_ready_to_approve(1).
- **No VIP direct on these** (VIP uses subs + get_vip_channel which bypasses ChannelService entirely, queries Channel model direct).
- bot.py: no direct (only scheduler start + some VIP ban using sub.channel.channel_id).
- Tests: heavy direct (see below).

**Scheduler jobs:**
- bot.py / SchedulerService: registration + get_scheduler calls (handlers/free only for schedule_free).
- Direct execution only in integ test_free_entry (patched).

**Cross / indirect:**
- VIP flows: common_handlers (get_vip_channel -> .channel_id TG for invites), bot.py startup checks, vip_service (direct Channel query + sub.channel_id=DB), scheduler expire (ban TG), reward/game wrappers (is_user_vip).
- Broadcast: TG ids throughout (separate cb path).
- No other domains call channel approve paths.

**Total ~20+ non-test call sites; 100+ test sites touching IDs/flows.**

---

## High-Risk Change Areas ("changed A and broke B")

1. **approve_all_pending / approve_request strengthened to do full TG approve + welcome** (desired contract?):
   - Breaks: Admin panel expectations (currently "mark approved in system" only; custodians may use it for early approve without granting membership yet?).
   - Breaks current tests: unit/test_channel_service.py (pure DB, no bot mock, would require bot injection or skip TG).
   - Breaks: scheduler path (if now duplicate approve? race on join_request already approved?); member_join path may double-send welcome.
   - Risks: Needs bot in service (how? global? passed?); session/tx atomicity (approve TG then DB? or reverse?); errors (TG fail -> rollback DB?); rate limits on bot API; for bulk approve_all: many TG calls + welcomes in one handler tick.
   - "Sacosita" (ghost/stuck): Users marked approved but not actually in TG channel if not using scheduler path.
   - Cross: If service now calls bot, then jobs using explicit ChannelService(db) + patch(SessionLocal) in pilots must also patch bot.
   - ID: Would still need correct channel.channel_id (TG) from the DB-loaded request.channel.

2. **Scheduler _process_pending_requests change (e.g. call service.approve instead of direct mutate)**:
   - If approve_request changes semantics (e.g. adds attempts col, no auto-commit, side effects), current direct in scheduler (and tests that sim approve via service) diverge -> phantom state, missed welcomes, inconsistent approved_at.
   - Current bypass means approval_attempts (if wired) never set by auto path.
   - Rollback per-req in scheduler: if move to service, service must not commit inside or handle partials.
   - Test pilots rely on direct execution + post-verify on PendingRequest model.

3. **ID duality fixes/renames (e.g. clarify params, change cb payloads, add get_by_telegram)**:
   - Massive: 20+ handlers + ~50+ test call sites/asserts break (free uses DB for pending after TG lookup; admin cbs are DB; broadcast TG; fixtures mix .id/.channel_id/.telegram_id).
   - Callback change = breaking for live users (pending cbs in TG chats become unparsable).
   - Wrong ID to schedule_free_welcome = ritual never sent (historical bug, now regressed in unit/test_scheduler.py).
   - Wrong to pending = dups or failed cancels on leave.
   - VIP cross: sub.channel_id must stay DB PK or all VIP lifecycle (redeem, expire ban, is_vip) + tests break.
   - Broadcast security risk if TG id confused.

4. **Free handlers changes (e.g. enforce 1-service rule, remove logic)**:
   - Would require extracting biz (dup check, create+schedule, msgs) to service or new layer -> ripples to scheduler schedule API, voice calls.
   - Low immediate for approve contract, but high for future.

5. **Schema/ORM mismatch (approval_attempts, FK duality, unique)**:
   - Adding column to model without mig = Alembic issues (per models/CLAUDE strict rules).
   - If code starts using approval_attempts, local DBs without col fail (prod has per stub).
   - Direct model query in scheduler (via rel) assumes session open.

6. **Inactive channel paths + error cases in jobs**:
   - Handlers skip silently; scheduler continues (no approve, no log?); tests (pilots happy-path only) don't cover -> "changed ready filter" could break real flow or leave stuck requests.

7. **Session patterns + close + patching**:
   - Scheduler + pilots use raw SessionLocal + explicit ChannelService(db) + patch.object(scheduler_service, "SessionLocal"...
   - Changing to get_service / context would break job pickle + test patches + connection leak fixes.
   - Legacy close() in channel/free handlers.

**"Today vs Desired Contract" Highlights:**
- Tests (unit + integ pilots) validate **current impl**: approve_* = pure DB flip (status/approved_at); get_ready = time filter only; approve_all from panel = bulk DB, no membership grant, no TG calls.
- Scheduler is the only path granting real TG membership + welcome for auto.
- Member_join path is fallback for "external" joins.
- approve_all_pending "approves" in Lucien DB but user may still have pending join_request in TG (stuck until manual or re-request?).
- Pilots in test_free_entry_flow.py (TestSchedulerPendingRequestsJob etc.) **document current behavior** (assert approve_chat_join called only in job sim; DB flip in service approve_all; explicit TG vs PK comments).
- Desired (per review notes): perhaps centralize "full grant" (TG+DB+welcome) into service method; or explicitly contract that approve_all is "system mark only".
- No test currently asserts "approve_all does NOT call bot.approve" (would be good pilot for contract).

---

## Existing Tests That Cover (or Should Cover) These Paths

**Direct coverage (current):**
- **tests/unit/test_channel_service.py** (TestPendingRequests + helpers): Covers ALL targeted service methods (create_pending, get_*, get_ready, approve_request, cancel, approve_all_pending, count, regression post-approve returns None). Injected db_session; pure DB; creates use correct .telegram_id now (post-fixes); some >= loose; aware DT in places. No TG, no scheduler.
- **tests/integration/test_free_entry_flow.py**:
  - TestFreeEntryFlow: service create/approve/get_ready/duplicate/impatient/welcome sim (no real job).
  - TestFreeEntryRaceCondition: double approve idempotent at service.
  - TestSchedulerPendingRequestsJob: **direct call to real _process_pending_requests** (tmp file SQLite + TestSession patch + _get_bot patch); verifies: TG approve_call with correct TG chat_id, DB status=approved on verify, send_message welcome+invite. Uses DB id internally for create, TG for asserts. Happy + timing force.
  - TestSchedulerFreeWelcomeJob: direct _send_free_welcome_job(TG ids); verifies ritual + keyboard.
- **tests/unit/test_scheduler.py**: Schedule API only (TG vs DB PK regression for free_welcome; IntervalTrigger for approve job; DateTrigger). No execution.
- **tests/conftest.py**: sample_free_channel (both ids), sample_pending_request (user.telegram_id + DB channel_id), used by unit+integ.

**Indirect / cross that would break:**
- All VIP integ: test_vip_*, test_vip_subscription_lifecycle, test_vip_complete_cycle, test_vip_flow*, test_vip_ritual_flow, test_invariants (I5), test_cross_service_atomicity: Channel creation (TG to create_channel), subs with .id DB, get_vip_channel, is_user_vip.
- Reaction/broadcast integ (use free channels for TG broadcast.channel_id): test_reaction_*, test_cross.
- Unit: test_vip_service, test_broadcast_service (TG), test_analytics (setup).
- Handlers tests: limited (no direct free/channel handler tests; some common use patched VIP).
- Others: test_alembic_heads, etc.

**Gaps (no/few coverage):**
- Full handler e2e for join_request -> create -> schedule (uses real TG events, hard in unit).
- Inactive channel skips in create/get_ready/scheduler (checks exist but no dedicated asserts).
- Error paths in _process (TG approve fail, welcome send fail, inactive, per-req rollback continue).
- approve_all from admin panel actually doing (or not) membership (no bot in those tests).
- approval_attempts column (nowhere).
- Multi-channel free (assumes?).
- Race between scheduler + manual member_join.
- Real bot integration (pilots use mocks).

**Tests that MUST be run/updated after ANY change to these:**
- Tier 1 (mandatory, zero-reg required):
  - pytest tests/unit/test_channel_service.py -q --tb=line
  - pytest tests/unit/test_scheduler.py -q
  - pytest tests/integration/test_free_entry_flow.py -q --tb=short  (job pilots critical)
  - pytest tests/unit/test_vip_service.py -q
  - pytest tests/integration/test_vip_subscription_lifecycle.py -q --tb=line
  - pytest tests/integration/test_invariants.py -q -k "vip or channel"
  - pytest tests/integration/test_vip_flows.py -q ; test_vip_complete_cycle.py ; test_vip_flow.py ; test_vip_ritual_flow.py
- Tier 2 (cross):
  - reaction full/limit/mission, cross_service_atomicity, test_broadcast_service
- Tier 3 / smoke:
  - pytest -k "channel or free_entry or pending or scheduler or vip" --tb=no
  - ./run_critical_tests.py (if updated)
  - Full: pytest tests/integration/ -q -k "channel or free or pending or vip" --maxfail=5
- Always post: ruff check --fix ; ruff format ; manual verification (if bot runnable: admin approve_all panel, free join request flow, VIP cycle).
- If ID changes: re-audit ALL fixtures + every .id vs .channel_id vs .telegram_id in channel-using tests (grep "channel_id|sample_.*channel").
- If service signature or approve semantics change: all direct callers + patches in pilots.

Re-run before/after any pilot addition.

---

## Architectural Violations / Bypasses in Current Impl

1. **Handler rules (root CLAUDE + handlers/CLAUDE.md non-negotiable)**:
   - free_channel_handlers violates: >1 service (User + Channel + get_scheduler direct), biz logic (dup detect + impatient, inactive early return, send msgs), long functions. "Exactly 1 service call".
   - channel_handlers + broadcast + admin use old `ChannelService()` + manual close (vs migrated `with get_service(...)`).
   - channels/CLAUDE.md outdated on "only handler does direct commit" (now scheduler does; free delegates).

2. **Scheduler bypass (services/scheduler_service.py)**:
   - Direct attr mutate + commit/rollback on PendingRequest (loaded via svc) instead of channel_service.approve_request(request.id). Violates "service for biz".
   - Raw SessionLocal in jobs (required for pickle of module funcs + APScheduler SQLJobStore).
   - request.channel rel load depends on session not closed.

3. **Service layer legacy**:
   - Manual session mgmt + close (not context or get_db_session everywhere).
   - approve_all/approve do direct DB in loop (no tx per? but single commit after).

4. **Model / access**:
   - No FK on PendingRequest.user_id (risk of orphan).
   - FK target inconsistency (Broadcast vs Pending/Subscription).
   - approval_attempts in prod schema (stub mig) but absent from ORM model + zero usage in approve paths (dead; if used would require mig-first per models/CLAUDE).
   - Param naming in ChannelService: "channel_id" overloaded (TG for create/get_by_id; DB for pending/delete/update).

5. **Cross-domain**:
   - VIPService bypasses ChannelService entirely (direct model queries for get_vip_channel + Channel() in add).
   - No central ID helpers (per prior recs).

6. **Tests validate impl not (yet) contract**:
   - Pilots assert current split (service=DB, scheduler=full grant). Adding pilots for "approve_all only DB" would be contract test.

Docs drift in multiple CLAUDEs (get_session examples obsolete, missing ID section, mig chain incomplete vs actual alembic/versions incl 73702).

---

## Recommendations for Safe Pilot Test Scope (Validate Desired Contract w/o Immediate Prod Changes)

**Goal of pilots (per task + review context):** Validate "desired contract" (e.g. what approve_all should/should not do; full membership grant semantics; ID contracts) using "documented only / not executed" or isolated test code, without touching prod sources. Use existing patterns: file SQLite + TestSession + patch for jobs; deterministic explicit creates; fresh TG ids (neg for chan, large for user); strict asserts + docstrings; GSD pre; ruff/pytest clean.

**Safe scope (start low-risk, no prod edits):**
1. **Contract pilot for approve_all limitation** (high value, per fases #3):
   - Extend test_free_entry_flow.py (new class or method in existing Test*Job, or isolated).
   - Setup pending via service (DB id); call approve_all_pending(DB id) **with bot mock patched at service?** or assert no approve call happened.
   - Assert: DB status flipped + approved_at set; **mock_bot.approve_chat_join_request NOT called**; no send_message for welcome; user "approved in system" but simulate re-join_request would still create new? or TG state would reject (mocked).
   - Docstring: "Current/desired contract: approve_all (admin panel path) performs ONLY DB flip. Full TG membership grant + welcome is scheduler's responsibility only. This distinguishes from get_ready + _process path."
   - Use tmp DB to avoid polluting; patch if needed.
   - Does NOT change any prod code.

2. **Strengthen existing pilots (low risk):**
   - In TestSchedulerPendingRequestsJob + free_entry: add variants for inactive channel (assert skip, no approve, no welcome, log?); error on TG approve (continue to next, no partial commit?); send_welcome fail.
   - Add assert on request.channel_id == DB vs channel.channel_id == TG in setup.
   - Cover get_all_pending_requests, cancel in pilots.
   - Add explicit: "after approve_all, get_pending returns None (already in unit)".
   - For ID: add test that passes TG to pending methods -> fails lookup (or None), to document contract.

3. **Unit edges (in test_channel_service, using db_session):**
   - create_pending on inactive channel (current raises? or allows? doc contract).
   - get_ready_to_approve with inactive? (current returns; scheduler skips).
   - approve_all on None / all channels.
   - Wrong id types (TG as channel for pending -> 0 count).
   - DT strict: use now(UTC) everywhere; assert exact or small delta.
   - Cover approval_attempts if column added to test model (but don't touch prod model).

4. **Schema / duality pilot (doc + assert only):**
   - In test_free_entry or new: assert on loaded Channel: obj.id != obj.channel_id; Pending.channel_id == channel.id (DB); Pending.user_id == user.telegram_id.
   - Document in test: "ID contract: PendingRequest.channel_id always references Channel PK (for FK); bot ops always use Channel.channel_id (TG). Handlers convert at boundary."
   - Inspect or query for 'approval_attempts' presence (xfail if prod-only).

5. **Non-test pilots (doc only, lowest risk):**
   - Update services/channels/CLAUDE.md + models/CLAUDE.md + handlers/CLAUDE.md (add ID duality section, exact current sigs, "approve_all is DB-only", "scheduler bypass note", "callback ID types", cross VIP/broadcast).
   - Add comments (no behavior) in source for clarity (but if counts as edit, do via GSD + minimal + revert if needed? per prior).
   - Add to test docs or README.

**Execution rules for pilots:**
- Pre: GSD log append (as done).
- Deterministic setup (no rely on sample_ fixtures for core contract if possible; or enhance fixtures).
- For jobs: always tmp file SQLite + patch SessionLocal + _get_bot.
- Fresh numeric IDs (avoid collisions with samples).
- Assert both sides of duality + bot calls (or not) + DB state.
- After any: targeted pytest -k "free_entry or channel or TestScheduler or pending" + ruff.
- Keep "pilots documented/not executed" if needed to avoid running in CI this phase.
- If adding to existing integ file, ensure no side effects on other tests (use tmp always for jobs).
- Broader smoke: -k "vip or invariants" to catch cross.

**Safe order:** 1. Doc pilots + comments (if allowed) + unit edges. 2. Extend free_entry pilots for contract + error matrix. 3. Later: full handler tests or service extraction.

**Risks to pilots themselves:** Fragility if DB engine differs (SQLite vs PG for tz/unique); over-reliance on mocks hides real TG errors; changing contract later requires pilot updates.

**Post-analysis actions (for team):** Re-run Tier1 listed; update MEMORY.md; append this report to GSD log; consider if desired contract is "centralize full approve in service" (then update pilots + all paths) or "document split explicitly".

This report + prior channels-impact-map.md + call-sites.md + todos.md give complete picture. All from direct tool exploration + cross-ref.

---
**End of report.** (Persisted to agent memory for future conversations.)