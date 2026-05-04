---
name: lucien-services
description: Service layer patterns for Lucien Bot. Trigger when: implementing service logic, creating business rules, adding methods to services, or working in the services/ directory. This skill provides patterns for correctly implementing services following the domain-driven architecture.
---

# Lucien Bot — Services

Lógica de negocio por dominio. Un service = un dominio.

## Archivo de Referencia
Consultar siempre: `services/CLAUDE.md` para lista completa de servicios y métodos disponibles.

## Dominios y Services

| Dominio | Services | Descripción |
|---------|----------|-------------|
| **VIP** | `VIPService`, `AnonymousMessageService` | Membresías via tokens, tarifas, suscripciones |
| **Gamificación** | `BesitoService`, `BroadcastService`, `DailyGiftService` | Besitos, reacciones, regalo diario |
| **Canales** | `ChannelService` | Canales VIP/free, auto-aprobación, wait time |
| **Tienda** | `StoreService`, `PackageService` | Catálogo, carrito, compras, paquetes |
| **Misiones** | `MissionService`, `RewardService` | Tareas recurrentes/únicas, recompensas |
| **Promociones** | `PromotionService` | "Me Interesa", precios en centavos MXN |
| **Narrativa** | `StoryService` | Nodos de historia, arquetipos, logros |
| **Usuarios** | `UserService` | Perfiles, roles admin |
| **Sistema** | `SchedulerService`, `BackupService` | APScheduler, backup dual |
| **Analytics** | `AnalyticsService` | Dashboard stats, exports CSV |

## Estructura Típica de Service

```python
class BesitoService:
    def get_or_create_balance(self, user_id: int) -> UserBalance:
        """Obtiene o crea balance de besitos para un usuario."""
        balance = session.query(UserBalance).filter_by(user_id=user_id).first()
        if not balance:
            balance = UserBalance(user_id=user_id, besitos=0)
            session.add(balance)
            session.commit()
            logger.info(f"besito_service/create_balance/{user_id}=0")
        return balance

    def credit_besitos(self, user_id: int, amount: int, source: TransactionSource) -> bool:
        """Credita besitos a un usuario. Retorna True si exitoso."""
        if amount <= 0:
            logger.warning(f"besito_service/credit_besitos/{user_id}=invalid_amount:{amount}")
            return False

        balance = self.get_or_create_balance(user_id)
        balance.besitos += amount

        transaction = BesitoTransaction(
            user_id=user_id,
            amount=amount,
            type=TransactionType.CREDIT,
            source=source
        )
        session.add(transaction)
        session.commit()

        logger.info(f"besito_service/credit_besitos/{user_id}={amount}")
        return True
```

## Reglas de Services

- Un service es dueño de su dominio
- Centraliza toda la lógica del dominio
- **PROHIBIDO**: lógica duplicada en múltiples services
- **PROHIBIDO**: acceso a DB directo (usar models)
- Funciones máximo 50 líneas
- Logging en cada acción importante

## Acceso a Models

Los services acceden a DB a través de models, no raw SQL:

```python
from models import User
from models.database import get_session

async def get_user(user_id: int):
    async with get_session() as session:
        return await session.get(User, user_id)
```

## Transacciones para Operaciones Atómicas

```python
def deliver_reward(self, user_id: int, reward_id: int) -> bool:
    try:
        with session.begin():
            reward = session.query(Reward).get(reward_id)
            if reward.type == "besitos":
                self.credit_besitos(user_id, reward.amount, TransactionSource.MISSION)
            elif reward.type == "vip":
                vip_service.extend_vip(user_id, reward.duration_days)
        return True
    except Exception as e:
        logger.error(f"reward_service/deliver/{user_id}={e}")
        session.rollback()
        return False
```

## Validaciones Comunes

```python
# Verificar admin
if not is_admin(telegram_id):
    raise PermissionError("Only admins can perform this action")

# Verificar saldo suficiente
if not has_sufficient_balance(user_id, amount):
    raise ValueError(f"Insufficient balance: {amount} required")

# Validar cantidad positiva
if amount <= 0:
    return False
```

## Dominios Específicos

Para reglas específicas de cada dominio, consultar:
- `services/vip/CLAUDE.md`
- `services/gamification/CLAUDE.md`
- `services/channels/CLAUDE.md`
- `services/store/CLAUDE.md`
- `services/missions/CLAUDE.md`
- `services/promotions/CLAUDE.md`
- `services/narrative/CLAUDE.md`