# PLAN — broadcast-robust-single-send (Item 1/1)

## Objetivo
Eliminar envío en 2 pasos (send + edit_message_reply_markup) del broadcast; validar contenido antes de enviar; no borrar mensajes del canal en fallos de tracking.

## Archivos
- `handlers/broadcast_handlers.py` — helpers puros + `send_broadcast_to_channel` + refactor `confirm_and_send_broadcast`
- `tests/integration/test_callbackdata_broadcast.py` — chunking + validación
- `tests/handlers/test_broadcast_handlers.py` — confirm single-send, validation gate

## Fases
1. Pure helpers: `chunk_inline_buttons`, `validate_broadcast_content_for_send`, chunk en `build_broadcast_send_markup`
2. `send_broadcast_to_channel` + `notify_broadcast_send_success`; refactor confirm handler ≤50 LOC
3. Tests + pytest golds

## Tests
```bash
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  tests/integration/test_callbackdata_broadcast.py tests/handlers/test_broadcast_handlers.py \
  -k "broadcast or Broadcast"
python -m pytest -q --tb=line -p no:cov --override-ini="addopts=" \
  -k "reaction_ or cross_service_atomicity"
```

## 3 crit
0 mutation en besitos/reactions credit paths; solo cambio de envío UI admin broadcast.