# Diseño: Timeout de 2 Minutos para Trivias por Racha

**Fecha:** 2026-05-05
**Versión:** 1.0
**Estado:** Aprobado

---

## 1. Resumen

Cuando un usuario inicia una racha en una promoción por racha activa (streak pasa de 0 → 1), el sistema registra un timestamp. Si el usuario no interactúa en 2 minutos, su racha se invalida y cualquier código activo se cancela. El objetivo es evitar que los usuarios investiguen respuestas: deben responder todo de corrido.

---

## 2. Mecanismo de Tracking

### Campo FSM

```python
streak_started_at: datetime | None  # UTC timestamp cuando streak pasó de 0→1
```

Se setea **una sola vez** cuando `streak = 0 → 1`. No se reinicializa en cada respuesta.

### Lógica de Verificación

En cada interacción válida (`trivia_answer`, `streak_continue`, `streak_retire`, `streak_exit`):

```python
def _check_streak_timeout(state_data: dict) -> bool:
    """
    Returns True si el timeout está vigente (OK).
    Returns False si expiró → invalidar racha.
    """
    streak_started_at = state_data.get("streak_started_at")
    if not streak_started_at:
        return True  # No hay tracking aún

    elapsed = datetime.now(timezone.utc) - streak_started_at
    return elapsed.total_seconds() <= 120  # 2 minutos
```

---

## 3. Flujo de Invalidación por Timeout

Cuando `now() - streak_started_at > 2 minutos`:

1. **Enviar mensaje de timeout** (voz Lucien, sarcástico)
2. **Invalidar código activo** — `invalidate_streak_code(user_id, config_id)`
   - Código existente pasa a estado `CANCELLED`
3. **Romper racha en GameRecord** — marcar último registro con `payout = 0`
4. **Limpiar FSM state** — remover `streak_started_at`, `streak_mode`, `current_tier_*`, etc.
5. **Resetear streak a 0** — se calcula dinámicamente desde GameRecord en próxima query

---

## 4. Mensaje de Timeout

```python
TIMEOUT_MESSAGE = """🎩 <b>Lucien:</b>
<i>Ah... parece que sus dedos necesitaban un descanso más largo que su mente.
El tiempo corre, incluso para quienes creen que pueden burlarlo.
Su racha ha sido... olvidada.</i>"""
```

Tono: sarcástico, humor negro, sin ofender. Voz de Lucien.

---

## 5. Puntos de Inyección

### `trivia_answer` handler
- **Antes de procesar respuesta:** verificar timeout si `streak > 0`
- **Al acertar y streak pasar de 0→1:** guardar `streak_started_at = now()` en FSM
- **Al fallar:** limpiar `streak_started_at` (racha se rompe, no hay nada que trackear)

### `streak_continue` handler
- Verificar timeout antes de continuar
- Si expira → invalidación completa

### `streak_retire` handler
- Verificar timeout antes de procesar retiro
- Si expira → invalidación completa (no genera código)

### `streak_exit` handler
- Verificar timeout antes de salir
- Si expira → invalidación completa

---

## 6. Servicio — Nuevo Helper

```python
# services/game_service.py

async def invalidate_streak_code(
    self,
    user_id: int,
    config_id: int
) -> None:
    """
    Cancela código activo y limpia streak del usuario.
    Se llama tanto por timeout como por respuesta incorrecta.
    """
    # 1. Buscar código ACTIVE para este user + config
    # 2. Cambiar estado a CANCELLED
    # 3. Marcar payout=0 en último GameRecord para romper streak calculada
    # 4. Limpiar FSM data del usuario
```

---

## 7. Scheduler de Limpieza (Casos Extremos)

Job periódico cada 60 segundos que revise usuarios con:
- streak > 0 (último GameRecord con payout > 0)
- `streak_started_at` expirado (> 2 min sin interacción)

```python
# services/game_service.py

async def cleanup_expired_streaks(self) -> int:
    """
    Busca usuarios huérfanos (con streak activa pero sin interacción reciente).
    Retorna cantidad de streak invalidadas.
    """
```

Este scheduler cubre el caso donde el usuario cierra Telegram y no vuelve a interactuar.

---

## 8. Comportamiento por Escenario

| Escenario | Comportamiento |
|-----------|----------------|
| streak 0→1, responde en < 2 min | Racha continúa, timer arranca |
| streak > 0, responde en < 2 min | Racha continúa, timer NO se reinicia |
| streak > 0, responde en > 2 min | Timeout + invalidación |
| Usuario alcanza tier, elige "continue" en < 2 min | Sigue jugando |
| Usuario alcanza tier, vuelve en 3 min | Timeout + invalidación |
| Usuario con streak se va y no vuelve | Scheduler lo limpia tras 2 min |

---

## 9. Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `services/game_service.py` | `_check_streak_timeout()`, `invalidate_streak_code()`, `cleanup_expired_streaks()` |
| `handlers/game_user_handlers.py` | Validación timeout en `trivia_answer`, `streak_continue`, `streak_retire`, `streak_exit` |
| `messages/trivia_messages.py` | Constante `TIMEOUT_MESSAGE` |

---

## 10. Decisiones de Diseño

1. **Timer no se reinicia** — una vez que arranca, corre los 2 minutos completos. Si el usuario quiere más tiempo, no lo tiene.
2. **Timeout aplica en todo el flujo** — tanto preguntas como elección de tier.
3. **Solo en promociones por racha** — streak > 0 en TriviaPromotionConfig activa.
4. **FSM state para tracking** — simple, sin infraestructura extra.