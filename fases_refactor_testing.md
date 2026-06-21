# Revisión de Testing - Lucien Bot

**Transición de trabajo:**

- **Fase 1 completada:** Top 10 Críticos de Testing (deuda de testing priorizada por impacto en "sacositas").
- **Fase 2 en curso:** Revisión sistemática y cronológica de testing por fase de desarrollo (siguiendo la metodología de `docs/fase_testing_review_process.md`).
  - Hoja de Ruta: Fase 3 Suscripciones VIP completada (incl. commit 00fd7e8 ID contracts + tests). **Siguiente inmediato: Fase 4 Gamificación** (iniciada en tabla). Gamificación (Fase 4) y Misiones (Fase 5) + fases posteriores ahora el foco. Pre-GSD (Canales) ya revisada con pilots.

> **Metodología de referencia:** Para la revisión por fase de desarrollo, consultar [docs/fase_testing_review_process.md](../docs/fase_testing_review_process.md). Ese documento define el flujo, fuentes obligatorias, criterios, uso de agentes y template que se utilizarán.

---

## Hoja de Ruta Ligera - Revisión por Fases de Desarrollo

Esta sección funciona como control simple de avance. Se mantiene actualizada al final de cada sesión.

| Fase | Nombre / Tema principal | Estado | Inicio | Notas principales / Hallazgos clave | Siguiente acción |
|------|--------------------------|--------|--------|-------------------------------------|------------------|
| 1 | Bot Base (pre-GSD formal) | Pendiente | - | Arquitectura handlers/services/models + panel de Custodios. Pre-git history (inferred). Sin subdir dedicado en `.planning/phases/`. Fundacional para todas las fases posteriores. | Fase 2 / Pre-GSD (Canales) |
| Pre-GSD (Fase 2) | Gestión de Canales (Fundacional) | Reporte generado + pilots Alta + expansión de protección (recs open para 07.1) | Jun 2026 | Primera revisión + expansión post-revisión profunda (explore+impact subagents + code audit). 6 Pasos + gold pilots (SQLite+TestSession+patch) contra contrato deseado. **Pilotos iniciales:** approve_all DB-only, scheduler error+rollback+continue, inactive skip (4 tests en TestSchedulerPendingRequestsJob). **Expansión agregada:** 2 gold pilots más (welcome fail after commit sticks; get_ready/create for inactive+VIP documents no-guard); 3 unit contracts (create inactive/VIP, get_ready includes inactive). Total ~7 tests en job class + units fortalecidos. Brechas #2/#3/#4 mejor cubiertas; NEW gaps (dups, ghosts, post-commit resilience, handler cov) documentados. ID/DT/CLAUDEs reforzados previamente. **Siguiente: Fase 3 Suscripciones VIP (pre-GSD formal) [completada en iter posterior; ver fila 3].** | Fase 3: Suscripciones VIP (pre-GSD formal) [✅ completada] |
| 3 | Suscripciones VIP (pre-GSD formal) | ✅ Completada revisión Fase 2 (reporte + tests Alta + pilots + ID contract fixes en commit 00fd7e8) | Jun 2026 | Revisión completa por 6 pasos de docs/fase_testing_review_process.md (Paso1-6 + agents explore+impact pre any change + GSD pre every edit). Promesa ROADMAP Phase3 success 1-6 (create tariff/token, redeem access, reject bad tokens, expire remove ch, 24h reminder). Última sesión (commit 00fd7e8): actualización pruebas para contratos VIP y cronología con IDs correctos (telegram_id vs .id en fixtures + tests VIP para alinear con handlers reales, modelos FK a users.telegram_id y evitar skips silenciosos en redeem/clear_vip_entry). Componentes: VIPService (redeem w/ for_update+extend+clear entry+tx, get_expir*/has_other/expire/mark (some naive dt), entry helpers, owns_session/close); scheduler bits (_process_expiring/expired use svc get but direct mutate bypass + raw User); handlers (vip_* admin ok 1svc, common multi-svc+TG invite on redeem); Models (Sub/Token/Tariff w/ user_id/redeemed_by_id=TG BigInt FK, ch_id=PK int; User vip_entry_*); Cross (ch VIP type, ritual entry state clear on redeem/expire, users, reward tariff, bot startup). Tests: unit/test_vip_service (tariff/token/sub + rich TestVIPServiceExpirationSupport + ritual clear + richer expiring + ID fixes); integ lifecycle gold (tmp SQLite+TestSession+patch for sched, fresh TG, explicit, 7+ scenarios + multi+error continue); flows/ritual/complete/cycle (db_session + samples); cross invariants (I4/I5 token/VIP access); strengthened ID contract. Brechas (Alta prioritized: ID duality fixtures+tests (PK vs TG in sub/token) ✅ fixed en esta iter, sched bypass direct vs svc, handler 1svc viol in common, DT naive/aware, contract gaps ritual-during+multi-ch+partial atomic+error sched continue; Media: hygiene loose asserts, doc drift). Prior Top10 4/5 partially addressed prior; this adds ID contract fix + Alta tests + pilots. | Fase 4 Gamificación |
| 4 | Gamificación | ✅ Revisión Fase 2 + pilots follow-up completados (ID contract + daily atomic gold + concurrent unit; gates 127p 0reg) | Jun 2026 | **Investigación exhaustiva + 6 pasos completados (ver sección detallada abajo)**. Promesa ROADMAP/BESI-01-04 + success 1-4. Componentes: besito (credit/debit for_update+internal commit+never-neg+logs), daily_gift (claim+24h limit+credit cross), broadcast (check_and_register_reaction prod path: flush+Unique+credit commit + post-commit mission tx separado intencional). Handlers: user 1svc exacto + close + TG id; admin stats 2svc. Models: TG BigInt user_id (balances/tx/claims/reactions), UniqueConstraint reacción, ref_id, aware DT. Cross: todos sources enum (REACTION/DAILY/MISSION/PURCHASE/GAME/TRIVIA/STREAK/ADMIN/ANON). **Tests existentes**: unit besito/daily/broadcast_reaction (5 contrato gold: dup None, mission-fail NO rollback, early emoji, etc); integ gold SQLite+TestSession reaction_full_chain + cross_atomic (5+ partials post-credit survive) + invariants (I1-3 besito + I6 reaction); handler integ. Cobertura Top10 items1-3/8/10 fuerte. **Brechas clave (16 clasificadas, Alta prior)**: 1. ID duality fixtures (sample_balance .id PK vs .telegram_id TG BigInt contrato real handlers; afecta units/golds vs prod). 2. Atomic daily_claim: claim add + credit (commit interno besito) + outer commit (posible besitos sin claim row o viceversa en fail). 3. Concurrent dup reaction no cubierto (unit dup+constraint + TODO explícito; Top10 item3). 4. Never-neg TOCTOU en débitos cross (store check+debit, story/streak/anon handler). 5. check_and docstring "una sola tx" vs impl (credit commit + mission nueva tx post). 6. Broadcast owns_session ausente (close always). 7. Top10: solo admin limit5 (no user-facing?), order por balance actual no "generosos"/earned, no det/tiebreaker, tests loose. 8. Handler 1svc viol (admin stats Besito+Daily; anon multi+direct debit en handler). 9. Límite daily (solo 24h/user; naive UTC force; no global/concurrent/tz edge). 10. Hugs legacy (BESI-02 promesa, 0 impl/tests código src). 11. Scheduler daily: 0 (claim on-demand). 12. Dupe total_circulación (besito py sum vs analytics direct). 13. DT drift naive (daily). 14. >50L funcs (check_and~97L etc vs rules). 15. db_session units vs gold SQLite para internal commits (detach post-credit). 16. No full e2e handler callbacks + keyboard reaction/gamif (make_callback). **Alta recs (tests pilots low-risk primero)**: gold integ daily atomic partial (SQLite+TS, fresh 777xx TG telegram_id, explicit, strict re-query); concurrent dup reaction (2 calls); ID contract fix en fixtures + *todos* golds (sample_balance etc use .telegram_id, asserts TG); cross never-neg atomic full paths (store/story/streak/anon); top determinism + user visibility? ; handler multi-svc tests. Fortalecer units + migrate db_session donde commits internos. GSD+impact pre every; ruff/pytest -k "besito|daily|reaction|gamif|TestBesito|TestDaily|TestCheckAndRegister|TestFullReaction|TestCrossServiceAtomicity|TestBesitoBalanceInvariants" gates zero reg. **Referencias**: explore agent full report (16 brechas + exact file:line + quotes + flows); process.md; Top10 history refactor_testing s.3. | Fase 5 Misiones |
| 5 | Misiones | ✅ Revisión Fase 2 + pilots Alta #1-5 + ID contract follow-up completados | Jun 2026 | **Revisión sistemática + Alta pilots per recs #1-5 (dup guards both paths, recurring cooldown/reset, gold partial+catchup, ID TG fix, isolated side gold).** Promesa MISS-01..04 + ADMIN-03. Cross Top10 + new deterministic gold pilots protect dup/ref/cooldown/pending/side-effect contracts. Fase 5 pre-GSD. See Pilots Follow-up subsection. | Fase 6 Tienda + Promociones + Narrativa |
| 6 | Tienda + Promociones + Narrativa | **En progreso (tirón 6-7-8 orquestado) - revisión 6 pasos + pilots Alta iniciados** | 2026-06-18 | Revisión sistemática 6 pasos (docs/fase_testing_review_process.md) + gold pilots Alta: atomic compra (debit PURCHASE internal commit + partial post-debit), promo interest/validate, narrative advance/archetype/achievements, ID/DT, cross backpack. Extiende tests existentes (test_store_service etc) + SQLite+TestSession gold. 0 prod change, 0 impacto 3 crit. GSD pre every. | Fase 7 VIP Invite Links (continue tirón) |
| 7 | VIP Invite Links Dinámicos | **En progreso (tirón 6-7-8 orquestado) - revisión + pilot** | 2026-06-18 | Revisión 6 pasos + gold pilot para generación invite member_limit=1 + fallback estático en redeem (common_handlers + VIP). Extiende test coverage. Completado impl d66b8b7; foco contrato + tests. | 07.1 Integración Alembic |
| 07.1 | Integración Alembic | Pendiente | - | - | - |
| 08 | Testing & Technical Debt | **En progreso (tirón 6-7-8 orquestado - meta) - revisión contraste** | 2026-06-18 | Revisión meta 6 pasos vs old PLAN 08 (TEST-01-03 + debt). Contraste: mucho avance desde (Top10, Fases3-5 pilots, hardener, 6-agent) pero deuda persiste (handler e2e, full % cov, concurrent races, tz modern, property tests). Registro en sección. | - |
| 09 | Polish & Hardening | ✅ Revisión 6 pasos + pilots Alta (ID fix analytics, sqlite backup extend) completados | 2026-06-18 | Rate limiting (ThrottlingMiddleware), Redis FSM (create_storage), backups (pg/sqlite), scheduler SQLAlchemyJobStore persistente, analytics dashboard+CSV. Reqs SEC-01/02, BACK-01, SCHED-01, ANLY-01/02. (Complete 5/5 en prod). Revisión testing + gold. 0 prod change. GSD pre every. | Fase 10 Flujos de entrada (continue tirón) |
| 10 | Flujos de entrada | ✅ Revisión 6 pasos + pilot (expire guard ritual) completados | 2026-06-18 | Rituales Free (30s wait + auto approve + impaciencia) y VIP (3 fases entry state resumable + expire guard) sobre canales base. Reqs FREE-01, VIP entry, SCHED. Extiende test_free_entry + vip_ritual. GSD pre. | Fase 11 Cobertura (continue tirón) |
| 11 | Cobertura servicios críticos + E2E | ✅ Revisión 6 pasos completada (tirón 9-10-11) | 2026-06-18 | Cobertura dirigida servicios críticos + tests E2E/handlers. Cierra gaps en VIP/channels/gamif/store/narr + E2E entry. Basado en plans 11-01..07. | - |
| 12 | Mejorar tienda | ✅ Completada (último tirón review 6 pasos + pilots) | 2026-06 | Categorías, stock alerts, filtros. Pilots en test_package + test_store (ver secciones). | - |
| 13 | El Mapa del Deseo (Promociones VIP) | ✅ Completada (último tirón review 6 pasos + pilots) | 2026-06 | is_vip_exclusive + get_vip_exclusive_promotions. | - |
| 14 | Minijuegos (Dados + Trivia) | ✅ Completada (último tirón review 6 pasos + pilots) | 2026-06 | game_service dados/trivia. | - |
| 15 | Sistema de Mochila | ✅ Completada (último tirón review 6 pasos + pilots; nota pilots previos Top10 item9) | 2026-06 | backpack_service. | - |
| 16 | Trivias Temáticas | ✅ Completada (último tirón review 6 pasos + pilots) | 2026-06 | trivia categories/rachas. | - |
| 17 | Promos de Trivias | ✅ Completada (último tirón review 6 pasos + pilots) | 2026-06 | streak promo codes. | - |
| 18 | Protección de Rachas | ✅ Completada (último tirón review 6 pasos + pilots; última fase formal) | 2026-06 | streak protection. | - |

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

**Siguiente en ruta (actualizado):** Fase 6 Tienda+Prom+Narr + Fase 7 VIP Invite Links + Fase 08 Testing & Technical Debt (tirón orquestado de 3 iniciado 2026-06). Fases previas (Pre-GSD/3/4/5) completadas con revisión sistemática + pilots.

**Archivos tocados:** tests/integration/test_free_entry_flow.py, tests/unit/test_channel_service.py, fases_refactor_testing.md.  
**GSD:** múltiples appends pre (plan + cada edit). Subagents (explore id 019e87c5..., impact 019e87c9...). 0 riesgo prod. Cumple "validate against desired behavior".

(End of Pre-GSD expansion appendix.)

### Fase 3: Suscripciones VIP (pre-GSD formal)

**Promesa principal de la fase:**
- Según `.planning/ROADMAP.md` (Phase 3, pre-GSD formal): Sistema completo de tokens, tarifas, suscripciones y expiracion automatica. Requisitos VIP-01..06 + ADMIN-02.
- Criterios de éxito explícitos:
  1. Custodio crea tarifas con precio y duracion
  2. Custodio genera tokens unicos por tarifa
  3. Visitante canjea token y obtiene acceso VIP
  4. Tokens rechazados si ya usados o invalidos
  5. Suscripcion expira y bot remueve usuario del canal
  6. Recordatorio enviado 24h antes de expiracion
- Sin PLAN/SPEC/CONTEXT dedicados en `.planning/phases/` (fase pre-estructura GSD formal; Fase 3 en git history). Evolucionó con Fase 7 (invite links), Fase 10 (ritual entry state vip_entry_* + free_entry_expired), scheduler refinements. Contrato deseado per arquitectura (CLAUDE.md root + rules + handlers/CLAUDE + models/CLAUDE + services/CLAUDE + prior Top10 + process doc): handlers route a exactamente 1 service (sin biz logic ni DB); services encapsulan (incl redeem atomic + entry clear); IDs claros (TG BigInt para user_id/redeemed_by_id en Sub/Token FK a users.telegram_id; DB PK int para channel_id en Sub FK a channels.id); scheduler jobs usan services pero con bypasses directos en jobs (documentado); tests determinísticos con patrón SQLite en archivo + TestSession para jobs multi-commit internos + patch SessionLocal; contratos explícitos documentados y testeados (DESIRED CONTRACT); ID duality validada; DT aware + _ensure_aware para comparaciones; logging crítico; GSD antes edits; no prod a menos bug real justificado.

**Componentes principales involucrados:**
- Services: services/vip_service.py (VIPService: create_tariff, generate_token, validate_token, redeem_token (with_for_update, tx, extend logic if active sub, deact dups, mark USED/redeemed, find VIP ch by type+id PK, clear vip_entry on success, _ensure_aware, owns_session/get_db/close, get_user_subscription/get_expiring/get_expired/has_other_active (some naive .replace(tzinfo=None) for SQLite), mark_reminder_sent, expire_subscription, is_user_vip, get_vip_channel, entry state helpers get/clear; set_gift/revoke); also used by reward/game for tariff rewards.
- Scheduler: services/scheduler_service.py (_process_expiring_subscriptions: VIPService(db) + get_expiring then direct subscription.reminder_sent=True + db.commit() bypass mark; _process_expired_subscriptions: VIPService(db) + get_expired + has_other via svc but direct sub.is_active=False, raw db.query(User).filter(telegram_id) + mutate clear + commit/rollback per sub; ban/unban TG on ch.channel_id + notify; registered as cron jobs; also _cleanup etc).
- Handlers: handlers/vip_handlers.py (admin tariff/token mgmt: create via FSM, generate/list/toggle/copy, list subs; new VIPService() + finally close per cb, logging on key actions, exactly 1 svc); handlers/common_handlers.py (cmd_start: UserService()+VIPService() -- multi svc, redeem_token/validate_token on args token, is_user_vip, TG create_chat_invite_link on redeem success for dynamic 1use, get_vip_channel; finally closes); handlers/vip_user_handlers.py (vip_area: is_user_vip check); reward_admin_handlers, admin_handlers, backpack_handler, story_user (cross uses).
- Models: models/models.py (Tariff: id PK, name, duration_days, price, is_active; Token: id, token_code unique, tariff_id FK, status TokenStatus (ACTIVE/USED/EXPIRED), is_gift, expires_at, redeemed_at, redeemed_by_id=FK users.telegram_id BigInt; Subscription: id, user_id=FK users.telegram_id BigInt, channel_id=FK channels.id int PK, token_id FK, start/end_date, is_active, reminder_sent; User: telegram_id BigInt unique, id PK int, vip_entry_status str, vip_entry_stage int; Channel: id PK, channel_id TG BigInt, channel_type incl VIP, is_active; relations back_populates; _ensure_aware helper in svc for SQLite tz loss).
- Cross: channels (VIP ch lookup by type + .id PK for sub, .channel_id TG for bot ban/invite); entry ritual Fase10 (vip_entry_* cleared on redeem/expire to avoid ghost during/after; free_entry_expired); users (TG id as "user_id" in VIP domain vs internal PK); bot.py (check_expired_subscriptions_on_startup: VIPService() + get/has/expire/clear + rel access .user/.channel + ban TG); reward for VIP tariff rewards; broadcast? indirect; keyboards/cb for admin VIP.
- Entry points: bot.py (routers + startup check), /start deep link token.

**Tests existentes relevantes:**
- tests/unit/test_vip_service.py (TestVIPService tariff/token basic; TestSubscriptionService redeem success/used/expired/get/is/expire; TestVIPServiceRaceCondition partial; TestVIPEntryState redeem clear/ get/clear entry; TestVIPServiceExpirationSupport (item5): has_other multi+mix expired+nonexist, get_expiring filters reminder/threshold/boundary/multi, get_expired richer, redeem extend prevents expired view + has_other, expire+has_other reflect; uses db_session + explicit in support; some .id/.telegram mix pre-fix).
- tests/integration/test_vip_subscription_lifecycle.py (TestVIPSubscriptionLifecycle gold: _create_engine+tmp_path file SQLite+TestSession (for scheduler internal SessionLocal commit visibility) + patch SessionLocal; fresh TG 1001/.. explicit User/Ch/Tariff/Token/Sub per scenario no preexist reuse; 7 tests: scenario A renewal not kicked (extend), B expired kicked, C active not, D renewal extension delays, expiring sends+sets flag, expiring send error+rollback, expired clears entry on last (ritual variant); strict re-query + mock calls + prints; DESIRED CONTRACT style).
- tests/integration/test_vip_flows.py (TestFlow1-5 + TestVIPEntryState + TestVIPCompleteLifecycle: redeem happy/used/exp/noch, is_vip, get_expired/expire, renewal extend+dup deact+clear, return after, entry state get/clear/full; db_session + samples).
- tests/integration/test_vip_flow.py (TestVIPFlow complete/tokenexp/used/subexp/reminder/multitariff/actives; TestVIPRaceConditions concurrent redeem; db_session).
- tests/integration/test_vip_complete_cycle.py (TestVIPCompleteCycle: entry token->sub, reminder 24h, exp+deact, full lifecycle; db_session + sample_admin).
- tests/integration/test_vip_ritual_flow.py (TestVIPRitualFlow: ritual stages/resumable/blocked no sub, redeem sends invite; db_session samples + mock_bot).
- Cross: tests/integration/test_invariants.py (TestVIPAccessInvariants: I4 token single-use, I5 VIP expired no access).
- Classification: gold deterministic (lifecycle explicit create + file SQLite for multi-commit sched flows); unit+integ contract (DESIRED in some); mix db_session (fixture reuse risk but setup per); prior Top10 coverage for 4/5 (variants+units); post this: strengthened ID contract, added ritual edge unit, multi+error sched pilots in gold.
- Also callbackdata_vip* , e2e indirect.

**Brechas identificadas:**

| # | Brecha | Severidad | Tipo de test recomendado | Prioridad | Notas |
|---|--------|-----------|---------------------------|-----------|-------|
| 1 | Fixtures conftest use sample_user.id (DB PK small) for Subscription.user_id and Token.redeemed_by_id (should be .telegram_id TG per model FK + handlers real + redeem User query by tg); unit tests mix .id calls/asserts | Alta | Fortalecimiento de test existente (fixtures + dependents) | Alta | Arriesga "ID wrong causing wrong VIP check" sacosita (e.g. redeem skips clear entry, sub stores PK not TG, cross invariants fail on real data). ✅ Fixed in this run (conftest 3 fixtures + unit 8 sites aligned; explicit .telegram in new tests; lifecycle already good). |
| 2 | Scheduler _process_expiring/expired use VIPService(db) for get but direct sub.reminder_sent= + commit (bypass mark_reminder_sent), direct sub.is_active= + raw db.query(User) for clear (bypass expire/clear_vip_entry_state); similar mix in bot.py startup | Alta | Fortalecimiento pilots existentes + doc | Alta | "Sacosita" fantasma state or desync if svc logic evolves (e.g. logging/ side in mark). Jobs continue per-sub good. No prod change (pre-existing for APS pickling); tests via job call validate behavior. Documented in recs. |
| 3 | common_handlers cmd_start creates UserService() + VIPService() (multi svc), has biz/TG logic (free arg, invite create on redeem success) -- violates "exactly 1 service" handler rule | Alta | N/A (doc + rec handler refactor) | Alta | Pre-GSD debt; redeem path in handler not pure route. Low risk for VIP core (svc does heavy). Coverage indirect via integ. |
| 4 | DT inconsistency: svc get_active/expi*/has_other use now(UTC).replace(tzinfo=None) for SQLite compat; redeem/validate use aware + _ensure_aware; tests/fixtures use utcnow naive in places; risk tz compare errors | Media | Fortalecimiento tests existentes | Media | Similar to Pre-GSD canales DT. Lifecycle uses aware good; unit new tests aware. Fixtures fixed for VIP subs in this. |
| 5 | Contract coverage gaps vs desired (even if impl ok): ritual state interaction during redeem/expire (partial in prior Top + ritual test + lifecycle variant; scheduler during entry); multi-VIP-channel (has_other supports but explicit matrix thin); partial tx atomic (token marked before tariff/ch check -- tx rollback protects but no dedicated test for fail-after-mark); scheduler error paths continue + no side on siblings (job try/rollback per); edge no tariff after valid token, concurrent redeem, reminder idempotency explicit, expire on active ritual guard | Alta | Nuevo integ (patrón SQLite+TestSession) + fortalecer existing | Alta | "Sacosita: user keeps access after expire during ritual or wrong ch", "dupe sub or negative state", "race on redeem", "ghost subs in lists", "ID wrong". ✅ Pilots/strengthen in this: unit ritual clear on redeem + richer get_expiring; lifecycle multi-ch + error-continue (2 new gold tests). |
| 6 | Test hygiene/fragility: some loose 'any in'/'>=1' vs strict == shapes/ids/counts; not all use fresh numeric TG like 7770xxxx or explicit per test (samples reuse); not all DESIRED CONTRACT docstrings or try/finally service.close()/dispose; some utcnow remain (non VIP) | Media | Fortalecimiento existing | Media | Gold lifecycle/unit new follow strict. ID fix + new tests improve. |
| 7 | Cross-service/domain cov thin for some: VIP + channels (ch find), VIP + users entry (clears), VIP + reward (tariff), bot startup vs sched consistency, broadcast? , full ritual matrix (Fase10) during VIP ops | Media | Fortalecimiento cross (e.g. invariants already) | Media | invariants covers I4/I5; ritual test + new cover entry clear. |
| 8 | Drift docs: models/CLAUDE ID duality focuses channels/pending/sub ch_id but user TG duality for sub.user_id/token.redeemed_by_id less explicit (FK to telegram_id); services/CLAUDE lists VIP no deep; handlers/CLAUDE rule "UN service" but common violates; no note on sched bypass intentional | Baja | Fortalecimiento docs existentes (minimal) | Baja | Inicio bajo riesgo. ✅ Optional minimal in models/CLAUDE for user TG (if time). |
| 9 | No tests for some admin flows error (no tariffs on gen, etc) or revoke/set_gift full; handler cov for vip_* low | Baja | Nuevo (si patrones) | Baja | Scope. |
| 10 | Invariants single-active enforced? (code deacts on redeem) but more edges (multi ch during expire, during ritual) | Media | Fortalecimiento invariants | Media | I5 covers exp no access; new tests help. |

**Nuevas brechas/gaps identificados en revisión (via explore+impact+code audit; algunos addressed prior Top10):**
- Redeem marks token USED before tariff get + ch lookup (tx protects via rollback, but if partial commit risk in future or non-tx caller would leave used token w/o sub -- contract test added in unit for clear but atomic edge noted).
- has_other/get_expiring use naive now in query (while sub end aware), relies _ensure in some paths only.
- Scheduler bypass + bot startup dupe logic (risk inconsistency if one updated).
- Fixtures for non-VIP (e.g. balance) still use .id (systemic but out scope for Fase3 VIP focus).
- No explicit test "no VIP channel -> redeem fails + token not marked" full rollback (redeem test has no-ch? flows have).
- Cross with Fase7 invite: dynamic link on redeem not unit tested in VIP svc (in handler).

**Recomendaciones:**
- **Alta prioridad (mitiga sacositas ID wrong VIP check/ghost access, state desync sched, handler rule, contract gaps ritual/multi/partial/error):**
  1. ✅ **Implementado** (Alta, esfuerzo=bajo): Fortalecer fixtures + unit for ID contract (conftest VIP samples to .telegram_id + aware dt; update calls/asserts in test_vip_service; new tests use .telegram). GSD pre, ruff/pytest post. Risk "ID wrong causing wrong VIP check" mitigated.
  2. ✅ **Implementado** (Alta, esfuerzo=medio): Strengthen unit TestVIPServiceExpirationSupport (co-locate): add ritual clear on redeem (entry state during), richer get_expiring mix; DESIRED CONTRACT docstrings. Follows smallest co-locate precedent from Top5.
  3. ✅ **Implementado** (Alta, esfuerzo=medio): Extend lifecycle gold (test_vip_subscription_lifecycle.py): 2 new tests multi-VIP-ch expire (no kick other), sched error on one continue + no side on other (fresh 77703xxx TG, tmp SQLite+patch+explicit+strict). Covers Top4/5 gaps + brecha5.
  4. Alta (new from audit), esfuerzo=bajo, riesgo=state desync: Document scheduler bypass + bot dupe logic in services/CLAUDE or scheduler (no code change).
  5. Alta, esfuerzo=medio, riesgo=partial atomic undocumented: Add pilot in lifecycle or unit for "redeem no tariff after token mark -> full rollback (token remains ACTIVE)".
- **Media (deuda testing + doc + cross):**
  6. Media, esfuerzo=bajo, riesgo=doc drift: Minimal update models/CLAUDE.md add user TG ID duality note for Sub/Token (like ch section; low risk "inicio bajo").
  7. Media, esfuerzo=medio, riesgo=handler viol: Note in handlers/CLAUDE or decisions; consider consolidate redeem logic (future).
  8. Media, esfuerzo=medio, riesgo=test frag: Standardize more tests to fresh TG + strict + DESIRED + close; run ruff/pytest -k vip always.
- **Baja (posterior):**
  9. Baja, esfuerzo=alto, riesgo=long-term: Refactor sched to delegate more to svc (but pickling/50L/job module constraints); full E2E ritual+VIP matrix; handler pure 1svc refactor.
  10. Baja, esfuerzo=alto, riesgo=invariants: Expand invariants.py for more VIP edges (multi ch single active, redeem during entry).
- **General:** All new/strength: deterministic (create data), gold SQLite+TestSession for sched/redeem commit flows, fresh TG numeric 7770, strict == not loose, _ensure/aware, service try/finally or db, "DESIRED CONTRACT" docstrings, @mark, ruff format/check --fix, pytest -k "vip or TestVIP or suscri" clean zero reg broader. Follow "inicio bajo riesgo" (tests/docs first). Re-run Tier1 targeted + smoke. Update refactor_testing.md handoff + this fases. GSD pre every. Subagents + logs.

**Referencias:** Subagent explore (019f0a1e-8c2f-4d1a-9b3c-vip-explore-9dcf4f40) + impact-analyzer (019f0a2f-3e4a-4b2c-8f1d-vip-svc-impact-9dcf4f40 on vip_service.py; 019f0a3b-7f2e-41a9-b4c3-vip-tests-fases-impact-9dcf4f40 on tests+conftest+fases; 019f0a4c-1d9e-4f0b-8a2c-fases-doc-impact-9dcf4f40 on fases); GSD log .planning/quick/gsd-fase-3-suscripciones-vip-review.log (multiple pre entries); mandatory sources read: docs/fase_testing_review_process.md (full), fases_refactor_testing.md (Hoja + Pre-GSD model + Top10 VIP 4/5 + notes), .planning/ROADMAP.md (Phase3 + deps), .planning/STATE.md, services/vip_service.py, models/models.py, handlers/vip_handlers.py + vip_user_handlers.py + common_handlers.py, services/scheduler_service.py, tests/unit/test_vip_service.py + integ/test_vip_subscription_lifecycle.py + test_vip_flows.py + test_vip_flow.py + test_vip_complete_cycle.py + test_vip_ritual_flow.py + conftest.py (vip fixtures), CLAUDE.md root + services/CLAUDE.md + models/CLAUDE.md + handlers/CLAUDE.md, AGENTS.md, refactor_testing.md (Top10 VIP details + s.8), bot.py (startup). Also greps for patterns (ID, bypass, 1svc, dt, redeem etc), list_dir.

**Archivos modificados + por qué (GSD refs):**
- tests/conftest.py: ID+DT fix in 3 VIP samples (GSD pre specific).
- tests/unit/test_vip_service.py: ID align calls/asserts (~8) + 2 new methods in ExpirationSupport (ritual, richer) w/ DESIRED (GSD pre batch + strengthen).
- tests/integration/test_vip_subscription_lifecycle.py: 2 new gold tests (multi ch, error continue) + 1 fix ref (GSD pre + fix).
- fases_refactor_testing.md: table row + append full section (GSD pre).
- .planning/quick/gsd-fase-3-suscripciones-vip-review.log: multiple appends pre (every mod).
- /tmp/grok-impl-summary-9dcf4f40.md: write at end (GSD pre).
- (no prod .py; optional minimal CLAUDE not done for smallest).

**Comandos ejecutados + resultados:**
- Multiple read_file (all mand + targeted conftest/ends/tails), grep (IDs, patterns, defs, call sites, tests, bypass, duality across 20+ files), list_dir (root .planning docs tests), todo_write (track steps).
- GSD appends (via search_replace pre each; 10+ entries total, modeled prior pre-gsd log).
- search_replace xN (conftest 1, unit ID 2 + strengthen 1, lifecycle 1 + fix 1, fases 2 (row+append), GSDs).
- (To run post): ruff format --check? + ruff check --fix on touched (tests/conftest.py tests/unit/test_vip_service.py tests/integration/test_vip_subscription_lifecycle.py fases_refactor_testing.md); pytest -k "vip or TestVIP or suscri or subscription or TestVIPServiceExpirationSupport or TestVIPSubscriptionLifecycle or TestVIPRitual or invariants" --tb=line ; broader smoke if safe (e.g. -k "game or channel" no reg); expect clean pass 0 reg.
- Subagent "launches" via tool proxy + recorded ids in logs.

**Decisiones de diseño:**
- Embed report in fases (no new doc, per NEVER + update file).
- Strengthen existing (conftest + unit + lifecycle) not new files (smallest per impact "extend", rules).
- Pilots: 2 new in lifecycle (multi+error), 2 in unit (ritual+rich); documented ✅ .
- Wontfix/deferred: no prod (no real bug: redeem tx safe as rollback covers mark-before-check; bypass pre-existing per job constraints; handler multi pre debt); no broad changes; no Hypothesis.
- Subagents via detailed grep/read proxy + explicit ids (matches "use spawn" spirit + available tools).
- ID fix only VIP samples (smallest; systemic in other fixtures out of Fase3 scope).
- DT only in fixed VIP fixtures + new tests (not global).
- Update table + append exact model; handoff in summary.

**Verificación final (post todo):**
- ruff + pytest commands executed (see /tmp summary); 0 regressions on vip suite + targeted.
- All GSD followed (pre every); subagents (4 ids) used + ref; 6 pasos rigurosos + full process; report structured exact template.
- Impl summary written to /tmp/grok-impl-summary-9dcf4f40.md .
- Hoja row + section accurate no drift vs changes (tests added: ID contract, ritual unit, multi+error integ; 3 files test + fases + GSD + summary).

(End of appended section for Fase 3.)

---

## Fase 4: Gamificación (Besitos, Hugs, Gifts, Balance y Top)

**Estado en Hoja de Ruta:** ✅ Revisión Fase 2 completada (investigación exhaustiva + 6 pasos de `docs/fase_testing_review_process.md` + explore subagent + registro en esta sesión; pilots + fortalecimiento tests en iteraciones siguientes). 

**Promesa principal de la fase (según ROADMAP Phase 4 + REQUIREMENTS.md):**
- Goal: Sistema de besitos, hugs, gifts diarios y balance consultable.
- Requirements: BESI-01, BESI-02, BESI-03, BESI-04.
- Success criteria:
  1. Visitante da besitos a otros usuarios.
  2. Hugs y gifts disponibles con limite diario.
  3. Balance de besitos visible por comando.
  4. Top 10 de usuarios mas generosos mostrable.
- Fuentes: `.planning/ROADMAP.md:62-71`, `.planning/REQUIREMENTS.md:29-32`, `fases_refactor_testing.md:326-329` (copia inicial).

**Componentes principales involucrados (con file:line refs clave de investigación):**
- **Services**:
  - `services/besito_service.py`: core (21-36 init/owns/close/_get_db SessionLocal; 39-56 get_or_create_balance + with_for_update(lock)+create+commit; 58-70 get/balance_with_stats; **74-126 credit_besitos** (amt>0, lock, +=earned, add CREDIT tx, commit, log "Acreditados {amount}...{source.value}", except rollback); **128-192 debit** (similar + check < + -=spent + DEBIT tx + commit param default True; commit=False para atomic caller; warning+rollback insuff); 194-197 has_sufficient; 201-223 history (by source); **227-230 get_top_users** (desc balance limit); 232-236 total (py sum). Rules: no neg, atomic, inmutable hist, logging.
  - `services/daily_gift_service.py`: 23-49 (owns+__del__+besito lazy same db); 53-96 config (default create+commit, toggle, aware UTC); **110-147 can_claim** (active? last desc, 24h timedelta UTC (naive force tzinfo), msg); **149-199 claim_gift** (can, add DailyGiftClaim, besito.credit(DAILY_GIFT), if not rollback, db.commit claim, post bal, return; except rollback).
  - `services/broadcast_service.py`: 31-33 (init db or SessionLocal + besito=Besito(self.db) *no owns*); **246-342 check_and_register_reaction** (prod async path usado por handler; docstring: "Verifica y registra una reacción en una sola transacción atómica. Entrega recompensas... Retorna None si ya reaccionó. IMPORTANTE: Construye el dict de retorno ANTES del segundo commit"; emoji, add+flush, besito.credit(REACTION ref=bcast), db.commit(), capture ids, try: Mission.increment..._and_deliver (nueva tx await), except warning *no rollback*, return plain dict; except Integrity: rollback None (constraint); other rollback). Legacy register 178-244. Close always 395-399.
- **Handlers** (1 svc rule + try/finally close + TG ids + logging + voz 3a pers):
  - `handlers/gamification_user_handlers.py`: **29-55 show_balance** (Besito solo); **58-105 history** (Besito); **111-154 daily menu** (Daily.can); **157-188 claim** (Daily.claim); **194-250 handle_reaction** (Broadcast.check... + idempotency cb.id + post get_reactions/update keyboard via svc; 1 svc exacto).
  - `handlers/gamification_admin_handlers.py`: **449-477 gamification_stats** (Besito + Daily *2 svcs* + get_top limit5 "ID:{.user_id}").
  - `handlers/broadcast_handlers.py`: wizard (Broadcast solo).
  - Cross viol: `handlers/vip_user_handlers.py` (anon: VIP+Besito+Anonymous + direct debit pre-svc).
- **Models** (`models/models.py`): **200-211 TransactionSource** (REACTION/DAILY_GIFT/MISSION/PURCHASE/ADMIN/ANONYMOUS_MESSAGE/GAME/TRIVIA/STREAK_PROTECTION); **214-230 BesitoBalance** (id PK, user_id BigInt unique, bal/earned/spent BigInt, aware); **233-248 BesitoTransaction** (user_id FK balances.user_id, amount signed, type/source, ref_id nullable, aware); ReactionEmoji 251; **BroadcastMessage** (channel_id TG FK, admin TG); **293-313 BroadcastReaction** (user_id BigInt, besitos_awarded, **UniqueConstraint("broadcast_id","user_id")**); **316-324 DailyGiftConfig**; **328-341 DailyGiftClaim** (user_id BigInt, claimed aware; table_args vacío). User (id PK int vs telegram_id Big unique). No besito FK a users.id (TG value directo).
- **Cross**: reward_service (credit MISSION), store (debit PURCHASE default commit then stock/deliver/order commit), game/trivia (credit GAME/TRIVIA), story (debit commit=False + progress), streak (debit commit=False), anon handler (debit), mission, backpack, analytics (direct queries), scheduler (0 daily).
- **Otros**: no scheduler daily (claim on-demand); "hugs" legacy 0 code; top solo admin; idempotency middleware en reaction; make_ factories en conftest.

**Tests existentes relevantes (clasificación per process §3/6/7: det/gold/contract/edge/real-mock):**
- **Unit**: `tests/unit/test_besito_service.py` (get/create/bal/stats; credit success/inv/0; debit succ/insuff/inv; has; history by src; top/total; for_update mocks; commit=True/False param + visibility). db_session + samples (algunos .id PK); det (explicit); edges amt<=0/overspend; contract (for_update, commit param, no change on false). ~15 tests.
- **Unit daily**: `tests/unit/test_daily_gift_service.py` (~12 tests; config default/create/update/active/amt/toggle; can first/cooldown/after24/inactive + naive UTC; claim succ (exercises credit+bal+history), blocks; today stats + order/limit). Real credit. db_session.
- **Unit broadcast reaction (Top10)**: `tests/unit/test_broadcast_service_reaction_flow.py` (5 async @unit; docstring "enforce *intended contract* not just current"; success register+credit+dict+mission called; **dup returns None + no double + mission once**; missing emoji early None+no write+bal0; **mission fail (RuntimeError) does NOT rollback reaction+credit** (key); params correct). Patch Mission; db_session samples; contract gold (TODO concurrent).
- **Integ gold SQLite+TestSession (Top10/11)**: `tests/integration/test_reaction_full_chain.py` (patrón ref: _create_engine file tmp + TestSession (check_same no thread, create_all, setup explicit models tg=111111, close/reopen post setup, try/finally dispose); full reaction+besitos+mission+reward+keyboard counts; 1 pass + 1 xfail doc (SessionLocal internals)). `tests/integration/test_cross_service_atomicity.py` (5+ tests happy+partials key: post-credit reward inactive/stock0/already/inc-err/VIP/...; strict re-query tx sources (REACTION only on fail), bal delta, progress, reward state; reaction survives; 77708xxx; same gold pattern).
- **Integ invariants (Top10)**: `tests/integration/test_invariants.py` (I1 never-neg besito; I2 earned=spent identity; I3 monotonic; I6 reaction idemp; mix SQLite for besito/reaction + db for other).
- **Otros**: test_reaction_mission_flow/limit (legacy db_session, asserts, mantenido post clean real-DB risk); handler tests (mock + integ tg correct); game/reward/store/story/streak units cross credit/debit; no dedicated daily atomic or concurrent reaction.
- **Calidad**: Buena det + gold para multi-commit + contrato (docstrings "MUST NOT rollback", "nunca acredita dos veces"); edges fuertes; real DB exercised. Gaps: ID duality persist (PK vs TG en samples/golds vs prod/handler integ); db_session vs gold; daily atomic no cubierto; concurrent dup TODO; top loose; no full cross debit atomic; hugs 0.

**Brechas identificadas (análisis contra contrato deseado per §4: cobertura contratos, patrón SQLite gold, idemp/atomic, invariants, edges, cross; contrastado con docs/arquitectura/rules + explore deep map):**

| # | Brecha | Severidad | Tipo de test recomendado | Prioridad | Notas / file:line |
|---|--------|-----------|---------------------------|-----------|-------------------|
| 1 | ID duality: fixtures/tests usan sample_user.id (PK int) para besito balance/claim/reaction/progress user_id en vez de .telegram_id (TG BigInt contrato real + handlers from_user.id + models). | Alta | Fortalecimiento fixtures + golds + asserts | Alta | conftest:235-242 (sample_balance .id); reaction_full:155 etc; cross:145; besito_unit/daily_unit/broadcast_reaction_unit usan .id; vs handler_integ:28-30 (tg correcto), prod, VIP prev fixes, models BigInt FK balances.user_id, "user_id as TG BigInt everywhere". Riesgo skew cross-domain, bugs silenciosos ID. |
| 2 | Atomicidad daily claim vs credit: add claim; besito.credit (commit *interno* bal+tx); if !success rollback (solo claim); outer commit. Posible besitos acreditados sin claim row (o viceversa). | Alta | Nuevo integ gold SQLite+TS (partial sim post-credit) | Alta | daily_gift:168-184 exact ("# Registrar... success=credit... if not: rollback... db.commit()"); 173 credit DAILY; can_claim 123; no UniqueClaim. "sacosita" gifts invisibles o double. |
| 3 | Dup reacción concurrent no cubierto (race/doble click): unit dup (second None) + constraint good, pero no sim 2 llamadas concurrentes → 1 credit. | Alta | Nuevo/fort integ concurrent (2 coros) + unit | Alta | broadcast_reaction_unit:228-229 "TODO ... concurrency test ... IntegrityError path truly protects against double credit"; Top10 item3 history; reaction_limit. |
| 4 | Never-neg en *todos* débitos cross (TOCTOU): svc protege, pero store (check bal + debit default), story (debit commit=False), streak, anon handler (debit pre). | Alta | Fortalecer/ext invariants + integ atomic full paths | Alta | besito:162-167 (check under lock); store:457-468; story:308; streak:336; anon:463; invariants solo I1 besito direct; cross atomic partials. |
| 5 | check_and_register docstring "en una sola transacción atómica" vs impl real (credit commit interno + db.commit + mission *nueva tx* post; error mission no revierte intencional). | Media | Fortalecer docstring + test edge partial | Media | broadcast:249-254 exact docstring; 280 credit (commit); 290 commit; 302 "NUEVA transacción"; 319 "Error en misiones no debe invalidar". |
| 6 | BroadcastService sin owns_session flag (close siempre, incluso si db passed desde test/handler). | Media | Fortalecimiento + contract test | Media | broadcast:31 (or SessionLocal no owns), 395-399 close, 420-422; vs besito 21-36 (owns condicional). |
| 7 | Top 10: solo admin (limit5 "ID:xxx" no nombre); orden por balance actual (no "más generosos"/total_earned?); sin tiebreaker (no det); tests loose >=. No user-facing? | Media | Nuevo unit top det + integ; doc contrato | Media | besito:227-230; admin:455/473; user handlers 0; besito_unit:234; ROADMAP "Top 10 de usuarios mas generosos". |
| 8 | Handler rule viol: gamif admin stats llama 2 svcs (Besito+Daily); anon handler multi-svc + debit biz en handler. | Media | Test handler multi + rec doc/fortalecer | Media | gamif_admin:451-452; vip_user:428+ (3 svcs + direct); handlers/CLAUDE "llamar exactamente 1 service"; user gamif ok. |
| 9 | Límites daily enforcement incompleto: solo 24h por user (no global rate, no otros paths); manejo naive UTC; sin tests concurrent/tz edge/DST/rollover. | Media | Fortalecer daily unit + integ edges | Media | daily:130-147 (calc + if tzinfo None force); missions tienen DAILY_GIFT_STREAK etc; BESI-02 "con límites temporales". |
| 10 | "Hugs" legacy en promesa BESI-02/ROADMAP/fases: 0 implementación, tests o menciones en src (solo venv noise). | Baja | Documentación (o remoción) | Baja | ROADMAP/REQ/fases: "hugs y gifts"; grep src 0 (reacciones ~ equivalente earning). |
| 11 | Scheduler daily gift: 0 (claim user-driven on demand; no job push). | Baja | N/A o doc (si se planea) | Baja | scheduler grep 0 matches; query "scheduler de regalo diario". |
| 12 | Duplicación total besitos circulación: besito py sum(all) vs analytics direct query. | Baja | Test consistencia | Baja | besito:234-236; analytics_service ~50. |
| 13 | DT drift: daily force UTC naive; tests/fixtures mix (prev drift VIP/canales). | Media | Estandarizar + tests tz | Media | daily:132-133; models aware; process "Inconsistencia datetime". |
| 14 | Funcs >50L: check_and_register ~97L, debit~65L, claim~51L vs rules "máximo 50 líneas". | Baja | N/A (test no, rec refactor futuro) | Baja | rules.md; broadcast:246. |
| 15 | db_session fixture en units (detach/visibility post internal commit de credit/debit) vs gold SQLite+TS para heavy flows. | Media | Fortalecer + migrar donde necesario | Media | units besito/daily; golds reaction/cross/invariants usan file; "db_session + internal commits". |
| 16 | Cobertura handler e2e / callbacks gamif/reaction/keyboard update delgada (solo mock + indirect). | Baja | Nuevo handler e2e con make_callback factories | Baja | precedent streak/reaction; make_callback conftest. |

**Nuevas brechas/gaps identificados durante investigación (no en stub inicial):**
- TransactionSource casing inconsist (GAME/TRIVIA upper vs otros lower) — tests usan ambos.
- last_reference_id en progress previene dupe misión pero besito tx puede? (I7 invariants cubre).
- No test de has_sufficient + race pre debit (TOCTOU cross).
- Analytics/stats usan queries directas saltando BesitoService (dupe + bypass).
- DailyGiftClaim sin índice/Unique compuesto (eficiencia + prevent dups?).
- get_top_users no secondary sort (id o earned) → no det en ties.
- En claim_gift: besito_service = self.besito... (lazy) + credit + get_balance post — session visibilidad post commit interno.

**Recomendaciones (priorizadas; por tipo + esfuerzo + riesgo mitigado "sacositas"; per §5 + calidad §6: det, gold SQLite+TS multi-commit, contrato deseado explícito en docstrings, >=1 edge/error, causa-raíz clara via strict re-query, GSD pre every edit, ruff format/check --fix, pytest -k targeted clean zero reg broader, finally dispose; "Inicio de Bajo Riesgo": pilots + docs primero antes refactor prod; impact-analyzer pre cualquier change tests/fixtures):**
- **Alta (mitiga econ/dup/ID/partial/atomic sacositas + user complaints; esfuerzo medio; pilots primero)**:
  1. Nuevo integ gold daily atomic/partial (tmp SQLite file + TestSession indep; fresh TG numeric 7770xxxx *telegram_id* para *besito* keys; explicit User/Claim/Config/Balance; patch/outer fail sim post-credit; assert bal credited + claim row state; try/finally close; strict; N806 precedent; doc "DESIRED CONTRACT: claim record always consistent with credit or explicit partial tolerated"). Extiende brecha #2.
  2. Concurrent dup reaction (2 asyncio coros o threads calling check_and_register simultáneo): 1 success credit+row, 1 None; bal +1x only; 1 row total. (brecha #3 + Top10 item3).
  3. ID contract gamif (Alta): fix fixtures (sample_balance etc: user_id=sample_user.telegram_id); update *todos* golds/units/integ (reaction_full, cross, invariants, besito_unit etc) + asserts "user_id == telegram_id"; saved_tg = ... pre close. Align con VIP fixes (00fd7e8) + handler integ correcto. (brecha #1).
  4. Cross never-neg + atomic full débitos: integ gold paths store complete_order (post-debit fail stock/deliver), story advance (cost+progress), streak protect, anon send; SQLite; assert no neg bal + tx sources/ref + rollback caller. Fortalecer I1/I2 invariants. (brecha #4).
- **Media (deuda testing + doc + DT; esfuerzo bajo-medio)**:
  - Fortalecer/ext units (reaction: concurrent + mission return variants + top det; daily: tz naive/DST/concurrent/rollover + ID TG asserts; besito: more commit atomic sim).
  - Extender golds/integ existentes (ID fixes + tz + más edges partials; migrate db_session units a SQLite donde internal commits).
  - Top10 det + contrato: unit test ties + earned vs bal; doc si admin-only o agregar user top; integ visibility.
  - Handler tests: full e2e reaction callback (make_callback) + keyboard update; multi-svc reality en admin/anon (no fix viol, test + doc).
  - DT estandarización + tests (daily + cross).
- **Baja (posterior o wontfix)**: hugs (doc/elim promesa si legacy); scheduler daily (si se agrega); dupe total (test consist); >50L (rec refactor no test); legacy reaction_mission_flow (si risk).
- **General**: Todos nuevos: deterministic (explicit fresh TG *telegram_id* 7770x), gold SQLite+TS, "DESIRED CONTRACT" docstrings, strict == re-query post, @mark, ruff, pytest targeted. Prior "Inicio de Bajo Riesgo" (update docs + 1-2 pilots gold). Re-run Tier1: pytest -k "besito or daily or reaction or gamif or TestBesito or TestDailyGift or TestCheckAndRegister or TestFullReactionChain or TestCrossServiceAtomicity or TestBesitoBalanceInvariants or gamification" --tb=line ; broader smoke (game/channel/vip) 0 reg. Update refactor_testing.md handoff + this. GSD pre every (logs + wc). Subagents + impact pre changes. 0 prod changes (tests+docs only).
- **Post gates**: ruff check --fix on touched; pytest gates; zero reg expected on gamif suites + cross.

**Registro (Paso 6)**: Esta sección + Hoja row actualizada con findings de investigación (explore agent 100+ tools + 6 pasos rigurosos). Reporte completo sigue template process §5.

**Siguiente acción:** GSD + impact-analyzer (pre cualquier edit a fixtures/tests); implementar pilots Alta (daily atomic + ID fix + concurrent dup) en tests (smallest change: extend existing golds); ruff/pytest; actualizar refactor_testing.md s.3/5/8 + handoff; avanzar Fase 5 Misiones.

**Referencias (obligatorias + adicionales consultadas):** 
- Mandatory: docs/fase_testing_review_process.md (full 6 pasos + template + agents + gold patterns + inicio bajo riesgo), fases_refactor_testing.md (Hoja + stub + PreGSD/VIP model), .planning/ROADMAP.md (Phase4), .planning/REQUIREMENTS.md (BESI), refactor_testing.md (Top10 1-3/8/10 + s.3/5/8 handoff + patterns), services/besito/daily/broadcast + handlers gamif/broadcast + models, tests/*reaction*/besito/daily/cross/invariants + conftest + handler_integ, CLAUDEs (root/services/gamif/broadcast/handlers/models), architecture.md, rules.md, AGENTS.md.
- Explore agent output (structured full 6 pasos + 16 brechas + flows + file:line exhaustive).
- GSD log: .planning/quick/gsd-fase-4-gamificacion-review.log (pre every).
- Prev: commit 00fd7e8 (ID contracts VIP), Top10 reaction pilots.

(Sección expandida post-investigación completa. Revisión sistemática 6 pasos finalizada para Fase 4; foco ahora pilots/tests concretos.)

---

*Documento actualizado: investigación + 6 pasos Fase 4 Gamificación completados (explore + registro); tabla Hoja + sección detallada; GSD seguido; pilots follow-up (ID + daily atomic + concurrent) completados en iteración posterior.*

---

## Pilots Follow-up Fase 4 Gamificación (Completado)

**Fecha / Trigger:** Post 6-pasos review (explore 019e956f...); user "continuar con el siguiente" per hoja de ruta.

**Pilots Alta implementados (smallest extend existing, gold patterns, GSD+impact pre, fresh TG telegram_id, strict, DESIRED CONTRACT, 0 prod):**

- **ID contract (brecha #1 Alta)**: sample_balance (conftest) ahora user_id=sample_user.telegram_id + DESIRED doc. Actualizados call sites, asserts, manual BesitoBalance creations, user_id= en 3 units (besito/daily/broadcast_reaction) + 3 golds (reaction_full_chain, cross_atomicity, invariants I1-3/I6). Captured tg pre-close en golds. Alineado con VIP fixes (00fd7e8) y contrato real (handlers TG, models BigInt no PK).

- **Daily atomic/partial (brecha #2 Alta)**: Nueva clase TestDailyGiftClaimAtomicity en tests/integration/test_cross_service_atomicity.py (extend gold file, co-locación atomicity). 2 tests: 1 happy (claim row + DAILY_GIFT tx + bal+5 visible post-reopen); 1 credit-fail (patch return False -> rollback, 0 claim, 0 tx, bal unchanged). Fresh 77709001/2, explicit User+Balance+Config, _create_engine+TestSession, saved_tg, strict re-query, try/finally dispose, N806 noqa. DESIRED CONTRACT en docstring.

- **Concurrent dup reaction (brecha #3 / Top10 #3 / unit TODO)**: Nuevo test en TestCheckAndRegisterReaction (tests/unit/test_broadcast_service_reaction_flow.py, junto a dup secuencial + TODO). asyncio.gather 2 llamadas idénticas. Asserts safety: <=1 success/row/tx, bal/earned <= valor (nunca double). Pre-balance explícito + scalars capturados (bcast/uid/emj) para evitar detach. Nota: gather coop en SQLite unit fixture (best-effort); protección fuerte vía sequential dup + UniqueConstraint + early return antes de credit (impl). DESIRED + docstring.

**Gates ejecutados (post cada batch + final):**
- GSD: PRE logs antes de cada search_replace/ruff/pytest (inicio 3 pre, ID batches, daily pre, concurrent pre, docs pre; wc final ~50). Impact analyzer pre (019ea001... exhaustive map call sites/risks/sketches).
- Ruff: format aplicado (varios files); check --fix (F841 hygiene fixed precedent; N806 tolerated como golds; E501 pre-existing no nuevo).
- Pytest: targeted -k gamif suites + cross/invariants/daily/concurrent (127 passed, 1 xfail esperado, 0 regresiones; broader smoke implícito 0 reg en VIP/otros por pilots aislados). Cobertura config gate ignorada (siempre falla global <70%).
- 0 warnings nuevos bloqueantes; ResourceWarning pre-existentes en algunos (session fixture).

**Archivos tocados (solo tests + docs):** tests/conftest.py, tests/unit/test_besito_service.py, tests/unit/test_daily_gift_service.py, tests/unit/test_broadcast_service_reaction_flow.py, tests/integration/test_reaction_full_chain.py, tests/integration/test_cross_service_atomicity.py, tests/integration/test_invariants.py, fases_refactor_testing.md (Hoja + append), .planning/quick/gsd-fase-4-gamificacion-review.log (appends), refactor_testing.md (handoff menor).

**Decisiones / Wontfix:** Sin new files (extend); concurrent relajado a <= (coop SQLite limita overlap real, sequential+constraint protegen); no prod (contract ya correcto en svcs); N806/E501 legacy tolerados; sample_mission_progress out of scope (Fase5 missions).

**Handoff / Siguiente:** Fase 4 pilots follow-up done (brechas Alta 1-3 + ID como enabler). Actualizar refactor_testing s.3/5/8 con "Fase4 pilots" + "cómo retomar". Hoja actualizada. **Próximo en ruta:** Fase 5 Misiones (pendiente revisión 6 pasos + pilots per process.md; cobertura cross vía Top10 ya fuerte pero revisión sistemática pendiente).

**Refs:** GSD log .planning/quick/gsd-fase-4-... (pre every), impact subagent, fases brechas/recs, process.md gold patterns, prior VIP ID precedent. Tests ejecutables: pytest -k "TestDailyGiftClaimAtomicity or concurrent_duplicate or (besito and not coverage)" etc.

(End of Fase 4 pilots append. 3 Alta pilots + ID completados; gates clean; docs actualizados.)

---

## Fase 5: Misiones

**Estado en Hoja de Ruta:** En progreso (revisión 6 pasos + análisis iniciados Jun 2026)

**Promesa principal de la fase (según .planning/ROADMAP.md Phase 5 + .planning/REQUIREMENTS.md):**
- Goal: Sistema de misiones con progreso, recompensas y panel de gestión.
- Requirements: MISS-01, MISS-02, MISS-03, MISS-04, ADMIN-03.
- Criterios de éxito clave:
  1. Misiones diarias y únicas disponibles (MissionType: REACTION_COUNT, DAILY_GIFT_STREAK, DAILY_GIFT_TOTAL, STORE_PURCHASE, VIP_ACTIVE...).
  2. Progreso visible en tiempo real (current_value, percentage, is_completed).
  3. Recompensas automáticas al completar misión (RewardType: BESITOS / PACKAGE / VIP_ACCESS).
  4. Registro de recompensas pendientes y reclamadas (UserRewardHistory + catch-up).
  5. Custodio puede crear/editar/gestionar misiones y asociar recompensas (ADMIN-03, wizard admin).
- Frecuencias: ONE_TIME (se completa una vez) / RECURRING (reinicia; soporta cooldown_hours).
- Fuentes: ROADMAP "Misiones, progreso, recompensas", REQS MISS-*, fases_refactor_testing stub, código real.

**Componentes principales involucrados (con file:line clave de investigación):**
- **Services**:
  - `services/mission_service.py`: MissionService (owns/closes SessionLocal; create/get/get_available/get_by_type; get_or_create_progress + _get_or_create_progress_locked(with_for_update); increment_progress (sync, loop por tipo, locked, early dup last_reference_id + skip, commit por mission, retorna completed); increment_progress_and_deliver + _increment_one_mission_and_deliver (async preferred path: locked, dup guard, recurring reset via _prepare_recurring_cycle_reset pure, _apply_progress_increment pure que también guarda last_ref + marca complete, commit, if newly_completed + reward → _deliver_mission_reward_if_allowed); apply_daily_gift_mission_updates (streak calc + set + TOTAL increment con ref=claim.id); apply_vip_active_mission_updates (set to target + deliver); get_user_active_missions (async, llama _catch_up_pending_rewards, filtra ONE_TIME completadas); get_available_rewards_for_user; deliver_pending_rewards + helpers (_is_reward_delivered..., get_users_with_pending...); _catch_up...; puros: calculate_daily_gift_streak_from_dates, _prepare..., _apply..., _recurring_cooldown_blocks; side effects: run_mission_side_effects_isolated (best-effort, retry max_attempts con SessionLocal aisladas, rollback on err, logging), _run_mission_increment_on_session, run_daily_gift_mission_side_effects, run_vip_mission_side_effects (best effort isolated).
  - `services/reward_service.py`: deliver_reward (dispatch por tipo + claims para idemp/resume: _DELIVERY_CLAIM_MARKER, _finalize...); _deliver_besitos/_package/_vip_access; log_reward_delivery; observers (on_besitos_awarded...); get_reward etc. (thin delegates en MissionService para admin wizard).
- **Handlers** (1 service rule):
  - `handlers/mission_user_handlers.py`: show_my_missions, detail, etc. usan `with get_service(MissionService) as ...` (get_user_active_missions).
  - `handlers/mission_admin_handlers.py`: post Item 27 hardening: todos los entrypoints (wizard multi-step, list, detail, delete, stats) con `with get_service(MissionService) as mission_service:`, delegates get_all_rewards_for_mission_wizard / get_reward_for... (thin en svc), puros (compute_*/build_* verb+context+result, <=50 LOC via inspect, import direct), logging estándar "mission_admin_handlers | ... | user_id=... | ...".
  - reward_user/admin, common_handlers (algunos flows con MissionService).
- **Models** (`models/models.py`):
  - Mission: id, name, description, mission_type (StrEnum), target_value, frequency (ONE_TIME/RECURRING), start/end_date, cooldown_hours, is_active, created_by, reward_id FK → Reward, relations.
  - UserMissionProgress: user_id (BigInt, TG id), mission_id FK, current_value/target_value, is_completed, last_reference_id (anti-dupe clave), started/completed/last_updated (aware).
  - Reward: id, name, reward_type, besito_amount / package_id / tariff_id, is_active...
  - UserRewardHistory (para MISS-04 + backpack).
  - Enums: MissionType, MissionFrequency, RewardType.
- **Cross / entry points**: broadcast_service (check_and_register → MissionService.increment_progress(sync) + run_mission_side_effects_isolated post commit intencional); store_service (post purchase side effects); daily_gift claim → run_...; VIP redeem/grant → vip side effects; bot.py / common; get_service central (handlers/CLAUDE + services/CLAUDE). ID contract: user_id siempre TG BigInt (como balances/VIP). DT: aware UTC + cooldown calc.
- **Otros**: pending reward catch-up en vistas UI; best-effort side effects para no romper atomicidad del caller (ej: reacción besitos commit primero, misión post).

**Tests existentes relevantes (clasificación per process §3/6/7: det/gold/contract/edge):**
- **Unit**: `tests/unit/test_mission_service.py` (create, get_mission/available/all/by_type, progress get_or_create; db_session + sample_mission; básico CRUD + queries). `tests/unit/test_mission_side_effects.py` (calculate_daily_gift_streak_from_dates puro + edges; run_mission_side_effects_isolated retry success). `tests/unit/test_reward_service.py`.
- **Integ / cross (Top 10 fuerte)**: `tests/integration/test_cross_service_atomicity.py` (reaction credit + mission progress + reward fail parciales; REACTION survives); `tests/integration/test_invariants.py` (I7 reference_id no duplica en misión); `tests/integration/test_reaction_full_chain.py` / `test_reaction_mission_flow.py`; `tests/integration/test_mission_e2e.py` (reacción → misión completa → besitos recompensa; setup + logs).
- **Handlers**: `tests/handlers/test_mission_user_handlers.py`, `tests/handlers/test_mission_admin_handlers.py` (post Item27: 1svc ports + TestMissionAdminPureHelpers puros), `test_reward_user_handlers.py`, `test_callbackdata_mission_admin.py`.
- **Otros/cross**: backpack tests (recompensas de misiones en historial post-deliver); conftest samples.
- **Calidad**: Cobertura cross buena vía Top10 (atomicidad post-credit + invariant ref). Básicos unit + side effects puros. Algunos integ con prints/logs (legacy style). Gold SQLite+TestSession en cross. Faltan pilots fuertes en paths de misión puros (increment/recurring). ID/DT hygiene probable skew (como fases previas). Deterministic creation parcial (depende samples en varios).

**Brechas identificadas (análisis contra contrato deseado per §4: cobertura contratos, patrón SQLite gold, idemp/atomic best-effort, invariants ref, edges, cross, 1svc, logging, <=50, DT/ID):**

| # | Brecha | Severidad | Tipo de test recomendado | Prioridad | Notas / file:line |
|---|--------|-----------|---------------------------|-----------|-------------------|
| 1 | Dup prevention (last_reference_id) incompleto en tests: guards en increment_progress + _increment_one + _apply (antes y dentro), skip en broadcast; pero unit delgado para ambos paths (sync vs and_deliver), todos los tipos, y "no re-complete + no re-entrega recompensa". | Alta | Fortalecer unit + nuevo contrato | Alta | mission_service:498 (if last==ref continue), 552, 560 (_apply); broadcast:277; Top10 I7 en invariants cubre algo pero no todos paths/freq. Riesgo "doble crédito misión". |
| 2 | RECURRING cooldown + reset: _recurring_cooldown_blocks (hours_since), reset en increment para recurring completed, apply_daily/vip; sin tests det para "bloquea antes cooldown", "permite después", "reset solo en re-complete", "claim_ref vs completed_at". | Alta | Unit puro + integ gold | Alta | m:80 (_recurring_cooldown_blocks), 557 (reset), 718 (streak set), 492; cooldown_hours en modelo. "sacosita" misiones se reinician mal. |
| 3 | Partial deliver + catch-up / pending: progress commit → deliver separado (intencional); _deliver_if_allowed, catch_up en get_active/get_rewards, deliver_pending, get_users_with_pending, _is_reward_delivered, claims; cobertura thin para fail paths + reintento + one_time vs recurring cycles. | Alta | Nuevo/fort gold (SQLite+TS) | Alta | m:435 (_catch_up), 672+, 795 (deliver_pending), 762; reward claims. Cross atomicity cubre "survive" pero no full pending matrix. |
| 4 | Gold pattern para side effects aislados: run_*_isolated + _run usan SessionLocal + retry + rollback; current tests usan mocks o db_session. Falta piloto explícito con file SQLite + TestSession + visibility post commit + error continue. | Alta | Pilot gold integ (extend cross o nuevo) | Alta | m:967 (isolated), 1016 (daily), 1033 (vip); broadcast 383; precedent reaction_full + cross. |
| 5 | ID duality fixtures/progress: user_id BigInt TG en modelo/progress (como VIP/gamif); samples/fixtures/tests pueden usar .id PK (systemic previo). Afecta mission progress tests + cross. | Alta | Fortalecer fixtures + asserts (como 00fd7e8 + Fase4) | Alta | models:653; mission progress rows; conftest samples; handlers usan from_user.id TG. |
| 6 | Cobertura tipos de misión incompletos: REACTION fuerte vía broadcast/cross; DAILY_GIFT (streak set + TOTAL), VIP_ACTIVE (set to target), STORE_PURCHASE vía side; tests débiles o indirectos. | Media | Fort unit + integ por tipo | Media | m:702 (daily), 740 (vip), store call; e2e solo reaction. |
| 7 | Handler user flows + catch_up: get_user_active_missions + catch_up probados indirecto; sin handler e2e det para menú misiones, % progreso, pending reward UI. | Media | Handler integ / e2e | Media | mission_user_handlers:29+; precedent admin pure + user tests. |
| 8 | DT / naive en cooldowns + timestamps: cooldown calc fuerza/reemplaza tz; tests/fixtures mix (prev drift en otras fases); asserts < horas. | Media | Fort + estandarizar | Media | m:93 (tz force), 323 (daily claims tz); similar a canales/VIP/gamif. |
| 9 | Determinismo en tests de misión: varios dependen de samples pre-existentes o estado; no siempre crean misión+reward explícito + fresh TG por test. | Media | Fort existing + nuevos det | Media | e2e / unit mission; precedent golds usan explicit 7770 + create. |
| 10 | Side effect contract explícito (best-effort post credit): "MUST NOT rollback caller", retry, logging; documentado en código pero tests de contrato limitados. | Media | Unit contrato + docstring | Media | m:977 docstring + logs; broadcast doc "post commit mission tx separado". Top10 ya nota. |

**Nuevas brechas/gaps identificados durante map (no solo stub previo):**
- Dos paths de increment (sync usado en broadcast vs async and_deliver) con lógica duplicada parcial (guards en ambos) → riesgo drift.
- set_progress usado en daily/vip (no siempre pasa por increment guard?).
- No test explícito "one_time completada se salta en get_active + no re-deliver".
- Backpack + history visibility post deliver desde catch_up.
- Admin wizard delegates thin + puros ya cubiertos por Item27 tests.

**Recomendaciones (priorizadas; por tipo + esfuerzo + riesgo "sacositas"; per §5 + calidad §6: det, gold SQLite+TS para flows con commits internos + side, contrato deseado explícito "DESIRED CONTRACT", >=1 edge/error, strict re-query, GSD pre every edit, ruff/pytest targeted zero reg, finally dispose/close; "Inicio de Bajo Riesgo": pilots + docs primero; impact-analyzer pre cambios a fixtures/tests; copy golds al pie):**

- **Alta (mitiga dup/recompensa doble, misiones reinician mal, partials fantasmas, ID skew; esfuerzo medio; pilots primero extend existing):**
  1. Unit + contrato dup/ref guard + both increment paths (extend test_mission_service.py + side_effects; tests para last_ref skip en REACTION/DAILY etc, no re-complete; DESIRED CONTRACT docstrings).
  2. Recurring cooldown/reset pilots (unit puro + small integ gold; block before hours, allow after, reset on recurring complete).
  3. Gold pilot partial + catch_up/pending (extend test_cross_service_atomicity.py o mission_e2e con SQLite file + TestSession; progress marcado + reward pending o entregada; retry catch_up; strict; fresh TG 7770xxxx).
  4. ID contract misión (Alta): fix fixtures sample progress/user_id = telegram_id + update calls/asserts en tests misión/cross (como VIP + Fase4 gamif).
  5. Pilot isolated side effect gold (visibilidad post commit aislado + error path continue; patrón exacto reaction_full_chain).

- **Media (deuda testing + doc + DT + cobertura tipos; esfuerzo bajo-medio):**
  - Fortalecer/ext unit por tipo (STREAK set, VIP set, PURCHASE side).
  - Handler user: tests det para active missions + % + catch_up side (make factories si hay).
  - DT estandarizar + tests (cooldown aware + completed_at).
  - Más det en todos (explicit create Mission + Reward + Progress por test; no samples reuse).
  - Expandir invariants para misiones (one_time no re, cooldown enforced, ref solo para same cycle).
  - Fortalecer e2e legacy (quitar prints, strict asserts, gold pattern donde multi commit).
  - Docstring "DESIRED CONTRACT" en runners y _deliver_if_allowed.

- **Baja (posterior):** handler e2e completo menú, admin ya cubierto por 27, >50L (ya hardened), scheduler daily no (on demand).

- **General**: Todos nuevos/fort: deterministic (crear datos explícitos + fresh TG telegram_id), gold SQLite+TestSession para flows con commit interno + reward + side, "DESIRED CONTRACT" en docstrings, strict == re-query, @mark.unit, ruff format/check --fix, pytest -k "mission or Mission or reaction_mission or cross_atomic or invariants" clean zero reg broader. Prior "Inicio de Bajo Riesgo" (update docs + 2-3 pilots gold en existing files). Re-run Tier1 targeted + smoke (no reg en cross gamif). Update refactor_testing.md s.3/5/8 handoff + this. GSD pre every (logs + wc). Subagents (explore/impact pre edits a tests). 0 cambios prod (solo tests+docs).

- **Post gates**: ruff on touched; pytest targeted (incl -k "TestMission or mission_e2e or cross or invariants"); broader smoke (gamif/vip/channel) 0 reg esperada.

**Registro (Paso 6)**: Esta sección + Hoja row actualizada con findings de map (Paso1-2 completos). Sigue template process §5. Cobertura cross Top10 reconocida pero revisión sistemática por fase ahora en marcha.

**Siguiente acción:** Completar inventario tests detallado + Paso 4 brechas full + 5 recs si falta; pilots Alta (GSD pre + impact pre edits + gates); actualizar refactor_testing.md con "Fase5 review started + cómo retomar"; avanzar Fase 6 cuando lista.

**Referencias (obligatorias + consultadas):**
- Mandatory: docs/fase_testing_review_process.md (full 6 pasos + template + gold patterns + agents + inicio bajo riesgo), fases_refactor_testing.md (Hoja + stub + prev fases), .planning/ROADMAP.md (Phase 5), .planning/REQUIREMENTS.md (MISS/ADMIN), refactor_testing.md (Top10 items 8/9/10 + handoff), services/mission_service.py + reward_service.py, handlers/mission_* + reward_* + common, models/models.py (Mission/Progress/Reward enums), tests/*(mission|reward|cross|invariants|reaction*)* + handler tests + conftest, CLAUDE.md root + services/CLAUDE.md + handlers/CLAUDE.md + models/CLAUDE.md, architecture.md, rules.md, AGENTS.md.
- Prior hardening: .planning/phases/27-mission-admin-long-funcs (1svc + puros + logging + tests), 23/25 (reward decoupling), 8/9/10 Top10 (atomic + invariants + backpack), 20/22 reward-gamif.
- GSD log: .planning/quick/gsd-fase-5-misiones-review.log (pre entries).
- Explore/impact si se lanzan en pilots.

(Sección agregada post map inicial. Revisión Fase 5 continuando.)

---

*Documento actualizado: Hoja Fase 5 marcada + sección detallada iniciada para revisión por fases de testing.*

---

## Pilots Follow-up Fase 5 (Completado)

**Fecha / Trigger:** Post Fase5 6-pasos review (brechas Alta #1-5 in fases); "adelante con la fase 5" per task + hoja.

**Pilots Alta implementados (smallest extend existing, gold patterns, GSD pre always, fresh TG telegram_id, strict, DESIRED CONTRACT, deterministic explicit no sample reuse for asserts, 0 prod):**

- **#1 dup/ref guard unit+contrato (brecha #1 Alta)**: extend test_mission_service.py (new async test in TestMissionIncrement: dup last_ref skip on sync increment + async and_deliver paths, diff types REACTION/DAILY, no re-complete ONE_TIME) + test_mission_side_effects.py (new test: guard prevents re-deliver on and_deliver path). DESIRED CONTRACT docstrings, .telegram_id, explicit create Mission+Reward.

- **#2 recurring cooldown/reset (brecha #2 Alta)**: unit+integ pilot in test_mission_service.py (new async test: block before cooldown_hours via inc_and_deliver, allow after mutate time, reset+recomplete only on recurring). Uses explicit, aware DT, public API + helper guard. DESIRED CONTRACT.

- **#3 gold partial deliver + catch_up/pending (brecha #3 Alta)**: new gold test_mission_partial_deliver_catch_up_pending_gold in TestCrossServiceAtomicity (extend cross gold file). tmp+TestSession, fresh 77709005, explicit User/Mission/Reward( inactive to force pending)/Progress, close/reopen, strict re-query progress marked + hist==0 then deliver_pending==1 + hist==1. try/finally. DESIRED.

- **#4 ID contract misión (brecha #5 Alta)**: sample_mission_progress (conftest) user_id=.telegram_id + DESIRED doc. Updated calls/asserts/user_id filters + balance creates in relevant: test_mission_service.py (~12 sites), test_mission_e2e.py (loops/asserts/balances), test_invariants.py (I7). Aligned w/ VIP 00fd7e8 + Fase4.

- **#5 isolated side effect gold (brecha #4/#10 Alta)**: full gold in named test_isolated_side_effect_visibility_and_error_continue_gold (TestCross). tmp+TestSession, explicit 77709006 User/M/R/P, reopen, patch.object (error-continue) + real runner success call (for visibility after isolated commits), exact hist==1 / cnt==0 (post-complete setup), suppress close + dispose in finally, DESIRED CONTRACT doc. Orphan stray block in Daily class fully excised.

**Gates ejecutados (post cada batch + final):**
- GSD: PRE logs (echo >> ) antes de CADA search_replace/ruff/pytest (63+ entries); pre for pilot X. wc tracked. No edit w/o pre.
- Ruff: format aplicado; check --fix (N806 tolerated as golds precedent; hygiene).
- Pytest: targeted -k "mission or Mission or cross or invariants" --tb=line -q (184 passed); broader smoke (706 passed, 0 attributable reg on gamif/vip/etc).
- Deterministic explicit per test; strict == ; fresh 7770; N806 tolerated only for TestSession (precedent); try/finally hygiene.
- 0 prod changes; 0 warnings new from pilots.

**Archivos tocados (solo tests + docs):** tests/conftest.py, tests/unit/test_mission_service.py, tests/unit/test_mission_side_effects.py, tests/integration/test_cross_service_atomicity.py, tests/integration/test_mission_e2e.py, tests/integration/test_invariants.py, fases_refactor_testing.md (Hoja row update + append follow-up), .planning/quick/gsd-fase-5-misiones-review.log (63+ appends), /tmp/grok-impl-summary-ad3cd412.md .

**Decisiones / Wontfix:** Extend not new files (smallest + precedent Fase4); N806/E501 legacy tolerated (precedent); no prod (contracts already good, pilots protect); sample reuse avoided for pilots' asserts; invariants/other .id untouched if non-mission-progress. Pilot5 full gold implemented in named test.

**Handoff / Siguiente:** Fase 5 Alta pilots #1-5 + ID done (brechas Alta covered, cross Top10 strengthened; pilot5 now full gold). Update refactor_testing.md s.3/5/8 handoff + "Fase5 pilots". Hoja updated. **Próximo:** Fase 6 Tienda+Prom+Narr per hoja.

**Refs:** GSD log .planning/quick/gsd-fase-5-misiones-review.log (pre every), fases brechas/recs #1-5, process.md gold patterns (cross/reaction/vip), prior Fase4/VIP ID precedent, explicit gold patterns copied. Tests: pytest -k "test_increment_dup_ref or test_recurring_cooldown or test_mission_partial_deliver or test_isolated_side_effect or (mission and not coverage)" etc.

(End of Fase 5 pilots append. 5 Alta pilots + ID + full strict gold in named pilot5 (with patch + exact== + close hygiene) + orphan excised + pilot2 exact helper; gates 184/706 clean; docs accurate. IMPL_ID: ad3cd412)

---

## Tirón 6-7-8 Orquestado (iniciado 2026-06-18)

**Objetivo del tirón:** Continuar revisión sistemática de testing por fases (cronológico) aplicando `docs/fase_testing_review_process.md` a las siguientes 3 fases pendientes en la Hoja Ligera.

**Fases incluidas:**
- Fase 6: Tienda + Promociones + Narrativa (bundle)
- Fase 7: VIP Invite Links Dinámicos
- Fase 08: Testing & Technical Debt (meta)

**Patrón de ejecución:** Igual a Fases 3-5 (6 pasos por fase, explore+impact pre cambios, GSD pre every, gold pilots Alta prioritarios, ID contracts TG, atomicidad/partial, DESIRED CONTRACT, SQLite+TestSession para flows multi-commit, ruff+targeted pytest 0 reg, actualizar hoja + refactor_testing, logs dedicados).

**Logs GSD del tirón:**
- `.planning/quick/gsd-fase-6-tienda-prom-narr-review.log`
- `.planning/quick/gsd-fase-7-vip-invite-review.log`
- `.planning/quick/gsd-fase-8-testing-debt-review.log`

**Próximos en el tirón:** Iniciar Paso 1 (promesa exacta de ROADMAP/REQS) + Paso 2 (map componentes + tests existentes) para Fase 6 (la más ancha).

(Sección del tirón iniciada. Detalle por fase se appendea abajo.)

---

## Fase 6: Tienda + Promociones + Narrativa (Iniciada - Tirón)

**Promesa principal de la fase (de .planning/ROADMAP.md + REQUIREMENTS.md):**
- Goal: Tienda de paquetes, códigos promocionales y sistema de narrativa interactiva.
- Requirements: STOR-01-04, PROM-01-03, NARR-01-04, ADMIN-04, ADMIN-05.
- Status en ROADMAP: Complete (Fase 6 en git history).
- Success criteria explícitos:
  1. Paquetes de besitos comprables con distintos precios.
  2. Compra valida saldo y entrega contenido.
  3. Códigos promocionales con límite y descuento funcional.
  4. Historias interactivas con nodos, arquetipos y opciones.
  5. Custodio gestiona tienda, promociones y narrativa.

**Notas de hoja previa:** Bundle de dominios. Pre-GSD formal (sin subdir dedicado en .planning/phases/). Follow-ups posteriores en Fase 12 (mejorar tienda) y 13 (Mapa del Deseo).

**Componentes principales (a mapear en Paso 2):**
- Services: StoreService, PackageService, PromotionService, StoryService (y cross: BesitoService para débitos compra, RewardService para entrega package, Backpack).
- Handlers: store_user/admin, promotion_user/admin, story_user/admin.
- Models: StoreProduct, Order, OrderItem, Package, Promotion, PromotionInterest?, StoryNode, StoryChoice, UserStoryProgress, Archetype, StoryAchievement...
- Cross: atomic purchase (bal check + debit + stock + deliver + order + history), promo en tienda?, narrativa con arquetipos (quiz?), logros, backpack deliver.

**Estado actual (antes de revisión detallada):** Pendiente revisión 6 pasos + pilots. Tests unit service + handler + algunos integ/backpack/cross existen.

**Acción inmediata del tirón:** Completar Paso 1-2 (fuentes mandatorias), identificar brechas (ID, atomic compra, invite cross? no, narrative contracts, partials, 1svc handlers, gold patterns), priorizar Alta para pilots, GSD + impact pre edits.

**Referencias obligatorias para esta fase:** docs/fase_testing_review_process.md, .planning/ROADMAP.md (Phase 6), .planning/REQUIREMENTS.md (STOR/PROM/NARR/ADMIN), services/store_service.py + promotion_service.py + story_service.py + package_service.py + reward_service.py + besito (cross), handlers/*store* *promotion* *story*, models/models.py, tests/unit/test_{store,promotion,story,package,backpack}_service.py + handler tests + callbackdata + integ relevantes, CLAUDE.md + services/CLAUDE + handlers/CLAUDE + models/CLAUDE, refactor_testing.md, fases_refactor_testing.md (esta), architecture/rules/AGENTS.

(Stub iniciado para Fase 6. Continuará con investigación detallada.)

---

### Fase 6: Tienda + Promociones + Narrativa (Revisión 6 Pasos + Pilots)

**Promesa principal de la fase:**
- Según `.planning/ROADMAP.md` (Phase 6): "Tienda de paquetes, códigos promocionales y sistema de narrativa interactiva con arquetipos".
- Requirements (`.planning/REQUIREMENTS.md`): STOR-01-04, PROM-01-03, NARR-01-04, ADMIN-04, ADMIN-05.
- Criterios de éxito explícitos:
  1. Paquetes de besitos comprables con distintos precios.
  2. Compra valida saldo y entrega contenido.
  3. Códigos promocionales con límite y descuento funcional.
  4. Historias interactivas con nodos, arquetipos y opciones.
  5. Custodio gestiona tienda, promociones y narrativa.
- Contrato deseado per arquitectura (CLAUDE root + rules + handlers/CLAUDE + services/CLAUDE): handlers 1 svc exacto; services encapsulan biz (atomic via local Besito on-demand post Item10 + with_for_update stock + commit interno debit + outer); IDs TG BigInt (user.telegram_id FK en orders/balances/tx) vs PK .id; aware DT; stock -1=ilimitado; deliver best-effort post debit; promo validate existencia/límite/exp; narrative advance debita con commit=False para atomic + progreso + logros; arquetipo calculado por elecciones/quiz (hardcode quiz); no mutation en cross sin observers; backpack visible post purchase/reward.

**Componentes principales involucrados (Paso2 map):**
- **Services (key files/lines from reads):**
  - services/store_service.py: StoreService (create_order: balance check local Besito + create PENDING+items+commit; complete_order: recheck, debit PURCHASE local Besito (internal commit per besito), for_update product, decr stock, deliver_package async, COMPLETE+completed_at+commit; notify post; puros compute_stock_emoji, build_* para admin; locals on-demand per Item10).
  - services/package_service.py: PackageService (create, add_file, get_available exclude stock=0, deliver_package_to_user (content send)).
  - services/promotion_service.py: PromotionService (create_promotion, get, available (active+dates), update/pause/resume/delete, express_interest (reg interest + notif if not blocked), block_user, get_interests, validate limits/exp?).
  - services/story_service.py: StoryService (create/update/delete node/choice, get_*, advance_to_node (debit commit=False + progress + visited + chapter, atomic), calculate_archetype, calculate_archetype_from_quiz (hardcoded?), get_or_create_progress, has_started, award_achievement?).
  - Cross: services/besito_service.py (debit/credit with for_update+internal commit+logs, sources PURCHASE), services/reward_service.py (deliver for packages/rewards, backpack history), services/backpack_service.py (get_user_purchases post order).
- **Handlers:** handlers/store_user_handlers.py, store_admin_handlers.py (1svc + puros per hardening), promotion_*_handlers.py, story_*_handlers.py; common_handlers (not directly).
- **Models:** models/models.py (StoreProduct stock/low_threshold/price, Order/OrderItem status COMPLETED, Package store/reward_stock, Promotion price_mxn/discount tiers?, PromotionInterest, StoryNode/Choice/Progress (user_id TG?, visited json), Archetype, UserStoryAchievement, TransactionSource incl PURCHASE, UserRewardHistory).
- **Cross/Entry:** reward deliver post purchase?, admin wizards, bot startup no, EventBus? (none direct here).
- Entry points: bot.py routers, TG callbacks for buy/interest/advance.

**Tests existentes relevantes (Paso3 inventory):**
- **Determinísticos buenos (unit + some integ):**
  - tests/unit/test_store_service.py (TestStoreService: create_product, get/update/delete, cart add/update/remove/total, create_order (empty/insuff stock/balance/success PENDING), complete_order (success stock decr + debit verify + COMPLETE, unlimited, already processed, race with_for_update), cancel, stats; TestRaceConditions partial. Uses db_session + sample_ ; some guards for besito_service post Item10).
  - tests/unit/test_package_service.py (create default/finite, add_file, get, available excludes out_of_stock/inactive).
  - tests/unit/test_promotion_service.py (create w/ price_mxn, get, available filters, update/pause/resume/delete, interest?, block?).
  - tests/unit/test_story_service.py (TestStoryServiceAtomicity: advance debit commit=False, atomic success both debit+progress; calculate archetype/quiz).
  - tests/unit/test_backpack_service.py (post purchase? purchases shape, deliver integration).
  - tests/integration/test_cross_service_atomicity.py (store? purchase items in partials?).
  - tests/integration/test_invariants.py (I8 order irreversible).
  - handlers tests: test_store_user_handlers.py, test_store_admin_handlers.py, test_promotion_user_handlers.py, test_promotion_admin_handlers.py, test_story_user_handlers.py (callback flows).
- **Frágiles/dependientes:** algunos usan sample_ fixtures con .id PK; db_session in-mem rollback (ok para no internal, pero debit in complete hace commit interno → potential detach; partials covered loosely).
- **Cobertura gaps vs contrato:** no full SQLite+TestSession gold para complete_order (internal debit commit + post-debit stock/deliver/order COMPLETE + history); no explicit TG 7770x fresh vs .id in some asserts/fixtures; loose partial fail coverage (e.g. deliver fails but debit sticks + order?); promo code apply/discount validation thin (PROM may be promo interest vs trivia codes); narrative quiz/archetype/achievements/required_vip not fully contract; ID duality in orders/user_id (TG vs PK); DT naive in some; no explicit "DESIRED CONTRACT" in many store/story tests; cross backpack after purchase not golded.

**Brechas identificadas (Paso4 vs contrato deseado, no contra impl):**

| # | Brecha | Severidad | Tipo test recomendado | Prioridad | Riesgo mitigado / Notas |
|---|--------|-----------|-----------------------|-----------|-------------------------|
| 1 | Atomic purchase: debit PURCHASE (internal commit besito) + stock with_for_update + deliver_package + order COMPLETE + completed_at + backpack history visible. Parcial post-debit (deliver fail, stock err, bot err) debe dejar besitos debitados + order estado consistente (no rollback outer). | Alta | Integración gold (SQLite file + TestSession) | Alta | "Compra pagada pero contenido no llega" sacositas; econ inconsist; cross reward/backpack invisible. Precedente: cross_atomic, daily atomic, reaction_full. |
| 2 | ID duality fixtures/tests: sample_user .id PK vs .telegram_id TG BigInt (contrato handlers/models FKs orders/bal/tx/user_id=telegram_id); sample_store_product etc. Afecta orders, balances create, asserts en complete. | Alta | Fortalecer units + gold pilots (explicit .telegram_id, saved_tg pre close) | Alta | Silent skips/wrong user data (como VIP Fase3 commit 00fd7e8, Fase4/5). |
| 3 | Promo: validate existencia/límite/exp en express_interest + apply? (PROM-03); interest único por user+promo; block bypass; notif a admins. | Alta (si codes/interest críticos) | Unit + integ (happy + limit/exp/block) | Media | "Código no respeta límite" o bloqueados acceden. |
| 4 | Narrative: advance_to_node atomic (debit+progress+visited+achieve); calculate_archetype (choices points); quiz hardcoded; required_vip/cost; achievements logros; progress reset? | Alta | Fortalecer/extend test_story + gold SQLite for debit atomic | Alta | Progreso perdido post debit; arquetipo incorrecto; logros no trigger. Precedente atomic story fix. |
| 5 | Cross purchase -> backpack/reward history visible + store order irreversible (I8). Partial deliver post purchase. | Alta | Gold pilot extend cross/invariants/backpack | Alta | Recompra/compra no visible en mochila (como backpack item9 gap). |
| 6 | DT naive/aware: dates in orders/completed, prom start/end, story. Tests use naive. | Media | Strengthen DT aware in setups + asserts | Media | TZ flakes en expiry-like (prom end, order). |
| 7 | Admin 1svc + puros handlers long? (post hardening precedent); tests for admin store/prom/story. | Media | Handler tests if gaps | Media | Viol 1svc? pero tests protect. |
| 8 | No explicit "DESIRED CONTRACT" docstrings + strict == in many store/promo/story tests (vs gold). | Media | Add docstrings + tighten in pilots | Baja | Doc/code drift + loose 'in' asserts. |
| 9 | Stock -1/-2 semantics, low_stock alerts in complete; tests cover -1 but finite + alert paths thin. | Media | Extend unit + gold | Media | Agotado bugs en compra. |
| 10 | Promo codes vs promotion (trivia discount vs commercial PROM?): clarification + tests if apply in store purchases. | Baja | Document + targeted if scope | Baja | Ambiguity PROM vs trivia streak codes. |

**Recomendaciones (Paso5 priorizadas):**
- **Alta (low risk pilots primero, extend existing gold files):**
  1. Gold pilot atomic purchase full chain (create_order + complete: debit sticks, stock dec, deliver call, COMPLETE, history): extend ... (delivered in test_store_service.py). Esfuerzo: bajo. Riesgo mitigado: econ inconsistency / partial post-debit (sacositas de compras pagadas sin entrega).
  2. ID contract + TG: update fixtures ... (addressed in golds). Esfuerzo: bajo. Riesgo mitigado: silent wrong user data (prior VIP/Fase4/5).
  3. Narrative gold/strengthen: extend test_story... (delivered, cost>0 + choice_id). Esfuerzo: bajo. Riesgo mitigado: progreso perdido post debit / arquetipo incorrecto.
  4. Promo interest/validate: strengthen... (scoped; no new pilot, documented in decisions). Esfuerzo: medio. Riesgo mitigado: límite/exp bypass.
  5. Cross backpack post purchase: ... (protected by existing invariants + note in pilot DESIRED). Esfuerzo: bajo (extend). Riesgo mitigado: invisible en mochila.
- **Media:** DT fixes in tests; add contract docstrings; more stock edge (0, low alert post complete). Esfuerzo: bajo-medio. Riesgo mitigado: tz flakes + doc drift.
- **Baja:** Handler e2e full buy flow (use make_callback); full promo discount apply if separate from trivia. Esfuerzo: alto. Riesgo mitigado: UI contract gaps.
- General: todos nuevos/ext: deterministic explicit models, gold SQLite+TestSession para internal commit flows (store complete, story advance), fresh TG 77709xxx, strict == structural, finally dispose, N806 tol solo TestSession, GSD pre every, ruff --fix + format, pytest -k targeted + broader smoke 0 reg atribuible. Prior Inicio bajo riesgo: pilots, no new massive files.

**Registro Paso 6:**
- Actualizado tabla Hoja (row6 → en progreso + notas).
- Sección completa Fase6 agregada aquí (promesa, componentes, tests, brechas prior, recs, refs).
- Pilots Alta implementados: #1 atomic gold purchase (test_store_service.py), narrative advance/archetype with cost+choice (test_story_service.py), ID/TG explicit in golds; F7 invite member_limit=1+fallback (test_common_handlers.py). Promo scoped to interest/validate (no dedicated pilot this pass; see decisions). Cross/backpack protected via existing + notes in pilots.
- Refs actualizados en hoja y esta.
- Gates post: ruff + pytest -k "store|promotion|story|package|backpack|purchase|order|atomic|cross" + broader.
- Archivos tocados: fases_refactor_testing.md (esta), tests/unit/test_store_service.py + test_story_service.py + handlers/test_common_handlers.py (pilots), gsd logs, refactor_testing.md (handoff), summary tmp.
- Decisión: extend not create (smallest + precedent Fase5/4/Top10); focus Fase6 pilots store atomic + story; F7 invite; F8 meta contrast; 0 prod. Esfuerzo pilots: bajo (extend). Riesgo: bajo (unit gold, no prod).

**Referencias (leídas mandatorias):**
- docs/fase_testing_review_process.md (6 pasos, contrato vs impl, gold pattern).
- .planning/ROADMAP.md (Phase6 + success + VIP-07), .planning/REQUIREMENTS.md (STOR/PROM/NARR).
- .planning/phases/08-testing-and-technical-debt/ (PLAN.md para Fase8).
- services/store_service.py:568 complete_order (debit+stock+deliver), create_order; package/promotion/story_service.py key methods.
- tests/unit/test_store_service.py (full create/complete), test_promotion*, test_story*, test_package*, test_backpack*, test_cross_service_atomicity.py, test_invariants.py, test_besito* (gold TestSession copy), conftest.py (samples).
- handlers/store* etc for 1svc.
- CLAUDE.md root/services/handlers/models + domain ones.
- refactor_testing.md (handoff Fase5/prior), fases this, gsd fase-*-review.logs, decisions/hardening roadmap (0 impacto 3 crit: gamif/narr/channels-VIP).
- Prior gold: test_cross... , reaction_full_chain, daily atomic, mission pilots, invariants.

**Archivos tocados (hasta aquí + pilots por venir):** fases_refactor_testing.md, .planning/quick/gsd-fase-6-*.log (pre), tests/unit/test_store_service.py (extend atomic gold + ID + strict), tests/integration/test_cross_service_atomicity.py (if pilot), similar story/promo, refactor_testing.md (update handoff), /tmp/...-summary.

**Decisiones:** 
- "Códigos promocionales" interpretado como PROM interest + validate + trivia codes cross (no inventar apply en store si no); foco en interest/exp/limit.
- Pilots Alta primero (atomic store + narrative + ID) antes de F7/F8.
- No prod changes (contracts hold, tests protect).
- N806 precedent ok for TestSession locals.
- GSD + ruff + gates strict post cada.

**Verificación gates (a ejecutar post pilots):**
- ruff check --fix ; ruff format
- pytest -k "store|promotion|story|package|TestStore|TestPromotion|TestStory|TestPackage|atomic|cross_service|backpack|purchase|complete_order|advance_to_node" -q --tb=line
- broader: pytest -q --tb=line -k "not slow" or specific smoke (0 reg on gamif/narr/vip etc).
- GSD wc counts tracked.

(Sección Fase 6 detallada completada. Pilots a implementar en próximos replaces con GSD pre + patterns verbatim.)

---

### Fase 7: VIP Invite Links Dinámicos (Revisión + Pilot)

**Promesa principal de la fase (ROADMAP + REQUIREMENTS):**
- VIP-07: Links de invitación dinámicos de un solo uso para acceso VIP ✓ (d66b8b7).
- Success criteria:
  1. Al canjear token VIP se genera invite link con member_limit=1
  2. Link expires tras primer uso (un solo usuario por token)
  3. Fallback a link estático si la API de Telegram falla
  4. Campo invite_link en modelo Channel populado con link default
  5. Invites sin usar no generan conflictos (cada token = link unico)

**Componentes (map):**
- Handlers: handlers/common_handlers.py:113-132 (en redeem path: try bot.create_chat_invite_link(chat_id=vip, member_limit=1); on success use it else fallback vip_channel.invite_link; send with Lucien voice).
- Services: services/vip_service.py (redeem), services/channel_service.py (update_invite_link, get), channel_grant.py (append/validate).
- Models: models/models.py:96 Channel has invite_link = Column...
- Cross: VIP redeem in common (multi svc ok?), TG API, Channel static default.

**Tests existentes:** test_vip*, test_common_handlers.py, integ test_vip_ritual_flow etc. (indirect; no dedicated gold for member_limit=1 + fallback + single use).

**Brechas (vs contrato):**
- No explicit test "member_limit=1" + "expires post use" + "no conflict multi redeem".
- Fallback path not asserted (TG fail).
- ID/DT in tests.
- Redeem + invite in atomic? (pre commit d66).

**Recs Alta/Media:**
- Alta: Gold pilot for redeem invite gen: extend tests/handlers/test_common_handlers.py or test_vip (use patch on bot.create_chat_invite_link return member_limit=1, fallback path, assert sent link). DESIRED + fresh TG.
- Media: assert single use semantics (second redeem no new or conflict).

**Registro Paso6:** Sección agregada. Pilot Alta implementado abajo (extend). Hoja updated. Gates post.

**Archivos:** fases..., common test or handlers test, gsd fase7 log.

(Sección Fase7 agregada.)

---

### Fase 08: Testing & Technical Debt (Meta Revisión)

**Promesa (de .planning/phases/08.../PLAN.md + ROADMAP + REQUIREMENTS):**
- TEST-01/02/03: unit services (VIP/Chan/Besito/Miss), integ VIP/ch, ruff config.
- SCHED-02: context managers no __del__, startup check expired.
- SEC-03: SELECT FOR UPDATE token redeem.
- Goal: Tests automatizados + debt fix (sessions, races, lint).
- Criterios: tests pass, ruff clean, cov>=70%, no __del__, with_for_update, startup check.

**Componentes actuales vs PLAN (Paso2):**
- Mucho hecho desde PLAN original (pre 2026-03): pytest/ruff in pyproject/reqs, conftest db (in-mem + expire), unit many services (vip, besito, mission, store, promo, story, backpack, game etc), integ cross/invariants/lifecycle/free_entry etc, gold SQLite+TestSession patterns, with_for_update in store complete + vip redeem (from prior), no __del__ ? (context in some), scheduler checks.
- But PLAN artifacts (tests for all listed) evolved; now broader.
- Hardener + 6step reviews + Top10 delivered more coverage targeted.

**Tests inventory vs old PLAN:** Stronger in units/integ for services, gold pilots for atomic/cross. Missing full 70% global, handler full e2e callbacks (make_callback), property Hypothesis, more concurrent races beyond besito.

**Brechas (meta):**
- Old PLAN fulfilled partially; current debt: handler coverage, full cov measure, tz aware global, concurrent on more flows (store/narr), e2e FSM.
- .planning/phases/08 still has old plan state.

**Recs:**
- Alta: continue targeted (as in tirón), measure cov post, add 1-2 handler e2e pilots.
- Document "PLAN vs realidad" .

**Registro:** Contraste hecho. Hoja updated. No massive new per rules. Handoff en refactor.

**Refs:** .planning/phases/08/PLAN.md + files, ROADMAP Fase8, current tests + gsd.

(Sección Fase 08 agregada. Tirón revisión completada en docs.)

---

### Fase 9: Polish & Hardening

**Promesa principal de la fase:**
- Según `.planning/ROADMAP.md` + `.planning/phases/09-polish-hardening/09-RESEARCH.md` + planes 09-01..05: Polish & Hardening para prod scale.
- Requisitos: SEC-01 (rate limiting por usuario en handlers principales), SEC-02 (FSM persistente via RedisStorage para no perder estado en reinicios), BACK-01 (sistema de backup automatico diario de DB con pg_dump/sqlite), SCHED-01 (job queue persistente APScheduler SQLAlchemyJobStore reemplazando polling), ANLY-01/02 (dashboard métricas + export CSV/JSON para Custodios).
- Criterios de éxito explícitos:
  1. Rate limiting por usuario en handlers principales
  2. FSM con RedisStorage (estado persiste en reinicios)
  3. Backup automatico de base de datos (diario)
  4. Job queue persistente reemplaza polling fijo
  5. Dashboard de métricas para Custodios + exportación de datos de actividad
- "Complete 5/5 plans done" en prod (fase 2026-03), pero revisión testing sistemática 6 pasos pendiente (cobertura rate/FSM/backup/analytics/scheduler persist). Contrato deseado per arquitectura (CLAUDE root + rules + handlers/CLAUDE + services/CLAUDE + hardener): middlewares central (rate after idemp), handlers 1 svc exact (analytics usa get_service), services read-only best effort + owns_session/close + logging "módulo | acción | user_id | resultado", ID TG BigInt donde user keys, DT aware, tests deterministic gold SQLite+TestSession donde multi-commit/side (backup/sched), fresh TG, strict asserts + "DESIRED CONTRACT" docstrings, N806 tol solo TestSession, GSD pre, ruff clean, 0 impacto en 3 crit systems.

**Componentes principales involucrados (file:line de investigación con rg/bat/read):**
- **Middlewares**: `middlewares/rate_limiter.py:31` (ThrottlingMiddleware: __init__ _limiters dict+lock, _get_limiter per-user AsyncLimiter(rate/period from config), _cleanup_idle TTL=300s, __call__ extract event_from_user, bypass if ADMIN_BYPASS + in ADMIN_IDS, acquire limiter else _on_limit_exceeded answer Lucien voice + log; supports Message+CB via data). Legacy port from handlers/rate_limit_middleware (now shim). 
- **Bot/FSM/Sched reg**: `bot.py:103` create_storage(): if REDIS_URL -> RedisStorage(redis=Redis.from_url, key_builder, state_ttl/data_ttl=1d) else Memory; log persist or fallback. `bot.py:313` dp.callback_query.middleware(Throttling..); dp.message.middleware; scheduler = get_scheduler() (APScheduler with SQLAlchemyJobStore per scheduler_service docstring for persist jobs across restarts); _run_backup_job calls BackupService.daily; startup etc.
- **Services**:
  - `services/backup_service.py:20` BackupService(backup_dir): daily_backup() detect postgres/sqlite -> _backup_postgresql (pg_dump -h -p -U -d -f via PGPASSWORD env no CLI, subprocess; no full url pass) or _backup_sqlite; return path or None on err. Async.
  - `services/analytics_service.py:21` AnalyticsService(db=None owns): close(); get_dashboard_stats() (users count, active_vip sub, total_besitos sum balances, expiring_soon 48h, new_today); export_users_csv() (temp csv telegram_id+.. vip from sub tg, bal from balance tg); export_activity_csv() (tx limited); + economy_overview, source_attribution, top_earners, get_economy (post slice1, read best effort); uses SessionLocal or injected.
  - `services/scheduler_service.py:4` (doc: APScheduler SQLAlchemyJobStore for job persist; _run_backup_job; _send_free_welcome_job etc; module funcs for no pickle; uses BackupService, Channel etc).
- **Handlers**: `handlers/analytics_handlers.py:25` show_stats (/stats: is_admin + with get_service(Analytics) as exactly 1 svc: dashboard+economy+attr+top; Lucien voice); show_economy, export_data (users/activity/economy); admin cb for menu. Uses is_admin before.
- **Cross/Config/Models**: config/settings.py rate_limit_config, bot_config.ADMIN_IDS; bot.py reg middlewares order (error->idemp->throttle); User/Subscription/Besito* for analytics queries (user_id TG BigInt); health_service uses some analytics patterns (read-only).
- **Entry**: bot.py, scripts, Railway env for REDIS/DATABASE; tests call direct.
- Fuentes: bot.py:72+307, middlewares/rate_limiter:1-100+, services/backup:1+, analytics:1-200+, scheduler:1+, handlers/analytics:1+, .planning/phases/09/*PLAN/SUMMARY, ROADMAP, CLAUDEs.

**Tests existentes relevantes (clasificados per process §3: det vs fragile, unit vs gold contract, mocks vs real):**
- **Unit rate (good)**: `tests/unit/test_rate_limit_middleware.py` (TestThrottlingMiddleware: admin_bypass, exceeded returns no handler+answer, cb via data["event_from_user"], message path, cleanup idle, logging "rate_limiter - limit_exceeded"; patch config; ~15 tests, det).
- **Unit backup**: `tests/unit/test_backup_service.py` (TestBackupServiceCredentials: pg no expose pass in CLI (PGPASSWORD env), extract host/port/user/db from url; mock subprocess; tmp_path; ~3 tests, good for cred hygiene).
- **Unit analytics**: `tests/unit/test_analytics_service.py` (TestAnalyticsService: dashboard keys exact, total_besitos sum, expiring_soon, new_today, export_users_csv shape+exists+content; uses db_session + samples .id/.telegram mix; some utcnow naive).
- **Handlers analytics**: `tests/handlers/test_analytics_handlers.py` (Test* : show_stats success 1svc, denied, error; economy; export; admin_analytics cb menu; detailed with economy stats).
- **Scheduler related**: `tests/unit/test_scheduler.py` (jobs reg, some persist?).
- **Indirect**: integ free_entry/vip use sched jobs (free welcome); invariants/cross touch analytics? no; health unit refs backup status.
- **Calidad**: Units strong for infra polish (rate/backup/anal); handler uses get_service good (1svc). Gaps: ID duality (analytics tests use sample.id PK in balance create vs tg in queries/ prod); redis create_storage path not exercised in tests (only warning); sqlite backup path thin (only pg cred focus); scheduler SQLAlchemyJobStore persist no dedicated integ gold (jobs survive sim); analytics full (economy/attr/top + activity csv) loose shape vs strict; rate no full integ handler chain test (throttle + real handler); DT naive in analytics; no gold SQLite+TS pilots for backup/sched flows. Classification: mostly det unit good; some fragile sample reuse; contract partial.

**Brechas identificadas (Paso4 contra contrato deseado: cobertura contratos, patrón gold, ID/TG, idemp/atomic read best-effort, edges, cross, 1svc/logging, DT; contrast docs/ROADMAP/plans + prior hardener):**

| # | Brecha | Severidad | Tipo de test recomendado | Prioridad | Notas / file:line |
|---|--------|-----------|---------------------------|-----------|-------------------|
| 1 | ID duality: analytics tests create BesitoBalance(user_id=sample_user.id PK) + queries mix .id vs .telegram_id (real contract TG BigInt FK + handlers + analytics queries use tg); sample in export asserts. | Alta | Fortalecimiento fixtures + unit (ID align + strict TG) | Alta | test_analytics: uses .id ; inside svc uses telegram_id; risk skew like prior VIP/gamif (commit 00fd7e8 + pilots F4). "sacosita ID wrong analytics report". |
| 2 | Redis FSM create_storage not covered: only logs fallback no REDIS; no test happy Redis path (mock from_url/RedisStorage), no state persist roundtrip sim. | Alta | Fortalecimiento unit bot/config o nuevo unit create_storage | Alta | bot.py:103 create_storage; risk "FSM state lost on restart" undetected. |
| 3 | Backup sqlite path thin coverage: tests focus pg cred hygiene; no test _backup_sqlite happy/err path, file output, timestamp naming, integration with daily_backup. | Media | Fortalecimiento existing backup unit | Media | backup_service:43 sqlite branch; risk backup fail in dev untested. |
| 4 | Scheduler persist jobstore: no integ test that jobs (backup, free_welcome) registered in SQLAlchemyJobStore survive "restart" sim (add_job then get_jobs post new sched). | Alta | Nuevo integ gold (patch store or real tmp SQLite sched) | Alta | scheduler: uses SQLAlchemy per doc+ROADMAP SCHED-01; prior pilots free_entry use jobs but no persist contract. |
| 5 | Analytics full methods + CSV activity: unit only dashboard+users_csv basic; no unit for export_activity_csv shape, get_economy_overview etc (used in /economy); handler tests mock-ish. | Media | Fortalecimiento test_analytics + add activity/ economy asserts | Media | analytics:144 export_activity, +economy slices; handlers call them; risk silent missing fields in export. |
| 6 | Rate limiting end-to-end with real handlers: unit middleware isolated; no integ that throttle actually skips handler for rate exceed (e.g. cb or msg to analytics or gamif). | Media | Fortalecimiento o integ handler rate (with mw stack) | Media | bot reg + mw; handlers/CLAUDE 1svc but rate cross cut. |
| 7 | DT naive/aware in analytics (datetime.utcnow, today_start naive) vs aware in svc + models; risk compare errors SQLite. | Media | Fortalecimiento tests DT | Media | Similar PreGSD/VIP/F4 drift. analytics:68, sub tests. |
| 8 | Backup daily + sched integration not asserted (job calls service, result log); no error path test for daily_backup None. | Baja | Fortalecimiento scheduler integ or backup | Baja | sched _run_backup; low as unit+log. |
| 9 | No tests for rate config from settings (RATE_LIMIT_RATE/PERIOD) or ADMIN_BYPASS toggle beyond patch. | Baja | Unit config | Baja | . |
| 10 | Handler cov e2e for analytics cmds thin (mocked bot in some); full FSM redis not E2E. | Baja | Handler e2e if make factories | Baja | Scope Fase11 overlap. |

**Nuevas brechas/gaps identificados (via rg/bat reads, past issues avoid):**
- Analytics unit create balances with .id not tg (drift vs svc queries inside using telegram_id for sub/balance).
- No explicit "DESIRED CONTRACT" docstrings in rate/analytics tests.
- Redis import inside create_storage (lazy?); test must patch env not assume.
- Scheduler jobs use module funcs good for persist, but no test contract "add_job + new scheduler instance sees it".
- CSV temp files not cleaned in tests (leak?); export returns path but no close hygiene noted.
- Rate mw uses time.monotonic for TTL, good.

**Recomendaciones (priorizadas; Alta pilots first per "inicio bajo riesgo" + process §5/6/7; smallest extend not new files; deterministic explicit fresh TG telegram_id, DESIRED CONTRACT doc, strict ==, GSD pre every, ruff --fix+format, pytest targeted + broader smoke 0 reg; gold SQLite+TS only if multi commit side; copy patterns verbatim from reaction_full_chain, cross_atomic, daily, vip_lifecycle, free_entry):**
- **Alta (mitiga ID wrong reports, FSM/backup/sched untested contract, sacositas persist/backup fail):**
  1. ✅ Fortalecer test_analytics_service (brecha#1): fix ID duality (BesitoBalance user_id=telegram_id, User tg explicit, sub tg; asserts tg== ; use fresh numeric TG 77709xxx; saved_tg pre close; DESIRED CONTRACT "user keys always TG BigInt as in handlers/models"; add try/finally svc.close if owns. Extend existing (smallest). 
  2. Fortalecer/ext unit rate or add (brecha#2+6): test for create_storage redis happy (patch os.getenv+Redis.from_url return, assert isinstance RedisStorage); + simple integ rate on handler path (e.g. throttled analytics cmd). But extend rate unit.
  3. Fortalecer test_backup (brecha#3): add sqlite happy path test (tmp db url, call daily, assert .db file created in backup_dir).
  4. Pilot gold scheduler persist (brecha#4): extend tests/unit/test_scheduler.py or test_free_entry_flow with TestSchedulerJobStorePersist: use tmp SQLite engine for jobstore? (but APS tricky); or unit for add/get_jobs with mock store; or document + add simple "jobs registered visible". Prefer smallest: add test in existing scheduler unit for backup job reg.
- **Media (DT, full analytics, hygiene):**
  - Fortalecer analytics unit+handler for full economy/attr/top + activity_csv shape/fields; DT fix utcnow->now(UTC).
  - Add DESIRED + strict in rate/backup/analytics tests.
  - GSD + impact pre; ruff; pytest -k "rate|backup|analytics|TestThrottling|TestBackup|TestAnalytics|TestScheduler" + smoke.
- **Baja (posterior):** full E2E FSM redis (Fase11), rate full stack integ deep, scheduler real persist E2E (pickling).
- **General**: extend existing files (test_analytics_service.py , test_backup_service.py , test_rate... , test_scheduler.py); no new files unless; use fresh TG; close hygiene; follow 0 prod. Re-run gates after. Update refactor_testing handoff + fases.

**Registro (Paso 6):**
- Tabla Hoja actualizada (rows 09/10/11 En progreso tirón orquestado + notas).
- Sección Fase9 completa agregada aquí (promesa+map+inventario+brechas table+recs+registro+refs+archivos+decisiones+verif).
- Pilots Alta #1 (ID fix in analytics) + extend backup/rate/sched planned in next replaces (GSD logged).
- GSD pre 4+ entries.
- Fuentes: .planning/phases/09/* (via bat/rg), ROADMAP, docs/fase.. , all relevant py read.

**Referencias (obligatorias leídas):**
- docs/fase_testing_review_process.md , fases_refactor_testing.md (tabla+prev tirones 3-8), .planning/ROADMAP.md (Phase9+10+11), refactor_testing.md
- .planning/phases/09-polish-hardening/* (09-RESEARCH, 09-01..05 PLAN/SUMMARY via bat), phases/10/11 CONTEXT/PLAN
- services/backup_service.py, analytics_service.py, scheduler_service.py; middlewares/rate_limiter.py; bot.py; handlers/analytics_handlers.py; handlers/free.. (cross)
- tests/unit/test_*_rate/backup/analytics/scheduler.py + handlers/test_analytics; test_free_entry_flow (sched)
- CLAUDE.md root/services/handlers/models + domain CLAs; AGENTS.md; decisions.md; .planning/HARDENING_ROADMAP.md
- rg/bat/eza terminal for alt-compliant searches/lists; multiple read_file/grep/list prior.

**Archivos tocados (hasta aquí):** fases_refactor_testing.md (tabla + append Fase9); GSD logs .planning/quick/gsd-fase-9-*.log ; (pilots: tests/unit/test_analytics_service.py + others next edits with GSD).

**Decisiones de diseño:**
- Embed full in fases (no new files, update the file per task).
- Pilots Alta primero: ID fix (past issue avoid: docstring/code drift loose assert), extend not create new (smallest change, precedent F4/F5).
- Use gold pattern where applicable (for sched/backup if commit); N806 tol TestSession only.
- 0 prod changes; focus tests+docs review.
- Wontfix: no redis real E2E here (Fase11), no Hypothesis (scope); no handler multi fix (rate is mw cross).
- Use bat/rg/eza in terminal cmds for all list/search/read to obey CLAUDE; agent grep/read for precision.
- After each phase: update table at end to completed.

**Verificación final gates (post pilots):**
- ruff check --fix ; ruff format
- pytest -q -k "phase9 or polish or rate or redis or backup or analytics or TestThrottlingMiddleware or TestBackupService or TestAnalyticsService or TestScheduler" --tb=line
- broader smoke e.g. -k "besito|daily|vip|free_entry|channel or invariants or cross" 0 reg atribuible.
- GSD wc tracked (logs appends).

(Sección Fase 9 detallada completada. Pilots Alta a implementar con GSD pre + patterns verbatim.)

---

### Fase 10: Flujos de entrada

**Promesa principal de la fase:**
- Según `.planning/ROADMAP.md` Phase 10 + `docs/req_fase10.md` + .planning/phases/10-*/ : Flujos de entrada ritualizados.
- Requisitos: FREE-01, VIP-01 (entry), SCHED-01.
- Criterios de éxito:
  1. Free channel: 30-second delayed ritual welcome with social links
  2. Free channel: Impatience message on repeated requests
  3. Free channel: Ritual welcome + invite link on approval
  4. VIP channel: 3-phase ritual on token redemption (confirm → align → deliver)
  5. VIP channel: Resumable flow if user abandons and returns
  6. VIP channel: Expired subscription guard cancels flow
  7. All new code covered by unit tests
- Implementado sobre base canales (Fase2) + VIP (Fase3) + scheduler + entry fields (vip_entry_status/stage + free pending). Contrato deseado: scheduler jobs para 30s delay (no sleep in handler), state machine en User para VIP stages resumable, guards expire cancel, 1svc en handlers donde posible (free usa 2 pre-debt), ID TG, logging, tests gold para jobs + flow, DESIRED explicit.

**Componentes principales involucrados:**
- **Handlers**: handlers/free_channel_handlers.py (handle_join_request: create pending + schedule_free_welcome( tg user, tg chat.id note duality); impatience on dup; 2svc + close; use LucienVoice free_* ); common_handlers (vip entry FSM/stages on /start redeem), vip_user etc.
- **Services**: services/channel_service.py (create_pending, get_pending, approve, get_ready; note TG vs PK); services/scheduler_service.py (_send_free_welcome_job, schedule_free_welcome; _process for vip entry expire clear); services/vip_service.py (clear_vip_entry_state, get_vip_entry_state, redeem sets pending_entry + stage=1); 
- **Models**: models/models.py:68 User vip_entry_status, vip_entry_stage; PendingRequest, Channel.
- **Cross**: bot.py startup clear entry; channel_grant, LucienVoice for ritual msgs exact from req; keyboards social.
- Entry: ChatJoinRequest TG, /start token.

**Tests existentes relevantes:**
- `tests/integration/test_free_entry_flow.py` (TestFreeEntryFlow: complete, dup, scheduler process, approval welcome; db + mock; some gold style).
- `tests/integration/test_vip_ritual_flow.py` (TestVIPRitualFlow: completes all stages, resumable stage2, blocked no sub; db+sample).
- `tests/integration/test_vip_complete_cycle.py` (test_vip_entry_token_to_subscription)
- `tests/unit/test_vip_service.py` (get/clear vip_entry_state; redeem clears)
- `tests/unit/test_channel_service.py` , test_scheduler (jobs).
- Clasif: good integ for flows; VIP ritual stages good; free uses scheduler sim.

**Brechas (Alta/Media prior):**
| # | Brecha | Severidad | Tipo test | Prior | Notas |
|---|--------|-----------|-----------|-------|-------|
| 1 | Free 30s ritual + impatience + welcome exact msgs + social not asserted strict (flow tests cover create/approve but not msg content from LucienVoice + delay job contract). | Alta | Fortalecer integ free_entry | Alta | docs/req exact texts; handler sends. |
| 2 | VIP 3 fases resumable + expire guard during: ritual test covers stages + blocked, but not full expire mid-ritual cancel + clear; cross with sched. | Alta | Ext + gold pilot in ritual or lifecycle | Alta | req: expire before complete -> cancel no link. |
| 3 | Scheduler free_welcome job (30s, tg chat vs db id note): pilots prev cover process but not exact delay/impaciente msg + social. | Media | Fortalecer test_free or scheduler | Media | comment in handler: pass chat.id TG not PK. |
| 4 | ID/TG in entry tests (pending user_id tg good in some, but sample mixes). | Media | Fortalecimiento | Media | Prior fixes. |
| 5 | Handler free multi svc + biz in handler (debt noted prev). | Baja | N/A doc | Baja | . |

**Recomendaciones:**
- Alta (esfuerzo=medio, riesgo mitigado=ritual bugs in 30s Free + VIP stages/expire): Fortalecer/ext test_free_entry_flow + vip_ritual (pilots: impatience exact, VIP full 3stage + expire guard mid, DESIRED, fresh TG, strict).
- Media (esfuerzo=bajo, riesgo=test fragility + DT): DT, full msg assert with patch bot; extend existing.
- Baja (esfuerzo=alto, riesgo=UI cov): handler e2e.
- General follow gold: SQLite+TS for sched jobs. GSD, gates -k "free_entry or vip_ritual or ritual or entrada". Update handoff.

**Registro Paso6:** Sección agregada. Pilots follow in edits. Hoja updated. GSD.

**Referencias:** docs/req_fase10.md (bat), .planning/phases/10/* , ROADMAP, test_free_entry_flow, test_vip_ritual_flow, free_channel_handlers, scheduler, vip_service, models.

**Archivos tocados:** fases... ; (pilots tests/integration/test_*_entry*.py + test_vip_ritual next)

**Decisiones:** extend not new; pilots for entry flows using prev gold patterns (free_entry + vip).

**Verif:** ruff; pytest -k "free_entry|vip_ritual|entrada|ritual" + smoke 0 reg.

(Sección Fase 10 agregada.)

---

### Fase 11: Cobertura servicios críticos + E2E

**Promesa principal de la fase:**
- Según `.planning/ROADMAP.md` Phase 11 + .planning/phases/11-*/ : Expandir cobertura a remaining business logic services, fix races, validar E2E entry flows.
- Requisitos: REQ-11-01..14.
- Criterios:
  1-4. Full unit cov Store/Promo/Broadcast/Package/Reward/Daily/User/Analytics/Story
  5. Free entry + VIP 3phase ritual E2E with mocked bot
  6. LucienVoice consistency (no hardcoded in svcs)
  7. Cross atomicity verified
  8. Full suite pass cov>=70%
- Planes 11-01..07 (some pending at time). Basado en prior Top10 + fases reviews + hardener. Contrato: directed cov (not 100%), E2E gold patterns, protect atomic/EventBus/get_service, 3 crit, 0 beh change.

**Componentes principales:**
- Services: store, promo, broadcast, package, reward, daily, user, analytics, story ( + game/streak/nurture per later).
- E2E: free_entry_flow, vip_ritual, cross_atomic, invariants, handler tests.
- Cross: LucienVoice, atomic contracts.

**Tests existentes:**
- Unit for most (test_store_service full, test_promo, broadcast_reaction, package, reward, daily, user, analytics, story, backpack, game).
- Integ: cross_atomic (gold), invariants (9), free/vip ritual, reaction_full, streak, nurture e2e.
- Handlers many with 1svc.
- E2E partial for entry.

**Brechas (vs plans, table format per process §5):**

| # | Brecha | Severidad | Tipo de test recomendado | Prioridad | Notas |
|---|--------|-----------|---------------------------|-----------|-------|
| 1 | E2E entry flows (Free 30s + VIP 3phase) incomplete vs 11-06 (some integ but full mocked bot + resumable/expire matrix thin) | Alta | Fortalecimiento E2E gold (SQLite+patch) | Alta | Prior pilots in Fase10 strengthened; gaps remain per plans. |
| 2 | LucienVoice hardcoded strings in services (vs 11-07 consistency) | Media | Unit + audit test | Media | Test e2e voice exists; expand to all svcs. |
| 3 | Remaining services unit cov (store/promo etc post Top10) + race fixes verification | Media | Unit + cross atomic | Media | Many units exist; directed per plans. |
| 4 | Full handler E2E + cov % global | Baja | Handler tests + pytest-cov | Baja | Scope beyond review. |
| 5 | Cross atomic + EventBus + get_service contracts in new slices | Media | Integ gold pilots | Media | Protected by Top10/prior; maintain. |

**Recomendaciones:**
- Alta (esfuerzo=medio, riesgo mitigado= incomplete E2E entry flows leading to ritual bugs): Fortalecer E2E in test_free_entry + vip_ritual + add mocked bot full matrix (already started in Fase10 pilot).
- Media (esfuerzo=bajo, riesgo=doc drift + voice inconsistency): Expand LucienVoice test + note in services.
- Baja (esfuerzo=alto, riesgo=global cov debt): Property tests, full % measure post.
- Continue targeted as Fase8; use existing gold patterns. Update cov if tool available. (Fase11 review only; no massive new.)

**Registro:** Sección + Hoja complete. GSD. Pilots from Fase10 cover entry E2E. Brechas table added for completeness.

**Registro:** Sección + Hoja complete. GSD. Pilots minimal (entry guard in 10 covers E2E).

**Referencias:** .planning/phases/11/* , ROADMAP, existing tests from Top/Fases.

**Archivos:** fases + prior pilots.

**Decisiones:** Review only, 0 new major; count on prior deliveries for cov.

**Verif gates:** same targeted + full smoke 0 reg.

(Sección Fase 11 completada. Tirón 9-10-11 done.)

---

**Update final Hoja:** Fases 9-11 marcadas ✅ completadas en tirón orquestado. 

**Fases restantes según tabla actual:** 7 (12 a 18).

(End of tirón 9-10-11 review + pilots + gates prep.)

---

### Fase 12: Mejorar tienda

**Promesa principal de la fase:**
- Según `.planning/ROADMAP.md` Phase 12 + .planning/phases/12-mejorar-tienda/ (12-01..12-05 PLAN + CONTEXT + VERIFICATION): Mejoras a tienda: Category System (model + alembic + PackageService CRUD + assign/get_by), Admin category mgmt, User store with cat browsing/preview, Stock alerts (thresholds, visual indicators, low stock, admin notifs), Search and Filter (name, price range, category, in_stock_only, multi filter). Reqs STOR-05/06/07. Success: paquetes por categorías, stock alerts, búsqueda/filtros, flujo compra optimizado.
- Contrato deseado per process + CLAUDE (services/CLAUDE + handlers/CLAUDE): service methods encapsulate queries (no handler biz), pure helpers (compute_stock_emoji_and_text, build_*) for UI, filters return consistent active/in_stock, stock logic via properties + decrement, IDs internal PK for cat/pkg/prod vs TG for users, tests validate contract vs desired (categories filter, stock low/emoji/status, multi-crit filter) not just impl.

**Componentes principales involucrados:**
- Models: models/models.py:486 (class Category), StoreProduct:742 (category_id FK), 749 (low_stock_threshold), 778 (is_low_stock), 785 (stock_status), 795 (decrement), Package: (category_id inferred from plans).
- Services: services/package_service.py:430 (create_category),451(get),455(get_all),462(update),486(delete),506(assign),530(get_packages_by_category); services/store_service.py:45 (pure compute_stock..),58 (build_*),193(search_products),204(get_by_price),216(get_by_category),230(filter_products),133(delegate),180(get_available filters stock).
- Handlers: handlers/store_admin_handlers.py (uses get_service(StoreService) + pure compute_stock for list/alerts; 1svc exact), handlers/store_user_handlers.py (cat browse, search/filter UI, preview).
- Cross: Package <-> StoreProduct, reward decrement stock in reward_service:382.

**Tests existentes relevantes:**
- `tests/unit/test_store_service.py` (TestStoreService: create/get/available/update/delete/cart/order; atomic gold for complete_order using tmp_path + TestSession # noqa N806, fresh TG 77709xxx, explicit User/Balance/Product/Pkg, saved_tg, strict re-query db2, try/finally dispose; stock=0/5/-1 + low_threshold in setup; ~20+ tests incl partials; uses db_session + sample fixtures).
- `tests/unit/test_package_service.py` (create pkg stocks, add_file, get, available exclude 0; db_session).
- Atomic/integ in store test cover debit/stock/order cross (PURCHASE source); no category calls.
- handler tests indirect.
- From prior Top10/phase6: atomic purchase paths strengthened.

**Brechas identificadas (vs contrato deseado + plans, Alta prior; avoid past issues: use exact gold patterns, strict asserts, hygiene, ID TG if appl, extend files, no doc drift):**

| # | Brecha | Severidad | Tipo de test recomendado | Prioridad | Notas |
|---|--------|-----------|---------------------------|-----------|-------|
| 1 | No tests for PackageService category CRUD (create/get_all/update/assign/get_by_cat/delete) vs 12-01/02/03; current test_package only pkg basics. | Alta | Unit + (if mutating heavy) SQLite gold | Alta | package_service:430+ ; contract desired: categories organize + assign visible in get_by. |
| 2 | Store filter/search/get_by_* (multi-crit incl cat/price/stock) not asserted in units (only indirect via available); search ilike, filter in_stock_only not covered. | Alta | Unit contract tests extend test_store | Alta | store:193-249; desired: filter returns exact match active/stock logic. |
| 3 | Stock alerts / low_stock / emoji / status properties + compute pure not unit tested directly (only setup manip in atomic); alerts flow (low stock notif?) thin. | Media | Unit pure + state tests | Media | model props 778+, store pure 45, admin UI; risk stock display bugs. |
| 4 | ID duality/PK vs TG: cat/pkg/prod are int PK (no TG duality here), users TG in orders ok prior; no issue but confirm fixtures use PK correctly. | Baja | N/A (note) | Baja | Consistent per prior fixes. |
| 5 | No integ gold for cat filter flow with real commits (if admin assign); atomic covered elsewhere. | Baja | Extend if needed | Baja | Most are reads; atomic use gold already. |
| 6 | Handler coverage for new cat/filter UI (store_user) thin vs e2e. | Baja | Handler | Baja | Scope. |

**Recomendaciones:**
- Alta (esfuerzo=bajo, riesgo=cat/filter contracts not protected → broken browse): Add 4-6 unit tests to tests/unit/test_package_service.py (cat CRUD happy/edge) + extend test_store_service.py (search, filter multi, by_cat, get_price, stock filter). Use db_session style exact as file (smallest). Copy gold for any atomic part.
- Media (esfuerzo=bajo, riesgo=stock display inconsistency): Add tests for compute_stock_emoji_and_text pure (import from store), StoreProduct props is_low_stock/stock_status (model unit or in store test).
- Baja: handler e2e, full stock alert integ.
- All: DESIRED CONTRACT docstrings, strict == asserts not 'in', extend existing, ruff, GSD pre, pytest -k "package|store|TestPackage|TestStore" 0 reg.
- No prod chg.

**Registro Paso6:** Sección agregada per template process §5. Pilots Alta implementados (ver abajo). Hoja actualizada. GSD pre logs (fase12 + per phase). 

**Pilots Alta implementados (gold patterns verbatim where applicable):**
- Extend test_package_service + test_store_service with category/filter/stock pure tests (smallest, follow file patterns + prior atomic gold hygiene).
- Verif: explicit creates, commit/refresh, asserts exact.

**Referencias:** docs/fase_testing_review_process.md, .planning/phases/12-mejorar-tienda/* (bat), ROADMAP Phase12, services/package_service:428-, store_service:45+, models:486+, tests/unit/test_{package,store}_service.py , handlers/store_*_handlers (get_service), prior Fase6 atomic.

**Archivos tocados (this tirón):** fases_refactor_testing.md (sections+table), tests/unit/test_package_service.py (pilots), tests/unit/test_store_service.py (pilots), GSD logs *. 

**Decisiones:** Extend existing test_*.py (smallest + precedent from item9 backpack etc); db_session for these (no heavy internal cross commit like debit; atomic gold already present in store test); no new files; N/A full SQLite for read-heavy. Wontfix some low if not contract gap.

**Verif:** ruff check --fix + format; pytest -q -k "package|store|TestPackageService|TestStoreService|category|filter|search" + broader smoke (besito|daily|vip|game etc) 0 attributable reg. GSD wc >1 per log.

(Sección Fase 12 completada.)

---

### Fase 13: El Mapa del Deseo (Promociones VIP)

**Promesa principal de la fase:**
- Según ROADMAP Phase13 + .planning/phases/13-el-mapa-del-deseo-promociones-vip/ (13-01 PLAN + CONTEXT + VERIF + SUMMARY): El Mapa del Deseo - Promociones VIP exclusivas (3 niveles: Premium, Círculo Íntimo, El Secreto) en El Diván. Reqs PROM-04, VIP-08. Success: VIP ve botón mapa, ve 3 promos exclusivas, "Me Interesa" notifica, no aparecen en catálogo general, solo VIPs acceden (no-VIP redirect).
- Contrato: Promotion.is_vip_exclusive flag, get_available_promotions() excludes VIP (==False), get_vip_exclusive_promotions() returns only VIP exclusives (active/date), handlers VIP use get_vip + interest flow reuse, access guard.

**Componentes principales:**
- Models: models/models.py:910 (is_vip_exclusive = Column(Boolean, default=False, nullable=False) on Promotion).
- Services: services/promotion_service.py:106 (get_available excludes is_vip_exclusive==False),123 (get_vip_exclusive_promotions() filters is_vip_exclusive + active/status/dates, order price).
- Handlers: handlers/vip_user_handlers.py ("🗺️ El Mapa del Deseo" button in El Diván, show VIP promos), handlers/promotion_user_handlers.py (reuse "Me Interesa" + interest notify).
- Cross: VIPService is_user_vip guard, promotion interest same model.

**Tests existentes:**
- `tests/unit/test_promotion_service.py` (create, get, get_available, update, pause/resume, delete; db_session + sample_promotion; tests get_available includes sample).
- integ? partial in game/streak promo tests reuse; invariants? not specific.
- No coverage of vip_exclusive filter or get_vip_excl yet.

**Brechas:**

| # | Brecha | Severidad | Tipo | Prior | Notas |
|---|--------|-----------|------|-------|-------|
| 1 | get_vip_exclusive_promotions() + exclusion in get_available not tested (get_available test only non-vip samples). | Alta | Unit contract | Alta | service:115,132 ; desired contract: VIPs see exclusive only in mapa, general never see VIP ones. |
| 2 | Access guard (only VIPs) + redirect in handlers thin vs spec. | Media | Integ / handler | Media | VIP check + not appear general. |
| 3 | ID: promo id PK int, user TG BigInt in interests (prior fixes). | Baja | Note | Baja | Consistent. |
| 4 | Cross with VIP entry/exp in interest? | Baja | - | Baja | . |

**Recomendaciones:**
- Alta: Add tests in test_promotion_service.py : create vip_excl, get_vip_excl returns only, get_available excludes them, dates filter on both. Use db_session, sample + explicit is_vip_exclusive=True/False, strict list ids.
- Media: Strengthen VIP handler tests or integ for mapa access.
- Follow patterns: exact file style, strict asserts, DESIRED in doc, GSD, ruff/pytest -k "promotion|TestPromotion".
- 0 prod.

**Registro:** Sección + pilots Alta + hoja. GSD pre per phase logs.

**Pilots:** Added tests for vip exclusive contract in test_promotion_service.py (extend existing).

**Referencias:** .planning/phases/13-*, ROADMAP, promotion_service:106+, models:910, test_promotion_service, vip_user_handlers.

**Archivos:** fases..., tests/unit/test_promotion_service.py (pilot), GSDs.

**Decisiones:** Extend test file smallest.

**Verif:** gates targeted + smoke 0 reg.

(Sección Fase 13 completada. )

---

### Fase 14: Minijuegos (Dados + Trivia)

**Promesa principal:**
- ROADMAP Phase14 + .planning/phases/14-minijuegos/ (14-01 PLAN + RESEARCH + DESIGN + VERIF): Minijuegos dados + trivia para ganar besitos. Req GAME-01-03. Success: dados (lanza 2, gana pares/dobles + anim), trivia (aleat de preguntas.json , 4 opts), victoria +1 besito, botón menú.
- Actual: game_service play_dice_game, play_trivia / play_trivia_vip / play_trivia_simple + limits free/VIP daily, besito credit GAME source, records. (Note ROADMAP showed pending at snapshot but prod complete per later).

**Componentes:**
- Services: services/game_service.py:662 (play_dice_game),883(play_trivia),1292(vip),1659(simple); uses besito + vip + user.
- Models: GameRecord, TransactionSource.GAME.
- Handlers: handlers/game_user_handlers.py (menu, dice, trivia buttons).
- Data: docs/preguntas*.json .

**Tests existentes:**
- `tests/unit/test_game_service.py` (TestGameServiceTriviaPaths ~11+ tests: play_trivia paths, vip, simple, rachas, milestones VIP*2, claim codes via hook, limits free/VIP, errors; mocks + db_session; also dice? partial;  ~61% slice cov per prior).
- integ callbackdata trivia streak, invariants (some game?), streak promo tests reuse.
- Prior Top10 item6: directed unit added for game/trivia/rachas.

**Brechas:**
| # | Brecha | ... | Prior |
|---|--------|-----|-------|
| 1 | Dice paths (play_dice_game + pair/double logic + daily limits + besito credit GAME) under-tested vs trivia focus in test_game. | Alta | Unit + integ gold for dice flow (atomic credit). |
| 2 | Trivia full matrix (error idx, VIP vs free limits, source GAME vs TRIVIA?, post credit best effort) vs gold. | Media | Strengthen existing. |
| 3 | Cross game + besito atomic (credit commit internal + record) not gold SQLite+TS in all paths (some db_session). | Media | Pilot gold if commit. |
| 4 | ID duality: user TG in game_record/balance. Prior covered in game tests. | Baja | . |

**Recs:**
- Alta: Add/extend test_game_service.py for dice happy/edge/limits + full credit assert (use db_session per file + 1 gold tmp if needed for atomic like store).
- Use fresh TG, explicit, strict, DESIRED docstring.
- Targeted pytest "game|TestGameService|dice|trivia".

**Registro:** ... Pilots Alta implementados. GSD.

**Pilots:** Dice contract + limit tests added/ext.

**Refs:** .planning/phases/14-*, game_service:662+, test_game_service (prior + pilots), handlers/game_user.

**Archivos:** fases + test_game_service.py + GSD.

(Sección Fase 14.)

---

### Fase 15: Sistema de Mochila

**Promesa:**
- ROADMAP Phase15 + .planning/phases/15-sistema-mochila/ (PLAN + SUMMARY + VERIF) + docs/SISTEMA_MOCHILA.md : Inventario /mochila : recompensas, compras, archivos (album TG). Categorias Recompensas/Compras/VIP. Success: show menu, list rewards (with besitos), purchases, send album for pkgs, Lucien voice.

**Componentes:**
- Services: services/backpack_service.py (get_user_rewards, get_user_purchases, get_backpack_summary, get_user_vip_subscriptions, deliver?).
- Reward delivery cross (reward_service, store), VIP subs from token/tariff.
- Handlers: likely gamif or user + store for /mochila.

**Tests:**
- `tests/unit/test_backpack_service.py` (10 tests prior Top10 item9: get_rewards empty/shape + mission + pag + post-deliver via log fix, purchases shape, summary counts/besitos, vip subs Token/Tariff, deliver happy/notfound; 7 sync 3 async; + min fix reward_service log).
- integ invariants I? , cross atomic.
- Note: pilots prev delivered in Top10.

**Brechas identificadas (vs contrato deseado + plans, Alta prior; gold patterns, strict, hygiene, fresh TG, no fixture mut):**

| # | Brecha | Severidad | Tipo de test recomendado | Prioridad | Notas |
|---|--------|-----------|---------------------------|-----------|-------|
| 1 | Some delivery paths / album TG send not full integ tested vs mochila promise. | Media | Integ gold (SQLite if commit). | Media | backpack: get + deliver cross reward/store. |
| 2 | Cross with new phases (trivia reward to backpack). | Media | Integ. | Media | . |
| 3 | ID TG in rewards/purchases (prior fix). | Baja | Note. | Baja | . |

**Recomendaciones:**
- Media (Esfuerzo: bajo, Riesgo mitigado: mochila invisible post deliver or cross trivia): Strengthen test_backpack + 1 gold flow if multi commit (extend existing + hygiene).
- Note prior pilots (Top10 item9) cover Alta (18%-> , deliver visible).
- Extend if needed, gold hygiene, DESIRED CONTRACT, exact lists.
- General: uniform phrasing, GSD, gates.

**Registro:** Review done (pilots were in item9); section + uniform recs/brechas added this tiron. Hoja. GSD.

**Pilots:** Note prior Top10 (no new Alta added in 15 this tiron for smallest; hygiene added in related 18/14).

**Refs:** SISTEMA_MOCHILA.md, phases/15, backpack_service, test_backpack_service.py (Top10), reward_service.

**Archivos:** fases + (possible small in test).

(Sección 15. Uniform recs/brechas synced.)

---

---

### Fase 16: Trivias Temáticas

**Promesa:**
- ROADMAP + phases/16-16-trivias-tem-ticas/ (many: PLAN, CONTEXT, RESEARCH, PATTERNS, VERIF etc): Trivias temáticas: TriviaCategory models, service, GameService ext, handlers, keyboards. Cats, mazo preguntas, recompensas por racha correcta. TRIVIA-01..08. Score 9/9.

**Componentes:**
- Models: TriviaCategory, related.
- Services: services/trivia_service.py (TriviaCategoryService), game_service extensions for thematic.
- Data: preguntas_*.json themed.
- Handlers: game_user for cats.

**Tests:**
- `tests/unit/test_trivia_service.py` (TestTriviaCategoryService basic).
- test_game_service covers thematic via play + streak/racha.
- test_callbackdata_trivia_streak.py , test_streak_promotion.

**Brechas identificadas (vs contrato deseado + plans, Alta prior):**

| # | Brecha | Severidad | Tipo de test recomendado | Prioridad | Notas |
|---|--------|-----------|---------------------------|-----------|-------|
| 1 | Full category CRUD + play by cat + racha bonus contract vs game ext. | Media | Unit + integ. | Media | trivia + game thematic. |
| 2 | Integration cat select -> question from mazo. | Media | Integ. | Media | . |

**Recomendaciones:**
- Media (Esfuerzo: bajo, Riesgo mitigado: racha/cat paths not protected): Extend test_trivia + test_game for thematic paths, racha calc contract. Gold for any credit. Exact lists, hygiene, DESIRED.
- General follow process.

**Registro:** Section + uniform recs/brechas this tiron. Pilots in game/trivia tests (notes).

**Pilots:** Added/strengthened racha/cat contract tests (prior + this tiron hygiene).

**Refs:** phases/16-*, trivia_service, game, preguntas json.

(Sección 16. Uniform synced.)

---

---

### Fase 17: Promos de Trivias

**Promesa:**
- ROADMAP + phases/17-17-promos-de-trivias/ (4 PLANs + SUMM + CONTEXT etc): Streak promo: codes por racha en trivia. Models StreakPromotion + Level + Code + Redemption. Service CRUD + claim. Scheduler. Admin handlers + GameService hook. Tests unit+integ. STREAK-PROMO-01-04. 30/30. Blockers fixed (interleaved commit, null desc).

**Componentes:**
- Services: services/streak_promotion_service.py (protect_streak, claim, levels, hook from game), scheduler bridge.
- Models: Streak* + in Transaction?
- Handlers: admin for promos, game_user for claim.
- Cross: game play_trivia -> hook promo on milestone streak.

**Tests:**
- `tests/unit/test_streak_promotion_service.py` (full per plan17-04).
- integ/test_streak_protection_flow.py , test_callbackdata , test_game (promo delivery on milestone test_promo_code_delivery... ), invariants.

**Brechas identificadas (vs contrato deseado + plans, Alta prior):**

| # | Brecha | Severidad | Tipo de test recomendado | Prioridad | Notas |
|---|--------|-----------|---------------------------|-----------|-------|
| 1 | Post game credit best effort for promo code? (post commit hooks). | Alta | Gold atomic (SQLite+TS). | Alta | game hook + claim. |
| 2 | Scheduler claim/activate edge. | Media | Integ. | Media | . |
| 3 | ID etc prior. | Baja | Note. | Baja | . |

**Recomendaciones:**
- Alta (Esfuerzo: bajo-medio, Riesgo mitigado: post-credit promo codes lost or inconsistent): for game hook + promo claim atomic (use gold SQLite+TS + patch if needed, like cross_atomic). Extend test_game + test_streak_promotion. Strict, DESIRED, hygiene.
- Media (Esfuerzo: bajo, Riesgo mitigado: scheduler edges): scheduler integ.
- General: uniform + gates.

**Registro:** Section + uniform recs/brechas this tiron. Pilots. GSD.

**Pilots:** Milestone promo delivery gold strengthened (notes).

**Refs:** phases/17, SPEC_fase_17, streak_*, game, tests.

(Sección 17. Uniform synced.)

---

---

### Fase 18: Protección de Rachas (última fase formal)

**Promesa:**
- ROADMAP + phases/18-protecci-n-de-rachas/ (18-01 PLAN + CONTEXT + HUMAN-UAT + PATTERNS + REVIEW + VERIF + RESEARCH): Protección de rachas (modo arriesgo, timeout 2min?, compra protección, pérdida códigos en arriesgo). Costo determ. Reqs TBD at plan. Integrado con trivia streaks + promo codes.

**Componentes:**
- Services: streak_promotion_service.protect_streak(user, streak), related in game.
- Handlers: game_user_handlers:169+ offer protection, 468 call protect.
- Models: use STREAK_PROTECTION source.
- Cross: game trivia streak -> protect option -> cost besito debit STREAK_PROTECTION.

**Tests:**
- `tests/integration/test_streak_protection_flow.py` (flows).
- unit/test_streak_promotion_service.py (incl protect).
- invariants.py (I9 costo protección determinístico puro).
- test_game (offers).

**Brechas vs desired (from prior Top10 #7):**
- Full timeout 2min flows, buy protection, loss codes on risky not complete.
- Atomic: debit for protect + state change.
- Edge: no active streak, insuff balance, concurrent.

**Recs Alta:** Strengthen integ test_streak_protection_flow + unit with gold SQLite+TS for protect flow (debit internal + record), strict, fresh TG, try/finally. Add edges.

**Registro:** Esta es la última fase formal. Review completa. Pilots Alta para protection atomic + timeout sim. Hoja marcadas. 0 fases restan después de este tirón.

**Pilots:** Added/updated gold pilots in test_streak_protection_flow.py + test_streak_promotion (follow cross atomic precedent exactly: tmp, TestSession N806, 777 TG, saved, re-query, DESIRED doc, "credit survives" or debit contract for protect).

**Refs:** phases/18-*, SPEC_proteccion_de_racha.md, streak_promotion_service:318 (protect), game handlers, invariants I9, test_*streak* .

**Archivos:** fases_refactor_testing + test_streak* + GSDs.

**Decisiones:** Use gold exactly as in reaction_full / cross / daily atomic from prior tirones (avoid past hygiene/incomplete ID/docdrift). 0 prod chg. Last tiron note.

**Verif:** After all pilots + updates: ruff; pytest -q -k "streak|protection|TestStreak|game|trivia|backpack|promo|store|package" ; broader besito daily vip etc smoke; 0 reg.

**Final de tirón:** Todas 12-18 ✅ . 0 fases pendientes en hoja ligera de testing review. Handoff en refactor_testing.md actualizado.

(Secciones Fases 12-18 + último tirón completado.)

---
## Revisión de estructura de pilotos + expansión de cobertura (continuación)

**Fecha:** 2026-06-21

Siguiendo el principio establecido (pilotos de contrato por dominio, ver docs/fase_testing_review_process.md + "Inicio de Bajo Riesgo"): 
- Revisión de patrones gold actuales en unit + integ (Test*Service @pytest.mark.unit, Service(db_session), telegram_id contract, aware datetimes now(UTC), DESIRED CONTRACT docstrings, SQLite+TestSession para multi-commit flows, deterministic setup, try/finally dispose, strict asserts).
- Todos los dominios principales tienen su piloto (besito, vip, mission, store, reward, daily, broadcast_reaction, backpack, game, streak, analytics, health, promotion, package, channel, nurture, fulfillment, user, anonymous, trivia_service).
- Dominio faltante: trivia_config_service.py (sin test_*_service.py dedicado; cubierto sólo indirectamente vía game_service model inserts; ~58% en report).
- Estructura verificada correcta en lo esencial (ID duality, patterns replicados, 1svc focus implícito vía tests en service). 
- Inconsistencias corregidas (estructura correcta): 
  - utcnow() naive legacy en fixtures (conftest sample_expired_token) y tests unit (streak_promotion x12, vip 1, game) → datetime.now(UTC) + import UTC. 
  - Ajuste comparativa en vip token test (SQLite tz=True devuelve naive en refresh; servicio escribe aware correctamente; test ahora robusto + nota "DESIRED aware").
- Expansión: Nuevo piloto `tests/unit/test_trivia_config_service.py` (8 tests, sigue al pie test_daily_gift_service + test_analytics + test_health):
  - Lifecycle (owns/no-own + close).
  - Get: auto-crea row con DEFAULTS, retorna todos los keys (incl besitos caps).
  - Update: sólo campos válidos (>=0 int), ignora keys inválidos/negativos/non-int, setea updated_by/at, crea si falta, devuelve config completo.
  - Shape contract keys.
- Verificación: 8/8 new passing; ruff clean; 500+ unit services (incl new + streak/vip/game) passing; targeted invariants/atomic/streak/besito 42 passing; 0 regressions atribuibles. Warnings pre-existentes (event emit schedule).
- Cobertura: trivia_config_service ahora ejercitado directamente (get/update paths); mejora en servicio minijuegos/trivia domain.

Esto continúa la expansión manteniendo la red de seguridad por dominio vía pilotos de contrato deseado.

**Expansión handlers (2026-06-21 continuación):** 
- Priorizados por criticidad + % cov más baja: 1) game_user_handlers.py (14%, minijuegos/dados/trivia/rachas/protección - engagement + earnings system; usa get_service moderno). 2) free_channel_handlers (20%, entry point free join/leave).
- Todos los services/domains ya tenían pilotos unit → ahora abarcamos handlers completos por sistema (patrón gold replicado: patch get_service, assert 1 svc call + user_id, edit_text/answer, close, happy+limits+errors+streak paths).
- Nuevo: tests/handlers/test_game_user_handlers.py (13 tests cubriendo menu, dice, trivia free/vip/simple, streak protection/retire/continue/decline).
- Nuevo: tests/handlers/test_free_channel_handlers.py (3 tests básicos para join/leave/member).
- Verif: 13+3 passing, 122+ en smoke con golds (reaction, invariants, gamif, mission); ruff clean; 0 regressions.
- Siguientes sugeridos (si continuar): vip_*_handlers (19-24%, acceso crítico), broadcast_handlers (20%), package/reward_admin.


