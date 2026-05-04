---
name: lucien-developer
description: Main orchestrator skill for Lucien Bot development. When this skill triggers, it coordinates specialized skills for handlers, services, models, migrations, security, GSD workflow, and pre-commit checklist. Use whenever working in this codebase -- adding features, fixing bugs, creating migrations, or any development task.
---

# Lucien Bot — Developer Orchestrator

Este skill es el orquestador principal. Delega a skills especializadas según el tipo de trabajo a realizar.

## Skills Especializadas Disponibles

| Skill | Trigger | Propósito |
|-------|---------|-----------|
| **lucien-architecture** | Arquitectura, naming, 50-líneas, logging | Reglas core del proyecto |
| **lucien-handlers** | Modificar handlers/, crear callbacks, FSM | Patrones de routing |
| **lucien-services** | Lógica de negocio, services/, dominio | Implementación de services |
| **lucien-models** | Models, SQLAlchemy, relaciones | Estructura de datos |
| **lucien-migrations** | alembic/, crear migración, enum | Migraciones de BD |
| **lucien-security** | is_admin(), rate limiting, permisos | Validaciones de seguridad |
| **lucien-gsd** | Antes de modificar archivos | Workflow obligatorio |
| **lucien-checklist** | Antes de commit, PR ready | Validación pre-commit |

## Reglas del Orquestador

1. **Identificar el tipo de trabajo** → invocar skill especializada
2. **Si hay múltiples tipos** → invocar todas las relevantes
3. **Si el trabajo toca un dominio específico** → también consultar `services/{dominio}/CLAUDE.md`

## Flujo de Trabajo

```
1. Usuario pide trabajo
2. Identificar qué skills se necesitan
3. Invocar lucien-gsd primero (si es modificación de archivos)
4. Invocar skills especializadas según el dominio
5. Ejecutar el trabajo siguiendo las reglas de cada skill
6. Antes de commit: invocar lucien-checklist
```

## Dominios y Sus Archivos de Referencia

| Dominio | Archivo CLAUDE.md |
|---------|------------------|
| VIP | `services/vip/CLAUDE.md` |
| Gamificación | `services/gamification/CLAUDE.md` |
| Canales | `services/channels/CLAUDE.md` |
| Tienda | `services/store/CLAUDE.md` |
| Misiones | `services/missions/CLAUDE.md` |
| Promociones | `services/promotions/CLAUDE.md` |
| Narrativa | `services/narrative/CLAUDE.md` |

## Ejemplo de Orquestación

**Trabajo: "Agregar nueva misión al sistema"**

1. Invocar `lucien-gsd` → planificar el trabajo
2. Invocar `lucien-architecture` → reglas core
3. Invocar `lucien-models` → verificar modelo de Mission
4. Invocar `lucien-migrations` → si se necesita nuevo enum
5. Consultar `services/missions/CLAUDE.md` → contexto del dominio
6. Invocar `lucien-checklist` → antes de commit

## Áreas de Conocimiento

El developer de Lucien debe conocer:
- **Arquitectura**: handlers → services → models → database
- **Nombrado**: verbo + contexto + resultado
- **Límites**: 50 líneas por función
- **Logging**: módulo/acción/user_id=resultado
- **Voz de Lucien**: 3ra persona, elegante, "visitantes" no "usuarios", "custodios" no "admins"

## Anti-Patterns (Nunca Hacer)

- Lógica de negocio en handlers
- Acceso a DB desde handlers
- Funciones llamadas `process_data()`, `handle_logic()`
- Hardcoded IDs de usuarios o configuraciones
- Duplicación entre services

## Workflow GSD

Antes de modificar archivos, usar los comandos GSD:

| Comando | Uso |
|---------|-----|
| `/gsd:quick` | Fixes pequeños, updates de docs |
| `/gsd:debug` | Investigación de bugs |
| `/gsd:execute-phase` | Features planificadas |

**No hacer edits directos fuera de GSD** a menos que el usuario lo pida explícitamente.