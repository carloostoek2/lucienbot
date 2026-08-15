# Impact Analysis: Reaction Ecosystem Week 3 — Beneficio vs Riesgo

**Item:** `reaction-ecosystem-week3` (pre-planificación)  
**Date:** 2026-07-06  
**Mode:** Analysis only — NO implementación  
**Builds on:** Week 1 (prod refactor) + Week 2 (tests/docs/defer) — cluster cerrado  
**Audience:** Decisión go/no-go antes de lanzar gsd-planner

---

## Executive Summary

Semana 3 propone **tres frentes** que quedaron fuera de Week 1–2. No son equivalentes en valor: uno es casi puro upside (tests admin), otro es deuda técnica cosmética, y el tercero es el único con **impacto real en integridad de datos** pero también el de **mayor blast radius**.

| # | Frente | Beneficio | Riesgo | Ratio B/R | Recomendación |
|---|--------|-----------|--------|-----------|---------------|
| **3A** | Test integración `tracking_failed` (wizard admin) | **Alto** (ops + DX) | **Muy bajo** | **8:1** | ✅ **Hacer** — Week 3 ítem 1 |
| **3B** | Refactor estructural `check_and_register_reaction` (≤50 LOC, sin cambiar tx) | **Medio** (mantenibilidad) | **Bajo** | **3:1** | ✅ **Hacer** — Week 3 ítem 2 (opcional) |
| **3C** | Eliminar `register_reaction` + migrar 2 tests legacy | **Bajo** (claridad) | **Bajo** | **2:1** | ⚠️ **Opcional** — solo si hay tiempo |
| **3D** | `credit_besitos(commit=False)` unificación atómica REACTION | **Alto** (integridad teórica) | **Muy alto** | **1:3** | ❌ **No ahora** — spike aislado o post-incidente |
| **3E** | Fix prod `tracking_failed` (retry/repair message_id) | **Alto** (UX ops real) | **Medio** | **4:1** | ⚠️ **Evaluar separado** — feature behavior, no hardening puro |

**Recomendación global:** Week 3 **acotada** = **3A + 3B** (tests + refactor extract-only). **No incluir 3D** en el mismo pool que tests — blast radius incompatible con "0 behavior change".

---

## Contexto: qué ya está resuelto (Week 1–2)

| Área | Estado |
|------|--------|
| Markup unificado | ✅ `broadcast_channel_markup.py` |
| Handler 1 svc / 1 call | ✅ `process_channel_reaction` |
| Validators extraídos | ✅ `reaction_validators.py` |
| Golds path producción | ✅ `full_chain` → `process_channel_reaction` |
| `message_id=0` → `message_mismatch` | ✅ test unitario (simula `tracking_failed`) |
| Docs alineados | ✅ `services/broadcast/CLAUDE.md` |
| `credit_besitos(commit=False)` | ❌ **DEFER** documentado en `decisions.md` |

**Golds actuales:** 117+ tests reaction/broadcast green. **0 regresiones** en atomicity desde Week 1.

---

## Frente 3A — Test integración `tracking_failed` (admin wizard)

### Qué falta hoy

- **Unit:** `test_message_mismatch_when_broadcast_stuck_at_message_id_zero` cubre el *efecto downstream* (reacción rechazada).
- **Handler:** `test_broadcast_handlers.py` cubre `sent` y `send_failed`, **no** `tracking_failed`.
- **Gap:** No hay test que verifique que `confirm_and_send_broadcast`:
  1. Llama `publish_broadcast_to_channel`
  2. Recibe `("tracking_failed", real_message_id)`
  3. Muestra alerta admin: *"Mensaje enviado, pero Lucien no pudo registrar el ID..."*
  4. **No** llama `notify_broadcast_send_success` (solo alerta)

### Beneficio

| Dimensión | Puntuación (1–5) | Detalle |
|-----------|------------------|---------|
| Protección regresión | 5 | Cierra el único hueco E2E admin→reacción no cubierto |
| Valor operativo | 4 | Documenta en código el fallo que admins ven en prod |
| Esfuerzo | 5 | ~1 test, mocks existentes, 0 prod |
| Alineación hardener | 5 | 0 behavior, 0 atomicity |

**Beneficio total: ALTO**

### Riesgo

| Dimensión | Puntuación (1–5) | Detalle |
|-----------|------------------|---------|
| Romper golds | 1 | Solo `tests/handlers/test_broadcast_handlers.py` |
| Behavior change | 1 | Ninguno |
| Acoplamiento | 1 | Patrón idéntico a `test_sends_with_markup_in_single_step` |

**Riesgo total: MUY BAJO**

### Ratio beneficio/riesgo: **~8:1** → **GO**

### Archivos tocados (estimado)
- `tests/handlers/test_broadcast_handlers.py` (+1 test)
- Opcional: test de `publish_broadcast_to_channel` aislado (pure helper)

### Tests gate
```bash
pytest tests/handlers/test_broadcast_handlers.py -q --tb=line -p no:cov --override-ini="addopts="
```

---

## Frente 3B — Refactor estructural `check_and_register_reaction` (sin cambiar transacción)

### Estado actual

- **149 LOC** total en `check_and_register_reaction`
- Validators ya extraídos (~27 LOC orquestación validación)
- **~100 LOC** cuerpo transacción: INSERT → flush → credit → commit → missions → IntegrityError

### Beneficio

| Dimensión | Puntuación | Detalle |
|-----------|------------|---------|
| Regla 50 LOC | 3 | Cumple naming/arch en validators; monolito tx sigue violando regla |
| Onboarding / cambios futuros | 4 | Más fácil parchear IntegrityError / logging sin tocar 150 líneas |
| Bugs encontrados | 1 | No corrige el split-tx; solo legibilidad |

**Beneficio: MEDIO** (mantenibilidad, no corrección funcional)

### Riesgo

| Dimensión | Puntuación | Detalle |
|-----------|------------|---------|
| Romper contrato dict | 2 | Bajo si copy-paste estricto |
| Romper atomicity | 2 | Bajo si **no** se toca orden flush/credit/commit |
| Regresiones gold | 2 | 28 tests `reaction_flow` + 10 `cross_service_atomicity` |

**Riesgo: BAJO** con disciplina extract-only

### Enfoque seguro propuesto

Extraer helpers **privados** en `broadcast_service.py` o `services/broadcast/reaction_persistence.py`:

```python
def _insert_reaction_row(...) -> BroadcastReaction  # flush only
def _handle_reaction_integrity_error(exc, ...) -> dict  # reason mapping
async def _run_reaction_mission_effects(...) -> int  # post-commit
```

**Orquestador `check_and_register_reaction` ≤45 LOC** — misma secuencia byte-a-byte.

### Ratio B/R: **~3:1** → **GO** (opcional, no bloqueante)

---

## Frente 3C — Eliminar `register_reaction` + migrar tests legacy

### Consumidores restantes

| Archivo | Uso |
|---------|-----|
| `test_broadcast_service.py` | 1 test `SELECT FOR UPDATE` en legacy |
| `test_reaction_mission_flow.py` | 1 test sync `complete_reaction_mission_flow_with_real_data` |
| `test_reaction_limit.py` | 1 test `no_daily_reaction_limit` (loop multi-emoji sync) |

### Beneficio

- Elimina doble camino mental (deprecated vs prod)
- Reduce 87 LOC deprecated en servicio

**Beneficio: BAJO** — prod ya usa solo async path

### Riesgo

- Reescribir 3 tests con semántica distinta (misiones sync vs `run_mission_side_effects_isolated`)
- Pérdida de cobertura `SELECT FOR UPDATE` si se borra sin reemplazo async

**Riesgo: BAJO–MEDIO**

### Ratio B/R: **~2:1** → **OPCIONAL** — no crítico para robustez

---

## Frente 3D — `credit_besitos(commit=False)` unificación atómica ⚠️

### Problema que intenta resolver

**Split-tx actual** (`broadcast_service.py:437-460`):

```
flush(BroadcastReaction)
  → credit_besitos()  # commit interno (balance + BesitoTransaction + EventBus)
  → db.commit()       # commit fila reacción
```

**Ventana de inconsistencia:** Si `credit_besitos` **commit exitoso** y `db.commit()` **falla** (caída DB, timeout, error de conexión), quedan **besitos acreditados sin `BroadcastReaction`** — crédito huérfano.

### ¿Qué tan probable es?

| Factor | Evaluación |
|--------|------------|
| Frecuencia histórica en prod | **Sin evidencia** en logs/decisions (Week 2 defer) |
| Mitigación actual | `credit_failed` → rollback antes de credit commit; UC anti-duplicados |
| `get_or_create_balance` | Hace **commit propio** al crear saldo nuevo (L55 `besito_service.py`) — otro split incluso con `commit=False` |
| Severidad si ocurre | **Media-alta** (usuario gana besitos sin registro de reacción; analytics/replay inconsistente) |

**Beneficio real:** **ALTO en teoría**, **BAJO en práctica** hasta que haya incidente o métrica de huérfanos.

### Blast radius si se implementa

| Área | Impacto |
|------|---------|
| `besito_service.credit_besitos` | Nuevo param `commit: bool = True` — API pública |
| Callers producción | **15+ sitios**: broadcast(2), game(6), reward, story, daily_gift, admin grant |
| EventBus | `schedule_emit` debe seguir **post-commit final**, no post-credit intermedio |
| Golds | `test_cross_service_atomicity` (10 escenarios), `test_besito_service`, daily atomic, game, invariants |
| Contrato "credit survives deliver False" | **Podría romperse** si se cambia timing de commits |
| 3 sistemas críticos | Gamificación **directo**; narrativa/store **indirecto** vía EventBus |

### Esfuerzo estimado

- Implementación: 2–4 h
- Re-gold completo + fix regressions: **4–8 h**
- Riesgo de regresión silenciosa: **no despreciable**

### Ratio beneficio/riesgo: **~1:3** → **NO-GO para Week 3 estándar**

### Alternativas de menor riesgo (ordenadas)

1. **Observabilidad** — query/script: `BesitoTransaction REACTION` sin matching `BroadcastReaction` (read-only, HealthService)
2. **Spike en branch aislado** — solo REACTION path + 1 test de atomicidad nueva; no merge sin golds 100%
3. **Fix puntual `get_or_create_balance`** — `commit=False` al crear saldo dentro de tx padre (sub-problema)
4. **Implementar solo post-incidente** — criterio ya en `decisions.md` Week 2

---

## Frente 3E — Fix producción `tracking_failed` (fuera de hardening puro)

### Comportamiento actual

Mensaje **sí** llega al canal; BD queda con `message_id=0`; reacciones fallan con `message_mismatch`; admin ve alerta pero **no hay repair**.

### Beneficio ops

| Acción | Beneficio |
|--------|-----------|
| Retry `update_broadcast_message_id` (3x) | Recupera mayoría de fallos transitorios |
| Job repair: listar broadcasts `message_id=0` + backfill manual | Recupera casos ya ocurridos |
| Eliminar broadcast huérfano si tracking falla | Evita reacciones rotas; **pierde** mensaje en canal |

**Beneficio: ALTO** para operación real Diana

### Riesgo

- **Behavior change** visible (retry, posible delete)
- Requiere decisión producto: ¿reintentar, alertar, o rollback TG message?

**Ratio B/R: ~4:1** pero **scope ≠ hardening** — recomendar **fase separada** o item de producto

---

## Matriz de decisión recomendada

```
                    RIESGO
                 Bajo    Alto
              ┌────────┬────────┐
    Alto      │  3A ✅  │  3D ❌  │
BENEFICIO     │  3E ⚠️  │        │
              ├────────┼────────┤
    Bajo      │  3B ✅  │        │
              │  3C ⚠️  │        │
              └────────┴────────┘
```

---

## Week 3 propuesta acotada (para gsd-planner)

### Pool item: `reaction-ecosystem-week3-tight`

**Scope:** 0 prod code, 0 atomicity change (igual Week 2)

| Task | Entregable | B/R |
|------|------------|-----|
| T1 | `test_tracking_failed_shows_alert_and_skips_success_notify` en `test_broadcast_handlers.py` | 8:1 |
| T2 | (Opcional) test aislado `publish_broadcast_to_channel` retorna `tracking_failed` | 7:1 |
| T3 | (Opcional) extract `_handle_reaction_integrity_error` + `_finalize_reaction_success` — orquestador ≤50 LOC | 3:1 |

**NO incluir en este pool:** 3D, 3E, eliminación `register_reaction`

### Si el usuario quiere 3D igualmente

**Secuencia obligatoria (pool separado `reaction-atomicity-spike`):**

1. Script observabilidad huérfanos (read-only) — 1 día
2. Spike `commit=False` **solo** en `check_and_register_reaction` + fix `get_or_create_balance` commit
3. Golds: `cross_service_atomicity` + `reaction_flow` + `besito_service` + `daily_gift` atomic
4. Canary/staging con carga concurrente (gather duplicate test production-like)
5. **Solo entonces** merge — estimar **2do pool de 4**, no mezclar con tests

---

## Tests a correr (cualquier opción Week 3)

```bash
# Gate mínimo (3A)
pytest tests/handlers/test_broadcast_handlers.py -q --tb=line -p no:cov --override-ini="addopts="

# Gate reaction cluster completo
pytest -k "reaction or broadcast_channel_markup or TestHandleReaction or TestConfirmAndSendBroadcast" \
  -q --tb=line -p no:cov --override-ini="addopts="

# Si 3B (refactor tx)
pytest tests/unit/test_broadcast_service_reaction_flow.py \
  tests/integration/test_cross_service_atomicity.py -q --tb=line -p no:cov --override-ini="addopts="

# Si 3D (NO recomendado sin spike)
pytest tests/unit/test_besito_service.py tests/integration/test_cross_service_atomicity.py \
  tests/integration/test_reaction_full_chain.py -q --tb=line -p no:cov --override-ini="addopts="
```

---

## Ready for chain

**Handoff a usuario:** Elegir variante:

| Opción | Contenido | Riesgo pool |
|--------|-----------|-------------|
| **A (recomendada)** | Solo 3A (+ opcional 3B) | Mínimo |
| **B** | A + 3C eliminar legacy | Bajo |
| **C** | A + 3E fix prod tracking | Medio (behavior) |
| **D** | 3D atomicidad | Alto — pool aparte |

**Handoff a gsd-planner:** Tras decisión usuario, crear `.planning/quick/20260706-reaction-ecosystem-week3/PLAN.md` con scope explícito de opción elegida.

---

**Analysis only** — no implementación en este paso.