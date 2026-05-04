---
name: lucien-security
description: Security patterns for Lucien Bot. Trigger when: validating permissions, checking admin access, implementing rate limiting, or handling user authorization. This skill provides the security patterns and validation rules required before any state-changing operation.
---

# Lucien Bot — Seguridad

Reglas de seguridad obligatorias en cada acción que modifique estado o acceda a datos sensibles.

## Reglas de Seguridad (Siempre)

| Regla | Función |
|-------|---------|
| Validar IDs de callback | Siempre antes de procesar |
| Verificar permisos admin | `is_admin(telegram_id)` antes de acciones admin |
| Verificar saldos | `has_sufficient_balance(user_id, amount)` antes de transacciones |
| Usar transacciones | Para operaciones atómicas |
| Rate limiting | `ThrottlingMiddleware` con `aiolimiter` (admin bypass) |

## Verificar Admin

```python
from handlers.admin_handlers import is_admin

def admin_only(func):
    """Decorador para funciones que solo admins pueden ejecutar."""
    async def wrapper(callback: CallbackQuery, *args, **kwargs):
        if not is_admin(callback.from_user.id):
            await callback.answer("Sin permisos", show_alert=True)
            return
        return await func(callback, *args, **kwargs)
    return wrapper
```

## Verificar Saldo

```python
def has_sufficient_balance(user_id: int, amount: int) -> bool:
    """Verifica si el usuario tiene saldo suficiente."""
    with get_session() as session:
        service = BesitoService(session)
        balance = service.get_balance(user_id)
        return balance.besitos >= amount
```

## Rate Limiting

```python
from handlers.rate_limit_middleware import ThrottlingMiddleware

router.message.middleware(ThrottlingMiddleware(rate_limit=1.0, key_prefix="my_handler"))
```

- **5 requests por ventana de 10 segundos** por usuario
- **Custodios tienen bypass completo** (ADMIN_BYPASS=True)
- Mensaje de throttle: "Espera un momento... no tan rápido"

## FSM Storage

- **RedisStorage**: si `REDIS_URL` está configurado
- **MemoryStorage**: si no hay Redis

```python
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

# Configuración en bot.py
if REDIS_URL:
    storage = RedisStorage.from_url(REDIS_URL)
else:
    storage = MemoryStorage()
```

## Validación de Callbacks

```python
@router.callback_query(F.data.startswith("manage_channel_"))
async def manage_channel(callback: CallbackQuery, state: FSMContext):
    # Siempre validar el callback antes de procesar
    try:
        channel_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("Invalid callback", show_alert=True)
        return
```

## Transacciones para Operaciones Atómicas

```python
def atomic_operation(user_id: int, amount: int) -> bool:
    try:
        with session.begin():
            balance = session.query(UserBalance).filter_by(user_id=user_id).first()
            balance.besitos -= amount
            # Si algo falla, rollback automático
        return True
    except Exception:
        session.rollback()
        return False
```