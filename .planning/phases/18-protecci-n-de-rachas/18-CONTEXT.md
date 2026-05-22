# Phase 18: Protección de Rachas - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning
**Source:** PRD Express Path (docs/SPEC_proteccion_de_racha.md)

<domain>
## Phase Boundary

Sistema de protección de rachas y modo arriesgo para el sistema de trivias con promociones (Phase 17). Extiende `StreakPromotionService` para que los usuarios puedan: (1) comprar protección de racha con besitos cuando fallen una pregunta, (2) elegir entre retirarse y conservar sus códigos o continuar por un código mayor arriesgando perderlo todo.

**Lo nuevo:**
- Modelo `StreakSession` que rastrea el ciclo de vida de una sesión de trivia promo
- Nuevo estado `CANCELLED` en `StreakPromotionCodeStatus`
- Lógica de protección: costo en besitos, 1 uso por sesión, fallback a trivia libre si no alcanzan besitos
- Modo arriesgo: FSM state para elegir retirarse/continuar tras alcanzar un tier
- Timeout de 2 minutos: si el usuario no regresa tras fallar y no tener besitos, pierde streak y códigos

**Lo que NO cambia:**
- Los modelos `StreakPromotion`, `StreakPromotionLevel`, `StreakPromotionRedemption` existentes — solo se extienden
- `StreakPromotionCode` — se agrega `session_id` FK y estado `CANCELLED`
- `claim_for_streak()` — se modifica para registrar códigos en la sesión activa
- La lógica de generación de códigos upfront (Phase 17) no se toca
- Los handlers de trivia existentes se extienden, no se reemplazan

**Dependencia:** Phase 17 (el sistema de promociones por racha ya está implementado y funcional)

</domain>

<decisions>
## Implementation Decisions

### Estados de Código
- **D-01:** Agregar `CANCELLED` al enum `StreakPromotionCodeStatus`. Valor: `"cancelled"`. Los códigos CANCELLED son aquellos que el usuario perdió tras fallar en modo arriesgo o timeout.
- **D-02:** Los códigos NUNCA se marcan como USED al entregarse. Solo el admin los marca USED manualmente. Esto ya existe en Phase 17 y se mantiene.

### Modelo StreakSession
- **D-03:** Nuevo modelo `StreakSession` con campos: id (UUID PK), user_id (int), promotion_id (int FK), is_in_risk_mode (bool), protection_used (bool), codes_delivered (JSON list de code_ids), started_at (datetime), expires_at (datetime para timeout de 2 min).
- **D-04:** Relación 1:N: un `StreakSession` puede tener múltiples `StreakPromotionCode` (via `session_id` FK en `StreakPromotionCode`).

### Protección
- **D-05:** Costo de protección: fórmula 5 + (streak // 3) * 5 besitos. Ej: streak 0-2 → 5, streak 3-5 → 10, streak 6-8 → 15.
- **D-06:** Protección disponible desde la primera pregunta. Se ofrece al fallar una respuesta.
- **D-07:** Si el usuario tiene protección disponible y besitos suficientes, puede comprarla. Se debitan los besitos, `protection_used = True`, y el streak continúa.
- **D-08:** Si ya usó la protección (protection_used = True) y vuelve a fallar: pierde el streak a 0, TODOS los códigos DELIVERED de esa sesión se marcan CANCELLED.
- **D-09:** Si falla y no tiene besitos suficientes para proteger: se le ofrece ir a trivia libre para ganar besitos. Timeout de 2 minutos.

### Modo Arriesgo
- **D-10:** Cuando el usuario alcanza un tier (claim_for_streak entrega un código), se activa FSM state con dos opciones: "Continuar por X%" (siguiente nivel) o "Retirarse con Y%" (conservar códigos actuales).
- **D-11:** Si elige retirarse: los códigos quedan en DELIVERED, la sesión se cierra, el admin los ve en el panel.
- **D-12:** Si elige continuar: entra en modo arriesgo (`is_in_risk_mode = True`). Si falla una pregunta en este modo, TODOS los códigos de la sesión se marcan CANCELLED.

### Timeout de 2 Minutos
- **D-13:** Si el usuario falla, no tiene besitos para proteger, y no tiene protección disponible, se le da timeout de 2 minutos para ganar besitos en trivia libre y volver.
- **D-14:** Si no regresa en 2 minutos: streak y códigos se pierden (CANCELLED).
- **D-15:** El timeout se implementa con `expires_at` en `StreakSession` y se verifica al reingresar.

### Handlers y FSM States
- **D-16:** Se necesitan 6 handlers/callbacks nuevos: game_trivia_promo (entry point), trivia_promo_answer (procesa respuestas con lógica de protección), waiting_retire_choice (FSM state para retirarse/continuar), trivia_promo_accept_protection, trivia_promo_decline_protection, trivia_promo_timeout.
- **D-17:** Estos handlers extienden el flujo de trivia existente, no lo reemplazan. El entry point normal de trivia sigue funcionando igual.

### Claude's Discretion
- Diseño exacto de los mensajes de Lucien para ofrecer protección, retirarse/continuar, timeout
- Formato de teclados inline para las opciones (proteger/no proteger, continuar/retirarse)
- Estrategia de limpieza de sesiones expiradas (scheduler job o lazy cleanup)
- Si la trivia libre durante el timeout debe tener algún límite especial
- Implementación exacta del timeout (job programado vs verificación lazy en cada interacción)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Modelos existentes (a extender)
- `models/models.py:1138-1143` — `StreakPromotionCodeStatus` enum (AVAILABLE, DELIVERED, USED)
- `models/models.py:1194-1207` — `StreakPromotionCode` model (agregar session_id FK)
- `models/models.py:1210-1220` — `StreakPromotionRedemption` model

### Servicio existente (a extender)
- `services/streak_promotion_service.py:192-222` — `claim_for_streak()` — entrega códigos al alcanzar racha
- `services/streak_promotion_service.py` completo — `StreakPromotionService` con get_active_promotions, activate, deactivate

### GameService (a extender)
- `services/game_service.py:750-780` — Llamada a `claim_for_streak` después de respuesta correcta en trivia
- `services/game_service.py:1050-1075` — Patrón de registro de jugada + claim

### Arquitectura y reglas
- `CLAUDE.md` — Reglas de proyecto: handlers/services/models, 50 líneas máximo, voz de Lucien
- `@architecture.md` — Separación de capas, handlers solo enrutan
- `@rules.md` — Naming: verbo + contexto + resultado, logging
- `models/CLAUDE.md` — Reglas de migraciones Alembic, patrón Enum-First para agregar CANCELLED

### Rama de referencia
- `resp_trivia_multiniveles` — intento previo con FSM states `waiting_streak_choice` y `streak_continue`. Issues encontrados: get_all_promotions roto, handler callbacks rotos, validación de max_codes fallaba. Revisar para no repetir errores.

</canonical_refs>

<specifics>
## Specific Ideas

- Formato de protección: el usuario falla → Lucien ofrece protección con costo calculado → teclado inline [Proteger (-X besitos)] [No proteger]
- Formato de arriesgo: el usuario alcanza tier → Lucien muestra código ganado → teclado inline [Continuar por Z%] [Retirarse con Y%]
- Formato de timeout: "Lucien te da 2 minutos para conseguir besitos en trivia libre. Usa /trivia para jugar."
- Ejemplo completo del flujo: User con streak=0 → P1-P5 correctas → TIER 1 (50%) → elige Continuar → P6-P10 correctas → TIER 2 (75%) → elige Continuar → P11-P13 → FALLA en P13 → protection_used=True → códigos CANCELLED, streak=0
- Si en P7 falla y protection_available=True → ofrece proteger por 12 besitos → si acepta: debita 12, protection_used=True, streak sigue en 7 → continúa P8
- Los códigos se generan upfront (Phase 17), esta fase solo gestiona su ciclo de vida post-generación

</specifics>

<deferred>
## Deferred Ideas

None — PRD covers complete phase scope.

</deferred>

---

*Phase: 18-protecci-n-de-rachas*
*Context gathered: 2026-05-22 via PRD Express Path*
