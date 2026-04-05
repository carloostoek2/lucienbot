# Verification Criteria: Phase 13 - El Mapa del Deseo

## Success Criteria

### Functional Requirements

- [ ] **REQ-13-01**: Usuario VIP ve botón "🗺️ El Mapa del Deseo" en El Diván
- [ ] **REQ-13-02**: Al entrar, ve las 3 promociones exclusivas listadas
- [ ] **REQ-13-03**: Cada promoción muestra: nombre, descripción completa, precio
- [ ] **REQ-13-04**: Botón "💕 Me Interesa" visible en cada promoción
- [ ] **REQ-13-05**: Flujo "Me Interesa" registra interés y notifica a admins
- [ ] **REQ-13-06**: Las promociones VIP NO aparecen en el catálogo general
- [ ] **REQ-13-07**: Solo usuarios VIP pueden ver estas promociones
- [ ] **REQ-13-08**: No-VIPs son redirigidos con mensaje de acceso denegado

### Technical Requirements

- [ ] **TECH-13-01**: Campo `is_vip_exclusive` existe en modelo Promotion
- [ ] **TECH-13-02**: Migración Alembic aplicada correctamente
- [ ] **TECH-13-03**: Método `get_vip_exclusive_promotions()` funciona
- [ ] **TECH-13-04**: Método `get_available_promotions()` excluye VIP exclusivas
- [ ] **TECH-13-05**: 3 promociones VIP creadas en BD con datos correctos

### Voz de Lucien

- [ ] **VOICE-13-01**: Mensajes en 3ra persona ("Lucien gestiona...")
- [ ] **VOICE-13-02**: Tono elegante y misterioso
- [ ] **VOICE-13-03**: "Diana" como figura central
- [ ] **VOICE-13-04**: "Visitantes" para usuarios

## Test Scenarios

### Scenario 1: VIP accede al Mapa del Deseo
1. Usuario VIP hace clic en "El Diván"
2. Ve botón "🗺️ El Mapa del Deseo"
3. Al hacer clic, ve las 3 promociones
4. Puede navegar entre ellas

### Scenario 2: No-VIP intenta acceder
1. Usuario no-VIP (o expirado) intenta acceder
2. Recibe mensaje de acceso denegado
3. Redirigido al menú principal

### Scenario 3: Flujo "Me Interesa"
1. VIP ve detalle de promoción
2. Clic en "Me Interesa"
3. Interés registrado en BD
4. Admins reciben notificación
5. Usuario ve confirmación

### Scenario 4: Promociones no aparecen en catálogo general
1. Usuario entra a "Ofertas" / "Gabinete de Oportunidades"
2. NO ve las promociones VIP exclusivas
3. Solo ve promociones generales

## Data Verification

Las 3 promociones deben existir con:

| Nombre | Precio MXN | is_vip_exclusive |
|--------|------------|------------------|
| ✨ Premium ✨ | 60000 | True |
| ❤️‍🔥 Círculo Íntimo ❤️‍🔥 | 95000 | True |
| 🔒 El Secreto 🔒 | 150000 | True |

## Files to Verify

- [ ] `models/models.py` - Campo agregado
- [ ] `migrations/versions/xxx_add_is_vip_exclusive_to_promotions.py` - Migración generada
- [ ] `services/promotion_service.py` - Nuevos métodos
- [ ] `handlers/vip_user_handlers.py` - Nuevos handlers y teclado
- [ ] `scripts/seed_vip_promotions.py` - Script de seed creado
