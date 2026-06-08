# PLAN: Unificación de manejo de sesiones/recursos con `get_service` context manager (Fase 21)

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-06-07  
**Focus:** Tight, conservative, phased unification of legacy manual service instantiation + try/finally .close() patterns to the modern `with get_service(Service) as svc:` context manager (already proven in mission/story/promotion/package/reward_admin/store_admin/etc.). Start with normalizing "dumb" services that lack proper `_owns_session` tracking (to preserve db= atomic tx compatibility and prevent double-close/leaks on external sessions), then convert Tier 1 handlers (gamification_user, store_user, broadcast) one-by-one per impact-analyzer recommendations. Update legacy handler unit tests, add explicit coverage for get_service + owns + exc paths, enforce gates on critical integrations (atomics, reactions, missions). Zero scope creep; no barrido masivo.

**Input principal (source of truth):** 
- User-provided impact-analyzer summary (executive: 3 critical systems — gamification (besitos/broadcast/daily), narrative, channel/VIP; Tier 1 = gamification_user/store_user/broadcast handlers; normalize Reward/Broadcast/Package/Game/User closes first; db= compat mandatory; tests-first where possible; 4-6 small phases).
- Full discovery performed by this planner (grep of all direct `XXXService()` in handlers/, all `.close()` patterns, all current `with get_service` usage, service __init__/close/owns implementations across services/, cross-ref with tests/integration/*_reaction*, test_cross_service_atomicity.py, test_reaction_full_chain.py, test_reaction_mission_flow.py + unit broadcast/besito; review of services/__init__.py _ServiceContext, models/database.py get_db_session, modern handler patterns from mission_user/story_user/store_admin + their tests, legacy patterns in Tier1 handlers + common/backpack/channel/vip/free/gamif_admin/etc.).
- Precedents: .planning/phases/20-reward-gamif-rules-compliance/PLAN.md (exact structure, GSD discipline, 1-service remediation, pure helpers, port of tests to get_service patch + __enter__/__exit__, LOC<=50, logging, safe points), 19-eventbus-poc, 08-mw-hardening, phase20 handoff notes, decisions.md (mw + eventbus), handlers/CLAUDE.md (1 service rule, get_service preferred), services/CLAUDE.md, architecture.md, rules.md, models/CLAUDE.md (no raw SQL, tx for atomics).
- Current broken state (discovered): ~15-20 legacy direct+close sites in Tier1+others; Broadcast/Reward/Package/Game/User implement `db or SessionLocal()` + unconditional close (no _owns_session, will close caller-provided sessions — breaks db= atomics and risks leaks/double-close when used via get_service); Besito/Daily/Store/Channel/VIP/Mission/Story/etc. already modern with `_owns_session = db is None` + guarded close + (some) _get_db; _ServiceContext (services/__init__.py:86) does `svc = Service(db); ... if hasattr close: close()` (no auto commit/rollback; relies on service internals); handler tests for modern use @patch("handlers.xxx.get_service") + mock_context.__enter__ etc.; legacy handler tests still patch Service classes directly.
- GSD enforcement: every pre-edit/pre-gate/pre-verif MUST append to dedicated log (see Instructions).

**GSD enforcement:** Executor MUST prefix **every** modification, gate, verification, ruff, pytest, grep, smoke, or summary step with a GSD log append (timestamp | PHASE | description) to `.planning/quick/gsd-getservice-unification.log`. Use identical discipline and entry style as gsd-eventbus-poc-item1.log / gsd-reward-gamif-item2.log / gsd-mw-hardening (pre + post + counts). No edits without pre-log.

---

## 1. Alcance preciso (In / Out explícito)

### En esta primera iteración (scope "tight" per analyzer recs + "no barrido masivo"):
- **Normalización de "dumb services" (cierres/owns) primero (prerrequisito seguro):** 
  - `services/reward_service.py`, `services/broadcast_service.py`, `services/package_service.py`, `services/game_service.py`, `services/user_service.py`.
  - Cambios: __init__ set `self._owns_session = db is None` (antes del `or SessionLocal()`); `self.db = db or SessionLocal()` (o equivalente); implementar/fijar `close()` para `if self._owns_session and self.db: self.db.close(); self.db=None`; para compositores (Reward/Broadcast/Game que crean sub-services como Besito/Package/VIP/User internamente) asegurar que subs reciban el db (ya hacen) y que close() del parent opcionalmente llame close() en subs (harmless, ya que subs verán owns=False cuando db fue provisto o creado por parent); limpiar __del__ peligrosos si existen (o dejar como no-op post-fix); mantener compat 100% con callers legacy directos y con `get_service(..., db=session)`.
- **Conversión de Tier 1 handlers (uno por uno) a exactly-1-service + get_service context (sin closes manuales):**
  - `handlers/gamification_user_handlers.py` (funcs: show_balance, show_transaction_history, claim_gift/daily paths, handle_reaction + helpers; servicios: BesitoService, DailyGiftService, BroadcastService).
  - `handlers/store_user_handlers.py` (shop_menu/balance, catalog, categories, buy flows, previews, history; servicios: Besito, Store, Package).
  - `handlers/broadcast_handlers.py` (start + wizard steps; servicios: ChannelService + BroadcastService en funcs separadas).
- **Actualización de tests de handlers legacy (port al patrón moderno):**
  - `tests/handlers/test_gamification_user_handlers.py`
  - `tests/handlers/test_store_user_handlers.py`
  - `tests/handlers/test_broadcast_handlers.py` (o nombre real del suite; confirmar con ls/grep en ejecución).
  - Patrón: @patch("handlers.xxx.get_service"), mock_context.__enter__.return_value = mock_svc, asserts en __exit__ para closes, remoción de parches directos a Service classes, mantener textos/UI/callbacks/llamadas idénticos.
- **Cobertura explícita para get_service + owns + exc paths:**
  - Adición de tests unitarios targeted (3-6 casos: owned session closed on exit, db= passed session NOT closed, exception in block still closes owned, no double-close, composer subs safe). Ubicación preferida: extender `tests/unit/test_broadcast_service_reaction_flow.py` (ya ejercita Broadcast + internal Besito) + `tests/unit/test_besito_service.py` (gold reference) o equivalente mínimo en un test de service normalizado. Usar mocks de Session o el patrón SQLite+TestSession del proyecto.
- **Gates obligatorios de integraciones críticas (zero regression en atomics/reactions/missions):**
  - Re-ejecución de: test_cross_service_atomicity.py (paths que usan db= o cross besito tx), test_reaction_full_chain.py, test_reaction_mission_flow.py, unit/test_broadcast_service_reaction_flow.py, handler tests de reacción (TestHandleReaction), mission/reward flows que tocan RewardService normalizado, daily gift + besito.
- **Comportamiento observable idéntico + reglas:** Handlers siguen llamando exactly 1 service (1 with get_service por entrypoint function); logging en formato "módulo | acción | user_id=... | resultado=..." para acciones importantes (agregar/actualizar donde falte); funciones ≤50 LOC (verificar post-extracción si helpers se tocan); ruff limpio; get_service context reemplaza todo try/finally close en los sitios convertidos; db= sigue funcionando para callers que lo usen (aunque poco en handlers; usado en tests/integ para atomics).
- **Artefactos:** Este PLAN.md + entradas GSD completas en el log dedicado + (si procede) SUMMARY.md posterior.

**Archivos que se modificarán (exactos, por orden de fases):**
1. `services/reward_service.py` (F1)
2. `services/broadcast_service.py` (F1)
3. `services/package_service.py` (F1)
4. `services/game_service.py` (F1)
5. `services/user_service.py` (F1)
6. `handlers/gamification_user_handlers.py` (F2)
7. `tests/handlers/test_gamification_user_handlers.py` (F2)
8. `handlers/store_user_handlers.py` (F3)
9. `tests/handlers/test_store_user_handlers.py` (F3)
10. `handlers/broadcast_handlers.py` (F4)
11. `tests/handlers/test_broadcast_handlers.py` (F4)
12. Tests de cobertura owns/get_service/exc (F5; archivos de unit tests existentes)
13. Re-runs y verifs no modifican más fuentes (F5/F6)

### Fuera explícitamente (nada de scope creep):
- **NO** otros handlers (common, backpack, channel, vip_*, free_channel, gamification_admin, reward_admin (ya usa get para Reward), admin, promotion_*, anonymous_message_admin, mission_admin (directos de Reward/Package que quedan), store_admin (un Package direct), story_* (ya modernos), etc.). Estos se benefician indirectamente de la normalización de servicios pero no se tocan.
- **NO** cambios en bot.py, middlewares, keyboards, models, Alembic, config, utils, o cualquier servicio ya moderno (no "arreglar" Besito/Store/etc. de nuevo).
- **NO** refactor de lógica de negocio, ni extracción de nuevos servicios, ni cambios en flujos de reacciones/daily/misiones/tienda/broadcast más allá de la unificación de lifecycle.
- **NO** uso de db= dentro de los handlers Tier 1 convertidos (se mantiene "plain with get_service()" como en misiones/story; db= se preserva para callers de bajo nivel/tests atómicos y compositores internos).
- **NO** edición de CLAUDE.md, decisions.md, AGENTS, ROADMAP, docs/, o cualquier .md excepto este PLAN + el log GSD + (opcional) SUMMARY al final.
- **NO** barrido masivo ni "limpieza extra"; scope tight para primera entrega (Tier 1 + dumb services + tests + gates).
- **NO** nuevos archivos de test a menos que sea la adición mínima de cobertura dentro de suites existentes (preferible extender; si se necesita archivo nuevo para claridad, solo con justificación en log GSD y como último recurso).

**Comportamiento de usuario final:** Saldos, historial, reclamo diario, reacciones (conteos, besitos, UI refresh), catálogos, compras, previews, historial de tienda, wizard de broadcast (canales + creación + reacciones) — todo idéntico en textos, botones, callbacks y efectos laterales.

---

## 2. Fases ordenadas (6 fases pequeñas, secuenciales, con gates estrictos)

### Fase 1: Normalizar closes/owns en servicios dumb (Reward, Broadcast, Package, Game, User) — prerrequisito

**Objective:** Hacer que estos 5 servicios sigan exactamente el patrón probado de BesitoService/DailyGiftService/ChannelService/etc. (`_owns_session`, guarded close, db or SessionLocal después del flag). Esto elimina leaks/double-closes cuando se usan vía get_service (con o sin db=), preserva compatibilidad legacy + db= para atomics, y permite que el context manager de services/__init__.py maneje lifecycle automáticamente. Composer services (Reward/Broadcast/Game) propagan db a subs (ya lo hacen) para que subs hereden owns=False correctamente.

**DoD checklist (marcar al completar):**
- [ ] RewardService: __init__ set `_owns_session = db is None`; `self.db = db or SessionLocal()`; close() guarded por owns + (después de fix) llama close() en besito/package/vip subs (harmless); __del__ o bien removido o safe (no cierra si !owns).
- [ ] BroadcastService: mismo (incluyendo su besito_service interno); close() actual (línea ~395) reemplazado por guarded; no cierra db externo.
- [ ] PackageService: mismo (close ~520).
- [ ] GameService: mismo (incl. subs besito/user/vip; close ~309).
- [ ] UserService: mismo (close ~110).
- [ ] Todos los 5: ruff limpio; smoke import + instanciación básica (con y sin db) pasa.
- [ ] Grep confirma presencia de `_owns_session` y guarded close en los 5 (y ausencia de closes incondicionales en paths owns).
- [ ] GSD pre-edit + pre-gate entries en el log.
- [ ] Safe point alcanzado (ver abajo).
- [ ] 0 comportamiento change para callers legacy (direct Service() + .close() sigue cerrando cuando owns).

**Archivos:** Los 5 services listados arriba.

**Cambios clave (bullets accionables, orden sugerido dentro de F1 — un service a la vez o batch por service si cheap):**
- Para cada service (empezar por Reward o Broadcast por impacto):
  - Localizar __init__ (ej. Reward:36, Broadcast:31, Package:22, Game:300, User:16).
  - Cambiar de `self.db = db or SessionLocal()` a:
    ```python
    self._owns_session = db is None
    self.db = db or SessionLocal()
    ```
    (Mantener creación de subs después, pasando self.db — ya lo hacen la mayoría.)
  - Localizar/fijar close() (Reward:331, Broadcast:395, Package:520, Game:309, User:110).
    Reemplazar el cuerpo por el guarded estándar (copiar de besito_service.py:32 o channel_service.py:31):
    ```python
    def close(self):
        """Cierra la sesión de base de datos si fue creada por este servicio."""
        if self._owns_session and self.db:
            self.db.close()
            self.db = None
    ```
  - Para compositores (Reward/Broadcast/Game): en close(), después del if owns, agregar (o asegurar):
    ```python
    # Cerrar subs (inofensivo: ellos tienen owns=False cuando db compartido)
    for sub in (getattr(self, 'besito_service', None), getattr(self, 'package_service', None), getattr(self, 'vip_service', None), getattr(self, '_user_service', None), getattr(self, '_vip_service', None)):
        if sub and hasattr(sub, 'close'):
            sub.close()
    ```
    (Reward ya intentaba algo similar; hazlo seguro post-owns.)
  - Si existe __del__ que fuerza close incondicional (Reward, Package, User, Game): o removerlo (preferido, anti-pattern con context managers) o dejarlo como `if getattr(self, '_owns_session', False): self.close()` — documentar en log GSD. Remover es más limpio si no hay dependencias raras.
  - Pre-log GSD antes de cada edit (por service o por cambio grande).
  - Post-edit por service: `./venv/bin/python -m ruff check <file> --fix` + format si aplica; smoke `python -c "from services.xxx import XxxService; s=XxxService(); s.close(); print('owned ok'); from unittest.mock import MagicMock; db=MagicMock(); s2=XxxService(db=db); s2.close(); db.close.assert_not_called(); print('db= ok')"` (adaptar por módulo).
  - Grep de verificación por service.
- Al final de F1 batch: ruff en los 5; smoke combinado; grep global de owns en los 5.

**Tests que deben pasar antes de avanzar (gates de F1):**
- Ruff + format check en los 5 archivos.
- Smoke import + owns/db= básico (el python -c anterior, o equivalente en un test runner; debe pasar para los 5).
- Si hay unit tests existentes de estos services que instancian y cierran (ej. test_broadcast_service_reaction_flow.py, test_besito indirect via Reward, unit de game/trivia que tocan Game), re-correrlos targeted: `pytest tests/unit/test_broadcast_service_reaction_flow.py -q --tb=line -p no:cov --override-ini="addopts="` (y similares para otros si existen); deben seguir verdes (comportamiento idéntico).
- Grep: `grep -n "_owns_session" services/{reward,broadcast,package,game,user}_service.py` (debe mostrar 1 por archivo); `grep -n "if self\._owns_session and self\.db" ...` (guarded).
- GSD entries + "F1 safe point".

**Riesgos + mitigaciones:**
- Riesgo bajo: callers legacy que dependían de close() siempre cerrando (incluso si pasaban db) → Mitigación: tales callers (pocos; la mayoría directos sin db=) ahora cierran correctamente su propia sesión; db= era "poco usado" pero ahora se preserva. Tests de atomics (F5) validarán.
- Riesgo: __del__ removido causa warnings o comportamiento en GC raros → Mitigación: __del__ ya era frágil (y causaba closes dobles potenciales); remover es mejora documentada. Si se deja condicionado, es safe.
- Riesgo: Reward close llama subs.close() y algún sub hace algo extra → Mitigación: los subs (besito etc.) ya son idempotentes en close() post-owns; llamar es no-op cuando !owns.
- Riesgo de tiempo: 5 services → Mitigación: F1 es solo servicios (sin handlers/tests de handler); se puede hacer en 1-2 waves con gates por service o batch final.
- Analyzer reportaba riesgos bajos en "dumb" services.

**Safe point:** Post-ruff + smokes verdes + greps de owns + GSD "F1 safe point - 5 dumb services now own-aware; db= safe; legacy direct callers unchanged". Reversible con git revert de los 5 (o edits puntuales). Ningún handler tocado aún.

---

### Fase 2: Convertir gamification_user_handlers.py a get_service + port de sus tests de handler + gate reactions

**Objective:** Reemplazar las 5+ instanciaciones directas + try/finally closes (balance, tx history, daily gift, reaction) por `with get_service(BesitoService/DailyGiftService/BroadcastService) as svc:`. Cada handler function llama exactly 1 service. Actualizar tests del handler al patrón @patch get_service + context (como test_mission_user_handlers.py). Añadir/estandarizar logging. Re-ejecutar chains de reacción para zero regression en UI refresh / besitos / misiones side.

**DoD checklist:**
- [ ] Imports: `from services import get_service`; `from services.besito_service import BesitoService`; `from services.daily_gift_service import DailyGiftService`; `from services.broadcast_service import BroadcastService` (o equivalentes desde services); 0 instanciaciones directas de estos en el módulo.
- [ ] Todas las funcs relevantes usan `with get_service(...) as xxx_service:` (sin try/finally closes manuales).
- [ ] `handle_reaction` (y cualquier helper de conteo si se extrae para LOC) ≤50 LOC; comportamiento de refresh (update_reaction_message, markup) idéntico.
- [ ] Logging estándar presente para acciones clave (e.g. "gamification_user_handlers | handle_reaction | user_id=... | broadcast_id=... | emoji=... | besitos=...").
- [ ] Tests de handler portados: 0 parches directos a Besito/Daily/BroadcastService; todos usan patch get_service + __enter__/__exit__ asserts; textos/callbacks/llamadas idénticos.
- [ ] Ruff limpio; LOC verificado si aplica; GSD pre + gates.
- [ ] Re-runs de TestHandleReaction + reaction chains integrations verdes (sin regressions atribuibles).
- [ ] Safe point.

**Archivos:** `handlers/gamification_user_handlers.py`, `tests/handlers/test_gamification_user_handlers.py`.

**Cambios clave (bullets accionables):**
- Actualizar imports al inicio (reemplazar los 3 directos por get_service + imports de clases específicas).
- Para show_balance (~33): `with get_service(BesitoService) as besito_service: stats = ...`
- show_transaction_history (~62): mismo para Besito.
- Daily gift funcs (can_claim ~117, claim_gift ~163): `with get_service(DailyGiftService) as gift_service:`
- handle_reaction (~211+): `with get_service(BroadcastService) as broadcast_service:` (dentro del if has_reactions etc.; el broadcast_service.get_reactions... y update se mantienen).
- Si handle_reaction >50 post-conversión (por boilerplate with), extraer helper puro como en phase20 (e.g. calculate_emoji_counts_from_reactions) — nombre siguiendo convención del proyecto; tests del helper en F2 o F5.
- Añadir logging dentro de los with (después de éxito) en formato estándar.
- Remover todos los `besito_service.close()` etc. y los finally blocks correspondientes.
- Post-edit: ruff; conteo LOC de handle_reaction si se tocó; grep "BesitoService()|BroadcastService()|DailyGiftService()" == 0 (activo).
- Para el test file: port masivo siguiendo exactamente el ejemplo de phase20 F4 (cambiar @patch a get_service, setups de __enter__, asserts de __exit__ en lugar de close(), remover asserts de "closes both", mantener todos los textos y calls a service methods).
- GSD pre cada edit + pre-ruff/pre-pytest.

**Tests que deben pasar antes de avanzar:**
- Ruff en los 2 archivos.
- Suite completa del test handler: `pytest tests/handlers/test_gamification_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts="`
- Al menos el test de updates_reaction_counts (o equivalente) + cualquier que ejercite refresh.
- Re-run targeted de chains: `pytest -k "TestHandleReaction or TestFullReactionChain or TestReactionMissionFlow or TestReactionLimit or reaction or broadcast" -q --tb=line -p no:cov --override-ini="addopts="` (debe pasar limpio; documentar cualquier pre-existing unrelated fail).
- Grep de reglas: 0 instanciaciones directas en el handler; get_service presente.

**Riesgos + mitigaciones:**
- Riesgo: reaction refresh difiere por orden de with/closes → Mitigación: el with hace lo mismo (enter crea, exit close si owns); tests re-ejecutados validan markup/llamadas idénticas.
- Riesgo: daily gift + besito cross (si algún path los usara juntos) → Mitigación: en este handler las funcs son separadas (shop usa besito para balance; claim usa daily); si un futuro path los combina, orquestar en servicio (fuera de scope).
- Riesgo medio: port de tests introduce errores de setup de mocks → Mitigación: copiar patrón de test_mission_user_handlers.py + test_reward_user (F4 de phase20) al pie de la letra; 5-10min por test.
- Riesgo de flakes en integ reaction → Mitigación: usar targeted -p no:cov; documentar; focus en "0 nuevas regressions".

**Safe point:** Post-ruff + handler tests verdes + reaction chains re-run + grep 0-direct + GSD "F2 safe point - gamif_user now get_service only; reaction UI unchanged". Reversible editando solo estos 2 archivos.

---

### Fase 3: Convertir store_user_handlers.py + port de sus tests

**Objective:** Igual que F2 pero para el dominio store (balance display via besito, catalog/categories via store/package, buy/preview/history flows). Convertir todas las ~15+ instanciaciones. Port tests. Mantener flujos de compra (debit + entrega de package) idénticos (la orquestación ya vive en StoreService/PackageService).

**DoD checklist:** Análogo a F2 (imports get_service + clases específicas; 0 directos; with en cada func relevante; logging; tests portados completos con get_service patches + __exit__; ruff; re-runs de cualquier integ que toque store (si existen en atomic/mission o backpack); safe point).

**Archivos:** `handlers/store_user_handlers.py`, `tests/handlers/test_store_user_handlers.py`.

**Cambios clave:** 
- shop_menu: with get_service(BesitoService) para balance.
- store_catalog, categories, previews, direct buy confirm, history: with get_service(StoreService) o PackageService según corresponda.
- Funcs que usan 2 en secuencia (ej. buy que debita besitos vía store y entrega package): verificar que el handler llama 1 service (StoreService orquestando); si el código actual hace besito + store en un solo def, aplicar decisión de diseño (orquestar en service o split); per discovery inicial, la mayoría son funcs separadas.
- Port de tests: mismo patrón que F2 (muchos tests en store_admin ya usan get_service; el user será similar).
- Grep post: 0 "BesitoService()|StoreService()|PackageService()" en handler (activo).

**Tests gates:** Ruff; suite test_store_user_handlers verde; cualquier integ store-related (backpack purchase history si toca, o cross atomic si ejercita compras); GSD + greps.

**Riesgos:** Similares (port de tests denso pero precedentes existen; buy flows son críticos pero orquestados en service layer ya).

**Safe point:** Análogo.

---

### Fase 4: Convertir broadcast_handlers.py + port de sus tests

**Objective:** Convertir el wizard admin de broadcast (start usa ChannelService; creación/emojis/confirm usa BroadcastService). Note: funcs separadas, no multi-service en un solo handler entrypoint. Channel ya es moderno (owns bueno); Broadcast se normalizó en F1. Port tests.

**DoD:** Análogo. Incluye send_broadcast_start (Channel), luego steps de emojis/reactions/confirm (Broadcast). Logging en pasos importantes del wizard si faltan.

**Archivos:** `handlers/broadcast_handlers.py`, `tests/handlers/test_broadcast_handlers.py`.

**Cambios:** Reemplazar los 5+ direct+close por with get_service(ChannelService/BroadcastService). Actualizar tests (el broadcast handler test probablemente mockea creation flows + reaction emoji config).

**Tests gates:** Ruff; suite del test; re-run de broadcast/reaction units + integ relevantes (test_broadcast_service_reaction_flow + full chain); grep 0 directos en el handler.

**Riesgos:** FSM + multi-step; mitigación: cada paso es un handler separado con su propio with (corto); tests cubren los estados.

**Safe point:** Análogo.

---

### Fase 5: Agregar cobertura explícita get_service + owns + exc paths + re-runs de atomics/reactions/missions + gates targeted

**Objective:** Asegurar que el "test-guardian" futuro tenga protección sobre el lifecycle unificado. Cubrir paths que antes no estaban explícitos (db= no-close, owned-close, exc en with block, compositores con subs). Re-ejecutar las gold integrations atómicas + reaction + mission/reward (que ejercitan los servicios normalizados y los handlers convertidos indirectamente).

**DoD checklist:**
- [ ] Al menos 4-6 nuevos tests unitarios (empty owned close, db= passed not closed, exc path still closes, no double close on repeated close, composer sub safe) — agregados en `tests/unit/test_broadcast_service_reaction_flow.py` (o el unit de besito si se prefiere gold, o test de package/game si existe) + ejecución real de with get_service en al menos un test (no solo mocks de handler).
- [ ] Re-runs completos de: test_cross_service_atomicity.py (especialmente paths con db= o cross-besito), reaction full/mission/limit chains, broadcast reaction unit, handler tests de gamif/store/broadcast (ya en fases previas), mission/reward flows que tocan Reward normalizado.
- [ ] Todos los targeted anteriores verdes (0 regressions nuevas).
- [ ] Ruff en todos los archivos tocados hasta ahora.
- [ ] Grep/LOC/logging rules verificados para los 3 handlers.
- [ ] GSD entries + "F5 coverage + re-runs done".

**Archivos:** Los unit tests de service relevantes (no se crean suites nuevas a menos que mínimo; extender existentes).

**Cambios clave:** Añadir una clase TestServiceLifecycleOrGetServiceContext (o similar) con los casos usando MagicMock de Session o el fixture real del proyecto (ver conftest.py para TestSession/SQLite). Para exc path: `with pytest.raises(...): with get_service(...) as s: raise`. Verificar s.db.closed o mock calls.
- Ejecutar los re-runs con comandos concretos (ver Instructions).
- Si algún pre-existing fail unrelated aparece (ej. alembic), documentarlo en log pero no contar como regression del Item.

**Tests gates:** Los re-runs + nuevos tests verdes; ruff.

**Riesgos:** Integ lentas → mitigación: targeted con -k + -p no:cov; correr en background si tool lo permite, pero preferir secuencial para logs.
- Cobertura de owns requiere mocks de session o hooks → mitigación: usar el patrón ya establecido en tests de services (muchos usan real SQLite en memoria/file para unit; para "not closed" se puede usar un wrapper o assert en el mock pasado).

**Safe point:** Re-runs + nuevos tests verdes + GSD "F5 safe point - owns/get_service/exc covered; atomics+reactions+missions 0 regression".

---

### Fase 6: Verificación final, criterios de arch-enforcer/test-guardian, self-check + handoff

**Objective:** Confirmar que todo el scope de la primera iteración está limpio, medible, y listo para que arch-enforcer re-escanee y test-guardian tenga los tests críticos listados. Completar GSD log con self-check PASSED. (Opcional: generar SUMMARY.md siguiendo precedente de phases/20 y 19 si el executor lo desea para handoff.)

**DoD checklist:**
- [ ] Todos los archivos tocados (5 services + 3 handlers + 3 handler tests + coverage additions) pasan ruff check + format --check.
- [ ] Grep global en los 3 handlers: 0 instanciaciones directas de los servicios migrados (solo get_service + imports de clases para with).
- [ ] LOC de cualquier func que rozara 50 (handle_reaction si se extrajo) verificado <=50.
- [ ] Logging formato spot-check (grep o lectura) en los handlers convertidos.
- [ ] Re-runs finales de los targeted críticos (puede repetir F5 commands + broader smoke si se quiere: e.g. -k "gamif or store or broadcast or reaction or atomic or mission or reward").
- [ ] GSD log tiene entradas para cada fase + pre-gates + self-check al final.
- [ ] Self-check explícito en log: lista de fases, DoD cumplidos, archivos modificados, tests que pasaron, reglas verificadas, desviaciones (si las hubo), tests críticos a re-correr en futuro (los mismos integ + handler units de los 3 + los nuevos owns tests), "Item closed. Ready for arch-enforcer + test-guardian".
- [ ] (Opcional pero recomendado) SUMMARY.md en el dir de la phase con resumen ejecutivo + refs al log GSD.
- [ ] Safe point final.

**Archivos:** Ninguno nuevo (solo el log + opcional SUMMARY; los edits ya hechos).

**Cambios clave:** Solo verificación + echo al log. Usar run_terminal para los comandos de gate final.

**Tests gates:** Los targeted finales + ruff global en touched files.

**Riesgos:** Ninguno nuevo (verificación).

**Safe point final + criterio de éxito del plan:** Todos los DoD de F6 + self-check PASSED en log. El plan completo (este archivo) + log GSD son la evidencia para el siguiente agente (arch-enforcer/test-guardian o gsd-executor de follow-up phases).

---

## 3. Estrategia de tests general

- **Port de handler units legacy (F2/F3/F4):** Seguir al pie de la letra el patrón de `tests/handlers/test_mission_user_handlers.py` (y el port de reward en phase20 F4): @patch("handlers.<module>.get_service"), mock_get_service.return_value.__enter__.return_value = mock_instance, configuración de returns para los métodos llamados, asserts de __exit__.assert_called (o en el mock_context), remoción completa de parches a las clases Service directas y de asserts de "closes manuales". Mantener todos los asserts de UI (edit_text, answer, textos producidos, botones/callbacks) idénticos. Para casos con relationship o puros (si aplica en estos dominios), seguir precedentes.
- **Nuevos tests de cobertura owns/get_service/exc (F5):** Ubicación: extender un unit de service existente que ya importa los servicios normalizados (preferiblemente `tests/unit/test_broadcast_service_reaction_flow.py` por ejercitar Broadcast + Besito interno, o `tests/unit/test_besito_service.py` como gold, o el de package si existe). Casos mínimos:
  - Instanciación sin db → owns=True → close() cierra la SessionLocal creada.
  - Instanciación con db= mock/real → owns=False → close() no llama close en el pasado.
  - with get_service(Svc) as s: ... → después del with, para owned: close fue llamado (verificar via mock o estado).
  - with get_service(Svc, db=passed) → el passed no fue cerrado.
  - with get_service(Svc) as s: raise RuntimeError → close aún llamado (usa try/finally del context o pytest.raises + assert).
  - Composer (Broadcast/Reward/Game): al close parent, subs no cierran la sesión compartida (pueden mockearse o inspeccionarse).
  Usar MagicMock para Session cuando se quiera aislar; o el fixture real del proyecto (conftest tiene setups SQLite para services).
- **Re-runs de integraciones críticas (F2 spot, F5 principal, F6 final):**
  - Handler reacción: `pytest tests/handlers/test_gamification_user_handlers.py -k "HandleReaction or handle_reaction or TestHandleReaction" ...`
  - Integrations gold: `pytest -k "TestFullReactionChain or TestReactionMissionFlow or TestReactionLimit or TestCrossServiceAtomicity or reaction_full or atomic" -q --tb=line -p no:cov --override-ini="addopts="`
  - Broadcast service: `pytest tests/unit/test_broadcast_service_reaction_flow.py ...`
  - Mission/reward cross (post normalización Reward): `pytest -k "mission or reward" ...` (targeted a flows que tocan get_available_rewards o deliver).
  - Store-related si hay integ específicas (backpack purchase history, o cualquier que use store_user paths indirectamente).
  - Comando combinado sugerido (adaptar por fase): `./venv/bin/python -m pytest -k "reaction or broadcast or atomic or gamif or store or mission or reward" -q --tb=line -p no:cov --override-ini="addopts="`
- **Gates generales:** Ruff con `./venv/bin/python -m ruff check <file>` (y --fix); format --check; pytest targeted limpio (exit 0); grep de reglas (0 direct Service() en handlers convertidos, owns en services, LOC via inspect o wc si aplica, logging formato).
- **Cobertura de logging:** No asertado por tests usualmente; gate es inspección manual + inclusión en GSD log durante las ediciones.
- **Precedente para --override-ini:** Usado en todas las phases recientes para evitar cov que ensucia exit codes en CI/local.

---

## 4. Decisiones de diseño (el executor debe confirmar o registrar desviación en el primer GSD entry de la fase relevante)

1. **Orden de migración:** Dumb services primero (F1, todo junto o secuencial por service con gates intermedios) → handlers Tier 1 uno por uno (F2 gamif, F3 store, F4 broadcast) → cobertura + re-runs (F5) → verif final (F6). Esto sigue la rec "normalizar closes en servicios dumb primero, convertir handlers Tier 1 uno por uno".
2. **Manejo de multi-servicio en un handler:** En esta iteración, las funcs de los 3 Tier 1 usan a lo sumo 1 servicio por entrypoint (diferentes funcs usan diferentes). Si durante F2/F3/F4 se descubre una func que instancia 2+ (ej. un buy que hace besito debit + store + package explícitamente en handler), la decisión es: (a) el handler debe llamar exactly 1 service (el principal, e.g. StoreService.process_direct_purchase que orquesta internamente el besito debit + entrega); (b) NO poner dos `with get_service` en una misma func de handler (viola la regla "exactly 1 service"); (c) db= se usa solo para callers que controlan tx explícitamente (tests atómicos, o un service que compone otro pasando su db) — no en handlers de esta fase. Si se necesita orquestación, se hace en el service layer (precedente: MissionService.get_available_rewards_for_user + relationship para reward; RewardService ya compone besito/package/vip). Registrar en log si se encontró tal caso y cómo se resolvió (scope tight: preferir no tocar lógica de store para orquestar si no es necesario; si el código actual ya delega a store, solo cambiar el lifecycle).
3. **db= en esta fase:** Solo plain `with get_service(XXXService) as ...` (sin db=) en los handlers convertidos. La compatibilidad se preserva vía la normalización de owns en F1 (get_service pasa el db al constructor, el service setea owns=False, close no toca). Los tests de F5 ejercitarán explícitamente el path db=.
4. **Logging:** Agregar/actualizar en las acciones importantes dentro de los with de los handlers (después de obtener datos exitosos o procesar): f"{module} | {action} | user_id={uid} | resultado=..." (copiar estilo de otros handlers/services modernos y de phase20). No es necesario en cada línea.
5. **Nombres de helpers (si se extraen para LOC en handle_reaction o similar):** Seguir convención proyecto: verbo + contexto + resultado (ej. `calculate_emoji_counts_from_reactions`). Confirmar en GSD de F2. Si no se necesita extracción porque el with hace que la func baje de 50, no extraer.
6. **__del__ en servicios normalizados:** Remover o condicionar a owns (preferir remover; es anti-pattern con context managers y puede causar closes dobles o en GC). Documentar en log de F1.
7. **Close de subs en compositores:** En close() del parent, llamar close() en los subs internos (besito etc.) — es safe post-F1 porque ellos tienen owns=False cuando el db es compartido. Esto alinea con la intención original de Reward.close() ("y servicios asociados") pero ahora correcto.
8. **No exportar nada nuevo en services/__init__.py:** No necesario (get_service ya está; las clases ya se importan directamente de sus módulos en handlers modernos).
9. **Log file GSD:** `.planning/quick/gsd-getservice-unification.log`. Formato de entry:
   ```
   === 2026-06-07Txx:xx:xx+00:00 | PHASE N | GSD pre-edit <archivo> (<motivo>) - <descripción + refs DoD>
   ```
   (o pre-ruff, pre-pytest, pre-grep, pre-smoke, pre-final). Apuntar a 5-10+ entries por fase como precedentes.
10. **Comandos concretos para gates:** Ver sección "Instrucciones para el gsd-executor" abajo. Siempre con -p no:cov --override-ini="addopts=" para targeted pytest.
11. **Si se necesita archivo nuevo para tests de cobertura:** Solo como último recurso; preferir extender unit tests existentes de los services normalizados. Si se crea (e.g. tests/unit/test_service_lifecycle.py), justificar brevemente en GSD y mantenerlo mínimo (solo los 4-6 casos).

Cualquier desviación de lo anterior debe registrarse en el GSD log + nota breve al final del PLAN o en SUMMARY.

---

## 5. Criterios de verificación antes de arch-enforcer/test-guardian

- Los 3 handlers Tier 1 no contienen instanciaciones directas (activas) de Besito/Broadcast/Daily/Store/Package/ChannelService (solo get_service + imports de las clases para el with).
- Los 5 dumb services tienen _owns_session + guarded close (y close de subs para compositores).
- Todos los tests de los 3 handler units pasan post-port (con get_service patches, __exit__ asserts, comportamiento/UI idéntico).
- Re-runs de atomics + reaction chains + mission/reward + broadcast reaction unit pasan sin regressions atribuibles a esta unificación.
- Nuevos tests de owns/get_service/exc existen y pasan.
- Ruff limpio en todos los archivos tocados.
- Verificaciones de reglas: grep 0-direct en handlers; LOC <=50 donde aplique; logging formato presente (spot); db= path cubierto en tests de F5.
- GSD log completo con pre-entries + self-check "PASSED" + lista explícita de "tests críticos a re-correr en el futuro para estos cambios" (los mismos integ + units de handlers + owns tests + cualquier smoke de bot import si se hizo).
- Comportamiento de usuario final idéntico en los flujos de gamificación (saldo, historial, daily, reacciones), tienda (catalogo, buys, history), y broadcast wizard.
- Safe point final documentado; item listo para arch-enforcer re-scan (enfocado en handlers/services para "get_service" y "close") + test-guardian (correr los tests críticos listados).

---

## Instrucciones para el gsd-executor

Este PLAN.md es tu prompt de ejecución. Síguelo al pie de la letra, sin scope creep. El trabajo es para UNA persona (tú) + disciplina GSD.

1. **GSD discipline (non-negotiable, como en todas las phases exitosas):**
   - ANTES de **cualquier** modificación (search_replace/write/edit), antes de ruff, pytest, grep de verif, smoke, o resumen: append al log.
   - Log: `.planning/quick/gsd-getservice-unification.log`
   - Crea el archivo si no existe (primer entry puede hacer touch + echo).
   - Formato de entry (copia estilo de gsd-eventbus-poc-item1.log y gsd-reward-gamif-item2.log):
     ```
     === 2026-06-07Txx:xx:xx+00:00 | PHASE 1 | GSD pre-edit services/reward_service.py (F1 owns) - Agregar _owns_session + fix close + subs; DoD: guarded, db= safe, legacy compat. Pre-ruff.
     ```
     Luego ejecuta el comando de edit/tool.
   - También pre-gate (pre-pytest, pre-ruff, pre-grep "owns", pre-final-self-check).
   - Cuenta las entradas; apunta a varias por fase (5-10+ totales por fase como precedentes). Al final del Item el log debe tener el self-check completo.
   - Usa `run_terminal_command` con `echo "=== $(date -Iseconds) | PHASE N | ..." >> .planning/quick/gsd-getservice-unification.log` (o printf). Nunca edites sin pre-log.

2. **Orden estricto:** Ejecuta Fase 1 completa (con gates internos si haces un service a la vez) → gates F1 → Fase 2 → gates F2 → F3 → gates → F4 → gates → F5 (cobertura + re-runs) → gates → F6 (verif final + self-check). **No saltes fases ni hagas "todo de una".** Marca DoD mentalmente o en el log al completar cada checklist.

3. **Herramientas y comandos concretos (usa run_terminal_command para estos):**
   - GSD logs: `echo "=== $(date -Iseconds) | PHASE N | GSD pre-... - <desc>" >> .planning/quick/gsd-getservice-unification.log`
   - Ruff: `./venv/bin/python -m ruff check <file> --fix` ; luego `./venv/bin/python -m ruff format --check <file>` (o apply).
   - Pytest targeted (siempre con estos flags para exit limpio): `./venv/bin/python -m pytest <path or -k "expr"> -q --tb=line -p no:cov --override-ini="addopts="`
     - Ejemplos:
       - `pytest tests/handlers/test_gamification_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts="`
       - `pytest -k "TestHandleReaction or TestFullReactionChain or TestReactionMissionFlow or TestReactionLimit or TestCrossServiceAtomicity or reaction or broadcast or atomic or gamif or store or mission or reward" -q --tb=line -p no:cov --override-ini="addopts="`
       - Para broadcast unit: `pytest tests/unit/test_broadcast_service_reaction_flow.py -q --tb=line -p no:cov --override-ini="addopts="`
   - Grep de reglas: `grep -n "BesitoService()\|BroadcastService()\|DailyGiftService()\|StoreService()\|PackageService()\|ChannelService()" handlers/gamification_user_handlers.py handlers/store_user_handlers.py handlers/broadcast_handlers.py | grep -v "get_service\|import"` (debe dar 0).
   - Grep owns: `grep -n "_owns_session\|if self\._owns_session and self\.db" services/reward_service.py services/broadcast_service.py services/package_service.py services/game_service.py services/user_service.py`
   - LOC (si aplica para handle_reaction): `python -c 'import inspect; from handlers.gamification_user_handlers import handle_reaction; src=inspect.getsourcelines(handle_reaction)[0]; print("LOC:", len(src))'`
   - Smokes: `python -c "from services import get_service; from services.broadcast_service import BroadcastService; print('import ok'); s=BroadcastService(); s.close(); print('owned close ok')"`
   - Para mkdir del phase (ya hecho por planner, pero si necesitas): `mkdir -p .planning/phases/21-getservice-unification`
   - Evita sleeps; usa comandos directos.

4. **Patrones a copiar (no reinventar):**
   - Patrón get_service en handlers + tests: copia de `handlers/mission_user_handlers.py` + `tests/handlers/test_mission_user_handlers.py` (y el port de reward en phase20).
   - Normalización de owns/close: copia el cuerpo exacto de `services/besito_service.py:22-36` (o channel_service.py) y adáptalo (incluyendo el manejo de subs para Reward/Broadcast/Game).
   - Extracción de helper + LOC trim (si se necesita en F2): espíritu de F2 de eventbus-poc (helpers privados, trim de docstring si 51 por boilerplate).
   - Logging: "módulo | acción | user_id=... | resultado=...".
   - GSD entries detalladas con "pre-" + descripción + qué se valida después (ruff/pytest/grep).
   - Safe points + self-check al final del log (como en Item 1/2).

5. **Decisiones (sección 4 del PLAN):** Al inicio de la fase relevante (primer GSD entry de la fase), registra qué decidiste para "nombre de helper si aplica", si removiste __del__, cómo manejaste close de subs, si encontraste algún multi-service en un handler y cómo lo resolviste (siguiendo la decisión 2), etc. Si difieres del "preferido", explica brevemente (mantén espíritu).

6. **Gates y re-runs:** 
   - Corre los targeted pytest con los flags exactos de arriba.
   - Si un unrelated fail preexistente aparece (ej. alembic_heads u otro), documéntalo en el log pero **no lo cuentes como regression del Item**.
   - Re-run de chains de reacción + atomic + mission es obligatorio en F5 (y spot en F2/F3 si el handler tocado es relevante).
   - Siempre GSD pre- antes del pytest.

7. **Alcance (recuerda siempre):** Solo edita los archivos listados en "Archivos que se modificarán" + el log GSD + (este PLAN ya está) + opcional SUMMARY.md al final. Si sientes la tentación de "limpiar más handlers" o "arreglar otros services", detente: scope tight para esta primera iteración. El analyzer recomendó empezar tight con Tier 1 + dumb services.

8. **Al final del Item (F6):**
   - Completa el self-check en el log (lista de fases/DoD/gates/archivos/tests/rules/desviaciones/tests críticos para futuro/"Item closed. Ready for arch-enforcer + test-guardian").
   - (Opcional) Produce `.planning/phases/21-getservice-unification/SUMMARY.md` con executive + refs al log + comandos de re-verificación (sigue estructura de phases/20 o 19 si existe).
   - Confirma en log: "Self-Check: PASSED".
   - El siguiente agente (arch-enforcer/test-guardian o planner de F22) usará el log + este PLAN + los tests agregados como fuente de verdad.

9. **Si algo no está claro o difiere del "reporte del analyzer":** El prompt del usuario + este PLAN (basado en discovery completa + el resumen provisto) es la fuente de verdad. Pregunta solo si un gate bloquea por ambigüedad real de nombre/firma/contrato; de lo contrario, elige conservadoramente siguiendo precedentes (mission port, owns de besito, etc.) y registra la elección en GSD.

**¡Ejecuta con disciplina total. Cierra la unificación de la primera iteración de forma limpia, segura, medible y con trazabilidad GSD completa. Los 3 sistemas críticos (gamif, narrative cross via events, channel/VIP) quedarán mejor protegidos contra leaks de sesión y listos para db= atomics cuando se usen.**

---

**Fin del PLAN para 21-getservice-unification.**

Referencias rápidas para el executor (actualizar con líneas reales durante ejecución si cambian):
- get_service + _ServiceContext: `services/__init__.py:69-101`
- Patrón owns gold: `services/besito_service.py:22-36` (y daily_gift, channel, vip, mission, store, story, backpack, etc.)
- Close legacy broken (pre-F1): broadcast:395, reward:331, package:520, game:309, user:110
- Tier 1 handlers legacy: `handlers/gamification_user_handlers.py:33 (Besito), 211 (Broadcast), ...`; store_user:46 (Besito),84 (Store),133 (Package),... ; broadcast:51 (Channel),341 (Broadcast),...
- Tests de handler modernos para copiar patrón: `tests/handlers/test_mission_user_handlers.py` (closes via __exit__), `tests/handlers/test_store_admin_handlers.py`, `tests/handlers/test_story_user_handlers.py`
- Integrations críticas: `tests/integration/test_cross_service_atomicity.py`, `tests/integration/test_reaction_full_chain.py`, `tests/integration/test_reaction_mission_flow.py`, `tests/unit/test_broadcast_service_reaction_flow.py`
- Precedentes de PLAN/GSD: `.planning/phases/20-reward-gamif-rules-compliance/PLAN.md`, `.planning/quick/gsd-reward-gamif-item2.log`, `.planning/phases/19-eventbus-poc/PLAN.md`, gsd-eventbus-poc-item1.log
- Reglas: `CLAUDE.md`, `rules.md`, `architecture.md`, `handlers/CLAUDE.md`, `services/CLAUDE.md`, `models/CLAUDE.md`
- GSD log para este Item: `.planning/quick/gsd-getservice-unification.log`

Listo para gsd-executor.