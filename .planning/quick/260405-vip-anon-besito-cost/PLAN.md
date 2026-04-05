# Quick Task: Costo en Besitos para Mensajes Anónimos VIP

**Created:** 2026-04-05
**Task:** Implementar costo de 50 besitos para enviar mensajes anónimos VIP

## Changes Required

### 1. models/models.py
- Add `ANONYMOUS_MESSAGE = "anonymous_message"` to TransactionSource enum

### 2. handlers/vip_user_handlers.py

#### Change A: Import BesitoService and TransactionSource
Add to imports:
```python
from services.besito_service import BesitoService
from models.models import TransactionSource
```

#### Change B: Add constant for cost
```python
ANONYMOUS_MESSAGE_COST = 50  # besitos
```

#### Change C: Update process_anonymous_message (line ~161)
Show cost in preview message:
```python
f"Antes de enviarlo… léalo de nuevo.\n\n"
f"Esto es lo que Diana recibirá:\n\n"
f"<blockquote>{preview}</blockquote>\n\n"
f"💋 <b>Costo: {ANONYMOUS_MESSAGE_COST} besitos</b>\n\n"
f"¿Está seguro de que esto… merece su atención?"
```

#### Change D: Update confirm_anonymous_send (line ~173)
Add balance check and debit before sending:

1. Check sufficient balance using `BesitoService.has_sufficient_balance()`
2. If insufficient, show elegant error message
3. If sufficient, debit using `BesitoService.debit_besitos()` with `TransactionSource.ANONYMOUS_MESSAGE`
4. Only then call `AnonymousMessageService.send_message()`

### 3. Error message for insufficient balance (Lucien voice)
```
🎩 <b>Lucien:</b>

<i>Los mensajes anónimos tienen un precio...</i>

Necesita <b>{ANONYMOUS_MESSAGE_COST} besitos</b> para enviar este susurro a Diana.

Su saldo actual: <b>{current_balance} besitos</b>

Participe en la comunidad, reaccione a las publicaciones de Diana o reclame su regalo diario para acumular más.
```

## Testing
- Verify balance check works
- Verify debit happens before message send
- Verify error shown when insufficient balance
- Verify success flow when sufficient balance
