# Misiones: antiduplicados (PR #11)

Origen: [PR #11](https://github.com/carloostoek2/lucienbot/pull/11), mergeado el 2026-10-29. Es el "PR A" del informe de impacto de misiones (ítems 5a y 5b).

## Problema

El análisis de impacto encontró varias vías de doble pago en misiones (hallazgos G1–G9): filas de progreso duplicadas por usuario y misión, un cooldown que el catch-up se saltaba, dos relojes distintos para `completed_at` y `delivered_at`, paquetes que se podían reenviar al reanudar una entrega y logros de historia que bloqueaban el pago de una misión con el mismo id. Además, al reactivar una misión se pagaba de golpe todo el backlog acumulado.

**Las misiones siguen apagadas.** Ninguna se reactiva sola con este cambio.

## Migración `20261029_mission_progress_unique`

Corre en el `alembic upgrade head` del arranque.

1. **Limpia duplicados de `user_mission_progress`.** Por cada par `(user_id, mission_id)` repetido se queda una fila: la completada si existe; si no, la de mayor `current_value`; si siguen empatadas, la de menor `id`. En esa fila se fusionan:
   - `completed_at`: el más antiguo entre las filas completadas.
   - `last_reference_id`: el de la fila conservada o, si está vacío, el más reciente.
   - `started_at`: el más antiguo.

   Las demás filas se borran y cada grupo queda en el log del deploy.
2. **`UNIQUE (user_id, mission_id)`** como `uq_user_mission_progress`. No traga errores: si falla, falla el deploy.
3. **Índice único parcial en `besito_transactions`**: `uq_besito_tx_mission_reward_credit (user_id, reference_id)` para `source='MISSION'`, `type='CREDIT'`, `description LIKE 'Recompensa:%'` e `id` mayor al máximo al migrar.
   - Solo cubre créditos. Las filas compensatorias del arreglo del 2026-10-29 (`fix-2026-10-29 dup-…`) son `DEBIT` y no chocan.
   - Solo protege filas nuevas: el histórico de abril todavía tiene créditos duplicados (se compensaron, no se borraron).
   - El prefijo `Recompensa:` deja fuera los logros de historia (`Logro desbloqueado: …`), que usan `source=MISSION` con otro espacio de ids. El prefijo está centralizado en `MISSION_REWARD_CREDIT_PREFIX`.
4. `downgrade` borra el índice y la constraint. No restaura los duplicados.

## Reglas nuevas de misiones

- **Una sola fila de progreso (G1):** el get-or-create inserta dentro de un SAVEPOINT; si la UNIQUE rechaza la fila, la vuelve a leer (con lock cuando corresponde). `set_progress` usa `FOR UPDATE`.
- **Cooldown real (G2):** se mide desde la última entrega finalizada (`user_reward_history.delivered_at`, reloj de BD) y aplica también en el catch-up. Se eliminó `skip_cooldown`. Durante el cooldown el progreso RECURRING no avanza: una misión `target=1` con 24 h paga como máximo una vez cada 24 h.
- **Un solo reloj (G3):** `completed_at` se escribe con `func.now()`; la edad de los claims también se mide con el reloj de la BD (`utils/db_clock.py`).
- **Entregas en vuelo (G4):** el TTL del claim sube de 60 s a 600 s. Los paquetes se marcan `__package_sending__` antes de enviarse; si el proceso muere a mitad, la reanudación no los reenvía (como máximo una entrega, con warning en el log).
- **Logros vs. misiones (G5):** `_has_mission_besitos_credit` filtra `type=CREDIT` y la descripción `Recompensa:`. Si el índice rechaza un crédito concurrente, la entrega se toma como "ya pagada".
- **Legado (G7):** `increment_progress` revisa el `reference_id` duplicado antes de reiniciar.
- **Recompensa pendiente (G9):** una misión RECURRING completada con recompensa pendiente ya no se reinicia con un incremento nuevo; la entrega el catch-up.

## Backlog al reactivar (G8)

- El catch-up no paga completaciones sin entregar de más de 48 h (`PENDING_DELIVERY_MAX_AGE`): las expira, reinicia el progreso a 0 y deja el log `pending_completion_expired`.
- Reactivar una misión (`update_mission(is_active=True)` desde inactiva, que es lo que hace el toggle de admin) expira todo su backlog sin entregar, sin importar la edad.
- Excepción: las filas con un claim de VIP en vuelo (marker `token:`/`sent:`) no se expiran; se reanudan por el flujo normal.
- `MissionService.count_pending_completions(mission_id)` sirve de dry-run: cuenta cuántas pagaría hoy.

## Rollout y verificación

1. Antes del deploy, en solo lectura: confirmar que existe `uq_broadcast_user_reaction` en `broadcast_reactions` y que no hay reacciones duplicadas. Si la constraint no existe, no hay que reactivar misiones de reacción.
2. Mergear y desplegar. En el log deben aparecer `user_mission_progress dedup | groups=…` y `uq_besito_tx_mission_reward_credit ensured`.
3. Después del deploy: comprobar que existen `uq_user_mission_progress` y `uq_besito_tx_mission_reward_credit`, y que no quedan duplicados en `user_mission_progress`.
4. Reactivar las misiones de una en una desde admin y vigilar `besito_transactions` con `source='MISSION'` durante 24 h.

Las consultas exactas están en la descripción del PR #11.

## Riesgos aceptados

- Las completaciones de más de 48 h sin entregar se pierden y el usuario reinicia el ciclo. Es intencional.
- Una misión RECURRING configurada contando con que el cooldown no limitaba ahora paga menos.
