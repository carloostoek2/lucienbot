# Promotions Domain

Promociones comerciales y registro de intereses ("Me Interesa").

## Services
- [promotion_service.py](../promotion_service.py) - Gestión de promociones

## Handlers
- [promotion_user_handlers.py](../../handlers/promotion_user_handlers.py) - Usuario
- [promotion_admin_handlers.py](../../handlers/promotion_admin_handlers.py) - Admin

## Modelos
- `Promotion` - Promociones comerciales
- `PromotionInterest` - Intereses registrados
- `Package` - Paquetes relacionados

## Flujo "Me Interesa"
```
Usuario → Ver promoción → Click "Me Interesa"
  → Verificar no bloqueado
  → Registrar interés
  → Notificar a TODOS los admins
  → Mensaje al usuario: "Diana ha sido notificada..."
```

## PromotionService API
```python
- create_promotion(...)                    # Crear promoción
- get_active_promotions()                  # Promociones activas
- express_interest(user_id, promotion_id) # Registrar interés
- notify_admins(promotion_id)             # Notificar admins
- block_user(user_id)                     # Bloquear usuario
- is_user_blocked(user_id)                # Verificar bloqueo
```

## Reglas de Negocio
- Usuario bloqueado = no puede expresar interés
- Un interés por usuario por promoción
- Notificación a **TODOS** los admins (no solo uno)
- Verificar bloqueo **antes** de registrar interés

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos existentes en promotion_service.py
