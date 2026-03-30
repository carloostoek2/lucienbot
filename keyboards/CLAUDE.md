# Keyboards

Teclados inline de Telegram.

## Archivos
- [inline_keyboards.py](inline_keyboards.py) - Definición de todos los teclados

## Tipos de Teclados

| Teclado | Descripción |
|---------|-------------|
| `main_menu_keyboard` | Menú principal |
| `back_keyboard` | Botón atrás |
| `confirm_keyboard` | Sí/No para confirmaciones |
| `store_keyboard` | Navegación de tienda |
| `mission_keyboard` | Missions |
| `promotion_keyboard` | Promociones |

## Uso
```python
from keyboards.inline_keyboards import main_menu_keyboard

await message.answer(
    "Texto",
    reply_markup=main_menu_keyboard()
)
```

## Reglas
- Un teclado por contexto
- Mantener简洁 (no más de 3 filas)
- Siempre incluir "Atrás"

## Voice de Teclados
- Usar texto elegante
- "Regesar" no "Volver"
- "Confirmar" para acciones irreversibles
