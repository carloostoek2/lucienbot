# Test-Guardian Audit: Item 32 — Store Admin Wizard UX (Fase 2)

**Date:** 2026-06-21  
**Agent:** test-guardian  
**Phase:** 32-store-admin-wizard-ux  
**Sources read:**
- `.planning/specs/store-admin-wizard-ux-SPEC.md` (§6 Testing, §7 criterios cierre)
- `.planning/phases/32-store-admin-wizard-ux/PLAN.md` (§5 escenarios de test)
- `.planning/phases/32-store-admin-wizard-ux/32-store-admin-wizard-ux-SUMMARY.md`
- `tests/handlers/test_store_admin_handlers.py`
- `handlers/store_admin_handlers.py` (wizard/edit handlers + pure helpers)

---

## Executive Summary

Audit of handler test coverage for Fase 2: inline tariff/story selection in product wizard + conditional edit menu for VIP_GRANT / STORY_UNLOCK. All **SPEC §6** scenarios and all **PLAN §5** matrix rows are implemented and green.

**Veredict: suite protege adecuadamente**

**Pytest gate:** `72 passed`, 1 warning (pre-existing `MovedIn20Warning` in `models/database.py`)

---

## SPEC §6 Coverage Matrix

| SPEC §6 escenario | Test(s) | Estado |
|-------------------|---------|--------|
| Wizard tariff por callback | `TestWizardSelectTariff::test_callback_sets_tariff_and_advances_to_price` | ✅ |
| Wizard story por callback | `TestWizardSelectStoryNode::test_callback_sets_node_and_advances_to_price` | ✅ |
| Edición tarifa | `TestEditProductTariff::test_vip_menu_shows_tariff_button`, `test_edit_tariff_updates_product` | ✅ |
| Lista vacía (tarifas) | `TestWizardEmptyTariffs::test_empty_list_shows_no_tariffs_and_clears_fsm` | ✅ |
| Lista vacía (nodos) | `TestWizardEmptyStoryNodes::test_empty_list_shows_no_story_nodes` | ✅ |
| Puro `build_wizard_tariff_keyboard` | `TestStoreAdminPureHelpers::test_build_wizard_tariff_keyboard` | ✅ |
| Puro `build_wizard_story_node_keyboard` | `TestStoreAdminPureHelpers::test_build_wizard_story_node_keyboard` | ✅ |
| Puro `build_product_edit_menu` condicional | `test_build_product_edit_menu_vip_shows_tariff`, `test_build_product_edit_menu_package_no_tariff_button`, `TestEditProductStoryNode::test_story_menu_shows_node_button` | ✅ |

---

## PLAN §5 Coverage Matrix (13 filas)

| Clase | Test | Validación | Estado |
|-------|------|------------|--------|
| `TestWizardSelectTariff` | `test_callback_sets_tariff_and_advances_to_price` | FSM `tariff_id` + `tariff_name` → `waiting_price` | ✅ |
| `TestWizardSelectStoryNode` | `test_callback_sets_node_and_advances_to_price` | FSM `story_node_id` + `story_node_title` → `waiting_price` | ✅ |
| `TestWizardEmptyTariffs` | `test_empty_list_shows_no_tariffs_and_clears_fsm` | voice `no_tariffs` + `admin_store` + `state.clear()` | ✅ |
| `TestWizardEmptyStoryNodes` | `test_empty_list_shows_no_story_nodes` | voice nodos + `admin_store` + clear | ✅ |
| `TestWizardRouteAfterKind` | `test_vip_grant_routes_to_tariff_selection` | routing real → `selecting_tariff` + delegate mock | ✅ |
| `TestEditProductTariff` | `test_vip_menu_shows_tariff_button` | menú VIP_GRANT incluye `👑 Tarifa VIP` | ✅ |
| `TestEditProductTariff` | `test_edit_tariff_updates_product` | `update_product(tariff_id=...)` vía `sel_tariff_edit` | ✅ |
| `TestEditProductStoryNode` | `test_story_menu_shows_node_button` | menú STORY_UNLOCK incluye `📖 Nodo narrativo` | ✅ |
| `TestStoreAdminPureHelpers` | `test_build_wizard_tariff_keyboard` | prefix `wiz_store_tariff` | ✅ |
| `TestStoreAdminPureHelpers` | `test_build_wizard_story_node_keyboard` | prefix `wiz_store_story` | ✅ |
| `TestStoreAdminPureHelpers` | `test_build_product_edit_menu_vip_shows_tariff` | texto tarifa actual en menú VIP | ✅ |
| `TestStoreAdminPureHelpers` | `test_build_product_edit_menu_package_no_tariff_button` | PACKAGE sin botón tarifa | ✅ |
| `TestStoreAdminPureHelpers` | `test_build_product_confirmation_includes_tariff_name` | resumen con nombre tarifa | ✅ |

---

## Patrón arquitectónico verificado en tests

- **1× `get_service(StoreService)`:** todos los tests Fase 2 nuevos usan `@patch("handlers.store_admin_handlers.get_service")` + `mock_context.__enter__.return_value = mock_store`; asserts sobre `mock_store.get_tariffs_for_product_wizard` / `get_story_nodes_for_product_wizard` / `update_product` — **no** patches directos a `VIPService`/`StoryService`.
- **Delegates read-only:** cubiertos indirectamente vía mocks de StoreService en wizard routing, empty-state y callbacks.
- **Pure helpers:** ejecutados directamente (sin patch) en `TestStoreAdminPureHelpers`.

---

## Pytest Gate (obligatorio F4)

```bash
./venv/bin/python -m pytest tests/handlers/test_store_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="
```

**Resultado:** `72 passed`, 1 warning in 0.39s

---

## Gaps opcionales (no bloquean veredicto)

Fuera de SPEC §6 y PLAN §5; hardening futuro si se desea simetría total:

| Gap | Severidad | Nota |
|-----|-----------|------|
| Sin test de `process_edit_product_story_node` (callback `sel_story_edit` → `update_product(story_node_id=...)`) | BAJA | Tariff edit sí tiene handler test; story solo menú. PLAN no lo exige; SPEC §6 solo menciona "edición tarifa". |
| Sin `test_story_unlock_routes_to_story_selection` en `TestWizardRouteAfterKind` | BAJA | VIP routing cubierto; STORY_UNLOCK routing es espejo trivial. |
| Sin `test_build_product_confirmation_includes_story_node_title` | BAJA | Confirmación tariff cubierta; story title en FSM/callback ya validado en `TestWizardSelectStoryNode`. |
| Sin unit tests directos de delegates `get_tariffs_for_product_*` / `get_story_nodes_for_product_*` en `test_store_service.py` | INFO | SPEC §6 acota a handler tests; delegates validados vía mocks handler. |
| Sin test de `edit_product_field_start` ramas `tariff`/`story_node` | INFO | Flujo de entrada edit; callback final tariff cubierto. |

**Acción tomada:** ningún test añadido — gaps son opcionales y no figuran en SPEC §6 ni PLAN §5.

---

## SPEC §7 criterios de cierre (trazabilidad test)

| Criterio | Evidencia test |
|----------|----------------|
| Custodio crea VIP sin escribir ID | Wizard callback + routing + keyboard pure + empty-state |
| Custodio crea STORY_UNLOCK sin escribir ID | Idem story |
| Custodio edita tarifa VIP existente | Menú condicional + `process_edit_product_tariff` |
| `test_store_admin_handlers` green | 72 passed |
| 1× `get_service(StoreService)` por handler | Patrón mock verificado en tests Fase 2 |
| Gold atomicity/fulfillment | Fuera de alcance test-guardian handler; SUMMARY reporta 43 regression green |

---

## Veredict Final

**suite protege adecuadamente**

- SPEC §6: 100% escenarios cubiertos
- PLAN §5: 13/13 filas green
- Gate pytest: **72 passed**
- Gaps listados son hardening opcional, no requeridos por spec/plan

**Ready for:** cierre Fase 2 test-guardian ✓