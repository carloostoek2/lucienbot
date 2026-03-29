# 🎩 Lucien Bot - Guardián de los Secretos de Diana

Bot de Telegram para la gestión automatizada de canales Free y VIP, con una personalidad elegante y misteriosa inspirada en un mayordomo sofisticado.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Aiogram](https://img.shields.io/badge/Aiogram-3.4.1-green.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.28-orange.svg)

## ✨ Características

### 🚪 Canal Free (Vestíbulo)
- **Aceptación automática** con tiempo de espera configurable
- **Notificaciones** al usuario sobre el estado de su solicitud
- **Aprobación en lote** de solicitudes pendientes
- **Gestión de múltiples canales** Free simultáneos

### 👑 Canal VIP (Círculo Exclusivo)
- **Tokens de acceso** de un solo uso
- **Tarifas configurables** (nombre, duración, precio)
- **Recordatorios automáticos** 24h antes del vencimiento
- **Expulsión automática** al vencer la suscripción
- **Auditoría completa** de tokens generados y utilizados

### 🎩 Panel de Administración
- **Interfaz conversacional** con botones inline
- **Gestión de canales** (registro, configuración, eliminación)
- **Gestión de tarifas VIP** (crear, editar, desactivar)
- **Generación de tokens** con enlaces listos para compartir
- **Monitoreo de suscriptores** activos

### 🎭 Personalidad de Lucien
- **Voz elegante y misteriosa** en todos los mensajes
- **Referencias a Diana** en las comunicaciones
- **Tono de mayordomo sofisticado** sin ser condescendiente
- **Experiencia inmersiva** para los usuarios

## 📋 Requisitos

- Python 3.9 o superior
- Token de bot de Telegram (obtener de [@BotFather](https://t.me/BotFather))
- Permisos de administrador en los canales a gestionar

## 🚀 Instalación

### 1. Clonar o descargar el proyecto

```bash
cd lucien_bot
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar el archivo `.env` con tus configuraciones:

```env
BOT_TOKEN=tu_token_de_bot_aqui
ADMIN_IDS=tu_id_de_telegram
DATABASE_URL=sqlite:///lucien_bot.db
TIMEZONE=America/Mexico_City
```

### 5. Iniciar el bot

```bash
python bot.py
```

## ⚙️ Configuración de Canales

### Configurar Canal Free

1. **Agregar el bot como administrador** del canal:
   - Gestionar chat ✅
   - Añadir miembros ✅
   - Aprobar solicitudes ✅

2. **Desactivar invitaciones** en el canal (Configuración > Permisos > Solicitar acceso)

3. **Registrar el canal** desde el panel de administración:
   - Reenviar cualquier mensaje del canal al bot
   - Seleccionar tipo "Vestíbulo (Free)"
   - Configurar tiempo de espera (2, 3, 5 minutos o personalizado)

### Configurar Canal VIP

1. **Agregar el bot como administrador** del canal (mismos permisos que Free)

2. **Registrar el canal** desde el panel:
   - Seleccionar tipo "Círculo Exclusivo (VIP)"

3. **Crear tarifas VIP**:
   - Nombre (ej: "Mensual", "Trimestral")
   - Duración en días
   - Precio

4. **Generar tokens** para compartir con usuarios

## 📁 Estructura del Proyecto

```
lucien_bot/
├── bot.py                    # Punto de entrada principal
├── config/
│   ├── __init__.py
│   └── settings.py           # Configuración del bot
├── handlers/
│   ├── __init__.py
│   ├── common_handlers.py    # Comandos básicos
│   ├── admin_handlers.py     # Panel de administración
│   ├── channel_handlers.py   # Gestión de canales
│   ├── vip_handlers.py       # Gestión VIP
│   └── free_channel_handlers.py  # Solicitudes Free
├── keyboards/
│   ├── __init__.py
│   └── inline_keyboards.py   # Teclados inline
├── models/
│   ├── __init__.py
│   ├── database.py           # Configuración de BD
│   └── models.py             # Modelos SQLAlchemy
├── services/
│   ├── __init__.py
│   ├── channel_service.py    # Lógica de canales
│   ├── vip_service.py        # Lógica VIP
│   ├── user_service.py       # Lógica de usuarios
│   └── scheduler_service.py  # Tareas programadas
├── utils/
│   ├── __init__.py
│   ├── lucien_voice.py       # Mensajes de Lucien
│   └── helpers.py            # Funciones auxiliares
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 🗄️ Modelos de Datos

### User
- `telegram_id`: ID único de Telegram
- `username`, `first_name`, `last_name`: Información del perfil
- `role`: admin o user

### Channel
- `channel_id`: ID del canal en Telegram
- `channel_name`: Nombre del canal
- `channel_type`: free o vip
- `wait_time_minutes`: Tiempo de espera (solo Free)

### Tariff
- `name`: Nombre de la tarifa
- `duration_days`: Duración en días
- `price`: Precio (texto libre)
- `is_active`: Estado de la tarifa

### Token
- `token_code`: Código único del token
- `tariff_id`: Tarifa asociada
- `status`: active, used, expired
- `redeemed_by_id`: Usuario que canjeó el token

### Subscription
- `user_id`: Usuario suscrito
- `channel_id`: Canal VIP
- `token_id`: Token utilizado
- `end_date`: Fecha de vencimiento
- `is_active`: Estado de la suscripción

### PendingRequest
- `user_id`: Usuario solicitante
- `channel_id`: Canal solicitado
- `scheduled_approval_at`: Fecha de aprobación programada
- `status`: pending, approved, cancelled

## 🔧 Comandos Disponibles

### Usuarios
- `/start` - Iniciar conversación con Lucien
- `/help` - Mostrar ayuda

### Administradores
- Panel completo accesible desde `/start`
- Gestión de canales, tarifas, tokens y usuarios

## 🔄 Flujos del Sistema

### Canal Free
1. Usuario solicita acceso al canal
2. Bot intercepta la solicitud
3. Bot notifica al usuario con tiempo de espera
4. Temporizador inicia
5. Al vencer el tiempo, bot aprueba automáticamente
6. Bot notifica al usuario del acceso concedido

### Canal VIP
1. Administrador genera token vinculado a tarifa
2. Usuario recibe enlace con token
3. Usuario hace clic en el enlace
4. Bot valida el token
5. Bot activa suscripción con fecha de vencimiento
6. 24h antes del vencimiento: recordatorio
7. Al vencer: expulsión automática y notificación

## 🛡️ Seguridad

- Tokens de un solo uso por defecto
- Validación de administradores por ID
- Base de datos SQLite local (fácil migración a PostgreSQL)
- Logs de auditoría de todas las acciones

## 📝 Personalización

### Mensajes de Lucien
Editar `utils/lucien_voice.py` para personalizar:
- Saludos y despedidas
- Mensajes de error
- Confirmaciones
- Notificaciones

### Zona Horaria
Cambiar en `.env`:
```env
TIMEZONE=Europe/Madrid
```

## 🐛 Solución de Problemas

### El bot no responde
- Verificar que `BOT_TOKEN` es correcto
- Verificar que el bot está ejecutándose
- Revisar logs en `lucien_bot.log`

### No puede aprobar solicitudes
- Verificar permisos del bot en el canal
- Debe tener: Gestionar chat, Añadir miembros, Aprobar solicitudes

### Tokens no funcionan
- Verificar que la tarifa está activa
- Verificar que el token no ha expirado
- Verificar que el token no fue usado previamente

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:
1. Fork el repositorio
2. Crear una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abrir un Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT.

---

<p align="center">
  <i>"Diana observa... y Lucien sirve."</i>
</p>
