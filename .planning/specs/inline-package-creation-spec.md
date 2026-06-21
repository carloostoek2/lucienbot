# SPEC: Creación inline de paquete desde selección de producto

**Status:** draft
**Date:** 2026-06-21
**Author:** Architect review pending

---

## 1. Problem

Cuando un Custodio crea o edita un producto con fulfillment kind `PACKAGE` o `PACKAGE_DEFERRED`, debe seleccionar un paquete existente. Si el paquete deseado no existe, el flujo actual lo fuerza a:

1. Cancelar el wizard de producto (perdiendo todo lo ingresado)
2. Navegar a "Gestionar Paquetes" (`manage_packages`)
3. Crear el paquete (wizard de 6 pasos: nombre → descripción → archivos → stock tienda → stock recompensas → confirmar)
4. Volver a "Gestionar Tienda" (`admin_store`)
5. Reiniciar el wizard de producto desde cero

Esto es disruptivo, lento, y propenso a abandono.

## 2. Solution

Agregar un botón "➕ Crear nuevo paquete" en el paso de selección de paquete (tanto en creación como en edición de producto). Al presionarlo:

1. Se guarda el contexto completo del wizard de producto en FSM data
2. Se inicia el wizard de creación de paquete inline
3. Al confirmar la creación del paquete, el sistema:
   - Recupera el contexto guardado del wizard de producto
   - Restaura los datos y el estado
   - Asigna automáticamente el nuevo paquete como seleccionado
   - Avanza directamente al paso de precio (sin que el admin tenga que volver a seleccionar)

## 3. Scope

### In scope
- Botón "➕ Crear nuevo paquete" en `_wizard_prompt_package_selection` (creación de producto, `store_admin_handlers.py`)
- Botón "➕ Crear nuevo paquete" en `build_edit_package_buttons` (edición de producto, `store_admin_handlers.py`)
- Guardado y restauración del contexto del wizard de producto al entrar/salir del wizard de paquete
- Auto-selección del paquete recién creado y avance a `waiting_price`
- Mensaje de confirmación mostrando qué paquete fue creado y seleccionado

### Out of scope
- Modificar el wizard de creación de paquete en sí (sigue igual, solo se le agrega detección del contexto de retorno)
- Otros fulfillment kinds (VIP_GRANT, STORY_UNLOCK, etc.)
- El flujo de usuario final (compra) — solo admin
- Encadenar creación de paquete desde otros lugares (solo desde producto)
- Tests en este spec (se definen en fase de tasks/apply)

## 4. Functional Requirements

### FR1: Botón de creación en wizard de producto
En el paso `selecting_package` del `ProductWizardStates`, cuando se muestran los paquetes disponibles, SIEMPRE debe aparecer un botón adicional "➕ Crear nuevo paquete" (después de la lista de paquetes, antes del botón Cancelar).

### FR2: Botón de creación en edición de producto
En el paso `selecting_package` del `ProductEditStates`, cuando se muestran los paquetes disponibles para editar, SIEMPRE debe aparecer un botón adicional "➕ Crear nuevo paquete".

### FR3: Guardado de contexto
Al presionar "Crear nuevo paquete", el sistema debe guardar en FSM data:
- Una clave `__return_context` con valor `"product_wizard"` o `"product_edit"`
- Para `product_wizard`: todos los datos acumulados del wizard (name, description, tier_id, tier_name, delivery_mode, fulfillment_kind)
- Para `product_edit`: el `product_id` que se está editando

### FR4: Inicio del wizard de paquete inline
Tras guardar el contexto, el sistema inicia el wizard de paquete desde `PackageWizardStates.waiting_name`, mostrando el mismo mensaje del paso 1 que usa `create_package_start`.

### FR5: Detección de contexto en wizard de paquete
El paso `confirming` del wizard de paquete (`show_package_preview` y `confirm_create_package`) debe detectar si existe `__return_context` en FSM data. Si existe, después de crear el paquete, en lugar de volver a `manage_packages`, debe restaurar el contexto del wizard de producto.

### FR6: Restauración y auto-selección
Al restaurar:
- Para `product_wizard`: se restauran todos los datos del wizard, se asigna `package_id = <nuevo_id>`, se avanza a `ProductWizardStates.waiting_price`, y se muestra el mensaje de precio con una nota de que el paquete fue creado y seleccionado.
- Para `product_edit`: se llama a `store_service.update_product(product_id, package_id=<nuevo_id>)`, se muestra confirmación, y se redirige al detalle del producto.

### FR7: Caso sin paquetes previos
Si no hay paquetes disponibles (lista vacía), el botón "Crear nuevo paquete" DEBE seguir apareciendo. Esto es el caso de uso principal: el admin entra a crear un producto, no hay paquetes, y quiere crear uno sin salir del wizard.

### FR8: Cancelación durante creación de paquete
Si el admin cancela durante el wizard de paquete (botón "❌ Cancelar" con callback_data="cancel"), el sistema debe restaurar el contexto del wizard de producto y volver al paso `selecting_package` (mostrando nuevamente la lista de paquetes, que ahora podría incluir el recién creado parcialmente... no, si canceló no se creó nada).

## 5. Technical Design

### 5.1 FSM Context Storage

La clave `__return_context` se almacena en FSM data como un string JSON o un dict serializable:

```python
# Al entrar al wizard de paquete desde producto:
return_context = {
    "source": "product_wizard",  # o "product_edit"
    "data": await state.get_data(),  # todos los datos del wizard actual
}
await state.update_data(__return_context=json.dumps(return_context))
```

Nota: `state.get_data()` devuelve un dict. Los valores son serializables (strings, ints, None). Se guarda como JSON string para evitar problemas con aiogram's FSM storage.

### 5.2 Callback Data

```python
class CreatePkgFromProductCallback(CallbackData, prefix="create_pkg_prod"):
    """Crear nuevo paquete desde flujo de selección de producto"""
    source: str  # "wizard" o "edit"
    product_id: int = 0  # solo usado en "edit"
```

### 5.3 Flujo detallado — Wizard de creación

```
[selecting_package]
  ├── SelectPkgProductCallback → asigna package_id → waiting_price
  ├── CreatePkgFromProductCallback(source="wizard") → guarda contexto → PackageWizardStates.waiting_name
  └── admin_store → cancela wizard

[PackageWizardStates.waiting_name → ... → confirming]
  └── confirm_create_package:
        ├── SIN __return_context → comportamiento normal (volver a manage_packages)
        └── CON __return_context:
              ├── source="wizard": restaura datos → package_id=nuevo_id → waiting_price
              └── source="edit": update_product(package_id=nuevo_id) → finish edit → product detail
```

### 5.4 Flujo detallado — Wizard de edición

```
[selecting_package (edit)]
  ├── SelectPkgEditProductCallback → update_product → finish edit
  ├── CreatePkgFromProductCallback(source="edit", product_id=X) → guarda contexto → PackageWizardStates.waiting_name
  └── EditProductCallback → volver a detalle producto

[PackageWizardStates... → confirming]
  └── confirm_create_package (con __return_context source="edit"):
        update_product(product_id, package_id=nuevo_id)
        → mensaje "Paquete creado y asignado"
        → product_admin_detail(product_id)
```

### 5.5 Mensajes

**Al entrar a crear paquete desde producto:**
Usar el mismo mensaje de `create_package_start` (Paso 1 de 6), sin cambios.

**Al volver del wizard con paquete creado (wizard creation):**
```
🎩 Lucien:

✨ Paquete "{nombre}" creado y seleccionado.

📋 Paso 6 de 6: Precio del producto

¿Cuántos besitos costará este producto?
Ejemplo: 100
```

**Al volver del wizard con paquete creado (product edit):**
```
🎩 Lucien:

✅ Paquete "{nombre}" creado y asignado al producto.
```
+ botones para ver producto y volver a tienda.

### 5.6 Lugares de modificación en package_handlers.py

En `show_package_preview` y/o `confirm_create_package`: detectar `__return_context` y rutear apropiadamente.

En los handlers de cancelación del wizard de paquete: si existe `__return_context`, restaurar en lugar de volver a `manage_packages`.

## 6. Files to Modify

| File | Change |
|------|--------|
| `keyboards/callback_data.py` | Agregar `CreatePkgFromProductCallback` |
| `handlers/store_admin_handlers.py` | Modificar `_wizard_prompt_package_selection` y `build_edit_package_buttons` para agregar botón; nuevo handler para `CreatePkgFromProductCallback` que guarda contexto e inicia wizard de paquete |
| `handlers/package_handlers.py` | Modificar `confirm_create_package` (y handlers de preview/cancel) para detectar `__return_context` y rutear retorno |
| `tests/handlers/test_store_admin_handlers.py` | Nuevos tests para el botón de creación + guardado de contexto + restauración |
| `tests/handlers/test_package_handlers.py` | Tests para detección de contexto en confirm + cancel |

## 7. Edge Cases

1. **Sin paquetes disponibles**: El botón "Crear nuevo paquete" debe aparecer incluso cuando la lista de paquetes está vacía.
2. **Cancelación en wizard de paquete**: Si el admin cancela (`/cancel` o botón "❌ Cancelar"), restaurar el contexto y volver al paso `selecting_package`.
3. **Múltiples creaciones**: Si el admin crea un paquete pero luego vuelve atrás en el wizard de producto y llega de nuevo a selección de paquete, el paquete recién creado debe aparecer en la lista.
4. **Paquete creado con store_stock=-2 (no disponible en tienda)**: Si el admin crea un paquete pero marca store_stock como "No disponible en tienda" (-2), el paquete NO debe aparecer en la lista de selección (consistente con `get_available_packages_for_store`). Sin embargo, SÍ debe poder ser asignado al producto actual porque es el que el admin acaba de crear con esa intención. Solución: forzar que el paquete se asigne, independientemente de su store_stock.
5. **FSM storage backend**: La lógica debe funcionar tanto con `MemoryStorage` como con `RedisStorage`. Los datos guardados en `__return_context` deben ser serializables.
6. **Timeout de FSM**: Si el admin tarda mucho en el wizard de paquete, el FSM del producto no debería expirar (el timeout se resetea al cambiar de estado).

## 8. Acceptance Criteria

- [ ] Existe botón "➕ Crear nuevo paquete" en la selección de paquete del wizard de creación de producto
- [ ] Existe botón "➕ Crear nuevo paquete" en la selección de paquete del wizard de edición de producto
- [ ] Al crear un paquete desde el wizard de producto, el sistema regresa automáticamente al paso de precio con el paquete asignado
- [ ] Al crear un paquete desde la edición de producto, el sistema asigna el paquete y muestra confirmación
- [ ] Al cancelar la creación de paquete, se regresa al paso de selección de paquete sin perder datos
- [ ] El botón aparece incluso cuando no hay paquetes disponibles
- [ ] El paquete recién creado se asigna correctamente incluso si tiene store_stock=-2
- [ ] Sin regresiones en el wizard de paquete standalone (crear desde `manage_packages` sigue funcionando igual)

## 9. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| FSM state clash entre ProductWizardStates y PackageWizardStates | Alto — cada user+chat solo puede tener un estado activo | Se limpia/setea explícitamente al cambiar entre wizards. Verificado en tests. |
| Pérdida de datos del wizard de producto al cambiar de estado | Alto — el admin perdería todo lo ingresado | Los datos se guardan en `__return_context` como JSON string antes de cambiar de estado. |
| Store stock -2 impide seleccionar el paquete recién creado | Medio — `get_available_packages_for_store` filtra -2 | Se fuerza la asignación directa sin pasar por la lista de disponibles. |
| Comportamiento divergente entre MemoryStorage y RedisStorage | Bajo — aiogram abstrae el storage | Se usa `state.update_data()` estándar. |

## 10. Open Questions

1. **¿El paquete se debe activar automáticamente (is_active=True)?** Actualmente `create_package` en `PackageService` crea con `is_active=True` por defecto. Verificar que esto aplica también al flujo inline.
2. **¿Mostrar un paso intermedio que confirme "Paquete creado: ¿desea seleccionarlo?" o avanzar directo?** El spec asume avance directo (más fluido). Si se prefiere confirmación intermedia, requiere un paso extra.
