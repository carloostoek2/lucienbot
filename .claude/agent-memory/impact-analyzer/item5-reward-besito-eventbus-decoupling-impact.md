---
name: item5-reward-besito-eventbus-decoupling
description: Impact analysis for Item 5: reduce direct BesitoService composition in RewardService using existing EventBus (post Item 1). Focus on missions/rewards vs gamification cross-domain coupling for BESITOS reward delivery.
type: project
---

# Impact Analysis Report: RewardService Besito Decoupling via EventBus (Item 5)

**Date:** 2026-06-07  
**Role:** impact-analyzer (Lucien Bot)  
**Feature:** Reduce direct composition of BesitoService inside RewardService (self.besito_service in __init__ + _deliver_besitos + close) by leveraging InternalEventBus (besitos_awarded) pattern introduced in Item 1. Align with domain ownership, less direct cross-domain (gamification vs missions/rewards), keep deliver_reward atomicity.  
**Context:** Follows EventBus PoC (narrative listener added as first subscriber; credit_besitos emits post-commit best-effort via schedule_emit). RewardService currently the only remaining? direct holder for *initiating* MISSION-sourced besitos credits (as part of unified reward delivery). Similar to pre-EventBus StoryService (which still initiates its own besito ops for costs/achievements but gained a listener). This is the automatic next item after critical tests.

## Executive Summary

**Current state (post-Item 1 + get_service unif + atomicity coverage):**
- `RewardService` (missions domain) unconditionally composes `self.besito_service = BesitoService(self.db)` in `__init__` (plus package/vip for other reward types).
- Only use of the besito collaborator: `async def _deliver_besitos` (called exclusively from `deliver_reward` when `reward.reward_type == RewardType.BESITOS`): does `credit_besitos(..., source=TransactionSource.MISSION, ...)` (which does its internal commit + `_schedule_besitos_awarded_event` best-effort), then `get_balance` for the success message returned to caller.
- `deliver_reward` (async, type dispatch): on success path does `log_reward_delivery` (separate commit for UserRewardHistory). Called primarily from `MissionService.increment_progress_and_deliver` (auto on mission complete, inside progress loop + final db.commit()).
- Other reward types (PACKAGE, VIP_ACCESS) use their own composed services (no besito).
- Besitos reward delivery is the mechanism for "recompensa de mision en besitos".
- Emission: every `credit_besitos` success (incl. those from reward deliver, daily_gift, broadcast reactions, game, story achievements, store? etc.) emits `"besitos_awarded"` (EVENT_BESITOS_AWARDED) post its own commit. Payload includes source, ref, etc. Bus: async gather + return_exceptions=True; schedule_emit for sync callers; errors per-listener logged/swallowed; never affects credit return value or causes rollback.
- StoryService precedent ("cómo StoryService fue actualizado"): Still holds `self.besito_service` (and uses it for `get_balance` pre-advance, `debit_besitos` for node costs with commit=False for atomicity with progress, `credit_besitos` inside `_grant_achievement` for reward_besitos on logros). Update was *adding* the listener `on_besitos_awarded_from_gamification` (owned in story_service.py at module level, narrative domain) + explicit central registration in `bot.py` on_startup. Listener is purely observational (logs "narrative | besitos_awarded_received | ..."); contract: **MUST NOT** credit/debit besitos (avoids re-entrancy/loop with its own _grant). Registered via `get_event_bus().register(...)`; documented in narrative/CLAUDE, gamification/CLAUDE, services/CLAUDE, decisions.md.
- Atomicity reality (validated by `test_cross_service_atomicity.py` + reaction flows): Credit (REACTION/DAILY_GIFT/MISSION etc.) commits independently. Post-credit: mission progress+deliver (separate tx via increment_and_deliver) + bus listeners (best-effort fire-and-forget) are "best effort". Partial failure contract is explicit and desired: e.g. reaction credit + progress complete can survive even if deliver_reward returns False early (inactive reward, package stock=0/not available_for_reward); no rollback of prior credit; no exception bubbles to reaction handler. Happy path: both REACTION + MISSION txs, balance = sum, progress complete. Tests use file SQLite + TestSession reopen + raw close/dispose for cross-commit visibility. deliver_reward success used only for logging "recompensa entregada" + history (if success).
- Call sites for deliver: almost exclusively internal to mission_service (auto); admin handlers use RewardService only for create/get/update (via get_service context); user claim flows go through mission increment. Backpack integration exercises deliver for history population.
- Direct composition sites for BesitoService overall (many, per domain initiating awards): reward, story, store, broadcast, daily_gift (lazy property), game, backpack (local), streak (local), + some handlers. Only narrative participates in *receiving* via bus so far.

**Key risks (atomicity + best-effort bus):**
- **Atomicity breaker if bus misused for delivery:** The besitos credit + MISSION tx + returned (success, balance msg) + subsequent history log are authoritative and synchronous within deliver_reward. Bus is explicitly *observational post-commit only* (see event_bus.py contract, besito _schedule, decisions.md: "Romper atomicidad del crédito... no"; "emit nunca afecta el retorno bool"). If refactor attempted to e.g. have RewardService emit a "besitos_reward_intent" and rely on a gamif listener (or vice-versa) to perform credit: (a) best-effort = may drop (schedule skips if no loop, listener error swallowed, no retry), (b) deliver would return success without credit/tx (or always fail), (c) callers (mission) see wrong balance/msg, (d) cross atomicity tests (happy + partials) and invariants would fail (no MISSION tx guaranteed synchronously, balance delta wrong), (e) history log would decouple from actual credit. Mitigation (required): **Keep direct synchronous credit_besitos call inside _deliver_besitos for BESITOS path** (the delivery *is* the credit for this reward type). Use bus exclusively for post-delivery notifications/observability (as with narrative).
- Listener failures never affect delivery (already true by bus design: gather return_exceptions, log only).
- Registration must be central/explicit in bot.py on_startup (no import side effects in domain modules, per PoC + decisions). Duplicates tolerated (bus appends); tests must use fresh InternalEventBus() or _reset for singleton cases.
- Removing `self.besito_service` attr will surface any hidden assumptions (tests, close hygiene, get_service lifecycle for subs). Only 1 direct access site found.
- RewardService still composes PackageService + VIPService (store/vip domain crosses for their reward types) — this item is scoped only to the gamif besito one.
- Source=MISSION in credits from rewards will be received by *all* listeners (incl. new rewards one + narrative); listener must not re-credit.
- Test patching: daily_gift exposes .besito_service (for patch.object in atomic fail case); reward's unit test currently does too for post-deliver balance. Post-change, patch sites for reward besitos credit would target the BesitoService class or credit_besitos path directly.
- Removability of bus (per decisions): still true; this item adds one more listener registration + def (easy to revert).

**Overall recommendation:** Proceed with tight scope (remove *held composition* / instance collaborator, keep local direct credit call for atomic delivery, *add* rewards-domain listener + registration to participate in EventBus pattern symmetrically to narrative). This reduces the "direct composition" surface (no self.besito_service collaborator owned by RewardService; coupling only on-demand inside the specific delivery method) while using the bus for cross-domain notification. 0 behavior change for callers, deliver_reward contracts, or atomicity. Verifiable with existing + 1-2 minimal test updates.

## Mapa de Impacto (archivos, cambios, listeners)

**Core services (reward domain):**
- `services/reward_service.py`:
  - Remove `from services.besito_service import BesitoService`? (keep if local instantiation used; lazy import inside _deliver_besitos possible for minimal surface like besito does for bus).
  - `__init__`: delete `self.besito_service = BesitoService(self.db)` line. (package_service + vip_service stay).
  - `_deliver_besitos`: refactor to local short-lived: `besito_service = BesitoService(self.db)` (or `from .besito_service import BesitoService; besito_service = BesitoService(self.db)` inside method) then use for credit + get_balance. Update docstring. (Still performs the cross call for delivery atomicity + msg.)
  - `deliver_reward` + `_deliver_*`: no logic change; success still triggers log_reward_delivery.
  - `close`: remove "besito_service" from the `for sub in (getattr(self, "besito_service", None), ...)` tuple + update comment ("Cerrar subs (inofensivo...)").
  - Add at module bottom (after history/stats, before/after the pattern of story): the listener owned by rewards/missions domain:
    ```python
    async def on_besitos_awarded_for_rewards(payload: dict) -> None:
        """Listener for 'besitos_awarded' (post-credit from any source incl. our own MISSION besitos reward deliveries).
        Best-effort, observational only (symmetric to narrative). Log + future e.g. stats/backpack hints. MUST NOT credit/debit (avoid loops).
        """
        uid = payload.get("user_id")
        amt = payload.get("amount")
        src = payload.get("source")
        ref = payload.get("reference_id")
        logger.info(f"rewards | besitos_awarded_received | user_id={uid} | amount={amt} | source={src} | ref={ref}")
    ```
  - Exports/docstrings: minor updates noting EventBus participation for besitos rewards.
  - (No new public API; deliver_reward contract unchanged.)

- `services/__init__.py`: No change required (listener not exported like story's; EVENT_BESITOS_AWARDED + get_event_bus already there for convenience).

**Registration / bootstrap:**
- `bot.py`:
  - Add import: `from services.reward_service import on_besitos_awarded_for_rewards` (alongside the story one).
  - In `on_startup`: after (or with) the narrative register: `get_event_bus().register(EVENT_BESITOS_AWARDED, on_besitos_awarded_for_rewards)`.
  - Update comments: "# Cross-domain listeners (explicit, central...) # ... narrative + rewards (mission besitos deliveries)".
  - Log: e.g. "Event listeners registrados (besitos_awarded -> narrative, rewards)".
  - (Import of EVENT/get_event_bus already present from Item 1.)

**Docs (must update for accuracy + cross-cutting rule):**
- `services/missions/CLAUDE.md`: 
  - In RewardService API / flujo: keep "llama internamente a BesitoService..." for BESITOS (truth for delivery); clarify it's the direct credit path (required for atomicity/success return).
  - Add new section at bottom: "## Cross-domain notifications (EventBus PoC Item 1)" modeled exactly on narrative/gamification ones. Explain: rewards domain initiates MISSION credits via local credit in deliver (for unified reward + history + msg); this emits besitos_awarded; owns listener here for post-delivery obs (logs); registration central in bot.py; listener best-effort + never re-enters besitos; ref to event_bus.py + bot.py + gamif CLAUDE.
- `services/CLAUDE.md`: Expand "Cross-cutting: Internal EventBus" to mention rewards domain as second subscriber (for its besitos reward deliveries) + narrative.
- `services/gamification/CLAUDE.md`: Optionally note "consumers: narrative (general besitos awards), rewards (MISSION reward deliveries)".
- `services/narrative/CLAUDE.md`: No change (or cross-ref).
- `decisions.md`: Add entry under EventBus section for Item 5 (tight scope, why kept direct credit, listener added for symmetry, risks/atomicity preserved, removable).
- `CLAUDE.md` (root) / architecture: No change (high level).
- Optional: `fases_refactor_testing.md` or refactor_testing.md append for the item.

**Other services/handlers (low/no impact):**
- `services/mission_service.py`: Calls deliver_reward unchanged (still gets success/msg for log). No besito import today; stays clean.
- `services/store_service.py`, `broadcast_service.py`, `story_service.py`, `game_service.py`, `daily_gift_service.py`, `backpack_service.py`: Unaffected (their own besito compositions for purchases/reactions/achievements/costs/daily remain; this item scoped to reward).
- Handlers (`mission_admin_handlers.py`, `reward_admin_handlers.py`, `reward_user_handlers.py` etc.): Use get_service(RewardService) or direct for creates; no besito access on reward instances. 0 changes.
- `services/event_bus.py`: No change (contract already supports multiple listeners).

**Tests (see dedicated section):**
- `tests/unit/test_reward_service.py` (1 site).
- `tests/unit/test_event_bus.py` (extend for new listener).
- `tests/integration/test_cross_service_atomicity.py` (verify no regression on MISSION paths).
- `tests/integration/test_mission_e2e.py`, `tests/integration/test_backpack_service.py` (deliver paths), `tests/integration/test_reaction_mission_flow.py` etc.: exercise indirectly; should pass as-is if credit path preserved.
- `tests/unit/test_besito_service.py`: Patches schedule_emit; will still be exercised by reward delivers (bonus coverage).
- No impact on middleware, handlers tests for rate/idemp (unless new listener side effects, which there aren't).

**New artifacts (minimal):**
- The listener def lives in reward_service.py (rewards domain ownership, like narrative).
- Report persisted here + MEMORY.md pointer.
- No new test files (extend existing per precedent: atomicity was extended, event_bus extended for narrative).

**0 prod behavior change expected.** Credit, tx, history, balance msgs, partial failure contracts, return values from deliver_reward all identical. Only internal structure (no more held besito collaborator on RewardService) + observability (extra listener).

## Tests críticos que se verían afectados o necesitarían nuevos / updates

**Affected (must fix for green):**
- `tests/unit/test_reward_service.py`:
  - `TestRewardServiceDelivery.test_deliver_reward_besitos`: 
    ```python
    # BEFORE (breaks post-removal):
    balance = service.besito_service.get_balance(sample_user.id)
    # AFTER (decouples test too; use independent instance on shared db_session):
    from services.besito_service import BesitoService
    balance = BesitoService(db_session).get_balance(sample_user.id)
    ```
  - Other delivery tests (package/vip/inactive/missing) unaffected (no besito access).
  - History/stats tests use direct log_ (not deliver); unaffected.
  - Creation/query tests: unaffected.
  - Opportunity: add small assert `assert not hasattr(service, 'besito_service') or service.besito_service is None` post-instantiation (but tight scope: just fix the one + let existing cover).

**Strongly recommend extend/verify (no breakage, coverage for new listener + regression on atomic flows):**
- `tests/unit/test_event_bus.py`:
  - Extend `test_narrative_listener_is_invoked_and_logs` or add parallel:
    ```python
    @pytest.mark.asyncio
    async def test_rewards_listener_is_invoked_and_logs(caplog):
        from services.reward_service import on_besitos_awarded_for_rewards
        bus = InternalEventBus()
        bus.register(EVENT_BESITOS_AWARDED, on_besitos_awarded_for_rewards)
        payload = {"user_id": 777, "amount": 42, "source": "MISSION", "reference_id": 99, ...}
        with caplog.at_level(logging.INFO):
            await bus.emit(...)
        assert any("rewards | besitos_awarded_received" in r.message and "source=MISSION" in r.message for r in caplog.records)
    ```
  - Existing `test_get_event_bus_singleton...` + registration tests remain valid.
- `tests/integration/test_cross_service_atomicity.py`:
  - `test_happy_path_reaction_credits_besitos_completes_mission_delivers_reward`: The inner `with patch("services.event_bus.schedule_emit")` (around reaction) will also capture the *subsequent* schedule from the mission deliver's besitos credit (source=MISSION). `assert mock_sched.called` stays true; no change needed. Post-deliver asserts on MISSION tx + balance delta + 8 total remain the verification that credit happened inside deliver.
  - Partial failure tests (inactive reward, package stock=0, already-completed): explicitly assert *no* MISSION tx / balance unchanged; these paths short-circuit before any _deliver_besitos credit, so unaffected.
  - Daily atomic sub-tests: touch daily's besito (via its lazy property), not reward; fine.
  - The dedicated `test_reward_redemption_deducts_and_registers_mission_tx`: just a marker; its contract still held by happy_path.
  - Bonus: could add inside happy_path (after patch block) a second patch or count for the MISSION source emit, but tight = no new code if not needed for gate.
- `tests/integration/test_mission_e2e.py` + `tests/integration/test_backpack_service.py` (deliver_reward success path that populates history):
  - Re-execute to confirm besitos reward still credits + logs history (backpack visible) + no double-close issues (RewardService with injected db_session never called .close() on self per its own test precedent).
- `tests/integration/test_reaction_mission_flow.py`, `tests/integration/test_reaction_full_chain.py`, `tests/integration/test_invariants.py`: indirect mission reward flows; re-run targeted to confirm MISSION txs + balances.
- `tests/unit/test_besito_service.py`: its schedule_emit patches will be hit more (via reward delivers in other tests); no edit.
- General: `tests/conftest.py` (no change); ensure db_session works for RewardService (it does).

**New tests? (tight scope: minimal / none required for green gate; add only if easy extension):**
- None strictly new files. The listener wiring is covered by extending event_bus unit (like narrative was).
- If time: one line in an existing reward unit or atomic happy_path to assert the event was scheduled for the *MISSION* credit specifically (e.g. separate patch around deliver only), but since patch during reaction already exercises schedule in deliver path indirectly, and besito unit + cross already assert emission for credits, low value for this item.
- No change to handler tests (delivery not directly callable from user reward handlers in current flows).

**Gates for this item (as in prior):** ruff clean, pytest -k "reward or atomicity or event_bus or mission" (or broader) pass, bot import/smoke, targeted cross flows. 0 unintended prod impact.

**Coverage lift:** RewardService delivery paths already well exercised; this tightens the internal collaborator surface + adds listener coverage parity with narrative. Atomicity contracts untouched (gold).

## Riesgos y Mitigaciones (énfasis atomicidad + bus best-effort)

1. **Romper entregas atómicas / contratos de deliver si credit movido al bus:**
   - Riesgo: deliver_reward success path, returned msg (incl. post-credit balance), MISSION tx creation, UserRewardHistory log, and caller (mission) "recompensa entregada" log all depend on sync credit result inside _deliver_besitos.
   - Si se usara bus para "trigger delivery": listeners best-effort (schedule may noop, gather swallows errors, no await in credit path), crédito podría no ocurrir o ocurrir post-return → partials tests fallan (MISSION tx count==0 en happy), balances incorrectos, mensajes de Lucien rotos, mochila history inconsistente.
   - Mitigación (en scope propuesto): **Mantener llamada directa síncrona a credit_besitos (local instance) dentro de _deliver_besitos para el path BESITOS.** El bus se usa *solo* para notificación post-facto (el emit ya ocurre dentro de credit post-commit; nuevo listener en rewards solo observa). Esto preserva exactamente los asserts en test_cross... (tx sources REACTION+MISSION, deltas exactos, balance final, early-False paths sin MISSION tx).
   - Adicional: log_reward_delivery sigue después del if success del credit (ya es post-commit separado; tolerado por diseño).

2. **Listeners que fallan afectan delivery:**
   - Riesgo: Si listener en rewards (o narrative) raise, podría (erróneamente) pensarse que impacta commit de credit o deliver.
   - Mitigación: Ya por contrato del bus (emit usa gather(return_exceptions=True); per-listener warning log only; never propagates to schedule_emit caller or credit_besitos). Prueba en test_event_bus.py (one listener fails, others execute, no exception to awaiter). Listener en rewards seguirá la regla explícita: solo log, nunca credit/debit.

3. **Necesidad de inyección / registro central:**
   - Riesgo: Si registro del listener se hace via import-time side-effect en reward_service.py (o mission), viola PoC rules + decisions ("explícito y central en bot.py", "no import side-effects").
   - Mitigación: Seguir patrón exacto de narrative: def listener en reward_service.py (ownership del dominio), import + `get_event_bus().register` solo en bot.py on_startup (después de scheduler). Tests usan fresh bus o _reset_event_bus_for_tests(). Singleton get_event_bus() para runtime, fresh para unit bus tests.
   - En get_service / context: listeners son globales al bus, no por instancia de servicio; no impacto.

4. **Test breakage + patching assumptions:**
   - Riesgo: Cualquier código que hace `reward_svc.besito_service` (o patch.object(reward_svc.besito_service...)) falla. (Daily expone via property para sus patches en atomic.)
   - Mitigación: Solo 1 site (unit reward besitos test balance assert) → fix a independent BesitoService(db) (mejora: test ya no asume composición interna). Para futuro patch del credit *dentro de deliver besitos* (raro), usar `patch("services.besito_service.BesitoService")` o patch en el módulo reward si se quiere. Cross atomic usa su propio besito_svc para queries post; no tocan reward's.
   - Lifecycle/close: RewardService tests (incl. history in backpack integ) *nunca* llaman close() en instancias con db inyectado (precedente explícito); subs close es best-effort. Remover besito reduce una llamada; seguro.

5. **Duplicación / loops / source confusion:**
   - Riesgo: Listener en rewards recibiendo su propio MISSION credit → si código futuro hace credit de nuevo = loop o conteo doble.
   - Mitigación: Documentar en listener + missions/CLAUDE (copiar de narrative): "MUST NOT call credit/debit besitos". El source=MISSION en payload permite filtrar si se extiende, pero PoC solo log. "besitos_awarded" event vs campo local en reaction_result/BroadcastReaction ya documentado/distinguido en decisions + tests (local value unchanged).
   - Múltiples listeners: bus soporta (append); ambos narrative + rewards recibirán todo (incl. DAILY, REACTION, GAME, etc.). Deseado para observabilidad.

6. **Otros menores:**
   - Removibilidad del bus: agregar 1 registro + 1 def de listener + 2 líneas en bot = fácil revertir (borrar listener def + registro + imports; zero residual en reward).
   - get_service unif: handlers que hacen with get_service(RewardService) as r: r no expondrá .besito_service (ya no lo hacía para callers externos de forma pública); interno solo.
   - Performance: local BesitoService(self.db) por deliver besitos (raro, solo en mission complete) = negligible vs held instance.
   - VIP/Package crosses en RewardService quedan (necesarios para tipos no-besitos); este item solo gamif.

**Mitigación general:** Tight scope + "no prod changes" + re-ejecutar exactamente los tests que cubren deliver besitos paths + event wiring + atomic partials/happy. GSD workflow + ruff + pytest gates antes de cualquier edit (aunque aquí análisis + solo memoria report).

## Scope propuesto para la primera entrega (tight, verificable, alineado con EventBus pattern)

**Tight scope (mínimo verificable, 0 comportamiento observable cambiado, sigue "services dueños de dominio" + "menos acoplamiento directo" + EventBus para cross notifications):**

1. **services/reward_service.py (principal):**
   - Remover línea de composición en `__init__`: `self.besito_service = BesitoService(self.db)`.
   - Mantener import o hacerla lazy dentro de _deliver (para reducir surface).
   - Refactor _deliver_besitos: crear instancia local corta-vida solo para el crédito + balance (ej. `besito_service = BesitoService(self.db)` al inicio del método). Mantener lógica idéntica (crédito síncrono, source=MISSION, ref=reward.id, success + balance en msg).
   - Actualizar `close()`: quitar besito_service del tuple de subs + comentario.
   - Añadir (al final del archivo, ownership rewards domain, paralelo a story):
     - `async def on_besitos_awarded_for_rewards(payload: dict) -> None:` (log "rewards | besitos_awarded_received | ..." usando campos del payload; comentarios explicitando best-effort + NO credit/debit).
   - Actualizar docstrings de deliver_reward / _deliver_besitos para mencionar que para BESITOS el crédito emite besitos_awarded (post-commit, para listeners como narrative/rewards).
   - (Opcional tight: añadir nota en create_reward_besitos etc.)

2. **bot.py:**
   - Importar el nuevo listener desde reward_service (junto al de story).
   - En on_startup (bloque de listeners): registrar también el de rewards.
   - Actualizar comentarios/logs para reflejar "narrative + rewards".

3. **Docs (mínimos pero obligatorios para mantener coherencia):**
   - `services/missions/CLAUDE.md`: Actualizar sección RewardService API/flujo (si menciona "llama internamente"); + nueva subsección "Cross-domain notifications (EventBus PoC Item 1)" describiendo emisor (credit en deliver para BESITOS), listener aquí, registro central, best-effort, refs.
   - `services/CLAUDE.md`: Mencionar rewards como subscriptor en cross-cutting EventBus.
   - `decisions.md`: Entrada breve para Item 5 (scope tight, atomicidad preservada manteniendo crédito directo, listener añadido para simetría con narrative, riesgos mitigados, bus removable).
   - (Opcional: gamification/CLAUDE cross-ref.)

4. **Tests (mínimo para verde + wiring):**
   - Fix único site en `tests/unit/test_reward_service.py::test_deliver_reward_besitos` (usar BesitoService(db_session) independiente para get_balance post-deliver; esto también reduce acoplamiento del test).
   - Extender `tests/unit/test_event_bus.py` con test análogo al de narrative listener (register + emit + assert log "rewards | ..."; usa fresh bus).
   - Re-ejecutar (sin editar): reward unit, cross_service_atomicity (happy/partials), mission_e2e, backpack deliver history, reaction_mission, besito (patches), event_bus. Confirmar: deliver besitos sigue produciendo MISSION tx + balance + history; schedule_emit se llama; listeners (narrative + nuevo) se invocan en eventos MISSION; partials siguen sin tx extra; ningún "service.besito_service" en reward expuesto.

**No scope (out of tight):**
- No tocar otras composiciones de BesitoService (store, broadcast, story, daily, game...); este item es específico Reward.
- No cambiar contratos de deliver_reward, increment_progress_and_deliver, o tx sources.
- No mover crédito fuera de deliver (rompería ownership + atomicidad).
- No inyección de bus o listeners (sigue patrón singleton PoC + central register).
- No nuevos archivos de test o handlers.
- No updates a atomicity tests más allá de re-run (contratos intactos).
- No close() calls en tests de reward (siguen precedente de nunca cerrar inyectados).
- Futuro (post-entrega): aplicar patrón similar a otros iniciadores si se desea (e.g. daily_gift podría exponer menos); extender listener rewards para lógica real (e.g. backpack refresh hints); property tests de "nunca besitos MISSION sin history entry".

**Verificabilidad de la entrega:**
- Post-cambio: `RewardService(db).besito_service` AttributeError (o no expuesto).
- `deliver_reward(..., BESITOS)` sigue retornando success + msg con balance actualizado; crea BesitoTransaction source=MISSION + UserRewardHistory.
- `get_event_bus()` tiene 2+ listeners para el event; emitir uno con source=MISSION causa logs de ambos "narrative | ..." y "rewards | ...".
- Todos los tests de reward delivery + atomic happy/partials + event wiring pasan sin reg.
- Ruff limpio; imports bot limpios; logs siguen convención "módulo | acción | user_id | ...".
- 0 diffs en comportamiento para visitantes/custodios.

**Alineación:**
- Reglas: handlers 1-service (ya), services dueño dominio (rewards sigue owning deliver + history; gamif owning credit/emission), <50 LOC (local instanciación cabe), logging, EventBus para cross notifications (no duplicación).
- Voz Lucien / arquitectura: sin cambios visibles.
- GSD: este análisis es pre-edit (report solo en memoria); cualquier impl futura usaría /gsd:execute-phase o quick + gates.
- Removable: sí.

Este scope es el "primera entrega" tight recomendado: reduce la composición directa (de held collaborator a local on-demand), incorpora rewards al EventBus (listener + registro), mantiene atomicidad 100%, mínimo churn en tests/docs, verificable inmediatamente.

**Handoff:** Listo para GSD + impl si se aprueba. Persistido en agent-memory para contexto futuro (ver MEMORY.md). Prior item4 tests + este análisis cierran el batch de EventBus follow-ups.

---
**Fin del reporte de impacto (Item 5).** Hecho con precisión para preservar contratos de Lucien Bot.
