# SUMMARY: 34-store-catalog-tier-nav

**Date:** 2026-06-28  
**Item:** 1/1 — Unificar navegación tienda: estanterías = tiers catálogo Kinky  
**Scope:** 0 behavior change en compra/atomicity/fulfillment

## Outcomes

1. `StoreService.get_tiers_for_shop()` — tiers con ≥1 producto activo (patrón `get_categories_for_shop`)
2. Menú tienda: "Recorrer las estanterías" → `store_tiers`; eliminado botón duplicado "Ver por niveles"
3. `store_categories` → thin delegate a `store_tiers_menu` (backward compat)
4. Botones secundarios: `store_categories` → `store_tiers`
5. `store_category_products` conservado para callbacks antiguos

## Verificación

- pytest store handlers + get_tiers: **108 passed**
- gold smoke (atomicity/reaction/daily/invariants): **89 passed**
- arch-enforcer: PASS WITH NOTES, 0 critical
- test-guardian: suite protege adecuadamente
- self-check: PASSED (gsd-34-store-catalog-tier-nav.log)

## Pool phrase

Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.