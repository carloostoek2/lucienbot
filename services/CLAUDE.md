# Services

Lógica de negocio por dominio. Un service = un dominio (no fragmentar).

## Servicios Disponibles

<!-- AUTO:SERVICES -->
| Service | Dominio | Archivo | Métodos |
|---------|---------|---------|--------|
| `ChannelService` | Channels | `channel_service.py` | close, create_channel, get_channel_by_id, get_channel_by_db_id, get_all_channels, +13 más |
| `VIPService` | VIP | `vip_service.py` | close, create_tariff, get_tariff, get_all_tariffs, update_tariff, +18 más |
| `UserService` | Users | `user_service.py` | create_user, get_user, get_or_create_user, get_all_users, get_admins, +4 más |
| `SchedulerService` | System | `scheduler_service.py` | start, stop |
| `BesitoService` | Gamificación | `besito_service.py` | close, get_or_create_balance, get_balance, get_balance_with_stats, credit_besitos, +6 más |
| `BroadcastService` | Broadcast | `broadcast_service.py` | create_reaction_emoji, get_reaction_emoji, get_reaction_emoji_by_emoji, get_all_emojis, update_emoji_value, +12 más |
| `DailyGiftService` | Gamificación | `daily_gift_service.py` | get_config, update_config, is_active, get_gift_amount, get_last_claim, +5 más |
| `PackageService` | Store | `package_service.py` | create_package, add_file_to_package, get_package, get_all_packages, get_available_packages_for_store, +11 más |
| `MissionService` | Missions | `mission_service.py` | close, create_mission, get_mission, get_all_missions, get_available_missions, +10 más |
| `RewardService` | Missions | `reward_service.py` | create_reward_besitos, create_reward_package, create_reward_vip, get_reward, get_all_rewards, +7 más |
| `StoreService` | Store | `store_service.py` | close, create_product, get_product, get_all_products, get_available_products, +15 más |



## Reglas de Services

- Un service es dueño de su dominio
- Centraliza toda la lógica del dominio
- **PROHIBIDO**: lógica duplicada en múltiples services
- **PROHIBIDO**: acceso a DB directo (usar models)
- Funciones máximo 50 líneas
- Logging en cada acción importante

## Acceso a DB

Los services NO acceden a DB directamente. Usan models:

`from models import User, BesitoTransaction

# Correcto
user = await session.get(User, user_id)
# Incorrecto
await session.execute(text("SELECT * FROM users"))`
