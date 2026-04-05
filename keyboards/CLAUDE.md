# Keyboards

Teclados inline de Telegram.

## Archivos
- [inline_keyboards.py](inline_keyboards.py) - Definición de todos los teclados

## Tipos de Teclados

<!-- AUTO:KEYBOARDS -->
| Función | Descripción |
|---------|-------------|
| `main_menu_keyboard(is_vip)` | Menú principal de usuario con gamificación |
| `admin_menu_keyboard()` | Menú principal de administrador |
| `channel_management_keyboard()` | Menú de gestión de canales |
| `channel_type_keyboard()` | Selección de tipo de canal |
| `channel_actions_keyboard(channel_id, channel_type)` | Acciones disponibles para un canal |
| `tariffs_keyboard(tariffs, for_selection)` | Teclado con lista de tarifas |
| `wait_time_keyboard()` | Opciones de tiempo de espera |
| `confirmation_keyboard(confirm_callback, cancel_callback)` | Teclado de confirmación Sí/No |
| `back_keyboard(back_callback)` | Teclado con botón de volver |
| `cancel_keyboard()` | Teclado con botón de cancelar |
| `broadcast_back_keyboard(current_step)` | Teclado con botón de regresar al paso anterior durante broadcast |
| `vip_management_keyboard()` | Menú de gestión VIP |
| `token_actions_keyboard(token_id)` | Acciones para un token específico |
| `vip_area_keyboard()` | Menú de El Diván VIP (mensajes anónimos) |
| `anonymous_message_confirm_keyboard()` | Confirmar envío de mensaje anónimo |
| `anonymous_messages_menu_keyboard()` | Menú de gestión de mensajes anónimos (admin) |
| `anonymous_message_actions_keyboard(message_id)` | Acciones para un mensaje anónimo específico |
| `anonymous_messages_list_keyboard(messages)` | Lista de mensajes con estados |



## Uso
`from keyboards.inline_keyboards import main_menu_keyboard

await message.answer(
    "Texto",
    reply_markup=main_menu_keyboard()
)`

## Reglas
- Un teclado por contexto
- Mantener简洁 (no más de 3 filas)
- Siempre incluir "Atrás"

## Voice de Teclados
- Usar texto elegante
- "Regesar" no "Volver"
- "Confirmar" para acciones irreversibles
