# Revisión de Testing - Lucien Bot

**Transición de trabajo:**

- **Fase 1 completada:** Top 10 Críticos de Testing (deuda de testing priorizada por impacto en "sacositas").
- **Fase 2 en curso:** Revisión sistemática y cronológica de testing por fase de desarrollo (siguiendo la metodología de `docs/fase_testing_review_process.md`).
  - Hoja de Ruta expandida (esta sesión) para incluir Fases 1-7 pre-07.1 sin huecos (ver tabla). Gamificación (Fase 4) y Misiones (Fase 5) + Suscripciones VIP (3), Tienda bundle (6), Invite Links (7) ahora contempladas explícitamente antes de Alembic. Pre-GSD = revisión de Fase 2 (Canales).

> **Metodología de referencia:** Para la revisión por fase de desarrollo, consultar [docs/fase_testing_review_process.md](../docs/fase_testing_review_process.md). Ese documento define el flujo, fuentes obligatorias, criterios, uso de agentes y template que se utilizarán.

---

## Hoja de Ruta Ligera - Revisión por Fases de Desarrollo

Esta sección funciona como control simple de avance. Se mantiene actualizada al final de cada sesión.

| Fase | Nombre / Tema principal | Estado | Inicio | Notas principales / Hallazgos clave | Siguiente acción |
|------|--------------------------|--------|--------|-------------------------------------|------------------|
| 1 | Bot Base (pre-GSD formal) | Pendiente | - | Arquitectura handlers/services/models + panel de Custodios. Pre-git history (inferred). Sin subdir dedicado en `.planning/phases/`. Fundacional para todas las fases posteriores. | Fase 2 / Pre-GSD (Canales) |
| Pre-GSD (Fase 2) | Gestión de Canales (Fundacional) | Reporte generado + pilots Alta + expansión de protección (recs open para 07.1) | Jun 2026 | Primera revisión + expansión post-revisión profunda (explore+impact subagents + code audit). 6 Pasos + gold pilots (SQLite+TestSession+patch) contra contrato deseado. **Pilotos iniciales:** approve_all DB-only, scheduler error+rollback+continue, inactive skip (4 tests en TestSchedulerPendingRequestsJob). **Expansión agregada:** 2 gold pilots más (welcome fail after commit sticks; get_ready/create for inactive+VIP documents no-guard); 3 unit contracts (create inactive/VIP, get_ready includes inactive). Total ~7 tests en job class + units fortalecidos. Brechas #2/#3/#4 mejor cubiertas; NEW gaps (dups, ghosts, post-commit resilience, handler cov) documentados. ID/DT/CLAUDEs reforzados previamente. **Siguiente: Fase 3 Suscripciones VIP (pre-GSD formal).** | Fase 3: Suscripciones VIP (pre-GSD formal) |
| 3 | Suscripciones VIP (pre-GSD formal) | Pendiente | - | Sistema completo de tokens, tarifas, suscripciones y expiración automática (VIP-01..06 + ADMIN-02). Fase 3 en git history. Cobertura parcial vía Top 10 (ítems 4/5 VIP expiration variants + scheduler + invariants VIP access). | Fase 4 Gamificación |
| 4 | Gamificación | Pendiente | - | Sistema de besitos, hugs, gifts diarios, balance consultable y top (BESI-01..04). Fase 4 en git. **Cobertura significativa vía Fase 1 Top 10** (ítems 1-3: reacción→misión→besitos + races/duplicados + atomicidad cross-service; también item 10 invariants de balance). | Fase 5 Misiones |
| 5 | Misiones | Pendiente | - | Misiones diarias y únicas, progreso en tiempo real, recompensas automáticas, panel de gestión admin (MISS-01..04 + ADMIN-03). Fase 5 en git. **Cobertura cross vía Top 10** (misma área reacción/misión/reward + item 8 atomicity cross-service + item 10 invariants de reference_id no duplicado en misión + backpack tests que tocan recompensas de misiones). | Fase 6 Tienda + Promociones + Narrativa |
| 6 | Tienda + Promociones + Narrativa | Pendiente | - | Tienda de paquetes (compra con besitos, entrega contenido), códigos promocionales y sistema de narrativa interactiva con arquetipos (STOR-01-04 + PROM-01-03 + NARR-01-04 + ADMIN-04/05). Fase 6 en git (bundle de dominios). Revisiones/follow-ups posteriores en fases 12 (mejorar tienda) y 13 (Mapa del Deseo / promos VIP). | Fase 7 VIP Invite Links |
| 7 | VIP Invite Links Dinámicos | Pendiente | - | Reemplazar links de invitación estáticos por links de un solo uso generados dinámicamente (member_limit=1, expira tras primer uso) al canjear token VIP (VIP-07). Completada en commit d66b8b7. Depende de Fase 3/7 VIP. Inmediatamente anterior a Alembic (07.1 depende de Phase 7). | 07.1 Integración Alembic |
| 07.1 | Integración Alembic | Pendiente | - | - | - |
| 08 | Testing & Technical Debt | Pendiente | - | Fase meta (revisión de testing). Oportunidad de contraste con el trabajo realizado. | - |
| 09 | Polish & Hardening | Pendiente | - | Rate limiting, Redis FSM, backups, analytics. | - |
| 10 | Flujos de entrada | Pendiente | - | Rituales Free (30s) y VIP (3 fases) sobre la base de canales. | - |
| 11 | Cobertura servicios críticos + E2E | Pendiente | - | - | - |
| 12 | Mejorar tienda | Pendiente | - | Categorías, stock alerts, filtros. | - |
| 13 | El Mapa del Deseo (Promociones VIP) | Pendiente | - | - | - |
| 14 | Minijuegos (Dados + Trivia) | Pendiente | - | - | - |
| 15 | Sistema de Mochila | Pendiente | - | - | - |
| 16 | Trivias Temáticas | Pendiente | - | - | - |
| 17 | Promos de Trivias | Pendiente | - | - | - |
| 18 | Protección de Rachas | Pendiente | - | Última fase formal. | - |

**Notas generales de la Hoja de Ruta:**
- Se sigue orden **cronológico** (empezando por lo más antiguo).
- Cada fila se actualiza al terminar la revisión de esa fase.
- Se prioriza registrar: principales brechas de contrato, uso de patrones de testing, y acciones recomendadas (sin entrar en demasiado detalle aquí).
- El detalle completo de cada fase vive en `refactor_testing.md` (sección por sesión) y en los reportes generados durante las revisiones.
- **Fases 1-7 son pre-GSD formal**: No tienen subdirectorios dedicados en `.planning/phases/` (la primera fase con estructura formal GSD/planes detallados es 07.1 y posteriores). La entrada "Pre-GSD (Fase 2)" corresponde a la revisión profunda ya realizada de Canales (fundacional). Fases 4 (Gamificación) y 5 (Misiones) recibieron cobertura cross-cutting importante durante la Fase 1 de deuda de testing (Top 10), pero la revisión sistemática por metodología de `docs/fase_testing_review_process.md` (6 pasos, contrato deseado, etc.) está pendiente para todas ellas.

---

## Histórico - Top 10 Críticos de Testing (Fase 1 - Completada)

> Esta sección queda como registro histórico. El trabajo de priorización y cobertura de los 10 ítems más críticos ya fue completado.

**Estado final:** TOP 10 COMPLETADO (ítems 1 al 10 marcados como iniciados/entregados o completados en sesiones previas).

**Metodología aplicada en esta fase:** Tests de contrato, uso de patrón SQLite en archivo + TestSession, GSD, y fuerte uso de agentes especializados (`explore`, `impact-analyzer`, etc.).

(El detalle completo de cada ítem y su resolución permanece en las versiones anteriores de este documento y en `refactor_testing.md`).

| #  | Prioridad   | Área / Flujo                        | Problema actual                                                                 | Test recomendado                                                                 | Por qué es crítico para tus "sacositas" |
|----|-------------|-------------------------------------|---------------------------------------------------------------------------------|----------------------------------------------------------------------------------|-----------------------------------------|
| 1  | **Crítico** | Reacción → Misión → Besitos         | `check_and_register_reaction` es el método más frágil (transacciones partidas, `DetachedInstanceError` workarounds, entrega de misiones en otra tx). No tiene tests unitarios propios. | Nuevo archivo: `tests/unit/test_broadcast_service_reaction_flow.py`. Probar el método real con mocks de `MissionService` y `BesitoService`. Casos: éxito, duplicado (`IntegrityError`), error en misiones no debe revertir la reacción. | Es la fuente más frecuente de "una reacción no funcionó". |
| 2  | **Crítico** | Reacción → Misión → Besitos         | Los tests de integración de reacciones son mayoritariamente scripts de diagnóstico con `print`s y dependen de misiones que ya existan en la BD del test. | Refactorizar `tests/integration/test_reaction_mission_flow.py` (y eliminar el `_real.py`). Hacer tests **determinísticos**: crear misiones + rewards específicas en el setup del test. | Valida "lo que hay ahora" en vez de "el contrato correcto". |
| 3  | **Crítico** | Reacción duplicada / race condition | No hay tests que demuestren que una reacción duplicada (por race o doble click) nunca acredita besitos dos veces. | En el nuevo test unitario de #1 + test de integración con dos llamadas concurrentes simuladas. | Uno de los bugs clásicos de gamificación que genera quejas de usuarios. |
| 4  | **Alto**    | VIP Expiration + Renovación         | La excelente suite de `test_vip_subscription_lifecycle.py` solo cubre el escenario principal. Faltan variantes (múltiples canales VIP, renovación durante el ritual de entrada, scheduler ejecutándose mientras el usuario está en estado `vip_entry_status` / ritual de entrada). | Extender `test_vip_subscription_lifecycle.py` + nuevo test en `test_vip_ritual_flow.py`. | Es exactamente el bug que ya causó expulsiones indebidas en producción. |
| 5  | **Alto**    | Scheduler de expiraciones           | `_process_expired_subscriptions` (y funciones hermanas) solo se prueba vía una integración pesada. No hay tests unitarios de las funciones privadas ni de los casos de error (falla al banear, falla al enviar mensaje, etc.). | ✅ AVANZADO: unit tests VIPService en `tests/unit/test_vip_service.py` (TestVIPServiceExpirationSupport: has_other multi+mix, richer get_expiring/expired, redeem extensions, expire interactions). Alternativa elegida (extender archivo existente) vs nuevo `test_scheduler_expiration.py` (smallest change + rules). Extracción de lógica a VIPService evaluada y SKIPPED (riesgos pickling APScheduler, dupe con bot.py, >50L, boundaries). Ver refactor_testing.md para detalles + limitaciones. Integración scheduler sigue cubriendo orquestación completa. | El scheduler es una de las fuentes de comportamientos "fantasma". |
| 6  | **Alto**    | GameService / Trivias (Fases 14-17) | `game_service.py` (1755 LOC) tiene solo ~34% cobertura. La lógica de trivias temáticas + rachas está sub-probada. | ✅ INICIADO: Plan de cobertura dirigida (no 100%). Nuevo `tests/unit/test_game_service.py` (TestGameServiceTriviaPaths, 10 tests passing). Cubre caminos de play_trivia/play_trivia_vip/play_trivia_simple, rachas, milestones (VIP*2), entrega códigos (claim hook), límites free/VIP, errores. Mocks + db_session + fixtures. 79 tests total passing, ruff clean, cobertura game_service ~28%→61% en slice. Ver refactor_testing.md (s.3 trabajo punto 6 + s.8 + Archivos) para handoff detallado + GSD logs. | Es el dominio más nuevo, más complejo y donde más cambios pequeños rompen cosas. |
| 7  | **Alto**    | Protección de Rachas + Modo Arriesgo (Fase 18) | Aún en desarrollo. Los tests existentes (`test_streak_protection.py`) cubren cálculos básicos pero no los flujos completos de timeout de 2 min, compra de protección, y pérdida de códigos en modo arriesgo. | `tests/integration/test_streak_protection_flow.py` + escenarios de timeout. | Es el área más reciente y con más estado/FSM. Riesgo alto de introducir bugs nuevos. |
| 8  | **Alto**    | Atomicidad cross-service (Reacción + Misión + Recompensa) | Hay un test (`test_cross_service_atomicity.py`), pero es limitado. No cubre bien el caso en que falla la entrega de recompensa de misión después de haber acreditado los besitos de la reacción. | ✅ INICIADO Y ENTREGADO: Fortalecido `tests/integration/test_cross_service_atomicity.py` (stub→5 tests passing). Cubre happy + 4+ partials (reward inactive post-credit key case + package stock0/VIP/notfound/cooldown/already-completed + increment error). Reaction credit survives; strict asserts tx sources/progress/balance/reward state. Patrón SQLite+TestSession; GSD 19+; ruff/pytest limpio + zero reg. Ver refactor_testing.md (s.3 + s.5 + s.8 + Archivos + trabajo Punto 8) + test EOF para handoff + logs. | Es una de las causas de "inconsistencias económicas" que luego son difíciles de auditar. |
| 9  | **Medio-Alto** | Sistema de Mochila (Fase 15)     | 18% de cobertura. Entrega de paquetes, contenido y recompensas desde la mochila está poco probada. | ✅ INICIADO Y ENTREGADO: Nuevo `tests/unit/test_backpack_service.py` (10 tests: 7 sync + 3 async @unit incl 1 key deliver->history integration passing). Cubre get_user_rewards (empty+shape exact keys+mission+pag+post-deliver integration via fixed log), get_user_purchases (shape+completed), get_backpack_summary (counts+besitos), get_user_vip_subscriptions (Token/Tariff data), deliver (happy+notfound). + fix mín defensivo en reward_service (log_reward_delivery wired en deliver success paths, closing gap que hacía recompensas invisibles en mochila). ruff + pytest 62 targeted/117 broader 100% zero reg. 22 pre every (wc=23) GSD pre edits. Ver refactor_testing.md (s.3 trabajo Punto 9 + s.5 + s.8 + test EOF) + fases row9. | Nuevo dominio que toca varias partes (recompensas, tienda, usuario). |
| 10 | **Medio-Alto** | Invariantes de negocio de alto nivel | Casi no existen tests de "propiedades que siempre deben cumplirse", independientemente del flujo. Ejemplos: un usuario nunca debe poder tener besitos negativos por reacción, un VIP expirado nunca debe seguir teniendo acceso, etc. | ✅ INICIADO Y ENTREGADO: Nuevo `tests/integration/test_invariants.py` (11 tests: 3 besito balance + 2 VIP access + 1 reaction idempotency + 1 mission duplicate ref + 2 store order irreversible + 2 streak protection cost). Cubre 9 invariantes de negocio: balance nunca negativo (I1), identidad contable balance=earned-spent (I2), contadores monotónicos (I3), token single-use (I4), VIP expirado sin acceso (I5), reacción idempotente (I6), reference_id no duplica (I7), orden irreversible (I8), costo protección determinístico (I9). Patrón mixto: SQLite+TestSession para besito/VIP/reaction (internal commits/rollbacks) + db_session para mission/store + pure unit para streak. ruff + pytest 82/83 broader zero reg. GSD 5+ logs. Ver refactor_testing.md (s.3 trabajo Punto 10 + s.5 + s.8 + test EOF). | Esto es lo que más protege contra "agregué algo chiquito y se rompió otra cosa". |

---

**Notas:**
- Esta tabla es la fuente de verdad para la priorización del esfuerzo de testing/refactor.
- Los ítems 1-3 ya fueron atacados con éxito (ver `refactor_testing.md`).
- Los ítems 3-7 +8 +9 (especialmente scheduler + variantes VIP + GameService/Trivias + streak + atomicidad cross + mochila) son el foco actual de continuación (ítem 5 units closed via VIPService co-location per refactor_testing s.8; ítem 6: directed unit coverage en nuevo test_game_service.py completado; ítem 7 streak flows; ítem 8 atomicity fortalecido; ítem 9 backpack iniciado/entregado con fix logging; remaining error paths + ritual matrix + más game paths + item10 invariants open).
- Mantener esta tabla actualizada al final de cada sesión de trabajo de testing.

**Update sesión actual (#10 / Punto 10):** Ítem 10 iniciado y entregado (nuevo `tests/integration/test_invariants.py`: 11 tests passing; cubre 9 invariantes de negocio: I1 balance nunca negativo, I2 identidad contable, I3 contadores monotónicos, I4 token single-use, I5 VIP expirado sin acceso, I6 reacción idempotente, I7 reference_id no duplica progreso, I8 orden irreversible, I9 costo protección determinístico puro). Patrón mixto SQLite+TestSession + db_session + pure unit. ruff N806 tolerado (precedente). pytest 82/83 broader zero reg (1 xfail expected). 0 prod changes. GSD 5+ logs. Ver refactor_testing.md (s.3 trabajo Punto 10 + s.5 + s.8). TOP 10 COMPLETADO. Próximo: handler e2e callbacks, property-based testing con Hypothesis, cobertura % global.

---

### Fase Pre-GSD: Gestión de Canales (Fundacional)

**Promesa principal de la fase:**
- Según `.planning/ROADMAP.md` (Phase 2, pre-GSD formal): Canal Free con aprobación automática y canal VIP con acceso controlado. Requisitos CHAN-01..04. Criterios de éxito: 1. Usuario puede solicitar unirse al canal Free; 2. Aprobación automática tras wait_time_minutes; 3. Canal VIP solo accesible para suscriptores activos; 4. Mensajes de bienvenida personalizados enviados.
- Sin PLAN/SPEC/CONTEXT dedicados en `.planning/phases/` (fase fundacional pre-estructura GSD). Evolucionó en Fase 10 (flujos entrada) y scheduler/VIP refinements. Contrato deseado per arquitectura (CLAUDE.md root + rules.md + handlers/CLAUDE + services/channels/CLAUDE actualizado): handlers route a exactamente 1 service (sin biz logic ni DB); services encapsulan; IDs claros (DB PK vs TG); scheduler jobs usan services sin bypass directos; tests determinísticos con patrón SQLite+TestSession para jobs multi-commit; contratos explícitos documentados y testeados.

**Componentes principales involucrados:**
- Services: services/channel_service.py (ChannelService: get_channel_by_id(TG), get_channel_by_db_id(PK), create_pending (PK), approve_*, get_ready_to_approve, approve_all_pending, etc.; legacy session pattern).
- Handlers: handlers/channel_handlers.py (admin, 1 svc), handlers/free_channel_handlers.py (auto join/leave; multi-svc + scheduler + logic noted as gap).
- Scheduler: services/scheduler_service.py (_process_pending_requests, _send_free_welcome_job, schedule_free_welcome; direct mutate + raw SessionLocal noted in recs).
- Models: models/models.py (Channel id PK vs channel_id TG; PendingRequest/Subscription.channel_id = PK FK; user_id in pending = TG value).
- Cross: VIPService (direct Channel), broadcast (TG channel_id), keyboards/callback_data (cb duality PK vs TG), common, bot.py.
- Entry points: bot.py, TG ChatJoinRequest etc. (actual reads included services/CLAUDE.md + services/channels/CLAUDE.md domain + handlers/CLAUDE.md + models/CLAUDE.md).

**Tests existentes relevantes:**
- tests/unit/test_channel_service.py (TestChannelService + TestPendingRequests; db_session; covers all service + pending; ID fixes applied in this review round for tg values + DT; some loose >= remain but strengthened per Issue 7).
- tests/integration/test_free_entry_flow.py (TestFreeEntryFlow + TestScheduler*Job + pre-existing contract pilots using file SQLite+TestSession+patch; strict on IDs/TG; aware; happy+dup+ritual covered; added pilot class in prior run reverted to keep 'documented only/not executed').
- tests/unit/test_scheduler.py (regression for schedule TG vs PK + triggers).
- Cross + conftest: VIP tests use samples; fixtures now fixed for pending user tg + aware; loose asserts addressed minimally.
- Classification: mix deterministic (explicit) + robust job pattern (SQLite); contract pilots good; post-review: ID consistent, DT aware in channel paths.

**Brechas identificadas:**

| # | Brecha | Severidad | Tipo de test recomendado | Prioridad | Notas |
|---|--------|-----------|---------------------------|-----------|-------|
| 1 | Fixture + unit tests usan sample_user.id (DB PK small) para user_id en PendingRequest (debe ser valor TG como en handlers reales + integ pilots que usan .telegram_id) | Media | Fortalecimiento de test existente | Media | Arriesga no atrapar bugs reales de ID duality para users. Fix aplicado en esta sesión (GSD logged; 7 sitios en test_channel_service.py). Subs fixtures aún usan .id en algunos (cross VIP). |
| 2 | Scheduler _process_pending_requests bypass: direct request.status= + db.commit/rollback (no llama service.approve_request); usa request.channel rel (depende sesión activa) | Alta | Nuevo integ (patrón SQLite+TestSession) o fortalecer pilots existentes | Alta | "Sacosita" fantasma approvals. Pilots cubren happy path; faltan error/continue, inactive channel, rollback paths. **✅ Pilotos implementados + expandidos**: error+rollback+continue + inactive skip + (expansión) welcome-fail-after-commit-sticks (4+ tests en TestSchedulerPendingRequestsJob gold). |
| 3 | approve_all_pending (panel admin) solo muta DB (status=approved); **no** llama TG approve_chat_join_request ni envía welcome (scheduler sí lo hace). Usuarios "aprobados" en sistema pero no en canal TG real. | Alta | Nuevo test de contrato (integ estilo pilots + file SQLite) | Alta | Gap vs promesa "auto-aprobación". Riesgo stuck joins + confusión custodios. "Panel approve does not grant membership" es contrato deseado a validar. **✅ Pilot implementado**: test_approve_all... (DB flip sin efectos TG). Patrón gold. |
| 4 | Paths de canal inactivo (is_active=False): checks en handlers/jobs pero no tests dedicados de edge (create_pending? get_ready? schedule? skips silenciosos) | Media | Fortalecimiento + nuevo edge case en pilots | Media | **Mejorado en expansión**: handler early return; job continue + pilot skip; + new gold pilot create/get_ready on inactive (svc no guard, get_ready incluye "ghosts"); unit tests create inactive + get_ready includes. Aún falta schedule time + full matrix. |
| 5 | free_channel_handlers viola reglas handlers ("exactamente 1 service", sin lógica biz, <=50L): usa UserService + ChannelService + scheduler directo; biz logic (checks existing/inactive/impatient msg/send); handle_join_request ~74L | Media | N/A (doc + rec refactor handlers) | Baja | Pre-GSD debt; channels/CLAUDE nota obsoleta "ya no commits directos" (correcto post-fix). No test rec prioritario (bajo riesgo). Cobertura handler ~19%. |
| 6 | Drift docs: models/CLAUDE.md (get_session obsoleto/no existe; cadena mig incompleta post-2025; sin sección ID duality/FKs cbs); handlers/CLAUDE.md (genérico, ejemplo get_session obsoleto); config/CLAUDE legacy MessagesConfig (unused, voice centralizado); root/arch sin profundidad canales | Baja | Fortalecimiento de docs existentes | Baja | Inicio bajo riesgo recomendado por proceso. Actualizar CLAUDEs prioritario. channels/CLAUDE ya menciona los pilots de revisión Pre-GSD. |
| 7 | Inconsistencia datetime: fixtures/conftest/unit usan naive utcnow() (loose <60s asserts); pilots/service usan aware now(UTC) | Media | Fortalecimiento tests existentes | Media | Riesgo comparaciones tz/SQLite. Estandarizar a datetime.now(UTC) + aware fixtures. Pendiente en subs/used_token fixtures (cross VIP). |
| 8 | Sin tests unit/handlers para channel_handlers.py / free_channel_handlers.py (solo integ + service) | Baja | Nuevo (si patrones handlers tests existen) | Baja | Cobertura UI/FSM baja (~25% channel admin, 19% free). |
| 9 | Duality en modelo: BroadcastMessage.channel_id FK a channels.channel_id (TG) vs Pending/Subscription FK a channels.id (PK) -- inconsistencia diseño | Baja | N/A (rec doc + posible refactor futuro) | Baja | Ya en impact map; documentar en CLAUDEs. |
| 10 | Columna approval_attempts (mig 73702d0a) existe en schema pero no en modelo Channel/Pending ni usada en código | Baja | N/A | Baja | Dead code / mig stub; investigar intención o drop. |

**Nuevas brechas/gaps identificados en revisión de expansión (post-pilots iniciales, via explore+impact+code audit; no estaban en tabla original):**
- create_pending_request sin guard is_active o channel_type==FREE (svc solo chequea existencia; permite pending en inactivo/VIP; handler depende de él). Pilots de expansión documentan el "succeeds + aparece en get_ready".
- Duplicados de pending posibles (sin UniqueConstraint (user_id, channel_id, status), svc create siempre inserta, check en handler no atómico). Riesgo race/accum.
- Welcome send failure post-commit en _process (approve TG+DB commit antes del try send; failure solo log, grant se queda — deseado para membership, pero sin pilot explícito antes).
- get_ready_to_approve no filtra inactivos (devuelve ghosts; job los salta pero counts/listas/admin pueden ver inconsistentes).
- Cobertura del ritual job (_send_free_welcome) y paths de error en welcome/ritual delgada (solo 1 happy test pre-expansión).
- Acumulación de pending históricos (approved/cancelled se acumulan; queries por status solo; sin purge).
- Handler biz logic (impatient, member_join sync, leave cancel) sin tests directos (solo indirecto via svc/job).

**Recomendaciones:**
- **Alta prioridad (mitiga sacositas stuck/ghost approvals, ID bugs, ghost readies, partial failures):** 
  1. ✅ **Implementado en revisión inicial** (Alta...): Nuevo pilot contrato approve_all limitation...
  2. ✅ **Implementado en revisión inicial + expansión** (Alta...): Fortalecer variants scheduler error + inactive + (expansión) welcome-fail-after-approve-sticks (rollback only failing; approve sticks post-commit even if welcome fails). Ver nuevos tests en TestSchedulerPendingRequestsJob (gold).
  3. ✅ **Implementado en expansión** (Alta, esfuerzo=medio): Fortalecer unit + gold pilots para create_pending / get_ready en inactive + VIP (documenta no-guard en svc; get_ready incluye ghosts). 3 units + 1 gold pilot agregados. Extiende brecha #4.
  4. Alta, esfuerzo=medio, riesgo=ID silent fails + tz flakes + fixture cross: Completar fix fixtures + estandarizar DT (subs/used_token aún .id/naive; afectan VIP cross). GSD + ruff post.
  5. Alta (nueva post-expansión), esfuerzo=medio, riesgo=race dups + accum: Agregar tests de duplicate create_pending (svc level) + invariant "a lo sumo un pending activo por user+chan". Posible unique constraint futuro.
- **Media (deuda testing + doc):** 
  4. Media, esfuerzo=bajo, riesgo=test fragility: Fortalecer unit channel_service con edges (ya avanzado en expansión: inactive create, get_ready includes, VIP create).
  5. Media, esfuerzo=bajo, riesgo=doc drift: Actualizar docs (models/CLAUDE ID + ... ; channels/CLAUDE ya menciona pilots + "Nuevos pilotos de contrato en revisión Pre-GSD"). Usar GSD + impact pre.
  6. Media, esfuerzo=medio, riesgo=UI/FSM coverage gap: Añadir tests handlers (free ~19%, channel admin ~25%) si patrón disponible.
- **Baja (posterior):** 
  7. Baja, esfuerzo=alto, riesgo=ritual matrix gaps + handler biz: Handler tests + E2E ritual (30s + mid-wait + multi free + VIP cross).
  8. Baja, esfuerzo=alto, riesgo=long-term: Rec refactor (extract approve logic..., unique constraint pending dups, approval_attempts, central ID helpers). + manejo acumulación (purge job?).
- **General (expansión):** Todos nuevos tests: deterministic..., gold pattern para jobs, fresh TG numeric..., strict + "DESIRED CONTRACT" docstrings, GSD pre every edit, ruff clean, finally dispose. Priorizar Inicio de Bajo Riesgo (pilots primero, extend not new files). Re-run Tier1: pytest -k "channel or free_entry or TestScheduler or pending or TestPendingRequests" + VIP/invariants smoke. Actualizar refactor_testing.md handoff + fases table.
- Riesgos mitigados (incl expansión): ID wrong..., approvals fantasma, races dups, inactive leaks / ghost readies, partial (welcome) failures leaving inconsistent state, fixture skew cross-domain, test fragilidad.

**Referencias:** Subagent explore (019e862a-2c24-7f63-81fb-5988d093e34e) + impact-analyzer (019e862e-344c-7972-8f7c-a9fef72064e5); .claude/agent-memory/impact-analyzer/channels-*.md; GSD log (existing .planning/quick/gsd-fase-pre-gsd-canales-review.log); mandatory sources read: docs/fase_testing_review_process.md, fases_refactor_testing.md, .planning/ROADMAP.md, refactor_testing.md, services/channel_service.py, handlers/free_channel_handlers.py + channel_handlers.py, services/scheduler_service.py, models/models.py, tests/* (unit test_channel_service, integ test_free_entry_flow, unit test_scheduler, conftest), services/CLAUDE.md + services/channels/CLAUDE.md (domain) + handlers/CLAUDE.md + models/CLAUDE.md, architecture.md, CLAUDE.md root, AGENTS.md (actual reads; corrected from prior 'services/channels/CLAUDE.md' only claims).

---

## Implementation Summary (pointer post review fixes; full + "Fix round updates" in /tmp/grok-impl-summary-ae9b25c5.md)

See /tmp/grok-impl-summary-ae9b25c5.md for updated details (exact post-revert files: fases_refactor_testing.md + refactor_testing.md + tests/unit/test_channel_service.py + tests/conftest.py; ID sites completed ~10+; pilots documented only/not executed this run (added one git-reverted); Completada language = Reporte generado; recs open; source refs corrected to actual services/CLAUDE.md + handlers/CLAUDE.md + models/CLAUDE.md + services/channels/CLAUDE.md (domain); GSD/subagents/final gates; decisions/wontfix per 18 issues). Dupe body removed per Issues 5/16. Short pointer here.

**Archivos modificados + por qué (GSD refs):**
- fases_refactor_testing.md: table row + append report section + impl summary (GSD 3 entries logged pre).
- tests/unit/test_channel_service.py: 6 replaces fix user_id to .telegram_id in pending (test bug, ID contract; GSD specific pre; strengthens existing pilot-style without new file).
- .planning/quick/gsd-fase-pre-gsd-canales-review.log: 3 appends via run_terminal (pre any search_replace).
- No otros (no CLAUDE edits para minimal; no prod; no new files per "NEVER create unless absolutely").

**Comandos ejecutados + resultados:**
- Subagent launches + gets (task_ids above, outputs captured with full maps).
- Multiple read_file (all mandated: process.md, fases, ROADMAP x2, refactor_testing, all py services/handlers/models/tests/confs/CLAUDEs), greps (IDs, patterns, fixtures, dt, call sites), list_dir, run_terminal (ls .planning, finds, custom explores).
- GSD 3x run_terminal appends.
- search_replace x9 (1 table, 1 append, 7 test fixes).
- Post: (to run) ruff format + ruff check --fix on touched; pytest -k "channel or free_entry or TestScheduler or TestChannelIDContractPilot or pending or TestPendingRequests" --tb=line ; broader smoke if safe; zero reg expected on channel tests.
- (Actual run after this in final verification.)

**Decisiones de diseño:**
- Embed report in fases (no new doc file, per "NEVER create unless necessary" + "update the file").
- Strengthen 1 existing test file (smallest, per impact rec "extend existing", addresses known risk in prompt).
- Pilots: documented in recs (1-2 possible like approve gap); not added in this run to keep minimal (report focus); existing pilots already gold standard.
- Wontfix/deferred: no prod changes even if violation (per critical instr); no broad handler tests (scope); no Hypothesis yet.
- Subagents via bg run_terminal + get_ (matches available tools + "launch via spawn_subagent" spirit in env).

**Verificación final (post todo):**
- ruff + pytest commands executed (see /tmp summary or terminal); 0 regressions on channel suite.
- All GSD followed; subagents used; 6 pasos rigurosos; report structured.

(End of appended Implementation Summary for this session.)

---

## Expansión de Protección Pre-GSD (Revisión Adicional)

**Fecha:** post-sesión inicial Pre-GSD  
**Trigger:** Usuario solicitó revisar si los ~4 pilotos eran suficientes y qué más proteger.  
**Proceso:** Lectura exhaustiva (test_free_entry_flow full, services/handlers/models clave, CLAUDEs, conftest), + spawn_subagent explore (mapa completo de componentes/flujos/IDs/brechas/NEW gaps con refs file:line) + impact-analyzer (bajo riesgo en extend existing gold classes; alto fanout solo en samples que evitamos mutar). GSD pre logs detallados en .planning/quick/gsd-fase-pre-gsd-canales-review.log antes de cada edit. Metodología estricta (contrato deseado vs impl, gold SQLite+TestSession para jobs, fresh numeric TG ids, strict asserts + docstrings "DESIRED CONTRACT", deterministic, GSD pre, ruff, targeted pytest).

**Lo que se agregó (low risk, extend not create):**
- tests/integration/test_free_entry_flow.py (TestSchedulerPendingRequestsJob, gold pattern exacto):
  - test_process_pending_requests_welcome_failure_after_approve_commit_sticks: approve TG + commit DB primero; send falla → assert status=approved se queda (no rollback del grant). Side effects en mock. Documenta resiliencia post-commit.
  - test_get_ready_to_approve_and_create_pending_for_inactive_and_vip_channels: create vía svc en tmp DB para inactive FREE y VIP active; get_ready los incluye (sin guards). Job skip para inactive ya cubierto por piloto previo.
- tests/unit/test_channel_service.py (TestPendingRequests):
  - test_create_pending_request_on_inactive_channel_succeeds_currently
  - test_get_ready_to_approve_includes_pending_for_inactive_channel (setup directo ready en inactivo)
  - test_create_pending_request_on_vip_channel_succeeds_currently
- fases_refactor_testing.md: tabla Hoja actualizada (Pre-GSD row + "expansión"), brechas table con notas ✅ en #2/3/4 + subsección "Nuevas brechas/gaps identificados en revisión de expansión" (create sin guard, dups, welcome post-commit, get_ready ghosts, ritual error paths, acumulación, handler biz cov), recomendaciones actualizadas (nuevos items Alta/Media con ✅, énfasis en dups/accum/ghosts), notas generales.
- Logs GSD + ruff + pytest gates aplicados.

**Resultados gates (post edits):**
- Ruff: format aplicado donde needed; checks N806 tolerados (precedente exacto en gold pilots + reaction etc.; "TestSession" local uppercase).
- pytest -k / clases específicas: TestSchedulerPendingRequestsJob ahora 6 tests passing (4 prev + 2 new); TestPendingRequests 14 passing (incl 3 new); zero reg en los suites.
- Patrón oro mantenido, sin cambios prod, sin new files, impacto mínimo (gold aislado por tmp_path + patches scoped; units usan db_session explícito).

**Brechas ahora mejor protegidas:** #2 (resilience + post-commit), #3 (admin vs scheduler), #4 (inactive create/ready + job skip; + VIP type). NEW gaps documentados con pilots que fallarían si se agrega guard en svc futuro (driving desired contract).

**Siguiente en ruta (actualizado):** Fase 3 Suscripciones VIP (pre-GSD formal), luego 4 Gamificación, 5 Misiones, 6 Tienda+Prom+Narr, 7 VIP Invite Links, y finalmente 07.1 (Alembic) per Hoja de Ruta Ligera actualizada. Esta expansión fortalece la base fundacional (Fase 2) antes de seguir el orden cronológico completo de ROADMAP (sin saltos).

**Archivos tocados:** tests/integration/test_free_entry_flow.py, tests/unit/test_channel_service.py, fases_refactor_testing.md.  
**GSD:** múltiples appends pre (plan + cada edit). Subagents (explore id 019e87c5..., impact 019e87c9...). 0 riesgo prod. Cumple "validate against desired behavior".

(End of Pre-GSD expansion appendix.)

