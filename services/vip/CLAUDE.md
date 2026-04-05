# VIP Domain

Membresías exclusivas y acceso a contenido VIP via tokens de un solo uso. Incluye el círculo exclusivo donde los suscriptores pueden enviar mensajes anónimos a Diana.

## Services
- `vip_service.py` — Gestión de membresías
- `anonymous_message_service.py` — Mensajes anónimos VIP a Diana

## Handlers
- `vip_handlers.py` — Admin: creación de tarifas y tokens
- `vip_user_handlers.py` — Círculo exclusivo VIP, envío de mensajes anónimos
- `anonymous_message_admin_handlers.py` — Diana gestiona susurros recibidos

## Modelos clave
- `Tariff` — Plan de precio/duración (ej: "1 mes VIP", $299, 30 días)
- `Token` — Código único, un solo uso, expira. Estados: ACTIVE / USED / EXPIRED
- `Subscription` — Suscripción activa de un usuario. Vinculada a un Token y un Channel

## Flujo VIP (Token-based)

```
Admin crea Tarifa
    → Admin genera Token
    → Admin comparte Token con visitante
    → Visitante usa /start → introduce Token
    → VIPService.validate_token() + redeem_token()
    → Se crea Subscription activa
    → Se envía invite link al canal VIP
    → Se banpea al canal VIP
```

## VIPService API
```python
# Tarifas
create_tariff(name, duration_days, price) -> Tariff
get_tariff(tariff_id) -> Tariff
get_all_tariffs(active_only=True) -> list[Tariff]
update_tariff(tariff_id, **kwargs) -> bool
deactivate_tariff(tariff_id) -> bool

# Tokens
generate_token(tariff_id, expires_in_days) -> Token
get_token_by_code(token_code) -> Token
get_all_tokens(status=None) -> list[Token]
validate_token(token_code) -> tuple  # (success, error_message)
redeem_token(token_code, user_id) -> Subscription
revoke_token(token_id) -> bool

# Suscripciones
get_user_subscription(user_id, channel_id=None) -> Subscription
get_active_subscriptions(channel_id=None) -> list[Subscription]
get_expiring_subscriptions(hours=24) -> list[Subscription]
expire_subscription(subscription_id) -> bool
is_user_vip(user_id, channel_id=None) -> bool
get_vip_channel() -> Channel
```

## AnonymousMessageService API
```python
# Envío y consulta
send_message(sender_id, content) -> AnonymousMessage
get_message(message_id) -> AnonymousMessage
get_all_messages(status=None, limit=50) -> list[AnonymousMessage]
get_unread_messages() -> list[AnonymousMessage]
get_message_count_by_status() -> dict  # {'unread': N, 'read': N, 'replied': N}

# Gestión por Diana
mark_as_read(message_id, admin_id) -> bool
reply_to_message(message_id, admin_id, reply) -> bool
get_sender_info(message_id) -> User  # Solo para casos delicados
delete_message(message_id) -> bool
```

## Flujo de Mensajes Anónimos

```
Suscriptor VIP
    → Click "💎 El círculo exclusivo"
    → Click "💌 Enviar mensaje a Diana"
    → Escribe mensaje (3-4000 chars)
    → Confirma envío
    → AnonymousMessageService.send_message()
    → Diana recibe notificación (estado: UNREAD)

Diana (Admin)
    → Click "💌 Susurros del círculo"
    → Ve estadísticas (no leídos/leídos/respondidos)
    → Lee mensaje (cambia a READ)
    → Opciones:
        • Responder → reply_to_message() → envía DM al suscriptor
        • Revelar remitente → get_sender_info() (solo casos delicados)
        • Eliminar → delete_message()
```

### Estados de Mensaje Anónimo
- `UNREAD` — No leído por Diana
- `READ` — Leído, sin respuesta
- `REPLIED` — Diana respondió, respuesta enviada al suscriptor

### Seguridad y Privacidad
- El remitente permanece anónimo para Diana
- Solo el ID se guarda en BD para casos delicados
- `get_sender_info()` debe usarse con extrema precaución
- Las respuestas de Diana se envían por DM directo al suscriptor

## Reglas de Negocio
- Token = un solo uso, no reutilizable
- Subscription tiene fecha de expiración → scheduler la renueva o expira
- Expiración: scheduler bans/unbans del canal VIP
- Recordatorio 24h antes de expirar
- **Solo admins** crean tarifas y tokens

## Reglas de Mensajes Anónimos
- **Solo suscriptores VIP activos** pueden enviar mensajes
- Mínimo 3 caracteres, máximo 4000
- Diana puede responder directamente al suscriptor
- La identidad del remitente está oculta por defecto
- Revelar remitente solo para casos delicados (acoso, amenazas)
- Los mensajes persisten en BD con historial completo

## Notas técnicas
- Canales VIP se gestionan via `ChannelService`, NO son env vars
- No existe "agregar/quitar VIP directo" — siempre via Token → Subscription
- `is_user_vip()` verifica suscripción activa contra el canal

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos en `vip_service.py` antes de asumir que existen
4. Si necesitas dar VIP directo a un usuario → generar y redimir un token
