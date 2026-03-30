# Broadcast Domain

Difusión masiva de mensajes a usuarios.

## Services
- [broadcast_service.py](../broadcast_service.py) - Difusión masiva

## Handlers
- [broadcast_handlers.py](../../handlers/broadcast_handlers.py) - Admin broadcast

## Modelos
- `User` - Destinatarios

## BroadcastService API
```python
- broadcast_message(text, admin_id)    # Enviar a todos
- broadcast_to_vip(text, admin_id)    # Enviar solo a VIP
- get_broadcast_stats(broadcast_id)  # Estadísticas
```

## Flujo de Broadcast
```
Admin → Seleccionar tipo (todos/VIP)
  → Escribir mensaje
  → Confirmar envío
  → Enviar a cada usuario
  → Mostrar estadísticas
```

## Reglas
- **Solo admins** pueden hacer broadcast
- Rate limiting para evitar spam
- Estadísticas de entrega
- Logging de cada envío

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos existentes en broadcast_service.py
