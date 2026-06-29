# Arch-Enforcer Audit Report: Item 36 — admin-forward-besitos-grant

**Date:** 2026-06-29  
**Auditor:** arch-enforcer  
**Task:** Audit Item 36 implementation — extend admin forward flow in `handlers/vip_handlers.py` with besitos grant branch.  
**Feature:** `admin-forward-besitos-grant`

**Scope (5 files):**
- `handlers/vip_handlers.py` — `AdminForwardStates`, action menu, besitos branch, notify helpers
- `keyboards/inline_keyboards.py` — `forward_action_keyboard`
- `services/besito_service.py` — `grant_manual_admin_besitos`, `MAX_ADMIN_BESITO_GRANT`
- `tests/handlers/test_vip_handlers.py`
- `tests/unit/test_besito_service.py` (grant tests)

**Rules checked:** handlers exactly 1 service per entrypoint; no DB in handlers; funcs ≤50 LOC; logging format; `is_admin`; `get_service`; 3 crit protected; Lucien voice.

---

## Methodology

- Full read of changed source files + arch-enforcer.md rules 1–7.
- Grep: `db.query|SessionLocal|db.commit` in `handlers/vip_handlers.py` (forward scope) → 0.
- Grep: `await.*bot\.|bot\.send_message` in `services/besito_service.py` → 0.
- Grep: `get_service` / `with get_service` in forward entrypoints — map 1-svc per handler.
- AST LOC on Item 36 functions in handler + `grant_manual_admin_besitos`.
- Pytest: `tests/handlers/test_vip_handlers.py` + grant tests in `test_besito_service.py` → **14 passed**.

---

## Findings (Classified)

### Critical (Architecture-breaking) — **0 found**

| Rule | Result |
|------|--------|
| R1: Handlers route only — 1× service per entrypoint | ✅ See entrypoint table below |
| R1: No DB in handlers | ✅ 0 matches |
| R2: No Telegram API in services | ✅ `grant_manual_admin_besitos` delegates credit only |
| R6: Atomic money ops | ✅ Single commit via `credit_besitos` (FOR UPDATE + 1 commit) |
| Funcs ≤50 LOC (Item 36 scope) | ✅ All new/changed funcs ≤44 LOC |
| `is_admin` on admin forward paths | ✅ All entrypoints guarded |
| `get_service` for grant paths | ✅ `confirm_forward_besitos_grant`, `confirm_forward_vip_activation`, `select_forward_action_vip` |
| Logging on critical besito mutation | ✅ Handler + `besito_service \| grant_manual_admin_besitos \| ...` |
| 3 critical systems protected | ✅ Gamif authoritative path; narrative 0; channels-VIP orthogonal |
| Lucien voice | ✅ All `build_forward_*` helpers use `🎩 <b>Lucien:</b>` + italic Diana tone |

**Entrypoint → service map (Item 36 forward flow):**

| Handler | Service calls | Count |
|---------|---------------|-------|
| `process_forwarded_admin_candidate` | 0 | ✅ |
| `select_forward_action_vip` | `get_service(VIPService)` → `get_all_tariffs` | 1 |
| `select_forward_action_besitos` | 0 | ✅ |
| `process_besitos_amount_for_forward` | 0 (pure `parse_positive_besito_amount`) | ✅ |
| `confirm_forward_besitos_grant` | `get_service(BesitoService)` → `grant_manual_admin_besitos` | 1 |
| `confirm_forward_vip_activation` | `get_service(VIPService)` → `grant_vip_from_tariff` | 1 |
| `select_tariff_for_forward_vip` | 0 (`SelectTariffCallback` typed) | ✅ |
| `cancel_forward_action` | 0 | ✅ |

**Layer compliance:** Handlers extract forward candidate (pure), drive FSM, call exactly one service on confirm paths, delegate Telegram notify to thin helpers (`notify_forward_besitos_result` — 0 svc). Service owns besito credit with `TransactionSource.ADMIN`, `reference_id=admin_id`, structured logging, post-commit event via existing `credit_besitos`.

**Service implementation (`grant_manual_admin_besitos`):**

```252:275:services/besito_service.py
    def grant_manual_admin_besitos(
        self, target_user_id: int, amount: int, admin_id: int
    ) -> tuple[bool, int]:
        """Otorga besitos por ajuste manual de Custodio. Returns (success, new_balance)."""
        if amount <= 0 or amount > MAX_ADMIN_BESITO_GRANT:
            logger.warning(
                f"besito_service | grant_manual_admin_besitos | user_id={admin_id} | "
                f"target={target_user_id} | amount={amount} | result=invalid_amount"
            )
            return False, 0
        ...
        ok = self.credit_besitos(
            target_user_id,
            amount,
            TransactionSource.ADMIN,
            description=desc,
            reference_id=admin_id,
        )
```

---

### Alta (Corregir en backlog — **1 finding**)

**ARCHIVO:** `handlers/vip_handlers.py:686-688`, `724-727`, `747`, `825-828` + `keyboards/inline_keyboards.py:347-354`

**REGLA VIOLADA:** R3 — Callbacks sin `CallbackData` (string matching)

**CÓDIGO ACTUAL:**
```python
@router.callback_query(
    AdminForwardStates.selecting_action,
    F.data == "forward_action_besitos",
    lambda cb: is_admin(cb.from_user.id),
)
```

Keyboard:
```python
InlineKeyboardButton(text="💋 Otorgar besitos", callback_data="forward_action_besitos")
```

**IMPACTO:** Medio — no hay parsing de IDs (el caso frágil clásico); FSM state + `is_admin` mitigan. Pero los nuevos botones `forward_action_vip` / `forward_action_besitos` / `cancel_forward_action` / `confirm_forward_besitos_grant` no son type-safe.

**CORRECCIÓN RECOMENDADA:**
```python
# keyboards/callback_data.py
class ForwardActionCallback(CallbackData, prefix="fwd_act"):
    action: str  # "vip" | "besitos" | "cancel"

class ForwardBesitosConfirmCallback(CallbackData, prefix="fwd_bes"):
    action: str  # "confirm" | "cancel"

# handler filter
@router.callback_query(
    AdminForwardStates.selecting_action,
    ForwardActionCallback.filter(F.action == "besitos"),
    lambda cb: is_admin(cb.from_user.id),
)
```

**Nota:** `confirmation_keyboard(confirm_callback: str, ...)` usa strings en todo el proyecto; `confirm_forward_besitos_grant` hereda ese patrón pre-existente. La deuda nueva principal es el menú `forward_action_*`.

---

### Media (Maintenance / Pre-existing — **2 findings**)

1. **Handler importa constante de dominio**  
   - `handlers/vip_handlers.py:30` — `from services.besito_service import MAX_ADMIN_BESITO_GRANT` usado en `parse_positive_besito_amount`.  
   - Aceptable como validación de entrada FSM (defense in depth; servicio re-valida). Acoplamiento menor. Alternativa futura: mover límite a `utils/constants.py` o validar solo en servicio.

2. **Pre-existing `VIPService()` direct en handlers legacy del mismo archivo**  
   - `manage_tariffs`, `generate_token`, etc. usan `VIPService()` + `try/finally close()` en lugar de `get_service`.  
   - **Fuera de scope Item 36.** El flujo forward nuevo sí usa `get_service` correctamente.

---

### Observations (Good adherence)

- **Pure helpers (≤19 LOC each):** `extract_forwarded_candidate`, `build_forward_besitos_*`, `parse_positive_besito_amount` — docstrings "Función pura (sin estado ni side-effects)" + naming verbo+contexto+resultado.
- **Thin notify helpers:** `notify_forward_besitos_result` — Telegram only, 0 svc; grant queda exclusivamente en `confirm_forward_besitos_grant`.
- **FSM:** `AdminForwardStates.besitos_waiting_amount` → `besitos_confirming`; cancel unificado `cancel_forward_action`.
- **Tariff selection:** reutiliza `SelectTariffCallback` (type-safe) en rama VIP.
- **Blocked-user fallback:** `notify_forward_besitos_result` copia patrón VIP (`bot was blocked by the user` + admin fallback).
- **Tests:** `test_confirm_forward_besitos_calls_exactly_1_grant`, `test_grant_manual_admin_besitos_success/respects_max`, pure helper tests — protegen contrato 1-svc + ADMIN source.

---

## Impact on 3 Critical Systems

| System | Impact |
|--------|--------|
| **Gamification (besitos)** | **Protected.** Nuevo método admin usa camino autoritativo `credit_besitos` (FOR UPDATE, 1 commit, `TransactionSource.ADMIN`, logging, post-commit event). No altera debit/reaction/daily/mission paths. |
| **Narrative** | **0 impact.** Sin story nodes, arquetipos ni listeners. |
| **Channels-VIP** | **Protected.** Rama besitos no toca pending/approve/subs. Rama VIP reutiliza `grant_vip_from_tariff` existente sin cambios de contrato. |

---

## Compliance Checklist

| Regla | Violaciones | Estado |
|-------|-------------|--------|
| R1: No lógica/DB en handlers | 0 | ✅ |
| R1: 1 service per entrypoint | 0 | ✅ |
| R2: No Telegram en services | 0 | ✅ |
| R3: CallbackData | 4 strings nuevos en menú forward | ⚠️ ALTA |
| R4: Funciones <50 líneas | 0 en scope | ✅ |
| R5: Logging crítico | 0 | ✅ |
| R6: Transacciones atómicas | 0 | ✅ |
| R7: No strings mágicos enum | 0 (usa `TransactionSource.ADMIN`) | ✅ |
| `is_admin` | 0 gaps en forward flow | ✅ |
| `get_service` | 0 gaps en grant entrypoints | ✅ |
| Lucien voice | 0 hardcoded admin strings fuera de builders | ✅ |
| 3 crit protected | 0 attributable impact | ✅ |

---

## Verdict

**PASS WITH NOTES (0 critical violations)**

**Reasons:**
- Arquitectura de capas correcta: handlers enrutan FSM → 1× `BesitoService`/`VIPService` en confirms → servicio acredita con atomicidad y logging.
- Besitos branch sigue patrón gold del forward VIP (pure builders, thin notify, `get_service`, `is_admin`, state clear).
- Tests verdes (14) cubren 1-svc grant, pure helpers, invalid amount, cancel.

**Notes (non-blocking):**
1. **ALTA:** Introducir `ForwardActionCallback` (y opcionalmente confirm CallbackData) para eliminar strings `forward_action_*`.
2. **MEDIA:** Import de `MAX_ADMIN_BESITO_GRANT` en handler — aceptable; considerar constante compartida si crece.
3. **MEDIA:** Deuda pre-existente `VIPService()` direct en handlers legacy del mismo archivo — no atribuible a Item 36.

**Handoff:** Ready for test-guardian (opcional: test blocked-notify besitos path) + documentador.