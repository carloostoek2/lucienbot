---
name: store-admin-wizard-ux-fase2
description: Impact analysis for Fase 2 — inline tariff/story selection in store admin wizard + edit flows. Admin UX only; 0 purchase/fulfillment path changes.
type: project
---

# Impact Analysis Report: Fase 2 — Store Admin Wizard UX

**Item:** store-admin-wizard-ux-fase2  
**Date analyzed:** 2026-06-21  
**Role:** impact-analyzer (Lucien Bot)  
**Spec:** `.planning/specs/store-admin-wizard-ux-SPEC.md` v0.1  
**Depends on:** Fase 1 VIP activation cerrada (tests green)  
**Gold pattern:** Package selection — `handlers/store_admin_handlers.py` Item 8 + `StoreService.get_available_packages_for_store` / `get_packages_for_product_edit`

## Executive Summary

**Problema:** El wizard admin de tienda pide `tariff_id` y `story_node_id` como texto numérico; la edición de productos VIP/STORY_UNLOCK no permite cambiar tarifa/nodo.

**Solución Fase 2:** Reemplazar prompts de ID por listas inline (callbacks) en creación; añadir campos condicionales en menú de edición. Delegates thin en `StoreService` hacia `VIPService.get_all_tariffs` y `StoryService.get_all_nodes`.

**Impacto global:** **BAJO en sistemas críticos.** Cambio acotado a **flujos admin de catálogo** (FSM + UI). Los contratos de compra (`complete_order`), fulfillment post-commit (`FulfillmentService._dispatch_vip_grant` / `_dispatch_story_unlock`), activación VIP Fase 1, debit besitos y narrativa de visitante **no se modifican**.

**Archivos a tocar (5):**

| Archivo | Nivel | Cambio |
|---------|-------|--------|
| `handlers/store_admin_handlers.py` | **ALTO** | FSM, routing wizard, handlers callback, edit menu, pure helpers |
| `services/store_service.py` | **BAJO** | 2 delegates thin (+ opcional helpers para edit list con entidad actual inactiva) |
| `keyboards/callback_data.py` | **BAJO** | 4 CallbackData nuevos (prefijos namespaced) |
| `utils/lucien_voice.py` | **BAJO** | Renombrar 2 métodos + 2 empty-state + extender resumen confirmación |
| `tests/handlers/test_store_admin_handlers.py` | **ALTO** | Nuevos escenarios + actualizar pure-helper tests |

**Riesgo principal:** Regresión de arquitectura (handler llama `VIPService`/`StoryService` directo en vez de 1× `StoreService`) o divergencia UX respecto al patrón paquetes (lista vacía, cancel, nombres en resumen). **No** hay riesgo atómico de pago.

---

## Estado actual vs objetivo

### Wizard crear producto (VIP_GRANT / STORY_UNLOCK)

| Elemento | Actual | Fase 2 |
|----------|--------|--------|
| FSM | `waiting_tariff_id`, `waiting_story_node_id` | `selecting_tariff`, `selecting_story_node` |
| Input | `@router.message` + `int(message.text)` | `@router.callback_query` + CallbackData |
| Prompt | `LucienVoice.fulfillment_admin_wizard_step_tariff_id()` | `fulfillment_admin_wizard_select_tariff()` + teclado inline |
| Routing | `_wizard_route_after_kind` → texto | `_wizard_route_after_kind` → `_wizard_prompt_tariff_selection` / `_wizard_prompt_story_node_selection` (espejo de `_wizard_prompt_package_selection`) |
| Handlers a eliminar | `wizard_process_tariff_id`, `wizard_process_story_node_id` | — |

**Ubicación actual (líneas clave):**

- `ProductWizardStates`: L48–49 (`waiting_tariff_id`, `waiting_story_node_id`)
- `_wizard_route_after_kind`: L704–727 (VIP/STORY → prompt ID)
- Handlers texto: L822–847

### Edición producto existente

| Elemento | Actual | Fase 2 |
|----------|--------|--------|
| `build_product_edit_menu_text` | Solo nombre, desc, paquete, precio, stock | + tarifa actual (VIP_GRANT) / nodo actual (STORY_UNLOCK) |
| `build_product_edit_menu_keyboard` | 5 campos fijos | + botones condicionales `👑 Tarifa VIP` / `📖 Nodo narrativo` |
| `ProductEditStates` | Sin tariff/story | `selecting_tariff`, `selecting_story_node` |
| `edit_product_field_start` | `field` ∈ name/description/package/price/stock | + `tariff`, `story_node` (o flujo dedicado vía botón) |
| Persistencia | `StoreService.update_product` ya acepta `tariff_id` / `story_node_id` con validación por kind | Sin cambio en service |

**Gap actual:** `EditProductFieldCallback.field` documentado como `name | description | package | price | stock` — extender a `tariff | story_node`.

---

## Mapa de impacto por archivo

### 1. `handlers/store_admin_handlers.py` — IMPACTO ALTO

**Funciones / zonas afectadas:**

| Zona | Acción |
|------|--------|
| `ProductWizardStates` | Renombrar 2 estados; eliminar handlers message |
| `ProductEditStates` | Añadir `selecting_tariff`, `selecting_story_node` |
| `_wizard_route_after_kind` | VIP → prompt lista tarifas; STORY → prompt lista nodos |
| Nuevos | `_wizard_prompt_tariff_selection`, `_wizard_prompt_story_node_selection` |
| Nuevos puros | `build_wizard_tariff_keyboard`, `build_wizard_story_node_keyboard`, `build_edit_tariff_buttons`, `build_edit_story_node_buttons` |
| `build_product_confirmation_text_and_keyboard` | Mostrar nombre tarifa/nodo (guardar `tariff_name` / `story_node_title` en FSM data) |
| `build_product_edit_menu_text` | Firma: necesita `product` con `fulfillment_kind`, relaciones `tariff` / `story_node` |
| `build_product_edit_menu_keyboard` | Firma: `product` o `(product_id, kind, ...)` para botones condicionales |
| `edit_product_field_start` | Ramas `tariff` / `story_node` → lista + FSM |
| Nuevos handlers | Wizard: `wizard_select_tariff`, `wizard_select_story_node`; Edit: `process_edit_product_tariff`, `process_edit_product_story_node` |

**Patrón gold a replicar (paquetes):**

```767:808:handlers/store_admin_handlers.py
async def _wizard_prompt_package_selection(target, state: FSMContext) -> None:
    with get_service(StoreService) as store_service:
        packages = store_service.get_available_packages_for_store()
    # ... empty → LucienVoice + back admin_store
    # ... buttons SelectPkgProductCallback
```

**Regla arch-enforcer:** Cada handler/router sigue con **exactamente 1** `with get_service(StoreService)`. Los delegates nuevos evitan importar `VIPService`/`StoryService` en handlers (contraste: `reward_admin_handlers.show_tariff_selection` usa `VIPService()` directo — **no** replicar en tienda).

**Consumidores del módulo (0 cambio en wiring):**

- `handlers/__init__.py` — `store_admin_router` sin cambio
- `bot.py` — `dp.include_router(store_admin_router)`
- `handlers/gamification_admin_handlers.py` — entrada `callback_data="admin_store"`

---

### 2. `services/store_service.py` — IMPACTO BAJO (additive)

**Añadir (SPEC §4.2):**

```python
def get_tariffs_for_product_wizard(self, active_only: bool = True) -> list[Tariff]:
    """Thin delegate → VIPService(db).get_all_tariffs(active_only)."""

def get_story_nodes_for_product_wizard(self, active_only: bool = True) -> list[StoryNode]:
    """Thin delegate → StoryService(db).get_all_nodes(active_only)."""
```

**Opcional recomendado (espejo `get_packages_for_product_edit`):**

```python
def get_tariffs_for_product_edit(self, product_id: int) -> list[Tariff]:
    """Activas + tarifa actual del producto si está inactiva."""

def get_story_nodes_for_product_edit(self, product_id: int) -> list[StoryNode]:
    """Activos + nodo actual del producto si está inactivo."""
```

**Implementación:** On-demand `VIPService(self._get_db())` / `StoryService(self._get_db())` dentro del delegate (mismo patrón que `FulfillmentService` local en otros métodos). **No** añadir held composition en `_init_services` salvo necesidad — delegates on-demand mantienen scope mínimo.

**0 cambio obligatorio en:**

- `create_product` / `update_product` (validación `tariff_id`/`story_node_id` por kind ya existe L173–176, L313–324)
- `complete_order`, `direct_purchase`, `purchase_and_complete`
- `get_available_packages_for_store`, CRUD stock, stats, notificaciones

**Tests unitarios existentes que deben seguir green (sin editar para Fase 2):**

- `test_create_product_rejects_vip_grant_without_tariff`
- `test_create_product_rejects_story_unlock_without_node`
- `test_update_product_rejects_vip_grant_without_tariff`
- `test_update_product_rejects_story_unlock_without_node`

---

### 3. `keyboards/callback_data.py` — IMPACTO BAJO (additive)

**Nuevos (SPEC §4.3, §5.2):**

| Clase | Prefix | Campos |
|-------|--------|--------|
| `SelectTariffStoreWizardCallback` | `wiz_store_tariff` | `tariff_id: int` |
| `SelectStoryNodeStoreWizardCallback` | `wiz_store_story` | `story_node_id: int` |
| `SelectTariffEditProductCallback` | `sel_tariff_edit` (sugerido) | `product_id`, `tariff_id` |
| `SelectStoryNodeEditProductCallback` | `sel_story_edit` (sugerido) | `product_id`, `story_node_id` |

**Colisión evitada:** `SelectTariffCallback` (prefix `select_tariff`) usado en rewards/VIP user — prefijos `wiz_store_*` y `sel_*_edit` son disjuntos.

**Consumidores actuales de callbacks STORE (sin cambio de contrato):**

- `SelectPkgProductCallback`, `SelectPkgEditProductCallback`, `EditProductFieldCallback`, `EditProductCallback` — siguen igual; tests existentes en `test_store_admin_handlers.py` deben pasar.

**Test recomendado (opcional):** `tests/integration/test_callbackdata_store.py` o ampliar suite callbackdata — pack/unpack roundtrip de los 4 nuevos.

---

### 4. `utils/lucien_voice.py` — IMPACTO BAJO

| Método actual | Acción Fase 2 |
|---------------|---------------|
| `fulfillment_admin_wizard_step_tariff_id()` L1404 | Reemplazar → `fulfillment_admin_wizard_select_tariff()` |
| `fulfillment_admin_wizard_step_story_node_id()` L1408 | Reemplazar → `fulfillment_admin_wizard_select_story_node()` |
| `fulfillment_admin_wizard_invalid_tariff_id()` | Deprecar/eliminar si ya no hay input texto |
| `fulfillment_admin_wizard_invalid_story_node_id()` | Idem |
| — | Nuevos: `fulfillment_admin_wizard_no_tariffs()`, `fulfillment_admin_wizard_no_story_nodes()` |
| `fulfillment_admin_wizard_confirmation_summary()` L1467 | Extender con `tariff_name` / `story_node_title` opcionales cuando kind es VIP_GRANT / STORY_UNLOCK |

**Criterio SPEC §7:** 0 strings user-facing nuevos fuera de LucienVoice.

**Consumidores de métodos a renombrar:** Solo `store_admin_handlers.py` (grep confirma). Rewards/VIP usan strings inline en `show_tariff_selection` — fuera de alcance.

---

### 5. `tests/handlers/test_store_admin_handlers.py` — IMPACTO ALTO

**Estado actual:** No hay tests para `wizard_process_tariff_id` / `wizard_process_story_node_id` (handlers existen pero sin cobertura). `TestProductWizardFulfillmentSteps` mockea `_wizard_route_after_kind` para VIP — habrá que añadir tests de integración del routing real.

**Tests a añadir (SPEC §6):**

| Clase / escenario | Qué validar |
|-------------------|-------------|
| `TestWizardSelectTariff` | Callback `SelectTariffStoreWizardCallback` → FSM `tariff_id` + avance a `waiting_price` |
| `TestWizardSelectStoryNode` | Callback story → `story_node_id` + avance a precio |
| `TestWizardEmptyTariffs` | Lista vacía → `fulfillment_admin_wizard_no_tariffs` + back `admin_store` + clear FSM |
| `TestWizardEmptyStoryNodes` | Idem nodos |
| `TestEditProductTariff` | Menú VIP_GRANT muestra botón tarifa; callback edit → `update_product(tariff_id=...)` |
| `TestEditProductStoryNode` | Menú STORY_UNLOCK muestra botón nodo |
| `TestStoreAdminPureHelpers` (extender) | `build_wizard_tariff_keyboard`, `build_product_edit_menu_*` condicional por kind |

**Tests existentes a revisar tras impl:**

- `test_build_product_edit_menu_text` / `test_build_product_edit_menu_keyboard` — asserts de 5/6 botones cambiarán si product mock incluye `fulfillment_kind`
- `test_build_product_confirmation_text_and_keyboard` — si resumen incluye tarifa/nodo

**Patrón de mock:** `@patch("handlers.store_admin_handlers.get_service")` + `mock_store.get_tariffs_for_product_wizard.return_value = [...]` (Item 8 precedent).

---

## Impacto en 3 sistemas críticos

### Gamificación — **SIN IMPACTO en runtime de visitante** | **INDIRECTO en catálogo admin**

| Aspecto | Evaluación |
|---------|------------|
| `BesitoService.credit/debit` | 0 cambio |
| `StoreService.complete_order` | 0 cambio — sigue leyendo `product.tariff_id` / `story_node_id` del registro ya persistido |
| Misiones / regalo diario | 0 cambio |
| Stats admin (`get_store_stats`, besitos gastados) | 0 cambio |
| **Riesgo indirecto** | Custodio asigna tarifa/nodo incorrecto vía UI → producto mal configurado → fulfillment falla en compra (**comportamiento preexistente** con IDs mal escritos; la UI reduce error humano) |

**Veredicto:** ✅ **0 impacto** en contratos gamificación. Mejora UX admin sin tocar atomicidad P1.

---

### Narrativa — **SIN IMPACTO en progresión** | **LECTURA para listas admin**

| Aspecto | Evaluación |
|---------|------------|
| `StoryService.advance_to_node` | 0 cambio |
| `StoryService.grant_node_access` | 0 cambio — invocado post-compra desde `FulfillmentService._dispatch_story_unlock` leyendo `product.story_node_id` |
| `get_all_nodes` | Solo lectura para teclado admin wizard/edit |
| Progreso visitante / arquetipos | 0 cambio |

**Veredicto:** ✅ **0 impacto** en narrativa runtime. Delegate es read-only catalog listing.

---

### Canales-VIP — **SIN IMPACTO en Fase 1** | **LECTURA para listas admin**

| Aspecto | Evaluación |
|---------|------------|
| `VIPService.grant_vip_from_tariff` (Fase 1 activación) | 0 cambio en código |
| `redeem_token`, suscripciones, cola pending | 0 cambio |
| `get_all_tariffs` | Solo lectura para teclado admin |
| Producto `VIP_GRANT` con `tariff_id` | Mismo campo DB; solo cambia **cómo** el custodio lo asigna |

**Veredicto:** ✅ **0 impacto** en Fase 1 VIP activation, fulfillment post-compra, canales. Scope explícito del item cumplido.

---

## Consumidores downstream (awareness — 0 touch)

| Consumidor | Relación | Impacto Fase 2 |
|------------|----------|----------------|
| `services/fulfillment_service.py` | Lee `product.tariff_id` / `product.story_node_id` en dispatch | 0 código; datos mejor asignados |
| `handlers/store_user_handlers.py` | Catálogo/compra visitante | 0 |
| `handlers/backpack_handler.py` | Post-compra UI | 0 |
| `handlers/fulfillment_admin_handlers.py` | Cola admin | 0 |
| `handlers/reward_admin_handlers.py` | Patrón `show_tariff_selection` (referencia) | 0 |
| `handlers/vip_handlers.py` | `SelectTariffCallback` distinto prefix | 0 |
| `handlers/story_admin_handlers.py` | CRUD nodos | 0 |
| `scripts/seed_catalog.py` | Seed productos con IDs | 0 |
| `models/models.py` | `StoreProduct.tariff_id`, `story_node_id`, relaciones | 0 |
| Alembic | — | 0 migraciones |

---

## Riesgos priorizados

| # | Severidad | Riesgo | Mitigación |
|---|-----------|--------|------------|
| 1 | **MEDIO** | Handler importa `VIPService`/`StoryService` directo (viola 1-service) | Solo delegates en `StoreService`; grep post-impl |
| 2 | **MEDIO** | `build_product_edit_menu_keyboard(product_id)` callers rotos al cambiar firma | Actualizar `edit_product_menu` + tests pure helpers |
| 3 | **MEDIO** | Lista `active_only=True` oculta tarifa/nodo **actual** en edición si fue desactivado | Implementar `get_*_for_product_edit` (patrón paquete) |
| 4 | **BAJO** | Colisión CallbackData | Prefijos `wiz_store_*` verificados vs `select_tariff`, `sel_pkg_*` |
| 5 | **BAJO** | FSM rename deja admins mid-wizard colgados | Aceptable (admin); documentar en deploy |
| 6 | **BAJO** | Funciones >50 LOC tras añadir handlers | Extraer puros (Item 8 precedent) |
| 7 | **BAJO** | Strings hardcoded en empty-state | Solo vía LucienVoice nuevos métodos |
| 8 | **INFO** | `fulfillment_admin_wizard_invalid_*` quedan huérfanos | Eliminar o dejar si se mantiene validación defensiva |

---

## Tests a ejecutar

### Obligatorios (cierre Fase 2 — SPEC §6)

```bash
pytest tests/handlers/test_store_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="
```

### Filtros pytest recomendados (desarrollo iterativo)

```bash
# Wizard tariff/story + edit + pure helpers
pytest tests/handlers/test_store_admin_handlers.py -k "Wizard or Tariff or Story or EditProduct or PureHelpers" -q --tb=line -p no:cov --override-ini="addopts="

# Solo nuevos escenarios (post-impl, nombres sugeridos)
pytest tests/handlers/test_store_admin_handlers.py -k "WizardSelectTariff or WizardSelectStory or WizardEmpty or EditProductTariff or EditProductStory" -q --tb=line -p no:cov --override-ini="addopts="
```

### Regresión store service (validación kind — sin cambio esperado)

```bash
pytest tests/unit/test_store_service.py -k "vip_grant or story_unlock or tariff or story_node" -q --tb=line -p no:cov --override-ini="addopts="
```

### Gold atomicidad / 3 sistemas (gate pre-merge — 0 cambio esperado)

```bash
pytest tests/unit/test_store_service.py -k "complete_order or atomic" -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/unit/test_fulfillment_service.py -k "vip_grant or story_unlock" -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_vip_flow.py -q --tb=line -p no:cov --override-ini="addopts="
```

### Opcional (nuevos CallbackData)

```bash
pytest tests/integration/test_callbackdata_vip.py -q --tb=line -p no:cov --override-ini="addopts="
# + nuevo test file store wizard callbacks si se añade
```

---

## Criterios de cierre (SPEC §7) — checklist impacto

- [ ] Custodio crea VIP sin escribir ID → wizard callback + delegate tarifas
- [ ] Custodio crea STORY_UNLOCK sin escribir ID → wizard callback + delegate nodos
- [ ] Custodio edita tarifa producto VIP existente → edit menu condicional + `update_product`
- [ ] `test_store_admin_handlers` green
- [ ] 0 strings user-facing fuera LucienVoice
- [ ] 1× `get_service(StoreService)` por handler
- [ ] Gold tests atomicidad / fulfillment VIP+story green (regresión)

---

## Orden de implementación sugerido

1. `keyboards/callback_data.py` — 4 CallbackData (desbloquea handlers)
2. `utils/lucien_voice.py` — strings nuevos/renombrados
3. `services/store_service.py` — delegates thin (+ edit helpers opcionales)
4. `handlers/store_admin_handlers.py` — puros → wizard routing → edit flow
5. `tests/handlers/test_store_admin_handlers.py` — escenarios SPEC + actualizar pure tests
6. Regresión gold (comandos arriba)

---

## Handoff

**Listo para gsd-executor / implementer.** Scope cerrado: admin UX Fase 2 únicamente. No abrir refactors en `reward_admin_handlers` (VIPService directo), `fulfillment_service`, ni unificación de session en `store_user_handlers`.

**Referencias:**

- Spec: `.planning/specs/store-admin-wizard-ux-SPEC.md`
- Precedente Item 8: `.claude/agent-memory/impact-analyzer/item8-store-admin-long-funcs.md`
- Fulfillment catalog (contexto VIP_GRANT/STORY_UNLOCK): `.claude/agent-memory/impact-analyzer/store-fulfillment-catalog-impact.md`