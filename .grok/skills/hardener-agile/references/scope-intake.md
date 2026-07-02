# Scope Intake — Lucien Bot (extensión)

Base genérica: `~/.grok/skills/hardener-agile/references/scope-intake.md`

Con `--clarify`, leer también `references/scope-clarify.md` (extensión Lucien) antes del intake.

## Restricciones Lucien Bot (siempre vigilar)

- handlers → exactamente 1 service call (`get_service`)
- sin acceso DB fuera de models
- funciones ≤50 líneas
- logging: `módulo | acción | user_id | resultado`
- 3 sistemas críticos: gamificación, narrativa, canales-VIP
- Contratos: atomicity, EventBus (MUST NOT mutate), get_service

## Roadmap hardening

`.planning/HARDENING_ROADMAP.md` — solo con `--hardening` o petición explícita.