# Sistema de Mochila (Inventario de Usuario)

## Documento de Diseño

---

## 1. Visión General

El sistema de **Mochila** permite a los visitantes consultar y gestionar las recompensas y productos adquiridos en su trayectoria con Diana. Este inventario centralizado proporciona una experiencia fluida donde el usuario puede:

- Visualizar todas las recompensas recibidas por completar misiones
- Consultar los productos comprados en la tienda
- Acceder a los archivos de los paquetes adquiridos
- Ver el detalle de besitos incluidos en cada recompensa

La mochila se convierte en el repositorio personal de cada visitante, un espacio donde se acumulan los tesoros ganados en el reino de Diana.

---

## 2. Flujos de Usuario

### 2.1 Flujo Principal: Consultar Mochila

```
Usuario → /mochila → Mostrar menú principal de mochila
                           │
                           ├── "Mis Recompensas" → Listado de recompensas por misión
                           │                         │
                           │                         └── Seleccionar recompensa → Ver detalle
                           │                                              │
                           │                                              └── (Si es paquete) → "Ver Archivos" → Enviar álbum
                           │
                           ├── "Mis Compras" → Listado de productos comprados
                           │                     │
                           │                     └── Seleccionar producto → Ver detalle
           │                                              │
           │                                              └── "Ver Archivos" → Enviar álbum
           │
           └── ← Volver al menú principal
```

### 2.2 Flujo: Ver Archivos de Paquete

```
Usuario → Selecciona paquete en recompensa/compra
         → Clic en "Ver Contenido"
         → PackageService.deliver_package_to_user()
         → Telegram MediaGroup (fotos/videos) + archivos individuales
```

### 2.3 Flujo: Consultar Detalle de Recompensa

```
Usuario → Selecciona recompensa de la lista
         → Mostrar información:
              • Nombre de la recompensa
              • Tipo (besitos/paquete/VIP)
              • Fecha de obtención
              • Besitos incluidos (si aplica)
              • Nombre de la misión asociada (si aplica)
```

---

## 3. Estructura de Datos

### 3.1 Modelos Existentes a Utilizar

El sistema reutiliza las siguientes tablas existentes:

| Modelo | Uso en Mochila |
|--------|---------------|
| `UserRewardHistory` | Historial de recompensas entregadas al usuario |
| `Reward` | Detalle de cada recompensa (tipo, besitos, paquete, VIP) |
| `Mission` | Misión asociada a la recompensa (información contextual) |
| `Order` | Órdenes de compra del usuario |
| `OrderItem` | Items específicos de cada orden |
| `StoreProduct` | Producto comprado (nombre, precio, paquete asociado) |
| `Package` | Paquete asociado al producto/recompensa |
| `PackageFile` | Archivos del paquete |
| `Subscription` | Suscripciones VIP activas del usuario |

### 3.2 Datos a Consultar

#### Recompensas (via `UserRewardHistory`)
```python
{
    "id": int,
    "reward_id": int,
    "reward_name": str,
    "reward_type": enum (BESITOS/PACKAGE/VIP_ACCESS),
    "besito_amount": int | None,
    "package_name": str | None,
    "package_id": int | None,
    "tariff_name": str | None,
    "mission_name": str | None,
    "delivered_at": datetime
}
```

#### Compras (via `Order` + `OrderItem` + `StoreProduct`)
```python
{
    "order_id": int,
    "product_name": str,
    "package_id": int | None,
    "package_name": str | None,
    "quantity": int,
    "total_price": int,
    "purchased_at": datetime,
    "status": enum (COMPLETED)
}
```

#### VIP Activo (via `Subscription` + `Tariff`)
```python
{
    "subscription_id": int,
    "tariff_name": str,
    "start_date": datetime,
    "end_date": datetime,
    "is_active": bool
}
```

---

## 4. Diseño de Interfaces

### 4.1 Menú Principal de Mochila

**Mensaje:**
```
🎩 <b>Lucien:</b>

<i>Permítame mostrarle los tesoros que Diana ha acumulado
en su mochila a lo largo de su viaje...</i>

📦 <b>Su Inventario</b>

<i>Seleccione una categoría para explorar:</i>
```

**Keyboard Inline:**
```
┌─────────────────────────────────┐
│ 🎁 Mis Recompensas (X)          │
├─────────────────────────────────┤
│ 🛒 Mis Compras (X)              │
├─────────────────────────────────┤
│ 👑 Membresías VIP (X)           │
├─────────────────────────────────┤
│ 💋 Besitos: X                   │
└─────────────────────────────────┘
```

### 4.2 Vista de Recompensas

**Mensaje:**
```
🎩 <b>Lucien:</b>

<i>Las recompensas que ha conquistado en su camino...</i>

📋 <b>Recompensas Obtenidas</b>
```

**Keyboard Inline (paginación):**
```
┌─────────────────────────────────┐
│ 🏆 Recompensa 1           05/03 │
├─────────────────────────────────┤
│ 🎁 Paquete Exclusivo      10/03 │
├─────────────────────────────────┤
│ 💋 +50 Besitos             15/03 │
├─────────────────────────────────┤
│ 👑 VIP 7 días              20/03 │
├─────────────────────────────────┤
│ [◀️]  1/3  [▶️]                │
├─────────────────────────────────┤
│ 🔙 Volver                       │
└─────────────────────────────────┘
```

### 4.3 Detalle de Recompensa

**Caso A: Recompensa de Besitos**
```
🎩 <b>Lucien:</b>

<i>Diana ha errado en su dirección besitos...</i>

💋 <b>Recompensa de Besitos</b>

🏷️ Nombre: Misión Diaria - Reaccionar 5 veces
📅 Obtenida: 05/03/2024 a las 14:30
💰 Besitos: +50

<i>Los besitos han sido acreditados a su cuenta.</i>
```

**Caso B: Recompensa de Paquete**
```
🎩 <b>Lucien:</b>

<i>El paquete espera ser descubierto...</i>

📦 <b>Recompensa de Paquete</b>

🏷️ Nombre: Sesión Fotos Premium
📅 Obtenida: 10/03/2024
💋 Besitos incluidos: 0

<i>¿Desea ver el contenido?</i>

[📂 Ver Contenido]  [🔙 Volver]
```

**Caso C: Recompensa VIP**
```
🎩 <b>Lucien:</b>

<i>Diana le ha abierto las puertas del círculo exclusivo...</i>

👑 <b>Recompensa VIP</b>

🏷️ Nombre: Acceso VIP - Tarifa Semanal
📅 Obtenida: 20/03/2024
⏱️ Duración: 7 días
📅 Vence: 27/03/2024
🔗 Enlace: [ Activar ]
```

### 4.4 Vista de Compras

**Mensaje:**
```
🎩 <b>Lucien:</b>

<i>Los tesoros que ha adquirido en la tienda de Diana...</i>

🛒 <b>Compras Realizadas</b>
```

**Keyboard Inline:**
```
┌─────────────────────────────────┐
│ 📦 Sesión Fotos #123      $99  │
│    📅 05/03/2024               │
├─────────────────────────────────┤
│ 📦 Video Exclusivo #124   $149 │
│    📅 12/03/2024               │
├─────────────────────────────────┤
│ ◀️ Volver                       │
└─────────────────────────────────┘
```

### 4.5 Entrega de Archivos (Álbum de Telegram)

El sistema reutiliza la lógica existente de `PackageService.deliver_package_to_user()`:

```python
async def deliver_package_to_user(bot, user_id, package_id):
    # Construir media groups (máx 10 items por grupo)
    media_groups = []
    for file in files:
        if file.file_type == "photo":
            media = InputMediaPhoto(media=file.file_id)
        elif file.file_type == "video":
            media = InputMediaVideo(media=file.file_id)
        # ... agrupar en grupos de 10
    
    # Enviar cada grupo como álbum
    for media_group in media_groups:
        await bot.send_media_group(chat_id=user_id, media=media_group)
```

**Mensaje introductorio antes del álbum:**
```
🎩 <b>Lucien:</b>

<i>Diana ha preparado el contenido...</i>

📦 <b>{package_name}</b>

<i>Entregando {file_count} archivo(s)...</i>
```

---

## 5. Integración con Servicios Existentes

### 5.1 Servicios a Integrar

| Servicio | Función | Integración |
|----------|---------|-------------|
| `RewardService` | Consultar historial de recompensas | `get_user_reward_history(user_id)` |
| `RewardService` | Obtener detalles de recompensa | `get_reward(reward_id)` |
| `StoreService` | Consultar órdenes del usuario | `get_user_orders(user_id)` |
| `StoreService` | Obtener producto de orden | `get_product(product_id)` |
| `PackageService` | Obtener archivos del paquete | `get_package_files(package_id)` |
| `PackageService` | Entregar paquete al usuario | `deliver_package_to_user()` |
| `VIPService` | Consultar membresías activas | `get_user_active_subscriptions(user_id)` |
| `BesitoService` | Consultar saldo actual | `get_balance(user_id)` |

### 5.2 Nuevo Servicio: BackpackService

Se creará un nuevo servicio `BackpackService` que centralice la lógica de inventario:

```python
class BackpackService:
    """Servicio para gestionar la mochila del usuario"""
    
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
    
    def get_user_rewards(self, user_id: int, limit: int = 20) -> List[dict]:
        """Obtiene el historial de recompensas del usuario"""
    
    def get_user_purchases(self, user_id: int, limit: int = 20) -> List[dict]:
        """Obtiene las compras del usuario"""
    
    def get_user_vip_subscriptions(self, user_id: int) -> List[dict]:
        """Obtiene las suscripciones VIP activas"""
    
    def get_backpack_summary(self, user_id: int) -> dict:
        """Obtiene resumen global de la mochila"""
    
    async def deliver_package_content(self, bot, user_id: int, package_id: int) -> Tuple[bool, str]:
        """Envía el contenido de un paquete al usuario"""
```

### 5.3 Patrón de Arquitectura

```
handlers/backpack_handler.py → services/backpack_service.py → models/
         │                                │
         └── Solo enrutamiento            └── Lógica de negocio
                                           └── Acceso a DB via models
```

---

## 6. Consideraciones de Arquitectura

### 6.1 Reglas del Proyecto a Respectar

1. **PROHIBIDO lógica en handlers** - El handler solo enrutará eventos y llamará a `BackpackService`
2. **PROHIBIDO acceso a DB fuera de models** - Usar modelos SQLAlchemy existentes
3. **PROHIBIDO duplicación entre servicios** - Reutilizar `RewardService`, `StoreService`, etc.
4. **Funciones máximo 50 líneas** - Dividir funciones largas
5. **Nombrar: verbo + contexto + resultado** - Ej: `get_user_backpack_summary`
6. **Logging** - Cada acción importante debe loguear: módulo, acción, user_id, resultado

### 6.2 Paginación

Para listas largas, implementar paginación con `InlineKeyboardButton`:
- Máximo 10 items por página
- Botones de navegación: `[◀️]` y `[▶️]`
- Callback data: `backpack_rewards_page_{page}`

### 6.3 Rate Limiting

- Reutilizar `ThrottlingMiddleware` existente
- Permitir acceso instantáneo a la mochila (no es una acción que abuse el sistema)
- Admin bypass ya configurado en el middleware existente

### 6.4 Caché (Futuro)

Considerar cachear el resumen de mochila durante la sesión:
- TTL: 5 minutos
- Clave: `backpack:{user_id}:summary`
- Invalidar al recibir nueva recompensa o compra

---

## 7. Propuesta de Implementación

### 7.1 Estructura de Archivos

```
services/backpack_service.py    # Nuevo servicio
handlers/backpack_handler.py    # Nuevo handler
utils/lucien_voice.py           # Agregar mensajes de mochila
```

### 7.2 Fases de Implementación

| Fase | Descripción | Entregable |
|------|-------------|------------|
| **Fase 1** | Crear `BackpackService` con métodos de consulta | `services/backpack_service.py` |
| **Fase 2** | Crear `backpack_handler.py` con comandos y callbacks | `handlers/backpack_handler.py` |
| **Fase 3** | Agregar textos de voz de Lucien | `utils/lucien_voice.py` |
| **Fase 4** | Registrar comandos en `bot.py` | Comando `/mochila` |
| **Fase 5** | Testing y ajustes | Pruebas E2E |

### 7.3 Detalle de Métodos

#### BackpackService.get_user_rewards()

```python
def get_user_rewards(self, user_id: int, limit: int = 20, offset: int = 0) -> List[dict]:
    """Obtiene el historial de recompensas con detalles."""
    db = self._get_db()
    
    history = db.query(UserRewardHistory).filter(
        UserRewardHistory.user_id == user_id
    ).order_by(desc(UserRewardHistory.delivered_at)).offset(offset).limit(limit).all()
    
    result = []
    for h in history:
        reward = h.reward  # Reload
        if not reward:
            continue
            
        item = {
            'history_id': h.id,
            'reward_id': reward.id,
            'reward_name': reward.name,
            'reward_type': reward.reward_type.value,
            'besito_amount': reward.besito_amount,
            'package_id': reward.package_id,
            'package_name': reward.package.name if reward.package else None,
            'tariff_id': reward.tariff_id,
            'tariff_name': reward.tariff.name if reward.tariff else None,
            'delivered_at': h.delivered_at
        }
        result.append(item)
    
    logger.info(f"backpack_service | get_user_rewards | user_id={user_id} | count={len(result)}")
    return result
```

#### BackpackService.get_user_purchases()

```python
def get_user_purchases(self, user_id: int, limit: int = 20, offset: int = 0) -> List[dict]:
    """Obtiene las compras completadas del usuario."""
    db = self._get_db()
    
    orders = db.query(Order).filter(
        Order.user_id == user_id,
        Order.status == OrderStatus.COMPLETED
    ).order_by(desc(Order.completed_at)).offset(offset).limit(limit).all()
    
    result = []
    for order in orders:
        for item in order.items:
            product = item.product
            result.append({
                'order_id': order.id,
                'product_id': product.id,
                'product_name': item.product_name,
                'package_id': product.package_id,
                'package_name': product.package.name if product.package else None,
                'quantity': item.quantity,
                'total_price': item.total_price,
                'purchased_at': order.completed_at
            })
    
    logger.info(f"backpack_service | get_user_purchases | user_id={user_id} | count={len(result)}")
    return result
```

#### BackpackService.deliver_package_content()

```python
async def deliver_package_content(self, bot, user_id: int, package_id: int) -> Tuple[bool, str]:
    """Envía el contenido de un paquete al usuario."""
    package = self.package_service.get_package(package_id)
    if not package:
        return False, LucienVoice.package_not_found()
    
    success, message = await self.package_service.deliver_package_to_user(
        bot=bot, user_id=user_id, package_id=package_id
    )
    
    logger.info(f"backpack_service | deliver_package_content | user_id={user_id} | package_id={package_id} | result={success}")
    return success, message
```

### 7.4 Keyboard Inline: Resumen de mochila

```python
def build_backpack_summary_keyboard(summary: dict) -> InlineKeyboardMarkup:
    """Construye el keyboard del menú principal de mochila."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎁 Mis Recompensas ({summary['rewards_count']})", 
                              callback_data="backpack_rewards")],
        [InlineKeyboardButton(text=f"🛒 Mis Compras ({summary['purchases_count']})", 
                              callback_data="backpack_purchases")],
        [InlineKeyboardButton(text=f"👑 Membresías VIP ({summary['vip_count']})", 
                              callback_data="backpack_vip")],
        [InlineKeyboardButton(text=f"💋 Besitos: {summary['besitos_balance']}", 
                              callback_data="backpack_balance")]
    ])
```

### 7.5 Comando /mochila

```python
@router.message(Command("mochila"))
async def cmd_mochila(message: Message, bot: Bot):
    """Muestra el menú principal de la mochila."""
    user_id = message.from_user.id
    
    # Obtener resumen
    backpack_service = BackpackService()
    summary = backpack_service.get_backpack_summary(user_id)
    
    # Construir mensaje y keyboard
    text = LucienVoice.backpack_summary(summary)
    keyboard = build_backpack_summary_keyboard(summary)
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    logger.info(f"backpack_handler | cmd_mochila | user_id={user_id} | result=shown")
```

### 7.6 Pruebas E2E Requeridas

1. **test_backpack_show_menu** - Verificar que el menú se muestra correctamente
2. **test_backpack_rewards_list** - Verificar listado de recompensas
3. **test_backpack_purchases_list** - Verificar listado de compras
4. **test_backpack_deliver_package** - Verificar entrega de archivos por álbum
5. **test_backpack_pagination** - Verificar paginación en listas largas
6. **test_backpack_empty_state** - Verificar mensaje cuando no hay items

---

## 8. Resumen

El sistema de **Mochila** proporciona una experiencia integrada para que los visitantes consulten sus recompensas, compras y membresías VIP. La implementación reutiliza los servicios existentes (`RewardService`, `StoreService`, `PackageService`, `VIPService`) y crea un nuevo `BackpackService` que centraliza la lógica de inventario.

La interfaz sigue la voz de Lucien con un diseño elegante y misterioso, utilizando键盘 inline para una navegación fluida. La entrega de archivos de paquetes reutiliza la lógica existente de `deliver_package_to_user()` que agrupa archivos en álbumes de Telegram.

---

*Documento generado para el proyecto Lucien Bot*
*Fecha: 2026-04-08*