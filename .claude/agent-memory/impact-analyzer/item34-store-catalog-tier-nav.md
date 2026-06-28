# Impact Analyzer — Item 34: store-catalog-tier-nav

**Date:** 2026-06-28  
**Scope:** UI navigation — unificar categorías de tienda con tiers del catálogo Kinky

## Archivos a tocar

| Archivo | Cambio |
|---------|--------|
| `handlers/store_user_handlers.py` | Menú + delegates + callback_data |
| `services/store_service.py` | `get_tiers_for_shop()` |
| `tests/handlers/test_store_user_handlers.py` | Actualizar TestStoreCategories |
| `tests/unit/test_store_service.py` | Unit test nuevo |

## Consumidores

- Visitante: menú tienda, navegación por estanterías
- Admin: sin cambio (Category CRUD en package admin intacto)

## 3 sistemas críticos

| Sistema | Impacto |
|---------|---------|
| Gamificación | **NINGUNO** — no toca besitos/debit |
| Narrativa | **NINGUNO** |
| Canales-VIP | **NINGUNO** |

## Contratos

- get_service: 1 call/handler — **preservado**
- Atomicity/EventBus — **sin toque**

## Tests a correr

- `test_store_user_handlers` (categories/tiers/shop_menu)
- `test_store_service` (get_tiers_for_shop)
- Gold smoke: cross_service_atomicity, reaction_, daily_gift, invariants

## Riesgo global: **BAJO**