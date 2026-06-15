# Channels Domain

Gestión de canales de Telegram (VIP y gratuito). Canales se almacenan en la DB, NO son env vars.

## Services
- `channel_service.py` — Gestión de canales y solicitudes pendientes
- `channel_grant.py` — **Orquestación compartida** grant/reject (scheduler + admin)

## Handlers
- `channel_handlers.py` — Admin: registrar, listar, configurar wait time, mensajes, approve/reject
- `free_channel_handlers.py` — Auto-aprobación: `ChatJoinRequest` + `ChatMemberUpdatedFilter`

## Modelos clave
- `Channel` — Canal registrado (VIP o FREE), con wait time y mensajes custom
- `PendingRequest` — Solicitud pendiente de acceso al canal free

## Flujo Canal Free (Auto-aprobación)

```
Visitante solicita unión al canal free
    → ChatJoinRequest recibido por free_channel_handlers
    → Se crea PendingRequest con scheduled_approval_at = ahora + wait_time
    → Job ritual 30s (_send_free_welcome_job) con approval_message custom o default
    → Scheduler pickea requests ready → channel_grant.grant_pending_request
    → approve_chat_join_request + welcome_message custom + invite link
```

## Contrato de IDs (dualidad)

| Contexto | ID usado |
|----------|----------|
| Callbacks admin, `PendingRequest.channel_id`, `update_wait_time`, `approve_all` | **DB PK** (`Channel.id`) |
| `approve_chat_join_request`, `decline_chat_join_request`, `schedule_free_welcome` | **Telegram chat ID** (`Channel.channel_id`) |

## channel_grant.py API

```python
resolve_channel_message(channel, field_name, default_fn, channel_name) -> str
build_welcome_payload(channel) -> str          # welcome custom + invite_link
build_approval_payload(channel) -> str         # ritual custom
async grant_pending_request(db, request, bot) -> GrantResult
async reject_pending_request(db, request, bot) -> bool  # status="rejected"
```

`GrantResult`: `success`, `request_id`, `error`
`ApproveAllResult`: `approved`, `failed`, `errors`

## ChannelService API
```python
# Canales
create_channel(channel_id, channel_name, channel_type, wait_time_minutes) -> Channel
get_channel_by_id(channel_id) -> Channel          # Telegram ID
get_channel_by_db_id(db_id) -> Channel            # DB PK
update_wait_time(channel_db_id, minutes) -> bool
update_approval_message(channel_db_id, text) -> bool
update_welcome_message(channel_db_id, text) -> bool
clear_custom_messages(channel_db_id, msg_type) -> bool  # approval|welcome|all

# Pending requests
create_pending_request(user_id, channel_id, ...) -> PendingRequest
get_pending_requests_by_channel(channel_db_id) -> list[PendingRequest]
get_ready_to_approve() -> list[PendingRequest]  # Para scheduler
approve_request(request_id) -> bool             # Solo BD (legacy)

# Async grant (admin + scheduler delega a channel_grant)
# expected_channel_db_id = DB PK del canal (IDOR guard desde Phase 30 R2)
async approve_request_now(request_id, expected_channel_db_id, bot) -> GrantResult
async approve_all_pending_now(channel_db_id, bot) -> ApproveAllResult
async reject_request_now(request_id, expected_channel_db_id, bot) -> bool
get_valid_pending_request(request_id, expected_channel_db_id) -> PendingRequest | None
```

## Mensajes personalizados

| Campo BD | Momento | Default |
|----------|---------|---------|
| `approval_message` | Job ritual 30s | `LucienVoice.free_entry_ritual` |
| `welcome_message` | Post-aprobación | `LucienVoice.free_entry_welcome` |

## Reglas de Negocio
- **Canales se registran en DB**, no via env vars
- `ChannelType.FREE`: auto-aprobación con wait time configurable (1–1440 min custom)
- Admin `approve_all` y approve/reject individual usan **grant real** en Telegram
- Status `rejected` para rechazo admin (sin migración — cabe en String(20))
- Paginación admin: 8 solicitudes pendientes por página

## Notas técnicas
- Scheduler `_process_pending_requests` delega a `grant_pending_request` (0 cambio semántico)
- Handlers admin: `is_admin` en todos los entrypoints + `get_service(ChannelService)`
- Tests gold: `tests/integration/test_free_entry_flow.py` (TestSchedulerPendingRequestsJob)
- Handler tests: `tests/handlers/test_channel_admin_handlers.py`
- Grant unit tests: `tests/unit/test_channel_grant.py`

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos en `channel_service.py` y `channel_grant.py`
4. Recuerda la dualidad de IDs en cada método nuevo