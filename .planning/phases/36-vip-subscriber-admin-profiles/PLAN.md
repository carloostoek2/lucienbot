# PLAN: VIP Subscriber Admin Profiles (Etapa 1)

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-07-02  
**Phase:** `36-vip-subscriber-admin-profiles`  
**Source:** `.grok/agent-memory/impact-analyzer/vip-subscriber-admin-profiles.md` + user scope Etapa 1

**GSD log dedicado:** `.planning/quick/gsd-planner-vip-subscriber-admin-profiles.log` (planner) + `.planning/quick/gsd-vip-subscriber-admin-profiles.log` (executor pre cada edit)

---

## SCOPE INTAKE

```
SCOPE INTAKE
- Objetivo: Reemplazar list_subscribers plano (10 max, sin paginación, sin acciones, sin is_admin)
  por router admin dedicado con lista paginada (8/página), perfiles clicables y acciones:
  extender VIP, otorgar besitos, debitar besitos, expulsar (kick).
- Fuente: impact report vip-subscriber-admin-profiles.md + patrones channel_handlers pagination
  + vip_handlers forward besitos FSM + scheduler kick contract.
- Ítems del pool (≤4): [Item 36 — vip-subscriber-admin-profiles Etapa 1]
- Restricciones: handlers 1 svc/entrypoint; funcs ≤50 LOC; is_admin en todo entrypoint admin;
  Lucien voice; 0 regresión forward-admin VIP|besitos; proteger 3 crit + golds.
- Sistemas sensibles: canales-VIP (kick ban/unban + has_other_active), gamificación
  (grant/debit besitos ADMIN), VIP grant (grant_internal_vip_access único path extend).
- Artefactos: este PLAN + SUMMARY post-exec + tests + decisions append.
```

---

## 1. Resumen ejecutivo

| Problema actual | Solución Etapa 1 |
|-----------------|------------------|
| `list_subscribers` en `vip_handlers.py` — flat, cap 10, sin `is_admin`, sin perfil | Nuevo `handlers/vip_subscriber_admin_handlers.py` |
| `list_subscribers_{channel_id}` en `inline_keyboards.py:229` — **callback muerto** | Mismo router con `SubscriberListCallback(channel_id=...)` |
| Sin acciones admin por suscriptor | Perfil + FSM: extend / grant / debit / kick |
| Kick manual inexistente | `VIPService.admin_revoke_subscription(bot)` con contrato `has_other_active` |
| Débito admin besitos inexistente | `BesitoService.debit_manual_admin_besitos` (espejo de grant) |

**Riesgo global:** Medium-High (channels-VIP kick + besitos debit + 1-service/async bot).

**Preservar intacto:** `handlers/vip_handlers.py` L752–971 (forward admin VIP | besitos).

---

## 2. Alcance (In / Out)

### En alcance

| Área | Cambio |
|------|--------|
| **Lista paginada** | 8 suscriptores/página, filas clicables → perfil |
| **Perfil** | ID, display name, besitos, tarifa, vencimiento, días restantes |
| **Extender** | Selección tarifa → confirmar → `grant_internal_vip_access` |
| **Otorgar besitos** | FSM cantidad → confirmar → `grant_manual_admin_besitos` |
| **Debitar besitos** | FSM cantidad → confirmar → `debit_manual_admin_besitos` (nuevo) |
| **Kick** | Confirmar → `admin_revoke_subscription(bot)` |
| **Dead callback** | `list_subscribers_{channel_id}` cableado |
| **Deprecar** | Eliminar handler `list_subscribers` de `vip_handlers.py` (mantener forward) |
| **Copy** | `LucienVoice` métodos admin suscriptores |
| **Tests** | handlers + unit VIP/Besito + callback_data + regression forward |

### Fuera de alcance (Etapa 1)

- Búsqueda/filtro por username o ID
- Historial de transacciones en perfil
- Export CSV de suscriptores
- Edición manual de `end_date` sin tarifa
- Notificación visitante en extend/kick (best-effort opcional Etapa 2)
- Refactor masivo de `vip_handlers.py` (solo quitar `list_subscribers`)
- Migraciones Alembic

---

## 3. Principios no negociables

1. **Handlers → 1 service** por entrypoint: `with get_service(X) as svc:` + exactamente 1 llamada de negocio.
2. **Funciones ≤ 50 LOC** — puros `build_*`, `format_*`, `parse_*`, `clamp_*`.
3. **`is_admin()`** en **cada** `@router.callback_query` y `@router.message` FSM del módulo nuevo.
4. **Logging:** `vip_subscriber_admin_handlers | <acción> | user_id=<admin_id> | resultado=...`
5. **Voz Lucien:** textos en `LucienVoice`; "Visitantes" / "Custodios".
6. **ID duality documentada:**
   - `SubscriberListCallback.channel_id` → **DB PK** (`Channel.id`) cuando viene del detalle de canal; `None` desde menú VIP global.
   - `admin_revoke_subscription` → `ban_chat_member`/`unban_chat_member` usa **Telegram chat ID** (`Channel.channel_id`).
7. **GSD pre-log** antes de cada edit en `.planning/quick/gsd-vip-subscriber-admin-profiles.log`.

---

## 4. Diseño técnico

### 4.1 Constantes y paginación

```python
SUBSCRIBER_PAGE_SIZE = 8  # alinear con PENDING_PAGE_SIZE en channel_handlers
```

Patrón gold: `handlers/channel_handlers.py` — `_clamp_page`, `build_*_nav_row`, `build_*_keyboard`, `build_*_list_text`.

### 4.2 CallbackData nuevos (`keyboards/callback_data.py`)

```python
class SubscriberListCallback(CallbackData, prefix="sub_list"):
    """Lista paginada de suscriptores activos."""
    channel_id: int = 0   # 0 = menú VIP global (sin filtro canal)
    page: int = 0

class SubscriberProfileCallback(CallbackData, prefix="sub_prof"):
    """Perfil admin de un suscriptor."""
    subscription_id: int
    channel_id: int = 0
    page: int = 0

class SubscriberActionCallback(CallbackData, prefix="sub_act"):
    """Iniciar acción admin sobre suscriptor."""
    action: str  # "extend" | "grant_besitos" | "debit_besitos" | "kick"
    subscription_id: int
    channel_id: int = 0
    page: int = 0

class SubscriberExtendTariffCallback(CallbackData, prefix="sub_ext_tar"):
    """Seleccionar tarifa para extender VIP."""
    subscription_id: int
    tariff_id: int
    channel_id: int = 0
    page: int = 0

class SubscriberConfirmCallback(CallbackData, prefix="sub_confirm"):
    """Confirmar acción (extend | grant_besitos | debit_besitos | kick)."""
    action: str
    subscription_id: int
    channel_id: int = 0
    page: int = 0
```

### 4.3 Teclados (`keyboards/inline_keyboards.py`)

| Función | Responsabilidad |
|---------|-----------------|
| `subscriber_list_keyboard(subs, channel_id, page, total_count)` | Fila por suscriptor → `SubscriberProfileCallback`; nav ◀️/▶️; volver |
| `subscriber_profile_keyboard(subscription_id, channel_id, page)` | Acciones: Extender / Otorgar / Debitar / Expulsar + Volver a lista |
| `subscriber_extend_tariffs_keyboard(tariffs, subscription_id, channel_id, page)` | Tarifas activas → `SubscriberExtendTariffCallback` |
| `subscriber_confirm_keyboard(action, subscription_id, channel_id, page)` | ✅ Confirmar / ❌ Cancelar |

**Wire keyboards existentes:**

```python
# vip_management_keyboard() L411 — reemplazar string muerto:
callback_data=SubscriberListCallback(channel_id=0, page=0).pack()

# channel detail VIP L229 — reemplazar f"list_subscribers_{channel_id}":
callback_data=SubscriberListCallback(channel_id=channel_id, page=0).pack()
```

### 4.4 FSM (`handlers/vip_subscriber_admin_handlers.py`)

```python
class SubscriberAdminStates(StatesGroup):
    extend_confirming = State()
    besitos_grant_waiting_amount = State()
    besitos_grant_confirming = State()
    besitos_debit_waiting_amount = State()
    besitos_debit_confirming = State()
    kick_confirming = State()
```

**State data keys:**
- `target_subscription_id: int`
- `target_user_id: int`
- `target_display: str`
- `list_channel_id: int` (0 = global)
- `list_page: int`
- `selected_tariff_id: int` (extend)
- `besito_amount: int` (grant/debit)

### 4.5 VIPService — métodos nuevos (`services/vip_service.py`)

```python
def count_active_subscriptions(self, channel_id: int | None = None) -> int:
    """Cuenta suscripciones activas (opcional filtro por channel DB PK)."""

def get_active_subscriptions_page(
    self, *, channel_id: int | None = None, page: int = 0, page_size: int = 8
) -> list[Subscription]:
    """Página de suscripciones activas ordenadas por end_date ASC."""

def get_subscriber_admin_snapshot(self, subscription_id: int) -> dict | None:
    """
    Snapshot read-only para perfil admin.
    Composición besitos SOLO aquí (local BesitoService(db=...) — NO desde handler).
    Returns dict: subscription_id, user_id, display_name, besitos_balance,
    tariff_name, expiry_iso, days_remaining, channel_db_id.
    """

async def admin_revoke_subscription(
    self, bot, subscription_id: int, admin_id: int
) -> tuple[bool, str, dict]:
    """
    Revoca suscripción admin (kick).
    CONTRATO IDÉNTICO a scheduler _process_expired_subscriptions:
      - has_other_active → solo desactivar (expire), SIN ban/unban
      - única activa → ban + unban + desactivar + clear vip_entry_state + notify user
    Returns: (ok, result_code, metadata)
    result_code: deactivated_only | kicked | not_found | channel_inactive | error
    """
```

**Extend:** handler llama **solo** `grant_internal_vip_access(user_id, tariff_id)` — prohibido duplicar lógica de extensión en handler.

### 4.6 BesitoService — método nuevo (`services/besito_service.py`)

```python
def debit_manual_admin_besitos(
    self, target_user_id: int, amount: int, admin_id: int
) -> tuple[bool, int]:
    """
    Debita besitos por ajuste manual de Custodio (espejo grant_manual_admin_besitos).
    - Valida 0 < amount <= MAX_ADMIN_BESITO_GRANT
    - has_sufficient_balance ANTES de debit
    - debit_besitos(..., TransactionSource.ADMIN, reference_id=None)
    - NO emite EventBus (débito admin no es award)
    Returns: (success, new_balance or 0 on fail)
    """
```

### 4.7 Puros handler (`handlers/vip_subscriber_admin_handlers.py`)

| Función | Propósito |
|---------|-----------|
| `clamp_subscriber_page(page, total_count) -> int` | Clamp 0..total_pages-1 |
| `format_subscriber_display_name(sub) -> str` | @user o ID (HTML-safe) |
| `compute_days_remaining(end_date) -> int` | Días hasta vencimiento (≥0) |
| `build_subscriber_list_text(subs, page, total_count)` | Header + líneas numeradas |
| `build_subscriber_profile_text(snapshot) -> str` | Perfil completo |
| `build_subscriber_nav_row(channel_id, page, total_count)` | ◀️ Anterior / Siguiente ▶️ |
| `resolve_list_back_callback(channel_id) -> str` | Volver a canal o menú VIP |

**Reutilizar (import, no duplicar):**
- `parse_positive_besito_amount` desde `handlers/vip_handlers.py`
- `notify_forward_besitos_result` o thin wrapper `notify_subscriber_besitos_result` (0 svc, best-effort DM)

### 4.8 Mapa handlers → 1 service

| Handler | Service call |
|---------|--------------|
| `open_subscriber_list` | `get_active_subscriptions_page` + `count_active_subscriptions` → **1 svc** vía método compuesto `list_active_subscribers_admin(channel_id, page)` si hace falta unificar (preferible 1 call: añadir método `get_subscriber_list_view` que retorna `(subs, total)`) |
| `subscriber_list_page_nav` | mismo que lista |
| `open_subscriber_profile` | `get_subscriber_admin_snapshot` |
| `start_subscriber_extend` | `get_all_tariffs(active_only=True)` |
| `select_extend_tariff` | 0 svc (guarda tariff_id en FSM) |
| `confirm_subscriber_extend` | `grant_internal_vip_access` |
| `start_subscriber_grant_besitos` | 0 svc |
| `process_grant_besitos_amount` | 0 svc (parse) |
| `confirm_subscriber_grant_besitos` | `grant_manual_admin_besitos` |
| `start_subscriber_debit_besitos` | 0 svc |
| `process_debit_besitos_amount` | 0 svc (parse) |
| `confirm_subscriber_debit_besitos` | `debit_manual_admin_besitos` |
| `start_subscriber_kick` | 0 svc |
| `confirm_subscriber_kick` | `admin_revoke_subscription(bot)` |

**Nota lista:** Si count+page requieren 2 queries, encapsular en **un solo método** `VIPService.get_subscriber_list_page(channel_id, page, page_size) -> tuple[list, int]` para cumplir 1-svc.

### 4.9 LucienVoice (`utils/lucien_voice.py`)

Añadir métodos (borrador):

| Método | Uso |
|--------|-----|
| `admin_subscriber_list_empty()` | Sin suscriptores |
| `admin_subscriber_list_header(total, page, total_pages)` | Encabezado lista |
| `admin_subscriber_list_line(index, display, expiry)` | Línea lista |
| `admin_subscriber_profile(snapshot)` | Perfil detallado |
| `admin_subscriber_extend_tariff_prompt(display, user_id)` | Elegir tarifa |
| `admin_subscriber_extend_confirm(display, tariff_name, days)` | Confirmar extend |
| `admin_subscriber_besitos_amount_prompt(display, action)` | Pedir cantidad grant/debit |
| `admin_subscriber_besitos_confirm(display, amount, action)` | Confirmación |
| `admin_subscriber_kick_confirm(display, user_id)` | Confirmar expulsión |
| `admin_subscriber_kick_deactivated_only(display)` | has_other_active — solo BD |
| `admin_subscriber_kick_success(display)` | Expulsión completa |
| `admin_subscriber_action_failed(reason)` | Error genérico |

### 4.10 Wire bot (`bot.py`, `handlers/__init__.py`)

```python
# handlers/__init__.py
from .vip_subscriber_admin_handlers import router as vip_subscriber_admin_router

# bot.py — después de vip_router
dp.include_router(vip_subscriber_admin_router)
```

### 4.11 Deprecar `list_subscribers` en `vip_handlers.py`

- **Eliminar** handler `@router.callback_query(F.data == "list_subscribers")` (L708–749).
- **No tocar** sección forward L752+.
- Añadir comentario: `# list_subscribers → vip_subscriber_admin_handlers (phase 36)`.

---

## 5. Fases de ejecución (F1–F6)

### F1 — CallbackData + teclados + LucienVoice (fundación UI)

**Objetivo:** Tipar callbacks, cablear keyboards, copy admin. Sin handlers nuevos aún.

**Archivos:**
- `keyboards/callback_data.py` — 5 clases Subscriber*
- `keyboards/inline_keyboards.py` — 4 keyboards + wire `vip_management_keyboard` + channel VIP button
- `utils/lucien_voice.py` — métodos admin suscriptores

**Tareas:**
1. Añadir CallbackData con prefix cortos (≤64 bytes TG limit).
2. Reemplazar `callback_data="list_subscribers"` y `f"list_subscribers_{channel_id}"`.
3. Implementar keyboards paginados (estructura vacía OK con `subs=[]` en tests).
4. LucienVoice: todos los métodos §4.9.

**DoD F1:**
- [ ] Grep: 0 ocurrencias de `callback_data="list_subscribers"` o `list_subscribers_{` sin `SubscriberListCallback`
- [ ] Import-inside test: pack/unpack Subscriber* callbacks
- [ ] ruff clean en archivos tocados

**Tests F1:**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "SubscriberList or callback_data" tests/
```

---

### F2 — Capa servicio (VIP list/snapshot/revoke + Besito debit)

**Objetivo:** Lógica de negocio centralizada antes de handlers.

**Archivos:**
- `services/vip_service.py`
- `services/besito_service.py`

**Tareas:**
1. `get_subscriber_list_page(channel_id, page, page_size=8) -> tuple[list[Subscription], int]`
2. `get_subscriber_admin_snapshot(subscription_id)` — local `BesitoService(db=db)` para balance
3. `admin_revoke_subscription(bot, subscription_id, admin_id)` — copiar semántica scheduler L206–242
4. `debit_manual_admin_besitos` — espejo grant + `has_sufficient_balance`
5. Logging estándar en cada método

**DoD F2:**
- [ ] `admin_revoke` con `has_other_active=True` → NO llama `ban_chat_member`
- [ ] `admin_revoke` sin otra activa → ban+unban+notify (mock bot en test)
- [ ] `debit_manual_admin_besitos` rechaza saldo insuficiente y amount inválido
- [ ] Snapshot retorna `None` si subscription inexistente/inactiva
- [ ] 0 BesitoService instanciado desde handler para snapshot (solo VIPService)

**Tests F2:**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "debit_manual_admin or admin_revoke_subscription or subscriber_admin_snapshot or get_subscriber_list" tests/unit/
```

---

### F3 — Router scaffold + deprecar list_subscribers + wire bot

**Objetivo:** Módulo handler existe, registrado, callback muerto resuelto.

**Archivos:**
- `handlers/vip_subscriber_admin_handlers.py` — **CREATE** (router, FSM, puros, stubs lista/perfil)
- `handlers/vip_handlers.py` — eliminar `list_subscribers` handler
- `handlers/__init__.py`, `bot.py` — registrar router

**Tareas:**
1. Crear router con `SUBSCRIBER_PAGE_SIZE = 8`, puros §4.7, FSM §4.4.
2. `open_subscriber_list` / `subscriber_list_page_nav` — `SubscriberListCallback`, `is_admin`, 1 svc.
3. `open_subscriber_profile` — `SubscriberProfileCallback`, 1 svc snapshot.
4. Eliminar handler viejo en `vip_handlers.py`.
5. Registrar router en bot.

**DoD F3:**
- [ ] Click «Ver suscriptores activos» (menú VIP y detalle canal) abre lista paginada
- [ ] Grep `vip_handlers.py`: 0 handler `list_subscribers`; forward L752+ intacto
- [ ] Todos los callbacks del módulo nuevo tienen `lambda cb: is_admin(cb.from_user.id)`

**Tests F3:**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "subscriber_admin and (list or profile or pagination)" tests/handlers/
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/handlers/test_vip_handlers.py
```

---

### F4 — Perfil clicables + navegación lista↔perfil

**Objetivo:** UX completa lista → perfil → volver, sin acciones FSM aún (botones pueden mostrar "próximamente" o wire a F5).

**Archivos:**
- `handlers/vip_subscriber_admin_handlers.py`
- `keyboards/inline_keyboards.py` (si falta wiring filas clicables)

**Tareas:**
1. Lista: cada fila botón con display + vencimiento → `SubscriberProfileCallback`.
2. Perfil: mostrar ID, display, besitos, tarifa, expiry, días restantes.
3. Volver: `SubscriberListCallback(channel_id, page)` preserva contexto.
4. Empty state + página única sin nav.

**DoD F4:**
- [ ] 9+ suscriptores → 2 páginas, nav funciona
- [ ] Perfil muestra snapshot completo
- [ ] Handlers lista/perfil ≤50 LOC (puros extraídos)

**Tests F4:**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "subscriber_admin and (SubscriberList or profile or pagination or build_subscriber)" tests/
```

---

### F5 — FSM acciones: extend / grant / debit / kick

**Objetivo:** Las 4 acciones admin operativas con confirmación.

**Archivos:**
- `handlers/vip_subscriber_admin_handlers.py` (principal)
- Reuso: `parse_positive_besito_amount`, patrón notify besitos

**Tareas por acción:**

| Acción | Flujo | 1 svc en confirm |
|--------|-------|------------------|
| **Extend** | Perfil → tarifas activas → confirm → extend | `grant_internal_vip_access` |
| **Grant besitos** | Perfil → cantidad → confirm | `grant_manual_admin_besitos` + notify best-effort |
| **Debit besitos** | Perfil → cantidad → confirm | `debit_manual_admin_besitos` |
| **Kick** | Perfil → confirm | `admin_revoke_subscription(bot)` |

**Reglas críticas F5:**
- Extend: **nunca** mutar `end_date` en handler; solo `grant_internal_vip_access`.
- Kick: **siempre** `has_other_active_subscription` antes de ban (dentro del service).
- Debit: **siempre** `has_sufficient_balance` en service; handler muestra error Lucien si fail.
- Cada confirm callback: `SubscriberConfirmCallback` + IdempotencyMiddleware existente.

**DoD F5:**
- [ ] 4 acciones completas con confirmación y cancelación (vuelve a perfil o lista)
- [ ] grep handlers confirm: exactamente 1 `get_service` por handler confirm
- [ ] LOC ≤50 en cada handler (inspect o wc)
- [ ] `state.clear()` en cancel/éxito/error

**Tests F5 (smoke handler mocks):**
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "subscriber_admin and (extend or grant or debit or kick or confirm)" tests/handlers/
```

---

### F6 — Tests completos + gates + self-check

**Objetivo:** Suite protege contratos; 0 regresión 3 crit; handoff arch-enforcer → test-guardian.

**Archivos tests:**

| Archivo | Acción |
|---------|--------|
| `tests/handlers/test_vip_subscriber_admin_handlers.py` | **CREATE** — puros, pagination, is_admin, 1-svc confirms, kick/extend/debit/grant |
| `tests/unit/test_vip_service.py` | **EDIT** — `admin_revoke_subscription`, `get_subscriber_list_page`, snapshot |
| `tests/unit/test_besito_service.py` | **EDIT** — `debit_manual_admin_besitos` (success, insufficient, max) |
| `tests/unit/test_callback_data.py` o existente | **EDIT** — Subscriber* pack/unpack |
| `tests/handlers/test_vip_handlers.py` | **EDIT** — 0 `list_subscribers`; forward regression intacta |

**Tabla tests mínimos:**

| Test | Tipo |
|------|------|
| `test_subscriber_list_callback_pack_unpack` | callback_data |
| `test_clamp_subscriber_page_*` | Puro |
| `test_build_subscriber_list_text_*` | Puro |
| `test_get_subscriber_list_page_pagination` | Unit VIP |
| `test_get_subscriber_admin_snapshot_includes_besitos` | Unit VIP |
| `test_admin_revoke_deactivated_only_when_other_active` | Unit VIP (mock bot) |
| `test_admin_revoke_ban_unban_when_only_subscription` | Unit VIP (mock bot) |
| `test_debit_manual_admin_besitos_insufficient_balance` | Unit Besito |
| `test_debit_manual_admin_besitos_success` | Unit Besito |
| `test_open_subscriber_list_requires_admin` | Handler |
| `test_open_subscriber_list_exactly_1_svc` | Handler |
| `test_confirm_extend_calls_grant_internal_only` | Handler |
| `test_confirm_kick_calls_admin_revoke_with_bot` | Handler |
| `test_confirm_grant_besitos_exactly_1_svc` | Handler |
| `test_confirm_debit_besitos_exactly_1_svc` | Handler |
| `test_vip_forward_flow_unchanged` | Regression (test_vip_handlers) |

**Comandos gates (ejecutar en orden):**

```bash
# Gate 1 — feature tests
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "subscriber_admin or SubscriberList or debit_manual_admin or admin_revoke_subscription"

# Gate 2 — VIP lifecycle + has_other_active
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "vip or TestVIPSubscriptionLifecycle or has_other_active"

# Gate 3 — atomicity + besitos grant
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "cross_service_atomicity or grant_manual_admin_besitos"

# Gate 4 — forward regression
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" tests/handlers/test_vip_handlers.py

# Gate 5 — broader smoke (0 regresiones atribuibles)
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" -k "reaction_ or daily_gift or invariants" tests/
```

**DoD F6:**
- [ ] Gates 1–5 green
- [ ] ruff en todos los archivos tocados
- [ ] grep: 0 `VIPService()` bare en nuevo handler (solo `get_service`)
- [ ] grep: 0 lógica `has_other_active` en handler (solo service)
- [ ] `decisions.md` append Item 36
- [ ] SUMMARY en `.planning/phases/36-vip-subscriber-admin-profiles/36-vip-subscriber-admin-profiles-SUMMARY.md`
- [ ] self-check PASSED en gsd log

---

## 6. Riesgos + mitigaciones (impact analysis)

### Críticos

| # | Riesgo | Mitigación |
|---|--------|------------|
| 1 | **Kick sin `has_other_active`** → expulsión indebida | `admin_revoke_subscription` copia literal scheduler L206–217; tests unit con 2 subs activas |
| 2 | **Débito besitos → saldo negativo o EventBus indebido** | `has_sufficient_balance` + `debit_besitos` (guard interno); NO emit event; tests insufficient |
| 3 | **Extend bypass `grant_internal_vip_access`** | Handler confirm llama solo ese método; test grep prohibe `end_date` assignment en handler |

### Medios

| # | Riesgo | Mitigación |
|---|--------|------------|
| 4 | `list_subscribers` sin `is_admin` | Todos los entrypoints nuevos con `is_admin`; test non-admin rejected |
| 5 | Handlers >50 LOC | Puros `build_*`/`format_*`; Test*PureHelpers import-inside |
| 6 | Snapshot acopla dominios | BesitoService **local** solo dentro `get_subscriber_admin_snapshot`; 0 import BesitoService en handler de perfil |

### 3 sistemas críticos

| Sistema | Riesgo | Mitigación |
|---------|--------|------------|
| **Canales-VIP** | Kick manual inconsistente con scheduler | Mismo contrato `has_other_active`; mock bot tests; gold `TestVIPSubscriptionLifecycle` |
| **Gamificación** | Nuevo path debit sin lock | Reusa `debit_besitos` FOR UPDATE; gold `cross_service_atomicity` |
| **Narrativa** | Observer reacciona a ADMIN debit | Debit NO emite `besitos_awarded`; gold `invariants` |

---

## 7. Archivos exactos

| Archivo | Acción |
|---------|--------|
| `handlers/vip_subscriber_admin_handlers.py` | **CREATE** |
| `services/vip_service.py` | EDIT (+list page, snapshot, admin_revoke) |
| `services/besito_service.py` | EDIT (+debit_manual_admin_besitos) |
| `keyboards/callback_data.py` | EDIT (+Subscriber* 5 clases) |
| `keyboards/inline_keyboards.py` | EDIT (+keyboards, wire callbacks) |
| `utils/lucien_voice.py` | EDIT (+admin subscriber copy) |
| `handlers/vip_handlers.py` | EDIT (deprecar list_subscribers only) |
| `handlers/__init__.py` | EDIT (export router) |
| `bot.py` | EDIT (include_router) |
| `tests/handlers/test_vip_subscriber_admin_handlers.py` | **CREATE** |
| `tests/unit/test_vip_service.py` | EDIT |
| `tests/unit/test_besito_service.py` | EDIT |
| `tests/handlers/test_vip_handlers.py` | EDIT (regression) |
| `decisions.md` | EDIT (append post-F6) |
| `.planning/phases/36-vip-subscriber-admin-profiles/PLAN.md` | Este archivo |

---

## 8. Instrucciones para gsd-executor

### Pre-vuelo
1. Leer este PLAN + impact report + `handlers/channel_handlers.py` (pagination) + `handlers/vip_handlers.py` (forward besitos) + `services/scheduler_service.py` L191–246 (kick).
2. Crear log executor: `.planning/quick/gsd-vip-subscriber-admin-profiles.log`
3. GSD pre-log **antes de cada edit**.

### Gold patterns (copiar al pie de la letra)

#### A) Channel pagination (`handlers/channel_handlers.py`)
```python
PENDING_PAGE_SIZE = 8  # → SUBSCRIBER_PAGE_SIZE = 8
def _clamp_page(page, total_count): ...
def build_pending_nav_row(channel_db_id, page, total_count): ...
def build_pending_requests_keyboard(...): ...
```
Adaptar a suscriptores: filas clicables → perfil en lugar de approve/reject.

#### B) Forward besitos FSM (`handlers/vip_handlers.py` L752+)
```python
# Patrón cantidad → confirm → 1 svc → notify best-effort
parse_positive_besito_amount(message.text)
with get_service(BesitoService) as svc:
    ok, balance = svc.grant_manual_admin_besitos(...)
await notify_forward_besitos_result(bot, message, target_user_id, ok, amount, balance, admin_id, ...)
```
Réplica para debit (sin notify obligatorio Etapa 1; opcional best-effort).

#### C) grant_internal extend (`services/vip_service.py` L534+)
```python
with get_service(VIPService) as svc:
    ok, sub, meta = await svc.grant_internal_vip_access(user_id, tariff_id)
```
**Prohibido:** calcular `end_date` en handler o duplicar commit/emit.

#### D) Scheduler kick (`services/scheduler_service.py` L206–242)
```python
other_active = vip_service.has_other_active_subscription(user_id, subscription.id)
if other_active:
    subscription.is_active = False
    db.commit()
    return  # NO ban
await bot.ban_chat_member(chat_id=channel.channel_id, user_id=...)
await bot.unban_chat_member(...)
# clear vip_entry_state + notify LucienVoice.vip_expired()
```
Encapsular íntegro en `admin_revoke_subscription`; handler solo pasa `callback.bot`.

#### E) 1-service + puros (hardener estándar)
- `with get_service(X) as svc:` + **exactly 1** business call.
- Puros: docstring `"""Función pura (sin estado ni side-effects)."""`
- Naming: `verb_context_result` (ej. `build_subscriber_list_text`).

### Prohibiciones explícitas
- **NO** tocar forward flow `vip_handlers.py` L752–971.
- **NO** instanciar `BesitoService` en handler de perfil (snapshot en VIPService).
- **NO** llamar `debit_besitos` / `credit_besitos` directo desde handler.
- **NO** `ban_chat_member` desde handler (solo via `admin_revoke_subscription`).
- **NO** crear archivos fuera del mapa §7 sin justificación en log.

### Self-check checklist (marcar PASSED en gsd log)

```
[ ] F1–F6 completadas en orden
[ ] SUBSCRIBER_PAGE_SIZE = 8
[ ] Dead callback list_subscribers_{channel_id} cableado
[ ] list_subscribers eliminado de vip_handlers (forward intacto)
[ ] is_admin en 100% entrypoints vip_subscriber_admin_handlers
[ ] Handlers confirm: grep 1 get_service por handler
[ ] admin_revoke: has_other_active test PASS
[ ] debit_manual_admin: insufficient balance test PASS
[ ] extend: solo grant_internal_vip_access
[ ] Gates 1–5 pytest green (-q --tb=line -p no:cov --override-ini="addopts=")
[ ] ruff clean
[ ] decisions.md append Item 36
[ ] LOC ≤50 funciones nuevas
[ ] 0 regresión test_vip_handlers forward
SELF-CHECK: PASSED
```

---

## 9. Handoff

**Ready for:** gsd-executor (F1→F6) → arch-enforcer → test-guardian → gates §F6 → (opcional documentador).

**Item 36/1 — vip-subscriber-admin-profiles Etapa 1.**

**Orden de ejecución:** F1 → F2 → F3 → F4 → F5 → F6. No saltar fases; tests de cada DoD antes de continuar.

**Referencias:**
- `.grok/agent-memory/impact-analyzer/vip-subscriber-admin-profiles.md`
- `.planning/phases/30-channel-admin-hardening/PLAN.md` (pagination gold)
- `.planning/phases/36-admin-forward-besitos-grant/PLAN.md` (besitos FSM gold)
- `tests/integration/test_vip_subscription_lifecycle.py` (has_other_active gold)
- `tests/handlers/test_channel_admin_handlers.py` (pagination pure helpers)