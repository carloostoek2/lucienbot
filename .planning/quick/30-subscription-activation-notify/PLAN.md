# PLAN — 30-subscription-activation-notify

Notificación por DM a Custodios del estado de activación VIP (éxito + fallo).
Pool de 2 ítems acoplados. 0 comportamiento / 0 atomicidad en `redeem_token`.

---

## 1. QUÉ

### Outcome
Cuando un token VIP se activa o falla, cada Custodio recibe un DM de Telegram con
identificación del visitante (id + @username + nombre), y en éxito la tarifa + duración,
en fallo la razón detallada. Best-effort: nunca muta estado VIP ni rompe el redeem.

### Scope

**Item 1 — Success notification (listener nuevo, evento existente).**
Reusar `EVENT_VIP_ACTIVATED` (sin evento nuevo). Nuevo listener
`on_vip_activated_admin_notify` → DM a admins con `user_id + @username + first_name +
Tariff.name + Tariff.duration_days`. Cubre las 5 sites de emisión existentes
(`vip_service.py:294-299`, `:341-345`, `:653-657`, `:701-705`, `:751-756`; incluye
grants internos — aceptado/intencional).

**Item 2 — Failure notification (evento nuevo + emits).**
Nuevo constante `EVENT_VIP_ACTIVATION_FAILED`; emitir en cada `return None` de fallo de
`redeem_token`; listener `on_vip_activation_failed_admin_notify` → DM con razón.

### Contracts

- **Success payload (existente, inmutable):** `{"user_id": int, "subscription_id": int}`.
- **Failure payload (nuevo):** `{"user_id": int, "token_code": str, "reason": str}`.
  `reason ∈ {not_found, used, expired, tariff_not_found, no_vip_channel}`.
- **Listener MUST-NOT-mutate** (EventBus observational contract, estilo "MUST NOT credit/debit"):
  solo lee (Subscription→Tariff, User) y envía DM. Nunca re-entra a `redeem_token`.
  Errores capturados por listener (`try/except` + log `result=swallowed_best_effort`).
- **Emits de fallo:** `schedule_emit(get_event_bus().emit(...))` colocado DESPUÉS del
  `rollback()`/`commit()` y ANTES del `return None`. Path de éxito intacto.

### DoD

**Item 1:**
- [ ] `on_vip_activated_admin_notify` registrado en `bot.py` y enriquece tarifa+usuario.
- [ ] DM enviado a cada `ADMIN_IDS` con nombre, duración y datos del visitante.
- [ ] Tolerancia a datos faltantes (N/A), sin mutación, sin excepción propagada.
- [ ] Tests: `test_on_vip_activated_admin_notify_enriches_tariff_and_user`,
  `test_notify_skips_when_no_admin_ids`.

**Item 2:**
- [ ] `EVENT_VIP_ACTIVATION_FAILED` definido + re-exportado.
- [ ] 6 puntos de fallo en `redeem_token` emiten con `reason` correcta.
- [ ] `on_vip_activation_failed_admin_notify` envía DM con razón.
- [ ] Tests de 5 razones + DM a admins + patch `schedule_emit` en tests legacy.

---

## 2. CÓMO

### Arquitectura

Nuevo módulo `services/vip_notifier.py` (NO NotificationService nuevo, NO en nurture_service).
Sigue los precedentes probados:
- Listener observational → patrón `nurture_service.on_vip_activated` (lazy `get_service`,
  try/except, log handled/swallowed).
- DM loop a admins → patrón `store_service._notify_admins_of_purchase` (`:1411`, loop
  `ADMIN_IDS` + `try/except` + `parse_mode="HTML"` + log sent/error).
- Bot lazy self-contained → patrón `link_notifier._get_bot` (`bot_config.TOKEN`).

### Archivos y orden

1. `services/event_bus.py` — agregar constante.
2. `services/__init__.py` — re-export constante.
3. `services/vip_notifier.py` — NUEVO (listeners + helper + puros).
4. `services/vip_service.py` — emits de fallo en `redeem_token`.
5. `bot.py` — registrar ambos listeners en `on_startup`.
6. Tests — `tests/unit/test_vip_notifier.py` (nuevo) + patch en `tests/unit/test_vip_service.py`.

### Patrón a copiar por archivo

- **`event_bus.py`**: copiar línea de `EVENT_VIP_KICKED` (`:29`) →
  `EVENT_VIP_ACTIVATION_FAILED: str = "vip_activation_failed"`.
- **`services/__init__.py`**: copiar import de `EVENT_VIP_KICKED` (`:14`) y entrada en `__all__`
  (`:88`).
- **`vip_notifier.py`**: listener → `nurture_service.on_vip_activated` (`:414`);
  `_notify_admins` → `store_service._notify_admins_of_purchase` (`:1480-1494`);
  `_get_bot` → `link_notifier._get_bot` (`:140`).
- **`vip_service.py`**: emits → patrón `schedule_emit(get_event_bus().emit(...))` ya existente
  (`:294-299`, `:341-345`); reutilizar imports de `event_bus` (`:17-22`).
- **`bot.py`**: copiar `get_event_bus().register(EVENT_VIP_ACTIVATED, on_vip_activated)` (`:252`)
  para ambos nuevos listeners.

---

## 3. Tasks

### Task 1 — Constante de evento + re-export

**Files:** `services/event_bus.py`, `services/__init__.py`
**New code:** ~2 LOC.

- `event_bus.py`: agregar `EVENT_VIP_ACTIVATION_FAILED: str = "vip_activation_failed"` tras
  `EVENT_VIP_KICKED`.
- `services/__init__.py`: agregar a import de `event_bus` (`:11-17`) y a `__all__` (`:86-90`).

**Verification:** `python -c "from services import EVENT_VIP_ACTIVATION_FAILED"` OK.

### Task 2 — Módulo `services/vip_notifier.py` (NUEVO)

**Files:** `services/vip_notifier.py`
**New code:** ~70 LOC repartidos (cada función ≤50 LOC).

Funciones (naming verbo+contexto+resultado):
- `_get_bot() -> Bot` — lazy singleton desde `bot_config.TOKEN`.
- `async _notify_admins(bot: Bot, text: str) -> None` — guard `if not bot_config.ADMIN_IDS` →
  `debug`; loop `send_message(chat_id, text, parse_mode="HTML")` + `try/except` + log
  `vip_notifier | notify_sent | admin_id=...` / `notify_error`.
- `build_activation_success_text(user_id, username, first_name, tariff_name, duration_days) -> str`
  — puro, stateless; valores `None` → "N/A".
- `build_activation_failure_text(user_id, username, first_name, reason, token_code=None) -> str`
  — puro; mapeo de `reason` a texto legible en voz de Lucien (directo/claro, sin vulgaridad).
- `async on_vip_activated_admin_notify(payload: dict) -> None` — extrae `user_id`+`subscription_id`;
  guard `missing_ids`; dentro de `try`: `from services import get_service, VIPService` (lazy,
  anti-circular), `with get_service(VIPService) as svc:` → `db = svc._get_db()`, query
  `Subscription` por id, `User` por `telegram_id`, tariff via `subscription.tariff` con fallback
  `subscription.token.tariff`; construye texto; `await _notify_admins(_get_bot(), text)`;
  log `result=handled`. `except` → log `result=swallowed_best_effort`.
- `async on_vip_activation_failed_admin_notify(payload: dict) -> None` — extrae `user_id`+`reason`
  (+`token_code`); query `User` por `telegram_id` (username/first_name, N/A si falta); construye
  texto; `await _notify_admins(...)`; mismo `try/except`.

**Verification:** import limpio (`python -c "from services.vip_notifier import ..."`); funciones
`inspect.getsource` ≤50 LOC.

### Task 3 — Emits de fallo en `redeem_token`

**Files:** `services/vip_service.py`
**New code:** ~6 × 4 LOC = ~24 LOC (sin cambio de lógica).

Agregar `schedule_emit(get_event_bus().emit(EVENT_VIP_ACTIVATION_FAILED, {...}))` en los 6
puntos, DESPUÉS del rollback/commit y ANTES del `return None`:
- `:223` `if not token` → `reason="not_found"` (sin rollback previo).
- `:227-229` USED → `reason="used"` (tras `rollback`).
- `:231-233` EXPIRED (status) → `reason="expired"` (tras `rollback`).
- `:235-238` EXPIRED (expires_at) → `reason="expired"` (tras `commit`).
- `:246-249` tariff faltante → `reason="tariff_not_found"` (tras `rollback`).
- `:317-319` canal VIP faltante → `reason="no_vip_channel"` (tras `rollback`).

Payload: `{"user_id": user_id, "token_code": token_code, "reason": "<reason>"}`.
Importar `EVENT_VIP_ACTIVATION_FAILED` del `event_bus` (`:17-22`).

**Verification:** revisar que no cambia flujo de retorno/rollback/commit; success path intacto.

### Task 4 — Registro en `bot.py` + tests

**Files:** `bot.py`, `tests/unit/test_vip_notifier.py` (nuevo), `tests/unit/test_vip_service.py`
**New code:** ~4 LOC bot.py + tests.

- `bot.py`: tras `:252`, agregar:
  `get_event_bus().register(EVENT_VIP_ACTIVATED, on_vip_activated_admin_notify)` y
  `get_event_bus().register(EVENT_VIP_ACTIVATION_FAILED, on_vip_activation_failed_admin_notify)`.
  Importar listeners + constante.
- Tests nuevos (ver §4) + patch `schedule_emit` en tests legacy.

**Verification:** suite verde (flags §4).

---

## 4. Tests

### Comando base

```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "vip or event_bus or nurture or notify" \
  tests/unit/test_vip_service.py tests/unit/test_event_bus.py tests/unit/test_store_service.py \
  tests/unit/test_vip_notifier.py \
  tests/integration/test_nurture_lifecycle_e2e.py tests/integration/test_vip_flow.py \
  tests/integration/test_vip_subscription_lifecycle.py tests/integration/test_vip_complete_cycle.py \
  tests/integration/test_vip_flows.py tests/integration/test_vip_ritual_flow.py \
  tests/integration/test_invariants.py
```

### Golds re-runs (obligatorio)

```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "cross_service_atomicity or reaction_ or daily or invariant" \
  tests/integration/test_invariants.py tests/integration/
```

### Tests a AÑADIR (`tests/unit/test_vip_notifier.py`, NUEVO)

Item 2 (emit + listener):
- `test_redeem_not_found_emits_failure` — patch `services.vip_service.get_event_bus` (mock bus) +
  `services.vip_service.schedule_emit` (no-op); assert `emit` con `EVENT_VIP_ACTIVATION_FAILED`
  y `reason=="not_found"`.
- `test_redeem_used_emits_failure` — `reason=="used"`.
- `test_redeem_expired_emits_failure` — `reason=="expired"` (ambos paths status + expires_at).
- `test_redeem_missing_tariff_emits_failure` — `reason=="tariff_not_found"`.
- `test_redeem_no_vip_channel_emits_failure` — `reason=="no_vip_channel"`.
- `test_on_vip_activation_failed_sends_dm_to_admins` — patch
  `services.vip_notifier._get_bot` (mock bot) + `services.vip_notifier.bot_config.ADMIN_IDS`;
  assert 1 `send_message` por admin, texto contiene razón.

Item 1:
- `test_on_vip_activated_admin_notify_enriches_tariff_and_user` — patch `_get_bot` + `ADMIN_IDS`;
  con `Subscription`+`Tariff`+`User` sembrados, assert DM texto contiene `Tariff.name` +
  `duration_days` + username/first_name.
- `test_notify_skips_when_no_admin_ids` — `ADMIN_IDS=[]` → sin `send_message`, log skip.

### Patrones a copiar

- Mock bot + assert `send_message`: `tests/unit/test_store_service.py:615-650`
  (`test_notify_admins_of_purchase_enriched_with_charged_amount`).
- Listener fresh bus + caplog: `tests/unit/test_event_bus.py:222-242`
  (`test_vip_activated_listener_is_invoked_and_logs`).
- Fixtures `db_session`, `sample_token`, `sample_user`, `sample_vip_channel`, `sample_used_token`,
  `sample_expired_token`: `tests/unit/test_vip_service.py`.

### Patch en tests legacy (riesgo conocido)

`tests/unit/test_vip_service.py` — `test_redeem_token_already_used` (`:206`) y
`test_redeem_token_expired` (`:214`) ahora ejecutan `schedule_emit` en path de fallo. Añadir
`with patch("services.vip_service.schedule_emit")` (o patch `get_event_bus`) para aislamiento
determinista. (En tests sync sin loop `schedule_emit` ya no-op, pero el patch elimina el riesgo
de side-effect si un fixture registra listeners en el singleton.)

---

## 5. Riesgos + mitigación

1. **Cross-test side-effect de `schedule_emit`** en tests de fallo legacy.
   → Mitigación: patch `get_event_bus`/`schedule_emit` en tests nuevos y legacy (§4). Emits
   reales usan bus singleton sin listeners registrados fuera de `on_startup` (noop en tests).
2. **5 sites de éxito / grants internos** generan ruido de notificación.
   → Aceptado por scope (decisión bloqueada #4). Listener puramente observational; no filtra.
3. **Circular import** (`services/__init__.py` ↔ `vip_notifier`).
   → Mitigación: import lazy de `get_service`/`VIPService` DENTRO del listener (patrón
   `nurture_service`); `vip_notifier` NO se importa desde `services/__init__.py`.
4. **Regresión de atomicidad en `redeem_token`**.
   → Mitigación: emits colocados tras rollback/commit, antes de `return`; ningún cambio a
   commits/rollbacks/returns. Verificado por golds de atomicidad + `test_redeem_token_success`.
5. **Tarifa nula (legacy `tariff_id=None`)**.
   → Mitigación: fallback `subscription.token.tariff`, y `None` → "N/A" en texto.

---

## 6. Instrucciones para gsd-executor

- GSD pre-log ANTES de cada edit/gate (`gsd pre` en `.planning/quick/gsd-30-*.log`); `wc -l` al
  final de cada tarea.
- Self-check PASSED al cierre de cada tarea: funciones ≤50 LOC, naming verbo+contexto+resultado,
  logging `vip_notifier | <acción> | user_id=<...> | resultado`, handlers intactos, 0 mutación en
  `redeem_token` (diffs de rollback/commit/return idénticos salvo los `schedule_emit` insertados).
- Commits atómicos por work unit (Task 1, Task 2, Task 3, Task 4) — mensajes conventional commits,
  sin "Co-Authored-By".
- Proteger 3 sistemas críticos (gamificación / narrativa / channels-VIP + VIP grant/revoke): este
  cambio solo OBSERVA y notifica; no toca créditos, progreso narrativo, ni pending/approve/expire.
- Al final: correr flags de §4 + golds re-runs; 0 regresiones atribuibles.
