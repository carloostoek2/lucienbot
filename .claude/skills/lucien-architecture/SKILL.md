---
name: lucien-architecture
description: Core architecture rules for Lucien Bot development. Trigger when: working with architecture patterns, layers, naming conventions, 50-line function limit, logging format, anti-patterns, or before making any structural changes. This skill provides the foundational rules that govern all development in this codebase.
---

# Lucien Bot — Architecture

Core architectural rules. These are non-negotiable.

## Flujo de Datos (Obligatorio)

```
handlers/ → services/ → models/ → database
```

| Capa | Responsibility | PROHIBIDO |
|------|---------------|-----------|
| **handlers/** | Solo enruta eventos | Lógica de negocio, acceso a DB |
| **services/** | Lógica de negocio por dominio | Acceso directo a DB (usar models) |
| **models/** | Entidades SQLAlchemy y acceso a DB | Lógica de negocio |
| **database** | Configuración de conexión y Base | Todo lo demás |

## Reglas Críticas

| Regla | Descripción |
|-------|-------------|
| **Handlers = routing** | Solo llaman a UN service. Sin lógica, sin DB. |
| **DB solo en models** | Nunca acceso directo a DB fuera de models. |
| **1 service por dominio** | No fragmentar lógica de un dominio en múltiples services. |
| **Máximo 50 líneas** | Cada función máximo 50 líneas. Una sola responsabilidad. |
| **Nombrar: verbo+contexto+resultado** | Ejemplo: `credit_besitos()`, `get_balance()` |

## Naming Conventions

### Archivos
| Tipo | Convención | Ejemplo |
|------|------------|---------|
| Archivos Python | snake_case | `besito_service.py`, `vip_handlers.py` |
| Handlers | `{dominio}_{tipo}_handlers.py` | `gamification_user_handlers.py` |
| Services | `{dominio}_service.py` | `store_service.py` |

### Clases
- PascalCase: `VIPService`, `BesitoService`, `UserService`

### Funciones y Métodos
- Patrón: **verbo + contexto + resultado**
- `credit_besitos()` — acredita besitos
- `get_balance()` — obtiene balance
- `has_sufficient_balance()` — verifica saldo suficiente
- `get_or_create_user()` — obtiene o crea usuario
- `is_user_vip()` — verifica si es VIP

### Variables
- snake_case: `user_id`, `tariff_id`, `is_vip`

### Constantes
- UPPER_CASE: `MAX_BESITOS_PER_DAY = 100`

## Logging (Obligatorio)

Formato: `módulo/acción/user_id=resultado`

```python
logger.info(f"besito_service/credit_besitos/{user_id}={amount}")
logger.info(f"vip_service/add_vip_user/{telegram_id}=success")
```

Siempre incluir: **módulo**, **acción**, **user_id**, **resultado**.

## Anti-patterns Prohibidos

- Funciones llamadas `process_data()`, `handle_logic()` — demasiado genéricas
- Lógica de negocio en handlers
- Acceso a DB desde handlers
- Duplicación entre services
- Hardcoded IDs de usuarios, tokens o configuraciones

## Voz de Lucien

- Habla en 3ra persona ("Lucien gestiona...")
- Elegante, misterioso, nunca vulgar
- "Diana" como figura central
- "Visitantes" no "usuarios"
- "Custodios" no "admins"

## Referencia Rápida

| Concepto | Ubicación |
|----------|-----------|
| Handlers | `handlers/CLAUDE.md` |
| Services | `services/CLAUDE.md` |
| Models | `models/CLAUDE.md` |
| Dominios | `services/{dominio}/CLAUDE.md` |
| Migraciones | `models/CLAUDE.md` (sección Alembic) |