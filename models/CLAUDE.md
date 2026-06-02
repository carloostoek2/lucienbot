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

Usar el patrón moderno (context manager) o inyección de sesión en services:

```python
from models import User
from models.database import get_db_session  # o SessionLocal según contexto

# Preferido en código nuevo / tests
async with get_db_session() as session:
    user = await session.get(User, user_id)
```

## Dualidad de IDs (crítica - especialmente Canales Pre-GSD / Fundacional)

**Regla que debe mantenerse (ver services/channels/CLAUDE.md y tests de contrato):**

- `Channel.id`: Primary Key entero de la base de datos (surrogate). Se usa internamente para:
  - `PendingRequest.channel_id` (FK)
  - `Subscription.channel_id` (FK)
  - La mayoría de operaciones admin, `get_by_db_id`, `approve_all_pending`, `create_pending_request` (el parámetro `channel_id` aquí **siempre es DB PK**).
- `Channel.channel_id`: ID real del chat en Telegram (BigInteger, usualmente negativo, ej. -1001234567890). Se usa para:
  - Todas las llamadas a la API de Telegram (`approve_chat_join_request`, `ban_chat_member`, `send_message`, etc.).
  - `get_channel_by_id` (siempre espera Telegram ID).
  - `BroadcastMessage.channel_id` (FK a la columna TG).
  - Lookups desde eventos de Telegram (ChatJoinRequest.chat.id, etc.).
  - `schedule_free_welcome` y jobs `_send_free_welcome_job` / `_process_pending_requests` (pasan TG ID).

**Métodos clave en ChannelService:**
- `get_channel_by_id(tg_id)` → busca por `channel.channel_id`
- `get_channel_by_db_id(db_pk)` → busca por `channel.id`
- `create_pending_request(..., channel_id=...)` → **debe recibir DB PK** (documentado en el método).

**Handlers:**
- free_channel_handlers: recibe TG IDs de eventos Telegram → convierte correctamente (usa `.id` del ORM para pending, `chat.id` TG para schedule).

**Riesgo histórico:** Pasar `channel.id` (PK) donde se esperaba TG ID causaba que rituales de 30s no se enviaran (lookup fallaba silenciosamente). Cubierto por tests de regresión + pilots de contrato.

**Broadcast vs Canales:** Nota la inconsistencia de FK en el modelo (BroadcastMessage apunta a la columna TG, Pending/Subscription a la PK). Usar siempre los helpers del servicio para no confundir.

**Tests de contrato deseado:** Siempre validar ambos lados de la dualidad (PK para relaciones internas, TG para efectos en Telegram). Ver `tests/integration/test_free_entry_flow.py` (TestScheduler*Job y pilots) y `tests/unit/test_channel_service.py` + `test_scheduler.py`.

## Reglas

- Usar ORM (SQLAlchemy), **nunca** SQL raw
- Transacciones para operaciones atómicas
- Historial inmutable (besitos)

---

## Migraciones (Alembic)

**Directorio:** `alembic/versions/`

### Cadena actual de migraciones

```
e8de5494e5b6 (base: initial schema)
  └── 9fab8787057e (vip_entry_status/stage)
        └── 287e36271be4 (BigInteger upgrade)
              └── add_selected_emoji_ids
                    └── 499b5924723f (anonymous_messages)
                          └── 41d674ac4f9a (low_stock_threshold)
                                └── 756121049a4a (is_vip_exclusive)
                                      └── c32861733e54 (game_records)
                                            ├── 20250406_add_trivia... (TRIVIA enum)
                                            └── 20250406_manual_file_count
                                                  ├── 20250406_add_category_id_to_packages
                                                  │     └── 20250406_add_category_id_to_store_products
                                                  └── ea7e3c03df29 (merge head)
                                                        └── f7d08ca1ce1a (unique constraint)
                                                              └── 3f20074a2dd3 (last_reference_id)
                                                                    └── 7c158f7483f5 (cooldown_hours)
                                                                          └── 20250407_add_unique... (unique constraint dup)
                                                                                └── 20250407_add_game_and_anonymous_message... ← ÚLTIMO
```

### Patrón Enum-First (OBLIGATORIO)

**Antes de usar un nuevo valor de enum en código, crear UNA migración dedicada que agregue el valor al enum.**

```
# 1. Crear migración de enum
alembic revision -m "Add MY_VALUE to transaction_source enum"

# 2. Editar la migración para agregar el valor al enum
# 3. Luego usar el enum en código
```

**¿Por qué?** PostgreSQL no permite eliminar valores de enum. Si agregas un enum via SQLAlchemy autogenerate, el downgrade no funciona. Un migrate dedicado con `IF NOT EXISTS` y downgrade documentado es idempotente y seguro.

### Valores actuales del enum `transactionsource`

| Valor | Migración donde se agregó | Notas |
|-------|--------------------------|-------|
| REACTION, DAILY_GIFT, MISSION, PURCHASE, ADMIN | `e8de5494e5b6` (baseline) | |
| TRIVIA | `20250406_add_trivia_to_transaction_source_enum` | |
| ANONYMOUS_MESSAGE | `20250407_add_game_and_anonymous_message...` | |
| GAME | `20250407_add_game_and_anonymous_message...` | |

### Reglas para migraciones

1. **Enum values → migración dedicada** (nunca en la misma migración que crea la tabla que lo usa)
2. **Unique constraints → verificar que no existan duplicados** antes de agregar (`SELECT ... HAVING COUNT(*) > 1`)
3. **Idempotencia** — usar `IF NOT EXISTS` para enum values y constraints
4. **Downgrade** — documentar si PostgreSQL no soporta rollback (ej: enum DROP VALUE)
5. **Testing** — probar `alembic upgrade head` y `alembic downgrade -1` en SQLite local

### Verificar integridad de la cadena

```bash
python -c "
from alembic.config import Config
from alembic.script import ScriptDirectory
cfg = Config('alembic.ini')
script = ScriptDirectory.from_config(cfg)
for rev in reversed(list(script.walk_revisions())):
    parent = rev.down_revision or '(base)'
    print(f'{rev.revision[:30]} <- {str(parent)[:30]}')
"
```

### Base de datos de producción (Railway PostgreSQL)

- `postgresql://postgres:<password>@gondola.proxy.rlwy.net:53750/railway`
- Ver valores de un enum: `SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = '<enum_name>') ORDER BY enumlabel;`
- Ver constraint único: `SELECT conname FROM pg_constraint WHERE conrelid = '<table>'::regclass AND contype = 'u';`
- Ver versión: `SELECT * FROM alembic_version;`
