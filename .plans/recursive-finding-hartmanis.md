# Plan: Reinicio Automático para Promociones de Trivia (Duración Relativa)

## Contexto

El usuario quiere agregar una funcionalidad de **reinicio automático del contador** cuando se agote el tiempo de una promoción con duración relativa en el sistema de trivias de minijuegos.

### Requisitos:
1. **Opción binaria (sí/no)** durante la creación de la promoción para activar el reinicio automático
2. **Al activarse**: el contador se reinicia al **25% del tiempo original** cuando expire
3. **Número de ciclos**: si se habilita, solicitar también el máximo de ciclos de reinicio permitidos
4. **Al completar los ciclos**: la promoción finaliza

## Archivos a modificar

### 1. `models/models.py`
- Agregar campos a `TriviaPromotionConfig`:
  - `auto_reset_enabled: Boolean` - si el reinicio automático está activo
  - `reset_count: Integer` - contador de reinicios ejecutados
  - `max_reset_cycles: Integer` - máximo de ciclos permitidos (nullable)

### 2. `handlers/trivia_discount_admin_handlers.py`
- Agregar estado FSM: `waiting_auto_reset` y `waiting_reset_cycles`
- Después de solicitar la duración relativa,preguntar si desea habilitar el reinicio automático
- Si responde "sí", solicitar el número máximo de ciclos
- Mostrar en la confirmación el estado del reinicio automático

### 3. `services/trivia_discount_service.py`
- Modificar `create_trivia_promotion_config()` para aceptar los nuevos parámetros
- Agregar método `check_and_reset_if_expired(config_id)` que:
  - Verifica si la promoción ha expirado
  - Si auto_reset está habilitado y no ha alcanzado el límite de ciclos
  - Reinicia el `started_at` y calcula el 25% del tiempo original
  - Incrementa `reset_count`
- Modificar `get_time_remaining()` para invocar el chequeo de reinicio

### 4. Game Service (verificación)
- En `game_service.py` donde se verifica la vigencia de la promoción, el servicio ya existente manejará el reinicio automáticamente

## Lógica del reinicio

```
Tiempo original: 60 minutos
25%: 15 minutos

Escenario:
1. Expira a los 60 min → se detecta en get_time_remaining()
2. Si auto_reset_enabled=True y reset_count < max_reset_cycles:
   - reset_count += 1
   - started_at = now()
   - duration_minutes = original_duration * 0.25 (15 min)
3. Si reset_count >= max_reset_cycles:
   - marcar como inactiva o expirada
```

## Verificación

1. Crear una promoción con duración relativa y reinicio automático (ej: 1h, 3 ciclos)
2. Verificar que el contador funcione correctamente
3. Simular expiración del tiempo y verificar que se reinicia al 25%
4. Después de los 3 ciclos, verificar que ya no se reinicia y la promoción expira

## Estados FSM necesarios

```python
class TriviaDiscountStates(StatesGroup):
    # ... existentes ...
    waiting_auto_reset = State()      # ¿Desea habilitar reinicio automático?
    waiting_reset_cycles = State()    # ¿Cuántos ciclos máximo?
```