# Channels Domain

Gestión de canales de Telegram (VIP y gratuito).

## Services
- [channel_service.py](../channel_service.py) - Gestión de canales

## Handlers
- [channel_handlers.py](../../handlers/channel_handlers.py) - Gestión canales
- [free_channel_handlers.py](../../handlers/free_channel_handlers.py) - Canal gratuito

## Modelos
- `Channel` - Canales configurados
- `User` - Relación con usuarios

## Configuración
```bash
VIP_CHANNEL_ID=@divan_de_diana      # Canal VIP
FREE_CHANNEL_ID=@senorita_kinky_free # Canal gratuito
```

## ChannelService API
```python
- set_vip_channel(channel_id)        # Configurar canal VIP
- set_free_channel(channel_id)       # Configurar canal gratuito
- get_vip_channel()                  # Obtener canal VIP
- get_free_channel()                 # Obtener canal gratuito
- is_user_member(user_id, channel_id)  # Verificar membresía
```

## Verificación de Acceso
```
Usuario → Acceder contenido VIP
  → Verificar membresía en VIP_CHANNEL
  → Si no es miembro → Mensaje de suscripción
  → Si es miembro → Mostrar contenido
```

## Reglas
- VIP_CHANNEL = contenido exclusivo
- FREE_CHANNEL = contenido público
- Verificar membresía antes de entregar contenido VIP

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos existentes en channel_service.py
