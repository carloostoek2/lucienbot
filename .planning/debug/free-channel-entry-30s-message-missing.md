---
status: verifying
trigger: "free-channel-entry-30s-message-missing"
created: 2026-04-02T00:00:00
updated: 2026-04-02T00:00:00
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: CONFIRMED - Bug en la linea 76 de free_channel_handlers.py
fix_applied: "schedule_free_welcome(user.id, channel.id)" -> "schedule_free_welcome(user.id, chat.id)"
verification: Run the regression test and observe scheduler test suite pass.
next_action: Request human verification: test the fix in a real channel join request flow.

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: |
  1. User arrives at free channel -> presses "Solicitar ingreso"
  2. Bot receives ChatJoinRequest
  3. After 30 seconds: bot sends free_entry_ritual() message to user
  4. If user sends second request before approval: free_entry_impatient() message
  5. When custodian approves: free_entry_welcome() + invite link message
actual: |
  - Message at 30 seconds does NOT arrive
  - Confirmation message after approval does NOT arrive
  - ONLY free_entry_impatient() arrives (when user sends second request)
errors: []
reproduction: |
  - User arrives at free channel and presses "Solicitar ingreso"
  - Does NOT receive any response for 30 seconds
  - Sends another request (second request) -> receives impaciencia message
  - Never receives confirmation message after custodian approves
started: After phase 10-02 implementation (commit d82e88d)

## Eliminated
<!-- APPEND only - prevents re-investigating -->

- hypothesis: Handler not registered
  evidence: Router is registered in bot.py line 226, __init__.py exports free_channel_router, handlers are decorated correctly
  timestamp: 2026-04-02
- hypothesis: Scheduler not initialized when handler runs
  evidence: on_startup calls get_scheduler(bot).start() before polling. get_scheduler() without args returns the same instance.
  timestamp: 2026-04-02
- hypothesis: APScheduler packages missing or misconfigured
  evidence: SQLAlchemyJobStore configured correctly, AsyncIOExecutor used for async jobs, job defaults set properly
  timestamp: 2026-04-02
- hypothesis: ChatJoinRequest updates not reaching bot
  evidence: free_entry_impatient() IS delivered, proving handle_join_request IS called
  timestamp: 2026-04-02
- hypothesis: _get_bot() returns None in scheduler job
  evidence: _bot_token is set from SchedulerService.__init__ via global, _bot_instance lazily created. Bot instance creation has no errors in code.
  timestamp: 2026-04-02

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-02
  checked: handlers/free_channel_handlers.py handle_join_request + models/models.py Channel schema
  found: |
    Channel model:
      - id = Column(Integer, primary_key=True)   <- DB auto-increment PK
      - channel_id = Column(BigInteger)         <- Telegram channel ID (BigInteger, unique)

    In handle_join_request:
      channel = channel_service.get_channel_by_id(chat.id)  <- returns Channel ORM object
      channel.id   = DB primary key (e.g., 42)
      channel.channel_id = Telegram channel ID (e.g., -1001234567890)

    BUG: scheduler.schedule_free_welcome(user.id, channel.id)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ channel.id = DB PK (42)
         This is WRONG.

    In _send_free_welcome_job:
      channel = channel_service.get_channel_by_id(channel_id)
      ^- get_channel_by_id queries: Channel.channel_id == channel_id
        Channel.channel_id column stores Telegram ID, not DB PK!
        So get_channel_by_id(42) queries "Channel.channel_id == 42"
        No row matches because channel_id values are large negatives (Telegram IDs)
        Result: channel is None -> function returns without sending message.
  implication: ROOT CAUSE FOUND. The fix is to pass chat.id (Telegram channel ID) to schedule_free_welcome.

- timestamp: 2026-04-02
  checked: handle_member_join for similar bug
  found: |
    In handle_member_join: channel = channel_service.get_channel_by_id(chat.id)
    chat comes from event.chat in ChatMemberUpdated event.
    event.chat.id IS the Telegram channel ID.
    So get_channel_by_id(chat.id) correctly queries Channel.channel_id == telegram_id.
    This lookup is correct.
    However: handle_member_join depends on the bot receiving ChatMemberUpdated events.
    For the bot to receive these events, it must be an admin in the channel and
    have appropriate privacy mode settings. If the bot is not an admin, or if
    Telegram is not forwarding ChatMemberUpdated updates to the bot, the handler
    will never fire. This is a configuration issue, not a code bug.
  implication: Confirmation message issue may be environmental (bot permissions) rather than code bug.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: |
  In handle_join_request (free_channel_handlers.py line 76, pre-fix):
  scheduler.schedule_free_welcome(user.id, channel.id) passed channel.id (database
  primary key, e.g. 42) to schedule_free_welcome.

  However, _send_free_welcome_job calls channel_service.get_channel_by_id(channel_id)
  which queries: Channel.channel_id == channel_id. Since Channel.channel_id stores the
  Telegram channel ID (e.g. -1001234567890), not the DB PK, the lookup always returned
  None. The function silently returned without sending the message.

  The fix: pass chat.id (Telegram channel ID from join_request.chat.id) instead of
  channel.id (DB PK).

fix: |
  File: handlers/free_channel_handlers.py, line 76
  Changed: scheduler.schedule_free_welcome(user.id, channel.id)
  To:     scheduler.schedule_free_welcome(user.id, chat.id)
  Added explanatory comment noting that chat.id is the Telegram channel ID.

verification: |
  - Unit test added: test_schedule_free_welcome_receives_telegram_channel_id
  - All 3 scheduler tests pass
  - No regression in channel service tests (22 passed)

files_changed:
  - handlers/free_channel_handlers.py: pass chat.id to schedule_free_welcome
  - tests/unit/test_scheduler.py: add regression test for channel ID type
