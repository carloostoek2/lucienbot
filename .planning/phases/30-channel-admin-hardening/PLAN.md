# PLAN: Channel Admin Hardening — Seguridad, grant real, mensajes y gestión individual

**Type:** gsd-planner output (for gsd-executor)  
**Date:** 2026-06-15  
**Phase:** `30-channel-admin-hardening`  
**Source:** Project Feature Advisor analysis (channel admin module) + user-approved scope: **ítems #1, #2, #4, #5, #6**

**Pool context (hardener):** Nuevo pool de 3 ítems (A → B → C). Este PLAN cubre el pool completo. Al cierre: arch-enforcer + test-guardian + tests green + documentador para HARDENING_ROADMAP.

---

## 1. Resumen ejecutivo

Fortalecer el módulo de administración de canales para que los Custodios puedan operarlo con confianza:

| # | Feature | Problema actual |
|---|---------|-----------------|
| **4** | Guards `is_admin()` | Solo el entrypoint `admin_channels` verifica permisos |
| **2** | Wait time personalizado | Opción "custom" sin handler de mensaje |
| **1** | Aprobación masiva real | `approve_all_pending` solo muta BD, sin `approve_chat_join_request` |
| **5** | Editor de mensajes | Botón `config_messages_*` sin handler; columnas BD sin uso |
| **6** | Gestión individual | Lista de pendientes solo lectura |

**Cambio de contrato explícito:** El test `test_approve_all_pending_marks_db_only_without_telegram_effects` en `test_free_entry_flow.py` debe **invertirse** — el path admin de aprobación masiva **sí** debe otorgar membresía en Telegram.

**Sistema crítico #3 protegido:** Flujo Free (pending → approve → welcome). Toda lógica de grant se centraliza en un helper compartido con el scheduler; tests gold del scheduler deben seguir verdes.

---

## 2. Alcance (In / Out)

### En alcance

- `handlers/channel_handlers.py` — seguridad, FSM, UI admin
- `services/channel_service.py` — métodos mensajes + async grant/reject
- `services/channel_grant.py` — **nuevo** — orquestación TG + BD (grant/reject compartido)
- `services/scheduler_service.py` — delegar loop de `_process_pending_requests` al helper
- `handlers/free_channel_handlers.py` — resolver mensajes custom en welcome manual
- `keyboards/callback_data.py` + `keyboards/inline_keyboards.py` — callbacks tipados
- `utils/lucien_voice.py` — textos admin (mensajes, reject confirm, resultados parciales)
- Tests: unit + integration (flip contrato) + handlers (nuevo archivo)
- `services/channels/CLAUDE.md` — documentar grant helper + nuevos métodos

### Fuera de alcance (explícito)

- Toggle `is_active` / soft-delete de canales
- Dashboard métricas por canal / export CSV
- Validación permisos del bot al registrar canal
- Vincular acciones VIP (`manage_tariffs_{id}`) al canal seleccionado
- Refactor completo hardener de todos los handlers (solo puros necesarios para ≤50 LOC)
- Migraciones Alembic (status `"rejected"` cabe en `String(20)` existente)
- Cambios en flujos VIP, gamificación o narrativa

---

## 3. Principios no negociables

1. **Handlers → 1 service** por entrypoint: `with get_service(ChannelService) as svc:`; métodos async reciben `bot` inyectado desde `callback.bot` / `message.bot`.
2. **Funciones ≤ 50 LOC** — extraer puros `build_*`, `format_*`, `parse_*`, `resolve_*`.
3. **ID duality** (documentar en cada método afectado):
   - Callbacks / `PendingRequest.channel_id` / `update_wait_time` / `approve_all` → **DB PK** (`Channel.id`)
   - `approve_chat_join_request`, `decline_chat_join_request`, `schedule_free_welcome` → **Telegram chat ID** (`Channel.channel_id`)
4. **Logging:** `channel_handlers | <acción> | user_id=<admin_id> | resultado=...`
5. **Voz Lucien:** defaults en `LucienVoice`; mensajes custom del canal como override opcional.
6. **GSD pre-log** antes de cada edit en `.planning/quick/gsd-channel-admin-hardening.log`.

---

## 4. Diseño técnico

### 4.1 Nuevo módulo `services/channel_grant.py`

Orquestación compartida entre scheduler, admin masivo e individual.

| Función | Tipo | Responsabilidad |
|---------|------|-----------------|
| `resolve_channel_message(channel, field, default_fn, channel_name) -> str` | Puro | Usa `welcome_message` / `approval_message` si no vacíos; si no, `default_fn(channel_name)` |
| `build_welcome_payload(channel) -> str` | Puro | Welcome resuelto + append `\n{invite_link}` si existe |
| `async grant_pending_request(db, request, bot) -> GrantResult` | Async | `approve_chat_join_request` → commit BD (`approved` + `approved_at`) → `send_message` welcome. Maneja `USER_ALREADY_PARTICIPANT` como scheduler |
| `async reject_pending_request(db, request, bot) -> bool` | Async | `decline_chat_join_request` → `status="rejected"` + commit |

`GrantResult` dataclass: `success: bool`, `request_id: int`, `error: str | None`

`ApproveAllResult` dataclass: `approved: int`, `failed: int`, `errors: list[str]`

**Contrato:** Misma semántica que `_process_pending_requests` actual (rollback por request en error; continue en lote).

### 4.2 Extensiones `ChannelService`

**Sync (existentes + nuevos):**
```python
update_approval_message(channel_db_id: int, text: str | None) -> bool
update_welcome_message(channel_db_id: int, text: str | None) -> bool
```

**Async (nuevos — reciben `bot`):**
```python
async def approve_request_now(self, request_id: int, bot) -> GrantResult
async def approve_all_pending_now(self, channel_db_id: int, bot) -> ApproveAllResult
async def reject_request_now(self, request_id: int, bot) -> bool
```

`approve_all_pending` (sync, solo BD) queda como método interno o deprecated — el path admin **solo** usa `approve_all_pending_now`.

### 4.3 Mapeo mensajes personalizados (#5)

| Campo BD | Momento de envío | Default si vacío |
|----------|------------------|------------------|
| `approval_message` | Job ritual 30s (`_send_free_welcome_job`) | `LucienVoice.free_entry_ritual` |
| `welcome_message` | Post-aprobación (scheduler, admin grant, `handle_member_join`) | `LucienVoice.free_entry_welcome` |

Wire en:
- `services/scheduler_service.py` — `_send_free_welcome_job`, `_process_pending_requests` (vía grant helper)
- `handlers/free_channel_handlers.py` — `handle_member_join`

### 4.4 Callbacks nuevos (`keyboards/callback_data.py`)

```python
class ConfigMessagesCallback(CallbackData, prefix="config_msgs"):
    channel_id: int  # DB PK

class ConfigMessageTypeCallback(CallbackData, prefix="config_msg_type"):
    channel_id: int
    msg_type: str  # "approval" | "welcome"

class ApproveOneCallback(CallbackData, prefix="approve_one"):
    request_id: int
    channel_id: int  # DB PK (navegación)

class RejectOneCallback(CallbackData, prefix="reject_one"):
    request_id: int
    channel_id: int

class ConfirmRejectCallback(CallbackData, prefix="confirm_reject"):
    request_id: int
    channel_id: int

class PendingPageCallback(CallbackData, prefix="pending_page"):
    channel_id: int
    page: int
```

Reemplazar `callback_data=f"config_messages_{channel_id}"` por `ConfigMessagesCallback`.

### 4.5 FSM nuevos estados (`ChannelStates`)

```python
configuring_wait_time_custom = State()   # #2
configuring_messages_menu = State()      # #5
configuring_approval_message = State()   # #5 — ritual
configuring_welcome_message = State()    # #5 — bienvenida
```

### 4.6 Status `PendingRequest`

| Status | Origen |
|--------|--------|
| `pending` | Solicitud creada |
| `approved` | Grant exitoso (scheduler, admin, join manual) |
| `cancelled` | Usuario abandonó canal (`handle_member_leave`) |
| `rejected` | **Nuevo** — Custodio rechazó desde admin (#6) |

---

## 5. Fases de ejecución

### Fase 1 — Seguridad + wait time custom (Ítems #4 + #2)

**Objetivo:** Cerrar brechas de permisos y botón roto de wait time.

**Tareas:**
1. Importar `is_admin` + `get_service` en `channel_handlers.py`.
2. Añadir `lambda cb: is_admin(cb.from_user.id)` en **cada** `@router.callback_query`.
3. En **cada** `@router.message` de FSM: guard al inicio con `is_admin(message.from_user.id)`; si falla → Lucien + `state.clear()`.
4. Migrar `ChannelService()` + `try/finally close` → `with get_service(ChannelService) as svc:` en handlers tocados.
5. Añadir `ChannelStates.configuring_wait_time_custom`.
6. En `set_wait_time` cuando `minutes == "custom"`: set state custom (no solo mostrar texto y return).
7. Nuevo puro `parse_wait_minutes(text: str) -> int | None` (rango 1–1440).
8. Handler message para custom wait → `svc.update_wait_time(channel_db_id, minutes)`.

**Archivos:** `handlers/channel_handlers.py`

**Tests (F1):**
- Nuevo `tests/handlers/test_channel_admin_handlers.py`:
  - `test_non_admin_callback_rejected` (ej. `list_channels`)
  - `test_non_admin_message_fsm_rejected` (ej. wait custom)
  - `test_parse_wait_minutes_valid_invalid` (puro, puede vivir en `test_channel_grant.py` o inline)

**DoD F1:**
- [ ] 0 callbacks/messages de canal sin guard admin
- [ ] Wait custom 7 min funciona; 0 / 2000 rechazados con mensaje Lucien
- [ ] `get_service(ChannelService)` en todos los entrypoints de `channel_handlers.py`

---

### Fase 2 — Grant helper + approve masivo real + wire mensajes servicio (Ítems #1 + #5 parcial)

**Objetivo:** Unificar grant con scheduler; aprobación masiva con efecto TG; resolver mensajes en runtime.

**Tareas:**
1. Crear `services/channel_grant.py` con funciones de §4.1.
2. Refactor `_process_pending_requests`: loop delega a `grant_pending_request` — **0 cambio de comportamiento observable**.
3. Refactor `_send_free_welcome_job`: usar `resolve_channel_message(..., "approval_message", free_entry_ritual)`.
4. Añadir métodos sync de mensajes en `ChannelService`.
5. Añadir métodos async `approve_request_now`, `approve_all_pending_now`, `reject_request_now` en `ChannelService` (delegan a `channel_grant`).
6. Actualizar `approve_all_requests` handler → `await svc.approve_all_pending_now(channel_db_id, callback.bot)`.
7. Wire `build_welcome_payload` en grant helper y `free_channel_handlers.handle_member_join`.

**Archivos:** `services/channel_grant.py` (new), `services/channel_service.py`, `services/scheduler_service.py`, `handlers/free_channel_handlers.py`, `handlers/channel_handlers.py` (solo approve_all)

**Tests (F2):**
- Nuevo `tests/unit/test_channel_grant.py`:
  - `resolve_channel_message` custom / vacío / whitespace
  - `build_welcome_payload` con y sin invite_link
  - `grant_pending_request` happy path (mock bot)
  - `grant_pending_request` USER_ALREADY_PARTICIPANT
  - `reject_pending_request` → decline + status rejected
- `tests/unit/test_channel_service.py`: `update_*_message`
- **Flip** `tests/integration/test_free_entry_flow.py`:
  - Renombrar/actualizar `test_approve_all_pending_marks_db_only_without_telegram_effects` → assert `approve_chat_join_request.called` y `send_message.called`
  - Docstring nuevo contrato: "admin approve_all MUST grant TG membership"
- Re-run `TestSchedulerPendingRequestsJob` — 0 regresiones

**DoD F2:**
- [ ] Scheduler tests gold verdes sin cambio de semántica
- [ ] approve_all admin llama TG + welcome
- [ ] Mensaje custom en ritual/welcome cuando campos BD seteados (unit + 1 integration)

---

### Fase 3 — UI mensajes + gestión individual (Ítems #5 UI + #6)

**Objetivo:** Completar panel admin: editor de mensajes y acciones por solicitud.

**Tareas:**

**#5 UI:**
1. Reemplazar callback f-string por `ConfigMessagesCallback` en `inline_keyboards.py`.
2. Handler menú mensajes: Ritual / Bienvenida / Ver actuales / Restaurar default.
3. FSM para editar cada tipo; aceptar texto o `"quitar"` para default Lucien.
4. Puros: `build_messages_menu_keyboard`, `truncate_message_preview(text, max_len=120)`.
5. Textos admin en `LucienVoice` (menú, guardado, restaurado).

**#6 UI:**
1. Refactor `view_pending_requests`: lista paginada (8 por página) con `PendingPageCallback`.
2. Por solicitud: botones `ApproveOneCallback` / `RejectOneCallback`.
3. `approve_one` → `await svc.approve_request_now` → refresh lista.
4. `reject_one` → confirmación `ConfirmRejectCallback` → `await svc.reject_request_now`.
5. Puros: `build_pending_requests_keyboard`, `format_pending_request_line`.
6. Footer: mantener "Aprobar todas" + volver a detalle canal.
7. Textos Lucien para approve/reject individual y errores parciales.

**Archivos:** `handlers/channel_handlers.py`, `keyboards/callback_data.py`, `keyboards/inline_keyboards.py`, `utils/lucien_voice.py`, `services/channels/CLAUDE.md`

**Tests (F3):**
- `tests/handlers/test_channel_admin_handlers.py`:
  - `test_config_messages_menu_renders`
  - `test_save_welcome_message_calls_service`
  - `test_approve_one_calls_service_with_bot`
  - `test_reject_one_requires_confirmation`
  - `test_pending_list_pagination`
- `tests/unit/test_channel_service.py`: approve/reject individual

**DoD F3:**
- [ ] Botón "Configurar mensajes" funcional end-to-end
- [ ] Aprobar/rechazar individual con efecto TG
- [ ] Paginación si >8 pendientes
- [ ] Funciones nuevas ≤50 LOC (verificar con `inspect.getsourcelines`)

---

## 6. Inventario de archivos

| Archivo | Fase | Acción |
|---------|------|--------|
| `.planning/quick/gsd-channel-admin-hardening.log` | 1–3 | GSD pre-log |
| `handlers/channel_handlers.py` | 1–3 | Modify |
| `services/channel_grant.py` | 2 | **Create** |
| `services/channel_service.py` | 2–3 | Modify |
| `services/scheduler_service.py` | 2 | Modify (delegate only) |
| `handlers/free_channel_handlers.py` | 2 | Modify (resolve messages) |
| `keyboards/callback_data.py` | 3 | Modify |
| `keyboards/inline_keyboards.py` | 3 | Modify |
| `utils/lucien_voice.py` | 3 | Modify |
| `tests/unit/test_channel_grant.py` | 2 | **Create** |
| `tests/handlers/test_channel_admin_handlers.py` | 1–3 | **Create** |
| `tests/unit/test_channel_service.py` | 2–3 | Modify |
| `tests/integration/test_free_entry_flow.py` | 2 | Modify (flip contrato) |
| `services/channels/CLAUDE.md` | 3 | Modify |

---

## 7. Verificación final (gates)

```bash
# Unit + grant
pytest tests/unit/test_channel_service.py tests/unit/test_channel_grant.py -q --tb=line -p no:cov --override-ini="addopts="

# Integration scheduler + approve_all
pytest tests/integration/test_free_entry_flow.py -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "Scheduler or approve_all"

# Handlers admin
pytest tests/handlers/test_channel_admin_handlers.py -q --tb=line -p no:cov --override-ini="addopts="

# Smoke crítico (obligatorio al cierre del pool)
pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "cross_service_atomicity or reaction_ or daily or invariants or SchedulerPending or approve_all or TestChannelGrant" \
  tests/
```

**Greps post-implementación:**
```bash
grep -c "is_admin" handlers/channel_handlers.py          # >= 15 (todos los entrypoints)
grep -c "with get_service(ChannelService)" handlers/channel_handlers.py  # >= 10
grep -c "ChannelService()" handlers/channel_handlers.py  # == 0
grep "config_messages_" keyboards/ -r                    # == 0 (migrado a CallbackData)
```

**Ruff:** `ruff check` + `ruff format` en archivos tocados.

**Smoke manual sugerido (UAT):**
1. Custodio registra canal Free → wait custom 7 min → persiste en detalle.
2. Configura mensaje ritual custom → visitante solicita unión → recibe custom a los 30s.
3. Configura welcome custom → tras aprobación recibe custom + invite link.
4. Lista pendientes → aprobar uno → usuario entra al canal.
5. Rechazar uno → usuario no entra; status `rejected` en BD.
6. Aprobar todas → todos entran; mensaje indica count.
7. Usuario no-admin intenta `list_channels` → denegado.

---

## 8. Riesgos y mitigaciones

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Regresión scheduler al extraer grant | Alta | Delegar sin cambiar orden commit/rollback; re-run gold tests antes de merge |
| Flip de contrato rompe CI | Media | Actualizar test en misma PR que cambio prod; docstring explícito |
| HTML inválido en mensajes custom | Baja | UI advierte "HTML básico"; truncar preview; try/except en send con fallback Lucien default |
| `approve_all` parcial (N ok, M fail) | Media | `ApproveAllResult` transparente en mensaje admin |
| Handler async + service mixto | Baja | Solo métodos grant son async; patrón `await svc.approve_*_now(..., bot)` |
| Confusión ID duality | Alta | Comentarios en grant helper + CLAUDE.md; asserts en tests con ambos IDs |

---

## 9. Secuencia hardener (post-implementación)

Por cada fase (o ítem A/B/C del pool):

1. **impact-analyzer** — mapa de archivos + 3 crit check
2. **gsd-executor** — implementar con GSD pre-log
3. **arch-enforcer** — PASS / PASS WITH NOTES (0 critical)
4. **test-guardian** — "suite protege adecuadamente" + re-runs golds
5. Al cierre del pool: **documentador** → HARDENING_ROADMAP + `services/channels/CLAUDE.md`

**Pool phrase (verbatim al cierre):**
> Pool anterior de 4 cerrado (tests passing per user). Nuevo pool de 4 iniciado. Quedan ~2-4 clusters del análisis inicial después de este pool.

_(Ajustar si este pool es independiente del anterior — documentador decide según ROADMAP actual.)_

---

## 10. Handoff

**Estado:** PLAN listo para revisión del usuario. **No ejecutar** hasta aprobación explícita.

**Tras aprobación:** Ejecutar Fase 1 → Fase 2 → Fase 3 en orden. Cada fase: GSD log + tests de su DoD antes de continuar.

**Preguntas abiertas para el revisor:**

1. ¿Confirmamos status `"rejected"` (sin migración) vs reutilizar `"cancelled"` para rechazo admin?
2. ¿Paginación de pendientes a 8 por página es adecuada o preferís otro límite?
3. ¿El pool se ejecuta como un solo tirón (3 fases) o prefieres parar y revisar tras Fase 1?

---

**Referencias:**
- `.claude/agent-memory/impact-analyzer/channels-impact-map.md`
- `.claude/agent-memory/impact-analyzer/channels-todos.md`
- `tests/integration/test_free_entry_flow.py` (TestSchedulerPendingRequestsJob — gold pattern)
- `handlers/store_admin_handlers.py` (precedente puros + get_service + is_admin)
- `services/channels/CLAUDE.md`