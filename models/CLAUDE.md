# Models

Entidades de SQLAlchemy y acceso a base de datos.

## Archivos

- [models.py](models.py) - Todos los modelos
- [database.py](database.py) - Configuración de conexión

## Modelos Principales

| Modelo | Descripción | Relaciones |
|--------|-------------|------------|
| `User` | Usuarios del bot | besitos_balance, vip_expiry |
| `BesitoTransaction` | Historial de besitos | User |
| `Package` | Paquetes de contenido | Files, Products |
| `StoreProduct` | Productos en tienda | Package, Orders |
| `Order` | Órdenes de compra | User, Items |
| `Mission` | Misiones disponibles | UserProgress |
| `MissionProgress` | Progreso de misiones | User, Mission |
| `Promotion` | Promociones comerciales | Package, Interests |
| `PromotionInterest` | Intereses en promociones | User, Promotion |
| `StoryNode` | Nodos de narrativa | Choices |
| `StoryChoice` | Opciones de decisión | Node |
| `UserStoryProgress` | Progreso narrativo | User |
| `Archetype` | Arquetipos definidos | - |
| `StoryAchievement` | Logros de narrativa | UserAchievements |

## Acceso a DB

```python
from models import User
from models.database import get_session

async def get_user(user_id: int):
    async with get_session() as session:
        return await session.get(User, user_id)
```

## Reglas

- Usar ORM (SQLAlchemy), **nunca** SQL raw
- Transacciones para operaciones atómicas
- Historial inmutable (besitos)
