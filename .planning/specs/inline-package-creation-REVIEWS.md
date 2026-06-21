---
phase: inline-package-creation
reviewers: [opencode]
reviewed_at: 2026-06-21T00:00:00Z
plans_reviewed: [.planning/specs/inline-package-creation-design.md]
---

# Cross-AI Design Review — Inline Package Creation

## OpenCode Review

### Summary

El diseño resuelve un problema UX real (pérdida de datos del wizard al necesitar crear un paquete intermedio) con una solución pragmática de FSM context switching. Sin embargo, el diseño subestima la complejidad del manejo de errores en el flujo de retorno, no aborda la deuda técnica de los imports circulares runtime, y no detecta que el `cancel` global en `common_handlers.py` representa un riesgo no mitigado. Adicionalmente, el diseño describe con exactitud lo que ya está implementado en el codebase, pero la documentación no señala gaps de cobertura de tests ni el patrón frágil de `from handlers.store_admin_handlers import ...` embebido en los handlers de paquete.

---

### Strengths

- **FSM context save/restore vía serialización JSON**: Correcto — evita colisión de keys entre wizards y funciona con MemoryStorage y RedisStorage. La elección de `json.dumps` sobre pickle es acertada (seguridad, portabilidad).
- **Cancel interception con state filter**: El handler decorado con `PackageWizardStates.*` + `F.data == "cancel"` efectivamente tiene prioridad sobre el `cancel` global sin state filter en `common_handlers.py`. La arquitectura de aiogram 3 lo garantiza.
- **Separación de responsabilidades**: El `_restore_product_context` helper vive en `package_handlers.py` donde ya existe el `PackageService`, evitando que `store_admin_handlers` necesite conocer detalles del package wizard.
- **store_stock=-2 handling**: El diseño menciona explícitamente que paquetes con stock `-2` (no disponible en tienda) deben ser asignables al producto — correcto.
- **Button aparece incluso con lista vacía**: Bien cubierto en el spec (FR7 y edge case 1).

---

### Concerns

#### HIGH — El error handler en `_restore_product_context` es incompleto

En el flujo `source == "product_edit"`:

```python
with get_service(StoreService) as store_service:
    store_service.update_product(product_id, package_id=package.id)
```

Si `update_product` falla (DB constraint, producto eliminado entre medio, etc.), la excepción burbujea al `except` de `confirm_create_package`. Ese catch RESTAURA el contexto del product wizard y muestra "Error creando paquete" — **pero el paquete YA fue creado exitosamente** en la DB. El admin no tiene visibilidad de que el paquete existe pero no se asignó.

**Mitigación sugerida**: Separar la transacción de creación del paquete de la asignación al producto. Si `update_product` falla, informar al admin que el paquete se creó pero hubo un error al asignarlo, con botones para reintentar la asignación.

#### HIGH — El cancel global (`common_handlers.py:237`) es un riesgo silencioso

El handler `cancel_action` en `common_handlers.py` NO tiene filtro de estado (no chequea `F.state`). Aunque los handlers decorados con state filter en `package_handlers.py` toman prioridad, el orden de registro de routers en `bot.py` es relevante:

```python
dp.include_router(common_router)      # línea 318
...
dp.include_router(package_router)     # línea 328
```

`package_router` se registra DESPUÉS de `common_router`. Si hay alguna ruta FSM state de `PackageWizardStates` que NO esté cubierta por los decoradores `@router.callback_query(PackageWizardStates.*, F.data == "cancel")` (6 estados actualmente cubiertos), el `cancel` caería al global sin restaurar `__return_context`, perdiendo datos del product wizard.

**Estado actual**: 6 estados cubiertos (`waiting_name`, `waiting_description`, `waiting_files`, `waiting_store_stock`, `waiting_reward_stock`, `confirming`). Si en el futuro se agrega un estado nuevo a `PackageWizardStates` y no se actualizan los decoradores, se pierden datos. Sugerencia: usar `PackageWizardStates` (sin estado específico) como filtro en el decorador de cancel para cubrir todos los estados automáticamente.

#### MEDIUM — Runtime imports frágiles en `package_handlers.py`

El diseño propone extraer `PackageWizardStates` a un archivo separado (sección 6), y esto YA está hecho en `handlers/states/package_states.py`. Sin embargo, `package_handlers.py` sigue importando `ProductWizardStates` y `ProductEditStates` de `store_admin_handlers` **a nivel función** (no top-level) en 4 lugares (líneas 779, 782, 802, 880, 888 del archivo real):

- `confirm_create_package`: lines 779, 782
- `cancel_package_wizard`: lines 880-883, 888
- `_restore_product_context`: line 802

Esto NO es un problema de circular imports gracias al lazy loading, pero es frágil:
- Si el módulo `store_admin_handlers` tiene un error de sintaxis o de import al cargarse, el runtime falla recién cuando se ejecuta el handler (no al iniciar el bot)
- Pyright/mypy no pueden verificar tipos en imports dinámicos
- Rompe el "principio de sorpresa mínima" — un handler en `package_handlers` no debería necesitar runtime imports de otro módulo handler

**Solución real**: Extraer `ProductWizardStates`, `ProductEditStates`, y la función `_wizard_prompt_package_selection` a un módulo compartido (e.g., `handlers/states/store_states.py`), siguiendo el mismo patrón que `package_states.py`. Esto eliminaría los runtime imports por completo.

#### MEDIUM — No hay handler para botones "Volver" específicos del contexto

Durante el wizard inline de paquete, los botones "🔙 Volver" de ciertos pasos apuntan a `manage_packages` (ver `ask_store_stock` line 523, `ask_reward_stock` line 599). Si el admin presiona "Volver" en lugar de "Cancelar" durante el flujo inline, vuelve al menú de paquetes y PIERDE el contexto del product wizard — porque esos callbacks NO pasan por el `cancel_package_wizard` handler.

El diseño no menciona esto como edge case. Los únicos botones de salida protegidos son los que disparan `F.data == "cancel"`.

#### LOW — Falta logging estandarizado

Los handlers nuevos (`create_package_for_product_wizard`, `create_package_for_product_edit`, `_restore_product_context`) no tienen logging del formato estándar del proyecto: `"módulo | acción | user_id | resultado"`.

#### LOW — UTF-8 / parse_mode inconsistente en mensajes al usuario

En `_restore_product_context`, el mensaje de restauración exitosa para wizard usa formato texto plano con `🎩 Lucien:\n\n` (sin HTML tags). El mensaje de creación de paquete standalone usa HTML completo con `<b>`, `<i>`. El restore path debería también especificar `parse_mode="HTML"` consistentemente.

---

### Suggestions

1. **Mover `ProductWizardStates` y `ProductEditStates` a un módulo compartido** (e.g., `handlers/states/store_states.py`) para eliminar los 4 runtime imports en `package_handlers.py`. Esto es trabajo que el diseño ya identificó para `PackageWizardStates` pero no llevó hasta el final — los states de producto también necesitan extracción.

2. **Separar creación de paquete de asignación a producto**: Usar dos transacciones. Si la asignación falla, mostrar botón de reintentar (`EditProductCallback(product_id=product_id)`) en vez de perder el paquete creado.

3. **Cubrir todos los botones de salida del package wizard**: Revisar `ask_store_stock` (botón "Volver" -> `manage_packages`), `ask_reward_stock` (mismo) y las funciones similares. Cualquier botón que limpie estado o navegue fuera del wizard debe detectar `__return_context` y restaurar.

4. **Agregar logging en todos los handlers nuevos** siguiendo el formato `"módulo | acción | user_id | resultado"`.

5. **Usar `PackageWizardStates` (sin estado específico) como filtro en el decorador de cancel** para cubrir todos los estados futuros automáticamente, en lugar de listar cada estado individualmente.

6. **Tests**: El diseño estima 120 LOC de tests, pero los gaps reales son más amplios:
   - No hay test para `CreatePkgForProductCallback` serialization/deserialization
   - No hay test para el error path (paquete creado pero `update_product` falla)
   - No hay test para `cancel` desde estados NO cubiertos por los decoradores (edge case de future-proofing)
   - No hay test para restore con `store_stock=-2`
   - No hay test para múltiples creaciones inline consecutivas

---

### Risk Assessment

**MEDIUM**

Justificación:
- El diseño es sólido conceptualmente y la implementación existente es correcta para el happy path. El FSM context switching está bien resuelto.
- El riesgo principal está en los **error paths no completamente cubiertos** (paquete creado pero asignación falla, cancel desde botones "Volver" no interceptados).
- Los **runtime imports** son deuda técnica que no se rompe hoy pero complica el mantenimiento futuro y el type-checking.
- La **ausencia de tests** combinada con la complejidad del FSM switching hace que regresiones sean difíciles de detectar.
- Los **logging gaps** dificultan debugging en producción si algo sale mal en el flujo cross-wizard.

---

## Consensus Summary

### Agreed Strengths
_(Single reviewer — no cross-reviewer consensus available)_

### Agreed Concerns
_(Single reviewer — no cross-reviewer consensus available)_

### Divergent Views
_(Single reviewer — no cross-reviewer consensus available)_

---

## Next Steps

Para incorporar el feedback en el plan:
1. Abordar los 2 concerns HIGH antes de mergear la feature
2. Extraer `ProductWizardStates`/`ProductEditStates` a `handlers/states/store_states.py`
3. Agregar tests para error paths y edge cases
4. Agregar logging estandarizado
