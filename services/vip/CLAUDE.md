# VIP Domain

Membresías exclusivas y acceso a contenido VIP via tokens de un solo uso. Incluye El Diván donde los suscriptores pueden enviar mensajes anónimos a Diana.

## Services
- `vip_service.py` — Gestión de membresías
- `anonymous_message_service.py` — Mensajes anónimos VIP a Diana

## Handlers
- `vip_handlers.py` — Admin: creación de tarifas y tokens
- `vip_user_handlers.py` — El Diván VIP, envío de mensajes anónimos
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
# Constantes
ANONYMOUS_MESSAGE_COST = 50          # besitos por mensaje
ANONYMOUS_MESSAGE_MIN_LENGTH = 3
ANONYMOUS_MESSAGE_MAX_LENGTH = 4000

# Envío pagado (atómico: VIP check + debit + persist)
send_paid_anonymous_message(user_id, content, cost=50) -> tuple  # (success, result_code, message|None)
# result_code: ok | not_vip | insufficient_balance | debit_failed | invalid_content | internal_error

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
    → Click "💎 El Diván"
    → Click "💌 Enviar mensaje a Diana"
    → Escribe mensaje (3-4000 chars)
    → Confirma envío
    → AnonymousMessageService.send_paid_anonymous_message()  # debit ANONYMOUS_MESSAGE + persist
    → Diana recibe notificación (estado: UNREAD, post-commit best-effort)

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
- **Convención actualizada (2026-06):** 
  - Distribución manual (admin genera token → usuario canjea con /start): siempre via Token → redeem → Subscription (token_id requerido, útil para share + is_gift + single-use).
  - Grants internos/programáticos (misiones/recompensas VIP, paquetes VIP en tienda, activación admin/forward, futuros): asociación directa a Tariff en Subscription (tariff_id). No se genera Token sintético a menos que se necesite explícitamente para fallback o auditoría.
- Subscription ahora puede tener tariff_id directo (nullable para compat). Queries prefieren tariff_id; fallback a token.tariff.
- `grant_vip_from_tariff` mantiene compatibilidad (todavía crea token para casos que lo requieran). Usar `grant_internal_vip_access` para el nuevo camino directo.
- `is_user_vip()` verifica suscripción activa contra el canal (independiente de cómo se otorgó).

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos en `vip_service.py` antes de asumir que existen
4. Distribución manual / usuario final → generar + redimir token.
5. Grants internos (misiones, tienda VIP, forward admin, etc.) → usar grant directo a tarifa (ver `grant_internal_vip_access` + tariff_id en Subscription).
