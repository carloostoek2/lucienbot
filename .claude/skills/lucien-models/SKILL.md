---
name: lucien-models
description: SQLAlchemy model patterns for Lucien Bot. Trigger when: creating models, modifying database schema, adding relationships, or working in the models/ directory. This skill provides patterns for correctly implementing SQLAlchemy models and database access.
---

# Lucien Bot — Models

Entidades de SQLAlchemy y acceso a base de datos.

## Archivos
- [models.py](models.py) - Todos los modelos
- [database.py](database.py) - Configuración de conexión

Consultar siempre: `models/CLAUDE.md` para modelo completo de entidades y relaciones.

## Patrón Base de Modelo

```python
from models.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

## Columnas Comunes

| Propósito | Tipo | Patrón |
|-----------|------|--------|
| Timestamps | DateTime(timezone=True) | `server_default=func.now()` / `onupdate=func.now()` |
| IDs Telegram | BigInteger | Para telegram_id, user_id |
| Booleanos | Boolean | `default=True` o `default=False` |
| Enums | Enum(EnumClass) | Con valores por defecto |
| Texto largo | Text | Para mensajes extensos |
| Strings | String(n) | Con límite de caracteres |

## Relaciones entre Modelos

```python
# Foreign Key directa
user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)

# Relación bidireccional
user = relationship("User", back_populates="subscriptions", cascade="all, delete-orphan")

# Unique constraint
__table_args__ = (
    UniqueConstraint('broadcast_id', 'user_id', name='uq_broadcast_user_reaction'),
)
```

## Enums Principales

**TransactionSource** (besitos):
```python
class TransactionSource(str, enum.Enum):
    REACTION = "reaction"           # Reacción a mensaje
    DAILY_GIFT = "daily_gift"       # Regalo diario
    MISSION = "mission"            # Recompensa por misión
    PURCHASE = "purchase"          # Compra en tienda
    ADMIN = "admin"                # Ajuste manual
    ANONYMOUS_MESSAGE = "anonymous_message"  # Mensaje anónimo VIP
    GAME = "GAME"                  # Victoria en dados
    TRIVIA = "TRIVIA"              # Respuesta correcta en trivia
```

Otros enums: `ChannelType` (FREE, VIP), `TokenStatus` (ACTIVE, USED, EXPIRED), `UserRole` (ADMIN, USER), `TransactionType` (CREDIT, DEBIT)

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
- Siempre incluir timestamps (created_at, updated_at)