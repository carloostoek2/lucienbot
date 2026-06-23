# 📊 Análisis de Impacto: Broadcast Link Buttons Catalog (ITEM 1 of 3)

## Cambio Propuesto
**ITEM 1 (tight scope)**: Introducir el catálogo de botones de enlace extra para broadcasts.
- Nuevo modelo: `BroadcastButton` (id, label, url, is_active, created_at, [opcional: description/name para admin])
- Migración Alembic (nueva tabla)
- Extender `BroadcastService` con CRUD para botones:
  - `create_broadcast_button(label, url, ...)`
  - `get_broadcast_button(button_id)`
  - `get_all_buttons(active_only=True)`
  - `toggle_broadcast_button(button_id)`
  - `update_broadcast_button(button_id, ...)`
  - `delete_broadcast_button(button_id)`
- Posible entrada mínima de UI admin (deferir wizard completo si es largo)
- **NO** cambios a `broadcast_handlers` wizard, **NO** lógica de envío, **NO** flip de reacciones por defecto
- Identificar todos los lugares que posteriormente tocarán el botón (creación de broadcast, preview, construcción de markup, etc.)

**Decisión pendiente**: ¿Agregar `extra_button_id` FK opcional a `BroadcastMessage` en ITEM 1, o deferir completamente a ITEM 2?

## Riesgo Total: MEDIO

**Justificación**: 
- Afecta BroadcastService (dominio de gamificación crítica vía reacciones)
- NO toca paths de crédito de besitos, atomicidad, o EventBus contracts directamente
- Pero BroadcastMessage es parte del flujo de reacciones (has_reactions, selected_emoji_ids)
- Agregar un catálogo similar a ReactionEmoji es un patrón conocido y de bajo riesgo si se mantiene aislado
- Riesgo futuro: cuando se integre en el flujo de envío, podría afectar markup building y send paths

## Mapa de Impacto Directo

| Archivo | Línea(s) | Por qué se ve afectado |
|---------|----------|------------------------|
| `models/models.py` | ~273-297 | Definición de `BroadcastMessage`; nuevo modelo `BroadcastButton` debe agregarse en Fase 1 Gamificación; posible FK `extra_button_id` en BroadcastMessage |
| `models/__init__.py` | 2-36, 38-76 | Exportar `BroadcastButton` (similar a `ReactionEmoji`) |
| `services/broadcast_service.py` | ~28+ (nueva sección) | Agregar métodos CRUD para BroadcastButton siguiendo patrón de ReactionEmoji (create/get/get_all/toggle/update/delete) |
| `alembic/versions/` | NEW | Nueva migración para tabla `broadcast_buttons`; posible columna FK en `broadcast_messages` |

## Mapa de Impacto Indirecto

| Archivo | Cadena de dependencia | Notas |
|---------|----------------------|-------|
| `handlers/broadcast_handlers.py` | broadcast_handlers → get_service(BroadcastService) → [futuro] get_all_buttons, attach extra button | **NO tocar en ITEM 1**. Identificar call sites para ITEM 2/3 |
| `handlers/gamification_user_handlers.py` | handle_reaction → get_broadcast → has_reactions check | Indirecto; BroadcastMessage se lee aquí. FK nuevo no afecta si es nullable |
| `keyboards/callback_data.py` | — | NO necesita cambios en ITEM 1. Futuro: posiblemente nuevo callback para seleccionar botón extra en wizard |
| `keyboards/inline_keyboards.py` | — | NO necesita cambios en ITEM 1. Futuro: markup building para botón extra + reacciones |
| `bot.py` | — | NO necesita cambios en ITEM 1. (EventBus listeners ya registrados para broadcast) |
| `tests/unit/test_broadcast_service.py` | TestBroadcastMessage, TestBroadcastEmoji | Necesitará tests para CRUD de botones (nueva clase TestBroadcastButton) |
| `tests/integration/test_callbackdata_broadcast.py` | TestReactionCallback → build_send_reaction_markup | Test de helper de markup; NO se toca en ITEM 1 pero se verá afectado en ITEM 2 cuando markup incluya botón extra |
| `tests/integration/test_cross_service_atomicity.py` | setup crea BroadcastMessage | Setup fixtures crean BroadcastMessage; FK nullable no rompe si se omite |
| `tests/integration/test_reaction_full_chain.py` | setup crea BroadcastMessage | Igual que arriba |
| `tests/integration/test_invariants.py` | TestReactionInvariants crea BroadcastMessage | Igual que arriba |
| `tests/integration/test_reaction_mission_flow.py` | setup crea BroadcastMessage | Igual que arriba |
| `tests/integration/test_reaction_limit.py` | setup crea BroadcastMessage | Igual que arriba |
| `tests/conftest.py` | sample_broadcast_message fixture | Crea BroadcastMessage; FK nullable no afecta |
| `alembic/versions/` (varios) | Historial de migraciones | Nueva migración se agrega al head; debe mantenerse cadena lineal |
| `tests/integration/test_alembic_heads.py` | Verifica single head | Debe seguir pasando tras nueva migración |

## Lugares que TOCARÁN el botón en el futuro (identificados para ITEM 2/3)

| Ubicación | Qué hará | Evidencia actual |
|-----------|----------|------------------|
| `handlers/broadcast_handlers.py:288` (ask_for_reactions) | Posible paso adicional: "¿Agregar botón extra de enlace?" | Actualmente solo pregunta por reacciones |
| `handlers/broadcast_handlers.py:618` (show_broadcast_preview) | Mostrar en resumen: "Botón extra: ✅/❌" | Actualmente muestra: Canal, Texto, Adjunto, Reacciones, Protección |
| `handlers/broadcast_handlers.py:726-747` (confirm_and_send_broadcast) | Si se seleccionó botón, pasarlo a create_broadcast_message; construir markup combinado (botón + reacciones) | Actualmente: selected_emoji_ids_str → create → build_send_reaction_markup → edit_message_reply_markup |
| `handlers/broadcast_handlers.py:34-54` (build_send_reaction_markup) | Extender para incluir botón extra como fila adicional o al final | Función pura que construye InlineKeyboardMarkup desde selected_emoji_ids |
| `services/broadcast_service.py:105-135` (create_broadcast_message) | Agregar parámetro `extra_button_id: int = None`; guardarlo en BroadcastMessage | Actualmente recibe has_reactions, selected_emoji_ids |
| `services/broadcast_service.py:164-172` (get_selected_emoji_ids) | Posible nuevo helper: `get_extra_button(broadcast_id)` | — |
| `handlers/gamification_user_handlers.py:221-236` (refresh_reaction_markup_counts) | Al refrescar markup de conteos, preservar el botón extra si existe | Actualmente reconstruye solo reacciones |
| `keyboards/inline_keyboards.py` | Nueva función helper para botón de enlace (o integrar en reactions_keyboard_with_counts) | Actualmente tiene reactions_keyboard_with_counts |

## Tests que DEBES Correr Antes

```bash
# 1. Verificar estado de migraciones (CRÍTICO antes de nueva migración)
pytest tests/integration/test_alembic_heads.py -v

# 2. Tests unitarios de broadcast service (CRUD de emojis + mensajes)
pytest tests/unit/test_broadcast_service.py -v

# 3. Tests de flujo de reacción (gold tests para atomicidad)
pytest tests/unit/test_broadcast_service_reaction_flow.py -v

# 4. Tests de atomicidad cross-service (gold para contratos de crédito)
pytest tests/integration/test_cross_service_atomicity.py -v -k "cross_service_atomicity or TestCrossServiceAtomicity"

# 5. Tests de cadena completa de reacción
pytest tests/integration/test_reaction_full_chain.py -v

# 6. Tests de invariantes de reacción
pytest tests/integration/test_invariants.py -v -k "reaction" 

# 7. Tests de límites de reacción
pytest tests/integration/test_reaction_limit.py -v

# 8. Tests de flujo misión-reacción
pytest tests/integration/test_reaction_mission_flow.py -v

# 9. Tests de callbacks broadcast (build_send_reaction_markup)
pytest tests/integration/test_callbackdata_broadcast.py -v

# 10. Tests de handlers de gamificación (reacciones)
pytest tests/handlers/test_gamification_user_handlers.py -v -k "reaction or Reaction"

# 11. Smoke de handlers de broadcast (si existen tests específicos)
pytest tests/handlers/ -v -k "broadcast" 2>/dev/null || echo "No broadcast handler tests found"

# Comando combinado recomendado (antes de tocar código):
pytest tests/integration/test_alembic_heads.py tests/unit/test_broadcast_service.py tests/unit/test_broadcast_service_reaction_flow.py tests/integration/test_cross_service_atomicity.py tests/integration/test_reaction_full_chain.py tests/integration/test_invariants.py -v --tb=line
```

## Tests que FALTAN (riesgo no cubierto)

- [ ] `test_broadcast_button_crud_full` — no existe (nuevo para el catálogo)
- [ ] `test_broadcast_button_toggle_active` — no existe
- [ ] `test_broadcast_button_validation_telegram_url` — no existe (validación de "enlace personalizado de Telegram")
- [ ] `test_broadcast_message_with_extra_button_fk` — no existe (si se agrega FK en ITEM 1)
- [ ] `test_get_all_buttons_active_only_filter` — no existe
- [ ] `test_delete_broadcast_button_cascades_or_restricts` — no existe (¿qué pasa si un broadcast lo referencia?)
- [ ] `test_broadcast_button_label_length_and_url_length` — no existe (límites de columna)

## Precauciones Específicas

1. **Patrón ReactionEmoji es el espejo correcto**: BroadcastButton debe seguir exactamente el mismo patrón que ReactionEmoji (modelo simple con is_active, CRUD en BroadcastService, admin UI separado en gamification_admin_handlers). NO crear un service nuevo.

2. **get_service contract**: Cualquier nuevo método en BroadcastService debe ser usable via `with get_service(BroadcastService) as svc:`. Los métodos existentes de emojis usan patrón de instancia directa en algunos lugares de admin (gamification_admin_handlers.py:86-90). Mantener consistencia.

3. **Validación de URL Telegram**: El requisito dice "enlace personalizado de Telegram". Debe empezar con `https://t.me/` o `tg://`? Mantener validación **loose por ahora** (como indica el scope), pero documentar la decisión. No bloquear con validación estricta en ITEM 1.

4. **Una sola decisión de FK en BroadcastMessage**:
   - Opción A (recomendada para ITEM 1): Agregar columna `extra_button_id = Column(Integer, ForeignKey("broadcast_buttons.id"), nullable=True)` en la misma migración que crea la tabla. Esto permite que ITEM 2/3 solo seteen el valor sin otra migración.
   - Opción B (deferir): No tocar BroadcastMessage en ITEM 1. ITEM 2 agregará la columna + migración separada. Riesgo: dos migraciones para un cambio lógico.
   - **Decisión debe tomarse antes de escribir la migración.**

5. **No romper atomicidad de reacciones**: Aunque ITEM 1 no toca check_and_register_reaction ni credit paths, cualquier test que cree BroadcastMessage debe seguir funcionando. FK nullable garantiza compatibilidad.

6. **Función <= 50 LOC**: Los nuevos métodos CRUD deben respetar la regla de 50 líneas. Patrón de ReactionEmoji ya lo cumple (ej: create_reaction_emoji ~8 LOC).

7. **Logging verb+context+result**: Cada método nuevo debe loguear: `logger.info(f"broadcast_service | create_broadcast_button | label={label} | id={button.id}")`

8. **Export en models/__init__.py**: No olvidar agregar `BroadcastButton` a la importación y a `__all__`.

9. **Alembic heads**: Después de la migración, `pytest tests/integration/test_alembic_heads.py` debe pasar (único head).

10. **3 sistemas críticos**: Gamificación (besitos + REACTIONS + daily) es crítico. Este cambio es al catálogo de botones, no a los paths de crédito. Sin impacto en atomicity gold tests si se mantiene aislado.

## Recomendación

**SÍ vale la pena el cambio** con las siguientes condiciones:

1. **Mantener ITEM 1 ultra-estrecho**: Solo modelo + migración + service CRUD. Sin UI wizard, sin cambios en handlers de broadcast, sin cambios en markup building.

2. **Decidir FK ahora**: Agregar `extra_button_id` nullable a `BroadcastMessage` en la misma migración. Es más limpio que una migración separada después. El FK no afecta nada hasta que ITEM 2/3 lo usen.

3. **No agregar relationship bidireccional en BroadcastMessage** si no es necesaria. Mantener simple (solo la columna FK). La relación puede agregarse después si se necesita navegación.

4. **Validación de URL**: Hacerla en el service o en el modelo (un validator simple), pero mantenerla no-estricta. Documentar que "debe ser enlace de Telegram" es un requisito de negocio futuro, no enforcement duro en ITEM 1.

5. **Tests nuevos**: Agregar al menos:
   - Test unitario de CRUD completo para BroadcastButton (similar a TestBroadcastEmoji)
   - Test de filtro active_only
   - Test de toggle
   - (Opcional) test de validación básica de URL

6. **Handoff claro a ITEM 2/3**:
   - ITEM 2: Integrar selección de botón extra en wizard de broadcast (paso adicional o dentro de reacciones)
   - ITEM 2: Modificar create_broadcast_message para aceptar extra_button_id
   - ITEM 2: Modificar build_send_reaction_markup (o crear nuevo helper) para incluir botón extra
   - ITEM 3: Posiblemente "reacciones por defecto activadas" (fuera del scope de botones)

7. **Alternativa de menor impacto**: Si se quiere evitar FK en BroadcastMessage por ahora, se puede almacenar el button_id en un JSON/text field temporal, pero esto es anti-patrón. Mejor FK nullable.

## Resumen de Archivos a Modificar (ITEM 1 solamente)

1. `models/models.py` — agregar clase `BroadcastButton`; (opcional pero recomendado) agregar columna FK a `BroadcastMessage`
2. `models/__init__.py` — exportar `BroadcastButton`
3. `services/broadcast_service.py` — agregar 6 métodos CRUD para botones (create/get/get_all/toggle/update/delete)
4. `alembic/versions/NEW_MIGRATION.py` — crear tabla `broadcast_buttons` + (opcional) columna en `broadcast_messages`
5. `tests/unit/test_broadcast_service.py` — agregar `TestBroadcastButton` con CRUD tests
6. (Opcional) `handlers/gamification_admin_handlers.py` — entrada mínima de admin para listar/crear botones (si el scope permite "posiblemente UI mínima")

## Hand-off a ITEM 2 y ITEM 3 (explícito)

**ITEM 2 (botones en flujo de broadcast)**:
- Modificar `BroadcastStates` FSM si es necesario (nuevo estado para seleccionar botón extra)
- Agregar paso en wizard: "¿Agregar botón de enlace extra?"
- UI para seleccionar de la lista de botones activos (similar a selección de emojis)
- Modificar `create_broadcast_message` signature para aceptar `extra_button_id`
- Modificar `build_send_reaction_markup` o crear `build_broadcast_markup(broadcast_id, selected_emojis, extra_button)`
- Guardar `extra_button_id` al crear el broadcast
- Actualizar preview para mostrar el botón extra
- Actualizar `refresh_reaction_markup_counts` para preservar el botón extra al refrescar conteos

**ITEM 3 (reacciones por defecto)**:
- Cambiar default de `has_reactions` en el flujo (o agregar config global)
- Posiblemente: si no se selecciona nada, adjuntar todos los emojis activos por defecto
- Toggle admin para "reacciones por defecto habilitadas"

**Ninguno de estos cambios se hace en ITEM 1.**

## Evidencia de Contratos Protegidos

- `check_and_register_reaction` NO se toca → contratos de atomicity intactos
- `register_reaction` (legacy) NO se toca
- `on_besitos_awarded_broadcast_reaction_observer` NO se toca
- `build_send_reaction_markup` NO se modifica en ITEM 1 (solo se identifica para ITEM 2)
- Gold tests (`test_cross_service_atomicity`, `test_reaction_full_chain`, `test_reaction_mission_flow`, `test_invariants`) solo crean `BroadcastMessage` con campos existentes; FK nullable no los rompe
- `test_alembic_heads` debe re-correrse tras migración para verificar single head

## Log de Sesión (para gsd-planner)

Ver: `.planning/quick/gsd-impact-analyzer-broadcast-link-buttons.log`

Entradas generadas:
- Log init
- Reading key files
- Identifying consumers
- Compiling report
- Writing report
