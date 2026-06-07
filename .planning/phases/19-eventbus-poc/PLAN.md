# PLAN: Internal EventBus PoC + besitos_awarded (Item 1)

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-06-07  
**Focus:** Conservative, tight PoC for cross-domain notifications. First real use case: gamification (BesitoService.credit_besitos) emits "besitos_awarded" after successful DB commit; narrative domain receives as first listener.  
**Input principal (source of truth):** Impact-analyzer report + exhaustive discovery (call-site map, risks, recs synthesized from greps/reads of besito_service, broadcast_service, story_service, reward, daily_gift, game_service, models, tests (cross atomicity, reaction chains, invariants), bot.py, services/*_CLAUDE.md, architecture.md, rules.md, decisions.md, middleware-hardening impact report pattern, fases_refactor_testing.md patterns).  
**GSD enforcement:** Executor MUST prefix every modification with GSD log append via run_terminal_command to `.planning/quick/gsd-eventbus-poc-item1.log` (see Instructions for gsd-executor).

---

## 1. Alcance preciso (In / Out explícito)

### En esta entrega (PoC enfocada, "tight" como recomendó analyzer):
- Implementación mínima del Internal EventBus (async fanout con `asyncio.gather(..., return_exceptions=True)` siguiendo el patrón demostrado en `tests/unit/test_broadcast_service_reaction_flow.py:285-301`).
- Emit **solo** en la ruta de éxito de `credit_besitos` (post `db.commit()` exitoso, dentro del try; nunca afecta retorno bool ni rollback).
- Un (1) listener real en el dominio narrative (recibe, loguea con contexto user_id/amount/source, prueba de wiring; no genera nuevos besitos para evitar loops con el crédito inverso que ya hace StoryService en `_grant_achievement`).
- Registro central explícito (no side-effects mágicos en imports si posible).
- Tests unit puros para el bus + verificación de emit desde besito (con mocks).
- Actualizaciones mínimas en tests de integración críticos (atomicity, reaction full chain, etc.) para probar que no se rompió nada + opcionalmente que el emit ocurrió (vía patch).
- Actualizaciones de docs/CLAUDEs (services, gamification, narrative, decisions.md) + verificación gates.
- Todo sigue reglas: handlers llaman exactamente 1 service (sin cambios en handlers); funciones ≤50 LOC; logging "módulo | acción | user_id | resultado".

### Fuera explícitamente (no scope creep):
- **NO** eliminar ni consolidar instanciaciones directas de `BesitoService()` (hay ~60+ en services, handlers y tests; analyzer + prompt prohíben intentarlo en esta iteración).
- **NO** otros eventos (solo "besitos_awarded").
- **NO** cambios en `debit_besitos` u otros paths de besitos.
- **NO** cambios en flujos existentes de side-effects "best effort" (el post-commit de misiones en `broadcast_service.check_and_register_reaction` se mantiene intacto; el nuevo emit es adicional y también best-effort).
- **NO** inyección de bus en BesitoService (para minimizar diff; usamos singleton/getter interno).
- **NO** listeners en otros dominios (solo narrative como primero).
- **NO** persistencia de eventos, retry policies complejas, o topics avanzados.
- **NO** migraciones, modelos nuevos, o cambios en TransactionSource/BesitoTransaction.
- **NO** afectar los tres sistemas críticos más allá de lo necesario: gamification (emitter), narrative (listener), y nota de que channel_admin/VIP paths que involucren créditos indirectos (pocos) no se tocan en lógica.

**Justificación del scope (del impact map):** credit_besitos es el punto de emisión natural y único para "awarded". Llamadores clave (broadcast reactions con su "besitos_awarded" local en el dict de retorno, daily, reward, game, story achievements) deben seguir funcionando idéntico. El emit es observacional y post-commit.

---

## 2. Fases ordenadas (5 fases pequeñas y verificables)

### Fase 1: Bus implementation + unit tests (aislado, zero wiring en prod)

**Objective:** Entregar un InternalEventBus funcional, testeable, que implementa el contrato del skill (async gather + return_exceptions; errores de listeners no propagan al emisor ni afectan otros listeners). Sin tocar besito_service ni bot.

**Definition of Done (checklist):**
- [ ] Archivo nuevo `services/event_bus.py` con clase `InternalEventBus`, constantes `EVENT_BESITOS_AWARDED = "besitos_awarded"`, método `register(event: str, listener: Callable[[dict], Awaitable])`, y `async def emit(self, event: str, payload: dict)`.
- [ ] `emit` usa `asyncio.gather(*[listener(p) for ...], return_exceptions=True)`, procesa resultados, loguea por listener (incluyendo errores), **nunca** levanta excepción al caller.
- [ ] Helper interno `_schedule_emit(coro)` o equivalente para uso desde código sync (usa `asyncio.get_running_loop().create_task(...)` con try/except RuntimeError para "no running loop"; en ese caso log + skip o asyncio.run solo si seguro — documentar decisión).
- [ ] `get_event_bus()` (o singleton module-level) para acceso fácil (similar espíritu a `get_scheduler`).
- [ ] Nuevo test `tests/unit/test_event_bus.py` con ≥5 tests: register multiple, emit llama a todos, un listener falla (return_exceptions: otros se ejecutan, awaiter no recibe exc, log de error), payload intacto, evento desconocido es no-op.
- [ ] Ruff limpio en archivos nuevos.
- [ ] Tests unit del bus 100% verdes (`pytest -k "event_bus or TestInternalEventBus"`).
- [ ] GSD logs pre cada edit + final de fase.
- [ ] Safe point: el bus es completamente removable (borrar archivo + test no afecta nada).

**Archivos exactos:**
- Crear: `services/event_bus.py`
- Crear: `tests/unit/test_event_bus.py`
- Modificar (solo si necesario para exports iniciales): `services/__init__.py` (agregar "InternalEventBus", "get_event_bus", "EVENT_BESITOS_AWARDED" a __all__ y from .event_bus — decisión del executor; mínimo impacto).

**Cambios clave (bullets accionables):**
- En `event_bus.py`: logging con `f"event_bus | emit | event={event} | listeners={n} | errors={e}"` (incluir user_id del payload cuando aplique).
- Implementar listeners como `async def (payload: dict)`.
- Exportar constante del nombre de evento para evitar typos.
- Docstrings claros con "DESIRED CONTRACT" (patrón de tests exitosos previos).
- No depende de DB ni services; puro.

**Tests que deben estar verdes antes de avanzar:**
- `pytest -k "event_bus" -q --tb=line` (verde limpio).
- `pytest tests/unit/test_event_bus.py -q`.
- Ruff en los dos archivos.
- (Opcional smoke) `python -c "from services.event_bus import get_event_bus, EVENT_BESITOS_AWARDED; print('import ok')"`

**Riesgos + mitigaciones:**
- Over-engineering del bus: mitigar con impl mínima (dict de listeners, gather simple).
- Test isolation (global listeners afectan otros tests): los tests del bus usan **instancia fresca** `bus = InternalEventBus()`; no tocan el getter singleton.
- "No running loop" en schedule: documentar y hacer best-effort (log + skip); PoC no requiere emit en contextos puramente sync sin loop (scheduler jobs que llamen credit son raros y pueden adaptarse después).

**Rollback / safe point:** Borrar `services/event_bus.py` + su test + cualquier import temporal en __init__. No hay otros cambios. Commit intermedio recomendado.

---

### Fase 2: Wiring del emit en credit_besitos (post-commit exitoso)

**Objective:** Modificar **solo** `besito_service.py` para emitir el evento **después** del `db.commit()` exitoso en `credit_besitos`. El crédito y su retorno (bool + side effects en DB) permanecen idénticos e atómicos. Emit es best-effort y nunca falla el path de crédito.

**Definition of Done (checklist):**
- [ ] En `credit_besitos`, inmediatamente después de `db.commit()` (línea ~118 en la versión actual) y **antes** del log de éxito o return True, construir payload y disparar el emit de forma segura (no await en hot path).
- [ ] El emit captura: user_id, amount, source (como .value str), reference_id, description, timestamp (isoformat UTC).
- [ ] Todo el bloque de emit está dentro de `try: ... except Exception as e: logger.warning(f"event_bus | emit_failed | user_id={user_id} | error={e}")` — **nunca** rollback ni return False por esto.
- [ ] Logging adicional post-emit (o dentro del bus): "besito_service | credit_besitos | user_id=... | result=credited amount=... source=... event_emitted=best_effort".
- [ ] `besito_service.py` sigue ≤50 LOC por función (el emit wrapper es pequeño; si excede, extraer helper privado).
- [ ] Unit tests de besito (existentes) siguen pasando + nuevo test/assert de que el bus fue notificado (vía patch).
- [ ] No se toca `debit_besitos`, `get_*`, ni nada más.
- [ ] GSD pre-logs + ruff + pytest targeted verdes.

**Archivos exactos:**
- Modificar: `services/besito_service.py` (solo la función `credit_besitos`, imports mínimos al tope).
- (Posible) ligero update en `tests/unit/test_besito_service.py` para el assert de emit (ver Fase 4 si se prefiere agrupar).

**Cambios clave (bullets accionables):**
- Import: `from .event_bus import get_event_bus, EVENT_BESITOS_AWARDED` (o import inside the try para lazy).
- Después del commit exitoso:
  ```python
  try:
      bus = get_event_bus()
      payload = {
          "user_id": user_id,
          "amount": amount,
          "source": source.value if hasattr(source, "value") else str(source),
          "reference_id": reference_id,
          "description": description,
          "timestamp": datetime.now(UTC).isoformat(),
      }
      _schedule_event(bus.emit(EVENT_BESITOS_AWARDED, payload))  # helper que hace create_task con gather interno
  except Exception as emit_err:
      logger.warning(f"event_bus | emit_failed_post_credit | user_id={user_id} | error={emit_err}")
  ```
- Mantener el log original de "Acreditados {amount}...".
- Asegurar que si no hay loop running, el schedule no crashea el crédito (ver decisión de diseño).

**Tests que deben estar verdes antes de avanzar (pre-cualquier edit de esta fase y post):**
- `pytest -k "TestBesito or credit_besitos or besito" --tb=line -q` (todos los unit de besito).
- `pytest tests/unit/test_besito_service.py -q`.
- Los tests de broadcast reaction que ejercitan credit internamente: `pytest -k "reaction or broadcast" -q --tb=line` (al menos los unit; integ se fortalecen en Fase 4).
- Ruff en besito_service.py.

**Riesgos + mitigaciones:**
- Romper atomicidad del crédito: mitigar — emit **después** de commit, fuera del bloque de balance/tx, wrapped. El commit del crédito ya sucedió; listeners son observadores.
- Excepción en schedule desde sync: mitigar con el helper que atrapa RuntimeError y solo loguea.
- "besitos_awarded" confusion con el campo local de BroadcastReaction: el event es general; el dict de retorno de check_and_register_reaction se mantiene exactamente igual (no se toca broadcast_service en esta fase).
- Logging duplicado o verboso: usar el formato estándar del proyecto.

**Rollback / safe point:** Revertir solo el bloque try/except de emit en credit_besitos (dejar el import si se quiere, o quitar). El crédito funciona exactamente como antes. Git revert de la diff de esta fase es safe. No afecta callers.

---

### Fase 3: Primer listener en narrative + registro central

**Objective:** Conectar el dominio narrative como primer subscriptor real del evento. Probar el flujo gamif → bus → narrative sin acoplamiento directo (narrative no "importa" lógica de gamif para enterarse de awards; solo se registra).

**Definition of Done (checklist):**
- [ ] Listener implementado (async def) que recibe el payload, loguea con formato "narrative | besitos_awarded_received | user_id=... | amount=... | source=... | ref=...", y hace algo "real pero seguro" (p.ej. best-effort check de logros o simplemente prueba de wiring; **no** llama credit_besitos de vuelta).
- [ ] El listener puede vivir dentro de `services/story_service.py` (como método privado `_on_besitos_awarded` o standalone async en el módulo) o un archivo pequeño nuevo si el executor decide (preferiblemente mínimo: dentro de story_service.py para ownership del dominio).
- [ ] Registro explícito y central: preferiblemente en `bot.py` (en `on_startup` o una función `setup_event_listeners()` llamada desde allí), usando `get_event_bus().register(EVENT_BESITOS_AWARDED, listener)`. Alternativa: helper `register_narrative_listeners()` en el módulo de story que el bot llama. Decisión documentada.
- [ ] Si el listener necesita DB (p.ej. para consultar progreso de story), usa `with get_service(StoryService) as story: ...` (o crea listener que capture el patrón).
- [ ] Import de story_service o narrative bits **no** causa side effects de registro automáticos (explícito es mejor).
- [ ] bot.py se modifica solo para el registro (agregar import + llamada en startup; mantener on_startup limpio).
- [ ] Test de integración ligero o unit que prueba "narrative listener fue invocado" (vía patch o spy en el bus) cuando se hace un crédito vía daily/reaction/etc.
- [ ] No se rompe el crédito inverso que story ya hace (en _grant_achievement).

**Archivos exactos:**
- Modificar: `services/story_service.py` (agregar el listener func + quizás un método público o privado para futuro "on_besitos_earned").
- Modificar: `bot.py` (agregar import del bus y del listener o setup; llamada en on_startup o post-init).
- (Opcional conservador) Modificar: `services/__init__.py` para re-exportar si ayuda al registro.
- Tests: updates o nuevo test simple (puede ser en existing test_besito o un integration smoke).

**Cambios clave (bullets accionables):**
- En story_service (o módulo): definir
  ```python
  async def on_besitos_awarded_from_gamification(payload: dict):
      uid = payload.get("user_id")
      amt = payload.get("amount")
      src = payload.get("source")
      logger.info(f"narrative | besitos_awarded_received | user_id={uid} | amount={amt} | source={src}")
      # PoC real pero mínimo: aquí podría ir lógica futura de "progreso narrativo por besitos" sin side effects de crédito.
  ```
- En bot.py (on_startup, después de scheduler):
  ```python
  from services.event_bus import get_event_bus, EVENT_BESITOS_AWARDED
  from services.story_service import on_besitos_awarded_from_gamification  # o donde viva
  get_event_bus().register(EVENT_BESITOS_AWARDED, on_besitos_awarded_from_gamification)
  ```
- Logging sigue reglas del proyecto.
- El listener **debe** ser async (para el gather del bus).

**Tests que deben estar verdes antes de avanzar:**
- Todos los de Fase 2 + Fase 1.
- `pytest -k "story or narrative" -q --tb=line` (unit de story, especialmente los que tocan _grant_achievement que hace credit).
- Smoke de startup si posible (o al menos import bot sin crash).
- Cualquier nuevo test que verifique "listener narrative recibió" verde.

**Riesgos + mitigaciones:**
- Loop de créditos (narrative recibe → credit → re-emit → ...): mitigar — PoC listener **no** acredita besitos. Futuro código en listener debe chequear source o usar flag si quiere evitar.
- Registro demasiado temprano/tarde: registrar en on_startup después de init_db es seguro (bus no depende de DB).
- Múltiples registros en tests/reloads: hacer register idempotente (chequear si ya está) o usar lista y permitir duplicados con cuidado; para PoC, tests que necesiten pueden usar instancia fresca o limpiar.
- Impact en critical systems: narrative listener es best-effort; si falla, solo se loguea (gracias al bus).

**Rollback / safe point:** Quitar la llamada de register en bot.py y el def del listener en story. El emit de Fase 2 sigue existiendo pero sin suscriptores (inofensivo). Revertir estas dos diffs es seguro. Créditos y todo lo demás intacto.

---

### Fase 4: Actualizaciones de tests / integration (atomicity, reaction, mission, story, daily, game paths)

**Objective:** Fortalecer la protección de regresión en los flujos que ejercitan credit_besitos (especialmente los "cross service atomicity" y reaction chains que el analyzer identifica como críticos). Asegurar que el nuevo emit no rompe balances, misiones post-commit, "besitos_awarded" en retornos de broadcast, ni los tests de story achievements que acreditan besitos.

**Definition of Done (checklist):**
- [ ] En tests de besito unit: patch del bus (o del get_event_bus) y asserts de que se llamó con payload correcto en success paths; no se llama en early returns (amount <=0).
- [ ] En `tests/integration/test_cross_service_atomicity.py`, `test_reaction_full_chain.py`, `test_reaction_mission_flow.py`: 
  - Asegurar que los patches existentes de MissionService siguen funcionando.
  - Agregar o asegurar patch/spy del event bus (o aceptar que con listeners registrados el emit corre como best-effort).
  - Re-asserts estrictos de balances post-crédito, reaction rows, "besitos_awarded" en dicts de retorno, misiones completadas.
  - Al menos un escenario donde se verifica que "el emit habría ocurrido" (contador o mock call).
- [ ] Tests de story que otorgan besitos por achievement (test_story_service.py y relacionados) siguen pasando (crédito funciona, emit se dispara pero listener no altera el flujo).
- [ ] Tests de daily_gift, game_service paths que usan credit (unit/integ existentes) no requieren cambios grandes, pero smoke/run targeted confirma 0 regresiones.
- [ ] Uso de mocks para el bus en la mayoría de tests (aislamiento).
- [ ] Todos los targeted gates verdes + ruff.
- [ ] Actualizar docstrings "DESIRED CONTRACT" donde se mencione el flujo post-credit (misiones + ahora events).

**Archivos exactos (principales):**
- `tests/unit/test_besito_service.py`
- `tests/integration/test_cross_service_atomicity.py`
- `tests/integration/test_reaction_full_chain.py`
- `tests/integration/test_reaction_mission_flow.py`
- `tests/unit/test_story_service.py` (y cualquier que toque grant achievement)
- Posiblemente `tests/integration/test_invariants.py` (si toca credits)
- Cualquier otro que el executor descubra vía grep "credit_besitos" en tests/ (pero solo editar los críticos; no scope creep).

**Cambios clave (bullets accionables):**
- Agregar `from unittest.mock import patch, AsyncMock` donde falte.
- Ejemplo de assert:
  ```python
  with patch("services.besito_service.get_event_bus") as mock_get_bus:
      mock_bus = MagicMock()
      mock_bus.emit = AsyncMock()
      mock_get_bus.return_value = mock_bus
      result = svc.credit_besitos(...)
      assert result is True
      mock_bus.emit.assert_awaited_once()  # o verificado vía schedule
      # o para fire-forget: assert mock_get_bus.called
  ```
- Para integ con SQLite+TestSession: patch antes de crear los services que llaman credit, o después de setup registrar un listener mock en el bus real.
- Mantener asserts de `reaction_result["besitos_awarded"] == expected` exactamente como están (el event no cambia ese contrato local de broadcast).
- En cross atomicity: documentar que ahora post-credit hay "misiones (best effort) + event listeners (best effort)".

**Tests que deben estar verdes antes de avanzar:**
- `pytest -k "cross_service_atomicity or TestCrossServiceAtomicity or reaction_full_chain or reaction_mission or atomicity" -q --tb=line`
- `pytest -k "besito or TestBesitoService or credit_besitos" -q`
- `pytest -k "story or TestStoryService" -q`
- `pytest -k "daily or DailyGift" -q` (smoke)
- `pytest -k "game or trivia or dice" -q` (smoke, ya que game_service hace muchos credits)
- Full targeted from analyzer recs: combinar con `or gamification or broadcast`.
- 0 regressions en broader smoke si se corre (pero no requerido si targeted pasa limpio).

**Riesgos + mitigaciones:**
- Tests flaky por listeners globales: usar patch o `bus = get_event_bus(); bus._listeners = {}` reset en fixture, o preferir patch en el módulo de besito.
- "besitos_awarded" asserts rotos: no se tocan los retornos de broadcast; solo se añade observabilidad.
- Cobertura de "emit fallando": agregar un test donde el listener mockeado levanta, y se verifica que el crédito/return/misión siguen OK (el bus ya lo garantiza).

**Rollback / safe point:** Revertir solo los edits de test (los asserts de emit y patches). La prod (emit + listener) puede quedarse o revertirse independientemente (Fase 2/3 rollbacks). Tests son aditivos.

---

### Fase 5: Docs + verificación final + handoff

**Objective:** Cerrar la entrega con documentación actualizada, gates completos, y preparación para arch-enforcer + test-guardian. Dejar el sistema listo para que "el siguiente Item" pueda agregar más listeners o eventos sin sorpresas.

**Definition of Done (checklist):**
- [ ] Actualizar `services/gamification/CLAUDE.md`: mencionar que BesitoService ahora emite "besitos_awarded" vía InternalEventBus post-commit (best effort); otros dominios pueden subscribirse.
- [ ] Actualizar `services/narrative/CLAUDE.md`: mencionar el listener para besitos_awarded (propósito, que es best effort, ownership del wiring).
- [ ] Actualizar `services/CLAUDE.md` o `services/__init__.py` docs si se exporta el bus.
- [ ] Actualizar `decisions.md`: agregar entrada para "Internal EventBus (Fase X / Item 1)" con motivo (loose coupling cross-domain sin romper handlers 1-service ni atomicity), patrón usado (gather+return_exceptions), y nota de PoC conservadora.
- [ ] (Opcional) Actualizar root `CLAUDE.md` en la sección de dominios o seguridad/cross-cutting si corresponde.
- [ ] Grep confirmando que "besitos_awarded" en contextos de broadcast/reaction sigue siendo el campo local (no confundir con el event).
- [ ] Todos los gates: ruff format/check --fix en archivos tocados; pytest targeted (ver lista en estrategia de tests) limpio 0 failures; smoke de imports y bot startup (python -c "import bot; ..." o similar).
- [ ] GSD log final de la fase + summary de commits/refs.
- [ ] Hand-off note: lista de tests críticos que deben re-correr en cualquier futuro cambio a credit_besitos o al bus (la misma que en estrategia).
- [ ] Verificación manual de que handlers siguen llamando exactamente 1 service (grep rápido en handlers/ que tocan besitos: gamification_user, store_user, etc. — no deben haber cambiado).

**Archivos exactos:**
- `services/gamification/CLAUDE.md`
- `services/narrative/CLAUDE.md`
- `services/CLAUDE.md` (si aplica)
- `decisions.md`
- `.planning/quick/gsd-eventbus-poc-item1.log` (append final)
- Posiblemente `fases_refactor_testing.md` o ROADMAP si se quiere trackear (pero conservador: no obligatorio para PoC).

**Cambios clave (bullets accionables):**
- En CLAUDEs: agregar sección corta "Cross-domain notifications" o "EventBus integration" con 2-3 bullets + "ver services/event_bus.py".
- En decisions.md: seguir el estilo de la entrada de "Middleware centralization (gsd-mw-hardening)".
- Añadir al final de la sección de besito en gamification CLAUDE: "Emite 'besitos_awarded' después de commit exitoso (Fase Item 1). Primer subscriptor: narrative."
- Confirmar logging en el emit path sigue "módulo | acción | user_id | resultado".

**Tests / verificación que deben estar verdes antes de "done":**
- Todos los targeted de Fase 4 + 1-2.
- `ruff check services/event_bus.py services/besito_service.py tests/unit/test_event_bus.py ... --fix`
- `pytest -k "event_bus or besito or reaction or cross_service_atomicity or story" -q --tb=no` (resumen limpio).
- Comando de smoke: `python -c "
from services import get_event_bus, EVENT_BESITOS_AWARDED
from services.besito_service import BesitoService
print('imports ok')
bus = get_event_bus()
print('bus listeners for besitos_awarded:', len(bus._listeners.get(EVENT_BESITOS_AWARDED, [])))
" `
- Revisión rápida: `grep -n "BesitoService()" handlers/ | cat` (para confirmar que no tocamos nada allí).

**Riesgos + mitigaciones:**
- Doc drift: actualizar las CLAUDEs de los dominios directamente afectados (gamif + narrative) + decisions es mínimo pero suficiente para PoC.
- "Arch-enforcer va a quejarse": el plan incluye criterios explícitos (ver sección 6) para que executor pase antes de handoff.

**Rollback / safe point:** Revertir solo los archivos de docs (decisions, CLAUDEs). El código de bus + emit + listener puede quedarse (es funcional) o revertirse por fases (Fase 3 → 2 → 1). Docs son los últimos y más seguros de revertir.

---

## 3. Estrategia de tests detallada

**Unit (aislados, rápidos, determinísticos):**
- `tests/unit/test_event_bus.py` (nuevo): 5+ tests puros sobre la clase (instancia local, no singleton). Cubre: múltiples listeners, gather con return_exceptions (un falla, los demás corren, resultado del gather no propaga), payload forwarding, registro idempotente o duplicados tolerados, evento sin listeners.
- `tests/unit/test_besito_service.py`: extender tests existentes de `credit_besitos_success` etc. con `patch("services.besito_service.get_event_bus")` (o el módulo). Assert call count =1 en success, =0 en invalid amount/early return, payload contiene user_id/amount/source/reference_id/description. Mantener todos los asserts de balance, tx, for_update, etc.

**Integration (ejercitan flujos reales con DB + commits internos de credit):**
- `tests/integration/test_cross_service_atomicity.py` (crítico per analyzer y docs): el "gold" para reaction → credit commit → mission separate tx. Agregar patch o verificación del bus emit. Confirmar que si el listener "falla" (mock que raise), el crédito, reacción y mission progress siguen exactos. Re-query balances post todo. Usar el patrón SQLite tmp + TestSession + fresh 7770x tg ids + close/dispose + strict asserts.
- `tests/integration/test_reaction_full_chain.py` y `test_reaction_mission_flow.py`: asegurar "besitos_awarded" en reaction_result y BroadcastReaction se mantiene; agregar nota/assert de que el event se emitió (puede ser vía side effect en un listener de prueba o patch en el service).
- `tests/integration/test_invariants.py`: smoke de múltiples créditos (ADMIN, REACTION, MISSION, etc.); si se registra listener global en conftest para la sesión de tests, verificar que no altera balances.
- Story paths: `tests/unit/test_story_service.py` (test de grant achievement que llama credit_besitos internamente) + cualquier integ de logros. El listener narrative se ejecutará (best effort); no debe cambiar el resultado del grant.
- Daily y game: targeted smoke (`-k "daily or game or trivia"`) para confirmar que credits de DAILY_GIFT / GAME / TRIVIA / STREAK_PROTECTION disparan el emit sin romper sus retornos.

**Mocks y aislamiento:**
- Siempre mockear el bus (o get_event_bus) en tests unit de besito y en integ donde no se quiere ejercicio real del listener.
- Para tests que quieren ejercicio real del listener (p.ej. "narrative recibió"), registrar un AsyncMock listener temporal en el bus singleton o usar una instancia inyectable (si el executor decide exponer `bus=` en BesitoService __init__ para tests — permitido si mínimo).
- Fixtures: no registrar listeners "reales" en conftest global a menos que se limpie después de cada test (reset `_listeners = {}`).
- Evitar depender de orden de registro.

**Gates obligatorios (ejecutar antes de marcar fase completa y al final):**
- `pytest -k "event_bus or TestInternalEventBus or TestEventBus" -q --tb=line`
- `pytest -k "besito or TestBesito or credit_besitos or daily or DailyGift" -q`
- `pytest -k "reaction or broadcast or TestCheckAndRegister or TestFullReactionChain or TestCrossServiceAtomicity or TestReactionMissionFlow" -q --tb=line`
- `pytest -k "story or narrative or TestStoryService or achievement" -q`
- `pytest -k "atomicity or invariants" -q`
- `ruff check <archivos modificados> --fix && ruff format --check`
- Post-todos: broader smoke si tiempo (`pytest --tb=no -q` con markers relevantes) — 0 regresiones esperadas en gamif/narrative/channel/vip paths que no tocan crédito.

**Aislamiento de DB:** Seguir patrón probado (SQLite file + TestSession para integ que ejercitan commits internos de credit + broadcast + mission + ahora listeners).

---

## 4. Decisiones de diseño (que el gsd-executor debe tomar / confirmar; recs del impact-analyzer sintetizadas)

1. **Ubicación del archivo del bus:** Recomendado `services/event_bus.py` (colocado junto a los services; es lógica de cross-cutting pero "system" liviano, no un dominio de negocio). Alternativa: `services/internal/event_bus.py` (subpaquete) — pero mantener flat por ahora para minimizar fricción con imports existentes. No poner en utils/ (utils es para helpers no-core) ni en raíz.

2. **Cómo registrar listeners:** Explícito y centralizado en `bot.py` (en `on_startup` o una `setup_cross_domain_listeners()` llamada desde allí). Esto hace el wiring visible, fácil de auditar, y evita side-effects en import de story_service. El listener mismo vive en el módulo de story_service (ownership del dominio narrative). El bus expone `.register(event, async_callable)`.

3. **Payload exacto del evento "besitos_awarded":**
   ```python
   {
     "user_id": int,           # telegram_id style (BigInt value usado en todo el sistema)
     "amount": int,
     "source": str,            # source.value (ej "reaction", "daily_gift", "MISSION", ...)
     "reference_id": int | None,
     "description": str | None,
     "timestamp": str          # ISO UTC, e.g. datetime.now(UTC).isoformat()
   }
   ```
   Usar dict simple (consistente con los dicts de retorno de broadcast reactions y otros servicios). Documentar en el bus y en los CLAUDEs de gamif/narrative.

4. **Cómo manejar el emit desde código sync (credit_besitos es def síncrono):** 
   - Implementar helper en `event_bus.py` (p.ej. `def schedule_emit(coro: Awaitable): ...`).
   - Dentro: `try: loop = asyncio.get_running_loop(); loop.create_task(coro) except RuntimeError: logger.debug("no running loop for event emit; skipping (best effort)"); return`.
   - El coro que se schedulea es `bus.emit(...)` que internamente hace el gather + return_exceptions.
   - Nunca bloquear el thread del crédito. Si en futuro hay paths puramente sync sin loop (scheduler jobs sync), el emit se degrada a log (aceptable para PoC; se puede evolucionar a queue o thread-safe schedule después).

5. **Nombre del evento y constantes:** `EVENT_BESITOS_AWARDED = "besitos_awarded"` (string). Exportar desde `event_bus.py` y re-exportar en `services/__init__.py` si ayuda. Usar la constante en todos los sitios (besito_service, registro, tests) para evitar typos.

6. **Bus como singleton vs factory vs inyección:**
   - Para PoC conservador y mínimo diff en besito_service: singleton / module-level instance accesible vía `get_event_bus()` (sin DB, no necesita context manager como get_service).
   - No inyectar en BesitoService.__init__ en esta iteración (evita tocar todos los sitios que hacen `BesitoService(db)` o bare `()` y los tests que los crean).
   - Tests usan patch en el módulo (`patch("services.besito_service.get_event_bus")`) o resetean el estado del singleton.
   - Futuro (Item 2+): se puede evolucionar a inyección o context si se necesita por testabilidad o multi-bus.

7. **Primer listener "real" en narrative (qué hace):** Para PoC, el listener es principalmente de observación + log (prueba el wiring). Puede incluir un stub "if amount >= X and source in [...] : best effort check story progress or unlock hint" pero **sin** llamar credit_besitos (para no re-entrar). El ownership está en narrative; si más adelante se quiere que narrative "reaccione con progreso de historia por besitos acumulados", se añade lógica ahí (usando get_service(StoryService) dentro del listener para obtener una sesión fresca si es necesario). Documentar que es best-effort y que errores se tragan en el bus.

8. **Impacto en los tres sistemas críticos:** 
   - Gamification: solo el emit post-commit (no cambia contratos de crédito).
   - Narrative: primer consumer; su listener no debe asumir que el crédito viene "de fuera" (puede venir de su propio _grant_achievement).
   - Channel admin / VIP: no afectados directamente (créditos en VIP contexts son via game/trivia/streak o admin; los paths de reacción/broadcast/daily son los principales y ya están cubiertos por tests de atomicity). Asegurar que cualquier crédito en flujos VIP (pocos) sigue funcionando.

9. **Logging y voz:** El bus y el emit path usan el formato estándar del proyecto (no voz de Lucien en logs técnicos; la voz es para mensajes a usuarios). Logs deben incluir user_id siempre que esté en el payload.

---

## 5. Criterios de verificación (antes de pasar a arch-enforcer / test-guardian)

Antes de declarar la entrega lista para los agentes siguientes, el gsd-executor debe confirmar (y documentar en el GSD log final):

1. **Gates de tests targeted verdes (0 failures, 0 errors):**
   - event_bus unit
   - besito unit + credit paths
   - cross_service_atomicity + reaction_full_chain + reaction_mission_flow
   - story / narrative paths que acreditan besitos
   - daily + game credits (smoke)
   - ruff limpio en todos los archivos tocados.

2. **Arquitectura (verificación manual + grep):**
   - Handlers que tocan besitos (gamification_user_handlers.py, store_user_handlers.py, gamification_admin_handlers.py, etc.) siguen llamando **exactamente 1 service** y sin nueva lógica de emit.
   - Ningún handler importa el event_bus directamente.
   - services/besito_service.py no importa nada de narrative ni viceversa (el acoplamiento es solo a través del bus).
   - Funciones modificadas (credit_besitos, listener) ≤50 líneas (o el helper de schedule está separado).
   - Logging presente con módulo | acción | user_id | resultado en los paths clave.

3. **Atomicity & best-effort invariants (ejecutados en los integ tests):**
   - Post-crédito exitoso: el BesitoBalance y BesitoTransaction existen y son correctos **aunque** el listener narrative falle o el mission side-effect falle.
   - El dict retornado por broadcast reactions sigue teniendo "besitos_awarded" con el valor del emoji (no cambiado).
   - No saldos negativos introducidos (los tests de invariants ya lo cubren).

4. **PoC conservador verificado:**
   - Grep muestra que no se removieron instanciaciones directas de BesitoService (intencional).
   - Solo un listener registrado (narrative).
   - El bus es removable (comentario en código o nota en CLAUDE).

5. **Docs actualizados y consistentes** con el estado real (CLAUDEs de gamification/narrative/services + decisions.md).

6. **GSD discipline cumplida:** `.planning/quick/gsd-eventbus-poc-item1.log` tiene appends pre-cada edit significativo (mínimo 1 por fase + inicio + final; estilo de los logs exitosos previos como gsd-mw-hardening y testing-debt). wc -l del log al final es evidencia.

7. **No breakage en critical systems:** smoke manual o targeted de channel/VIP flows (incluso si no ejercitan crédito directamente) no muestra regresiones (p.ej. `pytest -k "vip or channel or free_entry" -q --tb=no`).

Si cualquiera de estos falla, no se pasa a arch-enforcer/test-guardian hasta fix + re-gate.

---

## 6. Instrucciones claras para el siguiente agente (gsd-executor)

**Antes de tocar cualquier archivo (incluso tests o docs):**
1. Lee **completo** este `PLAN.md` (y los archivos referenciados en "Context" abajo).
2. Ejecuta GSD pre-log: usa `run_terminal_command` con `echo "=== $(date -Iseconds) | PHASE X | intent: ..." >> .planning/quick/gsd-eventbus-poc-item1.log` (y `wc -l` para contar). Haz esto al inicio de cada fase y antes de **cada** search_replace / write / edit significativo. Los logs previos exitosos tenían 8-50+ entradas.
3. Re-confirma el mapa de impacto actual (corre los greps clave: `grep -n "credit_besitos" services/ handlers/ tests/`, `grep -n "BesitoService(" ...`, `grep -n "besitos_awarded" ...`). El impact-analyzer "report" de esta sesión está sintetizado arriba; si hay duda, trata los call sites como fuente de verdad.
4. Sigue el orden estricto de fases. Marca una fase "completa" solo cuando su DoD checklist + tests verdes + ruff estén confirmados y logueados.

**Durante implementación:**
- Implementa fase por fase. Verifica gates entre fases.
- Para el bus: sigue exactamente el patrón `asyncio.gather(..., return_exceptions=True)` del test de concurrent reactions.
- Para el emit en credit: **post commit**, try-wrapped, best effort. No toques la estructura de la transacción de besitos.
- Usa `patch` / `AsyncMock` para el bus en tests (aislamiento).
- Mantén la voz de Lucien solo donde corresponde (mensajes a usuarios); logs técnicos usan el formato "módulo | acción | user_id | resultado".
- Si una decisión de diseño listada arriba no está clara o el código actual sugiere algo mejor, documenta tu elección en el GSD log y en un comentario en el código, y actualiza la sección correspondiente de este plan (o decisions.md) si es permanente.
- No hagas "mejoras" fuera de scope (ej. no empieces a inyectar el bus en todos los services "porque es más limpio").

**Al final de cada fase / de toda la entrega:**
- Confirma los criterios de verificación de la sección 5.
- Append final al GSD log con resumen (archivos modificados, tests gates, safe points, handoff).
- Prepara el estado para arch-enforcer (pide revisión de que no se violó handlers=1service, domain boundaries, no duplicación) y test-guardian (los tests críticos siguen cubriendo los contratos de crédito + el nuevo emit no introdujo flakes).
- Si algo no está verde o una aserción de "besitos_awarded" en reaction dicts se rompió, detente y rollback la fase ofensiva.

**Archivos de referencia obligatorios que debes leer antes de empezar (además de este PLAN):**
- `@architecture.md`, `@rules.md`, `@decisions.md`, root `@CLAUDE.md`
- `services/CLAUDE.md`, `services/gamification/CLAUDE.md`, `services/narrative/CLAUDE.md`
- `models/CLAUDE.md` (para TransactionSource y Besito models)
- `services/__init__.py` (get_service pattern — el bus no lo usa, pero es el patrón de acceso a servicios)
- `services/besito_service.py` (crédito completo), `services/broadcast_service.py` (check_and_register_reaction y el patrón best-effort de misiones post-commit), `services/story_service.py` (especialmente _grant_achievement que hace credit inverso)
- Ejemplos de GSD logs exitosos: `.planning/quick/gsd-mw-hardening-*.log`, `.planning/quick/gsd-fase-*-review.log`
- Patrón de tests de atomicidad: `tests/integration/test_cross_service_atomicity.py` (docstrings + setup), `tests/unit/test_broadcast_service_reaction_flow.py` (el gather+return_exceptions)
- Impact report de ejemplo para estilo de riesgos/recs: `.claude/agent-memory/impact-analyzer/middleware-hardening-impact-report.md` y el de canales.

**Espíritu GSD + PoC:** Este es un experimento controlado de baja riesgo para introducir infraestructura de notificaciones internas. Prueba de concepto enfocada. Si el PoC demuestra valor sin romper atomicity ni los flujos de reacción/misión, Items siguientes pueden expandir (más listeners, más eventos, quizás inyección). Si hay problemas, los safe points por fase permiten rollback quirúrgico.

**Success looks like:** Un crédito de besitos (desde cualquier source: reacción, daily, misión, game, logro de historia, admin) resulta en:
- DB actualizada y committed (balance + tx) como siempre.
- Misiones (si aplica) procesadas en su tx separada como siempre.
- El event "besitos_awarded" entregado (best effort) al listener de narrative (logueado), sin que el usuario o el crédito se enteren de fallos en el listener.
- Todos los tests críticos verdes.
- 0 violaciones de arquitectura.
- Docs y decisiones actualizadas.

Ejecuta con disciplina. Loggea todo. Verifica antes de avanzar.

**Fin del PLAN.** Listo para `/gsd:execute-phase` o equivalente con este archivo como prompt principal.

---

**Context / References (para executor):**
- Impact-analyzer agent def y memoria: `.claude/agents/impact-analyzer.md` + `.claude/agent-memory/impact-analyzer/`
- Fases previas y metodología: `fases_refactor_testing.md`, `refactor_testing.md`, `docs/fase_testing_review_process.md`
- GSD quick logs y phases: `.planning/quick/`, `.planning/phases/`
- Patrones de middleware hardening (último exitoso cross-cutting): decisions.md entrada + middlewares/ + tests de mw.

¡Buena suerte, executor! Sigue el plan al pie de la letra.