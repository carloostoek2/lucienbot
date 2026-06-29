# 📊 Análisis de Impacto: admin-forward-besitos-grant (Item 36)

**Date:** 2026-06-29  
**Agent:** impact-analyzer  
**PLAN:** `.planning/phases/36-admin-forward-besitos-grant/PLAN.md`  
**Analysis only** — ready for gsd-executor → arch-enforcer → test-guardian → pytest F5

---

## Cambio Propuesto

Extender el flujo de reenvío admin en `handlers/vip_handlers.py`:

| Hoy | Target |
|-----|--------|
| Admin reenvía mensaje → extrae candidato → **1× VIPService** (tarifas) → selección tarifa directa | Admin reenvía → extrae candidato → **menú acción** (0 svc) → «Activar VIP» \| «Otorgar besitos» \| Cancelar |
| Solo rama VIP | Rama VIP: misma lógica `grant_vip_from_tariff`, entrada vía botón |
| — | Rama besitos: cantidad → confirmar → `BesitoService.grant_manual_admin_besitos()` → `credit_besitos(..., TransactionSource.ADMIN)` |

Nuevo método delgado en `services/besito_service.py`; teclado `forward_action_keyboard()` en `keyboards/inline_keyboards.py`; FSM `VIPForwardActivationStates` → `AdminForwardStates`.

---

## Riesgo Total: **CRÍTICO (acotado)** → ejecución segura con scope PLAN

**Por qué CRÍTICO:** Toca **BesitoService** (crédito económico + EventBus post-commit) y **entrada VIP forward** (canales-VIP).  
**Por qué acotado:** Sin cambio de contrato en `credit_besitos` / `grant_vip_from_tariff`; sin migraciones; sin nuevos listeners; 7 archivos máx.

**HIGH risks identificados:** 1 (regresión UX VIP forward). **Mitigado** por tests de regresión PLAN F2/F4. **0 HIGH sin mitigación.**

---

## Mapa de Impacto Directo (Nivel 1)

| Archivo | Línea(s) / zona | Por qué se ve afectado |
|---------|-----------------|------------------------|
| `handlers/vip_handlers.py` | 47-50 (FSM), 52-120 (puros notify), 536-652 (forward handlers) | Cambio principal: menú acción, FSM unificada, handlers besitos, rename entrypoint, VIP path re-entrada por botón |
| `keyboards/inline_keyboards.py` | ~305+ (nuevo `forward_action_keyboard`) | Contrato callback ↔ handler: `forward_action_vip`, `forward_action_besitos`, `cancel_forward_action` |
| `services/besito_service.py` | post-`credit_besitos` (~107+) | Nuevo `MAX_ADMIN_BESITO_GRANT` + `grant_manual_admin_besitos()` (wrapper → `credit_besitos`) |
| `tests/handlers/test_vip_handlers.py` | 117-146, 148-172, 284-297 | **Breaking esperado:** detección ya no llama VIPService; FSM rename; nuevos casos besitos |
| `tests/unit/test_besito_service.py` | sección transacciones | Nuevos tests ADMIN grant + max cap |
| `decisions.md` | append | Documentación post-gates Item 36 |

**Estado actual verificado (grep):**
- `VIPForwardActivationStates` / `process_forwarded_vip_candidate`: **solo** `vip_handlers.py` + `test_vip_handlers.py` (rename seguro).
- `grant_manual_admin_besitos`: **no existe** aún (greenfield wrapper).
- `TransactionSource.ADMIN`: ya en `models/models.py:220`; usado en tests (`test_invariants.py`), **sin path producción admin besitos** hasta este item.

---

## Mapa de Impacto Indirecto (Nivel 2+)

### Nivel 2 — Llamados por código tocado

| Archivo | Cadena de dependencia |
|---------|----------------------|
| `services/besito_service.credit_besitos` | `grant_manual_admin_besitos` → FOR UPDATE + commit + `_schedule_besitos_awarded_event` |
| `services/event_bus.py` | `schedule_emit` / `EVENT_BESITOS_AWARDED` disparado post-commit del crédito ADMIN |
| `bot.py` L225-230 | 6 listeners ya registrados reciben payload con `source=admin` (sin cambio de registro) |
| `services/story_service.py` | `on_besitos_awarded_from_gamification` — log observacional |
| `services/reward_service.py` | `on_besitos_awarded_rewards_observer` — observacional |
| `services/broadcast_service.py` | `on_besitos_awarded_broadcast_reaction_observer` — observacional |
| `services/game_service.py` | `on_besitos_awarded_game_award_observer` — observacional |
| `services/store_service.py` | `on_besitos_awarded_store_observer` — observacional |
| `services/streak_promotion_service.py` | `on_besitos_awarded_streak_promotion_observer` — observacional |
| `middlewares/idempotency.py` | Protege `confirm_forward_besitos_grant` (y resto CBs) contra double-execution TG retry |
| `handlers/__init__.py` | Import `vip_router` — sin cambio de wiring |
| `utils/admin.py` | `is_admin()` guard en todos los handlers forward — sin cambio |

### Nivel 3 — Sin touch pero deben seguir verdes (golds)

| Archivo | Relación |
|---------|----------|
| `services/vip_service.py` | `grant_vip_from_tariff` — **0 cambio**; forward VIP lo invoca igual tras menú |
| `services/broadcast_service.py` | `check_and_register_reaction` — path reacción independiente |
| `services/daily_gift_service.py` | `claim_gift` — path daily independiente |
| `services/reward_service.py` | `_deliver_besitos` — path misión independiente |
| `handlers/gamification_user_handlers.py` | Reacciones — 0 overlap con forward filter |
| `handlers/channel_handlers.py` | `forward_from_chat` en FSM canal — filtro distinto (`ChannelStates.waiting_channel_message`) |

**0 consumidores** de `forward_action_*` / `grant_manual_admin_besitos` fuera del scope (pre-implementación).

---

## Riesgos a 3 Sistemas Críticos

### 1. Gamificación (BesitoService / créditos)

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Nuevo path credit sin lock | BAJA | Reusa `credit_besitos` (SELECT FOR UPDATE + commit atómico) |
| Double grant por retry CallbackQuery | MEDIA | `IdempotencyMiddleware` global corta antes del handler |
| Handler llama `credit_besitos` directo (bypass wrapper/logging) | MEDIA | PLAN prohíbe; arch-enforcer grep `confirm_forward_besitos_grant` = 1× `get_service(BesitoService)` |
| EventBus re-entrancy (listener credit de vuelta) | BAJA | 6 listeners con contrato **MUST NOT credit/debit/mutate**; golds `test_on_besitos_awarded_*` |
| Regresión reaction/daily/mission/store debit | BAJA | 0 cambio en composers existentes; golds F5 |

**Contratos atómicos / EventBus / get_service (besitos branch):**

```
confirm_forward_besitos_grant (handler entrypoint)
  └─ with get_service(BesitoService) as svc:     # EXACTLY 1
       └─ grant_manual_admin_besitos(...)
            └─ credit_besitos(..., ADMIN)        # commit interno
                 └─ schedule_emit(besitos_awarded)  # best-effort, post-commit
notify_forward_besitos_result(...)               # 0 svc, best-effort send
```

### 2. Narrativa (StoryService / EventBus listeners)

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Listener reacciona a ADMIN award mutando progreso/besitos | BAJA | `on_besitos_awarded_from_gamification` solo log; test `test_on_besitos_awarded_listener_does_not_mutate_besitos` |
| ADMIN en invariant tests confunde semántica | BAJA | `test_invariants.py` usa ADMIN como seed — ortogonal al nuevo path |

**0 archivos narrative a tocar.**

### 3. Canales-VIP (VIPService / forward grant)

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Regresión forward VIP (grant roto o UX rota) | **ALTA** | `grant_vip_from_tariff` intacto; tests `test_forward_vip_path_unchanged_after_action_select` + confirm suite existente |
| Detección forward deja de listar tarifas (0 tarifas UX) | MEDIA | Movido a `select_forward_action_vip` (1 svc); mensaje error si vacío |
| FSM rename rompe estados confirm | MEDIA | Actualizar tests + filtros `@router.callback_query(AdminForwardStates.vip_*)` |
| Bloqueo visitante post-grant besitos | BAJA | Besitos ya acreditados; notify best-effort (patrón VIP blocked sin deep link) |

**Contrato VIP forward post-cambio:**

```
process_forwarded_admin_candidate     # 0 svc (CAMBIO: antes 1 svc)
select_forward_action_vip             # 1 svc get_all_tariffs
select_tariff_for_forward_vip         # 0 svc (sin cambio lógico)
confirm_forward_vip_activation        # 1 svc grant_vip_from_tariff (sin cambio)
```

---

## Archivos Exactos a Tocar

| Archivo | Acción |
|---------|--------|
| `handlers/vip_handlers.py` | **Modificar** (principal) |
| `keyboards/inline_keyboards.py` | **+** `forward_action_keyboard()` |
| `services/besito_service.py` | **+** `MAX_ADMIN_BESITO_GRANT`, `grant_manual_admin_besitos()` |
| `tests/handlers/test_vip_handlers.py` | **Actualizar** + nuevos casos besitos/VIP regression |
| `tests/unit/test_besito_service.py` | **+** tests ADMIN grant |
| `decisions.md` | **Append** post-gates |
| `.planning/phases/36-admin-forward-besitos-grant/PLAN.md` | Referencia (ya existe) |

---

## Archivos que **NO** deben tocarse

| Categoría | Archivos |
|-----------|----------|
| **Modelos / BD** | `models/models.py`, `alembic/versions/*` — `TransactionSource.ADMIN` ya existe |
| **VIP core** | `services/vip_service.py`, `handlers/vip_user_handlers.py`, `handlers/common_handlers.py` |
| **Gamificación composers** | `services/broadcast_service.py`, `services/daily_gift_service.py`, `services/game_service.py`, `services/reward_service.py`, `services/store_service.py`, `services/mission_service.py` |
| **Narrativa** | `services/story_service.py`, `handlers/story_*.py` |
| **EventBus wiring** | `bot.py`, `services/event_bus.py` — sin nuevo listener |
| **Otros handlers admin** | `handlers/gamification_admin_handlers.py` (config besitos ≠ grant manual) |
| **Middleware** | `middlewares/idempotency.py` — ya cubre nuevos CBs |
| **Utils voice** | `utils/lucien_voice.py` — textos inline en puros handler (PLAN) |
| **VIP menu keyboard** | `vip_management_keyboard()` — flujo es por reenvío, no menú VIP |

---

## Tests que DEBES Correr / Crear

### Gate F5 (obligatorio pre-merge)

```bash
pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "vip_handlers or TestBesitoService or cross_service_atomicity or reaction_ or daily_gift or invariants" \
  tests/
```

### Por archivo / dominio

| Suite | Comando | Propósito |
|-------|---------|-----------|
| Handler forward + besitos | `pytest tests/handlers/test_vip_handlers.py -q --tb=line` | Regresión VIP + nueva rama besitos |
| BesitoService unit | `pytest tests/unit/test_besito_service.py -q --tb=line` | ADMIN source, max cap, FOR UPDATE |
| Atomicity gold | `pytest tests/integration/test_cross_service_atomicity.py -q --tb=line` | 0 regresión reaction/mission/daily chains |
| Reaction golds | `pytest tests/integration/test_reaction_full_chain.py tests/integration/test_reaction_mission_flow.py tests/unit/test_broadcast_service_reaction_flow.py -q --tb=line` | Composer reacción intacto |
| Daily gold | `pytest tests/unit/test_daily_gift_service.py -q --tb=line` | Claim atomicity intacta |
| Invariants | `pytest tests/integration/test_invariants.py -q --tb=line` | I1-I3 balance identity con ADMIN seed |
| EventBus contract | `pytest tests/unit/test_event_bus.py tests/unit/test_story_service.py -k besitos_awarded -q --tb=line` | Listeners no mutan |
| Idempotency | `pytest tests/unit/test_idempotency_middleware.py -q --tb=line` | Dedup CB confirm besitos |
| VIP service (sanity) | `pytest tests/unit/test_vip_service.py -k grant_vip -q --tb=line` | Grant core sin cambio |

### Tests a **crear** (PLAN F4 — faltantes hoy)

- [ ] `test_build_forward_action_*` — puros menú/amount/confirm/success/notify
- [ ] `test_parse_positive_besito_amount_*` — 0, neg, >MAX, ok
- [ ] `test_process_forward_shows_action_menu_0_svc` — **reemplaza** expectativa 1 svc en detección
- [ ] `test_forward_vip_path_unchanged_after_action_select` — regresión VIP end-to-end
- [ ] `test_besitos_amount_invalid_rejects` — FSM amount validation
- [ ] `test_confirm_besitos_calls_exactly_1_svc` — contrato get_service
- [ ] `test_grant_manual_admin_besitos_success` — tx ADMIN + balance
- [ ] `test_grant_manual_admin_besitos_respects_max` — cap 10_000
- [ ] (recomendado) `test_confirm_besitos_blocked_visitor_still_credited` — parity VIP blocked pattern

### Tests a **actualizar** (breaking esperado)

- [ ] `test_process_forwarded_vip_candidate_detects_and_uses_exactly_1_svc` → 0 svc + menú acción
- [ ] `test_select_tariff_for_forward_vip_transitions_state_no_svc` → state `AdminForwardStates.vip_*`
- [ ] `test_cancel_vip_forward_clears_state` → `cancel_forward_action` si se generaliza cancel

---

## Precauciones Específicas

1. **Callback contract:** Cada string en `forward_action_keyboard()` debe tener handler en `vip_handlers.py` (grep ambos lados post-edit).
2. **1-svc rule por entrypoint:** Grep post-impl:
   - `process_forwarded_admin_candidate`: 0× `get_service`
   - `select_forward_action_vip`: 1× `get_service(VIPService)`
   - `confirm_forward_vip_activation`: 1× `get_service(VIPService)`
   - `confirm_forward_besitos_grant`: 1× `get_service(BesitoService)`
3. **No acreditar desde handler:** Prohibido `credit_besitos` directo en handler; solo `grant_manual_admin_besitos`.
4. **FSM filters:** Besitos amount handler debe filtrar `AdminForwardStates.besitos_waiting_amount` + `is_admin` para no capturar mensajes admin fuera del flujo.
5. **Confirm callbacks distintos:** VIP mantiene `confirm_vip_forward_activation`; besitos usa `confirm_forward_besitos_grant` — no colisionar con `confirmation_keyboard` reutilizado.
6. **LOC ≤50:** Puros nuevos + `grant_manual_admin_besitos` — inspect post-edit.
7. **Logging:** Formato `besito_service | grant_manual_admin_besitos | user_id=... | target=... | amount=... | result=...`

---

## Veredicto

| Pregunta | Respuesta |
|----------|-----------|
| **¿Scope tight enough?** | **Sí.** 6 archivos funcionales + decisions; PLAN excluye bot/models/composers/middleware; patrón copy-paste VIP forward + thin besito wrapper. |
| **¿HIGH risks sin mitigar?** | **No.** Único HIGH (regresión VIP forward) cubierto por tests F2/F4. Besito double-grant mitigado por IdempotencyMiddleware + confirm único svc. |
| **¿Vale la pena?** | **Sí.** Primer path producción para `TransactionSource.ADMIN`; reutiliza infra atómica/EventBus existente; UX admin unificada forward. |
| **Alternativa menor impacto?** | Menú besitos en `gamification_admin_handlers` sin forward — fuera de scope usuario; duplicaría extracción candidato. |

**Recomendación:** Proceder con gsd-executor siguiendo PLAN fases F1→F5. Ejecutar gate F5 completo antes de merge. arch-enforcer debe validar 1-svc/0-svc por handler y 0 touch fuera de lista.

---

## Handoff

**Ready for:** gsd-executor (PLAN F1-F5) → arch-enforcer → test-guardian → pytest F5 → documentador (opcional pool de 1).