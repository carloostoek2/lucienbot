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
