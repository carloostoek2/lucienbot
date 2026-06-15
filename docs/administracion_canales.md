# Módulo de Administración de Canales — Lucien Bot

**Alcance:** Únicamente el módulo de canales (administración + soporte al flujo de acceso). Excluye detalles completos de VIP, gamificación, narrativa, tienda, etc. excepto las interacciones explícitas de integración.

**Dominio:** Canales (Free y VIP). Gestiona el registro de dominios de Telegram en DB, configuración de acceso Free (wait time + auto-aprobación), mensajes custom, approve/reject manuales y automáticos, y la base para suscripciones VIP a canales VIP.

**Arquitectura local:** `handlers/channel*` (solo routing + UI + FSM + puros) → `services/ChannelService` (dueño del dominio) → models (Channel, PendingRequest) + `channel_grant` (orquestación compartida) + scheduler (jobs). Sin lógica de negocio en handlers, sin DB fuera de models.

**Entrypoint admin:** `admin_channels` (admin_handlers.py) → `channel_management_keyboard()` → handlers de `channel_handlers.py` (router independiente).

---

## Módulos Principales

| Módulo | Archivo | Responsabilidad |
|--------|---------|-----------------|
| Handlers Admin | `handlers/channel_handlers.py` | FSM `ChannelStates`, guards `is_admin`, puros para UI/texto/teclados, flujos de registro/config/pendings/approve/reject/delete. Usa **exactamente 1 service** vía `with get_service(ChannelService) as svc:`. |
| Handlers Free (soporte) | `handlers/free_channel_handlers.py` | Recepción de `ChatJoinRequest` y `ChatMemberUpdated` (LEAVE/JOIN). Crea `PendingRequest` + schedule ritual. Maneja cancelación por leave. (No es "admin" pero parte integral del flujo de canales). |
| ChannelService | `services/channel_service.py` | CRUD de `Channel` y `PendingRequest`. Update de wait/invite/mensajes custom. `get_ready_to_approve`, `get_valid_pending_request` (guard). Métodos async `*_now` que delegan a grant. Context manager de sesión propio. |
| Orquestación Grant | `services/channel_grant.py` | Puras: builders de payloads (`build_welcome_payload`, `build_approval_payload`, `resolve_channel_message`). `grant_pending_request` (TG approve + commit BD + welcome) y `reject_pending_request`. Dataclasses `GrantResult` / `ApproveAllResult`. Validación de invite links. |
| Scheduler (integración) | `services/scheduler_service.py` | Jobs: `_send_free_welcome_job` (ritual 30s), `_process_pending_requests` (auto-grant de ready), jobs de expiración VIP (ban + cleanup usando `subscription.channel`). Importa `channel_grant` y `ChannelService`. |
| Modelos | `models/models.py` | `Channel`, `PendingRequest`, `ChannelType`, `Subscription` (para VIP). Relaciones. |
| Soporte VIP (integración) | `services/vip_service.py` | Para canales VIP: `redeem_token` busca primer `Channel` VIP activo y crea `Subscription` (channel_id = DB PK). |
| Keyboards / Callbacks | `keyboards/inline_keyboards.py`, `keyboards/callback_data.py` | `channel_management_keyboard`, `channel_actions_keyboard`, `channel_type_keyboard`, callbacks `ChannelDetailCallback`, `Approve*Callback`, `Pending*Callback`, `Config*Callback`, etc. |
| Admin entry + analytics | `handlers/admin_handlers.py` | `admin_channels` (muestra menú), conteos en analytics (free/vip channels + pending). |

**Notas de construcción (Hardener Phase 30 / Item canal):** 
- `is_admin` en **todos** los entrypoints admin + lambdas de filtro.
- `with get_service(ChannelService)` (1 sola llamada por handler).
- Funciones puras (verb+context+result, stateless, importables para tests, ≤50 LOC verificado).
- Guard IDOR explícito: `get_valid_pending_request(request_id, expected_channel_db_id)`.
- Logging estándar: `"channel_handlers | approve_one | user_id=... | result=..."`.
- UI 1:1 idéntica vía puros (LucienVoice + previews escapados + paginación 8 items).
- Dualidad de IDs documentada y defendida.

---

## Modelos Clave (extracto)

```python
class ChannelType(enum.StrEnum):
    FREE = "free"
    VIP = "vip"

class Channel(Base):
    id = PK (Integer)                       # DB surrogate — usar en admin, PendingRequest.channel_id, Subscription.channel_id, callbacks, get_by_db_id, approve_all etc.
    channel_id = BigInteger unique          # Telegram chat ID (negativo usual) — usar en approve_chat_join_request, decline, send_message, scheduler jobs, get_by_id(tg), BroadcastMessage.
    channel_name, channel_type, is_active
    # Free-specific
    wait_time_minutes: int = 3
    welcome_message: Text | None
    approval_message: Text | None
    invite_link: str | None
    # relations: subscriptions, pending_requests

class PendingRequest(Base):
    id, user_id, channel_id (FK a channels.id = DB PK)
    username, first_name
    status: str = "pending"  # pending | approved | cancelled | rejected
    requested_at, scheduled_approval_at, approved_at
    channel = relationship back to Channel

class Subscription(Base):  # Usado por VIP domain para canales VIP
    user_id (FK users.telegram_id), channel_id (FK channels.id = DB PK), token_id
    start_date, end_date, is_active
    channel = relationship
```

**Regla dualidad de IDs (crítica, mantenida por contrato):**
- Interno/admin/relaciones/pendings/callbacks/svc: **siempre DB PK** (`Channel.id`, `PendingRequest.channel_id`).
- Efectos en Telegram + scheduler jobs + lookups desde eventos TG: **Telegram ID** (`Channel.channel_id`).
- Métodos del service documentan explícitamente qué esperan.
- `get_channel_by_id(tg_id)` vs `get_channel_by_db_id(db_pk)`.
- `create_pending_request(..., channel_id=...)` recibe DB PK.
- Riesgo histórico: pasar PK donde se esperaba TG → rituales silenciosamente fallaban.

---

## ChannelService — API Principal

### Canales
- `create_channel(channel_id: int (tg), channel_name, channel_type: ChannelType, wait_time=3)` → Channel. Para VIP fuerza wait=0.
- `get_channel_by_id(channel_id: int)` → por TG ID.
- `get_channel_by_db_id(db_id: int)` → por PK DB.
- `get_all_channels()`, `get_free_channels()`, `get_vip_channels()`.
- `delete_channel(channel_id: int (db pk))`.
- `update_wait_time(channel_db_id, minutes)`.
- `update_invite_link(channel_db_id, link | None)` (valida formato vía `channel_grant.is_valid...`).
- `update_approval_message(channel_db_id, text | None)`, `update_welcome_message(...)`.
- `clear_custom_messages(channel_db_id, msg_type: "approval"|"welcome"|"all")`.

### Pending Requests
- `create_pending_request(user_id, channel_id (DB PK), username=None, first_name=None)` → calcula `scheduled_approval_at = now + wait_time`.
- `get_request_by_id`, `get_pending_request(user, channel)`, `get_pending_requests_by_channel(channel_db_id)` (ordenado por scheduled + id).
- `get_valid_pending_request(request_id, expected_channel_db_id)` → None si no pending o mismatch (IDOR guard + log).
- `get_all_pending_requests`, `get_ready_to_approve()` (scheduled <= now y pending).
- `approve_request(request_id)` (solo marca BD — legacy, no TG grant).
- `cancel_request(user_id, channel_id (db))`.
- `approve_all_pending(channel_id=None)` (solo BD — legacy).
- `count_pending_requests(channel_id=None)`.

### Async Grant (admin + scheduler delega)
- `async approve_request_now(request_id, expected_channel_db_id (PK), bot) -> GrantResult`
- `async approve_all_pending_now(channel_db_id (PK), bot) -> ApproveAllResult`
- `async reject_request_now(request_id, expected_channel_db_id (PK), bot) -> bool`

Internamente obtiene sesión, valida con `get_valid...`, delega a `grant_pending_request(db, request, bot)` / reject.

**Patrón de servicio:** `__init__(db=None)`, `_owns_session`, `_get_db()`, `close()`. Soporta inyección para tests/transacciones compartidas.

---

## channel_grant.py — Orquestación Compartida

Puras (sin side effects, fáciles de testear):

- `is_valid_telegram_invite_link(link)`
- `resolve_channel_message(channel, field_name, default_fn, channel_name) → str` (custom si non-empty else default_fn(name))
- `append_invite_link(message, invite_link)` (solo si válido https://t.me/..., HTML-escaped)
- `build_welcome_payload(channel) → str` (welcome resuelto + invite si válido)
- `build_approval_payload(channel) → str` (ritual/approval resuelto)

Resultados:
```python
@dataclass
class GrantResult:
    success: bool
    request_id: int
    error: str | None = None

@dataclass
class ApproveAllResult:
    approved: int = 0
    failed: int = 0
    errors: list[str] = ...
```

Core:
- `async grant_pending_request(db, request, bot)`: obtiene channel (de relationship), `bot.approve_chat_join_request(chat_id=channel.channel_id (TG), user_id)`, marca approved+approved_at, envía welcome vía `build_welcome_payload` + social_links_keyboard. Maneja `USER_ALREADY_PARTICIPANT` como success. Rollback en error.
- `async reject_pending_request(db, request, bot)`: `bot.decline_chat_join_request(usa TG id)`, marca "rejected".

Usado por:
- Scheduler (process + ritual job)
- ChannelService `*_now` (admin manual)
- free_channel_handlers (en JOIN_TRANSITION legacy path)

---

## Flujos Principales (Administración de Canales)

### 1. Registro de Canal (Admin)
FSM: `waiting_channel_message` → `confirming_channel` → `selecting_channel_type`
- Forward de mensaje del canal → extrae `forward_from_chat.id` (TG) + title.
- Confirm → elige FREE ("Vestíbulo", wait configurable) o VIP ("Círculo VIP", wait=0).
- `svc.create_channel(...)` → registrado en DB.
- UI: LucienVoice + teclado de gestión.

### 2. Listado y Detalle
- `list_channels` → `get_all_channels()` → botones `ChannelDetailCallback(db_pk)`.
- `channel_detail` → `get_by_db_id`, cuenta pendings (solo Free), render tipo + acciones vía `channel_actions_keyboard(channel_id=db, type)`.

Acciones por tipo (en keyboard):
- Free: config wait, config invite, config messages, ver pendientes, approve/reject, delete.
- VIP: más limitado (invite, messages?, delete).

### 3. Configuración Free
- Wait time: presets (vía `WaitTimeCallback`) o custom (1-1440 min, `parse_wait_minutes` + state).
- Invite link: input o "quitar", validación, update.
- Mensajes custom:
  - `approval_message`: ritual (enviado ~30s tras join request).
  - `welcome_message`: post-aprobación (+ invite link si configurado).
  - Menu: editar, ver preview (usa `_resolve_message_preview` + defaults LucienVoice), restaurar a None (defaults).
  - `update_*_message(db_pk, text|None)`, `clear_custom...`.
- Defaults provistos por `LucienVoice.free_entry_ritual(name)`, `free_entry_welcome(name)` vía `resolve...`.

### 4. Solicitudes Pendientes (Free) — Admin + Auto
Paginación: `PENDING_PAGE_SIZE=8`, `build_pending_requests_keyboard` (approve/reject por fila + nav + "Aprobar todas" + volver).

Puros clave:
- `build_pending_request_rows`, `build_pending_nav_row`, `build_pending_footer_rows`, `build_pending_requests_keyboard`
- `build_pending_list_text`, `format_pending_request_line`, `format_display_name*`, `truncate_message_preview`

Handlers:
- `view_pending_requests` / `pending_page_nav` → `_render_pending_list` (with get_service + puros).
- `approve_one_request` → `get_valid...` (guard) → `svc.approve_request_now(...)` (real TG grant) → re-render + toast.
- Reject: confirm screen → `confirm_reject_request` → `reject_request_now` + re-render + toast.
- `approve_all_requests` → `approve_all_pending_now` (cuenta + resultado detallado) → resumen.

**Auto (sin admin):**
- `free_channel_handlers.handle_join_request`:
  - UserService.get_or_create (legacy directo aquí).
  - Si canal registrado + activo + no pending existente → `create_pending_request(channel.id = DB PK)` → `scheduler.schedule_free_welcome(user, chat.id = TG ID)`.
  - Si ya pending → mensaje de impaciencia.
- Leave → `cancel_request`.
- JOIN_TRANSITION legacy → marca approved + welcome (ahora centralizado en grant).
- Scheduler `_send_free_welcome_job(user_id, channel_tg_id)`: envía `build_approval_payload` (ritual) tras 30s.
- Scheduler `_process_pending_requests` (interval): `get_ready_to_approve()` → `grant_pending_request` para cada una.

Resultado: aprobación automática tras wait_time (con ritual intermedio), o manual instantáneo por admin.

### 5. Delete Canal
Confirm → `svc.delete_channel(db_pk)` (cascade orphan pendings).

### 6. Canales VIP (lado admin de canales + VIP)
- Se registran igual (tipo VIP).
- Acceso **no** vía pending/wait: vía tokens (VIPService) → Subscription a un Channel VIP.
- En `vip_service.redeem_token`: busca `Channel` VIP activo (`.first()`), crea Subscription con `channel_id = vip_channel.id (DB PK)`.
- Expiración: scheduler marca inactive + `ban_chat_member` / `unban` usando `subscription.channel.channel_id (TG)` (si no tiene otra sub activa).
- Reminders de expiración también via subs + channel.

---

## Integración con Scheduler

- Ritual 30s y auto-approve: delegan a `channel_grant` + `ChannelService` (usa DB PK o TG según job).
- VIP expiry/reminders: `VIPService` + `subscription.channel` (acceso directo a relación para obtener channel_id TG para ban).
- Jobs como funciones de módulo + `_get_bot()` lazy (evita pickling).
- `schedule_free_welcome` programado desde free_handler.

---

## Cómo se Comunica con Gamificación

**El módulo de canales (ChannelService / channel_handlers / grant) NO depende de ni llama a servicios de gamificación (BesitoService, MissionService, etc.).**

**Dirección inversa (Gamificación → Canales):**

- Misiones y recompensas (dominio gamificación) soportan `RewardType.VIP_ACCESS`.
- `RewardService.create_reward_vip(name, ..., tariff_id)`.
- `deliver_reward` → `_deliver_vip_access`: 
  - `vip_service.get_tariff(reward.tariff_id)`
  - `vip_service.generate_token(tariff_id)` (nuevo token)
  - Envía al usuario link `/start=<token_code>`
- Usuario redime (common start handler) → `VIPService.redeem_token` → valida token, crea/extiende `Subscription` a **un Channel VIP** (query interna por `ChannelType.VIP`).
- Efecto: la recompensa de misión da acceso a canal(es) VIP vía suscripción.
- No hay cruce de besitos directo con canales (free es gratuito; VIP es por token/tarifa).
- Broadcast (relacionado gamif/difusión) usa `ChannelService.get_all_channels()` para targets.
- HealthService consulta conteos de canales/pendings (read-only).
- EventBus: VIP emite `EVENT_VIP_ACTIVATED` (post redeem/subs); narrativa y nurture escuchan (best-effort). Canales no emiten eventos propios aquí.

**Contrato:** 0 mutación de besitos desde canales; entrega VIP de reward es "mejor esfuerzo" post-misión; atomicidad preservada en credit_besitos local on-demand dentro de Reward (patrón hardener).

---

## Cómo se Comunica con Narrativa

**Narrativa NO usa ChannelService, PendingRequest ni los handlers/flows de admin de canales directamente.**

**Dirección (Narrativa consume estado derivado de VIP/Channels):**

- `StoryNode` tiene `required_vip: bool`.
- `StoryService.can_access_node(user_id, node_id, is_vip: bool)`: si `node.required_vip and not is_vip` → deniega con "fragmento VIP required".
- `advance_to_node` etc. reciben `is_vip` del caller (calculado típicamente con `VIPService.get_user_subscription(user_id)` o equivalente que chequea subs activas).
- Subs activas implican acceso a los canales VIP registrados (el mismo destino de las suscripciones creadas al redimir tokens VIP).
- Por tanto: progreso narrativo en nodos VIP requiere membresía VIP activa, que a su vez se materializa como Subscription a un Channel VIP.
- No hay llamadas desde StoryService a ChannelService ni creación de pendings.
- Canales Free son completamente independientes de narrativa (cualquiera puede entrar con wait).
- EventBus: narrativa es listener de `besitos_awarded` (para triggers de historia), no de eventos de canales.

**Resumen de acoplamiento:**
- Canales (admin) → proveen "destinos" (Channel VIP) que VIPService usa para materializar acceso.
- Gamif (recompensas) → genera el derecho (token → sub → Channel).
- Narrativa → consume el derecho (is_vip derivado de sub activa) para gatear nodos.
- Separación fuerte: ChannelService es dueño solo de registro/config/pendings Free + grant; VIP y Story mantienen sus contratos.

---

## Reglas, Patrones y Gotchas

- **Handlers:** exactamente 1 service. `get_service` context manager. Guards `is_admin` + `_deny_non_admin_*`. Estado FSM limpiado siempre. Logging por acción.
- **Puros:** builders de texto/keyboard, parsers (`parse_wait_minutes`, `parse_custom_message_text`), formatters, truncate. Tests unit importan los puros directamente (sin patch de get_service).
- **≤50 LOC:** puros + delegados en service para wizards largos.
- **IDOR / Seguridad:** `get_valid_pending_request` + expected_channel_db_id en todos los approve/reject admin callbacks. Validación en update invite.
- **Mensajes:** custom > default LucienVoice. HTML parse_mode + escape en previews/admin lists.
- **Canales en DB:** nunca hardcodear TG IDs de canales VIP/Free como env (solo config de broadcast u otros). Migraciones agregan columnas (ej. approval_attempts histórico).
- **Scheduler:** jobs no mutan desde canales de forma que rompa atomicidad de gamif/narrativa.
- **Tests clave:** `tests/handlers/test_channel_admin_handlers.py`, `tests/unit/test_channel_grant.py`, `tests/integration/test_free_entry_flow.py` (TestSchedulerPendingRequestsJob + pilots de contrato dualidad).
- **Health/Observability:** ChannelService usado para conteos read-only (free/vip/pending/ready).

**Antes de tocar:** leer `services/channels/CLAUDE.md`, `models/CLAUDE.md` (sección dualidad), `handlers/CLAUDE.md` (patrón hardener + phase 30), arquitectura y rules.

---

**Fin del documento — solo módulo de administración de canales.**

Construido con: handlers puros + 1-service, service central + grant compartido, scheduler jobs de módulo, dualidad IDs defendida, integración indirecta vía VIP/Subscription para gamif y narrativa (0 acoplamiento directo innecesario).
