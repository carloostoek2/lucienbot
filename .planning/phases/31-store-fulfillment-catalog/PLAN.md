# PLAN: Store Fulfillment Catalog Ecosystem

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-06-21  
**SPEC:** `.planning/specs/store-fulfillment-catalog-SPEC.md` v1.0  
**Impact:** `.claude/agent-memory/impact-analyzer/store-fulfillment-catalog-impact.md`  
**GSD log:** `.planning/quick/gsd-store-fulfillment-catalog-plan.log`

---

## 1. Objective

Implementar el ecosistema de fulfillment del catálogo Kinky: 22 productos en 5 tiers con entrega heterogénea (AUTO paquete/VIP/narrativa/privilegios, MANUAL cola + input FSM), mochila enriquecida y panel custodio — **sin modificar** el contrato atómico de `StoreService.complete_order`.

### Success criteria (medibles)

| ID | Criterio | Verificación |
|----|----------|--------------|
| SC1 | Pago atómico intacto (debit + stock + COMPLETED en un commit) | Gold tests `TestStorePurchaseAtomicGold` + G6 |
| SC2 | Fulfillment post-commit best-effort (fallo no revierte cobro) | G1 + `test_complete_order_deliver_tuple_failure_still_commits` adaptado |
| SC3 | Toda compra COMPLETED tiene `OrderFulfillment` visible en mochila | G7 |
| SC4 | 22 productos seed idempotente | `scripts/seed_catalog.py` + checkpoint human |
| SC5 | 0 strings user-facing ES en handlers/services (nuevos) | G8 grep + `test_no_hardcoded_spanish_in_services` |
| SC6 | Handlers cumplen 1 servicio por callback | arch-enforcer grep |

### Principios no negociables (SPEC §1.3)

- P1: Fulfillment **nunca** en transacción de `complete_order`
- P2: Fallo entrega TG → status FAILED, cobro intacto
- P3: 1 `get_service(X)` por handler
- P7: Proteger gamificación (debit), narrativa (grant sin debit), VIP (token + redeem)

### Decisiones bloqueadas (SPEC §14 defaults)

| ID | Decisión |
|----|----------|
| D1 | Ventaja Kinky: `PRIVILEGE_EARLY_ACCESS` + `companion_discount_pct` → dispatcher crea 2 `StorePrivilege` |
| D2 | Sin backfill fulfillments históricos |
| D3 | Carrito multi-ítem soportado (1 fulfillment por OrderItem) |
| D4 | Sin badge AUTO/MANUAL al visitante |
| D5 | `StoreTier` dedicado (no reutilizar Package.category) |

---

## 2. Scope

### In

- Modelos, 2 migraciones Alembic, `FulfillmentService`, handlers admin/user/backpack extendidos
- `StoryService.grant_node_access`, LucienVoice métodos anexo A
- `scripts/seed_catalog.py`, job scheduler monthly cap
- Tests G1–G8 + actualización golds existentes

### Out (v1)

- Pasarela MXN, API externa, chat en vivo, edición canal Telegram automática
- Dominio Promotions
- Backfill órdenes históricas
- `notify_early_access_holders` (SPEC §9.6) — stub/log only en D5; integración con drops en v1.1

---

## 3. Architecture snapshot

```
complete_order (atomic)
  └─ post-commit: FulfillmentService.create_fulfillments_for_order
                   FulfillmentService.process_order_fulfillments
                        ├─ PACKAGE → PackageService.deliver_package_to_user
                        ├─ VIP_GRANT → VIPService.generate_token
                        ├─ STORY_UNLOCK → StoryService.grant_node_access
                        ├─ PRIVILEGE_* → StorePrivilege rows
                        ├─ WAITLIST_ENTRY → StoreWaitlistEntry
                        └─ MANUAL kinds → cola + notif admin
```

**Remediación 1-service (handlers existentes):**

- `StoreService.get_product_preview_context(product_id)` — thin delegate: file_count, can_preview (absorbe PackageService en store_user)
- `StoreService.get_shop_balance_display(user_id)` — thin delegate para balance en catálogo
- `StoreService.purchase_and_complete(bot, user_id, product_id, qty)` — encapsula direct_purchase + complete_order en una sesión (fix session split)
- `BackpackService.get_vip_subscriptions_for_backpack(user_id)` — absorbe VIPService en backpack VIP callback
- `BackpackService.retry_fulfillment_delivery(bot, user_id, fulfillment_id)` — delega a FulfillmentService
- `BackpackService.get_vip_activation_link(user_id, fulfillment_id)` — delega a FulfillmentService
- **Regla:** handlers de mochila llaman solo `BackpackService`; nunca importan `FulfillmentService`

---

## 4. Oleadas de implementación

Cada oleada = fase ejecutable independiente. **Gate obligatorio** al cierre:

```bash
pytest tests/unit/test_store_service.py -k "complete_order or atomic" -q --tb=line -p no:cov --override-ini="addopts="
```

---

### Oleada A — Foundation + PACKAGE AUTO

**Objective:** Modelos, migración 1, FulfillmentService scaffold, refactor entrega PACKAGE sin cambiar comportamiento legacy.

#### Task A1: Enums y modelos

**Files:** `models/models.py`  
**Actions:**
- Añadir `DeliveryMode`, `FulfillmentKind`, `FulfillmentStatus`
- Crear `StoreTier`, `OrderFulfillment`, `StorePrivilege`, `StoreWaitlistEntry`
- Extender `StoreProduct`: `delivery_mode`, `fulfillment_kind`, `tier_id`, `story_node_id`, `tariff_id`, `fulfillment_config`, `monthly_stock_cap`, `sort_order` (defaults AUTO + PACKAGE)
- Índices en `OrderFulfillment` según SPEC §3.4

**Verification:** `alembic revision --autogenerate` + revisión manual; model imports en tests

#### Task A2: Migración Alembic 1

**Files:** `alembic/versions/*_fulfillment_mig1.py`  
**Actions:**
- Crear tablas nuevas
- ALTER `store_products` con defaults
- Seed 5 `StoreTier` (SPEC §8.1)
- `package_id` permanece NOT NULL

**Verification:** `alembic upgrade head` en SQLite test DB

#### Task A3: FulfillmentService scaffold

**Files:** `services/fulfillment_service.py`, `services/__init__.py`, `services/store/CLAUDE.md`  
**Actions:**
- Implementar API §4.2 (stubs para kinds no-A en oleadas posteriores)
- `create_fulfillments_for_order`: 1 row por OrderItem, idempotente por `order_item_id` unique
- `dispatch_fulfillment` PACKAGE: delega `PackageService.deliver_package_to_user`, actualiza status FULFILLED/FAILED
- Helpers strategy ≤50 LOC: `_dispatch_package`, `_build_fulfillment_row`, etc.
- Logging: `fulfillment_service | acción | user_id | resultado`

**Verification:** `tests/unit/test_fulfillment_service.py::test_g1_package_auto` + `test_g6_fulfillment_not_in_atomic_tx`

#### Task A4: Integrar StoreService post-commit

**Files:** `services/store_service.py`  
**Actions:**
- En `_complete_order_post_commit_side_effects`: reemplazar `_deliver_order_packages_best_effort` por FulfillmentService (SPEC §4.7)
- `_decrement_stock_for_order`: eliminar construcción `package_ids` (solo stock)
- Mantener misiones side-effects y admin notif

**Verification:** Todos los `TestStorePurchaseAtomicGold` verdes (ver A4b)

#### Task A4b: Actualizar gold tests post-refactor entrega

**Files:** `tests/unit/test_store_service.py`, `tests/integration/test_cross_service_atomicity.py`  
**Actions:**
- Reemplazar mocks de `package_service.deliver_package_to_user` por `FulfillmentService.process_order_fulfillments` o `dispatch_fulfillment`
- Preservar contratos: `debit_survives`, `deliver_tuple_failure_still_commits`, idempotencia double-complete
- Añadir assert G6: fulfillment rows no existen antes de `db.commit()` en complete_order

**Verification:** `TestStorePurchaseAtomicGold` + cross atomicity green

#### Task A5: LucienVoice base fulfillment

**Files:** `utils/lucien_voice.py`  
**Actions:**
- Añadir: `fulfillment_package_delivered`, `fulfillment_package_failed_retry_mochila`
- Mantener `store_purchase_completed` para fallback

**Verification:** G8 grep en archivos tocados

#### Task A6: Export FulfillmentService

**Files:** `services/__init__.py`  
**Verification:** `get_service(FulfillmentService)` funciona

**Oleada A checkpoint:** G1 + G6 + atomic golds green.

---

### Oleada B — Manual queue + FSM input + Mochila

**Objective:** Cola custodio, captura input visitante, mochila con estado fulfillment.

#### Task B1: FulfillmentService MANUAL paths

**Files:** `services/fulfillment_service.py`  
**Actions:**
- `USER_INPUT_THEN_MANUAL`: status PENDING_INPUT → submit → PENDING_FULFILLMENT
- `PACKAGE_DEFERRED`, `CHANNEL_HONOR`, `SCHEDULED_CHAT`: cola PENDING_FULFILLMENT
- `admin_mark_fulfilled`, `admin_deliver_package_from_queue`, `get_pending_queue`
- `submit_user_input` con validación min/max desde `fulfillment_config`

**Verification:** G4 transiciones; unit tests cola

#### Task B2: FSM PurchaseInputStates

**Files:** `handlers/states/store_fulfillment_states.py`, `handlers/store_user_handlers.py`, `keyboards/callback_data.py`  
**Actions:**
- Definir `PurchaseInputStates` (awaiting_input, validating) en módulo states dedicado
- Trigger post-compra cuando status PENDING_INPUT
- Handler input submit: 1× `get_service(FulfillmentService)` por callback
- Handler tier/catalog: 1× `get_service(StoreService)` (sin FulfillmentService en navegación)

**Verification:** Handler test FSM happy path

#### Task B3: fulfillment_admin_handlers

**Files:** `handlers/fulfillment_admin_handlers.py`, `bot.py`, `handlers/__init__.py`  
**Actions:**
- Menú cola §6.2, detalle item §6.3, FSM notas obligatorias
- `is_admin()` en todos los entry points
- Registrar router en `bot.py`

**Verification:** Admin handler tests con mock bot

#### Task B4: Backpack enrichment

**Files:** `services/backpack_service.py`, `handlers/backpack_handler.py`  
**Actions:**
- `get_user_purchases` enriquecido: fulfillment_id, status, kind, status_display, actions_available
- `retry_fulfillment_delivery`, `get_fulfillment_detail` — delegan internamente a FulfillmentService
- Handlers: callbacks retry/VIP/detail llaman **solo** `BackpackService` (nunca FulfillmentService directo)
- Eliminar strings hardcoded en purchase detail (SPEC §7.4)
- `get_vip_subscriptions_for_backpack` thin delegate (fix 1-service)

**Verification:** G7 mochila; backpack unit tests; grep handlers sin import FulfillmentService

#### Task B5: LucienVoice B-track

**Files:** `utils/lucien_voice.py`  
**Actions:** `fulfillment_*`, `fulfillment_input_*`, `fulfillment_admin_*`, `backpack_fulfillment_*` según anexo A (subset B)

**Verification:** G8

#### Task B6: Admin notif enriquecida

**Files:** `services/store_service.py` o FulfillmentService helper  
**Actions:** Extender notif compra con kind + deep-link cola

**Oleada B checkpoint:** G4 + G7 + atomic golds.

---

### Oleada C — VIP + Narrative unlock

**Objective:** VIP_GRANT y STORY_UNLOCK automatizados.

#### Task C1: StoryService.grant_node_access

**Files:** `services/story_service.py`, `services/narrative/CLAUDE.md`, `decisions.md`  
**Actions:**
- Nuevo método SPEC §4.5: sin debit, sin advance principal, idempotente por `reference_fulfillment_id`
- Actualizar `can_access_node` / handlers para respetar unlock por compra
- Entrada en `decisions.md`: contrato grant vs advance, 0 achievement side effects

**Verification:** G3 — cero debit besitos en grant

#### Task C2: VIP_GRANT dispatcher

**Files:** `services/fulfillment_service.py`  
**Actions:**
- Patrón `RewardService._deliver_vip_access`: `generate_token` + `auto_result` JSON
- Idempotencia: reutilizar token en `auto_result`

**Verification:** G2

#### Task C3: purchase_and_complete + post-compra messages

**Files:** `services/store_service.py`, `handlers/store_user_handlers.py`, `utils/lucien_voice.py`  
**Actions:**
- Implementar `StoreService.purchase_and_complete(bot, user_id, product_id, qty) -> tuple[Order|None, list[dict], str|None]`:
  - Una sesión DB: `direct_purchase` + `complete_order` sin close intermedio
  - Retorna resumen fulfillment kinds para mensaje UI
- `confirm_direct_buy` usa solo este método (elimina session split)
- Mensaje post-compra depende de `fulfillment_kind` (no genérico único)

**Verification:** Handler tests; no regression atomic; grep sin double get_service StoreService

#### Task C4: Backpack VIP activate action

**Files:** `handlers/backpack_handler.py`, `keyboards/callback_data.py`, `services/backpack_service.py`  
**Actions:** `BackpackActivateVipCallback` → `BackpackService.get_vip_activation_link` (delega FulfillmentService internamente)

**Oleada C checkpoint:** G2 + G3 + atomic golds.

---

### Oleada D — Privileges, waitlist, hybrid manual

**Objective:** Kinds restantes del catálogo.

#### Task D1: StorePrivilege dispatcher + discount pre-check

**Files:** `services/fulfillment_service.py`, `services/store_service.py`, `models/models.py`  
**Actions:**
- `PRIVILEGE_EARLY_ACCESS`, `PRIVILEGE_DISCOUNT`
- Ventaja Kinky (D1): 2 filas `StorePrivilege` desde un fulfillment
- Descuento activo: validar en **`direct_purchase`**, **`create_order`** y recálculo `total_price` antes de debit en **`complete_order`**
- Marcar `StorePrivilege.consumed_at` en el mismo commit del debit (atómico con cobro)

**Verification:** Unit tests privilege creation + discount apply en los 3 entry points

#### Task D2: Waitlist + honor + scheduled chat

**Files:** `services/fulfillment_service.py`  
**Actions:**
- `WAITLIST_ENTRY`: position auto-increment
- `CHANNEL_HONOR`, `SCHEDULED_CHAT`: cola manual + admin_mark_fulfilled

**Verification:** Unit tests waitlist position

#### Task D3: Admin wizard extendido

**Files:** `handlers/store_admin_handlers.py`  
**Actions:** Wizard §6.1: tier → mode → kind → payload → price → stock (+ monthly cap field)
- Pure helpers para UI ≤50 LOC
- 1× `get_service(StoreService)` o `FulfillmentService` según operación (wizard create → StoreService)

**Verification:** `test_store_admin_handlers` extendido

#### Task D4: Migración Alembic 2

**Files:** `alembic/versions/*_fulfillment_mig2.py`  
**Actions:** `package_id` nullable; validación service kind→package

**Verification:** Productos sin package creables para MANUAL kinds

#### Task D5: Early access notification stub

**Files:** `services/fulfillment_service.py`  
**Actions:**
- `notify_early_access_holders(drop_id)` — best-effort log + DM placeholder; no bloquea publicación
- Documentar en `services/store/CLAUDE.md` como deferred v1.1 para integración Promotions

**Oleada D checkpoint:** Privilege + waitlist tests; atomic golds.

---

### Oleada E — Monthly cap, seed, tier UI

**Objective:** Tier 5, catálogo completo, producción-ready.

#### Task E1: Monthly stock cap

**Files:** `services/fulfillment_service.py`, `services/store_service.py`  
**Actions:**
- `is_monthly_cap_available`, `count_monthly_sales` (TZ Mexico City)
- Pre-check en `direct_purchase` / `create_order`
- Job `reset_monthly_store_caps` en SchedulerService

**Verification:** G5

#### Task E2: Tier navigation UI

**Files:** `handlers/store_user_handlers.py`, `utils/lucien_voice.py`, `keyboards/`  
**Actions:**
- Flujo §5.1: shop → tiers → products → detail
- `store_tier_*` intros
- Thin delegates para preview/balance (1-service)

**Verification:** Handler tests tier nav

#### Task E2b: checkpoint:decision — placeholders seed

**Type:** `checkpoint:decision`  
**Actions:** Custodio confirma `package_id`, `story_node_id`, `tariff_id` para productos TBD antes de seed producción

#### Task E3: seed_catalog.py

**Files:** `scripts/seed_catalog.py`  
**Actions:** 22 productos SPEC §8.2, idempotente, placeholders desde env/config tras checkpoint E2b

**Verification:** Script runnable 2× sin duplicar

#### Task E4: checkpoint:human-verify

**Type:** `checkpoint:human-verify`  
**Actions:** Diana/Custodio valida copy Lucien en 3 flujos: compra AUTO, compra MANUAL, mochila pendiente

#### Task E5: bot-ui-experience-enhancer audit

**Type:** `checkpoint:human-verify`  
**Actions:** Ejecutar skill post-implementación; corregir hallazgos P0/P1

**Oleada E checkpoint:** G5 + G8 + seed + atomic golds + full suite:

```bash
pytest tests/unit/test_fulfillment_service.py tests/unit/test_store_service.py \
  tests/unit/test_backpack_service.py -q --tb=line -p no:cov --override-ini="addopts="
```

---

## 5. Testing strategy

### Gold tests (SPEC §11) — archivo `tests/unit/test_fulfillment_service.py`

| ID | Test name | Contrato |
|----|-----------|----------|
| G1 | `test_g1_package_auto_debit_survives` | debit + order COMPLETED aunque TG fail |
| G2 | `test_g2_vip_grant_one_token_idempotent` | un token; segunda dispatch OK |
| G3 | `test_g3_story_unlock_zero_debit` | grant_node_access sin BesitoTransaction |
| G4 | `test_g4_user_input_manual_transitions` | PENDING_INPUT → pending → fulfilled |
| G5 | `test_g5_monthly_cap_blocks_then_allows` | cap agotado bloquea; mes siguiente OK |
| G6 | `test_g6_fulfillment_not_in_atomic_tx` | fulfillment rows creadas post-commit |
| G7 | `test_g7_backpack_status_display` | status_display legible post-complete |
| G8 | (grep CI) | 0 español user-facing en services/handlers tocados |

### Regression suite (cada oleada)

```bash
pytest tests/unit/test_store_service.py -k "complete_order or atomic" -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/integration/test_invariants.py -k "order" -q --tb=line -p no:cov --override-ini="addopts="
```

---

## 6. File inventory (SPEC §13)

| Archivo | Oleada |
|---------|--------|
| `services/fulfillment_service.py` | A (scaffold), B-D (kinds) |
| `handlers/fulfillment_admin_handlers.py` | B |
| `handlers/store_user_handlers.py` | B, C, E |
| `handlers/store_admin_handlers.py` | D |
| `handlers/backpack_handler.py` | B, C |
| `models/models.py` | A |
| `utils/lucien_voice.py` | A→E incremental |
| `keyboards/callback_data.py` | B, C |
| `services/store/CLAUDE.md` | A |
| `scripts/seed_catalog.py` | E |
| `bot.py` | B |

---

## 7. GSD execution notes

- GSD pre-log en `.planning/quick/gsd-store-fulfillment-catalog-plan.log` antes de cada edit
- Ejecutar oleadas secuencialmente A→E; no saltar gates
- Post-oleada E: arch-enforcer + test-guardian recomendados
- Funciones ≤50 LOC; helpers puros para UI wizard/cola

---

## 8. Risks and mitigations

| Riesgo | Mitigación |
|--------|------------|
| Fulfillment en atomic tx | Code review gate G6; grep `create_fulfillments` solo en post-commit |
| Story double debit | Solo `grant_node_access`; test G3 |
| Legacy products break | Defaults AUTO+PACKAGE; oleada A sin cambiar datos existentes |
| Handler 1-service violations | Thin delegates en StoreService/BackpackService (§3) |
| PLAN too large for one context | Oleadas = unidades de ejecución (~50% context cada una) |

---

*Plan revisado: impact-analyzer → gsd-planner → gsd-reviewer (Round 2 OK).*