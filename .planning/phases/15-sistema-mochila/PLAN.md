---
wave: 1
depends_on: []
files_modified:
  - bot.py
  - services/__init__.py
  - handlers/__init__.py
autonomous: false
---

<objective>
Implementar Sistema de Mochila (Inventario de Usuario) - Comando /mochila que muestra menú principal con categorías (Recompensas, Compras, VIP), permite ver lista de recompensas ganadas con besitos incluidos, lista de productos comprados, y envío de álbumes Telegram para paquetes comprados. Voz de Lucien en todas las interfaces.
</objective>

<read_first>
- docs/SISTEMA_MOCHILA.md (Diseño completo del sistema)
- services/reward_service.py (RewardService.get_user_reward_history)
- services/store_service.py (StoreService.get_user_orders)
- services/package_service.py (PackageService.deliver_package_to_user)
- services/vip_service.py (VIPService.get_user_active_subscriptions)
- handlers/__init__.py (Pattern for registering handlers)
- bot.py (Command registration pattern)
</read_first>

<requirements_addressed>
- REQ-001: Comando /mochila muestra menú principal con categorías
- REQ-002: Ver recompensas con besitos incluidos
- REQ-003: Ver compras de tienda
- REQ-004: Ver archivos de paquetes como álbum Telegram
- REQ-005: Voz de Lucien en todas las interfaces
</requirements_addressed>

<task>
<action>
Crear BackpackService en services/backpack_service.py con métodos:
- get_user_rewards(user_id, limit, offset) -> List[dict]
- get_user_purchases(user_id, limit, offset) -> List[dict]  
- get_user_vip_subscriptions(user_id) -> List[dict]
- get_backpack_summary(user_id) -> dict
- async deliver_package_content(bot, user_id, package_id) -> Tuple[bool, str]

Consultar UserRewardHistory, Order, OrderItem, Subscription existente.
Reutilizar RewardService, StoreService, PackageService, VIPService.
Seguir arquitectura del proyecto: lógica en services, NO en handlers.
</action>
<read_first>
- services/reward_service.py
- services/store_service.py
- services/package_service.py
- models/user.py (UserRewardHistory model)
- models/store.py (Order, OrderItem, StoreProduct models)
- models/vip.py (Subscription model)
</read_first>
<acceptance_criteria>
- services/backpack_service.py existe
- BackpackService tiene métodos get_user_rewards, get_user_purchases, get_user_vip_subscriptions, get_backpack_summary, deliver_package_content
- get_backpack_summary devuelve dict con keys: rewards_count, purchases_count, vip_count, besitos_balance
- Los métodos utilizan modelos SQLAlchemy existentes (no duplicación)
- Cada método tiene logger.info con formato "backpack_service | método | user_id= | resultado="
</acceptance_criteria>
</task>

<task>
<action>
Crear handler en handlers/backpack_handler.py con:
- cmd_mochila: Comando /mochila que muestra menú principal
- callback_rewards: Muestra lista de recompensas del usuario
- callback_purchases: Muestra lista de compras del usuario
- callback_vip: Muestra membresías VIP activas
- callback_reward_detail: Muestra detalle de recompensa seleccionada
- callback_deliver_package: Envía contenido de paquete como álbum

Usar InlineKeyboardMarkup para navegación.
Seguir patrón de arquitectura: handler solo enrutamiento, llama a BackpackService.
</action>
<read_first>
- handlers/admin/__init__.py (Pattern example)
- handlers/gamification/__init__.py (Callback pattern)
- utils/lucien_voice.py (Voz de Lucien messages)
</read_first>
<acceptance_criteria>
- handlers/backpack_handler.py existe
- Handler tiene comando /mochila registrado
- Callback data usa prefijo "backpack_" (backpack_rewards, backpack_purchases, etc.)
- Cada callback llama a BackpackService对应的方法
- Mensajes usan LucienVoice para consistencia
- Pagination implementada para listas > 10 items
</acceptance_criteria>
</task>

<task>
<action>
Agregar textos de mochila a utils/lucien_voice.py:
- backpack_summary(summary: dict) -> str (menú principal)
- backpack_rewards_list(rewards: list) -> str (lista recompensas)
- backpack_reward_detail(reward: dict) -> str (detalle recompensa)
- backpack_purchases_list(purchases: list) -> str (lista compras)
- backpack_vip_list(subscriptions: list) -> str (lista VIP)
- backpack_package_delivering(package_name, file_count) -> str (envío álbum)
- backpack_empty(type) -> str (estados vacíos)

Incluir HTML formatting y emojis según diseño en SISTEMA_MOCHILA.md.
</action>
<read_first>
- utils/lucien_voice.py
</read_first>
<acceptance_criteria>
- utils/lucien_voice.py contiene funciones con prefijo "backpack_"
- Mensajes incluyen 🎩 Lucien y HTML <b> para énfasis
- Voz elegante y misteriosa según especificación
</acceptance_criteria>
</task>

<task>
<action>
Registrar comando /mochila en bot.py:
- Importar router de handlers.backpack_handler
- Agregar router en include_router de bot
- Verificar que comando aparece en /help
</action>
<read_first>
- bot.py
</read_first>
<acceptance_criteria>
- bot.py importa backpack_handler
- Router registrado en bot
- /mochila responde al comando
</acceptance_criteria>
</task>

<task>
<action>
Agregar BackpackService a services/__init__.py exports:
- from .backpack_service import BackpackService
</action>
<read_first>
- services/__init__.py
</read_first>
<acceptance_criteria>
- services/__init__.py exporta BackpackService
- Import funciona sin errores
</acceptance_criteria>
</task>

<must_haves>
1. Comando /mochila muestra menú principal con categorías (Recompensas, Compras, VIP)
2. Ver recompensas: lista de recompensas ganadas con besitos incluidos
3. Ver compras: lista de productos comprados en la tienda  
4. Ver archivos: envío de álbumes Telegram para paquetes comprados
5. Voz de Lucien en todas las interfaces
</must_haves>

<verification>
- [ ] /mochila muestra menú con categorías y conteos
- [ ]backpack_rewards muestra lista paginada de recompensas
- [ ] backpack_purchases muestra lista de compras completadas
- [ ] backpack_vip muestra membresías VIP activas
- [ ] Selection de paquete entrega contenido como álbum Telegram
- [ ] Todos los mensajes usan voz de Lucien
- [ ] Paginación funciona para >10 items
- [ ] Estados vacíos muestran mensaje apropiado
</verification>
