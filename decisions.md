# TECHNICAL DECISIONS

## Separación por dominios
Motivo:
- escalabilidad

Decisión:
- cada dominio tiene su propio service

---

## Estructura handlers/services
Motivo:
- claridad
- compatibilidad con LLM

Decisión:
- handlers solo enrutan
- services ejecutan lógica

---

## Uso de múltiples handlers
Problema:
- crecimiento descontrolado

Decisión:
- consolidar handlers por dominio cuando sea posible

---

## Uso de LLMs
Motivo:
- acelerar desarrollo

Reglas:
- LLM genera
- humano valida arquitectura
- tests validan comportamiento

---

## Próxima decisión pendiente

Tema:
- consolidación de handlers

Opciones:
- mantener estructura actual
- agrupar por dominio

Riesgo:
- explosión de complejidad

---

## Middleware centralization (rate limiting + idempotency) - gsd-mw-hardening (phase 2-6)

Motivo:
- Preocupaciones cross-cutting (rate limit, dedup de callbacks por reintentos de TG) estaban duplicadas o implementadas de forma frágil (manual if-dupe en 3 sitios de handlers: gamification handle_reaction + reward 2 funcs; stub en middlewares; lógica madura solo en handlers/rate_limit_middleware.py legacy).
- Violaba reglas de handlers (sin lógica), dificultaba testing central, bypass de Custodios, y orden de aplicación.
- Riesgo a sistemas críticos: reacciones con besitos (gamif), quiz narrativa (choices como cbs), gestión canales/VIP (acciones admin deben bypass rate), recompensas.

Decisión:
- Portar lógica madura (aiolimiter por usuario, ADMIN_BYPASS real desde config + lista de admins, cleanup idle, mensaje Lucien idéntico con show_alert, soporte CQ via data["event_from_user"], logging, robustez en answer) a `middlewares/rate_limiter.py` como clase `ThrottlingMiddleware` (nombre canónico) + alias `RateLimiterMiddleware`.
- Agregar `IdempotencyMiddleware(BaseMiddleware)` en `middlewares/idempotency.py` que usa el `idempotency_cache` existente para CBs (skip + answer + log + pass-through + robustness).
- Actualizar middlewares/__init__.py exports.
- Wiring en bot.py (phase 4) con orden: Error outer, Idempotency para cb, Throttling para cb; Throttling para messages. (Error cambiado a outer_middleware).
- Fase 5: remover los 3 sitios manuales de `idempotency_cache.is_duplicate` + imports en los dos handlers (ahora handlers llaman exactly 1 service, sin lógica). Actualizar tests de handlers (remover tests "skips_when_duplicate" y sus @patch; simplificar happy-paths).
- Fase 2/3: tests unit actualizados/creados y 100% verdes *antes* de wiring.
- Fase 6: header DEPRECATED fuerte en el legacy rate file, actualizar docs (handlers/CLAUDE.md, CLAUDE.md, decisions.md), grep confirmando 0 usos manuales en handlers/, verificación completa (units + smoke + integrations/smokes para reacciones, rewards, narrative quiz choices, channel/vip admin bypass, reward).
- Shim legacy rate mantiene compat temporal + warning.
- Revertir solo bot.py es safe point principal si algo rompe.

Resultado:
- Rate limiting + idempotencia ahora globales, centralizados, testeados, con bypass Custodios correcto y orden explícito.
- Handlers 100% routing (1 service call).
- Los 3 sistemas críticos protegidos sin duplicación de guards.
- Tests de mw (rate + idemp + cache) + handlers actualizados verdes.
- Traceabilidad vía commits por fase con refs "gsd-mw-hardening: phase X".

(Ver PLAN y SUMMARY en .planning/phases/08-testing-and-technical-debt/ para ejecución detallada.)

## Internal EventBus (PoC Item 1 - "besitos_awarded" primer caso de uso) - gsd eventbus-poc

Motivo:
- Necesidad de notificaciones cross-domain loose-coupled (gamif → narrative, potencialmente otros) sin violar "handlers llaman exactly 1 service", sin duplicar lógica de side-effects, y sin acoplar servicios directamente (import de story desde besito o viceversa).
- El analyzer identificó credit_besitos como el punto natural único de emisión para "awarded" (reacciones, daily, misiones, game, logros de story, admin todos pasan por ahí). Los tres sistemas críticos (gamif reactions con besitos, narrative achievements que acreditan besitos inverso, channel/VIP) dependen de la atomicidad y contratos de crédito.
- Patrón maduro ya existía en el código: `asyncio.gather(..., return_exceptions=True)` en test_broadcast_service_reaction_flow para concurrencia segura de reacciones (un "fallo" no mata las demás).
- PoC conservadora: solo un evento, un listener, emit post-commit best-effort, sin inyección (usa get/schedule para mínimo diff), sin persistencia/retry.

Riesgos (críticos):
- Romper atomicidad del crédito o los retornos de broadcast reactions (el dict con "besitos_awarded" local por emoji).
- Loops de crédito si el listener narrative volvía a acreditar.
- "besitos_awarded" confusion (nombre del event vs campo local en BroadcastReaction/reaction_result).
- Tests flaky por singleton listeners o falta de loop en schedule desde tests sync.
- Import side-effects o registro mágico.

Decisión:
- Implementar `services/event_bus.py` (InternalEventBus con register/emit async + schedule_emit helper para sync callers + get_event_bus singleton + EVENT_* const).
- Emit solo en la ruta de éxito de `credit_besitos`, inmediatamente después de `db.commit()` y **dentro** del try del crédito, wrapped en su propio try/except que solo warning + nunca rollback/return False.
- Payload estándar (user_id, amount, source str, reference_id, description, timestamp ISO).
- Helper privado en besito (`_schedule_besitos_awarded_event`) para mantener credit_besitos <=50 LOC.
- Primer listener real en narrative (`on_besitos_awarded_from_gamification` en story_service.py): solo log + prueba de wiring; ownership narrative; explícitamente prohíbe re-entrar a besitos.
- Registro explícito y central en `bot.py` on_startup (después de scheduler, antes de notificar admins). Sin auto-registro en imports de story.
- Tests: unit puro del bus (fresh instances, return_exceptions, logs, noop), patch del schedule/get en unit besito + integ atómicas, smoke de "listener narrative recibió".
- Actualizaciones mínimas de docs (gamif/narrative/services CLAUDEs + decisions) + grep de distinción "besitos_awarded" local vs event.
- No se removieron instanciaciones directas de BesitoService (scope explícito).

Resultado:
- Un crédito (cualquier source) actualiza DB atómicamente (balance + tx), procesa misiones best-effort en tx separada, y entrega el evento best-effort al listener narrative (logueado), sin que el caller del crédito se entere de fallos en listeners.
- 0 cambios en contratos de broadcast reactions (local "besitos_awarded" sigue igual).
- Handlers siguen llamando exactly 1 service (sin imports de bus).
- Bus removable (borrar event_bus.py + su test + la línea de register en bot + la def del listener + los exports = zero impacto residual).
- Gates: event_bus unit 7/7, besito 46+, reaction/atomicity/story 200+, ruff limpio, smokes de import bot y register+emit manual.
- Preparado para Item 2+ (más listeners/eventos, quizás inyección posterior) y para arch-enforcer/test-guardian (tests críticos listados en GSD log final).

(Ver .planning/phases/19-eventbus-poc/PLAN.md y gsd-eventbus-poc-item1.log para ejecución fase por fase y handoff.)

## Reduce direct BesitoService composition in RewardService via EventBus (Item 5 / post eventbus-poc) - gsd-reward-besito-eventbus-decoupling

Motivo:
- Tight, conservative follow-up to Item 1 (eventbus-poc + first narrative listener + central reg in bot) and Item 22 (critical-tests three-systems handoff that explicitly named this as next "Item 5"). Reduce *one* held direct BesitoService composition site (RewardService, the MISSION delivery composer) via the EventBus loose-coupling pattern for cross-domain *notifications* (besitos_awarded emitted post-credit commit), while keeping the *command* credit local/on-demand inside the atomic deliver flow (0 atomicity impact on MISSION tx + balance + history).
- Impact-analyzer + precedents (19/20/21/22 + gsd logs) recommended "smallest change" + "tight scope": only this composer for now (1 unit test needed 1-line fix; atomicity gold already covered the deliver besitos path + "credit survives deliver False"; 0 other composers per "0 scope creep"; 0 new files).
- Continues the "reduce direct composition" direction without breaking the 3 critical systems (gamif reactions, missions/rewards delivery, narrative achievements that inverse-credit besitos) or the partial-failure contracts protected by gold tests.

Riesgos (críticos incl atomicity + partial failure contracts):
- Atomicity of the MISSION credit inside deliver_reward (the credit's internal db.commit() + BesitoTransaction + balance update must commit even if later log_reward_delivery or best-effort listeners fail or "would fail").
- Partial failure contract from gold `test_cross_service_atomicity.py`: "credit survives deliver False" (inactive reward, package stock=0 triggering early False in _deliver_package, already-completed skip, simulated increment error post reaction credit). The local Besito(db=) must behave identically to the old held.
- Re-entrancy risk if the new rewards listener called back into credit/debit (would create loop with deliver path or future extensions; "MUST NOT credit" contract mandatory).
- 1 unit test (`test_deliver_reward_besitos`) directly accessed the removed held via `service.besito_service.get_balance` (only direct access site; all other reward tests go through deliver_reward which we fix internally first).
- Ruff/format hygiene on touched files (pre-existing style surfaced by gates); pre-existing dirty tree from prior items (we stage only our files).
- Listener coverage without new tests (rely on re-runs of credit paths + manual smoke of register+emit + existing event_bus/story tests).

Decisión:
- RewardService: remove `self.besito_service = BesitoService(self.db)` from __init__ (add detailed comments: "Held direct ... removed (Item 5 / reduce via EventBus pattern)", "BESITOS ... local on-demand ... *only* inside _deliver_besitos (preserves atomicity...)", "Package + VIP remain held (scope: other composers untouched for now)"); PackageService + VIPService held untouched.
- In `_deliver_besitos` only (the sole BESITOS credit site): `besito_service = BesitoService(db=self.db)` local on-demand (shares self.db so owns=False, close no-op; credit does its own internal commit + schedule_emit best-effort exactly as the held did; get_balance after uses the local; docstring updated " (local BesitoService on-demand with shared db for atomicity)").
- close() body left verbatim (the getattr("besito_service", None) becomes None → if sub: skips; harmless; no code change per "scope tight").
- Add at bottom of reward_service.py (after close): full "Cross-domain event listeners" comment block + async `on_besitos_awarded_rewards_observer(payload: dict) -> None` (exact copy of story_service.py:670-694 structure, comment, docstring, log format, final comment; adapted only for "rewards domain ownership", "rewards | besitos_awarded_received", "no re-entrancy risk with deliver paths", "0 impact on deliver_reward contracts / partial failure"; "MUST NOT call back into credit/debit besitos"; "DESIRED CONTRACT (copy of narrative precedent)"; "purely observational + wiring proof"; "Future extensions ... use get_service(RewardService) or direct models"; name chosen in first F3 GSD for domain clarity vs narrative's "from_gamification"; bus tolerates dups but distinct preferred).
- bot.py: add `from services.reward_service import on_besitos_awarded_rewards_observer`; after the narrative register line add the rewards register; extend the logger.info to "(besitos_awarded -> narrative, rewards)"; update the preceding comment to "Fase 3 of eventbus-poc + Item 5: narrative + rewards domains." (explicit, central, no import side-effects).
- tests/unit/test_reward_service.py: exactly 1 line change in `test_deliver_reward_besitos` (the balance access at the site) to `BesitoService(db=db_session).get_balance(sample_user.id)  # 1-line fix post held removal (F4); was service.besito_service`; minimal companion import `from services.besito_service import BesitoService` (counted as part of the 1-line delta per tight scope/impact). No other test changes, no new tests/cases (coverage via re-runs of paths that call credit + smoke of register + existing event_bus tests).
- Docs (minimal): add "Cross-domain notifications (EventBus)" section at end of services/missions/CLAUDE.md (4-5 bullets + refs to event_bus, decisions, PLAN, gold); append this decision entry after the Item 1 eventbus one in decisions.md (exact Motivo/Riesgos/Decisión/Resultado style + refs).
- Gates: ruff limpio + format on the 3 py (with hygiene commits where needed); targeted pytest with exact flags `-q --tb=line -p no:cov --override-ini="addopts="` (reward unit full post-fix, cross atomicity gold full with its patch schedule_emit + DESIRED + TestSession + strict == + "credit survives deliver False" + "post-credit best effort" in doc, story+besito re-runs, broader -k "reward or deliver... or besitos_awarded or atomicity"); greps per PLAN for 0 held, local present, listener block + MUST NOT + "rewards |", register + extended log, 1-line comment, docs sections; smokes (import bot, manual register+emit, python -c); GSD pre *every* (edits, ruff, pytest, grep, smoke, self-check) with counts 5-10+/phase; self-check PASSED in log with full structure.
- 0 new files, 0 prod behavior change (deliver_reward for BESITOS/PACKAGE/VIP returns identical success/msg/balance/history/tx source MISSION + ref=reward.id, LucienVoice strings), 0 atomicity impact (gold re-runs in F2/F4 + patch confirm emit still scheduled from the local credit), 0 other composers touched, 0 logic in handlers, 0 change to close body or other _deliver_*/CRUD.

Resultado:
- Held removed for this site: grep -c "self\.besito_service = BesitoService" active in reward_service.py == 0; local on-demand BesitoService(db=self.db) present in _deliver_besitos.
- Listener + wiring: def present with "MUST NOT credit" + "rewards | besitos_awarded_received" + best-effort doc; register call + extended log in bot.py; both narrative + rewards receive on emit when registered.
- 1-line fix only: access line (and import) changed in the one test; all reward unit tests now pass (17/17).
- Docs present: cross-domain section in missions/CLAUDE.md; decision entry in decisions.md (style of Item1).
- 0 behavior change: re-runs of reward unit (deliver besitos returns exact same msg + balance), cross atomicity (MISSION tx present, credit survives deliver=False, balance delta exact, "besitos_awarded" local unchanged), mission/reward flows — all green with 0 regressions attributable to this Item.
- Emit still fires: patch schedule_emit asserts executed in atomicity happy path re-runs (F2 spot + F4); when registered, both listeners receive (F3/F5 smokes).
- Ruff limpio + format --check on the 3 py (reward_service.py, bot.py, test) + 2 docs (spot); GSD pre every (counts 45+ total entries across F1-F5); logging in listener + comments; LOC of touched funcs preserved or <50; 0 new files; scope exactly as listed in PLAN (no broadcast/game/daily touched, no get_service migration for the local, no new tests beyond the 1-line, no handler changes).
- GSD log completo with pre-entries + self-check "PASSED" + lista explícita de "tests críticos a re-correr en el futuro" (reward unit full, cross_service_atomicity full, -k "reward or deliver or TestRewardServiceDelivery or TestCrossServiceAtomicity or mission or besitos_awarded or atomicity", story, besito credit, bot import/register smoke, the combined) + "Item 5/23 closed. Ready for gsd-executor of next batch item (if any) + arch-enforcer re-scan (enfocado en reward composition sites + listener wiring + 3 critical systems: gamif/missions/rewards/narrative) + test-guardian (correr los tests críticos listados)".
- Commits (per protocol, individual after each phase/tarea): F1 chore (test ruff hygiene from baseline gate), F2 feat (reward reduce + local), F3 feat (listener + central reg), F4 test (1-line + import), F4 chore (format hygiene post 1-line), F5 (docs appends + final hygiene if any). All with GSD refs + "0 behavior/0 atomicity".
- Safe point final + criterio de éxito: todos DoD F5 + self-check PASSED en log. Comportamiento de usuario final idéntico (reclamo de recompensas MISSION con besitos, saldos, mensajes Lucien, historial). Los 3 sistemas críticos (gamif, missions/rewards, narrative) protegidos; held composition reduced for this site following the bus loose-coupling precedent safely. Item listo para siguiente en batch (si aplica) y guardians.

(Ver .planning/phases/23-reward-besito-eventbus-decoupling/PLAN.md + gsd-reward-besito-eventbus.log (full GSD + self-check PASSED + critical tests list) + commits for execution details + handoff.)

## Unify/reduce remaining direct BesitoService compositions in broadcast/game/daily (Item 6 / 4th and final in tirón, max 4) - gsd-remaining-besito-compositions

Motivo:
- Tight, conservative, phased reduction of *held direct compositions* (and lazy property usage for credits) of BesitoService inside the three core high-volume gamification composers: BroadcastService (reactions), GameService (minijuegos + streaks), DailyGiftService (daily claim). Per impact-analyzer recs + precedents (Reward Item5/23: held→local inside _deliver_besitos only + obs listener + central reg + 1-line test; Story: held retained + listener; EventBus: post-commit best-effort via schedule_emit + gather return_exceptions; atomicity golds in test_cross_service_atomicity + reaction_mission_flow + invariants).
- Use **local on-demand `BesitoService(db=self.db)` (or `db=self._get_db()` for daily) *only inside the credit/debit call sites*** (the methods/blocks that perform credit_besitos or debit). This preserves 100% atomicity/tx control of the caller's tx (reaction INSERT + credit internal commit + mission best-effort; game record + credits; daily claim + credit; all as before).
- Remove the `__init__` held for broadcast/game; for daily (which already avoids __init__ held via lazy property), use local inside `claim_gift` credit block only. Add 1-2 *observational* EventBus listeners if high-value for domain (post-award reactions in broadcast for potential streak/promo hooks; post-award game for streaks/promo/analytics) with "MUST NOT credit/debit" contract + best-effort doc (copy story_service.py:670-694 structure). Central explicit registration in bot.py on_startup (extend the existing cross-domain block).
- Exactly the 1-line test fixes (or minimal + hasattr guards per daily precedent) in the specific tests that access .besito_service (test_broadcast_service_reaction_flow.py:401 owns assert; test_daily_gift_service.py:135 and the concurrent 287; cross_service_atomicity.py daily patches/guards at 726/762).
- Targeted docs updates ONLY in `services/broadcast/CLAUDE.md`, `services/gamification/CLAUDE.md` (cross notes), `services/missions/CLAUDE.md` (append to Item5), `decisions.md` (this entry). 0 prod behavior change, 0 atomicity impact, 0 other composers (store/mission etc out), 4th/final in tirón (max 4 per user "máximo 4").

Riesgos (críticos incl atomicity + partial failure contracts):
- Atomicity of the REACTION/GAME/TRIVIA/DAILY_GIFT credits inside the composers (the credit's internal db.commit() + BesitoTransaction + balance update must commit even if later mission best-effort or best-effort listeners "fail").
- Partial failure contract from golds `test_cross_service_atomicity.py` + `test_reaction_mission_flow.py` + `test_reaction_full_chain.py`: "credit survives deliver False" (and reaction credit + mission progress survive even if later deliver fails); "post-credit misiones (best effort) + event listeners (best effort)". The local Besito(db=) must behave identically to the old held.
- Re-entrancy risk if the new listeners (broadcast/game) called back into credit/debit (would create loop with reaction/game credit paths; "MUST NOT credit" contract mandatory in listener docs + comments).
- 1-3 unit/integration tests directly accessed the removed held (broadcast owns sub test, daily claim success direct + concurrent guard, cross daily patch sites); exactly 1-line fixes + hasattr guards per daily precedent (no new tests/cases).
- Ruff/format hygiene on touched files (pre-existing style surfaced by gates); pre-existing dirty tree + unrelated fails (e.g. daily concurrent UNIQUE, some cross daily !success path pre F5 fix) from prior items (document, do not count as regression; use targeted -k + flags -p no:cov --override-ini="addopts=").
- Listener coverage without new tests (rely on re-runs of credit paths + manual smoke of register+emit + existing event_bus/story tests; schedule_emit exercised by golds).
- N806 tolerance for TestSession in atomicity gold (precedent); fresh TG 777x for ID contract in tests.

Decisión:
- BroadcastService: remove `self.besito_service = BesitoService(self.db)` from __init__ (add detailed comments: "Held direct ... removed (Item 6 / remaining composers unification)", "REACTION credits now use local on-demand BesitoService(db=self.db) *only* inside register_reaction / check_and_register_reaction (preserves atomicity...)"; other composers handled in their phases; scope tight). In the two credit sites only (`register_reaction` ~220 and `check_and_register_reaction` ~283, the atomic gold path): create local on-demand `besito_service = BesitoService(db=self.db)` right before the credit_besitos call (shares session so credit's internal FOR UPDATE/lock + commit + schedule_emit best-effort stay in context with the caller's reaction tx; the outer db.commit() after remains for the reaction row). close() getattr list for "besito_service" stays as-is (getattr returns None → if sub: skips; harmless; no code change).
- GameService: remove held from __init__ (mirroring comments; the has_sufficient local at ~953 for claim_for_streak_protection remains or consistent style). In the play_* methods that credit (play_dice_game ~615, play_trivia_game ~847+859 for win+streak bonus, play_vip_trivia_game ~1239+1251, play_simple_trivia_game ~1590+1601): create local on-demand `besito_service = BesitoService(db=self.db)` before the credit call(s) in each block (re-use the local for the 1-2 credits per method if both win + bonus). close() getattr stays (becomes None for besito; harmless).
- DailyGiftService: no __init__ held (already uses lazy @property besito_service at 45-49 creating BesitoService(self._get_db())). In `claim_gift` only (the credit site, lines ~165/173/187 for the credit + get_balance after success): create local on-demand `besito_service = BesitoService(db=self._get_db())` for those calls (instead of `self.besito_service`). Keep the @property (for test compat + hasattr guards precedent; it can still be accessed by tests for balance asserts or patching in some paths, while the actual credit command uses the local inside the method). close() and __del__ untouched (never touched besito sub).
- 1-2 observational EventBus listeners (high-value for domain): add at module bottom of broadcast_service.py (and game_service.py) the domain observational listener(s) (async def, e.g. `on_besitos_awarded_broadcast_reaction_observer` for broadcast; `on_besitos_awarded_game_award_observer` for game). Full "Cross-domain event listeners" comment block + docstring with "MUST NOT credit/debit besitos", "best effort, non-authoritative", "domain ownership", "use get_service if future needs DB", log format "broadcast | besitos_awarded_received | ..." (or "game | ..."). No side effects that mutate besitos or call credit. Decision logged in first GSD of F2 (broadcast primary, high-value for reactions per 3 critical systems + potential streak/promo) and F3 (game for win+streak); 2 total. If added, central reg follows.
- bot.py: extend the cross-domain listeners block (after scheduler, after the existing narrative + rewards registers from Item5; add import(s) + register call(s) + extend the logger.info line). Explicit, central, no import side-effects. Comment updated (e.g. "Fase 3 of eventbus-poc + Item 5 + Item 6: narrative + rewards + broadcast + game domains.").
- 1-line test fixes + hasattr guards (daily precedent; no new tests/cases): `tests/unit/test_broadcast_service_reaction_flow.py`: exactly 1 line change in `test_composer_sub_closes_are_harmless_for_passed_db` (the `assert hasattr(svc, "besito_service")` + owns assert at ~400-401) to a guard or "not present" reality post-removal (e.g. `assert not hasattr(svc, "besito_service") or svc.besito_service is None  # 1-line fix post held removal (F5/Item 6); was asserting on composer sub`); or equivalent minimal. `tests/unit/test_daily_gift_service.py`: 1-line adjustments at 135 (direct .besito_service.get_balance in claim success) and/or the concurrent path 287 (already has hasattr guard at 288; ensure fallback or direct BesitoService(db) style); add comment "# 1-line fix post local-in-claim (F5); daily precedent guard preserved". `tests/integration/test_cross_service_atomicity.py`: 1-line or guard at 726 (daily_svc.besito_service.get_balance with hasattr at 727-728 already present → keep/ensure + comment); at 762 (patch.object(daily_svc.besito_service, "credit_besitos"...) → adjust to hasattr guard or patch after property access or use a direct local mock strategy with 1-line comment); 783 already uses direct BesitoService(db) fallback. Game tests: F1 baseline grep found 0 direct `svc.besito_service` or `game.besito_service` accesses in unit/integ → 0 1-line for game tests. 0 new test files/cases (coverage for new listeners via re-runs of credit paths + smoke of register+emit + existing event_bus/story tests).
- Docs (minimal, cross-domain + targeted): `services/broadcast/CLAUDE.md`: Add short "Cross-domain notifications (EventBus)" section at end (modeled on gamification/CLAUDE + missions/CLAUDE Item5) documenting the reduced composition in BroadcastService, the broadcast listener, best-effort contract, "MUST NOT credit", refs to event_bus + decisions + this PLAN/log + gold atomicity/reaction. `services/gamification/CLAUDE.md`: Append/update the existing "Cross-domain notifications (EventBus PoC Item 1)" section with note on Item 6 reductions in broadcast/game/daily (locals inside credit methods only; 1-2 new obs listeners if high-value for game/broadcast awards; 0 atomicity impact; refs). `services/missions/CLAUDE.md`: Append 1-2 bullets to the existing "Cross-domain notifications (EventBus) (Item 5 ...)" section (or new sub) noting the continuation for the remaining core composers (broadcast/game/daily), locals for atomic credits, optional high-value listeners, 0 other services touched, refs to this PLAN + 23-PLAN. `decisions.md`: Append this full Item 6 decision entry after the Item 5 entry (exact style Motivo/Riesgos/Decisión/Resultado + refs to this PLAN + log + "BATCH: 4 items completed in tirón"). `bot.py` (listeners): extend the reg comment to reference Item 6.
- Gates + re-runs (protect 0 regression + atomicity gold + listener wiring + reaction/mission chains): Targeted re-runs of: broadcast reaction unit (TestCheckAndRegisterReaction + composer close/lifecycle), `test_cross_service_atomicity.py` (gold: happy REACTION credit path + "credit survives" partials + patch schedule_emit + note post-credit best-effort sides + daily atomic with guards), `test_reaction_mission_flow.py` + `test_reaction_full_chain.py` + `test_reaction_limit.py` (full chains reaction→credit→mission→besitos), game unit (play dice/trivia paths), daily unit (claim + concurrent), besito credit (emit still fires), story (protects inverse credit in _grant), event_bus (if listener coverage extended cheaply without new files), broader smoke filtered by reaction/atomic/mission/besitos_awarded/game/daily. Patch schedule_emit + DESIRED CONTRACT style where verifying emit (as in atomicity gold + Item1/5). 0 new test files/cases (coverage for listeners comes from re-runs of paths that exercise credit inside broadcast/game/daily + existing event_bus/story listener tests + manual smoke of register+emit). Always with flags `-q --tb=line -p no:cov --override-ini="addopts="`; N806 tolerated + doc for TestSession (exact precedent in gold); fresh TG 777x or sample_user for ID contract.
- Behavior/contracts: All credit paths (REACTION via check_and_register_reaction, GAME via play_*, DAILY_GIFT via claim_gift, plus any internal) return identical (bool success, dicts with besitos_awarded, Lucien msgs, balances, history tx with correct source + ref). The event is still emitted (best-effort) on every credit including these; if new listeners, they receive when registered. No user-visible or admin-visible change. Partial failure contracts (credit tx commits even if later mission best-effort or listeners "fail") protected by golds.
- Artefacts: This PLAN.md + GSD entries (pre every) in the dedicated log + (optional post-exec) SUMMARY.md. Batch note "4 items completed in tirón" at F5 self-check + log.

Resultado:
- Held composition removed: `grep -c "self\.besito_service = BesitoService" services/broadcast_service.py services/game_service.py` (active) == 0; local on-demand `BesitoService(db=self.db)` (or daily _get_db) present in the credit sites (register/check_and_register, play_*, claim_gift).
- (Listeners added): def(s) present with "MUST NOT credit" + domain log ("broadcast | ..." + "game | ..."); register call(s) + extended log in bot.py on_startup (4 total).
- 1-line fixes only: exactly the access/owns/patch lines (and minimal imports/guards) changed in the listed tests (broadcast reaction flow, daily gift unit, cross atomicity); all relevant unit tests now pass (broadcast owns sub test reflects no held; daily/cross use guards or direct Besito(db) with comments).
- Docs present: cross-domain section in broadcast/CLAUDE; append in gamification/CLAUDE; append bullets in missions/CLAUDE (Item5 section); Item6 decision entry in decisions.md (style of Item5); bot reg comment updated.
- 0 behavior change: re-runs of broadcast reaction unit (reaction dict + besitos_awarded + mission best-effort identical), daily unit (claim returns + balance + claim row + cooldown identical), game unit (play returns + payout + records + streak identical), cross atomicity (REACTION/DAILY_GIFT tx present, credit survives partials, balance delta exact, guards exercised), reaction→mission chains (full flow balance/tx/mission), besito credit (emit still scheduled via patch), story (inverse credit protected) — all green with 0 regressions attributable.
- Emit still fires: patch schedule_emit asserts executed in at least the atomicity happy + reaction/game/daily credit paths re-runs (verified emit still scheduled from the local credits); when registered, new listener(s) receive (smoke).
- Ruff limpio + format --check on all touched py (3 services + tests + bot) + 4 docs (docs spot).
- Verificaciones de reglas/patrones: GSD pre every (counts 5-10+/fase, total 40+); logging format in listener if + credits; comments reference Item 6 + precedents; LOC of touched funcs preserved or <50 (no change); 0 new files (except optional SUMMARY); scope exactly as listed (no store/mission/story/reward held touched, no get_service for locals, no new tests beyond 1-lines, no handler changes).
- GSD log completo with pre-entries + self-check "PASSED" + lista explícita de "tests críticos a re-correr en el futuro" (broadcast reaction unit full, cross_service_atomicity full, reaction_mission_flow + full_chain + limit, daily unit + concurrent, game unit play paths, besito credit paths, story, event_bus, bot import/register smoke if listeners, the combined -k "reaction or atomicity or mission or besitos_awarded or game or daily or broadcast or TestCross...") + "Item 6/24 closed. BATCH: 4 items completed in this tirón (final of max 4). Ready for gsd-executor of next (if any) + arch-enforcer re-scan (enfocado en broadcast/game/daily composition sites + listener wiring if + 3 critical systems: gamif/missions/rewards/narrative) + test-guardian (correr los tests críticos listados)".
- Safe point final + criterio de éxito: todos DoD F5 + self-check PASSED en log with batch note. Comportamiento de usuario final idéntico (reacciones con besitos, minijuegos + rachas, regalo diario, saldos, mensajes Lucien, historial, misiones por reacción). Los 3 sistemas críticos (gamif, missions/rewards, narrative) protegidos; held compositions reduced for these 3 core sites following the bus loose-coupling precedent safely. Item + tirón listos para guardians + (user opt) futuro.

(Ver .planning/phases/24-remaining-besito-compositions/PLAN.md + gsd-remaining-besito-compositions.log (full GSD + self-check PASSED + critical tests list + BATCH note) + commits for execution details + handoff to arch-enforcer/test-guardian + re-scan focused on the 3 sites + 3 systems.)
