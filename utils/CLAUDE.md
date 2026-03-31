# Utils

Utilidades y helpers del bot.

## Archivos
- [helpers.py](helpers.py) - Funciones helper
- [lucien_voice.py](lucien_voice.py) - Plantillas de mensajes

<!-- AUTO:FUNCTIONS -->
| Módulo | Función | Descripción |
|--------|---------|-------------|
| `helpers` | `get_current_time()` | Obtiene la hora actual en la zona horaria configurada |
| `helpers` | `format_datetime(dt, format_str)` | Formatea una fecha/hora |
| `helpers` | `escape_markdown(text)` | Escapa caracteres especiales de Markdown |
| `helpers` | `truncate_text(text, max_length)` | Trunca texto si excede el límite |
| `helpers` | `generate_invite_link(bot_username, token)` | Genera enlace de invitación con token |
| `helpers` | `is_admin(user_id)` | Verifica si un usuario es administrador |
| `helpers` | `parse_duration(text)` | 
    Parsea una duración en texto a días.
    Soporta: '30 dias', '1 mes', '1 año', etc.
     |

### LucienVoice

| Método | Descripción |
|--------|-------------|
| `greeting(user_name)` | Saludo principal para usuarios |
| `admin_greeting()` | Saludo para administradores |
| `vip_greeting(user_name)` | Saludo para usuarios VIP |
| `free_request_received(wait_minutes)` | Mensaje cuando se recibe solicitud al canal free |
| `free_access_approved(channel_name)` | Mensaje cuando se aprueba acceso al canal free |
| `free_request_cancelled()` | Mensaje cuando el usuario cancela su solicitud |
| `vip_activated(tariff_name, expiration_date)` | Mensaje cuando se activa membresía VIP |
| `vip_renewal_reminder(expiration_date)` | Recordatorio de renovación VIP (24h antes) |
| `vip_expired()` | Mensaje cuando expira la suscripción VIP |
| `vip_renewed()` | Mensaje cuando se renueva VIP |
| `token_invalid()` | Token inválido o inexistente |
| `token_used()` | Token ya utilizado |
| `token_expired()` | Token expirado |
| `token_generated(token_url, tariff_name)` | Token generado exitosamente |
| `admin_channel_registered(channel_name, channel_type)` | Canal registrado exitosamente |
| `admin_channel_list(channels)` | Lista de canales registrados |
| `admin_channel_deleted(channel_name)` | Canal eliminado |
| `admin_tariff_created(name, days, price)` | Tarifa creada exitosamente |
| `admin_tariff_list(tariffs)` | Lista de tarifas |
| `admin_pending_requests(count, requests)` | Lista de solicitudes pendientes |
| `admin_requests_cleared(count)` | Solicitudes aprobadas en lote |
| `admin_wait_time_updated(minutes)` | Tiempo de espera actualizado |
| `analytics_dashboard(stats)` | Dashboard de metricas para Custodios. |
| `export_ready(filename)` | Confirmacion de exportacion. |
| `export_no_data()` | No hay datos para exportar. |
| `analytics_access_denied()` | Acceso denegado a estadisticas. |
| `error_message(context)` | Mensaje de error general |
| `permission_error()` | Error de permisos |
| `not_admin_error()` | Usuario no es administrador |
| `farewell()` | Despedida |
| `coming_soon()` | Función en desarrollo |



## Reglas
- **NUNCA** lógica de negocio en utils
- Solo helpers puros (sin efectos secundarios)
- Voice de Lucien: siempre elegante y misterioso
