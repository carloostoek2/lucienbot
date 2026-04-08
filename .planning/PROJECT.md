# Lucien Bot

## What This Is

Telegram bot gamificado para la comunidad de Señorita Kinky (Diana Hernández). Gestiona suscripciones VIP, canales de contenido, un sistema de gamificación con besitos, misiones, tienda virtual, promociones y narrativa interactiva con arquetipos de personajes.

## Core Value

Crear una experiencia premium y gamificada que incentiva el compromiso de la comunidad con Diana a través de un sistema de recompensas, acceso exclusivo VIP y narrativa inmersiva.

## Requirements

### Validated

- ✓ **Sistema VIP completo** — Tokens, tarifas, suscripciones, expiración automática — Fase 3
- ✓ **Gestión de canales** — Canal Free con aprobación automática y canal VIP con acceso por suscripción — Fase 2
- ✓ **Minijuegos (Dados y Trivia)** — Dados con límites diarios, trivia con preguntas, recompensas en besitos — Fase 14
- ✓ **Sistema de Mochila (Inventario)** — Comando /mochila con recompensas, compras, VIP, entrega de paquetes — Fase 15
- ✓ **Gamificación (Besitos)** — Sistema de besitos, hugs, regalos diarios, balances — Fase 4
- ✓ **Sistema de Misiones** — Misiones activas, seguimiento de progreso, recompensas — Fase 5
- ✓ **Tienda Virtual** — Paquetes de besitos, compra, entrega de contenido — Fase 6
- ✓ **Promociones** — Códigos promocionales con límites y descuentos — Fase 6
- ✓ **Sistema de Narrativa** — Historias interactivas con arquetipos, opciones de usuario — Fase 6
- ✓ **Panel de Administración** — Custodios pueden gestionar todos los dominios — Fases 3-6
- ✓ **Migraciones Alembic** — Sistema de migraciones de esquema con Alembic, baseline migration, Railway integration — Fase 07.1

### Active

- [ ] **VIP Invite Links Dinámicos** — Generar links de invitación de un solo uso para el canal VIP en lugar de links estáticos — mejora de Fase 6

### Out of Scope

- **App móvil nativa** — El bot es la plataforma principal, no hay planes de app
- **Multi-idioma** — Todos los mensajes en español únicamente
- **Copias de seguridad automáticas** — Database backup manual por ahora
- **Webhooks** — Long polling es suficiente para la escala actual

## Context

**Comunidad:** Señorita Kinky (Diana Hernández) — creadora de contenido
**Usuarios:** Miembros de la comunidad que pagan por acceso VIP y participan en gamificación
**Custodios (Admins):** Equipo de Diana que gestiona el bot

**Stack:** aiogram 3.4.1 + SQLAlchemy 2.0 + SQLite (production: PostgreSQL via Railway)
**Despliegue:** Railway con PostgreSQL
**Arquitectura:** handlers → services → models (capas estrictas, sin lógica en handlers)

**Tech debt conocido:**
- Sin tests automatizados (riesgo de regresión alto)
- Archivos de handlers grandes (>900 líneas)
- Gestión de sesiones DB via `__del__` (poco confiable)
- MemoryStorage para FSM (estado perdido en reinicios)

**Seguridad conocida:**
- No rate limiting implementado
- Tokens VIP con race condition potencial
- Scheduler con polling cada 30s (puede perder expiraciones)

## Constraints

- **Tech stack**: Python 3.12+, aiogram 3.x, SQLAlchemy 2.0 — no cambiar sin razón
- **Arquitectura**: Capas handlers/services/models estrictas — sin lógica de negocio en handlers
- **Voz de Lucien**: Siempre en 3ra persona, elegante y misterioso, "Diana" como figura central
- **DB**: SQLite local / PostgreSQL en Railway — compatible SQLAlchemy
- **Sin tests**: Prioridad alta pero no bloqueante para features

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| aiogram 3.x (no v4) | v4 en desarrollo, rompería todo | ✓ Good |
| SQLite → PostgreSQL en Railway | SQLite no escala con writes concurrentes | ✓ Good |
| FSM con MemoryStorage | Simple, suficiente para el uso actual | ⚠️ Revisit (perdida de estado en reinicios) |
| Invite links estáticos para VIP | Simplicidad operativa | ⚠️ Revisit (limitación: un link compartido = varios usan) |
| Scheduler con polling 30s | Simple de implementar | ⚠️ Revisit (puede perder expiraciones) |
| python-dotenv para config | Simple, sin dependencias extra | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-06 after phase 14 completion*
