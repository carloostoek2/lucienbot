# SPEC (borrador): UX Admin — Wizard y edición de productos tienda

| Campo | Valor |
|-------|-------|
| **Versión** | 0.1 borrador |
| **Fecha** | 2026-06-21 |
| **Estado** | Completado — Fase 32 (2026-06-21) |
| **Depende de** | Fase 1 cerrada (tests green) |
| **Relacionado** | [store-fulfillment-catalog-SPEC.md](./store-fulfillment-catalog-SPEC.md) |

---

## 1. Problema

Durante pruebas del catálogo ampliado, el wizard de creación de productos en tienda pide **IDs numéricos** que el Custodio no conoce ni debería buscar:

- `tariff_id` para productos `VIP_GRANT`
- `story_node_id` para productos `STORY_UNLOCK`

Además, al **editar** un producto VIP existente no hay forma de cambiar la tarifa asociada.

**Nota:** El flujo de recompensas misión (`reward_admin_handlers`) ya presenta tarifas VIP como lista seleccionable — ese es el patrón a replicar en tienda.

---

## 2. Objetivo (Fase 2)

1. Wizard crear producto: selección inline de tarifas y nodos narrativos (como paquetes).
2. Edición producto: campos condicionales para cambiar tarifa (VIP_GRANT) y nodo (STORY_UNLOCK).
3. Cero prompts de ID de entidad en flujos admin de tienda.
4. Mantener arquitectura: handlers → 1× `get_service(StoreService)`; delegates thin en StoreService.

---

## 3. Auditoría admin — IDs vs selección

| Flujo | Estado actual | Acción Fase 2 |
|-------|---------------|---------------|
| Wizard tienda: tarifa VIP | Texto `tariff_id` | **Lista tarifas activas** |
| Wizard tienda: nodo narrativo | Texto `story_node_id` | **Lista nodos activos** |
| Wizard tienda: paquete | Lista inline | OK |
| Wizard tienda: tier catálogo | Botones `wiz_tier:` | OK |
| Wizard tienda: `fulfillment_config` | JSON opcional | OK (config, no IDs) |
| Recompensas misión: tarifa | Lista (`show_tariff_selection`) | OK |
| Envío manual paquete: `waiting_user_id` | Telegram ID destinatario | Fuera de alcance |

---

## 4. Wizard crear producto

### 4.1 Estados FSM

Reemplazar en `ProductWizardStates`:

- `waiting_tariff_id` → `selecting_tariff`
- `waiting_story_node_id` → `selecting_story_node`

Eliminar handlers `wizard_process_tariff_id` / `wizard_process_story_node_id`.

### 4.2 StoreService delegates

```python
def get_tariffs_for_product_wizard(self, active_only: bool = True) -> list[Tariff]
def get_story_nodes_for_product_wizard(self, active_only: bool = True) -> list[StoryNode]
```

Implementación: thin delegate a `VIPService.get_all_tariffs` y `StoryService.get_all_nodes`.

### 4.3 Callbacks nuevos

En `keyboards/callback_data.py`:

- `SelectTariffStoreWizardCallback(tariff_id: int)` — prefix `wiz_store_tariff`
- `SelectStoryNodeStoreWizardCallback(story_node_id: int)` — prefix `wiz_store_story`

### 4.4 Puros UI (handlers/store_admin_handlers.py)

- `build_wizard_tariff_keyboard(tariffs) -> InlineKeyboardMarkup`
- `build_wizard_story_node_keyboard(nodes) -> InlineKeyboardMarkup`

Lista vacía → mensaje Lucien + volver a admin tienda (patrón `show_tariff_selection` en rewards).

### 4.5 LucienVoice

Reemplazar:

- `fulfillment_admin_wizard_step_tariff_id` → `fulfillment_admin_wizard_select_tariff()`
- `fulfillment_admin_wizard_step_story_node_id` → `fulfillment_admin_wizard_select_story_node()`
- Nuevos: `fulfillment_admin_wizard_no_tariffs`, `fulfillment_admin_wizard_no_story_nodes`
- Resumen confirmación: mostrar **nombre** de tarifa/nodo, no ID

---

## 5. Edición de producto existente

### 5.1 Menú edición

Extender `build_product_edit_menu_text` / `build_product_edit_menu_keyboard`:

- Si `fulfillment_kind == VIP_GRANT`: mostrar tarifa actual + botón "👑 Tarifa VIP"
- Si `fulfillment_kind == STORY_UNLOCK`: mostrar nodo actual + botón "📖 Nodo narrativo"

Campos existentes (nombre, descripción, paquete, precio, stock) sin cambio.

### 5.2 Estados y callbacks

`ProductEditStates`:

- `selecting_tariff`
- `selecting_story_node`

Callbacks:

- `SelectTariffEditProductCallback(product_id, tariff_id)`
- `SelectStoryNodeEditProductCallback(product_id, story_node_id)`

`StoreService.update_product` ya acepta `tariff_id` / `story_node_id` con validación por kind.

---

## 6. Testing (Fase 2)

| Archivo | Escenarios |
|---------|------------|
| `tests/handlers/test_store_admin_handlers.py` | Wizard tariff/story por callback; edición tarifa; lista vacía |
| Tests puros | `build_wizard_tariff_keyboard`, `build_product_edit_menu` condicional |

```bash
pytest tests/handlers/test_store_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="
```

---

## 7. Criterios de cierre Fase 2

- [x] Custodio crea producto VIP sin escribir ningún ID
- [x] Custodio crea producto STORY_UNLOCK sin escribir ningún ID
- [x] Custodio edita tarifa de producto VIP existente
- [x] Tests handler store_admin green (72 passed)
- [x] 0 strings user-facing nuevos fuera de LucienVoice

---

## 8. Aprobación

Pendiente hasta cierre Fase 1.