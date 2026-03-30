# VIP Domain

Membresías exclusivas y acceso a contenido VIP.

## Services
- [vip_service.py](../vip_service.py) - Gestión de membresías

## Handlers
- [vip_handlers.py](../../handlers/vip_handlers.py) - Gestión VIP

## Modelos
- `User.vip_expiry` - Fecha de expiración VIP
- `VIPSubscriber` - Suscriptores VIP (si existe tabla separada)

## VIPService API
```python
- add_vip_user(user_id, duration_days)  # Agregar VIP
- remove_vip_user(user_id)              # Remover VIP
- is_user_vip(user_id)                   # Verificar VIP
- get_vip_users()                        # Listar VIPs
- extend_vip(user_id, days)              # Extender VIP
```

## Reglas de Negocio
- **Solo admins** pueden asignar/quitar VIP
-VIP = acceso a contenido exclusivo
- Verificar VIP al acceder a contenido restringido
- Fecha de expiración para renovaciones automáticas

## Canales
- VIP_CHANNEL_ID - Canal exclusivo VIP
- FREE_CHANNEL_ID - Canal gratuito

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos existentes en vip_service.py
4. Usar middleware para verificar VIP en contenido restringido
