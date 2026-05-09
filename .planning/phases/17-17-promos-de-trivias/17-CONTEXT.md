# Phase 17: Promociones por Racha - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning
**Source:** PRD Express Path (docs/SPEC_fase_17.md)

<domain>
## Phase Boundary

Sistema independiente de promociones por racha para trivias. El administrador podrá crear y configurar promociones que otorgan códigos de descuento cuando un usuario alcanza una racha específica de preguntas consecutivas correctas.

**Lo nuevo:**
- Modelo `StreakPromotion` con niveles configurables (cantidad ilimitada)
- Cada nivel define: preguntas consecutivas requeridas, porcentaje de descuento, códigos disponibles
- Duración configurable: fechas concretas (inicio/fin) o duración relativa (horas/días desde activación)
- Asociación con un set de preguntas temáticas (categoría de trivia)
- Generación de códigos de descuento únicos
- Panel de administración para crear, configurar y gestionar estas promociones
- Historial de rachas y códigos canjeados por usuario

**Lo que NO cambia:**
- El sistema de trivias existente (GameService, GameRecord, TriviaCategory) — solo se conecta para leer rachas
- Las promociones comerciales existentes (`Promotion`, `PromotionInterest`, `PromotionService`) — no se tocan
- Los límites diarios de trivia
- El sistema de besitos

**Independencia total:** Estas promociones NO tienen relación con el modelo `Promotion` existente ni con `PromotionService`. Son una entidad separada con sus propios modelos, servicio y handlers.

</domain>

<decisions>
## Implementation Decisions

### Modelo de Datos
- **D-01:** Nuevo modelo `StreakPromotion` independiente del modelo `Promotion` existente. Tabla propia con: nombre, duración (fechas o relativa), set de preguntas asociado.
- **D-02:** Nuevo modelo `StreakPromotionLevel` relacionado 1:N con `StreakPromotion`. Cada nivel define: preguntas_consecutivas_requeridas (int), porcentaje_descuento (int), códigos_disponibles (int).
- **D-03:** Nuevo modelo `StreakPromotionCode` para códigos de descuento generados. Cada código es único y tiene estado (disponible/entregado/usado).
- **D-04:** Nuevo modelo `StreakPromotionRedemption` para historial de canjeos por usuario: código entregado, racha alcanzada, fecha, estado del código.

### Duración
- **D-05:** Dos modos de vigencia: fechas concretas (start_date, end_date con hora) O duración relativa (horas o días desde activación).
- **D-06:** Una promoción solo está activa durante su vigencia. Fuera de vigencia no se evalúan rachas ni se entregan códigos.

### Asociación con Trivia
- **D-07:** Cada `StreakPromotion` se asocia a un `category_id` de `TriviaCategory` (o `null` para el mazo general).
- **D-08:** El set de preguntas asociado se activa únicamente durante la duración de la promoción.
- **D-09:** Fuera del período de la promoción, el sistema vuelve automáticamente al paquete de preguntas por defecto.

### Códigos de Descuento
- **D-10:** Los códigos se generan al crear la promoción (no al alcanzar la racha). Todos los códigos para todos los niveles se generan upfront.
- **D-11:** Cada código es único a nivel sistema (no solo dentro de una promoción).
- **D-12:** Los códigos no se descuentan automáticamente al entregarse — solo cuando el administrador marca un código como "usado" se descuenta del total configurado.
- **D-13:** El conteo de "códigos disponibles" mostrado al admin refleja: total_configurado - códigos_entregados.

### Rachas y Entrega
- **D-14:** Cuando un usuario alcanza una racha que coincide con un nivel de una promoción activa, se le notifica y se le asigna un código de descuento.
- **D-15:** Un usuario solo puede recibir un código por nivel de promoción (no se entregan múltiples códigos del mismo nivel al mismo usuario).
- **D-16:** El historial de rachas y códigos canjeados se registra para evitar duplicidades y abusos.

### Claude's Discretion
- Formato de los códigos de descuento (longitud, caracteres, prefijo)
- Diseño exacto de la UI del panel de administración para gestión de estas promociones
- Cómo se notifica al usuario que alcanzó una racha y recibió un código
- Si el código se entrega como mensaje automático o el admin lo revisa primero
- Integración con el scheduler para activación/desactivación automática por fechas

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Trivia existente
- `services/game_service.py` — GameService: rachas (`_get_trivia_streak`), `TriviaCategory`, límites diarios
- `models/models.py` — `GameRecord` (game_type, user_id, payout, played_at), `TriviaCategory`
- `handlers/game_user_handlers.py` — Handlers de trivia con callback data

### Promociones existentes (solo como referencia de patrón — NO modificar)
- `services/promotion_service.py` — Patrón de servicio para gestionar entidades promocionales
- `models/models.py:715-834` — Patrón de modelos `Promotion`, `PromotionInterest` (solo referencia estructural)

### Panel de administración
- `handlers/admin_handlers.py` — Patrón de handlers admin: `is_admin()`, `F.data`, `lambda cb: is_admin(cb.from_user.id)`
- `keyboards/inline_keyboards.py` — Patrón de teclados inline y menú admin

### Arquitectura y reglas
- `CLAUDE.md` — Reglas de proyecto: handlers/services/models, 50 líneas máximo
- `@architecture.md` — Separación de capas
- `@rules.md` — Naming: verbo + contexto + resultado, logging
- `models/CLAUDE.md` — Reglas de migraciones Alembic, patrón Enum-First

</canonical_refs>

<specifics>
## Specific Ideas

- La promoción se comporta como un "evento" temporal: durante su vigencia, el set de preguntas asociado está activo, y las rachas de los usuarios se evalúan contra los niveles configurados
- El admin configura: nombre → niveles (ilimitados, con campos: racha requerida, % descuento, códigos disponibles) → duración → set de preguntas
- Ejemplo de 4 niveles: racha 5 = 30% (20 códigos), racha 10 = 50% (10 códigos), racha 15 = 70% (5 códigos), racha 20 = 90% (2 códigos)
- Los códigos son para descuentos en productos/servicios externos al bot (no en la tienda de besitos)

</specifics>

<deferred>
## Deferred Ideas

None — PRD covers complete phase scope.

</deferred>

---

*Phase: 17-promos-de-trivias*
*Context gathered: 2026-05-09 via PRD Express Path*
