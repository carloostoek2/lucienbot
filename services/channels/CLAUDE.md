# Channels Domain

Gestión de canales de Telegram (VIP y gratuito). Canales se almacenan en la DB, NO son env vars.

## Services
- `channel_service.py` — Gestión de canales

## Handlers
- `channel_handlers.py` — Admin: registrar, listar, configurar wait time
- `free_channel_handlers.py` — Auto-aprobación: `ChatJoinRequest` + `ChatMemberUpdatedFilter`

## Modelos clave
- `Channel` — Canal registrado (VIP o FREE), con wait time configurado
- `PendingRequest` — Solicitud pendiente de acceso al canal free

## Flujo Canal Free (Auto-aprobación)

```
Visitante solicita unión al canal free
    → ChatJoinRequest recibido por free_channel_handlers
    → Se crea PendingRequest con scheduled_approval_at = ahora + wait_time
    → Scheduler pickea requests ready
    → approve_request() → status = "approved"
    → Se envía invite link al visitante
    → Se añade al canal
```

## ChannelService API
```python
# Canales
create_channel(channel_id, channel_name, channel_type, wait_time_minutes) -> Channel
get_channel_by_id(channel_id) -> Channel
get_all_channels() -> list[Channel]
get_free_channels() -> list[Channel]
get_vip_channels() -> list[Channel]
update_wait_time(channel_id, minutes) -> bool
delete_channel(channel_id) -> bool

# Pending requests
create_pending_request(user_id, channel_id, scheduled_approval_at) -> PendingRequest
get_pending_request(user_id, channel_id) -> PendingRequest
get_pending_requests_by_channel(channel_id) -> list[PendingRequest]
get_ready_to_approve() -> list[PendingRequest]  # Para scheduler
approve_request(request_id) -> bool
cancel_request(user_id, channel_id) -> bool
approve_all_pending(channel_id=None) -> int
count_pending_requests(channel_id=None) -> int
```

## Reglas de Negocio
- **Canales se registran en DB**, no via env vars
- `ChannelType.FREE`: auto-aprobación con wait time configurable
- `ChannelType.VIP`: acceso via `Subscription` (Token → Subscription → acceso)
- `PendingRequest` permite approve en lote o automático
- Verificar que visitante no sea ya miembro antes de crear request

## Notas técnicas
- No existen `VIP_CHANNEL_ID` ni `FREE_CHANNEL_ID` como env vars
- Scheduler (`_process_pending_requests`) hace el approve automático
- `free_channel_handlers.py` es el único handler que hace commit directo a DB
  (fuera del service — esto es una excepción arquitectural documentada aquí)

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos en `channel_service.py`
4. Para wait times, usar `update_wait_time()`, no recrear el canal
