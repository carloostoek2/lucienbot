# Quick Task 260405-hje: Notificación admin al recibir mensaje anónimo VIP

**Date:** 2026-04-05
**Status:** Ready for execution

---

## Goal

Cuando un usuario VIP envía un mensaje anónimo, notificar al administrador (Diana) con un mensaje que incluya botones para ver el mensaje o volver al menú admin.

---

## Tasks

### Task 1: Crear función de teclado para notificación admin

**Files:** `keyboards/inline_keyboards.py`
**Action:**
- Agregar función `admin_anonymous_notification_keyboard(message_id: int)` que retorne un InlineKeyboardMarkup con:
  - Botón "Ver mensaje" con callback_data `anon_view_{message_id}`
  - Botón "Cerrar" con callback_data `back_to_admin`

**Verify:**
- La función existe y está correctamente definida
- Los callback_data siguen el formato existente del proyecto
- Se importa correctamente desde handlers

**Done:**
- [ ] Función agregada a inline_keyboards.py
- [ ] Callbacks verificados contra anonymous_message_admin_handlers.py

---

### Task 2: Enviar notificación al admin después de enviar mensaje anónimo

**Files:** `handlers/vip_user_handlers.py`
**Action:**
- Después de enviar el mensaje anónimo (línea 258-274), agregar código para:
  1. Importar `bot_config` de `config.settings`
  2. Iterar sobre `bot_config.ADMIN_IDS`
  3. Enviar mensaje a cada admin con el texto y teclado definidos
  4. Manejar excepciones silenciosamente (no fallar si no se puede notificar)

**Texto de notificación:**
```
🎩 <b>Lucien:</b>

Alguien ha buscado su atención de manera anónima
```

**Verify:**
- La notificación se envía después de que el mensaje se guarda exitosamente
- Se usa el message.id retornado por send_message
- Las excepciones son capturadas y logueadas, no propagadas
- El flujo del usuario no se interrumpe si falla la notificación

**Done:**
- [ ] Import de bot_config agregado
- [ ] Código de notificación agregado después de anon_service.send_message()
- [ ] Manejo de excepciones implementado
- [ ] Logging de errores incluido

---

## Implementation Notes

1. **Botón "Ver mensaje":** Usa el callback `anon_view_{message_id}` que ya está implementado en `anonymous_message_admin_handlers.py:210` (función `view_anonymous_message`)

2. **Botón "Cerrar":** Usa el callback `back_to_admin` que ya está implementado en `admin_handlers.py` como menú principal de admin

3. **Importante:** La notificación debe enviarse DESPUÉS de confirmar que el mensaje se guardó correctamente, pero el fallo en el envío de la notificación NO debe afectar la experiencia del usuario VIP

4. **Patrón de código a seguir:**
   ```python
   # Notificar a admins (no fallar si no se puede notificar)
   from config.settings import bot_config
   from keyboards.inline_keyboards import admin_anonymous_notification_keyboard

   for admin_id in bot_config.ADMIN_IDS:
       try:
           await callback.bot.send_message(
               chat_id=admin_id,
               text="🎩 <b>Lucien:</b>\n\nAlguien ha buscado su atención de manera anónima",
               reply_markup=admin_anonymous_notification_keyboard(message.id),
               parse_mode="HTML"
           )
       except Exception as e:
           logger.warning(f"No se pudo notificar al admin {admin_id}: {e}")
   ```
