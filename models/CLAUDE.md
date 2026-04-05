# Models

Entidades de SQLAlchemy y acceso a base de datos.

## Archivos
- [models.py](models.py) - Todos los modelos
- [database.py](database.py) - Configuración de conexión

## Modelos Principales

<!-- AUTO:MODELS -->
| Modelo | Descripción | Relaciones |
|--------|-------------|------------|
| `ChannelType` | Tipos de canal | - |
| `TokenStatus` | Estados de un token | - |
| `UserRole` | Roles de usuario | - |
| `User` | Modelo de usuario | Subscription, Token |
| `Channel` | Modelo de canal | Subscription, PendingRequest |
| `Tariff` | Modelo de tarifa VIP | Token |
| `Token` | Modelo de token de acceso VIP | Tariff, User, Subscription |
| `Subscription` | Modelo de suscripción VIP | User, Channel, Token |
| `PendingRequest` | Modelo de solicitud pendiente de acceso al canal Free | Channel |
| `TransactionType` | Tipos de transacción de besitos | - |
| `TransactionSource` | Fuentes de transacción de besitos | - |
| `BesitoBalance` | Saldo de besitos por usuario | BesitoTransaction |
| `BesitoTransaction` | Historial de transacciones de besitos | BesitoBalance |
| `ReactionEmoji` | Configuración de emojis de reacción y sus valores | BroadcastReaction |
| `BroadcastMessage` | Mensajes de broadcasting con reacciones | BroadcastReaction |
| `BroadcastReaction` | Reacciones de usuarios a mensajes de broadcast | BroadcastMessage, ReactionEmoji |
| `DailyGiftConfig` | Configuración del regalo diario | - |
| `DailyGiftClaim` | Registros de reclamos de regalo diario | - |
| `Package` | Paquetes de contenido (fotos/archivos) para tienda o recompensas | PackageFile |
| `PackageFile` | Archivos individuales dentro de un paquete | Package |
| `MissionType` | Tipos de misiones soportados | - |
| `MissionFrequency` | Frecuencia de la mision | - |
| `Mission` | Misiones configuradas por el administrador | Reward, UserMissionProgress |
| `UserMissionProgress` | Progreso de cada usuario en las misiones | Mission |
| `RewardType` | Tipos de recompensas | - |
| `Reward` | Recompensas configuradas por el administrador | Mission, Package, Tariff |
| `UserRewardHistory` | Historial de recompensas entregadas a usuarios | - |
| `StoreProduct` | Productos disponibles en la tienda | Package, CartItem, OrderItem |
| `CartItem` | Items en el carrito de compras de un usuario | StoreProduct |
| `OrderStatus` | Estados de una orden | - |
| `Order` | Ordenes de compra en la tienda | OrderItem |
| `OrderItem` | Items dentro de una orden | Order, StoreProduct |
| `PromotionStatus` | Estados de una promoción | - |
| `Promotion` | Promociones comerciales con precio en dinero real (MXN) | Package, PromotionInterest |
| `InterestStatus` | Estados de un interés en promoción | - |
| `PromotionInterest` | Registro de intereses de usuarios en promociones | Promotion |
| `BlockedPromotionUser` | Usuarios bloqueados del sistema de promociones | - |
| `NodeType` | Tipos de nodos de historia | - |
| `ArchetypeType` | Arquetipos disponibles para los usuarios | - |
| `StoryNode` | Nodos de la historia narrativa | StoryChoice |
| `StoryChoice` | Opciones de decision desde un nodo | StoryNode, StoryNode |
| `UserStoryProgress` | Progreso de cada usuario en la narrativa | - |
| `Archetype` | Información sobre cada arquetipo | - |
| `StoryAchievement` | Logros de narrativa desbloqueables | - |
| `UserStoryAchievement` | Logros desbloqueados por cada usuario | - |
| `AnonymousMessageStatus` | Estados de mensaje anónimo (UNREAD/READ/REPLIED) | - |
| `AnonymousMessage` | Mensajes anónimos VIP a Diana | User (sender) |



## Acceso a DB

`from models import User
from models.database import get_session

async def get_user(user_id: int):
    async with get_session() as session:
        return await session.get(User, user_id)`

## Reglas

- Usar ORM (SQLAlchemy), **nunca** SQL raw
- Transacciones para operaciones atómicas
- Historial inmutable (besitos)
