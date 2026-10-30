# Recordatorio a usuarios Free inactivos (PR #13)

Origen: [PR #13](https://github.com/carloostoek2/lucienbot/pull/13), mergeado el 2026-10-29 (ítem 6 del informe). **Apagado por defecto** con `FEATURE_FREE_INACTIVITY_REMINDER`.

## Qué hace

Un usuario Free que lleva 3 días sin actividad recibe un mensaje privado:

- **Principal:** recuerda que su regalo diario sigue esperándole, con el monto de `daily_gift_config` (ya recortado por los topes del [PR #12](https://github.com/carloostoek2/lucienbot/pull/12)).
- **Alterno** (ciclos siguientes, o si el regalo diario está apagado): Lucien le guarda el lugar; la trivia y su regalo del día siguen esperándole. No promete contenido nuevo.

## Quién lo recibe

- Hizo `/start` al menos una vez (`bot_started_at` no nulo). Los usuarios creados solo por join-request no cuentan.
- No bloqueó al bot (`bot_blocked_at` nulo), está activo, no es admin (ni por rol ni por `ADMIN_IDS`) y no tiene VIP vigente.
- Tuvo actividad **después** de que se encendió el flag: `last_activity_at >= activado_en`. Los inactivos históricos (actividad anterior o nula) nunca lo reciben.

## Qué cuenta como actividad

`middlewares/activity.py` (`ActivityMiddleware`), solo en chat privado: regalo diario y saldo, dados y trivia, tienda, menú principal y `/start`. Las reacciones del canal **no** cuentan. Escribe como máximo una vez cada 15 minutos por usuario. La actividad se registra aunque el flag esté apagado; el flag solo controla el envío.

## Frecuencia y horario

- Uno a los 3 días de inactividad. No se repite hasta que el usuario vuelva y pase otra vez 3 días inactivo. Máximo uno cada 7 días por usuario.
- Solo de 10:00 a 20:59, hora de Ciudad de México. El job `free_inactivity_reminders` corre en el scheduler a los minutos 7 y 37 de cada hora entre las 10 y las 20, y revalida la ventana antes de cada envío.
- Lotes de 200 por corrida, con 50 ms entre envíos.
- `activado_en` se guarda una sola vez en `feature_activations` la primera vez que el job corre con el flag encendido. Apagar y volver a encender no lo mueve.

## Envíos seguros

- **Claim por fila** antes de enviar: dos instancias a la vez (deploy solapado) no mandan dos veces.
- **Bloqueo:** ante `TelegramForbiddenError` se marca `bot_blocked_at` y no se reintenta. Un `/start` posterior lo limpia.
- **`TelegramRetryAfter`:** se libera el claim y se corta el lote. Con otros errores el claim queda, para no duplicar.

## Migración `20261029_free_inactivity_reminder`

- `users` += `bot_started_at`, `last_activity_at`, `last_inactivity_reminder_at`, `bot_blocked_at` (nullable).
- Tabla nueva `feature_activations(key, activated_at)`.
- Índice `ix_users_inactivity_candidates (last_activity_at)`, parcial en PostgreSQL.
- Backfill conservador: `bot_started_at = created_at` solo para usuarios con uso registrado en privado (regalo diario, juegos, órdenes, ciertas transacciones de besitos o un token VIP canjeado). Los de solo join-request quedan nulos hasta su próximo `/start`.
- Idempotente, con downgrade.

## Rollout

1. Mergear con el flag apagado: no se envía nada, solo se registra actividad.
2. Dejarlo correr unos días apagado para que se llenen `last_activity_at` y `bot_started_at`.
3. Encender con `FEATURE_FREE_INACTIVITY_REMINDER=1` en Railway (requiere reinicio).
4. Vigilar el log `inactivity_reminder | run | {sent, blocked, skipped, errors}`. Para apagar: `FEATURE_FREE_INACTIVITY_REMINDER=0` (no borra `activado_en`).

## Riesgo conocido

Un ex-VIP (incluido el VIP corto del PR #12) pasa a Free. Si su última actividad fue hace más de 3 días, puede recibir el recordatorio poco después de que vence su acceso.
