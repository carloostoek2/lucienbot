---
name: hardener-agile
description: >
  Override de proyecto para Lucien Bot. Delega al orquestador global
  (~/.grok/skills/hardener-agile/) con contexto Lucien: 3 sistemas críticos
  (gamificación, narrativa, canales-VIP), HARDENING_ROADMAP con --hardening,
  aclaración de scope con --clarify, y agentes locales en .grok/agents/.
  Usa /hardener-agile normalmente.
argument-hint: "[--clarify] [--plan PATH | --spec PATH | --hardening | status | item N] [descripción]"
metadata:
  short-description: "Pipeline 6 agentes — Lucien Bot override"
---

# Hardener Agile — Lucien Bot

Este skill **extiende** el orquestador global. Lee primero:

`~/.grok/skills/hardener-agile/SKILL.md`

Luego aplica estos defaults de proyecto:

## Contexto Lucien Bot

- **Reglas:** `CLAUDE.md`, `architecture.md`, `rules.md`, `services/*/CLAUDE.md`
- **3 sistemas críticos:** gamificación (besitos/reacciones/daily), narrativa (FSM/arquetipos), canales-VIP (pending/approve/subs)
- **Contratos:** atomicidad, EventBus (MUST NOT mutate), get_service (1 call/handler)
- **Tests gold:** `cross_service_atomicity`, `reaction_`, `daily_gift`, `invariants`
- **Flags pytest default:** `-q --tb=line -p no:cov --override-ini="addopts="`

## Modo `--clarify`

Primer paso operativo cuando la bandera está activa. Protocolo global + extensiones Lucien:

- Global: `~/.grok/skills/hardener-agile/references/scope-clarify.md`
- Lucien: `references/scope-clarify.md` (zonas grises típicas: 3 crit, atomicidad, voz, tests gold)

Persistir en `.planning/quick/<slug>-CLARIFY.md`. Inyectar en todos los agentes del pipeline.

## Agentes

Resolución con override local:
- `.grok/agents/<nombre>.md` → Lucien-specific (documentador, arch-enforcer, test-guardian)
- `~/.grok/agents/<nombre>.md` → global

**Test-guardian:** audita mocks obligatoriamente (ver `references/mock-audit.md` global + override local con patrón integration gamif/store pool 33).

## Modo --hardening

Incluir `.planning/HARDENING_ROADMAP.md` en intake.
Frase de cierre de pool hardening (verbatim):

> Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.

## Resto del pipeline

Seguir exactamente la secuencia global: [§0a clarify si `--clarify`] → intake → impact-analyzer → gsd-planner → gsd-executor → arch-enforcer → test-guardian → pytest → documentador.