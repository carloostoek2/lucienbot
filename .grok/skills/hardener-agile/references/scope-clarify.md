# Scope Clarification — Lucien Bot (extensión)

Base genérica: `~/.grok/skills/hardener-agile/references/scope-clarify.md`

## Zonas grises típicas en Lucien Bot

Priorizar preguntas sobre estas áreas cuando la petición las toque o sea ambigua:

| Área | Preguntas concretas |
|------|---------------------|
| **3 sistemas críticos** | ¿Toca gamificación (besitos/reacciones/daily), narrativa (FSM/arquetipos/quiz), o canales-VIP (pending/approve/subs)? ¿Cuál debe quedar intacto? |
| **Tipo de cambio** | ¿0 behavior / 0 atomicity (hardening) o cambio visible al visitante? |
| **Handlers vs services** | ¿Solo refactor de handlers (1 svc + puros) o lógica nueva en services? |
| **EventBus / observers** | ¿Nuevo listener, modificar existente, o sin EventBus? (observers MUST NOT mutate) |
| **Besitos / atomicidad** | ¿Crédito/débito en misma tx? ¿Post-credit best-effort aceptable? |
| **Voz de Lucien** | ¿Dominio con copy directo (Tienda/Minijuegos) o estilo poético estándar? |
| **Tests gold** | ¿Re-correr `cross_service_atomicity`, `reaction_`, `daily_gift`, `invariants`? |
| **Modo hardening** | ¿Item de pool desde `HARDENING_ROADMAP.md` o trabajo ad-hoc? |

## Restricciones siempre vigilar (inyectar en Clarification)

- handlers → exactamente 1 `get_service` call
- sin DB fuera de models
- funciones ≤50 líneas
- logging: `módulo | acción | user_id | resultado`

## Persistencia preferida

`.planning/quick/<slug>-CLARIFY.md` — versionado con el repo.