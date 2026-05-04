---
name: trivia-code-verification
description: Implementar verificación de códigos de descuento por racha de trivia para administradores
date: 2026-05-04
status: in-progress
agent: executor
quick_id: q1
slug: trivia-code-verification
---

## Tasks

### Task 1: Agregar botón de verificación en vista de configuración

**Files:**
- `handlers/trivia_discount_admin_handlers.py`

**Action:**
En el callback `view_trivia_discounts`, agregar un botón adicional "🔍 Verificar códigos" con callback_data `verify_codes_{config.id}`. Esto permitirá al administrador ver el detalle de cada código generado.

**Verify:**
- Botón aparece en el keyboard de la configuración
- El callback `verify_codes_{config_id}` está registrado

**Done:**
- El menú de configuración incluye la opción "Verificar códigos"

---

### Task 2: Implementar vista de verificación detallada de códigos

**Files:**
- `handlers/trivia_discount_admin_handlers.py`
- `services/trivia_discount_service.py`

**Action:**
Implementar el handler `verify_discount_codes` que:
1. Obtiene todos los códigos de la configuración
2. Para cada código, muestra:
   - Código (TRI-XXXXXX)
   - Usuario (username o nombre)
   - Descuento del tier que tenía cuando se generó (buscar en game_records el streak máximo)
   - Pregunta máxima alcanzada (streak)
   - Estado actual (ACTIVO/USADO/CANCELLED)
   - Timestamp de generación
3. Botones de acción:
   - Para activos: "✓ Marcar como usado" (`use_code_{id}`) y "✗ Cancelar" (`cancel_code_{id}`)
   - Para usados: solo mostrar info, sin acciones

**Verify:**
- Se muestra streak máximo alcanzado por el usuario para cada código
- Se muestra el descuento del tier
- Se pueden marcar códigos como usados o cancelarlos

**Done:**
- Vista detallada muestra streak y descuento por código
- Acciones de marcar usado/cancelar funcionan correctamente

## Implementation Notes

- El streak máximo se puede inferir de los `GameRecord` del usuario con `game_type='trivia'` y `discount_code_id` igual al código
- Alternativamente, store el streak en el momento de generación del código en un campo del modelo `DiscountCode`
- Para esta implementación, consultar los `GameRecord` relacionados para obtener el streak máximo