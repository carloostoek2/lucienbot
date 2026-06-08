# Arch-Enforcer Audit Report: Item 6 (Unify/reduce remaining direct BesitoService compositions in broadcast_service, game_service, daily_gift_service)

**Date:** 2026-06-07 (PT)  
**Auditor:** arch-enforcer (Grok Build subagent)  
**Task:** Audit if changes from Item 6 (4th/final in tirón) violated any architectural or code rules of the project.  
**Changes under audit (per user-provided summary + PLAN cross-ref in decisions.md):**  
- Removed held `self.besito_service = BesitoService(...)` from `__init__` in broadcast, game, daily_gift (daily never had direct __init__ held; used lazy property).  
- Inside credit methods only (register_reaction/check_and_register_reaction in broadcast; play_* variants + streak in game; claim_gift in daily): local on-demand `BesitoService(db=self.db)` or `db=self._get_db()` *only* at credit sites, preserving shared-db atomicity.  
- Added 1-2 observational listeners (`on_besitos_awarded_broadcast_reaction_observer`, `on_besitos_awarded_game_award_observer`) in the services (at module bottom), with "MUST NOT credit/debit" + best-effort contract (copy of narrative precedent + Reward Item5).  
- Central registration in bot.py on_startup (explicit imports + 2 register calls + extended log/comment referencing "+ Item 6").  
- 1-line fixes + hasattr guards ONLY in targeted tests (broadcast reaction flow owns test; daily claim + concurrent; cross_service_atomicity daily paths) with comments "# 1-line fix post held removal (F<N>/Item 6)" (daily precedent retained property for guards/compat).  
- Docs updates ONLY: services/broadcast/CLAUDE.md (new cross section), services/gamification/CLAUDE.md (append), services/missions/CLAUDE.md (Item6 bullets), decisions.md (full Item6 entry + batch note), bot.py comments.  
- Claims: 0 behavior change, 0 atomicity impact (credits inside methods, schedule_emit best-effort post, partials "credit survives" intact), 0 other composers touched, 0 new files (except opt SUMMARY), tight scope to 3 services + listed tests/docs. GSD pre-every + self-check PASSED referenced in decisions/gsd logs.  
**Reference rules audited (sourced from CLAUDE.md, rules.md, architecture.md, services/CLAUDE.md + sub/CLAUDEs, handlers/CLAUDE.md, models/CLAUDE.md, decisions.md, AGENTS.md, event_bus.py, precedents in story/reward):**  
- Layers: handlers → services → models (handlers: routing + exactly 1 service call, NO business logic, NO DB access, ≤50 LOC, logging module|action|user_id|result).  
- Services: domain owners, centralize logic, PROHIBIDO duplication, use models for DB (no direct), NO logic in handlers.  
- Cross-domain: EventBus for notifications (best-effort, not commands), as in Item1/5 precedents; listeners "MUST NOT credit/debit" + removable + central reg in bot.py (no import side-effects).  
- Functions: verbo + contexto + resultado (no generics). Max 50 LOC.  
- Anti-patterns: logic in handlers, DB outside models, duplication, etc.  
- GSD: changes via PLAN + GSD logs (no direct edits outside flow).  
- 3 critical systems: gamification (besitos source), missions/rewards (atomic delivery via deliver_reward), narrative (listeners). Atomicity contracts: credits independent, post-credit best-effort (missions + listeners), partials explicit ("credit survives deliver False"), gold tests (cross_service_atomicity, reaction_mission_flow, invariants, daily atomic, reaction chains).  
- get_service / lifecycle + locals db= for explicit atomicity (per Reward Item5 precedent).  
- Logging, <50 LOC, naming, Lucien voice (user-facing).  
- Scope tight: only planned, 0 creep, 0 prod behavior change, 0 atomicity impact.  

## Methodology
- **Exploration (parallel reads + greps):**  
  - Modified code: services/broadcast_service.py (full + close/listener), services/game_service.py (full via offsets + listener at end), services/daily_gift_service.py (full + property/claim).  
  - Wiring: bot.py (imports + on_startup reg block).  
  - EventBus precedent/contract: services/event_bus.py (full).  
  - Docs/PLAN/decisions: decisions.md (Item6 entry full), services/broadcast/CLAUDE.md, services/gamification/CLAUDE.md, services/missions/CLAUDE.md (Item5+6), services/CLAUDE.md, services/narrative/CLAUDE.md, root CLAUDE.md (layers + rules + GSD), architecture.md, rules.md, handlers/CLAUDE.md, models/CLAUDE.md, AGENTS.md (cross-ref).  
  - Tests (gold + patched): tests/unit/test_broadcast_service_reaction_flow.py (owns test), tests/unit/test_daily_gift_service.py (claim + concurrent), tests/integration/test_cross_service_atomicity.py (daily atomic paths + guards + patch on class for local), + cross-refs to test_reaction_mission_flow.py, test_reaction_full_chain.py, test_invariants.py, test_reaction_limit.py, unit event_bus/story/reward/besito/gamification tests (via grep patterns).  
  - Patterns (grep, project-wide + scoped): "BesitoService|besito_service" (in services/ + handlers/), "MUST NOT|on_besitos_awarded|Item 6|held direct|post held removal", "1-line fix", defs of credit/claim/play/close, direct in handlers/.  
  - Atomicity/gold verification: cross-service tests use direct `BesitoService(db=...)` for post-asserts + guards/patches that intercept locals (not helds); "credit survives" + schedule_emit patch + TestSession + N806 + try/finally + strict deltas/tx sources exercised.  
  - No code mods performed (audit only; write used solely for report persistence per explicit user request).  

## Findings (Classified)
### Critical (Architecture-breaking, 0 found)
None. All changes follow Item5/Reward + narrative/EventBus precedents exactly for local-on-demand inside atomic credit sites + observational listeners with "MUST NOT" contract. No layer violations introduced by Item6 (no handler touches; services still own credits via locals; models via BesitoService internals). No DB direct outside models. No duplication of credit logic (locals are the approved thin wrapper per PLAN). Central reg explicit. GSD adherence claimed in decisions + docs (self-check PASSED, PLAN refs, gsd logs referenced). Atomicity/partials/best-effort contracts preserved in code + golds.

### Medium (Fragility / Maintenance / Pre-existing amplified, 3 findings)
1. **services/daily_gift_service.py:44-49 (property besito_service + _besito_service_instance in __init__)** + usage in claim_gift:165 (local) + tests:  
   - Desc: Daily retains lazy @property `besito_service` (creates on access via _get_db()) + _besito...=None in __init__, even though claim_gift now uses explicit local `BesitoService(db=...)` for credit/get_balance. Tests (and some guards) still access via property with `hasattr` fallbacks to direct `BesitoService(db)`. Close/__del__ untouched (never closed the sub).  
   - Why "medium" (not critical): Per explicit PLAN in decisions.md:180-181 ("Keep the @property (for test compat + hasattr guards precedent)"), and daily precedent from prior. Does not break atomicity (credit path uses local inside method, shared db). Property is now "compat shim" only — not the held composer for commands. But creates minor inconsistency (internal credit doesn't use self.besito_service, while tests may; risk of future confusion or accidental use of property for credits). Matches "fragility" category.  
   - Recommendation (for test-guardian/quick if desired): Document in gamification/CLAUDE or daily code that "property is retained *only* for test guards/compat post-Item6; all new credit paths must use local on-demand". Consider deprecation comment. (No behavior impact now.)

2. **tests/ (3 files) + hasattr guards + class-patch for locals (e.g. test_broadcast... :401, test_daily...:137-140 + 292-295, test_cross...:726-729 + 762-764 patch on "services.besito_service.BesitoService.credit_besitos"):**  
   - Desc: 1-line fixes + guards exactly as PLAN-specified (e.g. `assert not hasattr(svc, "besito_service") or svc.besito_service is None # 1-line fix...`; daily `if hasattr... else BesitoService(db)...`; cross patch now on class to catch *local* instantiation inside claim, not instance attr). Comments reference F5/Item6.  
   - Why "medium": These are test-only, planned, minimal, and use "daily precedent" (hasattr was already in some daily tests pre-Item6). They make tests robust to the removal. However, they are a bit of technical debt in test surface (guards instead of clean direct asserts on new locals). Broadcast owns test now correctly reflects "no held". Cross atomicity daily paths still exercise !success rollback + happy "credit survives" via the class patch. No production code fragility.  
   - Recommendation: Test-guardian to keep exercising the exact guards + class-patch paths in future re-runs of daily atomic + broadcast reaction flow + cross gold. If quick allowed, could centralize a test helper for "get_besito_for_test(db)" but per tight scope of Item6, leave as-is.

3. **Pre-existing long functions in game_service.py (play_trivia ~150+ LOC body, play_trivia_vip, play_trivia_simple, etc.) and broadcast check_and_register_reaction (~100 LOC):**  
   - Desc: The credit sites (where locals were added) live inside functions that already exceed the "máximo 50 líneas" rule (rules.md + root CLAUDE.md). Item6 added only 1-line local + multi-line explanatory comment (inside __init__ or method); no new long functions or body bloat.  
   - Why "medium": Strict non-negotiable per rules ("Funciones máximo 50 líneas"). But *not introduced by Item6 changes* (pre-existing; scope tight per PLAN: "LOC of touched funcs preserved or <50 (no change)"). Adding the local inside credit block is minimal + follows Reward Item5 pattern. No violation *caused by* the Item6 refactor.  
   - Recommendation: Note for future refactoring (outside this Item); test-guardian should not treat as regression from Item6. When touching game play_* again, consider extraction of win/credit + record logic (verbo+contexto naming).

### Observations (Good / Minor / Adherence, many — selected key)
- **EventBus pattern fidelity (broadcast_service.py:439-467, game_service.py:1773-1803, bot.py:69-77 + 202-210):** Exact copy of story_service precedent (narrative/CLAUDE + story 670-694 block) + Reward Item5: full "Cross-domain event listeners" header + "MUST NOT call back into credit/debit besitos (to avoid any re-entrancy... contracts ... are authoritative...)" + "This is observational only (best effort; errors swallowed by bus)." + DESIRED CONTRACT docstring + domain log format ("broadcast | besitos_awarded_received | user_id=... | amount=... | source=... | ref=...") + final "No side effects that mutate besitos here (best effort, non-authoritative; 0 impact on ... atomicity gold)". Listeners are plain async callables at module bottom (domain ownership). Central explicit reg in bot.py (no import side-effects, after scheduler, extended comment "Fase 3 of eventbus-poc + Item 5 + Item 6"). Matches services/CLAUDE.md + gamification/CLAUDE + event_bus DESIRED CONTRACT (gather return_exceptions, schedule_emit for sync credit paths, best-effort). Removable.  
  - Why OK: Directly upholds "EventBus for cross-domain notifications (not commands)", "listeners MUST NOT credit/debit", "central reg", "best-effort post-credit". 0 re-entrancy risk with reaction/game credit paths (authoritative credits remain inside check_and_register/play_* + mission best-effort). High-value for 3 critical systems (reaction awards for streaks/promo in broadcast; game awards for streaks in game).  
  - Good: Wiring proof + future extension hook without mutation.

- **Atomicity / partials / gold contracts preserved (all 3 services + tests + decisions):**  
  - Locals use shared `db=self.db` (or _get_db) so credit's internal commit/FOR UPDATE + BesitoTransaction + schedule_emit best-effort + caller's outer commit (reaction row / game record / claim) + post-credit mission best-effort remain identical to held era. "credit survives deliver False" + "post-credit misiones (best effort) + event listeners (best effort)" protected. Golds (cross_service_atomicity happy/partials, reaction_mission_flow, invariants, daily atomic, reaction chains) re-runnable with patches for schedule_emit + direct Besito(db) asserts + guards; no change to return values, tx sources (REACTION/GAME/TRIVIA/DAILY_GIFT), balances, history. Broadcast close() getattr guard + game close() harmless (now None).  
  - Why OK + strong: Matches Reward Item5 precedent exactly ("local on-demand ... preserves 100% atomicity", "credit's internal commit as before"). PLAN/Result in decisions: "0 atomicity impact (golds re-runs ... 'credit survives' + post-credit best effort hold)". 0 prod behavior (identical dicts/msgs/Lucien strings).  
  - Good: In daily claim, even on credit !success, rollback uses the local's result; tests patch class to intercept local.

- **Tight scope + 0 creep + docs/traceability (multiple files):**  
  - Only broadcast/game/daily touched for composers (store/story still hold their besito for their domains per PLAN "0 other composers"; reward already reduced in Item5). No get_service for locals (explicit `BesitoService(db=...)` inside credit sites, per "get_service / lifecycle" + "locals db= for atomicity" in rules). No new tests beyond 1-lines. No handler changes (grep confirmed 0 BesitoService creations added in handlers/ by this Item; pre-existing direct uses in gamif_admin/vip_user/store_user/gamif_user are legacy, outside scope). Docs updated with cross-refs to PLAN, gsd log, golds, precedents, batch "4 items completed in tirón (final of max 4)". Comments in code/__init__/close explain "Item 6 / remaining composers unification".  
  - Why OK: "Scope tight: solo lo planeado, 0 creep" per prompt + decisions. GSD workflow followed (pre-every referenced).  
  - Good: decisions.md has full Motivo/Riesgos/Decisión/Resultado + Result checklist that matches observed state (grep "self\.besito_service = BesitoService" ==0 in the 3; locals present; listeners + "MUST NOT"; reg; 1-lines; docs).

- **Logging / naming / voice (where applicable):**  
  - Listeners use project convention: "módulo | acción | user_id | ..." (even though observational). Credit sites unchanged (logs inside BesitoService.credit_besitos per besito domain). No user-facing strings changed (Lucien voice untouched). Function names pre-existing (verbo+contexto+resultado).  
  - OK per rules (logging for "cada acción importante"; the emit is logged by bus per-listener).

- **Handlers direct Besito (pre-existing, not from Item6):**  
  - Grep found imports + instantiations in handlers/gamification_*_handlers.py, vip_user_handlers.py, store_user_handlers.py (and doc example in handlers/CLAUDE.md using BesitoService(session)).  
  - Why OK for *this audit*: Item6 summary + decisions explicitly "0 handler changes", "0 logic in handlers". The changes did not introduce or worsen any handler-layer violation. (Separate concern: root CLAUDE + rules require "llamar exactamente 1 service" + "SIN lógica / SIN acceso a DB"; handlers/CLAUDE example may be outdated or for admin direct; gamification handlers likely should route via dedicated gamif service if not already.)  
  - Rec: Out of scope for Item6; flag for separate quick or arch review if desired. No impact on Item6 verdict.

- **Other minor positives:** Close guards in broadcast/game remain defensive. Daily _get_db() pattern consistent for its lazy style. No side-effects in listener bodies. Imports for listeners only in bot.py. 0 new files created by changes (per summary). Ruff/format/LOC hygiene noted in PLAN self-check.

## Impact on 3 Critical Systems
- **Gamification (besitos source — broadcast/game/daily as high-volume composers):** Protected + improved. Credits (REACTION, GAME/TRIVIA + streak bonuses, DAILY_GIFT) still originate here via authoritative paths (now using local Besito inside the methods for atomicity). Emit of besitos_awarded still fires post-commit (verified by schedule_emit patches in golds + re-runs). New observational listeners (broadcast reaction + game award) provide domain-owned hooks for future (streaks/promo) *without* mutation or re-entrancy. 0 change to balances, tx sources, partials. Daily property shim does not affect source-of-truth credits.
- **Missions/Rewards (atomic delivery):** 0 impact (untouched per tight scope; Item6 explicitly "other composers like broadcast/game/daily" continuation of Item5 which touched only reward). Golds (cross atomicity + reaction_mission_flow) still protect "credit survives deliver False" + best-effort post-credit sides. Reward's own listener + local pattern precedent upheld.
- **Narrative (listeners):** Protected + extended. Narrative remains first listener (inverse credits in _grant_achievement). New broadcast/game listeners follow identical "MUST NOT credit/debit + best-effort + log + domain ownership" contract (copy precedent). Central reg now includes all 4; bus swallows errors. 0 risk of loops with narrative's own credit-for-achievements. Wiring proof strengthened.

All 3 systems' contracts (atomicity golds, best-effort sides, "credit survives", EventBus removable) remain intact. "0 atomicity impact" + "3 critical systems remain protected" per PLAN Result + decisions self-check.

## Compliance Checklist (vs audited rules)
- Handlers: 0 changes → no new logic/DB/ >1-service violations introduced. (Pre-existing direct Besito in some handlers outside scope.)
- Services: Domain ownership preserved (credits stay in broadcast/game/daily methods); no duplication (local pattern is canonical per Item5); models via BesitoService; no DB direct.
- Layers/Cross: EventBus used for notifications (not commands); listeners "MUST NOT"; central explicit bot.py reg; locals for atomic command paths.
- Functions/LOC/Naming: No new long funcs; pre-existing lengths preserved; names unchanged; comments use "verbo + contexto".
- Anti-patterns/GSD: No prohibited patterns added; GSD/PLAN-driven (self-check PASSED referenced); tight scope.
- Atomicity/3-systems/EventBus: All upheld (see above + golds + "MUST NOT" + schedule_emit).
- Logging: Present in listeners + pre-existing credit paths.
- Scope/0-creep/0-change: Matches exactly (docs + code + tests + decisions confirm).

## Veredict
**PASS WITH NOTES**

**Reasons:**  
- Zero critical violations of architecture, layers, atomicity contracts, EventBus "MUST NOT"/best-effort, duplication, GSD, or 3 critical systems. Changes are a faithful, tight, conservative application of the proven Item5/Reward + narrative/EventBus precedent to the final 3 high-volume gamif composers.  
- Atomicity, partial-failure ("credit survives"), best-effort post-credit (missions + listeners), return contracts, and gold tests are explicitly protected in implementation + test guards/patches + docs. 0 prod behavior change.  
- All "medium" items are either (a) intentional per PLAN (daily property + test guards for compat) or (b) pre-existing (long funcs) and not caused by the Item6 deltas.  
- Strong traceability: comments, decisions.md full entry, updated CLAUDEs with refs to PLAN/gsd/golds/precedents, batch note. Central reg + removable listeners.  
- Minor notes (the 3 medium) are maintenance/fragility only; do not affect correctness, security, or the 3 systems. Handlers direct-Besito is legacy/out-of-scope.

**Overall:** Item 6 successfully completed the tirón (4 items) without breaking rules. The refactor unifies the remaining direct compositions safely while strengthening cross-domain observability for gamif. Ready for test-guardian (re-run critical list from decisions: broadcast reaction unit full, cross_service_atomicity full, reaction_mission_flow + full_chain + limit, daily unit + concurrent, game unit play paths, besito credit + emit, story, event_bus, combined -k filters) + any future items.

## Suggested (Non-Blocking) for Test-Guardian / Quick (if run)
- Re-execute the exact critical tests listed in decisions.md Item6 Result + gsd log (with `-q --tb=line -p no:cov --override-ini="addopts="` + schedule_emit patch + N806 tolerance + fresh TG 777). Verify guards exercised, locals intercepted, emit fires from broadcast/game/daily credits, "credit survives" + daily atomic hold, listeners receive when reg'd (smoke via bot import or manual).
- Spot-check: grep for held in the 3 services ==0; locals present in credit sites; listeners have "MUST NOT"; bot reg has 4 + Item6 comment; no handler deltas in git (if available).
- If quick: add a one-off comment in daily property noting "compat shim only (Item6)"; otherwise leave.
- No code changes required for PASS.

**References (for future auditors):**  
- decisions.md:160-202 (full Item6 entry + Result checklist that this audit verified matches state).  
- services/broadcast/CLAUDE.md:77-86, gamification/CLAUDE.md:45-47 (Item6 append), missions/CLAUDE.md:99-100.  
- services/event_bus.py (DESIRED CONTRACT), root CLAUDE.md (rules + GSD), architecture.md/rules.md (layers).  
- PLAN cross-refs + gsd-remaining-besito-compositions.log (self-check PASSED + critical tests list + BATCH note) — per decisions.  
- Golds: test_cross_service_atomicity.py, reaction_* flows, invariants, daily atomic (TestSession + patch + guards).  

**End of audit.** No fixes implemented (per instructions). Report persisted + MEMORY.md updated (see sibling file).
