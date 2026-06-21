# DESIGN: Creación inline de paquete desde selección de producto

**Date:** 2026-06-21
**Depends on:** [inline-package-creation-spec.md](./inline-package-creation-spec.md)

---

## 1. Architecture Decision

### FSM Context Switching

El desafío central: un user+chat solo puede tener un FSM state activo. Al pasar de `ProductWizardStates` a `PackageWizardStates`, los datos de ambos wizards colisionan (ambos usan keys como `name`, `description`).

**Decisión**: Serializar todos los datos del wizard de producto como JSON bajo una sola key `__return_context` antes de hacer `state.clear()` y comenzar el wizard de paquete. Al restaurar, hacer `state.clear()` → `state.update_data(**saved_data)` → `state.set_state(...)`.

### Cancel Handling

El handler global `F.data == "cancel"` en `common_handlers.py` no limpia el FSM state. Para el flujo inline, necesitamos interceptar cancel durante `PackageWizardStates` y restaurar el contexto del wizard de producto.

**Decisión**: Agregar un handler específico en `package_handlers.py` que filtre por `PackageWizardStates.*` + `F.data == "cancel"`. Como tiene filtro de estado, toma prioridad sobre el handler global sin filtro.

---

## 2. Callback Data

Agregar en `keyboards/callback_data.py`:

```python
class CreatePkgForProductCallback(CallbackData, prefix="create_pkg_prod"):
    """Crear nuevo paquete desde flujo de selección de producto"""
    source: str  # "wizard" o "edit"
    product_id: int = 0  # solo usado en source="edit"
```

---

## 3. Changes: `handlers/store_admin_handlers.py`

### 3.1 Modificar `_wizard_prompt_package_selection` (línea ~752)

Agregar botón "➕ Crear nuevo paquete" después de la lista de paquetes, antes de "Cancelar".

```
[Paquete 1]
[Paquete 2]
...
[➕ Crear nuevo paquete]   ← NUEVO
[❌ Cancelar]
```

El botón usa `CreatePkgForProductCallback(source="wizard").pack()`.

**Caso sin paquetes**: Cambiar el mensaje de "no hay paquetes" para incluir el botón de creación en lugar de solo "Volver".

### 3.2 Modificar `build_edit_package_buttons` (línea ~317)

Agregar botón "➕ Crear nuevo paquete" después de la lista, antes de "Cancelar".

La función necesita recibir `product_id` (ya lo recibe) y devolver el botón extra con `CreatePkgForProductCallback(source="edit", product_id=product_id).pack()`.

### 3.3 Nuevo handler: `create_package_from_product_selection`

```python
@router.callback_query(
    ProductWizardStates.selecting_package,
    CreatePkgForProductCallback.filter(F.source == "wizard"),
)
async def create_package_for_wizard(callback, state, callback_data):
    # 1. Guardar contexto
    wizard_data = await state.get_data()
    return_context = {"source": "product_wizard", "data": wizard_data}
    await state.clear()
    await state.update_data(__return_context=json.dumps(return_context))
    await state.set_state(PackageWizardStates.waiting_name)

    # 2. Mostrar paso 1 del wizard de paquete (mismo mensaje que create_package_start)
    await callback.message.edit_text(
        # ... mensaje estándar del paso 1 de 6 ...
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
```

### 3.4 Nuevo handler: `create_package_from_edit_selection`

```python
@router.callback_query(
    ProductEditStates.selecting_package,
    CreatePkgForProductCallback.filter(F.source == "edit"),
)
async def create_package_for_edit(callback, state, callback_data):
    product_id = callback_data.product_id
    # Guardar solo edit_product_id (es lo único que necesita el edit flow)
    return_context = {"source": "product_edit", "data": {"edit_product_id": product_id}}
    await state.clear()
    await state.update_data(__return_context=json.dumps(return_context))
    await state.set_state(PackageWizardStates.waiting_name)
    # ... mismo mensaje paso 1 ...
```

---

## 4. Changes: `handlers/package_handlers.py`

### 4.1 Modificar `confirm_create_package` (línea ~745)

Después de crear el paquete exitosamente y antes de `state.clear()`, chequear `__return_context`:

```python
data = await state.get_data()
return_context_raw = data.get("__return_context")

if return_context_raw:
    await _restore_product_context(callback, state, package, return_context_raw)
else:
    # Comportamiento normal (sin cambios)
    await callback.message.edit_text(...)
    await state.clear()
```

### 4.2 Nueva helper: `_restore_product_context`

```python
async def _restore_product_context(target, state, package, return_context_raw):
    import json
    return_context = json.loads(return_context_raw)
    source = return_context["source"]
    saved_data = return_context["data"]

    await state.clear()

    if source == "product_wizard":
        from handlers.store_admin_handlers import ProductWizardStates
        saved_data["package_id"] = package.id
        await state.update_data(**saved_data)
        await state.set_state(ProductWizardStates.waiting_price)
        text = (
            f"🎩 Lucien:\n\n"
            f"✨ Paquete \"{package.name}\" creado y seleccionado.\n\n"
            f"📋 Paso 6 de 6: Precio del producto\n\n"
            f"¿Cuántos besitos costará este producto?\n"
            f"Ejemplo: 100"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancelar", callback_data="admin_store")]
        ])
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=keyboard)
        else:
            await target.answer(text, reply_markup=keyboard)

    elif source == "product_edit":
        from services import get_service
        from services.store_service import StoreService
        product_id = saved_data["edit_product_id"]
        with get_service(StoreService) as store_service:
            store_service.update_product(product_id, package_id=package.id)
        await target.message.edit_text(
            f"🎩 Lucien:\n\n✅ Paquete \"{package.name}\" creado y asignado al producto.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📦 Ver producto",
                    callback_data=ProductAdminDetailCallback(product_id=product_id).pack(),
                )],
                [InlineKeyboardButton(text="🔙 Tienda", callback_data="admin_store")],
            ]),
        )
```

Wait, `ProductAdminDetailCallback` needs to be imported. Let me adjust — use a `back_keyboard("admin_store")` instead, or import it.

### 4.3 Nuevo handler: `cancel_package_wizard_for_product_flow`

Intercepta `F.data == "cancel"` durante cualquier estado de `PackageWizardStates`:

```python
@router.callback_query(PackageWizardStates.waiting_name, F.data == "cancel")
@router.callback_query(PackageWizardStates.waiting_description, F.data == "cancel")
@router.callback_query(PackageWizardStates.waiting_files, F.data == "cancel")
@router.callback_query(PackageWizardStates.waiting_store_stock, F.data == "cancel")
@router.callback_query(PackageWizardStates.waiting_reward_stock, F.data == "cancel")
@router.callback_query(PackageWizardStates.confirming, F.data == "cancel")
async def cancel_package_from_product(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    return_context_raw = data.get("__return_context")

    if not return_context_raw:
        # Comportamiento normal standalone
        await state.clear()
        await callback.message.edit_text(
            "🎩 Lucien:\n\nAcción cancelada.",
            reply_markup=back_keyboard("manage_packages"),
            parse_mode="HTML",
        )
        await callback.answer("Acción cancelada")
        return

    return_context = json.loads(return_context_raw)
    source = return_context["source"]
    saved_data = return_context["data"]

    await state.clear()
    await state.update_data(**saved_data)

    if source == "product_wizard":
        await state.set_state(ProductWizardStates.selecting_package)
        # Re-show package selection via _wizard_prompt_package_selection
        await _wizard_prompt_package_selection(callback, state)
    elif source == "product_edit":
        await state.set_state(ProductEditStates.selecting_package)
        product_id = saved_data["edit_product_id"]
        with get_service(StoreService) as store_service:
            packages = store_service.get_packages_for_product_edit(product_id)
        text = "🎩 Lucien:\n\nSelecciona el nuevo paquete:"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=build_edit_package_buttons(product_id, packages)
        )
        await callback.message.edit_text(text, reply_markup=keyboard)

    await callback.answer()
```

**Nota**: Para que el handler de cancel específico tome prioridad sobre el global, usamos `@router.callback_query(State, F.data == "cancel")`. En aiogram 3, los handlers con filtro de estado son más específicos y toman prioridad sobre los que no lo tienen.

---

## 5. Imports necesarios

### En `package_handlers.py`:
```python
import json  # si no está ya
from keyboards.callback_data import ProductAdminDetailCallback  # para edit flow
from services import get_service  # ya está
from services.store_service import StoreService  # nuevo
```

### En `store_admin_handlers.py`:
```python
from keyboards.callback_data import CreatePkgForProductCallback  # nuevo
from handlers.package_handlers import PackageWizardStates  # nuevo (para iniciar wizard)
import json  # si no está ya
```

**Precaución**: La importación de `PackageWizardStates` desde `package_handlers` podría crear una dependencia circular (store_admin_handlers → package_handlers). Los handlers no deberían importarse entre sí según las reglas de arquitectura.

**Alternativa**: Mover `PackageWizardStates` a un archivo compartido (ej. `handlers/states/`), o definir la lógica de inicio del wizard inline sin importar. O mejor: usar el callback_data `create_package` y dejar que el router de `package_handlers.py` maneje el inicio del wizard. Esto evita la importación circular.

**Decisión revisada**: El handler en `store_admin_handlers.py` solo debe:
1. Guardar `__return_context` en FSM data
2. Hacer `state.clear()`
3. Usar un callback_data especial que redirija a `create_package_start`

No, espera. `create_package_start` espera `F.data == "create_package"` y no tiene filtro de estado. Si hacemos `state.clear()` primero, no hay estado activo. Y `create_package_start` no filtra por estado, así que lo atraparía.

Pero hay un problema: después de `state.clear()`, no podemos editar el mensaje directamente con `callback.message.edit_text()` porque... bueno, en realidad sí podemos, el callback tiene la referencia al mensaje.

Entonces el flujo es:
1. Handler en store_admin recibe el callback `CreatePkgForProductCallback`
2. Guarda `__return_context` + hace `state.clear()`
3. Edita el mensaje para mostrar paso 1 del wizard de paquete (mismo texto que `create_package_start`)
4. Setea `state.set_state(PackageWizardStates.waiting_name)`
5. Esto requiere importar `PackageWizardStates`

La importación circular se rompe si movemos `PackageWizardStates` a `handlers/states/package_states.py`. Pero eso es un refactor extra. 

Alternativa más simple: manejarlo todo desde `package_handlers.py`. El handler en `store_admin_handlers.py` solo:
1. Guarda contexto
2. Redirige a un callback_data nuevo (ej. `pkg_wizard_start_from_product`) 
3. Ese callback es manejado por `package_handlers.py` que muestra el paso 1

Pero eso requiere un ciclo extra de callback. No es ideal.

**Mejor enfoque**: Definir el mensaje y estado inline sin importar `PackageWizardStates`. Las `State` instances son solo objetos; podemos obtenerlas del dispatcher o del FSM context. Pero no hay forma limpia.

**Enfoque pragmático**: Mover `PackageWizardStates` a `handlers/states/package_states.py`. Es un cambio pequeño (6 líneas) que evita la dependencia circular y sigue el patrón existente de `handlers/states/store_fulfillment_states.py`.

Archivos afectados por el move:
- `handlers/package_handlers.py` → importar de `handlers.states.package_states`
- `handlers/store_admin_handlers.py` → importar de `handlers.states.package_states`

---

## 6. Resumen de archivos modificados

| File | Change | LOC est. |
|------|--------|----------|
| `handlers/states/package_states.py` | **NUEVO** — extraer `PackageWizardStates`, `SendPackageStates`, `UpdatePackageStates`, `DeleteFileStates` | ~20 |
| `handlers/package_handlers.py` | Importar states del nuevo archivo; modificar `confirm_create_package` (+25L); agregar handler de cancel para product flow (+35L); agregar helper `_restore_product_context` (+30L) | +90 |
| `keyboards/callback_data.py` | Agregar `CreatePkgForProductCallback` | +6 |
| `handlers/store_admin_handlers.py` | Modificar `_wizard_prompt_package_selection` (+5L); modificar `build_edit_package_buttons` (+4L); nuevo handler wizard (+20L); nuevo handler edit (+20L) | +50 |
| `tests/handlers/test_store_admin_handlers.py` | Tests para botón + guardado de contexto | ~60 |
| `tests/handlers/test_package_handlers.py` | Tests para detección de contexto + cancel + restauración | ~60 |

---

## 7. Testing Strategy

### En `test_store_admin_handlers.py`:
- `TestPackageSelectionCreateButton`: Verifica que el botón "➕ Crear nuevo paquete" aparece en la lista de paquetes
- `TestPackageSelectionCreateButtonNoPackages`: Verifica que el botón aparece incluso sin paquetes
- `TestCreatePkgForWizardSavesContext`: Verifica que al presionar el botón, `__return_context` se guarda con `source="product_wizard"` y los datos del wizard
- `TestCreatePkgForEditSavesContext`: Similar para edit flow
- `TestEditPackageButtonsHasCreateButton`: Verifica botón en `build_edit_package_buttons`

### En `test_package_handlers.py`:
- `TestConfirmCreatePackageWithReturnContext`: Verifica que al confirmar con `__return_context={"source": "product_wizard", ...}`, se restaura el contexto y avanza a `waiting_price`
- `TestConfirmCreatePackageWithReturnContextEdit`: Similar para edit, verifica que se llama `update_product`
- `TestConfirmCreatePackageWithoutContext`: Verifica comportamiento normal (sin `__return_context`)
- `TestCancelPackageWizardRestoresContext`: Verifica que cancelar durante package wizard con `__return_context` restaura el wizard de producto
- `TestCancelPackageWizardWithoutContext`: Verifica cancel normal

---

## 8. Rollback Plan

Si algo falla:
1. Revertir cambios en `store_admin_handlers.py` y `package_handlers.py`
2. Eliminar `CreatePkgForProductCallback` de `callback_data.py`
3. Eliminar `handlers/states/package_states.py` y restaurar imports
4. El wizard de paquete standalone (`manage_packages → create_package`) no se ve afectado
