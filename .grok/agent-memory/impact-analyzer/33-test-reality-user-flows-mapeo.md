# 📊 Análisis de Impacto: Test Reality Hardening — User Flows (Focus: Tienda/Store)

**Agent:** impact-analyzer (hardener-agile, effort=4)  
**Date:** 2026-06-26  
**Scope:** Tests only. 0 behavior change, 0 atomicity change, 0 prod code change. Protect 3 critical systems (gamificación/besitos/reacciones/daily, narrativa, canales-VIP) + atomicity/EventBus/get_service contracts.

---

## Cambio Propuesto (User Request Verbatim)
"Lo que quiero es que reduzcamos esa fragilidad en cuanto a la baja confianza de realidad sobre todo en los flujos críticos está bien que los los tres sistemas estén protegidos de manera correcta pero en los flujos del usuario por ejemplo en la tienda es muy importante y el hecho de que haya tanto mock me parece una mala práctica. Estructura un plan para que refactoricemos pues al menos lo más importante es un mapeo de cuáles afectan flujos importantes para que los refactoricemos"

**Objetivo:** Mapear tests que cubren flujos de usuario importantes (priorizar tienda), identificar baja "confianza de realidad" causada por mocks pesados (unittests.mock exclusively), proponer clusters de refactor a estilo integration (real service + real db_session) como el precedente existente en gamification_user_handlers_integration.py, sin tocar prod ni golds de 3 crit.

---

## Riesgo Total: ALTO (para tests de tienda; MEDIO para otros flujos de usuario)

**Por qué ALTO para tienda:**
- Tienda toca el límite de atomicidad (debit besitos PURCHASE + stock + COMPLETE + post-commit fulfillment + mission side effects).
- 252 get_service patches + ~380 total mock occurrences solo en test_store_user_handlers.py (1873 LOC).
- Los mocks retornan MagicMock para productos, balances, effective_price, tier gates, etc. — un bug real en get_product_detail_context, _apply_discount, complete_order debit, o fulfillment dispatch NO se detectaría.
- Item 10/28 (remaining-besito-store) ya unificó a locals BesitoService(db=...) dentro de los sitios de balance/debit en store_service (direct_purchase, create_order, complete_order). Cualquier cambio en tests de purchase paths requiere 1-line/guard ports siguiendo precedente.

**3 crit protegidos:** Golds de atomicity/cross (gamif), reaction chains, daily, invariants, vip flows NO deben romperse. Store purchase side effects (STORE_PURCHASE mission + best-effort) son "post-credit" y ya ejercitados en golds/cross.

---

## Mapa de Impacto Directo (User Flows + Tests)

### Tienda / Store (MÁXIMA PRIORIDAD — flujo económico crítico para usuarios)

| Flujo de Usuario | Archivos de Test | Mock Count / Tipos | Nivel de Realidad Actual | Riesgo de "Realidad de Resultados" | Recomendación de Hardening |
|------------------|------------------|--------------------|---------------------------|------------------------------------|----------------------------|
| Browse catalog, categories, filters (price/stock/recent), search | tests/handlers/test_store_user_handlers.py (TestStoreCatalog, TestStoreCategories, TestStoreCategoryProducts, TestStoreFilters*, TestStoreSearch*, TestShowFilteredProducts) | 380 total mocks en archivo; ~252 get_service patches. _mock_store_ctx helper que setea MagicMock en todos los métodos. | Pure isolation (MagicMock service). | Alto: texto de UI, conteos de productos, botones de filtro, empty states — todo depende de returns mockeados. Bug en filter_products o resolve_product_category_id no se vería. | Convertir paths clave a "handler-integration" style (patch class StoreService, return real instance(db_session) como gamif). Usar fixtures reales (sample_store_product + packages + categories). |
| Product detail (balance, effective_price con descuentos, tier lock, stock ∞/agotado, preview flag) | TestProductDetail (muchos tests: sufficient/insufficient, tier_locked, discounted, monthly_cap_exhausted, etc.) + get_product_detail_context | ~80-100 mocks solo en esta clase. Mocks de product + ctx dicts completos. | Pure isolation. | Crítico: effective_price, tier gates, monthly_cap, can_preview — lógica compleja en servicio + FulfillmentService + tiers. | Alta: crear tests de integración handler que llamen real get_product_detail_context con productos reales + privilegios de descuento + tiers. |
| Direct buy + confirm (saldo check con effective, cap, tier gate, luego complete_order que debita) | TestDirectBuy, TestConfirmDirectBuy | ~60-80 mocks. _setup_direct_buy helper. | Isolation + algunos service unit reales. | Muy alto: el path handler → direct_purchase → complete_order (local Besito debit commit=False + stock + COMPLETE + post) está completamente mockeado en handler tests. | Muy alta: port a integration style. Reusar/ extender gold atomic (TestStorePurchaseAtomicGold en unit/test_store_service.py). |
| Purchase history | TestPurchaseHistory | ~20-30 mocks. | Isolation. | Medio: solo lectura de órdenes. | Baja-media: convertir a real service si hay tiempo en pool. |
| Preview envío (photo/video, error graceful, first file only) | TestProductPreview | ~40-50 mocks. | Isolation. | Medio: depende de get_preview_files_for_product (delegate a PackageService). | Media: si se toca, usar real PackageService o mock solo externo. |

**Total get_service patches en handlers tests (todos los flujos):** 1152 (store_user solo: 252 ≈ 22%).

**Consumers directos de StoreService (trazado):**
- handlers/store_user_handlers.py (todas las entrypoints vía `with get_service(StoreService) as svc:` — 1 service rule).
- handlers/store_admin_handlers.py (admin CRUD + wizard, ya hardened en Item 8/26 con puros + 1svc).
- services/fulfillment_service.py (indirecto vía delivery).
- tests/unit/test_store_service.py (instanciación directa con db_session real).
- tests/integration/test_callbackdata_store*.py (solo packing, no lógica).
- Posible backpack/fufillment admin para reintentos (thin delegates).

**Dependencias internas de StoreService (trazado 2 niveles):**
- Local on-demand `BesitoService(db=self.db)` SOLO en balance/debit sites (post Item10): direct_purchase, create_order, complete_order.
- `PackageService` (held): get_available_packages, files, categories.
- `FulfillmentService` (on-demand en métodos): monthly_cap, consume discount, create/process fulfillments.
- `MissionService.run_mission_side_effects_isolated` (post-commit best-effort STORE_PURCHASE).
- EventBus schedule_emit (best-effort, no mutation).

**Impacto indirecto:**
- Cualquier refactor de handler test que empiece a ejercitar complete_order real → toca misión side effects → re-run cross_service_atomicity + invariants I8.
- Si se tocan paths de descuento/privilegios → tests de StorePrivilege en unit/test_store_service.py.
- Backpack fulfillment tests (58 mocks) y promotion "me interesa" (174 mocks) son flujos de usuario importantes pero no tocan el core debit atómico de besitos.

### Otros Flujos de Usuario Importantes (Mapeo Resumido)

| Flujo | Handler Test File | get_service / total mocks (aprox) | Realidad | Notas |
|-------|-------------------|-----------------------------------|----------|-------|
| "Me interesa" (promotions) | tests/handlers/test_promotion_user_handlers.py | 66-80 get_service / 174 total | Isolation pesada | Usuario expresa interés → notif admins. No dinero. Menos crítico que tienda pero alto volumen UX. |
| Misiones de usuario (claim, progress, list) | tests/handlers/test_mission_user_handlers.py | 47 get_service / 95 total | Isolation + algunos service unit reales | Toca gamif (credits via reward), pero golds de cross/reaction_mission protegen. |
| Narrativa (story quiz, advance, achievements) | tests/handlers/test_story_user_handlers.py | 84-95 get_service / 186 total | Isolation | CRÍTICO #2 (narrativa). No tocar sin gold re-runs de story + archetype. Mocks pesados en quiz/FSM. |
| Backpack (fulfillment retry, read chapter, VIP resend) | tests/handlers/test_backpack_handler.py | 35 get_service / 58 total | Isolation | Post-compra. Toca fulfillment + VIP. Menos mocks pero aún detached. |
| Gamificación usuario (balance, daily, history, reactions) | tests/handlers/test_gamification_user_handlers.py + _integration.py | 79 en unit-style; integration ya usa real Besito/DailyGiftService | Híbrido: integration existe (precedente bueno) | El único flujo de usuario con estilo integration real + real service. Modelo a copiar. |

**No hay "handler integration" para store, promotion, story, mission user, backpack.** Solo gamif + common.

---

## Mapa de Impacto Indirecto (Cadenas)

| Archivo Afectado | Cadena de Dependencia |
|------------------|-----------------------|
| tests/handlers/test_store_user_handlers.py (cualquier conversión) | handler test → real StoreService → local BesitoService (debit PURCHASE) → db commit → post-commit: FulfillmentService + run_mission_side_effects_isolated (STORE_PURCHASE) → cross atomicity / invariants I8 |
| tests/unit/test_store_service.py (gold atomic + complete_order tests) | service unit (real db) → patch PackageService/Fulfillment para deliver → 1-line/guard ports para BesitoService local post-Item10 |
| tests/integration/test_cross_service_atomicity.py | store purchase side-effect (mission) → re-run obligado |
| tests/integration/test_invariants.py (I8) | order status COMPLETE irreversible |
| bot.py (listener reg) + services/event_bus.py | si se agrega observer store (ya hecho en Item10); 0 impacto en tests de mocks |
| handlers/store_admin_handlers.py | si indirectamente se tocan fixtures de productos/tiers en tests de user; 0 impacto directo (ya hardened) |

---

## Tests que DEBES Correr Antes (y Después de Cualquier Refactor)

**Golds obligatorios (0 regression permitida):**
```bash
# Store atomic contract (real DB + TestSession + local besito)
pytest tests/unit/test_store_service.py -k "TestStorePurchaseAtomicGold or complete_order" -q --tb=line -p no:cov --override-ini="addopts="

# Cross atomicity (incluye side effects de purchase → misiones)
pytest tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="

# Invariants (I8 order status irreversible)
pytest tests/integration/test_invariants.py -q --tb=line -p no:cov --override-ini="addopts="

# Reaction/mission chains (protegen gamif crítico)
pytest tests/integration/test_reaction_full_chain.py tests/integration/test_reaction_mission_flow.py tests/integration/test_reaction_limit.py -q --tb=line -p no:cov --override-ini="addopts="

# Daily atomic
pytest tests/unit/test_daily_gift_service.py -q --tb=line -p no:cov --override-ini="addopts="

# VIP flows (canales-VIP crítico)
pytest tests/integration/test_vip_flow.py tests/integration/test_vip_flows.py tests/integration/test_vip_complete_cycle.py -q --tb=line -p no:cov --override-ini="addopts="

# Broad smoke (post-cambio)
pytest -k "store or atomicity or mission or reaction or daily or vip" -q --tb=line -p no:cov --override-ini="addopts=" 2>&1 | tail -20
```

**Handler store específico (después de ports):**
```bash
pytest tests/handlers/test_store_user_handlers.py -q --tb=line -p no:cov --override-ini="addopts="
pytest tests/handlers/test_store_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="
```

**Re-runs de golds post-cualquier edit en tests de purchase paths (incluyendo 1-line ports):**
- cross_service_atomicity (full)
- test_store_service (atomic gold + complete_order + discount tests)
- invariants (I8)
- reaction_mission_flow (side effects)
- Si se tocan discounts/privilegios: unit/test_store_service.py discount tests

---

## Tests que FALTAN (Riesgo No Cubierto — Confianza de Realidad Baja)

- [ ] test_store_user_purchase_success_integration — no existe (solo gold en service unit)
- [ ] test_store_user_purchase_insufficient_balance_shows_exact_amount — mockeado, no real debit path
- [ ] test_store_user_product_detail_with_active_discount_and_tier — ctx mockeado
- [ ] test_store_user_direct_buy_monthly_cap_blocks_end_to_end — mock
- [ ] test_store_user_purchase_triggers_store_mission_side_effect — solo indirecto vía service
- [ ] test_promotion_user_express_interest_real_flow — isolation
- [ ] test_backpack_fulfillment_retry_real_delivery — isolation
- [ ] test_mission_user_claim_real_progress_persist — isolation (aunque service unit cubre)
- [ ] test_story_user_quiz_real_archetype_calc — isolation (crítico narrativa)

**Patrón faltante:** Solo 2 archivos de handlers usan pytestmark=integration + real service: gamification_user + common. Ninguno para store (el más importante para usuario + dinero).

---

## Precauciones Específicas

1. **Item10 precedent (locals BesitoService):** Cualquier test que parchee "services.store_service.BesitoService" o acceda a service.besito_service debe portearse con 1-line guard:
   ```python
   bal = (BesitoService(db=db_session).get_balance(tg)
          if not hasattr(svc, "besito_service") else svc.besito_service.get_balance(tg))
   ```
   Ver test_store_service.py líneas ~210, ~420+ y cross_service_atomicity 1-line ports.

2. **Complete_order post-commit best-effort:** En tests de integración handler que lleguen a complete_order real, fulfillment (PackageService.deliver) y mission side effects son fire-and-forget. Patch PackageService/FulfillmentService dentro del test de service (como ya hace el gold), o aceptar que delivery no se ejecuta en handler test (solo verifica orden COMPLETE + tx PURCHASE).

3. **Fixtures ricos requeridos para store integration:**
   - Productos con package real (para file_count/preview).
   - Productos con tier (StoreTier) + REQUIRED_PREV_TIER_PURCHASES=2.
   - Productos con monthly_stock_cap + Fulfillment config.
   - StorePrivilege (descuento) para effective_price.
   - BesitoBalance con telegram_id = user.telegram_id (contrato TG BigInt).
   - Ordenes con items para history.

4. **No tocar golds de 3 crit:** cross_service_atomicity.py, reaction_*.py, test_invariants.py (I1-I9), vip_*.py, daily atomic. Solo re-correrlos. Si un port de test_store causa falla en estos, es señal de que el port rompió contrato (revertir).

5. **get_service context manager:** Al convertir, usar el patrón de gamif:
   ```python
   real_svc = StoreService(db_session)
   with patch("handlers.store_user_handlers.StoreService") as MockStore:
       MockStore.return_value = real_svc
       # test
   ```
   NO parches get_service directamente en el nuevo estilo (el integration gamif parchea el class name, no el ctx manager get_service).

6. **CallbackData tests (test_callbackdata_store*.py):** Son packing only. No los toques para "realism"; son correctos como están (unit de serialización).

7. **Arch-enforcer gate:** Cualquier pool item debe pasar arch con 0 critical (1-service via get_service ya está en handlers; puros si se extraen helpers de tests; logging; <=50 si se tocan funcs largas; 3 crit protegidos).

---

## Recomendación de Pool de <=4 Items (Tests Only, Tight, Hardener-Compliant)

**Pool phrase (al cerrar):** "Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool."

**Propuesta de 4 items (o 3 si se quiere más tight):**

1. **Item A: Store user purchase paths a estilo integration (core)**
   - Scope: TestDirectBuy + TestConfirmDirectBuy + TestProductDetail (context paths) + TestPurchaseHistory.
   - Convertir a usar real StoreService(db_session) vía class patch (como gamif).
   - Agregar 1-2 tests nuevos de "purchase success" y "insufficient after effective discount" que lleguen a complete_order y verifiquen tx PURCHASE + order COMPLETE + balance delta (reusando fixtures del gold atomic).
   - Ports de 1-line/guard donde se acceda a besito interno.
   - Re-correr golds + store handler tests.
   - 0 prod change.

2. **Item B: Reducir mocks en test_store_service.py para purchase paths**
   - Scope: En TestStoreService y TestStorePrivilegeDiscount, donde hay MagicMock de query o parches de Fulfillment/Package para paths de complete_order/direct, preferir DB real + fixtures cuando posible.
   - Mantener los patches necesarios para deliver (external a TG) pero documentar "external only".
   - Asegurar que los gold atomic (TestStorePurchaseAtomicGold) sigan pasando sin cambios (o con 1-line ports documentados).
   - Re-runs de atomic gold + cross + invariants.

3. **Item C: Agregar / extender integración dedicada para store purchase E2E paths (usando TestSession/file si necesario)**
   - Basado en el gold existente en unit/test_store_service.py (TestSession + 7770x + explicit models + try/finally).
   - Cubrir: success (debit + stock + COMPLETE + side effects best effort), insufficient, cap agotado, tier locked, descuento aplicado una sola vez.
   - Si se usa TestSession, tolerar N806 + docstring DESIRED CONTRACT (copiar al pie de cross atomicity).
   - Verificar que no duplica el gold atómico existente (extender o referenciar).

4. **Item D (opcional, si pool de 4):** Audit + un cluster pequeño de otro flujo alto-impacto usuario (e.g. promotion_user "me interesa" o backpack fulfillment callbacks) para aplicar mismo patrón de reducción de mocks. O dejar para siguiente pool. Mantener tight: solo si Item A-C cierran limpio.

**Entregables por item (hardener):**
- GSD pre-log antes de cada edit/gate.
- self-check PASSED en executor.
- arch-enforcer: PASS / PASS WITH NOTES (0 critical).
- test-guardian: "suite protege adecuadamente" + re-runs de golds listados + veredicto.
- Documentador al cierre del pool (actualiza ROADMAP + extract learnings + agent-memory + MEMORY.md).

**No scope creep:** Nada de prod code, nada de cambiar contratos de servicio, nada de tocar golds de 3 crit (solo re-correr), nada de agregar listeners nuevos (ya hecho en Item10), nada de cambiar get_service o EventBus.

---

## Riesgos Específicos de Este Mapeo / Refactor de Tests

- **Riesgo 1 (alto):** Tocar paths de debit en tests de store puede requerir ports de 1-line/guard en múltiples sitios (cross atomicity, store service unit, cualquier test que haga `service.besito_service`). Precedente existe y está documentado; copiar al pie.
- **Riesgo 2:** Fixtures de db_session (in-memory) vs TestSession (file) para atomic: complete_order hace commit interno + debit commit=False. Si el port de handler test usa db_session fixture, puede haber DetachedInstance o visibility issues post-commit. Usar TestSession para paths que ejerciten complete_order (como el gold).
- **Riesgo 3:** Fulfillment dispatch en tests reales puede enviar a TG mock o fallar si no hay Package real con files. El gold ya parchea PackageService.deliver; seguir ese patrón.
- **Riesgo 4:** Mission side effects (STORE_PURCHASE) en post-commit: si el test no tiene misión configurada, el side effect es no-op (best effort, swallowed). No rompe, pero para "realism completo" se puede seedear una misión STORE_PURCHASE en el test de integración.
- **Riesgo 5 (bajo):** Cambiar 250+ líneas de mocks en test_store_user_handlers.py es churn de tests; mantener UI 1:1 (textos, botones, callbacks) para que arch no marque como regression visual.

---

## Resumen Ejecutivo + Próximos Pasos

**Estado actual de confianza de realidad:**
- 3 sistemas críticos: bien protegidos por golds con real DB + real services (cross, reaction, daily, invariants, vip).
- Flujos de usuario tienda: baja confianza — 1873 LOC de tests con 252 get_service patches + MagicMock para todo el contexto de compra (precio efectivo, tiers, caps, stock, preview). El contrato atómico de debit está en gold de service unit, pero el flujo "usuario clickea comprar → ve confirmación con precio correcto → complete → ve mensaje de éxito" está 100% mockeado.
- Otros flujos (promoción, misión user, story user, backpack): también isolation pesada, pero menor impacto económico que tienda.

**Mapeo entregado:** Este archivo en .grok/agent-memory/impact-analyzer/33-test-reality-user-flows-mapeo.md

**Recomendación:** Iniciar pool de 3-4 items siguiendo el estándar hardener (impact → planner → executor con GSD pre + self-check → arch → test-guardian → tests + pool phrase). Empezar por Item A (store purchase paths a integration style) porque es el de mayor valor para "confianza de realidad del usuario" y toca el límite atómico más sensible.

**No decir "parece que solo afecta X".** Se trazó:
- 19 archivos de handler tests con get_service patches.
- Store domina con 252/1152.
- Cadena completa handler → StoreService → Besito local → Fulfillment → Mission side effects → cross/invariants.
- Golds obligatorios listados explícitamente.
- Precauciones de Item10 + fixtures + TestSession documentadas.

**Siguiente agente en secuencia (si se procede):** gsd-planner con este mapeo como input, para producir PLAN.md tight con fases, DoD, patrones a copiar (gamif integration + atomic gold), y lista exacta de tests a re-correr.

---

**Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.**

*Fin del reporte de mapeo (impact-analyzer).*
