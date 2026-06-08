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
