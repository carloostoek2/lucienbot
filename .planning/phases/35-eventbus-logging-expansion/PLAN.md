# PLAN: Expand EventBus + structured logging coverage (Item 3/35, third of new pool of 4)

**Type:** gsd-planner output (for gsd-executor + hardener seq)  
**Date:** 2026-06-26  
**Focus:** Tight hardening: expand EventBus coverage with 0-2 high-value purely observational listeners (e.g. streaks or promo if F1 analysis confirms safe obs-only, no mutation risk to 3 crit) + align structured logging "módulo | acción | user_id=... | resultado=..." (copy health_service + pool34 item4 hygiene al pie) in emitter (besito) + listeners + touched files. Update central explicit reg in bot.py + comments. Extend test_event_bus.py + logging assertions (caplog) in listener tests. Re-run golds protecting atomicity/EventBus contracts + 3 crit. 0 behavior/0 atomicity/0 prod change. Builds on Item1/5/6/10 (eventbus + locals + obs listeners), pool34 hygiene (logging align), Item11 (health check_event_bus_listeners). Source of truth: impact report for this item (expand coverage + logging hygiene; files primarily services/besito_service.py + 0-2 listener hosts + bot.py + tests/unit/test_event_bus.py + test listener sites + minimal docs; golds: event_bus + cross + reaction chains + daily + besito + health event_bus + listener tests). GSD pre every edit/gate/ruff/pytest/grep/smoke/self-check. Self-check PASSED + pool phrase + handoff. "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

**Input principal (source of truth):** 
- Impact report key excerpts (verbatim context for item3): "Objective: Expand EventBus + structured logging coverage. Add 0-2 high-value obs listeners only (e.g. streaks or promo if safe purely observational per precedents). Align logging format in touched emitter/listener files (besito credit paths + listeners). Central reg update in bot.py. Test extensions (new listener coverage + logging assertions via caplog in test_event_bus + reaction/game tests). Minimal docs (decisions + CLAUDE cross). Critical tests: event_bus unit, cross_service_atomicity (with patch schedule_emit + DESIRED), reaction_* (full_chain/mission_flow/limit), daily atomic, besito credit/emit, story/reward/broadcast/game/store listener paths + health check_event_bus_listeners, broader smoke. Scope tight: 0 new events, 0 mutation, listeners MUST NOT credit/debit, 0 impact on 3 crit (gamif/narrativa/channels-VIP), 0 atomicity/EventBus/get_service contracts change. Precedents: story_service bottom listener template, reward/broadcast/game/store observers + 'MUST NOT' + DESIRED CONTRACT + domain log, bot.py reg block, event_bus DESIRED (gather return_exceptions, best-effort, schedule_emit), health check_event_bus_listeners + logging, pool34 item4 hygiene (rate/idemp/health/besito align to 'módulo | ...'), atomicity gold (TestSession/file + N806 tol+doc + 777 + try/finally + patch + 'credit survives deliver False' + 'post-credit best effort (misiones + listeners)')."
- .planning/HARDENING_ROADMAP.md (pool34 close + phrase + "Expand EventBus listeners + structured logging coverage" in Proposed Next + metrics + 3 crit + contracts).
- Precedents al pie: .planning/phases/35-full-redis-rate-idemp-middleware/PLAN.md + 34-observability-health-docs/PLAN.md + 34-*-SUMMARYs + gsd-34-*.log (structure/header/scope In/Out 0/0/0/phases gated/DoD/GSD pre/wc/safe points/golds list/self-check/pool phrase/"copy al pie"), .planning/phases/23-reward-besito-eventbus-decoupling/PLAN.md + 24-remaining-besito-compositions/PLAN.md + 28/29 (listener template + central reg + 1-line ports + patch + DESIRED + atomic golds), services/event_bus.py (full DESIRED CONTRACT), bot.py on_startup (current 5 listeners + vip + log + comments), services/story_service.py:1040+ (on_besitos_awarded_from_gamification + Cross-domain block), reward_service.py:735+ , broadcast_service.py:611+ , game_service.py:1903+ , store_service.py:1458+ (exact observers + MUST NOT + DESIRED + log format), services/health_service.py (check_event_bus_listeners + structured logs "health_service | ... | user_id=0 | ..."), tests/unit/test_event_bus.py + test_broadcast_service_reaction_flow.py + test_game_service.py + test_reward_service.py (caplog asserts for "domain | besitos_awarded_received"), services/besito_service.py (credit + _schedule_besitos_awarded_event + current logs), services/gamification/CLAUDE.md + services/CLAUDE.md + services/missions/CLAUDE.md + services/broadcast/CLAUDE.md (cross EventBus sections), decisions.md (prior Item entries + BATCH), CLAUDE.md (hardener + 3 crit + EventBus contracts + logging rule + phrase).
- Current state (mandatory read/grep first): 5 besitos_awarded listeners registered (narrative/rewards/broadcast/game/store); vip_activated -> nurture; emit only post-commit in credit via schedule_emit (best effort); health check counts them; logging partially aligned (listeners + health + pool34 hygiene in rate/idemp/besito some paths); test coverage via direct bus + caplog in domain tests.

**GSD enforcement (mandatory):** Executor MUST append GSD pre-log (timestamp | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie>) to `.planning/quick/gsd-35-eventbus-logging-expansion.log` BEFORE every modification, gate, ruff, pytest, grep, smoke, self-check, or summary. Use style from 35-redis/34-obs/23-eventbus/29 gsd logs (detailed, wc -l after, "GSD pre-edit <file> (F<N>) - ...", "GSD pre-ruff F<N>", "GSD pre-pytest ...", "F<N> safe point", "GSD pre self-check"). No edits without pre-log. Planner did INIT + pre-mkdir + pre-write entries + multiple pre-log.

---

## 1. Alcance preciso (In / Out explícito; tight per impact + 0/0/0 + protects 3 crit + contracts)

### En esta entrega (scope tight; builds EventBus + logging hygiene precedents al pie):
- **Prep/baseline (F1):** reads/greps (current listeners/emit sites/logs format " | " usage, ruff baseline, gold runs exact flags); confirm no held direct in new listener hosts, health check_event_bus_listeners exercises counts.
- **Add safe listeners 0-2 high-value obs only (F2 if confirmed):** purely observational async def at module bottom of 0-2 safe hosts (e.g. streak_promotion_service.py for award receipt logging/stats hints or promotion_service.py if F1 safe; copy verbatim template from story_service:670-694 + reward/broadcast/game/store "Cross-domain event listeners" block + docstring). MUST NOT credit/debit/mutate besitos or gamif state. Best-effort, errors swallowed. Log "streak | besitos_awarded_received | user_id=... | amount=... | source=... | ref=..." (or "promotion | ..."). 0 mutation/0 re-entrancy risk. 0 impact on credit paths/atomicity golds.
- **Align structured logging (F3):** in touched emitter (besito_service.py: credit_besitos + debit_besitos + _schedule to consistent "besito_service | credit_besitos | user_id={user_id} | amount={amount} source=... result=credited" per rules + pool34 hygiene al pie from health/rate/idemp); listener logs if gap (already good); ensure health + any touched follow "módulo | acción | user_id=... | resultado=...". No behavior change.
- **Central reg update (F4):** bot.py on_startup: extend listeners block + imports if new + logger.info line (add "; + Item 3/35 logging expansion") + comment update ("Fase 3 of eventbus-poc + Item 5 + Item 6 + Item 10 + Item 3/35: ..."). Explicit central, no side-effects.
- **Test extensions (F5):** tests/unit/test_event_bus.py (extend coverage for new listeners + register/emit smoke); add/align caplog assertions for new domain logs in test_event_bus + existing listener tests (broadcast/game/reward); 1-line/guard ports if any direct access exposed (minimal). No new test files.
- **Gates (F6):** ruff on touched; re-runs exact golds + broader smoke (flags from precedents); greps (0 held in new, listeners + MUST NOT + logs present, bot reg count + "Item 3/35", logging format, "MUST NOT", patch usage).
- **Traceability:** decisions.md append (Item 3/35 entry mirroring style + BATCH/POOL + phrase), gsd log, this PLAN + (opt post) SUMMARY; documentador at pool close for ROADMAP.
- **Files (minimal, exact):** .planning/quick/gsd-35-eventbus-logging-expansion.log (appends), services/besito_service.py (F3 logging), 0-2 service bottoms if listeners added (e.g. services/streak_promotion_service.py or services/promotion_service.py), bot.py (F4), tests/unit/test_event_bus.py + spot test_*_service*.py for caplog (F5), decisions.md, services/gamification/CLAUDE.md or services/CLAUDE.md (append cross note if needed for traceability, tight), no models/migrations/handlers/other.

### Fuera explícitamente (no creep):
- NO change to event_bus.py contract/DESIRED/schedule_emit/gather.
- NO new events (only besitos_awarded + vip if already).
- NO mutation on 3 crit paths (listeners obs only; "MUST NOT credit/debit/mutate" enforced in code + comments + tests + golds).
- NO behavior/UX/return/atomicity change (credit still schedules post-commit; listeners best-effort only; "credit survives deliver False" + "post-credit best effort (misiones + listeners)" protected).
- NO other composers touched (no new locals/held changes beyond logging).
- NO broad logging rewrite (only touched emitter/listeners per F3; hygiene not full sweep).
- NO >0-2 listeners; only if F1 confirms purely safe obs high-value.
- NO test behavior change on existing paths; no new test cases beyond extensions for coverage.
- NO touch to health checks beyond using existing event_bus check in smoke; no /health change.
- 0 prod change (REDIS/FSM/ existing listeners untouched).

**Comportamiento observable:** Identical for credits, reactions, games, daily, missions, store, story, rewards. Event still emitted best-effort post-credit; if new listeners added they log receipt (observational proof); health reports same or +1-2 counts. Logs in touched paths use consistent format. Golds pass. UI/Lucien/flows unchanged.

---

## 2. Fases (strict order, 7 small gated; GSD pre every; copy precedents al pie)

**F1 prep/GSD/baseline** (GSD pre; read this PLAN full + impact excerpts verbatim + .planning/HARDENING_ROADMAP.md (pool34 close + phrase + "Expand EventBus + structured logging coverage" + metrics) + 35-redis PLAN + 34-observability-health-docs/PLAN.md + 34-*-SUMMARY + 23-eventbus + 24 PLAN full + recent gsd logs/SUMMARYs for style + event_bus.py full + bot.py (on_startup listeners block ~210-235 + imports + health) + services/story_service.py bottom listener + reward/broadcast/game/store listeners full + besito_service.py (credit/_schedule + current logs) + health_service.py (check_event_bus_listeners + overall) + tests/unit/test_event_bus.py full + test_broadcast.../test_game.../test_reward... (caplog listener tests) + services/* for streak/promo potential (grep besitos_awarded or cross award logic; confirm 0 mutation sites) + greps for listeners/emit/logs ("besitos_awarded" + " | " format usage + "MUST NOT" + schedule_emit) + current reg count; baseline ruff --check on touched; baseline targeted pytest exact: `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "event_bus or TestEventBus or besitos_awarded or cross_service_atomicity or reaction_full_chain or reaction_mission_flow or reaction_limit or daily or TestDaily or besito or health or TestHealth or TestCross or TestFreeEntry" tests/` (expect green or pre-exist only); greps for gold patterns (DESIRED, patch schedule_emit, "credit survives", "post-credit best effort", listener comment block, bot reg); confirm golds list + fixtures; "F1 safe point - DoD: reads + baseline + greps + ruff baseline + gold runs done". DoD marked.)

**F2 add safe listeners (0-2 high-value obs only)** (GSD pre each; analysis from F1 confirms purely obs safe (e.g. streak_promotion or promotion for award receipt logging/stats only); if 0 then skip to hygiene; add at module bottom exact copy of story/reward template: "# Cross-domain event listeners..." block + async def on_besitos_awarded_xxx_observer(payload: dict) -> None: with docstring "DESIRED CONTRACT (copy of narrative precedent + ...): ... MUST NOT credit, debit, or mutate besitos state here." + extract uid/amt/src/ref + logger.info(f"streak | besitos_awarded_received | user_id={uid} | amount={amt} | source={src} | ref={ref}"); comment "# No side effects that mutate besitos here (best effort...)"; 0 impact on any credit/atomicity; if added import in F4; ruff; targeted pytest on new host + event_bus; greps for "MUST NOT" + log line + "Item 3/35"; "F2 safe point". DoD marked. 0 beh.)

**F3 align structured logging in touched emitter/listener files** (GSD pre; edit besito_service.py: credit_besitos + debit + _schedule to use consistent project format e.g. after existing or replace plain logs with f"besito_service | credit_besitos | user_id={user_id} | amount={amount} source={source.value} result=credited" + similar for debit; align any plain logs in listener hosts touched by F2; ensure format matches health/rate/idemp/pool34 ("módulo | acción | user_id=... | resultado=..."); add arch comment "Item 3/35 logging hygiene + EventBus expansion"; no change to logic/returns/tx; ruff; targeted pytest besito + event; greps for new log strings; "F3 safe point". DoD marked.)

**F4 central reg update in bot.py + comments** (GSD pre; update on_startup cross-domain listeners block: if F2 added import the new observer(s); add register call(s) for new; extend the logger.info( "Event listeners registrados (besitos_awarded -> narrative, rewards, broadcast, game, store[ + new]; ... )" ); update preceding comment to "... + Item 3/35 eventbus logging expansion"; preserve order (besitos then vip); ruff; bot smoke; greps for reg + "Item 3/35" + updated log; "F4 safe point". DoD marked.)

**F5 test extensions (new listener coverage + logging assertions + golds)** (GSD pre; edit tests/unit/test_event_bus.py: extend for new listeners (register + emit smoke if added); ensure isolation fresh bus; add caplog checks for new domain logs if present; align/extend caplog in spot listener tests (test_broadcast... etc) for format if touched; 1-line/guard ports if any (minimal); import inside tests per conv if needed; ruff; pytest event_bus + listener tests + spot golds; greps for assertions + "besitos_awarded_received"; "F5 safe point". DoD marked.)

**F6 gates/ruff/golds re-runs** (GSD pre; run ruff --check/fix safe on touched (pre N806 tol in golds); re-run exact gold commands (see section 4) + broader smoke with flags; bot smoke `python -c "import bot; from services.event_bus import get_event_bus, EVENT_BESITOS_AWARDED; print('ok listeners reg')"; if new listeners manual reg+emit smoke; greps (0 held, listeners + MUST NOT + domain logs + "Item 3/35", bot reg updated count, logging format in F3, patch schedule in golds); "F6 safe point". DoD marked.)

**F7 self-check + handoff (ready for arch + testg + documentador pool close)** (GSD pre; full self-check PASSED (phases/DoD/gates/archivos/tests passed; reglas: GSD pre every, scope tight per PLAN + impact, 3 crit protected via re-runs/greps (obs only + MUST NOT), precedents (listener template + "MUST NOT" + DESIRED + logging format from health/pool34 + central reg + patch schedule_emit + atomic DESIRED + bot create_storage style if relevant) copied al pie, 0/0/0, ruff, golds); append pool phrase + "Item 3/35 closed. Third of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch + testg + documentador (final pool close + ROADMAP update)"; handoff explicit.)

---

## 3. Copia patrones **al pie de la letra**

### Listener template + contract (story 670-694 / reward 735+ / broadcast 611+ / game 1903+ / store 1458+ exact)
```
# =============================================================================
# Cross-domain event listeners (registered explicitly from bot.py on startup).
# The listener lives here (xxx domain ownership). It is a plain async callable
# receiving the standard payload dict. It MUST NOT call back into credit/debit besitos
# (to avoid any re-entrancy with ... paths; ... contracts and partial-failure behavior
# are authoritative in the credit + ... flow).
# This is observational only (best effort; errors swallowed by bus).
# =============================================================================


async def on_besitos_awarded_xxx_observer(payload: dict) -> None:
    """
    Xxx-domain listener for "besitos_awarded" events (emitted by BesitoService.credit_besitos
    post-commit, including from ... credits ...).

    DESIRED CONTRACT (copy of narrative precedent): log reception with full context (user_id/amount/source/ref);
    purely observational + wiring proof for this domain. MUST NOT credit, debit, or mutate besitos state here.
    Future extensions (e.g. ...) belong in this module and should use
    get_service(XxxService) or direct models if a fresh DB session is required.
    """
    uid = payload.get("user_id")
    amt = payload.get("amount")
    src = payload.get("source")
    ref = payload.get("reference_id")
    logger.info(
        f"xxx | besitos_awarded_received | user_id={uid} | amount={amt} | source={src} | ref={ref}"
    )
    # No side effects that mutate besitos here (best effort, non-authoritative; 0 impact on ... contracts).
```

### Logging format (health_service + pool34 item4 hygiene al pie)
- "health_service | check_... | user_id=0 | status=... latency_ms=..."
- "rate_limiter | ... | user_id=... | result=..."
- "idempotency_middleware | skip_duplicate | user_id=... | result=..."
- "besito_service | credit_besitos | user_id=... | amount=... source=... result=credited"
- Listeners: "domain | besitos_awarded_received | user_id=... | ..."

### Golds + DESIRED + patch (atomicity gold + Item1/5/6/10 + cross)
- Patch schedule_emit in reaction/atomic tests; assert emit fired from local/credit.
- "credit survives deliver False" + "post-credit best effort (misiones + listeners)"
- TestSession/file + N806 tol w/ doc + 777 + try/finally + gather return_exceptions
- Listener tests use fresh InternalEventBus(); caplog.at_level(INFO) + assert "domain | besitos_awarded_received" in rec.message

### Central reg + comments (bot.py + Item5/6/10)
- After scheduler; explicit registers; logger.info with list + "; + Item 3/35 ..."
- Comment: "# Cross-domain listeners (explicit, central...) ... + Item 3/35 eventbus logging expansion"

### GSD + self-check + pool phrase (35/34/33/29 precedents)
- Pre every: timestamp | PHASE N | GSD pre-... + refs DoD + patrones (listener template, "MUST NOT", logging format, DESIRED, patch, pool phrase)
- wc -l after key; "F<N> safe point"; full self-check at end with checklist + phrase verbatim + "Item 3/35 closed. Third of new pool of 4."
- Arch: PASS or PASS WITH NOTES 0 critical. Test-guardian: "suite protege adecuadamente".

---

## 4. Golds a re-ejecutar (exactos; protect 3 crit + contracts + listener wiring + logging; 0 attributable reg target)
- EventBus + cross + atomic: `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "event_bus or TestEventBus or besitos_awarded or cross_service_atomicity" tests/`
- Reaction chains + daily + invariants (gamif critical): `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "reaction_full_chain or reaction_mission_flow or reaction_limit or daily or invariants" tests/`
- Besito emit + story/reward/broadcast/game/store listener paths + health: `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "besito or TestBesito or story or reward or broadcast or game or TestGame or health or TestHealth or TestCross or TestFreeEntry" tests/`
- Broader smoke (include listener coverage): `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "event_bus or reaction or daily or vip or store or atomicity or mission or story or health or TestCross or TestFreeEntry or TestAnalytics" tests/`
- All green (pre-exist flakes/xf doc non-reg only; 0 attributable to this item; verify listeners log on emit via caplog + health counts; patch schedule_emit in atomicity happy verifies emit from credits).
- Also bot smoke + ruff on touched + manual reg+emit if new listeners.

---

## 5. Riesgos + Mitigación (0 impact 3 crit; obs only)
- Riesgo: new listener accidentally mutates (re-entrancy). Mit: copy template verbatim + "MUST NOT" + best-effort + F1 analysis only safe obs + greps/tests assert no credit calls.
- Riesgo: logging change affects parsing/observability. Mit: exact format copy + hygiene only on touched; no new keys that break health.
- Riesgo: reg order or duplicate reg. Mit: explicit central block update; bot smoke + health check.
- Riesgo: test caplog brittle on format. Mit: exact substring match as in current listener tests.
- Overall: LOW (leverages mature EventBus + 5 listeners precedent; obs-only; logging hygiene precedent in pool34; golds protect).

---

## 6. Self-Check (executor fills at F7; must PASSED)
- [ ] F1-F7 all phases executed in order with GSD pre every + safe points marked + wc tracked
- [ ] GSD log has entries for every step + wc tracked (planner + executor)
- [ ] 0-2 listeners added only if F1 confirmed safe obs (MUST NOT verbatim + DESIRED + domain log); or 0 added
- [ ] Structured logging aligned in besito (credit/debit/_schedule) + touched to "módulo | acción | user_id=... | resultado=..." (copy health/pool34)
- [ ] bot.py reg updated + comments + "Item 3/35"; if new: imports + registers present
- [ ] test_event_bus + caplog asserts cover new/expanded (if added) + existing listener logs
- [ ] ruff clean on touched (safe fixes); bot smoke + import ok + manual listener smoke if added
- [ ] Golds re-runs (event_bus/cross, reaction/daily/invariants, besito/health/listener paths, broader) all green (0 attributable reg); patch schedule_emit + DESIRED exercised; health event_bus count matches
- [ ] Arch: PASS or PASS WITH NOTES 0 critical
- [ ] Test-guardian: "suite protege adecuadamente"
- [ ] 3 crit + atomicity/EventBus/get_service contracts protected (re-runs + greps; obs only + MUST NOT; 0 mutation)
- [ ] 0/0/0: 0 beh/0 atomicity/0 prod change; scope tight per PLAN + impact excerpts
- [ ] Listener template, logging format, central reg, "MUST NOT", patch + DESIRED + atomic gold verbatim copied al pie
- [ ] Self-check PASSED full + pool phrase + handoff text
- [ ] Handoff: "Item 3/35 closed. Third of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch + testg + documentador (final pool close + ROADMAP update)"

---

**Handoff to gsd-executor + arch-enforcer + test-guardian + documentador (pool close):**
Item 3/35 closed. Third of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch + testg + documentador (final pool close + ROADMAP update).

Start with GSD pre-log to .planning/quick/gsd-35-eventbus-logging-expansion.log, read this PLAN + sources (impact excerpts verbatim + HARDENING_ROADMAP pool34 end + 35-redis/34-obs/23/24 PLAN precedents + event_bus + bot.py + listeners + besito + health + test_event_bus + gsd logs), then F1 baseline. Copy gold patterns **al pie de la letra** (listener template + "MUST NOT credit, debit, or mutate besitos state here" + "DESIRED CONTRACT" + "domain | besitos_awarded_received | ..." log exactly; logging "módulo | acción | user_id=... | resultado=..." from health/pool34; patch schedule_emit + atomic gold DESIRED "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + TestSession + N806 tol w/doc + 777 + gather + try/finally; central reg block + comment style; GSD pre every + wc; self-check + phrase verbatim). Add 0-2 listeners only if F1 proves purely safe obs high-value (streaks/promo). No behavior/atomicity change. 3 crit always protected (obs only; greps + golds). Worktree or direct ok but respect no-edit outside GSD. Review loop ~effort=4 until 0 issues (copy 33/34 fix rounds if any nits). "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

---

**Post-write GSD (planner discipline):** Planner GSD pre + writes complete. Ready for executor. wc tracked.
