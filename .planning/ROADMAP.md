# Roadmap: Lucien Bot

**Created:** 2026-03-30
**Phases completed:** 8 of 10
**Milestone:** v1.0 — Core bot functionality

## Summary

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Bot Base | Bot funcional con arquitectura handlers/services/models | ADMIN-01 | Bot responde, capas separadas, comandos básicos |
| 2 | Canales | Canal Free con aprobación + Canal VIP con acceso | CHAN-01, CHAN-02, CHAN-03, CHAN-04 | Usuarios acceden a canales según flujo esperado |
| 3 | Suscripciones VIP | Tokens, tarifas, suscripciones, expiración | VIP-01, VIP-02, VIP-03, VIP-04, VIP-05, VIP-06, ADMIN-02 | Flujo completo VIP funcional |
| 4 | Gamificación | Besitos, hugs, gifts, balance, top | BESI-01, BESI-02, BESI-03, BESI-04 | Sistema de besitos activo y balance correcto |
| 5 | Misiones | Misiones, progreso, recompensas | MISS-01, MISS-02, MISS-03, MISS-04, ADMIN-03 | Visitantes completan misiones y reciben recompensas |
| 6 | Tienda + Promociones + Narrativa | Compra de paquetes, códigos, historias interactivas | STOR-01–04, PROM-01–03, NARR-01–04, ADMIN-04, ADMIN-05 | Store, promociones y narrativa funcionando |
| 7 | **VIP Invite Links Dinámicos** ✓ | Links de invitación de un solo uso para canal VIP | VIP-07 | Un token = un link de un solo uso generado dinámicamente |
| 07.1 | **Integrar Alembic** ✓ | Sistema de migraciones Alembic reemplazar create_all() | — | Alembic gestiona esquema, Railway ejecuta upgrade |
| 8 | Testing & Technical Debt | Tests, linting, manejo de sessiones, refactor handlers | TEST-01–03, SCHED-02, SEC-03 | Cobertura de tests y código más mantenible |
| 9 | Polish & Hardening | Rate limiting, FSM persistente, backups, analytics | SEC-01, SEC-02, BACK-01, SCHED-01, ANLY-01–02 | Bot listo para producción a escala |

## Phase Details

### Phase 1: Bot Base ✓
**Goal:** Bot funcional con arquitectura handlers/services/models y panel de administración
**Requirements:** ADMIN-01
**Status:** Complete (inferred from codebase — pre-git history)
**Success criteria:**
1. Bot responde a comandos `/start`, `/help`
2. Arquitectura handlers → services → models respetada
3. Panel de Custodios accesible
4. Logger configurado

### Phase 2: Canales ✓
**Goal:** Canal Free con aprobación automática y canal VIP con acceso controlado
**Requirements:** CHAN-01, CHAN-02, CHAN-03, CHAN-04
**Status:** Complete (Fase 2 en git history)
**Success criteria:**
1. Usuario puede solicitar unirse al canal Free
2. Aprobación automática tras wait_time_minutes
3. Canal VIP solo accesible para suscriptores activos
4. Mensajes de bienvenida personalizados enviados

### Phase 3: Suscripciones VIP ✓
**Goal:** Sistema completo de tokens, tarifas, suscripciones y expiración automática
**Requirements:** VIP-01, VIP-02, VIP-03, VIP-04, VIP-05, VIP-06, ADMIN-02
**Status:** Complete (Fase 3 en git history)
**Success criteria:**
1. Custodio crea tarifas con precio y duración
2. Custodio genera tokens únicos por tarifa
3. Visitante canjea token y obtiene acceso VIP
4. Tokens rechazados si ya usados o inválidos
5. Suscripción expira y bot remueve usuario del canal
6. Recordatorio enviado 24h antes de expiración

### Phase 4: Gamificación ✓
**Goal:** Sistema de besitos, hugs, gifts diarios y balance consultable
**Requirements:** BESI-01, BESI-02, BESI-03, BESI-04
**Status:** Complete (Fase 4 en git history)
**Success criteria:**
1. Visitante da besitos a otros usuarios
2. Hugs y gifts disponibles con límite diario
3. Balance de besitos visible por comando
4. Top 10 de usuarios más generosos mostrable

### Phase 5: Misiones ✓
**Goal:** Sistema de misiones con progreso, recompensas y panel de gestión
**Requirements:** MISS-01, MISS-02, MISS-03, MISS-04, ADMIN-03
**Status:** Complete (Fase 5 en git history)
**Success criteria:**
1. Misiones diarias y únicas disponibles
2. Progreso visible en tiempo real
3. Recompensas entregadas automáticamente al completar
4. Custodio puede crear, editar y gestionar misiones

### Phase 6: Tienda + Promociones + Narrativa ✓
**Goal:** Tienda de paquetes, códigos promocionales y sistema de narrativa interactiva
**Requirements:** STOR-01–04, PROM-01–03, NARR-01–04, ADMIN-04, ADMIN-05
**Status:** Complete (Fase 6 en git history)
**Success criteria:**
1. Paquetes de besitos comprables con distintos precios
2. Compra valida saldo y entrega contenido
3. Códigos promocionales con límite y descuento funcional
4. Historias interactivas con nodos, arquetipos y opciones
5. Custodio gestiona tienda, promociones y narrativa

### Phase 7: VIP Invite Links Dinámicos ✓
**Goal:** Reemplazar links de invitación estáticos por links de un solo uso generados dinámicamente
**Requirements:** VIP-07
**Status:** Complete (d66b8b7)
**Success criteria:**
1. Al canjear token VIP se genera invite link con member_limit=1
2. Link expires tras primer uso (un solo usuario por token)
3. Fallback a link estático si la API de Telegram falla
4. Campo invite_link en modelo Channel populado con link default
5. Invites sin usar no generan conflictos (cada token = link único)

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
**Goal:** Tests automatizados, configuración de linting y refactor de deuda técnica
**Requirements:** TEST-01, TEST-02, TEST-03, SCHED-02, SEC-03
**Status:** Pending
**Success criteria:**
1. Tests unitarios para VIPService, ChannelService, BesitoService, MissionService
2. Tests de integración para flujos VIP y canales
3. Configuración de ruff/black/isort integrada
4. Sesiones DB con context managers (eliminar __del__)
5. Startup check para suscripciones expiradas
6. SELECT FOR UPDATE en token redemption (resolver race condition)

### Phase 9: Polish & Hardening
**Goal:** Rate limiting, FSM persistente, backups y analytics
**Requirements:** SEC-01, SEC-02, BACK-01, SCHED-01, ANLY-01, ANLY-02
**Status:** Pending
**Success criteria:**
1. Rate limiting por usuario en handlers principales
2. FSM con RedisStorage (estado persiste en reinicios)
3. Backup automático de base de datos (diario)
4. Job queue persistente取代 polling fijo
5. Dashboard de métricas para Custodios
6. Exportación de datos de actividad

## Milestone Completion Criteria

- [ ] Phases 1-6: Todas las funcionalidades core validadas en producción
- [x] Phase 7: Invite links dinámicos deployados y funcionando
- [ ] Phase 8: Cobertura de tests ≥ 70%, deuda técnica reducida
- [ ] Phase 9: Bot hardened para producción a escala

---
*Roadmap created: 2026-03-30 from codebase analysis and git history*
