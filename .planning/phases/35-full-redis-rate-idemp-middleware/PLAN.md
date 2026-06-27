# PLAN: Full Redis backing for rate/idemp middlewares (when REDIS_URL) + exact in-mem fallback; optional redis client in ctors (default None, public API unchanged); centralize share in bot.py create_storage + wiring; use SET NX EX or ZSET parity for rate + dict for idemp; protect exact logs/Lucien voice/ADMIN_BYPASS/TTL/monotonic/cleanup/registration order (idemp before throttle on cb); minimal test parity (keep in-mem, optional redis path); 0 behavior/0 atomicity/0 prod change; critical: guarantee skip before any Besito credit (gamif double-credit risk) (Item 1/35, first of new pool of 4)

**Type:** gsd-planner output (for gsd-executor + hardener seq)  
**Date:** 2026-06-26  
**Focus:** Tight hardening building on middleware gsd-mw-hardening + pool 34 hygiene (rate/idemp logging already aligned); addresses remaining "in-mem rate/idemp (prod risk)" from initial analysis + ROADMAP sec5 "full Redis for rate/idemp (in-mem still)" + Proposed Next #2. Leverages bot.py create_storage Redis precedent (Redis.from_url when REDIS_URL), FSM RedisStorage, redis==5.0.1 dep, exact fallback discipline (MemoryStorage precedent), public no-arg ctors (ThrottlingMiddleware(), IdempotencyMiddleware()). Source of truth: impact-analyzer key excerpts for pool35 item1 (verbatim below). Golds protected verbatim. GSD pre every edit/gate/ruff/pytest/grep/smoke/self-check. Self-check PASSED + pool phrase + handoff. "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

**Input principal (source of truth):** 
- Impact report key excerpts (verbatim): "Objective: Full Redis backing (when REDIS_URL) for ThrottlingMiddleware (aiolimiter in-mem per-user) + IdempotencyCache (in-mem seen dict TTL60) with EXACT fallback when absent or no redis. Files to change: primarily middlewares/rate_limiter.py, middlewares/idempotency.py, bot.py (share redis_client + wiring comments), minimal tests/unit/*middleware*.py (keep in-mem tests, optional redis path), comments only elsewhere. Public API unchanged (ThrottlingMiddleware(), IdempotencyMiddleware() no-arg). Preserve: exact logs format, Lucien voice throttle msg, ADMIN_BYPASS (live from config), registration order (idemp before throttle on cb), monotonic TTL semantics, cleanup. Golds to protect: cross_service_atomicity, all reaction_* (full_chain, mission_flow, limit), invariants, daily atomic, store atomic gold TestStorePurchaseAtomicGold, vip flows, broader handler flows that do cb credits/purchases. Exact test cmd flags: -q --tb=line -p no:cov --override-ini="addopts=". Critical risk: gamif double-credit (dupe cb or missed throttle across instances) → must guarantee skip before any Besito credit. Mitigate by making Redis path equivalent. Recommended outline: optional redis: Redis = None in ctors; centralize client in bot.py create_storage or on_startup; if redis use SET NX EX or ZSET for rate; else pure current in-mem. Risks/gotchas: distributed rate algo must parity single-inst; async error handling (no leak); test internals still work on fallback; no model/service change."
- .planning/HARDENING_ROADMAP.md (end of pool 34 section + "What Is Missing" + "Proposed Next" + pool phrase verbatim + metrics; references "in-mem rate/idemp (prod risk)", "full Redis backing for rate/idemp (builds middleware)").
- Precedents al pie: pool 34 PLANs (34-observability-health-docs/PLAN.md + 34-*-SUMMARYs + gsd-34-*.log), 33-*-PLAN.md (structure: header+pool phrase, In/Out 0/0/0, 5-7 gated phases F1 prep + ..., DoD, exact pytest cmds, GSD pre every, safe points, gold lists, self-check template, arch/testg verdicts, handoff, "copy al pie", instructions to executor); bot.py create_storage (Redis.from_url + fallback log + MemoryStorage), middleware registration (Error outer → Idempotency (cb) → Throttling (cb+msg); comments exact), 34-item4 hygiene (rate/idemp logging already "módulo | ..."); gsd-mw-hardening impact + rate/idemp tests + legacy shim notes.

**Current state (read first):** 
- middlewares/rate_limiter.py: ThrottlingMiddleware __init__ no-arg; pure in-mem _limiters: dict[int, tuple[AsyncLimiter, float]] + _lock; _get_limiter, _cleanup_idle (monotonic TTL 300s), __call__ (bypass ADMIN, cleanup, acquire, _on_limit_exceeded with exact Lucien voice answer + show_alert); logs "rate_limiter | <action> | user_id=... | result=..."; RateLimiterMiddleware alias; no redis.
- middlewares/idempotency.py: IdempotencyCache __init__(ttl=60) with _seen: dict[str,float]; is_duplicate (cleanup + check/mark); mark_processed; global idempotency_cache; IdempotencyMiddleware (only CB, is_duplicate → answer + skip handler (critical for no dupe credit), pass-through else); logs "idempotency_middleware | skip_duplicate | user_id=... | result=..."; comment "Para producción con múltiples instancias, usar Redis."
- bot.py: create_storage() (if REDIS_URL: redis_client=Redis.from_url... else fallback Memory; no shared export yet); middleware wiring in main() with explicit order comment ("IdempotencyMiddleware for callback_query only ... ThrottlingMiddleware for callback_query (after idemp...)"); on_startup has EventBus regs + health (no mw redis yet); import redis.asyncio.Redis already present.
- tests/unit/test_rate_limit_middleware.py + test_idempotency_middleware.py: unit coverage for per-user, bypass, dupe skip, answer robustness, pass-through, non-CB; patch cache for idemp; use real config; no redis paths yet.
- config/settings.py: RateLimitConfig (RATE/ PERIOD/ADMIN_BYPASS); no redis config (env REDIS_URL direct).
- 0 impact on models/services/handlers (comments only elsewhere per impact).

**GSD enforcement (mandatory):** Executor MUST append GSD pre-log (timestamp | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie>) to `.planning/quick/gsd-35-full-redis-rate-idemp-middleware.log` BEFORE every modification, gate, ruff, pytest, grep, smoke, self-check, or summary. Use style from 34/33 gsd logs (detailed, wc -l after, "GSD pre-edit <file> (F<N>) - ...", "GSD pre-ruff F<N>", "GSD pre-pytest ...", "F<N> safe point", "GSD pre self-check"). No edits without pre-log. "Planner did INIT + pre-mkdir + pre-write entries + multiple pre-log."

---

## 1. Alcance preciso (In / Out explícito; tight per impact excerpts + 0/0/0 + protects 3 crit + contracts)

### En esta entrega (scope tight; builds middleware hardening; leverages bot redis + create_storage pattern al pie):
- **Optional redis client support (default None, public API unchanged):** Add `redis: "Redis | None" = None` (import inside or string for type, per instructions) to ThrottlingMiddleware.__init__ and IdempotencyMiddleware.__init__ (or to cache helper). Calls ThrottlingMiddleware() / IdempotencyMiddleware() remain valid and identical. Store as self._redis if provided.
- **Centralize redis client in bot.py:** Extend create_storage() or add small helper (e.g. after storage= , or return also client) to create shared `redis_client = Redis.from_url(redis_url) if redis_url else None`; pass explicitly to mw instances in wiring: ThrottlingMiddleware(redis=redis_client), IdempotencyMiddleware(redis=redis_client) (or cache init). Add wiring comments + "Item 1/35 redis backing" note. Share the same client used for FSM where possible (reuse if created).
- **ThrottlingMiddleware Redis path + exact in-mem fallback:** If self._redis: implement distributed rate using SET NX EX (simple) or ZSET + timestamps for sliding window parity with aiolimiter (RATE per PERIOD). Fallback: pure current in-mem _limiters + aiolimiter + _cleanup + _get_limiter when no redis or no REDIS_URL. Preserve monotonic, TTL cleanup, lock semantics, logs exact, bypass live from config, Lucien voice _on_limit_exceeded identical.
- **IdempotencyCache + Middleware Redis path + exact fallback:** If redis: use SET key=f"idem:{cb_id}" NX EX ttl (atomic mark + check). Else: pure current dict _seen + cleanup + is_duplicate/mark. Keep global idempotency_cache for fallback compat (tests patch it); support redis in cache class or inside mw. Preserve TTL=60 monotonic, logs exact format, answer on skip, no handler call on dupe (guarantee before any credit), pass-through else, robustness on answer fail.
- **Wiring/comments + minimal hygiene:** bot.py middleware section + create_storage comments updated for redis sharing + "full Redis backing when present (exact fallback, parity for distributed dupes/spam)"; no behavior change. Logging already aligned from pool34 item4.
- **Tests (minimal per impact):** Keep all current in-mem unit tests passing unchanged (they exercise fallback). Add optional redis paths in test_rate... + test_idemp... (e.g. if redis available or with patch/fakeredis-like mock; or skipif no REDIS; test internal is_duplicate / limiter logic with redis path returns same semantics). Re-run on fallback always. No new files beyond minimal edits.
- **Golds + gates:** Re-run exact golds with flags; 0 attributable regressions. Arch + test-guardian + self-check.
- **Traceability:** decisions.md append (Item 1/35 entry), gsd log, this PLAN + (opt post) SUMMARY; documentador at pool close for ROADMAP.
- **Files (minimal, exact):** .planning/quick/gsd-35-full-redis-rate-idemp-middleware.log (appends only), middlewares/rate_limiter.py, middlewares/idempotency.py, bot.py (create_storage + main wiring + comments), tests/unit/test_rate_limit_middleware.py (parity + optional), tests/unit/test_idempotency_middleware.py (parity + optional), decisions.md (entry); comments only elsewhere.

### Fuera explícitamente (no creep):
- NO change to public API (ctors remain callable with 0 args; no new required params).
- NO behavior/UX/rate semantics change (Redis path equivalent to in-mem for single-inst; distributed parity for multi-inst to prevent dups).
- NO mutation on 3 crit paths (rate/idemp are guards before credit/claim/purchase; guarantee skip protects gamif besitos/reactions/daily; narrative/channel/VIP untouched).
- NO change to atomicity/EventBus/get_service contracts (middlewares orthogonal pre-handler).
- NO new models/migrations/services/handlers (comments only).
- NO broad rate algo rewrite (parity only; use SET/ZSET as recommended).
- NO test behavior change on fallback; in-mem tests must continue to cover current paths 100%.
- NO touching golds or prod credit sites.
- 0 prod change (REDIS_URL already supported for FSM; this extends guards safely).

**Comportamiento observable:** Identical on single instance or no REDIS_URL (pure fallback). With REDIS_URL in multi-inst: distributed dedup + rate prevents dup CB executions / spam that could cause double-credit on gamif (critical guarantee: skip before handler/credit). Logs, Lucien voice, ADMIN_BYPASS, TTL, cleanup unchanged. Golds pass. UI/flows unchanged.

---

## 2. Fases (strict order, 7 small gated; GSD pre every; copy precedents al pie)

**F1 prep/GSD/baseline** (GSD pre; mkdir phase dir if needed (done); read this PLAN full + impact excerpts verbatim + .planning/HARDENING_ROADMAP.md (pool34 close + What Is Missing + Proposed Next redis item + phrase) + 34-observability...PLAN.md + 33-*-PLAN.md full + recent gsd logs/SUMMARYs for style + bot.py (create_storage + middleware wiring + comments + on_startup) + middlewares/*.py full + tests/unit/test_*_middleware*.py full + config/settings.py + grep redis/REDIS in bot/middlewares/tests + current rate/idemp logs + Lucien string; baseline ruff --check on touched; baseline targeted pytest exact: `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "rate or Throttling or idempotency or TestThrottling or TestIdempotency or cross_service_atomicity or reaction or daily or vip or store or atomicity or invariants" tests/` (expect green or pre-exist only); greps for current in-mem ( _limiters, _seen, AsyncLimiter, is_duplicate, global idempotency_cache, no redis in mw), bot middleware order comment, REDIS_URL in create_storage, bypass/ADMIN, Lucien answer text; confirm golds list + fixtures; read Health/observability logging precedent if relevant for any hygiene; "F1 safe point - DoD: reads + baseline + greps + ruff baseline done". DoD marked.)

**F2 bot redis client central + optional pass to mws** (GSD pre each edit; extend create_storage() to also produce/return or expose redis_client = Redis.from_url(...) if url else None (reuse existing logic, add log "rate/idemp redis client: available" or fallback); in main() after storage = create_storage(), instantiate with optional: ThrottlingMiddleware(redis=redis_client), IdempotencyMiddleware(redis=redis_client) (or pass to cache); add precise comments: "# Redis backing for middlewares (pool35 Item 1/35): shared client from create_storage when REDIS_URL; exact fallback when None (in-mem parity); registration order preserved: Error → Idemp (cb) → Throttle (cb/msg)"; no change to other startup; ruff; greps for "redis_client" + mw(redis= + "Item 1/35"; "F2 safe point". DoD marked. 0 beh.)

**F3 rate_limiter redis path + exact in-mem fallback** (GSD pre; edit rate_limiter.py: __init__(self, redis: "Redis | None" = None) — import Redis inside if needed for type to avoid top dep if absent; self._redis = redis; keep all current in-mem _limiters/_lock/_get_limiter/_cleanup/_on... ; in __call__ and helpers: if self._redis: <redis rate impl using SET NX EX or ZSET for per-user rate window parity (e.g. key f"rate:{user_id}", score monotonic time, trim > period, count <= RATE); else: pure current in-mem path; preserve every log string, monotonic, TTL cleanup, lock, bypass live, exception on acquire → _on_limit_exceeded (Lucien exact), answer robustness; add arch comment "Item 1/35 redis backing + exact fallback"; ruff; targeted pytest rate tests (in-mem path); greps for new if/else + keys; "F3 safe point". DoD marked.)

**F4 idempotency redis path + exact fallback** (GSD pre; edit idempotency.py: update IdempotencyCache to accept optional redis: Redis|None=None (or inside mw); if redis use atomic SET f"idem:{cb_id}" NX EX self.ttl (check via exists or lua-like); else pure current _seen dict + cleanup in is_duplicate; keep mark_processed compat; update IdempotencyMiddleware __init__(self, redis: ... = None) and pass to cache or handle; global cache remains for fallback/tests (patch continues to work); preserve exact logs "idempotency_middleware | skip_duplicate | ...", answer on dupe, return None no handler, pass-through Messages/non-dupes, robustness answer fail, TTL=60 monotonic; critical: dupe path MUST skip before handler; add comment "Item 1/35 + exact fallback per impact"; ruff; pytest idemp tests (fallback); "F4 safe point". DoD marked. No beh change.)

**F5 unit test parity + new redis paths (minimal)** (GSD pre; edit tests/unit/test_rate_limit_middleware.py + test_idempotency_middleware.py: ensure 100% current in-mem paths still pass (no breakage on fallback); add minimal optional redis tests (e.g. @pytest.mark.skipif(not os.getenv("REDIS_URL"), reason="redis optional"); or patch Redis and assert SET/ ZSET calls or is_duplicate semantics equivalent; test internal _get or cache with redis; keep all existing assertions; import inside tests if needed; ruff; full pytest on *middleware* files + spot broader; greps for "fallback" + "redis" in tests; "F5 safe point". DoD marked. Internals still work on fallback per impact.)

**F6 wiring/comments/gold cmds + ruff** (GSD pre; finalize any wiring tweaks + expand comments in bot.py + middlewares (e.g. "guarantees skip before credit on dupe CB across instances"); run ruff on all touched (fix safe style only); re-run exact gold commands (see section 4) + broader smoke with flags; bot smoke `python -c "import bot; from middlewares.rate_limiter import ThrottlingMiddleware; from middlewares.idempotency import IdempotencyMiddleware; print('ok no-arg ctors')"; terminal if redis present; greps (0 public API change, redis optional passed, fallback paths present, logs/Lucien preserved, order comment, "Item 1/35"); "F6 safe point". DoD marked.)

**F7 self-check + handoff (ready for arch + testg + documentador pool close)** (GSD pre; full self-check PASSED (phases/DoD/gates/archivos/tests passed; reglas: GSD pre every, scope tight per PLAN, 3 crit protected via re-runs/greps (esp gamif no dupe credit guarantee), precedents (bot create_storage redis + fallback, mw order, in-mem exact, logging, Lucien, robustness) copied al pie, 0/0/0, no public API change, minimal tests, ruff); append pool phrase + "Item 1/35 closed. First of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch + testg + documentador (final pool close + ROADMAP update)"; handoff explicit.)

---

## 3. Copia patrones **al pie de la letra**

### Redis + fallback (bot create_storage precedent + impact rec)
- create_storage: if REDIS_URL try Redis.from_url else warn fallback; reuse/share client.
- Optional param with default: __init__(self, redis: "Redis | None" = None) — call sites with 0 args unchanged.
- Exact fallback: when None or no url: 100% identical current in-mem code paths.
- For redis rate: SET NX EX or ZSET (parity single-inst behavior + distributed safety); idemp SET NX EX.
- Async error handling: no leaks (existing try/robustness preserved).
- Logs + Lucien + ADMIN + TTL + cleanup + order: verbatim identical.

### GSD pre + self-check + pool phrase (34/33/29/28 precedents)
- Append before every: timestamp | PHASE N | GSD pre-... - desc + refs DoD + patrones (bot redis, mw fallback, impact critical dupe guarantee, 3 crit, 0/0/0).
- wc -l after key steps.
- "F<N> safe point", full self-check at end with checklist + phrase verbatim + "Item 1/35 closed. First of new pool of 4."
- Arch: PASS or PASS WITH NOTES 0 critical. Test-guardian: "suite protege adecuadamente".

### Golds + 0 impact + UI/Lucien (all recent)
- No touch to credit/claim/purchase paths; rate/idemp only guards.
- 3 crit + atomicity/EventBus/get_service always protected (re-runs + no writes).
- Lucien voice throttle answer exact preserved.
- Review loop: effort ~4 until 0 open issues.

### Middleware registration (bot.py comments al pie)
"ErrorHandler as *outer* ... IdempotencyMiddleware for callback_query only ... ThrottlingMiddleware for callback_query (after idemp so duplicate retries do not consume rate quota) ..."

---

## 4. Golds a re-ejecutar (exactos; protect 3 crit + contracts + critical dupe guarantee; 0 attributable reg target)
- Middleware + atomic/cross: `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "rate or Throttling or idempotency or TestThrottling or TestIdempotency or cross_service_atomicity" tests/`
- Reaction chains + daily + invariants (gamif critical): `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "reaction_full_chain or reaction_mission_flow or reaction_limit or daily or invariants" tests/`
- Store atomic gold + vip + broader (cb credit/purchase flows): `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "TestStorePurchaseAtomicGold or vip or store or atomicity or TestCross or TestFreeEntry" tests/`
- Full broader smoke: `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "store or atomicity or mission or reaction or daily or vip or health or story or event_bus or TestCross or TestFreeEntry or TestAnalytics" tests/`
- All green (pre-exist flakes/xf doc non-reg only; 0 attributable to this item; verify dupe skip before credit paths via golds).
- Also bot smoke + ruff on touched.

---

## 5. Riesgos + Mitigación (0 impact 3 crit; critical dupe guarantee)
- Riesgo: distributed rate algo != single-inst (spam or over-throttle). Mit: implement parity path + fallback exact; re-run golds + targeted rate tests on both paths.
- Riesgo: async redis errors leak or crash handlers. Mit: try/except around redis calls; fall to in-mem or pass on error; copy existing robustness (answer fail logs only).
- Riesgo: tests break fallback or public API. Mit: keep in-mem tests first; ctor default=None; patch tests continue working; minimal optional redis tests.
- Riesgo: gamif double credit if dupe not skipped in redis path. Mit: idemp dupe path identical skip before handler; rate guards equivalent; golds that hit cb credit paths re-run; critical risk called out in every phase.
- Overall: LOW (leverages existing redis in bot + create_storage pattern; in-mem mature; public API preserved; tests cover fallback; 0 prod/0 beh change).

---

## 6. Self-Check (executor fills at F7; must PASSED)
- [ ] F1-F7 all phases executed in order with GSD pre every + safe points marked + wc tracked
- [ ] GSD log has entries for every step + wc tracked (planner + executor)
- [ ] Optional redis=None ctors (default) + calls with 0 args unchanged (public API)
- [ ] Redis client centralized in bot.py create_storage + passed in wiring; comments "Item 1/35" + order preserved
- [ ] rate_limiter.py: redis path (SET/ZSET) + pure exact current in-mem fallback; all logs/Lucien/ADMIN/cleanup/monotonic/TTL identical
- [ ] idempotency.py: redis path (SET NX EX) + pure exact current dict fallback; global cache compat; skip before handler guaranteed; logs exact
- [ ] Unit tests: in-mem paths 100% pass unchanged; optional redis paths added (minimal); internals work on fallback
- [ ] ruff clean on touched (safe fixes); bot smoke + import ok
- [ ] Golds re-runs (middleware+atomic, reaction/daily/invariants, store atomic + vip + broader) all green (0 attributable reg); critical dupe skip protects gamif credits
- [ ] Arch: PASS or PASS WITH NOTES 0 critical
- [ ] Test-guardian: "suite protege adecuadamente"
- [ ] 3 crit + atomicity/EventBus/get_service contracts protected (re-runs + greps; no dupe credit possible; 0 mutation)
- [ ] 0/0/0: 0 beh/0 atomicity/0 prod change; scope tight per PLAN + impact excerpts
- [ ] Lucien voice, logs formats, ADMIN_BYPASS, registration order, TTL semantics preserved
- [ ] Self-check PASSED full + pool phrase + handoff text
- [ ] Handoff: "Item 1/35 closed. First of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch + testg + documentador (final pool close + ROADMAP update)"

---

**Handoff to gsd-executor + arch-enforcer + test-guardian + documentador (pool close):**
Item 1/35 closed. First of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch + testg + documentador (final pool close + ROADMAP update).

Start with GSD pre-log to .planning/quick/gsd-35-full-redis-rate-idemp-middleware.log, read this PLAN + sources (impact excerpts verbatim + HARDENING_ROADMAP pool34 end + 34/33 PLAN precedents + middlewares + bot.py + tests), then F1 baseline. Copy gold patterns al pie de la letra (in-mem fallback exact, logging "rate_limiter | ...", "idempotency_middleware | ...", Lucien voice throttle answer verbatim, robustness on errors, bot create_storage redis pattern, mw reg order comment, GSD pre every, self-check, pool phrase). Use optional redis ctor (default None). No behavior change. 3 crit always protected (no dupe credits on gamif; guarantee skip before Besito credit). Import redis inside if needed for type (avoid hard top-level dep). Worktree or direct ok but respect no-edit outside GSD. Review loop ~effort=4 until 0 issues (copy 33/34 fix rounds if any nits). "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

---

**Post-write GSD (planner discipline):** Planner GSD pre + writes complete. Ready for executor. wc tracked.
