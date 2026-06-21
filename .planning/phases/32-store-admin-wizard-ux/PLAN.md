# PLAN: Fase 2 — Store Admin Wizard UX (inline tariff/story selection + edit VIP/STORY_UNLOCK)

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-06-21  
**Phase:** 32-store-admin-wizard-ux  
**Focus:** Reemplazar prompts numéricos `tariff_id` / `story_node_id` en wizard admin de tienda por listas inline (callbacks); añadir edición condicional de tarifa/nodo en menú de producto existente. **Admin UX only.** 0 cambios en `complete_order`, fulfillment post-commit, Fase 1 VIP activation, debit besitos, narrativa visitante.

**Input principal (source of truth):**
- Spec: `.planning/specs/store-admin-wizard-ux-SPEC.md` v0.1
- Impact report: `.claude/agent-memory/impact-analyzer/item-store-admin-wizard-ux-fase2.md`
- Gold precedent (package selection): `.planning/phases/26-store-admin-long-funcs/PLAN.md` + `handlers/store_admin_handlers.py` (`_wizard_prompt_package_selection` L767–808, `get_packages_for_product_edit` L389–403)
- Arch rules: `handlers/CLAUDE.md` (exactly 1× `get_service(StoreService)` per handler entrypoint; **no** `VIPService()`/`StoryService()` directo en handlers tienda)

**GSD enforcement:** Executor MUST prefix **every** modification / pre-gate / verification / ruff / pytest / grep / self-check with a GSD log append to `.planning/quick/gsd-store-admin-wizard-ux.log` (timestamp | PHASE | description). Planner did INIT + pre-mkdir + pre-write.

---

## 1. Alcance preciso (In / Out)

### En esta entrega (5 archivos + log GSD)

| # | Archivo | Cambio |
|---|---------|--------|
| 1 | `keyboards/callback_data.py` | 4 CallbackData nuevos (prefijos namespaced) |
| 2 | `utils/lucien_voice.py` | Renombrar 2 métodos wizard; 2 empty-state; extender resumen confirmación |
| 3 | `services/store_service.py` | 4 delegates thin → VIP/Story read-only |
| 4 | `handlers/store_admin_handlers.py` | FSM, routing wizard, handlers callback, edit menu, pure helpers |
| 5 | `tests/handlers/test_store_admin_handlers.py` | Nuevos escenarios + actualizar pure-helper tests |

### Fuera explícitamente

- **NO** `reward_admin_handlers.py` (usa `VIPService()` directo — referencia UX, no replicar arquitectura)
- **NO** `fulfillment_service.py`, `store_user_handlers.py`, `vip_handlers.py`, `story_admin_handlers.py`
- **NO** `create_product` / `update_product` / `complete_order` contracts (ya validan `tariff_id`/`story_node_id` por kind)
- **NO** migraciones Alembic, modelos, `bot.py`, `handlers/__init__.py`
- **NO** strings user-facing fuera de `LucienVoice` (SPEC §7)
- **NO** importar `VIPService`/`StoryService` en `store_admin_handlers.py`

### Criterios de cierre (SPEC §7)

- [ ] Custodio crea VIP sin escribir ID
- [ ] Custodio crea STORY_UNLOCK sin escribir ID
- [ ] Custodio edita tarifa de producto VIP existente
- [ ] `test_store_admin_handlers` green
- [ ] 0 strings user-facing nuevos fuera LucienVoice
- [ ] 1× `get_service(StoreService)` por handler
- [ ] Gold tests atomicidad / fulfillment VIP+story green (regresión)

---

## 2. Oleadas A–D → Fases F1–F4

| Oleada | Fase | Entregable | Gate |
|--------|------|------------|------|
| **A** | **F1** | 4 CallbackData + LucienVoice | ruff + grep prefijos + import smoke |
| **B** | **F2** | 4 StoreService delegates | ruff + smoke delegate + store unit `-k tariff\|story` |
| **C** | **F3** | Wizard FSM + puros + handlers callback | handler tests `-k Wizard` green |
| **D** | **F4** | Edit flow + tests completos + regresión + self-check | full `test_store_admin_handlers` + gold atomicity |

---

## 3. Contratos exactos (copiar al pie de la letra)

### 3.1 Cuatro CallbackData (`keyboards/callback_data.py`)

```python
class SelectTariffStoreWizardCallback(CallbackData, prefix="wiz_store_tariff"):
    """Seleccionar tarifa VIP en wizard crear producto tienda."""
    tariff_id: int


class SelectStoryNodeStoreWizardCallback(CallbackData, prefix="wiz_store_story"):
    """Seleccionar nodo narrativo en wizard crear producto tienda."""
    story_node_id: int


class SelectTariffEditProductCallback(CallbackData, prefix="sel_tariff_edit"):
    """Seleccionar tarifa al editar producto VIP_GRANT."""
    product_id: int
    tariff_id: int


class SelectStoryNodeEditProductCallback(CallbackData, prefix="sel_story_edit"):
    """Seleccionar nodo al editar producto STORY_UNLOCK."""
    product_id: int
    story_node_id: int
```

**Colisión evitada:** `SelectTariffCallback` prefix `select_tariff` (rewards/VIP user) — disjunto de `wiz_store_*` y `sel_*_edit`.

**Extender docstring** `EditProductFieldCallback.field`: `# name | description | package | price | stock | tariff | story_node`

### 3.2 Cuatro StoreService delegates (`services/store_service.py`)

```python
def get_tariffs_for_product_wizard(self, active_only: bool = True) -> list[Tariff]:
    """Thin delegate → VIPService(db).get_all_tariffs(active_only).
    Fase 2 store-admin-wizard-ux: wizard inline tariff selection. Read-only. 0 purchase impact.
    """
    from services.vip_service import VIPService
    return VIPService(self._get_db()).get_all_tariffs(active_only=active_only)

def get_story_nodes_for_product_wizard(self, active_only: bool = True) -> list[StoryNode]:
    """Thin delegate → StoryService(db).get_all_nodes(active_only).
    Fase 2 store-admin-wizard-ux: wizard inline story selection. Read-only. 0 purchase impact.
    """
    from services.story_service import StoryService
    return StoryService(self._get_db()).get_all_nodes(active_only=active_only)

def get_tariffs_for_product_edit(self, product_id: int) -> list[Tariff]:
    """Tarifas elegibles al editar: activas + tarifa actual del producto si está inactiva.
    Espejo get_packages_for_product_edit (item8 gold).
    """
    available = self.get_tariffs_for_product_wizard(active_only=True)
    product = self.get_product(product_id)
    if not product or not product.tariff_id:
        return available
    from services.vip_service import VIPService
    current = VIPService(self._get_db()).get_tariff(product.tariff_id)
    if not current:
        return available
    available_ids = {t.id for t in available}
    if current.id in available_ids:
        return available
    return [current, *available]

def get_story_nodes_for_product_edit(self, product_id: int) -> list[StoryNode]:
    """Nodos elegibles al editar: activos + nodo actual del producto si está inactivo.
    Espejo get_packages_for_product_edit (item8 gold).
    """
    available = self.get_story_nodes_for_product_wizard(active_only=True)
    product = self.get_product(product_id)
    if not product or not product.story_node_id:
        return available
    from services.story_service import StoryService
    current = StoryService(self._get_db()).get_node(product.story_node_id)
    if not current:
        return available
    available_ids = {n.id for n in available}
    if current.id in available_ids:
        return available
    return [current, *available]
```

**Imports tipos:** `Tariff`, `StoryNode` desde `models.models` si no presentes.

### 3.3 FSM changes

**`ProductWizardStates`** — reemplazar:
- `waiting_tariff_id` → `selecting_tariff`
- `waiting_story_node_id` → `selecting_story_node`

**Eliminar handlers:**
- `wizard_process_tariff_id` (L822–833)
- `wizard_process_story_node_id` (L836–847)

**`ProductEditStates`** — añadir:
- `selecting_tariff = State()`
- `selecting_story_node = State()`

### 3.4 Pure helpers nuevos (`handlers/store_admin_handlers.py`)

| Función | Firma | Patrón gold |
|---------|-------|-------------|
| `build_wizard_tariff_keyboard` | `(tariffs: list) -> InlineKeyboardMarkup` | espejo `build_edit_package_buttons` + `SelectTariffStoreWizardCallback` |
| `build_wizard_story_node_keyboard` | `(nodes: list) -> InlineKeyboardMarkup` | idem con `SelectStoryNodeStoreWizardCallback` |
| `build_edit_tariff_buttons` | `(product_id: int, tariffs: list) -> list[list[InlineKeyboardButton]]` | espejo `build_edit_package_buttons` L322–349 |
| `build_edit_story_node_buttons` | `(product_id: int, nodes: list) -> list[list[InlineKeyboardButton]]` | idem |

**Botón label sugerido (copiar estilo rewards):**
- Tarifa: `f"{tariff.name} ({tariff.duration_days} dias)"`
- Nodo: `f"{node.title}"` o `node.internal_name` si title vacío

**Lista vacía wizard:** mensaje `LucienVoice.fulfillment_admin_wizard_no_tariffs()` / `_no_story_nodes()` + botón `🔙 Volver` → `admin_store` + `state.clear()` (patrón empty packages L777–789, pero con clear FSM como rewards L580).

**`build_product_edit_menu_text(product)`** — extender:
- Si `product.fulfillment_kind == FulfillmentKind.VIP_GRANT`: línea `👑 Tarifa: {product.tariff.name}` (o "Sin tarifa")
- Si `product.fulfillment_kind == FulfillmentKind.STORY_UNLOCK`: línea `📖 Nodo: {product.story_node.title}` (o "Sin nodo")

**`build_product_edit_menu_keyboard(product)`** — cambiar firma de `product_id: int` → `product` (objeto con `id`, `fulfillment_kind`):
- Campos fijos: name, description, package, price, stock (sin cambio)
- Condicional VIP_GRANT: botón `👑 Tarifa VIP` → `EditProductFieldCallback(field="tariff")`
- Condicional STORY_UNLOCK: botón `📖 Nodo narrativo` → `EditProductFieldCallback(field="story_node")`
- Actualizar caller `edit_product_menu` L1193–1195: pasar `product` no solo `product_id`

**`build_product_confirmation_text_and_keyboard(data)`** — guardar en FSM al seleccionar:
- `tariff_id` + `tariff_name` (wizard callback tariff)
- `story_node_id` + `story_node_title` (wizard callback story)
- Pasar a `fulfillment_admin_wizard_confirmation_summary(..., tariff_name=..., story_node_title=...)`

### 3.5 Handlers nuevos / modificados

**Wizard routing** — `_wizard_route_after_kind` (L700–743):
- VIP_GRANT: `await _wizard_prompt_tariff_selection(target, state)` (espejo L767 `_wizard_prompt_package_selection`)
- STORY_UNLOCK: `await _wizard_prompt_story_node_selection(target, state)`

**`_wizard_prompt_tariff_selection`** — copiar verbatim estructura de `_wizard_prompt_package_selection`:

```python
async def _wizard_prompt_tariff_selection(target, state: FSMContext) -> None:
    with get_service(StoreService) as store_service:
        tariffs = store_service.get_tariffs_for_product_wizard()
    if not tariffs:
        text = LucienVoice.fulfillment_admin_wizard_no_tariffs()
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Volver", callback_data="admin_store")]]
        )
        # edit_text / answer según isinstance(target, CallbackQuery)
        await state.clear()
        return
    keyboard = build_wizard_tariff_keyboard(tariffs)
    text = LucienVoice.fulfillment_admin_wizard_select_tariff()
    # edit_text / answer
    await state.set_state(ProductWizardStates.selecting_tariff)
```

**`_wizard_prompt_story_node_selection`** — idem con `get_story_nodes_for_product_wizard` + `build_wizard_story_node_keyboard` + `selecting_story_node`.

**Wizard callbacks:**

```python
@router.callback_query(ProductWizardStates.selecting_tariff, SelectTariffStoreWizardCallback.filter())
async def wizard_select_tariff(callback, state, callback_data):
    await state.update_data(tariff_id=callback_data.tariff_id, tariff_name=<nombre del botón o lookup>)
    await _wizard_prompt_price_step(callback, state)
    await callback.answer()

@router.callback_query(ProductWizardStates.selecting_story_node, SelectStoryNodeStoreWizardCallback.filter())
async def wizard_select_story_node(callback, state, callback_data):
    await state.update_data(story_node_id=..., story_node_title=...)
    await _wizard_prompt_price_step(callback, state)
    await callback.answer()
```

**Edit** — `edit_product_field_start` ramas nuevas:
- `field == "tariff"`: `get_tariffs_for_product_edit(product_id)` → lista + `ProductEditStates.selecting_tariff`
- `field == "story_node"`: `get_story_nodes_for_product_edit(product_id)` → lista + `ProductEditStates.selecting_story_node`

**Edit callbacks:**

```python
@router.callback_query(ProductEditStates.selecting_tariff, SelectTariffEditProductCallback.filter())
async def process_edit_product_tariff(...):
    with get_service(StoreService) as store_service:
        success = store_service.update_product(product_id, tariff_id=callback_data.tariff_id)
        await _finish_product_edit(..., "tarifa")

@router.callback_query(ProductEditStates.selecting_story_node, SelectStoryNodeEditProductCallback.filter())
async def process_edit_product_story_node(...):
    with get_service(StoreService) as store_service:
        success = store_service.update_product(product_id, story_node_id=callback_data.story_node_id)
        await _finish_product_edit(..., "nodo narrativo")
```

### 3.6 LucienVoice (`utils/lucien_voice.py`)

| Acción | Método |
|--------|--------|
| Reemplazar | `fulfillment_admin_wizard_step_tariff_id()` → `fulfillment_admin_wizard_select_tariff()` |
| Reemplazar | `fulfillment_admin_wizard_step_story_node_id()` → `fulfillment_admin_wizard_select_story_node()` |
| Nuevo | `fulfillment_admin_wizard_no_tariffs()` |
| Nuevo | `fulfillment_admin_wizard_no_story_nodes()` |
| Extender | `fulfillment_admin_wizard_confirmation_summary(..., tariff_name: str \| None = None, story_node_title: str \| None = None)` — mostrar nombre cuando kind VIP/STORY |
| Eliminar/deprecar | `fulfillment_admin_wizard_invalid_tariff_id()`, `fulfillment_admin_wizard_invalid_story_node_id()` (ya no hay input texto) |

**Texto sugerido select_tariff:** `"Paso: Seleccionar tarifa VIP\n\nElige la tarifa para este producto:"`  
**Texto sugerido select_story_node:** `"Paso: Seleccionar nodo narrativo\n\nElige el nodo a desbloquear:"`

---

## 4. Fases ordenadas (F1–F4)

### F1 / Oleada A — Foundation: CallbackData + LucienVoice

**Objective:** Desbloquear handlers con contratos de callback y strings centralizados.

**Archivos:** `keyboards/callback_data.py`, `utils/lucien_voice.py`, `.planning/quick/gsd-store-admin-wizard-ux.log`

**DoD:**
- [ ] 4 CallbackData con prefijos exactos `wiz_store_tariff`, `wiz_store_story`, `sel_tariff_edit`, `sel_story_edit`
- [ ] `EditProductFieldCallback.field` doc extendido con `tariff | story_node`
- [ ] LucienVoice: 2 rename + 2 empty-state + confirmation summary extendido
- [ ] Métodos `invalid_tariff_id` / `invalid_story_node_id` eliminados o sin referencias
- [ ] Ruff clean en ambos archivos
- [ ] Smoke: `./venv/bin/python -c "from keyboards.callback_data import SelectTariffStoreWizardCallback, SelectStoryNodeStoreWizardCallback, SelectTariffEditProductCallback, SelectStoryNodeEditProductCallback; print(SelectTariffStoreWizardCallback(tariff_id=1).pack())"`

**Tests gate F1:**
```bash
./venv/bin/python -m ruff check keyboards/callback_data.py utils/lucien_voice.py --fix
grep -n "wiz_store_tariff\|wiz_store_story\|sel_tariff_edit\|sel_story_edit" keyboards/callback_data.py
```

**Riesgos:** Colisión prefix → grep `select_tariff` vs `wiz_store_tariff` antes de merge.

**Safe point:** F1 — callbacks + voice listos; handlers aún sin tocar.

---

### F2 / Oleada B — StoreService delegates

**Objective:** Thin delegates read-only; handlers nunca importan VIP/Story.

**Archivos:** `services/store_service.py`

**DoD:**
- [ ] 4 métodos delegate presentes (grep)
- [ ] On-demand `VIPService(self._get_db())` / `StoryService(self._get_db())` dentro delegate (no held composition)
- [ ] `get_*_for_product_edit` incluye entidad actual si inactiva (espejo paquetes)
- [ ] 0 cambio en `create_product` / `update_product` / `complete_order`
- [ ] Ruff clean + smoke import

**Tests gate F2:**
```bash
./venv/bin/python -m ruff check services/store_service.py --fix
./venv/bin/python -m pytest tests/unit/test_store_service.py -k "vip_grant or story_unlock or tariff or story_node or get_packages" -q --tb=line -p no:cov --override-ini="addopts="
grep -n "def get_tariffs_for_product_wizard\|def get_story_nodes_for_product_wizard\|def get_tariffs_for_product_edit\|def get_story_nodes_for_product_edit" services/store_service.py
```

**Riesgos:** `StoryService.get_node` vs `get_story_node` — verificar nombre real en `story_service.py` antes de implementar edit delegate.

**Safe point:** F2 — delegates listos; wizard/edit handlers pendientes.

---

### F3 / Oleada C — Wizard inline selection

**Objective:** FSM + routing + puros wizard + handlers callback; eliminar prompts ID.

**Archivos:** `handlers/store_admin_handlers.py`

**DoD:**
- [ ] `ProductWizardStates`: `selecting_tariff`, `selecting_story_node` (sin `waiting_*_id`)
- [ ] Eliminados `wizard_process_tariff_id`, `wizard_process_story_node_id`
- [ ] `_wizard_route_after_kind` delega a `_wizard_prompt_tariff_selection` / `_wizard_prompt_story_node_selection`
- [ ] Puros: `build_wizard_tariff_keyboard`, `build_wizard_story_node_keyboard`
- [ ] Handlers: `wizard_select_tariff`, `wizard_select_story_node`
- [ ] `build_product_confirmation_text_and_keyboard` muestra nombres tarifa/nodo
- [ ] Imports nuevos CallbackData en header handler
- [ ] grep `VIPService\|StoryService` en handler == 0
- [ ] grep `get_service(StoreService)` en cada entrypoint nuevo
- [ ] Funciones nuevas <=50 LOC (extraer puros si roza límite item8)

**Tests gate F3:**
```bash
./venv/bin/python -m ruff check handlers/store_admin_handlers.py --fix
./venv/bin/python -m pytest tests/handlers/test_store_admin_handlers.py -k "WizardSelectTariff or WizardSelectStory or WizardEmpty or Wizard or PureHelpers" -q --tb=line -p no:cov --override-ini="addopts="
grep -n "VIPService\|StoryService" handlers/store_admin_handlers.py   # expect 0
grep -n "waiting_tariff_id\|waiting_story_node_id\|wizard_process_tariff_id\|wizard_process_story_node_id" handlers/store_admin_handlers.py  # expect 0
```

**Riesgos:** Admins mid-wizard con FSM antiguo colgados → aceptable (admin); documentar en GSD.

**Safe point:** F3 — wizard completo; edit menu pendiente F4.

---

### F4 / Oleada D — Edit flow + tests + regresión + self-check

**Objective:** Menú edición condicional, handlers edit tariff/story, suite tests completa, gold regression.

**Archivos:** `handlers/store_admin_handlers.py` (edit zone), `tests/handlers/test_store_admin_handlers.py`

**DoD:**
- [ ] `build_product_edit_menu_text` / `keyboard` condicional por `fulfillment_kind`
- [ ] `edit_product_menu` pasa `product` a keyboard builder
- [ ] `edit_product_field_start` ramas `tariff` / `story_node`
- [ ] Puros: `build_edit_tariff_buttons`, `build_edit_story_node_buttons`
- [ ] Handlers: `process_edit_product_tariff`, `process_edit_product_story_node`
- [ ] Tests SPEC §6 todos green (lista abajo)
- [ ] Tests existentes `test_build_product_edit_menu_*` actualizados
- [ ] Self-check PASSED en GSD log
- [ ] 0 strings hardcoded nuevos fuera LucienVoice (grep spot en handler)

**Tests gate F4 (obligatorio cierre):**
```bash
./venv/bin/python -m pytest tests/handlers/test_store_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="
```

**Regresión gold (0 cambio esperado):**
```bash
./venv/bin/python -m pytest tests/unit/test_store_service.py -k "complete_order or atomic" -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -m pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -m pytest tests/unit/test_fulfillment_service.py -k "vip_grant or story_unlock" -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -m pytest tests/integration/test_vip_flow.py -q --tb=line -p no:cov --override-ini="addopts="
```

**Safe point:** F4 COMPLETE — Fase 2 cerrada.

---

## 5. Escenarios de test (`tests/handlers/test_store_admin_handlers.py`)

| Clase | Test | Qué validar |
|-------|------|-------------|
| `TestWizardSelectTariff` | `test_callback_sets_tariff_and_advances_to_price` | `SelectTariffStoreWizardCallback` → FSM `tariff_id` + `tariff_name` + `waiting_price` |
| `TestWizardSelectStoryNode` | `test_callback_sets_node_and_advances_to_price` | story callback → `story_node_id` + avance precio |
| `TestWizardEmptyTariffs` | `test_empty_list_shows_no_tariffs_and_clears_fsm` | `no_tariffs` voice + `admin_store` + `state.clear()` |
| `TestWizardEmptyStoryNodes` | `test_empty_list_shows_no_story_nodes` | idem nodos |
| `TestWizardRouteAfterKind` | `test_vip_grant_routes_to_tariff_selection` | routing real (des-mock `_wizard_route_after_kind` del test VIP existente) |
| `TestEditProductTariff` | `test_vip_menu_shows_tariff_button` | menú VIP_GRANT incluye `👑 Tarifa VIP` |
| `TestEditProductTariff` | `test_edit_tariff_updates_product` | callback edit → `update_product(tariff_id=...)` |
| `TestEditProductStoryNode` | `test_story_menu_shows_node_button` | menú STORY_UNLOCK incluye `📖 Nodo narrativo` |
| `TestStoreAdminPureHelpers` | `test_build_wizard_tariff_keyboard` | botones con prefix packed `wiz_store_tariff` |
| `TestStoreAdminPureHelpers` | `test_build_wizard_story_node_keyboard` | prefix `wiz_store_story` |
| `TestStoreAdminPureHelpers` | `test_build_product_edit_menu_vip_shows_tariff` | texto incluye tarifa actual |
| `TestStoreAdminPureHelpers` | `test_build_product_edit_menu_package_no_tariff_button` | kind PACKAGE sin botón tarifa |
| `TestStoreAdminPureHelpers` | `test_build_product_confirmation_includes_tariff_name` | resumen con nombre no ID |

**Patrón mock (copiar verbatim de item8 / TestProcessProductDescription):**
```python
@patch("handlers.store_admin_handlers.get_service")
async def test_...(self, mock_get_service, make_callback, make_fsm_context):
    mock_store = MagicMock()
    mock_tariff = MagicMock()
    mock_tariff.id = 2
    mock_tariff.name = "VIP 30 dias"
    mock_tariff.duration_days = 30
    mock_store.get_tariffs_for_product_wizard.return_value = [mock_tariff]
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_store
    mock_get_service.return_value = mock_context
    # late import handler; assert on mock_store not VIPService
```

---

## 6. Self-check criteria (registrar en GSD log al cierre F4)

```
Self-Check: PASSED
- Fases: F1 (callbacks+voice) F2 (delegates) F3 (wizard) F4 (edit+tests)
- Archivos: callback_data.py, lucien_voice.py, store_service.py, store_admin_handlers.py, test_store_admin_handlers.py
- 4 CallbackData: wiz_store_tariff, wiz_store_story, sel_tariff_edit, sel_story_edit
- 4 delegates: get_tariffs_for_product_wizard, get_story_nodes_for_product_wizard, get_tariffs_for_product_edit, get_story_nodes_for_product_edit
- FSM: selecting_tariff/selecting_story_node (wizard+edit); 0 waiting_*_id handlers
- grep handler: 0 VIPService/StoryService direct
- grep handler: 1× get_service(StoreService) per entrypoint
- pytest test_store_admin_handlers: PASS
- gold atomicity/vip/fulfillment: PASS (0 regression)
- 0 user-facing strings outside LucienVoice
- Desviaciones: (none | list)
- Item 32-store-admin-wizard-ux Fase 2 CLOSED. Ready for arch-enforcer + test-guardian.
```

---

## 7. Comandos de regresión (copiar al pie de la letra)

```bash
# Gate principal Fase 2
./venv/bin/python -m pytest tests/handlers/test_store_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="

# Desarrollo iterativo
./venv/bin/python -m pytest tests/handlers/test_store_admin_handlers.py -k "Wizard or Tariff or Story or EditProduct or PureHelpers" -q --tb=line -p no:cov --override-ini="addopts="

# Store service kind validation (sin cambio esperado)
./venv/bin/python -m pytest tests/unit/test_store_service.py -k "vip_grant or story_unlock or tariff or story_node" -q --tb=line -p no:cov --override-ini="addopts="

# Gold atomicidad / 3 sistemas (gate pre-merge)
./venv/bin/python -m pytest tests/unit/test_store_service.py -k "complete_order or atomic" -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -m pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -m pytest tests/unit/test_fulfillment_service.py -k "vip_grant or story_unlock" -q --tb=line -p no:cov --override-ini="addopts="
./venv/bin/python -m pytest tests/integration/test_vip_flow.py -q --tb=line -p no:cov --override-ini="addopts="

# Arch-enforcer greps post-impl
grep -n "VIPService\|StoryService" handlers/store_admin_handlers.py
grep -n "wiz_store_tariff\|wiz_store_story\|sel_tariff_edit\|sel_story_edit" keyboards/callback_data.py
grep -n "def get_tariffs_for_product_wizard\|def get_story_nodes_for_product_wizard\|def get_tariffs_for_product_edit\|def get_story_nodes_for_product_edit" services/store_service.py
```

---

## 8. Riesgos priorizados

| # | Severidad | Riesgo | Mitigación |
|---|-----------|--------|------------|
| 1 | MEDIO | Handler importa VIP/Story directo | Solo delegates StoreService; grep post F3 |
| 2 | MEDIO | `build_product_edit_menu_keyboard(product_id)` callers rotos | Actualizar `edit_product_menu` + tests |
| 3 | MEDIO | Lista active_only oculta tarifa/nodo actual inactivo | `get_*_for_product_edit` obligatorio F2 |
| 4 | BAJO | Colisión CallbackData | Prefijos verificados §3.1 |
| 5 | BAJO | Funciones >50 LOC | Extraer puros (item8 precedent) |
| 6 | BAJO | Strings hardcoded empty-state | Solo LucienVoice |
| 7 | INFO | FSM rename mid-wizard | Aceptable admin |

---

## 9. Instrucciones para gsd-executor

Este PLAN.md ES tu prompt de ejecución. **Sin scope creep.** Ejecuta F1 → F2 → F3 → F4 secuencialmente; no saltar gates.

### 9.1 GSD discipline (non-negotiable)

- Log: `.planning/quick/gsd-store-admin-wizard-ux.log`
- ANTES de cada edit/ruff/pytest/grep:
  ```bash
  echo "=== $(date -Iseconds) | PHASE N | GSD pre-... <file> (F<N> <motivo>) - <desc>" >> .planning/quick/gsd-store-admin-wizard-ux.log
  wc -l .planning/quick/gsd-store-admin-wizard-ux.log
  ```
- Al final F4: self-check §6 completo en log.

### 9.2 Patrones gold a copiar verbatim

**1. Wizard package selection (NO reinventar):**

```767:808:handlers/store_admin_handlers.py
async def _wizard_prompt_package_selection(target, state: FSMContext) -> None:
    with get_service(StoreService) as store_service:
        packages = store_service.get_available_packages_for_store()
    # empty → LucienVoice + back admin_store
    # buttons SelectPkgProductCallback
    await state.set_state(ProductWizardStates.selecting_package)
```

**2. Edit package list (incluye entidad actual inactiva):**

```389:403:services/store_service.py
def get_packages_for_product_edit(self, product_id: int) -> list[Package]:
    available = self.package_service.get_available_packages_for_store()
    product = self.get_product(product_id)
    # ... current package prepended if inactive
```

**3. Edit package buttons pure:**

```322:349:handlers/store_admin_handlers.py
def build_edit_package_buttons(product_id: int, packages: list) -> list[list[InlineKeyboardButton]]:
    # loop + SelectPkgEditProductCallback + cancel
```

**4. Test mock 1-service (item8 port):**

```python
@patch("handlers.store_admin_handlers.get_service")
mock_store = MagicMock()
mock_context = MagicMock()
mock_context.__enter__.return_value = mock_store
mock_get_service.return_value = mock_context
# assert mock_store.get_tariffs_for_product_wizard.called — NOT VIPService
```

**5. Delegate thin (item8 store_service):**

```382:387:services/store_service.py
def get_available_packages_for_store(self) -> list[Package]:
    """Thin delegate to internal package_service.get_available_packages_for_store().
    Added for item8: enables store_admin_handlers product creation wizard to call exactly 1 service...
    """
    return self.package_service.get_available_packages_for_store()
```

**6. NO replicar** `reward_admin_handlers.show_tariff_selection` (usa `VIPService()` directo L564) — solo copiar **UX** (label formato, empty-state flow), no arquitectura.

### 9.3 Orden estricto

1. F1 → gate → F2 → gate → F3 → gate → F4 → self-check
2. Marca DoD por fase en log ("F<N> safe point" / "F<N> COMPLETE")
3. Pytest siempre: `-q --tb=line -p no:cov --override-ini="addopts="`
4. Si fallo preexistente no relacionado (alembic, SAWarnings, etc.) → documentar en log, no contar como regresión de este item

### 9.4 Alcance recordatorio

Solo los 5 archivos listados + log GSD. Si aparece tentación de tocar `fulfillment_service`, `reward_admin_handlers`, o unificar session patterns — **detener**.

---

**Fin del PLAN — 32-store-admin-wizard-ux (4 fases F1–F4 = oleadas A–D).**

Referencias:
- Spec: `.planning/specs/store-admin-wizard-ux-SPEC.md`
- Impact: `.claude/agent-memory/impact-analyzer/item-store-admin-wizard-ux-fase2.md`
- Gold item8: `.planning/phases/26-store-admin-long-funcs/PLAN.md`

Listo para gsd-executor. Ejecuta F1 → F4 con GSD pre en cada paso.