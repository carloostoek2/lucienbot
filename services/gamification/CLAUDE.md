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

- Item 6 (remaining besito composers unification / 4th and final in tirón): BroadcastService + GameService + DailyGiftService held direct compositions reduced (locals on-demand BesitoService(db=...) *only* inside the credit/debit call sites: reaction register/check_and_register, game play_* (win+streak bonus), daily claim_gift; daily already used lazy prop + _get_db(), now local inside claim only; property kept for test guards/compat + hasattr daily precedent). 1-2 high-value observational listeners added (on_besitos_awarded_broadcast_reaction_observer + on_besitos_awarded_game_award_observer; copy story 670-694 + "MUST NOT credit/debit/mutate", best effort, DESIRED CONTRACT, domain logs "broadcast | ..." / "game | ..."; 0 re-entrancy, 0 mutation, 0 impact on credit contracts/partial failure/atomicity gold). Central reg in bot.py extended (now 4 listeners: narrative + rewards + broadcast + game; comment "+ Item 6"). 0 behavior/0 atomicity (golds re-runs + patch schedule_emit + reaction/mission chains + daily atomic + game play + besito emit all green post; "credit survives deliver False" + "post-credit misiones (best effort) + event listeners (best effort)" protected). 1-line fixes only in 3 tests (broadcast owns assert, daily claim accesses + guards, cross daily patches) with daily precedent + comments. Docs: broadcast/CLAUDE new cross section, this append, missions/CLAUDE bullets to Item5, decisions Item6 entry + "BATCH: 4 items completed in tirón". Refs: 24-PLAN.md + gsd-remaining-besito-compositions.log (GSD pre every, self-check PASSED), test_cross_service_atomicity.py (gold), test_reaction_* (chains), atomicity gold patterns (patch, TestSession, N806, TG 777, try/finally, strict deltas/tx source).
- The 3 critical systems (gamif as source of credits, missions/rewards via atomic, narrative as listener) remain protected; scope tight (0 other composers, 0 get_service for locals, 0 new tests beyond 1-lines, 0 handler changes).
