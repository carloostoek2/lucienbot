# PLAN: Observability + health spike + docs hygiene (structured logging everywhere per rules; simple /health (DB/bot/channels/bus/scheduler + critical sanity); update drifted CLAUDEs/handlers/CLAUDE examples to current get_service + 1-service + puros + integration style; ruff/N806 where safe) (Item 4/34, fourth of new pool of 4)

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-06-26  
**Focus:** Tight, min-hardening, 0/0/0 hygiene + spike follow-up after pool 33 (tests-only reality). Leverages Item 11/29 (observability-health) precedent al pie de la letra: HealthService read-only/best-effort, Analytics pattern (__init__ db=None, _owns_session, _get_db, close, direct counts, no mutation), <50 LOC, verb+context+result, mandatory structured logging "health_service | <action> | user_id=0 | status=... latency=...", exactly 1 get_service(HealthService) + is_admin in handlers, Lucien voice, 0 impact on 3 crit or atomicity/EventBus/get_service contracts. Sources read first (mandatory): .planning/HARDENING_ROADMAP.md (sec5 gaps + Proposed Next #3 + initial logging/observability/no health + doc drift + pool33 + item11 precedent), health_service.py (current complete), bot.py (on_startup + _BOT_START_TIME + listeners), handlers/analytics_handlers.py (has /health + admin_health cb + get_service 1 call), CLAUDEs (root + handlers/CLAUDE.md drifted examples), services (logging consistency sparse), middlewares (rate/idemp logs not yet strict format). Golds/tests for re-runs: health unit + cross + broader, story/gamif/vip/channel golds (protect 3 crit). GSD pre every edit/gate/ruff/pytest/grep/smoke/self-check. Self-check PASSED + pool phrase + handoff. "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

**Input principal (source of truth):** 
- .planning/HARDENING_ROADMAP.md (full read; sec5 "Proposed Next #3: Observability + health spike + docs hygiene (structured logging everywhere per rules; simple /health (DB/bot/channels/bus/scheduler); update drifted CLAUDEs/handlers/CLAUDE examples to current get_service + 1-service patterns; ruff/N806 where safe)"; references initial fragility "inconsistent structured logging... no health", pool33 close, item11/29 precedent).
- Precedents al pie: Item 11/29 (29-observability-health/PLAN.md + SUMMARY + gsd-*.log + health_service.py + analytics_handlers /health + scripts/health_check.py + health_server.py + bot.py wiring + Lucien system_health + "🛡️ Pulso del reino"; HealthService follows Analytics al pie; get_service 1 call + is_admin; logging format; read-only/best-effort; 0 impact 3 crit; arch PASS WITH NOTES 0 crit; testg "suite protege"; self-check PASSED + pool phrase; documentador used).
- Current state (read first): health_service.py (all 7 checks + get_overall + structured logs + <50 + arch comment "Item 11"); bot.py (on_startup has health endpoint task if HEALTH_ENABLED + _BOT_START_TIME + 5 besitos listeners + VIP expired + scheduler; on_shutdown stops health); handlers/analytics_handlers.py (/health cmd + cb "admin_health" + "🛡️ Pulso del reino" + get_service(HealthService) exactly 1 + is_admin + logging "health | cmd | ..."); scripts/health_check.py (get_service + --json/--verbose + user_id=0 logs + exit codes); keyboards/inline_keyboards.py (admin_health btn); utils/lucien_voice.py (system_health + health_access_denied); tests/unit/test_health_service.py (lifecycle + best-effort checks); services/CLAUDE.md (Health row + Observability section + hardener precedent); root CLAUDE.md (HealthService documented + hardener workflow + pool phrase + 1svc/puros pattern from tirones 25-29).
- Drifts identified (grep + read): handlers/CLAUDE.md "Ejemplo Correcto" still shows `with get_session() as session: service = BesitoService(session)` (obsolete; current is `with get_service(BesitoService) as svc:` + 1 call/handler); root/services CLAUDEs have correct current descriptions but examples in handlers/ need sync to 1svc + puros + integration style from Item7-10 + pool33; logging "módulo | acción | user_id | resultado" per root CLAUDE rule is sparse (only health_service, backpack, story, one scheduler use the format; most services use plain logger.info or none).
- Golds (protect 3 crit + contracts): health unit/cross/broader, story/gamif/vip/channel units, cross_service_atomicity (gold with patch schedule_emit + DESIRED + TestSession + strict + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + N806 tol + 777 + gather + try/finally), reaction_* flows, daily atomic, invariants, vip flows; broader smoke. Exact flags from precedents: `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "..."`.
- 0/0/0: 0 behavior/0 atomicity/0 prod change; 0 mutation on gamif credits/reactions/daily/missions, narrative progress/archetypes/FSM/quiz, channel pending/approve/expire/bans/subs + VIP grant/revoke; leverages prior (Item11 HealthService + get_service pattern + pool33 integration style); min hardening (docs + logging hygiene + verify health core; no new features).

**GSD enforcement (mandatory):** Executor MUST append GSD pre-log (timestamp | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados al pie>) to `.planning/quick/gsd-34-observability-health-docs.log` BEFORE every modification, gate, ruff, pytest, grep, smoke, self-check, or summary. Use style from 29/28/27/33 gsd logs (detailed, wc -l after, "GSD pre-edit <file> (F<N>) - ...", "GSD pre-ruff F<N>", "GSD pre-pytest ...", "F<N> safe point", "GSD pre self-check"). No edits without pre-log. "Planner did INIT + pre-mkdir + pre-write entries."

---

## 1. Alcance preciso (In / Out explícito; tight per "min hardening" + 0/0/0 + protects 3 crit + contracts)

### En esta entrega (scope tight; leverages Item 11/29 + pool33 patterns al pie):
- **Structured logging hygiene (where missing per rules):** Add/align "módulo | acción | user_id | resultado" format (copy health_service.py style exactly) for important actions in observability paths + middlewares (rate limit hits, idemp dupes) + representative critical services actions (e.g. key credit/debit or claim sites if missing; use existing patterns, no new locals/composers). No behavior change. Targeted (not "rewrite everything" — hygiene pass on sources read: health, middlewares/rate/idemp, 1-2 core services for consistency). Ruff after.
- **/health verification + spike hygiene (simple core):** Verify/ensure simple /health covers DB/bot/channels/bus/scheduler + critical sanity (already present in health_service.py from Item11; confirm via run + script). No new checks unless gap in core; best-effort/read-only preserved. Terminal `python -m scripts.health_check [--json] [--verbose]` + bot /health + cb exercise. 0 change to wiring (bot.py/analytics_handlers already correct).
- **CLAUDEs/docs hygiene to current patterns:** Update handlers/CLAUDE.md (main drift): replace "Ejemplo Correcto" get_session block with current `with get_service(XXXService) as svc: exactly 1 call` + ctx manager + 1-service/handler rule + puros for long funcs + integration style note + ref to hardener Items 7-11 + pool33. Sync any other drifted examples (e.g. in sync_claude.py comments or fases md if in scope, but tight: focus handlers/CLAUDE + cross note in decisions/services/CLAUDE if needed for traceability). Add logging rule enforcement note. UI/docs 1:1.
- **ruff/N806 where safe:** Run ruff on touched; fix safe hygiene (E501 in comments, style); N806 tolerated in golds/tests with doc (per precedent); no logic change.
- **Tests + gates:** Re-run health unit + cross + story/gamif/vip/channel golds + broader smoke (exact flags); 0 attributable reg. Arch + test-guardian + self-check.
- **Traceability:** decisions.md append (Item 4/34 entry mirroring style), gsd log, this PLAN + (opt post) SUMMARY; documentador at pool close for ROADMAP (not manual here).
- **Files (minimal, exact):** .planning/quick/gsd-34-observability-health-docs.log (appends only), handlers/CLAUDE.md (docs fix), middlewares/rate_limiter.py + idempotency.py (logging format for key events if missing), health_service.py (logging alignment if gaps), possibly 1 core service for sample (e.g. besito_service.py for credit path log hygiene), decisions.md (entry), services/CLAUDE.md (if cross note), no new models/handlers/migrations.

### Fuera explícitamente (no creep):
- NO new health checks or endpoint changes (verify only; wiring exists).
- NO behavior/UX change to any flow (0 impact gamif/narr/channel-VIP atomicity/contracts).
- NO touching 3 crit code paths for mutation (logs only; reads in health untouched).
- NO broad logging rewrite across all services (targeted hygiene on sources + rule).
- NO new tests beyond coverage hygiene if needed (re-runs + existing health tests protect).
- NO edits to root CLAUDE/services/CLAUDE beyond minimal cross if required for traceability (documentador handles ROADMAP).
- NO changes to get_service/EventBus/atomicity golds (re-run only).
- 0 other files beyond listed.

**Comportamiento observable:** Identical. /health (cmd/cb/script) continues to work (Lucien voice, get_service 1 call, read-only). Logging format appears in more places for observability + rate/idemp (no user impact). Docs examples now match reality (get_service + 1svc + puros). Ruff clean (safe fixes). Golds green.

---

## 2. Fases (strict order, 5-6 small gated; GSD pre every; copy precedents al pie)

**F1 prep/GSD/baseline** (GSD pre; mkdir -p .planning/phases/34-observability-health-docs if needed (already); read this PLAN + .planning/HARDENING_ROADMAP.md sec5 + Proposed #3 + item11 precedent files (health_service.py, bot.py, analytics_handlers.py, scripts/health_check.py, handlers/CLAUDE.md, services/CLAUDE.md) + 29-PLAN + 33-PLAN/SUMMARY for patterns; ruff --check on touched (handlers/CLAUDE middlewares health services decisions); baseline pytest exact: `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "health or TestHealthService or cross_service_atomicity or reaction or daily or vip or story or TestCross or atomicity" tests/` (expect green or pre-exist only); greps for logging format (expect sparse), get_session drift (handlers/CLAUDE + sync_claude), /health presence (cmd/cb/script/service), get_service usage in analytics_handlers; confirm golds list + fixtures; read HealthService pattern (read-only, Analytics al pie, <50, logging "health_service | ... | user_id=0 | ...", get_service 1 call + is_admin, Lucien, 0 impact); "F1 safe point - DoD: reads + baseline + greps + ruff baseline done". DoD marked.)

**F2 structured logging hygiene (where missing)** (GSD pre each edit; add/align strict format "módulo | acción | user_id | resultado" (copy health_service.py al pie) for: health_service (verify all checks), middlewares/rate_limiter.py (limit hit, bypass, cleanup), middlewares/idempotency.py (dupe detected, skip), + 1-2 key actions in a core service (e.g. besito_service credit/debit if plain logs present — add alongside, no change to tx/atomic); no new deps/composers; ruff after; greps post "service | action | user_id=" + count; "F2 safe point". DoD marked. 0 beh/0 atomicity.)

**F3 /health verification + spike hygiene (simple core + critical sanity)** (GSD pre; run terminal `python -m scripts.health_check --json` + `--verbose`; bot smoke import + on_startup sim; manual exercise /health cmd if bot running (or unit equiv); verify core checks present (DB/bot/channels/bus/scheduler + critical sanity in health_service.get_overall_status); confirm best-effort/read-only/no mutation (grep in health_service); if any gap in simple core fill minimally (read-only only); ruff; greps for check_* + "DB/bot/channels/bus/scheduler"; "F3 safe point". DoD marked. Leverages Item11/29 al pie; 0 change to 3 crit.)

**F4 CLAUDEs/docs hygiene to current patterns** (GSD pre; edit handlers/CLAUDE.md: replace "Ejemplo Correcto" get_session block with current:
```python
async def handle_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    with get_service(BesitoService) as svc:  # exactly 1 service
        balance = svc.get_balance(user_id)
    await callback.message.edit_text(f"Tu saldo: {balance}")
```
+ update rules section to reference 1 service via get_service + puros for long admin <=50 + integration style (real svc + class patch + UI 1:1) + ref hardener Items 7-11 + pool33; add logging rule note; update any other drifted example in scope (e.g. comment in sync_claude.py if tight); decisions.md append Item 4/34 entry (Motivo/Riesgos/Decisión/Resultado + refs + pool phrase + handoff); optional 1-line cross in services/CLAUDE if needed for traceability; ruff on md/py touched; greps "with get_service" + "1 service" + "puros" + "get_session" (0 in active code, fixed in docs); "F4 safe point". DoD marked. UI/docs 1:1.)

**F5 gates (arch + testg + re-runs + ruff/N806)** (GSD pre every; arch-enforcer (focused on 1svc/get_service in health path, logging format, docs hygiene, 0 crit violations on 3 systems, read-only best-effort); test-guardian (re-runs exact golds: health unit + cross atomicity gold full + reaction_* + daily + vip + story + broader smoke with flags; veredict "suite protege adecuadamente"; coverage for logging/docs hygiene); ruff on all touched (fix safe N806/E501 where not gold-tol; N806 tol + doc in golds per precedent); bot smoke + terminal health_check --json (exit 0 on healthy); greps (logging format present, get_service 1 call in health handlers, 0 get_session in code, 0 writes in crit paths); "F5 safe point". DoD marked.)

**F6 self-check + handoff (ready for arch + testg + documentador final pool close)** (GSD pre; full self-check PASSED (phases/DoD/gates/archivos/tests passed; reglas: GSD pre every, scope tight per PLAN, 3 crit protected via re-runs/greps, precedents HealthService + get_service + 1svc + puros + integration al pie, UI 1:1 Lucien, 0/0/0, logging format, ruff/N806 safe, /health core verified, docs hygiene done); append pool phrase + "Item 4/34 closed. Fourth of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch + testg + documentador (final pool close + ROADMAP update)"; handoff explicit.)

---

## 3. Copia patrones **al pie de la letra**

### HealthService / Observability (Item 11/29 precedent — copy exactly for any hygiene)
- Read-only/best-effort: all checks try/except + short budgets; never blocks main loop or tx.
- Pattern: __init__(db=None), self._owns_session = db is None, _get_db, close; direct model counts for speed; no mutation.
- Logging: "health_service | <action> | user_id=0 | status=... latency=..." (or admin_id for bot).
- Handler: is_admin + with get_service(HealthService) as svc: exactly 1 call; Lucien voice; "🛡️ Pulso del reino".
- 0 impact on 3 crit (gamif credits/reactions/daily/missions, narrative progress/archetypes/FSM, channel pending/approve/expire/bans/subs + VIP grant/revoke) or atomicity/EventBus/get_service contracts.
- Terminal: python -m scripts.health_check [--json] [--verbose]; exit codes; user_id=0 logs.
- See health_service.py arch comment + 29-PLAN + services/CLAUDE "Hardener pattern for new observability".

### GSD pre (every step, from 29/28/27/33)
- Append before edit/gate: timestamp | PHASE N | GSD pre-... - desc + refs DoD + patrones copiados.
- wc -l after key steps.
- "GSD pre-edit <file> (F<N>)", "GSD pre-ruff F<N>", "GSD pre-pytest ...", "F<N> safe point", "GSD pre self-check".

### Self-check structure (F6; copy 29/28/27)
- Phases/DoD passed (list F1-F6 + marks).
- Gates (arch veredict, testg "suite protege", ruff, greps, smokes, terminal).
- Archivos/tests passed (exact list + counts).
- Reglas verificadas (GSD pre every, scope tight, 3 crit + contracts protected, precedents al pie, 0/0/0, logging, get_service 1 call, <50 if touched, UI 1:1, read-only best-effort).
- Desviaciones (pre-exist only, doc non-reg).
- "Item 4/34 closed. Fourth of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch + testg + documentador (final pool close + ROADMAP update)".

### Pool phrase (verbatim in SUMMARY/gsd/self-check/handoff/ROADMAP)
"Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

### UI 1:1 Lucien + 0 impact
- Health renders (if touched): same elegant 3rd person, "Diana", "custodios", "visitantes", emojis ✅⚠️❌.
- No change to any existing admin/user UI or flows.
- 0 behavior/0 atomicity/0 prod change.

---

## 4. Golds a re-ejecutar (exactos; protect 3 crit + contracts; 0 attributable reg target)
- Health: `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "health or TestHealthService" tests/`
- Cross + atomicity gold: `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "cross_service_atomicity or TestCrossServiceAtomicity" tests/`
- Reaction chains + daily + invariants: `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "reaction_full_chain or reaction_mission_flow or reaction_limit or daily or invariants" tests/`
- Story/gamif/vip/channel (3 crit): `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "story or gamif or vip or channel or TestStory or TestVip or TestChannel or TestGame or TestDaily" tests/`
- Broader smoke: `pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "store or atomicity or mission or reaction or daily or vip or health or story or event_bus or TestCross or TestFreeEntry or TestAnalytics" tests/`
- All green (pre-exist flakes/xf doc non-reg only; 0 attributable to this item).
- Also: terminal `python -m scripts.health_check --json` (valid json, exit reflects status); bot smoke `python -c "import bot; from services import get_service, HealthService; print('ok')"; python -m scripts.health_check --verbose`.

---

## 5. Riesgos + Mitigación (0 impact 3 crit; leverages prior)
- Riesgo: logging additions could be noisy or touch atomic paths. Mit: targeted (health + middlewares + 1-2 samples), logs only (no tx change), copy health format, re-run atomic golds + 3 crit golds.
- Riesgo: docs changes miss a drift. Mit: greps pre/post for get_session (active code 0), focus handlers/CLAUDE as main drift source.
- Riesgo: N806/ruff introduces noise. Mit: safe fixes only; tolerate gold N806 with doc (precedent).
- Overall: LOW (leverages Item11 HealthService complete + pool33 integration style + get_service pattern proven; 0 writes to crit paths; read-only health untouched).

---

## 6. Self-Check (executor fills at F6; must PASSED)
- [ ] F1-F6 all phases executed in order with GSD pre every + safe points marked
- [ ] GSD log has entries for every step + wc tracked
- [ ] Structured logging added/aligned where missing (greps show format in health + middlewares + samples)
- [ ] /health core verified (DB/bot/channels/bus/scheduler + critical sanity); terminal + bot paths exercise OK
- [ ] handlers/CLAUDE.md updated (get_service + 1svc + puros + integration; 0 get_session in code examples)
- [ ] decisions.md + (opt) services/CLAUDE cross updated for traceability
- [ ] ruff clean on touched (safe fixes); N806 tol + doc where gold
- [ ] Golds re-runs: health unit + cross atomicity gold + reaction/daily + story/gamif/vip/channel + broader all green (0 attributable reg)
- [ ] Arch: PASS or PASS WITH NOTES 0 critical
- [ ] Test-guardian: "suite protege adecuadamente"
- [ ] 3 crit + atomicity/EventBus/get_service contracts protected (re-runs + greps; 0 mutation)
- [ ] 0/0/0: 0 beh/0 atomicity/0 prod change; scope tight per PLAN
- [ ] UI 1:1 Lucien preserved (health renders unchanged)
- [ ] Self-check PASSED full + pool phrase + handoff text
- [ ] Handoff: "Item 4/34 closed. Fourth of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch + testg + documentador (final pool close + ROADMAP update)"

---

**Handoff to gsd-executor + arch-enforcer + test-guardian + documentador (pool close):**
Item 4/34 closed. Fourth of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch + testg + documentador (final pool close + ROADMAP update).

Start with GSD pre-log to .planning/quick/gsd-34-observability-health-docs.log, read this PLAN + sources (HARDENING_ROADMAP + health_service + handlers/CLAUDE + precedents), then F1 baseline. Copy HealthService pattern + GSD pre + self-check + pool phrase al pie de la letra. 0 impact. 3 crit protected.
