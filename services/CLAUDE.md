# Services

Lógica de negocio por dominio. Un service = un dominio (no fragmentar).

## Servicios Disponibles

| Service | Dominio | Responsabilidad |
|---------|---------|----------------|
| [besito_service.py](besito_service.py) | Gamificación | Puntos, transacciones, historial |
| [daily_gift_service.py](daily_gift_service.py) | Gamificación | Regalo diario |
| [mission_service.py](mission_service.py) | Missions | Tareas, progreso, completado |
| [reward_service.py](reward_service.py) | Missions | Recompensas |
| [store_service.py](store_service.py) | Store | Productos, compras |
| [package_service.py](package_service.py) | Store | Paquetes de contenido |
| [promotion_service.py](promotion_service.py) | Promotions | Promociones, intereses |
| [vip_service.py](vip_service.py) | VIP | Membresías exclusivas |
| [story_service.py](story_service.py) | Narrative | Nodos, arquetipos, elección |
| [user_service.py](user_service.py) | Users | Perfiles de usuario |
| [channel_service.py](channel_service.py) | Channels | Gestión de canales |
| [broadcast_service.py](broadcast_service.py) | Broadcast | Difusión masiva |
| [scheduler_service.py](scheduler_service.py) | System | Tareas programadas |

## Reglas de Services

- Un service es dueño de su dominio
- Centraliza toda la lógica del dominio
- **PROHIBIDO**: lógica duplicada en múltiples services
- **PROHIBIDO**: acceso a DB directo (usar models)
- Funciones máximo 50 líneas
- Logging en cada acción importante

## Acceso a DB

Los services NO acceden a DB directamente. Usan models:

```python
from models import User, BesitoTransaction

# Correcto
user = await session.get(User, user_id)
# Incorrecto
await session.execute(text("SELECT * FROM users"))
```
