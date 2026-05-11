
───

📋 REQUERIMIENTO: Sistema de Trivia Promo con Apuesta y Protección

Contexto

El bot Lucien tiene un sistema de trivia con promociones por racha (Phase 17). Actualmente funciona así: el usuario alcanza un streak → gana un código de descuento. El sistema nuevo agregar protección comprable con besitos y modo arriesgo donde el usuario puede continuar jugando para ganar un código mayor pero con el riesgo de perder todo.

───

Reglas del Sistema

1. Ciclo de vida de códigos de descuento

| Estado    | Significado                                                     |
| --------- | --------------------------------------------------------------- |
| AVAILABLE | Generado al crear la promoción, disponible para entregar        |
| DELIVERED | Usuario alcanzó el streak y ganó el código                      |
| USED      | Admin lo marca manualmente cuando el usuario reclama en tienda  |
| CANCELLED | Usuario falló después de elegir "continuar" (perdió la apuesta) |

Nota: Los códigos NO se marcan como USED al entregarse. Solo cuando el admin lo hace manualmente. Esto es porque hay usuarios que juegan por jugar y nunca reclaman.

2. Protección (1 uso por sesión de promo)

• Se ofrece desde la primera pregunta
• Costo: fórmula 5 + (streak // 3) * 5 besitos (o configurable por tiers)
• Si falla y tiene protección disponible:
• Puede comprar protección con besitos
• Streak continúa desde donde estaba
• protection_used = True
• Si ya se usó la protección y falla:
• Pierde streak a 0
• TODOS los códigos DELIVERED de esa sesión se marcan como CANCELLED
• Si no tiene besitos suficientes: se le ofrece ir a trivia libre

3. Modo Arriesgar (después de alcanzar un tier)

Cuando el usuario alcanza un tier (ej: streak 5 → código 50%), aparece:

┌─────────────────────────────────────┐
│ 🎰 ¿Qué desea hacer?                 │
│                                      │
│ [🏆 Continuar por 75%]              │
│ [💰 Retirarse con 50%]               │
└─────────────────────────────────────┘

• Retirarse: códigos quedan en DELIVERED, admin los ve en panel, usuario recibe su código
• Continuar: entra en "modo arriesgo" — si falla, pierde TODOS los códigos de esa sesión

4. Timeout de 2 minutos

• Si falló y no tiene besitos → va a trivia libre
• Tiene 2 minutos para ganar besitos y volver
• Si no regresa → streak y códigos se pierden (CANCELLED)
• Esto evita que investiguen las respuestas mientras juegan

5. Ejemplo completo del flujo

User entra a TRIVIA PROMO con streak=0

P1 → P2 → P3 (correcto, streak=3)
P4 → P5 → ¡TIER 1! (50% descuento) → код DELIVERED

┌─────────────────────────────────────┐
│ [🏆 Continuar por 75%]              │
│ [💰 Retirarse con 50%]              │
└─────────────────────────────────────┘

User elige CONTINUAR → modo arriesgo activo
P6 → P7 → P8 → P9 → P10 → ¡TIER 2! (75% descuento) → код DELIVERED

User elige CONTINUAR → modo arriesgo activo
P11 → P12 → P13 → FALLA

Protection_used = True → NO puede proteger
→ Código 50% CANCELLED
→ Código 75% CANCELLED
→ Streak = 0

6. Si falla Y tiene protección disponible

P7 falla (streak=7), protection_available=True

┌─────────────────────────────────────┐
│ 🔒 ¿Proteger tu racha? (-12 besitos)│
│                                      │
│ [Proteger] [No proteger]            │
└─────────────────────────────────────┘

Si elige Proteger:

• Debitar 12 besitos
• protection_used = True
• Streak sigue en 7
• Sigue P8

Si después falla P13:

• protection_used = True → no puede proteger
• Pierde streak, códigos CANCELLED

───

Estructura de datos

Nuevo modelo: StreakSession

• id: UUID (primary key)
• user_id: int
• promotion_id: int
• is_in_risk_mode: bool (continuó tras alcanzar tier)
• protection_used: bool




• codes_delivered: [code_ids] (códigos ganados en esta sesión)
• started_at: datetime
• expires_at: datetime (para timeout de 2 min)

Modificar enum StreakPromotionCodeStatus

• Agregar CANCELLED si no existeEn StreakPromotionService

• _cancel_session_codes(session_id) — marca todos los códigos de la sesión como CANCELLED
• claim_for_streak() — registra códigos en session_codes

───

Handlers a crear/modificar

1. game_trivia_promo — entry point a trivia modo promo (nuevo callback)
2. trivia_promo_answer — procesa respuesta con lógica de protección
3. waiting_retire_choice — FSM state cuando alcanza tier (retirarse o continuar)
4. trivia_promo_accept_protection — usuario acepta protección
5. trivia_promo_decline_protection — usuario no puede o no quiere
6. trivia_promo_timeout — cuando expira el timeout de 2 min

───

Flujo de códigos (resumen)

1. Admin crea promoción con niveles (streak 5 → 30%, streak 10 → 50%, etc)
2. Se generan códigos AVAILABLE upfront (D-10)
3. Usuario juega y alcanza streak 5
4. claim_for_streak() entrega código → estado DELIVERED
5. Usuario elige: retirarse (conserva código) o continuar (arriesga)
6. Si continua y falla: todos códigos de esa sesión → CANCELLED
7. Si se retira: códigos quedan DELIVERED para que admin los vea

───

Referencia

En la rama resp_trivia_multiniveles hay un intento previo de esto con FSM states waiting_streak_choice y streak_continue. Se puede revisar para no repetir los mismos errores. Los issues que tuvo fueron:

• get_all_promotions no funcionaba correctamente
• Handler callbacks rotos
• Validación de max_codes fallab
