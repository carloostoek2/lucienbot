# Missions Domain

Tareas, progreso y completado de misiones.

## Services
- [mission_service.py](../mission_service.py) - Misiones
- [reward_service.py](../reward_service.py) - Recompensas

## Handlers
- [mission_user_handlers.py](../../handlers/mission_user_handlers.py) - Usuario
- [mission_admin_handlers.py](../../handlers/mission_admin_handlers.py) - Admin
- [reward_admin_handlers.py](../../handlers/reward_admin_handlers.py) - Admin recompensas

## Modelos
- `Mission` - Misiones disponibles
- `MissionProgress` - Progreso por usuario
- `Reward` - Recompensas disponibles

## MissionService API
```python
- create_mission(...)           # Crear misión
- assign_mission(user_id, mission_id)  # Asignar
- update_progress(user_id, mission_id, progress)  # Actualizar
- complete_mission(user_id, mission_id)  # Completar
- get_user_missions(user_id)   # Misiones del usuario
```

## RewardService API
def create_reward(...) -> 'Reward': ...
def claim_reward(user_id: int, reward_id: int) -> None: ...
def get_available_rewards(user_id: int) -> list['Reward']: ...

## Reglas de Negocio
- Una misión por usuario a la vez (opcional según diseño)
- Progreso persistente
- Recompensas atomicidad en entrega

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos existentes en mission_service.py
