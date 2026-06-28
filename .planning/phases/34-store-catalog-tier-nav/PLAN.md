# PLAN: 34-store-catalog-tier-nav

## Objetivo

Unificar navegación del visitante en tienda: las "estanterías/categorías" del menú deben reflejar los **tiers del catálogo Kinky** (IMPULSO → MÍTICO, `docs/catalogo.md`), no las categorías de paquetes (`Category`).

## Scope (tight)

- 0 cambio en compra, atomicity, fulfillment, EventBus, besitos
- Solo handlers UI + thin delegate en service + tests

## Fases

### F1 — Service: `get_tiers_for_shop`

**Archivo:** `services/store_service.py`

- Añadir `get_tiers_for_shop(active_only=True)` — tiers activos con ≥1 producto activo (patrón `get_categories_for_shop`)
- `store_tiers_menu` usará este método

**DoD:** unit test en `test_store_service.py`

### F2 — Handlers: unificar menú y callbacks

**Archivo:** `handlers/store_user_handlers.py`

1. `shop_menu`: botón "Recorrer las estanterías" → `callback_data="store_tiers"`; eliminar fila duplicada "Ver por niveles"
2. `store_categories`: thin delegate → `store_tiers_menu` (backward compat callback antiguo)
3. Botones secundarios (`_build_product_buttons`, `store_category_products`, etc.): `store_categories` → `store_tiers`
4. Mantener `store_category_products` + `StoreCategoryCallback` sin cambios (mensajes antiguos)

**DoD:** handlers ≤50 LOC; 1× `get_service(StoreService)` por handler

### F3 — Tests

**Archivo:** `tests/handlers/test_store_user_handlers.py`

- Actualizar `TestStoreCategories` → tiers (mock `get_tiers_for_shop` / `get_all_tiers`)
- Añadir test: `shop_menu` no tiene botón duplicado de niveles
- Unit: `test_get_tiers_for_shop_only_with_products`

### F4 — Verificación

```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "store_user_handlers or TestStoreService and tier or get_tiers_for_shop"
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "cross_service_atomicity or reaction_ or daily_gift or invariants" --maxfail=3
```

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Callbacks antiguos `store_categories` | Delegate a `store_tiers_menu` |
| Callbacks antiguos `store_category:N` | Handler conservado |
| 3 crit | Sin tocar purchase/fulfillment paths |

## Instrucciones para gsd-executor

- GSD pre-log en `.planning/quick/gsd-34-store-catalog-tier-nav.log` antes de cada edit
- Self-check PASSED al final
- Pool phrase en SUMMARY