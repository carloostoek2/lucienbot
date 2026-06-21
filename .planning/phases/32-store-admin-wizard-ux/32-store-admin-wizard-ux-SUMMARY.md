# SUMMARY: Fase 2 — Store Admin Wizard UX

**Phase:** 32-store-admin-wizard-ux  
**Date:** 2026-06-21  
**Status:** CLOSED

---

## Outcomes

| Criterio SPEC §7 | Estado |
|------------------|--------|
| Custodio crea VIP sin escribir ID | ✅ Lista inline `wiz_store_tariff` |
| Custodio crea STORY_UNLOCK sin escribir ID | ✅ Lista inline `wiz_store_story` |
| Custodio edita tarifa de producto VIP existente | ✅ Menú condicional + `sel_tariff_edit` |
| `test_store_admin_handlers` green | ✅ 72 passed |
| 0 strings user-facing nuevos fuera LucienVoice | ✅ |
| 1× `get_service(StoreService)` por handler | ✅ grep 0 VIP/Story direct |
| Gold atomicity / fulfillment VIP+story | ✅ 43 regression tests passed |

---

## Fases ejecutadas

| Fase | Entregable | Gate |
|------|------------|------|
| **F1** | 4 CallbackData + LucienVoice (rename, empty-state, confirmation extend) | ruff callback_data + smoke import |
| **F2** | 4 StoreService thin delegates (VIP/Story read-only) | ruff + 5 unit tests `-k tariff\|story\|get_packages` |
| **F3** | Wizard FSM `selecting_tariff`/`selecting_story_node`, puros, callbacks; eliminados `waiting_*_id` handlers | ruff + grep 0 VIP/Story |
| **F4** | Edit menu condicional, edit handlers tariff/story, tests completos + regresión | full handler suite + gold |

---

## Archivos modificados (5)

1. `keyboards/callback_data.py` — 4 CallbackData; doc `EditProductFieldCallback.field` extendido
2. `utils/lucien_voice.py` — `select_tariff`/`select_story_node`, `no_tariffs`/`no_story_nodes`, confirmation con nombres
3. `services/store_service.py` — 4 delegates read-only
4. `handlers/store_admin_handlers.py` — wizard inline + edit flow
5. `tests/handlers/test_store_admin_handlers.py` — 11 escenarios nuevos + pure-helper updates

---

## Test counts

| Suite | Resultado |
|-------|-----------|
| `tests/handlers/test_store_admin_handlers.py` | **72 passed** (was 61; +11 nuevos) |
| `tests/unit/test_store_service.py -k complete_order or atomic` | 19 passed |
| `tests/integration/test_cross_service_atomicity.py` | 10 passed |
| `tests/unit/test_fulfillment_service.py -k vip_grant or story_unlock` | 6 passed |
| `tests/integration/test_vip_flow.py` | 8 passed |

### Nuevos tests (Fase 2)

- `TestWizardSelectTariff::test_callback_sets_tariff_and_advances_to_price`
- `TestWizardSelectStoryNode::test_callback_sets_node_and_advances_to_price`
- `TestWizardEmptyTariffs::test_empty_list_shows_no_tariffs_and_clears_fsm`
- `TestWizardEmptyStoryNodes::test_empty_list_shows_no_story_nodes`
- `TestWizardRouteAfterKind::test_vip_grant_routes_to_tariff_selection`
- `TestEditProductTariff::test_vip_menu_shows_tariff_button`
- `TestEditProductTariff::test_edit_tariff_updates_product`
- `TestEditProductStoryNode::test_story_menu_shows_node_button`
- `TestStoreAdminPureHelpers::test_build_wizard_tariff_keyboard`
- `TestStoreAdminPureHelpers::test_build_wizard_story_node_keyboard`
- `TestStoreAdminPureHelpers::test_build_product_edit_menu_vip_shows_tariff`
- `TestStoreAdminPureHelpers::test_build_product_edit_menu_package_no_tariff_button`
- `TestStoreAdminPureHelpers::test_build_product_confirmation_includes_tariff_name`

---

## Self-check

**PASSED** — ver `.planning/quick/gsd-store-admin-wizard-ux.log`

Desviación documentada: ruff pre-existente en `lucien_voice.py` (F841 `btn_text`, E402 `ChannelType` import) no introducido por esta fase.

---

**Ready for:** arch-enforcer + test-guardian