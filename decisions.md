# TECHNICAL DECISIONS

## Separación por dominios
Motivo:
- escalabilidad

Decisión:
- cada dominio tiene su propio service

---

## Estructura handlers/services
Motivo:
- claridad
- compatibilidad con LLM

Decisión:
- handlers solo enrutan
- services ejecutan lógica

---

## Uso de múltiples handlers
Problema:
- crecimiento descontrolado

Decisión:
- consolidar handlers por dominio cuando sea posible

---

## Uso de LLMs
Motivo:
- acelerar desarrollo

Reglas:
- LLM genera
- humano valida arquitectura
- tests validan comportamiento

---

## Próxima decisión pendiente

Tema:
- consolidación de handlers

Opciones:
- mantener estructura actual
- agrupar por dominio

Riesgo:
- explosión de complejidad

---

## Middleware centralization (rate limiting + idempotency) - gsd-mw-hardening (phase 2-6)

Motivo:
- Preocupaciones cross-cutting (rate limit, dedup de callbacks por reintentos de TG) estaban duplicadas o implementadas de forma frágil (manual if-dupe en 3 sitios de handlers: gamification handle_reaction + reward 2 funcs; stub en middlewares; lógica madura solo en handlers/rate_limit_middleware.py legacy).
- Violaba reglas de handlers (sin lógica), dificultaba testing central, bypass de Custodios, y orden de aplicación.
- Riesgo a sistemas críticos: reacciones con besitos (gamif), quiz narrativa (choices como cbs), gestión canales/VIP (acciones admin deben bypass rate), recompensas.

Decisión:
- Portar lógica madura (aiolimiter por usuario, ADMIN_BYPASS real desde config + lista de admins, cleanup idle, mensaje Lucien idéntico con show_alert, soporte CQ via data["event_from_user"], logging, robustez en answer) a `middlewares/rate_limiter.py` como clase `ThrottlingMiddleware` (nombre canónico) + alias `RateLimiterMiddleware`.
- Agregar `IdempotencyMiddleware(BaseMiddleware)` en `middlewares/idempotency.py` que usa el `idempotency_cache` existente para CBs (skip + answer + log + pass-through + robustness).
- Actualizar middlewares/__init__.py exports.
- Wiring en bot.py (phase 4) con orden: Error outer, Idempotency para cb, Throttling para cb; Throttling para messages. (Error cambiado a outer_middleware).
- Fase 5: remover los 3 sitios manuales de `idempotency_cache.is_duplicate` + imports en los dos handlers (ahora handlers llaman exactly 1 service, sin lógica). Actualizar tests de handlers (remover tests "skips_when_duplicate" y sus @patch; simplificar happy-paths).
- Fase 2/3: tests unit actualizados/creados y 100% verdes *antes* de wiring.
- Fase 6: header DEPRECATED fuerte en el legacy rate file, actualizar docs (handlers/CLAUDE.md, CLAUDE.md, decisions.md), grep confirmando 0 usos manuales en handlers/, verificación completa (units + smoke + integrations/smokes para reacciones, rewards, narrative quiz choices, channel/vip admin bypass, reward).
- Shim legacy rate mantiene compat temporal + warning.
- Revertir solo bot.py es safe point principal si algo rompe.

Resultado:
- Rate limiting + idempotencia ahora globales, centralizados, testeados, con bypass Custodios correcto y orden explícito.
- Handlers 100% routing (1 service call).
- Los 3 sistemas críticos protegidos sin duplicación de guards.
- Tests de mw (rate + idemp + cache) + handlers actualizados verdes.
- Traceabilidad vía commits por fase con refs "gsd-mw-hardening: phase X".

(Ver PLAN y SUMMARY en .planning/phases/08-testing-and-technical-debt/ para ejecución detallada.)

## Internal EventBus (PoC Item 1 - "besitos_awarded" primer caso de uso) - gsd eventbus-poc

Motivo:
- Necesidad de notificaciones cross-domain loose-coupled (gamif → narrative, potencialmente otros) sin violar "handlers llaman exactly 1 service", sin duplicar lógica de side-effects, y sin acoplar servicios directamente (import de story desde besito o viceversa).
- El analyzer identificó credit_besitos como el punto natural único de emisión para "awarded" (reacciones, daily, misiones, game, logros de story, admin todos pasan por ahí). Los tres sistemas críticos (gamif reactions con besitos, narrative achievements que acreditan besitos inverso, channel/VIP) dependen de la atomicidad y contratos de crédito.
- Patrón maduro ya existía en el código: `asyncio.gather(..., return_exceptions=True)` en test_broadcast_service_reaction_flow para concurrencia segura de reacciones (un "fallo" no mata las demás).
- PoC conservadora: solo un evento, un listener, emit post-commit best-effort, sin inyección (usa get/schedule para mínimo diff), sin persistencia/retry.

Riesgos (críticos):
- Romper atomicidad del crédito o los retornos de broadcast reactions (el dict con "besitos_awarded" local por emoji).
- Loops de crédito si el listener narrative volvía a acreditar.
- "besitos_awarded" confusion (nombre del event vs campo local en BroadcastReaction/reaction_result).
- Tests flaky por singleton listeners o falta de loop en schedule desde tests sync.
- Import side-effects o registro mágico.

Decisión:
- Implementar `services/event_bus.py` (InternalEventBus con register/emit async + schedule_emit helper para sync callers + get_event_bus singleton + EVENT_* const).
- Emit solo en la ruta de éxito de `credit_besitos`, inmediatamente después de `db.commit()` y **dentro** del try del crédito, wrapped en su propio try/except que solo warning + nunca rollback/return False.
- Payload estándar (user_id, amount, source str, reference_id, description, timestamp ISO).
- Helper privado en besito (`_schedule_besitos_awarded_event`) para mantener credit_besitos <=50 LOC.
- Primer listener real en narrative (`on_besitos_awarded_from_gamification` en story_service.py): solo log + prueba de wiring; ownership narrative; explícitamente prohíbe re-entrar a besitos.
- Registro explícito y central en `bot.py` on_startup (después de scheduler, antes de notificar admins). Sin auto-registro en imports de story.
- Tests: unit puro del bus (fresh instances, return_exceptions, logs, noop), patch del schedule/get en unit besito + integ atómicas, smoke de "listener narrative recibió".
- Actualizaciones mínimas de docs (gamif/narrative/services CLAUDEs + decisions) + grep de distinción "besitos_awarded" local vs event.
- No se removieron instanciaciones directas de BesitoService (scope explícito).

Resultado:
- Un crédito (cualquier source) actualiza DB atómicamente (balance + tx), procesa misiones best-effort en tx separada, y entrega el evento best-effort al listener narrative (logueado), sin que el caller del crédito se entere de fallos en listeners.
- 0 cambios en contratos de broadcast reactions (local "besitos_awarded" sigue igual).
- Handlers siguen llamando exactly 1 service (sin imports de bus).
- Bus removable (borrar event_bus.py + su test + la línea de register en bot + la def del listener + los exports = zero impacto residual).
- Gates: event_bus unit 7/7, besito 46+, reaction/atomicity/story 200+, ruff limpio, smokes de import bot y register+emit manual.
- Preparado para Item 2+ (más listeners/eventos, quizás inyección posterior) y para arch-enforcer/test-guardian (tests críticos listados en GSD log final).

(Ver .planning/phases/19-eventbus-poc/PLAN.md y gsd-eventbus-poc-item1.log para ejecución fase por fase y handoff.)
