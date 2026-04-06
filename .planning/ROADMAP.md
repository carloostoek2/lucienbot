# Roadmap: Lucien Bot

**Created:** 2026-03-30
**Phases completed:** 8 of 11
**Milestone:** v1.0 — Core bot functionality

## Summary

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Bot Base | Bot funcional con arquitectura handlers/services/models | ADMIN-01 | Bot responde, capas separadas, comandos basicos |
| 2 | Canales | Canal Free con aprobacion + Canal VIP con acceso | CHAN-01, CHAN-02, CHAN-03, CHAN-04 | Usuarios acceden a canales segun flujo esperado |
| 3 | Suscripciones VIP | Tokens, tarifas, suscripciones, expiracion | VIP-01, VIP-02, VIP-03, VIP-04, VIP-05, VIP-06, ADMIN-02 | Flujo completo VIP funcional |
| 4 | Gamificacion | Besitos, hugs, gifts, balance, top | BESI-01, BESI-02, BESI-03, BESI-04 | Sistema de besitos activo y balance correcto |
| 5 | Misiones | Misiones, progreso, recompensas | MISS-01, MISS-02, MISS-03, MISS-04, ADMIN-03 | Visitantes completan misiones y reciben recompensas |
| 6 | Tienda + Promociones + Narrativa | Compra de paquetes, codigos, historias interactivas | STOR-01-04, PROM-01-03, NARR-01-04, ADMIN-04, ADMIN-05 | Store, promociones y narrativa funcionando |
| 7 | **VIP Invite Links Dinamicos** ✓ | Links de invitacion de un solo uso para canal VIP | VIP-07 | Un token = un link de un solo uso generado dinamicamente |
| 07.1 | **Integrar Alembic** ✓ | Sistema de migraciones Alembic reemplazar create_all() | Complete    | 2026-03-30 |
| 8 | Testing & Technical Debt | Tests, linting, manejo de sessiones, refactor handlers | TEST-01, TEST-02, TEST-03, SCHED-02, SEC-03 | Cobertura de tests y codigo mas mantenible |
| 9 | Polish & Hardening | Rate limiting, FSM persistente, backups, analytics | Complete    | 2026-03-31 |
| 12 | Mejorar tienda | 5/5 | Complete    | 2026-04-05 |
| 13 | El Mapa del Deseo | 3/3 | Complete    | 2026-04-05 |
| 14 | Minijuegos | Sistema de dados y trivia para ganar besitos | Complete    | 2026-04-06 |

## Phase Details

### Phase 1: Bot Base ✓
**Goal:** Bot funcional con arquitectura handlers/services/models y panel de administracion
**Requirements:** ADMIN-01
**Status:** Complete (inferred from codebase — pre-git history)
**Success criteria:**
1. Bot responde a comandos `/start`, `/help`
2. Arquitectura handlers → services → models respetada
3. Panel de Custodios accesible
4. Logger configurado

### Phase 2: Canales ✓
**Goal:** Canal Free con aprobacion automatica y canal VIP con acceso controlado
**Requirements:** CHAN-01, CHAN-02, CHAN-03, CHAN-04
**Status:** Complete (Fase 2 en git history)
**Success criteria:**
1. Usuario puede solicitar unirse al canal Free
2. Aprobacion automatica tras wait_time_minutes
3. Canal VIP solo accesible para suscriptores activos
4. Mensajes de bienvenida personalizados enviados

### Phase 3: Suscripciones VIP ✓
**Goal:** Sistema completo de tokens, tarifas, suscripciones y expiracion automatica
**Requirements:** VIP-01, VIP-02, VIP-03, VIP-04, VIP-05, VIP-06, ADMIN-02
**Status:** Complete (Fase 3 en git history)
**Success criteria:**
1. Custodio crea tarifas con precio y duracion
2. Custodio genera tokens unicos por tarifa
3. Visitante canjea token y obtiene acceso VIP
4. Tokens rechazados si ya usados o invalidos
5. Suscripcion expira y bot remueve usuario del canal
6. Recordatorio enviado 24h antes de expiracion

### Phase 4: Gamificacion ✓
**Goal:** Sistema de besitos, hugs, gifts diarios y balance consultable
**Requirements:** BESI-01, BESI-02, BESI-03, BESI-04
**Status:** Complete (Fase 4 en git history)
**Success criteria:**
1. Visitante da besitos a otros usuarios
2. Hugs y gifts disponibles con limite diario
3. Balance de besitos visible por comando
4. Top 10 de usuarios mas generosos mostrable

### Phase 5: Misiones ✓
**Goal:** Sistema de misiones con progreso, recompensas y panel de gestion
**Requirements:** MISS-01, MISS-02, MISS-03, MISS-04, ADMIN-03
**Status:** Complete (Fase 5 en git history)
**Success criteria:**
1. Misiones diarias y unicas disponibles
2. Progreso visible en tiempo real
3. Recompensas entregadas automaticamente al completar
4. Custodio puede crear, editar y gestionar misiones

### Phase 6: Tienda + Promociones + Narrativa ✓
**Goal:** Tienda de paquetes, codigos promocionales y sistema de narrativa interactiva
**Requirements:** STOR-01-04, PROM-01-03, NARR-01-04, ADMIN-04, ADMIN-05
**Status:** Complete (Fase 6 en git history)
**Success criteria:**
1. Paquetes de besitos comprables con distintos precios
2. Compra valida saldo y entrega contenido
3. Codigos promocionales con limite y descuento funcional
4. Historias interactivas con nodos, arquetipos y opciones
5. Custodio gestiona tienda, promociones y narrativa

### Phase 7: VIP Invite Links Dinamicos ✓
**Goal:** Reemplazar links de invitacion estaticos por links de un solo uso generados dinamicamente
**Requirements:** VIP-07
**Status:** Complete (d66b8b7)
**Success criteria:**
1. Al canjear token VIP se genera invite link con member_limit=1
2. Link expires tras primer uso (un solo usuario por token)
3. Fallback a link estatico si la API de Telegram falla
4. Campo invite_link en modelo Channel populado con link default
5. Invites sin usar no generan conflictos (cada token = link unico)

### Phase 07.1: Integrar completamente sistema de migraciones alembic ✓

**Goal:** Replace `Base.metadata.create_all()` startup schema creation with proper Alembic migration system
**Requirements**: Alembic integration
**Depends on:** Phase 7
**Status:** Complete (07.1-01 committed: 3 commits)
**Success criteria:**
1. `alembic.ini` and `alembic/` directory configured with `env.py` pointing to `models.database.Base`
2. Baseline migration capturing all 32 existing tables + sync migration for schema drift
3. SQLite dev DB stamped to HEAD (c25b0020dcc5 -> 53f8f3496f23)
4. `alembic==1.12.1` in `requirements.txt`
5. `init_db()` in `models/database.py` updated to DEPRECATED no-op
6. Standalone migration archived to `migrations/archive/`
7. `railway.toml` updated to run `alembic upgrade head && python bot.py`
8. `migrations/README.txt` created

**Deviation:** 2 revisions generated instead of 1 (DB had 3 missing columns/constraints from models)

### Phase 8: Testing & Technical Debt
**Goal:** Tests automatizados, configuracion de linting y refactor de deuda tecnica
**Requirements:** TEST-01, TEST-02, TEST-03, SCHED-02, SEC-03
**Status:** Pending
**Success criteria:**
1. Tests unitarios para VIPService, ChannelService, BesitoService, MissionService
2. Tests de integracion para flujos VIP y canales
3. Configuracion de ruff/black/isort integrada
4. Sesiones DB con context managers (eliminar __del__)
5. Startup check para suscripciones expiradas
6. SELECT FOR UPDATE en token redemption (resolver race condition)

### Phase 9: Polish & Hardening
**Goal:** Rate limiting, FSM persistente, backups y analytics
**Requirements:** SEC-01, SEC-02, BACK-01, SCHED-01, ANLY-01, ANLY-02
**Status:** Complete (5/5 plans done)
**Plans:** 5/5 plans complete
Plans:
- [x] 09-01-PLAN.md -- Rate limiting via ThrottlingMiddleware (SEC-01) ✓
- [x] 09-02-PLAN.md -- FSM persistence via RedisStorage factory (SEC-02) ✓
- [x] 09-03-PLAN.md -- Database backup service with pg_dump/sqlite3 (BACK-01) ✓
- [x] 09-04-PLAN.md -- APScheduler persistent job queue replacing polling (SCHED-01) ✓
- [x] 09-05-PLAN.md -- Analytics dashboard + CSV export commands (ANLY-01, ANLY-02) ✓
**Success criteria:**
1. Rate limiting por usuario en handlers principales
2. FSM con RedisStorage (estado persiste en reinicios)
3. Backup automatico de base de datos (diario)
4. Job queue persistente取代 polling fijo
5. Dashboard de metricas para Custodios
6. Exportacion de datos de actividad

### Phase 10: Flujos de entrada @docs/req_fase10.md

**Goal:** Implement ritualized entry flows for Free and VIP channels
**Requirements**: FREE-01, VIP-01, SCHED-01
**Depends on:** Phase 9
**Status:** ✓ Complete (2026-03-31)
**Plans:** 4/4 plans complete

Plans:
- [x] 10-01: Foundation — DB columns, LucienVoice, keyboards ✓
- [x] 10-02: Free channel — 30s delay, impatience, approval loop ✓
- [x] 10-03: VIP entry — 3-phase ritual, callbacks, state management ✓
- [x] 10-04: Tests — VIP entry state, scheduler triggers, regression ✓

**Success criteria:**
1. Free channel: 30-second delayed ritual welcome with social links
2. Free channel: Impatience message on repeated requests
3. Free channel: Ritual welcome + invite link on approval
4. VIP channel: 3-phase ritual on token redemption (confirm → align → deliver)
5. VIP channel: Resumable flow if user abandons and returns
6. VIP channel: Expired subscription guard cancels flow
7. All new code covered by unit tests

### Phase 11: Critical Services Test Coverage + E2E Tests

**Goal:** Expand test coverage to all remaining business logic services, fix race conditions, and validate E2E entry flows
**Requirements:** REQ-11-01, REQ-11-02, REQ-11-03, REQ-11-04, REQ-11-05, REQ-11-06, REQ-11-07, REQ-11-08, REQ-11-09, REQ-11-10, REQ-11-11, REQ-11-12, REQ-11-13, REQ-11-14
**Depends on:** Phase 10
**Status:** In Progress
**Plans:** 7/7 plans complete

Plans:
- [x] 11-01: Wave 0 — Test infrastructure: fixtures, e2e marker, stub files
- [x] 11-02: StoreService — Unit tests + race condition fix (SELECT FOR UPDATE)
- [x] 11-03: PromotionService + BroadcastService — Unit tests + race condition fixes
- [x] 11-04: PackageService + RewardService + DailyGiftService — Unit tests
- [x] 11-05: UserService + AnalyticsService + StoryService — Unit tests
- [ ] 11-06: Free entry + VIP ritual — E2E integration tests with mocked bot
- [ ] 11-07: LucienVoice + cross-service atomicity — E2E audit + integration tests

**Success criteria:**
1. StoreService: full unit coverage + race condition fixed
2. PromotionService + BroadcastService: full unit coverage + race conditions fixed
3. PackageService + RewardService + DailyGiftService: full unit coverage
4. UserService + AnalyticsService + StoryService: full unit coverage
5. Free channel entry flow and VIP 3-phase ritual covered by E2E tests
6. LucienVoice consistency validated (no hardcoded strings in services)
7. Cross-service atomicity patterns verified
8. Full test suite passes with coverage >= 70%

### Phase 12: Mejorar tienda

**Goal:** Mejoras al sistema de tienda: gestión de fotos de paquetes, organización por categorías, y flujo de compra optimizado
**Requirements:** STOR-05, STOR-06, STOR-07
**Depends on:** Phase 11
**Status:** ✓ Complete
**Plans:** 5/5 plans complete

### Phase 13: El Mapa del Deseo - Promociones VIP Exclusivas

**Goal:** Sistema de promociones exclusivas dentro de El Diván con 3 niveles: Premium, Círculo Íntimo y El Secreto
**Requirements:** PROM-04, VIP-08
**Depends on:** Phase 12
**Status:** ✓ Complete
**Plans:** 3/3 plans complete

**Success criteria:**
1. Usuario VIP ve botón "🗺️ El Mapa del Deseo" en El Diván ✓
2. Ve 3 promociones exclusivas con descripciones completas ✓
3. Flujo "Me Interesa" funciona y notifica a admins ✓
4. Promociones VIP no aparecen en catálogo general ✓
5. Solo VIPs pueden acceder (no-VIPs redirigidos) ✓

**Success criteria:**
1. Admin puede eliminar fotos de paquetes existentes ✓ (Already completed in quick task 260404-vjx)
2. Paquetes organizados por categorías/tipos
3. Flujo de compra más intuitivo con preview de contenido
4. Búsqueda y filtrado de paquetes en tienda
5. Mejor gestión de stock (alertas de bajo stock)

**Plans:**
- [x] 12-01-PLAN.md — Category System Foundation: models, migrations, PackageService methods (STOR-05) ✓
- [x] 12-02-PLAN.md — Admin Category Management: handlers for CRUD and package assignment (STOR-05) ✓
- [x] 12-03-PLAN.md — User Store with Categories: category browsing, product detail with preview (STOR-05, STOR-06)
- [x] 12-04-PLAN.md — Stock Alerts and Management: thresholds, visual indicators, admin notifications (STOR-07)
- [x] 12-05-PLAN.md — Search and Filter: search by name, filter by price/availability (STOR-05, STOR-06)

### Phase 14: Minijuegos

**Goal:** Sistema de minijuegos (dados y trivia) para que usuarios ganen besitos
**Requirements:** GAME-01, GAME-02, GAME-03
**Depends on:** Phase 13
**Status:** Pending
**Plans:** 1/1 plans complete

**Plans:**
- [x] 14-01-PLAN.md — Game Service + TransactionSource.GAME: lógica de minijuegos (dados, trivia) ✓ (plan created)
- [ ] 14-02-PLAN.md — Game Handlers: menú, dados con animación, trivia con botones inline (plan created)

**Success criteria:**
1. Dados: usuario lanza 2 dados, gana si son pares (ambos pares diferentes) o dobles (iguales)
2. Dados: animación visual de lanzamiento
3. Trivia: pregunta aleatoria de docs/preguntas.json con 4 opciones
4. Victoria: +1 besito con mensaje de celebración
5. Botón de minijuegos en menú principal

---

*Roadmap created: 2026-03-30 from codebase analysis and git history*
*Updated: 2026-04-06 — Phase 14 Minijuegos added*