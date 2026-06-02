# Channels Refactor Prep (post-analysis)

## Immediate (minimal, low-risk, doc+clarity first -- no behavior change)
- [ ] Update services/channels/CLAUDE.md (fix sigs, add ID duality section, correct "who commits direct", list get_by_db_id + update_invite, note cbs + VIP bypass + scheduler jobs)
- [ ] Add precise comments in:
  - services/channel_service.py (per affected method: "TG chat ID" vs "DB PK for Channel/Pending FK")
  - handlers/free_channel_handlers.py (around 48/59/72/84 handoff, reinforce existing comment)
  - services/scheduler_service.py (_send 76, schedule 368, _process 104/117)
  - handlers/channel_handlers.py (when packing ChannelDetail etc: "# DB PK")
  - handlers/broadcast_handlers.py (when packing BroadcastChannel: "# TG id")
  - services/vip_service.py (on direct Channel queries)
- [ ] Sync any auto tables if services/CLAUDE.md lists methods count
- [ ] Run Tier 1 tests (see impact-map) before/after doc changes (should be noop)

## Low-risk followups (after GSD + doc landed)
- [ ] Migrate channel_handlers.py + broadcast + admin_analytics + free to `with get_service(ChannelService)` (note: free still has UserService + scheduler direct call -- may need separate refactor per rules)
- [ ] In scheduler _process_pending: replace direct mutate+commit with `channel_service.approve_request(request.id)` (use the passed db session; preserves tx per-req)
- [ ] Add get_vip_channel() (or get_vip_channels) to ChannelService; update VIPService to delegate (remove direct query + import model)
- [ ] Consider adding `get_channel_by_telegram_id` alias (or rename get_by_id) + update internal callers gradually + tests
- [ ] Once clear, decide on cb naming (e.g. add telegram_id field? or keep but document) -- high risk, do last

## Tests to extend (if time)
- [ ] Add test asserting that count_pending / approve_all etc receive DB id (not TG) in unit
- [ ] Assert in integration that schedule_free_welcome is always called with TG (already in scheduler unit)
- [ ] Cover the approval_attempts column (if ever wired)

## Risks / Gotchas to watch in GSD
- Scheduler jobs: must continue using explicit db= ChannelService(db) + module funcs (pickle)
- No change to cb payloads until all pack sites + any persisted cbs considered
- Free handler still calls 2 services + scheduler: fix as part of rule enforcement, not ID fix
- Verify both .id (DB) and .channel_id (TG) in every channel-using test after changes
- Run full Tier1 + manual bot flows for free join + channel admin + VIP cycle

## Memory update
Update this + impact-map if new call sites discovered (e.g. via future grep).
