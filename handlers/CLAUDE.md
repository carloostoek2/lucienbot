# Handlers

Solo enrutan eventos desde Telegram. **SIN lógica de negocio, SIN acceso a DB.**

## Estructura

```
handlers/
├── common_handlers.py          # start, help, etc.
├── admin_handlers.py           # Panel admin principal
├── vip_handlers.py            # Gestión VIP
├── channel_handlers.py         # Gestión canales
├── free_channel_handlers.py    # Canal gratuito
│
├── gamification_user_handlers.py   # Besitos (usuario)
├── gamification_admin_handlers.py  # Besitos (admin)
├── broadcast_handlers.py           # Difusión masiva
│
├── package_handlers.py             # Paquetes
│
├── mission_user_handlers.py        # Misiones (usuario)
├── mission_admin_handlers.py       # Misiones (admin)
├── reward_admin_handlers.py        # Recompensas
│
├── store_user_handlers.py          # Tienda (usuario)
├── store_admin_handlers.py         # Tienda (admin)
│
├── promotion_user_handlers.py      # Promociones (usuario)
├── promotion_admin_handlers.py     # Promociones (admin)
│
└── story_user_handlers.py          # Narrativa (usuario)
└── story_admin_handlers.py         # Narrativa (admin)
```

## Reglas de Handlers

1. **UN service** por handler
2. **SIN lógica** de negocio
3. **SIN acceso** directo a DB
4. **Logging** de eventos recibidos

## Ejemplo Correcto

```python
async def handle_besitos_balance(callback: CallbackQuery, service: BesitoService):
    """Solo llama al service, no tiene lógica."""
    user_id = callback.from_user.id
    balance = await service.get_balance(user_id)
    await callback.message.edit_text(f"Tu saldo: {balance}")
```

## Ejemplo Incorrecto (PROHIBIDO)

```python
async def handle_besitos_balance(callback: CallbackQuery):
    # ❌ Lógica en handler
    user = await session.get(User, callback.from_user.id)
    user.besitos += 10  # ❌ Lógica de negocio
    await session.commit()  # ❌ Acceso a DB
```
