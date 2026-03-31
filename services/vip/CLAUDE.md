# VIP Domain

Membresías exclusivas y acceso a contenido VIP via tokens de un solo uso.

## Services
- `vip_service.py` — Gestión de membresías

## Handlers
- `vip_handlers.py` — Admin: creación de tarifas y tokens

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

## Reglas de Negocio
- Token = un solo uso, no reutilizable
- Subscription tiene fecha de expiración → scheduler la renueva o expira
- Expiración: scheduler bans/unbans del canal VIP
- Recordatorio 24h antes de expirar
- **Solo admins** crean tarifas y tokens

## Notas técnicas
- Canales VIP se gestionan via `ChannelService`, NO son env vars
- No existe "agregar/quitar VIP directo" — siempre via Token → Subscription
- `is_user_vip()` verifica suscripción activa contra el canal

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos en `vip_service.py` antes de asumir que existen
4. Si necesitas dar VIP directo a un usuario → generar y redimir un token
