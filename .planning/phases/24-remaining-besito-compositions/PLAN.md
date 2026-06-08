# PLAN: Unify/reduce remaining direct BesitoService compositions in broadcast_service, game_service, daily_gift_service (Item 6 / 4th and final in tirón, max 4)

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-06-08  
**Focus:** Tight, conservative, phased reduction of *held direct compositions* (and lazy property usage for credits) of BesitoService inside the three core high-volume gamification composers: BroadcastService (reactions), GameService (minijuegos + streaks), DailyGiftService (daily claim). Per impact-analyzer recs + precedents (Reward Item5/23: held→local inside _deliver_besitos only + obs listener + central reg + 1-line test; Story: held retained + listener; EventBus: post-commit best-effort via schedule_emit + gather return_exceptions; atomicity golds in test_cross_service_atomicity + reaction_mission_flow + invariants): use **local on-demand `BesitoService(db=self.db)` (or `db=self._get_db()` for daily) *only inside the credit/debit call sites*** (the methods/blocks that perform credit_besitos or debit). This preserves 100% atomicity/tx control of the caller's tx (reaction INSERT + credit internal commit + mission best-effort; game record + credits; daily claim + credit; all as before). Remove the `__init__` held for broadcast/game; for daily (which already avoids __init__ held via lazy property), use local inside `claim_gift` credit block only. Add 1-2 *observational* EventBus listeners if high-value for domain (e.g. post-award reactions in broadcast for potential streak/promo hooks; post-award game for streaks/promo/analytics) with "MUST NOT credit/debit" contract + best-effort doc (copy story_service.py:670-694 structure). Central explicit registration in bot.py on_startup (extend the existing cross-domain block). Exactly the 1-line test fixes (or minimal + hasattr guards per daily precedent) in the specific tests that access .besito_service (test_broadcast_service_reaction_flow.py:401 owns assert; test_daily_gift_service.py:135 and the concurrent 287; cross_service_atomicity.py daily patches/guards at 726/762). Targeted docs updates ONLY in `services/broadcast/CLAUDE.md`, `services/gamification/CLAUDE.md` (cross notes), `services/missions/CLAUDE.md` (append to existing cross section), `decisions.md` (new Item 6 entry mirroring Item 5 style), and bot.py reg comment if listeners added. **Zero prod behavior change** (all credit paths, balances, tx sources REACTION/GAME/DAILY_GIFT/TRIVIA, reaction_result dicts, daily claim returns, game win msgs, Lucien strings identical), **zero atomicity impact** (locals share the db; credit's internal commit + schedule_emit best-effort remain exactly as before; gold tests protect "credit survives later best-effort"), **zero other services touched** (store, mission, reward, story, vip, package, backpack, streak etc. OUT per tight scope), **zero new test files**, **zero new events/payload changes**. 5 small phases (F1 prep/GSD/baseline + confirm golds atomicity/reaction/mission/invariants; F2 broadcast (locals inside the two credit sites + high-value listener if); F3 game (locals inside play_* credit blocks + listener if for streaks); F4 daily (local inside claim_gift + hasattr guards); F5 1-line fixes + re-runs golds (atomicity + reaction_mission_flow + invariants + besito credit + story) + verif final + self-check PASSED with batch note "4 items completed in tirón"). Full GSD pre-log discipline on `.planning/quick/gsd-remaining-besito-compositions.log` before *every* edit/gate/verif/ruff/pytest/grep/smoke/summary. At F5 end: explicit batch update phrase in log + handoff to arch-enforcer/test-guardian + fin de tirón (batch completo 4 items).

**Input principal (source of truth):** 
- User prompt's complete impact-analyzer report description (exec summary + risks atomicity/best-effort/loops + mapa de impacto with targets broadcast/game/daily + tests with 1-line accesses + scope tight proposal: locals in credit methods for broadcast/game/daily, 1-2 obs listeners, 1-line fixes, docs; precedents Reward/Story/EventBus golds; "core high-volume from impact"; "use local db= inside credit/debit methods only (to preserve atomicity/tx control like Reward Item5)"; "exactly the 1-line test fixes + hasattr guards (daily precedent)"; "0 other services (store/mission etc out)"; "update docs/CLAUDEs/decisions"; "GSD pre-log ... before edits"; "at end: update batch to 4 items completed in tirón"; "Instrucciones explícitas para el siguiente agente (gsd-executor): GSD pre-log formato (timestamp | PHASE N | ...), orden estricto F1→F5, comandos concretos (run_terminal para echo/ruff/pytest -q --tb=line -p no:cov --override-ini=.../grep/smoke), **patrones a copiar al pie de la letra** (Reward local inside _deliver + 1-line test, story listener block + "MUST NOT" + best-effort, bot reg, atomicity golds patch+DESIRED+file+TestSession+strict+"post-credit best effort", daily hasattr, N806 tolerance with doc), self-check PASSED en log con handoff a arch-enforcer/test-guardian + fin de tirón (batch completo 4 items)").
- Exhaustive discovery by planner (current code state post-Item5/23 + 22/21/20/19: broadcast_service.py:34 holds `self.besito_service = BesitoService(self.db)`, credits at 220 (register_reaction) + 283 (check_and_register_reaction, the atomic gold path), close getattr at 402; game_service.py:303 holds, credits at 615(dice)/847+859(trivia win+streak bonus)/1239+1251(vip trivia)/1590+1601(simple) + one local already at 953 for has_sufficient in streak protection, close getattr 317; daily_gift_service.py: no __init__ held (lazy @property besito_service at 45-49 creating BesitoService(self._get_db())), claim_gift uses at 165/173/187 for credit+get_balance, close does not touch besito sub; bot.py:200-204 has the cross-domain reg block (now 2 listeners from Item5: narrative + rewards) + imports 71-74; story_service.py:670-694 exact "Cross-domain event listeners" block + on_besitos_awarded_from_gamification + "MUST NOT call back into credit/debit besitos" + best-effort + log "narrative | besitos_awarded_received" (copy source); event_bus.py:23 EVENT_BESITOS_AWARDED + schedule_emit + DESIRED CONTRACT + gather return_exceptions; tests with direct accesses in scope: test_broadcast_service_reaction_flow.py:401 (assert hasattr + _owns_session on the sub, in test_composer_sub_closes...); test_daily_gift_service.py:135 (direct in claim success) + 287-288 (hasattr guard in concurrent claim, daily precedent); test_cross_service_atomicity.py:726-728 (daily guard+fallback to BesitoService(db)), 762 (patch.object on daily_svc.besito_service for !success path), 783 (direct BesitoService(db) elsewhere); reward/story/store tests have accesses but story keeps held (precedent), store/mission OUT; decisions.md has the full Item5 entry to mirror for Item6; services/broadcast/CLAUDE.md (no cross section yet), gamification/CLAUDE.md (has Item1 cross notes), missions/CLAUDE.md (has Item5 cross section to append); 23-PLAN.md + gsd-reward-besito-eventbus.log (exact structure, GSD style, snippets, self-check, executor instrs); atomicity gold + reaction_mission_flow + invariants (file+TestSession, patch schedule_emit, strict == on deltas/counts/tx source, "credit survives deliver False", "post-credit misiones (best effort) + event listeners (best effort)", DESIRED CONTRACT, N806 tolerance with doc, fresh TG 777x, try/finally close+dispose); gsd logs (gsd-reward-besito-eventbus.log, gsd-critical-tests.log, gsd-eventbus-poc-item1.log etc.); no pre-existing 24- dir or gsd-remaining log (created by planner with INIT/DISCOVERY/PLANNING entries).
- Precedents + gold (exact structure, GSD, phases, DoD, snippets, self-check, executor instrs): `.planning/phases/23-reward-besito-eventbus-decoupling/PLAN.md` + SUMMARY.md + log (Item5: held→local inside _deliver + rewards observer listener + central reg + 1-line in 1 test + docs only missions/CLAUDE + decisions; 5 phases F1-F5; GSD pre every; copy story listener block al pie de la letra; atomicity gold re-runs with patch+DESIRED+TestSession+strict+"credit survives"; self-check PASSED with handoff + critical tests list); 22-critical-tests-three-systems/PLAN.md (handoff named the reduce as next); 21-getservice-unification/PLAN.md (local db= for shared/owns=False, get_service for high-level contexts); 20-reward-gamif-rules-compliance/PLAN.md + 19-eventbus-poc/PLAN.md + 19-*-SUMMARY.md + gsd-*.logs; gold tests `tests/integration/test_cross_service_atomicity.py` (full _create_engine_and_session tmp_path + TestSession reopen pre-svc, DESIRED CONTRACT TG ID, patch event_bus, strict dict/balance/progress/tx asserts, N806, happy + partial fail paths, try/finally dispose, "post-credit best effort"), `tests/integration/test_reaction_mission_flow.py` + `test_reaction_full_chain.py` + `test_reaction_limit.py` (reaction→credit→mission chains, strict balance/tx/mission asserts), `tests/unit/test_broadcast_service_reaction_flow.py` (concurrent gather pilot for dup reaction, get_service, TestCheckAndRegisterReaction), `tests/unit/test_besito_service.py` (credit with EventBus patch, race-mock, insuff, DESIRED, TG 77728001 + N806 doc), `tests/unit/test_daily_gift_service.py` (concurrent claim with hasattr guard + fallback, direct .besito_service in success path), `tests/unit/test_game_service.py` (if accesses), event_bus unit + story listener test coverage.
- Project rules (non-negotiable): CLAUDE.md (3 critical systems: gamif source of credits, missions/rewards via atomic, narrative listener precedent; EventBus for *notifications* (obs-only, "MUST NOT credit/debit" contract), local db= inside methods for atomic credits (per Reward fix), get_service where lifecycle, <50 LOC, logging "módulo | acción | user_id | resultado", GSD pre-log before edits, handlers exactly-1-service), rules.md (≤50 LOC per func, naming verb+context+result, anti-patterns), architecture.md (handlers→services→models; no logic in handlers), models/CLAUDE.md (tx for atomics, no raw, Alembic rules), decisions.md (EventBus + mw + Item5 reduce entry to extend), services/gamification/CLAUDE.md + broadcast/CLAUDE.md + missions/CLAUDE.md + narrative/CLAUDE.md (current cross notes + "MUST NOT credit" contract for listeners), services/CLAUDE.md, handlers/CLAUDE.md.
- Current state (post prior Items 1/5/19-23/21-22): strong (emit wired only in credit success post-commit, 2 listeners + central reg, atomicity gold protects credit vs best-effort sides + reaction/mission chains + invariants, broadcast reaction flow concurrent + get_service, daily has hasattr precedent + concurrent claim test, game has one local already for has_sufficient, held composition still present in broadcast+game; daily uses lazy property for credits). This Item reduces the remaining core high-volume sites safely (tight: only these 3; 0 other composers).

**GSD enforcement:** Executor MUST prefix **every** modification, gate, verification, ruff, pytest, grep, smoke, or summary step with a GSD log append (timestamp | PHASE | description) to `.planning/quick/gsd-remaining-besito-compositions.log`. Use identical discipline and entry style as gsd-reward-besito-eventbus.log / gsd-eventbus-poc-item1.log / gsd-reward-gamif-item2.log / gsd-getservice-unification.log / gsd-critical-tests.log (pre + post + counts, "GSD pre-edit <file> (F<N> <short motive>) - <desc + refs DoD + patrones copiados>", wc tracking). No edits (even to PLAN or log beyond appends) without pre-log. Planner already did initial pre-create/pre-write entries (see log, 4 lines at PLAN time).

---

## 1. Alcance preciso (In / Out explícito)

### En esta entrega (scope "tight" per analyzer recs + "smallest change" + precedents + 0 behavior/0 atomicity/0 other composers):
- **BroadcastService refactor (reduce held composition):**
  - `services/broadcast_service.py`: Remove `self.besito_service = BesitoService(self.db)` from __init__ (line ~34). In the two credit sites only (`register_reaction` ~220 and `check_and_register_reaction` ~283, the latter the atomic gold path used by handlers), create local on-demand `besito_service = BesitoService(db=self.db)` right before the credit_besitos call (shares session so credit's internal FOR UPDATE/lock + commit + schedule_emit best-effort stay in context with the caller's reaction tx; the outer db.commit() after remains for the reaction row). close() getattr list for "besito_service" stays as-is (getattr returns None → if sub: skips; harmless; no code change needed for close). All logs, return dicts (id, broadcast_id, user_id, besitos_awarded, emoji_id, emoji_char), TransactionSource.REACTION, mission increment best-effort, reaction_result "besitos_awarded" local field identical. No change to emoji CRUD, stats, create_broadcast, get_*, or the IntegrityError/duplicate path.
- **GameService refactor (reduce held composition):**
  - `services/game_service.py`: Remove `self.besito_service = BesitoService(self.db)` from __init__ (line ~303). In the play_* methods that credit (play_dice_game ~615, play_trivia_game ~847+859 for win+streak bonus, play_vip_trivia_game ~1239+1251, play_simple_trivia_game ~1590+1601), create local on-demand `besito_service = BesitoService(db=self.db)` before the credit call(s) in each block (re-use the local for the 1-2 credits per method if both win + bonus). The existing local at ~953 for has_sufficient_balance in claim_for_streak_protection remains (or consistent style). close() getattr stays (becomes None for besito; harmless). All records (GameRecord with payout), return dicts, streak bonus calc, VIP vs free limits, Lucien voice templates, TransactionSource.GAME/TRIVIA identical. No change to question loading, check_win, streak helpers, or non-credit paths.
- **DailyGiftService (local inside credit method only; property/guards for compat):**
  - `services/daily_gift_service.py`: No __init__ held (already uses lazy @property besito_service at 45-49). In `claim_gift` only (the credit site, lines ~165/173/187 for the credit + get_balance after success), create local on-demand `besito_service = BesitoService(db=self._get_db())` for those two calls (instead of `self.besito_service`). Keep the @property (for test compat + hasattr guards precedent; it can still be accessed by tests for balance asserts or patching in some paths, while the actual credit command uses the local inside the method). close() and __del__ untouched (never touched besito sub). All returns (success, amount, "¡Recibiste N besitos! ... Tu saldo actual es: X"), TransactionSource.DAILY_GIFT, claim row, cooldown logic, config identical. 0 change to can_claim, get_last_claim, history, totals.
- **1-2 observational EventBus listeners (high-value for domain, if confirmed in F2/F3 GSD):**
  - `services/broadcast_service.py` (and/or game_service.py): Add at module bottom (after close, mirroring story_service.py:670-694 and reward post-Item5) the domain observational listener(s) (async def, e.g. `on_besitos_awarded_broadcast_reaction_observer(payload: dict) -> None` for broadcast; optional `on_besitos_awarded_game_award_observer` for game). Full "Cross-domain event listeners" comment block + docstring with "MUST NOT credit/debit besitos", "best effort, non-authoritative", "domain ownership", "use get_service if future needs DB", log format "broadcast | besitos_awarded_received | user_id=... | amount=... | source=... | ref=..." (or "game | ..."). No side effects that mutate besitos or call credit. Decision on 1 vs 2 and exact names logged in first GSD of the phase (high-value: post-award reactions for potential streak/promo hooks per 3 critical systems; game awards for streaks/promo). If added, central reg follows.
  - `bot.py`: If listener(s) added, extend the cross-domain listeners block (after scheduler, after the existing narrative + rewards registers; add import(s) + register call(s) + extend the logger.info line). Explicit, central, no import side-effects. Comment updated (e.g. "Fase 3 of eventbus-poc + Item 5 + Item 6: narrative + rewards + broadcast[/game] domains.").
- **1-line test fixes + hasattr guards (daily precedent; no new tests/cases):**
  - `tests/unit/test_broadcast_service_reaction_flow.py`: Exactly 1 line change in `test_composer_sub_closes_are_harmless_for_passed_db` (the `assert hasattr(svc, "besito_service")` + owns assert at ~400-401) to a guard or "not present" reality post-removal (e.g. `assert not hasattr(svc, "besito_service") or svc.besito_service is None  # 1-line fix post held removal (F2); was asserting on composer sub`); or equivalent minimal that makes the test reflect new owns/close semantics without the held sub. (Import if needed minimal.)
  - `tests/unit/test_daily_gift_service.py`: 1-line adjustments at 135 (direct .besito_service.get_balance in claim success) and/or the concurrent path 287 (already has hasattr guard at 288; ensure fallback or direct BesitoService(db) style); add comment "# 1-line fix post local-in-claim (F4); daily precedent guard preserved".
  - `tests/integration/test_cross_service_atomicity.py`: 1-line or guard at 726 (daily_svc.besito_service.get_balance with hasattr at 727-728 already present → keep/ensure); at 762 (patch.object(daily_svc.besito_service, "credit_besitos"...) → adjust to hasattr guard or patch after property access or use a direct local mock strategy with 1-line comment; 783 already uses direct BesitoService(db) fallback). Per "exactly the 1-line test fixes + hasattr guards (daily precedent)".
  - Game tests: if F1 baseline grep finds any direct `svc.besito_service` or `game.besito_service` accesses in unit/integ (e.g. test_game_service.py or streak flows), exactly 1-line fix each with comment (scope tight: no new tests).
  - 0 new test files/cases (coverage for new listeners via re-runs of credit paths + smoke of register+emit + existing event_bus/story tests).
- **Docs (minimal, cross-domain + targeted):**
  - `services/broadcast/CLAUDE.md`: Add short "Cross-domain notifications (EventBus)" section at end (modeled on gamification/CLAUDE + missions/CLAUDE Item5) documenting the reduced composition in BroadcastService, the broadcast listener (if added), best-effort contract, "MUST NOT credit", refs to event_bus + decisions + this PLAN/log + gold atomicity/reaction.
  - `services/gamification/CLAUDE.md`: Append/update the existing "Cross-domain notifications (EventBus PoC Item 1)" section with note on Item 6 reductions in broadcast/game/daily (locals inside credit methods only; 1-2 new obs listeners if high-value for game/broadcast awards; 0 atomicity impact; refs).
  - `services/missions/CLAUDE.md`: Append 1-2 bullets to the existing "Cross-domain notifications (EventBus) (Item 5 ...)" section (or new sub) noting the continuation for the remaining core composers (broadcast/game/daily), locals for atomic credits, optional high-value listeners, 0 other services touched, refs to this PLAN + 23-PLAN.
  - `decisions.md`: Append new decision entry "## Unify/reduce remaining direct BesitoService compositions in broadcast/game/daily (Item 6 / 4th and final in tirón)" following the exact style/structure of the Item 5 entry (Motivo, Riesgos (críticos incl atomicity + partial failure contracts from golds + re-entrancy if listeners credited), Decisión (locals inside credit/debit methods only for the 3 + 1-2 obs listeners if high-value + central reg if + 1-line fixes + hasattr daily precedent + targeted docs), Resultado (0 behavior/0 atomicity change, held removed for these, listeners wired if, gates, handoff, batch "4 items completed in tirón")).
  - `bot.py` (if listeners): extend the reg comment to reference Item 6.
- **Gates + re-runs (protect 0 regression + atomicity gold + listener wiring + reaction/mission chains):**
  - Targeted re-runs of: broadcast reaction unit (TestCheckAndRegisterReaction + composer close/lifecycle), `test_cross_service_atomicity.py` (gold: happy REACTION credit path + "credit survives" partials + patch schedule_emit + note post-credit best-effort sides + daily atomic with guards), `test_reaction_mission_flow.py` + `test_reaction_full_chain.py` + `test_reaction_limit.py` (full chains reaction→credit→mission→besitos), game unit (play dice/trivia paths), daily unit (claim + concurrent), besito credit (emit still fires), story (protects inverse credit in _grant), event_bus (if listener coverage extended cheaply without new files), broader smoke filtered by reaction/atomic/mission/besitos_awarded/game/daily.
  - Patch schedule_emit + DESIRED CONTRACT style where verifying emit (as in atomicity gold + Item1/5).
  - 0 new test files/cases (coverage for listeners comes from re-runs of paths that exercise credit inside broadcast/game/daily + existing event_bus/story listener tests + manual smoke of register+emit).
- **Behavior/contracts:** All credit paths (REACTION via check_and_register_reaction, GAME via play_*, DAILY_GIFT via claim_gift, plus any internal) return identical (bool success, dicts with besitos_awarded, Lucien msgs, balances, history tx with correct source + ref). The event is still emitted (best-effort) on every credit including these; if new listeners, they receive when registered. No user-visible or admin-visible change. Partial failure contracts (credit tx commits even if later mission best-effort or listeners "fail") protected by golds.
- **Artefacts:** This PLAN.md + GSD entries (pre every) in the dedicated log + (optional post-exec) SUMMARY.md. Batch note "4 items completed in tirón" at F5 self-check + log.

**Archivos que se modificarán (exactos, por orden de fases; prefer extend, minimal):**
1. `.planning/quick/gsd-remaining-besito-compositions.log` (all phases, pre only via echo; no "edit" of source).
2. `services/broadcast_service.py` (F2: __init__ + two credit sites; optional listener at bottom).
3. `services/game_service.py` (F3: __init__ + play_* credit blocks; optional listener at bottom).
4. `services/daily_gift_service.py` (F4: inside claim_gift credit block; property kept for compat).
5. `tests/unit/test_broadcast_service_reaction_flow.py` (F5 or F2 gate: exactly the 1 access/owns assert line + comment).
6. `tests/unit/test_daily_gift_service.py` (F5 or F4: 1-line at 135 + ensure guards at 287).
7. `tests/integration/test_cross_service_atomicity.py` (F5 or F4: guards/patches at 726/762 with 1-line comments).
8. (If game direct accesses found in F1): the relevant game test file(s) — 1-line each.
9. `bot.py` (F3/F5: import(s) + register call(s) + extended log line + comment, *only if* 1-2 listeners added).
10. `services/broadcast/CLAUDE.md` (F5: add cross-domain section).
11. `services/gamification/CLAUDE.md` (F5: append to existing cross section).
12. `services/missions/CLAUDE.md` (F5: append 1-2 bullets to Item5 cross section).
13. `decisions.md` (F5: append Item 6 decision entry after Item 5).
14. Re-runs/gates/verifs/smokes do not modify (except log appends + ruff auto-fixes if any on touched).

**Fuera explícitamente (nada de scope creep, per "tight" + "0 other composers" + "1-line only" + precedents + "4th and final in tirón"):**
- **NO** other files in services/ (no store_service, mission_service, reward_service (already done Item5), story_service (keeps held per precedent), package/vip, backpack, streak_promotion, trivia_*, user, channel, vip, analytics, scheduler, backup, __init__.py exports, etc.).
- **NO** handlers (broadcast_handlers, game_user_handlers, gamification_* etc. — they already follow 1-service or call via the composers; no change).
- **NO** new test files, no new test methods/cases (only the 1-line access fixes + hasattr guards in the *existing* listed tests; no extension of event_bus tests or atomicity for "new listener" coverage — re-runs + smoke suffice).
- **NO** changes to close() bodies beyond the getattr becoming None (harmless), to non-credit methods, to emoji CRUD, to question loading, to cooldown/config, to any return strings/dicts or LucienVoice.
- **NO** migration to get_service() for the local credits (use direct BesitoService(db=...) to keep tx/owns semantics explicit inside the atomic flows; get_service is for handlers/contexts per 21 precedent).
- **NO** editing CLAUDEs/decisions except the four specified (broadcast/, gamification/, missions/ + decisions.md); no AGENTS/ROADMAP/root CLAUDE/handlers/CLAUDE.
- **NO** touching models, alembic, config, utils, middlewares, keyboards, bot startup beyond the reg block (if listeners).
- **NO** new events, no change to besitos_awarded payload, no removal of schedule_emit from credit.
- **NO** broad "reduce all compositions" (only these three core high-volume per analyzer + "0 other services").
- **NO** behavior or contract changes (0 impact on partial failure, 0 on "credit survives later best-effort", 0 on reaction_result local "besitos_awarded", 0 on daily claim returns, 0 on game win payouts).
- **NO** adding tests for listeners beyond re-runs/smoke (tight scope).

**Comportamiento observable:** Identical for all reaction credits (REACTION tx + balance + mission best-effort + return dict), game plays (GAME/TRIVIA tx + balance + records + streak bonuses + returns + voice), daily claims (DAILY_GIFT tx + balance + claim row + cooldown + returns). If listeners added, the event is still emitted (best-effort) on every credit from these sources; the new observer(s) receive when registered (log only, no mutation). No user-visible or admin-visible change. The 3 critical systems (gamif as source, missions/rewards via atomic, narrative as existing listener) remain protected.

---

## 2. Fases ordenadas (5 fases pequeñas, secuenciales, con gates estrictos)

### Fase 1: Preparación (GSD log, baseline, fixtures/mocks/patterns confirm, patrones gold)
**Objective:** Establecer disciplina GSD para el Item (log touched by planner with 4+ lines), confirmar baseline de archivos tocados (ruff + targeted pytest verdes pre-cambios), mapear sites de composición actual + credit call sites + listener patterns + bot reg + atomicity/reaction/mission golds + daily hasattr precedent, preparar setups para the 1-line fixes (fresh TG or sample_user, db_session, TestSession for cross), confirmar that credits inside broadcast/game/daily still exercise schedule_emit (via patch in re-runs). Sin cambios de lógica aún. Safe point inicial.

**DoD checklist (marcar al completar):**
- [ ] Log `.planning/quick/gsd-remaining-besito-compositions.log` exists with planner INIT/DISCOVERY/PLANNING/pre-write entries (≥4 lines) + at least 1 pre-F1 of executor.
- [ ] Baseline: ruff clean on `services/broadcast_service.py`, `services/game_service.py`, `services/daily_gift_service.py`, the 3 specific tests (broadcast_reaction_flow, daily_gift unit, cross_atomicity), `bot.py` (and spot on story_service.py for listener pattern + reward_service.py for post-Item5 gold).
- [ ] Baseline targeted pytest verdes (clean flags): `pytest tests/unit/test_broadcast_service_reaction_flow.py -q --tb=line -p no:cov --override-ini="addopts="`, `pytest tests/unit/test_daily_gift_service.py ...`, `pytest tests/unit/test_game_service.py ...` (if exists or relevant), `pytest tests/integration/test_cross_service_atomicity.py ...` (gold), `pytest tests/integration/test_reaction_mission_flow.py ...` (or full chain), spot story/besito units for patterns.
- [ ] Confirm gold patterns via grep/lectura: DESIRED CONTRACT, patch("services.event_bus.schedule_emit"), "post-credit ... best effort", listener comment block + "MUST NOT" in story_service.py:670+, bot.py on_startup register block (200-204, now with 2), atomicity "credit survives deliver False" + reaction credit paths, N806 tolerance if any, TG-style or sample_user, local db= for shared session in atomic flows, daily hasattr guards at 288/727.
- [ ] Mocks/fixtures list: db_session (for local Besito(db=)), TestSession + tmp_path for cross, mock_bot, sample_user/sample_broadcast/sample_emoji, patch schedule_emit ready, get_event_bus for smoke, fresh TG 7772xxxx for ID contract.
- [ ] Grep current composition: `grep -n "besito_service\|BesitoService(self.db)\|self\.besito_service" services/broadcast_service.py services/game_service.py services/daily_gift_service.py` shows the sites (init held for b/g, credits, daily property + claim uses, close getattr for b/g); confirm only credit sites will change to local.
- [ ] GSD pre + post entries for baseline (≥5-10 total for F1).
- [ ] Safe point F1.

**Archivos:** Log + (lectura/grep/ruff/pytest; 0 edits to prod/tests in F1).

**Cambios clave (bullets accionables):**
- Ejecutar comandos de baseline (ver Instructions).
- Grep/lectura rápida de patterns (story listener block, bot reg, atomicity patch+docstring + daily guard, broadcast reaction flow close test, reward post-Item5 as local gold).
- Confirm import of BesitoService will be available for any 1-line (or note minimal import companion).
- Actualizar log con "F1 baseline verde + patterns confirmed (story listener copy source, atomicity/reaction golds for atomicity, daily hasattr precedent, 1-3 access sites in broadcast/daily/cross tests) + ready for refactor".
- (No code changes.)

**Tests que deben pasar antes de avanzar (gates de F1):**
- Ruff on touched py (3 services + 3 tests + bot + spot story/reward).
- `pytest tests/unit/test_broadcast_service_reaction_flow.py -q --tb=line -p no:cov --override-ini="addopts="`
- `pytest tests/unit/test_daily_gift_service.py -q --tb=line -p no:cov --override-ini="addopts="`
- `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="` (gold)
- Spot `pytest tests/integration/test_reaction_mission_flow.py -q --tb=line -p no:cov --override-ini="addopts="` (or -k subset)
- Grep confirm + GSD entries + "F1 safe point".

**Riesgos + mitigaciones:**
- Riesgo: baseline shows pre-existing unrelated fails (alembic, xfails in besito for lifecycle, etc.) → Mit: document in log; use targeted -k; do not count as regression of this Item (precedent in 23/22/19/20).
- Riesgo: the broadcast reaction flow test has a sub-close test specifically for the besito held → Mit: the 1-line fix in F5 (or early gate) will adjust the assert to reflect new reality (no held sub); F1 gates run pre-change.
- Riesgo: daily test patches on daily_svc.besito_service (cross 762) → Mit: F1 confirms the hasattr guard pattern exists in the file (288/727); F4/F5 will ensure 1-line guard or fallback for the patch site.
- Bajo: time on baseline → Mit: targeted, parallel commands where safe but prefer sequential for log.

**Safe point:** Baseline verde + patterns confirmed + "F1 safe point - ready for broadcast refactor; no source changed yet". Reversible (nada editado en fuentes aún).

---

### Fase 2: Refactor BroadcastService (remove held; local Besito on-demand inside the two credit sites; listener if high-value)
**Objective:** Ejecutar el core change for broadcast (high-volume reaction credit path): remover la composición held en __init__, re-implementar the credit call sites (register_reaction + check_and_register_reaction) usando local BesitoService(db=self.db) para the credit_besitos (copia el patrón de "local for shared db" de atomicity golds + Reward Item5 + getservice normalization). Mantener 100% comportamiento (return dicts, tx source REACTION, commits, "besitos_awarded" local, mission best-effort). close() getattr se vuelve no-op para besito (harmless). Logging estándar. Decisión en primer GSD de F2: agregar 1 high-value obs listener (broadcast reaction award) + nombre exacto (e.g. on_besitos_awarded_broadcast_reaction_observer); si sí, append at bottom + prepare for central reg in F3. GSD pre every edit. Ruff + smoke + targeted (note: the 1 access test will fail until F5; gate other paths + service itself). Safe point.

**DoD checklist:**
- [ ] __init__ no longer sets self.besito_service (comment explaining reduction + local-only for reaction credits; scope other composers untouched).
- [ ] register_reaction and check_and_register_reaction use local `besito_service = BesitoService(db=self.db)` for the credit call (docstring or inline comment updated to note "local on-demand (shared db preserves atomicity of REACTION credit + reaction row + mission best-effort)"); success path + error/IntegrityError paths identical.
- [ ] All other methods untouched (emoji CRUD, stats, create/get/update/delete broadcast, get_reactions_*, close getattr list).
- [ ] (If listener decision YES): listener added at bottom of broadcast_service.py (after close): full comment block "Cross-domain event listeners..." + async def with docstring quoting "MUST NOT credit/debit", "observational best-effort for broadcast domain", "no re-entrancy risk with reaction credit paths", log "broadcast | besitos_awarded_received | ...", no mutation code. Decision + name logged in GSD.
- [ ] Ruff limpio + format; GSD pre each edit + pre-gate.
- [ ] Smoke: import BroadcastService + basic (non-credit paths or emoji CRUD).
- [ ] Grep: `grep -n "self\.besito_service = " services/broadcast_service.py` → 0 (active); "BesitoService(db=self.db)" present in the credit sites; (if listener) def + "MUST NOT credit" present.
- [ ] Targeted broadcast reaction unit (excluding or noting the 1 failing access test) + cross atomicity spot (exercises check_and_register_reaction + credit) + reaction_mission_flow spot pass where applicable; 0 regressions in non-credit broadcast paths.
- [ ] GSD "F2 safe point" documented.

**Archivos:** `services/broadcast_service.py` (only for edits; tests/docs later).

**Cambios clave (bullets accionables, orden: __init__ then credit sites; listener last if):**
- Pre-log GSD "pre-edit services/broadcast_service.py (F2 remove held + local in credit sites) - refs DoD F2 + copy local db= pattern from atomicity gold + Reward Item5 _deliver_besitos + getservice norm; 1-line test fix deferred to F5; listener decision in this phase GSD".
- Edit __init__ (around line 31-35):
  ```python
  def __init__(self, db: Session = None):
      self._owns_session = db is None
      self.db = db or SessionLocal()
      # Held direct BesitoService composition removed (Item 6 / remaining composers unification).
      # REACTION credits now use local on-demand BesitoService(db=self.db) *only*
      # inside register_reaction / check_and_register_reaction (preserves atomicity:
      # credit's internal commit + REACTION tx + mission best-effort + return dict all unchanged;
      # best-effort schedule_emit still fires post-credit commit).
      # Other composers (game/daily) handled in their phases; scope tight per Item 6.
      self.mission_service = ...  # (if any other held; keep as-is)
  ```
- Edit the credit sites (first the old register_reaction ~218-226, then the gold check_and_register_reaction ~281-289; keep all logic identical except the instantiation):
  ```python
  # ... (inside try, after reaction add/flush or before credit)
  description = f"Reacción con {emoji.emoji}"
  besito_service = BesitoService(db=self.db)  # local, on-demand; owns=False (db shared); credit commits internally as before + schedule_emit best-effort
  besito_service.credit_besitos(
      user_id=user_id,
      amount=besito_value,
      source=TransactionSource.REACTION,
      description=description,
      reference_id=broadcast_id,
  )
  ```
  (Exact same block for both sites; the second is the atomic path with flush + commit after.)
- (If decision YES in F2 GSD): append at very end (after last method or close):
  ```python
  # =============================================================================
  # Cross-domain event listeners (registered explicitly from bot.py on startup).
  # The listener lives here (broadcast domain ownership). It is a plain async callable
  # receiving the standard payload dict. It MUST NOT call back into credit/debit besitos
  # (to avoid any re-entrancy with reaction credit paths or future extensions; reaction
  # credit contracts and partial-failure behavior are authoritative in the credit + mission
  # best-effort flow inside check_and_register_reaction).
  # This is observational only (best effort; errors swallowed by bus).
  # =============================================================================

  async def on_besitos_awarded_broadcast_reaction_observer(payload: dict) -> None:
      """
      Broadcast-domain listener for "besitos_awarded" events (emitted by BesitoService.credit_besitos
      post-commit, including from REACTION credits in check_and_register_reaction).

      DESIRED CONTRACT (copy of narrative precedent + Reward Item5): log reception with full context
      (user_id/amount/source/ref); purely observational + wiring proof for this domain.
      MUST NOT credit, debit, or mutate besitos state here.
      Future extensions (e.g. streak/promo hooks on reaction awards) belong in this module and should use
      get_service(BroadcastService) or direct models if a fresh DB session is required.
      """
      uid = payload.get("user_id")
      amt = payload.get("amount")
      src = payload.get("source")
      ref = payload.get("reference_id")
      logger.info(
          f"broadcast | besitos_awarded_received | user_id={uid} | amount={amt} | source={src} | ref={ref}"
      )
      # No side effects that mutate besitos here (best effort, non-authoritative; 0 impact on reaction credit contracts / atomicity gold).
  ```
  (Name confirmed in F2 first GSD; "on_besitos_awarded_broadcast_reaction_observer" recommended for clarity.)
- Post edit: ruff --fix + format --check (apply if needed); smoke `python -c "from services.broadcast_service import BroadcastService; ..."` (emoji paths); grep for the removal + local (+ listener if).
- GSD entry post-gate.
- Re-run relevant broadcast/reaction tests (the owns sub test will be noted for F5; other paths green).

**Tests que deben pasar antes de avanzar:**
- Ruff on broadcast_service.py.
- `pytest tests/unit/test_broadcast_service_reaction_flow.py -q --tb=line -p no:cov --override-ini="addopts=" -k "not test_composer_sub_closes_are_harmless_for_passed_db"` (or full with expectation the 1 access fails until F5; document).
- `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="` (at least the reaction credit paths).
- Spot `pytest tests/integration/test_reaction_mission_flow.py -q --tb=line -p no:cov --override-ini="addopts="` (or -k "reaction").
- Grep + smoke + "F2 safe point".

**Riesgos + mitigaciones:**
- Riesgo: atomicity of reaction credit broken (credit now in "local" vs held) → Mit: local uses `db=self.db` (exact shared session as the old held one had); credit does its own commit inside (as always); the subsequent db.commit() for reaction row + mission best-effort are unchanged; gold test_cross_service_atomicity (which does full reaction credit + asserts credit tx present even on partial) will be re-run in F5 and protects. Local creation is cheap and matches "on-demand" rec + Reward precedent.
- Riesgo: close() or owns semantics affected → Mit: no change to close body; getattr for besito will be None (safe); the local inside credit creates a non-owning instance (db passed) whose close() is no-op.
- Riesgo: test that does `svc.besito_service` now fails → Mit: exactly the 1-line planned for F5; F2 gates exclude or note it.
- Riesgo: listener decision wrong (name/scope) → Mit: log the decision in GSD; if added, copy story block al pie de la letra (adapt 3-4 words); removable in F3 if needed (but tight scope prefers final in F2).
- Mit general: targeted, DESIRED-style comments in the edit, GSD, patch schedule_emit in re-runs.

**Safe point:** Post-ruff + greps + non-credit broadcast tests green + GSD "F2 safe point - held removed, local Besito(db=) in the two reaction credit sites only; 0 behavior change in reaction paths; close safe; listener added if high-value (name logged); 1 owns sub test deferred to F5". Reversible by restoring the init line + 2 credit sites (pre F2 commit).

---

### Fase 3: Refactor GameService (remove held; local Besito on-demand inside play_* credit blocks; listener if high-value for streaks)
**Objective:** Ejecutar el core change for game (high-volume award + streak bonus credits): remover la composición held en __init__, re-implementar the credit call sites inside play_dice_game / play_trivia_game (win + streak bonus) / play_vip_trivia_game / play_simple_trivia_game usando local BesitoService(db=self.db) antes de cada credit (o una local por método re-usada para win+bonus). Mantener 100% comportamiento (GameRecord payout, return dicts, streak calc, VIP limits, voice). El local existente para has_sufficient (~953) queda consistente. close() getattr se vuelve no-op para besito (harmless). Decisión en primer GSD de F3: agregar 1 high-value obs listener for game post-award (streaks/promo) + nombre (e.g. on_besitos_awarded_game_award_observer); si sí, append + reg in F5 (or combined with broadcast if broadcast listener added in F2). GSD pre every. Ruff + targeted game + cross gates. Safe point.

**DoD checklist:**
- [ ] __init__ no longer sets self.besito_service (comment explaining reduction + local-only for game credits; the has_sufficient local at 953 remains or style-consistent).
- [ ] All credit sites inside the four play_* methods use local `besito_service = BesitoService(db=self.db)` (one per method, re-used for win + bonus if both); docstring/inline note "local on-demand (shared db preserves atomicity of GAME/TRIVIA credit + record + return)".
- [ ] All other methods untouched (question loading, check_win, streak helpers, claim_for_streak_protection, close getattr list, non-credit paths).
- [ ] (If listener decision YES in F3 GSD): listener added at bottom of game_service.py (full block + "MUST NOT credit" + "game | besitos_awarded_received" + best-effort + "0 impact on game award contracts"; copy story al pie de la letra, adapt domain words).
- [ ] Ruff limpio + format; GSD pre each.
- [ ] Smoke: import GameService + basic non-credit (or unit paths that don't hit credits).
- [ ] Grep: 0 "self\.besito_service = " active in game_service.py; locals present in play_*; (if listener) def + MUST NOT present.
- [ ] Targeted game unit (play dice/trivia paths) + cross atomicity/reaction spot (if they overlap game) + besito credit (emit) pass; 0 regressions in non-credit game paths.
- [ ] GSD "F3 safe point".

**Archivos:** `services/game_service.py` (only for edits).

**Cambios clave (bullets accionables):**
- Pre-log GSD "pre-edit services/game_service.py (F3 remove held + local in play_* credits) - refs DoD F3 + copy local db= from Reward/atomicity + broadcast F2; listener decision (game post-award) logged here; 1-line fixes for any game test accesses in F5".
- Edit __init__ (around 300-309) with comment block mirroring F2.
- Edit each credit block (example for trivia win + bonus ~843-864; similar for dice ~611-620, vip ~1235-1256, simple ~1585-1606):
  ```python
  besitos = 0
  if is_correct:
      besitos = self.TRIVIA_WIN_BESITOS
      besito_service = BesitoService(db=self.db)  # local on-demand inside credit site; shared db; credit internal commit + schedule_emit
      besito_service.credit_besitos(
          user_id=user_id,
          amount=besitos,
          source=TransactionSource.TRIVIA,
          description=f"Victoria en trivia (racha: {new_streak})",
      )
  ...
  if is_correct and new_streak in self.STREAK_MILESTONES:
      ...
      besito_service.credit_besitos(  # re-use the local from above, or new one if not in scope
          ...
      )
  ```
  (For methods with 1 credit, one local suffices; for 2, create once before first or per credit — either fine as long as local, not self.)
- (If YES): append listener at end (name per F3 GSD decision; log prefix "game | ..."; doc "0 impact on game award contracts / partial failure").
- Post: ruff; smoke; grep; targeted pytest game unit + cross/reaction spot.
- GSD + safe point.

**Tests gates:**
- Ruff on game_service.py.
- `pytest tests/unit/test_game_service.py -q --tb=line -p no:cov --override-ini="addopts="` (targeted play paths; note any direct .besito_service access for F5).
- Spot cross/reaction + besito credit (emit still fires).
- Grep + smoke + "F3 safe point".

**Riesgos + mitigaciones:** (mirror F2: atomicity via shared db; close safe; test accesses deferred to F5; listener name decision logged; patch schedule_emit in re-runs).

**Safe point:** Post gates + GSD "F3 safe point - held removed, locals in play_* credit blocks; 0 behavior; listener added if (name logged); any game test 1-line deferred". Reversible by restoring init + credit sites.

---

### Fase 4: Refactor DailyGiftService (local inside claim_gift credit block; guards for tests)
**Objective:** Ejecutar el minimal change for daily (already no __init__ held): inside `claim_gift` only, replace the credit/get_balance uses of the lazy property with local on-demand `BesitoService(db=self._get_db())`. Keep the @property for compat (tests access it; hasattr guards precedent). 0 change to close/__del__/other methods. GSD pre. Ruff + daily unit + cross gates (with guards). 1-line/guard prep for F5 if needed. Safe point.

**DoD checklist:**
- [ ] claim_gift uses local `besito_service = BesitoService(db=self._get_db())` for the credit (173) + get_balance (187) inside the success path (after claim add, before/around the commit); comment or docstring note "local inside credit method per Item 6 (atomicity of DAILY_GIFT credit + claim row)".
- [ ] @property besito_service kept (for test compat + hasattr guards; no credit uses it after this change).
- [ ] close/__del__/can_claim/get_last/get_history/totals/config/toggle untouched.
- [ ] Ruff limpio; GSD pre.
- [ ] Grep: local present in claim_gift; property still defined (for guards).
- [ ] Targeted daily unit (claim success + concurrent with guards) + cross atomicity daily paths (guards at 726/762/783) pass; 0 regressions.
- [ ] GSD "F4 safe point".

**Archivos:** `services/daily_gift_service.py` (only).

**Cambios clave:**
- Pre-log "pre-edit services/daily_gift_service.py (F4 local inside claim_gift) - refs DoD F4 + daily precedent hasattr in tests + atomicity daily paths; property kept for compat; 1-line/guard fixes in F5 for the 3 sites (135, 287, cross 726/762)".
- In claim_gift (around 162-188):
  ```python
  ...
  db = self._get_db()
  besito_service = BesitoService(db=self._get_db())  # local on-demand inside credit method only (Item 6); property kept for test guards/compat
  try:
      ...
      success = besito_service.credit_besitos(...)
      ...
      if success:
          ...
          db.commit()
          balance = besito_service.get_balance(user_id)
          ...
  ```
- Post: ruff; grep; pytest daily unit + cross daily paths (they use hasattr guards or direct Besito(db) fallbacks).
- GSD + safe.

**Tests gates:**
- Ruff on daily_gift_service.py.
- `pytest tests/unit/test_daily_gift_service.py -q --tb=line -p no:cov --override-ini="addopts="`
- `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="` (daily atomic tests with guards).
- Grep + "F4 safe point".

**Riesgos + mitigaciones:** (atomicity via shared _get_db(); property kept so existing patches on daily_svc.besito_service in cross 762 still "see" something or guard applies; 1-line/guard in F5 for any direct that would break).

**Safe point:** Post gates + GSD "F4 safe point - local inside claim_gift only; property kept; 0 behavior; guards in tests protect; ready for F5 1-lines".

---

### Fase 5: 1-line fixes + re-runs golds (atomicity, reaction/mission chains, invariants, besito credit, story) + verif final + self-check + batch complete
**Objective:** Aplicar las modificaciones de test (1-line en broadcast reaction flow owns assert; 1-line/guard en daily claim success + concurrent; 1-line/guard en cross daily patches; + any game direct found). Luego re-ejecutar TODOS los golds que ejercitan reaction credit / game awards / daily claim / cross atomicity / reaction→mission→besitos chains / besito emit / story inverse + patch schedule_emit donde se verifica. Confirmar 0 regressions atribuibles + que el emit sigue ocurriendo (best effort). Si listeners added, smoke register+emit (both/all receive). Actualizar docs (4 CLAUDEs targeted + decisions Item6 entry mirroring Item5 + bot reg comment if). Completar GSD log con self-check PASSED explícito + lista de "tests críticos a re-correr en futuro" + "BATCH: 4 items completed in this tirón (final Item 6)". Opcional SUMMARY.md. Handoff para arch-enforcer/test-guardian + fin de tirón. GSD pre every.

**DoD checklist:**
- [ ] Exactly the 1-line (or minimal + comment) changes in the 3 (or 4 if game) test files; all now pass (broadcast owns sub test reflects no held; daily/cross use guards or direct Besito(db) with comments "# 1-line fix post ... (F5); daily precedent guard").
- [ ] Re-runs: full broadcast reaction unit, daily unit, game unit (if), `test_cross_service_atomicity.py` (gold full with patch + daily guards + "credit survives"), `test_reaction_mission_flow.py` + full_chain + limit (chains), besito credit (emit + patch), story (inverse credit + listener), broader -k filtered by reaction/atomic/mission/besitos_awarded/game/daily; all green with 0 attributable reg.
- [ ] Patch schedule_emit executed in at least the atomicity happy + one reaction/game/daily credit path (verified emit still scheduled from the local credits).
- [ ] (If listeners): smoke bot import or manual register+emit under loop; both/all receive (log lines); grep for new def(s) + reg call(s).
- [ ] Grep/inspección: 0 "self\.besito_service = BesitoService" active in broadcast/game (daily never had in init); locals present in credit sites; 1-line comments in tests; daily property still there (for guards); listener block(s) + "MUST NOT credit" + domain log if added; register + extended log in bot if; cross-domain sections in the 3 CLAUDEs; Item6 entry in decisions.
- [ ] Ruff limpio + format --check on all touched py (3 services + tests + bot if); GSD pre + "F5 re-runs + docs done".
- [ ] Self-check explícito "Self-Check: PASSED" in log with full structure (phases/DoD/gates/archivos/tests/rules verificadas (GSD pre every, scope tight 0 new files/0 behavior/0 atomicity/0 other composers, local db= para atomicity, "MUST NOT credit", patch schedule_emit, 1-line + hasattr daily precedent, logging, no prod change)/desviaciones/tests críticos/"Item 6/24 closed. BATCH: 4 items completed in this tirón (final). Ready for gsd-executor of next (if any) + arch-enforcer re-scan (broadcast/game/daily composition sites + listener wiring if + 3 critical systems) + test-guardian (correr los tests críticos listados)").
- [ ] (Opcional) SUMMARY.md in the phase dir with executive + refs al log + comandos de re-verif.
- [ ] Safe point final + criterio de éxito.

**Archivos:** The 3 (or 4) tests (1-line fixes), the 3 CLAUDEs (append), decisions.md (append), bot.py (reg comment if), log (self-check + batch note), optional SUMMARY.

**Cambios clave:**
- Pre-log per test "pre-edit <test> (F5 1-line + guard) - change ... to ... with comment; refs DoD F5 + daily precedent + atomicity gold".
- The edits (examples):
  - broadcast test ~400:
    ```python
    # assert hasattr(svc, "besito_service")
    # assert svc.besito_service._owns_session is False
    assert not hasattr(svc, "besito_service") or svc.besito_service is None  # 1-line fix post held removal (F5/Item 6); was asserting on composer sub besito_service (owns=False when db= passed)
    ```
  - daily test ~135:
    ```python
    balance = service.besito_service.get_balance(sample_user.telegram_id) if hasattr(service, "besito_service") else BesitoService(db_session).get_balance(sample_user.telegram_id)  # 1-line fix + guard post local-in-claim (F5); daily precedent
    ```
  - cross ~726 and ~762: ensure/ add the hasattr guard + fallback (already partially present; 1-line comment addition); 762 patch wrapped in if hasattr or adjusted to patch the credit path via local.
  - docs: append sections/bullets per scope (copy style from Item5 in missions/CLAUDE + decisions Item5 entry).
  - decisions: append full Item6 entry after Item5 (Motivo/Riesgos/Decisión/Resultado + refs to this PLAN + log + "BATCH: 4 items completed in tirón").
  - If listeners: bot reg extend + comment.
- Post: ruff; full re-runs of golds + chains + broader; greps all criteria; smokes; GSD pre-self-check.
- Append self-check + "BATCH: 4 items completed in this tirón (Item 6 final of max 4). Hand off to arch-enforcer/test-guardian + (user opt) future tirón." to log.
- (Opcional) write SUMMARY.md mirroring 23- one.
- GSD final + "F5 safe point + batch complete".

**Tests gates (obligatorios):**
- Ruff on all touched py.
- Full targeted per file + combined:
  ```
  ./venv/bin/python -m pytest tests/unit/test_broadcast_service_reaction_flow.py tests/unit/test_daily_gift_service.py tests/unit/test_game_service.py tests/integration/test_cross_service_atomicity.py tests/integration/test_reaction_mission_flow.py tests/integration/test_reaction_full_chain.py tests/integration/test_reaction_limit.py tests/unit/test_besito_service.py tests/unit/test_story_service.py -q --tb=line -p no:cov --override-ini="addopts="
  ```
- Broader smoke: `pytest -k "reaction or atomicity or mission or besitos_awarded or game or daily or trivia or broadcast or TestCrossServiceAtomicity or TestReaction or TestDaily or TestGame" -q --tb=line -p no:cov --override-ini="addopts="`
- Patch schedule_emit verification in at least one re-run (atomicity or besito or reaction).
- Grep for all criteria + "F5 gates + 0 new regressions attributable + BATCH 4 items completed".
- (If listeners) manual smoke register+emit.

**Riesgos + mitigaciones:**
- Riesgo: 1-line tests now exercise fresh BesitoService or no sub → Mit: they only read/post or patch; credit already committed via the local; golds re-runs confirm tx + delta + emit. Guards preserve compat.
- Riesgo: unrelated fails in broader re-runs → Mit: document (precedent 23/22); focus "0 attributable to these 1-lines".
- Riesgo: listener not "covered" because units don't run bot startup → Mit: re-runs of credit paths (schedule) + smoke register+emit (as in Item1/5 F3/F5) + note in log; no new test code per tight.
- Riesgo: batch phrase missing → Mit: explicit in F5 self-check entry + final log line.

**Safe point final + criterio de éxito:** Todos DoD F5 + self-check PASSED en log with batch note. El plan completo + log GSD son evidencia para siguiente agente (gsd-executor fin de tirón o arch-enforcer/test-guardian). 0 breakage en critical systems or credit contracts; the 3 systems (gamif, missions/rewards, narrative) remain protected; held compositions reduced for these 3 core sites following the bus loose-coupling precedent safely. "4 items completed in tirón" recorded.

---

## 3. Estrategia de tests general

- **Unit para lógica de credit sites (now with locals):** db_session fixture (in-mem or file per gold); direct create broadcast/emoji or game question setup + call the play/register/claim; post-fix the access uses explicit local BesitoService(db=) or hasattr guard + direct (same as the one created inside the credit method); asserts on return (dict for reaction, payout/balance for game, success+msg+balance for daily), tx source via other queries if needed (REACTION/GAME/TRIVIA/DAILY_GIFT), no double credit. Patch("services.event_bus.schedule_emit") around the credit call to verify emit still scheduled (best effort, as in atomicity gold + besito unit from Item1/5).
- **Integration para flujos cross (atomicity gold, reaction→mission→besitos chains, daily atomic, invariants):** file SQLite + TestSession (gold exact from test_cross_service_atomicity.py + reaction_mission_flow); patch schedule_emit; strict asserts on balance delta, BesitoTransaction source==REACTION/GAME/DAILY_GIFT + reference_id, reaction row, mission progress if overlaps, "credit survives later best-effort" path (the local credit still commits even if later mission or listener would "fail"). Re-run full happy + partials (e.g. credit ok, mission error → credit present; daily !success → no claim no tx; game limit reached → no credit).
- **Listener coverage (no new files/cases per tight):** exercised by (a) re-runs of credit paths (broadcast reaction unit, game play, daily claim, atomicity, besito unit) which call schedule_emit; (b) smoke/manual in F2/F3/F5: get_event_bus().register(the new observer(s)) + await bus.emit(...) + caplog or print (copy from Item1/5 F3 test_event_bus addition); (c) existing event_bus unit + story listener test (they cover the bus + one listener; the new ones are symmetric). When bot startup is exercised (smoke), all registered listeners receive.
- **Gates:** always `-p no:cov --override-ini="addopts="` for clean exit (precedent all recent phases 23/22/21/19); targeted -k first (broadcast, reaction, atomicity, cross, mission, game, daily, besitos_awarded); broader smoke at end filtered by keywords; ruff pre/post; GSD pre each.
- **ID / DESIRED CONTRACT:** in the 1-line fixes + any docstring updates, quote "credit survives later best-effort", "REACTION/GAME/DAILY_GIFT tx + history log + return", "best-effort listeners no afectan credit contracts". Use sample_user / db_session / fresh TG 7772xxxx as in the files (or per atomicity gold). N806 tolerated + doc for TestSession (exact precedent in gold).
- **Precedente --override-ini + N806 (if surfaces):** tolerate + document (atomicity gold has it for TestSession; besito unit has for TG 77728001).
- **No scope creep en tests:** only the 1-line access fixes + hasattr guards in the *existing* listed tests; re-runs protect existing + the emit contract. No new methods even if cheap. Story accesses untouched (story keeps held per precedent).
- **Cobertura logging:** not asserted in tests; gate is manual inspection during F2/F3 (listener log if added) + inclusion in GSD + re-runs of credit paths (which log "Acreditados ...").

---

## 4. Decisiones de diseño (el executor debe confirmar o registrar desviación en el primer GSD entry de la fase relevante)

1. **Nombres de listeners (si high-value decision YES):** `on_besitos_awarded_broadcast_reaction_observer` (primary, for reaction awards as high-volume source per 3 systems + potential streak/promo hooks); optional `on_besitos_awarded_game_award_observer` for game (win + streak bonuses). Confirm in F2 (broadcast) and F3 (game) first GSD; document. Bus tolerates dups but distinct preferred for ownership clarity. If only 1, prefer broadcast reactions.
2. **Cómo mantener credit atómico con local Besito:** `besito_service = BesitoService(db=self.db)` (or `db=self._get_db()` for daily) — pasa la sesión compartida; el local tendrá owns=False y su close no-op. El credit_besitos hace su propio commit (como siempre) + schedule_emit best-effort (post its commit, inside its try); el outer commit (reaction row, game record, daily claim) es idéntico. Esto replica exactamente lo que el held hacía antes (mismo db object). No usar get_service aquí (get_service es para contextos de alto nivel/handlers per 21; local directo preserva el "dentro de la tx de caller" explícito). El emit post-commit de credit sigue ocurriendo — listeners best-effort.
3. **Payload handling + logging en listener (si added):** Idéntico al de narrative/rewards (uid/amt/src/ref); log prefix "broadcast | besitos_awarded_received | ..." or "game | ...". Incluir el comentario grande "Cross-domain event listeners..." (copy from story 670-675) adaptado para el dominio + "0 impact on <domain> credit contracts / partial failure / atomicity gold".
4. **Docstring MUST NOT credit:** Copiar espíritu exacto de story + reward Item5: "It MUST NOT call back into credit/debit besitos to avoid re-entrancy with <domain> credit paths... best effort, non-authoritative." + "DESIRED CONTRACT (copy of narrative precedent)". Colocar en el def + en el bloque de comentarios.
5. **1-line fix en tests + daily guards:** Cambiar solo la(s) línea(s) de acceso (broadcast owns assert → not hasattr or guard + comment; daily direct .besito_service.get_balance → hasattr guard + direct BesitoService(db=...) or fallback with comment "# 1-line fix post ... (F5); daily precedent"; cross patch/guard sites → ensure guard + 1-line comment). Mantener todos los asserts/textos idénticos. Para el patch en cross 762 (daily_svc.besito_service): if hasattr guard around the patch, or adjust to patch the credit call site differently (1-line); property kept in daily so some paths may still see it.
6. **close() en Broadcast/Game:** Dejar el getattr("besito_service", None) tal cual (se volverá None → skip; inofensivo). No tocar el for-loop (scope tight; otros subs como mission/user/vip siguen).
7. **Daily property:** Mantenerla (para compat de tests que hacen hasattr + access o patch en algunos paths); los créditos en claim_gift usan el local. Esto es "local inside credit methods only" mientras se preserva el daily precedent de guards.
8. **Registro en bot.py (si listeners):** Después de los existentes (narrative + rewards); extender el logger.info; mantener/actualizar el comentario "Cross-domain listeners (explicit, central...) + Item 6".
9. **Actualizaciones de docs:** broadcast/CLAUDE add cross section (4-5 bullets + refs); gamification/CLAUDE append to existing Item1 section (note Item6 reductions + listeners if); missions/CLAUDE append 1-2 bullets to Item5 section; decisions.md append full Item6 entry after Item5 (exact style Motivo/Riesgos/Decisión/Resultado + "BATCH: 4 items completed in tirón"); bot reg comment if.
10. **Log file GSD:** `.planning/quick/gsd-remaining-besito-compositions.log`. Formato:
    ```
    === 2026-06-08Txx:xx:xx+00:00 | PHASE 2 | GSD pre-edit services/broadcast_service.py (F2 remove held + local in credit sites) - Agregar local BesitoService(db=self.db) en register_reaction y check_and_register_reaction; remover self.besito_service= en __init__; copiar patrón db= compartido de atomicity gold + Reward Item5 _deliver + getservice norm; refs DoD F2 + impacto analyzer (mantener atomicidad, 0 behavior chg). Listener decision: on_besitos_awarded_broadcast_reaction_observer (high-value para reactions).
    ```
    (o pre-ruff, pre-pytest -k "broadcast or reaction or atomicity", pre-grep "besito_service =", pre-final-self-check). Apuntar 5-10+ entries por fase (como precedentes 23/22/19). Al final: self-check + "BATCH: 4 items completed in this tirón (Item 6 final of max 4)".
11. **Comandos concretos:** Ver sección Instrucciones abajo. Siempre con -p no:cov + override para pytest targeted. Para smoke listener + emit (bajo loop): usa un snippet con asyncio o pytest caplog. Para batch note: echo al log en F5 self-check.
12. **Cualquier desviación:** Registrar en GSD entry de la fase + nota breve al final del PLAN o en SUMMARY. Executor confirma decisiones de nombres/1 vs 2 listeners / game test accesses en GSD de F2/F3/F5.

Cualquier decisión que difiera de lo anterior debe registrarse en el GSD log + nota breve al final del PLAN o en SUMMARY posterior.

---

## 5. Criterios de verificación + gates finales

**Criterios de éxito del Item (medibles, para self-check del executor):**
- Held composition removed: `grep -c "self\.besito_service = BesitoService" services/broadcast_service.py services/game_service.py` (active) == 0; local on-demand `BesitoService(db=self.db)` (or daily _get_db) present in the credit sites (register/check_and_register, play_*, claim_gift).
- (If listeners added): def(s) present with "MUST NOT credit" + domain log ("broadcast | ..." or "game | ..."); register call(s) + extended log in bot.py on_startup.
- 1-line fixes only: exactly the access/owns/patch lines (and minimal imports/guards) changed in the listed tests (broadcast reaction flow, daily gift unit, cross atomicity, + game if any); all relevant unit tests now pass.
- Docs: cross-domain section in broadcast/CLAUDE; append in gamification/CLAUDE; append bullets in missions/CLAUDE (Item5 section); Item6 decision entry in decisions.md (style of Item5); bot reg comment if.
- 0 behavior change: re-runs of broadcast reaction unit (reaction dict + besitos_awarded + mission best-effort identical), daily unit (claim returns + balance + claim row + cooldown identical), game unit (play returns + payout + records + streak identical), cross atomicity (REACTION/DAILY_GIFT tx present, credit survives partials, balance delta exact, guards exercised), reaction→mission chains (full flow balance/tx/mission), besito credit (emit still scheduled via patch), story (inverse credit protected) — all green with 0 regressions attributable.
- Emit still fires: patch schedule_emit asserts in at least one re-run (atomicity or besito or reaction/game/daily credit path); when registered, new listener(s) receive (smoke).
- Ruff limpio + format --check on all touched py (3 services + tests + bot if) + 4 docs (docs spot).
- Verificaciones de reglas/patrones: GSD pre every (counts 5-10+/fase, total 30+); logging format in listener if + credits; comments reference Item 6 + precedents; LOC of touched funcs preserved or <50 (no change); 0 new files (except optional SUMMARY); scope exactly as listed (no store/mission/story/reward held touched, no get_service for locals, no new tests beyond 1-lines, no handler changes).
- GSD log completo con pre-entries + self-check "PASSED" + lista explícita de "tests críticos a re-correr en el futuro para estos cambios" (broadcast reaction unit full, cross_service_atomicity full, reaction_mission_flow + full_chain + limit, daily unit + concurrent, game unit play paths, besito credit paths, story, event_bus, bot import/register smoke if listeners, the combined -k "reaction or atomicity or mission or besitos_awarded or game or daily or broadcast or TestCross...") + "Item 6/24 closed. BATCH: 4 items completed in this tirón (final of max 4). Ready for gsd-executor of next (if any) + arch-enforcer re-scan (enfocado en broadcast/game/daily composition sites + listener wiring if + 3 critical systems: gamif/missions/rewards/narrative) + test-guardian (correr los tests críticos listados)".
- Safe point final documentado; item + tirón listos para guardians + (user opt) futuro.
- Comportamiento de usuario final idéntico (reacciones con besitos, minijuegos + rachas, regalo diario, saldos, mensajes Lucien, historial, misiones por reacción).

**Gates por fase (ver secciones de fases para detalles):**
- Pre-edit: GSD log entry.
- Post-edit: ruff + targeted pytest (cuando aplique) + smoke + grep/LOC + GSD entry de resultado.
- Avanzar solo si gate verde (o documentar desviación menor).
- F5: re-runs obligatorios de golds + broader smoke filtrado + docs + self-check + batch note.

**Comando combinado sugerido para gates finales (adaptar por fase; targeted primero):**
```
./venv/bin/python -m pytest -k "TestCheckAndRegisterReaction or TestBroadcastReaction or TestDailyGift or TestGame or TestCrossServiceAtomicity or TestReactionMissionFlow or TestReactionFullChain or TestReactionLimit or reaction or atomicity or mission or besitos_awarded or game or daily or broadcast or trivia or TestReward or cross_service_atomicity" -q --tb=line -p no:cov --override-ini="addopts="
```
Para suites específicas: `pytest tests/unit/test_broadcast_service_reaction_flow.py ...` (con flags).  
Ruff: `./venv/bin/python -m ruff check services/broadcast_service.py services/game_service.py services/daily_gift_service.py tests/unit/test_broadcast_service_reaction_flow.py tests/unit/test_daily_gift_service.py tests/integration/test_cross_service_atomicity.py bot.py --fix && ./venv/bin/python -m ruff format --check ...`  
Grep rules: `grep -n "self\.besito_service = \|besito_service = BesitoService(db=\|on_besitos_awarded_broadcast\|on_besitos_awarded_game\|broadcast \| besitos_awarded_received\|game \| besitos_awarded_received\|MUST NOT credit\|Cross-domain event listeners" services/broadcast_service.py services/game_service.py services/daily_gift_service.py bot.py tests/unit/test_broadcast_service_reaction_flow.py tests/unit/test_daily_gift_service.py tests/integration/test_cross_service_atomicity.py | head -30`  
Smoke listener (if added): `python -c "
import asyncio
from services.event_bus import get_event_bus, EVENT_BESITOS_AWARDED
from services.broadcast_service import on_besitos_awarded_broadcast_reaction_observer
# (similar for game if)
bus = get_event_bus()
bus.register(EVENT_BESITOS_AWARDED, on_besitos_awarded_broadcast_reaction_observer)
print('broadcast listener registered')
# (under running loop or use caplog in pytest for the log line)
" `
Batch note (F5): `echo "=== $(date -Iseconds) | F5 | BATCH: 4 items completed in this tirón (Item 6 final of max 4). Self-Check: PASSED. Handoff to arch-enforcer/test-guardian + (user opt) future tirón." >> .planning/quick/gsd-remaining-besito-compositions.log`

---

## Instrucciones para el gsd-executor

Este PLAN.md es tu prompt de ejecución. Síguelo al pie de la letra, sin scope creep. El trabajo es para UNA persona (tú) + disciplina GSD total. Este es el **4to y final item en este tirón (max 4)**; al terminar, reportar batch completo + proponer si user quiere más en futuro (pero el prompt cubre el actual).

1. **GSD discipline (non-negotiable, como en todas las phases exitosas 23/22/21/20/19):**
   - ANTES de **cualquier** modificación (search_replace/write/edit en fuentes o log), antes de ruff, pytest, grep de verif, smoke, o resumen: append al log.
   - Log: `.planning/quick/gsd-remaining-besito-compositions.log`
   - Crea el archivo si no existe (planner ya lo tocó con 4+ líneas INIT/DISCOVERY/PLANNING/pre-write; primer entry de executor puede ser confirm + wc).
   - Formato de entry (copia estilo de gsd-reward-besito-eventbus.log / gsd-eventbus-poc-item1.log / gsd-reward-gamif-item2.log / gsd-getservice-unification.log / gsd-critical-tests.log):
     ```
     === 2026-06-08Txx:xx:xx+00:00 | PHASE 2 | GSD pre-edit services/broadcast_service.py (F2 remove held + local in credit sites) - Agregar local BesitoService(db=self.db) en register_reaction y check_and_register_reaction; remover self.besito_service= en __init__; copiar patrón db= compartido de atomicity gold + Reward Item5 _deliver_besitos + getservice norm + story listener comments; refs DoD F2 + impacto analyzer (mantener atomicidad, 0 behavior chg). Listener decision: on_besitos_awarded_broadcast_reaction_observer (high-value para reactions).
     ```
     Luego ejecuta el comando de edit/tool.
   - También pre-gate (pre-pytest, pre-ruff, pre-grep "besito_service =|on_besitos_awarded_broadcast|MUST NOT", pre-final-self-check).
   - Cuenta las entradas; apunta a 5-10+ por fase (como precedentes). Al final del Item el log debe tener el self-check completo + "BATCH: 4 items completed in this tirón".
   - Usa `run_terminal_command` con `echo "=== $(date -Iseconds) | PHASE N | ..." >> .planning/quick/gsd-remaining-besito-compositions.log` (o printf). Nunca edites sin pre-log. wc -l después de appends clave.

2. **Orden estricto:** Ejecuta Fase 1 completa (con gates) → gates F1 → Fase 2 (refactor BroadcastService; locals inside credit sites; listener decision + optional append) → gates F2 → Fase 3 (GameService locals + optional listener) → gates → Fase 4 (DailyGiftService local inside claim + guards) → gates → Fase 5 (1-line fixes + re-runs golds + docs + verif final + self-check + batch note) → gates finales. **No saltes fases ni hagas "todo de una".** Marca DoD mentalmente o en el log al completar cada checklist. Al final de cada fase documenta "F<N> safe point" en log. Al final de F5: "BATCH: 4 items completed in this tirón (Item 6 final of max 4)".

3. **Herramientas y comandos concretos (usa run_terminal_command para estos):**
   - GSD logs: `echo "=== $(date -Iseconds) | PHASE N | GSD pre-... - <desc + refs DoD + patrones copiados>" >> .planning/quick/gsd-remaining-besito-compositions.log`
   - Mkdir (si planner no lo hizo completamente): `mkdir -p .planning/phases/24-remaining-besito-compositions`
   - Ruff: `./venv/bin/python -m ruff check <file> --fix` ; luego `./venv/bin/python -m ruff format --check <file>` (o apply).
   - Pytest targeted (siempre con estos flags para exit limpio): `./venv/bin/python -m pytest <path or -k "expr"> -q --tb=line -p no:cov --override-ini="addopts="`
     - Ejemplos por fase en las secciones de gates + el combinado en "Criterios de verificación".
   - Grep de reglas/patrones: `grep -n "self\.besito_service = \|BesitoService(db=self.db)\|on_besitos_awarded_broadcast\|on_besitos_awarded_game\|broadcast \| besitos_awarded_received\|game \| besitos_awarded_received\|MUST NOT credit\|Cross-domain event listeners" services/broadcast_service.py services/game_service.py services/daily_gift_service.py bot.py tests/unit/test_broadcast_service_reaction_flow.py tests/unit/test_daily_gift_service.py tests/integration/test_cross_service_atomicity.py | head -30`
   - Smokes: `./venv/bin/python -c "from services.broadcast_service import BroadcastService; print('import ok')"; ./venv/bin/python -c "import bot; print('bot import ok')"`
   - Para smoke listener + emit (bajo loop): usa un snippet con asyncio.get_event_loop().run_until_complete o pytest caplog en un test temporal si es el camino más barato (pero scope tight → prefer el smoke simple + nota que re-runs de credit paths cubren el schedule).
   - Para contar/inspeccionar: `grep -c "def " services/xxx_service.py` o `python -c 'import inspect; ...'`.
   - Evita sleeps; usa comandos directos. Si tool soporta background para integ lentas, úsalo pero log secuencial prefer.
   - Al final F5: re-ejecuta los combinados + broader smoke filtrado por reaction/atomic/mission/besitos_awarded/game/daily/broadcast + self-check en log + batch phrase + optional SUMMARY write.
   - Para batch update: en F5 self-check append + final echo "BATCH: 4 items completed in this tirón (Item 6 final of max 4)."

4. **Patrones a copiar (no reinventar; al pie de la letra donde se indica):**
   - Listener + comment block + "MUST NOT credit" + best-effort doc: copia EXACTA de `services/story_service.py:670-694` (el bloque # Cross-domain... + async def on_besitos_awarded_from_gamification + docstring + log + final comment); adapta solo el prefijo de log ("broadcast |" or "game |" vs "narrative |"), el nombre del def (decisión F2/F3), y 2-3 frases de "broadcast/game domain" + "0 impact on <domain> credit contracts / atomicity gold / partial failure". Colócalo al final del archivo después de la clase/close si se agrega.
   - Registro central + comentario en bot.py: copia de `bot.py:200-204` (get_event_bus().register + logger.info); extiende después de los existentes (narrative + rewards); actualiza el comment "Cross-domain listeners (explicit, central...) + Item 6".
   - Local Besito with shared db para atomicity: copia espíritu de setups en `tests/integration/test_cross_service_atomicity.py` (_create... + TestSession + db=TestSession() para services que hacen commit interno) + normalización owns en 21-getservice (db= passed → owns=False); + el Reward Item5 precedent `besito_service = BesitoService(db=self.db)` dentro del método (_deliver_besitos); aquí es directo BesitoService(db=self.db) o daily _get_db() dentro del credit site (no get_service, para mantener el contexto de la tx del caller explícito).
   - Patch schedule_emit + DESIRED CONTRACT + strict asserts: copia de `tests/integration/test_cross_service_atomicity.py` (el patch en el happy path + asserts de balance/tx/source + docstring "post-credit misiones (best effort) + event listeners (best effort)") + besito unit post-Item1 + event_bus tests + reaction_mission_flow stricts.
   - 1-line test fix + comment + daily hasattr: minimal como en ports de Item5 (cambio de acceso + nota "# 1-line fix post held removal (F<N>/Item 6); was ...") + daily precedent guards (if hasattr(service, "besito_service") else BesitoService(db=...).get_balance(...) or similar fallback).
   - GSD entries detalladas con "pre-" + descripción + qué se valida después (ruff/pytest/grep) + patrones copiados + "DoD refs".
   - Safe points + self-check al final del log (estructura de Item 5/23 + 22/21/19: lista fases/DoD/gates/archivos/tests que pasaron/reglas verificadas (GSD pre every, scope tight 0 new files/0 behavior/0 atomicity/0 other composers, logging, patch, local db=, "MUST NOT", 1-line + hasattr daily, etc.)/desviaciones/tests críticos/"Item 6/24 closed. BATCH: 4 items completed in this tirón (final). Ready for ... + arch-enforcer + test-guardian").
   - Precedentes de PLAN/GSD: `.planning/phases/23-reward-besito-eventbus-decoupling/PLAN.md` (y SUMMARY + log), 22/21/20/19 PLANs + gsd logs citados.
   - Atomicity gold: `tests/integration/test_cross_service_atomicity.py` (file+TestSession, try/finally dispose/close, DESIRED, patch event, strict == on deltas/counts, "credit survives deliver False", N806 with doc, fresh TG 777x).
   - N806 tolerance with doc: copy from besito unit (TestBesitoServiceRaceCondition or similar) + atomicity gold for TestSession.

5. **Decisiones (sección 4 del PLAN):** Al inicio de la fase relevante (primer GSD entry de la fase), registra qué decidiste para nombre de listener(s), 1 vs 2, cómo estructuraste el local Besito(db=) (1 línea o con var, por método), si el import en tests fue necesario, si game tuvo accesses directos, etc. Si difieres del "preferido", explica brevemente (mantén espíritu tight + gold + 0 behavior).

6. **Gates y re-runs:** 
   - Corre los targeted pytest con los flags exactos de arriba + por-fase.
   - Si un unrelated fail preexistente aparece (ej. alembic_heads, besito lifecycle xfail, SA warnings), documéntalo en log pero **no lo cuentes como regression del Item**.
   - Re-run de atomicity gold + reaction_mission_flow + full_chain + daily concurrent + game play paths + besito credit (emit) + story inverse es obligatorio en F5 (y spot en F2/F3/F4 si relevante).
   - Siempre GSD pre- antes del pytest/ruff/grep grande.
   - Al final F5: re-ejecuta los combinados + broader smoke filtrado + self-check + batch phrase.

7. **Alcance (recuerda siempre):** Solo edita los archivos listados en "Archivos que se modificarán" + el log GSD + (este PLAN ya está) + opcional SUMMARY.md al final. Si sientes la tentación de "reducir más composiciones (store etc)", "agregar tests para el listener", "cambiar a get_service", "tocar handlers o mission_service", "editar más docs", "agregar listeners para daily", detente: scope tight para esta entrega (recomendado por analyzer: solo broadcast/game/daily para locals en credit methods; 1-2 listeners high-value si; 1-line + guards en los tests listados; docs targeted; 0 other; 4th/final in tirón). El analyzer + 23/22 handoff recomendaron empezar tight y terminar el batch aquí.

8. **Al final del Item (F5) + fin de tirón:**
   - Completa el self-check en el log (lista de fases, DoD cumplidos, archivos modificados, tests que pasaron, reglas verificadas (GSD pre every, scope tight 0/0/0/0, local db= para atomicity, "MUST NOT credit", patch schedule_emit, 1-line + hasattr daily precedent, logging, no prod change), desviaciones (si las hubo), tests críticos a re-correr en futuro (lista explícita), "Item 6/24 closed. BATCH: 4 items completed in this tirón (final of max 4). Ready for gsd-executor of next (if any) + arch-enforcer re-scan (enfocado en broadcast/game/daily composition sites + listener wiring if + 3 critical systems: gamif/missions/rewards/narrative) + test-guardian (correr los tests críticos listados)").
   - (Opcional pero recomendado) Produce `.planning/phases/24-remaining-besito-compositions/SUMMARY.md` con executive + refs al log GSD + comandos de re-verificación (sigue estructura de phases/23 o 22 o 21 o 20 o 19).
   - Confirma en log: "Self-Check: PASSED" + el batch phrase.
   - Reporta (en tu salida final o log) que el batch de 4 items en este tirón está completo; propone si user quiere más en futuro (pero no inicies sin nuevo prompt).
   - El siguiente agente (gsd-executor fin de tirón o arch-enforcer/test-guardian) usará el log + este PLAN + los cambios como fuente de verdad. Arch-enforcer re-scan enfocado en los 3 sitios reducidos + listeners if + 3 critical systems. Test-guardian: re-correr los tests críticos listados en self-check.

9. **Si algo no está claro o difiere del "reporte del analyzer":** El prompt del usuario + este PLAN (basado en discovery completa + el reporte completo descrito en el prompt + handoff explícito de 23-SUMMARY/PLAN + 22 handoff) es la fuente de verdad. Pregunta solo si un gate bloquea por ambigüedad real de nombre/firma/contrato (e.g. listener name exacto, si game test tiene access directo); de lo contrario, elige conservadoramente siguiendo precedentes (story listener copy, atomicity gold for the local db= + patch, bot reg block, 1-line minimal + daily hasattr, GSD style) y registra la elección en GSD.

**¡Ejecuta con disciplina total. Cierra el Item y el tirón de forma limpia, segura, medible y con trazabilidad GSD completa. La reducción de las composiciones held en broadcast/game/daily (vía el patrón del bus para loose coupling de notificaciones, manteniendo el command credit local para atomicity) queda hecha sin impacto en los 3 sistemas críticos ni en los contratos de crédito/partial failure. BATCH: 4 items completed in this tirón. Listo para arch-enforcer + test-guardian + (user opt) futuro.**

---

**Fin del PLAN para 24-remaining-besito-compositions (Item 6 / 4th and final in tirón).**

Referencias rápidas para el executor (actualizar con líneas reales durante ejecución si cambian):
- Impact report (source of truth): user prompt description + discovery state (broadcast_service.py:34 held + 220/283 credits + 402 getattr; game_service.py:303 held + 615/847/859/1239/1251/1590/1601 credits + 953 local has + 317 getattr; daily_gift_service.py:45-49 property + 165/173/187 claim uses; bot.py:200-204 reg + 71-74 imports (post Item5 with 2); story_service.py:670-694 listener block + 678 def; event_bus.py:23 EVENT + schedule + DESIRED; test_broadcast_reaction_flow.py:400-401 owns sub test; test_daily_gift.py:135/287-288; cross_atomicity.py:726-728/762/783 daily guards/fallbacks/patches; decisions.md Item5 entry; services/broadcast/CLAUDE.md + gamification/CLAUDE.md + missions/CLAUDE.md:90-98 Item5 cross; 23-PLAN.md + gsd-reward log; atomicity gold + reaction_mission_flow + invariants).
- Gold cross/race/atomic + patch + "best effort" note + daily guards: `tests/integration/test_cross_service_atomicity.py` + `tests/integration/test_reaction_mission_flow.py` + `tests/unit/test_broadcast_service_reaction_flow.py`.
- Story listener precedent (copy source): `services/story_service.py:670-694` (comment + on_besitos_awarded_from_gamification + "MUST NOT" + log).
- Central reg precedent: `bot.py:200-204` + imports 71-74 (extend after existing).
- EventBus + schedule_emit + DESIRED: `services/event_bus.py:23-...` (contract), schedule_emit, get.
- Reward local inside method (copy spirit): `services/reward_service.py` post-Item5 _deliver_besitos (besito_service = BesitoService(db=self.db) + comment).
- Daily hasattr precedent: tests at 288/727-728 + fallback to BesitoService(db).
- Precedentes PLAN/GSD + handoff + batch: `.planning/phases/23-reward-besito-eventbus-decoupling/PLAN.md` (y SUMMARY/log que nombra el batch/tirón context), 22/21/20/19 + gsd-*.log citados; "4 items completed in tirón" al final.
- GSD log para este Item: `.planning/quick/gsd-remaining-besito-compositions.log`
- Reglas: `CLAUDE.md`, `rules.md`, `architecture.md`, `handlers/CLAUDE.md`, `services/CLAUDE.md`, `services/missions/CLAUDE.md`, `services/gamification/CLAUDE.md`, `services/broadcast/CLAUDE.md`, `models/CLAUDE.md`, `decisions.md`.
- Next: gsd-executor para este item (F1→F5) → self-check + batch note "4 items completed in tirón" → arch-enforcer re-scan + test-guardian (re-correr críticos listados) + (user opt) futuro tirón.

Listo para gsd-executor. Ejecuta F1 → ... → F5 con GSD pre en cada paso. Self-Check: PASSED al final. Handoff explícito + "BATCH: 4 items completed in this tirón". 

**Actualización de batch (para executor en F5 self-check / final log):** BATCH: 4 items completed in this tirón (Item 6 final of max 4).