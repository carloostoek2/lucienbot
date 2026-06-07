# Gamification Domain

Sistema de puntos (besitos), niveles y recompensas.

## Services
- [besito_service.py](../besito_service.py) - Puntos, transacciones, historial
- [daily_gift_service.py](../daily_gift_service.py) - Regalo diario

## Handlers
- [gamification_user_handlers.py](../../handlers/gamification_user_handlers.py) - Usuario
- [gamification_admin_handlers.py](../../handlers/gamification_admin_handlers.py) - Admin

## Modelos
- `BesitoBalance` - Saldo por usuario (NO `User.besitos_balance`)
- `BesitoTransaction` - Historial de transacciones (inmutable)

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

## Cross-domain notifications (EventBus PoC Item 1)
- `BesitoService.credit_besitos` emite el evento `"besitos_awarded"` (const `EVENT_BESITOS_AWARDED`) **después** del `db.commit()` exitoso (best effort, via `schedule_emit` + `InternalEventBus.emit` con `gather(..., return_exceptions=True)`).
- El emit **nunca** afecta el retorno bool, ni causa rollback, ni altera la transacción de crédito.
- Payload: `{"user_id", "amount", "source" (str .value), "reference_id", "description", "timestamp" (ISO UTC)}`.
- Otros dominios pueden subscribirse explícitamente (ver `bot.py` on_startup + `get_event_bus().register`).
- Logging: el bus loguea por listener (incluyendo errores) + "event_bus | emit | user_id=... | event=besitos_awarded | listeners=N | errors=E".
- Primer subscriptor: narrative (ver services/narrative/CLAUDE.md).
- Ver `services/event_bus.py` y tests/unit/test_event_bus.py para el contrato.
