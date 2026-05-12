---
name: callbackdata-migration-debug
description: Migrar parsing de callbacks string-based a CallbackData de aiogram 3
type: project
created: 2026-05-11
agents:
  - impact-analyzer: Análisis de impacto por dominio
  - telegram-backend-architect: Diseño y migración de cada dominio
  - arch-enforcer: Verificación de reglas arquitectónicas
  - test-guardian: Tests de integración
status: in_progress
progress: 106/160+ instancias (66%)
---

# Migración CallbackData

## Objetivo
Migrar todas las 95 instancias de parsing frágil de callback.data (como `int(callback.data.replace("select_tariff_", ""))`) a CallbackData de aiogram 3.

## Estado: 🔵 EN PROGRESO

### Flujo de Ejecución (para continuar)
Cada dominio se migra siguiendo este flujo estructurado:

1. **impact-analyzer** → Analiza impacto (instancias, dependencias cruzadas, riesgo)
2. **telegram-backend-architect** → Migra el dominio
3. **arch-enforcer** → Verifica reglas arquitectónicas
4. **test-guardian** → Tests de integración
5. **Actualizar PROGRESS.md** → Documentar avances

### Completado
- **Gamification (reacciones broadcast)** - 1 instancia ✅
- **VIP (select_tariff, copy_token)** - 5 instancias ✅
- **Store User** - 21 instancias ✅
- **Promotion (admin + user)** - 37 instancias ✅
- **Channel** - 9 instancias ✅
- **Package** - 14 instancias ✅
- **Story Admin** - 7 instancias ✅
- **Store Admin** - 7 instancias ✅
- **Reward Admin** - 5 instancias ✅

### Pendiente
- ~66 instancias restantes

## Dominios Pendientes (por prioridad)
| Dominio | Instancias | Prioridad |
|--------|-----------|----------|
| Category Admin | 6 | ALTA |
| Anonymous Message Admin | 4 | ALTA |
| Gamification Admin | 4 | BAJA |
| Story User | 3 | BAJA |
| Game | 3 | BAJA |
| Broadcast | 3 | MEDIA |
| Store User | 5 | ALTA |
| Inventario (Backpack) | 5 | MEDIA |
| Promotion User | 2 | MEDIA |
| Mission Admin | 8 | MEDIA |
| Trivia Streak Admin | 7 | MEDIA |
| VIP | 2 | ALTA |
| VIP User | 2 | ALTA |
| Trivia Config Admin | 1 | MEDIA |
| Trivia Admin | 1 | MEDIA |
| Mission User Handlers | 1 | MEDIA |
| Reward User Handlers | 1 | MEDIA |
| Promotion Admin | 11 | ALTA |

## Optimizaciones Aplicadas
- **Colapsar confirm/execute pairs**: Usar campo `confirmed: bool` en lugar de 2 clases
- **Prefijos separados**: Admin (`adm_*`) vs User (`usr_*`) para evitar colisiones
- **Callbacks type-safe**: Todo usa `callback_data.field` en lugar de parsing string

## Archivo Central
- `keyboards/callback_data.py` - Definiciones CallbackData

## Siguiente Paso
- **Category Admin** - 6 instancias, ALTA prioridad

## Documentación
- `.planning/callbackdata-migration-PROGRESS.md` - Estado detallado

---
*Última actualización: 2026-05-12*
*Migración completada: 106/160+ instancias (66%)*