# 📊 Análisis de Impacto: Broadcast Link Buttons Wizard Integration (ITEM 2 of 3)

## Cambio Propuesto
**ITEM 2 (tight scope)**: Integrar el botón extra (a lo sumo 1) en el flujo de broadcast.
- Extender FSM/wizard en `broadcast_handlers.py`: después de reacciones (o integrado), decisión opcional + selección de exactamente 1 botón del catálogo activo (similar a toggle de emoji pero single choice, "ninguno" default).
- Actualizar preview para mostrar "Botón extra: label (url) o ninguno".
- Modificar `create_broadcast_message` para aceptar `extra_button_id: int | None`, almacenarlo.
- Extender `build_send_reaction_markup` (o nuevo helper `build_broadcast_markup`) para retornar InlineKeyboard combinado (fila de reacciones + fila opcional de botón url).
- En `confirm_and_send`: pasar botón seleccionado, construir markup con reacciones (si hay) + botón extra (si elegido), adjuntar al send o edit.
- Actualizar `refresh_reaction_markup_counts` en `gamification_user_handlers` para preservar el botón extra al reconstruir conteos.
- Manejar "sin extra" como None.
- Agregar callbacks necesarios (e.g. ToggleExtraButton o select one).
- Actualizar textos de pasos (conteo de Paso X de Y puede cambiar).
- **NO** flip de reacciones por defecto (eso es ITEM 3).
- **NO** cambios en service más allá de extensión de firma si es necesario (CRUD ya está en ITEM 1).
- Actualizar docs mínimamente.

**Restricción clave:** siempre a lo sumo UN botón extra. UI de selección debe enforzar single choice.

## Riesgo Total: ALTO (para ITEM 2; pre-existente + nuevo wiring)

**Justificación:**
- Toca el flujo principal de broadcast (wizard FSM + send path) que es el "broadcast domain".
- `confirm_and_send_broadcast` ya tiene **173 LOC** (violación pre-existente de regla <=50 LOC). Agregar lógica de botón extra la empeora o requiere split.
- `build_send_reaction_markup` (función pura) y `refresh_reaction_markup_counts` son puntos de contacto con markup de reacciones enviadas.
- `reactions_keyboard_with_counts` en `inline_keyboards.py` se usa tanto en handlers como en tests de integración (full chain). Si se construye un nuevo markup combinado, hay que decidir si esa función se extiende o se crea un helper nuevo.
- El catálogo (`BroadcastButton` + `get_all_buttons`) ya existe (ITEM 1); la integración lo "activa".
- **0 impacto en atomicidad de reacciones:** markup es post-send best-effort. `check_and_register_reaction`, credit paths, EventBus observers permanecen intactos.
- **Riesgo de pasos del wizard:** agregar un paso (o integrarlo) cambia "Paso X de 6" → puede requerir renumeración o re-estructuración de back-navigation.
- **Gap administrativo:** NO existe UI admin para definir botones (catalog CRUD solo en service). El scope de ITEM 2 asume que "ya hay botones activos" — si no los hay, el flujo de selección queda vacío o requiere "ninguno".

## Mapa de Impacto Directo

| Archivo | Línea(s) | Por qué se ve afectado |
|---------|----------|------------------------|
| `handlers/broadcast_handlers.py` | 34-54 (`build_send_reaction_markup`) | Debe extenderse o delegar a helper que incluya botón url opcional como fila adicional |
| `handlers/broadcast_handlers.py` | 58-66 (`BroadcastStates`) | Posible nuevo estado (e.g. `waiting_extra_button_decision`, `selecting_extra_button`) |
| `handlers/broadcast_handlers.py` | 288-318 (`ask_for_reactions`) | Lugar lógico para insertar paso "botón extra" después de reacciones (o integrar en el mismo paso) |
| `handlers/broadcast_handlers.py` | 389-434 (`show_reaction_selection`) | ~46 LOC ya cerca del límite; si se fusiona selección de botón aquí, puede romper <=50 |
| `handlers/broadcast_handlers.py` | 618-664 (`show_broadcast_preview`) | ~47 LOC; debe leer `extra_button_id` o `selected_extra_button` del state y mostrar "Botón extra: ..." |
| `handlers/broadcast_handlers.py` | 712-885 (`confirm_and_send_broadcast`) | **173 LOC**; lee `selected_emojis`, llama `create_broadcast_message`, construye `reaction_markup`, envía, edita markup. Debe: (a) leer selección de botón extra del state, (b) pasar `extra_button_id` a create, (c) construir markup combinado, (d) adjuntar al edit. Riesgo de crecer más o requerir refactor. |
| `handlers/broadcast_handlers.py` | 727 (`create_broadcast_message` call) | Firma actual NO acepta `extra_button_id`. Debe cambiarse para pasarlo. |
| `handlers/gamification_user_handlers.py` | 214-236 (`refresh_reaction_markup_counts`) | Reconstruye markup SOLO con reacciones vía `reactions_keyboard_with_counts`. Debe preservar el botón extra si `broadcast.extra_button_id` está seteado. |
| `handlers/gamification_user_handlers.py` | 267 (`refresh` call site en `handle_reaction`) | Pasa `broadcast` (que ahora puede tener `extra_button_id`); el callee debe usarlo. |
| `services/broadcast_service.py` | 176-206 (`create_broadcast_message`) | Firma debe aceptar `extra_button_id: int | None = None` y almacenarlo en el modelo. |
| `services/broadcast_service.py` | 235-243 (`get_selected_emoji_ids`) | Posible simetría: helper `get_extra_button_id(broadcast_id)` o simplemente leer `broadcast.extra_button_id` tras `get_broadcast`. |
| `keyboards/callback_data.py` | ~733+ (sección BROADCAST) | Agregar nuevo CallbackData: e.g. `ToggleExtraButtonCallback` o `SelectExtraButtonCallback(button_id: int)` + acción "ninguno". |
| `keyboards/inline_keyboards.py` | 582-605 (`reactions_keyboard_with_counts`) | Se usa para reconstruir markup en reactions. Posible nuevo helper `broadcast_markup_with_extra(broadcast_id, emojis, counts, extra_button)` o extensión. Usado en tests de integración. |
| `models/models.py` | 306-308 (`extra_button_id` column) | Ya existe (ITEM 1). Código de ITEM 2 lo leerá/escribirá. |

## Mapa de Impacto Indirecto

| Archivo | Cadena de dependencia | Notas |
|---------|-----------------------|-------|
| `tests/integration/test_callbackdata_broadcast.py` | `test_build_send_reaction_markup_uses_reaction_callback` importa `build_send_reaction_markup` de handlers | Se verá afectado si la firma o el retorno cambia. Debe seguir produciendo ReactionCallbacks para emojis. |
| `tests/integration/test_reaction_full_chain.py` | Crea `BroadcastMessage` directo + usa `reactions_keyboard_with_counts` + llama `update_reaction_message` | Fixtures crean sin `extra_button_id` (nullable → OK). Si tests reconstruyen markup, deben seguir funcionando. |
| `tests/integration/test_cross_service_atomicity.py` | Crea `BroadcastMessage` en setup | Nullable FK → no impacto. |
| `tests/integration/test_invariants.py` | Crea `BroadcastMessage` | Igual. |
| `tests/integration/test_reaction_mission_flow.py` | Crea `BroadcastMessage` | Igual. |
| `tests/integration/test_reaction_limit.py` | Crea `BroadcastMessage` | Igual. |
| `tests/unit/test_broadcast_service.py` | `test_create_broadcast_message` llama a `create_broadcast_message` sin extra | Debe seguir pasando (param nuevo con default). Test ligero para FK ya existe. |
| `tests/conftest.py` | `sample_broadcast_message` fixture | Crea sin `extra_button_id`. OK (nullable). |
| `tests/handlers/test_gamification_user_handlers.py` | `TestHandleReaction.test_updates_reaction_counts` mockea `update_reaction_message` + `get_selected_emoji_ids` etc. | Si `refresh_reaction_markup_counts` cambia para leer `extra_button_id` del broadcast, los mocks deben proveer un broadcast con ese attr (o el código debe tolerar None). |
| `bot.py` | Registro de routers | NO cambia. |
| `services/__init__.py` | Export de `BroadcastService` | Ya exportado; nuevo param no requiere cambios aquí. |

## Estados y Callbacks Nuevos (identificados)

**Estados FSM actuales (BroadcastStates):**
```
selecting_channel
waiting_text
waiting_attachment_decision
waiting_attachment
waiting_reaction_decision
selecting_reactions
waiting_protection_decision
confirming
```

**Opción A (recomendada por scope "after reactions"):** Insertar entre reacciones y protección:
- `waiting_extra_button_decision` (¿agregar botón extra?)
- `selecting_extra_button` (elegir 1 de la lista activa, o "ninguno")

**Opción B (integrado):** Dentro de `selecting_reactions` o un paso combinado "reacciones + botón extra". Menos estados, pero UI más densa.

**Callbacks nuevos sugeridos (en callback_data.py):**
- `ToggleExtraButtonCallback(button_id: int)` — similar a `ToggleReactionCallback`, pero para selección single
- O `SelectExtraButtonCallback(button_id: int | 0)` donde 0 = ninguno
- Acción "ninguno" puede ser un F.data literal o un callback con id=0

**UI de selección single choice:**
- Lista de botones activos + "⏭️ Ninguno" (default)
- Al seleccionar uno, deseleccionar cualquier otro (a diferencia de emojis que son multi)
- "✅ Continuar" solo si hay 0 o 1 seleccionado (siempre es el caso con single choice)

## Riesgos a Funciones Largas (>50 LOC)

| Función | LOC actual | Acción al tocar |
|---------|------------|-----------------|
| `confirm_and_send_broadcast` | **173** | Ya viola regla. Agregar botón extra aumenta riesgo. **Recomendación:** extraer helpers puros (e.g. `build_final_send_markup`, `persist_broadcast_from_state`) ANTES o DURANTE ITEM 2 para mantener delta pequeño. Si no se splitea, documentar como pre-existente. |
| `show_reaction_selection` | 46 | Cerca del límite. Si se fusiona selección de botón aquí, puede romper. |
| `show_broadcast_preview` | 47 | Cerca del límite. Mostrar "Botón extra" añade texto; mantener <=50. |
| `build_send_reaction_markup` | 21 | Función pura pequeña; OK extender o delegar. |

**Hardener rule:** <=50 LOC. Si ITEM 2 toca `confirm_and_send_broadcast`, debe o bien (a) no crecerla neto (refactor + agregar), o (b) extraer primero. El scope de ITEM 2 NO prohíbe split, pero dice "flag if long funcs >50? split if so".

## Riesgo de Atomicidad

**BAJO (casi nulo).**
- El markup (reacciones + botón extra) se adjunta **después** del send exitoso (edit_message_reply_markup).
- `check_and_register_reaction` NO lee `extra_button_id`; solo valida `has_reactions` + `selected_emoji_ids`.
- Los paths de crédito (REACTION) permanecen intactos.
- EventBus observers (besitos_awarded) no se ven afectados.
- `refresh_reaction_markup_counts` es best-effort (swallow "not modified", log warnings).
- Gold tests de atomicidad (`cross_service_atomicity`, `reaction_full_chain`, etc.) crean BroadcastMessage sin `extra_button_id`; el FK nullable garantiza compatibilidad.

## Tests que DEBES Correr Antes (baseline de ITEM 1 + golds)

```bash
# Pre-flight (igual que ITEM 1, confirmar estado limpio)
pytest tests/integration/test_alembic_heads.py tests/unit/test_broadcast_service.py tests/unit/test_broadcast_service_reaction_flow.py tests/integration/test_cross_service_atomicity.py tests/integration/test_reaction_full_chain.py tests/integration/test_invariants.py -v --tb=line -q -p no:cov --override-ini="addopts="

# Adicionales del PLAN de ITEM 1 (Task 5)
pytest tests/integration/test_reaction_limit.py -v --tb=line -q
pytest tests/integration/test_reaction_mission_flow.py -v --tb=line -q
pytest tests/integration/test_callbackdata_broadcast.py -v --tb=line -q
pytest tests/handlers/test_gamification_user_handlers.py -v -k "reaction or Reaction" --tb=line -q
pytest tests/handlers/ -v -k "broadcast" --tb=line -q 2>/dev/null || echo "No dedicated broadcast handler tests (smoke only via callbackdata)"

# Post-ITEM 2 (después de cambios): re-ejecutar TODOS los anteriores + smoke manual del wizard si es posible
```

## Tests que FALTAN (riesgo no cubierto)

- [ ] `test_broadcast_send_with_extra_button` — no existe (handler flow: seleccionar botón → create con FK → markup combinado)
- [ ] `test_broadcast_send_without_extra_button_default_none` — no existe
- [ ] `test_refresh_reaction_markup_preserves_extra_button` — no existe (gamification_user_handlers)
- [ ] `test_build_broadcast_markup_includes_url_button_when_extra_selected` — no existe (o test de `build_send_reaction_markup` extendido)
- [ ] `test_single_choice_enforced_in_extra_button_selection` — no existe (UI debe permitir 0 o 1, no más)
- [ ] `test_preview_shows_extra_button_label_and_url` — no existe
- [ ] `test_create_broadcast_message_accepts_extra_button_id` — unit service test faltante (solo test genérico de create message existe)
- [ ] `test_callbackdata_extra_button_unique_prefix` — no existe (evitar colisiones con bc_*)
- [ ] `test_reaction_callback_still_works_with_combined_markup` — integración (el ReactionCallback debe seguir parseando aunque el markup tenga 2 filas)

**Nota:** `TestBroadcastButton` (6 tests) ya existe de ITEM 1 y cubre CRUD del catálogo. No es necesario re-agregar.

## Precauciones Específicas

1. **"Ninguno" default:** El state debe inicializar `extra_button_id=None` o `selected_extra=None`. Si el usuario nunca toca la selección, el broadcast se crea sin botón extra.

2. **Single choice enforcement:** A diferencia de emojis (multi-select toggle), la selección de botón extra debe reemplazar cualquier selección previa. UI debe reflejar "✅" en uno solo.

3. **Back navigation step counts:** Si se inserta un paso nuevo, los callbacks `broadcast_back_*` y `broadcast_back_keyboard` deben mapear correctamente el nuevo estado. Los strings "Paso X de 6" deben actualizarse consistentemente (o decidir no renumerar y aceptar "6+" o redefinir).

4. **Preview muestra botón extra:** En `show_broadcast_preview`, leer del state:
   ```python
   extra_id = data.get("extra_button_id")
   if extra_id:
       btn = broadcast_service.get_broadcast_button(extra_id)
       text += f"   • Botón extra: {btn.label} ({btn.url})\n"
   else:
       text += "   • Botón extra: ❌\n"
   ```
   Cuidado con None y con que el servicio esté disponible en preview (actualmente preview no abre servicio; puede necesitarlo).

5. **Markup combinado:**
   - Fila 0: reacciones (si hay)
   - Fila 1 (opcional): [InlineKeyboardButton(text=label, url=url)]
   - `build_send_reaction_markup` retorna `InlineKeyboardMarkup | None`. Si hay extra pero no reacciones, debe retornar markup con solo la fila del botón url.
   - Si hay ambos, retornar markup con 2 filas.

6. **refresh_reaction_markup_counts debe tolerar extra_button:**
   ```python
   extra_id = broadcast.extra_button_id  # o service.get_extra_button_id(broadcast_id)
   extra_btn = broadcast_service.get_broadcast_button(extra_id) if extra_id else None
   # construir reactions row + (si extra_btn: url row)
   # usar reactions_keyboard_with_counts o nuevo helper
   ```
   Si `reactions_keyboard_with_counts` no acepta extra, crear un helper o componer.

7. **Admin config gap (flagged):**
   - Actualmente NO hay UI para crear/listar/toggle botones de enlace (gamification_admin_handlers no menciona "botón" ni "enlace extra").
   - ITEM 2 asume que el catálogo ya tiene botones activos (o el flujo de selección mostrará lista vacía).
   - Si el usuario quiere "definir primero", eso es trabajo admin separado (posiblemente ITEM futuro o pre-requisito manual via servicio).
   - **Decisión:** ITEM 2 NO agrega admin UI a menos que el scope se amplíe explícitamente. Documentar que para usar el feature, alguien debe crear botones vía `BroadcastService.create_broadcast_button` (o se agrega UI en un slice posterior).

8. **Servicio: extensión mínima:**
   - Agregar param a `create_broadcast_message` es OK.
   - No se requiere nuevo método tipo `get_extra_button_for_broadcast` si `get_broadcast` ya retorna el objeto con el FK poblado. Se puede exponer helper por simetría con `get_selected_emoji_ids`, pero no es obligatorio.

9. **CallbackData prefix uniqueness:**
   - Prefijos broadcast actuales: `bc_channel`, `bc_reaction`, `bc_protect`
   - Nuevo: usar `bc_extra` o `bc_button` (verificar en `TestBroadcastCallbacksNoCollisions`).

10. **get_service contract:**
    - BroadcastService ya se usa via `with get_service(...)`. No cambiar `__init__`.
    - El nuevo param en create es transparente.

## Recomendación

**SÍ vale la pena el cambio**, con estas condiciones:

1. **Decidir la inserción del paso ANTES de codificar:**
   - Opción A (after reactions): estados nuevos + back nav nuevo. Más claro, más LOC.
   - Opción B (integrated): menor delta de estados, pero UI más compleja.
   - Handoff al planner: proponer una, documentar trade-off.

2. **Atacar la función larga `confirm_and_send_broadcast` (173 LOC):**
   - Antes de agregar lógica de botón, extraer al menos:
     - `persist_broadcast_record(state_data, admin_id) -> BroadcastMessage`
     - `build_final_reply_markup(selected_emojis, extra_button) -> InlineKeyboardMarkup | None`
   - Esto reduce el riesgo de crecer más allá de 50 y mejora mantenibilidad.
   - Si no se hace split en ITEM 2, registrar como deuda conocida.

3. **Mantener "reactions_keyboard_with_counts" estable o versionar:**
   - Los tests de integración (full_chain) la llaman directamente.
   - Si se extiende, mantener firma existente y agregar un helper nuevo para el caso combinado.
   - Alternativa: en `refresh_reaction_markup_counts`, si hay extra_button, construir markup manualmente (2 filas) sin tocar la función de solo reacciones.

4. **Actualizar tests de handler reaction para mockear extra_button:**
   - `test_updates_reaction_counts` mockea `get_broadcast.return_value = MagicMock(has_reactions=True, ...)`.
   - Agregar `extra_button_id=None` explícitamente, o asegurar que el código en refresh no asuma que el attr existe (usa `getattr` o accede vía servicio).

5. **Cobertura mínima para ITEM 2:**
   - Al menos 1 test de integración o handler que ejerza el camino "seleccionar botón extra → enviar → markup tiene url button".
   - Test de "sin botón extra" (default).
   - Test de refresh que preserva botón extra.
   - Actualizar `test_callbackdata_broadcast.py` si `build_send_reaction_markup` firma cambia.

6. **Alternativa de menor impacto:**
   - Si se quiere evitar tocar `confirm_and_send_broadcast` extensamente, se puede post-procesar el broadcast después de crear: `broadcast_service.set_extra_button(broadcast.id, extra_id)`.
   - Esto aísla el wiring de envío, pero requiere un método nuevo en service y una segunda lectura del state.

7. **Documentación:**
   - Actualizar CLAUDE.md de handlers/services si se introduce patrón nuevo (single choice para botones).
   - Mínimo: nota en broadcast_handlers.py sobre "extra button is at most 1".

## Hand-off a gsd-planner (decisiones clave)

**Archivos a modificar (orden sugerido):**
1. `keyboards/callback_data.py` — agregar CallbackData para extra button (antes de handlers que lo usan)
2. `services/broadcast_service.py` — extender firma de `create_broadcast_message(extra_button_id: int | None = None)`
3. `keyboards/inline_keyboards.py` — decidir: extender `reactions_keyboard_with_counts` o nuevo helper `build_broadcast_markup`
4. `handlers/broadcast_handlers.py`:
   - Agregar estados FSM
   - Agregar paso UI (ask/select extra)
   - Actualizar preview
   - Actualizar `build_send_reaction_markup` o delegar
   - Actualizar `confirm_and_send` (leer state, pasar a create, construir markup combinado)
5. `handlers/gamification_user_handlers.py` — modificar `refresh_reaction_markup_counts` para preservar extra
6. Tests:
   - `tests/unit/test_broadcast_service.py` — test unit para create con extra_button_id
   - `tests/integration/test_callbackdata_broadcast.py` — verificar markup combinado si aplica
   - `tests/handlers/test_gamification_user_handlers.py` — actualizar mocks de refresh test
   - Nuevos tests de flujo (handler o integración) para selección + envío + refresh

**Tests exactos a re-correr (post):**
```bash
pytest tests/integration/test_alembic_heads.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/unit/test_broadcast_service.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/unit/test_broadcast_service_reaction_flow.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_cross_service_atomicity.py -q -k "cross_service_atomicity or TestCrossServiceAtomicity" --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_reaction_full_chain.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_invariants.py -q -k "reaction" --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_reaction_limit.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_reaction_mission_flow.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_callbackdata_broadcast.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/handlers/test_gamification_user_handlers.py -q -k "reaction or Reaction" --tb=line -p no:cov --override-ini="addopts="
```

**Decisiones para planner:**
- ¿Dónde insertar el paso de botón extra en el wizard? (after reactions vs integrado)
- ¿Renumerar "Paso X de 6" o mantener numeración actual y aceptar "Paso 4 de 6: Botón extra" como excepción?
- ¿Extender `reactions_keyboard_with_counts` o crear `build_broadcast_markup` nuevo?
- ¿Extraer helpers de `confirm_and_send_broadcast` (173 LOC) como parte de ITEM 2, o solo tocarla mínimamente?
- ¿Agregar helper simétrico `get_extra_button_id(broadcast_id)` en service, o leer `broadcast.extra_button_id` directamente?
- ¿UI admin de botones se considera pre-requisito o se documenta como gap? (ITEM 2 scope dice "NO admin UI changes" implícitamente al decir "NO changes to service beyond signature"; pero el gap existe.)

**Contratos protegidos (0 impacto deseado):**
- `check_and_register_reaction` firma y comportamiento
- `register_reaction` (legacy)
- `on_besitos_awarded_broadcast_reaction_observer`
- Atomicity golds (re-correrlos)
- EventBus wiring
- `get_service(BroadcastService)` contract
- `reactions_keyboard_with_counts` firma existente (si se decide no tocarla)

**Evidencia de ITEM 1 (base):**
- `BroadcastButton` + `extra_button_id` FK existen y están en migración
- `TestBroadcastButton` (6 tests) verde
- CRUD de botones en service (6 métodos) siguiendo patrón ReactionEmoji
- 0 comportamiento cambiado en paths de reacción

---

**End of ITEM 2 Impact Analysis.**
