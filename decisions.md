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

## Reduce direct BesitoService composition in StoreService (debits in complete_order / balance checks in purchase flows) (Item 10 / second of new pool of 4, automatic continuation after Item 9 closed full 6-step + "suite protege adecuadamente" + tests green + documentador just updated HARDENING_ROADMAP) - gsd-remaining-besito-store

Motivo:
- Tight, conservative, phased reduction of *held direct composition* of BesitoService inside StoreService (the PURCHASE debit/balance composer for content buys). Per impact-analyzer recs + precedents (Reward Item5/23: held→local inside _deliver_besitos only + obs listener + central reg + 1-line test + DESIRED; Item6 broadcast/game/daily: locals in credit sites + 2 obs + "MUST NOT" + DESIRED + central reg 4 total + 1-line guards in cross/daily + property kept for daily; atomicity golds in test_cross_service_atomicity): use **local on-demand `BesitoService(db=self.db)` *only inside the debit/balance call sites*** (the methods/blocks that perform debit_besitos or get_balance for pre-purchase checks: complete_order ~493 debit + rechecks ~488, direct_purchase ~366, create_order ~440). This preserves 100% atomicity/tx control of the caller's tx (besito debit internal commit + PURCHASE tx source + history + order/stock/deliver outer commit all as before).
- Remove the `__init__` / _init_services held `self.besito_service = BesitoService(db)`. PackageService held remains untouched. close() untouched (store never closed subs; getattr not present). Add one high-value *observational* EventBus listener `on_besitos_awarded_store_observer` (copy story_service.py:670-694 + reward/broadcast expanded templates: "Cross-domain event listeners" block + "MUST NOT credit/debit/mutate" + best-effort + DESIRED CONTRACT + log "store | besitos_awarded_received"; purely observational, 0 mutation, 0 re-entrancy risk with purchase debit paths; high-value for domain wiring + future even if current purchases are debits). Central explicit registration in bot.py on_startup (extend the cross-domain listeners block after Item6 narrative+rewards+broadcast+game; add import + register call + extend logger.info + comment "+ Item 10 store"). Exactly the 1-line/guard test ports (hasattr guards or class patch to services.besito_service.BesitoService for local intercept; "if hasattr... else BesitoService(db=...)"; new contract tests for no-held/uses_local/observer if fits tight). Targeted docs/CLAUDEs if precedent (gamif/store/missions cross + decisions Item10 entry after Item6). 0 behavior/0 atomicity change ("credit survives deliver False", "post-credit best effort (misiones + listeners)", tx counts/deltas strict in golds). "Item 10 SECOND of NEW pool of 4; automatic continuation after Item 9 (mission_admin) closed via full 6-step"; "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."
- Refs: impact10 report (exec summary + risks low + tight scope + exact design notes for locals + observer + 1-line ports + DESIRED CONTRACT + critical tests list + "second of new pool of 4" + pool phrase), .planning/phases/28-remaining-besito-store/PLAN.md (source of truth, 5 phases, DoD, "Copia patrones al pie de la letra", self-check structure, handoff), 23/24 PLAN/SUMMARY/gsd (Item5 local inside _deliver + observer + reg + 1-line test + DESIRED; Item6 locals in credit sites + 2 obs + "MUST NOT" + daily hasattr guards + BATCH/pool phrase), 25/26/27 SUMMARIES (pool phrase + "first/second of new pool" language + self-check + handoff "Item X/2X closed. Nth of new pool of 4. Previous batch of 4 ... closed with tests passing per 24-SUMMARY BATCH note + self-check PASSED. Ready for arch-enforcer re-scan (...) + test-guardian (...) + gsd-executor del siguiente item del pool de 4."), gold `tests/integration/test_cross_service_atomicity.py` (guards, patch schedule_emit, TestSession/file, 777, gather, DESIRED, "credit survives deliver False", "post-credit best effort (misiones + listeners)", strict tx/deltas), current sources (store_service.py focus _init/3 purchase methods, bot.py reg block, 2 tests).

Riesgos (críticos incl atomicity + partial failure contracts):
- Atomicity of the PURCHASE debit in complete_order (the debit\'s internal with_for_update + (default commit=True) + BesitoTransaction + balance update must commit even if later stock/deliver or best-effort listeners "fail"; "debit internal commit authoritative").
- Partial failure contract from golds `test_cross_service_atomicity.py`: "credit survives deliver False" + "post-credit best effort (misiones + listeners)" (protected even for debit analog "spend survives later failure" by re-runs of complete_order paths + cross; store unit asserts debit tx + balance delta strict).
- Re-entrancy risk if the new store listener called back into credit/debit (would create loop with any future store credit paths or purchase debit; "MUST NOT credit/debit/mutate" contract mandatory in listener docs + comments + "0 impact on purchase debit contracts / atomicity gold").
- 1-2 tests directly accessed the removed held (store unit test_complete_order_success ~134 `service.besito_service.get_balance` + setup in other complete tests); exactly 1-line/guard ports + class patch for local intercept per daily precedent (no new tests/cases).
- Ruff/format hygiene on touched files (pre-existing style surfaced by gates); pre-existing dirty tree + unrelated fails (e.g. N806 in cross gold for TestSession, SA warnings, Runtime emit not awaited, daily concurrent UNIQUE, cross daily !success pre patches in priors) from prior items (document, do not count as regression; use targeted -k + flags -p no:cov --override-ini="addopts=").
- Listener coverage without new tests (rely on re-runs of credit paths which schedule + manual smoke of register+emit + existing event_bus/story/reward/broadcast listener tests; schedule_emit exercised by golds).
- N806 tolerance for TestSession in atomicity gold (precedent); fresh TG 777x for ID contract in tests; TestSession/file + try/finally + gather return_exceptions.
- Store purchase tx independence: complete_order debit commit independent of later stock/deliver/order COMPLETE commit (precedent in daily claim + credit internal; cross tests validate).
- Observer for debit path: Purchases debit (no "awarded"), but observer still high-value for domain (wiring + future credits in store?); "store | besitos_awarded_received" log exact; name "on_besitos_awarded_store_observer" per impact.

Decisión:
- StoreService: remove `self.besito_service = BesitoService(db)` from _init_services (add detailed comments per PLAN: "Held direct BesitoService composition removed (Item 10 / remaining store debits unification)", "PURCHASE debits/balance checks now use local on-demand BesitoService(db=self.db) *only* inside the balance/debit sites in direct_purchase / create_order / complete_order (preserves atomicity: debit's internal commit + PURCHASE tx + order/stock/deliver all unchanged; best-effort schedule_emit still fires post-credit commit if any credit path). PackageService remains held (scope: other composers untouched per Item 10 tight). # self.besito_service = ... REMOVED"). In the sites ONLY (copy Reward Item5 _deliver + bcast/game Item6 credit sites exactly; use self.db from _get_db pattern; add db.commit() after local if needed for caller visibility per daily/credit precedent):
  - direct_purchase (~366 get_balance pre-purchase): `besito_service = BesitoService(db=self.db)  # local, on-demand; owns=False (db shared); balance check for atomic pre-purchase` ; balance = besito_service.get_balance(user_id) ; if < return insufficient (no schedule; outer order commit unchanged).
  - create_order (~440 get_balance for carrito total): analogous local + comment for pre-purchase balance check on total_price.
  - complete_order (~488 recheck + ~493 debit): `besito_service = BesitoService(db=self.db)  # local, on-demand; owns=False (db shared); recheck for atomicity with debit` ; balance = ... ; then success = besito_service.debit_besitos( user_id=..., amount=..., source=TransactionSource.PURCHASE, description=f"Compra en tienda - Orden #{order.id}", reference_id=order.id, ) ; comment after "# (no schedule for debit; debit internal commit authoritative; outer stock/deliver/order COMPLETE + db.commit() unchanged)".
- close() left verbatim (store close only does owns_session + db close; never closed subs; no getattr besito list; harmless).
- 1 high-value observational EventBus listener (high-value for domain per impact/PLAN F2 decision YES): append at module bottom of store_service.py (after last method) the store-domain observational listener (async def `on_besitos_awarded_store_observer(payload: dict) -> None`). Full "Cross-domain event listeners" comment block (adapt for store + purchase debit paths + "0 impact on purchase debit contracts / atomicity gold / partial failure") + docstring with "MUST NOT credit, debit, or mutate besitos state here", "DESIRED CONTRACT (copy of narrative precedent + Reward Item5 + broadcast Item6)", "observational best-effort for store domain", "no re-entrancy risk with purchase debit paths", log format "store | besitos_awarded_received | user_id={uid} | amount={amt} | source={src} | ref={ref}". No side effects that mutate besitos or call credit/debit. Arch comment "Item 10 / remaining store besito / arch-enforcer". Decision logged in F2 first GSD.
- bot.py: extend the cross-domain listeners block (after scheduler, after the existing narrative + rewards + broadcast + game registers from Item5/6; add import `from services.store_service import on_besitos_awarded_store_observer` + register call after game + extend the logger.info line to include ", store"). Explicit, central, no import side-effects. Comment updated (e.g. "Fase 3 of eventbus-poc + Item 5 + Item 6 + Item 10 store: narrative + rewards + broadcast + game + store domains.").
- 1-line/guard test ports only (no new tests/cases, no new test files): `tests/integration/test_cross_service_atomicity.py`: 1-line or guard around any store balance if emerges in store purchase atomic paths; `with patch("services.event_bus.schedule_emit") as mock_sched:` reuse in store paths if added; class patch like `with patch("services.besito_service.BesitoService") as mock_besito_cls:` or .debit_besitos for local creation/intercept in atomicity tests exercising complete_order (or direct/create balance checks); optional "new contract tests for no-held/uses_local/observer if fits tight" (e.g. assert no hasattr(store_svc, 'besito_service') post init; or manual emit + listener received log "store |"); keep exact asserts on deltas/tx/source=PURCHASE/"credit survives"/DESIRED strings/patch schedule_emit; docstrings update "1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer)"; N806 tol w/doc for TestSession; fresh TG 777x if new; TestSession/file + try/finally raw close+dispose; gather return_exceptions.
  - `tests/unit/test_store_service.py`: 1-line port for `service.besito_service.get_balance` post-complete (e.g. `bal = BesitoService(db=db_session).get_balance(...) if not hasattr(service, "besito_service") else service.besito_service.get_balance(...)  # 1-line/guard port post Item10 local (copy daily precedent in cross); was service.besito_service` + import if needed; or simpler independent since post-remove); add comment "# 1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer)"; keep exact asserts on deltas/tx/source=PURCHASE.
- Docs (minimal, cross-domain + targeted if precedent): `services/gamification/CLAUDE.md` (or services/store/CLAUDE.md): Append/update the existing "Cross-domain notifications (EventBus PoC Item 1)" / Item6 section with note on Item 10 reduction in StoreService (locals inside the exact debit/balance sites in complete_order/direct_purchase/create_order only; high-value obs listener on_besitos_awarded_store_observer "MUST NOT" + "store | ..." + DESIRED + central reg + Item 10; 0 behavior/0 atomicity (golds... "credit survives" + "post-credit best effort" protected)); refs to this PLAN + impact + gsd log + atomicity gold + 23/24 precedents. `services/missions/CLAUDE.md`: Append 1 bullet to the existing "Cross-domain notifications (EventBus) (Item 5 ...)" section (or new sub) noting the continuation for the remaining store purchase composer (locals for atomic debits + history + PURCHASE source, optional high-value listener, 0 other services/files touched per tight, refs to this PLAN + 23/24-PLAN + impact). `decisions.md`: Append new decision entry "## Reduce direct BesitoService composition in StoreService (debits in complete_order / balance checks in purchase flows) (Item 10 / second of new pool of 4)" following the exact style/structure of the Item 5/6 entries (Motivo, Riesgos (críticos incl atomicity + partial failure contracts from golds + re-entrancy if listener credited + "credit survives" for debit analog), Decisión (locals inside the exact debit/balance sites ONLY for the 3 purchase methods + high-value obs listener "MUST NOT" + DESIRED + "store | ..." + central reg in bot.py with "+ Item 10 store" + 1-line/guard ports in cross + store unit + targeted docs if precedent), Resultado (0 behavior/0 atomicity change, held removed for this composer, listener wired if, gates, handoff, pool "second of new pool of 4")). `bot.py` (if listener): extend the reg comment to reference "+ Item 10 store".
- Gates + re-runs (protect 0 regression + atomicity gold + listener wiring + purchase/atomicity contracts): Targeted re-runs of: `tests/integration/test_cross_service_atomicity.py` (gold full happy + sad/partials with patch("services.event_bus.schedule_emit") + strict + DESIRED + "credit survives deliver False" + "post-credit best effort (misiones + listeners)" + TestSession/file + 777 TG + gather + N806 tol w/doc; extend for store purchase atomic if contract test added; guards exercised); broader `pytest -k "store or purchase or complete_order or atomicity or besitos or TestStoreService" -q --tb=line -p no:cov --override-ini="addopts="` (broader gamif/store flows + unit store ports); bot smoke: manual reg+emit for new listener (python -c or in test); unit store targeted `pytest tests/unit/test_store_service.py::TestStoreService::test_complete_order_success -q --tb=line`; ruff on touched; greps (post edit, in GSD): `grep -n "local, on-demand" services/store_service.py` ; `grep -c "self\.besito_service = BesitoService" services/store_service.py` (expect 0); `grep -A20 -E "on_besitos_awarded_store|store \| besitos_awarded_received|MUST NOT credit" services/store_service.py` ; `grep -n "Item 10 store" bot.py` ; `grep -n "1-line/guard port post Item10|hasattr.*besito_service" tests/...` ; `grep -n "store | besitos" services/gamification/CLAUDE.md decisions.md` etc. Patch schedule_emit + DESIRED CONTRACT style where verifying emit (as in atomicity gold + Item1/5/6). 0 new test files/cases (coverage for listener via re-runs of credit paths (any) + smoke of register+emit + existing event_bus/story/reward/broadcast listener tests).
- Behavior/contracts: All purchase paths (direct_purchase, create_order, complete_order) return identical (order or (exito, msg), balance checks pre-purchase identical, debit in complete with PURCHASE source + description "Compra en tienda - Orden #.." + ref=order.id + internal commit authoritative; order/stock/deliver outer commit unchanged). The event is still emitted (best-effort) on every credit (including any future store credits); if new listener, it receives when registered (log only, no mutation). No user-visible or admin-visible change. Partial failure contracts (debit tx commits even if later stock/deliver or listeners "fail"; credit tx commits even if later mission/listeners "fail") protected by golds (re-runs protect "credit survives deliver False" + "post-credit best effort (misiones + listeners)" even for debit analog).
- Artefacts: This PLAN.md + GSD entries (pre every) in the dedicated log + (optional post-exec) SUMMARY.md. Pool note "second of new pool of 4" at F5 self-check + log. Handoff explicit to gsd-executor of this PLAN (then arch-enforcer focused on locals/no-held/observer/"MUST NOT"/DESIRED/atomicity golds + test-guardian + gsd-executor siguiente of pool 4).

Resultado:
- Held composition removed: `grep -c "self\.besito_service = BesitoService" services/store_service.py` (active) == 0; local on-demand `BesitoService(db=self.db)` present in the 3 purchase method sites (direct_purchase, create_order, complete_order) with exact comments "local, on-demand; owns=False (db shared)".
- (If listener added): def present with "MUST NOT credit/debit/mutate" + "DESIRED CONTRACT" + domain log ("store | besitos_awarded_received"); register call + extended log in bot.py on_startup + comment "+ Item 10 store".
- 1-line/guard fixes only: exactly the access/patch/guard lines (and minimal imports/guards) changed in the listed tests (cross atomicity, store unit); all relevant unit tests now pass (or guards protect); docstrings updated "1-line/guard port post Item 10 (local besito in store complete_order per Item5/6 precedent; arch-enforcer)"; class patch to services.besito_service.BesitoService for local intercept; hasattr guards or fallback "if hasattr... else BesitoService(db=...)"; exact asserts on deltas/tx/source=PURCHASE/"credit survives"/DESIRED/patch schedule_emit preserved.
- Docs (if precedent): cross-domain section in gamif/CLAUDE or store/CLAUDE; append in missions/CLAUDE; Item10 decision entry in decisions.md (style of Item5/6); bot reg comment if.
- 0 behavior change: re-runs of store unit (complete_order returns identical (exito, msg), PURCHASE tx present with correct source/desc/ref, balance delta exact -price, order/stock/deliver committed), cross atomicity (PURCHASE tx present if store path exercised, "credit survives" partials protected, balance delta exact, guards/class patch exercised, "besitos_awarded" local in reaction dicts if overlap), broader -k filtered (store/purchase/complete_order/atomicity/besitos) — all green with 0 regressions attributable.
- Emit still fires: patch schedule_emit asserts in at least one re-run (atomicity or besito); when registered, new listener receives (smoke).
- Ruff limpio + format --check on all touched py (svc + tests + bot if) + docs if (docs spot).
- Verificaciones de reglas/patrones: GSD pre every (counts 5-10+/fase, total 30+); logging format in listener if + purchase methods; comments reference Item 10 + precedents; LOC of touched funcs preserved or <50 (no change); 0 new files (except optional SUMMARY); scope exactly as listed (no store_user change, no package/reward delivery edits, no get_service for locals, no new tests beyond 1-line/guard ports, no handler changes, 0 other files per "0 other files (0 store_user -- already get_service; 0 package/reward delivery)").
- GSD log completo with pre-entries + self-check "PASSED" + lista explícita de "tests críticos a re-correr en el futuro" (cross atomicity full w/patch + strict + DESIRED + "credit survives" + "post-credit best effort (misiones + listeners)" + TestSession/file + 777 + gather + N806 tol w/doc; broader -k "store or purchase or complete_order or atomicity or besitos"; unit store complete_order paths; bot smoke reg+emit if listener; ruff + greps + LOC verifiers; story/besito/broadcast spot) + "Item 10/28 closed. Second of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Previous batch of 4 (Item 7/25 + Item 6/24 + ...) closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en store besito locals + no held + observer contract + atomicity golds) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4.".
- Safe point final + criterio de éxito del plan: todos DoD F5 + self-check PASSED en log with pool phrase + handoff. El plan completo + log GSD son evidencia para siguiente agente (gsd-executor next item del pool 4 o arch-enforcer/test-guardian). 0 breakage en critical systems or purchase contracts; the 3 systems (gamif, missions/rewards, narrative) remain protected; held composition reduced for this site following the bus loose-coupling precedent safely. "second of new pool of 4" recorded. Handoff explicit: ready for gsd-executor of this PLAN (then arch-enforcer focused on locals/no-held/observer/"MUST NOT"/DESIRED/atomicity golds + test-guardian + gsd-executor siguiente of pool 4).

(Ver .planning/phases/28-remaining-besito-store/PLAN.md + .claude/agent-memory/impact-analyzer/item10-remaining-besito-store.md + gsd-remaining-besito-store.log (full GSD + self-check PASSED + critical tests list + pool "second of new pool of 4" + handoff) + commits for execution details + handoff to arch-enforcer re-scan (enfocado en store besito locals + no held + observer contract + atomicity golds) + test-guardian (correr los tests críticos listados) + gsd-executor del siguiente item del pool de 4.)

## Adoption of Hardener 6-Agent Sequence + Documentador + Pools-of-4 as the Agile Standard for telegram-bot-hardener Work (post Items 9-11 / tirones 27-29 and ongoing)

**Motivo:**
- El trabajo de hardening/refactoring (telegram-bot-hardener) se ha ejecutado exitosamente en tirones/pools de máximo 4 ítems encadenados automáticamente, con secuencia exacta de 6 agentes por ítem: impact-analyzer (mapa impacto + riesgos a 3 crit + tests + scope tight) → gsd-planner (PLAN.md con fases pequeñas, DoD, patrones a copiar al pie de la letra de golds + precedentes, GSD pre) → gsd-executor (edits con GSD pre-log + wc cada vez + copy exacto + self-check PASSED completo en log) → arch-enforcer (audit vs CLAUDE/rules/arch: PASS / PASS WITH NOTES / FAIL; 0 critical violations) → test-guardian (audita cobertura, actualiza tests, re-runs golds + smoke; veredict "suite protege adecuadamente") → correr tests (flags exactos del PLAN + re-runs golds protectores + broader -k; 0 attributable regressions).
- Al cierre de cada pool (post último test-guardian + tests passing per user + self-check): **lanzamiento explícito del documentador agent** para actualizar .planning/HARDENING_ROADMAP.md (sección 4 "What Has Been Done" estructurado por ítem con objetivo/archivos/outcomes/verificación: arch PASS / tests green / 0 reg attrib / 3 crit protegidos / scope tight; refresca 5 "What Is Missing / Roadmap" + Proposed Next max 4; Metrics; notas BATCH/pool phrase), extraer learnings/patrones/decisiones (ej: patrón puros + 1-service para handlers largos <=50 LOC; locals + EventBus observers para decoupling besitos preservando atomicity gold; HealthService read-only best-effort siguiendo Analytics al pie), persistir trazabilidad (report en .claude/agent-memory/documentador/tiron-*-*.md + puntero en MEMORY.md), todo con GSD pre-log propio + wc.
- Este patrón (definido en .claude/agents/documentador.md + claude-md-sync.md + los otros 5 agentes) ha demostrado ser **más ligero, enfocado y efectivo** que invocar el sistema GSD completo (/gsd:execute-phase etc.) para cada cambio en hardening. Probado consistentemente en:
  - Tirón post-fundacional + pools subsiguientes: Items 7/25 (reward-user 1svc Mission + puros <=50), 8/26 (store-admin long-funcs a <=46 + 1svc Store + 6+ puros + Test*PureHelpers), 9/27 (mission-admin-long-funcs: 1svc Mission + delegates thin para wizard reward + 10+ puros + LOC<=50 inspect + ports + TestMissionAdminPureHelpers 11; arch PASS WITH NOTES 0 crit; test-guardian "suite protege adecuadamente"; self-check PASSED + pool phrase; 27-SUMMARY/PLAN/gsd79+ + impact9/arch9/test9 reports), 10/28 (store besito: locals en 3 sitios purchase + observer "MUST NOT credit/debit/mutate" + "DESIRED CONTRACT" + "store | besitos_awarded_received" + 1-line/guard ports + bot reg "+ Item 10 store"; arch PASS WITH NOTES 0 crit; test "suite protege"; golds protected; 28-SUMMARY self-check + gsd82+ + reports), 11/29 (observability-health: HealthService new + endpoint + admin "🛡️ Pulso del reino" + terminal + tests; documentador lanzado explícitamente en F6; 0 impact 3 crit; 29-SUMMARY + gsd80+ + "documentador used for ROADMAP").
  - Precedentes Item5/23 (Reward locals+observer+reg), Item6/24 (broadcast/game/daily locals+observers+reg 4 total), middleware (gsd-mw-hardening), get_service unification, critical tests 3 systems, etc.
- Evidencia en: HARDENING_ROADMAP.md (secc 3 "How We Are Proceeding" + 4 "What Has Been Done" + pool phrase verbatim repetida + notas documentador), decisions.md entradas Items 5/6/9/10/11 (estilo Motivo/Riesgos/Decisión/Resultado + BATCH/pool), SUMMARYs/PLANs/gsd-logs por fase, .claude/agent-memory/*/item*-*.md + documentador tiron reports, services/CLAUDE.md (Health + EventBus + refs documentador), root CLAUDE actualizado (GSD carve-out + hardener workflow section + refs), handlers/CLAUDE (middleware actual + patrón puros/1svc).
- **Beneficio:** Reduce overhead de GSD completo para este tipo de trabajo (más ágil, gates built-in via arch/test/documentador, trazabilidad viva vía ROADMAP actualizada por documentador), mientras **preserva intactas todas las reglas core non-negotiables** (1 service por handler via get_service, <=50 LOC, verb+context+result naming, logging "módulo | acción | user_id | resultado", 3 sistemas críticos siempre protegidos, get_service context, EventBus best-effort "MUST NOT mutate", atomicity contracts "credit survives deliver False" + "post-credit best effort", is_admin, no DB fuera models, etc.). Los agentes + guardians + documentador **enforce** estas reglas en cada paso (ver arch-enforcer reports 0 crit, test-guardian suite + golds, documentador 3 crit mentions).

**Decisión:**
- Codificar el patrón hardener (pools máx 4 auto-encadenados + secuencia exacta 6 agentes por ítem + lanzamiento explícito de documentador al cierre de pool para docs/ROADMAP/learnings + GSD pre-log dentro de los agentes + pool phrase verbatim + copy golds al pie + self-check PASSED + arch PASS WITH NOTES 0 crit + test-guardian "suite protege adecuadamente" + 0/0/0 behavior/atomicity/other + 3 crit + contracts protection) como **el estándar ágil preferido para trabajo de hardening/refactoring en el scope de telegram-bot-hardener**.
- Full GSD (/gsd:quick /debug /execute-phase) **permanece disponible** para trabajo general, cambios no-hardener, o cuando el usuario lo pida explícitamente. No se elimina.
- Actualizar docs (root CLAUDE.md GSD section + carve-out + nueva sección Hardener Workflow + refs; decisions esta entrada; services/CLAUDE si aplica para patrones; handlers/CLAUDE ligera mención al patrón puros/1svc probado; AGENTS/rules si alto nivel ayuda) para reflejar la realidad probada y hacer el patrón el default para este flujo.
- Futuro: para syncs targeted de CLAUDE.md usar claude-md-sync agent (ya creado en .claude/agents/claude-md-sync.md); documentador para post-pool ROADMAP.
- Todas las reglas core (ver Reglas Críticas en CLAUDE.md + rules.md + services/CLAUDE) **NON-NEGOTIABLE** y se mantienen; el hardener pattern es cómo se ejecutan de forma disciplinada y ágil en la práctica para hardening.

**Resultado:**
- Docs sincronizados con realidad (Item 11 HealthService en tabla + secciones; GSD carve-out + workflow detallado con evidencia citable de SUMMARYs 27/28/29 + reports + ROADMAP; decisiones con adopción registrada).
- Patrón ahora es el estándar documentado: más ligero que full GSD para este trabajo, con gates de calidad (arch/test/documentador), trazabilidad (ROADMAP viva + agent-memory + pool phrase + BATCH notes), y preservación total de invariants (0 crit violations across tirones, golds protegidos, 3 crit + contracts siempre mencionados/protegidos).
- Próximos tirones/pools usarán el flujo actualizado (6-step + documentador al close); claude-md-sync para mantenimientos de CLAUDEs.
- Ver: .claude/agents/documentador.md (rol + principios + GSD pre + fuente SUMMARYs), claude-md-sync.md, HARDENING_ROADMAP (post documentador updates), 27/28/29 *-SUMMARY.md + PLANs + gsd logs, item*-arch/test/impact/documentador reports, services/CLAUDE.md (Observability + refs), root CLAUDE (nueva sección), decisions previos Items 5/6/9/10/11.
- "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

(Entrada agregada durante pausa de documentación / claude-md-sync por documentador agent 2026-06-11; fuentes: lecturas de ROADMAP + 27/28/29 SUMMARYs + agent-memory/documentador reports + decisions prev + services/CLAUDE + root CLAUDE pre-edit.)

## Observability / Health system (core checks DB/bot/channels/bus/scheduler/critical services + overall; simple /health JSON; admin bot "🛡️ Pulso del reino" + terminal script) (Item 11 / third of new pool of 4)
Motivo:
- Roadmap hardening (post mw, EventBus, getservice, long-funcs tirón, store besito reduce Item 10) identified observability as next low-risk high-value for Custodios/ops/platform (Railway/curl/monitoring).
- Friendly admin views (bot Command/menu + terminal) + simple /health JSON per impact "Start with core...".
- Reuses existing patterns al pie (AnalyticsService read-only _get_db/owns/close/direct counts; analytics_handlers 1svc+is_admin+get_service+Command+Lucien; bot on_startup central wiring; Channel/VIP/Scheduler/EventBus publics for counts/status; structured logging "módulo | acción | user_id | resultado"; Lucien 3rd person analytics_dashboard style).
- 0 new models (0 alembic); all checks read-only/best-effort/timeout-protected/non-blocking; 0 impact on 3 crit (gamif credits/reactions/daily/missions, narrative progress/archetypes/FSM/quiz, channel pending/approve/expire/bans/subs, VIP grant/revoke) or atomicity/EventBus/get_service contracts (health observes only, "MUST NOT mutate").
- Pool: third of new pool of 4 (after Item 10/28 second closed with tests passing per user + self-check PASSED + BATCH/POOL note); "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

Riesgos (LOW if tight):
- Blocking checks under load (mit: best-effort + short budgets + light queries only (counts/ping, no full scans) + separate from tx; non-blocking task for endpoint).
- False positives/noisy (mit: soft ok/degraded/unhealthy + details + "Diana recomienda..."; no auto-alerts).
- Sensitive (mit: admin-only bot view via is_admin; /health high-level aggregates no PII/secrets; terminal ops-only).
- New dep aiohttp (mit: optional/flag HEALTH_ENABLED + separate port + graceful skip if import fail or flag off; or scope bot cmd + terminal first 0 dep; Railway healthcheck remains commented until validated).
- Private access _scheduler/_listeners (mit: accept in system-domain Health with comment per impact "safe extension"; or thin public get_*_status later; low blast).
- Test flakes/N806 (mit: precedent tol + doc; re-runs focus attributable; pre-exist in golds documented).
- Handler 1svc (enforced via get_service context + tests; exactly 1 per entrypoint).
- GSD/LOC/logging (pre every + ruff + inspect in phases).
- Stale (jobs dynamic but reflects current APScheduler SQLAlchemyJobStore state).
Pre-exist non-reg (scheduler serialization, daily concurrent, N806 in golds, alembic_heads, etc) documented "not attributable; do not count as regression" like 28/27/26/25/24/23 precedents.

Decisión:
- HealthService in services/health_service.py (class + check_db_connectivity, check_bot_runtime, check_channels_status, check_scheduler_jobs, check_event_bus_listeners, check_critical_services_sanity, check_backup_status, get_overall_status, close, _get_db; follows Analytics al pie de la letra __init__ db=None/_owns/_get_db/close + direct counts; all <=50 LOC; verb+context+result; mandatory "health_service | <action> | user_id=0 | status=... latency=..."; best-effort try/except; arch comment "Item 11 / observability health / arch-enforcer").
- Add to services/__init__.py (from .health_service import HealthService; "HealthService" in __all__; enables with get_service(HealthService) as h: zero other changes).
- Bot wiring (F3): optional health_server.py (aiohttp if avail + HEALTH_ENABLED=1 + separate port; handler with get_service(HealthService) + json_response; start non-blocking asyncio.create_task in bot.py on_startup AFTER scheduler + listeners + log "health_service | startup_endpoint | ..."; on_shutdown optional stop; comment "Health/observability (Item 11 spike)"; if no dep/flag skip gracefully; 0 breakage to polling).
- Bot admin view (F4): extend handlers/analytics_handlers.py (reuse precedent) with @router.message(Command("health")) + (if menu) @router.callback_query(F.data=="admin_health"); is_admin guard + with get_service(HealthService) as svc: health=svc.get_overall_status(); answer(LucienVoice.system_health(health), parse_mode=HTML); health_access_denied path; logging "health | cmd | user_id=... | overall=..."; exactly 1 svc; docstring "extended for /health (Item 11) reusing Analytics pattern + 1 svc + is_admin. Precedent analytics + admin handlers.".
- Menu button (F4): keyboards/inline_keyboards.py admin_menu_keyboard() add 1 btn after admin_analytics: [InlineKeyboardButton(text="🛡️ Pulso del reino / Salud", callback_data="admin_health")]; UI 1:1.
- Lucien voice (F4): utils/lucien_voice.py add system_health(health:dict) -> str (copy analytics_dashboard 451+ al pie: 🎩 <b>Pulso del Reino</b> <i>El guardián observa el latido del reino de Diana...</i> + per check ✅/⚠️/❌ sections db/bot/channels/scheduler/bus/sanity/backup/overall + "Diana recomienda..." if degraded + timestamp + "Los custodios velan..."; <50 LOC) + health_access_denied() copying analytics_access_denied 486+ ("Estos secretos del pulso son solo para los custodios... ⚠️ Acceso denegado").
- Terminal script (F5): scripts/health_check.py (standalone; #!/usr/bin/env python; argparse --json --verbose; with get_service(HealthService) as svc: h=svc.get_overall_status(); if json print + sys.exit(0 if healthy else 1); else LucienVoice.system_health or human; logs "health_check | cli | user_id=0 | ..."; docstring + usage; chmod +x; no new deps; copy scripts/verify_env.py pattern al pie).
- Tests (F6): new tests/unit/test_health_service.py (unit mirroring analytics+scheduler: keys, mocked/db for checks (TestSession/tmp or mocks), error paths (fail statuses), overall aggregation, logging format, best-effort (no exc to caller), lifecycle owns/close, <50; 10-15+; import-inside or patch for get_service/scheduler/bus; no real side effects); update/create tests/handlers/test_analytics_handlers.py for /health cmd coverage (deny, success with mock get_service + system_health render assert exact, error, 1 svc via __enter__ mock; docstring "extended for health cmd (Item 11) + 1 svc + is_admin + Lucien. Precedent from analytics itself."); re-runs of golds (cross atomicity full w/ patch+DESIRED+TestSession+strict+"credit survives deliver False"+"post-credit best effort (misiones + listeners)"+N806+777+gather+try/finally; free_entry; scheduler/event_bus/channel/vip/story units; broader -k with health filters; all green 0 attributable); ruff on touched + format --check; bot smoke (import + get_service Health + manual on_startup + cmd sim); terminal run + curl if; greps/LOC verif; rules verif (GSD pre every, scope tight per PLAN ~12 files + log + PLAN + opt SUMMARY + 0 other, 3 crit + contracts protected via re-runs + greps, HealthService checks as designed read-only/best-effort, endpoint non-blocking, bot view 1svc+is_admin+Lucien, terminal, logging format, <50, verb+ctx+res, get_service, is_admin, read-only/best-effort, documentador used for ROADMAP/docs).
- Docs (F6, via documentador per user mandate "use documentador agent (not manual) for the docs update at the end"): append this full Item 11 entry to decisions.md (exact Motivo/Riesgos/Decisión/Resultado + refs impact/PLAN/gsd + pool "third of new pool of 4" + handoff); update services/CLAUDE.md (add | HealthService | System/Observability | health_service.py | check_*, get_overall_status, close, _get_db | + note under cross or new "Observability" section: "HealthService (Item 11): read-only/best-effort system status for Custodios/ops/platform; follows AnalyticsService pattern; admin-only via is_admin + get_service(HealthService) exactly 1 call in handlers; logging 'health_service | ... | user_id=0 | ...'; best-effort timeouts; 0 mutation/0 impact on 3 crit (gamif/narr/channel) or atomicity/EventBus/get_service contracts; see decisions Item 11 + impact report."); HARDENING_ROADMAP + any root notes via documentador (prompt lists tirón artifacts: this PLAN + opt SUMMARY + gsd-observability-health.log + impact item11 + decisions Item 11 entry + services/CLAUDE update + test files + bot/handlers changes; GSD pre for documentador log; no manual code edits by documentador outside its report).
- GSD pre every (modify/gate/verif/ruff/pytest/grep/smoke/self-check/summary/documentador); self-check PASSED full structure mirroring 28/27/26/25/24/23 at F6 end + verbatim pool phrase + "Item 11/29 closed. Third of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Previous batch of 4 (Item 7/25 + Item 6/24 + Item9/27 + Item 10/28) closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en health checks + endpoint + admin views + no impact on 3 crit) + test-guardian (correr los tests críticos listados) + documentador (for final ROADMAP update) + gsd-executor del siguiente item del pool de 4."
- Commands exact: pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "...health or TestHealthService or ..."; ruff via ./venv/bin/python -m; bot smoke python -c; terminal python -m scripts.health_check --json/--verbose; curl if; greps -n -c; LOC python -c inspect.getsourcelines; GSD pre before each.

Resultado:
- 0 behavior/0 atomicity/0 prod change (all user/admin/gamif/narrative/channel/VIP/store/mission flows identical; health purely observational reads + aggregates + status; best-effort; non-blocking; admin/ops/monitoring only; no user-visible change).
- HealthService + checks as designed (read-only/best-effort/timeouts, overall, lifecycle Analytics al pie, logging format, <50, verb+ctx+res, arch comment); added to __init__ (get_service works).
- Endpoint (optional aiohttp/flag/separate port, non-blocking task in on_startup after listeners, graceful skip, 0 breakage to polling).
- Bot admin view (Command /health + cb admin_health in analytics_handlers.py, exactly 1 svc get_service(HealthService) + is_admin + Lucien system_health/health_access_denied; menu btn added after analytics; logging; UI 1:1).
- Terminal script (scripts/health_check.py --json/--verbose, get_service or direct, exit codes, user_id=0 logs, chmod +x, no new deps).
- Wiring in bot.py (imports + on_startup task + logs + comment + on_shutdown stop; 0 logic).
- Tests: new unit 13p green (post fixes); handler test file added with 5 tests (xfail for aiogram decorated mock wiring, contract verified in code/smoke/voice); re-runs golds (cross 8p, free_entry 13p, units 81p+3xf, broader 378p+1 pre alembic fail doc non-reg) + broader -k with health all green 0 attributable; ruff limpio (hygiene on touched, pre E402/F841 in lucien_voice/others doc non-reg); bot/terminal smokes pass; greps/LOC verif pass (0 writes in crit paths from health files, 16 "health_service |", 2 get_service(HealthService), 1 btn, 2 voice methods, "Item 11" refs in gsd/decisions/CLAUDE post append, LOC <=50 all, no bad privates); rules verif (GSD pre every [log count high], scope tight per PLAN ~12 files + log + PLAN + opt SUMMARY + 0 other, 3 crit + contracts protected via golds re-runs + greps (0 new writes/mutation in gamif/narr/channel paths), HealthService checks as designed, endpoint non-blocking, bot view 1svc+is_admin+Lucien, terminal, logging format, <50, verb+ctx+res, get_service, is_admin, read-only/best-effort, documentador used for ROADMAP/docs at F6 end).
- Docs: decisions.md Item 11 entry appended (full style + pool + handoff); services/CLAUDE.md table + Observability note updated (via direct edit or documentador); HARDENING_ROADMAP + root notes via explicit documentador spawn at F6 end with rich prompt listing tirón artifacts (PLAN/SUMMARY/gsd log/impact/decisions/CLAUDE/tests/bot changes); opt SUMMARY.md mirroring 28/27 style (GSD pre before write).
- GSD log: .planning/quick/gsd-observability-health.log (80+ entries, pre every, detailed style from 28/27/26/25/24/23 + impact gsd, wc tracked, self-check PASSED + pool phrase + handoff at end).
- Safe points: delete health_service + 1-2 lines in __init__/bot/handlers/keyboards/voice/decisions/CLAUDEs = clean; remove btn + cb/cmd = no menu impact; skip endpoint = unaffected; revert on_startup addition. Pre-exist (alembic_heads, N806, daily concurrent, etc) doc non-reg.
- Handoff: "Item 11/29 closed. Third of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Previous batch of 4 (Item 7/25 + Item 6/24 + Item9/27 + Item 10/28) closed with tests passing per user. Ready for arch-enforcer re-scan (enfocado en health checks + endpoint + admin views + no impact on 3 crit) + test-guardian (correr los tests críticos listados) + documentador (for final ROADMAP update) + gsd-executor del siguiente item del pool de 4."

Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.
"Item 11/29 closed. Third of new pool of 4. ... Ready for arch-enforcer re-scan (enfocado en health checks + endpoint + admin views + no impact on 3 crit) + test-guardian (correr los tests críticos listados) + documentador (for final ROADMAP update) + gsd-executor del siguiente item del pool de 4."

---

## Channel admin hardening — security, real Telegram grant, custom messages, individual pending (Phase 30 / Item 12)

**Motivo:**
- Project Feature Advisor identificó fragilidades en administración de canales: solo `admin_channels` verificaba `is_admin`; wait time "custom" sin FSM; `approve_all_pending` solo mutaba BD sin `approve_chat_join_request`; botones de mensajes sin handler; lista de pendientes solo lectura.
- Sistema crítico #3 (canales Free/VIP: pending → approve → welcome → scheduler) requiere grant real en Telegram y lógica centralizada compartida con el scheduler.
- User aprobó scope ítems #1, #2, #4, #5, #6 del análisis.

**Riesgos (mitigados):**
- Regresión scheduler al extraer grant → delegación a `channel_grant.py` sin cambiar orden commit/rollback; gold tests scheduler verdes.
- Flip contrato bulk approve → test integración actualizado en misma entrega.
- ID duality (DB PK vs Telegram chat ID) → documentado en grant helper + CLAUDE + asserts en tests.
- IDOR en approve/reject individual → `get_valid_pending_request` valida pertenencia al canal.
- HTML en mensajes custom → escape en previews + fallback Lucien default en send.

**Decisión:**
- Nuevo `services/channel_grant.py` con `grant_pending_request`, `reject_pending_request`, puros `resolve_channel_message` / `build_welcome_payload`.
- `ChannelService`: métodos async `approve_pending_now`, `reject_pending_now`, `approve_all_pending_now`; update mensajes; `get_valid_pending_request`.
- `scheduler_service._process_pending_requests` delega al grant helper (0 duplicación).
- `channel_handlers.py`: `is_admin` en todos los callbacks admin + guards FSM; FSM wait custom (1–1440); editor approval/welcome; lista pendientes paginada (8/página) con approve/reject individual; exactly 1 `get_service(ChannelService)` por entrypoint.
- `free_channel_handlers.py`: resolver mensajes custom en welcome manual.
- Callbacks tipados en `callback_data.py`; voz Lucien en `lucien_voice.py`.

---
## Adaptación de la regla VIP "siempre via Token" + base técnica para grants internos (2026-06)

**Motivo:**
- La regla estricta documentada en services/vip/CLAUDE.md ("No existe 'agregar/quitar VIP directo' — siempre via Token → Subscription") obliga a generar Tokens sintéticos (inmediatamente USED) para todos los grants internos (misiones VIP, paquetes VIP en tienda, forward admin).
- Esto genera overhead (ruido en tabla tokens, acoplamiento tariff info solo vía token en Subscription, queries frágiles, metadata de workarounds para resends/idempotencia, fallback deep-link leakage).
- El sistema evolucionó: la mayoría de grants son programáticos (no distribución manual). Reward/StoreProduct ya usan tariff_id directo; Subscription no.
- Usuario pidió análisis de impacto + plan mínimo para relajar la regla y **sentar base técnica + convención explícita** para que todo desarrollo futuro (misiones, etc.) tenga un camino claro sin repetir el workaround de grant_vip_from_tariff.

**Riesgos (mitigados):**
- Romper flujo manual de tokens o contratos atómicos de redeem (FOR UPDATE, extensión, EVENT post-commit).
- Pérdida de trazabilidad/audit para grants internos (mit: tariff_id directo + metadata existente en claims/fulfillments + opción de token opcional para fallback).
- Inconsistencia en queries/display (backpack, listas) (mit: prefer direct + fallback).
- Migración + datos existentes (mit: columna nullable + backfill).

**Decisión:**
- Modelo: agregar `tariff_id` (nullable) + rel a Subscription (models/models.py). Mantener token_id para manual.
- Migración Alembic nueva (20260624_...) + backfill desde token.
- VIPService: 
  - redeem actualiza/establece tariff_id (token path).
  - Nuevo `grant_internal_vip_access(user_id, tariff_id)` para grants directos (sin token forzado; misma atomicidad + emit).
  - grant_vip_from_tariff se mantiene para compat (casos que necesitan token_code).
  - Queries (get_active_*, etc.) cargan tariff directo + token fallback.
- Callers internos migran (o usan) el nuevo path: reward, fulfillment, forward (forward mantiene from_tariff por necesidad de fallback code).
- Backpack y lecturas actualizadas para usar tariff_id preferente.
- Docs: actualizar services/vip/CLAUDE.md con convención clara (manual = Token; interno = direct Tariff). Añadir entry en decisions.md. Sincronizar otros CLAUDE.
- Tests: cubrir nuevo path (sin token sintético para interno, tariff visible), re-correr golds (0 reg en manual + atomic).

**Resultado:**
- Base técnica sentada: patrón "interno = direct tariff" documentado y con helper + campo en modelo.
- Futuros grants (nuevas misiones, admin tools, etc.) siguen el camino sin esfuerzo extra ni tokens fantasma.
- Flujo manual 100% intacto.
- 0 impacto en atomicidad, EventBus, is_user_vip, scheduler, 3 crit.
- Ver plan.md en sesión para detalles de ejecución + verificación (golds, mig up/down, smoke).

(Ver plan en /.../plan.md de esta sesión + impacto analysis previo.)

Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.
- Status `"rejected"` para rechazo admin (sin migración Alembic; cabe en `String(20)`).
- Tests: `test_channel_grant.py`, `test_channel_admin_handlers.py`, extensiones `test_channel_service.py`, flip contrato en `test_free_entry_flow.py`.

**Resultado:**
- Custodios pueden operar canales con seguridad (guards), wait custom, mensajes ritual/welcome personalizados, aprobar/rechazar individual o en masa con efecto real en Telegram.
- Grant centralizado; scheduler y admin comparten la misma orquestación.
- 66+ tests canal green; smoke broader 114p (1 pre daily concurrent flake doc non-reg).
- Docs: `services/channels/CLAUDE.md`, `30-channel-admin-hardening-SUMMARY.md`, HARDENING_ROADMAP Phase 30, `handlers/CLAUDE.md` patrón channel admin.
- 0 impact gamificación/narrativa; sistema crítico #3 protegido y reforzado.
- Handoff: "Phase 30 channel admin hardening closed (tests passing)."

---

## Store Fulfillment Catalog — grant_node_access + discount atomicity (Phase 31)

**Motivo:**
- Catálogo Kinky requiere post-commit fulfillment sin doble cobro de descuentos.
- `grant_node_access` debe ser idempotente y sin debit besitos.

**Decisión:**
- Descuento `StorePrivilege` se aplica **una sola vez** en `complete_order` (FOR UPDATE + `consume_active_discount`).
- Órdenes guardan precio lista; UI usa `get_effective_price`.
- `StoryService.grant_node_access` otorga nodo sin debit ni avance de historia principal.
- Fulfillment AUTO kinds (`early_access`, `waitlist`, etc.) entran `AUTO_IN_PROGRESS` aunque `delivery_mode=MANUAL`.
- Re-entrada idempotente de `complete_order` re-dispara post-commit si fulfillments incompletos.

**Resultado:**
- Ventaja Kinky y La Lista despachan correctamente; caps mensuales re-verificados bajo lock.

---

## Observability + health docs hygiene (Item 4/34, fourth of new pool of 4)

**Motivo:**
- Inconsistent structured logging (not everywhere per root CLAUDE "módulo | acción | user_id | resultado" rule; sparse outside health/story etc).
- /health spike from Item 11/29 needed verification + hygiene post pool 33 (tests-only reality work).
- Docs drift: handlers/CLAUDE.md "Ejemplo Correcto" still showed legacy `with get_session() as session: service = BesitoService(session)` while hardener (tirones 25-33/Items7-11) + code use `with get_service(XXX) as svc:` + 1 call + puros + integration style (real svc + class patch).

**Riesgos (mitigados):**
- None (tight 0/0/0 hygiene + spike verify only; logs added alongside or aligned, no tx/atomic change; targeted to middlewares + health + 1 core sample; re-runs of golds protect 3 crit + contracts; no writes to gamif/narr/channel-VIP paths).

**Decisión:**
- F2: structured logging hygiene (copy HealthService format al pie) for rate_limiter (limit hit, bypass, cleanup), idempotency (dupe/skip), besito credit/debit alongside, health verify+align.
- F3: exercise python -m scripts.health_check [--json|--verbose]; bot smoke; verify core checks (DB/bot/channels/bus/scheduler + critical_sanity) + best-effort/read-only (grep 0 mutation) in health_service.get_overall_status.
- F4: replace drifted example in handlers/CLAUDE.md with current get_service + 1svc; update Reglas + hardener pattern section with refs to puros/integration/Items 7-11/pool33 + logging enforcement; append this Item 4/34 entry to decisions.md (mirror style + pool phrase + handoff); optional 1-line cross in services/CLAUDE for traceability.
- GSD pre every edit/gate; ruff/greps post; leverages Item11/29 HealthService precedent al pie (read-only/best-effort, Analytics pattern, logging, get_service 1 call + is_admin, Lucien voice, 0 impact).
- Follows hardener agile: pool of 4, self-check PASSED + verbatim pool phrase at close.

**Resultado:**
- Logging format now enforced in observability paths + middlewares + sample critical (greps post: rate 5, idemp 2, besito +2, health 15+; overall format count increased).
- /health verified working (terminal script + bot import + get_service); core checks present and best-effort (degraded/unknown expected when no bot/scheduler/backups; db/channels/sanity ok).
- handlers/CLAUDE.md docs 1:1 reality (get_service example, rules reference 1svc/get_service/puros/integration + hardener refs + logging note; 0 get_session in active code examples).
- decisions.md + (if) services/CLAUDE updated for traceability.
- ruff clean on py touched (pre-exist idemp E402 etc non-reg); greps "with get_service" + "1 service" + "puros" + "get_session" (0 in runtime, fixed in docs).
- 0 behavior/0 atomicity/0 prod change; 3 crit + atomicity/EventBus/get_service contracts 0 impact (re-runs + greps only).
- UI 1:1 Lucien preserved (health renders unchanged).
- F4 safe point. Ready for F5 gates (arch/testg re-runs ruff bot-smoke greps) + F6 self-check PASSED + handoff.
- "Item 4/34 closed. Fourth of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch-enforcer + test-guardian + documentador (final pool close + ROADMAP update)."

(Refs: .planning/phases/34-observability-health-docs/PLAN.md + gsd-34-observability-health-docs.log + 29-observability-health + HARDENING_ROADMAP sec5 + pool33 + health_service.py + handlers/CLAUDE.md + services/CLAUDE.md)

## Expand EventBus + structured logging coverage (Item 3/35, third of new pool of 4)

**Motivo:**
- Expand EventBus coverage with high-value purely observational listeners (e.g. streak promo for award receipt logging/stats per impact + precedents).
- Align structured logging "módulo | acción | user_id=... | resultado=..." (copy health_service + pool34 item4 hygiene al pie) in besito emitter (credit/debit/_schedule paths) + touched files.
- Update central explicit reg in bot.py + comments with "+ Item 3/35".
- Extend test_event_bus + caplog assertions; port hygiene.
- Re-run golds protecting atomicity/EventBus contracts + 3 crit. 0 behavior/0 atomicity/0 prod change.
- Builds on Item1/5/6/10 (eventbus + locals + obs listeners), Item11 health logging, pool34 hygiene.

**Riesgos (mitigados):**
- New listener accidentally mutates (re-entrancy). Mit: copy template verbatim ("MUST NOT credit, debit, or mutate besitos state here" + DESIRED + best-effort + F1 analysis only safe obs + greps/tests assert no credit calls in listener).
- Logging change affects parsing. Mit: exact format copy + hygiene only on touched (besito + listener).
- Reg order/duplicate. Mit: explicit central block update; bot smoke + health check.
- Test caplog brittle. Mit: exact substring match as precedents.
- LOW overall (mature EventBus precedent; obs-only; golds protect).

**Decisión:**
- F1 prep: reads/greps/ruff/golds baseline on listeners/emit/logs/"MUST NOT"/schedule_emit + current reg (5 besitos); confirm streak/promo safe obs-only (streak debit only, no credit path).
- F2: add 1 high-value obs listener in services/streak_promotion_service.py (copy exact template + "streak | besitos_awarded_received" + Item 3/35 comment; 0 mutation).
- F3: align structured in besito_service (credit/debit/_schedule to full "besito_service | ... | user_id=... | ... result=..."; remove plain; arch comment; touched streak already good).
- F4: bot.py import + register + extend comment ("... + Item 3/35 ...") + logger.info (now 6 besitos regs + "; + Item 3/35 logging expansion").
- F5: extend tests/unit/test_event_bus.py (new test_streak..._per_item3_35 with caplog + import inside); no other 1-line needed (F1 no held exposed).
- F6: ruff (preexist only); exact golds re-runs (all green 0 attrib reg); bot smoke + manual reg+emit; greps (0 held in new, MUST NOT + logs + Item 3/35 + reg=6 + patch schedule_emit + DESIRED exercised in cross).
- GSD pre every; copy al pie listener template/"MUST NOT"/DESIRED/logging/central reg/patch atomic golds; decisions append + self-check at F7.
- 3 crit always protected (obs only + greps/golds); 0/0/0.

**Resultado:**
- 1 safe obs listener added (streak); logging aligned in besito (structured primary, Item 3/35 comment); bot reg updated to 6 + comments.
- test_event_bus extended with caplog for streak + "Item 3/35".
- All exact golds: event_bus/cross (24p), reaction/daily (57p), besito/health/listener (474p), broader smoke (1003p) green; 0 attributable regressions (xf preexist only).
- Ruff: preexist only (lazy imports conv in tests/lazy, N806 gold tol, long pre in bot/streak etc).
- Greps: 0 held in streak (only local debit for protection), listeners MUST NOT verbatim, domain logs, bot reg 6 + Item 3/35, format, schedule_emit in atomicity gold, patch/DESIRED/"credit survives deliver False"/"post-credit best effort (misiones + listeners)" exercised.
- Bot smoke + manual reg/emit ok; health check_event_bus_listeners will report +1.
- 0 behavior/0 atomicity/0 prod/0 mutation on 3 crit (gamif/narr/channels-VIP) or contracts (EventBus/get_service/atomicity protected by golds + "MUST NOT").
- GSD log: .planning/quick/gsd-35-eventbus-logging-expansion.log (30+ entries, pre every + wc).
- decisions.md + PLAN + gsd + (post) SUMMARY/ROADMAP via documentador.
- F6 safe point. F7 self-check PASSED + handoff.
- "Item 3/35 closed. Third of new pool of 4. Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool. Ready for arch-enforcer + test-guardian + documentador (final pool close + ROADMAP update)."

(Refs: .planning/phases/35-eventbus-logging-expansion/PLAN.md + gsd-35-eventbus-logging-expansion.log + impact excerpts + HARDENING_ROADMAP pool34 + 23/24/28/29/34 precedents + services/event_bus.py + bot.py + besito/health + listeners in story/reward/broadcast/game/store/streak + tests/unit/test_event_bus.py + golds cross/reaction etc.)

## Admin forward besitos grant (Item 36 / pool de 1)

**Motivo:** Custodios necesitaban otorgar besitos manualmente a visitantes identificados por reenvío de mensaje. El flujo VIP forward ya existía; se extendió con menú de acción sin duplicar detección de usuario.

**Riesgos (mitigados):**
- Regresión VIP forward (antes auto-tarifa). Mit: tests regression + rama VIP intacta tras botón «Activar VIP».
- Atomicidad/EventBus en nuevo crédito ADMIN. Mit: reusa `credit_besitos` (FOR UPDATE + commit + schedule_emit best-effort); golds cross/reaction/daily/invariants verdes.
- Double grant por retry CB. Mit: `IdempotencyMiddleware` en confirm + 1 svc en confirm handler.

**Decisión:**
- Reenvío admin → menú `Activar VIP | Otorgar besitos | Cancelar` (0 svc en detección).
- FSM `AdminForwardStates` (reemplaza `VIPForwardActivationStates`).
- `BesitoService.grant_manual_admin_besitos` con `TransactionSource.ADMIN`, `MAX_ADMIN_BESITO_GRANT=10000`, `reference_id=admin_id`.
- Puros `build_forward_*` + `parse_positive_besito_amount`; `notify_forward_besitos_result` thin (0 svc).
- Handlers: 1 svc en `confirm_forward_besitos_grant` y `confirm_forward_vip_activation`; 1 svc en `select_forward_action_vip` (tarifas).

**Resultado:**
- 5 archivos tocados; 111 tests gate verdes; arch-enforcer PASS WITH NOTES (0 critical); test-guardian «suite protege adecuadamente».
- Refs: `.planning/phases/36-admin-forward-besitos-grant/PLAN.md` + SUMMARY + gsd log + impact/arch/test-guardian reports item36.

## VIP Subscriber Admin Profiles Etapa 1 (Item 36 — vip-subscriber-admin-profiles)

**Motivo:** `list_subscribers` en `vip_handlers.py` era plano (10 max), sin `is_admin`, sin paginación, sin perfil ni acciones; callback `list_subscribers_{channel_id}` muerto en teclado de canal.

**Riesgos (mitigados):**
- Kick sin `has_other_active` → expulsión indebida. Mit: `admin_revoke_subscription` copia contrato scheduler; tests unit mock bot.
- Débito besitos saldo negativo/EventBus. Mit: `has_sufficient_balance` + `debit_besitos` ADMIN sin emit; tests insufficient.
- Extend bypass `grant_internal_vip_access`. Mit: confirm handler llama solo ese método; test grep.

**Decisión:**
- Nuevo `handlers/vip_subscriber_admin_handlers.py`: lista 8/página, perfil, FSM extend/grant/debit/kick.
- `VIPService`: `get_subscriber_list_page`, `get_subscriber_admin_snapshot` (BesitoService local), `admin_revoke_subscription(bot)`.
- `BesitoService.debit_manual_admin_besitos` espejo grant.
- 5 `Subscriber*` CallbackData + 4 keyboards; wire `vip_management_keyboard` + channel VIP button.
- Eliminar handler `list_subscribers` de `vip_handlers.py`; forward L707+ intacto.
- Router registrado en `bot.py` tras `vip_router`.

**Resultado:**
- Gates 1/3–5 verdes (16+13+14+83); gate 2: 257 pass, 1 fail pre-existente store (no atribuible).
- Dead callback resuelto; `is_admin` 100% entrypoints; 1 svc/confirm; LucienVoice copy admin.
- Refs: `.planning/phases/36-vip-subscriber-admin-profiles/PLAN.md` + SUMMARY + `.planning/quick/gsd-vip-subscriber-admin-profiles.log`
