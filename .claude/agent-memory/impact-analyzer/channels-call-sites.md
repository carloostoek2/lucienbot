# Raw Call Sites Trace (from greps on 2026-06-01)

## ChannelService method calls (key affected by ID confusion)
- services/channel_service.py (defs):
  delete_channel, update_wait_time, update_invite_link (use get_by_db_id internally despite param 'channel_id')
  create_pending_request (lookup get_by_db_id; store to Pending.channel_id=DB)
  get_pending_*, approve_*, cancel_*, approve_all_*, count_* (all 'channel_id' = Pending.channel_id = DB PK)
  get_channel_by_id (TG), get_by_db_id (PK)

- handlers/channel_handlers.py:
  create_channel (TG):126
  get_all_channels:167
  get_by_db_id:215,325,365,461
  count_pending_requests(channel_id=DB):225
  update_wait_time(DB):300
  update_invite_link(DB):363
  get_pending_requests_by_channel(DB):401
  approve_all_pending(DB):421
  delete_channel(DB):465
  (all with ChannelService() + finally close)

- handlers/free_channel_handlers.py:
  get_channel_by_id(TG=chat.id):48,114,150
  get_pending_request(..., channel.id=DB):59,156
  create_pending_request(..., channel.id=DB):72
  cancel_request(..., DB):120
  approve_request(id):158
  (old closes + UserService + direct scheduler)

- handlers/broadcast_handlers.py:
  get_all:53
  get_channel_by_id(TG):109
  (Broadcast cb uses TG)

- handlers/admin_handlers.py:
  get_free/vip:100,101
  count_pending_requests():103

- services/scheduler_service.py:
  get_channel_by_id(TG):76 (_send_free)
  get_ready_to_approve:104 (_process)
  (ChannelService(db) inside jobs)

- tests/unit/test_channel_service.py: EVERY test (get_by_id(TG), by_db(DB), create_pending(DB), delete(DB), update(DB), get_pending(DB), by_channel(DB), ready, approve, cancel(DB), approve_all(DB), count(DB) )

- tests/integration/test_free_entry_flow.py: create_pending(DB), approve, get_pending, get_ready, approve_all in sims; direct job calls

- tests/integration/test_vip_*.py + test_cross + test_invariants + reaction_*: ChannelService(db) for test channel creation (TG ids passed to create)

- tests/unit/test_vip_service etc indirect

## schedule_free_welcome / _send_free_welcome_job / _process_pending_requests
- free_channel_handlers.py:84 schedule(..., chat.id=TG) + comment
- scheduler_service.py:368 def schedule( TG ), 377 call _send with TG; 324 schedule job _process; 76 _send get_by_id(TG)
- tests/unit/test_scheduler.py:34 schedule(TG), assert != db_pk; 79 schedule
- tests/integration/test_free_entry_flow.py:365 _send(TG), 266 _process()

## VIP direct Channel + get_vip_channel
- services/vip_service.py:262 query Channel VIP (in add), 415 (get_vip_channel)
- callers: common_handlers:46,99 get_vip_channel().channel_id(TG)
- bot.py:148 sub.channel (from VIP sub)
- scheduler:192 sub.channel (expired job)
- tests: vip_*, invariants, complete_cycle, ritual, unit/vip_service: get_vip_channel test + sub.channel_id==.id(DB)

## Callback packing (ID type)
- channel_handlers.py:193 ChannelDetail(DB=ch.id), 247 actions(DB)
- broadcast_handlers.py:78 BroadcastChannel(TG=ch.channel_id)
- keyboards/inline_keyboards.py:206 ConfigWait(DB),210 invite(DB),218 pending(DB),222 approve(DB),243 delete(DB); VIP f-strings with DB id (unused)

## Broadcast channel_id (TG)
- broadcast_handlers:705 data channel_id=TG for send + create_broadcast
- broadcast_service: channel_id=TG throughout
- models: Broadcast FK on channel_id (TG)
- gamif handlers: broadcast.channel_id

## Direct PendingRequest mutate (bypass)
- scheduler_service.py:117-119 in _process: request.status=...; db.commit() (no service.approve)
- (service approve_all also direct mutates in loop)

## Channel in other models/FKs
- Subscription.channel_id = channels.id (DB)
- Pending.channel_id = channels.id (DB)
- Broadcast.channel_id = channels.channel_id (TG)

## Old service instantiation sites (ChannelService)
- channel_handlers.py: x8 (set, list, detail, set_wait, config_invite, process_invite, view, approve_all, delete)
- free_channel_handlers.py: x3 (join, leave, member_join) + UserService
- broadcast_handlers.py: x2 (start, select)
- admin_handlers.py: x1 (analytics)
- (scheduler jobs use explicit ChannelService(db) -- keep)
- Contrast: many other handlers use `from services import get_service; with get_service(X) as s:`

## Docs references needing update
- services/channels/CLAUDE.md (signatures, flow, notes on commits/bypass, missing methods, no ID note)
- Cross: services/CLAUDE.md, models/CLAUDE.md, root CLAUDE, AGENTS, README, refactor mds

(Extracted via multiple greps for each method name + "channel_id|ChannelService|PendingRequest" + file reads. 100% of call sites covered for the listed pain points.)
