# 🎩 AGENTS.md - Documentación Técnica de Lucien Bot

> **Versión:** 1.0  
> **Última actualización:** Marzo 2026  
> **Autor:** Carlos Toek  
> **Para:** Señorita Kinky (Diana Hernández)

---

## 📋 Índice

1. [Visión General](#visión-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Estructura de Carpetas](#estructura-de-carpetas)
4. [Modelos de Datos](#modelos-de-datos)
5. [Servicios Principales](#servicios-principales)
6. [Handlers y Flujos](#handlers-y-flujos)
7. [Configuración](#configuración)
8. [Despliegue](#despliegue)
9. [Restricciones y Reglas](#restricciones-y-reglas)
10. [Guía de Contribución](#guía-de-contribución)

---

## 🎯 Visión General

**Lucien Bot** es un bot de Telegram diseñado para automatizar y gamificar la experiencia de la comunidad de Señorita Kinky. Actúa como un mayordomo virtual (Lucien) que gestiona:

- Sistema de puntos ("besitos")
- Tienda virtual con contenido exclusivo
- Sistema de misiones y recompensas
- Promociones comerciales con notificaciones
- Narrativa interactiva con arquetipos
- Gestión de membresías VIP

### Principios de Diseño

1. **Voz de marca:** Lucien habla en tercera persona, elegante, misterioso, nunca vulgar
2. **Gamificación:** Todo se convierte en juego (puntos, logros, misiones)
3. **Dualidad:** Diana (cercanía) vs Señorita Kinky (misterio/deseo)
4. **Escalabilidad:** Arquitectura modular por fases

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                      TELEGRAM API                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    LUCIEN BOT                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Router    │  │   FSM       │  │  Middleware         │  │
│  │   (aiogram) │  │   (estados) │  │  (logging, auth)    │  │
│  └──────┬──────┘  └─────────────┘  └─────────────────────┘  │
│         │                                                   │
│  ┌──────▼──────────────────────────────────────────────┐   │
│  │                    HANDLERS                          │   │
│  │  • User handlers  • Admin handlers  • Common         │   │
│  └──────┬──────────────────────────────────────────────┘   │
│         │                                                   │
│  ┌──────▼──────────────────────────────────────────────┐   │
│  │                    SERVICES                          │   │
│  │  • BesitoService  • VIPService    • StoreService    │   │
│  │  • MissionService • StoryService  • PromotionService│   │
│  └──────┬──────────────────────────────────────────────┘   │
│         │                                                   │
│  ┌──────▼──────────────────────────────────────────────┐   │
│  │                    MODELS (SQLAlchemy)               │   │
│  │  • User  • Package  • Mission  • StoryNode          │   │
│  │  • Order • Promotion • Archetype • Achievement      │   │
│  └──────┬──────────────────────────────────────────────┘   │
│         │                                                   │
│  ┌──────▼──────────────────────────────────────────────┐   │
│  │                    DATABASE                          │   │
│  │         SQLite (desarrollo) / PostgreSQL (prod)      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Estructura de Carpetas

```
lucien_bot/
├── bot.py                      # Punto de entrada principal
├── config/
│   ├── __init__.py
│   └── settings.py             # Configuración y variables de entorno
├── handlers/                   # Todos los manejadores de eventos
│   ├── __init__.py
│   ├── common_handlers.py      # Handlers comunes (start, help, etc.)
│   ├── admin_handlers.py       # Panel de administración principal
│   ├── channel_handlers.py     # Gestión de canales
│   ├── vip_handlers.py         # Gestión VIP
│   ├── free_channel_handlers.py # Canal gratuito
│   │
│   ├── gamification_user_handlers.py   # Fase 1: Gamificación (usuario)
│   ├── gamification_admin_handlers.py  # Fase 1: Gamificación (admin)
│   ├── broadcast_handlers.py           # Fase 1: Difusión masiva
│   │
│   ├── package_handlers.py             # Fase 2: Paquetes de contenido
│   │
│   ├── mission_user_handlers.py        # Fase 3: Misiones (usuario)
│   ├── mission_admin_handlers.py       # Fase 3: Misiones (admin)
│   ├── reward_admin_handlers.py        # Fase 3: Recompensas
│   │
│   ├── store_user_handlers.py          # Fase 4: Tienda (usuario)
│   ├── store_admin_handlers.py         # Fase 4: Tienda (admin)
│   │
│   ├── promotion_user_handlers.py      # Fase 5: Promociones (usuario)
│   ├── promotion_admin_handlers.py     # Fase 5: Promociones (admin)
│   │
│   ├── story_user_handlers.py          # Fase 6: Narrativa (usuario)
│   └── story_admin_handlers.py         # Fase 6: Narrativa (admin)
├── services/                   # Lógica de negocio
│   ├── __init__.py
│   ├── besito_service.py       # Gestión de besitos (puntos)
│   ├── vip_service.py          # Gestión de membresías VIP
│   ├── user_service.py         # Gestión de usuarios
│   ├── channel_service.py      # Gestión de canales
│   ├── package_service.py      # Gestión de paquetes
│   ├── mission_service.py      # Gestión de misiones
│   ├── reward_service.py       # Gestión de recompensas
│   ├── store_service.py        # Gestión de tienda
│   ├── promotion_service.py    # Gestión de promociones
│   ├── story_service.py        # Gestión de narrativa
│   ├── broadcast_service.py    # Difusión masiva
│   ├── daily_gift_service.py   # Regalo diario
│   └── scheduler_service.py    # Tareas programadas
├── models/                     # Modelos de base de datos
│   ├── __init__.py
│   ├── models.py               # Todos los modelos SQLAlchemy
│   └── database.py             # Configuración de conexión
├── keyboards/                  # Teclados inline
│   ├── __init__.py
│   └── inline_keyboards.py     # Definición de teclados
├── utils/                      # Utilidades
│   ├── __init__.py
│   ├── helpers.py              # Funciones auxiliares
│   └── lucien_voice.py         # Plantillas de voz de Lucien
├── .env.example                # Ejemplo de variables de entorno
├── .env                        # Variables de entorno (NO SUBIR A GIT)
├── requirements.txt            # Dependencias Python
├── railway.toml                # Configuración Railway
├── Procfile                    # Configuración de proceso
└── README.md                   # Documentación general
```

---

## 🗄️ Modelos de Datos

### Diagrama Entidad-Relación (Resumido)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    User     │────<│ BesitoTrans │     │   Package   │
└──────┬──────┘     └─────────────┘     └──────┬──────┘
       │                                        │
       │         ┌─────────────┐               │
       └────────<│   Mission   │               │
       │         └─────────────┘               │
       │                                        │
       │         ┌─────────────┐               │
       └────────<│    Order    │>──────────────┘
       │         └─────────────┘
       │
       │         ┌─────────────┐
       └────────<│ StoryProgress│
                 └──────┬──────┘
                        │
               ┌────────┴────────┐
               │                 │
        ┌──────▼──────┐   ┌──────▼──────┐
        │  StoryNode  │   │  Archetype  │
        └─────────────┘   └─────────────┘
```

### Modelos Principales

| Modelo | Descripción | Relaciones |
|--------|-------------|------------|
| `User` | Usuarios del bot | Transacciones, misiones, órdenes |
| `BesitoTransaction` | Historial de besitos | User |
| `Package` | Paquetes de contenido | Files, Products |
| `StoreProduct` | Productos en tienda | Package, Orders |
| `Order` | Órdenes de compra | User, Items |
| `Mission` | Misiones disponibles | UserProgress |
| `MissionProgress` | Progreso de misiones | User, Mission |
| `Promotion` | Promociones comerciales | Package, Interests |
| `PromotionInterest` | Intereses en promociones | User, Promotion |
| `StoryNode` | Nodos de narrativa | Choices |
| `StoryChoice` | Opciones de decisión | Node |
| `UserStoryProgress` | Progreso narrativo | User |
| `Archetype` | Arquetipos definidos | - |
| `StoryAchievement` | Logros de narrativa | UserAchievements |

---

## ⚙️ Servicios Principales

### BesitoService
```python
# Gestión del sistema de puntos
- credit_besitos()      # Acreditar besitos
- debit_besitos()       # Debitar besitos
- get_balance()         # Consultar saldo
- get_transaction_history()  # Historial
```

### VIPService
```python
# Gestión de membresías VIP
- add_vip_user()        # Agregar VIP
- remove_vip_user()     # Remover VIP
- is_user_vip()         # Verificar VIP
- get_vip_users()       # Listar VIPs
```

### StoreService
```python
# Gestión de tienda
- create_product()      # Crear producto
- get_available_products()  # Productos disponibles
- process_purchase()    # Procesar compra
- get_user_orders()     # Órdenes del usuario
```

### PromotionService
```python
# Gestión de promociones
- create_promotion()    # Crear promoción
- express_interest()    # Registrar interés
- notify_admins()       # Notificar a admins
- block_user()          # Bloquear usuario
```

### StoryService
```python
# Gestión de narrativa
- create_node()         # Crear nodo
- create_choice()       # Crear opción
- advance_to_node()     # Avanzar usuario
- calculate_archetype() # Calcular arquetipo
```

---

## 🎮 Handlers y Flujos

### Flujo de Usuario Nuevo

```
/start
  │
  ▼
┌─────────────────────┐
│  Bienvenida Lucien  │
│  "Bienvenido al     │
│   reino de Diana"   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Menú Principal    │
│  • Mi saldo         │
│  • Regalo diario    │
│  • Misiones         │
│  • Tienda           │
│  • Ofertas          │
│  • Fragmentos       │
└─────────────────────┘
```

### Flujo de Compra en Tienda

```
Tienda
  │
  ▼
Seleccionar Producto
  │
  ▼
Verificar Saldo ──> Saldo insuficiente ──> Cancelar
  │
  Saldo suficiente
  │
  ▼
Confirmar Compra
  │
  ▼
Debitar Besitos
  │
  ▼
Entregar Contenido
  │
  ▼
Notificar Admins
```

### Flujo "Me Interesa" (Promociones)

```
Ver Promoción
  │
  ▼
Click "Me Interesa"
  │
  ▼
Verificar no bloqueado
  │
  ▼
Registrar Interés
  │
  ├──> Notificar a TODOS los admins
  │
  └──> Mensaje usuario:
       "Diana ha sido notificada..."
```

---

## ⚙️ Configuración

### Variables de Entorno (.env)

```bash
# 🎩 Lucien Bot - Configuración

# Token del Bot de Telegram (obtener de @BotFather)
BOT_TOKEN=your_bot_token_here

# IDs de administradores (separados por comas)
# Obtener tu ID desde @userinfobot
ADMIN_IDS=123456789,987654321

# Base de datos
# SQLite para desarrollo:
DATABASE_URL=sqlite:///lucien_bot.db
# PostgreSQL para producción:
# DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Zona horaria
TIMEZONE=America/Mexico_City

# Username de la creadora (sin @)
CREATOR_USERNAME=dianita

# Canal VIP (ID o @username)
VIP_CHANNEL_ID=@divan_de_diana

# Canal gratuito (ID o @username)
FREE_CHANNEL_ID=@senorita_kinky_free
```

### Configuración de Railway (railway.toml)

Ver archivo `railway.toml` en raíz del proyecto.

---

## 🚀 Despliegue

### Opción 1: Railway (Recomendado)

1. Crear cuenta en [Railway](https://railway.app)
2. Conectar repositorio GitHub
3. Configurar variables de entorno en dashboard
4. Deploy automático en cada push

### Opción 2: Servidor VPS

```bash
# 1. Clonar repositorio
git clone https://github.com/carlostoek/lucienbot.git
cd lucienbot

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
nano .env  # Editar variables

# 5. Iniciar bot
python bot.py
```

### Opción 3: Docker (Próximamente)

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

---

## 🚫 Restricciones y Reglas

### Reglas de Negocio

1. **Besitos:**
   - No se pueden tener saldos negativos
   - Las transacciones son atómicas
   - Historial inmutable

2. **VIP:**
   - Solo admins pueden asignar/quitar VIP
   - Un usuario VIP tiene acceso a contenido exclusivo

3. **Promociones:**
   - Usuario bloqueado = no puede expresar interés
   - Un interés por usuario por promoción
   - Notificación a TODOS los admins

4. **Narrativa:**
   - Nodo VIP requiere membresía activa
   - Arquetipo determina contenido disponible
   - Progreso se guarda automáticamente

### Reglas de Código

1. **Nunca hardcodear:**
   - IDs de usuarios
   - Tokens
   - Configuraciones

2. **Siempre usar:**
   - Variables de entorno para secrets
   - Transacciones en BD
   - Logging en operaciones críticas

3. **Voz de Lucien:**
   - Tercera persona siempre
   - Elegante, nunca vulgar
   - "Diana" como figura central
   - "Visitantes" no "usuarios"
   - "Custodios" no "admins"

### Seguridad

1. **Validar siempre:**
   - IDs de callback
   - Permisos de admin
   - Saldos antes de transacciones

2. **Prevenir:**
   - SQL Injection (usar ORM)
   - Race conditions (transacciones)
   - Spam (rate limiting implícito)

---

## 🤝 Guía de Contribución

### Para Agregar una Nueva Fase

1. **Modelos:** Agregar a `models/models.py`
2. **Servicio:** Crear en `services/nueva_fase_service.py`
3. **Handlers:**
   - Usuario: `handlers/nueva_fase_user_handlers.py`
   - Admin: `handlers/nueva_fase_admin_handlers.py`
4. **Teclados:** Actualizar `keyboards/inline_keyboards.py`
5. **Bot:** Registrar routers en `bot.py`
6. **Init:** Exportar en `handlers/__init__.py`

### Convenciones de Código

```python
# Nombres de funciones: snake_case
async def process_user_action()

# Nombres de clases: PascalCase
class BesitoService:

# Constantes: UPPER_CASE
MAX_BESITOS_PER_DAY = 100

# Docstrings obligatorios
def funcion():
    """
    Descripción breve.
    
    Args:
        param1: Descripción
        
    Returns:
        Descripción del retorno
    """
```

### Testing (Futuro)

```python
# tests/test_besito_service.py
def test_credit_besitos():
    service = BesitoService()
    initial = service.get_balance(123)
    service.credit_besitos(123, 50)
    assert service.get_balance(123) == initial + 50
```

---

## 📚 Recursos Adicionales

- [Documentación aiogram](https://docs.aiogram.dev/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Railway Docs](https://docs.railway.app/)
- [Brief de Marca](./brief.md)

---

## 📝 Changelog

### v1.0 (Marzo 2026)
- Fase 1: Gamificación (besitos, misiones, regalo diario)
- Fase 2: Paquetes de contenido
- Fase 3: Misiones y recompensas
- Fase 4: Tienda virtual
- Fase 5: Promociones y "Me Interesa"
- Fase 6: Narrativa con arquetipos

---

**Hecho con 💋 para Diana (Señorita Kinky)**
