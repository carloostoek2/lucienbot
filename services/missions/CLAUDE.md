# Missions Domain

Tareas configurables por admin con recompensas automáticas al completarse.

## Services
- `mission_service.py` — Misiones y progreso
- `reward_service.py` — Recompensas y entrega

## Handlers
- `mission_user_handlers.py` — Usuario: ver misiones, reclamar recompensa
- `mission_admin_handlers.py` — Admin: crear/editar/listar misiones
- `reward_admin_handlers.py` — Admin: crear recompensas (besitos/paquete/VIP)

## Modelos clave
- `Mission` — Definición: nombre, tipo, target, reward_id. Tipos: REACTION_COUNT, DAILY_GIFT_STREAK, DAILY_GIFT_TOTAL, STORE_PURCHASE, VIP_ACTIVE
- `UserMissionProgress` — Progreso por usuario/misión. NO "MissionProgress"
- `Reward` — Recompensa: besitos, paquete o acceso VIP. Tipos: BESITOS, PACKAGE, VIP_ACCESS
- `UserRewardHistory` — Log de entregas

## MissionService API
```python
# Misiones
create_mission(name, description, mission_type, target_value, reward_id,
              frequency) -> Mission  # frequency: ONE_TIME o RECURRING
get_mission(mission_id) -> Mission
get_all_missions(active_only=True) -> list[Mission]
get_available_missions() -> list[Mission]  # Disponibles para el usuario
update_mission(mission_id, **kwargs) -> bool
delete_mission(mission_id) -> bool

# Progreso
get_or_create_progress(user_id, mission_id) -> UserMissionProgress
get_user_progress(user_id, mission_id) -> UserMissionProgress
get_user_all_progress(user_id) -> list[UserMissionProgress]
get_user_active_missions(user_id) -> list[dict]
increment_progress(user_id, mission_type, value) -> None  # Auto-incrementa todas las missions de ese tipo
set_progress(user_id, mission_id, value) -> UserMissionProgress
```

## RewardService API
```python
# Creación por tipo
create_reward_besitos(name, description, besito_amount) -> Reward
create_reward_package(name, description, package_id) -> Reward
create_reward_vip(name, description, tariff_id, duration_days) -> Reward

# CRUD
get_reward(reward_id) -> Reward
get_all_rewards(active_only=True) -> list[Reward]
get_rewards_by_type(reward_type) -> list[Reward]
update_reward(reward_id, **kwargs) -> bool
delete_reward(reward_id) -> bool

# Entrega (async, llama internamente a BesitoService / PackageService / VIPService)
deliver_reward(user_id, reward_id, mission_id=None) -> bool

# Historial y stats
log_reward_delivery(user_id, reward_id, mission_id, details) -> None
get_user_reward_history(user_id, limit=20) -> list[UserRewardHistory]
get_reward_stats(reward_id) -> dict
```

## Flujo de Misión

```
Admin crea Mission + Reward asociada
    → Admin configura tipo, target, reward
Admin o sistema detecta progreso del visitante
    → MissionService.increment_progress() o set_progress()
    → Si current_value >= target_value → is_completed = True
    → Handler ofrece "Reclamar recompensa"
    → RewardService.deliver_reward()
        → BESITOS: BesitoService.credit_besitos()
        → PACKAGE: PackageService.deliver_package_to_user()
        → VIP_ACCESS: VIPService (genera token + subscription)
```

## Reglas de Negocio
- Missions de tipo RECURRING se reinician tras completar (progreso se resetea)
- `deliver_reward()` es idempotente en la lógica de entrega
- Si la recompensa es de tipo PACKAGE: stock del paquete se decrementa (reward_stock)
- `increment_progress()` es el mecanismo preferido para incrementar — itera todas las missions activas del tipo dado

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Usar `increment_progress()` con `mission_type` para auto-incrementar todas las missions del mismo tipo
4. Para entregar recompensa: siempre usar `RewardService.deliver_reward()`, no llamar servicios internos directamente
