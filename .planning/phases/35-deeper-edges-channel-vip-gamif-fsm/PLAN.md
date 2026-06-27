# PLAN: Deeper edges tests (channel/VIP: pay→VIP+remove-free/expire-no-error/ban-both/multi/partial/offline/real TG grant/pending after expire; gamif property/caps: explicit max limits + concurrent races; FSM real Redis sim: restart/restore + narrative/archetype once-only + invalid branches with real progress) (Item 4/35, fourth/last of new pool of 4)

**Type:** gsd-planner output (for gsd-executor + hardener seq: arch-enforcer + test-guardian + documentador at pool close)  
**Date:** 2026-06-26  
**Focus:** Ultra-tight, tests-only (real DB + TestSession/file, class patch real_svc, external-only patch, 1:1 precedents) for deeper edges per impact-analyzer key excerpts (pool 35 item 4) + ROADMAP pool 35 section (post 3 items: redis + promo wizard + eventbus logging; "deeper edges channel-vip-gamif-fsm" cluster from initial + pool34 item3 gaps + 33 mapeo). 0 prod/0 beh/0 atomicity. Protects 3 crit (gamif caps/races, narrative FSM/archetype/quiz/progress, canales-VIP edges) + atomicity/EventBus/get_service contracts (re-runs only). "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

**Input principal (MANDATORY full read first):**  
- The full impact-analyzer report for this item (pool 35 item 4 deeper edges) from the just-completed subagent (key excerpts in task context below as source of truth; consumers tree, gaps vs current coverage detailed there).  
- `/home/ubuntu/repos/lucienbot/.claude/agents/gsd-planner.md`  
- `/home/ubuntu/repos/lucienbot/CLAUDE.md` (hardener section full, 3 crit, pool phrase verbatim, GSD pre, 0/0/0, precedents copy, rules, "copy gold patterns al pie de la letra").  
- `/home/ubuntu/repos/lucienbot/.planning/HARDENING_ROADMAP.md` (pool 34 close + pool 35 section "3/4 items completed" + "Deeper edges..." + phrase + prior 3 items closed + documentador use).  
- Precedent PLANs for exact style: `.planning/phases/34-test-gaps-hygiene/PLAN.md` (full, especially structure/header/phases/scope/DoD/golds/GSD pre/self-check/handoff/"copy al pie"/pool phrase) + `.planning/phases/35-eventbus-logging-expansion/PLAN.md` + `.planning/phases/35-full-redis-rate-idemp-middleware/PLAN.md` + `.planning/phases/35-promotion-admin-wizard/PLAN.md` (recent pool35 consistency).  
- Key sources from impact (MANDATORY): `services/channel_service.py`, `services/vip_service.py`, `services/channel_grant.py`, `services/scheduler_service.py`, `services/game_service.py` + `services/streak_promotion_service.py`, `services/story_service.py`, `services/daily_gift_service.py`, relevant handlers (vip_handlers, channel_handlers, free_channel_handlers, gamification_*, story_*), `bot.py` (FSM storage + EventBus reg + startup), tests for vip/channel/story/gamif/edges (e.g. `tests/integration/test_vip_*.py`, `tests/integration/test_free_entry_flow.py`, `tests/unit/test_vip_service.py`, `tests/unit/test_channel_service.py`, `tests/unit/test_story_service.py`, `tests/unit/test_besito_service.py`, `tests/unit/test_daily_gift_service.py`, `tests/test_streak_fsm.py`, cross/reaction/daily/atomic golds).

**Impact key excerpts (source of truth):**  
- Objective: Deeper edges (channel/VIP: pay→VIP+remove-free, expire-no-error-if-gone, ban-both, multi-tariff/partial, offline, free pending after VIP expire, real TG grant; gamif property/caps: explicit max limits, concurrent races; FSM real Redis sim: restart/restore with Redis or sim, narrative/archetype once-only, invalid branches with real progress).  
- Safe approach: tests-only (real DB + TestSession/file, class patch("handlers.xxx.XXXService") return real_svc, external-only patch, 1:1 precedents, UI 1:1 Lucien, 777, N806+doc, try/finally, strict asserts).  
- Golds to protect/re-run (exact flags -q --tb=line -p no:cov --override-ini="addopts="): vip flows, free_entry, cross atomicity, reaction_*, daily atomic, story FSM/inverse/archetype, invariants, broader channel/gamif/vip smoke.  
- Risks: 3 crit (gamif caps/races, narrative FSM, canales-VIP edges) + atomicity/EventBus/get_service; pre-exist flakes non-reg.  
- Consumers tree, gaps vs current coverage (detailed in report).  
- Copy al pie: pool34 item3 (caps/FSM/VIP edges), pool33 int/E2E (real svc + class patch + TestSession + 1-line/guard exact + DESIRED + UI1:1), story golds, atomic gold, daily guards.

**Precedents obligatorios (copiar AL PIE DE LA LETRA):**  
- Pool34 item3 (34-test-gaps-hygiene/PLAN.md + SUMMARY): explicit caps (TestGamifDailyCapsExplicit once+block real DailyGift+credit +1-line/guard; TestGamifTriviaCapsExplicit DEFAULTS pins), full handler E2E "mensaje correcto" Lucien insuff (store int + gamif int game protection), FSM restart sim (TestFSMRestartSim fresh MemoryStorage per bot.py + real svc + DB StreakSession survive), VIP/channel edges (TestVIPChannelEdges expire-no-error-if-gone, multi-tariff real+DB). Tests added/ext in unit/int (daily, trivia, store/gamif int, streak_fsm, vip_flows). GSD ~66l 42+ entries. self-check PASSED + "Item 3/34 closed. Third...". Arch: **PASS WITH NOTES 0 critical**. Golds re-runs (gamif 51p+4xf, cross/reac19p, story43p, vip140p+7xf, inv14p, broader1201p+9xf pre) 0 attr. UI1:1, precedents al pie, scope tight.  
- Pool33 int/E2E (33-test-reality-user-flows-store): pytestmark=integration, real_svc=XXXService(db_session), `with patch("handlers.xxx.XXXService") as mock: mock.return_value = real_svc`, handler→real svc→DB→UI 1:1 exact Lucien strings/keywords/emojis preserved; TestSession/file (N806 tolerated + docstring), fresh TG 7770xxxx, explicit models (User/BesitoBalance/...), try/finally reopen/re-query, external patch ONLY, "credit survives deliver False" / post best-effort, strict asserts, DESIRED CONTRACT docstring; 1-line/guard exact comment + noqa.  
- Story golds (tests/unit/test_story_service.py): TestStoryArchetypeImmutability (once-only + DESIRED+777+explicit), TestStoryInvalidTransitions (no partial), TestStoryServiceAtomicity (debit commit=False), TestStoryFSMEventBus, TestStoryAchievementAtomicity, TestStoryNarrativeGoldFase6; invalid graceful.  
- Atomic gold (tests/integration/test_cross_service_atomicity.py): full + patch schedule_emit + DESIRED + strict + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + N806 tol+doc+777+try/finally+gather.  
- Daily atomic: hasattr guards + fallback (lazy besito precedent).  
- GSD pre-log: `=== $(date -Iseconds) | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie de la letra>` appended to `.planning/quick/gsd-35-deeper-edges-channel-vip-gamif-fsm.log` BEFORE every edit/gate/ruff/pytest/grep/smoke/self-check; wc -l tracked.  
- self-check PASSED full structure at final phase (mirror 34/35/33 exact: phases/DoD/gates/archivos/tests passed; reglas verificadas (GSD pre every + wc, scope tight per PLAN/impact/ROADMAP, 3 crit protected via re-runs/greps, precedents copiados al pie, UI 1:1, integration style, 1-line/guard if any, 0/0/0, pool phrase verbatim); desviaciones (pre-exist only non-reg); "Item 4/35 closed. Fourth/last of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch-enforcer re-scan (enfocado en deeper edges tests: channel/VIP/gamif caps/FSM) + test-guardian (correr golds listados) + documentador (update ROADMAP + extract learnings + .claude/agent-memory/documentador/ + MEMORY.md pointer) + pool close if last".  
- Arch: PASS or PASS WITH NOTES (0 critical). Test-guardian: "suite protege adecuadamente" + re-runs golds exactos. 0 attributable regressions.

**GSD enforcement (non-negotiable):**  
Executor MUST prefix **every** modification, gate, verification, ruff, pytest, grep, smoke, self-check, or summary step with GSD log append (timestamp | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie de la letra from pool34 item3 + pool33 int/E2E + story/atomic golds + 1-line/guard + daily guards + impact/ROADMAP/impact excerpts>) to `.planning/quick/gsd-35-deeper-edges-channel-vip-gamif-fsm.log`. Use python -c for long/quoted safety. wc -l after. Planner pre-entries done (INIT + pre-mkdir + pre-write + multiple). No edits (even to PLAN or log beyond appends) without pre-log. "Planner did INIT + pre-mkdir + pre-write + 4+ pre-log entries."

---

## 1. Alcance preciso (In / Out explícito; ultra tight per impact excerpts + ROADMAP + 0/0/0 + protects 3 crit + contracts)

### En esta entrega (Item 4/35 fourth/last of new pool of 4; tests-only; 0 prod/0 behavior/0 atomicity; 3 crit + contracts protected via re-runs only; source = impact excerpts + ROADMAP pool35 + pool34 item3 + pool33):
- **Gamif property/caps explicit + concurrent races (property tests style or explicit limits + gather races):**  
  Extend tests (prefer `tests/unit/test_daily_gift_service.py`, `tests/unit/test_besito_service.py`, `tests/unit/test_game_service.py` or tight integration) with explicit max limits asserts (e.g. once-per-day claim blocked, dice/trivia DAILY_*_LIMIT_*/vip caps enforced/pinned from config, no exceed on repeated plays); concurrent races using gather (real DB TestSession/file where visible) for credit/debit/claim/play to prove <=1 success or caps respected (no dup points). Use real services + explicit 777 tg + strict asserts. 1-line/guard if balance/lazy. Re-runs protect gamif golds. UI 1:1 if handler paths.

- **Channel/VIP deeper edges (integration style + real TG grant where possible):**  
  Extend `tests/integration/test_vip_flows.py` + `tests/integration/test_free_entry_flow.py` + `tests/unit/test_vip_service.py` + `tests/unit/test_channel_service.py` (or new tight `tests/integration/test_vip_channel_deeper_edges.py`): cases for pay→VIP + remove-free access, expire-no-error-if-gone (no crash if user not member), ban-both-channels propagation, multi-tariff/partial subs, offline (startup recovery via check_expired_subscriptions_on_startup + scheduler grant), free pending after VIP expire, real TG grant (patch bot.ban/unban/chat_join but assert calls + DB state post; use TestSession/file if atomic visible in grant/revoke). External patch ONLY for TG calls (channel_grant/scheduler paths). Assert DB + no error paths. Re-runs vip flows + free_entry + broader channel/gamif/vip smoke.

- **FSM real Redis sim + narrative/archetype once-only + invalid branches with real progress:**  
  Extend `tests/test_streak_fsm.py` + `tests/unit/test_story_service.py` (or tight integration): simulate restart/restore with RedisStorage (if REDIS_URL) or fresh MemoryStorage (per bot.py create_storage fallback + note "real Redis sim"); verify narrative/archetype once-only (quiz/assign immutable on re-complete), progress state survives restore, invalid branches/choices graceful (no partial corrupt, returns prior or error reason with real progress DB), FSM context roundtrip. Real services + 777 tg + explicit seeds + story golds DESIRED. External only if any. Re-runs story unit + FSM/inverse/archetype.

- **Files exact (minimal extensions or tight new; 0 other creep):**  
  - `.planning/quick/gsd-35-deeper-edges-channel-vip-gamif-fsm.log` (GSD pre + wc + self-check + pool phrase every phase).  
  - `tests/unit/test_daily_gift_service.py` or `tests/unit/test_besito_service.py` or `tests/unit/test_game_service.py` (caps + races explicit).  
  - `tests/integration/test_vip_flows.py`, `tests/integration/test_free_entry_flow.py`, `tests/unit/test_vip_service.py`, `tests/unit/test_channel_service.py` (deeper VIP/channel edges).  
  - `tests/test_streak_fsm.py`, `tests/unit/test_story_service.py` (FSM real sim + narrative/archetype/ invalid with real progress).  
  - `.planning/phases/35-deeper-edges-channel-vip-gamif-fsm/` (this PLAN.md + opt *-SUMMARY.md post + arch/testg reports via documentador).  
  - decisions.md (append Item 4/35 entry mirroring prior style + BATCH/pool + handoff; via executor or documentador).  

**Fuera explícitamente (no scope creep):**  
- **NO** prod code (0 writes to handlers/*.py, services/*.py, bot.py, models, channel_grant etc; git/grep confirm post).  
- **NO** change to golds of 3 crit (cross_service_atomicity, reaction_*, daily atomic, story FSM/inverse/archetype/achievement, vip_*, invariants, free_entry, store atomic; only re-run with exact flags).  
- **NO** new models/alembic/migrations.  
- **NO** broad impl changes (only test existing edges + hygiene; 0 beh).  
- **NO** other flows (store purchase, promo, mission user, admin wizards, etc beyond listed edges).  
- **NO** edit CLAUDEs/ROADMAP/decisions except append via documentador or minimal at close.  
- **NO** mutation of contracts (1 svc via get_service in prod; EventBus "MUST NOT mutate"; atomic golds verbatim untouched).  
- **NO** new deps (no fakeredis; MemoryStorage or conditional real Redis if env REDIS_URL present per bot.py).  
- 0 creep to listed test files only + log + PLAN.

**Comportamiento observable (tests only):** Existing prod flows identical. New/ported tests exercise deeper real paths (explicit caps/races, pay+remove-free, expire-no-error, ban-both, multi/partial/offline/pending, real TG, FSM restart sim + archetype once-only + invalid graceful with real progress). Golds protected 0 attributable reg. 0 user-visible change. 3 crit + atomicity/EventBus/get_service 0 impact.

---

## 2. Fases (strict order; 5-7 small gated; safe points; DoD per phase; GSD pre every)

**Pool/Item context:** Item 4/35 (fourth/last of new pool of 4 after Item1/35 redis, Item2/35 promo wizard, Item3/35 eventbus logging closed clean per ROADMAP). Pool phrase verbatim in all artifacts + self-checks + handoffs. Focus: deeper edges tests-only. After gates + self-check: handoff to arch-enforcer (focus: deeper edges tests + real svc/class patch/TestSession/1-line/guard/UI1:1/0 impact 3 crit) + test-guardian (re-run golds list) + documentador (ROADMAP + learnings + agent-memory + MEMORY) + pool close.

### F1 prep/GSD/baseline (GSD pre)
- GSD pre-log.  
- Read MANDATORY: this PLAN full + impact key excerpts (verbatim) + ROADMAP (pool35 3/4 + phrase + deeper edges + pool34 item3 + pool33) + 34-test-gaps-hygiene/PLAN.md full + recent 35-*.PLAN.md + CLAUDE.md hardener + gsd-planner.md + key sources listed (channel/vip/channel_grant/scheduler/game/streak/story/daily + handlers + bot.py FSM + relevant tests full or targeted) + story golds + atomic gold + daily guards + vip flows + free_entry.  
- Baseline ruff --check on target test files.  
- Baseline targeted pytest exact flags (`-q --tb=line -p no:cov --override-ini="addopts="`): vip flows (complete_cycle + *_flows + subscription_lifecycle etc), free_entry, cross atomicity spot, reaction_full_chain + limit + mission, daily atomic, story unit (archetype/imm/invalid/atomic/FSM/achievement), invariants I8, broader `-k "vip or channel or free or story or fsm or gamif or cap or limit or race or edge or offline or multi or expire or ban or restart or archetype or invalid"`.  
- Greps: current edge coverage (pay remove free, expire-no-error, ban both, multi/partial, offline/startup, pending after expire, caps in daily/game/besito, concurrent gather, FSM Memory/Redis in streak/story, archetype once-only, invalid branch graceful); storage in bot.py; real TG grant sites (channel_grant + scheduler + vip). Confirm fixtures (balances telegram_id=777, tariffs, subs, nodes, channels, configs with limits). Confirm golds list + re-run cmds.  
- "F1 safe point". DoD marked. 0 edits to prod.

### F2 gamif caps/property explicit tests + concurrent races (GSD pre every edit)
- GSD pre.  
- Add/extend tests in daily/besito/game unit (or tight int): real service (DailyGiftService/BesitoService/GameService) + db; assert explicit limits returned/enforced/pinned (once-per-day claim block, dice/trivia caps from config, no exceed on repeated); concurrent races via asyncio.gather real credit/debit/claim/play (real DB TestSession/file where atomic visible) proving <=1 success or cap respected (no dup). Use real services + explicit 777 tg + strict. 1-line/guard if balance/lazy per daily precedent. ruff. Targeted pytest on touched + spot gamif/daily. Grep caps/races exercised + no prod touch. "F2 safe point". DoD marked.

### F3 channel/VIP deeper edges tests (multi/expire/ban/pay-remove-free/offline/real TG) (GSD pre)
- GSD pre.  
- Extend vip flows + free_entry + unit vip/channel (or new tight edges integration): real VIPService/ChannelService; cases exercising pay→VIP+remove-free, expire-no-error-if-gone (no crash if not member), ban-both, multi-tariff/partial, offline (startup check_expired + scheduler), free pending after VIP expire, real TG grant (patch bot calls external only + assert + DB post state). TestSession/file if atomic visible in grant/revoke paths (N806+doc+777+try/finally+external patch ONLY for TG). Assert DB state + no error. Re-run vip golds + free_entry. "F3 safe point". DoD marked.

### F4 FSM real Redis sim + narrative/archetype once-only + invalid branches with real progress (GSD pre)
- GSD pre.  
- FSM restart sim + narrative edges: extend streak_fsm + story unit (or tight int): use MemoryStorage (per bot.py fallback) or conditional RedisStorage if REDIS_URL; simulate restart (new storage instance or clear scope); verify story quiz/archetype once-only (immut on re-complete), progress survives, invalid branches/choices graceful no partial corrupt (real DB progress), FSM roundtrip. Real services + 777 tg + explicit seeds. Copy story FSM gold + DESIRED + atomic patterns. External only. ruff; pytest + re-run story unit + FSM. "F4 safe point". DoD marked.

### F5 gates + re-runs + rules verif (GSD pre every)
- GSD pre every.  
- ruff on touched (new/extended tests; pre N806 tol in TestSession files per gold).  
- Re-execute exact golds list (see section 3; spot after F2/F3/F4).  
- Bot smoke (import handlers/services; create_storage Memory/Redis path).  
- Grep 0 prod changes (handlers/services untouched); 0 new models; 1-line/guard comments exact if present; integration style (class patch real_svc); UI 1:1 strings where touched; caps tests assert explicit; FSM uses Memory/Redis per bot; edges use real TG patches external.  
- Rules verif: GSD pre every + wc, scope tight per listed files + log + PLAN + impact, 3 crit protected via re-runs (no writes in crit paths), precedents al pie (pool34 item3 + pool33 int/E2E + story/atomic golds + 1-line/guard + daily guards + UI 1:1), 0/0/0, get_service 1 call unchanged in prod, N806 tol documented in TestSession. "F5 safe point". DoD marked.

### F6 self-check PASSED + handoff (GSD pre)
- GSD pre.  
- Append full self-check structure to log + opt SUMMARY.md (mirror 34/35/33 exact): phases/DoD/gates/archivos/tests passed; reglas verificadas (GSD pre every + wc, scope tight per PLAN/impact/ROADMAP, 3 crit protected via re-runs/greps, precedents copiados al pie (pool34 item3 caps/FSM/VIP + pool33 real svc/class patch/TestSession/1-line/guard/DESIRED/UI1:1 + story golds + atomic + daily), integration real svc + class patch + 1-line/guard + TestSession where atomic + UI 1:1 Lucien, deeper edges coverage added (caps/races + channel/VIP multi/expire/ban/pay-remove/offline/pending/real TG + FSM restart sim + archetype once-only + invalid graceful with real progress), 0 prod touch, 0 attr reg); desviaciones (pre-exist only non-reg: e.g. N806 tol in golds, daily concurrent flake, some VIP xfail); tests críticos para futuro (list); "Item 4/35 closed. Fourth/last of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch-enforcer re-scan (enfocado en deeper edges tests channel/VIP/gamif/FSM: explicit caps/races + multi/expire/ban/pay-remove-free/offline/pending/real TG grant + FSM Redis sim + archetype once-only + invalid branches real progress; 0 impact 3 crit) + test-guardian (correr golds listados exact) + documentador (update ROADMAP + extract learnings + .claude/agent-memory/documentador/ + MEMORY.md pointer) + pool close if final".  
- Self-check PASSED. Pool phrase verbatim. Launch arch + testg + documentador per hardener. Explicit next: pool close.

---

## 3. Golds to re-run (exact; after each relevant phase + final; 0 attributable regressions target)

Use exact flags from precedents: `-q --tb=line -p no:cov --override-ini="addopts="`

- VIP + channel: `pytest tests/integration/test_vip_complete_cycle.py tests/integration/test_vip_flow.py tests/integration/test_vip_flows.py tests/integration/test_vip_ritual_flow.py tests/integration/test_vip_subscription_lifecycle.py tests/unit/test_vip_service.py tests/unit/test_channel_service.py -q --tb=line -p no:cov --override-ini="addopts="`
- Free entry: `pytest tests/integration/test_free_entry_flow.py -q --tb=line -p no:cov --override-ini="addopts="`
- Cross + atomic: `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="` (full; patch schedule_emit)
- Reaction golds: `pytest tests/integration/test_reaction_full_chain.py tests/integration/test_reaction_mission_flow.py tests/integration/test_reaction_limit.py -q --tb=line -p no:cov --override-ini="addopts="`
- Daily atomic: `pytest tests/integration/test_streak_protection_flow.py -k "daily" -q --tb=line -p no:cov --override-ini="addopts="` (or specific daily atomic)
- Story golds (unit + FSM/inverse/archetype): `pytest tests/unit/test_story_service.py -q --tb=line -p no:cov --override-ini="addopts="` (archetype/imm/invalid/atomic/FSM/achievement + inverse if present)
- Invariants + broader: `pytest tests/integration/test_invariants.py -q --tb=line -p no:cov --override-ini="addopts="`
- Broader smoke (channel/gamif/vip): `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "vip or channel or free or story or fsm or gamif or cap or limit or race or edge or offline or multi or expire or ban or restart or archetype or invalid or daily or reaction or mission or cross or atomic" --maxfail=5`
- Spot after ports: vip flows, free_entry, story unit, cross atomic, daily, reaction chains.
- Bot smoke: `python -c "import bot; print('bot import OK')"; python -c "from aiogram.fsm.storage.memory import MemoryStorage; from aiogram.fsm.storage.redis import RedisStorage; print('storage sim OK')"`

Re-runs mandatory at F5 + final; spot after F2/F3/F4. Pre-exist (daily concurrent flake, some VIP xfail, N806 in golds) doc non-reg only. 0 attributable.

---

## 4. Riesgos + mitigación (0 impact; orthogonal)

- Risk: Accidental prod touch → Mit: GSD pre every + grep 0 writes in F5 + git diff/collect confirm; scope lists exact test files only.  
- Risk: Gold mutation (e.g. edit atomic class or story immut) → Mit: "100% untouched" + re-run verbatim + 1-line/guard only with exact comment; TestSession new files ok.  
- Risk: N806 in new TestSession/files → Mit: tol + docstring per gold precedent; ruff allows in those.  
- Risk: FSM sim not "real Redis" → Mit: use MemoryStorage as bot.py fallback (explicit in test + note "real Redis sim via env if REDIS_URL, fallback Memory as in bot.py"); if REDIS_URL present in env use it; document "sim". No new deps.  
- Risk: Real TG grant hard to assert (offline) → Mit: patch external only + DB state + no-crash asserts; copy vip_lifecycle / free_entry patterns.  
- Risk: Pre-exist flakes (daily concurrent, some VIP) → Mit: doc non-reg; do not xfail new; re-runs only.  
- Risk: Scope creep to impl edges → Mit: "tests-only"; 0 beh; In/Out strict per impact.  
- Overall: orthogonal tests (no writes to crit paths); re-runs protect atomicity/EventBus/get_service/3 crit (gamif credits/reactions/daily/missions untouched; narrative progress/archetypes/FSM/quiz; channel pending/approve/expire/bans/subs + VIP grant/revoke). "0 attributable regressions".

---

## 5. Success criteria (medibles)

- GSD pre + wc: >=1 per phase + total log lines tracked; every edit/gate has entry.  
- Tests added/extended: gamif caps/races explicit (limits pinned + concurrent gather <=1 or cap respected); channel/VIP deeper (pay+remove-free, expire-no-error, ban-both, multi/partial, offline, pending after expire, real TG grant >=5-7 cases); FSM sim + narrative (restart/restore, archetype once-only, invalid branches graceful with real progress >=4-6 cases).  
- Golds re-runs: all listed green (pre-exist only non-attrib); 0 attributable regressions.  
- Arch: PASS or PASS WITH NOTES (0 critical).  
- Test-guardian: "suite protege adecuadamente".  
- Self-check: PASSED full + pool phrase + "Item 4/35 closed. Fourth/last..." + handoff.  
- 0/0/0: 0 prod/0 beh/0 atomicity (git/grep confirm); UI 1:1; integration style + real svc + class patch + 1-line/guard (if any) + TestSession (if any) + UI 1:1 + external only.  
- 3 crit + contracts: protected (re-runs + 0 writes in gamif credit/reaction/daily/mission, narrative FSM/archetype/progress, channel-VIP pending/approve/expire/ban/subs + VIP grant).  
- Ruff clean on touched (N806 tol only in TestSession per precedent).  
- Review: 0 open issues post (if loop).  
- Traceability: PLAN + gsd log + self-check + arch/testg reports + documentador update + ROADMAP append + decisions append + pool phrase verbatim.

---

**Instructions to executor (copy verbatim from impact + precedents):**  
"Copy gold patterns al pie de la letra (TestSession/file + N806+doc+777+try/finally+external patch ONLY+class patch real_svc + 1-line/guard exact comment if needed + UI 1:1 + DESIRED + credit survives + post-credit best effort + story/gamif precedents + daily guards). GSD pre every. 3 crit always. Use real DB where atomic visible."

**Handoff (after F6 self-check PASSED):**  
"Item 4/35 closed. Fourth/last of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch-enforcer re-scan (enfocado en deeper edges tests: channel/VIP pay→VIP+remove-free/expire-no-error/ban-both/multi/partial/offline/pending/real TG + gamif caps/races explicit + FSM real Redis sim + narrative/archetype once-only + invalid branches real progress; 0/0/0; 3 crit + contracts protected) + test-guardian (correr golds listados) + documentador (update ROADMAP + learnings + .claude/agent-memory/documentador/ + MEMORY.md pointer) + pool close."

**Self-check template for executor (fill at F6; append to log + SUMMARY if created):**

```
=== SELF-CHECK PASSED (Item 4/35) ===
Phases: F1 prep (read + baseline + greps + F1 safe) ... F6 (self-check + handoff) — all DoD marked, safe points passed.
Gates: ruff (touched), pytest (new + golds re-runs), grep (0 prod, integration style, 1-line comments, UI 1:1), bot smoke, LOC if puros.
Archivos: .planning/quick/gsd-35-deeper-edges-channel-vip-gamif-fsm.log (wc=XXX), listed test files (new/extended), PLAN.md, (opt SUMMARY), decisions.md (append).
Tests passed: <list counts per file + golds green>.
Reglas verificadas:
- GSD pre every + wc tracked
- Scope tight (tests-only per In/Out + listed files only + impact excerpts)
- 3 crit protected (re-runs + 0 writes in crit paths: gamif caps/races, narrative FSM/archetype/progress, channel-VIP edges)
- Precedents copiados al pie (pool34 item3 caps/FSM/VIP edges + pool33 int/E2E real svc/class patch/TestSession/1-line/guard/DESIRED/UI1:1 + story golds + atomic gold + daily guards)
- Integration style (class patch real_svc, real DB where atomic, UI 1:1 Lucien)
- 0/0/0 (0 prod/0 beh/0 atomicity; git/grep)
- get_service 1 call unchanged in prod
- N806 tol only in TestSession files + doc
- Pool phrase verbatim
- 0 attr reg
Desviaciones: (pre-exist only: N806 in golds, daily concurrent flake, some VIP xfail — non-reg)
Tests críticos para futuro: deeper caps/races explicit, channel/VIP multi/expire/ban/pay-remove-free/offline/pending/real TG, FSM restart sim + archetype once-only + invalid branches real progress (list files)
"Item 4/35 closed. Fourth/last of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch-enforcer re-scan (enfocado en deeper edges tests channel/VIP/gamif/FSM...) + test-guardian + documentador + pool close."
Self-check: PASSED
```

**Fin del PLAN para Item 4/35. Ejecutable, tight, listo para gsd-executor. PLAN ready. Handing to executor.**

Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.
