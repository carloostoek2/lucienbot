# Requirements: Lucien Bot

**Defined:** 2026-03-30
**Core Value:** Crear una experiencia premium y gamificada que incentiva el compromiso de la comunidad con Diana a través de un sistema de recompensas, acceso exclusivo VIP y narrativa inmersiva.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### VIP Subscriptions

- [ ] **VIP-01**: Custodios pueden crear y editar tarifas VIP con precio y duración
- [ ] **VIP-02**: Custodios pueden generar tokens de acceso único para cada tarifa
- [ ] **VIP-03**: Visitantes pueden canjear tokens para activar suscripción VIP
- [ ] **VIP-04**: Sistema detecta y rechaza tokens ya utilizados o expirados
- [ ] **VIP-05**: Suscripciones expiran automáticamente y el bot remueve al usuario del canal VIP
- [ ] **VIP-06**: Recordatorio enviado 24h antes de expiración de suscripción
- [x] **VIP-07**: Links de invitación dinámicos de un solo uso para acceso VIP ✓ — [d66b8b7]

### Channel Management

- [ ] **CHAN-01**: Canal Free con tiempo de espera configurable antes de aprobación
- [ ] **CHAN-02**: Aprobación automática de solicitudes pendientes según schedule
- [ ] **CHAN-03**: Canal VIP accesible solo para suscriptores activos
- [ ] **CHAN-04**: Mensajes de bienvenida personalizados por canal

### Gamification

- [ ] **BESI-01**: Visitantes pueden dar besitos a otros usuarios
- [ ] **BESI-02**: Sistema de hugs y gifts diarios con límites temporales
- [ ] **BESI-03**: Balance de besitos visible y consultable por usuario
- [ ] **BESI-04**: Top 10 de usuarios más generosos visible

### Missions

- [ ] **MISS-01**: Misiones diarias/únicas con objetivo específico
- [ ] **MISS-02**: Progreso de misión visible en tiempo real
- [ ] **MISS-03**: Recompensas automáticas al completar misión
- [ ] **MISS-04**: Registro de recompensas pendientes y reclamadas

### Store

- [ ] **STOR-01**: Paquetes de besitos con diferentes precios y cantidades
- [ ] **STOR-02**: Compra de paquetes con validación de saldo
- [ ] **STOR-03**: Entrega de contenido tras confirmación de compra
- [ ] **STOR-04**: Historial de compras del visitante

### Promotions

- [ ] **PROM-01**: Custodios pueden crear códigos promocionales con descuento y límite de uso
- [ ] **PROM-02**: Visitantes pueden aplicar códigos promocionales en compras
- [ ] **PROM-03**: Validación de código: existencia, límite de usos, expiración

### Narrative

- [ ] **NARR-01**: Sistema de historias interactivas con nodos y opciones
- [ ] **NARR-02**: Arquetipos de personajes (guardián, tentador, etc.) con rasgos específicos
- [ ] **NARR-03**: Elecciones del visitante afectan el desarrollo de la narrativa
- [ ] **NARR-04**: Sistema de logros vinculados a decisiones narrativas

### Admin Panel

- [ ] **ADMIN-01**: Menú principal de administración para Custodios
- [ ] **ADMIN-02**: Gestión completa de canales (crear, editar, activar/desactivar)
- [ ] **ADMIN-03**: Gestión de misiones y recompensas
- [ ] **ADMIN-04**: Gestión de tienda y paquetes
- [ ] **ADMIN-05**: Gestión de promociones y códigos

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Testing & Quality

- **TEST-01**: Suite de tests unitarios para services
- **TEST-02**: Tests de integración para handlers
- **TEST-03**: Cobertura mínima del 70% en lógica de negocio

### Infrastructure

- [x] **BACK-01**: Sistema de backup automático de base de datos
- **BACK-02**: Restauración desde backup funcional
- **SCHED-01**: Job queue persistente para scheduler (取代 polling 30s)
- **SCHED-02**: Verificación de suscripciones expiradas al iniciar bot

### Security & Hardening

- **SEC-01**: Rate limiting por usuario en handlers principales
- **SEC-02**: FSM persistente (RedisStorage) para no perder estado en reinicios
- **SEC-03**: Resolución de race condition en token redemption (SELECT FOR UPDATE)

### Analytics

- **ANLY-01**: Dashboard de métricas para Custodios
- **ANLY-02**: Exportación de datos de usuarios y actividad

### Experience

- **I18N-01**: Framework de internacionalización (español + inglés)
- **I18N-02**: Cambio de idioma por usuario
- **APP-01**: API REST para integración con frontend/web
- **APP-02**: Panel web para visitants (ver balance, misiones, historial)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| App móvil nativa | El bot Telegram es la plataforma principal |
| Multi-idioma | Solo español, comunidad hispanohablante |
| Copias de seguridad automáticas | Backup manual por ahora, Railway tiene snapshots |
| Webhooks en lugar de polling | Long polling es suficiente para la escala actual |
| Horizontal scaling | Una instancia es suficiente para la base de usuarios actual |
| OAuth / login externo | Autenticación via Telegram es suficiente |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VIP-01 through VIP-06 | Phase 3 | Complete |
| VIP-07 (invite links dinámicos) | Phase 7 | Complete |
| CHAN-01 through CHAN-04 | Phase 2 | Complete |
| BESI-01 through BESI-04 | Phase 4 | Complete |
| MISS-01 through MISS-04 | Phase 5 | Complete |
| STOR-01 through STOR-04 | Phase 6 | Complete |
| PROM-01 through PROM-03 | Phase 6 | Complete |
| NARR-01 through NARR-04 | Phase 6 | Complete |
| ADMIN-01 through ADMIN-05 | Phases 3-6 | Complete |

**Coverage:**
- v1 requirements: 32 total (32 complete, 0 pending)
- Mapped to phases: 32
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 after Phase 7 completion (VIP-07)*
