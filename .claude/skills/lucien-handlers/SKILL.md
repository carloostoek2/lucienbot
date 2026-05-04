---
name: lucien-handlers
description: Handler patterns for Lucien Bot. Trigger when: creating or modifying handlers, implementing FSM states, adding callback queries, setting up middleware, or working in the handlers/ directory. This skill provides the routing patterns and rules unique to this codebase's handler layer.
---

# Lucien Bot — Handlers

Solo enrutan eventos desde Telegram. **SIN lógica de negocio, SIN acceso a DB.**

## Archivo de Referencia
Consultar siempre: `handlers/CLAUDE.md` para estructura completa y lista de todos los handlers.

## Middleware

- `ThrottlingMiddleware` (`rate_limit_middleware.py`) — Rate limiting global
  - 5 requests por ventana de 10 segundos por usuario
  - **Custodios tienen bypass completo** (ADMIN_BYPASS=True)
  - Mensaje de throttle: "Espera un momento... no tan rápido"
  - Usa `aiolimiter.AsyncLimiter`

## Estructura de Handler

```python
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Solo llama a services. Sin lógica, sin DB."""
    user = message.from_user

    user_service = UserService()
    vip_service = VIPService()

    logger.info(f"/start recibido - user_id={user.id}")

    # Solo llamadas a services
    db_user = user_service.get_or_create_user(...)
    is_vip = vip_service.is_user_vip(user.id)

    await message.answer(...)
```

## FSM (Finite State Machine)

```python
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

class TariffStates(StatesGroup):
    waiting_name = State()
    waiting_price = State()
    waiting_duration = State()

@router.callback_query(F.data == "create_tariff")
async def start_tariff(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Nombre de la tarifa:")
    await state.set_state(TariffStates.waiting_name)

@router.message(TariffStates.waiting_name)
async def process_tariff_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    ...
```

## Reglas de Handlers

1. **UN service** por handler
2. **SIN lógica** de negocio
3. **SIN acceso** directo a DB
4. **Logging** de eventos recibidos
5. Máximo 50 líneas por función

## Ejemplo Correcto

```python
async def handle_balance(callback: CallbackQuery):
    """Solo llama al service."""
    user_id = callback.from_user.id
    with get_session() as session:
        service = BesitoService(session)
        balance = service.get_balance(user_id)
    await callback.message.edit_text(f"Tu saldo: {balance}")
```

## Ejemplo Incorrecto (PROHIBIDO)

```python
async def handle_balance(callback: CallbackQuery):
    user = await session.get(User, callback.from_user.id)  # ❌ DB en handler
    user.besitos += 10  # ❌ Lógica de negocio
    await session.commit()  # ❌ DB en handler
```

## Dominios y Sus Handlers

| Handler | Dominio |
|---------|---------|
| `common_handlers.py` | Sistema (/start, /help) |
| `admin_handlers.py` | Admin |
| `channel_handlers.py` | Channels |
| `vip_handlers.py`, `vip_user_handlers.py` | VIP |
| `anonymous_message_admin_handlers.py` | VIP |
| `free_channel_handlers.py` | Channels |
| `gamification_user_handlers.py`, `gamification_admin_handlers.py` | Gamificación |
| `broadcast_handlers.py` | Broadcast |
| `package_handlers.py` | Store |
| `mission_user_handlers.py`, `mission_admin_handlers.py` | Missions |
| `reward_admin_handlers.py` | Missions |
| `store_user_handlers.py`, `store_admin_handlers.py` | Store |
| `promotion_user_handlers.py`, `promotion_admin_handlers.py` | Promociones |
| `story_user_handlers.py`, `story_admin_handlers.py` | Narrative |
| `game_user_handlers.py` | Game |
| `trivia_discount_admin_handlers.py` | TriviaDiscount |
| `analytics_handlers.py` | Analytics |