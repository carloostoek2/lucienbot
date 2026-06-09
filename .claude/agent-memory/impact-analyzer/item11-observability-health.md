# Impact Analysis: Observability / Health System (Item 11)

**Agent:** impact-analyzer (telegram-bot-hardener pipeline)  
**Date:** 2026-06-09 (analysis time)  
**Context:** Post Item 10 (store besito reduce + observer + pool), EventBus (besitos_awarded listeners: narrative/rewards/broadcast/game/store), get_service unification, mw hardening (Error/Idemp/Throttle), long handler refactors.  
**References:** CLAUDE.md (full rules: handlers=exactly 1 service call + no logic/DB, services own logic, <50 LOC funcs, verb+context+result naming, mandatory "módulo | acción | user_id | resultado" logging for important actions, GSD pre every modify, is_admin() for custodios, read-only for health), AGENTS.md (arch), decisions.md (EventBus + besito Items 5/6/10 + pool phrases), services/CLAUDE.md (current services table + get_service + EventBus), models/CLAUDE.md (Channel id/PK duality, no raw SQL, alembic rules), handlers/CLAUDE.md (1 svc rule), HARDENING_ROADMAP (referenced in task/prior decisions; currently absent at root but doc updates via documentador), bot.py, scheduler_service.py, database.py, analytics_service.py, channel_service.py, vip_service.py, backup_service.py, event_bus.py, besito_service.py, admin_handlers.py + analytics_handlers.py, keyboards/inline_keyboards.py, utils/{admin.py, lucien_voice.py}, requirements.txt, railway.toml, Procfile, DEPLOY.md, tests (golds + scheduler + free_entry + event_bus etc), services/__init__.py (get_service).

**Pool context (verbatim):** "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

---

## Executive Summary + Risks

**Proposal:** Add comprehensive but *tight-scope* observability/health system: HealthService (read-only checks for DB, bot runtime, channels/VIP/pending, EventBus listeners, Scheduler (APScheduler jobs status), critical services sanity (besitos balances, VIP active, narrative progress counts, recent activity volume via tx), backups last status); admin-friendly views (bot: /health Command or admin menu "🛡️ Pulso del reino" → Lucien-voiced summary using get_service(HealthService) + exactly 1 svc call; terminal: `python -m scripts.health_check [--json] [--verbose]` using same service); simple HTTP /health JSON endpoint (best-effort, for Railway/curl/monitoring) via minimal non-blocking aiohttp server on separate port (e.g. 8080) started in on_startup.

**Overall risk:** LOW if scoped tight + strictly read-only/best-effort/non-blocking/timeouts. MEDIUM if endpoint forces new dep + port wiring without care (but mitigable). 0 risk to correctness/atomicity of critical flows.

**Key positives (builds on existing):**
- Reuses AnalyticsService pattern (read-only stats via _get_db/owns_session/close, direct model counts for speed, get_service context in handlers).
- Reuses get_service (unification), is_admin, LucienVoice (add health_* renderers), EventBus logging convention ("event_bus | ..."), scheduler singleton + jobs, ChannelService/VIPService public APIs (counts, get_ready, get_active/expiring/expired, pending).
- Central registration precedent in bot.py on_startup (for listeners).
- No new models → 0 alembic impact.
- 3 critical systems (Gamification/besitos/missions/daily/reactions/minigames; Narrative/story nodes/archetypes/achievements/FSM/quiz; Channel/VIP/subs/pending/auto-approve/expire/ban) explicitly protected (see below).
- Logging format will be followed for all health actions (e.g. "health_service | check_db | user_id=0 | status=ok latency=12ms").

**Risks (high-level + mitigations):** See dedicated section below. Top: blocking checks (use timeouts + best-effort), false positives (soft statuses: ok/degraded/unhealthy + details), sensitive info (admin-only for bot view + no secrets in JSON), perf (caching trivial results 30s, rate via existing mw for cmds, light queries only), new dep for HTTP (defer or minimal aiohttp; scope can drop full endpoint if platform constraints).

**Recommendation:** PROCEED with gsd-planner for tight 5-6 phase implementation (prep/GSD + skeleton, HealthService+checks, endpoint server, bot admin view + menu, terminal script, tests+docs via documentador at end). Low surface, reuses patterns, 0 impact on atomicity/EventBus/get_service contracts or the 3 systems. "Ready for gsd-planner (observability/health item, next after Item 10 in current pool or new tirón)"

---

## Complete Impact Map

### Files Potentially Affected / To Create (tight scope)
**New (core, minimal):**
- `services/health_service.py` (HealthService class; read-only checks; follows service patterns: __init__(db=None), _get_db, close, _owns_session; methods verb+context+result e.g. check_db_connectivity, check_bot_runtime, check_channels_status, check_scheduler_jobs, check_event_bus_listeners, check_critical_services_sanity, check_backup_status, get_overall_status; uses get_db_session or direct for speed; structured logs; best-effort + timeouts; NO mutation, NO writes, NO side effects).
- `scripts/health_check.py` (standalone CLI: `python -m scripts.health_check` or `python scripts/health_check.py --json --bot --verbose`; uses `from services import get_service, HealthService`; prints human/Lucien or JSON; supports --db for direct; user_id=0 in logs).
- `tests/unit/test_health_service.py` (unit tests mirroring analytics + scheduler: keys, mocked/ db_session for checks, error paths, overall status).

**Modified (small, targeted, pattern-following):**
- `services/__init__.py`: Add `from .health_service import HealthService`; add "HealthService" to __all__ (enables `with get_service(HealthService) as h:` everywhere, zero other changes needed).
- `bot.py`: 
  - Import `from services import get_service, HealthService` (or direct) + health server starter if endpoint.
  - In on_startup (after scheduler + listeners): optional `asyncio.create_task(start_health_server())` if HEALTH_PORT env or similar (non-blocking; fire-and-forget).
  - Wire health cmd if using Message Command (like analytics_handlers /stats), or rely on admin cb routing.
  - Extend on_shutdown for server stop if any.
  - (Minimal; no logic.)
- `handlers/analytics_handlers.py` (or preferred: new `handlers/admin_health_handlers.py` + router include in bot.py): Add Command("/health") or keep menu-driven. Handler: `if not is_admin(...): deny; with get_service(HealthService) as svc: health = svc.get_overall_status() or render; await answer(LucienVoice.system_health(health))`; EXACTLY 1 service call (strict per CLAUDE/handlers/CLAUDE). Use cb for menu item.
- `handlers/admin_handlers.py`: (optional/minimal) Add cb handler for "admin_health" that delegates or calls exactly 1 service (but to obey "exactly 1", better dedicated handler file like analytics).
- `keyboards/inline_keyboards.py`: Add 1 button in `admin_menu_keyboard()` e.g. `[InlineKeyboardButton(text="🛡️ Pulso del reino / Estado", callback_data="admin_health")]`.
- `utils/lucien_voice.py`: Add static methods e.g. `system_health(health: dict) -> str`, `health_check_section(name, status, details)`, access_denied_health, etc. Follow existing analytics_dashboard style + admin_greeting + 3rd person elegant + emojis (✅ ⚠️ ❌) + "Diana" refs. <50 LOC each.
- `decisions.md`: Append full decision entry (Motivo/Riesgos/Decisión/Resultado style of Item 10/6/5) after last besito Item, with refs to this report + PLAN + gsd log + pool phrase.
- `services/CLAUDE.md`: Update services table (add HealthService | System/Observability | health_service.py | check_*, get_overall_status, ...); add note under cross-cutting or new "Observability" section referencing get_service, logging, best-effort, admin-only.
- (Optional for docs) `handlers/CLAUDE.md` or root if needed, but minimal; documentador will handle HARDENING_ROADMAP update at end.

**No changes (0 impact areas):**
- No changes to models/ (0 alembic), critical services (besito/credit paths, story/advance/grant, channel/approve/pending/expire logic, VIP grant/revoke, store purchase, missions deliver, broadcast reactions, game, daily, reward, etc.).
- No changes to EventBus contracts (MUST NOT mutate; health only *observes* listener counts).
- No changes to get_service impl (it will just work for new svc).
- No changes to atomic tx paths, scheduler job *handlers* (only observe status), middleware, FSM, etc.
- 0 new deps in base (endpoint may add aiohttp optional; document as such).
- 0 handler logic (all in HealthService).
- Existing analytics remains separate (health is status/ping, analytics is metrics/export).

**Consumers / Call sites (map):**
- **bot.py (on_startup/on_shutdown):** already wires scheduler + 5x besitos_awarded listeners + expired check + admin notify. Add: health server task (optional), perhaps log "health | checks_available". get_scheduler/get_event_bus consumers stay (streak_scheduler_bridge.py also calls get_scheduler; tests; sync_claude.py).
- **Services:** SchedulerService (jobs via get_jobs or new public get_status), EventBus (via get_event_bus + new get_status or _listeners len), Analytics-like (reuse query patterns), ChannelService/VIPService/BesitoService/BackupService/StoryService (for counts: pending, active subs, balances sanity, story progress/archetype counts, last backup file mtime). HealthService *calls* them read-only (or direct models for speed like Analytics). NO cross-mutation.
- **Handlers:** analytics_handlers.py (Command /stats/export using get_service + is_admin) precedent for new health Command or cb. admin_*_handlers (callbacks + is_admin lambda filters). New health view will follow *exactly* "with get_service(HealthService) as h: ...; 1 call".
- **Tests:** unit (analytics_service, scheduler, event_bus, besito, channel, vip, story, game, daily, reward, store, broadcast); integration (cross_service_atomicity.py gold, reaction_mission_flow.py, reaction_full_chain.py, free_entry_flow.py (scheduler/pending/channel jobs), vip_* flows/lifecycles/complete/ritual, invariants, streak, trivia etc.); handlers tests (admin, story_user, mission etc.); conftest fixtures (db_session, sample_*).
- **External/platform:** Railway (startCommand alembic+bot; commented healthcheckPath="/health" + timeout; will need later config for /health or custom port); Procfile (worker only); DEPLOY.md (old TG /health cmd example, update minimally); curl/monitoring (new JSON); terminal ops (new script).
- **EventBus:** health can observe registered (for "bus health"), but emits remain best-effort post-commit; 0 change to schedule_emit/gather/return_exceptions/DESIRED CONTRACTs.
- **No external (no current /health).**

**3 Critical Systems — Explicit 0 Risk Check:**
- **Gamification (besitos, missions, daily, reactions, minigames, streaks, trivia):** Health checks are pure reads (balance counts/sanity e.g. "no negative balances?", recent tx volume via BesitoTransaction count in last N, no writes). 0 risk to credit_besitos/debit paths, REACTION tx + mission best-effort + event emit, daily claim atomic, game payouts, streaks. "0 risk to gamif credits, reaction_mission_flow, daily atomic, partial failure contracts." Re-runs of golds protect.
- **Narrative (story nodes, archetypes, achievements, FSM/quiz, progress, inverse besitos on logros):** Health can count UserStoryProgress, UserStoryAchievement, current_node etc (read-only). 0 risk to advance_to_node, calculate_archetype, _grant_achievement (besitos credit path protected by story listener "MUST NOT credit" + atomicity). 0 impact on quiz FSM or story_user_handlers.
- **Channel/VIP (subs, pending requests, auto-approve wait, expire, ban propagation, free entry ritual, VIP tokens/tariffs):** Health uses ChannelService (get_free/vip, count_pending, get_ready_to_approve) + VIPService (get_active_subscriptions, get_expired, get_expiring) + reads on Subscription/Pending/Channel (is_active, end_date, scheduled_approval_at). 0 risk to create_pending, approve logic (in _process_pending_requests + handlers), expire_subscriptions cron (ban/unban + clear vip_entry), startup expired processing, free welcome jobs. "0 risk to channel approvals/pending/expirations, VIP grant/revoke, ban prop, atomic subs." Re-runs of free_entry_flow + vip_* + scheduler unit protect.

**Atomicity / Contracts / get_service / EventBus:** Health never participates in tx; best-effort reads only (like current analytics). No schedule_emit or listeners added. get_service used exactly as in analytics_handlers (context auto-close). 0 violation of "handlers 1 svc", "services own logic".

**Affected tests (explicit list for re-runs/gates):**
- Golds/invariants: `tests/integration/test_cross_service_atomicity.py` (full: happy REACTION, partials reward/package/mission/daily, daily_claim success/fail, reward_redemption; must use -q --tb=line -p no:cov --override-ini="addopts=" + patch schedule_emit + DESIRED + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + TestSession + 777 TG + gather + N806 tol w/doc).
- Reaction/mission: `tests/integration/test_reaction_mission_flow.py`, `test_reaction_full_chain.py`, `test_reaction_limit.py`.
- Scheduler/channel: `tests/integration/test_free_entry_flow.py` (all Test* pending/welcome/approve/get_ready + job flows), `tests/unit/test_scheduler.py` (triggers, schedule_free_welcome ID contract TG vs PK).
- VIP: `tests/integration/test_vip_flow.py`, `test_vip_flows.py`, `test_vip_subscription_lifecycle.py`, `test_vip_complete_cycle.py`, `test_vip_ritual_flow.py`, `test_callbackdata_vip*.py`; unit/test_vip_service.py.
- Narrative/story: `tests/unit/test_story_service.py`, `tests/handlers/test_story_user_handlers.py`, `tests/integration/test_streak_protection_flow.py` (some overlap), story FSM tests.
- EventBus + bus-related: `tests/unit/test_event_bus.py` (register/emit, logs, return_exceptions, noop).
- Service units: test_besito_service, test_daily_gift_service, test_broadcast_service_reaction_flow, test_reward_service, test_game_service, test_channel_service, test_analytics_service, test_store_service (for balance paths).
- Handlers/admin: tests/handlers/test_*_admin_handlers.py (esp mission/gamif/store etc + any admin cb tests); will need update for new health cb if added.
- Broader: `tests/integration/test_invariants.py`, streak/trivia flows if scheduler overlap.
- Exact pytest invocations (targeted, fast): `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "cross_service_atomicity or reaction_mission_flow or reaction_full_chain or free_entry_flow or TestScheduler or scheduler or vip or story or event_bus or atomicity or daily_claim or besitos or TestCrossServiceAtomicity or TestFreeEntry or TestAnalytics or health" tests/`
- Non-pytest gates: ruff (on new/touched py), format --check, bot smoke (`python -c "import bot; print('bot import ok'); from services import get_service, HealthService; print('get_service Health ok')"` + manual register if any), manual terminal run (`python -m scripts.health_check --json`), manual /health curl (if endpoint), full bot startup smoke (no crash in on_startup).

**Other consumers:** Railway healthcheck (future), monitoring, Custodios via bot/terminal (no direct DB per CLAUDE).

---

## Recommended Tight Scope + Design Notes (for planner/executor)

**Tight scope (builds on existing, low risk, 0 creep):** Core checks first (DB, bot/uptime, channels/pending, scheduler jobs, event_bus listeners count, besito sanity + tx volume, VIP active/expiring, narrative progress/archetype/achievement counts, backup last success via file mtime or log). Friendly bot (admin-only via is_admin + get_service) + terminal script. Simple JSON /health. Later: more metrics, structured logging expansion everywhere, alerts. Follow "Start with core... friendly bot command + terminal script, simple /health JSON."

**Exact suggested files/class/methods (conventions):**
- `class HealthService:` (in services/health_service.py; like AnalyticsService: __init__(self, db: Session = None), self.db, self._owns_session, def _get_db(self), def close(self)).
- Checks (async def or sync? prefer sync for simplicity like analytics, wrap in timeouts where needed; all <=50 LOC; verb+context+result names):
  - `def check_db_connectivity(self) -> dict: ...` (try: with get_db_session() as s: s.execute(text("SELECT 1")).scalar(); return {"status": "ok", "latency_ms": ..., "pool": ...} except Exception as e: {"status": "fail", "error": str(e)[:100]} ; log "health_service | check_db_connectivity | user_id=0 | status=ok latency=..")
  - `def check_bot_runtime(self) -> dict: ...` (uptime from global start_time in bot.py or module; polling inferred; last_activity if trackable lightly; {"status":"ok", "uptime_seconds": , "start_time": iso})
  - `def check_channels_status(self) -> dict: ...` (with get_service? or direct: ch = ChannelService(); free=len(ch.get_free_channels()), vip=..., pending=ch.count_pending_requests(), ready=len(ch.get_ready_to_approve()); return {"status": "ok" if pending<100 else "degraded", "free_channels": , "vip_channels":, "pending_requests":, "ready_to_approve": } ; ch.close() or use context)
  - `def check_scheduler_jobs(self) -> dict: ...` (scheduler = get_scheduler(); if not: fail; jobs = scheduler._scheduler.get_jobs() if hasattr else []; list [{"id":j.id, "name":j.name, "next_run_time": str(j.next_run_time), "trigger": str(j.trigger)} for ...]; status ok if all scheduled; log "health_service | check_scheduler_jobs | user_id=0 | jobs=N next_approve=..")
  - `def check_event_bus_listeners(self) -> dict: ...` (bus=get_event_bus(); counts = {e: len(ls) for e,ls in bus._listeners.items()}; total=sum; {"status":"ok", "total_listeners": total, "by_event": counts, "besitos_awarded_listeners": counts.get(EVENT_BESITOS_AWARDED,0)} )
  - `def check_critical_services_sanity(self) -> dict: ...` (besito: e.g. neg = count negative balances (query), recent_tx = BesitoTransaction count last hour; vip: active = VIPService().get_active... count; narrative: progress_count = query(UserStoryProgress), archetypes_assigned=...; return {"besitos": {"neg_balances":0, "recent_tx_vol":N, "status":"ok"}, "vip":..., "narrative":... } )
  - `def check_backup_status(self) -> dict: ...` (find latest in backups/ dir mtime or parse; {"last_backup": iso or None, "age_hours": , "status": "ok" if <24h else "degraded"})
  - `def get_overall_status(self) -> dict: ...` (run all checks, aggregate "healthy" if all ok else "degraded"/"unhealthy"; add "timestamp": datetime.now(UTC).isoformat(), "version": "1.0-spike"; structured log "health_service | get_overall_status | user_id=0 | overall=healthy checks=7")
- Example check structure (in code):
  ```python
  def check_db_connectivity(self) -> dict:
      """Check DB connectivity and basic ping. Best-effort, timeout protected."""
      start = time.time()
      try:
          # Use sync context; for hard timeout wrap if needed (or accept short block)
          with get_db_session() as db:
              db.execute(text("SELECT 1")).scalar()
          latency = int((time.time() - start) * 1000)
          logger.info(f"health_service | check_db_connectivity | user_id=0 | status=ok latency_ms={latency}")
          return {"status": "ok", "latency_ms": latency}
      except Exception as e:
          logger.warning(f"health_service | check_db_connectivity | user_id=0 | status=fail error={e}")
          return {"status": "fail", "error": str(e)[:120]}
  ```
- Wire in bot.py on_startup: after `await scheduler.start()` and listeners:
  ```python
  # Health/observability (Item 11 spike)
  try:
      from services.health_service import HealthService  # or via get
      # For endpoint if implemented:
      # asyncio.create_task(start_health_http_server(port=int(os.getenv("HEALTH_PORT", "8080"))))
      logger.info("health_service | startup_checks_available | user_id=0 | result=ready")
  except Exception as e:
      logger.warning(...)
  ```
- Admin view registration (no logic in handler): In analytics_handlers.py (or dedicated admin_health_handlers.py exported + included in bot.py like analytics_router):
  ```python
  @router.message(Command("health"))
  async def health_cmd(message: Message):
      if not is_admin(message.from_user.id):
          await ... (LucienVoice.health_access_denied())
          return
      try:
          with get_service(HealthService) as svc:  # exactly 1 service
              health = svc.get_overall_status()
          await message.answer(LucienVoice.system_health(health), parse_mode=ParseMode.HTML)
      except Exception as e:
          logger.error(f"health | cmd | user_id={message.from_user.id} | error={e}")
          await ... error
  ```
  For menu cb: similar in admin cb router, data=="admin_health", same pattern (1 svc call). Add router include if new file.
- Terminal script example structure (scripts/health_check.py):
  ```python
  #!/usr/bin/env python
  import argparse, json, sys
  from services import get_service, HealthService
  # ... parse --json --verbose
  with get_service(HealthService) as svc:  # or HealthService(db=...) for direct
      h = svc.get_overall_status()
  if args.json: print(json.dumps(h)); sys.exit(0 if h['status']=='healthy' else 1)
  else: print(LucienVoice... or human format)
  ```
  chmod +x, support user_id=0 in internal logs.
- For HTTP endpoint (design): New `health_server.py` (minimal):
  ```python
  from aiohttp import web
  async def health_handler(request):
      # best effort, no db passed; instantiate HealthService() inside (owns)
      with get_service(HealthService) as svc:
          data = svc.get_overall_status()
      return web.json_response(data)
  app = web.Application(); app.router.add_get('/health', health_handler)
  # runner in start_health_http_server()
  ```
  Start non-blocking: `asyncio.create_task(web._run_app(runner, ...))` or use asyncio.gather style. Separate port to not conflict with aiogram polling (0 breakage). Env: HEALTH_ENABLED=1, HEALTH_PORT=8080. JSON: {"status": "healthy|degraded|unhealthy", "checks": {...dict per check...}, "timestamp": "...", "uptime_s": 12345}. Lightweight queries only (no full exports). Timeout per check (use asyncio.wait_for on sync via executor if strict).
- Logging: Every check + overall + errors: "health_service | <action> | user_id=0 | resultado=..." (or admin_id for bot calls). Follow event_bus precedent.
- Admin-only: All bot views use `is_admin()` (utils/admin.py) + deny with Lucien voice (like analytics_access_denied). Terminal/script is ops (assumes trusted env).
- 0 heavy: Reuse SQLA sessions, no new tables, counts not full scans where possible (Analytics does .count() + sum on small tables ok for bot).
- Caching/rate: Simple in-mem last_result + ts (30s TTL) inside HealthService for repeated calls; rely on ThrottlingMiddleware for bot cmds.
- Voice: Lucien 3rd person, "Diana", "custodios", "visitantes", elegant. E.g. in system_health: "🎩 <b>Lucien:</b>\n\n<i>El pulso del reino...</i>\n\n✅ DB: latencia 8ms\n⚠️ Scheduler: 5/5 jobs (next expire 2h)\n..."

**How to avoid logic in handler:** All aggregation/render prep in HealthService + LucienVoice. Handler: guard is_admin + 1 svc call + answer + answer() + log event.

**Safe extension points:** Add public methods to SchedulerService (def get_jobs_status(self) -> list[dict]) and InternalEventBus (def get_listener_counts(self) -> dict) if private access ugly (small, read-only, non-breaking; document in decisions). HealthService can import/use get_ directly for system components.

**Docs at end:** documentador updates HARDENING_ROADMAP (per prior patterns in decisions), append decisions, update CLAUDEs. GSD pre-logs + self-check PASSED + critical tests list + pool phrase in final handoff.

---

## List of Critical Tests/Gates for Future (exact)

- **Pytest targeted (run with flags for speed/strict):** 
  `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "cross_service_atomicity or TestCrossServiceAtomicity or reaction_mission_flow or reaction_full_chain or free_entry_flow or TestFreeEntry or TestScheduler or scheduler or vip or TestVip or story or TestStory or event_bus or TestEventBus or atomicity or daily_claim or besitos or health or TestHealthService or TestAnalyticsService" tests/`
- Specific gold re-runs: full `tests/integration/test_cross_service_atomicity.py` (all 8+ test_* partials + happy + daily + reward; validate "credit survives", tx counts/deltas, patches, DESIRED strings, gather).
- Scheduler/channel: full `tests/integration/test_free_entry_flow.py` (pending approve, welcome job, get_ready, inactive clean, errors with rollback).
- Units: `tests/unit/test_scheduler.py`, `test_event_bus.py`, `test_analytics_service.py` (adapt pattern), `test_channel_service.py`, `test_vip_service.py`, `test_besito_service.py`, new `test_health_service.py`.
- Handlers: relevant admin/story/mission handler tests post any cb addition.
- **Non-test gates (in GSD per phase):** 
  - ruff + format --check on services/health_service.py services/__init__.py handlers/*health*.py scripts/health_check.py utils/lucien_voice.py keyboards/inline_keyboards.py bot.py decisions.md (etc)
  - Bot smoke: `python -c "import asyncio, bot; from services import get_service, HealthService; print('imports+get_service ok'); h=HealthService(); print(h.check_db_connectivity())" ` + manual on_startup import/register simulation.
  - Manual endpoint: `curl -s http://localhost:8080/health | python -m json.tool` (status, checks keys, no secrets).
  - Terminal: `python -m scripts.health_check --json` (valid json, exit 0 on healthy); `python -m scripts.health_check --verbose` (Lucien sections).
  - Grep verifs: no "self\.(besito|other)_service" new; 1 svc calls in health handlers; logs with "health_service | "; get_service(HealthService) usages; "Item 11" refs in decisions/gsd.
  - Full bot start smoke (no crash, scheduler jobs registered, health available).
  - LOC <50 for new funcs; naming verb+context+result.
- **Self-check in gsd log:** Structure with pre-entries counts, "PASSED", explicit "tests críticos a re-correr en el futuro" list, "0 risk to 3 systems", pool phrase, handoff.

---

## Risks / Mitigations + Safe Points + DoD

**Risks + Mitigations (conservative):**
- Blocking checks under load affecting polling/gamif/narrative/channel jobs: Mitigation — all checks best-effort + short timeouts (asyncio.wait_for or time budget); light queries only (counts, not full table scans or CSV); separate from main tx; non-blocking server task. 0 side effects.
- False positives / noisy admins: Soft statuses (ok/degraded on thresholds e.g. pending>50 or no recent backup); include details + "Diana recomienda..."; no auto-alerts yet.
- Exposing sensitive (user counts, exact balances? but aggregate only): Admin-only for bot (is_admin); for /health keep high-level aggregates (no per-user PII, no secrets like tokens/urls); terminal ops-only.
- New dep (aiohttp) for endpoint: Mitigation — make endpoint optional (if import fails or HEALTH_ENABLED=0, skip server; log warning); or scope initial impl to bot cmd + terminal (0 dep), add HTTP in follow-up phase. Railway healthcheck remains commented until validated.
- Private access (_scheduler, _listeners): Add thin public get_*_status() methods (read-only) in SchedulerService + InternalEventBus; or accept in HealthService (system domain) with comments. Low blast.
- Test flakiness / N806 / DB in tests: Follow precedents (TestSession/tmp_path in golds, N806 tol w/doc, fresh 777 TG, guards for get_service).
- Handler rule violation: Enforce "exactly 1 svc" + no logic in all new/updated handlers (use get_service context); update tests accordingly.
- GSD/LOC/logging/naming: Pre every modify (echo >> gsd log), ruff/LOC checks in phases, explicit logs in health methods.
- Stale health (e.g. scheduler jobs): Jobs are dynamic but health reflects current APScheduler state (jobs persist via SQLAlchemyJobStore).

**Safe points (revertable with 0 residual):**
- Delete services/health_service.py + test + script + 1-2 lines in __init__.py/bot/handlers/keyboards/voice/decisions/CLAUDEs = clean.
- Remove button + cb handler = no menu impact.
- Skip endpoint wiring = bot unaffected.
- Revert bot on_startup addition.
- Precedent: EventBus was "completely removable" per decisions.

**DoD (for gsd-planner/executor phases + final):**
- All 5-6 phases GSD pre-logs (counts 5-10+/fase), self-check "PASSED" with full structure + critical tests list + pool phrase + "0 behavior/0 atomicity/0 risk to 3 systems".
- HealthService implements listed checks, logs in format, read-only, <50LOC, uses get_service compat, closes properly.
- Bot admin view (cmd or menu cb) + terminal script functional, use get_service + is_admin + LucienVoice, exactly 1 svc.
- Endpoint (if in scope) serves JSON on /health, non-blocking, no breakage to polling.
- 0 changes to critical flows/services (grep confirm 0 new writes/mutations in gamif/narrative/channel paths).
- Tests: new unit green; targeted -k re-runs of golds + scheduler + free_entry + event_bus + vip/story all green with 0 regressions; ruff clean; smokes pass.
- Docs: decisions entry, services/CLAUDE table+notes, (documentador handles ROADMAP).
- Grep/LOC/verif in final GSD: "health_service |" logs present, get_service(HealthService), no privates without comment or public wrapper, etc.
- Handoff: "Item 11 closed. ... of new pool of 4. Ready for gsd-executor ... + arch-enforcer re-scan (enfocado en health_service + get_service usage + admin views + 3 critical systems read-only) + test-guardian (correr los tests críticos listados)".

---

## Recommendation

Proceed with gsd-planner for a 5-6 phase tight implementation (prep, service+checks, endpoint, bot admin view, terminal script, tests+docs via documentador).

**Ready for gsd-planner (observability/health item, next after Item 10 in current pool or new tirón)**

Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.

(Full GSD pre-log in .planning/quick/gsd-impact-analyzer-item11-observability-health.log (15+ entries); report persisted; MEMORY.md updated with pointer + exec summary.)
