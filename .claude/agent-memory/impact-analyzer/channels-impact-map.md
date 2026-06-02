# Channels Domain Impact Analysis (ID Confusion + Patterns + Doc)

**Date:** 2026-06-01 (analysis)
**Scope:** Minimal, low-risk refactor pre-GSD. Focus: Channels domain pain points.
**Priorities:** 1) ID confusion (`Channel.id` PK vs `channel_id` TG chat ID) in params/calls/cbs/scheduler/VIP. 2) Outdated doc in services/channels/CLAUDE.md. 
**Non-goals (for now):** Full modernization of service patterns, direct bypass fixes, handler rule fixes (mentioned for completeness).
**Goal of analysis:** Prevent regressions in **Free channel approval flow** and **VIP-related channel access** (bans, invites, is_vip, subs).

## 1. ID Confusion Summary (root cause)
- `Channel.id`: Integer PK (DB surrogate, used in FKs for Subscription.channel_id, PendingRequest.channel_id)
- `Channel.channel_id`: BigInteger (unique, Telegram chat ID, used for bot API calls: approve_chat_join, ban, send to channel, BroadcastMessage.channel_id FK)
- Inconsistent param naming in ChannelService: "channel_id" means TG for `get_channel_by_id`/`create_channel`, but DB PK for `delete_channel`/`update_*`/`create_pending_request` (and all pending_* methods filter on PendingRequest.channel_id which stores the DB PK).
- Callers mix: free handlers lookup by TG then pass `.id` (DB) to pending methods; scheduler free welcome passes TG to get_by_id.
- Callbacks: ChannelDetail* etc. carry DB id; BroadcastChannelCallback carries TG id. (Same field name, different semantics.)
- VIP/Subs: channel_id in sub = DB PK; lookups in VIPService direct on model.
- Broadcasts: TG id.
- Display/logs: usually show `.channel_id` (TG) which is correct for humans.
- Result: brittle, comments like "IMPORTANTE: pasar chat.id (TG), no channel.id (DB)" (free_channel_handlers.py:80), regression test in test_scheduler.py.

See models/models.py:83 (id PK),84 (channel_id TG),155 (Sub FK id),176 (Pending FK id),274 (Broadcast FK channel_id).

## 2. Complete Impact Map (Files + Specific Locations)

### Core Service (definitions + logic with confusing params)
- **services/channel_service.py** (ALL methods affected by param semantics or consumers):
  - create_channel(self, channel_id: int=TG, ...): 39-53 (stores to .channel_id)
  - get_channel_by_id(self, channel_id: int=TG): 55-58 (filter Channel.channel_id)
  - get_channel_by_db_id(self, db_id: int): 60-63 (filter Channel.id) -- note clearer name
  - get_all/free/vip_channels: 65-86
  - delete_channel(self, channel_id: int=**DB** !!): 88-99 (calls get_by_db_id(channel_id); logs as if id)
  - update_wait_time(self, channel_id: int=**DB**): 101-109 (get_by_db; only for FREE)
  - update_invite_link(self, channel_id: int=**DB**): 111-119 (get_by_db)
  - create_pending_request(self, user_id, channel_id: int=**DB PK** !!, username=..., first_name): 123-144 (does get_by_db_id(channel_id) to fetch wait_time; stores channel_id=DB to PendingRequest.channel_id)
  - get_pending_request(self, user_id, channel_id: int=**DB**): 146-157 (filter Pending.channel_id)
  - get_pending_requests_by_channel(self, channel_id: int=**DB**): 159-166
  - get_all_pending_requests: 168-171
  - get_ready_to_approve: 173-181
  - approve_request(self, request_id): 183-192 (note: does NOT touch approval_attempts column)
  - cancel_request(self, user_id, channel_id: int=**DB**): 194-202
  - approve_all_pending(self, channel_id: int=**DB**|None): 204-219 (direct mutate + commit)
  - count_pending_requests(self, channel_id: int=**DB**|None): 221-227
  - Also: __init__/close/_get_db manual session mgmt (21-35)

### Handlers (call sites + old instantiation + cb data)
- **handlers/channel_handlers.py** (old `ChannelService()` + try/finally close everywhere; cbs carry DB id):
  - set_channel_type (confirm): 126-153 (create_channel with TG from state; log uses channel.id DB)
  - list_channels: 165-204 (get_all; for ch: ChannelDetailCallback(channel_id=ch.id=DB); 193)
  - channel_detail: 209-252 (channel_id=cb=DB; get_by_db_id(211); count_pending(225) if free; show channel.channel_id=TG(236); channel_actions_keyboard(247) with DB; 215,225,248)
  - config_wait_time: 258-274 (cb=DB)
  - set_wait_time: 278-310 (update_wait_time(DB), back with ChannelDetail(DB); 300,304)
  - config_invite_link_start: 317-348 (get_by_db(325); update state DB; 325,342)
  - process_invite_link: 351-389 (update_invite(DB), get_by_db; 363,365)
  - view_pending_requests: 394-411 (get_by_channel(DB); back cb DB; 397,401,406)
  - approve_all_requests: 414-430 (approve_all(DB); 417,421)
  - delete_* : 436-484 (get_by_db, delete_channel(DB); 439,457,461,465)
  - Also imports: 33; many finally:close 153,204,251,308,346,386,410,429,482

- **handlers/free_channel_handlers.py** (old multi-service + direct scheduler + rule violation; main Free flow entry):
  - handle_join_request: 24-96 (user_service + channel_service manual; get_by_id(TG=chat.id:48); get_pending(user, channel.id=DB:59); create_pending(..., channel_id=channel.id=DB:74); scheduler.schedule_free_welcome(user.id, chat.id=TG:84); comment 80-81 explicit; close 92-96)
  - handle_member_leave: 99-133 (get_by_id(TG:114); cancel(user, channel.id=DB:120))
  - handle_member_join: 136-178 (get_by_id(TG:150); get_pending(DB:156); approve_request(158); no create here)
  - Imports:14,15,16; multiple closes; direct get_scheduler call violates "exactly 1 service"

- **handlers/broadcast_handlers.py** (old pattern; cbs use TG id -- contrast to channel mgmt):
  - send_broadcast_start: 49-97 (ChannelService(); get_all; BroadcastChannelCallback(channel_id=ch.channel_id=TG:78))
  - select_channel_for_broadcast: 100-112 (channel_id=cb=TG; get_by_id(TG:109); later send to chat_id=channel_id=TG, create_broadcast with TG)
  - Other uses of data["channel_id"] are TG for bot.send_*
  - Imports + closes:25,51-55,107-111
  - Note: BroadcastMessage.channel_id stores TG (per model)

- **handlers/admin_handlers.py** (old pattern):
  - admin_analytics (or equiv): 96-122 (ChannelService(); get_free, get_vip, count_pending_requests() noarg:100-103; VIPService mixed; close 121)

- Indirect (use VIPService.get_vip_channel() or is_user_vip, which internally query Channel):
  - handlers/common_handlers.py:46,99 (vip_channel = ...get_vip_channel(); .channel_id=TG for bot.create_chat_invite_link, send; error log)
  - handlers/vip_handlers.py, vip_user_handlers.py, story_user_handlers.py, reward_admin_handlers.py, backpack_handler.py, bot.py (startup), gamification_user_handlers.py (broadcast.channel_id=TG)

### Scheduler (jobs + direct DB bypass + ID specifics)
- **services/scheduler_service.py** (jobs are module funcs for pickle; use raw SessionLocal + ChannelService(db)):
  - _send_free_welcome_job(user_id, channel_id: int=TG !!):68-96 (ChannelService(db); get_channel_by_id(TG:76); send ritual; note comment in caller)
  - _process_pending_requests():99-150 (ChannelService(db); get_ready_to_approve:104; for req: channel=req.channel (rel); bot.approve( chat_id=channel.channel_id=TG:114 ); **DIRECT MUTATE** `request.status=..., approved_at=...; db.commit()` **bypassing approve_request()**:117-119 ; rollback on err; log with TG:142)
  - schedule_free_welcome(user_id, channel_id: int=TG):368-385 (add_job to _send... with TG kwarg)
  - Also _process_expired_subscriptions uses VIPService + sub.channel.channel_id=TG for ban/unban:192,211,213
  - Imports ChannelService + VIPService:24,26
  - get_scheduler global

- Callers of schedule: only free_channel_handlers.py:84 (with TG)

### VIPService (direct DB bypass / cross-domain queries on Channel model)
- **services/vip_service.py**:
  - add_vip_user (internal):260-265 (`db.query(Channel).filter(VIP,active).first()`; sub = Subscription(..., channel_id=vip_channel.id=DB:272))
  - get_vip_channel:411-418 (same direct query; returns Channel)
  - get_user_subscription / get_active / is_user_vip etc accept optional channel_id=**DB PK** for Sub filter:316,326,329,341
  - No calls to ChannelService; imports Channel model directly:14
  - Used by: reward_service, game_service (is_user_vip wrapper), many handlers, scheduler jobs, bot.py, tests

### Keyboards / Callbacks (ID semantics in packed data)
- **keyboards/callback_data.py**:
  - ChannelDetailCallback, ConfigWaitCallback, ConfigInviteCallback, PendingReqCallback, ApproveAllCallback, DeleteChannelCallback, ConfirmDeleteChannelCallback: channel_id: int (all = DB PK) :213-250
  - BroadcastChannelCallback: channel_id: int (= TG id) :456-458
  - ChannelTypeCallback action only
- **keyboards/inline_keyboards.py**:
  - channel_actions_keyboard(channel_id: int=DB, ...):198-250 (passes DB to all Config*/Pending*/Approve*/Delete* cbs; for VIP: f"manage_tariffs_{channel_id=DB}", f"generate_token_{DB}", f"list_subscribers_{DB}" -- but these strings are matched exactly in handlers without parsing id suffix, so id is dead payload)
  - Imports callback_data:9-11
  - Other keyboards use static for some VIP mgmt

- Note: f-string callbacks for VIP channel actions from channel detail are effectively ignored (handlers listen to bare "manage_tariffs" etc.). See vip_handlers.py:48,180,401

### Models + Relationships (foundational for IDs)
- **models/models.py**:
  - Channel: id=PK, channel_id=TG BigInt unique:83-84; relations to subs + pending:99-102
  - Subscription: channel_id = FK("channels.id") =DB:155; rel to channel:165
  - PendingRequest: channel_id = FK("channels.id")=DB:176; rel:185
  - BroadcastMessage: channel_id = FK("channels.channel_id")=TG:274; (inconsistent FK target!)
  - ChannelType enum:30
  - No approval_attempts in ORM (but migration added column)
- models/__init__.py exports

### Bot / Startup / Orchestration
- **bot.py**:
  - check_expired... + on_startup:116 (VIPService), 148 (sub.channel.channel_id=TG for ban/unban), 154,158,161
  - Routers:31,33 channel + free; 189 scheduler start; 256 include
  - Imports:68 VIP,67 scheduler

### Voice + Utils (display only)
- **utils/lucien_voice.py**: admin_channel_list(channels):319-338 (uses ch.channel_type, ch.channel_id=TG for display; 335-338); free_*/admin_* messages take names/ids
- utils/CLAUDE.md mentions admin_pending

### Other Handlers / Services (indirect)
- handlers/gamification_user_handlers.py:238 (broadcast.channel_id = TG)
- services/broadcast_service.py: channel_id params = TG (for BroadcastMessage):101,145,151,157,162,402
- services/reward_service.py: uses VIPService (for VIP rewards)
- services/game_service.py: wraps is_user_vip from VIP
- No other direct ChannelService in gamif/store/mission etc.

### Docs (outdated + references)
- **services/channels/CLAUDE.md** (primary outdated):
  - API doc:31-47 (wrong create_pending sig: says scheduled_approval_at param but code takes user+channel+username+first; missing get_by_db_id, get_all_pending, update_invite, get_vip_channels in some places; signatures incomplete)
  - Flow:22-25
  - Notes:59-61 ("free_channel_handlers.py es el único handler que hace commit directo" -- FALSE, it's scheduler; free uses service)
  - Missing: ID semantics note, scheduler direct bypass mention, get_channel_by_db_id usage, callback ID types, VIP direct queries
  - Lines ~23,32,36-47,59-61,67
- services/CLAUDE.md:10 (ChannelService methods count)
- root CLAUDE.md:31 (Channels domain)
- models/CLAUDE.md:14,18,22 (Channel, Pending, Sub)
- AGENTS.md:66,215 (high level)
- utils/CLAUDE.md, README.md, handlers/CLAUDE.md (structure only)
- refactor_testing.md, fases_refactor_testing.md: historical mentions of tests + channel flow
- alembic/versions/* : schema (e.g. initial has FKs, 73702 for pending attempts stub)

### Test Files (all that would be affected or must re-run)
**Unit (direct calls + ID assertions):**
- tests/unit/test_channel_service.py (heavily): fixtures use .id=DB for pending/create/delete/update/count; .channel_id=TG for get_by_id; e.g. lines 49(get_by TG),59(db),99(delete db),120(update db),143(create db),174(get_pending),187(by_channel),242(cancel),263(approve_all),273(count),280-285(regression). Tests ~15 methods.
- tests/unit/test_scheduler.py: regression for TG vs DB in schedule_free + triggers:14-42 (explicit db_pk vs telegram),71+
- tests/unit/test_vip_service.py: get_vip_channel, subs with .id=DB:282(test),191(assert sub.channel_id==.id)
- tests/unit/test_broadcast_service.py: broadcast with .channel_id=TG:82,89
- tests/unit/test_backpack_service.py: channel setup VIP:322

**Integration (core flows + scheduler jobs + VIP channel access):**
- **tests/integration/test_free_entry_flow.py (HIGHEST RISK, must 100% pass)**: TestFreeEntryFlow + TestSchedulerPendingRequestsJob + TestSchedulerFreeWelcomeJob. create_pending always with channel.id=DB; _process calls; _send with chan_tg_id; direct verify on PendingRequest model; asserts on bot calls with TG ids; comments 355 "debe pasar el TG id, no DB pk"; lines 32,52,60,72,83,103,133,141,168,175,243,266,324-365 (job tests use tmp SQLite + patch SessionLocal/_get_bot)
- tests/integration/test_vip_complete_cycle.py: ChannelService for setup VIP channels:41,111,190,255; create with TG ids; assert sub.channel_id == vip_channel.id (DB)
- tests/integration/test_vip_flow.py: similar setup:20,23
- tests/integration/test_vip_flows.py: many VIP subs + is_user_vip, channel.id
- tests/integration/test_vip_subscription_lifecycle.py: heavy VIP + scheduler expire; channel.channel_id=TG:398,1110; asserts; sub.channel_id DB
- tests/integration/test_vip_ritual_flow.py: get_vip_channel:66
- tests/integration/test_invariants.py: I5 VIP expired; channel setups:278(VIP),433(FREE),445; is_user_vip
- tests/integration/test_cross_service_atomicity.py: FREE + broadcast TG:98,110,152
- tests/integration/test_reaction_full_chain.py, test_reaction_limit.py, test_reaction_mission_flow.py: FREE channels for broadcast tests:97+,113,264,355,412
- tests/integration/test_trivia_*.py ? (indirect via VIP limits in game)
- tests/handlers/test_common_handlers*.py, test_story_user_handlers.py: patch VIPService (get_vip_channel, is_user_vip)

**Conftest + others:**
- tests/conftest.py: sample_vip_channel(94), sample_free(110) set both ids; sample_pending(266) sets channel_id=DB .id; sample_subscription(187) channel_id=DB; sample_broadcast(347) uses TG .channel_id; sample_expired etc.
- tests/e2e/ minor
- Also: test_handler_service_leaks.py etc may touch close patterns

**Other tests mentioning:** unit/test_analytics? no; many use db_session indirectly.

## 3. Consumers / Call Sites Trace (key methods)
From exhaustive grep:
- create_pending_request: channel_service (internal), free_channel_handlers:72, channel? no, tests/unit:143+, tests/int free:32+, vip_setup tests:44+
- get_pending_request / by_channel / cancel / count / approve_all / approve_request: similar + channel_handlers:225,401,421; admin:103; scheduler indirect via get_ready
- get_channel_by_id (TG): free:48,114,150; scheduler _send:76; broadcast:109; channel_service tests + internal create_pending
- get_channel_by_db_id (DB): channel_handlers:215,325,365,461; delete/update internal
- delete/update_wait/update_invite: only channel_handlers + their tests (unit channel)
- schedule_free_welcome / _send_free...: free:84; scheduler:368,377; unit scheduler test; int free test job
- _process_pending...: scheduled in bot/scheduler start:324; called in int free test
- get_vip_channel / direct Channel query in VIP: vip_service internal, called from common:46,99; bot startup indirect; tests many; reward/game wrappers
- BroadcastChannel vs ChannelDetail cbs: broadcast_handlers:78,105; channel_handlers:193,247 etc; keyboards

Full raw calls in channels-call-sites.md (generated from grep).

## 4. Risks of "cambié A y se rompió B"
- **Param rename in service (e.g. channel_id -> channel_db_id for pending/delete)**: Breaks 20+ call sites across handlers + ~30 test asserts/calls. Compile/runtime fail in free entry + all channel admin. (Low risk if search-replace all, but many files.)
- **Change what cbs carry (DB<->TG)**: Breaks channel mgmt UI completely (detail, wait, invite, pending, delete, approve). Broadcast unaffected but if shared type, chaos. Callbacks are serialized in TG, old pending cbs would fail unpack.
- **Make delete/update take TG instead**: Would silently use wrong lookup (tg as pk -> not found or collision if ids overlap), channels undeletable/configurable. Free approval unaffected directly.
- **Touch scheduler direct mutate**: If change approve_request to do more (e.g. increment attempts, side effects, no commit?), _process_pending won't follow -> inconsistent state, duplicate welcomes, users not added to channel. (Current bypass means approval_attempts never set.)
- **VIP direct query change**: If refactor to always use ChannelService.get_vip_channels()[0], need to handle multiple VIP? (current assumes 1); affects every VIP redeem/sub/expire/is_vip. Risk in ban flows if wrong channel_id.
- **Service instantiation modernization (with get_service)**: In free handler (multi svc + scheduler), if wrap wrong, leaks or in scheduler jobs (which patch SessionLocal internally) may not work (jobs pass db explicitly: ChannelService(db)). Scheduler _send/_process use ChannelService(db) not context. Risk connection leaks if pattern mismatch (see fix_connection_leaks.py).
- **Free flow specific**: Wrong ID to schedule -> ritual never sent (historical bug fixed by regression test); wrong ID to pending -> duplicate requests or no cancel on leave; scheduler get_ready but mutate vs service -> status not updated or welcome sent twice.
- **VIP channel access**: get_vip_channel None or wrong -> no invites on /start for VIP, is_user_vip false positives, expired not banned, sub create fails.
- **Broadcast**: Wrong TG -> broadcast to wrong chat (security/privacy + spam risk).
- **Schema/ORM mismatch**: Broadcast FK vs others; pending column not in model.
- **Logs/callback validation**: Some logs use mixed ids.
- **Multi-VIP future**: Current code often takes "first" VIP; changing ID handling could expose.
- Low risk areas: pure display in voice (uses .channel_id correctly), create_channel (always TG).

High "butterfly" : free_channel_handlers.py:59-84 (the join request) + scheduler _process:107-147 + _send:76 . Changing one lookup ripples to bot API calls + DB state + user messages.

## 5. High-Risk Areas (prioritized)
1. **Free channel approval + ritual flow** (free_channel_handlers.py + scheduler_service.py jobs + test_free_entry_flow.py): Auto-approve, add to channel, send ritual (30s) + welcome. Direct scheduler bypass on PendingRequest. Focus prevent reg here.
2. **VIP subscription lifecycle + access** (vip_service.py direct Channel + scheduler _process_expired + bot.py startup + common_handlers invite + is_user_vip everywhere): Bans, unban, invites, entry checks. Affects all VIP users.
3. **Channel admin config UI** (channel_handlers + cbs + keyboards): Wait times, invites, delete, pending list/approve. DB id in cbs.
4. **Broadcast channel selection/send** (broadcast_handlers + service): Uses TG in cbs + sends.
5. **Scheduler jobs orchestration** (bypass + raw sessions + pickle constraints): _process_pending, free welcome, expired subs.
6. **Test fixtures + job tests** (conftest + free_entry + vip_* + scheduler unit): Any ID flip breaks setup/asserts on both .id and .channel_id.
7. **Handler rule + instantiation** (free especially: 2 services + scheduler in 1 handler; old close pattern in 4 handlers): Minor but mentioned.

## 6. Relevant Tests to Run Post-Change (mandatory for free + VIP channel)
**Tier 1 (must pass, cover critical flows):**
- `pytest tests/unit/test_channel_service.py -q --tb=line`
- `pytest tests/unit/test_scheduler.py -q`
- `pytest tests/integration/test_free_entry_flow.py -q --tb=short` (includes direct job invocations with patches)
- `pytest tests/unit/test_vip_service.py -q`
- `pytest tests/integration/test_invariants.py -q -k vip` (I5 expired access)
- `pytest tests/integration/test_vip_subscription_lifecycle.py -q --tb=line`
- `pytest tests/integration/test_vip_flows.py -q`
- `pytest tests/integration/test_vip_complete_cycle.py -q`
- `pytest tests/integration/test_vip_flow.py -q`
- `pytest tests/integration/test_vip_ritual_flow.py -q`

**Tier 2 (broadcast + reaction + cross that use channels):**
- `pytest tests/unit/test_broadcast_service.py -q`
- `pytest tests/integration/test_cross_service_atomicity.py -q`
- `pytest tests/integration/test_reaction_full_chain.py -q`
- `pytest tests/integration/test_reaction_limit.py -q`
- `pytest tests/integration/test_reaction_mission_flow.py -q`

**Tier 3 (handler + common + broader):**
- `pytest tests/handlers/test_common_handlers_integration.py tests/handlers/test_common_handlers.py -q -k "vip or channel"`
- `pytest tests/handlers/test_story_user_handlers.py -q`
- `pytest tests/integration/ -q -k "channel or pending or free or vip" --maxfail=5`

**Full regression suggestion:**
- `./run_critical_tests.py` (if covers)
- `pytest -k "channel or free_entry or vip or broadcast or pending or scheduler" --tb=no`
- Manual: admin channel list/detail/config (in running bot), join free channel, VIP redeem + expire sim.

**Always after:** ruff check --fix, format; check no new direct DB in handlers; verify logs have user_id etc per rules.

Also re-run any that patch ChannelService/VIPService.

## 7. Recommendations for Minimal Low-Risk Changes (ID + Doc first)
- **Doc only (lowest risk):** Update services/channels/CLAUDE.md with:
  - Explicit note on ID duality + which methods take TG vs DB PK.
  - Accurate method sigs (create_pending takes 4 params now).
  - Correct "who does direct commit": scheduler _process_pending_requests does direct on PendingRequest (not free handler).
  - Mention get_channel_by_db_id, update_invite_link, get_all_pending_requests, approval_attempts column (unused).
  - Note callback_data semantics (Channel* = DB PK; BroadcastChannel = TG).
  - Cross-ref to VIPService direct queries + scheduler bypass as known (for future).
  - Update flow diagram if needed.
  - Sync services/CLAUDE.md if counts change.
- **Minimal code (low risk, no behavior change):**
  - Add comments in channel_service.py at each method: "# channel_id param here is Telegram chat ID" or "# here is DB PK (for PendingRequest FK)"
  - Add comments in free_channel_handlers.py around the TG/DB handoff + existing comment.
  - Add to scheduler _send and schedule: "# channel_id MUST be Telegram chat ID (Channel.channel_id), NOT DB PK"
  - In channel_handlers.py and broadcast: comments when packing cb: "# DB PK for channel mgmt cbs" vs "# TG id for broadcast cbs"
  - In VIPService: comment on direct Channel queries (and why not using ChannelService yet).
  - No param renames yet (high churn).
  - Consider adding thin wrappers in ChannelService e.g. get_channel_by_telegram_id alias to get_by_id (for clarity, keep old).
- **Next after doc/ID clarity (still low risk):** 
  - Migrate 4 handlers to `with get_service(ChannelService) as svc:` (but scheduler jobs keep explicit db= since they control session for job tx).
  - Make _process_pending use channel_service.approve_request(req.id) instead of direct (ensures future consistency; since same db session passed to svc, commit inside ok? careful with loop commits).
  - Move VIP Channel queries to use ChannelService (add get_vip_channel to ChannelService? or get_vip_channels and pick first).
- **High risk to avoid now:** Changing cb payloads, renaming service params without global replace + test update, touching scheduler pickle/session logic, altering approve_request semantics.
- Verify with the Tier 1 tests above + manual free join + VIP cycle.

## 8. Additional Context / Gotchas
- There is only ever 1 active FREE and 1 VIP in practice (get_vip_channels returns list but get_vip_channel picks first).
- approval_attempts migration exists (73702d0a06be) but column not modeled, never incremented in approve or scheduler.
- Free handler is "system" triggered (chat events), not user cmd -> still must obey 1-service rule per CLAUDE.
- Old close pattern still in channel domain handlers (contrast to migrated domains using get_service).
- Direct DB in scheduler is documented exception in (outdated) channels CLAUDE.
- Tests use two patterns: db_session fixture (for unit/int with provided) vs tmp SQLite+TestSession patch (for jobs that do internal SessionLocal()).
- To detect breakage: any free join not resulting in auto-approve + ritual + welcome; VIP sub not creating with correct channel; config changes not persisting.

This map is exhaustive from greps/reads of all call sites (141+ for methods, 160+ for Channel/channel_id).

Next step (when GSD authorized): start with doc update + comment annotations only. Run Tier1 tests before/after.
