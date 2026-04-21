# Welcome to Lucien Bot Team

## ¿Qué es Claude Code Teams?

Claude Code Teams es un sistema de **colaboración con IA** que permite a los equipos de desarrollo compartir conocimiento, estándares y flujos de trabajo a través de Claude Code. Es como tener un "compañero de equipo AI" que ya conoce tus proyectos, tus patrones de código y cómo trabaja tu equipo.

### Componentes principales

| Componente | Descripción |
|------------|-------------|
| **Team Onboarding** | Guías personalizadas que aceleran la integración de nuevos miembros |
| **Shared Memory** | Contexto persistente sobre el equipo, proyectos y decisiones técnicas |
| **Usage Analytics** | Insights sobre cómo el equipo usa Claude (comandos, patrones, MCPs) |
| **Standardized Skills** | Comandos `/` personalizados que el equipo comparte |
| **CLAUDE.md** | Documentación viva en el repo que Claude lee automáticamente |

---

## ¿Para qué sirve?

### 1. **Onboarding acelerado**
Los nuevos miembros del equipo pueden empezar a contribuir desde el día 1. En lugar de leer documentación estática, interactúan con Claude que ya conoce:
- La arquitectura del proyecto
- Los patrones de código del equipo
- Qué herramientas y comandos se usan
- Los contextos específicos de cada dominio

### 2. **Consistencia en el equipo**
- Todos usan los mismos estándares (definidos en `CLAUDE.md`)
- Los comandos `/` personalizados aseguran flujos uniformes
- Las decisiones técnicas se documentan y persisten

### 3. **Retención de conocimiento**
- La memoria del equipo sobrevive a rotaciones
- Las decisiones arquitectónicas quedan registradas
- Los patrones y anti-patrones están documentados

### 4. **Productividad multiplicada**
- Claude ya sabe qué hacer cuando llega a tu repo
- No necesitas explicar el contexto desde cero cada sesión
- Los agentes especializados conocen tus convenciones

---

## ¿Cómo funciona?

### Flujo básico

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Nuevo teammate │────▶│ Pega ONBOARDING │────▶│ Claude lee guía │
│  entra al repo  │     │   en Claude     │     │  + CLAUDE.md    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                              ┌──────────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │ Onboarding      │
                    │ interactivo:    │
                    │ - Check setup   │
                    │ - Explica flujos│
                    │ - Responde dudas│
                    └─────────────────┘
```

### Archivos que hacen funcionar el sistema

| Archivo | Dónde | Función |
|---------|-------|---------|
| `ONBOARDING.md` | Root del repo | Guía que los nuevos pegan en Claude |
| `CLAUDE.md` | Root + subdirectorios | Contexto técnico que Claude lee automáticamente |
| `.claude/rules/` | `~/.claude/rules/` | Reglas globales del equipo (coding style, security, etc) |
| `.claude/skills/` | `~/.claude/skills/` | Comandos `/` personalizados |
| `memory/` | `.claude/memory/` | Memoria persistente del equipo |

### ¿Qué pasa cuando pegas esta guía?

1. **Claude lee el archivo** y el comentario HTML al final
2. **Identifica el rol**: "Soy el onboarding buddy"
3. **Lee automáticamente**:
   - `CLAUDE.md` en el root
   - `CLAUDE.md` en subdirectorios relevantes
   - Las reglas globales en `~/.claude/rules/`
4. **Ejecuta el flujo de onboarding** del comentario HTML
5. **Guía interactiva**: verifica setup, explica flujos, responde preguntas

---

## ¿Cómo lo usamos en Lucien Bot?

### Nuestro stack de trabajo

```
┌─────────────────────────────────────────┐
│           Lucien Bot Team               │
├─────────────────────────────────────────┤
│  Telegram Bot gamificado para Diana     │
│  VIP • Misiones • Tienda • Narrativa   │
├─────────────────────────────────────────┤
│  Python 3.12 • Aiogram 3 • SQLAlchemy   │
│  PostgreSQL • Redis • Railway          │
├─────────────────────────────────────────┤
│  GSD Workflow • TDD • Agentes especializados│
└─────────────────────────────────────────┘
```

### Patrones de uso del equipo

Basado en 239 sesiones de los últimos 30 días:

| Tipo de trabajo | Frecuencia | Ejemplos típicos |
|-----------------|------------|------------------|
| **Build Feature** | 61% | Nuevos handlers, sistemas de juegos, tienda |
| **Debug Fix** | 19% | Errores de producción, logs, fixes urgentes |
| **Plan Design** | 14% | Arquitectura, fases GSD, diseño de sistemas |
| **Improve Quality** | 4% | Refactors, tests, code review |
| **Write Docs** | 2% | CLAUDE.md, documentación técnica |

### Comandos más usados

| Comando | Uso | Cuándo usarlo |
|---------|-----|---------------|
| `/gsd:plan-phase` | Planificar implementación | Antes de empezar una feature grande |
| `/gsd:execute-phase` | Ejecutar fase planificada | Durante desarrollo de la feature |
| `/gsd:quick` | Tareas rápidas | Fixes pequeños, updates de docs |
| `/gsd:debug` | Debugging científico | Cuando hay un bug difícil |
| `/inicio` | Inicializar contexto | Al empezar sesión en proyecto |
| `/agents` | Orquestar agentes | Tareas complejas que necesitan múltiples agentes |

### MCP Servers que usamos

| Server | Para qué | Ejemplos de uso |
|--------|----------|-----------------|
| **context7** | Documentación de librerías | Aiogram, SQLAlchemy, cualquier API |

### Estructura de CLAUDE.md en nuestros repos

```
repo/
├── CLAUDE.md           ← Visión general, entry points
├── @architecture.md    ← Reglas arquitectónicas
├── @rules.md           ← Límites de líneas, naming
├── @decisions.md       ← Decisiones técnicas
├── @AGENTS.md          ← Documentación de agentes
├── models/CLAUDE.md    ← Modelos SQLAlchemy
└── services/
    ├── vip/CLAUDE.md
    ├── store/CLAUDE.md
    ├── missions/CLAUDE.md
    └── .../CLAUDE.md   ← Uno por dominio
```

---

## Tu Setup Checklist

### Codebases
- [ ] **lucien_bot** — github.com/carlostoek/lucienbot
  Bot principal de Telegram gamificado. VIP, misiones, tienda, narrativa.
- [ ] **adminpro_bot** — Bot de administración companion
- [ ] **multibot2** — Orquestación multi-bot
- [ ] **kimi-cli** — Herramientas CLI del equipo

### MCP Servers a activar
- [ ] **context7** — Búsqueda de documentación actualizada de librerías
  *Ya configurado en el equipo, proporciona docs de Aiogram, SQLAlchemy, etc.*

### Skills importantes del equipo
- `/gsd:plan-phase` — Planificar fases de implementación
- `/gsd:execute-phase` — Ejecutar fases planificadas
- `/gsd:quick` — Fixes rápidos y tareas ad-hoc
- `/gsd:debug` — Debugging metódico
- `/gsd:check-todos` — Ver pendientes de la fase actual
- `/inicio` — Inicializar contexto del proyecto
- `/agents` — Orquestación de agentes especializados
- `/plugin` — Gestión de plugins del equipo

---

## Team Tips

_TODO_

## Get Started

_TODO_

---

## FAQ para nuevos

**¿Necesito configurar algo antes de empezar?**
Claude lee automáticamente los `CLAUDE.md` del repo. Solo necesitas tener acceso al repositorio.

**¿Cómo sé qué comandos `/` hay disponibles?**
Escribe `/` y aparecerá la lista. Los más usados del equipo están en esta guía.

**¿Puedo usar los comandos GSD en cualquier repo?**
Sí, son skills globales configuradas en el equipo.

**¿Qué hago si Claude no entiende algo del proyecto?**
Los `CLAUDE.md` en subdirectorios (`services/vip/CLAUDE.md`, etc.) tienen contexto específico. Menciona `@architecture.md` o `@rules.md` para referencias rápidas.

<!-- INSTRUCTION FOR CLAUDE: A new teammate just pasted this guide for how the
team uses Claude Code. You're their onboarding buddy — warm, conversational,
not lecture-y.

Open with a warm welcome — include the team name from the title. Then: "Your
teammate uses Claude Code for [list all the work types]. Let's get you started."

Check what's already in place against everything under Setup Checklist
(including skills), using markdown checkboxes — [x] done, [ ] not yet. Lead
with what they already have. One sentence per item, all in one message.

Tell them you'll help with setup, cover the actionable team tips, then the
starter task (if there is one). Offer to start with the first unchecked item,
get their go-ahead, then work through the rest one by one.

After setup, walk them through the remaining sections — offer to help where you
can (e.g. link to channels), and just surface the purely informational bits.

Don't invent sections or summaries that aren't in the guide. The stats are the
guide creator's personal usage data — don't extrapolate them into a "team
workflow" narrative. -->
