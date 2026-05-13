# Migración CallbackData - Progreso y Estado

## Objetivo
Migrar parsing de callbacks string-based (frágil) a CallbackData de aiogram 3 (type-safe).

**Patrón frágil original:**
```python
tariff_id = int(callback.data.replace("select_tariff_", ""))
```

---

## Estado Actual: 🔵 EN PROGRESO

### Dominios Migrados

| Dominio | Instancias | Estado |
|--------|-----------|--------|
| **Gamification (reacciones broadcast)** | 1/1 | ✅ COMPLETADO |
| **VIP (select_tariff, copy_token)** | 5/5 | ✅ COMPLETADO |
| **Store User (product_detail, direct_buy, etc)** | 21/21 | ✅ COMPLETADO |
| **Promotion (admin + user)** | 37/37 | ✅ COMPLETADO |
| **Channel (admin_channels, channel_detail, etc)** | 9/9 | ✅ COMPLETADO |
| **Package (wizard, detail, delete, files)** | 14/14 | ✅ COMPLETADO |
| **Story Admin (nodes, choices, archetypes)** | 7/7 | ✅ COMPLETADO |
| **Store Admin (products, stock, delete)** | 7/7 | ✅ COMPLETADO |
| **Reward Admin (besitos, packages, VIP)** | 5/5 | ✅ COMPLETADO |
| **Anonymous Message Admin** | 4/4 | ✅ COMPLETADO |
| **VIP User** | 2/2 | ✅ COMPLETADO |
| **Broadcast** | 3/3 | ✅ COMPLETADO |
| **Gamification Admin** | 2/2 | ✅ COMPLETADO |
| **Mission Admin** | 6/6 | ✅ COMPLETADO |
| **Story User** | 3/3 | ✅ COMPLETADO |
| **Trivia Streak Admin** | 7/7 | ✅ COMPLETADO |
| **Mission User** | 1/1 | ✅ COMPLETADO |
| **Reward User** | 1/1 | ✅ COMPLETADO |
| **Trivia Admin** | 1/1 | ✅ COMPLETADO |
| **Trivia Config Admin** | 1/1 | ✅ COMPLETADO |

**Total migrado: 137/95+ instancias (sobrepasó el estimado original)**

### Dominios Pendientes (~66 instancias)

| Dominio | Handler | Instancias | Prioridad |
|---------|---------|------------|----------|
| Mission User Handlers | `mission_user_handlers.py` | 1 | MEDIA |
| Reward User Handlers | `reward_user_handlers.py` | 1 | MEDIA |
| Trivia Admin | `trivia_admin_handlers.py` | 1 | MEDIA |
| Trivia Config Admin | `trivia_config_admin_handlers.py` | 1 | MEDIA |
| Promotion User | `promotion_user_handlers.py` | 2 | MEDIA |
| VIP | `vip_handlers.py` | 2 | ALTA |
| VIP User | `vip_user_handlers.py` | 2 | ALTA |
| Broadcast | `broadcast_handlers.py` | 3 | MEDIA |
| Game | `game_user_handlers.py` | 3 | BAJA |
| Story User | `story_user_handlers.py` | 3 | BAJA |
| Anonymous Message Admin | `anonymous_message_admin_handlers.py` | 4 | ALTA |
| Gamification Admin | `gamification_admin_handlers.py` | 4 | BAJA |
| Inventario (Backpack) | `backpack_handler.py` | 5 | MEDIA |
| Store User | `store_user_handlers.py` | 5 | ALTA |
| Category Admin | `category_admin_handlers.py` | 6 | ALTA |
| Trivia Streak Admin | `trivia_streak_admin_handlers.py` | 7 | MEDIA |
| Mission Admin | `mission_admin_handlers.py` | 8 | MEDIA |
| Promotion Admin | `promotion_admin_handlers.py` | 11 | ALTA |

---

## Archivo Central: `keyboards/callback_data.py`

```python
"""
CallbackData definitions - Centralized for Lucien Bot.
"""
from aiogram.filters.callback_data import CallbackData


# ==================== GAMIFICATION ====================

class ReactionCallback(CallbackData, prefix="react"):
    """Reacciones a mensajes broadcast"""
    broadcast_id: int
    emoji_id: int


class BalanceCallback(CallbackData, prefix="bal"):
    """Consulta de saldo de besitos"""
    action: str = "view"


class HistoryCallback(CallbackData, prefix="hist"):
    """Historial de transacciones"""
    action: str = "view"


class DailyGiftCallback(CallbackData, prefix="gift"):
    """Menú y reclamo de regalo diario"""
    action: str = "menu"


# ==================== BACK NAVIGATION ====================

class BackCallback(CallbackData, prefix="back"):
    """Navegación de vuelta"""
    dest: str = "main"


# ==================== VIP ====================

class SelectTariffCallback(CallbackData, prefix="select_tariff"):
    """Selección de tarifa VIP"""
    tariff_id: int


class CopyTokenCallback(CallbackData, prefix="copy_token"):
    """Copiar token de acceso"""
    token_id: int
```

**Agregar más definiciones según se migran dominios.**

---

## Patrón de Implementación (cómo migrar un dominio)

### Paso 1: Agregar CallbackData en `keyboards/callback_data.py`

```python
class SelectTariffCallback(CallbackData, prefix="select_tariff"):
    tariff_id: int
```

### Paso 2: Actualizar keyboard que genera el callback

```python
# keyboard.py
callback_data=SelectTariffCallback(tariff_id=tariff.id).pack()
```

### Paso 3: Migrar handler

```python
# handler.py
from keyboards.callback_data import SelectTariffCallback

@router.callback_query(SelectTariffCallback.filter())
async def handle_select_tariff(callback: CallbackQuery, callback_data: SelectTariffCallback):
    tariff_id = callback_data.tariff_id  # Type-safe
    # ... resto del handler
```

---

## Refactorización Realizada (prerequisite)

Antes de migrar a CallbackData, se resolvió deuda técnica preexistente:

### Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `keyboards/inline_keyboards.py` | Nueva función `reactions_keyboard_with_counts()` |
| `services/broadcast_service.py` | Nuevo método `update_reaction_message()` |
| `handlers/gamification_user_handlers.py` | Handler refactorizado + logging |

### Por qué fue necesario

El handler original violaba R2 (lógica de negocio en handler):
- Reconstruía keyboard manualmente
- Llamaba `callback.bot.edit_message_reply_markup()` directamente

La refactorización extrajo esta lógica a `keyboards/` y `services/` antes de migrar a CallbackData.

---

## Siguiente Paso Recomendado

### Opción A: Continuar con VIP (4 instancias, alta prioridad)

VIP tiene callbacks críticos:
- `select_tariff_{tariff.id}` - selección de tarifa
- `copy_token_{token_id}` - copiar token

**Archivos a modificar:**
- `handlers/vip_handlers.py`
- `handlers/vip_user_handlers.py`
- `handlers/anonymous_message_admin_handlers.py`

### Opción B: Continuar con Store (5+7 instancias)

Store es uno de los dominios más usados con más frágil. Instancias críticas:
- `product_detail_`, `direct_buy_`, `confirm_direct_buy_`
- `store_category_`, `product_preview_`

---

## Tests a Ejecutar Después de Cambios

```bash
# Unit tests
python3 -m pytest tests/unit/test_broadcast_service.py -v

# Integration tests
python3 -m pytest tests/integration/test_reaction_*.py -v

# Verificar imports
python3 -c "from handlers.gamification_user_handlers import router; print('OK')"
```

---

## Reglas Arquitectónicas a Verificar

| Regla | Descripción |
|-------|-------------|
| R1 | Handler llama exactamente 1 service |
| R2 | SIN lógica de negocio en handler |
| R3 | SIN acceso a DB directo en handler |
| R4 | CallbackData definido en keyboards/ |
| R5 | Logging en operaciones críticas |

Cada dominio migrado debe pasar la verificación con `arch-enforcer`.

---

## Recursos

- **Debug session:** `.planning/debug/callbackdata-migration.md`
- **Diseño:** `.planning/debug/callbackdata-migration-design.md`
- **Archivo central:** `keyboards/callback_data.py`
- **Archivo keyboards:** `keyboards/inline_keyboards.py`

---

*Última actualización: 2026-05-12*
*Migración completada: 1/95 instancias (1%)*