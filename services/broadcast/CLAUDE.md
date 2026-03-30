# Broadcast Domain

Difusión masiva de mensajes a usuarios.

## Services
- [broadcast_service.py](../broadcast_service.py) - Difusión masiva

## Handlers
- [broadcast_handlers.py](../../handlers/broadcast_handlers.py) - Admin broadcast

## Modelos
- `User` - Destinatarios

## BroadcastService API
def broadcast_message(text: str, admin_id: int) -> None:
    """Enviar a todos"""
    ...

def broadcast_to_vip(text: str, admin_id: int) -> None:
    """Enviar solo a VIP"""
    ...

def get_broadcast_stats(broadcast_id: int) -> dict:
    """Estadísticas"""
    ...

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
