# Users Domain

Gestión de perfiles de usuarios.

## Services
- [user_service.py](../user_service.py) - Gestión de usuarios

## Handlers
- [common_handlers.py](../../handlers/common_handlers.py) - start, help
- [admin_handlers.py](../../handlers/admin_handlers.py) - Panel admin

## Modelos
- `User` - Usuario completo
  - `id`, `telegram_id`
  - `username`, `full_name`
  - `besitos_balance`
  - `vip_expiry`
  - `created_at`, `updated_at`

## UserService API
```python
- get_or_create_user(telegram_id, username, full_name)  # Obtener o crear
- get_user(user_id)                    # Obtener por ID
- get_user_by_telegram(telegram_id)   # Obtener por telegram_id
- update_user(user_id, **kwargs)       # Actualizar
- get_all_users()                      # Listar todos
```

## Registro de Usuario Nuevo
```
/start
  → Bienvenida Lucien ("Bienvenido al reino de Diana")
  → Mostrar menú principal
  → Guardar usuario si no existe
```

## Reglas
- Un usuario por telegram_id
- Crear automáticamente en /start
- Nunca eliminar datos de usuario

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos existentes en user_service.py
