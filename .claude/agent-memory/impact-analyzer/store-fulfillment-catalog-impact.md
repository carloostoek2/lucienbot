---
name: store-fulfillment-catalog
description: Impact analysis for Store Fulfillment Catalog ecosystem (FulfillmentService, tiers, 22 products, mochila, admin queue). Source SPEC v1.0.
type: project
---

# Impact Analysis Report: Store Fulfillment Catalog Ecosystem

**Date:** 2026-06-21  
**Role:** impact-analyzer (Lucien Bot)  
**Feature:** Ecosistema de fulfillment para catálogo Kinky (22 productos, 5 tiers, AUTO/MANUAL, cola admin, mochila enriquecida)  
**Source:** `.planning/specs/store-fulfillment-catalog-SPEC.md` v1.0

## Executive Summary

**Current state:** Todos los productos se tratan como `PACKAGE` + entrega inmediata vía `StoreService._deliver_order_packages_best_effort` → `PackageService.deliver_package_to_user`. No existe `FulfillmentService`, `OrderFulfillment`, `StoreTier`, ni distinción AUTO/MANUAL. El pago atómico en `complete_order` está bien protegido por gold tests.

**Target state:** Nuevo `FulfillmentService` orquesta post-commit; modelos ampliados; UI por tiers; cola custodio; mochila con estado; FSM input; kinds heterogéneos (VIP, narrativa, privilegios, waitlist, manual).

**Overall recommendation:** Proceder en **5 oleadas (A→E)** del SPEC. Proteger contrato P1 (fulfillment **nunca** en commit atómico). Cada oleada debe re-ejecutar golds `complete_order` antes de avanzar.

## Mapa de Impacto

### Crítico — no romper (3 sistemas + atomicidad)

| Sistema | Archivo / contrato | Riesgo | Mitigación |
|---------|-------------------|--------|------------|
| Gamificación | `StoreService.complete_order` debit PURCHASE | Fulfillment en tx atómica | `create_fulfillments` + `process_*` solo post-commit (SPEC §4.7) |
| Gamificación | `BesitoService.debit_besitos` | Rollback si dispatch falla | P2 best-effort; gold `debit_survives` |
| Narrativa | `StoryService.advance_to_node` debita besitos | Doble cobro en STORY_UNLOCK | Nuevo `grant_node_access` sin debit (SPEC §4.5) |
| Canales-VIP | `VIPService.redeem_token` | Bypass grant | VIP_GRANT genera token; visitante redime (patrón RewardService) |

### Core services (alto impacto)

| Archivo | Cambio | Consumidores afectados |
|---------|--------|------------------------|
| `services/store_service.py` | Post-commit → FulfillmentService; monthly cap pre-check; `_decrement_stock` sin `package_ids` | `store_user_handlers`, gold tests, cross atomicity |
| `services/fulfillment_service.py` | **NUEVO** — strategy dispatch por kind | store, backpack, admin handlers |
| `services/backpack_service.py` | Enriquecer purchases con fulfillment | `backpack_handler` |
| `services/story_service.py` | `grant_node_access` nuevo | fulfillment, story_user_handlers |
| `services/package_service.py` | Sin cambio API; caller cambia | fulfillment (único post-compra) |
| `services/vip_service.py` | Sin cambio API; idempotencia en `auto_result` | fulfillment VIP_GRANT |
| `services/scheduler_service.py` | Job `reset_monthly_store_caps` | Tier 5 productos |

### Models + migrations

| Artefacto | Cambio |
|-----------|--------|
| `models/models.py` | Enums `DeliveryMode`, `FulfillmentKind`, `FulfillmentStatus`; tablas `StoreTier`, `OrderFulfillment`, `StorePrivilege`, `StoreWaitlistEntry`; columnas en `StoreProduct` |
| Alembic mig 1 | Nuevas tablas + columnas; `package_id` sigue NOT NULL |
| Alembic mig 2 | `package_id` nullable + validación service |

### Handlers (nuevo + extendido)

| Archivo | Acción |
|---------|--------|
| `handlers/fulfillment_admin_handlers.py` | **NUEVO** — cola, marcar cumplido, wizard payload |
| `handlers/store_admin_handlers.py` | Wizard tier/mode/kind/config |
| `handlers/store_user_handlers.py` | Tier nav, FSM input, mensajes por kind |
| `handlers/backpack_handler.py` | Fulfillment status + acciones; eliminar strings hardcoded |
| `bot.py` | Registrar `fulfillment_admin_router` |

### Deuda arquitectural existente (remediar en plan)

| Violación | Ubicación | Plan |
|-----------|-----------|------|
| Multi-service handlers | `store_user_handlers` (BesitoService + PackageService) | Delegar balance/preview a StoreService thin methods |
| Multi-service handler | `backpack_handler.callback_vip` → VIPService directo | Delegar a BackpackService |
| Strings hardcoded ES | `backpack_handler`, `store_user_handlers` | LucienVoice (G8) |
| Session split confirm_buy | `store_user_handlers:489-500` | Unificar en un `get_service(StoreService)` o método atómico delegado |

### Tests críticos (obligatorios cada oleada)

```bash
pytest tests/unit/test_store_service.py -k "complete_order or atomic" -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_invariants.py -q --tb=line -p no:cov --override-ini="addopts="
```

**Gold tests nuevos (SPEC §11):** `tests/unit/test_fulfillment_service.py` — G1–G8.

### Tests existentes que requieren actualización

| Test | Motivo |
|------|--------|
| `test_store_service.py::TestStorePurchaseAtomicGold` | Mock `deliver_package` → mock FulfillmentService o mantener PACKAGE path |
| `test_backpack_service.py` | Shape purchases + fulfillment fields |
| `test_store_user_handlers.py` | Tier nav, FSM, post-purchase messages |
| `test_store_admin_handlers.py` | Wizard extendido |
| `test_cross_service_atomicity.py` | Post-commit path change |

## Riesgos priorizados

1. **CRÍTICO:** Fulfillment dentro de `complete_order` commit → rompe P1 + todos los golds.
2. **CRÍTICO:** `STORY_UNLOCK` vía `advance_to_node` → doble debit besitos.
3. **ALTO:** `_decrement_stock_for_order` asume `product.package` → crash en productos sin package.
4. **ALTO:** Productos legacy sin migración defaults → comportamiento idéntico si AUTO+PACKAGE.
5. **MEDIO:** `confirm_direct_buy` session split → race en fulfillments si no se unifica.
6. **MEDIO:** Ventaja Kinky combo (D1) — dispatcher debe crear 2 `StorePrivilege` sin kind nuevo.
7. **BAJO:** `notify_stock_alert` stub — fuera de alcance v1 salvo wiring cola.

## Recomendación de oleadas (del SPEC §12)

| Oleada | Scope | Gate |
|--------|-------|------|
| A | Modelos, mig 1, FulfillmentService scaffold, PACKAGE AUTO, LucienVoice base | G1, G6 + atomic golds |
| B | Cola admin, FSM input, mochila status, PACKAGE_DEFERRED | G4, G7 |
| C | VIP_GRANT, STORY_UNLOCK, grant_node_access | G2, G3 |
| D | Privilegios, waitlist, channel honor, scheduled chat, Ventaja Kinky | G5 parcial |
| E | Stock mensual, scheduler, seed 22, UI tiers, auditoría UI | G5, G8 + seed |

## Verificación DoD (impact-analyzer)

- [x] Consumidores de `StoreService.complete_order` mapeados
- [x] 3 críticos identificados con mitigaciones
- [x] Tests gold listados con comandos
- [x] Archivos nuevos vs modificados inventariados
- [x] Deuda arquitectural pre-existente documentada
- [x] Oleadas alineadas con SPEC

**Handoff:** Listo para gsd-planner → PLAN.md en `.planning/phases/31-store-fulfillment-catalog/`.