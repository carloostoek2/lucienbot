# Gamification Domain

Sistema de puntos (besitos), niveles y recompensas.

## Services
- [besito_service.py](../besito_service.py) - Puntos, transacciones, historial
- [daily_gift_service.py](../daily_gift_service.py) - Regalo diario

## Handlers
- [gamification_user_handlers.py](../../handlers/gamification_user_handlers.py) - Usuario
- [gamification_admin_handlers.py](../../handlers/gamification_admin_handlers.py) - Admin

## Modelos
- `User.besitos_balance` - Saldo de besitos
- `BesitoTransaction` - Historial de transacciones

## BesitoService API
```python
- credit_besitos(user_id, amount, reason)  # Acreditar
- debit_besitos(user_id, amount, reason)  # Debitar
- get_balance(user_id)                     # Consultar saldo
- get_transaction_history(user_id)         # Historial
```

## Reglas de Negocio
- **No saldos negativos**
- Transacciones atómicas
- Historial inmutable
- Logging: módulo, acción, user_id, resultado

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos existentes en besito_service.py
4. No duplicar lógica entre services
