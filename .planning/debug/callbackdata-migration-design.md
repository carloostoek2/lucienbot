# Diseño: CallbackData para Gamification User Handlers

## Contexto
El dominio más pequeño del proyecto con **1 instancia** de callback parsing frágil:
- `handlers/gamification_user_handlers.py` línea 198

## Patrón Frágil Actual (líneas 192-208)

```python
@router.callback_query(F.data.startswith("react_"))
async def handle_reaction(callback: CallbackQuery):
    user = callback.from_user

    # Parsear datos: react_{broadcast_id}_{emoji_id}
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer("Error en la reacción", show_alert=True)
        return

    try:
        broadcast_id = int(parts[1])
        emoji_id = int(parts[2])
    except ValueError:
        await callback.answer("Error en la reacción", show_alert=True)
        return
```

## Migración Propuesta: CallbackData

### Paso 1: Definir CallbackData en keyboards/callback_data.py (nuevo archivo)

```python
"""
Centralized CallbackData definitions for Lucien Bot.
"""
from aiogram.filters.callback_data import CallbackData


class ReactionCallback(CallbackData, prefix="react"):
    """Reacciones a mensajes broadcast: react_{broadcast_id}_{emoji_id}"""
    broadcast_id: int
    emoji_id: int
```

### Paso 2: Actualizar keyboards que usan este callback

En `keyboards/inline_keyboards.py` - función que genera los botones de reacción:

```python
from keyboards.callback_data import ReactionCallback

def reactions_keyboard(broadcast_id: int, emojis: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """Genera teclado de reacciones para un broadcast."""
    buttons = []
    for emoji_id, emoji_char in emojis:
        buttons.append([InlineKeyboardButton(
            text=emoji_char,
            callback_data=ReactionCallback(
                broadcast_id=broadcast_id,
                emoji_id=emoji_id
            ).pack()
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

**Keyboard caller** debe usar:
```python
callback_data=ReactionCallback(broadcast_id=broadcast.id, emoji_id=emoji.id).pack()
```

En vez de:
```python
callback_data=f"react_{broadcast.id}_{emoji.id}"
```

### Paso 3: Migrar el handler (handlers/gamification_user_handlers.py)

```python
from keyboards.callback_data import ReactionCallback


@router.callback_query(ReactionCallback.filter())
async def handle_reaction(callback: CallbackQuery, callback_data: ReactionCallback):
    """Maneja las reacciones a mensajes de broadcast"""
    user = callback.from_user
    broadcast_id = callback_data.broadcast_id
    emoji_id = callback_data.emoji_id

    # Deduplication key para prevención de duplicates
    dedup_key = f"{user.id}:{broadcast_id}:{emoji_id}"
    
    # Verificar si ya procesando este callback
    if dedup_key in _reaction_callbacks_being_processed:
        logger.debug(f"Callback duplicado ignorado: {dedup_key}")
        await callback.answer("Procesando tu reacción...", show_alert=False)
        return

    _reaction_callbacks_being_processed.add(dup_key)

    try:
        broadcast_service = BroadcastService()
        reaction = await broadcast_service.check_and_register_reaction(
            broadcast_id=broadcast_id,
            user_id=user.id,
            emoji_id=emoji_id,
            username=user.username,
            bot=callback.bot
        )
        
        if reaction:
            emoji_char = reaction.get('emoji_char', '💋')
            besitos = reaction.get('besitos_awarded', 0)
            # ... resto del código sin cambios
    finally:
        _reaction_callbacks_being_processed.discard(dedup_key)
```

## Beneficios de la Migración

| Antes (Frágil) | Después (Type-Safe) |
|----------------|------------------|
| `int(parts[1])` puede fallar con ValueError | `callback_data.broadcast_id` siempre es int |
| Magic string `"react_"` en dos lugares | Definición única |
| No hay validación hasta runtime | Validación en definition |
| Error silencioso en producción | Filtro no matchea si formato incorrecto |

## Verificación Arquitectónica Requerida

- [ ] Handler llama exactamente 1 service
- [ ] SIN lógica de negocio en handler
- [ ] SIN acceso a DB directo
- [ ] CallbackData definido en keyboards/ no en handlers/
- [ ] Logging presente